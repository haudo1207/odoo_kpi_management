import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class KpiPeriod(models.Model):
    _name = "kpi.period"
    _description = "Kỳ đánh giá KPI"
    _order = "date_from desc"

    name = fields.Char("Tên kỳ", required=True)
    period_type = fields.Selection(
        [("month", "Tháng"), ("sprint", "Sprint"), ("quarter", "Quý")],
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
        """Nhân viên đủ điều kiện tạo phiếu: có tài khoản người dùng và chức danh đã gắn bộ KPI.
        Đọc bằng sudo vì chức danh, phòng ban nằm ở hr.version."""
        domain = [("user_id", "!=", False)]
        if departments:
            domain.append(("department_id", "child_of", departments.ids))
        employees = self.env["hr.employee"].sudo().search(domain)
        return employees.filtered(lambda e: e.job_id.kpi_template_id.line_ids)

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
