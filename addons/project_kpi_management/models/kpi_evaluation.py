from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

RATINGS = [
    ("excellent", "Xuất sắc"),
    ("good", "Tốt"),
    ("pass", "Đạt"),
    ("improve", "Cần cải thiện"),
]

# Giá trị mặc định, ghi đè được bằng ir.config_parameter (giao diện Settings làm ở Phase 7)
PARAM_DEFAULTS = {
    "score_cap": 120.0,
    "adjustment_max": 10.0,
    "min_applicable_weight": 50.0,
    "rating_excellent": 100.0,
    "rating_good": 90.0,
    "rating_pass": 75.0,
}


def get_kpi_param(env, key):
    value = env["ir.config_parameter"].sudo().get_param(f"project_kpi_management.{key}")
    return float(value) if value else PARAM_DEFAULTS[key]


class KpiEvaluation(models.Model):
    _name = "kpi.evaluation"
    _description = "Phiếu đánh giá KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_id desc, employee_id"

    # Các field chỉ được sửa khi phiếu ở trạng thái Nháp
    _LOCKED_FIELDS = {
        "employee_id", "period_id", "template_id", "line_ids",
        "manager_adjustment", "adjustment_note", "manual_rating", "manual_rating_note",
    }

    name = fields.Char("Phiếu", compute="_compute_name", store=True)
    employee_id = fields.Many2one("hr.employee", string="Nhân viên", required=True, index=True, tracking=True)
    # Chụp lúc tạo phiếu: job_id, department_id trên hr.employee không stored (nằm ở hr.version)
    job_id = fields.Many2one("hr.job", string="Chức danh", readonly=True, index=True)
    department_id = fields.Many2one("hr.department", string="Phòng ban", readonly=True, index=True)
    period_id = fields.Many2one("kpi.period", string="Kỳ đánh giá", required=True, index=True, tracking=True)
    template_id = fields.Many2one("kpi.template", string="Bộ KPI", required=True)
    line_ids = fields.One2many("kpi.evaluation.line", "evaluation_id", string="Chỉ số")
    state = fields.Selection(
        [("draft", "Nháp"), ("submitted", "Đã gửi"), ("approved", "Đã duyệt")],
        string="Trạng thái",
        default="draft",
        required=True,
        tracking=True,
    )

    applicable_weight = fields.Integer("Trọng số được áp dụng", compute="_compute_kpi_score", store=True)
    insufficient_data = fields.Boolean("Không đủ dữ liệu đánh giá", compute="_compute_kpi_score", store=True)
    kpi_score = fields.Float("Điểm KPI", digits=(16, 2), compute="_compute_kpi_score", store=True)
    manager_adjustment = fields.Float("Điều chỉnh của quản lý", digits=(16, 2), tracking=True)
    adjustment_note = fields.Text("Lý do điều chỉnh")
    final_score = fields.Float("Điểm cuối", digits=(16, 2), compute="_compute_final_score", store=True, tracking=True)
    rating = fields.Selection(RATINGS, string="Xếp loại tự động", compute="_compute_final_score", store=True)
    manual_rating = fields.Selection(RATINGS, string="Xếp loại thủ công", tracking=True)
    manual_rating_note = fields.Text("Lý do xếp loại thủ công")
    final_rating = fields.Selection(
        RATINGS, string="Xếp loại", compute="_compute_final_rating", store=True, tracking=True,
        help="Dùng cho mọi báo cáo: xếp loại thủ công nếu thiếu dữ liệu, ngược lại là xếp loại tự động.",
    )

    _employee_period_unique = models.Constraint(
        "UNIQUE(employee_id, period_id)", "Mỗi nhân viên chỉ có một phiếu đánh giá trong một kỳ."
    )

    @api.depends("employee_id", "period_id")
    def _compute_name(self):
        for ev in self:
            ev.name = f"{ev.employee_id.name or ''} — {ev.period_id.name or ''}"

    @api.depends("line_ids.score", "line_ids.weight", "line_ids.is_applicable")
    def _compute_kpi_score(self):
        min_weight = get_kpi_param(self.env, "min_applicable_weight")
        for ev in self:
            applicable = ev.line_ids.filtered("is_applicable")
            weight = sum(applicable.mapped("weight"))
            ev.applicable_weight = weight
            ev.insufficient_data = weight < min_weight
            # Chỉ cộng chỉ số được áp dụng, chia cho tổng trọng số được áp dụng
            ev.kpi_score = sum(l.score * l.weight for l in applicable) / weight if weight else 0.0

    @api.depends("kpi_score", "manager_adjustment", "insufficient_data")
    def _compute_final_score(self):
        excellent = get_kpi_param(self.env, "rating_excellent")
        good = get_kpi_param(self.env, "rating_good")
        passed = get_kpi_param(self.env, "rating_pass")
        for ev in self:
            ev.final_score = ev.kpi_score + ev.manager_adjustment
            # So trên giá trị chưa làm tròn, khoảng nửa mở
            if ev.insufficient_data:
                ev.rating = False
            elif ev.final_score >= excellent:
                ev.rating = "excellent"
            elif ev.final_score >= good:
                ev.rating = "good"
            elif ev.final_score >= passed:
                ev.rating = "pass"
            else:
                ev.rating = "improve"

    @api.depends("rating", "manual_rating", "insufficient_data")
    def _compute_final_rating(self):
        for ev in self:
            ev.final_rating = ev.manual_rating if ev.insufficient_data else ev.rating

    @api.constrains("manager_adjustment", "adjustment_note")
    def _check_adjustment(self):
        max_adj = get_kpi_param(self.env, "adjustment_max")
        for ev in self:
            if abs(ev.manager_adjustment) > max_adj:
                raise ValidationError(f"Điều chỉnh của quản lý phải nằm trong khoảng ±{max_adj:g} điểm.")
            if ev.manager_adjustment and not (ev.adjustment_note or "").strip():
                raise ValidationError("Điều chỉnh điểm khác 0 thì bắt buộc ghi lý do.")

    @api.constrains("period_id")
    def _check_period_open(self):
        for ev in self:
            if ev.period_id.state != "open" and ev.state == "draft":
                raise ValidationError(f"Kỳ \"{ev.period_id.name}\" đã đóng, không tạo phiếu mới được.")

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.job_id.kpi_template_id:
            self.template_id = self.employee_id.job_id.kpi_template_id

    @api.model_create_multi
    def create(self, vals_list):
        Employee = self.env["hr.employee"]
        for vals in vals_list:
            employee = Employee.browse(vals.get("employee_id"))
            vals.setdefault("job_id", employee.job_id.id)
            vals.setdefault("department_id", employee.department_id.id)
            if not vals.get("template_id"):
                vals["template_id"] = employee.job_id.kpi_template_id.id
            template = self.env["kpi.template"].browse(vals.get("template_id"))
            if not template:
                raise UserError(f"Chức danh của {employee.name} chưa gắn bộ KPI. Hãy chọn bộ KPI cho phiếu.")
            if not template.line_ids:
                raise UserError(f"Bộ KPI \"{template.name}\" chưa có chỉ số nào, không tạo phiếu được.")
            if "line_ids" not in vals:
                # Chụp dữ liệu từ template: sửa template sau này không ảnh hưởng phiếu đã tạo
                vals["line_ids"] = [
                    fields.Command.create({
                        "sequence": line.sequence,
                        "metric_id": line.metric_id.id,
                        "target": line.target,
                        "weight": line.weight,
                        "min_volume": line.min_volume,
                    })
                    for line in template.line_ids
                ]
        return super().create(vals_list)

    def write(self, vals):
        if self._LOCKED_FIELDS & vals.keys() and self.filtered(lambda e: e.state != "draft"):
            raise UserError("Phiếu đã gửi hoặc đã duyệt, chỉ sửa được khi ở trạng thái Nháp.")
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda e: e.state != "draft"):
            raise UserError("Chỉ xoá được phiếu ở trạng thái Nháp.")
        return super().unlink()

    # ---- Quy trình: Nháp → Đã gửi → Đã duyệt ----

    def action_submit(self):
        for ev in self:
            if ev.state != "draft":
                raise UserError("Chỉ gửi duyệt được phiếu ở trạng thái Nháp.")
            missing = ev.line_ids.filtered(lambda l: l.compute_mode == "manual" and not l.actual_entered)
            if missing:
                raise UserError(
                    "Chưa chấm các chỉ số nhập tay: %s." % ", ".join(missing.metric_id.mapped("display_name"))
                )
            if ev.insufficient_data and not (ev.manual_rating and (ev.manual_rating_note or "").strip()):
                raise UserError(
                    "Phiếu không đủ dữ liệu đánh giá (trọng số được áp dụng %s). "
                    "Hãy chọn xếp loại thủ công và ghi lý do." % ev.applicable_weight
                )
        self.write({"state": "submitted"})

    def action_approve(self):
        if self.filtered(lambda e: e.state != "submitted"):
            raise UserError("Chỉ duyệt được phiếu đã gửi.")
        self.write({"state": "approved"})

    def action_return_draft(self):
        return self._open_reason_wizard("return")

    def action_reopen(self):
        return self._open_reason_wizard("reopen")

    def _open_reason_wizard(self, mode):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Trả về nháp" if mode == "return" else "Mở lại phiếu",
            "res_model": "kpi.evaluation.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_evaluation_id": self.id, "default_mode": mode},
        }


