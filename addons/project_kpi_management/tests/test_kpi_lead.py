from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiLead(TransactionCase):
    """Bước 4 (Chương 9.2, Ưu tiên 2): bộ KPI Team Lead / PM — P1 cấu hình, P2, P3 hàm Python, P5 nhập tay."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["kpi.engine"]
        today = fields.Date.today()
        cls.today = today
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ Lead", "date_from": cls.date_from, "date_to": cls.date_to})
        cls.lead_user = new_test_user(cls.env, login="kpi_lead_pm")
        cls.lead = cls.env["hr.employee"].create({
            "name": "PM", "user_id": cls.lead_user.id, "job_id": cls.env.ref("project_kpi_management.hr_job_pm").id,
        })
        cls.project = cls.env["project.project"].create({"name": "DA của Lead", "user_id": cls.lead_user.id})
        cls.metrics = {m.code: m for m in cls.env["kpi.metric"].search([])}

    def _compute(self, code):
        return self.engine.compute_actual(self.metrics[code], self.lead, self.date_from, self.date_to)

    def _milestone(self, deadline, reached=False, project=None):
        return self.env["project.milestone"].create({
            "name": "M", "project_id": (project or self.project).id, "deadline": deadline, "is_reached": reached,
        })

    # ---- P1 ----

    def test_p1_has_no_python_code_and_uses_domain(self):
        self.assertEqual(self.metrics["P1"].compute_mode, "domain")
        self.assertFalse(hasattr(self.engine, "_metric_p1"))

    def test_p1_on_time_milestones_of_lead_projects(self):
        t = self.today
        self._milestone(t + timedelta(days=2), reached=True)    # đạt hôm nay, deadline sau hôm nay: đúng hạn
        self._milestone(t - timedelta(days=3), reached=True)    # đạt hôm nay, deadline đã qua: trễ
        self._milestone(t - timedelta(days=5))                  # chưa đạt, quá hạn: trễ
        self._milestone(False)                                  # không deadline: không tính
        self._milestone(t - timedelta(days=60), reached=True)   # deadline ngoài kỳ: không tính
        other = self.env["project.project"].create({"name": "DA người khác"})
        self._milestone(t + timedelta(days=1), reached=True, project=other)  # không phải dự án của Lead
        actual, volume = self._compute("P1")
        self.assertEqual(volume, 3)
        self.assertAlmostEqual(actual, 100 / 3)

    def test_is_reached_on_time_flag(self):
        on_time = self._milestone(self.today + timedelta(days=2), reached=True)
        late = self._milestone(self.today - timedelta(days=2), reached=True)
        no_deadline = self._milestone(False, reached=True)
        self.assertEqual(
            (on_time.is_reached_on_time, late.is_reached_on_time, no_deadline.is_reached_on_time), (True, False, False)
        )

    # ---- P2 ----

    def _subordinate(self, login, state):
        user = new_test_user(self.env, login=login)
        employee = self.env["hr.employee"].create({
            "name": login, "user_id": user.id, "parent_id": self.lead.id,
            "job_id": self.env.ref("project_kpi_management.hr_job_developer").id,
        })
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": self.period.id})
        ev.line_ids.write({"actual": 10, "volume": 10})
        if state != "draft":
            ev.write({"state": state, "computed_date": fields.Datetime.now()})
        return ev

    def test_p2_only_closed_evaluations_of_same_period(self):
        done1 = self._subordinate("p2_a", "submitted")
        done2 = self._subordinate("p2_b", "approved")
        self._subordinate("p2_c", "draft")  # chưa chốt: không vào
        self.env.invalidate_all()
        actual, volume = self._compute("P2")
        self.assertEqual(volume, 2)
        self.assertAlmostEqual(actual, (done1.final_score + done2.final_score) / 2)

    def test_p2_not_applicable_when_team_not_closed(self):
        self._subordinate("p2_d", "draft")
        ev = self.env["kpi.evaluation"].create({"employee_id": self.lead.id, "period_id": self.period.id})
        ev.action_compute_kpi()
        line = ev.line_ids.filtered(lambda l: l.metric_id.code == "P2")
        self.assertEqual(line.volume, 0)
        self.assertFalse(line.is_applicable)  # min_volume 2: không ra số sai

    def test_p2_other_period_ignored_and_no_self_loop(self):
        other_period = self.env["kpi.period"].create({
            "name": "Kỳ khác", "date_from": self.date_from - timedelta(days=60), "date_to": self.date_from - timedelta(days=31),
        })
        sub = self._subordinate("p2_e", "draft")
        sub.period_id = other_period
        sub.write({"state": "approved", "computed_date": fields.Datetime.now()})
        own = self.env["kpi.evaluation"].create({"employee_id": self.lead.id, "period_id": self.period.id})
        own.write({"state": "approved", "computed_date": fields.Datetime.now()})
        self.assertEqual(self._compute("P2"), (0.0, 0))  # kỳ khác và phiếu của chính Lead đều không tính

    # ---- P3 ----

    def test_p3_clean_ratio_of_lead_projects(self):
        Task = self.env["project.task"]
        done = Task.create({"name": "F", "project_id": self.project.id, "story_points": 3, "state": "1_done"})
        Task.create({"name": "F2", "project_id": self.project.id, "state": "1_done"})  # thiếu SP
        Task.create({
            "name": "B", "project_id": self.project.id, "task_type": "bug", "origin_task_id": done.id,
            "bug_resolution": "valid", "bug_root_cause": "code",
        })
        Task.create({"name": "B2", "project_id": self.project.id, "task_type": "bug"})  # thiếu task gốc và phân loại
        other_project = self.env["project.project"].create({"name": "X"})
        Task.create({"name": "Khác", "project_id": other_project.id, "state": "1_done"})  # dự án khác: không tính
        # Theo kỳ (Đợt A4): Feature xong trong kỳ 2 (1 thiếu SP) + bug tạo trong kỳ 2 (1 thiếu gốc, 1 chưa phân loại)
        # tổng tiêu chí = 2 + 2*2 = 6; sạch = 1 (SP) + 1 (có gốc) + 1 (đủ phân loại) = 3
        actual, volume = self._compute("P3")
        self.assertEqual(volume, 6)
        self.assertAlmostEqual(actual, 50.0)

    def test_p3_ignores_records_outside_period(self):
        """Đợt A4: bản ghi ngoài kỳ không ảnh hưởng — mở lại, tính lại phiếu kỳ cũ cho cùng kết quả."""
        Task = self.env["project.task"]
        Task.create({"name": "F", "project_id": self.project.id, "story_points": 3, "state": "1_done"})
        before = self._compute("P3")
        old = Task.create({"name": "F cũ", "project_id": self.project.id, "state": "1_done"})  # thiếu SP
        old.date_end = fields.Datetime.now() - timedelta(days=90)
        bug = Task.create({"name": "Bug cũ", "project_id": self.project.id, "task_type": "bug"})
        self.env.flush_all()
        self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id = %s", (fields.Datetime.now() - timedelta(days=90), bug.id))
        self.env.invalidate_all()
        self.assertEqual(self._compute("P3"), before)

    # ---- Phiếu qua nút Tính KPI ----

    def test_template_and_click_compute(self):
        t = self.today
        self._milestone(t + timedelta(days=2), reached=True)
        self._milestone(t - timedelta(days=3))
        job = self.env.ref("project_kpi_management.hr_job_pm")
        self.assertEqual(sorted(job.kpi_template_id.line_ids.mapped("metric_id.code")), ["P1", "P2", "P3", "P5"])
        ev = self.env["kpi.evaluation"].create({"employee_id": self.lead.id, "period_id": self.period.id})
        ev.line_ids.filtered(lambda l: l.metric_id.code == "P5").actual = 4
        ev.action_compute_kpi()
        by = {line.metric_id.code: line for line in ev.line_ids}
        self.assertAlmostEqual(by["P1"].actual, 50.0)
        self.assertTrue(by["P1"].is_applicable)    # 2 milestone >= min_volume 2
        self.assertFalse(by["P2"].is_applicable)   # chưa có cấp dưới chốt phiếu
        self.assertFalse(by["P3"].is_applicable)   # < 10 bản ghi
        # Chỉ P1 (50/80 = 62.5% x 25) và P5 (100% x 30) áp dụng: (62.5 x 25 + 100 x 30) / 55
        self.assertAlmostEqual(ev.kpi_score, (62.5 * 25 + 100 * 30) / 55, places=3)

    def test_p2_skips_evaluation_with_insufficient_data(self):
        """Phiếu cấp dưới đã chốt nhưng thiếu dữ liệu (nhân viên mới) không vào P2, cả giá trị lẫn khối lượng."""
        full = self._subordinate("p2_f", "approved")
        thin = self._subordinate("p2_g", "draft")
        thin.line_ids.write({"volume": 0})  # chỉ còn vài chỉ số min_volume 0 áp dụng → dưới ngưỡng trọng số
        thin.write({"state": "approved", "computed_date": fields.Datetime.now()})
        self.env.invalidate_all()
        self.assertTrue(thin.insufficient_data)
        self.assertFalse(full.insufficient_data)
        actual, volume = self._compute("P2")
        self.assertEqual(volume, 1)
        self.assertAlmostEqual(actual, full.final_score)
