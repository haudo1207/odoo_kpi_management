# Triển khai Project KPI lên VPS

Hướng dẫn chạy module `project_kpi_management` trên Odoo 19 production: Docker Compose, PostgreSQL 16, nginx có HTTPS (Let's Encrypt).

## 1. Chuẩn bị

| Hạng mục | Yêu cầu tối thiểu |
|---|---|
| VPS | Ubuntu 22.04/24.04, 2 vCPU, 4 GB RAM, 40 GB ổ đĩa |
| Tên miền | Bản ghi A trỏ về IP của VPS (ví dụ `kpi.example.com`) |
| Cổng mở | 22 (SSH), 80, 443. **Không** mở 5432, 8069, 8072 |

Cài Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # đăng xuất rồi đăng nhập lại
```

## 2. Lấy mã nguồn và cấu hình

```bash
git clone https://github.com/haudo1207/odoo_kpi_management.git
cd odoo_kpi_management/deploy
cp .env.example .env               # đổi DB_PASSWORD
cp odoo.conf.example odoo.conf     # đổi admin_passwd
sed -i 's/kpi.example.com/<tên-miền-của-bạn>/g' nginx/odoo.conf
```

Tạo mật khẩu ngẫu nhiên: `openssl rand -base64 32`.

## 3. Lấy chứng chỉ HTTPS (lần đầu)

nginx cần chứng chỉ mới khởi động được, nên lần đầu lấy chứng chỉ ở chế độ standalone, khi nginx chưa chạy:

```bash
mkdir -p certbot/conf certbot/www
docker run --rm -p 80:80 -v "$PWD/certbot/conf:/etc/letsencrypt" certbot/certbot \
  certonly --standalone -d <tên-miền> --agree-tos -m <email> --no-eff-email
```

Gia hạn tự động: thêm vào `crontab -e` của VPS:

```
0 3 * * 1 cd /path/to/odoo_kpi_management/deploy && docker run --rm -v "$PWD/certbot/conf:/etc/letsencrypt" -v "$PWD/certbot/www:/var/www/certbot" certbot/certbot renew --webroot -w /var/www/certbot && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 4. Khởi tạo database và chạy

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d db
docker compose -f docker-compose.prod.yml --env-file .env run --rm odoo \
  odoo -d kpi -i project_kpi_management --stop-after-init   # Odoo 19 mặc định không nạp dữ liệu demo
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

Mở `https://<tên-miền>` và đăng nhập `admin`/`admin`, **đổi mật khẩu admin ngay**.

**Ba module cầu nối (tuỳ chọn, thêm chỉ số theo module gốc đã cài):** `project_kpi_timesheet` (giờ
làm thực tế so kế hoạch — cần `hr_timesheet`), `project_kpi_skills` (mức đáp ứng kỹ năng — cần
`hr_skills`), `project_kpi_survey` (phản hồi 360 độ — cần `survey`). Cả ba đều `auto_install`: nếu
module gốc tương ứng đã được cài (hoặc cài cùng lúc, ví dụ
`-i project_kpi_management,hr_timesheet`), Odoo tự cài module cầu nối, không cần `-i` riêng. Không
cài `hr_timesheet`/`hr_skills`/`survey` thì hệ thống vẫn chạy đủ, chỉ thiếu các chỉ số đó.

## 5. Cấu hình bắt buộc sau khi cài

1. **Stage Done của mọi dự án phải bật "Folded in Kanban"**: Dự án › Cấu hình › Giai đoạn. Không bật thì Odoo không ghi ngày hoàn thành, D1 và D7 sẽ sai mà không báo lỗi. Có thể kiểm tra ở KPI › Báo cáo › Kiểm tra dữ liệu (cột "Task xong thiếu ngày hoàn thành").
2. Gắn **Bộ KPI** cho từng chức danh: Nhân viên › Cấu hình › Chức danh.
3. Nhân viên phải có **tài khoản người dùng** và **quản lý trực tiếp** (trường Quản lý trên hồ sơ).
4. Phân quyền: Thiết lập › Người dùng › tab Quyền truy cập, mục KPI: User / Manager / Administrator.
5. Ngưỡng xếp loại, điểm trần, biên độ điều chỉnh: KPI › Cấu hình › Thiết lập.
6. Tạo kỳ đánh giá: KPI › Cấu hình › Kỳ đánh giá. Khi kỳ kết thúc, tác vụ tự động tạo phiếu và Tính KPI.

## 6. Sao lưu

```bash
# Database (chạy hằng ngày bằng crontab, giữ 14 bản gần nhất)
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U odoo -Fc kpi > backup/kpi_$(date +%F).dump
find backup -name 'kpi_*.dump' -mtime +14 -delete
# Filestore (file đính kèm)
docker run --rm -v deploy_odoo-data:/data -v "$PWD/backup:/backup" alpine tar czf /backup/filestore_$(date +%F).tgz -C /data .
```

Khôi phục: `pg_restore -U odoo -d kpi --clean` từ file `.dump`, giải nén filestore vào volume `odoo-data`.

## 7. Cập nhật phiên bản module

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env run --rm odoo \
  odoo -d kpi -u project_kpi_management --stop-after-init
docker compose -f docker-compose.prod.yml restart odoo
```

## 8. REST API

Mỗi người dùng tạo API key ở Hồ sơ › Bảo mật tài khoản › API Keys, rồi gọi với header `Authorization: Bearer <key>`:

```bash
curl -H "Authorization: Bearer $KEY" https://<tên-miền>/api/kpi/evaluations?period_id=1
curl -H "Authorization: Bearer $KEY" https://<tên-miền>/api/kpi/evaluations/5
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"actual": 4, "remark": "Làm việc nhóm tốt"}' https://<tên-miền>/api/kpi/evaluations/5/metrics/D9
```

API chạy bằng quyền của người sở hữu key: nhân viên chỉ đọc phiếu của mình, quản lý đọc và ghi phiếu của nhóm. POST chỉ nhận chỉ số nhập tay.

## 9. Kiểm tra sau khi deploy

- [ ] `https://<tên-miền>` có khoá xanh, `http://` tự chuyển sang `https://`
- [ ] `/web/database/manager` không truy cập được (`list_db = False`)
- [ ] Từ máy ngoài, cổng 5432, 8069 không kết nối được
- [ ] Thông báo trong Odoo hiện tức thì (websocket qua `/websocket` hoạt động)
- [ ] In thử một phiếu PDF
- [ ] Gọi thử `GET /api/kpi/evaluations` bằng API key
- [ ] Đã chạy thử một lần sao lưu và khôi phục
