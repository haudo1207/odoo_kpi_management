from odoo import fields, models
from odoo.exceptions import UserError


class KpiEvaluationGenerateWizard(models.TransientModel):
    _name = "kpi.evaluation.generate.wizard"
    _description = "Tạo phiếu KPI hàng loạt cho một kỳ"

    period_id = fields.Many2one("kpi.period", string="Kỳ đánh giá", required=True, domain=[("state", "=", "open")])
    department_ids = fields.Many2many("hr.department", string="Phòng ban",
                                      help="Để trống: tất cả phòng ban. Có chọn: gồm cả phòng ban con.")
    compute = fields.Boolean("Tính KPI ngay", default=True)
    preview_count = fields.Integer("Số phiếu sẽ tạo", compute="_compute_preview_count")

    def _compute_preview_count(self):
        for wizard in self:
            if not wizard.period_id:
                wizard.preview_count = 0
                continue
            existing = self.env["kpi.evaluation"].sudo().search([("period_id", "=", wizard.period_id.id)]).employee_id
            wizard.preview_count = len(wizard.period_id._eligible_employees(wizard.department_ids) - existing)

    def action_generate(self):
        self.ensure_one()
        if self.period_id.state != "open":
            raise UserError("Chỉ tạo phiếu cho kỳ đang mở.")
        evaluations = self.period_id._generate_evaluations(self.department_ids, compute=self.compute)
        if not evaluations:
            raise UserError("Không có nhân viên nào cần tạo phiếu: đã có phiếu, chưa có tài khoản, chức danh chưa gắn bộ KPI, hoặc bộ KPI khác loại kỳ với kỳ này.")
        return {
            "type": "ir.actions.act_window",
            "name": f"Phiếu vừa tạo — {self.period_id.name}",
            "res_model": "kpi.evaluation",
            "view_mode": "list,form",
            "domain": [("id", "in", evaluations.ids)],
        }
