from odoo import api, fields, models


class ProjectMilestone(models.Model):
    _inherit = "project.milestone"

    is_reached_on_time = fields.Boolean(
        "Đạt đúng hạn", compute="_compute_is_reached_on_time", store=True,
        help="Bước 4 (P1): đã đạt và ngày đạt (reached_date) không muộn hơn deadline. Milestone không có "
             "deadline thì không bao giờ là đúng hạn nên cũng không vào mẫu số của P1 (lọc theo deadline).",
    )

    @api.depends("is_reached", "reached_date", "deadline")
    def _compute_is_reached_on_time(self):
        for milestone in self:
            milestone.is_reached_on_time = bool(
                milestone.is_reached and milestone.reached_date and milestone.deadline
                and milestone.reached_date <= milestone.deadline
            )
