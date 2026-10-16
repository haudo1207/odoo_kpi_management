"""Bước 2 (đổi mã bộ Tester T4-T8 thành QA1-QA5): chạy TRƯỚC khi nạp dữ liệu của bản mới, để dữ liệu XML
nhận ra các bản ghi cũ theo xmlid mới thay vì tạo bản ghi trùng. Chỉ chạy một lần, khi nâng từ bản cũ."""

XMLID_RENAMES = {f"kpi_metric_t{n}": f"kpi_metric_qa{n - 3}" for n in range(4, 9)}


def migrate(cr, version):
    for old, new in XMLID_RENAMES.items():
        cr.execute(
            "UPDATE ir_model_data SET name = %s WHERE module = 'project_kpi_management' AND name = %s "
            "AND NOT EXISTS (SELECT 1 FROM ir_model_data WHERE module = 'project_kpi_management' AND name = %s)",
            (new, old, new),
        )
