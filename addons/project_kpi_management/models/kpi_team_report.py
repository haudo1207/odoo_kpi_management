from odoo import fields, models, tools


class KpiTeamReport(models.Model):
    """Chỉ số cấp team (Mục 5): team = dự án, cùng cách làm với kpi.data.quality.report.
    Chỉ đọc, không tính điểm cá nhân — dùng để phát hiện vấn đề nằm ở quy trình/dự án
    thay vì chỉ nhìn từng người."""

    _name = "kpi.team.report"
    _description = "Chỉ số KPI theo dự án"
    _auto = False
    _order = "production_bug_rate desc, on_time_rate"

    project_id = fields.Many2one("project.project", string="Dự án", readonly=True)
    company_id = fields.Many2one("res.company", string="Công ty", readonly=True)
    feature_done_count = fields.Integer("Feature đã xong", readonly=True)
    feature_on_time_count = fields.Integer("Feature đúng hạn", readonly=True)
    on_time_rate = fields.Float("Tỷ lệ đúng hạn (%)", readonly=True, aggregator=None)
    bug_count = fields.Integer("Bug", readonly=True)
    bug_density = fields.Float("Mật độ lỗi (bug/feature)", readonly=True, aggregator=None)
    production_bug_count = fields.Integer("Lỗi lọt production", readonly=True)
    production_bug_rate = fields.Float("Tỷ lệ lỗi lọt production (%)", readonly=True, aggregator=None)
    avg_bug_fix_hours = fields.Float("Giờ sửa bug trung bình", readonly=True, aggregator=None)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                WITH based AS (
                    -- Bug được quy về dự án của task gốc (giống quy ước D3/D4 ở kpi_engine.py:
                    -- "quy về người được giao và kỳ hoàn thành của task gốc"); bug không có task
                    -- gốc (bug_without_origin, xem kpi.data.quality.report) thì giữ dự án của chính nó.
                    SELECT
                        t.id,
                        t.task_type,
                        t.state,
                        t.days_late,
                        t.is_production_bug,
                        t.bug_resolution,
                        t.date_end,
                        t.create_date,
                        CASE WHEN t.task_type = 'bug' THEN COALESCE(o.project_id, t.project_id)
                             ELSE t.project_id END AS report_project_id
                    FROM project_task t
                    LEFT JOIN project_task o ON o.id = t.origin_task_id
                    WHERE t.active
                ),
                counts AS (
                    SELECT
                        p.id AS project_id,
                        p.company_id,
                        COUNT(*) FILTER (WHERE b.task_type = 'feature' AND b.state = '1_done') AS feature_done_count,
                        COUNT(*) FILTER (WHERE b.task_type = 'feature' AND b.state = '1_done'
                                         AND b.days_late = 0) AS feature_on_time_count,
                        COUNT(*) FILTER (WHERE b.task_type = 'bug') AS bug_count,
                        COUNT(*) FILTER (WHERE b.task_type = 'bug' AND b.is_production_bug) AS production_bug_count,
                        AVG(EXTRACT(EPOCH FROM (b.date_end - b.create_date)) / 3600.0)
                            FILTER (WHERE b.task_type = 'bug' AND b.bug_resolution = 'valid'
                                    AND b.state = '1_done' AND b.date_end IS NOT NULL) AS avg_bug_fix_hours
                    FROM based b
                    JOIN project_project p ON p.id = b.report_project_id
                    GROUP BY p.id, p.company_id
                )
                SELECT
                    project_id AS id,
                    *,
                    CASE WHEN feature_done_count > 0
                         THEN 100.0 * feature_on_time_count / feature_done_count END AS on_time_rate,
                    CASE WHEN feature_done_count > 0
                         THEN 1.0 * bug_count / feature_done_count END AS bug_density,
                    CASE WHEN bug_count > 0
                         THEN 100.0 * production_bug_count / bug_count END AS production_bug_rate
                FROM counts
            )
        """)
