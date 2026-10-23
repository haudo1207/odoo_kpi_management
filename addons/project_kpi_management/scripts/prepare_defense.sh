#!/usr/bin/env bash
# Chuẩn bị buổi bảo vệ trong MỘT lệnh: nạp lại module trên database, khởi động lại container, chờ server sẵn sàng rồi chạy
# pre_defense_check.py. Gói các bước hay bị quên (đã gây lỗi "server chưa nạp code mới" ba lần) thành một script.
#
# Dùng (từ thư mục gốc của repo, đứng trên nhánh main đã `git pull`):
#     bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense
# Tuỳ chọn qua biến môi trường: WEB_CONTAINER (mặc định odoo19-web), DB_CONTAINER (odoo19-db), URL_PORT (8069 trong container).
set -euo pipefail

DB="${1:?Cách dùng: prepare_defense.sh <tên database>, ví dụ kpi_defense}"
WEB="${WEB_CONTAINER:-odoo19-web}"
DBC="${DB_CONTAINER:-odoo19-db}"
SCRIPT="/mnt/extra-addons/project_kpi_management/scripts/pre_defense_check.py"
export MSYS_NO_PATHCONV=1   # Git Bash trên Windows đổi đường dẫn bắt đầu bằng / nếu không đặt biến này

echo "== 1/4  Tìm các module KPI đã cài trong database '$DB'"
MODULES=$(docker exec "$DBC" psql -U odoo -d "$DB" -Atc \
  "select string_agg(name, ',' order by name) from ir_module_module where name like 'project_kpi%' and state = 'installed'")
if [ -z "$MODULES" ]; then
  echo "Database '$DB' chưa cài module KPI nào. Dựng database trước (Chương 5.7 trong Nhom7_BaoCao.md)." >&2
  exit 1
fi
echo "   $MODULES"

echo "== 2/4  Nạp lại module bằng code hiện tại trên đĩa (-u)"
docker exec "$WEB" odoo -d "$DB" -u "$MODULES" --stop-after-init --max-cron-threads=0 --http-port=8073 2>&1 \
  | grep -E "ERROR|CRITICAL" && { echo "Nạp module báo lỗi, dừng." >&2; exit 1; } || true

echo "== 3/4  Khởi động lại container và chờ server sẵn sàng"
docker restart "$WEB" >/dev/null
for i in $(seq 1 60); do
  if docker exec "$WEB" python3 -c "import xmlrpc.client as x; x.ServerProxy('http://localhost:8069/xmlrpc/2/common').version()" >/dev/null 2>&1; then
    echo "   sẵn sàng sau ${i}s"; break
  fi
  sleep 1
  [ "$i" = 60 ] && { echo "Server không sẵn sàng sau 60 giây." >&2; exit 1; }
done

echo "== Phiên bản: file manifest trên đĩa và database (phải đồng đều); trạng thái Git"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
DIRTY=$(git status --porcelain 2>/dev/null | head -1 || true)
echo "   Git: nhánh $BRANCH, commit $(git rev-parse --short HEAD 2>/dev/null || echo ?)${DIRTY:+  (CÓ thay đổi chưa commit!)}"
BAD=0
for M in ${MODULES//,/ }; do
  FILE_V=$(docker exec "$WEB" sh -c "grep -o '\"version\": \"[^\"]*\"' /mnt/extra-addons/$M/__manifest__.py | cut -d'\"' -f4")
  DB_V=$(docker exec "$DBC" psql -U odoo -d "$DB" -Atc "select latest_version from ir_module_module where name = '$M'")
  FLAG="OK"
  [ "$FILE_V" != "$DB_V" ] && { FLAG="LỆCH: đĩa $FILE_V khác database $DB_V"; BAD=1; }
  echo "   $M: đĩa $FILE_V | database $DB_V | $FLAG"
done
[ "$BAD" = 1 ] && { echo "Phiên bản không đồng đều, dừng." >&2; exit 1; }
[ "$BRANCH" != "main" ] && echo "   Lưu ý: đang không đứng trên nhánh main (mã nguồn duy nhất là main, Chương 5.7)." || true
[ -n "$DIRTY" ] && echo "   Lưu ý: có thay đổi chưa commit — hệ thống đang chạy mã chưa nằm trong main." || true

echo "== 4/4  Chạy pre_defense_check.py"
docker exec "$WEB" python3 "$SCRIPT" --db "$DB"
