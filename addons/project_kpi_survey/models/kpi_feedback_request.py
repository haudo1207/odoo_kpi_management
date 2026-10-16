from odoo import api, fields, models
from odoo.exceptions import AccessError

ACT_FEEDBACK_XMLID = "project_kpi_survey.mail_activity_type_feedback"
# Dưới ngưỡng này không hiện điểm trung bình và F1 "Không áp dụng": với 1-2 câu trả lời, người quản lý đoán được ai chấm bao nhiêu.
FEEDBACK_MIN_RESPONSES = 3


class KpiFeedbackRequest(models.Model):
    """Lời mời đánh giá 360: một dòng cho mỗi người được mời trên một phiếu. Chỉ lưu AI được mời và đã trả lời xong chưa;
    điểm nằm ở survey.user_input (chỉ nhóm Surveys đọc được), phiếu chỉ hiện số người đã trả lời và điểm trung bình."""

    _name = "kpi.feedback.request"
    _description = "Lời mời đánh giá 360 độ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "evaluation_id, id"

    evaluation_id = fields.Many2one("kpi.evaluation", string="Phiếu", required=True, ondelete="cascade", index=True)
    employee_id = fields.Many2one(related="evaluation_id.employee_id", string="Nhân viên được đánh giá", store=True)
    reviewer_id = fields.Many2one("res.users", string="Người đánh giá", required=True, index=True)
    survey_id = fields.Many2one("survey.survey", string="Khảo sát", required=True, readonly=True)
    user_input_id = fields.Many2one("survey.user_input", string="Câu trả lời", readonly=True, ondelete="set null", copy=False)
    state = fields.Selection(
        [("pending", "Chưa hoàn thành"), ("done", "Đã trả lời")], string="Trạng thái",
        compute="_compute_state", store=True, compute_sudo=True,
    )

    _reviewer_unique = models.Constraint(
        "UNIQUE(evaluation_id, reviewer_id)", "Người này đã được mời đánh giá phiếu này."
    )

    @api.depends("user_input_id.state")
    def _compute_state(self):
        for request in self:
            request.state = "done" if request.user_input_id.state == "done" else "pending"

    def _survey_url(self):
        self.ensure_one()
        return self.user_input_id.sudo().get_start_url()

    def action_open_survey(self):
        """Người được mời mở đúng khảo sát của mình (link có mã câu trả lời riêng)."""
        self.ensure_one()
        if self.env.user != self.reviewer_id:
            raise AccessError("Chỉ người được mời mới mở được khảo sát này.")
        return {"type": "ir.actions.act_url", "url": self._survey_url(), "target": "self"}

    def _schedule_reminder(self):
        """Nhắc việc cho từng người được mời kèm link khảo sát: không cần máy chủ email, dùng lại cơ chế nhắc việc."""
        for request in self:
            url = f"{request.get_base_url()}{request._survey_url()}"
            request.sudo().activity_schedule(
                act_type_xmlid=ACT_FEEDBACK_XMLID, user_id=request.reviewer_id.id,
                summary=f"Đánh giá 360 cho {request.employee_id.name}",
                note=f'Hãy hoàn thành khảo sát: <a href="{url}">Mở khảo sát</a>',
            )

    def _close_reminder(self):
        act_type = self.env.ref(ACT_FEEDBACK_XMLID, raise_if_not_found=False)
        for request in self.sudo():
            activities = request.activity_ids.filtered(lambda a: a.activity_type_id == act_type)
            if activities:
                activities.action_feedback(feedback="Đã hoàn thành khảo sát 360.")
