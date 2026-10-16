"""Bước 2: chạy SAU khi nạp dữ liệu của bản mới, đúng một lần khi nâng từ bản cũ (không chạy lại ở các lần
-u sau, nên không hoàn tác được lựa chọn của Admin). Gồm: đổi mã chỉ số T4-T8 → QA1-QA5, bù bug_reporter_id
cho bug cũ, chuyển chức danh Tester sang bộ "Tester (tự động)"."""
from odoo import SUPERUSER_ID, api

CODE_RENAMES = {f"kpi_metric_qa{n - 3}": (f"T{n}", f"QA{n - 3}") for n in range(4, 9)}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, (old_code, new_code) in CODE_RENAMES.items():
        metric = env.ref(f"project_kpi_management.{xmlid}", raise_if_not_found=False)
        if metric and metric.code == old_code:
            metric.code = new_code
    env["project.task"]._migrate_bug_reporter_id()
    env["hr.job"]._migrate_tester_template()
