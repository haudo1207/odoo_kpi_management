from odoo import fields, models

from .kpi_feedback_request import FEEDBACK_MIN_RESPONSES


class KpiEvaluation(models.Model):
    _inherit = "kpi.evaluation"

    feedback_request_ids = fields.One2many("kpi.feedback.request", "evaluation_id", string="Lời mời đánh giá 360")
    feedback_invited_count = fields.Integer("Đã mời", compute="_compute_feedback")
    feedback_done_count = fields.Integer("Đã trả lời", compute="_compute_feedback")
    feedback_avg_score = fields.Float("Điểm 360 trung bình (%)", compute="_compute_feedback", digits=(16, 2))
    feedback_score_visible = fields.Boolean(compute="_compute_feedback")

    def _feedback_valid_inputs(self):
        """Câu trả lời đã hoàn thành, bỏ bản test. Đọc bằng sudo vì survey.user_input không cấp quyền đọc cho quản lý KPI."""
        self.ensure_one()
        inputs = self.sudo().feedback_request_ids.user_input_id
        return inputs.filtered(lambda i: i.state == "done" and not i.test_entry)

    def _compute_feedback(self):
        """Chỉ hiện SỐ người đã trả lời và điểm trung bình (khi đủ ngưỡng) — không hiện ai chấm bao nhiêu."""
        for ev in self:
            inputs = ev._feedback_valid_inputs()
            ev.feedback_invited_count = len(ev.sudo().feedback_request_ids)
            ev.feedback_done_count = len(inputs)
            ev.feedback_score_visible = len(inputs) >= FEEDBACK_MIN_RESPONSES
            ev.feedback_avg_score = (
                sum(inputs.mapped("scoring_percentage")) / len(inputs) if ev.feedback_score_visible else 0.0
            )

    def action_open_feedback_invite(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": "Mời đánh giá 360", "res_model": "kpi.feedback.invite.wizard",
            "view_mode": "form", "target": "new", "context": {"default_evaluation_id": self.id},
        }
