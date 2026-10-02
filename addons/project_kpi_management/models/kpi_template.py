from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KpiTemplate(models.Model):
    _name = "kpi.template"
    _description = "Bộ KPI theo vai trò"
    _order = "name"

    name = fields.Char("Tên bộ KPI", required=True)
    description = fields.Text("Mô tả")
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("kpi.template.line", "template_id", string="Chỉ số", copy=True)
    job_ids = fields.One2many("hr.job", "kpi_template_id", string="Chức danh áp dụng")
    total_weight = fields.Integer("Tổng trọng số", compute="_compute_total_weight")

    @api.depends("line_ids.weight")
    def _compute_total_weight(self):
        for template in self:
            template.total_weight = sum(template.line_ids.mapped("weight"))

    # Đặt trên template chứ không đặt trên dòng: form template tách thao tác
    # trên các dòng thành nhiều lệnh create/write, ràng buộc trên dòng sẽ gặp
    # trạng thái nửa chừng. Template chưa có dòng nào thì cho phép lưu.
    @api.constrains("line_ids")
    def _check_total_weight(self):
        for template in self:
            if template.line_ids and template.total_weight != 100:
                raise ValidationError(
                    "Tổng trọng số của bộ KPI \"%s\" phải bằng 100 (hiện là %s)."
                    % (template.name, template.total_weight)
                )

    @api.constrains("active")
    def _check_archive_with_jobs(self):
        for template in self.filtered(lambda t: not t.active):
            if template.job_ids:
                raise ValidationError(
                    "Không thể ẩn bộ KPI \"%s\" vì đang gắn với chức danh: %s.\n"
                    "Hãy gỡ bộ KPI khỏi các chức danh này trước."
                    % (template.name, ", ".join(template.job_ids.mapped("name")))
                )


class KpiTemplateLine(models.Model):
    _name = "kpi.template.line"
    _description = "Dòng chỉ số trong bộ KPI"
    _order = "sequence, id"

    template_id = fields.Many2one("kpi.template", string="Bộ KPI", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    metric_id = fields.Many2one("kpi.metric", string="Chỉ số", required=True, ondelete="restrict")
    target = fields.Float("Mục tiêu", digits=(16, 2))
    weight = fields.Integer("Trọng số (%)", required=True)
    min_volume = fields.Float(
        "Khối lượng tối thiểu",
        digits=(16, 2),
        help="Dưới mức này, chỉ số được đánh dấu Không áp dụng. 0 = luôn áp dụng.",
    )
    direction = fields.Selection(related="metric_id.direction")
    unit = fields.Char(related="metric_id.unit")
    compute_mode = fields.Selection(related="metric_id.compute_mode")

    _metric_unique = models.Constraint(
        "UNIQUE(template_id, metric_id)", "Mỗi chỉ số chỉ xuất hiện một lần trong một bộ KPI."
    )
    _weight_range = models.Constraint(
        "CHECK(weight >= 0 AND weight <= 100)", "Trọng số phải nằm trong khoảng 0–100."
    )
    _min_volume_positive = models.Constraint(
        "CHECK(min_volume >= 0)", "Khối lượng tối thiểu không được âm."
    )
