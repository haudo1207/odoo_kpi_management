from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiTargetSuggestion(TransactionCase):
    """Đợt B2 (v1.4): gợi ý mục tiêu Dễ / Vừa / Khó từ lịch sử các kỳ đã duyệt (phân vị 25 / 50 / 75)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.today = fields.Date.today()
        cls.department = env["hr.department"].create({"name": "Phòng gợi ý"})
        cls.metrics = {m.code: m for m in env["kpi.metric"].search([])}
        cls._counter = 0

    def setUp(self):
        super().setUp()
        self.templates = {}  # template tạo trong từng test (được rollback theo test)

    def _template(self, code, period_type="month", insufficient=False):
        key = (code, period_type, insufficient)
        if key not in self.templates:
            lines = [(0, 0, {"metric_id": self.metrics[code].id, "target": 10, "weight": 10 if insufficient else 100})]
            if insufficient:  # dòng 90% không áp dụng (volume 0 < min_volume 1) → trọng số áp dụng 10 < 50
                lines.append((0, 0, {"metric_id": self.metrics["D4"].id, "target": 5, "weight": 90, "min_volume": 1}))
            self.templates[key] = self.env["kpi.template"].create({
                "name": f"Lịch sử {key}", "period_type": period_type, "line_ids": lines,
            })
        return self.templates[key]

    def _history(self, code, values, employee=None, period_type="month", state="approved", insufficient=False,
                 applicable=True):
        """Mỗi giá trị là một kỳ đã duyệt, từ cũ tới mới (giá trị cuối là kỳ gần nhất)."""
        employee = employee or self._employee(f"sg_{self._counter}")
        template = self._template(code, period_type, insufficient)
        for index, actual in enumerate(values):
            TestKpiTargetSuggestion._counter += 1
            end = self.today - timedelta(days=30 * (len(values) - index))
            period = self.env["kpi.period"].create({
                "name": f"Lịch sử {self._counter}", "period_type": period_type,
                "date_from": end - timedelta(days=29), "date_to": end,
            })
            ev = self.env["kpi.evaluation"].create({
                "employee_id": employee.id, "period_id": period.id, "template_id": template.id,
            })
            line = ev.line_ids.filtered(lambda l: l.metric_id.code == code)
            line.write({"actual": actual, "volume": 1 if applicable else 0})
            if not applicable:
                line.min_volume = 1  # volume 0 < min_volume 1 → Không áp dụng
            ev.write({"state": state})
        return employee

    def _employee(self, login, department=None):
        TestKpiTargetSuggestion._counter += 1
        return self.env["hr.employee"].create({
            "name": login, "user_id": new_test_user(self.env, login=f"{login}_{self._counter}").id,
            "department_id": (department or self.department).id,
            "job_id": self.env.ref("project_kpi_management.hr_job_developer").id,
        })

    def _override(self, code, employee=None, department=None, period_type="month"):
        template = self._template(code, period_type)
        return self.env["kpi.target.override"].create({
            "template_line_id": template.line_ids.filtered(lambda l: l.metric_id.code == code).id,
            "employee_id": employee.id if employee else False,
            "department_id": False if employee else (department or self.department).id,
            "target": 1,
        })

    def test_percentiles_higher_is_better(self):
        self._history("D2", [10, 20, 30, 40])
        override = self._override("D2")
        self.assertTrue(override.suggestion_available)
        # 4 kết quả: P25 = 10 + 0,75·10 = 17,5; P50 = 25; P75 = 30 + 0,25·10 = 32,5
        self.assertEqual((override.suggestion_easy, override.suggestion_medium, override.suggestion_hard), (17.5, 25.0, 32.5))

    def test_lower_is_better_reverses_difficulty(self):
        """Mật độ lỗi (thấp là tốt): con số thấp hơn mới là mục tiêu khó hơn → Dễ = phân vị 75, Khó = phân vị 25."""
        self._history("D3", [0.1, 0.2, 0.3, 0.4])
        override = self._override("D3")
        self.assertAlmostEqual(override.suggestion_easy, 0.325)
        self.assertAlmostEqual(override.suggestion_medium, 0.25)
        self.assertAlmostEqual(override.suggestion_hard, 0.175)

    def test_only_six_latest_periods(self):
        self._history("D2", [1000, 10, 20, 30, 40, 50, 60])  # kỳ cũ nhất bị loại
        override = self._override("D2")
        self.assertEqual((override.suggestion_easy, override.suggestion_medium, override.suggestion_hard), (22.5, 35.0, 47.5))

    def test_needs_three_periods(self):
        self._history("D2", [10, 20])
        override = self._override("D2")
        self.assertFalse(override.suggestion_available)
        self.assertIn("Chưa đủ dữ liệu", override.suggestion_note)
        with self.assertRaises(UserError):
            override.action_apply_medium()

    def test_excludes_unapproved_insufficient_not_applicable_and_other_period_type(self):
        self._history("D2", [10, 20, 30])                                    # hợp lệ
        self._history("D2", [900, 900, 900], state="submitted")              # chưa duyệt
        self._history("D2", [900, 900, 900], insufficient=True)              # phiếu thiếu dữ liệu
        self._history("D2", [900, 900, 900], applicable=False)               # dòng Không áp dụng
        self._history("D2", [900, 900, 900], period_type="quarter")          # khác loại kỳ
        override = self._override("D2")
        self.assertEqual((override.suggestion_easy, override.suggestion_medium, override.suggestion_hard), (15.0, 20.0, 25.0))

    def test_employee_scope_uses_only_that_employees_history(self):
        mine = self._history("D2", [10, 20, 30])
        self._history("D2", [100, 200, 300])  # đồng nghiệp cùng phòng ban
        override = self._override("D2", employee=mine)
        self.assertEqual(override.suggestion_medium, 20.0)
        department = self._override("D2")
        self.assertEqual(len(self.env["kpi.evaluation.line"].search([("department_id", "=", self.department.id)])), 6)
        self.assertNotEqual(department.suggestion_medium, 20.0)

    def test_apply_buttons_write_target_and_stay_editable(self):
        self._history("D2", [10, 20, 30, 40])
        override = self._override("D2")
        override.action_apply_easy()
        self.assertEqual(override.target, 17.5)
        override.action_apply_medium()
        self.assertEqual(override.target, 25.0)
        override.action_apply_hard()
        self.assertEqual(override.target, 32.5)
        override.target = 28  # chỉ là gợi ý: quản lý vẫn sửa được
        self.assertEqual(override.target, 28)
