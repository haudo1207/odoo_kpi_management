import ast

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

# Bước 1 (Chương 9.1): chỉ cho chỉ số "domain" đọc trên các model này — domain nhập tự do nên phải
# giới hạn model để không ai đọc được dữ liệu ngoài phạm vi KPI (nhân sự, kế toán...).
DOMAIN_METRIC_ALLOWED_MODELS = ["project.task", "project.milestone", "calendar.event"]
NUMERIC_FIELD_TYPES = ("integer", "float", "monetary")

# Bước 0 (rà soát sau Bước 1): đọc domain bằng ast.literal_eval — chỉ parse literal Python
# (list/tuple/str/số...), không chạy được bất kỳ biểu thức hay code nào, an toàn tuyệt đối. Biến
# động (người phụ trách, mốc kỳ) không eval được bằng literal_eval nên dùng chuỗi giữ chỗ, thay giá
# trị thật SAU khi đã parse xong (xem substitute_domain_placeholders trong kpi_engine.py).
DOMAIN_PLACEHOLDER_USER_ID = "$CURRENT_USER_ID"
DOMAIN_PLACEHOLDER_PERIOD_START = "$PERIOD_START"
DOMAIN_PLACEHOLDER_PERIOD_END = "$PERIOD_END"


def parse_metric_domain(expr):
    """Đọc một domain cấu hình bằng ast.literal_eval. Lỗi cú pháp/không phải literal thì raise
    ValueError (gọi nơi dùng tự quyết định bọc lại thành ValidationError hay không)."""
    try:
        domain = ast.literal_eval((expr or "[]").strip() or "[]")
    except (ValueError, SyntaxError) as e:
        raise ValueError(f"không phải cú pháp Python literal hợp lệ ({e})")
    if not isinstance(domain, list):
        raise ValueError("domain phải là một danh sách (list), ví dụ [('state', '=', 'done')]")
    return domain


def substitute_domain_placeholders(domain, user_id, period_start, period_end):
    """Thay $CURRENT_USER_ID/$PERIOD_START/$PERIOD_END trong domain đã parse bằng giá trị thật.
    Chỉ thay trong VALUE của từng điều kiện (phần tử thứ 3), không đụng tên field hay toán tử."""
    mapping = {
        DOMAIN_PLACEHOLDER_USER_ID: user_id,
        DOMAIN_PLACEHOLDER_PERIOD_START: period_start,
        DOMAIN_PLACEHOLDER_PERIOD_END: period_end,
    }

    def _sub_value(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [_sub_value(v) for v in value]
        if isinstance(value, tuple):
            return tuple(_sub_value(v) for v in value)
        return value

    result = []
    for item in domain:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            field, operator, value = item
            result.append((field, operator, _sub_value(value)))
        else:
            result.append(item)  # '|', '&', '!'
    return result


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
        help="Để trống nếu điều kiện người đã viết sẵn trong domain bằng $CURRENT_USER_ID.",
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
        help="Domain Odoo dạng literal thuần (đọc bằng ast.literal_eval, không chạy được code). Dùng "
             "chuỗi giữ chỗ $CURRENT_USER_ID / $PERIOD_START / $PERIOD_END khi cần điều kiện người/kỳ "
             "qua quan hệ — ví dụ [('origin_task_id.user_ids', 'in', ['$CURRENT_USER_ID'])].",
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
            # gamification.goal.definition._check_domain_validity() đang làm. Giá trị thử chỉ để
            # kiểm tra cú pháp/field hợp lệ — không lưu kết quả nên dùng giá trị giả cũng được.
            Model = self.env[metric.source_model_id.model].sudo()
            now = fields.Datetime.now()
            exprs = [metric.numerator_domain]
            if metric.aggregation == "ratio":
                exprs.append(metric.denominator_domain)
            try:
                for expr in exprs:
                    domain = parse_metric_domain(expr)
                    domain = substitute_domain_placeholders(domain, self.env.user.id, now, now)
                    Model.search_count(domain)
            except Exception as e:
                raise ValidationError(f"Chỉ số \"{metric.name}\": domain không hợp lệ — {e}")

    @api.constrains("code", "compute_mode")
    def _check_auto_metric_has_function(self):
        """Chỉ số Tự động (code) cần đúng một hàm `_metric_<mã>()` trong `kpi.engine` (xem
        `compute_actual()`). Không kiểm ở đây thì lỗi chỉ lộ ra lúc bấm "Tính KPI" với `UserError`
        chung chung — quá muộn so với lúc lưu, nhất là khi đổi mã của một chỉ số đang dùng (ví dụ
        D1 → D01). `kpi.engine` là AbstractModel, không có record, nên tra hàm ngay trên model,
        cùng cách `compute_actual()` tự làm."""
        engine = self.env["kpi.engine"]
        for metric in self.filtered(lambda m: m.compute_mode == "auto"):
            if not getattr(engine, f"_metric_{metric.code.lower()}", None):
                raise ValidationError(
                    f"Chỉ số \"{metric.name}\" (mã {metric.code}): chưa có hàm "
                    f"_metric_{metric.code.lower()}() trong kpi.engine. Nếu vừa đổi mã của chỉ số có "
                    "sẵn, đổi lại đúng mã cũ, hoặc thêm hàm tương ứng trước khi lưu."
                )

    def _is_engine_computed(self):
        """Điều kiện DUY NHẤT quyết định chỉ số nào do engine tính (mọi chế độ trừ nhập tay). Mọi nơi gọi
        engine hoặc chặn ghi số liệu (Tính KPI, wizard, cron, API, view) phải dùng hàm này thay vì tự so
        compute_mode — chế độ mới thêm sau sẽ không bị sót ở một đường nào."""
        self.ensure_one()
        return self.compute_mode != "manual"

    def action_open_test_wizard(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("project_kpi_management.group_kpi_admin"):
            raise AccessError("Chỉ KPI Administrator được thử tính chỉ số.")
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
