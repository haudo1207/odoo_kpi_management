import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    task_type = fields.Selection(
        [("feature", "Feature"), ("bug", "Bug"), ("requirement", "Yêu cầu")],
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
    review_approve_count = fields.Integer(
        "Số lần được duyệt", readonly=True, copy=False,
        help="Task có số lần được duyệt hoặc bị trả về > 0 là task đã qua review (mẫu số của D5).",
    )
    has_unit_test = fields.Boolean("Có unit test", tracking=True)
    kpi_can_review = fields.Boolean(compute="_compute_kpi_can_review")

    # T1-T3 (Bước 2, Chương 9.2): người phát hiện bug, dùng để quy T1-T3 đúng người — KHÔNG dùng
    # create_uid vì PM có thể log bug hộ tester, hoặc bug được import, nên create_uid có thể sai.
    bug_reporter_id = fields.Many2one(
        "res.users", string="Người phát hiện bug", default=lambda self: self.env.user,
        help="Mặc định là người tạo task. Chỉ KPI Manager trở lên sửa được, để tránh tự gán bug "
             "người khác log về mình nhằm tăng QA1 (số bug hợp lệ tìm được).",
    )

    # Bước 5 (BA): task Feature trỏ về yêu cầu gốc; người phụ trách yêu cầu (user_ids của task Requirement) là BA
    requirement_id = fields.Many2one(
        "project.task", string="Yêu cầu gốc", index=True, copy=False,
        domain="[('task_type', '=', 'requirement'), ('project_id', '=', project_id)]",
        help="Task Yêu cầu mà Feature này hiện thực, cùng dự án. Bug có nguyên nhân \"Yêu cầu sai\" của Feature "
             "được quy về BA phụ trách yêu cầu này (B2) thay vì Developer (D3, D4).",
    )
    is_on_time = fields.Boolean(
        "Hoàn thành đúng hạn", compute="_compute_is_on_time", store=True,
        help="Task đã xong, có deadline và không trễ ngày nào (cùng quy tắc ngày địa phương với D1: days_late = 0). "
             "Dùng cho chỉ số B1; D1 giữ nguyên cách tính riêng.",
    )

    # D1: số ngày trễ, đo cả khi đã hoàn thành
    days_late = fields.Integer("Số ngày trễ", compute="_compute_days_late", store=True)

    def _compute_kpi_can_review(self):
        can_review = self.env.user.has_group("project_kpi_management.group_kpi_manager")
        for task in self:
            task.kpi_can_review = can_review

    @api.constrains("requirement_id")
    def _check_requirement(self):
        for task in self.filtered("requirement_id"):
            requirement = task.requirement_id
            if requirement == task or requirement.task_type != "requirement":
                raise ValidationError("Yêu cầu gốc phải là một task loại Yêu cầu khác.")
            if requirement.project_id != task.project_id:
                raise ValidationError("Yêu cầu gốc phải cùng dự án với task.")

    @api.depends("state", "days_late", "date_deadline")
    def _compute_is_on_time(self):
        for task in self:
            task.is_on_time = bool(task.state == "1_done" and task.date_deadline and task.days_late == 0)

    @api.constrains("origin_task_id")
    def _check_origin_task(self):
        for task in self:
            if task.origin_task_id == task:
                raise ValidationError("Task gốc không thể là chính nó.")

    def _calc_days_late(self):
        """Giá trị days_late của một task, dùng chung cho compute lẫn cron (so sánh trước khi ghi,
        tránh ghi write_date mỗi ngày cho task mà giá trị không đổi — xem _cron_update_days_late)."""
        self.ensure_one()
        if not self.date_deadline or self.state == "1_canceled":
            return 0
        # Task chưa xong thì so với hôm nay (cron cập nhật hằng ngày)
        now = fields.Datetime.now()
        ref = self.date_end if self.state == "1_done" and self.date_end else now
        tz = pytz.timezone(self.company_id.resource_calendar_id.tz or "UTC")
        ref_day = pytz.utc.localize(ref).astimezone(tz).date()
        deadline_day = pytz.utc.localize(self.date_deadline).astimezone(tz).date()
        return max((ref_day - deadline_day).days, 0)

    @api.depends("date_deadline", "date_end", "state")
    def _compute_days_late(self):
        for task in self:
            task.days_late = task._calc_days_late()

    @api.model
    def _cron_update_days_late(self):
        tasks = self.search([
            ("date_deadline", "<", fields.Datetime.now()),
            ("state", "not in", ["1_done", "1_canceled"]),
        ])
        for task in tasks:
            new_value = task._calc_days_late()
            if new_value != task.days_late:
                task.days_late = new_value

    def _check_kpi_manager_fields(self, vals, fields_checked, message):
        if fields_checked & vals.keys() and not self.env.su and \
                not self.env.user.has_group("project_kpi_management.group_kpi_manager"):
            raise AccessError(message)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_kpi_manager_fields(vals, {"has_unit_test"}, "Chỉ quản lý KPI được xác nhận task có unit test.")
            self._check_kpi_manager_fields(
                vals, {"bug_reporter_id"}, "Chỉ quản lý KPI được xác nhận người phát hiện bug."
            )
        tasks = super().create(vals_list)
        tasks._ensure_date_end()
        return tasks

    def write(self, vals):
        # D6: has_unit_test là căn cứ chấm điểm, chỉ quản lý KPI được xác nhận
        self._check_kpi_manager_fields(vals, {"has_unit_test"}, "Chỉ quản lý KPI được xác nhận task có unit test.")
        # T1-T3: bug_reporter_id là căn cứ chấm điểm, chỉ quản lý KPI được sửa (xem field ở trên)
        self._check_kpi_manager_fields(vals, {"bug_reporter_id"}, "Chỉ quản lý KPI được xác nhận người phát hiện bug.")
        # Lọc trước super(): sau khi ghi thì không còn biết trạng thái cũ
        rejected = approved = self.browse()
        if vals.get("state") == "02_changes_requested":
            rejected = self.filtered(lambda t: t.state != "02_changes_requested")
        elif vals.get("state") == "03_approved":
            approved = self.filtered(lambda t: t.state != "03_approved")
        res = super().write(vals)
        for task in rejected:
            task.review_reject_count += 1
        for task in approved:
            task.review_approve_count += 1
        # Chạy sau super(): Odoo xoá date_end khi task sang stage không fold
        if {"state", "stage_id", "date_end"} & vals.keys():
            self._ensure_date_end()
        return res

    @api.model
    def _migrate_bug_reporter_id(self):
        """Bù dữ liệu cũ (Bước 2): bug tạo trước khi có field này thì gán bug_reporter_id =
        create_uid. Gọi từ migrations/19.0.1.1.0/post-migrate.py (một lần khi nâng cấp); chỉ tìm những
        bug còn thiếu nên chạy lại vẫn an toàn, không ghi đè giá trị đã sửa tay."""
        bugs = self.search([("task_type", "=", "bug"), ("bug_reporter_id", "=", False)])
        for bug in bugs:
            bug.bug_reporter_id = bug.create_uid

    def _ensure_date_end(self):
        """date_end là mốc hoàn thành duy nhất cho D1 và D7 (working_hours_close)."""
        missing = self.filtered(lambda t: t.state == "1_done" and not t.date_end)
        if missing:
            missing.write({"date_end": fields.Datetime.now()})
