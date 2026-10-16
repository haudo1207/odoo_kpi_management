from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiTimesheet(TransactionCase):
    """Chạy riêng: --test-tags /project_kpi_timesheet (database phải cài hr_timesheet)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = fields.Date.today()
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ P4", "date_from": cls.date_from, "date_to": cls.date_to})
        cls.user = new_test_user(cls.env, login="kpi_ts_pm")
        cls.employee = cls.env["hr.employee"].create({"name": "PM giờ", "user_id": cls.user.id})
        cls.metric = cls.env.ref("project_kpi_timesheet.kpi_metric_p4")
        cls.engine = cls.env["kpi.engine"]

    def _project(self, allocated, **vals):
        return self.env["project.project"].create({
            "name": "DA giờ", "user_id": self.user.id, "allow_timesheets": True, "allocated_hours": allocated, **vals,
        })

    def _log(self, project, hours, date=None):
        task = self.env["project.task"].create({"name": "T", "project_id": project.id})
        self.env["account.analytic.line"].create({
            "name": "giờ", "project_id": project.id, "task_id": task.id, "unit_amount": hours,
            "employee_id": self.employee.id, "date": date or fields.Date.today(),
        })

    def _p4(self):
        return self.engine.compute_actual(self.metric, self.employee, self.date_from, self.date_to)

    def test_metric_and_template_installed(self):
        self.assertEqual((self.metric.compute_mode, self.metric.direction), ("auto", "lower"))
        template = self.env.ref("project_kpi_timesheet.kpi_template_lead_timesheet")
        self.assertEqual(sorted(template.line_ids.mapped("metric_id.code")), ["P1", "P2", "P3", "P4", "P5"])
        self.assertEqual(template.total_weight, 100)

    def test_deviation_both_directions_penalised(self):
        project = self._project(100)
        self._log(project, 120)
        actual, volume = self._p4()
        self.assertAlmostEqual(actual, 20.0)  # vượt 20%
        self.assertEqual(volume, 1)
        self._log(self._project(100), 60)  # dự án thứ hai chỉ làm 60/100
        # tổng 180 / 200 = 0.9 → lệch 10% (xét gộp theo giờ)
        actual, volume = self._p4()
        self.assertAlmostEqual(actual, 10.0)
        self.assertEqual(volume, 2)

    def test_projects_without_planned_hours_or_other_leads_ignored(self):
        self._log(self._project(0), 50)  # không có giờ kế hoạch
        other = new_test_user(self.env, login="kpi_ts_other")
        project = self._project(100, user_id=other.id)
        self._log(project, 100)
        self.assertEqual(self._p4(), (0.0, 0))  # volume 0 < min_volume 1 → Không áp dụng

    def test_timesheet_after_period_end_ignored(self):
        project = self._project(100)
        self._log(project, 100)
        self._log(project, 40, date=self.date_to + timedelta(days=5))
        self.assertAlmostEqual(self._p4()[0], 0.0)

    def test_click_compute_on_evaluation(self):
        """Đi qua nút Tính KPI với bộ có P4: 130/100 giờ → lệch 30% → thấp tốt, mục tiêu 15 → 15/30 = 50%."""
        self._log(self._project(100), 130)
        template = self.env.ref("project_kpi_timesheet.kpi_template_lead_timesheet")
        ev = self.env["kpi.evaluation"].create({
            "employee_id": self.employee.id, "period_id": self.period.id, "template_id": template.id,
        })
        ev.action_compute_kpi()
        line = ev.line_ids.filtered(lambda l: l.metric_id.code == "P4")
        self.assertAlmostEqual(line.actual, 30.0)
        self.assertTrue(line.is_applicable)
        self.assertAlmostEqual(line.score, 50.0)

    def test_under_planned_hours_also_penalised(self):
        self._log(self._project(100), 70)
        self.assertAlmostEqual(self._p4()[0], 30.0)
