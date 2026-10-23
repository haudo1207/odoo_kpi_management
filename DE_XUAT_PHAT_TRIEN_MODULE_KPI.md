# Đề xuất phát triển thêm — Module `project_kpi_management` (Odoo 19)

> Đối chiếu module hiện tại với các hệ thống mã nguồn mở và module tương tự, xác định tính năng còn
> thiếu, và đề xuất thứ tự triển khai trước khi bảo vệ đồ án.

> **Cập nhật 2026-10-23 — tài liệu lịch sử, đã lỗi thời so với code:** đây là bản đề xuất gốc, viết
> trước khi làm Bước 0–5 và Đợt A–D (Chương 9 của `PHASE_11_TAI_LIEU_DU_AN.md`). Toàn bộ Mức 1 và
> Mức 2 bên dưới đã triển khai xong, trừ **mục 4 (huy hiệu Gamification)** — không làm, lý do ở cuối
> tài liệu. Cột "Trạng thái" ở mục 1 và 2 ghi tình trạng thực tế hiện nay; nội dung gốc giữ nguyên để
> còn thấy quá trình ra quyết định. Danh sách chức năng đang có, đối chiếu đầy đủ, nằm ở Chương 1 và
> Chương 10 của `PHASE_11_TAI_LIEU_DU_AN.md`.

---

## 0. Hiện trạng

Module đã có đủ phần lõi mà các hệ thống tương tự đều có:

- Bộ KPI theo chức danh (`hr.job.kpi_template_id`), trọng số, ràng buộc tổng = 100.
- Phiếu đánh giá theo nhân viên/kỳ, chụp mục tiêu và trọng số khi tạo.
- Engine tự tính D1–D8 từ dữ liệu Project và Calendar, D9 nhập tay.
- Quy trình Nháp → Đã gửi → Đã duyệt, trả về/mở lại có lý do.
- Phân quyền 3 nhóm, dashboard, báo cáo kiểm tra dữ liệu, wizard, Settings, cron, PDF, REST API.

Các tính năng dưới đây là phần **các hệ thống khác có mà module chưa có**.

---

## 1. Tính năng các hệ thống tương tự có mà module chưa có

| Nhóm | Tính năng | Nguồn tham khảo | Module hiện tại (lúc viết đề xuất) | Trạng thái nay |
|---|---|---|---|---|
| Đánh giá đa chiều | Nhân viên tự đánh giá | Frappe HR: điểm tự đánh giá tổng tính từ mức chấm và trọng số từng tiêu chí [1]. KPI Management & Performance Scorecard: mỗi chỉ số có điểm tự chấm, điểm quản lý chấm và kết quả cuối [6] | Chưa có, nhân viên chỉ xem | **Đã làm** (`self_score`, `employee_comment`) |
| | Phản hồi 360 độ | Odoo Appraisals: thu phản hồi từ quản lý, đồng nghiệp, cấp dưới và chính nhân viên [9] | Chưa có, D9 chỉ do quản lý chấm | **Đã làm** (Đợt D1, `project_kpi_survey`, chỉ số F1) |
| Mục tiêu | Mục tiêu theo phòng ban | Frappe HR: tạo kỳ đánh giá riêng cho chi nhánh, phòng ban hoặc chức danh [3] | Chỉ sửa tay trên phiếu Nháp | **Đã làm** (`kpi.target.override`, Đợt B) |
| | Mục tiêu từ dữ liệu lịch sử | Apache DevLake: lập mức nền năng lực từ dữ liệu lịch sử (lạc quan, khả dĩ, bi quan) [13] | Chưa có | **Đã làm** (gợi ý theo percentile 25/50/75, Đợt B) |
| | Mục tiêu cá nhân gắn với task | Frappe HR: điểm KRA tự tính từ mức hoàn thành các mục tiêu gắn với KRA [1][4] | Chưa có | Chưa làm (OKR, xem Chương 9.6 "Không làm") |
| Theo dõi trong kỳ | Cập nhật KPI định kỳ, có lịch sử | OCA `kpi`: bộ lịch chạy mỗi giờ, cập nhật KPI theo chu kỳ từng chỉ số [15] | Chỉ tính khi bấm nút | **Đã làm** (cron tạm tính, Đợt A3) |
| | Dải xếp loại có màu, cấu hình được | OCA `kpi`: mỗi khoảng ngưỡng có tên, min, max và màu [15] | 4 mức cố định | Chưa làm (xem Chương 9.6 "Không làm") |
| Sau đánh giá | Kế hoạch cải thiện cho người điểm thấp | HRMS Performance Management: gợi ý kế hoạch cải thiện (PIP) khi kết quả thấp [8] | Chưa có | **Đã làm** (nhắc việc PIP, Đợt A1) |
| Cấp team | Chỉ số theo team/dự án | Apache DevLake: dashboard dựng sẵn cho yêu cầu, lỗi, pull request, build, DORA [11][12] | Chỉ theo cá nhân | **Đã làm một phần** (báo cáo phòng ban, Đợt A5; không làm DORA/đồng bộ Jira-GitLab) |

