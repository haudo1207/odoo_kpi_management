# Project KPI & Performance Management trên Odoo 19

Module quản lý và đánh giá KPI nhân sự cho doanh nghiệp phát triển phần mềm, xây trên nền Odoo 19
Community, tích hợp trực tiếp với module **Project** có sẵn (task, bug, milestone) thay vì nhập liệu
rời.

Nguyên tắc thiết kế cốt lõi: **không hardcode vai trò/chỉ số trong code.** Chỉ số, bộ KPI, mục tiêu,
trọng số đều là dữ liệu cấu hình qua giao diện — thêm một vai trò KPI mới (ví dụ Sales) không cần sửa
một dòng code nào (xem Chương 7 của tài liệu đồ án).

## Thành phần

| Module | Phụ thuộc | Vai trò |
|---|---|---|
| `addons/project_kpi_management/` | `project`, `hr`, `calendar`, `mail`, `web` | Module chính: chỉ số, bộ KPI, phiếu đánh giá, quy trình duyệt, dashboard, báo cáo, REST API |
| `addons/project_kpi_timesheet/` | + `hr_timesheet` | Cầu nối: chỉ số P4 (giờ thực tế so với kế hoạch) |
| `addons/project_kpi_skills/` | + `hr_skills` | Cầu nối: chỉ số S1 (mức đáp ứng kỹ năng) |
| `addons/project_kpi_survey/` | + `survey` | Cầu nối: chỉ số F1 (phản hồi 360 độ) |

Ba module cầu nối đều `auto_install` — tự bật khi Odoo có sẵn `hr_timesheet`/`hr_skills`/`survey`,
không cần cài tay. Phiên bản hiện tại của cả bốn module: `19.0.1.7.4`.

Bộ KPI có sẵn theo vai trò: Developer (D1–D9), Tester/QA (QA1–QA5), Team Lead/PM (P1–P5),
Business Analyst (B1–B4).

## Yêu cầu hệ thống

- Docker, Docker Compose
- Odoo 19.0 (ảnh `odoo:19.0`), PostgreSQL 16

## Chạy thử (môi trường dev)

```bash
git clone https://github.com/haudo1207/odoo_kpi_management.git
cd odoo_kpi_management
cp config/odoo.conf.example config/odoo.conf   # đổi admin_passwd khỏi change_me
docker compose up -d
docker exec odoo19-web odoo -d kpi_dev -i project_kpi_management --stop-after-init
```

Truy cập `http://localhost:8019`, đăng nhập `admin`.

## Kiểm thử

208 unit test tự động (0 lỗi): 185 ở module chính + 6/9/8 ở ba module cầu nối.

```bash
bash addons/project_kpi_management/scripts/run_all_tests.sh
```

## Triển khai production

Xem [`deploy/README.md`](deploy/README.md) — Docker Compose + nginx + Let's Encrypt (HTTPS).

## Tài liệu đồ án

Tài liệu đầy đủ (yêu cầu, kiến trúc, thiết kế CSDL, triển khai, kiểm thử, hướng dẫn sử dụng, demo mở
rộng, giới hạn, hướng phát triển, kết luận) nằm ở [`Nhom7_BaoCao.md`](Nhom7_BaoCao.md).

## Giấy phép

Đồ án phục vụ mục đích học tập.
