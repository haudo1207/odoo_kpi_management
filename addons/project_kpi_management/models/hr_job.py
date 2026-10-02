from odoo import fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    kpi_template_id = fields.Many2one("kpi.template", string="Bộ KPI", ondelete="restrict")
