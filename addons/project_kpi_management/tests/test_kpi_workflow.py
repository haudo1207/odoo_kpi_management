from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

COMPLETE = "project_kpi_management.mail_activity_type_complete"
APPROVE = "project_kpi_management.mail_activity_type_approve"
ACK = "project_kpi_management.mail_activity_type_ack"


@tagged("post_install", "-at_install")
class TestKpiWorkflow(TransactionCase):
    """Đợt A (v1.3): nhắc việc theo quy trình (A1), nhân viên xác nhận kết quả (A2), tạm tính giữa kỳ (A3),
    báo cáo theo phòng ban (A5). Mọi bước đi qua đúng hành động người dùng bấm (nút, wizard, cron)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        today = fields.Date.today()
        cls.period = env["kpi.period"].create({
            "name": "Kỳ quy trình", "date_from": today - timedelta(days=20), "date_to": today + timedelta(days=10),
        })
        group = "base.group_user,project_kpi_management."
        cls.manager = new_test_user(env, login="wf_manager", groups=group + "group_kpi_manager")
        cls.approver = new_test_user(env, login="wf_approver", groups=group + "group_kpi_admin")
        cls.user = new_test_user(env, login="wf_employee", groups=group + "group_kpi_user")
        cls.manager_employee = env["hr.employee"].create({"name": "Quản lý", "user_id": cls.manager.id})
        cls.employee = env["hr.employee"].create({
            "name": "Nhân viên", "user_id": cls.user.id, "parent_id": cls.manager_employee.id,
            "job_id": env.ref("project_kpi_management.hr_job_developer").id,
        })
        env["ir.config_parameter"].sudo().set_param("project_kpi_management.default_approver_id", str(cls.approver.id))

    def _evaluation(self, employee=None):
        return self.env["kpi.evaluation"].create({"employee_id": (employee or self.employee).id, "period_id": self.period.id})

    def _acts(self, ev, xmlid):
        return ev._open_activities(xmlid)

    def _ready_to_submit(self, ev):
        ev.action_compute_kpi()
        ev.line_ids.write({"actual": 100, "volume": 100})  # đủ dữ liệu; chỉ số nhập tay được tính là đã chấm
        return ev

    def _reason_wizard(self, ev, mode, user):
        wizard = self.env["kpi.evaluation.reason.wizard"].with_user(user).create(
            {"evaluation_id": ev.id, "mode": mode, "reason": "Lý do kiểm thử"}
        )
        wizard.action_confirm()

    # ---- A1: nhắc việc ----

    def test_create_reminds_manager_to_complete(self):
        ev = self._evaluation()
        acts = self._acts(ev, COMPLETE)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts.user_id, self.manager)

    def test_submit_closes_complete_and_reminds_approver(self):
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        self.assertFalse(self._acts(ev, COMPLETE))   # đã đánh dấu xong
        approve = self._acts(ev, APPROVE)
        self.assertEqual((len(approve), approve.user_id), (1, self.approver))
        ev._sync_workflow_activities()                # idempotent: gọi lại không tạo trùng
        self.assertEqual(len(self._acts(ev, APPROVE)), 1)

    def test_approve_closes_approver_reminder_and_reminds_employee(self):
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        ev.action_approve()
        self.assertFalse(self._acts(ev, APPROVE))
        ack = self._acts(ev, ACK)
        self.assertEqual((len(ack), ack.user_id), (1, self.user))

    def test_return_to_draft_cancels_approve_and_reminds_again(self):
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        self._reason_wizard(ev, "return", self.approver)
        self.assertEqual(ev.state, "draft")
        self.assertFalse(self._acts(ev, APPROVE))
        self.assertEqual(len(self._acts(ev, COMPLETE)), 1)

    def test_no_default_approver_means_no_approve_reminder(self):
        self.env["ir.config_parameter"].sudo().set_param("project_kpi_management.default_approver_id", "")
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        self.assertFalse(self._acts(ev, APPROVE))
        self.assertIn("Chưa đặt người duyệt", ev.message_ids[0].body)

    def test_approver_in_role_conflict_is_skipped(self):
        """Người duyệt mặc định lại là quản lý trực tiếp của phiếu: không được duyệt nên không giao nhắc việc."""
        self.manager.group_ids = [(4, self.env.ref("project_kpi_management.group_kpi_admin").id)]
        self.env["ir.config_parameter"].sudo().set_param("project_kpi_management.default_approver_id", str(self.manager.id))
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        self.assertFalse(self._acts(ev, APPROVE))

    def test_manager_without_kpi_group_falls_back_to_approver(self):
        plain = new_test_user(self.env, login="wf_plain", groups="base.group_user")
        boss = self.env["hr.employee"].create({"name": "Sếp không nhóm KPI", "user_id": plain.id})
        employee = self.env["hr.employee"].create({
            "name": "NV khác", "user_id": new_test_user(self.env, login="wf_emp2", groups="base.group_user,project_kpi_management.group_kpi_user").id,
            "parent_id": boss.id, "job_id": self.env.ref("project_kpi_management.hr_job_developer").id,
        })
        acts = self._acts(self._evaluation(employee), COMPLETE)
        self.assertEqual(acts.user_id, self.approver)  # Odoo không giao nhắc việc cho người không đọc được phiếu

    def test_settings_approver_must_be_admin(self):
        settings = self.env["res.config.settings"].create({"kpi_default_approver_id": self.manager.id})
        with self.assertRaises(ValidationError):
            settings.execute()

    # ---- A2: nhân viên xác nhận ----

    def _approved(self):
        ev = self._ready_to_submit(self._evaluation())
        ev.action_submit()
        ev.action_approve()
        return ev

    def _ack(self, ev, user, decision, comment=False):
        wizard = self.env["kpi.acknowledge.wizard"].with_user(user).create(
            {"evaluation_id": ev.id, "decision": decision, "comment": comment}
        )
        return wizard.action_confirm()

    def test_employee_acknowledges_after_approval(self):
        ev = self._approved()
        self._ack(ev, self.user, "agree")
        self.assertEqual((ev.ack_decision, bool(ev.ack_date), ev.state), ("agree", True, "approved"))
        self.assertFalse(self._acts(ev, ACK))  # nhắc việc đã hoàn tất

    def test_disagree_requires_comment(self):
        ev = self._approved()
        with self.assertRaises(UserError):
            self._ack(ev, self.user, "disagree")
        self._ack(ev, self.user, "disagree", "Tôi không đồng ý điểm D4")
        self.assertEqual((ev.ack_decision, ev.ack_comment), ("disagree", "Tôi không đồng ý điểm D4"))

    def test_only_own_employee_and_only_after_approval(self):
        ev = self._ready_to_submit(self._evaluation())
        with self.assertRaises(UserError):  # chưa duyệt
            self._ack(ev, self.user, "agree")
        ev.action_submit()
        ev.action_approve()
        with self.assertRaises(AccessError):  # người khác
            self._ack(ev, self.manager, "agree")

    def test_acknowledgement_not_writable_directly(self):
        ev = self._approved()
        with self.assertRaises(UserError):
            ev.with_user(self.manager).write({"ack_decision": "agree"})
        with self.assertRaises(UserError):
            self.env["kpi.evaluation"].with_user(self.manager).create({
                "employee_id": self.manager_employee.id, "period_id": self.period.id,
                "template_id": ev.template_id.id, "ack_decision": "agree",
            })

    def test_reopen_clears_acknowledgement(self):
        ev = self._approved()
        self._ack(ev, self.user, "agree")
        self._reason_wizard(ev, "reopen", self.approver)
        self.assertEqual((ev.state, ev.ack_decision, ev.ack_date), ("draft", False, False))
        self.assertEqual(len(self._acts(ev, COMPLETE)), 1)

    # ---- A3: tạm tính giữa kỳ ----

    def test_cron_provisional_compute_touches_only_engine_lines(self):
        project = self.env["project.project"].create({"name": "DA tạm tính"})
        task = self.env["project.task"].create({
            "name": "T", "project_id": project.id, "user_ids": [(6, 0, self.user.ids)], "story_points": 8,
        })
        task.write({"state": "1_done"})
        task.write({"date_end": fields.Datetime.now() - timedelta(days=2)})
        ev = self._evaluation()
        d2 = ev.line_ids.filtered(lambda l: l.metric_id.code == "D2")
        d9 = ev.line_ids.filtered(lambda l: l.metric_id.code == "D9")
        d9.write({"actual": 3})                 # quản lý đã chấm tay
        d2.target = 99                           # mục tiêu đã sửa
        self.assertFalse(ev.computed_date)
        other = self.env["hr.employee"].create({
            "name": "NV đã gửi", "user_id": new_test_user(self.env, login="wf_sent", groups="base.group_user").id,
            "job_id": self.env.ref("project_kpi_management.hr_job_developer").id,
        })
        submitted = self._ready_to_submit(self._evaluation(other))
        submitted.action_submit()
        stamp = submitted.last_computed_date

        self.env["kpi.evaluation"]._cron_provisional_compute()

        self.assertEqual(d2.actual, 8)           # dòng do engine tính được cập nhật
        self.assertEqual((d9.actual, d2.target), (3, 99))  # nhập tay và mục tiêu giữ nguyên
        self.assertTrue(ev.last_computed_date)
        self.assertFalse(ev.computed_date)       # tạm tính không thay bước Tính KPI chủ động của quản lý
        self.assertEqual(submitted.last_computed_date, stamp)  # phiếu đã gửi không bị đụng

    def test_manual_compute_sets_both_dates(self):
        ev = self._evaluation()
        ev.action_compute_kpi()
        self.assertTrue(ev.computed_date and ev.last_computed_date)

    # ---- A5: báo cáo theo phòng ban ----

    def test_department_reports(self):
        action = self.env.ref("project_kpi_management.kpi_evaluation_department_action")
        self.assertEqual({v.view_mode for v in action.view_ids}, {"graph", "pivot"})
        self.env.ref("project_kpi_management.kpi_evaluation_line_department_action")
        groups = self.env["kpi.evaluation"].read_group([], ["final_score:avg"], ["department_id"])
        self.assertIsInstance(groups, list)

    # ---- Quản lý chưa có quyền KPI (báo cáo cấu hình) ----

    def test_manager_without_kpi_permission_is_listed(self):
        job = self.env.ref("project_kpi_management.hr_job_developer")
        plain_manager = self.env["hr.employee"].create({
            "name": "Sếp thường", "user_id": new_test_user(self.env, login="wf_plain_boss", groups="base.group_user").id,
        })
        no_account_manager = self.env["hr.employee"].create({"name": "Sếp chưa có tài khoản"})
        flagged = [
            self.env["hr.employee"].create({
                "name": name, "user_id": new_test_user(self.env, login=login, groups="base.group_user").id,
                "job_id": job.id, "parent_id": boss.id,
            })
            for name, login, boss in (("NV dưới sếp thường", "wf_i1", plain_manager), ("NV dưới sếp không tài khoản", "wf_i2", no_account_manager))
        ]
        # self.employee có quản lý thuộc nhóm KPI Manager: không bị liệt kê
        action = self.env["kpi.manager.issue"].action_open()
        names = self.env["kpi.manager.issue"].browse(self.env["kpi.manager.issue"].search(action["domain"]).ids).mapped("employee_name")
        self.assertEqual(sorted(n for n in names if n in {e.name for e in flagged} | {self.employee.name}), sorted(e.name for e in flagged))
