from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiSecurity(TransactionCase):
    """Phase 5: mỗi vai trò chỉ thấy và sửa đúng phần của mình."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dev = new_test_user(cls.env, login="kpi_sec_dev", groups="base.group_user,project.group_project_user")
        cls.outsider = new_test_user(cls.env, login="kpi_sec_out", groups="base.group_user")
        cls.manager = new_test_user(cls.env, login="kpi_sec_mgr",
                                    groups="base.group_user,project_kpi_management.group_kpi_manager")
        cls.admin = new_test_user(cls.env, login="kpi_sec_admin",
                                  groups="base.group_user,project_kpi_management.group_kpi_admin")
        Employee = cls.env["hr.employee"]
        cls.emp_manager = Employee.create({"name": "Quản lý", "user_id": cls.manager.id})
        cls.emp_dev = Employee.create({"name": "Dev", "user_id": cls.dev.id, "parent_id": cls.emp_manager.id})
        cls.emp_out = Employee.create({"name": "Nhóm khác", "user_id": cls.outsider.id})
        cls.template = cls.env.ref("project_kpi_management.kpi_template_developer")
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ quyền", "date_from": "2026-09-01", "date_to": "2026-09-30"})
        Evaluation = cls.env["kpi.evaluation"]
        cls.ev_dev, cls.ev_out, cls.ev_manager = [
            Evaluation.create({"employee_id": emp.id, "period_id": cls.period.id, "template_id": cls.template.id})
            for emp in (cls.emp_dev, cls.emp_out, cls.emp_manager)
        ]

    def _visible(self, user):
        return self.env["kpi.evaluation"].with_user(user).search([("period_id", "=", self.period.id)])

    def test_default_groups(self):
        self.assertTrue(self.dev.has_group("project_kpi_management.group_kpi_user"))
        self.assertFalse(self.dev.has_group("project_kpi_management.group_kpi_manager"))
        self.assertTrue(self.manager.has_group("project.group_project_manager"))
        self.assertTrue(self.admin.has_group("project_kpi_management.group_kpi_manager"))

    def test_visibility(self):
        self.assertEqual(self._visible(self.dev), self.ev_dev)
        self.assertEqual(self._visible(self.manager), self.ev_dev | self.ev_manager)
        self.assertEqual(self._visible(self.admin), self.ev_dev | self.ev_out | self.ev_manager)

    def test_user_read_only(self):
        with self.assertRaises(AccessError):
            self.ev_dev.with_user(self.dev).write({"manager_adjustment": 5, "adjustment_note": "Tự sửa"})

    def test_manager_scope(self):
        self.ev_dev.with_user(self.manager).write({"manager_adjustment": 3, "adjustment_note": "Hỗ trợ đồng nghiệp"})
        self.assertEqual(self.ev_dev.manager_adjustment, 3)
        with self.assertRaises(AccessError):  # không tự sửa phiếu của chính mình
            self.ev_manager.with_user(self.manager).write({"manager_adjustment": 5, "adjustment_note": "x"})
        with self.assertRaises(AccessError):  # không sửa phiếu nhân viên nhóm khác
            self.ev_out.with_user(self.manager).write({"manager_adjustment": 5, "adjustment_note": "x"})
        with self.assertRaises(AccessError):
            self.env["kpi.metric"].with_user(self.manager).create({"code": "X1", "name": "X", "category": "quality"})

    def _submit(self, ev):
        ev.line_ids.write({"volume": 100, "actual": 100})
        ev.computed_date = "2026-10-01 00:00:00"
        ev.action_submit()

    def test_manager_approves_own_team_but_not_others(self):
        """Bản sửa theo YC-09: quản lý trực tiếp (nhóm KPI Manager, không cần thêm quyền Admin) tự
        Duyệt/Trả về/Mở lại được phiếu của CHÍNH nhân viên mình quản lý trực tiếp, nhưng vẫn không
        đụng được phiếu của nhân viên nhóm khác (ev_out) — đó vẫn là việc của KPI Administrator."""
        self._submit(self.ev_dev)
        self.ev_dev.with_user(self.manager).action_approve()
        self.assertEqual(self.ev_dev.state, "approved")
        self.ev_dev.with_user(self.manager).action_reopen()  # mở wizard: tự mở lại được phiếu đội mình
        self.assertEqual(self.ev_dev.state, "approved")  # action_reopen chỉ mở wizard, chưa đổi state

        self._submit(self.ev_out)
        with self.assertRaises(AccessError):
            self.ev_out.with_user(self.manager).action_approve()
        self.ev_out.with_user(self.admin).action_approve()
        self.assertEqual(self.ev_out.state, "approved")

    def test_self_approval_blocked_even_with_admin(self):
        """Xung đột vai trò duy nhất còn lại sau bản sửa: một người không được tự duyệt phiếu của
        chính mình, dù được gán thêm quyền Admin."""
        self._submit(self.ev_manager)
        self.manager.write({"group_ids": [(4, self.env.ref("project_kpi_management.group_kpi_admin").id)]})
        with self.assertRaises(AccessError):
            self.ev_manager.with_user(self.manager).action_approve()
        self.ev_manager.with_user(self.admin).action_approve()
        self.assertEqual(self.ev_manager.state, "approved")

    def test_has_unit_test_manager_only(self):
        project = self.env["project.project"].create({"name": "Quyền task"})
        task = self.env["project.task"].create({"name": "T", "project_id": project.id, "user_ids": [(6, 0, self.dev.ids)]})
        with self.assertRaises(AccessError):
            task.with_user(self.dev).write({"has_unit_test": True})
        task.with_user(self.manager).write({"has_unit_test": True})
        self.assertTrue(task.has_unit_test)