---

## 2. Đề xuất triển khai theo mức ưu tiên

### Mức 1 — Nên làm trước bảo vệ (công sức nhỏ, giá trị cao)

| # | Tính năng | Lý do ưu tiên | Cách triển khai | Trạng thái nay |
|---|---|---|---|---|
| 1 | **Chặn xung đột vai trò** | Đang là giới hạn đã ghi ở Chương 8.3, sửa được thì xoá một điểm yếu | Trong `action_approve()` và `action_return()`: báo lỗi nếu người duyệt là quản lý trực tiếp (`employee_id.parent_id.user_id`) hoặc chính nhân viên. Thêm 2 test | **Đã làm** |
| 2 | **Mục tiêu theo phòng ban** | Giải quyết D2 "theo team" đang phải sửa tay | Model mới `kpi.target.override` (`template_line_id`, `department_id`, `employee_id`, `target`). Khi tạo phiếu, lấy mục tiêu theo thứ tự: nhân viên → phòng ban → template. Thêm 3 test cho 3 mức | **Đã làm** |
| 3 | **Nhắc việc và kế hoạch cải thiện** | `kpi.evaluation` đã kế thừa `mail.activity.mixin` nhưng chưa dùng | Tạo phiếu → activity cho quản lý "Chấm D9". Gửi duyệt → activity cho Admin "Duyệt phiếu". Duyệt với xếp loại "Cần cải thiện" → activity cho quản lý "Lập kế hoạch cải thiện" | **Đã làm** (Đợt A1) |
| 4 | **Huy hiệu cho nhân viên Xuất sắc** | Tận dụng module Gamification có sẵn trong Odoo Community [16], chứng minh nguyên tắc "không xây lại thứ đã có" | Thêm `gamification` vào `depends`, tạo 1 huy hiệu trong data XML. Duyệt phiếu Xuất sắc thì tự trao huy hiệu | **Chưa làm** — module `gamification` không có trong `depends`; giá trị trình diễn thấp so với ba Đợt B/C/D đã chọn làm thay, bỏ qua có chủ đích |

### Mức 2 — Làm nếu còn thời gian

