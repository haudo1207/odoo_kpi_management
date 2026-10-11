from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    kpi_evaluation_count = fields.Integer("Phiếu KPI", compute="_compute_kpi_evaluation_count")

    def _compute_kpi_evaluation_count(self):
        # Đếm theo quyền của người xem: nhân viên chỉ thấy phiếu của mình, quản lý thấy phiếu của nhóm
        counts = dict(self.env["kpi.evaluation"]._read_group(
            [("employee_id", "in", self.ids)], ["employee_id"], ["__count"]
        ))
        for employee in self:
            employee.kpi_evaluation_count = counts.get(employee, 0)

    def action_view_kpi_evaluations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Phiếu KPI — {self.name}",
            "res_model": "kpi.evaluation",
            "view_mode": "list,form,graph",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }
