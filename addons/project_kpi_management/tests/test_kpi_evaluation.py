from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestKpiEvaluation(TransactionCase):
    """Phase 3: phiếu đánh giá, công thức điểm, quy trình duyệt."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("project_kpi_management.kpi_template_developer")
        cls.job = cls.env["hr.job"].create({"name": "Dev test", "kpi_template_id": cls.template.id})
        cls.department = cls.env["hr.department"].create({"name": "R&D test"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Nhân viên A", "job_id": cls.job.id, "department_id": cls.department.id,
        })
        cls.period = cls.env["kpi.period"].create({
            "name": "Kỳ test", "date_from": "2026-10-01", "date_to": "2026-10-31",
        })

    def _evaluation(self, **vals):
        return self.env["kpi.evaluation"].create({
            "employee_id": self.employee.id, "period_id": self.period.id, **vals,
        })

    def _line(self, ev, code):
        return ev.line_ids.filtered(lambda l: l.metric_id.code == code)

    def _fill_all(self, ev, actuals):
        """Giả lập engine: đặt thực tế và khối lượng đủ lớn cho mọi chỉ số."""
        for code, actual in actuals.items():
            self._line(ev, code).write({"actual": actual, "volume": 100})

    def test_snapshot_from_template_and_employee(self):
        ev = self._evaluation()
        self.assertEqual(ev.template_id, self.template)
        self.assertEqual(ev.job_id, self.job)
        self.assertEqual(ev.department_id, self.department)
        self.assertEqual(len(ev.line_ids), 9)
        self.assertEqual(self._line(ev, "D1").target, 90)
        # Sửa template sau khi tạo phiếu không ảnh hưởng phiếu
        self.template.line_ids.filtered(lambda l: l.metric_id.code == "D1").target = 95
        self.assertEqual(self._line(ev, "D1").target, 90)

    @mute_logger("odoo.sql_db")
    def test_one_evaluation_per_employee_period(self):
        self._evaluation()
        with self.assertRaises(IntegrityError):
            self._evaluation()

    def test_empty_template_blocked(self):
        empty = self.env["kpi.template"].create({"name": "Rỗng"})
        with self.assertRaises(UserError):
            self._evaluation(template_id=empty.id)

    def test_closed_period_blocked(self):
        self.period.action_close()
        with self.assertRaises(ValidationError):
            self._evaluation()

    def test_score_formula(self):
        ev = self._evaluation()
        # Cao là tốt: 81/90 = 90; Thấp là tốt: 0.3/0.6 = 50; trần 120
        self._fill_all(ev, {"D1": 81, "D2": 40, "D3": 0.6, "D4": 0, "D5": 80,
                            "D6": 70, "D7": 24, "D8": 1, "D9": 4})
        self.assertAlmostEqual(self._line(ev, "D1").score, 90)
        self.assertAlmostEqual(self._line(ev, "D2").score, 120)  # 200% bị chặn trần
        self.assertAlmostEqual(self._line(ev, "D3").score, 50)
        self.assertAlmostEqual(self._line(ev, "D4").score, 120)  # thấp tốt, thực tế 0
        # (90*20 + 120*10 + 50*15 + 120*15 + 100*10 + 100*10 + 100*5 + 100*5 + 100*10) / 100
        self.assertAlmostEqual(ev.kpi_score, 95.5)
        self.assertEqual(ev.rating, "good")
        self.assertEqual(ev.final_rating, "good")

    def test_not_applicable_excluded(self):
        ev = self._evaluation()
        self._fill_all(ev, {"D1": 90, "D2": 20, "D3": 0, "D4": 0, "D5": 80,
                            "D6": 70, "D7": 0, "D8": 1, "D9": 4})
        # D3, D7 không đủ khối lượng: không được điểm trần, bị loại khỏi tử và mẫu số
        self._line(ev, "D3").volume = 0
        self._line(ev, "D7").volume = 0
        self.assertFalse(self._line(ev, "D3").is_applicable)
        self.assertEqual(ev.applicable_weight, 80)
        self.assertAlmostEqual(ev.kpi_score, (100 * 65 + 120 * 15) / 80)

    def test_insufficient_data_needs_manual_rating(self):
        ev = self._evaluation()
        self._line(ev, "D9").actual = 4  # chỉ D2, D8, D9 áp dụng: trọng số 25
        self.assertTrue(ev.insufficient_data)
        self.assertFalse(ev.rating)
        with self.assertRaises(UserError):
            ev.action_submit()
        ev.write({"manual_rating": "pass", "manual_rating_note": "Mới vào giữa kỳ"})
        self.assertEqual(ev.final_rating, "pass")
        ev.action_submit()
        self.assertEqual(ev.state, "submitted")

    def test_rating_boundaries(self):
        ev = self._evaluation()
        self._fill_all(ev, {"D1": 90, "D2": 20, "D3": 0.3, "D4": 5, "D5": 80,
                            "D6": 70, "D7": 24, "D8": 1, "D9": 4})
        self.assertAlmostEqual(ev.kpi_score, 100)
        self.assertEqual(ev.rating, "excellent")
        ev.write({"manager_adjustment": -0.01, "adjustment_note": "Sát ngưỡng"})
        self.assertEqual(ev.rating, "good")  # 99.99 → Tốt, không rơi vào khoảng hở
        ev.write({"manager_adjustment": -10, "adjustment_note": "Thử ngưỡng"})
        self.assertAlmostEqual(ev.final_score, 90)
        self.assertEqual(ev.rating, "good")  # đúng 90 thuộc [90, 100)

    def test_adjustment_rules(self):
        ev = self._evaluation()
        with self.assertRaises(ValidationError):
            ev.write({"manager_adjustment": 5})  # thiếu lý do
        with self.assertRaises(ValidationError):
            ev.write({"manager_adjustment": 11, "adjustment_note": "Quá biên độ"})
        ev.write({"manager_adjustment": 5, "adjustment_note": "Hỗ trợ dự án gấp"})
        self.assertEqual(ev.manager_adjustment, 5)

    def test_manual_metric_required_before_submit(self):
        ev = self._evaluation()
        self._fill_all(ev, {"D1": 90, "D2": 20, "D3": 0.3, "D4": 5, "D5": 80, "D6": 70, "D7": 24, "D8": 1})
        with self.assertRaises(UserError):
            ev.action_submit()  # D9 chưa chấm
        self._line(ev, "D9").actual = 4
        self.assertTrue(self._line(ev, "D9").actual_entered)
        ev.action_submit()
        self.assertEqual(ev.state, "submitted")

    def _submitted(self):
        ev = self._evaluation()
        self._fill_all(ev, {"D1": 90, "D2": 20, "D3": 0.3, "D4": 5, "D5": 80,
                            "D6": 70, "D7": 24, "D8": 1, "D9": 4})
        ev.action_submit()
        return ev

    def _reason(self, ev, mode, reason):
        wizard = Form(self.env["kpi.evaluation.reason.wizard"].with_context(
            default_evaluation_id=ev.id, default_mode=mode))
        wizard.reason = reason
        wizard.save().action_confirm()

    def test_workflow_lock_return_reopen(self):
        ev = self._submitted()
        # Đã gửi: khoá
        with self.assertRaises(UserError):
            ev.write({"manager_adjustment": 1, "adjustment_note": "x"})
        with self.assertRaises(UserError):
            self._line(ev, "D1").target = 80
        # Trả về nháp có lý do, lưu vào chatter
        self._reason(ev, "return", "Sai số liệu D1")
        self.assertEqual(ev.state, "draft")
        self.assertIn("Sai số liệu D1", ev.message_ids[0].body)
        # Duyệt rồi mở lại
        ev.action_submit()
        ev.action_approve()
        self.assertEqual(ev.state, "approved")
        with self.assertRaises(UserError):
            self._line(ev, "D9").actual = 5
        with self.assertRaises(UserError):
            ev.unlink()
        self._reason(ev, "reopen", "Duyệt nhầm")
        self.assertEqual(ev.state, "draft")
        self.assertIn("Duyệt nhầm", ev.message_ids[0].body)

    def test_approve_requires_submitted(self):
        ev = self._evaluation()
        with self.assertRaises(UserError):
            ev.action_approve()

    def test_target_editable_in_draft(self):
        ev = self._evaluation()
        self._line(ev, "D2").target = 30  # mục tiêu D2 theo team, sửa khi Nháp
        self.assertEqual(self._line(ev, "D2").target, 30)
