from odoo import models


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def _mark_done(self):
        """Người được mời nộp bài xong thì nhắc việc "Đánh giá 360" tự đánh dấu xong (cùng đường mà controller khảo sát gọi)."""
        res = super()._mark_done()
        self.env["kpi.feedback.request"].sudo().search([("user_input_id", "in", self.ids)])._close_reminder()
        return res
