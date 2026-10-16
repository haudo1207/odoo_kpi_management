from odoo import fields, models
from odoo.exceptions import ValidationError

from .kpi_evaluation import PARAM_DEFAULTS

PREFIX = "project_kpi_management."


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Lưu ở ir.config_parameter, đúng khóa mà get_kpi_param() đọc
    kpi_score_cap = fields.Float("Điểm trần mỗi chỉ số", config_parameter=PREFIX + "score_cap",
                                 default=PARAM_DEFAULTS["score_cap"])
    kpi_adjustment_max = fields.Float("Biên độ điều chỉnh (±)", config_parameter=PREFIX + "adjustment_max",
                                      default=PARAM_DEFAULTS["adjustment_max"])
    kpi_min_applicable_weight = fields.Float("Trọng số áp dụng tối thiểu (%)",
                                             config_parameter=PREFIX + "min_applicable_weight",
                                             default=PARAM_DEFAULTS["min_applicable_weight"])
    kpi_rating_excellent = fields.Float("Ngưỡng Xuất sắc", config_parameter=PREFIX + "rating_excellent",
                                        default=PARAM_DEFAULTS["rating_excellent"])
    kpi_rating_good = fields.Float("Ngưỡng Tốt", config_parameter=PREFIX + "rating_good",
                                   default=PARAM_DEFAULTS["rating_good"])
    kpi_rating_pass = fields.Float("Ngưỡng Đạt", config_parameter=PREFIX + "rating_pass",
                                   default=PARAM_DEFAULTS["rating_pass"])

    kpi_default_approver_id = fields.Many2one(
        "res.users", string="Người duyệt mặc định", config_parameter=PREFIX + "default_approver_id",
        help="Nhắc việc Duyệt phiếu KPI được giao cho người này (nhắc việc chỉ giao được cho một người, "
             "nên không giao cho cả nhóm Admin). Để trống: không tạo nhắc việc duyệt.",
    )

    def set_values(self):
        if self.kpi_default_approver_id and not self.kpi_default_approver_id.has_group("project_kpi_management.group_kpi_admin"):
            raise ValidationError("Người duyệt mặc định phải thuộc nhóm KPI Administrator.")
        if not (self.kpi_rating_excellent > self.kpi_rating_good > self.kpi_rating_pass > 0):
            raise ValidationError("Ngưỡng xếp loại phải giảm dần: Xuất sắc > Tốt > Đạt > 0.")
        if self.kpi_score_cap < 100:
            raise ValidationError("Điểm trần phải từ 100 trở lên.")
        if not 0 < self.kpi_min_applicable_weight <= 100:
            raise ValidationError("Trọng số áp dụng tối thiểu phải trong khoảng (0, 100].")
        if self.kpi_adjustment_max < 0:
            raise ValidationError("Biên độ điều chỉnh không được âm.")
        return super().set_values()
