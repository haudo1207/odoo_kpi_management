from odoo import fields, models


class KpiTargetOverride(models.Model):
    _name = "kpi.target.override"
    _description = "Mục tiêu riêng theo nhân viên hoặc phòng ban cho một chỉ số trong bộ KPI"

    template_line_id = fields.Many2one(
        "kpi.template.line", string="Dòng chỉ số", required=True, ondelete="cascade", index=True
    )
    template_id = fields.Many2one(related="template_line_id.template_id", string="Bộ KPI", store=True)
    metric_id = fields.Many2one(related="template_line_id.metric_id", string="Chỉ số", store=True)
    employee_id = fields.Many2one("hr.employee", string="Nhân viên")
    department_id = fields.Many2one("hr.department", string="Phòng ban")
    target = fields.Float("Mục tiêu riêng", digits=(16, 2), required=True)

    _employee_xor_department = models.Constraint(
        "CHECK((employee_id IS NOT NULL AND department_id IS NULL) "
        "OR (employee_id IS NULL AND department_id IS NOT NULL))",
        "Mỗi mục tiêu riêng phải chọn đúng một trong hai: Nhân viên hoặc Phòng ban, không được cả hai hoặc không chọn gì.",
    )
    _template_line_employee_unique = models.Constraint(
        "UNIQUE(template_line_id, employee_id)", "Nhân viên này đã có mục tiêu riêng cho chỉ số này."
    )
    _template_line_department_unique = models.Constraint(
        "UNIQUE(template_line_id, department_id)", "Phòng ban này đã có mục tiêu riêng cho chỉ số này."
    )
