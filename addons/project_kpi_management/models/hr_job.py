from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    kpi_template_id = fields.Many2one("kpi.template", string="Bộ KPI", ondelete="restrict")

    @api.model
    def _migrate_tester_template(self):
        """Bước 2: chuyển chức danh Tester sang bộ KPI tự động (QA1-QA5), ẩn bộ cũ toàn chỉ số nhập tay.
        Bản ghi trong kpi_org_data.xml nằm trong noupdate="1" nên sửa XML không đổi được database
        đã cài — hàm này chỉ được gọi từ migrations/19.0.1.1.0/post-migrate.py (MỘT lần khi nâng cấp,
        không phải <function> chạy mỗi lần -u, vì như vậy sẽ hoàn tác lựa chọn của admin về sau).
        Chỉ chuyển khi chức danh còn trỏ về bộ cũ."""
        old = self.env.ref("project_kpi_management.kpi_template_tester", raise_if_not_found=False)
        new = self.env.ref("project_kpi_management.kpi_template_tester_auto", raise_if_not_found=False)
        if not old or not new:
            return
        self.search([("kpi_template_id", "=", old.id)]).write({"kpi_template_id": new.id})
        if old.active:
            old.active = False
        # Chỉ số T1-T3 cũ không còn dùng; không xoá (phiếu cũ có thể còn tham chiếu), chỉ ẩn
        for code in ("kpi_metric_t1", "kpi_metric_t2", "kpi_metric_t3"):
            metric = self.env.ref(f"project_kpi_management.{code}", raise_if_not_found=False)
            if metric and metric.active and not self.env["kpi.template.line"].search_count(
                [("metric_id", "=", metric.id), ("template_id.active", "=", True)]
            ):
                metric.active = False
