from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

# Bước 1 (Chương 9.1): chỉ cho chỉ số "domain" đọc trên các model này — domain nhập tự do nên phải
# giới hạn model để không ai đọc được dữ liệu ngoài phạm vi KPI (nhân sự, kế toán...).
DOMAIN_METRIC_ALLOWED_MODELS = ["project.task", "project.milestone", "calendar.event"]
NUMERIC_FIELD_TYPES = ("integer", "float", "monetary")


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
        [("auto", "Tự động (code)"), ("domain", "Tự động (cấu hình)"), ("manual", "Nhập tay")],
        string="Cách tính",
        required=True,
        default="auto",
    )
    description = fields.Text("Mô tả / công thức")
    active = fields.Boolean(default=True)

    # Bước 1 (Chương 9.1): chỉ số cấu hình không cần code — xem kpi_engine._compute_domain_metric().
    # Theo đúng cách gamification.goal.definition đã làm (model + field + domain), nhưng chỉ dùng
    # phần domain/count/sum (dữ liệu, an toàn) — không có lựa chọn "chạy code Python tuỳ ý".
    source_model_id = fields.Many2one(
        "ir.model", string="Model dữ liệu",
        domain=[("model", "in", DOMAIN_METRIC_ALLOWED_MODELS)],
    )
    user_field_id = fields.Many2one(
        "ir.model.fields", string="Field người phụ trách",
        domain="[('model_id', '=', source_model_id)]",
        help="Để trống nếu điều kiện người/kỳ đã viết sẵn trong domain (dùng biến user/start/end).",
    )
    date_field_id = fields.Many2one(
        "ir.model.fields", string="Field ngày lọc theo kỳ",
        domain="[('model_id', '=', source_model_id), ('ttype', 'in', ('date', 'datetime'))]",
    )
    aggregation = fields.Selection(
        [("count", "Đếm"), ("sum", "Tổng"), ("avg", "Trung bình"), ("ratio", "Tỷ lệ")],
        string="Phép tính",
    )
    value_field_id = fields.Many2one(
        "ir.model.fields", string="Field để Tổng/Trung bình",
        domain="[('model_id', '=', source_model_id), ('ttype', 'in', ('integer', 'float', 'monetary'))]",
    )
    numerator_domain = fields.Char(
        "Domain (tử số nếu Tỷ lệ)", default="[]",
        help="Domain Odoo chuẩn. Có thể dùng biến 'user' (res.users của nhân viên), 'start', 'end' "
             "(mốc đầu/cuối kỳ, datetime UTC) — ví dụ [('origin_task_id.user_ids', 'in', [user.id])].",
    )
    denominator_domain = fields.Char("Domain mẫu số (khi Tỷ lệ)")

    _code_unique = models.Constraint("UNIQUE(code)", "Mã chỉ số đã tồn tại.")

    @api.constrains(
        "compute_mode", "source_model_id", "user_field_id", "date_field_id", "value_field_id",
        "aggregation", "numerator_domain", "denominator_domain",
    )
    def _check_domain_metric_config(self):
        for metric in self.filtered(lambda m: m.compute_mode == "domain"):
            if not metric.source_model_id:
                raise ValidationError(f"Chỉ số \"{metric.name}\": chưa chọn model dữ liệu.")
            if metric.source_model_id.model not in DOMAIN_METRIC_ALLOWED_MODELS:
                raise ValidationError(
                    "Chỉ số \"%s\": chỉ được chọn model trong danh sách cho phép (%s)."
                    % (metric.name, ", ".join(DOMAIN_METRIC_ALLOWED_MODELS))
                )
            if not metric.aggregation:
                raise ValidationError(f"Chỉ số \"{metric.name}\": chưa chọn phép tính.")
            for field in (metric.user_field_id, metric.date_field_id, metric.value_field_id):
                if field and field.model_id != metric.source_model_id:
                    raise ValidationError(
                        f"Chỉ số \"{metric.name}\": field phải thuộc đúng model dữ liệu đã chọn."
                    )
            if metric.aggregation in ("sum", "avg"):
                if not metric.value_field_id:
                    raise ValidationError(f"Chỉ số \"{metric.name}\": Tổng/Trung bình cần chọn field số.")
                if metric.value_field_id.ttype not in NUMERIC_FIELD_TYPES:
                    raise ValidationError(f"Chỉ số \"{metric.name}\": field để Tổng/Trung bình phải kiểu số.")
            if metric.aggregation == "ratio" and not (metric.denominator_domain or "").strip():
                raise ValidationError(f"Chỉ số \"{metric.name}\": Tỷ lệ cần nhập domain mẫu số.")
            # Thử chạy domain thật để bắt lỗi cú pháp/field sai ngay khi lưu, cùng cách
            # gamification.goal.definition._check_domain_validity() đang làm.
            Model = self.env[metric.source_model_id.model].sudo()
            ctx = {"user": self.env.user, "start": fields.Datetime.now(), "end": fields.Datetime.now()}
            try:
                Model.search_count(safe_eval(metric.numerator_domain or "[]", ctx))
                if metric.aggregation == "ratio":
                    Model.search_count(safe_eval(metric.denominator_domain or "[]", ctx))
            except Exception as e:
                raise ValidationError(f"Chỉ số \"{metric.name}\": domain không hợp lệ — {e}")

    def action_open_test_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Thử tính chỉ số",
            "res_model": "kpi.metric.test.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_metric_id": self.id},
        }

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
