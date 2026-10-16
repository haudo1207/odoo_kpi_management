from odoo import api, models


class KpiEngine(models.AbstractModel):
    _inherit = "kpi.engine"

    @api.model
    def _metric_p4(self, ctx):
        """Bước 4 (P4): độ lệch giờ làm so với kế hoạch của các dự án Lead quản lý (project.user_id) có khai báo
        giờ kế hoạch (allocated_hours > 0): |giờ thực tế / giờ kế hoạch − 1| × 100. Chiều "Thấp tốt", nên engine
        không cần thêm chiều "gần 100% tốt": lệch ít là tốt, cả vượt lẫn thiếu giờ đều bị phạt.
        Giờ thực tế = tổng timesheet tới hết kỳ (giờ kế hoạch là của cả dự án, không chia theo kỳ). Khối lượng =
        số dự án có giờ kế hoạch."""
        projects = self.env["project.project"].sudo().search([
            ("user_id", "=", ctx["user"].id), ("allocated_hours", ">", 0),
        ])
        if not projects:
            return 0.0, 0
        self.env["account.analytic.line"].flush_model()
        lines = self.env["account.analytic.line"].sudo().search([
            ("project_id", "in", projects.ids), ("date", "<=", ctx["date_to"]),
        ])
        planned = sum(projects.mapped("allocated_hours"))
        actual = sum(lines.mapped("unit_amount"))
        return abs(actual / planned - 1) * 100, len(projects)
