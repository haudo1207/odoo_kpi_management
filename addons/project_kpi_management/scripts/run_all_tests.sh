#!/usr/bin/env bash
# Chạy toàn bộ test của bốn module KPI trên một database TẠM (tự xoá, kể cả filestore), dùng được khi config/odoo.conf đang
# khoá dbfilter cho ngày bảo vệ: test API (HttpCase) đi qua HTTP nên bị dbfilter chặn (404), vì vậy script dùng bản sao
# config đã bỏ dbfilter/list_db chỉ cho lần chạy này; config thật không bị đổi.
# Dùng từ thư mục gốc repo:  bash addons/project_kpi_management/scripts/run_all_tests.sh
set -uo pipefail
WEB="${WEB_CONTAINER:-odoo19-web}"; DBC="${DB_CONTAINER:-odoo19-db}"
DB="kpi_test_$$"; CONF=/tmp/odoo_test.conf
FS=/var/lib/odoo/.local/share/Odoo/filestore
export MSYS_NO_PATHCONV=1
cleanup() { docker exec "$DBC" dropdb -U odoo --force --if-exists "$DB" >/dev/null 2>&1; docker exec "$WEB" rm -rf "$FS/$DB"; }
trap cleanup EXIT
docker exec "$WEB" sh -c "grep -v -E '^(dbfilter|list_db)[[:space:]]*=' /etc/odoo/odoo.conf > $CONF"
LOG=$(mktemp)
docker exec "$WEB" odoo -c "$CONF" -d "$DB" -i project_kpi_timesheet,project_kpi_skills,project_kpi_survey \
  --test-tags /project_kpi_management,/project_kpi_timesheet,/project_kpi_skills,/project_kpi_survey \
  --stop-after-init --max-cron-threads=0 --http-port=8071 > "$LOG" 2>&1
grep -E "post-tests in|failed, .* error\(s\)" "$LOG" | sed -e 's/^.*odoo.service.server: //' -e 's/^.*odoo.tests.result: //'
if grep -qE "ERROR $DB|CRITICAL" "$LOG"; then grep -E "FAIL:|ERROR:" "$LOG" | head -10; echo "CÓ TEST LỖI (log: $LOG)"; exit 1; fi
echo "TẤT CẢ TEST ĐẠT (bốn module)"; rm -f "$LOG"
