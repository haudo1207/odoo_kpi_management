from odoo import fields, models
from odoo.exceptions import AccessError, UserError


class KpiAcknowledgeWizard(models.TransientModel):
    """Đợt A2: nhân viên xác nhận kết quả sau khi phiếu Đã duyệt — đồng ý hoặc có ý kiến. Không thêm trạng thái nên
    không đụng khoá phiếu/quyền/nhắc việc của quy trình; cùng cách làm với wizard Tự đánh giá (kiểm đúng người, đúng
    trạng thái rồi mới ghi bằng sudo(), không nới quyền ghi)."""

    _name = "kpi.acknowledge.wizard"
    _description = "Nhân viên xác nhận kết quả KPI"

    evaluation_id = fields.Many2one("kpi.evaluation", string="Phiếu", required=True)
    decision = fields.Selection([("agree", "Đồng ý với kết quả"), ("disagree", "Có ý kiến")], string="Xác nhận", required=True)
    comment = fields.Text("Nội dung")

    def action_confirm(self):
        self.ensure_one()
        ev = self.evaluation_id
        if self.env.user != ev.employee_id.sudo().user_id:
            raise AccessError("Chỉ chính nhân viên trên phiếu mới xác nhận được.")
        if ev.state != "approved":
            raise UserError("Chỉ xác nhận được khi phiếu đã được duyệt.")
        if self.decision == "disagree" and not (self.comment or "").strip():
            raise UserError("Có ý kiến thì bắt buộc ghi nội dung.")
        ev = ev.sudo()
        ev.write({"ack_decision": self.decision, "ack_comment": self.comment, "ack_date": fields.Datetime.now()})
        ev._close_activities("project_kpi_management.mail_activity_type_ack", done=True)
        label = dict(self._fields["decision"].selection)[self.decision]
        ev.message_post(body=f"Nhân viên xác nhận kết quả: {label}." + (f" Nội dung: {self.comment}" if self.comment else ""))
        return {"type": "ir.actions.act_window_close"}
