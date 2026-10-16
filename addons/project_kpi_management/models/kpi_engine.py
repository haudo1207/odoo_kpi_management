from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

from .kpi_metric import parse_metric_domain, substitute_domain_placeholders

BUG_RESOLUTIONS_COUNTED = ("valid", "wont_fix")
HIGH_PRIORITIES = ("2", "3")  # High, Urgent


class KpiEngine(models.AbstractModel):
    """Tính giá trị thực tế (actual) và khối lượng (volume) của các chỉ số tự động.

    Mỗi chỉ số có một hàm _metric_<mã>(ctx) trả về (actual, volume). Điểm, xếp loại
    do phiếu đánh giá tự tính từ actual/volume (compute stored ở kpi.evaluation.line).
    Engine chỉ đọc dữ liệu nên chạy bằng sudo, không phụ thuộc quyền xem task của người bấm.
    """

    _name = "kpi.engine"
    _description = "KPI Engine"

    @api.model
    def compute_actual(self, metric, employee, date_from, date_to):
        """Trả về (actual, volume) của một chỉ số, hoặc None nếu chỉ số nhập tay."""
        if not metric._is_engine_computed():
            return None
        if metric.compute_mode == "domain":
            return self._compute_domain_metric(metric, employee, date_from, date_to)
        method = getattr(self, f"_metric_{metric.code.lower()}", None)
        if not method:
            raise UserError(f"Chưa có hàm tính cho chỉ số tự động {metric.code}.")
        return method(self._context_for(employee, date_from, date_to))

    @api.model
    def _compute_domain_metric(self, metric, employee, date_from, date_to):
        """Bước 1 (Chương 9.1): chỉ số cấu hình thuần dữ liệu, không cần hàm _metric_<mã>().
        Domain đọc bằng ast.literal_eval (an toàn tuyệt đối), chuỗi giữ chỗ $CURRENT_USER_ID/
        $PERIOD_START/$PERIOD_END được thay bằng giá trị thật sau khi parse. Cộng thêm điều kiện
        người/kỳ nếu metric có khai báo user_field_id/date_field_id (để trống thì domain phải tự
        viết đủ, ví dụ dùng đường dẫn quan hệ như origin_task_id.user_ids — xem Chương 9.1 về giới
        hạn domain không so sánh được hai field với nhau trên cùng bản ghi)."""
        user = employee.sudo().user_id
        if not user:
            raise UserError(f"Nhân viên {employee.name} chưa gắn tài khoản người dùng, không lấy được số liệu.")
        # Chuỗi giữ chỗ luôn dùng mốc kỳ datetime UTC (khớp _period_bounds); field ngày tự khai báo
        # qua date_field_id thì tự chọn bounds đúng kiểu Date/Datetime của chính field đó bên dưới.
        placeholder_start, placeholder_end = self._period_bounds(date_from, date_to)
        Model = self.env[metric.source_model_id.model].sudo()

        def _domain(expr):
            domain = parse_metric_domain(expr)
            domain = substitute_domain_placeholders(domain, user.id, placeholder_start, placeholder_end)
            if metric.user_field_id:
                domain = domain + [(metric.user_field_id.name, "=", user.id)]
            if metric.date_field_id:
                start, end = self._domain_field_bounds(metric.date_field_id, date_from, date_to)
                domain = domain + [(metric.date_field_id.name, ">=", start), (metric.date_field_id.name, "<", end)]
            return domain

        if metric.aggregation == "count":
            count = Model.search_count(_domain(metric.numerator_domain))
            return count, count
        if metric.aggregation in ("sum", "avg"):
            records = Model.search(_domain(metric.numerator_domain))
            values = records.mapped(metric.value_field_id.name)
            total = sum(values)
            if metric.aggregation == "avg":
                return (total / len(values) if values else 0.0), len(records)
            return total, len(records)
        if metric.aggregation == "ratio":
            denominator = Model.search_count(_domain(metric.denominator_domain))
            numerator = Model.search_count(_domain(metric.numerator_domain))
            return self._ratio(numerator, denominator), denominator
        raise UserError(f"Chỉ số \"{metric.name}\": chưa chọn phép tính hợp lệ.")

    @api.model
    def _domain_field_bounds(self, date_field, date_from, date_to):
        """Bước 0 (rà soát sau Bước 1): field Date thì lọc bằng chính kiểu Date (>= đầu kỳ, <
        đầu kỳ sau) — so Date với Datetime UTC có thể lệch múi giờ ở đúng ngày biên. Field
        Datetime thì dùng mốc UTC như các chỉ số Python hiện có (_period_bounds)."""
        if date_field.ttype == "date":
            return date_from, date_to + timedelta(days=1)
        return self._period_bounds(date_from, date_to)

    @api.model
    def _context_for(self, employee, date_from, date_to):
        user = employee.sudo().user_id
        if not user:
            raise UserError(f"Nhân viên {employee.name} chưa gắn tài khoản người dùng, không lấy được số liệu task.")
        start, end = self._period_bounds(date_from, date_to)
        return {
            "user": user, "employee": employee.sudo(), "date_from": date_from, "date_to": date_to,
            "start": start, "end": end, "cache": {},
        }

    @api.model
    def _period_bounds(self, date_from, date_to):
        """Kỳ theo ngày địa phương [date_from, date_to] → khoảng UTC [start, end) để so với Datetime."""
        tz = pytz.timezone(self.env.company.resource_calendar_id.tz or "UTC")
        start = tz.localize(datetime.combine(date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        end = tz.localize(datetime.combine(date_to + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return start, end

    # ---- Truy vấn dùng chung ----

    def _tasks(self, ctx, domain):
        return self.env["project.task"].sudo().search([("user_ids", "in", ctx["user"].id)] + domain)

    def _done_tasks(self, ctx):
        """Task của nhân viên hoàn thành trong kỳ (theo date_end)."""
        if "done" not in ctx["cache"]:
            ctx["cache"]["done"] = self._tasks(ctx, [
                ("state", "=", "1_done"),
                ("date_end", ">=", ctx["start"]),
                ("date_end", "<", ctx["end"]),
            ])
        return ctx["cache"]["done"]

    def _story_points(self, ctx):
        return sum(self._done_tasks(ctx).mapped("story_points"))

    def _counted_bugs(self, ctx):
        """Bug tính KPI: kết quả valid/wont_fix và nguyên nhân do code.
        Quy về người được giao và kỳ hoàn thành của task gốc."""
        if "bugs" not in ctx["cache"]:
            ctx["cache"]["bugs"] = self.env["project.task"].sudo().search([
                ("task_type", "=", "bug"),
                ("bug_resolution", "in", BUG_RESOLUTIONS_COUNTED),
                ("bug_root_cause", "=", "code"),
                ("origin_task_id.user_ids", "in", ctx["user"].id),
                ("origin_task_id.state", "=", "1_done"),
                ("origin_task_id.date_end", ">=", ctx["start"]),
                ("origin_task_id.date_end", "<", ctx["end"]),
            ])
        return ctx["cache"]["bugs"]

    # ---- Các chỉ số ----

    def _metric_d1(self, ctx):
        """Hoàn thành đúng hạn: task xong đúng hạn / task có deadline trong kỳ × 100.
        Task chưa xong mà đã quá hạn tính là trễ; chưa tới hạn thì chưa xét. Bỏ qua task huỷ."""
        now = fields.Datetime.now()
        tasks = self._tasks(ctx, [
            ("date_deadline", ">=", ctx["start"]),
            ("date_deadline", "<", ctx["end"]),
            ("state", "!=", "1_canceled"),
        ]).filtered(lambda t: t.state == "1_done" or t.date_deadline < now)
        on_time = tasks.filtered(lambda t: t.state == "1_done" and t.days_late == 0)
        return self._ratio(len(on_time), len(tasks)), len(tasks)

    def _metric_d2(self, ctx):
        """Story point hoàn thành trong kỳ."""
        sp = self._story_points(ctx)
        return sp, sp

    def _metric_d3(self, ctx):
        """Mật độ lỗi: bug tính KPI / SP hoàn thành. Khối lượng = SP hoàn thành."""
        sp = self._story_points(ctx)
        bugs = len(self._counted_bugs(ctx))
        return (bugs / sp if sp else 0.0), sp

    def _metric_d4(self, ctx):
        """Lỗi lọt production: bug production / bug tính KPI × 100. Khối lượng = số bug tính KPI."""
        bugs = self._counted_bugs(ctx)
        production = bugs.filtered("is_production_bug")
        return self._ratio(len(production), len(bugs)), len(bugs)

    def _metric_d5(self, ctx):
        """Pass review lần đầu: task chưa từng bị trả về / task đã qua review × 100."""
        reviewed = self._done_tasks(ctx).filtered(lambda t: t.review_approve_count or t.review_reject_count)
        first_pass = reviewed.filtered(lambda t: not t.review_reject_count)
        return self._ratio(len(first_pass), len(reviewed)), len(reviewed)

    def _metric_d6(self, ctx):
        """Có unit test: task Feature có unit test / task Feature hoàn thành × 100."""
        features = self._done_tasks(ctx).filtered(lambda t: t.task_type == "feature")
        tested = features.filtered("has_unit_test")
        return self._ratio(len(tested), len(features)), len(features)

    def _metric_d7(self, ctx):
        """Thời gian sửa bug nghiêm trọng: trung bình working_hours_close của bug High/Urgent.
        Quy cho người được giao chính bug, theo kỳ hoàn thành của bug."""
        bugs = self._done_tasks(ctx).filtered(lambda t: t.task_type == "bug" and t.priority in HIGH_PRIORITIES)
        hours = bugs.mapped("working_hours_close")
        return (sum(hours) / len(hours) if hours else 0.0), len(bugs)

    def _metric_d8(self, ctx):
        """Chia sẻ kiến thức: số sự kiện gắn nhãn "Chia sẻ kiến thức" do nhân viên tổ chức trong kỳ."""
        event_type = self.env.ref("project_kpi_management.calendar_event_type_knowledge_sharing", raise_if_not_found=False)
        if not event_type:
            return 0.0, 0.0
        count = self.env["calendar.event"].sudo().search_count([
            ("user_id", "=", ctx["user"].id),
            ("categ_ids", "in", event_type.id),
            ("start", ">=", ctx["start"]),
            ("start", "<", ctx["end"]),
        ])
        return count, count

    def _metric_qa4(self, ctx):
        """Bước 2: lỗi lọt production của các dự án tester tham gia = bug production / bug hợp lệ
        (valid, wont_fix) trong các dự án đó, tính theo ngày tạo bug trong kỳ. "Dự án tham gia" là
        dự án tester đã log ít nhất 1 bug trong kỳ. Khối lượng = số dự án tham gia. Cần hàm Python
        vì tập dự án suy ra từ chính dữ liệu bug — domain một bước không diễn đạt được."""
        Task = self.env["project.task"].sudo()
        in_period = [("task_type", "=", "bug"), ("create_date", ">=", ctx["start"]), ("create_date", "<", ctx["end"])]
        projects = Task.search(in_period + [("bug_reporter_id", "=", ctx["user"].id)]).project_id
        if not projects:
            return 0.0, 0
        bugs = Task.search(in_period + [
            ("project_id", "in", projects.ids), ("bug_resolution", "in", BUG_RESOLUTIONS_COUNTED),
        ])
        return self._ratio(len(bugs.filtered("is_production_bug")), len(bugs)), len(projects)

    def _metric_b2(self, ctx):
        """Bước 5 (B2): mật độ bug do yêu cầu sai của BA = bug có bug_root_cause = requirement, kết quả valid/wont_fix,
        truy ngược origin_task_id → requirement_id → BA (user_ids của yêu cầu), chia cho số yêu cầu BA hoàn thành trong
        kỳ. Quy kỳ theo ngày hoàn thành của yêu cầu, giống D3 quy theo task gốc. Khối lượng = số yêu cầu hoàn thành.
        Cùng một bug đã bị loại khỏi D3/D4 của Developer (chỉ tính nguyên nhân "code") — trách nhiệm quy đúng người."""
        Task = self.env["project.task"].sudo()
        requirements = self._tasks(ctx, [
            ("task_type", "=", "requirement"), ("state", "=", "1_done"),
            ("date_end", ">=", ctx["start"]), ("date_end", "<", ctx["end"]),
        ])
        if not requirements:
            return 0.0, 0
        bugs = Task.search_count([
            ("task_type", "=", "bug"), ("bug_root_cause", "=", "requirement"),
            ("bug_resolution", "in", BUG_RESOLUTIONS_COUNTED),
            ("origin_task_id.requirement_id", "in", requirements.ids),
        ])
        return bugs / len(requirements), len(requirements)

    def _metric_p2(self, ctx):
        """Bước 4 (P2): điểm KPI trung bình của cấp dưới trực tiếp, chỉ lấy phiếu đã Gửi hoặc Đã duyệt
        (điểm cuối) VÀ đủ dữ liệu (insufficient_data = False), có kỳ NẰM TRỌN trong kỳ của người này (Đợt B1: PM theo
        quý lấy các phiếu theo tháng trong quý; cùng loại kỳ thì chính là cùng kỳ như trước; kỳ cấp dưới dài hơn kỳ
        của PM không nằm trọn nên không tính). Giá trị = trung bình các trung bình theo từng người; khối lượng = số cấp
        dưới có ít nhất một phiếu hợp lệ. Phiếu chưa chốt hoặc thiếu dữ liệu (ví dụ nhân viên
        mới) bị bỏ cả ở giá trị lẫn khối lượng: điểm của phiếu thiếu dữ liệu chỉ tính trên phần nhỏ chỉ số áp
        dụng, không phản ánh hiệu suất, nên không được kéo điểm của quản lý xuống. Ít phiếu hơn min_volume thì
        "Không áp dụng", không ra số sai; không cần ép thứ tự tạo phiếu trong wizard, và không tính phiếu của chính
        người này nên không có vòng lặp. Khối lượng = số phiếu hợp lệ."""
        subordinates = self.env["hr.employee"].sudo().search([("parent_id", "=", ctx["employee"].id)])
        evaluations = self.env["kpi.evaluation"].sudo().search([
            ("employee_id", "in", subordinates.ids), ("state", "in", ("submitted", "approved")),
            ("insufficient_data", "=", False),
            ("period_id.date_from", ">=", ctx["date_from"]), ("period_id.date_to", "<=", ctx["date_to"]),
        ])
        # Trung bình theo từng người trước, rồi mới giữa các người: nếu gộp chung mọi phiếu, người làm đủ 3 tháng
        # của một quý sẽ có trọng số gấp 3 người mới vào giữa quý.
        per_person = []
        for employee in evaluations.employee_id:
            scores = evaluations.filtered(lambda e: e.employee_id == employee).mapped("final_score")
            per_person.append(sum(scores) / len(scores))
        if not per_person:
            return 0.0, 0
        return sum(per_person) / len(per_person), len(per_person)

    def _metric_p3(self, ctx):
        """Bước 4 (P3), theo kỳ từ Đợt A4: chất lượng dữ liệu của các dự án do người này quản lý (project.user_id),
        chỉ xét bản ghi THUỘC KỲ — Feature xong có date_end trong kỳ (sạch nếu có story point) và bug tạo trong kỳ
        (sạch nếu có task gốc; sạch nếu đủ phân loại: mỗi bug xét hai tiêu chí). Tỷ lệ = tiêu chí sạch / tổng tiêu chí,
        nên mở lại và tính lại phiếu của kỳ cũ cho cùng kết quả dù dữ liệu kỳ khác được dọn sau đó. Không còn tiêu chí
        "task xong thiếu ngày hoàn thành": task thiếu date_end không xác định được thuộc kỳ nào — lỗi đó vẫn có trong
        báo cáo Kiểm tra dữ liệu. Khối lượng = tổng số tiêu chí xét."""
        Task = self.env["project.task"].sudo()
        projects = self.env["project.project"].sudo().search([("user_id", "=", ctx["user"].id)])
        in_projects = [("project_id", "in", projects.ids)]
        features = Task.search(in_projects + [
            ("task_type", "=", "feature"), ("state", "=", "1_done"),
            ("date_end", ">=", ctx["start"]), ("date_end", "<", ctx["end"]),
        ])
        bugs = Task.search(in_projects + [
            ("task_type", "=", "bug"), ("create_date", ">=", ctx["start"]), ("create_date", "<", ctx["end"]),
        ])
        total = len(features) + 2 * len(bugs)
        clean = (
            len(features.filtered("story_points"))
            + len(bugs.filtered("origin_task_id"))
            + len(bugs.filtered(lambda b: b.bug_resolution and b.bug_root_cause))
        )
        return self._ratio(clean, total), total

    @staticmethod
    def _ratio(part, total):
        return part / total * 100 if total else 0.0
