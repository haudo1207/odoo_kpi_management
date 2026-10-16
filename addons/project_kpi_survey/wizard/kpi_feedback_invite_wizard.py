from odoo import api, fields, models
from odoo.exceptions import UserError


class KpiFeedbackInviteWizard(models.TransientModel):
    """Quản lý chọn người đánh giá cho một phiếu Nháp. Tạo câu trả lời riêng cho từng người bằng survey._create_answer(user=...)
    và nhắc việc kèm link — thao tác khảo sát chạy bằng sudo vì quản lý KPI không có quyền Surveys."""

    _name = "kpi.feedback.invite.wizard"
    _description = "Mời đánh giá 360 độ"

    evaluation_id = fields.Many2one("kpi.evaluation", string="Phiếu", required=True)
    survey_id = fields.Many2one("survey.survey", string="Khảo sát", required=True, domain=[("scoring_type", "!=", "no_scoring")])
    reviewer_ids = fields.Many2many(
        "res.users", string="Người đánh giá", domain=[("share", "=", False)],
        help="Người dùng nội bộ, không trùng nhau, không phải chính nhân viên (nhân viên đã có tự đánh giá riêng).",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        survey = self.env.ref("project_kpi_survey.survey_360", raise_if_not_found=False)
        if survey and "survey_id" in fields_list:
            res.setdefault("survey_id", survey.id)
        return res

    def action_invite(self):
        self.ensure_one()
        ev = self.evaluation_id
        ev.check_access("write")  # đúng quản lý của nhân viên (record rule) hoặc Admin
        if ev.state != "draft":
            raise UserError("Chỉ mời đánh giá 360 khi phiếu còn ở trạng thái Nháp: phiếu đã gửi hoặc duyệt đã khoá điểm.")
        if not self.reviewer_ids:
            raise UserError("Hãy chọn ít nhất một người đánh giá.")
        employee_user = ev.employee_id.sudo().user_id
        if employee_user in self.reviewer_ids:
            raise UserError("Không mời chính nhân viên được đánh giá (đã có tự đánh giá riêng).")
        already = ev.sudo().feedback_request_ids.reviewer_id & self.reviewer_ids
        if already:
            raise UserError("Đã mời rồi: %s." % ", ".join(already.mapped("name")))
        survey = self.survey_id.sudo()  # quản lý KPI không có quyền Surveys nên mọi thao tác khảo sát chạy bằng sudo
        if survey.scoring_type == "no_scoring":
            raise UserError("Khảo sát phải bật chấm điểm, nếu không F1 luôn bằng 0.")
        for reviewer in self.reviewer_ids:
            answer = survey._create_answer(user=reviewer, check_attempts=False)
            request = self.env["kpi.feedback.request"].sudo().create({
                "evaluation_id": ev.id, "reviewer_id": reviewer.id, "survey_id": survey.id, "user_input_id": answer.id,
            })
            request._schedule_reminder()
        ev.message_post(body="Đã mời đánh giá 360: %d người." % len(self.reviewer_ids))
        return {"type": "ir.actions.act_window_close"}
