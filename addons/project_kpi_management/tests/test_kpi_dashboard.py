from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiDashboard(TransactionCase):
    """Đợt C1 (v1.5): màn hình tổng quan — kanban theo kỳ, số liệu tính theo quyền người xem, mỗi con số là một nút."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        today = fields.Date.today()
        group = "base.group_user,project_kpi_management."
        cls.admin = new_test_user(env, login="db_admin", groups=group + "group_kpi_admin")
        cls.manager1 = new_test_user(env, login="db_mgr1", groups=group + "group_kpi_manager")
        cls.manager2 = new_test_user(env, login="db_mgr2", groups=group + "group_kpi_manager")
        mgr1, mgr2 = (env["hr.employee"].create({"name": n, "user_id": u.id}) for n, u in (("Q1", cls.manager1), ("Q2", cls.manager2)))
        cls.period = env["kpi.period"].create({"name": "Kỳ tổng quan", "date_from": today - timedelta(days=20), "date_to": today + timedelta(days=10)})
        d9 = env.ref("project_kpi_management.kpi_metric_d9")
        d4 = env.ref("project_kpi_management.kpi_metric_d4")
        full = env["kpi.template"].create({"name": "Một chỉ số (test)", "line_ids": [(0, 0, {"metric_id": d9.id, "target": 4, "weight": 100})]})
        thin = env["kpi.template"].create({"name": "Thiếu dữ liệu (test)", "line_ids": [
            (0, 0, {"metric_id": d9.id, "target": 4, "weight": 10}),
            (0, 0, {"metric_id": d4.id, "target": 5, "weight": 90, "min_volume": 1}),
        ]})
        job = env.ref("project_kpi_management.hr_job_developer")

        def evaluation(name, boss, template, actual, state="draft", **extra):
            employee = env["hr.employee"].create({
                "name": name, "user_id": new_test_user(env, login=f"db_{name}", groups="base.group_user").id,
                "parent_id": boss.id, "job_id": job.id,
            })
            ev = env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": cls.period.id, "template_id": template.id})
            ev.line_ids.filtered(lambda l: l.metric_id == d9).actual = actual   # D9 = actual / 4 · 100
            if state != "draft":
                ev.write({"state": state, **extra})
            return ev

        # Team của Q1: Nháp; Đã gửi 75; Đã duyệt 100 (đã xác nhận); Đã duyệt 50 (Cần cải thiện, chờ xác nhận);
        # Đã duyệt, thiếu dữ liệu (D4 không áp dụng) 100, chờ xác nhận. Team của Q2: Đã duyệt 75 (chờ xác nhận).
        cls.e_draft = evaluation("draft", mgr1, full, 4)
        cls.e_sent = evaluation("sent", mgr1, full, 3, "submitted")
        cls.e_ok = evaluation("ok", mgr1, full, 4, "approved", ack_decision="agree")
        cls.e_improve = evaluation("improve", mgr1, full, 2, "approved")
        cls.e_thin = evaluation("thin", mgr1, thin, 4, "approved")
        cls.e_other_team = evaluation("other", mgr2, full, 3, "approved")

    def _read(self, user):
        period = self.period.with_user(user)
        return {name: period[name] for name in (
            "dashboard_total_count", "dashboard_draft_count", "dashboard_submitted_count", "dashboard_approved_count",
            "dashboard_avg_score", "dashboard_improve_count", "dashboard_insufficient_count", "dashboard_pending_ack_count",
        )}

    def test_numbers_match_hand_count_for_admin(self):
        """Admin thấy cả hai team: 6 phiếu = 1 nháp + 1 đã gửi + 4 đã duyệt; điểm TB đã duyệt (100 + 50 + 100 + 75)/4 = 81,25;
        Cần cải thiện 1 (phiếu 50); thiếu dữ liệu 1; chờ xác nhận 3 (phiếu 50, phiếu thiếu dữ liệu, phiếu team Q2)."""
        data = self._read(self.admin)
        self.assertEqual(
            (data["dashboard_total_count"], data["dashboard_draft_count"], data["dashboard_submitted_count"],
             data["dashboard_approved_count"], data["dashboard_improve_count"], data["dashboard_insufficient_count"],
             data["dashboard_pending_ack_count"]),
            (6, 1, 1, 4, 1, 1, 3),
        )
        self.assertAlmostEqual(data["dashboard_avg_score"], 81.25)

    def test_manager_sees_only_own_team(self):
        """Cùng một kỳ, quản lý Q1 chỉ thấy team mình: 5 phiếu, đã duyệt 3, điểm TB (100 + 50 + 100)/3, chờ xác nhận 2;
        quản lý Q2 chỉ thấy 1 phiếu của team Q2 — số liệu không dùng sudo nên record rule tự áp dụng."""
        mine = self._read(self.manager1)
        self.assertEqual((mine["dashboard_total_count"], mine["dashboard_approved_count"], mine["dashboard_pending_ack_count"]), (5, 3, 2))
        self.assertAlmostEqual(mine["dashboard_avg_score"], 250 / 3, places=2)  # trường hiển thị 2 chữ số lẻ
        other = self._read(self.manager2)
        self.assertEqual((other["dashboard_total_count"], other["dashboard_approved_count"], other["dashboard_improve_count"]), (1, 1, 0))
        self.assertNotEqual(self._read(self.admin)["dashboard_total_count"], mine["dashboard_total_count"])

    def test_each_button_opens_exactly_its_evaluations(self):
        expected = {
            "action_open_all": self.e_draft | self.e_sent | self.e_ok | self.e_improve | self.e_thin | self.e_other_team,
            "action_open_draft": self.e_draft,
            "action_open_submitted": self.e_sent,
            "action_open_approved": self.e_ok | self.e_improve | self.e_thin | self.e_other_team,
            "action_open_improve": self.e_improve,
            "action_open_insufficient": self.e_thin,
            "action_open_pending_ack": self.e_improve | self.e_thin | self.e_other_team,
        }
        for method, evaluations in expected.items():
            with self.subTest(button=method):
                action = getattr(self.period.with_user(self.admin), method)()
                found = self.env["kpi.evaluation"].with_user(self.admin).search(action["domain"])
                self.assertEqual(found, evaluations)

    def test_button_respects_viewer_permissions(self):
        action = self.period.with_user(self.manager1).action_open_pending_ack()
        found = self.env["kpi.evaluation"].with_user(self.manager1).search(action["domain"])
        self.assertEqual(found, self.e_improve | self.e_thin)  # không có phiếu team Q2

    def test_number_of_queries_does_not_grow_with_periods(self):
        """Một _read_group cho mọi kỳ: đọc 1 kỳ và đọc 8 kỳ tốn số truy vấn như nhau (không search_count từng kỳ)."""
        today = fields.Date.today()
        many = self.env["kpi.period"].create([
            {"name": f"Kỳ phụ {i}", "date_from": today - timedelta(days=400 + i), "date_to": today - timedelta(days=380 + i)}
            for i in range(7)
        ]) | self.period

        def cost(periods):
            periods = periods.with_user(self.admin)
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_log_count
            periods.read(["dashboard_total_count", "dashboard_approved_count", "dashboard_avg_score", "dashboard_improve_count",
                          "dashboard_data_issues"])
            return self.env.cr.sql_log_count - before

        cost(self.period)  # lần đầu nạp cache quyền/nhóm, không tính
        self.assertEqual(cost(self.period), cost(many))

    def test_data_issues_are_current_and_only_for_managers_on_open_periods(self):
        before = self.period.with_user(self.admin).dashboard_data_issues
        project = self.env["project.project"].create({"name": "DA lỗi dữ liệu"})
        self.env["project.task"].create({"name": "F", "project_id": project.id, "state": "1_done"})  # Feature xong thiếu SP
        self.env["project.task"].create({"name": "B", "project_id": project.id, "task_type": "bug"})  # thiếu gốc + chưa phân loại
        self.env.invalidate_all()
        self.assertEqual(self.period.with_user(self.admin).dashboard_data_issues - before, 3)
        self.assertTrue(self.period.with_user(self.admin).dashboard_show_data_issues)
        plain = new_test_user(self.env, login="db_plain", groups="base.group_user")
        self.assertFalse(self.period.with_user(plain).dashboard_show_data_issues)
        self.period.action_close()
        self.assertFalse(self.period.with_user(self.admin).dashboard_show_data_issues)  # không gắn lỗi hiện tại vào kỳ đã đóng

    def test_dashboard_is_the_first_menu_and_view_is_valid(self):
        action = self.env.ref("project_kpi_management.kpi_period_dashboard_action")
        self.assertEqual(action.view_mode.split(",")[0], "kanban")
        self.assertIn("search_default_open", action.context)  # mặc định lọc kỳ đang mở
        views = self.env["kpi.period"].get_views([(False, "kanban"), (False, "search")])
        self.assertIn("kanban", views["views"])
        root = self.env.ref("project_kpi_management.menu_kpi_root")
        first = min(root.child_id, key=lambda m: (m.sequence, m.id))
        self.assertEqual(first, self.env.ref("project_kpi_management.menu_kpi_dashboard"))  # vào app mở thẳng màn hình này
