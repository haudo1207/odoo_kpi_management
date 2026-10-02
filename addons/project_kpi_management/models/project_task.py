import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    task_type = fields.Selection(
        [("feature", "Feature"), ("bug", "Bug")],
        string="Loại task",
        default="feature",
        required=True,
        index=True,
        tracking=True,
    )
    story_points = fields.Float("Story point", digits=(16, 1), tracking=True)

    # Thông tin bug: D3, D4
    origin_task_id = fields.Many2one(
        "project.task", string="Task gốc", index=True, domain="[('id', '!=', id)]",
        help="Task sinh ra bug này. Bug được quy về người được giao và kỳ hoàn thành của task gốc.",
    )
    bug_ids = fields.One2many("project.task", "origin_task_id", string="Bug phát sinh")
    is_production_bug = fields.Boolean("Lỗi production", tracking=True)
    bug_resolution = fields.Selection(
        [
            ("valid", "Lỗi thật, cần sửa"),
            ("wont_fix", "Lỗi thật, không sửa"),
            ("duplicate", "Trùng bug khác"),
            ("invalid", "Không phải lỗi"),
        ],
        string="Kết quả xử lý bug",
        tracking=True,
    )
    bug_root_cause = fields.Selection(
        [
            ("code", "Lỗi lập trình"),
            ("requirement", "Yêu cầu sai, thiếu"),
            ("environment", "Môi trường, hạ tầng"),
        ],
        string="Nguyên nhân bug",
        tracking=True,
    )

    # D5, D6
    review_reject_count = fields.Integer("Số lần bị trả về", readonly=True, copy=False)
    has_unit_test = fields.Boolean("Có unit test", tracking=True)

    # D1: số ngày trễ, đo cả khi đã hoàn thành
    days_late = fields.Integer("Số ngày trễ", compute="_compute_days_late", store=True)

    @api.constrains("origin_task_id")
    def _check_origin_task(self):
        for task in self:
            if task.origin_task_id == task:
                raise ValidationError("Task gốc không thể là chính nó.")

    @api.depends("date_deadline", "date_end", "state")
    def _compute_days_late(self):
        now = fields.Datetime.now()
        for task in self:
            if not task.date_deadline or task.state == "1_canceled":
                task.days_late = 0
                continue
            # Task chưa xong thì so với hôm nay (cron cập nhật hằng ngày)
            ref = task.date_end if task.state == "1_done" and task.date_end else now
            tz = pytz.timezone(task.company_id.resource_calendar_id.tz or "UTC")
            ref_day = pytz.utc.localize(ref).astimezone(tz).date()
            deadline_day = pytz.utc.localize(task.date_deadline).astimezone(tz).date()
            task.days_late = max((ref_day - deadline_day).days, 0)

    @api.model
    def _cron_update_days_late(self):
        tasks = self.search([
            ("date_deadline", "<", fields.Datetime.now()),
            ("state", "not in", ["1_done", "1_canceled"]),
        ])
        self.env.add_to_compute(self._fields["days_late"], tasks)
        tasks.flush_recordset(["days_late"])

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._ensure_date_end()
        return tasks

    def write(self, vals):
        rejected = self.browse()
        if vals.get("state") == "02_changes_requested":
            rejected = self.filtered(lambda t: t.state != "02_changes_requested")
        res = super().write(vals)
        for task in rejected:
            task.review_reject_count += 1
        # Chạy sau super(): Odoo xoá date_end khi task sang stage không fold
        if {"state", "stage_id", "date_end"} & vals.keys():
            self._ensure_date_end()
        return res

    def _ensure_date_end(self):
        """date_end là mốc hoàn thành duy nhất cho D1 và D7 (working_hours_close)."""
        missing = self.filtered(lambda t: t.state == "1_done" and not t.date_end)
        if missing:
            missing.write({"date_end": fields.Datetime.now()})
