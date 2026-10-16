import logging

from odoo import api, fields, models

from .kpi_template import PERIOD_TYPES

_logger = logging.getLogger(__name__)


class KpiPeriod(models.Model):
    _name = "kpi.period"
    _description = "Kỳ đánh giá KPI"
    _order = "date_from desc"

    name = fields.Char("Tên kỳ", required=True)
    period_type = fields.Selection(
        PERIOD_TYPES,
        string="Loại kỳ",
        required=True,
        default="month",
    )
    date_from = fields.Date("Từ ngày", required=True)
    date_to = fields.Date("Đến ngày", required=True)
    state = fields.Selection(
        [("open", "Đang mở"), ("closed", "Đã đóng")],
        string="Trạng thái",
        required=True,
        default="open",
    )
    evaluation_ids = fields.One2many("kpi.evaluation", "period_id", string="Phiếu đánh giá")
    evaluation_count = fields.Integer("Số phiếu", compute="_compute_evaluation_count")
    auto_generated = fields.Boolean(
        "Đã tạo phiếu tự động", readonly=True, copy=False,
        help="Tác vụ cuối kỳ đã tạo phiếu cho kỳ này. Tác vụ chỉ chạy một lần mỗi kỳ.",
    )

    _date_check = models.Constraint("CHECK(date_from <= date_to)", "Ngày bắt đầu phải trước ngày kết thúc.")

    # ---- Đợt C1: số liệu cho màn hình tổng quan (kanban theo kỳ). Compute không lưu, tính theo QUYỀN người xem. ----
    dashboard_total_count = fields.Integer("Tổng phiếu", compute="_compute_dashboard")
    dashboard_draft_count = fields.Integer("Nháp", compute="_compute_dashboard")
    dashboard_submitted_count = fields.Integer("Đã gửi", compute="_compute_dashboard")
    dashboard_approved_count = fields.Integer("Đã duyệt", compute="_compute_dashboard")
    dashboard_avg_score = fields.Float("Điểm cuối trung bình (phiếu đã duyệt)", compute="_compute_dashboard", digits=(16, 2))
    dashboard_improve_count = fields.Integer("Cần cải thiện", compute="_compute_dashboard")
    dashboard_insufficient_count = fields.Integer("Thiếu dữ liệu", compute="_compute_dashboard")
    dashboard_pending_ack_count = fields.Integer("Chờ nhân viên xác nhận", compute="_compute_dashboard")
    dashboard_data_issues = fields.Integer("Lỗi dữ liệu hiện tại", compute="_compute_dashboard")
    dashboard_show_data_issues = fields.Boolean(compute="_compute_dashboard")

    @api.depends_context("uid")
    def _compute_dashboard(self):
        """Một _read_group cho TẤT CẢ kỳ đang hiển thị (không search_count trong vòng lặp từng kỳ, nếu không mỗi lần mở
        màn hình sẽ là hàng chục truy vấn). Không dùng sudo(): record rule tự áp dụng nên quản lý chỉ thấy số của
        team mình, Admin thấy tất cả. Lỗi dữ liệu đến từ báo cáo theo dự án (ảnh chụp hiện tại, không theo kỳ) nên được
        ghi rõ "hiện tại" và chỉ hiện trên kỳ đang mở."""
        buckets = {period.id: {"state": {}, "improve": 0, "insufficient": 0, "pending_ack": 0, "score_sum": 0.0}
                   for period in self}
        rows = self.env["kpi.evaluation"]._read_group(
            [("period_id", "in", self.ids)],
            ["period_id", "state", "final_rating", "insufficient_data", "ack_decision"],
            ["__count", "final_score:sum"],
        )
        for period, state, rating, insufficient, ack, count, score_sum in rows:
            bucket = buckets[period.id]
            bucket["state"][state] = bucket["state"].get(state, 0) + count
            if state != "draft" and rating == "improve":
                bucket["improve"] += count
            if insufficient:
                bucket["insufficient"] += count
            if state == "approved":
                bucket["score_sum"] += score_sum
                if not ack:
                    bucket["pending_ack"] += count
        issues, show_issues = 0, self.env.user.has_group("project_kpi_management.group_kpi_manager")
        if show_issues:
            (totals,) = self.env["kpi.data.quality.report"]._read_group(
                [], [], ["done_without_sp:sum", "done_without_date_end:sum", "bug_without_origin:sum",
                        "bug_unclassified:sum", "bug_requirement_untraceable:sum"]
            )
            issues = sum(value or 0 for value in totals)
        for period in self:
            bucket = buckets[period.id]
            states = bucket["state"]
            approved = states.get("approved", 0)
            period.dashboard_total_count = sum(states.values())
            period.dashboard_draft_count = states.get("draft", 0)
            period.dashboard_submitted_count = states.get("submitted", 0)
            period.dashboard_approved_count = approved
            period.dashboard_avg_score = bucket["score_sum"] / approved if approved else 0.0
            period.dashboard_improve_count = bucket["improve"]
            period.dashboard_insufficient_count = bucket["insufficient"]
            period.dashboard_pending_ack_count = bucket["pending_ack"]
            period.dashboard_data_issues = issues
            period.dashboard_show_data_issues = show_issues and period.state == "open"

    def _open_evaluations(self, title, domain):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"{title} — {self.name}",
            "res_model": "kpi.evaluation",
            "view_mode": "list,form",
            "domain": [("period_id", "=", self.id)] + domain,
            "context": {"default_period_id": self.id},
        }

    def action_open_all(self):
        return self._open_evaluations("Tất cả phiếu", [])

    def action_open_draft(self):
        return self._open_evaluations("Phiếu Nháp", [("state", "=", "draft")])

    def action_open_submitted(self):
        return self._open_evaluations("Phiếu đã gửi", [("state", "=", "submitted")])

    def action_open_approved(self):
        return self._open_evaluations("Phiếu đã duyệt", [("state", "=", "approved")])

    def action_open_improve(self):
        return self._open_evaluations("Cần cải thiện", [("state", "!=", "draft"), ("final_rating", "=", "improve")])

    def action_open_insufficient(self):
        return self._open_evaluations("Thiếu dữ liệu", [("insufficient_data", "=", True)])

    def action_open_pending_ack(self):
        return self._open_evaluations("Chờ nhân viên xác nhận", [("state", "=", "approved"), ("ack_decision", "=", False)])

    def action_open_data_quality(self):
        return self.env["ir.actions.act_window"]._for_xml_id("project_kpi_management.kpi_data_quality_report_action")

    def _compute_evaluation_count(self):
        counts = dict(self.env["kpi.evaluation"]._read_group(
            [("period_id", "in", self.ids)], ["period_id"], ["__count"]
        ))
        for period in self:
            period.evaluation_count = counts.get(period, 0)

    def action_close(self):
        self.state = "closed"

    def action_open(self):
        self.state = "open"

    def action_view_evaluations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Phiếu đánh giá — {self.name}",
            "res_model": "kpi.evaluation",
            "view_mode": "list,form",
            "domain": [("period_id", "=", self.id)],
            "context": {"default_period_id": self.id},
        }

    def _eligible_employees(self, departments=None):
        """Nhân viên đủ điều kiện tạo phiếu: có tài khoản người dùng, chức danh đã gắn bộ KPI VÀ bộ KPI đó cùng
        loại kỳ với kỳ này (Đợt B1: Developer theo tháng, BA/PM theo quý...). Đọc bằng sudo vì chức danh,
        phòng ban nằm ở hr.version."""
        domain = [("user_id", "!=", False)]
        if departments:
            domain.append(("department_id", "child_of", departments.ids))
        employees = self.env["hr.employee"].sudo().search(domain)
        return employees.filtered(
            lambda e: e.job_id.kpi_template_id.line_ids and e.job_id.kpi_template_id.period_type == self.period_type
        )

    def _generate_evaluations(self, departments=None, compute=True):
        """Tạo phiếu cho mọi nhân viên đủ điều kiện chưa có phiếu trong kỳ, rồi Tính KPI.
        Dùng chung cho wizard (tuần 3) và tác vụ cuối kỳ (tuần 4). Trả về các phiếu mới."""
        self.ensure_one()
        existing = self.env["kpi.evaluation"].sudo().search([("period_id", "=", self.id)]).employee_id
        employees = self._eligible_employees(departments) - existing
        evaluations = self.env["kpi.evaluation"].create([
            {"employee_id": employee.id, "period_id": self.id} for employee in employees
        ])
        if compute and evaluations:
            evaluations.action_compute_kpi()
        return evaluations

    @api.model
    def _cron_generate_evaluations(self):
        """Tác vụ hằng ngày: kỳ đang mở đã qua ngày kết thúc mà chưa tạo phiếu thì tạo và Tính KPI.
        Mỗi kỳ chạy một lần (auto_generated). Lỗi ở một kỳ không chặn các kỳ khác."""
        periods = self.search([
            ("state", "=", "open"),
            ("auto_generated", "=", False),
            ("date_to", "<", fields.Date.context_today(self)),
        ])
        for period in periods:
            try:
                with self.env.cr.savepoint():
                    evaluations = period._generate_evaluations(compute=True)
                    period.auto_generated = True
                _logger.info("KPI: kỳ %s, tạo tự động %s phiếu", period.name, len(evaluations))
            except Exception:
                _logger.exception("KPI: không tạo được phiếu cho kỳ %s", period.name)
