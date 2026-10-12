from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class KpiSelfAssessmentWizard(models.TransientModel):
    """Mục 6: nhân viên tự đánh giá — chỉ tham khảo, không cộng vào điểm, không thêm trạng thái.
    Nhân viên chỉ có quyền đọc trên kpi.evaluation/kpi.evaluation.line, nên wizard tự kiểm tra
    đúng người + đúng trạng thái Nháp rồi mới ghi bằng sudo(), không nới record rule."""

    _name = "kpi.self.assessment.wizard"
    _description = "Nhân viên tự đánh giá"

    evaluation_id = fields.Many2one("kpi.evaluation", string="Phiếu", required=True)
    employee_comment = fields.Text("Nhận xét của nhân viên")
    line_ids = fields.One2many("kpi.self.assessment.wizard.line", "wizard_id", string="Tự chấm")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ev = self.env["kpi.evaluation"].browse(res.get("evaluation_id"))
        if ev:
            res["employee_comment"] = ev.employee_comment
            res["line_ids"] = [
                (0, 0, {"evaluation_line_id": line.id, "self_score": line.self_score})
                for line in ev.line_ids.filtered(lambda l: l.compute_mode == "manual")
            ]
        return res

    def _check_allowed(self):
        self.ensure_one()
        ev = self.evaluation_id
        if self.env.user != ev.employee_id.sudo().user_id:
            raise AccessError("Chỉ chính nhân viên trên phiếu mới tự đánh giá được.")
        if ev.state != "draft":
            raise UserError("Chỉ tự đánh giá được khi phiếu ở trạng thái Nháp.")

    def action_confirm(self):
        self.ensure_one()
        self._check_allowed()
        self.evaluation_id.sudo().write({"employee_comment": self.employee_comment})
        for line in self.line_ids:
            line.evaluation_line_id.sudo().write({"self_score": line.self_score})
        return {"type": "ir.actions.act_window_close"}


class KpiSelfAssessmentWizardLine(models.TransientModel):
    _name = "kpi.self.assessment.wizard.line"
    _description = "Dòng tự chấm trong wizard Tự đánh giá"

    wizard_id = fields.Many2one("kpi.self.assessment.wizard", required=True, ondelete="cascade")
    evaluation_line_id = fields.Many2one("kpi.evaluation.line", string="Chỉ số", required=True, readonly=True)
    metric_id = fields.Many2one(related="evaluation_line_id.metric_id", string="Chỉ số", readonly=True)
    target = fields.Float(related="evaluation_line_id.target", readonly=True)
    self_score = fields.Float("Tự chấm")
