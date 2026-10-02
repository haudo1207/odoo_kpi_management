from odoo import fields, models


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

    _date_check = models.Constraint("CHECK(date_from <= date_to)", "Ngày bắt đầu phải trước ngày kết thúc.")

    def action_close(self):
        self.state = "closed"

    def action_open(self):
        self.state = "open"
