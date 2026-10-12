from odoo import fields, models


class KpiMetricTestWizard(models.TransientModel):
    """Bước 1 (Chương 9.1): nút "Thử tính" trên form chỉ số — Admin chọn một nhân viên và một
    kỳ, xem ngay kết quả/khối lượng mà không cần tạo phiếu thật, để biết domain mình viết có
    đúng không trước khi dùng cho cả bộ KPI."""

    _name = "kpi.metric.test.wizard"
    _description = "Thử tính chỉ số"

    metric_id = fields.Many2one("kpi.metric", required=True)
    employee_id = fields.Many2one("hr.employee", required=True, string="Nhân viên")
    date_from = fields.Date("Từ ngày", required=True, default=fields.Date.today)
    date_to = fields.Date("Đến ngày", required=True, default=fields.Date.today)
    result_actual = fields.Float("Kết quả (actual)", readonly=True)
    result_volume = fields.Float("Khối lượng (volume)", readonly=True)
    has_result = fields.Boolean(readonly=True)

    def action_test_compute(self):
        self.ensure_one()
        actual, volume = self.env["kpi.engine"].compute_actual(
            self.metric_id, self.employee_id, self.date_from, self.date_to
        )
        self.write({"result_actual": actual, "result_volume": volume, "has_result": True})
        return {
            "type": "ir.actions.act_window",
            "name": "Thử tính chỉ số",
            "res_model": "kpi.metric.test.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
