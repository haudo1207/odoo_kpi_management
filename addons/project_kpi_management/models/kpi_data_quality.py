from odoo import fields, models, tools


class KpiDataQualityReport(models.Model):
    """Chỉ số kiểm tra dữ liệu theo dự án (không tính điểm).
    KPI chỉ đáng tin khi task, bug được nhập đủ: báo cáo này chỉ ra dự án nào đang thiếu."""

    _name = "kpi.data.quality.report"
    _description = "Kiểm tra dữ liệu KPI"
    _auto = False  # SQL view, không có bảng thật
    _order = "bug_without_origin desc, done_without_date_end desc"

    project_id = fields.Many2one("project.project", string="Dự án", readonly=True)
    company_id = fields.Many2one("res.company", string="Công ty", readonly=True)
    done_feature_count = fields.Integer("Task Feature đã xong", readonly=True)
    done_without_sp = fields.Integer("Feature xong thiếu story point", readonly=True)
    done_count = fields.Integer("Task đã xong", readonly=True)
    done_without_date_end = fields.Integer("Task xong thiếu ngày hoàn thành", readonly=True)
    bug_count = fields.Integer("Bug", readonly=True)
    bug_without_origin = fields.Integer("Bug thiếu task gốc", readonly=True)
    bug_unclassified = fields.Integer("Bug chưa phân loại", readonly=True)
    sp_rate = fields.Float("Tỷ lệ Feature có SP (%)", readonly=True, aggregator=None)
    origin_rate = fields.Float("Tỷ lệ bug có task gốc (%)", readonly=True, aggregator=None)
    classified_rate = fields.Float("Tỷ lệ bug đủ phân loại (%)", readonly=True, aggregator=None)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                WITH counts AS (
                    SELECT
                        p.id AS project_id,
                        p.company_id,
                        COUNT(*) FILTER (WHERE t.state = '1_done' AND t.task_type = 'feature') AS done_feature_count,
                        COUNT(*) FILTER (WHERE t.state = '1_done' AND t.task_type = 'feature'
                                         AND COALESCE(t.story_points, 0) = 0) AS done_without_sp,
                        COUNT(*) FILTER (WHERE t.state = '1_done') AS done_count,
                        COUNT(*) FILTER (WHERE t.state = '1_done' AND t.date_end IS NULL) AS done_without_date_end,
                        COUNT(*) FILTER (WHERE t.task_type = 'bug') AS bug_count,
                        COUNT(*) FILTER (WHERE t.task_type = 'bug' AND t.origin_task_id IS NULL) AS bug_without_origin,
                        COUNT(*) FILTER (WHERE t.task_type = 'bug'
                                         AND (t.bug_resolution IS NULL OR t.bug_root_cause IS NULL)) AS bug_unclassified
                    FROM project_task t
                    JOIN project_project p ON p.id = t.project_id
                    WHERE t.active
                    GROUP BY p.id, p.company_id
                )
                SELECT
                    project_id AS id,
                    *,
                    CASE WHEN done_feature_count > 0
                         THEN 100.0 * (done_feature_count - done_without_sp) / done_feature_count END AS sp_rate,
                    CASE WHEN bug_count > 0
                         THEN 100.0 * (bug_count - bug_without_origin) / bug_count END AS origin_rate,
                    CASE WHEN bug_count > 0
                         THEN 100.0 * (bug_count - bug_unclassified) / bug_count END AS classified_rate
                FROM counts
            )
        """)
