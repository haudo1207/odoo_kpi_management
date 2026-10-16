# Triển khai hệ thống Project KPI & Performance Management — End-to-end

Tài liệu này mô tả **toàn bộ hệ thống** (module `project_kpi_management` trên Odoo 19), theo đúng
thứ tự triển khai, Phase 0 → Phase 10. Mỗi Phase gồm 4 phần:

- **Mục tiêu:** Phase này giải quyết việc gì.
- **Vị trí source:** file nào trong repo chứa logic của Phase.
- **Thao tác trên Odoo:** làm gì trên giao diện — menu, nút bấm, field cần điền, theo đúng thứ tự click.
- **Kiểm tra:** cách biết Phase đã chạy đúng.

Đây là tài liệu **vận hành** (thao tác UI + vị trí code). Tài liệu **xây dựng** (giải thích code viết
như thế nào, vì sao thiết kế vậy) nằm ở [`HUONG_DAN_XAY_DUNG_TUAN_1_2.md`](HUONG_DAN_XAY_DUNG_TUAN_1_2.md)
(Phase 0–5). Hai tài liệu bổ sung cho nhau, không trùng lặp nội dung.

**Phạm vi:** toàn bộ repo tính tới commit `11623f1` (Tuần 1–4 đã gộp vào `main`, kịch bản mẫu đã gỡ
phụ thuộc `--with-demo`). Phase 11 (tài liệu, bảo vệ) chưa làm, ghi ở cuối.

---

## Mục lục

