from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

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
        if metric.compute_mode != "auto":
            return None
        method = getattr(self, f"_metric_{metric.code.lower()}", None)
        if not method:
            raise UserError(f"Chưa có hàm tính cho chỉ số tự động {metric.code}.")
        return method(self._context_for(employee, date_from, date_to))

    @api.model
    def _context_for(self, employee, date_from, date_to):
        user = employee.sudo().user_id
        if not user:
            raise UserError(f"Nhân viên {employee.name} chưa gắn tài khoản người dùng, không lấy được số liệu task.")
        start, end = self._period_bounds(date_from, date_to)
        return {"user": user, "start": start, "end": end, "cache": {}}

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

    @staticmethod
    def _ratio(part, total):
        return part / total * 100 if total else 0.0
