#!/usr/bin/env bash
# Sao lưu database + filestore của kpi_defense vào backups/ (thư mục không đưa vào Git).
# Dùng từ thư mục gốc repo:  bash addons/project_kpi_management/scripts/backup_defense.sh clean
# Nên sao lưu "clean" khi database ở trạng thái sạch (chưa có phiếu của kỳ mẫu), và khôi phục sau mỗi lần tổng duyệt.
set -euo pipefail
NAME="${1:?Cách dùng: backup_defense.sh <tên bản sao lưu, ví dụ clean>}"
FS=/var/lib/odoo/.local/share/Odoo/filestore   # data_dir mặc định của image odoo:19.0
export MSYS_NO_PATHCONV=1
mkdir -p backups
docker exec odoo19-db pg_dump -U odoo -Fc kpi_defense > "backups/kpi_defense_${NAME}.dump"
docker exec odoo19-web tar -czf - -C "$FS" kpi_defense > "backups/kpi_defense_${NAME}_filestore.tgz"
ls -la "backups/kpi_defense_${NAME}".dump "backups/kpi_defense_${NAME}_filestore.tgz"
