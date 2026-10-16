import math

from odoo import api, fields, models
from odoo.exceptions import UserError

SUGGESTION_MIN_PERIODS = 3
SUGGESTION_MAX_PERIODS = 6


def percentile(sorted_values, q):
    """Phân vị q (0..1) nội suy tuyến tính giữa hai giá trị kề nhau."""
    position = q * (len(sorted_values) - 1)
    low = math.floor(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


class KpiTargetOverride(models.Model):
    _name = "kpi.target.override"
    _description = "Mục tiêu riêng theo nhân viên hoặc phòng ban cho một chỉ số trong bộ KPI"

    template_line_id = fields.Many2one(
        "kpi.template.line", string="Dòng chỉ số", required=True, ondelete="cascade", index=True
    )
    template_id = fields.Many2one(related="template_line_id.template_id", string="Bộ KPI", store=True)
    metric_id = fields.Many2one(related="template_line_id.metric_id", string="Chỉ số", store=True)
    employee_id = fields.Many2one("hr.employee", string="Nhân viên")
    department_id = fields.Many2one("hr.department", string="Phòng ban")
    target = fields.Float("Mục tiêu riêng", digits=(16, 2), required=True)

    # Đợt B2: gợi ý từ lịch sử — chỉ gợi ý, quản lý vẫn quyết định và sửa được
    suggestion_easy = fields.Float("Gợi ý — Dễ", digits=(16, 4), compute="_compute_suggestions")
    suggestion_medium = fields.Float("Gợi ý — Vừa", digits=(16, 4), compute="_compute_suggestions")
    suggestion_hard = fields.Float("Gợi ý — Khó", digits=(16, 4), compute="_compute_suggestions")
    suggestion_note = fields.Char("Nguồn gợi ý", compute="_compute_suggestions")
    suggestion_available = fields.Boolean(compute="_compute_suggestions")

    _employee_xor_department = models.Constraint(
        "CHECK((employee_id IS NOT NULL AND department_id IS NULL) "
        "OR (employee_id IS NULL AND department_id IS NOT NULL))",
        "Mỗi mục tiêu riêng phải chọn đúng một trong hai: Nhân viên hoặc Phòng ban, không được cả hai hoặc không chọn gì.",
    )
    _template_line_employee_unique = models.Constraint(
        "UNIQUE(template_line_id, employee_id)", "Nhân viên này đã có mục tiêu riêng cho chỉ số này."
    )
    _template_line_department_unique = models.Constraint(
        "UNIQUE(template_line_id, department_id)", "Phòng ban này đã có mục tiêu riêng cho chỉ số này."
    )

    @api.depends("template_line_id", "employee_id", "department_id")
    def _compute_suggestions(self):
        """Ba mức gợi ý từ kết quả thực tế (actual) của chính chỉ số này ở các phiếu ĐÃ DUYỆT, dòng được áp dụng,
        phiếu đủ dữ liệu, cùng loại kỳ với bộ KPI, cùng nhân viên hoặc cùng phòng ban (phòng ban đã chụp trên phiếu);
        lấy tối đa 6 kỳ gần nhất, cần ít nhất 3 kỳ khác nhau. Dễ / Vừa / Khó là phân vị 25 / 50 / 75 với chỉ số
        "Cao là tốt"; với "Thấp là tốt" đảo lại (số thấp hơn mới là mục tiêu khó hơn), nên nhãn theo độ khó chứ không
        theo độ lớn của con số."""
        for override in self:
            override.suggestion_easy = override.suggestion_medium = override.suggestion_hard = 0.0
            override.suggestion_available = False
            line = override.template_line_id
            if not line or not (override.employee_id or override.department_id):
                override.suggestion_note = "Chọn dòng chỉ số và nhân viên hoặc phòng ban để xem gợi ý."
                continue
            domain = [
                ("metric_id", "=", line.metric_id.id), ("evaluation_state", "=", "approved"),
                ("is_applicable", "=", True), ("evaluation_id.insufficient_data", "=", False),
                ("period_id.period_type", "=", line.template_id.period_type),
            ]
            domain.append(("employee_id", "=", override.employee_id.id) if override.employee_id
                          else ("department_id", "=", override.department_id.id))
            lines = self.env["kpi.evaluation.line"].sudo().search(domain)
            periods = sorted(lines.period_id, key=lambda p: p.date_from, reverse=True)[:SUGGESTION_MAX_PERIODS]
            if len(periods) < SUGGESTION_MIN_PERIODS:
                override.suggestion_note = (
                    f"Chưa đủ dữ liệu: cần ít nhất {SUGGESTION_MIN_PERIODS} kỳ đã duyệt cùng loại kỳ, hiện có {len(periods)}."
                )
                continue
            values = sorted(line_.actual for line_ in lines if line_.period_id in periods)
            low, mid, high = (percentile(values, q) for q in (0.25, 0.5, 0.75))
            if line.metric_id.direction == "lower":
                override.suggestion_easy, override.suggestion_hard = high, low
            else:
                override.suggestion_easy, override.suggestion_hard = low, high
            override.suggestion_medium = mid
            override.suggestion_available = True
            override.suggestion_note = f"Từ {len(values)} kết quả của {len(periods)} kỳ gần nhất đã duyệt."

    def _apply_suggestion(self, level):
        self.ensure_one()
        if not self.suggestion_available:
            raise UserError("Chưa đủ dữ liệu lịch sử để gợi ý mục tiêu.")
        self.target = {"easy": self.suggestion_easy, "medium": self.suggestion_medium, "hard": self.suggestion_hard}[level]

    def action_apply_easy(self):
        self._apply_suggestion("easy")

    def action_apply_medium(self):
        self._apply_suggestion("medium")

    def action_apply_hard(self):
        self._apply_suggestion("hard")
