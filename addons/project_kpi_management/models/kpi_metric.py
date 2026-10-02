from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KpiMetric(models.Model):
    _name = "kpi.metric"
    _description = "Chỉ số KPI"
    _order = "code"
    _rec_names_search = ["code", "name"]

    code = fields.Char("Mã", required=True)
    name = fields.Char("Tên chỉ số", required=True)
    category = fields.Selection(
        [
            ("delivery", "Tiến độ"),
            ("quality", "Chất lượng"),
            ("process", "Quy trình"),
            ("collaboration", "Cộng tác"),
        ],
        string="Nhóm",
        required=True,
    )
    unit = fields.Char("Đơn vị")
    direction = fields.Selection(
        [("higher", "Cao là tốt"), ("lower", "Thấp là tốt")],
        string="Chiều",
        required=True,
        default="higher",
    )
    compute_mode = fields.Selection(
        [("auto", "Tự động"), ("manual", "Nhập tay")],
        string="Cách tính",
        required=True,
        default="auto",
    )
    description = fields.Text("Mô tả / công thức")
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint("UNIQUE(code)", "Mã chỉ số đã tồn tại.")

    @api.depends("code", "name")
    def _compute_display_name(self):
        for metric in self:
            metric.display_name = f"{metric.code} — {metric.name}"

    @api.constrains("active")
    def _check_archive_in_active_template(self):
        # Chặn ẩn chỉ số khi còn template đang hoạt động dùng nó,
        # vì phiếu tạo mới vẫn sẽ chép chỉ số này vào.
        archived = self.filtered(lambda m: not m.active)
        if not archived:
            return
        lines = self.env["kpi.template.line"].search([
            ("metric_id", "in", archived.ids),
            ("template_id.active", "=", True),
        ])
        if lines:
            raise ValidationError(
                "Không thể ẩn chỉ số đang được dùng trong template: %s.\n"
                "Hãy gỡ chỉ số khỏi các template này trước."
                % ", ".join(lines.template_id.mapped("name"))
            )
