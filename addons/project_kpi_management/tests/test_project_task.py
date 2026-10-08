from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectTask(TransactionCase):
    """Phase 2: field KPI trên task, date_end, số lần bị trả về, số ngày trễ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stage_open = cls.env["project.task.type"].create({"name": "Doing", "fold": False})
        cls.stage_done = cls.env["project.task.type"].create({"name": "Done (no fold)", "fold": False})
        cls.project = cls.env["project.project"].create({
            "name": "KPI test",
            "type_ids": [(6, 0, [cls.stage_open.id, cls.stage_done.id])],
        })

    def _task(self, **vals):
        return self.env["project.task"].create({"name": "T", "project_id": self.project.id, **vals})

    def test_date_end_set_when_done_on_non_fold_stage(self):
        # Stage Done không fold: Odoo không ghi date_end, module phải tự ghi theo state
        task = self._task()
        task.write({"stage_id": self.stage_done.id, "state": "1_done"})
        self.assertTrue(task.date_end)

    def test_date_end_survives_stage_change(self):
        task = self._task()
        task.write({"state": "1_done"})
        self.assertTrue(task.date_end)
        # Đổi stage không fold: Odoo xoá date_end, task vẫn Done nên phải ghi lại
        task.write({"stage_id": self.stage_done.id})
        self.assertEqual(task.state, "1_done")
        self.assertTrue(task.date_end)

    def test_create_done_task(self):
        self.assertTrue(self._task(state="1_done").date_end)

    def test_review_reject_count(self):
        task = self._task()
        task.write({"state": "02_changes_requested"})
        task.write({"state": "02_changes_requested"})  # ghi lại cùng trạng thái: không đếm
        task.write({"state": "01_in_progress"})
        task.write({"state": "02_changes_requested"})
        self.assertEqual(task.review_reject_count, 2)
        task.write({"state": "03_approved"})
        task.write({"state": "03_approved"})  # ghi lại cùng trạng thái: không đếm
        self.assertEqual(task.review_approve_count, 1)

    def test_days_late(self):
        now = fields.Datetime.now()
        on_time = self._task(date_deadline=now + timedelta(days=2), state="1_done")
        self.assertEqual(on_time.days_late, 0)
        late_done = self._task(date_deadline=now - timedelta(days=5))
        late_done.write({"state": "1_done", "date_end": now - timedelta(days=2)})
        self.assertEqual(late_done.days_late, 3)
        overdue_open = self._task(date_deadline=now - timedelta(days=4))
        self.assertEqual(overdue_open.days_late, 4)
        canceled = self._task(date_deadline=now - timedelta(days=4), state="1_canceled")
        self.assertEqual(canceled.days_late, 0)

    def test_bug_link_to_origin(self):
        feature = self._task(task_type="feature", story_points=5)
        bug = self._task(task_type="bug", origin_task_id=feature.id,
                         bug_resolution="valid", bug_root_cause="code", is_production_bug=True)
        self.assertEqual(feature.bug_ids, bug)
        with self.assertRaises(ValidationError):
            feature.origin_task_id = feature