- [0. Kiến trúc tổng quan](#0-kiến-trúc-tổng-quan)
- [1. Chuẩn bị môi trường](#1-chuẩn-bị-môi-trường)
- [Phase 1 — Cấu hình KPI](#phase-1--cấu-hình-kpi)
- [Phase 2 — Customize task](#phase-2--customize-task)
- [Phase 3 — Kỳ và phiếu đánh giá](#phase-3--kỳ-và-phiếu-đánh-giá)
- [Phase 4 — Tính KPI tự động](#phase-4--tính-kpi-tự-động)
- [Phase 5 — Phân quyền](#phase-5--phân-quyền)
- [Phase 6 — Dashboard và báo cáo](#phase-6--dashboard-và-báo-cáo)
- [Phase 7 — Wizard và Settings](#phase-7--wizard-và-settings)
- [Phase 8 — Mở rộng vai trò mới (không sửa code)](#phase-8--mở-rộng-vai-trò-mới-không-sửa-code)
- [Phase 9 — Tự động hoá và tích hợp](#phase-9--tự-động-hoá-và-tích-hợp)
- [Phase 10 — Deploy production](#phase-10--deploy-production)
- [Phase 11 — Chưa làm](#phase-11--chưa-làm)
- [Phụ lục A — Cấu trúc thư mục đầy đủ](#phụ-lục-a--cấu-trúc-thư-mục-đầy-đủ)
- [Phụ lục B — Lệnh thường dùng](#phụ-lục-b--lệnh-thường-dùng)
- [Phụ lục C — REST API](#phụ-lục-c--rest-api)
- [Phụ lục D — 3 nhóm quyền](#phụ-lục-d--3-nhóm-quyền)
- [Phụ lục E — Sự cố thường gặp](#phụ-lục-e--sự-cố-thường-gặp)

---

## 0. Kiến trúc tổng quan

```
kpi.metric ──┐
             ├──▶ kpi.template (+ kpi.template.line) ──▶ hr.job.kpi_template_id
             │                                                   │
             │                                          hr.employee.job_id
             │                                                   │
kpi.period ──┴──────────────▶ kpi.evaluation (+ kpi.evaluation.line) ◀── kpi.engine (D1–D8)
                                        │
                        Nháp → Đã gửi → Đã duyệt
                                        │
                        Dashboard / Báo cáo / PDF / REST API
```

- **Chỉ số** (`kpi.metric`) độc lập với vai trò. **Bộ KPI** (`kpi.template`) gộp nhiều chỉ số +
  mục tiêu + trọng số, gắn vào **chức danh** (`hr.job`). Thêm vai trò mới = thêm dữ liệu, không
  sửa code (chứng minh ở Phase 8).
- **Phiếu đánh giá** (`kpi.evaluation`) chụp dữ liệu từ bộ KPI tại thời điểm tạo, không bị ảnh
  hưởng nếu bộ KPI đổi sau đó.
- **Engine** (`kpi.engine`) chỉ tính các chỉ số `compute_mode = auto` (D1–D8). Chỉ số nhập tay
  (D9, hoặc chỉ số tự tạo như T1–T3) do quản lý nhập trực tiếp trên phiếu.
- **9 chỉ số Developer:** D1 Đúng hạn · D2 Story point · D3 Mật độ lỗi · D4 Lỗi lọt production ·
  D5 Pass review · D6 Unit test · D7 Sửa bug nghiêm trọng · D8 Chia sẻ kiến thức · D9 Quản lý chấm.

---

## 1. Chuẩn bị môi trường

**Vị trí source:** `docker-compose.yml`, `config/odoo.conf`

**Thao tác:**

```bash
cd D:\Nam4\odoo19-kpi
docker compose up -d
```

Mở http://localhost:8019, đăng nhập `admin` / `admin` (Odoo tự băm lại mật khẩu master sau lần
chạy đầu — không ảnh hưởng tới mật khẩu đăng nhập web).

**Cài module:**

```bash
docker exec odoo19-web odoo -d kpi_dev -i project_kpi_management --stop-after-init --max-cron-threads=0 --http-port 8070
docker restart odoo19-web
```

Không cần `--with-demo` — module tự tạo đủ dữ liệu cấu hình cần thiết (xem Phase 1, 8). Sau khi
cài, vào **Apps**, bỏ bộ lọc "Apps", tìm "Project KPI" để xác nhận đã cài (trạng thái Installed).

**Kiểm tra:** menu **KPI** xuất hiện trên thanh điều hướng trên cùng.

**Về ngôn ngữ giao diện:** Odoo 19 chỉ cài sẵn `en_US`. Muốn toàn bộ giao diện gốc (Settings,
Employees, Project...) hiển thị tiếng Việt như tài liệu này mô tả, cài thêm gói tiếng Việt:
**Cài đặt › Dịch thuật › Ngôn ngữ** → thêm "Vietnamese / Tiếng Việt", rồi đặt ngôn ngữ này cho user
ở **Cài đặt › Người dùng & Công ty › Người dùng** (field *Ngôn ngữ* trên hồ sơ user). Một vài field
kỹ thuật (ví dụ *Folded*, xem Phase 2) chưa có bản dịch tiếng Việt trong Odoo 19, sẽ vẫn hiện tiếng
Anh — không phải lỗi.

---

## Phase 1 — Cấu hình KPI

**Mục tiêu:** khai báo chỉ số, bộ KPI theo vai trò, gắn vào chức danh.

**Vị trí source:**

| Thành phần | File |
|---|---|
| Model chỉ số | `models/kpi_metric.py` |
| Model bộ KPI + dòng | `models/kpi_template.py` |
| Gắn bộ KPI vào chức danh | `models/hr_job.py` |
| View | `views/kpi_metric_views.xml`, `views/kpi_template_views.xml`, `views/hr_job_views.xml` |
| Dữ liệu D1–D9 + bộ Developer (luôn có sau khi cài) | `data/kpi_metric_data.xml`, `data/kpi_template_data.xml` |
| Phòng ban, 2 chức danh mẫu (luôn có sau khi cài) | `data/kpi_org_data.xml` |

**Thao tác trên Odoo:**

1. **KPI › Cấu hình › Chỉ số KPI** — xem sẵn D1–D9. Để tạo chỉ số mới: điền *Mã*, *Tên chỉ số*,
   *Nhóm* (Tiến độ/Chất lượng/Quy trình/Cộng tác), *Chiều* (Cao là tốt/Thấp là tốt), *Cách tính*
   (Tự động — cần Engine hỗ trợ mã đó; hoặc Nhập tay — dùng ngay, không cần code).
2. **KPI › Cấu hình › Bộ KPI** — xem sẵn bộ "Developer" (tổng trọng số 100) và "Tester" (toàn nhập
   tay). Tạo bộ mới: đặt tên, thêm dòng trong tab **Chỉ số** (chọn chỉ số, Mục tiêu, Trọng số %,
   Khối lượng tối thiểu). Không lưu được nếu tổng trọng số ≠ 100.
3. **Nhân viên › Cấu hình › Tuyển dụng › Vị trí công việc** (model `hr.job` — tuy nằm trong mục
   Tuyển dụng, đây chính là chức danh gán cho nhân viên) — mở một chức danh, field **Bộ KPI** nằm
   ngay dưới tên chức danh (không phải trong tab). Chọn bộ KPI tương ứng.

**Kiểm tra:** mở bộ KPI "Developer", tổng trọng số hiện 100 (không đỏ). Thử ẩn (Archive) chỉ số D1
→ bị chặn, báo tên bộ KPI đang dùng.

---

## Phase 2 — Customize task

**Mục tiêu:** ghi nhận dữ liệu công việc làm đầu vào tính KPI.

**Vị trí source:** `models/project_task.py`, `views/project_task_views.xml`, `data/ir_cron_data.xml`

**Thao tác trên Odoo:**

1. Mở một task bất kỳ trong **Project**. Tab **Thông tin KPI** (sau tab Mô tả) có: *Loại task*
   (Feature/Bug), *Story point*, *Có unit test* (chỉ Quản lý KPI sửa được), *Số ngày trễ*, *Số lần
   được duyệt/bị trả về* (chỉ đọc).
2. Nếu *Loại task = Bug*: nhóm "Thông tin bug" hiện thêm — *Task gốc*, *Lỗi production*, *Kết quả
   xử lý bug* (valid/wont_fix/duplicate/invalid), *Nguyên nhân bug* (code/requirement/environment).
3. Danh sách task (list view) có bộ lọc: Bug, Lỗi production, Trễ hạn, Bị trả về, Bug chưa phân
   loại, Bug thiếu task gốc — ở ô tìm kiếm phía trên danh sách.

**Cấu hình bắt buộc:** stage "Done"/"Hoàn thành" của **mọi dự án** phải bật ô **Folded** (tên field
chưa có bản dịch tiếng Việt trong Odoo 19, sẽ hiện "Folded" dù giao diện đang tiếng Việt). Hai cách
vào:
- **Không cần bật chế độ dev:** mở Kanban task của dự án, trỏ chuột vào tiêu đề cột "Hoàn thành" →
  bấm icon bánh răng (⚙) hiện ra → Edit → tick **Folded** → lưu.
- **Cần bật chế độ nhà phát triển:** **Dự án › Cấu hình › Giai đoạn nhiệm vụ** — sửa được hàng loạt
  stage cùng lúc trên một list.

Không bật thì `date_end` không được ghi, D1 và D7 sẽ sai mà không báo lỗi.

**Kiểm tra:** chuyển một task Bug sang Done, xem *Số ngày trễ* và *Số lần được duyệt* có cập nhật.

---

## Phase 3 — Kỳ và phiếu đánh giá

**Mục tiêu:** tạo phiếu đánh giá theo nhân viên/kỳ, quy trình duyệt có lưu vết.

**Vị trí source:** `models/kpi_period.py`, `models/kpi_evaluation.py`,
`wizard/kpi_evaluation_reason_wizard.py`, `views/kpi_period_views.xml`, `views/kpi_evaluation_views.xml`

**Thao tác trên Odoo:**

1. **KPI › Cấu hình › Kỳ đánh giá** — tạo kỳ mới: *Tên kỳ*, *Loại kỳ* (Tháng/Sprint/Quý), *Từ
   ngày*/*Đến ngày*. Nút **Đóng kỳ**/**Mở lại kỳ** ở header.
2. **KPI › Đánh giá › Phiếu đánh giá** — tạo phiếu: chọn *Nhân viên*, *Kỳ đánh giá* (chỉ kỳ Đang
   mở). *Bộ KPI* tự chọn theo chức danh của nhân viên.
3. Tab **Chỉ số** của phiếu hiện toàn bộ dòng từ bộ KPI. *Mục tiêu* sửa được khi còn Nháp (ví dụ
   chỉnh D2 theo năng lực từng team).
4. Quy trình (nút ở header, hiện dần theo trạng thái): **Tính KPI** → **Gửi duyệt** → **Duyệt**.
   **Trả về nháp** (từ Đã gửi) và **Mở lại** (từ Đã duyệt) mở một ô nhỏ bắt buộc nhập lý do, lý do
   được lưu vào tab lịch sử (chatter) dưới phiếu.
5. Nếu điều chỉnh điểm (*Điều chỉnh của quản lý*, ±10) khác 0, ô *Lý do điều chỉnh* bắt buộc điền.

**Kiểm tra:** phiếu Đã duyệt không sửa được bất kỳ field nào (kể cả dòng chỉ số) — thử sửa sẽ báo lỗi.

---

## Phase 4 — Tính KPI tự động

**Mục tiêu:** tự lấy số liệu D1–D8 từ task/bug/lịch, không cần quản lý tổng hợp thủ công.

**Vị trí source:** `models/kpi_engine.py`, `data/kpi_calendar_data.xml`

**Thao tác trên Odoo:**

1. Trên phiếu (trạng thái Nháp), bấm **Tính KPI**. Field *Tính KPI lúc* hiện thời điểm vừa chạy.
   Cột *Thực tế*, *Khối lượng*, *Áp dụng*, *Điểm* trên từng dòng tự cập nhật.
2. Chỉ số D9 (nhập tay) **không** bị ghi đè bởi Tính KPI — quản lý tự gõ số vào cột *Thực tế* của
   dòng D9, tick *Đã chấm*.
3. D8 cần có sự kiện lịch gắn nhãn **"Chia sẻ kiến thức"**: **Lịch** › tạo sự kiện, tab thêm loại
   sự kiện, chọn "Chia sẻ kiến thức" (nhãn đã có sẵn, từ `kpi_calendar_data.xml`).
4. **Gửi duyệt** chỉ bấm được sau khi đã Tính KPI.

**Kiểm tra:** dòng *Không áp dụng* (chưa đủ khối lượng tối thiểu) hiện mờ, không cộng vào điểm
KPI. Nếu tổng trọng số các dòng áp dụng < 50%, khung cảnh báo màu vàng hiện ở đầu phiếu, bắt buộc
chọn *Xếp loại thủ công* + lý do trước khi gửi duyệt.

---

## Phase 5 — Phân quyền

**Mục tiêu:** 3 vai trò, mỗi vai trò chỉ thấy/sửa đúng phần của mình.

**Vị trí source:** `security/kpi_security.xml`, `security/ir.model.access.csv`

**Thao tác trên Odoo:**

1. **Cài đặt › Người dùng & Công ty › Người dùng** — mở một user, tab **Quyền truy cập**, mục **KPI**: chọn *User*
   (xem phiếu của mình — mọi nhân viên nội bộ có sẵn), *Manager* (quản lý trực tiếp), hoặc
   *Administrator*.
2. Quan hệ quản lý–nhân viên lấy từ field **Quản lý** trên hồ sơ nhân viên (Nhân viên › mở nhân
   viên › tab Thông tin công việc › *Quản lý*). KPI Manager chỉ sửa được phiếu của người có
   *Quản lý* = chính mình.
3. Chỉ **Administrator** thấy và bấm được nút Duyệt/Trả về/Mở lại, và vào được **KPI › Cấu hình ›
   Thiết lập**.

**Kiểm tra:** xem bảng đầy đủ ở [Phụ lục D](#phụ-lục-d--3-nhóm-quyền).

---

## Phase 6 — Dashboard và báo cáo

**Mục tiêu:** quản lý nhìn báo cáo biết ai điểm thấp, thấp ở đâu, dữ liệu có đáng tin không.

**Vị trí source:** `models/kpi_data_quality.py`, `models/hr_employee.py`,
`views/kpi_evaluation_views.xml` (pivot/graph), `views/kpi_report_views.xml`

**Thao tác trên Odoo:**

1. **KPI › Báo cáo › Xu hướng điểm** — graph đường, điểm cuối theo kỳ.
2. **KPI › Báo cáo › Phân bố xếp loại** — graph cột, số phiếu theo từng xếp loại.
3. **KPI › Báo cáo › Phân tích theo chỉ số** — pivot nhân viên × chỉ số, mặc định chỉ tính dòng
   *Được áp dụng* (lọc sẵn ở ô tìm kiếm).
4. **KPI › Báo cáo › Kiểm tra dữ liệu** — danh sách theo dự án: tỷ lệ Feature có story point, tỷ
   lệ bug có task gốc, tỷ lệ bug đủ phân loại, số task Done thiếu ngày hoàn thành. Tỷ lệ < 80% tô
   đỏ.
5. Trên **Danh sách phiếu đánh giá**, có thể chuyển sang view **Pivot** (nhân viên × kỳ) ngay từ
   action gốc.
6. Mở hồ sơ một nhân viên (**Nhân viên**), smart button **"Phiếu KPI"** ở góc trên hiện số phiếu,
   bấm vào xem danh sách/graph riêng của người đó.
7. Trên phiếu đã duyệt, nếu có bug tính KPI phát sinh **sau** lúc duyệt, smart button **"Bug phát
   sinh muộn"** hiện kèm số đếm — bấm vào xem danh sách bug đó (tham khảo cho kỳ sau, không tính
   lại điểm phiếu đã duyệt).

**Kiểm tra:** `psql` hoặc pgAdmin, bảng `kpi_data_quality_report` là **SQL view**, không phải bảng
thật (`_auto = False`), chỉ đọc.

---

## Phase 7 — Wizard và Settings

**Mục tiêu:** tạo phiếu hàng loạt, chỉnh ngưỡng xếp loại/điểm trần mà không sửa code.

**Vị trí source:** `wizard/kpi_evaluation_generate_wizard.py`, `models/res_config_settings.py`,
`views/kpi_wizard_settings_views.xml`

**Thao tác trên Odoo:**

1. **KPI › Đánh giá › Tạo phiếu cho kỳ** (hoặc nút cùng tên trên form Kỳ đánh giá). Chọn *Kỳ đánh
   giá* (phải đang Mở), tuỳ chọn *Phòng ban* (để trống = tất cả, có chọn thì gồm cả phòng ban con),
   tick *Tính KPI ngay*. Field *Số phiếu sẽ tạo* hiện trước khi bấm, để xem trước. Nhân viên đã có
   phiếu, chưa có tài khoản, hoặc chức danh chưa gắn bộ KPI sẽ tự bị bỏ qua.
2. Trên **danh sách** phiếu đánh giá, chọn nhiều dòng → **Hành động (⚙) › Tính lại KPI** — chỉ áp
   dụng cho phiếu đang Nháp, bỏ qua phiếu khác mà không báo lỗi.
3. **Cài đặt › KPI** (hoặc **KPI › Cấu hình › Thiết lập**): *Điểm trần mỗi chỉ số*, *Trọng số áp
   dụng tối thiểu*, *Biên độ điều chỉnh*, và 3 ngưỡng *Xuất sắc/Tốt/Đạt*. Lưu xong, bấm **Tính lại
   KPI** trên phiếu cũ để áp ngưỡng mới (phiếu không tự tính lại).

**Kiểm tra:** đổi ngưỡng "Xuất sắc" cao hơn điểm hiện tại của một phiếu, bấm Tính lại KPI, xếp loại
phải đổi theo ngưỡng mới.

---

## Phase 8 — Mở rộng vai trò mới (không sửa code)

**Mục tiêu:** chứng minh thêm phòng ban/chức danh/bộ KPI mới chỉ cần cấu hình dữ liệu.

**Vị trí source:** `data/kpi_org_data.xml` (bộ KPI "Tester" làm ví dụ có sẵn)

**Thao tác trên Odoo (tái hiện lại ví dụ Tester, hoặc tự làm vai trò khác):**

1. **Nhân viên › Phòng ban** (menu con, không nằm trong Cấu hình) — tạo phòng ban mới (nếu cần).
2. **KPI › Cấu hình › Chỉ số KPI** — tạo chỉ số mới, *Cách tính = Nhập tay* (không cần đụng code).
3. **KPI › Cấu hình › Bộ KPI** — tạo bộ mới, thêm dòng là chỉ số vừa tạo (hoặc tái dùng D1–D9 có
   sẵn), đảm bảo tổng trọng số = 100.
4. **Nhân viên › Cấu hình › Tuyển dụng › Vị trí công việc** — tạo chức danh mới, chọn *Bộ KPI* vừa tạo.
5. Tạo nhân viên mới với chức danh đó → **KPI › Đánh giá › Tạo phiếu cho kỳ** sẽ tự nhận ra người
   này mà không cần sửa file nào.

**Giới hạn thật sự (không tránh được):** nếu chỉ số mới là *Tự động* (không phải Nhập tay), Engine
cần một hàm `_metric_<mã>()` tương ứng trong `models/kpi_engine.py` — vì "tính tự động" nghĩa là
phải có thuật toán đọc dữ liệu, không tự sinh ra từ cấu hình được. Đây là ranh giới tự nhiên giữa
tự động và nhập tay, không phải lỗi thiết kế.

**Kiểm tra:** bộ "Tester" (T1–T3 + D9) là ví dụ sống — mở bất kỳ lúc nào tại **KPI › Cấu hình › Bộ
KPI**.

---

## Phase 9 — Tự động hoá và tích hợp

**Mục tiêu:** tự tạo phiếu cuối kỳ, in PDF, cung cấp REST API cho công cụ ngoài.

**Vị trí source:** `data/ir_cron_data.xml` (tác vụ `_cron_generate_evaluations` trong
`models/kpi_period.py`), `report/kpi_evaluation_report.xml`, `controllers/api.py`

**Thao tác trên Odoo:**

1. **Cài đặt › Kỹ thuật › Tự động hoá › Tác vụ đã lên lịch** (cần bật chế độ nhà phát triển):
   tìm "KPI: tạo phiếu đánh giá khi hết kỳ" — chạy hằng ngày, tự tạo + Tính KPI cho kỳ đã hết hạn
   mà chưa có phiếu (mỗi kỳ chỉ chạy một lần, lỗi ở một kỳ không chặn kỳ khác).
2. Trên phiếu đánh giá, menu **In (🖶)** ở header → **"Phiếu đánh giá KPI"** — xuất PDF gồm thông
   tin phiếu, bảng chỉ số, điểm, điều chỉnh, khối ký tên.
3. REST API: xem chi tiết ở [Phụ lục C](#phụ-lục-c--rest-api).

**Kiểm tra:** đặt *Đến ngày* của một kỳ về quá khứ, đợi tác vụ chạy (hoặc bấm "Chạy thủ công" trên
dòng hành động theo lịch ở chế độ dev), kiểm tra phiếu mới xuất hiện.

---

## Phase 10 — Deploy production

**Mục tiêu:** chạy hệ thống thật, có HTTPS, không lộ cổng database.

**Vị trí source:** `deploy/` (`docker-compose.prod.yml`, `nginx/odoo.conf`, `odoo.conf.example`,
`.env.example`, `README.md`)

**Thao tác:** làm theo đúng 9 bước trong [`deploy/README.md`](deploy/README.md) — lấy mã nguồn,
copy `.env.example`/`odoo.conf.example` rồi đổi mật khẩu, lấy chứng chỉ HTTPS, khởi tạo database,
**cấu hình bắt buộc sau khi cài** (bật Folded in Kanban cho stage Done, gắn bộ KPI cho chức danh,
gán quyền), sao lưu, cập nhật phiên bản.

**Kiểm tra:** làm theo checklist "Kiểm tra sau khi deploy" ở cuối `deploy/README.md`.

---

## Phase 11 — Chưa làm

Tài liệu Yêu cầu, Thiết kế CSDL, Kiến trúc, Hướng dẫn sử dụng, Test case, slide bảo vệ. Tài liệu
này (`TRIEN_KHAI_HE_THONG.md`) có thể dùng làm khung cho phần "Hướng dẫn sử dụng" và một phần
"Kiến trúc".

---

## Phụ lục A — Cấu trúc thư mục đầy đủ

```
addons/project_kpi_management/
├── __init__.py                          import controllers, models, wizard; post_init_hook
├── __manifest__.py                      thứ tự nạp file — xem khi cần tra load order
├── controllers/
│   └── api.py                           REST API (Phase 9)
├── models/
│   ├── kpi_metric.py                    Chỉ số KPI (Phase 1)
│   ├── kpi_template.py                  Bộ KPI + dòng (Phase 1)
│   ├── hr_job.py                        kpi_template_id trên hr.job (Phase 1)
│   ├── hr_employee.py                   Smart button "Phiếu KPI" (Phase 6)
│   ├── project_task.py                  Field KPI trên task (Phase 2)
│   ├── kpi_period.py                    Kỳ đánh giá + cron tạo phiếu (Phase 3, 9)
│   ├── kpi_evaluation.py                Phiếu, dòng phiếu, công thức điểm (Phase 3, 4)
│   ├── kpi_engine.py                    Tính D1–D8 (Phase 4)
│   ├── kpi_demo.py                      Kịch bản mẫu An/Bình/Chi (nạp qua menu, không tự chạy)
│   ├── kpi_data_quality.py              SQL view kiểm tra dữ liệu (Phase 6)
│   └── res_config_settings.py           Settings (Phase 7)
├── wizard/
│   ├── kpi_evaluation_reason_wizard.py  Lý do Trả về/Mở lại (Phase 3)
│   └── kpi_evaluation_generate_wizard.py Tạo phiếu hàng loạt (Phase 7)
├── security/
│   ├── kpi_security.xml                 3 group + record rule (Phase 5)
│   └── ir.model.access.csv              Quyền CRUD từng model
├── data/
│   ├── kpi_metric_data.xml              D1–D9 (noupdate)
│   ├── kpi_calendar_data.xml            Nhãn sự kiện "Chia sẻ kiến thức"
│   ├── kpi_template_data.xml            Bộ KPI Developer (noupdate)
│   ├── kpi_org_data.xml                 Phòng ban/chức danh mẫu + bộ Tester (noupdate)
│   ├── ir_cron_data.xml                 2 tác vụ: số ngày trễ, tạo phiếu cuối kỳ
│   ├── kpi_demo_scenario_action.xml     Menu "Nạp dữ liệu mẫu" (không tự chạy)
│   └── kpi_demo.xml                     (demo) vá fold stage Done của demo gốc project — tuỳ chọn
├── views/                                1 file view theo mỗi model/nhóm, + menus.xml
├── report/
│   └── kpi_evaluation_report.xml        Mẫu in PDF (Phase 9)
└── tests/                                8 file, 66 test — xem tests/*.py
```

```
odoo19-kpi/ (gốc repo)
├── docker-compose.yml, config/odoo.conf      môi trường dev
├── deploy/                                    Phase 10 — xem deploy/README.md
└── addons/project_kpi_management/             toàn bộ ở trên
```

---

## Phụ lục B — Lệnh thường dùng

| Việc | Lệnh |
|---|---|
| Khởi động | `docker compose up -d` |
| Chỉ sửa logic Python | `docker restart odoo19-web` |
| Thêm/sửa field, view, data, security | `docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management --stop-after-init --http-port 8070` rồi `docker restart odoo19-web` |
| Chạy test | `docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management --test-tags /project_kpi_management --stop-after-init --http-port 8070` |
| Mở shell Odoo | `docker exec -it odoo19-web odoo shell -d kpi_dev --no-http` |
| Tạo lại database từ đầu | xem [`HUONG_DAN_XAY_DUNG_TUAN_1_2.md`, Phụ lục](HUONG_DAN_XAY_DUNG_TUAN_1_2.md#phụ-lục) |

---

## Phụ lục C — REST API

Xác thực bằng **API key** (header `Authorization: Bearer <key>`). Tạo tại: bấm avatar góc trên bên
phải → **My Profile** (Hồ sơ của tôi) → tab **Security** (chưa có bản dịch tiếng Việt trong Odoo 19,
vẫn hiện tiếng Anh dù giao diện đang tiếng Việt) → mục *API Keys* → nút **Add API Key**. Mọi request
chạy bằng quyền của người sở hữu key — record rule KPI áp dụng y như trên giao diện (nhân viên chỉ
đọc phiếu của mình, quản lý đọc/ghi phiếu của nhóm).

| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| GET | `/api/kpi/evaluations?period_id=&state=&limit=&offset=` | Danh sách phiếu theo quyền người gọi |
| GET | `/api/kpi/evaluations/<id>` | Chi tiết phiếu + từng dòng chỉ số |
| POST | `/api/kpi/evaluations/<id>/metrics/<mã>` | Body `{"actual": 4, "remark": "..."}` — chỉ nhận chỉ số *Nhập tay* |

Mã lỗi: `401` thiếu/sai key · `403` không có quyền ghi · `404` không tìm thấy (kể cả khi phiếu có
tồn tại nhưng không được xem — không lộ thông tin) · `400` dữ liệu sai hoặc gửi vào chỉ số tự động.

**Lưu ý môi trường dev:** nếu database có nhiều hơn 1 database và chưa đặt `dbfilter`, phải thêm
header `X-Odoo-Database: <tên db>` (hoặc đăng nhập qua `/web/login?db=...` trước để có session).
Môi trường production (`deploy/`) đã đặt `dbfilter` cố định một database, không cần header này.

---

## Phụ lục D — 3 nhóm quyền

| | KPI User | KPI Manager | KPI Administrator |
|---|---|---|---|
| Ai | Mọi nhân viên nội bộ | Quản lý trực tiếp (có người cấp dưới) | Chỉ định thủ công (mặc định: admin) |
| Xem phiếu | Của mình | Của mình + nhân viên trực tiếp | Tất cả |
| Sửa phiếu (mục tiêu, D9, điều chỉnh), Tính KPI, Gửi duyệt | — | Phiếu nhân viên trực tiếp, **không sửa phiếu của chính mình** | Tất cả |
| Duyệt / Trả về / Mở lại | — | — | Có |
| Cấu hình (chỉ số, bộ KPI, kỳ, Settings) | Xem | Xem (trừ Settings) | Sửa |
| `has_unit_test` trên task | Không sửa | Sửa | Sửa |

---

## Phụ lục E — Sự cố thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| D1, D7 ra số lạ, task Done không có ngày hoàn thành | Stage Done chưa bật "Folded in Kanban" (Phase 2) |
| Không gửi duyệt được | Chưa Tính KPI, hoặc D9 chưa chấm, hoặc thiếu dữ liệu mà chưa chọn xếp loại thủ công |
| Sửa dữ liệu trong file XML mà `-u` không áp dụng | File có `noupdate="1"` — sửa trên giao diện, hoặc tạo lại database |
| REST API trả 404 dù phiếu có tồn tại | Môi trường dev có nhiều database — thêm header `X-Odoo-Database` |
| `docker exec` báo lỗi "could not serialize access" khi `-u` | Server chính đang chạy cron cùng lúc — chạy lại lệnh, hoặc thêm `--max-cron-threads=0` |
| Database có nhân viên tên nước ngoài lạ (Mitchell Admin...) | Đã cài kèm `--with-demo` — module KPI không cần cờ này nữa (xem Phase 1, 8); tạo lại database không dùng `--with-demo` |
