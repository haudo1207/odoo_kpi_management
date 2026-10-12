from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiEngine(TransactionCase):
    """Phase 4: quy tắc nghiệp vụ của từng chỉ số tự động."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["kpi.engine"]
        cls.now = fields.Datetime.now()
        today = fields.Date.today()
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.user = new_test_user(cls.env, login="kpi_engine_dev")
        cls.other = new_test_user(cls.env, login="kpi_engine_dev2")
        cls.employee = cls.env["hr.employee"].create({"name": "Dev engine", "user_id": cls.user.id})
        cls.other_employee = cls.env["hr.employee"].create({"name": "Dev engine 2", "user_id": cls.other.id})
        cls.project = cls.env["project.project"].create({"name": "Engine test"})  # không có stage
        cls.metrics = {m.code: m for m in cls.env["kpi.metric"].search([])}

    def _task(self, users=None, done=None, **vals):
        task = self.env["project.task"].create({
            "name": "T", "project_id": self.project.id,
            "user_ids": [(6, 0, (users or self.user).ids)], **vals,
        })
        if done is not None:
            task.write({"state": "1_done"})
            task.write({"date_end": done})
        return task

    def _compute(self, code, employee=None):
        return self.engine.compute_actual(self.metrics[code], employee or self.employee, self.date_from, self.date_to)

    def _days(self, n):
        return self.now + timedelta(days=n)

    def test_d1_on_time(self):
        self._task(date_deadline=self._days(-5), done=self._days(-6))          # đúng hạn
        self._task(date_deadline=self._days(-10), done=self._days(-8))         # trễ
        self._task(date_deadline=self._days(-3))                               # quá hạn, chưa xong: trễ
        self._task(date_deadline=self._days(3))                                # chưa tới hạn: chưa xét
        self._task(date_deadline=self._days(-4), state="1_canceled")           # huỷ: bỏ qua
        self._task(date_deadline=self._days(-40), done=self._days(-41))        # deadline ngoài kỳ
        actual, volume = self._compute("D1")
        self.assertEqual(volume, 3)
        self.assertAlmostEqual(actual, 100 / 3)

    def test_d2_story_points(self):
        self._task(story_points=5, done=self._days(-2))
        self._task(story_points=3, done=self._days(-60))  # xong ngoài kỳ
        self._task(story_points=8)                         # chưa xong
        self.assertEqual(self._compute("D2"), (5, 5))

    def test_d3_d4_counted_bugs(self):
        both = self.user | self.other
        feature = self._task(users=both, story_points=10, done=self._days(-5))
        old = self._task(story_points=5, done=self._days(-60))
        code = {"task_type": "bug", "bug_root_cause": "code"}
        self._task(origin_task_id=feature.id, bug_resolution="valid", is_production_bug=True, **code)
        self._task(origin_task_id=feature.id, bug_resolution="wont_fix", **code)
        self._task(origin_task_id=feature.id, bug_resolution="duplicate", **code)          # không tính
        self._task(origin_task_id=feature.id, bug_resolution="invalid", **code)            # không tính
        self._task(origin_task_id=feature.id, bug_resolution="valid", task_type="bug", bug_root_cause="requirement")
        self._task(origin_task_id=old.id, bug_resolution="valid", **code)                  # task gốc ngoài kỳ
        self.assertEqual(self._compute("D3"), (0.2, 10))   # 2 bug / 10 SP
        self.assertEqual(self._compute("D4"), (50.0, 2))   # 1 production / 2 bug
        # Task gốc có 2 người được giao: bug tính cho cả hai
        self.assertEqual(self._compute("D4", self.other_employee), (50.0, 2))

    def test_domain_metric_equivalent_to_d4(self):
        """Bước 1 (Chương 9.1): chỉ số cấu hình thuần domain phải ra đúng kết quả như hàm Python
        _metric_d4() trên cùng dữ liệu — bằng chứng mạnh nhất rằng cơ chế cấu hình không cần
        code là đúng, không chỉ đúng về lý thuyết."""
        both = self.user | self.other
        feature = self._task(users=both, story_points=10, done=self._days(-5))
        code = {"task_type": "bug", "bug_root_cause": "code"}
        self._task(origin_task_id=feature.id, bug_resolution="valid", is_production_bug=True, **code)
        self._task(origin_task_id=feature.id, bug_resolution="wont_fix", **code)

        denominator_domain = (
            "[('task_type', '=', 'bug'), ('bug_resolution', 'in', ['valid', 'wont_fix']),"
            " ('bug_root_cause', '=', 'code'), ('origin_task_id.user_ids', 'in', [user.id]),"
            " ('origin_task_id.state', '=', '1_done'),"
            " ('origin_task_id.date_end', '>=', start), ('origin_task_id.date_end', '<', end)]"
        )
        numerator_domain = denominator_domain.rstrip("]") + ", ('is_production_bug', '=', True)]"
        model_id = self.env["ir.model"].search([("model", "=", "project.task")], limit=1).id
        metric = self.env["kpi.metric"].create({
            "code": "DOMAIN_D4", "name": "D4 cấu hình (thử nghiệm)", "category": "quality",
            "compute_mode": "domain", "source_model_id": model_id, "aggregation": "ratio",
            "numerator_domain": numerator_domain, "denominator_domain": denominator_domain,
        })
        self.assertEqual(
            self.engine.compute_actual(metric, self.employee, self.date_from, self.date_to),
            self._compute("D4"),
        )

    def test_d5_d6_review_and_unit_test(self):
        self._task(done=self._days(-3), review_approve_count=1, has_unit_test=True)
        self._task(done=self._days(-3), review_approve_count=1, review_reject_count=1)
        self._task(done=self._days(-3))                        # không qua review: ngoài mẫu số D5
        self._task(done=self._days(-3), task_type="bug", review_approve_count=1)  # bug: ngoài mẫu số D6
        actual5, volume5 = self._compute("D5")
        self.assertEqual(volume5, 3)
        self.assertAlmostEqual(actual5, 200 / 3)               # 2 chưa từng bị trả về / 3 đã review
        actual6, volume6 = self._compute("D6")
        self.assertEqual(volume6, 3)
        self.assertAlmostEqual(actual6, 100 / 3)

    def test_d7_high_priority_bugs(self):
        high = self._task(task_type="bug", priority="2", done=self._days(-2))
        urgent = self._task(task_type="bug", priority="3", done=self._days(-1))
        self._task(task_type="bug", priority="0", done=self._days(-1))      # ưu tiên thấp: không tính
        self._task(task_type="feature", priority="3", done=self._days(-1))  # không phải bug
        actual, volume = self._compute("D7")
        self.assertEqual(volume, 2)
        self.assertAlmostEqual(actual, (high.working_hours_close + urgent.working_hours_close) / 2)

    def test_d8_knowledge_sharing_events(self):
        sharing = self.env.ref("project_kpi_management.calendar_event_type_knowledge_sharing")
        Event = self.env["calendar.event"]
        base = {"start": self._days(-2), "stop": self._days(-2) + timedelta(hours=1)}
        Event.create({"name": "Chia sẻ", "user_id": self.user.id, "categ_ids": [(6, 0, sharing.ids)], **base})
        Event.create({"name": "Họp thường", "user_id": self.user.id, **base})
        Event.create({"name": "Người khác", "user_id": self.other.id, "categ_ids": [(6, 0, sharing.ids)], **base})
        self.assertEqual(self._compute("D8"), (1, 1))

    def test_manual_metric_skipped(self):
        self.assertIsNone(self._compute("D9"))

    def test_employee_without_user(self):
        employee = self.env["hr.employee"].create({"name": "Không có tài khoản"})
        with self.assertRaises(UserError):
            self._compute("D1", employee)

    def test_compute_on_evaluation(self):
        template = self.env.ref("project_kpi_management.kpi_template_developer")
        period = self.env["kpi.period"].create({"name": "Kỳ engine", "date_from": self.date_from, "date_to": self.date_to})
        self._task(story_points=5, done=self._days(-2))
        ev = self.env["kpi.evaluation"].create({
            "employee_id": self.employee.id, "period_id": period.id, "template_id": template.id,
        })
        d9 = ev.line_ids.filtered(lambda l: l.metric_id.code == "D9")
        d9.actual = 4
        ev.action_compute_kpi()
        self.assertTrue(ev.computed_date)
        d2 = ev.line_ids.filtered(lambda l: l.metric_id.code == "D2")
        self.assertEqual((d2.actual, d2.volume), (5, 5))
        self.assertEqual(d9.actual, 4)  # chỉ số nhập tay không bị engine ghi đè
