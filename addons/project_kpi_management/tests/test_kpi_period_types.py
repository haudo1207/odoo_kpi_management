from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiPeriodTypes(TransactionCase):
    """Đợt B1 (v1.4): kỳ riêng theo bộ KPI — Developer theo tháng, bộ theo quý chỉ tạo phiếu ở kỳ Quý."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.today = fields.Date.today()
        cls.quarter_template = env["kpi.template"].create({
            "name": "Theo quý (test)", "period_type": "quarter",
            "line_ids": [(0, 0, {"metric_id": env.ref("project_kpi_management.kpi_metric_d2").id, "target": 60, "weight": 100})],
        })
        cls.quarter_job = env["hr.job"].create({"name": "Vai trò theo quý", "kpi_template_id": cls.quarter_template.id})
        cls.month_employee = cls._employee("pt_month", env.ref("project_kpi_management.hr_job_developer"))
        cls.quarter_employee = cls._employee("pt_quarter", cls.quarter_job)

    @classmethod
    def _employee(cls, login, job):
        return cls.env["hr.employee"].create({
            "name": login, "user_id": new_test_user(cls.env, login=login).id, "job_id": job.id,
        })

    def _period(self, period_type, days_back_from, days_back_to, **vals):
        return self.env["kpi.period"].create({
            "name": f"Kỳ {period_type} {days_back_from}", "period_type": period_type,
            "date_from": self.today - timedelta(days=days_back_from), "date_to": self.today - timedelta(days=days_back_to),
            **vals,
        })

    # ---- Tạo phiếu chỉ cho bộ cùng loại kỳ ----

    def test_wizard_creates_only_matching_period_type(self):
        for period_type, expected, other in (
            ("month", self.month_employee, self.quarter_employee),
            ("quarter", self.quarter_employee, self.month_employee),
        ):
            period = self._period(period_type, 20, -10)
            form = Form(self.env["kpi.evaluation.generate.wizard"])
            form.period_id = period
            wizard = form.save()
            self.assertIn(expected, period._eligible_employees())
            self.assertNotIn(other, period._eligible_employees())
            wizard.action_generate()
            employees = period.evaluation_ids.employee_id
            self.assertIn(expected, employees)
            self.assertNotIn(other, employees)

    def test_cron_creates_only_matching_period_type(self):
        self.env["kpi.period"].search([]).write({"auto_generated": True})
        month = self._period("month", 40, 10)
        quarter = self._period("quarter", 100, 10)
        self.env["kpi.period"]._cron_generate_evaluations()
        self.assertIn(self.month_employee, month.evaluation_ids.employee_id)
        self.assertNotIn(self.quarter_employee, month.evaluation_ids.employee_id)
        self.assertIn(self.quarter_employee, quarter.evaluation_ids.employee_id)
        self.assertNotIn(self.month_employee, quarter.evaluation_ids.employee_id)

    def test_cannot_change_period_type_with_open_period_evaluations(self):
        period = self._period("quarter", 20, -10)
        self.env["kpi.evaluation"].create({"employee_id": self.quarter_employee.id, "period_id": period.id})
        with self.assertRaises(UserError):
            self.quarter_template.period_type = "month"
        period.action_close()
        self.quarter_template.period_type = "month"
        self.assertEqual(self.quarter_template.period_type, "month")

    # ---- P2 với PM theo quý ----

    def _closed_evaluation(self, employee, period, actual, template):
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": period.id, "template_id": template.id})
        ev.line_ids.write({"actual": actual})
        ev.write({"state": "submitted", "computed_date": fields.Datetime.now()})
        return ev

    def test_p2_quarterly_lead_averages_per_person_over_monthly_evaluations(self):
        """PM theo quý, 2 cấp dưới theo tháng: A có 3 phiếu (50, 75, 100 → 75), B có 1 phiếu (50).
        P2 = (75 + 50) / 2 = 62,5 trên 2 người. Nếu gộp chung mọi phiếu sẽ ra (50+75+100+50)/4 = 68,75 — người làm
        đủ quý có trọng số gấp 3 người mới vào. Phiếu kỳ dài hơn kỳ PM (100 điểm) không nằm trọn nên không tính."""
        env = self.env
        template = env["kpi.template"].create({
            "name": "Một chỉ số nhập tay (test)",
            "line_ids": [(0, 0, {"metric_id": env.ref("project_kpi_management.kpi_metric_d9").id, "target": 4, "weight": 100})],
        })
        pm = self._employee("pt_pm", env.ref("project_kpi_management.hr_job_pm"))
        a, b, c = (self._employee(login, env.ref("project_kpi_management.hr_job_developer")) for login in ("pt_a", "pt_b", "pt_c"))
        for sub in (a, b, c):
            sub.parent_id = pm
        start = self.today - timedelta(days=89)
        quarter = env["kpi.period"].create({
            "name": "Quý test", "period_type": "quarter", "date_from": start, "date_to": self.today,
        })
        months = [
            env["kpi.period"].create({
                "name": f"Tháng {i}", "period_type": "month",
                "date_from": start + timedelta(days=30 * i), "date_to": start + timedelta(days=30 * i + 29),
            })
            for i in range(3)
        ]
        longer = env["kpi.period"].create({
            "name": "Kỳ dài hơn quý", "period_type": "quarter", "date_from": start, "date_to": self.today + timedelta(days=30),
        })
        for month, actual in zip(months, (2, 3, 4)):  # 50, 75, 100
            self._closed_evaluation(a, month, actual, template)
        self._closed_evaluation(b, months[2], 2, template)  # 50
        self._closed_evaluation(c, longer, 4, template)     # 100 nhưng kỳ không nằm trọn trong quý của PM
        actual, volume = env["kpi.engine"].compute_actual(
            env.ref("project_kpi_management.kpi_metric_p2"), pm, quarter.date_from, quarter.date_to
        )
        self.assertEqual(volume, 2)
        self.assertAlmostEqual(actual, 62.5)