| # | Tính năng | Cách triển khai | Trạng thái nay |
|---|---|---|---|
| 5 | **Nhân viên tự đánh giá** | Thêm trạng thái "Chờ nhân viên phản hồi" giữa Nháp và Đã gửi. Field `self_score` trên dòng nhập tay, `employee_comment` trên phiếu. Record rule cho nhân viên ghi đúng 2 field này | **Đã làm** |
| 6 | **Báo cáo cấp team** | SQL view `kpi.team.report` theo phòng ban/dự án, cùng cách làm với `kpi.data.quality.report`: tỷ lệ đúng hạn, mật độ lỗi, lỗi lọt production, thời gian sửa bug | **Đã làm** (Đợt A5, báo cáo phòng ban) |
| 7 | **Bộ KPI BA có chỉ số tự động** | Thêm `_metric_ba1()`: tỷ lệ bug do yêu cầu sai, dựa trên `bug_root_cause = requirement` đã có. Chứng minh dữ liệu Phase 2 dùng lại được cho vai trò khác | **Đã làm** (bộ BA: B1, B2, B3, Đợt B) |
| 8 | **Tạm tính giữa kỳ** | Cron hằng tuần gọi lại "Tính lại KPI" cho phiếu Nháp của kỳ đang mở, để quản lý và nhân viên thấy tiến độ sớm | **Đã làm** (Đợt A3, cron tạm tính) |

### Mức 3 — Ghi vào Hướng phát triển (lúc viết đề xuất)

| Tính năng | Lý do để sau | Trạng thái nay |
|---|---|---|
| Phản hồi 360 độ | Cần model phản hồi riêng, phân quyền phức tạp, ẩn danh | **Đã làm** (Đợt D1, xem mục 1 ở trên) |
| Mục tiêu cá nhân/OKR gắn task | Gần như một module riêng | Vẫn chưa làm — giữ ở Chương 9.6 "Không làm" |
| Gợi ý mục tiêu từ lịch sử | Cần dữ liệu nhiều kỳ mới có ý nghĩa | **Đã làm** (percentile 25/50/75, không cần nhiều kỳ — tính trên kỳ hiện có) |
| Dải xếp loại cấu hình có màu | Giá trị thấp so với công sức đổi cấu trúc Settings hiện tại | Vẫn chưa làm — giữ ở Chương 9.6 "Không làm" |
| Đồng bộ Jira/GitLab, DORA | Phụ thuộc hạ tầng ngoài | Vẫn chưa làm — giữ ở Chương 9.6 "Không làm" |

---

## 3. Lưu ý trước khi làm thêm

- **Mỗi tính năng mới cần đủ 3 thứ:** test, cập nhật tài liệu Phase 11, và tự giải thích được. Thiếu
  một trong ba thì để ở Hướng phát triển.
- **Chốt thời điểm dừng thêm tính năng** (ví dụ 1–2 tuần trước bảo vệ). Sau mốc đó chỉ sửa lỗi và
  luyện trình bày.
- Mức 1 gồm 4 việc nhỏ, nâng hệ thống mà không làm loãng phần lõi. Mục 1 và 4 dễ trình bày trước hội
  đồng: một mục xoá giới hạn đã nêu, một mục chứng minh tận dụng Odoo có sẵn.

---

## 4. Tài liệu tham khảo

### 4.1. Frappe HR (mã nguồn mở, cùng hệ sinh thái ERPNext)

Gần thiết kế của module nhất: mẫu đánh giá gắn chức danh, KRA có trọng số, kỳ đánh giá theo phòng
ban, tạo phiếu hàng loạt, tự đánh giá.

| # | Tài liệu | Link |
|---|---|---|
| [1] | Appraisal — phiếu đánh giá, đánh giá KRA, tự đánh giá | https://docs.frappe.io/hr/appraisal |
| [2] | Appraisal Template — mẫu đánh giá, KRA và trọng số, gắn chức danh | https://docs.frappe.io/hr/appraisal-template |
| [3] | Appraisal Cycle — kỳ đánh giá theo phòng ban/chức danh, tạo phiếu hàng loạt | https://docs.frappe.io/hr/appraisal-cycle |
| [4] | Bài giới thiệu module Performance (KRA vs Goals, 360, báo cáo tổng quan) | https://frappe.io/blog/frappe-hr/frappe-hr-updates-from-march-2023 |
| [5] | Trang tính năng Performance Management | https://frappe.io/hr/performance-management |

### 4.2. Module trên Odoo Apps Store

