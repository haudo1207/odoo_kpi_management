from odoo import api, models

from .kpi_feedback_request import FEEDBACK_MIN_RESPONSES


class KpiEngine(models.AbstractModel):
    _inherit = "kpi.engine"

    @api.model
    def _metric_f1(self, ctx):
        """Đợt D1 (F1): điểm trung bình (scoring_percentage, % trên tối đa) của các câu trả lời 360 đã hoàn thành của
        CHÍNH phiếu đang tính, bỏ bản test. Khối lượng = số câu trả lời hoàn thành. Dưới ngưỡng tối thiểu thì trả về
        giá trị 0 để dòng phiếu không lộ điểm của một hai người (min_volume trên bộ KPI làm dòng "Không áp dụng").
        Phiếu đã gửi thì không tính lại nên câu trả lời đến sau không đổi điểm."""
        evaluation = ctx.get("evaluation")
        if not evaluation:
            return 0.0, 0  # không gắn với phiếu nào (ví dụ nút Thử tính của chỉ số)
        inputs = evaluation._feedback_valid_inputs()
        if len(inputs) < FEEDBACK_MIN_RESPONSES:
            return 0.0, len(inputs)
        return sum(inputs.mapped("scoring_percentage")) / len(inputs), len(inputs)
