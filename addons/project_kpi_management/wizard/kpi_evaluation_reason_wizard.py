from odoo import fields, models
from odoo.exceptions import UserError


class KpiEvaluationReasonWizard(models.TransientModel):
    _name = "kpi.evaluation.reason.wizard"
    _description = "Nhập lý do trả về / mở lại phiếu KPI"

    evaluation_id = fields.Many2one("kpi.evaluation", required=True, ondelete="cascade")
    mode = fields.Selection([("return", "Trả về nháp"), ("reopen", "Mở lại")], required=True)
    reason = fields.Text("Lý do", required=True)

    def action_confirm(self):
        self.ensure_one()
        ev = self.evaluation_id
        ev._check_kpi_admin()
        expected = "submitted" if self.mode == "return" else "approved"
        if ev.state != expected:
            raise UserError("Trạng thái phiếu đã thay đổi, hãy tải lại trang.")
        if not self.reason.strip():
            raise UserError("Bắt buộc ghi lý do.")
        ev.write({"state": "draft"})
        label = dict(self._fields["mode"].selection)[self.mode]
        ev.message_post(body=f"{label}. Lý do: {self.reason}")
        return {"type": "ir.actions.act_window_close"}
