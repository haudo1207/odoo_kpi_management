from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKpiTargetOverride(TransactionCase):
    """Mục 4: mục tiêu riêng theo nhân viên/phòng ban, ưu tiên nhân viên -> phòng ban -> template."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("project_kpi_management.kpi_template_developer")
        cls.d1_line = cls.template.line_ids.filtered(lambda l: l.metric_id.code == "D1")
        cls.job = cls.env["hr.job"].create({"name": "Dev override test", "kpi_template_id": cls.template.id})
        cls.department = cls.env["hr.department"].create({"name": "R&D override test"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Nhân viên Override", "job_id": cls.job.id, "department_id": cls.department.id,
        })
        cls.period = cls.env["kpi.period"].create({
            "name": "Kỳ override test", "date_from": "2026-10-01", "date_to": "2026-10-31",
        })

    def _evaluation(self):
        return self.env["kpi.evaluation"].create({"employee_id": self.employee.id, "period_id": self.period.id})

    def _d1_target(self, ev):
        return ev.line_ids.filtered(lambda l: l.metric_id.code == "D1").target

    def test_no_override_uses_template_target(self):
        ev = self._evaluation()
        self.assertEqual(self._d1_target(ev), self.d1_line.target)

    def test_department_override(self):
        self.env["kpi.target.override"].create({
            "template_line_id": self.d1_line.id, "department_id": self.department.id, "target": 70,
        })
        ev = self._evaluation()
        self.assertEqual(self._d1_target(ev), 70)

    def test_employee_override_wins_over_department(self):
        self.env["kpi.target.override"].create({
            "template_line_id": self.d1_line.id, "department_id": self.department.id, "target": 70,
        })
        self.env["kpi.target.override"].create({
            "template_line_id": self.d1_line.id, "employee_id": self.employee.id, "target": 60,
        })
        ev = self._evaluation()
        self.assertEqual(self._d1_target(ev), 60)

    def test_override_after_creation_does_not_change_existing_evaluation(self):
        ev = self._evaluation()
        original = self._d1_target(ev)
        self.env["kpi.target.override"].create({
            "template_line_id": self.d1_line.id, "employee_id": self.employee.id, "target": original + 5,
        })
        self.assertEqual(self._d1_target(ev), original)