class KpiEvaluationLine(models.Model):
    _name = "kpi.evaluation.line"
    _description = "Dòng chỉ số trong phiếu đánh giá"
    _order = "sequence, id"

    evaluation_id = fields.Many2one("kpi.evaluation", string="Phiếu", required=True, ondelete="cascade", index=True)
    evaluation_state = fields.Selection(related="evaluation_id.state")
    sequence = fields.Integer(default=10)
    metric_id = fields.Many2one("kpi.metric", string="Chỉ số", required=True, ondelete="restrict")
    compute_mode = fields.Selection(related="metric_id.compute_mode")
    direction = fields.Selection(related="metric_id.direction")
    unit = fields.Char(related="metric_id.unit")

    target = fields.Float("Mục tiêu", digits=(16, 2))
    weight = fields.Integer("Trọng số (%)")
    min_volume = fields.Float("Khối lượng tối thiểu", digits=(16, 2))
    volume = fields.Float("Khối lượng", digits=(16, 2), help="Engine tính ở Phase 4. Dưới khối lượng tối thiểu thì Không áp dụng.")
    actual = fields.Float("Thực tế", digits=(16, 2))
    actual_entered = fields.Boolean("Đã chấm", help="Chỉ số nhập tay đã được chấm. Tự bật khi sửa giá trị Thực tế.")
    is_applicable = fields.Boolean("Áp dụng", compute="_compute_score", store=True)
    score = fields.Float("Điểm", digits=(16, 2), compute="_compute_score", store=True)
    weighted_score = fields.Float("Điểm đóng góp", digits=(16, 2), compute="_compute_score", store=True)
    remark = fields.Text("Ghi chú")

    @api.depends("actual", "target", "volume", "min_volume", "weight", "metric_id.direction")
    def _compute_score(self):
        cap = get_kpi_param(self.env, "score_cap")
        for line in self:
            line.is_applicable = line.volume >= line.min_volume
            line.score = self._score(line.actual, line.target, line.direction, cap) if line.is_applicable else 0.0
            line.weighted_score = line.score * line.weight / 100

    @staticmethod
    def _score(actual, target, direction, cap):
        if direction == "lower":
            # Thấp là tốt: thực tế = 0 thì lấy điểm trần (chỉ khi chỉ số được áp dụng)
            score = cap if actual <= 0 else target / actual * 100
        else:
            score = cap if target <= 0 else actual / target * 100
        return max(min(score, cap), 0.0)

    @api.onchange("actual")
    def _onchange_actual(self):
        if self.compute_mode == "manual":
            self.actual_entered = True

    def _check_evaluation_draft(self):
        if self.evaluation_id.filtered(lambda e: e.state != "draft"):
            raise UserError("Phiếu đã gửi hoặc đã duyệt, chỉ sửa được khi ở trạng thái Nháp.")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_evaluation_draft()
        return lines

    def write(self, vals):
        self._check_evaluation_draft()
        if "actual" in vals:
            manual = self.filtered(lambda l: l.compute_mode == "manual")
            if manual and "actual_entered" not in vals:
                super(KpiEvaluationLine, manual).write({"actual_entered": True})
        return super().write(vals)

    def unlink(self):
        self._check_evaluation_draft()
        return super().unlink()