Lưu ý: thông tin trên trang Apps Store là mô tả của tác giả, chưa đọc code. Kiểm tra giấy phép trước
khi tham khảo code; module OPL-1 chỉ nên tham khảo ý tưởng.

| # | Module | Phiên bản | Giấy phép | Link |
|---|---|---|---|---|
| [6] | KPI Management & Performance Scorecard — điểm tự chấm/quản lý chấm, lấy dữ liệu Project và Timesheet | 18.0 | LGPL-3 | https://apps.odoo.com/apps/modules/18.0/kpi_management |
| [7] | EH HR Appraisal — template có trọng số, tạo phiếu theo kỳ | 19.0 | LGPL-3 | https://apps.odoo.com/apps/modules/19.0/eh_hr_appraisal |
| [8] | HRMS Performance Management — KRA/KPI theo phòng ban, chức danh, gợi ý PIP | 18.0 | Xem trang module | https://apps.odoo.com/apps/modules/18.0/hrms_performance_management |

### 4.3. Odoo Appraisals (bản Enterprise, không phải mã nguồn mở)

Dùng để so sánh tính năng, không dùng làm nền vì module chạy trên bản Community.

| # | Tài liệu | Link |
|---|---|---|
| [9] | Cấu hình Appraisals Odoo 19 (kế hoạch đánh giá, 360, thang đánh giá, thư viện mục tiêu) | https://www.cybrosys.com/odoo/odoo-books/v19/appraisals/configuration/ |
| [10] | Tài liệu chính thức: Goals trong Appraisals | https://www.odoo.com/documentation/master/applications/hr/appraisals/goals.html |

### 4.4. Apache DevLake (mã nguồn mở, Apache-2.0)

Nguồn danh mục chỉ số kỹ thuật phần mềm có định nghĩa, công thức và SQL mẫu. Dùng để tham khảo chỉ
số cho Developer, Tester, BA, DevOps và báo cáo cấp team.

| # | Tài liệu | Link |
|---|---|---|
| [11] | Mã nguồn | https://github.com/apache/devlake |
| [12] | Danh mục chỉ số (yêu cầu, lỗi, PR, build, DORA, chất lượng code) | https://devlake.apache.org/docs/Metrics |
| [13] | Requirement Delivery Rate (có gợi ý lập mức nền từ lịch sử) | https://devlake.apache.org/docs/Metrics/RequirementDeliveryRate |
| [14] | Bug Age (tương đương D7) | https://devlake.apache.org/docs/Metrics/BugAge |

### 4.5. OCA — Odoo Community Association (mã nguồn mở, AGPL-3)

| # | Module | Link |
|---|---|---|
| [15] | `kpi` — KPI có ngưỡng nhiều khoảng (tên, min, max, màu), cập nhật theo lịch. Có bản 19.0 | https://pypi.org/project/odoo-addon-kpi/19.0.1.0.0.4/ |
| — | Kho mã nguồn chứa `kpi`, `kpi_dashboard` | https://github.com/OCA/reporting-engine |
| — | `kpi_dashboard` — tính KPI bằng hàm định sẵn hoặc code (đến bản 15.0) | https://apps.odoo.com/apps/modules/15.0/kpi_dashboard |

### 4.6. Có sẵn trong Odoo 19 Community

| # | Module | Link |
|---|---|---|
| [16] | `gamification` — mục tiêu, challenge, huy hiệu (đã kiểm tra trên source 19.0) | https://github.com/odoo/odoo/tree/19.0/addons/gamification |

### 4.7. Nguồn bổ sung

| Nguồn | Nội dung | Link |
|---|---|---|
| OrangeHRM (mã nguồn mở) | KPI định nghĩa riêng cho từng chức danh | https://github.com/orangehrm/orangehrm |
| Bài viết Octura Solutions | Appraisals Odoo 19: kế hoạch theo phòng ban, mục tiêu có trọng số, 360 | https://octurasolutions.com/resources/odoo-19-employee-appraisals-goal-setting-360-feedback-and-performance-reviews |
