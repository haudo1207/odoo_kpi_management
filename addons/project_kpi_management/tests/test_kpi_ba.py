from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiBa(TransactionCase):
    """Bước 5 (Chương 9.2, Ưu tiên 3): bộ KPI BA — B1, B3 cấu hình, B2 hàm Python, B4 nhập tay."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["kpi.engine"]
        cls.now = fields.Datetime.now()
        today = fields.Date.today()
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ BA", "date_from": cls.date_from, "date_to": cls.date_to})
        cls.ba_user = new_test_user(cls.env, login="kpi_ba_user")
        cls.dev_user = new_test_user(cls.env, login="kpi_ba_dev")
        cls.ba = cls.env["hr.employee"].create({
            "name": "BA", "user_id": cls.ba_user.id, "job_id": cls.env.ref("project_kpi_management.hr_job_ba").id,
        })
        cls.dev = cls.env["hr.employee"].create({
            "name": "Dev", "user_id": cls.dev_user.id, "job_id": cls.env.ref("project_kpi_management.hr_job_developer").id,
        })
        cls.project = cls.env["project.project"].create({"name": "DA BA"})
        cls.metrics = {m.code: m for m in cls.env["kpi.metric"].search([])}

    def _days(self, n):
        return self.now + timedelta(days=n)

    def _task(self, user, done=None, **vals):
        task = self.env["project.task"].create({
            "name": "T", "project_id": self.project.id, "user_ids": [(6, 0, user.ids)], **vals,
        })
        if done is not None:
            task.write({"state": "1_done"})
            task.write({"date_end": done})
        return task

    def _requirement(self, done=None, **vals):
        return self._task(self.ba_user, done=done, task_type="requirement", **vals)

    def _compute(self, code, employee=None):
        return self.engine.compute_actual(self.metrics[code], employee or self.ba, self.date_from, self.date_to)

    # ---- Cấu hình, liên kết, cờ ----

    def test_b1_b3_have_no_python_code(self):
        for code in ("B1", "B3"):
            self.assertEqual(self.metrics[code].compute_mode, "domain")
            self.assertFalse(hasattr(self.engine, f"_metric_{code.lower()}"))
        self.assertTrue(hasattr(self.engine, "_metric_b2"))
        self.assertEqual(self.metrics["B4"].compute_mode, "manual")

    def test_requirement_link_validation(self):
        requirement = self._requirement()
        feature = self._task(self.dev_user, requirement_id=requirement.id)
        self.assertEqual(feature.requirement_id, requirement)
        with self.assertRaises(ValidationError):  # trỏ về task không phải Yêu cầu
            self._task(self.dev_user, requirement_id=feature.id)
        other = self.env["project.project"].create({"name": "DA khác"})
        with self.assertRaises(ValidationError):  # khác dự án
            self.env["project.task"].create({"name": "F", "project_id": other.id, "requirement_id": requirement.id})

    def test_is_on_time_flag(self):
        on_time = self._requirement(done=self._days(-5), date_deadline=self._days(-3))
        late = self._requirement(done=self._days(-3), date_deadline=self._days(-8))
        not_done = self._requirement(date_deadline=self._days(-8))
        no_deadline = self._requirement(done=self._days(-3))
        self.assertEqual(
            [t.is_on_time for t in (on_time, late, not_done, no_deadline)], [True, False, False, False]
        )

    # ---- B1, B3 (domain) ----

    def test_open_requirement_not_yet_due_is_not_on_time(self):
        """Yêu cầu đang làm dở, chưa tới hạn: days_late = 0 nhưng cờ is_on_time phải là False (cờ yêu cầu đã xong),
        nên không bao giờ vào tử số của B1; nó chỉ nằm ở mẫu số (chưa đạt) cho tới khi hoàn thành."""
        open_future = self._requirement(date_deadline=self._days(5))
        self.assertEqual(open_future.days_late, 0)
        self.assertFalse(open_future.is_on_time)
        done_on_time = self._requirement(done=self._days(-2), date_deadline=self._days(-1))
        self.assertTrue(done_on_time.is_on_time)
        actual, volume = self._compute("B1")
        self.assertEqual(volume, 2)       # mẫu số: cả yêu cầu đang làm
        self.assertAlmostEqual(actual, 50.0)  # tử số chỉ có yêu cầu đã xong đúng hạn

    def test_b1_on_time_ratio(self):
        self._requirement(done=self._days(-5), date_deadline=self._days(-3))                  # đúng hạn
        self._requirement(done=self._days(-3), date_deadline=self._days(-8))                  # trễ
        self._requirement(date_deadline=self._days(-4))                                       # quá hạn chưa xong: trễ
        self._requirement(date_deadline=self._days(-4), state="1_canceled")                   # huỷ: bỏ
        self._requirement(done=self._days(-60), date_deadline=self._days(-61))                # ngoài kỳ
        self._task(self.ba_user, done=self._days(-5), date_deadline=self._days(-3))           # không phải Yêu cầu
        actual, volume = self._compute("B1")
        self.assertEqual(volume, 3)
        self.assertAlmostEqual(actual, 100 / 3)

    def test_b3_first_review_pass(self):
        self._requirement(done=self._days(-3), review_approve_count=1)                          # qua lần đầu
        self._requirement(done=self._days(-3), review_approve_count=1, review_reject_count=1)   # từng bị trả về
        self._requirement(done=self._days(-3), review_approve_count=2)                          # qua lần đầu
        self._requirement(done=self._days(-3))                                                  # không qua review: ngoài mẫu số
        actual, volume = self._compute("B3")
        self.assertEqual(volume, 3)
        self.assertAlmostEqual(actual, 200 / 3)

    # ---- B2: quy trách nhiệm đúng người ----

    def _requirement_bug(self, feature, **vals):
        return self.env["project.task"].create({
            "name": "Bug", "project_id": self.project.id, "task_type": "bug", "origin_task_id": feature.id,
            "bug_resolution": "valid", "bug_root_cause": "requirement", **vals,
        })

    def test_same_bug_not_for_developer_but_for_ba(self):
        """Một lần phân loại bug, trách nhiệm quy đúng người: bug "yêu cầu sai" bị loại khỏi D3, D4 của Developer
        (chỉ tính nguyên nhân code) nhưng tính vào B2 của BA."""
        requirement = self._requirement(done=self._days(-4))
        feature = self._task(self.dev_user, done=self._days(-3), story_points=5, requirement_id=requirement.id)
        self._requirement_bug(feature)
        dev_d3 = self.engine.compute_actual(self.metrics["D3"], self.dev, self.date_from, self.date_to)
        dev_d4 = self.engine.compute_actual(self.metrics["D4"], self.dev, self.date_from, self.date_to)
        self.assertEqual(dev_d3, (0.0, 5))   # 0 bug / 5 SP
        self.assertEqual(dev_d4, (0.0, 0))   # không có bug tính cho Developer
        self.assertEqual(self._compute("B2"), (1.0, 1))  # 1 bug / 1 yêu cầu hoàn thành

    def test_b2_only_counted_bugs_of_requirement_cause(self):
        r1, r2 = self._requirement(done=self._days(-4)), self._requirement(done=self._days(-3))
        f1 = self._task(self.dev_user, requirement_id=r1.id)
        f2 = self._task(self.dev_user, requirement_id=r2.id)
        self._requirement_bug(f1)
        self._requirement_bug(f1, bug_resolution="wont_fix")
        self._requirement_bug(f2, bug_resolution="duplicate")      # trùng: không tính
        self._requirement_bug(f2, bug_root_cause="code")           # lỗi code: thuộc Developer
        self._requirement(done=self._days(-60))                    # yêu cầu ngoài kỳ: không vào mẫu số
        actual, volume = self._compute("B2")
        self.assertEqual(volume, 2)
        self.assertAlmostEqual(actual, 1.0)  # 2 bug / 2 yêu cầu

    def test_untraceable_requirement_bug_reported_in_data_quality(self):
        requirement = self._requirement(done=self._days(-4))
        traced = self._task(self.dev_user, requirement_id=requirement.id)
        untraced = self._task(self.dev_user)  # Feature không có yêu cầu gốc
        self._requirement_bug(traced)
        self._requirement_bug(untraced)
        self.env["project.task"].create({  # bug yêu cầu sai không có cả task gốc
            "name": "Bug mồ côi", "project_id": self.project.id, "task_type": "bug", "bug_root_cause": "requirement",
        })
        self.env["project.task"].flush_model()
        row = self.env["kpi.data.quality.report"].search([("project_id", "=", self.project.id)])
        self.assertEqual(row.bug_requirement_untraceable, 2)
        self.assertEqual(self._compute("B2"), (1.0, 1))  # chỉ bug truy được mới tính cho BA

    # ---- Phiếu qua nút Tính KPI ----

    def test_click_compute_matches_hand_calculation(self):
        """Tính tay: 3 yêu cầu (2 đúng hạn, 1 trễ; 2 qua review lần đầu, 1 bị trả về); 1 bug yêu cầu sai.
        B1 66,67/90 = 74,07% ·25; B2 0,3/0,3333 = 90% ·30; B3 66,67/70 = 95,24% ·25; B4 = 4 → 100% ·20 → 89,328."""
        r1 = self._requirement(done=self._days(-5), date_deadline=self._days(-3), review_approve_count=1)
        self._requirement(done=self._days(-3), date_deadline=self._days(-8), review_approve_count=1, review_reject_count=1)
        self._requirement(done=self._days(-2), date_deadline=self._days(-1), review_approve_count=1)
        self._requirement_bug(self._task(self.dev_user, requirement_id=r1.id))
        ev = self.env["kpi.evaluation"].create({"employee_id": self.ba.id, "period_id": self.period.id})
        self.assertEqual(ev.template_id, self.env.ref("project_kpi_management.kpi_template_ba"))
        ev.line_ids.filtered(lambda l: l.metric_id.code == "B4").actual = 4
        ev.action_compute_kpi()
        self.assertAlmostEqual(ev.kpi_score, 89.328, places=3)
        self.assertEqual(ev.applicable_weight, 100)
