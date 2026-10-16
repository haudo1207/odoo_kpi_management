#!/usr/bin/env bash
# Khôi phục kpi_defense từ backups/ rồi chạy prepare_defense.sh (nạp lại module, khởi động lại, kiểm tra).
# Dùng từ thư mục gốc repo:  bash addons/project_kpi_management/scripts/restore_defense.sh clean
set -euo pipefail
NAME="${1:?Cách dùng: restore_defense.sh <tên bản sao lưu, ví dụ clean>}"
FS=/var/lib/odoo/.local/share/Odoo/filestore   # data_dir mặc định của image odoo:19.0
export MSYS_NO_PATHCONV=1
[ -f "backups/kpi_defense_${NAME}.dump" ] || { echo "Không thấy backups/kpi_defense_${NAME}.dump" >&2; exit 1; }
docker exec odoo19-db dropdb -U odoo --force --if-exists kpi_defense
docker exec odoo19-db createdb -U odoo kpi_defense
docker exec -i odoo19-db pg_restore -U odoo -d kpi_defense --no-owner < "backups/kpi_defense_${NAME}.dump"
docker exec odoo19-web rm -rf "$FS/kpi_defense"
docker exec -i odoo19-web tar -xzf - -C "$FS" < "backups/kpi_defense_${NAME}_filestore.tgz"
bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense
