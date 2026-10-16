from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

RATINGS = [
    ("excellent", "Xuất sắc"),
    ("good", "Tốt"),
    ("pass", "Đạt"),
    ("improve", "Cần cải thiện"),
]

PIP_ACTIVITY_XMLID = "project_kpi_management.mail_activity_type_pip"


def _check_self_assessment_field(vals_list, env, field, message):
    """Mục 6: employee_comment/self_score chỉ được ghi bằng sudo() (qua wizard Tự đánh giá), dù
    quản lý/admin có quyền ghi bình thường trên model (cho manager_adjustment, D9...). Phải chặn
    cả create() lẫn write() — chặn một chỗ vẫn lách được qua chỗ kia (phát hiện khi rà lại sau khi
    sửa write(), xem Chương 5.6: script pre_defense_check.py)."""
    if env.su:
        return
    if any(field in vals for vals in vals_list):
        raise UserError(message)

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


# Điểm và giá trị thực tế lưu đủ độ chính xác (không khai báo digits): xếp loại so trên giá trị
# chưa làm tròn, D3 (bug/SP) cần nhiều chữ số lẻ. Làm tròn chỉ ở view, bằng thuộc tính digits.


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

    computed_date = fields.Datetime("Tính KPI lúc", readonly=True, copy=False)
    approved_date = fields.Datetime("Duyệt lúc", readonly=True, copy=False)
    late_bug_count = fields.Integer("Bug phát sinh muộn", compute="_compute_late_bug_count")

    applicable_weight = fields.Integer("Trọng số được áp dụng", compute="_compute_kpi_score", store=True)
    insufficient_data = fields.Boolean("Không đủ dữ liệu đánh giá", compute="_compute_kpi_score", store=True)
    kpi_score = fields.Float("Điểm KPI", compute="_compute_kpi_score", store=True, aggregator="avg")
    manager_adjustment = fields.Float("Điều chỉnh của quản lý", digits=(16, 2), tracking=True)
    adjustment_note = fields.Text("Lý do điều chỉnh")
    final_score = fields.Float("Điểm cuối", compute="_compute_final_score", store=True, tracking=True, aggregator="avg")
    rating = fields.Selection(RATINGS, string="Xếp loại tự động", compute="_compute_final_score", store=True)
    manual_rating = fields.Selection(RATINGS, string="Xếp loại thủ công", tracking=True)
    manual_rating_note = fields.Text("Lý do xếp loại thủ công")
    final_rating = fields.Selection(
        RATINGS, string="Xếp loại", compute="_compute_final_rating", store=True, tracking=True,
        help="Dùng cho mọi báo cáo: xếp loại thủ công nếu thiếu dữ liệu, ngược lại là xếp loại tự động.",
    )

    # Mục 6: nhân viên tự đánh giá — chỉ tham khảo, không cộng vào điểm, không thêm trạng thái.
    # Ghi qua wizard kpi.self.assessment.wizard bằng sudo(), không nới quyền ghi trực tiếp.
    employee_comment = fields.Text("Nhận xét của nhân viên", copy=False)
    is_own_evaluation = fields.Boolean(compute="_compute_is_own_evaluation")

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

    def _compute_is_own_evaluation(self):
        for ev in self:
            ev.is_own_evaluation = ev.employee_id.sudo().user_id == self.env.user

    def action_open_self_assessment(self):
        self.ensure_one()
        if not self.is_own_evaluation:
            raise AccessError("Chỉ chính nhân viên trên phiếu mới tự đánh giá được.")
        if self.state != "draft":
            raise UserError("Chỉ tự đánh giá được khi phiếu ở trạng thái Nháp.")
        return {
            "type": "ir.actions.act_window",
            "name": "Tự đánh giá",
            "res_model": "kpi.self.assessment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_evaluation_id": self.id},
        }

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
        _check_self_assessment_field(
            vals_list, self.env, "employee_comment", "Chỉ ghi nhận xét của nhân viên qua wizard Tự đánh giá."
        )
        # sudo: quản lý KPI không thuộc nhóm HR vẫn cần đọc chức danh, phòng ban (nằm ở hr.version)
        Employee = self.env["hr.employee"].sudo()
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
                overrides = self.env["kpi.target.override"].sudo().search([
                    ("template_line_id", "in", template.line_ids.ids),
                    "|", ("employee_id", "=", vals["employee_id"]), ("department_id", "=", vals["department_id"]),
                ])
                # Chụp dữ liệu từ template: sửa template hay mục tiêu riêng sau này không ảnh hưởng phiếu đã tạo.
                # Thứ tự ưu tiên mục tiêu: nhân viên -> phòng ban -> template
                vals["line_ids"] = [
                    fields.Command.create({
                        "sequence": line.sequence,
                        "metric_id": line.metric_id.id,
                        "target": line._resolve_target(overrides, vals["employee_id"], vals["department_id"]),
                        "weight": line.weight,
                        "min_volume": line.min_volume,
                        "scale_json": line.scale_id._snapshot() if line.scale_id else False,
                    })
                    for line in template.line_ids
                ]
        return super().create(vals_list)

    def write(self, vals):
        # employee_comment là lời của chính nhân viên: quản lý/admin vẫn có quyền ghi (group_kpi_manager
        # write=1 trên cả model) nên _LOCKED_FIELDS (chỉ khoá khi hết Nháp) không đủ — chặn hẳn việc ghi
        # trực tiếp ngoài wizard, bất kể trạng thái. Wizard ghi qua sudo() nên không bị chặn ở đây.
        _check_self_assessment_field(
            [vals], self.env, "employee_comment", "Chỉ ghi nhận xét của nhân viên qua wizard Tự đánh giá."
        )
        if self._LOCKED_FIELDS & vals.keys() and self.filtered(lambda e: e.state != "draft"):
            raise UserError("Phiếu đã gửi hoặc đã duyệt, chỉ sửa được khi ở trạng thái Nháp.")
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda e: e.state != "draft"):
            raise UserError("Chỉ xoá được phiếu ở trạng thái Nháp.")
        return super().unlink()

    # ---- Tính KPI ----

    def action_compute_kpi(self):
        """Lấy số liệu thực tế cho các chỉ số tự động. Điểm tự tính lại qua compute."""
        engine = self.env["kpi.engine"]
        for ev in self:
            if ev.state != "draft":
                raise UserError(f"Phiếu {ev.name} không ở trạng thái Nháp, không tính lại được.")
            for line in ev.line_ids.filtered(lambda l: l.metric_id._is_engine_computed()):
                actual, volume = engine.compute_actual(
                    line.metric_id, ev.employee_id, ev.period_id.date_from, ev.period_id.date_to
                )
                line.write({"actual": actual, "volume": volume})
            ev.computed_date = fields.Datetime.now()
        # Tính lại điểm kể cả khi số liệu không đổi: tham số trong Settings (trần, ngưỡng) có thể đã đổi.
        # add_to_compute chỉ đánh dấu đúng field được truyền vào, nên phải liệt kê mọi field của từng hàm compute
        lines = self.line_ids
        for name in ("is_applicable", "score", "weighted_score"):
            self.env.add_to_compute(lines._fields[name], lines)
        for name in ("applicable_weight", "insufficient_data", "kpi_score", "final_score", "rating", "final_rating"):
            self.env.add_to_compute(self._fields[name], self)
        return True

    # ---- Quy trình: Nháp → Đã gửi → Đã duyệt ----

    # ---- Bug phát sinh muộn: bug tính KPI xuất hiện sau khi phiếu đã duyệt ----

    def _late_bugs(self):
        self.ensure_one()
        if not self.approved_date or not self.employee_id.sudo().user_id:
            return self.env["project.task"]
        engine = self.env["kpi.engine"]
        ctx = engine._context_for(self.employee_id, self.period_id.date_from, self.period_id.date_to)
        return engine._counted_bugs(ctx).filtered(lambda b: b.create_date > self.approved_date)

    def _compute_late_bug_count(self):
        for ev in self:
            ev.late_bug_count = len(ev._late_bugs())

    def action_view_late_bugs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Bug phát sinh muộn — {self.name}",
            "res_model": "project.task",
            "view_mode": "list,form",
            "domain": [("id", "in", self._late_bugs().ids)],
        }

    def _check_kpi_admin(self):
        if not self.env.su and not self.env.user.has_group("project_kpi_management.group_kpi_admin"):
            raise AccessError("Chỉ KPI Administrator được duyệt, trả về hoặc mở lại phiếu.")

    def _check_no_role_conflict(self):
        """Không cho một người vừa là nhân viên/quản lý trực tiếp vừa tự duyệt phiếu của chính họ
        bằng vai trò KPI Administrator (Chương 8.3 cũ). Dựa vào self.env.user nên vẫn đúng khi gọi
        qua sudo(); bỏ qua khi chạy bằng superuser (cron, script) vì đó không phải một người duyệt."""
        if self.env.su:
            return
        user = self.env.user
        for ev in self:
            employee = ev.employee_id.sudo()
            if user in (employee.user_id, employee.parent_id.user_id):
                raise AccessError(
                    f"{user.name} là chính nhân viên hoặc quản lý trực tiếp của {employee.name}, "
                    f"không được duyệt, trả về hay mở lại phiếu {ev.name}."
                )

    def action_submit(self):
        for ev in self:
            if ev.state != "draft":
                raise UserError("Chỉ gửi duyệt được phiếu ở trạng thái Nháp.")
            if not ev.computed_date:
                raise UserError(f"Phiếu {ev.name} chưa Tính KPI.")
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
        return True

    def action_approve(self):
        self._check_kpi_admin()
        self._check_no_role_conflict()
        if self.filtered(lambda e: e.state != "submitted"):
            raise UserError("Chỉ duyệt được phiếu đã gửi.")
        self.write({"state": "approved", "approved_date": fields.Datetime.now()})
        self._sync_pip_activity()
        return True

    def _sync_pip_activity(self):
        """Mục 3: phiếu duyệt với xếp loại Cần cải thiện thì nhắc quản lý trực tiếp lập kế hoạch
        cải thiện. Không tạo trùng nếu đã có nhắc việc đang mở (ví dụ Mở lại rồi Duyệt lại)."""
        pip_type = self.env.ref(PIP_ACTIVITY_XMLID, raise_if_not_found=False)
        if not pip_type:
            return
        for ev in self:
            if ev.final_rating != "improve":
                continue
            if ev.activity_ids.filtered(lambda a: a.activity_type_id == pip_type):
                continue
            manager_user = ev.employee_id.sudo().parent_id.user_id
            ev.activity_schedule(
                act_type_xmlid=PIP_ACTIVITY_XMLID,
                user_id=(manager_user or self.env.user).id,
                summary="Lập kế hoạch cải thiện",
                note=f"Phiếu {ev.name} được duyệt với xếp loại Cần cải thiện. "
                     "Hãy lập kế hoạch cải thiện cho nhân viên.",
            )

    def _cancel_pip_activity(self):
        """Huỷ nhắc việc PIP khi phiếu không còn ở trạng thái Đã duyệt (Trả về/Mở lại), để lần
        duyệt sau tự đánh giá lại đúng theo xếp loại mới, không để sót nhắc việc đã lỗi thời."""
        pip_type = self.env.ref(PIP_ACTIVITY_XMLID, raise_if_not_found=False)
        if not pip_type:
            return
        self.activity_ids.filtered(lambda a: a.activity_type_id == pip_type).unlink()

    def action_return_draft(self):
        return self._open_reason_wizard("return")

    def action_reopen(self):
        return self._open_reason_wizard("reopen")

    def _open_reason_wizard(self, mode):
        self.ensure_one()
        self._check_kpi_admin()
        self._check_no_role_conflict()
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
    evaluation_state = fields.Selection(related="evaluation_id.state", store=True, string="Trạng thái phiếu")
    employee_id = fields.Many2one(related="evaluation_id.employee_id", store=True, index=True)
    period_id = fields.Many2one(related="evaluation_id.period_id", store=True, index=True)
    department_id = fields.Many2one(related="evaluation_id.department_id", store=True)
    job_id = fields.Many2one(related="evaluation_id.job_id", store=True)
    category = fields.Selection(related="metric_id.category", store=True)
    sequence = fields.Integer(default=10)
    metric_id = fields.Many2one("kpi.metric", string="Chỉ số", required=True, ondelete="restrict")
    compute_mode = fields.Selection(related="metric_id.compute_mode")
    direction = fields.Selection(related="metric_id.direction")
    unit = fields.Char(related="metric_id.unit")

    target = fields.Float("Mục tiêu", digits=(16, 2))
    weight = fields.Integer("Trọng số (%)")
    min_volume = fields.Float("Khối lượng tối thiểu", digits=(16, 2))
    scale_json = fields.Text(
        "Bảng bậc (chụp)", copy=False, readonly=True,
        help="Bước 3: bảng bậc điểm chụp từ bộ KPI lúc tạo phiếu, dạng JSON [[% từ, điểm], ...]. Trống = tính tuyến tính.",
    )
    achievement_pct = fields.Float("% đạt mục tiêu", compute="_compute_score", store=True, digits=(16, 2))
    volume = fields.Float("Khối lượng", help="Engine tính ở Phase 4. Dưới khối lượng tối thiểu thì Không áp dụng.")
    actual = fields.Float("Thực tế", aggregator="avg")
    actual_entered = fields.Boolean("Đã chấm", help="Chỉ số nhập tay đã được chấm. Tự bật khi sửa giá trị Thực tế.")
    is_applicable = fields.Boolean("Áp dụng", compute="_compute_score", store=True)
    score = fields.Float("Điểm", compute="_compute_score", store=True, aggregator="avg")
    weighted_score = fields.Float("Điểm đóng góp", compute="_compute_score", store=True)
    remark = fields.Text("Ghi chú")
    self_score = fields.Float(
        "Tự chấm", copy=False,
        help="Mục 6: nhân viên tự chấm (chỉ tham khảo, không cộng vào điểm chính thức).",
    )

    @api.depends("actual", "target", "volume", "min_volume", "weight", "metric_id.direction", "scale_json")
    def _compute_score(self):
        cap = get_kpi_param(self.env, "score_cap")
        for line in self:
            line.is_applicable = line.volume >= line.min_volume
            # % đạt mục tiêu đã chặn trần (Thấp tốt, thực tế = 0 → trần) rồi mới tra bậc; điểm tra được
            # vẫn bị chặn trần lần nữa. Chỉ số Không áp dụng thì không tra bậc (điểm 0 như trước).
            pct = self._score(line.actual, line.target, line.direction, cap) if line.is_applicable else 0.0
            line.achievement_pct = pct
            if line.is_applicable and line.scale_json:
                line.score = min(self.env["kpi.score.scale"].lookup(line.scale_json, pct), cap)
            else:
                line.score = pct
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
        _check_self_assessment_field(
            vals_list, self.env, "self_score", "Chỉ ghi tự chấm của nhân viên qua wizard Tự đánh giá."
        )
        lines = super().create(vals_list)
        lines._check_evaluation_draft()
        return lines

    def write(self, vals):
        _check_self_assessment_field(
            [vals], self.env, "self_score", "Chỉ ghi tự chấm của nhân viên qua wizard Tự đánh giá."
        )
        self._check_evaluation_draft()
        if "actual" in vals:
            manual = self.filtered(lambda l: l.compute_mode == "manual")
            if manual and "actual_entered" not in vals:
                super(KpiEvaluationLine, manual).write({"actual_entered": True})
        return super().write(vals)

    def unlink(self):
        self._check_evaluation_draft()
        return super().unlink()
