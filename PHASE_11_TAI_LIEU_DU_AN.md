# Tài liệu đồ án — Project KPI & Performance Management trên Odoo 19

> Phase 11 (Tài liệu và bảo vệ) của lộ trình triển khai. Tài liệu này gộp đủ 5 phần theo yêu cầu
> Phase 11: **Yêu cầu, Thiết kế CSDL, Kiến trúc, Hướng dẫn sử dụng, Test case**, cộng thêm phần
> **Đối tượng áp dụng và giới hạn**, **Demo minh hoạ mở rộng**, và **Hướng phát triển**.

**Tên đồ án:** Xây dựng module quản lý và đánh giá KPI nhân sự (`project_kpi_management`) trên nền
tảng Odoo 19, tích hợp với module Project có sẵn.
**Mã nguồn:** `addons/project_kpi_management/` trong repo này.
**Tài liệu liên quan:** [`TRIEN_KHAI_HE_THONG.md`](TRIEN_KHAI_HE_THONG.md) (hướng dẫn thao tác
Odoo + vị trí source theo từng Phase), [`HUONG_DAN_XAY_DUNG_TUAN_1_2.md`](HUONG_DAN_XAY_DUNG_TUAN_1_2.md)
(giải thích cách viết code Phase 0–5), [`deploy/README.md`](deploy/README.md) (triển khai production).

---

## Mục lục

- [Chương 1 — Yêu cầu](#chương-1--yêu-cầu)
- [Chương 2 — Kiến trúc hệ thống](#chương-2--kiến-trúc-hệ-thống)
- [Chương 3 — Thiết kế cơ sở dữ liệu](#chương-3--thiết-kế-cơ-sở-dữ-liệu)
- [Chương 4 — Triển khai](#chương-4--triển-khai)
- [Chương 5 — Kiểm thử](#chương-5--kiểm-thử)
- [Chương 6 — Hướng dẫn sử dụng](#chương-6--hướng-dẫn-sử-dụng)
- [Chương 7 — Demo minh hoạ khả năng mở rộng](#chương-7--demo-minh-hoạ-khả-năng-mở-rộng)
- [Chương 8 — Đối tượng áp dụng và giới hạn](#chương-8--đối-tượng-áp-dụng-và-giới-hạn)
- [Chương 9 — Hướng phát triển](#chương-9--hướng-phát-triển)
- [Chương 10 — Kết luận](#chương-10--kết-luận)
- [Phụ lục — Thuật ngữ](#phụ-lục--thuật-ngữ)

---

## Chương 1 — Yêu cầu

### 1.1. Bối cảnh và lý do chọn đề tài

Doanh nghiệp quản lý dự án phần mềm bằng Odoo Project có đủ dữ liệu công việc (task, bug, deadline,
story point...) nhưng Odoo không có sẵn công cụ tổng hợp dữ liệu đó thành **KPI đánh giá nhân sự**.
Quản lý phải tự tổng hợp thủ công, không nhất quán, không lưu vết. Đồ án xây dựng module đóng vai
trò cầu nối: biến dữ liệu công việc đã có sẵn trong Odoo thành bộ chỉ số KPI tính tự động, có quy
trình phê duyệt và báo cáo.

### 1.2. Mục tiêu

1. Cho phép định nghĩa **bộ chỉ số KPI theo từng vai trò** (chức danh), không hardcode trong code.
2. **Tự động tính toán** phần lớn chỉ số từ dữ liệu Project có sẵn (task, bug, lịch).
3. Có **phiếu đánh giá** theo nhân viên/kỳ, đi qua quy trình duyệt có lưu vết, cho phép quản lý điều
   chỉnh nhưng bắt buộc giải trình.
4. Có **báo cáo/dashboard** giúp quản lý cấp trên thấy ai điểm thấp, thấp ở đâu, và dữ liệu có đáng
   tin không.
5. Cho phép **mở rộng sang vai trò khác** (QA, Sales...) chỉ bằng cấu hình, không sửa code (trừ
   trường hợp cần công thức tính tự động hoàn toàn mới).

### 1.3. Đối tượng áp dụng

Doanh nghiệp phần mềm vừa và nhỏ, quản lý công việc bằng Odoo Project, có cấu trúc quản lý trực
tiếp rõ ràng (mỗi nhân viên có một quản lý), đánh giá hiệu suất theo **kỳ** (tháng/sprint/quý)
chứ không theo từng task riêng lẻ.

### 1.4. Yêu cầu chức năng

| Mã | Vai trò | Yêu cầu |
|---|---|---|
| YC-01 | KPI Administrator | Định nghĩa chỉ số KPI (mã, tên, nhóm, chiều, cách tính) |
| YC-02 | KPI Administrator | Định nghĩa bộ KPI theo vai trò (nhiều chỉ số, mục tiêu, trọng số), ràng buộc tổng trọng số = 100 |
| YC-03 | KPI Administrator | Gắn bộ KPI vào chức danh (`hr.job`) |
| YC-04 | Nhân viên (Developer) | Dữ liệu công việc (task, bug) được ghi nhận đủ để tính KPI: loại task, story point, phân loại bug, số lần trả về, có unit test |
| YC-05 | KPI Administrator / Manager | Tạo kỳ đánh giá (tháng/sprint/quý), đóng/mở kỳ |
| YC-06 | Quản lý trực tiếp | Tạo phiếu đánh giá cho nhân viên mình quản lý, trong một kỳ cụ thể |
| YC-07 | Hệ thống | Tự động tính 8/9 chỉ số (D1–D8) từ dữ liệu task/bug/lịch; chỉ số còn lại (D9) do quản lý chấm tay |
| YC-08 | Quản lý trực tiếp | Điều chỉnh điểm cuối trong biên độ cho phép, bắt buộc ghi lý do khi điều chỉnh khác 0 |
| YC-09 | Quản lý trực tiếp → KPI Administrator | Phiếu đi qua quy trình Nháp → Gửi duyệt → Duyệt; Trả về/Mở lại phải ghi lý do, lưu vết |
| YC-10 | KPI Administrator / Manager | Xem báo cáo: xu hướng điểm theo kỳ, phân bố xếp loại, phân tích theo chỉ số, kiểm tra chất lượng dữ liệu |
| YC-11 | KPI Administrator | Tạo phiếu hàng loạt theo kỳ (và theo phòng ban nếu cần) |
| YC-12 | KPI Administrator | Chỉnh ngưỡng xếp loại, điểm trần, biên độ điều chỉnh qua giao diện Settings, không sửa code |
| YC-13 | Hệ thống | Mọi vai trò chỉ xem/sửa đúng phạm vi của mình (phân quyền) |
| YC-14 | Hệ thống | Tự động tạo phiếu khi kỳ kết thúc (không cần quản lý nhớ tạo tay) |
| YC-15 | Nhân viên/Quản lý | In phiếu đánh giá ra PDF để lưu trữ/ký tay |
| YC-16 | Công cụ ngoài (CI, quản lý test) | Đọc/ghi dữ liệu phiếu qua REST API có xác thực |

### 1.5. Yêu cầu phi chức năng

| Mã | Yêu cầu |
|---|---|
| PCN-01 | Chạy trên Odoo 19 Community (không phụ thuộc tính năng Enterprise, ví dụ không dùng `hr_appraisal`) |
| PCN-02 | Không hardcode vai trò/chỉ số trong code — toàn bộ nằm trong dữ liệu cấu hình (xem Chương 2.4) |
| PCN-03 | Không xây lại tính năng Odoo gốc đã có (deadline, trạng thái, mức ưu tiên, nhân viên, lịch, chatter) |
| PCN-04 | Dữ liệu tính KPI minh bạch: mỗi dòng chỉ số có cờ "Áp dụng", loại trừ rõ ràng khi thiếu dữ liệu, không âm thầm tính sai |
| PCN-05 | Có kiểm thử tự động bao phủ từng quy tắc nghiệp vụ (không chỉ happy case) |
| PCN-06 | Giao diện bằng tiếng Việt, tương thích khi cài thêm gói ngôn ngữ Odoo |
| PCN-07 | REST API xác thực bằng API key chuẩn Odoo, tuân thủ phân quyền ghi/đọc như trên giao diện |
| PCN-08 | Triển khai production có HTTPS, không public cổng database |

### 1.6. Ràng buộc và giả định

- Nhân viên được tính KPI tự động phải có **tài khoản người dùng Odoo** gắn với `hr.employee`
  (Engine đọc task/bug theo `user_ids`).
- Mỗi nhân viên có **một quản lý trực tiếp** (field `parent_id` trên `hr.employee`) — cấu trúc phân
  quyền theo nhóm dựa vào quan hệ này.
- Stage "Done"/"Hoàn thành" của mọi dự án phải bật **Folded** (mục kỹ thuật, xem Chương 2.5) — đây
  là ràng buộc vận hành bắt buộc, không phải lỗi phần mềm.

---

## Chương 2 — Kiến trúc hệ thống

### 2.1. Kiến trúc tổng quan (4 tầng)

```
┌─────────────────────────────────────────────────────────────────┐
│ Tầng tích hợp     REST API (controllers/api.py) · Báo cáo PDF    │
│                   (report/) · Cron (data/ir_cron_data.xml)       │
├─────────────────────────────────────────────────────────────────┤
│ Tầng trình bày    Views (list/form/search/pivot/graph) · Wizard  │
│                   (wizard/) · Settings (res_config_settings.py)  │
├─────────────────────────────────────────────────────────────────┤
│ Tầng nghiệp vụ    kpi.metric · kpi.template(.line) · kpi.period  │
│                   kpi.evaluation(.line) · kpi.engine · kpi.data  │
│                   .quality.report                                │
├─────────────────────────────────────────────────────────────────┤
│ Tầng tích hợp     Mở rộng project.task, hr.job, hr.employee —    │
│ với Odoo gốc      ghi thêm field KPI vào model có sẵn, không     │
│                   tạo bảng song song                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Luồng dữ liệu chính

```
                         ┌─ kpi.metric (D1–D9, hoặc tự định nghĩa) ─┐
                         │                                           │
hr.job ──kpi_template_id──▶ kpi.template ──line_ids──▶ kpi.template.line
   ▲                                                          │ (mục tiêu, trọng số, khối lượng tối thiểu)
   │ job_id                                                   │ chụp khi tạo phiếu
hr.employee                                                   ▼
   │                                              kpi.evaluation (phiếu)
   │ employee_id                                        │        ▲
   └──────────────────────────────────────────────────▶ │        │ action_compute_kpi()
kpi.period ──period_id──────────────────────────────────┘        │
                                                                   │
                                            kpi.engine._metric_d1..d8()
                                                    │ đọc (sudo)
                                                    ▼
                                project.task (task_type, story_points,
                                bug_resolution, bug_root_cause, ...),
                                calendar.event (nhãn "Chia sẻ kiến thức")

kpi.evaluation.line (mỗi dòng 1 chỉ số)
   actual, volume ──compute──▶ is_applicable, score, weighted_score
                                         │
kpi.evaluation: Σ(score×weight)/Σweight ──▶ kpi_score ──+manager_adjustment──▶ final_score ──▶ rating
                                                                                                   │
                                                                         insufficient_data ? manual_rating : rating
                                                                                                   ▼
                                                                                           final_rating (dùng cho mọi báo cáo)
```

### 2.3. Cấu trúc thư mục module

```
addons/project_kpi_management/
├── controllers/api.py              REST API
├── models/
│   ├── kpi_metric.py               Danh mục chỉ số + chỉ số cấu hình không cần code (Bước 1)
│   ├── kpi_template.py             Bộ KPI + dòng + resolve mục tiêu riêng
│   ├── kpi_target_override.py      Mục tiêu riêng theo nhân viên/phòng ban (Mục 4)
│   ├── hr_job.py                   Mở rộng hr.job: kpi_template_id
│   ├── hr_employee.py              Mở rộng hr.employee: smart button
│   ├── project_task.py             Mở rộng project.task: field KPI
│   ├── kpi_period.py               Kỳ đánh giá + sinh phiếu hàng loạt + cron
│   ├── kpi_evaluation.py           Phiếu + dòng phiếu + công thức điểm + quy trình + PIP + tự đánh giá
│   ├── kpi_engine.py               Tính D1–D8 + chỉ số cấu hình domain (AbstractModel, không bảng)
│   ├── kpi_demo.py                 Kịch bản dữ liệu mẫu (AbstractModel)
│   ├── kpi_data_quality.py         SQL view kiểm tra chất lượng dữ liệu
│   ├── kpi_team_report.py          SQL view chỉ số cấp team/dự án (Mục 5)
│   └── res_config_settings.py      Mở rộng Settings
├── wizard/
│   ├── kpi_evaluation_reason_wizard.py      Lý do Trả về/Mở lại
│   ├── kpi_evaluation_generate_wizard.py    Tạo phiếu hàng loạt
│   ├── kpi_self_assessment_wizard.py        Nhân viên tự đánh giá (Mục 6)
│   └── kpi_metric_test_wizard.py            Nút "Thử tính" chỉ số cấu hình (Bước 1)
├── security/                        3 nhóm quyền + record rule + CSV quyền model
├── data/                             Dữ liệu cấu hình chuẩn (D1–D9, bộ Developer/Tester, cron, loại nhắc việc PIP...)
├── views/                           View cho từng model + menu
├── report/                          Mẫu in PDF
└── tests/                           12 file, 109 test
```

### 2.4. Nguyên tắc thiết kế cốt lõi: không hardcode vai trò

Đây là nguyên tắc xuyên suốt toàn bộ thiết kế, không phải khẩu hiệu. Bằng chứng kiến trúc:

- `hr.job.kpi_template_id` (Many2one) — mỗi chức danh **tự chọn** bộ KPI của mình, không có đoạn
  code nào kiểm tra `if job.name == 'Developer'`.
- `kpi.template.line` chỉ là bảng ánh xạ (chỉ số, mục tiêu, trọng số, khối lượng tối thiểu) — thêm
  dòng mới là thao tác dữ liệu thuần tuý.
- `kpi.evaluation.create()` chọn bộ KPI theo `employee.job_id.kpi_template_id`, hoàn toàn generic
  (xem trích đoạn ở Chương 3.3).
- `kpi.period._eligible_employees()` lọc nhân viên đủ điều kiện tạo phiếu chỉ dựa vào
  `job_id.kpi_template_id.line_ids` khác rỗng — không biết và không cần biết tên chức danh.

**Đã kiểm chứng trực tiếp** (không chỉ suy luận): tạo một phòng ban, một chỉ số nhập tay, một bộ
KPI, một chức danh, một nhân viên hoàn toàn mới — chỉ bằng thao tác dữ liệu (ORM/giao diện), không
sửa một dòng code nào — toàn bộ luồng (wizard tạo phiếu hàng loạt tự nhận diện, tính điểm, gửi
duyệt) chạy đúng ngay lập tức. Chi tiết và kết quả ở [Chương 7](#chương-7--demo-minh-hoạ-khả-năng-mở-rộng).

**Giới hạn tự nhiên (không tránh được):** chỉ số *Tự động* (`compute_mode = auto`) cần một hàm
`_metric_<mã>()` trong `kpi_engine.py`, vì "tính tự động" nghĩa là phải có thuật toán đọc dữ liệu —
không thể tự sinh ra từ cấu hình. Đây là ranh giới giữa tự động và nhập tay, không phải lỗ hổng
thiết kế. Chỉ số *Nhập tay* (`compute_mode = manual`) không có giới hạn này.

### 2.5. Tích hợp với Odoo gốc

| Model gốc | Field/khả năng được tái sử dụng | Field module KPI thêm vào |
|---|---|---|
| `project.task` | `date_deadline`, `date_end`, `state`, `priority`, `working_hours_close`, `user_ids` | `task_type`, `story_points`, `origin_task_id`, `bug_ids`, `is_production_bug`, `bug_resolution`, `bug_root_cause`, `bug_reporter_id`, `review_reject_count`, `review_approve_count`, `has_unit_test`, `kpi_can_review`, `days_late` |
| `project.task.type` | Field `fold` có sẵn (ẩn trong Kanban) | — (chỉ yêu cầu cấu hình, không thêm field) |
| `hr.employee` | `user_id`, `parent_id`, `job_id`, `department_id` (qua `hr.version`) | `kpi_evaluation_count` (compute) |
| `hr.job` | Model chức danh có sẵn | `kpi_template_id` |
| `hr.department` | Model phòng ban có sẵn, không đổi | — |
| `calendar.event` | `user_id`, `categ_ids`, `start`/`stop` | — (chỉ thêm 1 bản ghi `calendar.event.type` làm nhãn) |
| `mail.thread`, `mail.activity.mixin` | Lịch sử (chatter) | `kpi.evaluation` kế thừa để có lịch sử duyệt/trả về |
| `res.config.settings` | Cơ chế Settings app chuẩn | 6 field tham số KPI |
| `res.groups.privilege` (Odoo 19) | Cơ chế nhóm quyền mới | 1 privilege "KPI", 3 group con |

**Phát hiện quan trọng khi đối chiếu source Odoo 19** (ảnh hưởng trực tiếp thiết kế, không chỉ là
ghi chú): `date_end` chỉ được Odoo ghi khi task vào stage có `fold = True`, và bị **xoá** khi task
sang stage không fold. Vì D1 và D7 đều phụ thuộc `date_end`, module phải tự ghi lại giá trị này
trong `write()` (chạy **sau** `super().write()`), và tài liệu vận hành phải nêu rõ yêu cầu cấu hình
bắt buộc: stage Done/Hoàn thành của mọi dự án phải bật **Folded**.

---

## Chương 3 — Thiết kế cơ sở dữ liệu

### 3.1. Danh sách model

| # | Model | Loại | Vai trò |
|---|---|---|---|
| 1 | `kpi.metric` | Bảng thật | Danh mục chỉ số KPI |
| 2 | `kpi.template` | Bảng thật | Bộ KPI theo vai trò |
| 3 | `kpi.template.line` | Bảng thật | Dòng chỉ số trong bộ KPI |
| 4 | `kpi.period` | Bảng thật | Kỳ đánh giá |
| 5 | `kpi.evaluation` | Bảng thật | Phiếu đánh giá |
| 6 | `kpi.evaluation.line` | Bảng thật | Dòng chỉ số trong phiếu |
| 7 | `kpi.data.quality.report` | **SQL view** (`_auto = False`) | Báo cáo chất lượng dữ liệu, chỉ đọc |
| 8 | `kpi.engine` | AbstractModel, không bảng | Thuật toán tính D1–D8 |
| 9 | `kpi.demo` | AbstractModel, không bảng | Nạp kịch bản mẫu |
| 10 | `kpi.evaluation.reason.wizard` | TransientModel | Lý do Trả về/Mở lại |
| 11 | `kpi.evaluation.generate.wizard` | TransientModel | Tạo phiếu hàng loạt |
| 12 | `project.task` *(mở rộng)* | Bảng gốc Odoo | Thêm field KPI |
| 13 | `hr.job` *(mở rộng)* | Bảng gốc Odoo | Thêm `kpi_template_id` |
| 14 | `hr.employee` *(mở rộng)* | Bảng gốc Odoo | Thêm smart button |
| 15 | `res.config.settings` *(mở rộng)* | TransientModel gốc Odoo | Thêm 6 tham số |
| 16 | `kpi.target.override` | Bảng thật | Mục tiêu riêng theo nhân viên/phòng ban cho một dòng chỉ số |
| 17 | `kpi.team.report` | **SQL view** (`_auto = False`) | Chỉ số cấp team (dự án): đúng hạn, mật độ lỗi, lỗi production, giờ sửa bug |
| 18 | `kpi.self.assessment.wizard`(`.line`) | TransientModel | Nhân viên tự đánh giá (Mục 6) |
| 19 | `kpi.metric.test.wizard` | TransientModel | Nút "Thử tính" cho chỉ số cấu hình (Bước 1, Chương 9.1) |

### 3.2. Sơ đồ quan hệ (ERD dạng văn bản)

```
hr.job ──1:1 (field)──▶ kpi.template ──1:N──▶ kpi.template.line ──N:1──▶ kpi.metric
  ▲ N:1                                                                      ▲ N:1
hr.employee                                                                  │
  │ N:1                                                                      │
  ├──employee_id──┐                                                         │
kpi.period ──1:N──▶ kpi.evaluation ──1:N──▶ kpi.evaluation.line ────────────┘
                         │ N:1 (job_id, department_id — chụp lúc tạo, không liên kết động)
                    (mail.thread: lịch sử duyệt/trả về/mở lại)

project.task ──N:1 (origin_task_id, tự tham chiếu)──▶ project.task   (bug ↔ task gốc)
project.task ──N:1 (user_ids)──▶ res.users ──1:1──▶ hr.employee

kpi.data.quality.report  (SQL view, GROUP BY theo project.task.project_id — không có FK thật)
```

### 3.3. Chi tiết từng bảng

#### `kpi.metric` — Danh mục chỉ số

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `code` | Char | required, **UNIQUE** (`models.Constraint`) | Mã ngắn (D1, T1...) |
| `name` | Char | required | Tên đầy đủ |
| `category` | Selection | required | delivery/quality/process/collaboration |
| `unit` | Char | | Đơn vị hiển thị (%, giờ, SP...) |
| `direction` | Selection | required, default `higher` | `higher` (cao tốt) / `lower` (thấp tốt) |
| `compute_mode` | Selection | required, default `auto` | `auto` (hàm Python `_metric_<mã>()`) / `domain` (cấu hình, không cần code — Chương 9.1) / `manual` (nhập tay) |
| `description` | Text | | Mô tả công thức |
| `active` | Boolean | default True | Ẩn (archive) bị **chặn** nếu còn bộ KPI đang dùng (`@api.constrains`) |

`_rec_names_search = ["code", "name"]`, `display_name` tự ghép `"<code> — <name>"`.

**Bước 1 (Chương 9.1, đã triển khai) — chỉ số cấu hình không cần code**, dùng khi `compute_mode = domain`:

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `source_model_id` | Many2one → `ir.model` | domain chỉ cho `project.task`, `project.milestone`, `calendar.event` | Model lấy dữ liệu |
| `user_field_id` | Many2one → `ir.model.fields` | phải thuộc `source_model_id` | Field người phụ trách — **để trống** nếu điều kiện người đã viết sẵn trong domain bằng `$CURRENT_USER_ID` (cần khi phải đi qua quan hệ, ví dụ `origin_task_id.user_ids`) |
| `date_field_id` | Many2one → `ir.model.fields` | phải thuộc `source_model_id`, kiểu Date/Datetime | Field ngày để lọc theo kỳ — tự chọn mốc Date hay Datetime UTC đúng theo kiểu field (Bước 0) |
| `aggregation` | Selection | required khi `compute_mode = domain` | `count` (Đếm) / `sum` (Tổng) / `avg` (Trung bình) / `ratio` (Tỷ lệ) |
| `value_field_id` | Many2one → `ir.model.fields` | bắt buộc nếu `aggregation` là sum/avg, kiểu Integer/Float/Monetary | Field số để Tổng/Trung bình |
| `numerator_domain` | Char | required, phải `ast.literal_eval` được | Domain Odoo dạng literal thuần; dùng chuỗi `$CURRENT_USER_ID`/`$PERIOD_START`/`$PERIOD_END` làm giữ chỗ cho giá trị động |
| `denominator_domain` | Char | bắt buộc nếu `aggregation = ratio` | Domain mẫu số |

Lấy nguyên mẫu từ `gamification.goal.definition` (Odoo 19 Community, đã kiểm tra trên source):
model + field + domain + `computation_mode` (count/sum/python). **Chỉ lấy phần domain/count/sum/avg
— không có lựa chọn chạy code Python tuỳ ý** như `gamification` (đó là lỗ hổng bảo mật nếu cho nhập
qua giao diện). Validate khi lưu (`_check_domain_metric_config`, cùng cách `gamification` làm ở
`_check_domain_validity`): model phải trong danh sách cho phép, field phải đúng model/kiểu, và thử
chạy `search_count()` thật với domain để bắt lỗi cú pháp ngay khi lưu, không đợi tới lúc tính KPI.

**Bước 0 (rà soát ngay sau khi triển khai Bước 1) — 4 điểm đã sửa:**

1. **Đọc domain bằng `ast.literal_eval`**, không phải `safe_eval`: chỉ parse literal Python thuần
   (list/tuple/str/số...), không chạy được bất kỳ biểu thức hay thuộc tính nào (`user.id` kiểu truy
   cập thuộc tính sẽ KHÔNG còn hợp lệ) — an toàn hơn hẳn so với bản đầu dùng `safe_eval` + biến
   `user`/`start`/`end`. Để vẫn tham chiếu được người/kỳ, domain dùng 3 chuỗi giữ chỗ cố định
   (`$CURRENT_USER_ID`, `$PERIOD_START`, `$PERIOD_END`), được `substitute_domain_placeholders()`
   thay bằng giá trị thật **sau khi** đã parse xong (không phải lúc parse) — xem
   `models/kpi_metric.py`.
2. **Lọc kỳ đúng kiểu field ngày:** field Date (ví dụ `project.milestone.deadline`) lọc bằng chính
   kiểu Date (`>= ngày đầu kỳ`, `< ngày đầu kỳ sau`); field Datetime (ví dụ `project.task.date_deadline`)
   dùng mốc UTC như các chỉ số Python hiện có (`_period_bounds()`). So Date với mốc UTC datetime
   trực tiếp có thể lệch múi giờ đúng ở ngày biên — `kpi.engine._domain_field_bounds()` tự chọn
   đúng loại mốc theo `date_field_id.ttype`. Có test cho cả hai kiểu, kiểm đúng bản ghi nằm sát
   ngày cuối kỳ.
3. **Nút "Thử tính" tự kiểm tra quyền** trong `action_open_test_wizard()` (`has_group`, giống
   `_check_kpi_admin()`), không chỉ ẩn ở view — gọi thẳng qua RPC bỏ qua nút vẫn bị chặn đúng.
4. **Dữ liệu test có 1 bản ghi đã lưu trữ** (`active = False`) trong `test_domain_metric_equivalent_to_d4`
   — xác nhận domain cấu hình và hàm Python `_metric_d4()` xử lý **giống nhau** với bản ghi đã lưu
   trữ (cả hai đều dùng `search()`/`search_count()` nên mặc định đều loại bản ghi đã lưu trữ), không
   lệch kết quả.

**Giới hạn đã biết:** domain không so sánh được hai field trên cùng bản ghi (ví dụ D1 cần
`date_end <= date_deadline`) — phải giữ hàm Python cho các chỉ số kiểu này, hoặc thêm field compute
stored dạng cờ (`is_on_time`) để domain chỉ cần so với giá trị cố định. Đi qua quan hệ (như D4 quy
bug về task gốc) **không** thuộc giới hạn này — domain vẫn so sánh được field quan hệ với hằng số
(`$CURRENT_USER_ID`/`$PERIOD_START`/`$PERIOD_END`), chỉ cần để trống `user_field_id`/`date_field_id`
và viết đủ điều kiện trong `numerator_domain`/`denominator_domain` (xem test
`test_domain_metric_equivalent_to_d4`).

`kpi.engine._compute_domain_metric()`: ghép domain cấu hình với điều kiện người/kỳ (nếu có khai báo
`user_field_id`/`date_field_id`), rồi `search_count`/`search().mapped()` theo `aggregation`. Trả về
`(actual, volume)` đúng khuôn với các hàm `_metric_<mã>()` hiện có — không cần sửa gì ở
`kpi.evaluation`/`kpi.evaluation.line`, nơi gọi `kpi.engine.compute_actual()` không quan tâm chỉ số
đến từ code hay cấu hình.

Nút **"Thử tính"** trên form chỉ số (chỉ hiện khi `compute_mode = domain`, chỉ KPI Admin): mở wizard
`kpi.metric.test.wizard`, chọn một nhân viên và một kỳ, xem ngay `actual`/`volume` — không cần tạo
phiếu thật để biết domain viết có đúng không.

#### `kpi.template` — Bộ KPI theo vai trò

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `name` | Char | required | |
| `description` | Text | | |
| `active` | Boolean | default True | Ẩn bị chặn nếu còn chức danh dùng (`job_ids`) |
| `line_ids` | One2many → `kpi.template.line` | | `copy=True` |
| `job_ids` | One2many ← `hr.job.kpi_template_id` | | Chỉ đọc, hiển thị chức danh đang dùng |
| `total_weight` | Integer, compute | | Tổng trọng số các dòng |

Ràng buộc: `@api.constrains('line_ids')` — tổng trọng số phải = 100 **nếu** đã có ít nhất 1 dòng
(template rỗng được phép lưu). Đặt trên template (không đặt trên dòng) vì form tách thao tác sửa/
thêm dòng thành nhiều lệnh ghi riêng — ràng buộc trên dòng sẽ bắt sai trạng thái "nửa chừng".

#### `kpi.template.line` — Dòng chỉ số trong bộ KPI

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `template_id` | Many2one → `kpi.template` | required, `ondelete=cascade` | |
| `sequence` | Integer | default 10 | |
| `metric_id` | Many2one → `kpi.metric` | required, `ondelete=restrict` | |
| `target` | Float | digits(16,2) | Mục tiêu |
| `weight` | **Integer** | required, CHECK 0–100 | Trọng số (%) — Integer để so sánh tổng=100 chính xác |
| `min_volume` | Float | CHECK ≥ 0 | Khối lượng tối thiểu để chỉ số được áp dụng |
| `direction`, `unit`, `compute_mode` | related → `metric_id.*` | | |

Ràng buộc SQL (`models.Constraint`): `UNIQUE(template_id, metric_id)` (một chỉ số không lặp trong
1 bộ KPI), `CHECK(weight BETWEEN 0 AND 100)`, `CHECK(min_volume >= 0)`.

`_resolve_target(overrides, employee_id, department_id)`: mục tiêu dùng khi chụp phiếu, ưu tiên
`kpi.target.override` của nhân viên, rồi của phòng ban, cuối cùng mới dùng `target` mặc định ở trên.

#### `kpi.target.override` — Mục tiêu riêng theo nhân viên/phòng ban

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `template_line_id` | Many2one → `kpi.template.line` | required, `ondelete=cascade` | Dòng chỉ số muốn đặt mục tiêu riêng |
| `employee_id` | Many2one → `hr.employee` | | Để trống nếu override theo phòng ban |
| `department_id` | Many2one → `hr.department` | | Để trống nếu override theo nhân viên |
| `target` | Float | required, digits(16,2) | Mục tiêu riêng, thay cho mục tiêu mặc định của template |

Ràng buộc SQL: `CHECK` đúng một trong hai (`employee_id` xor `department_id`), `UNIQUE(template_line_id,
employee_id)` và `UNIQUE(template_line_id, department_id)` (NULL không đụng nhau trong PostgreSQL nên
nhiều dòng phòng ban khác nhau cho cùng 1 chỉ số vẫn hợp lệ). Chỉ dùng lúc tạo phiếu (`kpi.evaluation.
create()`), không ảnh hưởng phiếu đã tạo trước đó — đúng nguyên tắc chụp dữ liệu.

#### `kpi.period` — Kỳ đánh giá

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `name` | Char | required | |
| `period_type` | Selection | required, default `month` | month/sprint/quarter |
| `date_from`, `date_to` | Date | required | CHECK `date_from <= date_to` |
| `state` | Selection | required, default `open` | open/closed |
| `evaluation_ids` | One2many ← `kpi.evaluation.period_id` | | |
| `evaluation_count` | Integer, compute | | Cho smart button |
| `auto_generated` | Boolean | readonly, copy=False | Đánh dấu cron đã chạy cho kỳ này — mỗi kỳ chỉ 1 lần |

#### `kpi.evaluation` — Phiếu đánh giá (kế thừa `mail.thread`, `mail.activity.mixin`)

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `name` | Char, compute, store | | `"<nhân viên> — <kỳ>"` |
| `employee_id` | Many2one → `hr.employee` | required | |
| `job_id`, `department_id` | Many2one, readonly | | **Chụp** lúc tạo (không related — `hr.employee.job_id` không stored vì nằm ở `hr.version`) |
| `period_id` | Many2one → `kpi.period` | required | |
| `template_id` | Many2one → `kpi.template` | required | |
| `line_ids` | One2many → `kpi.evaluation.line` | | Chụp từ template khi tạo |
| `state` | Selection | default `draft` | draft/submitted/approved |
| `computed_date` | Datetime, readonly | copy=False | Thời điểm bấm Tính KPI gần nhất |
| `approved_date` | Datetime, readonly | copy=False | Thời điểm Duyệt |
| `late_bug_count` | Integer, compute | | Bug tính KPI phát sinh **sau** `approved_date` |
| `applicable_weight` | Integer, compute, store | | Σ trọng số các dòng *Áp dụng* |
| `insufficient_data` | Boolean, compute, store | | `applicable_weight < 50` (tham số, Settings) |
| `kpi_score` | Float, compute, store | | Σ(score×weight)/Σweight trên dòng áp dụng |
| `manager_adjustment` | Float | digits(16,2) | ±10 (tham số), bắt buộc có `adjustment_note` nếu khác 0 |
| `adjustment_note` | Text | | |
| `final_score` | Float, compute, store | | `kpi_score + manager_adjustment` |
| `rating` | Selection, compute, store | | Xếp loại tự động, `False` nếu `insufficient_data` |
| `manual_rating`, `manual_rating_note` | Selection, Text | | Dùng khi `insufficient_data` |
| `final_rating` | Selection, compute, store | | `manual_rating` nếu thiếu dữ liệu, ngược lại `rating` — **dùng cho mọi báo cáo** |
| `employee_comment` | Text | copy=False | Mục 6 — nhân viên tự nhận xét, chỉ tham khảo, ghi qua wizard bằng `sudo()` |
| `is_own_evaluation` | Boolean, compute | không store | Mục 6 — `True` nếu người đang xem là chính nhân viên trên phiếu, dùng để hiện nút "Tự đánh giá" |

Ràng buộc SQL: `UNIQUE(employee_id, period_id)`. Ràng buộc Python: biên độ điều chỉnh, kỳ phải
đang mở khi tạo phiếu Nháp, khoá toàn bộ field thuộc `_LOCKED_FIELDS` khi không ở Nháp
(`employee_id`, `period_id`, `template_id`, `line_ids`, `manager_adjustment`, `adjustment_note`,
`manual_rating`, `manual_rating_note`).

`employee_comment` **không** nằm trong `_LOCKED_FIELDS` vì cần chặn mạnh hơn: quản lý vốn có quyền
ghi trên `kpi.evaluation` (cho `manager_adjustment`...) nên nếu chỉ khoá theo trạng thái thì vẫn ghi
hộ được field này trong lúc phiếu còn Nháp — phát hiện bằng chính `scripts/pre_defense_check.py`
(Chương 5.6). Cả `create()` lẫn `write()` đều chặn field này cho **mọi** lời gọi không qua `sudo()`,
bất kể trạng thái hay quyền — chặn một chỗ vẫn lách được qua chỗ kia (ví dụ truyền sẵn giá trị lúc
tạo phiếu), nên phải chặn cả hai. Chỉ wizard Tự đánh giá (ghi bằng `sudo()`) mới ghi được. `self_score`
trên `kpi.evaluation.line` (bên dưới) cùng cơ chế và cùng lý do, vì quản lý cũng có quyền ghi dòng
phiếu khi Nháp (để nhập D9).

#### `kpi.evaluation.line` — Dòng chỉ số trong phiếu

| Field | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `evaluation_id` | Many2one, `ondelete=cascade` | required | |
| `employee_id`, `period_id`, `department_id`, `job_id`, `category` | related, **store=True** | | Lưu sẵn để pivot/group by không phải join nhiều cấp |
| `metric_id` | Many2one → `kpi.metric` | required, `ondelete=restrict` | |
| `target` | Float | digits(16,2) | Chụp từ template, sửa được khi phiếu Nháp |
| `weight` | Integer | | Chụp từ template |
| `min_volume` | Float | digits(16,2) | Chụp từ template |
| `volume` | Float | | Engine ghi (chỉ số auto) |
| `actual` | Float | | Engine ghi (auto) hoặc quản lý nhập (manual) |
| `actual_entered` | Boolean | | Đánh dấu chỉ số nhập tay đã được chấm — tránh nhầm "chưa nhập" với "nhập 0" |
| `is_applicable` | Boolean, compute, store | | `volume >= min_volume` |
| `score` | Float, compute, store | | 2 chiều, trần = tham số `score_cap` (mặc định 120) |
| `weighted_score` | Float, compute, store | | `score × weight / 100` |
| `remark` | Text | | |
| `self_score` | Float | copy=False | Mục 6 — nhân viên tự chấm (chỉ chỉ số nhập tay), chỉ tham khảo, không cộng vào `score`/`weighted_score`. Chặn ghi trực tiếp giống `employee_comment` ở trên (cả `create()` lẫn `write()`), chỉ wizard Tự đánh giá ghi được. `copy=False` để Nhân bản phiếu không chép tự đánh giá của phiếu cũ sang (nếu không sẽ bị chặn `create()` nhầm) |

**Công thức tính điểm** (`_score()`, static method):

```python
if direction == "lower":                       # thấp là tốt
    score = cap if actual <= 0 else target / actual * 100
else:                                           # cao là tốt
    score = cap if target <= 0 else actual / target * 100
return max(min(score, cap), 0.0)
```

Chỉ áp dụng khi `is_applicable = True`; dòng không áp dụng có `score = 0` và bị loại khỏi cả tử số
lẫn mẫu số khi tính `kpi_score` của phiếu.

#### `kpi.data.quality.report` — Báo cáo chất lượng dữ liệu (SQL view)

Không phải bảng thật (`_auto = False`), tạo bằng `CREATE VIEW` trong `init()`, nhóm theo
`project.task.project_id`. Các field: `done_feature_count`, `done_without_sp`, `done_count`,
`done_without_date_end`, `bug_count`, `bug_without_origin`, `bug_unclassified`, và 3 tỷ lệ phần
trăm tương ứng (`sp_rate`, `origin_rate`, `classified_rate`, `aggregator=None` để pivot không cộng
dồn sai).

#### `kpi.team.report` — Chỉ số KPI theo dự án (SQL view, Mục 5)

Cùng cách làm với `kpi.data.quality.report` ở trên (`_auto = False`, `CREATE VIEW` trong `init()`,
nhóm theo `project_id`), nhưng không kiểm tra chất lượng nhập liệu mà đo hiệu quả của cả team: team
= dự án. Các field: `feature_done_count`, `feature_on_time_count`, `on_time_rate` (%), `bug_count`,
`bug_density` (bug/feature), `production_bug_count`, `production_bug_rate` (%), `avg_bug_fix_hours`
(giờ thực tế từ lúc tạo đến lúc sửa xong, tính bằng `EXTRACT(EPOCH FROM ...)`, không phải giờ làm
việc theo lịch công ty như D7). Không quy trách nhiệm cá nhân, không tính điểm — chỉ là báo cáo.

Bug được quy về **dự án của task gốc** (`origin_task_id.project_id`), không phải dự án chứa bản ghi
bug — đúng quy ước D3/D4 đã có ở `kpi_engine._counted_bugs()` ("quy về người được giao và kỳ hoàn
thành của task gốc"). Bug không có task gốc (`bug_without_origin`, xem báo cáo kiểm tra dữ liệu) thì
giữ nguyên dự án của chính nó.

#### Field mở rộng trên `project.task`

| Field | Kiểu | Dùng cho |
|---|---|---|
| `task_type` | Selection (feature/bug), required, default feature | Phân loại |
| `story_points` | Float, digits(16,1) | D2, D3 |
| `origin_task_id` | Many2one tự tham chiếu (`domain="[('id','!=',id)]"`) | D3, D4 — bug trỏ về task gốc |
| `bug_ids` | One2many ngược của `origin_task_id` | Hiển thị trên task gốc |
| `is_production_bug` | Boolean | D4 |
| `bug_resolution` | Selection (valid/wont_fix/duplicate/invalid) | Lọc bug tính KPI |
| `bug_root_cause` | Selection (code/requirement/environment) | Lọc bug tính KPI |
| `bug_reporter_id` | Many2one `res.users`, default người tạo | QA1–QA4 (Bước 2) — người phát hiện bug; **không dùng `create_uid`** vì PM có thể log bug hộ tester hoặc bug được import. Chỉ KPI Manager trở lên ghi được (kiểm ở `create`/`write`, và khoá trên form); bug cũ được bù `bug_reporter_id = create_uid` đúng một lần khi nâng lên 19.0.1.1.0 (`migrations/19.0.1.1.0/post-migrate.py`) |
| `review_reject_count`, `review_approve_count` | Integer, readonly | D5 — tăng trong `write()` khi đổi state |
| `has_unit_test` | Boolean | D6 — chỉ KPI Manager ghi được (kiểm ở `create`/`write`) |
| `kpi_can_review` | Boolean, compute | Khoá ô `has_unit_test` trên form nếu không phải Manager |
| `days_late` | Integer, compute, store | D1 — so `date_end`/hôm nay với `date_deadline`, cron cập nhật hằng ngày |

#### Field mở rộng trên `hr.job`, `hr.employee`, `res.config.settings`

| Model | Field | Ghi chú |
|---|---|---|
| `hr.job` | `kpi_template_id` (Many2one, `ondelete=restrict`) | Trung tâm của nguyên tắc "không hardcode vai trò" |
| `hr.employee` | `kpi_evaluation_count` (Integer, compute) | Cho smart button "Phiếu KPI" |
| `res.config.settings` | `kpi_score_cap`, `kpi_adjustment_max`, `kpi_min_applicable_weight`, `kpi_rating_excellent`, `kpi_rating_good`, `kpi_rating_pass` (đều Float, `config_parameter=...`) | Lưu ở `ir.config_parameter`, đọc qua `get_kpi_param()` |

#### Wizard (TransientModel)

| Model | Field chính | Mục đích |
|---|---|---|
| `kpi.evaluation.reason.wizard` | `evaluation_id`, `mode` (return/reopen), `reason` (required) | Bắt buộc lý do khi Trả về nháp/Mở lại, ghi vào chatter |
| `kpi.evaluation.generate.wizard` | `period_id`, `department_ids` (M2M), `compute`, `preview_count` (compute) | Tạo phiếu hàng loạt, xem trước số lượng |

### 3.4. Bộ 9 chỉ số KPI Developer (dữ liệu, không phải code)

| Mã | Tên | Công thức | Mục tiêu | Trọng số | Chiều | Khối lượng tối thiểu |
|---|---|---|---|---|---|---|
| D1 | Hoàn thành đúng hạn | Task xong đúng hạn / Task có deadline trong kỳ × 100 | 90% | 20% | Cao tốt | ≥ 3 task có deadline |
| D2 | Story point hoàn thành | Σ `story_points` task Done trong kỳ | Theo team | 10% | Cao tốt | Luôn áp dụng |
| D3 | Mật độ lỗi | Bug tính KPI / SP hoàn thành | ≤ 0,3 | 15% | Thấp tốt | ≥ 1 SP |
| D4 | Lỗi lọt production | Bug production tính KPI / Tổng bug tính KPI × 100 | ≤ 5% | 15% | Thấp tốt | ≥ 1 bug |
| D5 | Pass review lần đầu | Task duyệt chưa từng bị trả về / Task đã qua review × 100 | ≥ 80% | 10% | Cao tốt | ≥ 3 task qua review |
| D6 | Có unit test | Task Feature có unit test / Task Feature Done × 100 | ≥ 70% | 10% | Cao tốt | ≥ 1 Feature |
| D7 | Thời gian sửa bug nghiêm trọng | Trung bình `working_hours_close` bug High/Urgent | ≤ 24h | 5% | Thấp tốt | ≥ 1 bug High/Urgent |
| D8 | Chia sẻ kiến thức | Số sự kiện nhãn "Chia sẻ kiến thức" tổ chức trong kỳ | ≥ 1 | 5% | Cao tốt | Luôn áp dụng |
| D9 | Đánh giá của quản lý | Thang 1–5, nhập tay | 4 | 10% | Cao tốt | Luôn áp dụng |

**Quy tắc "Bug tính KPI"** (áp dụng cho D3, D4): `bug_resolution ∈ {valid, wont_fix}` **và**
`bug_root_cause = code`. Bug `duplicate`/`invalid`, hoặc nguyên nhân `requirement`/`environment`,
không tính. **Quy kỳ:** D3/D4 quy bug về người làm và kỳ hoàn thành của **task gốc**; D7 quy về
người sửa và kỳ hoàn thành của **chính bug đó** (lý do: D3/D4 đo chất lượng code đã viết ra, D7 đo
tốc độ phản ứng khi sửa).

**Xếp loại** (khoảng nửa mở, so trên giá trị chưa làm tròn): Xuất sắc ≥ 100 · Tốt [90, 100) · Đạt
[75, 90) · Cần cải thiện < 75.

---

## Chương 4 — Triển khai

### 4.1. Tiêu chí phân loại

| Nhóm | Định nghĩa |
|---|---|
| Có sẵn | Field/tính năng Odoo đã có, dùng nguyên |
| Customize | Sửa/mở rộng nghiệp vụ Odoo đã có (thêm field vào model gốc, kế thừa view/group) |
| Xây mới | Thành phần nghiệp vụ mới |

| Phạm vi | Định nghĩa |
|---|---|
| MVP | Bắt buộc để demo được |
| Nên có | Tăng tính thực tế |
| Mở rộng | Làm nếu còn thời gian / đề cương yêu cầu |

### 4.2. Bảng thống kê triển khai (38 hạng mục)

**Tổng hợp:** Có sẵn 10 · Customize 14 · Xây mới 14 — MVP 31 · Nên có 4 · Mở rộng 3.

Bảng đầy đủ (STT, nhóm, tính năng, Odoo hiện có, nội dung triển khai, Phase, phạm vi) nằm trong
[`lo-trinh-hoc-odoo-dev.md`](lo-trinh-hoc-odoo-dev.md) mục "Bảng thống kê triển khai" — đây là tài
liệu phân tích gốc dùng xuyên suốt quá trình xây dựng, không sao chép lại ở đây để tránh hai bản dễ
lệch nhau khi cập nhật. Tóm tắt theo Phase:

| Phase | Nội dung | Phạm vi |
|---|---|---|
| 0 | Môi trường Docker, khung module | MVP |
| 1 | `kpi.metric`, `kpi.template`, gắn `hr.job` | MVP |
| 2 | Field KPI trên `project.task`, `date_end`, số ngày trễ | MVP |
| 3 | `kpi.period`, `kpi.evaluation`, công thức điểm, quy trình duyệt | MVP |
| 4 | `kpi.engine` (D1–D8) | MVP |
| 5 | 3 nhóm quyền, record rule | MVP |
| 6 | Dashboard, báo cáo, kiểm tra chất lượng dữ liệu | MVP |
| 7 | Wizard tạo phiếu hàng loạt, Settings | Nên có |
| 8 | Bộ KPI Tester (chứng minh mở rộng không sửa code) | Nên có |
| 9 | Cron cuối kỳ, báo cáo PDF, REST API | Mở rộng |
| 10 | Cấu hình deploy production | Bàn giao |

### 4.3. Công nghệ sử dụng

Odoo 19 (Python 3.12, PostgreSQL 16), Docker/Docker Compose, QWeb (báo cáo PDF), nginx + Let's
Encrypt (production). Không dùng framework/thư viện ngoài hệ sinh thái Odoo chuẩn.

---

## Chương 5 — Kiểm thử

### 5.1. Chiến lược kiểm thử

- **Unit test tự động** (`odoo.tests.TransactionCase`/`HttpCase`), chạy bằng
  `--test-tags /project_kpi_management`, trên **database tạo mới hoàn toàn** mỗi lần — không chỉ
  chạy lại trên database đã có sẵn dữ liệu, để đảm bảo không phụ thuộc trạng thái còn sót.
- **Kiểm thử thủ công bổ sung** cho các phần khó mô phỏng đầy đủ trong unit test: gọi REST API thật
  qua HTTP bằng API key thật, render PDF thật và đọc nội dung, đăng nhập 3 vai trò qua XML-RPC.
- Một bài test riêng (`test_happy_path_full_approval_cycle`) **nối liền toàn bộ chu trình** (dữ
  liệu thật → Engine tính thật → Gửi duyệt → Duyệt → khoá) trong một lần chạy, để bắt lỗi chỉ lộ ra
  khi các bước ghép với nhau — bổ sung cho các test kiểm từng khúc rời.

### 5.2. Môi trường kiểm thử

Odoo 19.0, PostgreSQL 16, chạy trong container Docker (`odoo19-web`, `odoo19-db`). Lệnh chạy:

```bash
docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management \
  --test-tags /project_kpi_management --stop-after-init --http-port 8070
```

### 5.3. Danh sách test case (109 test, 12 file)

#### `tests/test_kpi_config.py` — 9 test (Phase 1: chỉ số, bộ KPI)

| Test | Kiểm tra |
|---|---|
| `test_data_loaded` | Dữ liệu D1–D9 và bộ Developer (9 dòng, tổng 100) có sau khi cài |
| `test_display_name_and_search` | `display_name` ghép đúng "mã — tên", tìm theo mã hoạt động |
| `test_empty_template_allowed` | Bộ KPI chưa có dòng vẫn lưu được |
| `test_total_weight_must_be_100` | Tổng ≠ 100 bị chặn khi tạo, khi sửa, khi xoá dòng |
| `test_update_and_add_line_in_one_save` | Sửa dòng cũ + thêm dòng mới cùng lúc, tổng đúng 100 → lưu được (bẫy "nửa chừng") |
| `test_duplicate_metric_code` | Trùng mã chỉ số bị chặn (ràng buộc SQL) |
| `test_duplicate_metric_in_template` | Một chỉ số xuất hiện 2 lần trong cùng bộ KPI bị chặn |
| `test_archive_metric_used_in_active_template` | Ẩn chỉ số đang dùng trong bộ KPI còn hoạt động bị chặn; chỉ số không dùng thì ẩn được |
| `test_archive_template_linked_to_job` | Ẩn bộ KPI đang gắn chức danh bị chặn; gỡ gắn kết rồi ẩn được |

#### `tests/test_kpi_domain_metric.py` — 8 test (Bước 1, Chương 9.1: chỉ số cấu hình không cần code)

| Test | Kiểm tra |
|---|---|
| `test_model_outside_allowed_list_blocked` | Chọn model ngoài danh sách cho phép (`res.partner`) bị chặn khi lưu |
| `test_field_from_other_model_blocked` | Chọn field không thuộc `source_model_id` bị chặn |
| `test_invalid_domain_syntax_blocked` | Domain sai cú pháp (thiếu `]`) bị chặn — thử `search_count()` thật khi lưu |
| `test_ratio_without_denominator_blocked` | Chọn Tỷ lệ mà không nhập domain mẫu số bị chặn |
| `test_sum_without_value_field_blocked` | Chọn Tổng mà không chọn field số bị chặn |
| `test_valid_config_saved` | Cấu hình hợp lệ lưu được bình thường |
| `test_only_admin_writes_domain_config` | Chỉ KPI Admin tạo/sửa được chỉ số cấu hình |
| `test_only_admin_opens_test_wizard` | Gọi thẳng `action_open_test_wizard()` qua ORM (bỏ qua nút) vẫn bị chặn đúng với người không phải KPI Admin (Bước 0) |

#### `tests/test_kpi_target_override.py` — 4 test (Mục tiêu riêng theo nhân viên/phòng ban)

| Test | Kiểm tra |
|---|---|
| `test_no_override_uses_template_target` | Không có override thì dùng đúng mục tiêu mặc định của template |
| `test_department_override` | Có override theo phòng ban thì dùng mục tiêu đó thay cho template |
| `test_employee_override_wins_over_department` | Có cả hai thì ưu tiên override theo nhân viên |
| `test_override_after_creation_does_not_change_existing_evaluation` | Tạo override sau khi đã có phiếu không làm đổi mục tiêu của phiếu cũ |

#### `tests/test_project_task.py` — 7 test (Phase 2: dữ liệu task)

| Test | Kiểm tra |
|---|---|
| `test_date_end_set_when_done_on_non_fold_stage` | Task Done trên stage không fold vẫn được tự ghi `date_end` |
| `test_date_end_survives_stage_change` | `date_end` không mất khi đổi stage sau đó, nếu task vẫn Done |
| `test_create_done_task` | Tạo task với `state=1_done` ngay từ đầu vẫn có `date_end` |
| `test_review_reject_count` | Đếm đúng số lần bị trả về, không đếm khi ghi lại cùng trạng thái |
| `test_days_late` | Đúng hạn, trễ (đã xong), quá hạn (chưa xong), đã huỷ → đúng số ngày trễ tương ứng |
| `test_cron_only_writes_when_days_late_changes` | Cron không ghi `write_date` cho task mà `days_late` không đổi; có ghi khi giá trị thật sự đổi |
| `test_bug_link_to_origin` | Bug liên kết đúng về task gốc; task không thể là task gốc của chính nó |

#### `tests/test_kpi_evaluation.py` — 15 test (Phase 3: phiếu, công thức điểm, quy trình)

| Test | Kiểm tra |
|---|---|
| `test_snapshot_from_template_and_employee` | Phiếu chụp đúng dữ liệu từ template; sửa template sau đó không ảnh hưởng phiếu cũ |
| `test_one_evaluation_per_employee_period` | Mỗi nhân viên chỉ 1 phiếu/kỳ (ràng buộc SQL) |
| `test_empty_template_blocked` | Không tạo được phiếu từ bộ KPI rỗng |
| `test_closed_period_blocked` | Không tạo phiếu trong kỳ đã đóng |
| `test_score_formula` | Công thức 2 chiều, trần 120, đúng với nhiều chỉ số pha trộn |
| `test_not_applicable_excluded` | Chỉ số không đạt khối lượng tối thiểu bị loại khỏi tử số và mẫu số |
| `test_insufficient_data_needs_manual_rating` | Trọng số áp dụng < 50 → bắt buộc xếp loại thủ công mới gửi duyệt được |
| `test_rating_boundaries` | Ranh giới xếp loại đúng theo khoảng nửa mở |
| `test_rating_uses_unrounded_score` | Điểm 89,9964 không bị làm tròn thành 90 rồi lên hạng sai |
| `test_adjustment_rules` | Điều chỉnh vượt biên độ bị chặn; khác 0 mà không có lý do bị chặn |
| `test_manual_metric_required_before_submit` | Chưa chấm D9 thì không gửi duyệt được |
| `test_workflow_lock_return_reopen` | Phiếu Đã gửi/Đã duyệt bị khoá; Trả về và Mở lại ghi lý do vào chatter |
| `test_submit_requires_compute` | Chưa Tính KPI thì không gửi duyệt được |
| `test_approve_requires_submitted` | Chỉ duyệt được phiếu Đã gửi |
| `test_target_editable_in_draft` | Mục tiêu sửa được khi còn Nháp |

#### `tests/test_kpi_engine.py` — 12 test (Phase 4: Engine)

| Test | Kiểm tra |
|---|---|
| `test_d1_on_time` | D1: đúng hạn, trễ, quá hạn chưa xong, huỷ, chưa tới hạn, ngoài kỳ |
| `test_d2_story_points` | D2: chỉ cộng SP của task Done trong kỳ |
| `test_d3_d4_counted_bugs` | D3/D4: đúng quy tắc "bug tính KPI", task gốc nhiều người được giao thì tính cho cả hai |
| `test_domain_metric_equivalent_to_d4` | Chỉ số cấu hình thuần domain (Bước 1) cho ra đúng kết quả như hàm Python `_metric_d4()` trên cùng dữ liệu, kể cả khi có bản ghi đã lưu trữ (Bước 0) |
| `test_domain_metric_datetime_field_includes_last_day_of_period` | Field Datetime (`date_deadline`) tính đúng nửa khoảng, kể cả bản ghi sát biên cuối kỳ (Bước 0) |
| `test_domain_metric_date_field_includes_last_day_of_period` | Field Date (`project.milestone.deadline`) lọc đúng kiểu Date, không lệch múi giờ (Bước 0) |
| `test_d5_d6_review_and_unit_test` | D5/D6: mẫu số đúng là task đã qua review / task Feature Done |
| `test_d7_high_priority_bugs` | D7: chỉ tính bug High/Urgent, đúng trung bình giờ làm việc |
| `test_d8_knowledge_sharing_events` | D8: chỉ đếm sự kiện đúng nhãn, đúng người tổ chức |
| `test_manual_metric_skipped` | Chỉ số nhập tay (D9) Engine trả về `None`, không tính |
| `test_employee_without_user` | Nhân viên chưa có tài khoản → báo lỗi rõ ràng, không trả về 0 |
| `test_compute_on_evaluation` | Gọi qua `action_compute_kpi()` từ phiếu, không ghi đè chỉ số nhập tay |

#### `tests/test_kpi_demo_scenario.py` — 10 test (đối chiếu bảng tính tay)

| Test | Kiểm tra |
|---|---|
| `test_actual_per_metric` | `(actual, volume)` của 3 nhân viên mẫu khớp bảng tính tay cho cả 8 chỉ số |
| `test_scores_and_ratings` | Điểm KPI, trọng số áp dụng, xếp loại khớp bảng tính tay |
| `test_binh_adjustment_reaches_pass` | Điều chỉnh +2 có lý do đưa điểm cuối lên đúng mức Đạt |
| `test_chi_insufficient_data` | Trọng số áp dụng 25% → xếp loại thủ công, gửi duyệt được sau khi chọn |
| `test_happy_path_full_approval_cycle` | **Luồng nối liền**: dữ liệu thật → Tính KPI → Gửi duyệt → Duyệt → khoá phiếu và dòng |
| `test_admin_manager_role_conflict` | Người vừa là quản lý trực tiếp vừa có thêm quyền Admin không tự duyệt được phiếu nhân viên mình quản lý, nhưng vẫn duyệt được phiếu nhân viên nhóm khác |
| `test_pip_activity_on_improve_rating` | Duyệt phiếu Cần cải thiện tạo đúng 1 nhắc việc PIP cho quản lý trực tiếp; Mở lại rồi Duyệt lại không tạo trùng |
| `test_no_pip_activity_when_not_improve` | Phiếu không xếp loại Cần cải thiện thì không tạo nhắc việc PIP |
| `test_self_assessment_wizard` | Chỉ chính nhân viên (không phải quản lý) tự đánh giá được qua wizard; không ai ghi trực tiếp được `employee_comment`/`self_score` qua `write()` lẫn `create()` (kể cả quản lý, vốn có quyền ghi phiếu/dòng phiếu khi Nháp); hết Nháp thì không tự đánh giá được nữa; `self_score` không ảnh hưởng `final_rating` |
| `test_copy_does_not_duplicate_self_assessment` | Nhân bản phiếu đã tự đánh giá không chép `employee_comment`/`self_score` sang phiếu mới, không bị chặn `create()` nhầm |

#### `tests/test_kpi_security.py` — 6 test (Phase 5: phân quyền)

| Test | Kiểm tra |
|---|---|
| `test_default_groups` | Nhóm mặc định đúng (User kéo theo mọi nhân viên, Manager kéo Project Manager) |
| `test_visibility` | Mỗi vai trò thấy đúng tập phiếu (của mình / nhóm / tất cả) |
| `test_user_read_only` | Nhân viên không tự sửa được phiếu của mình |
| `test_manager_scope` | Quản lý sửa được phiếu nhân viên trực tiếp, **không** sửa được phiếu của chính mình hay nhóm khác |
| `test_only_admin_approves` | Chỉ Admin duyệt/trả về/mở lại được |
| `test_has_unit_test_manager_only` | Chỉ Manager ghi được `has_unit_test` |

#### `tests/test_kpi_reports.py` — 10 test (Phase 6–8: báo cáo, wizard, Settings, Tester)

| Test | Kiểm tra |
|---|---|
| `test_generate_wizard` | Wizard lọc đúng theo phòng ban, bỏ qua người đã có phiếu/thiếu điều kiện |
| `test_recompute_server_action` | Hành động "Tính lại KPI" hàng loạt, bỏ qua phiếu không ở Nháp |
| `test_settings_change_rating_after_recompute` | Đổi ngưỡng ở Settings rồi Tính lại KPI thì xếp loại đổi theo (bắt đúng lỗi `add_to_compute` thiếu field) |
| `test_settings_validation` | Ngưỡng/điểm trần sai thứ tự hoặc sai khoảng bị chặn khi lưu Settings |
| `test_late_bugs` | Bug tạo sau lúc duyệt được tính đúng vào "Bug phát sinh muộn" |
| `test_data_quality_report` | SQL view tính đúng số liệu, tỷ lệ |
| `test_team_report_by_project` | SQL view `kpi.team.report` tính đúng tỷ lệ đúng hạn, mật độ lỗi, tỷ lệ lỗi production, giờ sửa bug trung bình (Mục 5) |
| `test_team_report_attributes_bug_to_origin_project` | Bug ở dự án khác nhưng có task gốc thì tính vào dự án của task gốc (đúng quy ước D3/D4); bug không có task gốc vẫn giữ dự án của chính nó |
| `test_line_report_fields_and_employee_button` | Field lưu sẵn trên dòng phiếu đúng; smart button trên hồ sơ nhân viên đúng domain |
| `test_tester_template_without_code` | Chức danh Tester gắn bộ "Tester (tự động)" gồm QA1–QA5 và tính điểm đúng — không cần sửa code |

#### `tests/test_kpi_tester.py` — 12 test (Bước 2, Chương 9.2: bộ KPI Tester tự động)

| Test | Kiểm tra |
|---|---|
| `test_t4_t6_have_no_python_code` | QA1–QA3 có `compute_mode = domain` và không tồn tại hàm `_metric_qa1/qa2/qa3`; QA4 có hàm riêng; QA5 nhập tay |
| `test_t4_counts_valid_bugs_of_reporter_only` | QA1 chỉ đếm bug valid/wont_fix của đúng người phát hiện |
| `test_t4_ignores_bugs_outside_period` | Bug ngoài kỳ không tính |
| `test_t5_t6_ratio` | Tử số/mẫu số QA2 (mẫu số = bug đã phân loại) và QA3 đúng |
| `test_below_min_volume_not_applicable` | Dưới khối lượng tối thiểu (3 bug) thì QA2, QA3 "Không áp dụng" |
| `test_t7_only_projects_where_tester_logged_bugs` | QA4 chỉ tính dự án tester có log bug trong kỳ, mẫu số gồm cả bug của người khác trong dự án đó |
| `test_t7_no_project_not_applicable` | Không log bug nào thì QA4 có khối lượng 0 |
| `test_bug_reporter_defaults_to_creator` | `bug_reporter_id` mặc định là người tạo |
| `test_bug_reporter_only_manager_edits` | Tester không sửa/không tạo kèm được `bug_reporter_id`; Manager sửa được |
| `test_migrate_backfills_old_bugs` | Bug cũ thiếu `bug_reporter_id` được bù bằng `create_uid` |
| `test_migrate_tester_template_on_upgraded_database` | Mô phỏng database đã cài bản cũ: chức danh Tester chuyển sang bộ mới, bộ cũ và T1–T3 bị ẩn, chạy lại không lỗi |
| `test_full_evaluation_matches_hand_calculation` | Phiếu đầy đủ cho 1 tester ra 46,5833 điểm đúng bảng tính tay (bắt luôn lỗi phiếu không tính chỉ số `domain`, xem 5.4) |

(`tests/test_kpi_demo_scenario.py` có thêm `test_dung_tester_evaluation`: tester mẫu Dung, 10 bug, ra 55,875 điểm — xếp loại "Cần cải thiện", nên khi demo duyệt phiếu của Dung sẽ tạo nhắc việc PIP; đây là chủ ý, cùng cơ chế với Bình.) Con số 71,0 trong `scripts/pre_defense_check.py` là phiếu của tester tự tạo trong script (3 bug), đã tính tay trước khi chạy: 3,333 + 6 + 16,667 + 30 + 15.

#### `tests/test_kpi_compute_paths.py` — 7 test (đi qua đúng hành động người dùng, rút kinh nghiệm lỗi ở 5.4)

Mọi đường tính KPI đều đi về `kpi.evaluation.action_compute_kpi()`, và điều kiện "chỉ số nào do engine tính" nay nằm ở **một hàm duy nhất**, `kpi.metric._is_engine_computed()` (engine, Tính KPI, REST API, view đều dùng hàm này, không tự so `compute_mode`).

| Test | Kiểm tra |
|---|---|
| `test_generate_wizard_computes_domain_metric` | Wizard tạo phiếu hàng loạt tính được chỉ số domain |
| `test_recompute_server_action_computes_domain_metric` | Hành động "Tính lại KPI" trên danh sách tính được chỉ số domain |
| `test_cron_computes_domain_metric` | Tác vụ cuối kỳ tính được chỉ số domain |
| `test_api_rejects_domain_metric` | REST API không cho ghi `actual` của chỉ số domain/Python (400), chỉ số nhập tay vẫn nhận |
| `test_single_rule_for_engine_computed` | Quy tắc `_is_engine_computed` đúng cho auto/domain/manual |
| `test_module_update_does_not_rerun_migrations` | Không file dữ liệu nào gọi hàm `_migrate_*` (tránh hoàn tác lựa chọn của Admin mỗi lần `-u`) |
| `test_post_migrate_script_renames_codes_once` | Script `post-migrate.py` đổi mã T4–T8 → QA1–QA5, chạy lại không lỗi |

**Quy ước cho các bước sau:** mỗi cơ chế mới phải có ít nhất một test đi qua hành động người dùng thật (nút, wizard, cron, API), không chỉ gọi thẳng engine.

#### `tests/test_kpi_integration.py` — 8 test (Phase 9: cron, PDF, REST API)

| Test | Kiểm tra |
|---|---|
| `test_cron_generates_once_for_finished_periods` | Cron tạo phiếu cho kỳ đã hết hạn, đánh dấu để không tạo lại |
| `test_cron_skips_closed_period` | Kỳ đã đóng không bị cron tạo phiếu |
| `test_pdf_report_content` | PDF chứa đủ thông tin: tên, mã chỉ số, điểm, tên quản lý |
| `test_requires_api_key` | Không có/sai API key → 401 |
| `test_list_respects_record_rules` | Danh sách qua API tuân theo quyền (quản lý không thấy phiếu nhóm khác) |
| `test_detail_and_not_found` | Phiếu không được xem trả về 404, không lộ là có tồn tại |
| `test_post_manual_metric` | Ghi số liệu chỉ số nhập tay qua API thành công |
| `test_post_rejected` | POST vào chỉ số tự động / thiếu field / sai quyền đều bị từ chối đúng mã lỗi |

### 5.4. Kết quả kiểm thử

**109/109 test đạt (0 failed, 0 error)**, xác nhận trên database tạo mới hoàn toàn (không chỉ chạy
lại trên database cũ), lần gần nhất 2026-10-12 — sau khi bổ sung 6 mục ở Chương 9 cũ (màu xếp loại,
chặn xung đột vai trò, nhắc việc PIP, mục tiêu theo phòng ban, chỉ số theo dự án, tự đánh giá), vá
thêm các phát hiện khi kiểm tra qua đường đi thật (xem 5.6): quản lý ghi trực tiếp được
`employee_comment`/`self_score` (cả qua `write()` lẫn `create()`), thiếu `copy=False` trên `self_score`
(Nhân bản phiếu đã tự đánh giá sẽ bị chặn nhầm), cron ghi `write_date` thừa, bug trong
`kpi.team.report` quy sai dự án (đã sửa ở Mục 5, Chương 3.3), và triển khai Bước 1 — chỉ số cấu hình
không cần code và rà soát bảo mật/kỹ thuật Bước 0 (Chương 9.1, +11 test), rồi Bước 2 — bộ KPI Tester tự động (Chương 9.2, +13 test). **Lỗi thật phát hiện khi làm Bước 2:** phiếu KPI chỉ tự tính các chỉ số `compute_mode = auto`, bỏ sót `domain` — nên chỉ số cấu hình của Bước 1 chạy đúng ở `kpi.engine` nhưng bấm "Tính KPI" trên phiếu không ra số (test Bước 1 chỉ gọi thẳng engine nên không thấy); đã sửa ở `kpi_evaluation.action_compute_kpi` và khoá ô `actual` của chỉ số domain trên form. Kiểm thử qua đường đi thật cũng chạy `-u` lên bản sao của `kpi_dev` để xác nhận migration (xem 9.2).

**Quan trọng — hạn chế của `TransactionCase`:** unit test chạy bằng superuser (`env.su = True`),
nên bỏ qua một số kiểm tra chỉ áp dụng cho người dùng thật (ví dụ chặn xung đột vai trò). Vì vậy 77
test ở trên KHÔNG đủ để kết luận hệ thống đang chạy đúng — phải xác minh thêm qua 5.6.

### 5.5. Kiểm thử thủ công bổ sung (ngoài phạm vi unit test)

| Hạng mục | Cách kiểm | Kết quả |
|---|---|---|
| REST API qua HTTP thật | Tạo API key thật, gọi `curl` với `GET`/`POST` qua `X-Odoo-Database` header, kiểm tra round-trip tiếng Việt UTF-8 | Đạt — dữ liệu tiếng Việt (có dấu, ký tự `—`) ghi/đọc chính xác |
| Báo cáo PDF | Render PDF thật qua `_render_qweb_pdf`, đọc nội dung từng dòng | Đạt — số liệu khớp bảng tính tay, không còn chữ tiếng Anh |
| Phân quyền 3 vai trò qua XML-RPC | Đăng nhập thật 3 tài khoản, gọi `search_count`, thử sửa/duyệt trái quyền | Đạt — đúng số phiếu nhìn thấy, đúng chỗ bị từ chối |
| Luồng hoàn chỉnh trên hệ thống sống | Tạo phiếu → Tính KPI → Gửi duyệt → Duyệt qua `odoo shell`, không dùng dữ liệu giả lập | Đạt — điểm khớp bảng tính tay (113,31 cho nhân viên mẫu An) |
| Kịch bản mở rộng vai trò mới | Tạo phòng ban + chỉ số + bộ KPI + chức danh + nhân viên hoàn toàn mới, không sửa code | Đạt — xem Chương 7 |
| Dọn phụ thuộc dữ liệu demo gốc Odoo | Cài module không `--with-demo`, kiểm tra toàn database | Đạt — chỉ còn đúng 1 nhân viên "Administrator" |

### 5.6. Script kiểm tra nhanh trước buổi bảo vệ

`addons/project_kpi_management/scripts/pre_defense_check.py` — kiểm tra qua **XML-RPC thật**, đăng
nhập bằng đúng tài khoản sẽ dùng khi demo (`admin`, `quocviet`, `an`), không phải `TransactionCase`.
Lý do cần script riêng: sửa code trên đĩa không tự áp dụng cho một server Odoo đang chạy liên tục —
phải nạp lại module hoặc khởi động lại tiến trình trước, nếu không hệ thống đang chạy vẫn sai dù
code đã đúng và test đã đạt (đúng loại lỗi đã gặp khi viết script này, xem dưới).

Kiểm tra 8 bước (4 nhóm), tự tạo kỳ/phiếu test riêng và tự dọn sạch ở cuối (kể cả khi có bước FAIL),
không ảnh hưởng dữ liệu demo dùng để trình bày:

1. Chặn xung đột vai trò (Mục 2): quản lý được gán thêm quyền Admin vẫn bị chặn khi duyệt phiếu
   nhân viên mình quản lý.
2. Nhắc việc PIP (Mục 3): duyệt phiếu Cần cải thiện tạo đúng 1 nhắc việc.
3. Tự đánh giá (Mục 6, 4 bước): nhân viên ghi được qua wizard; người khác — **kể cả quản lý, vốn
   có quyền ghi phiếu/dòng phiếu khi Nháp** — không ghi trực tiếp được `employee_comment` (qua
   `write()`) lẫn `self_score` (qua cả `write()` và `create()` dòng phiếu mới), và không tạo được
   phiếu mới kèm sẵn `employee_comment`.
4. Mục tiêu theo phòng ban (Mục 4): phiếu mới nhận đúng mục tiêu riêng.

Cách chạy trước khi bảo vệ:

```bash
docker compose exec odoo odoo -d kpi_dev -u project_kpi_management --stop-after-init
docker compose restart odoo
docker compose exec odoo python3 /mnt/extra-addons/project_kpi_management/scripts/pre_defense_check.py --db kpi_dev
```

In `KẾT QUẢ: tất cả OK — có thể demo.` thì yên tâm. Script này tự nó đã bắt được nhiều lỗi thật khi
viết (không phải chỉ lý thuyết): quản lý ghi trực tiếp được `employee_comment` qua `write()` (đã
sửa), sau đó rà lại theo đúng kiểu lỗi đó thì thấy thêm `self_score` trên dòng phiếu và cả đường
`create()` của cả hai field cũng bị lách tương tự (đã chặn ở cả `create()` lẫn `write()`, xem
Chương 3.3) — cộng thêm 2 lỗi thao tác khi viết chính script (chạy lần đầu trên container chưa nạp
lại code, và nhầm trạng thái phiếu sau khi Mở lại). Tất cả đã sửa và xác minh lại bằng cách chạy
script nhiều lần liên tiếp, không còn cảnh báo dọn dẹp.

### 5.6b. Cấu hình môi trường dev (clone repo mới)

`config/odoo.conf` **không** nằm trong Git (có mật khẩu master). Sau khi clone, chạy một lần trước `docker compose up`:

```bash
cp config/odoo.conf.example config/odoo.conf   # rồi đổi admin_passwd khỏi change_me
docker compose up -d
```

Mật khẩu `admin` cũ của dev vẫn còn trong lịch sử Git; môi trường dev nên coi như đã lộ và **server production
(Chương 7, thư mục `deploy/`) phải dùng mật khẩu khác** — các file `deploy/` chỉ chứa giá trị giữ chỗ
(`DOI_MAT_KHAU_*`), mật khẩu thật nằm trong `.env`/`odoo.conf` không commit.

### 5.7. Quy trình đúng ngày bảo vệ

Container Odoo đọc code trực tiếp từ thư mục `addons` trên đĩa. Nếu phát triển tiếp trên `main` sau
mốc `v1.0-bao-ve` (Chương 10) mà đến ngày bảo vệ quên chuyển về đúng tag, buổi demo sẽ chạy code
đang làm dở — không phải bản đã kiểm chứng đủ 78 test và 8 bước `pre_defense_check.py`.

```bash
git stash                      # nếu còn thay đổi chưa commit trên main
git checkout v1.0-bao-ve
docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management --stop-after-init
docker restart odoo19-web
python scripts/pre_defense_check.py --db kpi_dev   # phải OK cả 8 bước
# ... bảo vệ xong ...
git checkout main
git stash pop                  # nếu có stash ở bước đầu
```

Bước `-u project_kpi_management` + khởi động lại container là bắt buộc, không phải tuỳ chọn — lý do
đã nêu ở Chương 5.6: sửa file trên đĩa (hoặc đổi nhánh/tag như ở đây) không tự áp dụng cho tiến
trình Odoo đang chạy.

---

## Chương 6 — Hướng dẫn sử dụng

Hướng dẫn **đầy đủ theo từng Phase** (thao tác UI + vị trí source) nằm ở
[`TRIEN_KHAI_HE_THONG.md`](TRIEN_KHAI_HE_THONG.md). Mục này tóm tắt nhanh theo **vai trò người
dùng cuối** (không cần biết Phase nào).

### 6.1. Vai trò KPI Administrator (quản trị hệ thống)

1. Cấu hình chỉ số, bộ KPI, gắn vào chức danh (**KPI › Cấu hình**).
2. Tạo kỳ đánh giá, tạo phiếu hàng loạt (**KPI › Đánh giá › Tạo phiếu cho kỳ**).
3. Duyệt / Trả về / Mở lại phiếu.
4. Chỉnh ngưỡng xếp loại, điểm trần, biên độ điều chỉnh (**KPI › Cấu hình › Thiết lập**).
5. Theo dõi chất lượng dữ liệu (**KPI › Báo cáo › Kiểm tra dữ liệu**).

### 6.2. Vai trò Quản lý trực tiếp

1. Mở phiếu của nhân viên mình quản lý, bấm **Tính KPI**.
2. Chấm D9 (thang 1–5), kiểm tra các dòng *Không áp dụng* (nếu có, cần chọn xếp loại thủ công).
3. Điều chỉnh điểm nếu cần (bắt buộc ghi lý do).
4. Bấm **Gửi duyệt**.
5. Xem báo cáo của nhóm mình (**KPI › Báo cáo**).

### 6.3. Vai trò Nhân viên

Xem phiếu của mình (**KPI › Đánh giá › Phiếu đánh giá**), xem lịch sử thao tác ở tab chatter, không
sửa được gì (chỉ đọc).

### 6.4. Cấu hình bắt buộc trước khi dùng thật

Stage "Done"/"Hoàn thành" của **mọi dự án** phải bật **Folded** (xem Chương 2.5 và
`TRIEN_KHAI_HE_THONG.md` Phase 2) — thiếu bước này, D1 và D7 sẽ sai mà không có cảnh báo nào.

---

## Chương 7 — Demo minh hoạ khả năng mở rộng

Để chứng minh nguyên tắc "không hardcode vai trò" (Chương 2.4) không chỉ là khẳng định, đồ án có
2 minh chứng cụ thể:

### 7.1. Bộ KPI "Tester" (có sẵn trong dữ liệu cấu hình, Phase 8)

Phase 8 cài sẵn bộ "Tester" gồm 3 chỉ số nhập tay (T1–T3) + D9. **Từ Bước 2 bộ này được thay bằng
"Tester (tự động)"** (QA1–QA5, xem Chương 9.2), vẫn gắn vào chức danh "Kiểm thử phần mềm (QA)". QA1–QA3
chỉ nằm trong file dữ liệu (`data/kpi_org_data.xml`), **không có một dòng code nào** — đúng tinh thần của
phần này; riêng QA4 cần một hàm Python vì tập dự án suy ra từ chính dữ liệu bug.

### 7.2. Demo trực tiếp: dựng vai trò "Sales" hoàn toàn mới khi thuyết trình

Kịch bản đề xuất trình diễn trước hội đồng (khoảng 3 phút, làm trực tiếp trên giao diện):

1. **Nhân viên › Phòng ban** — tạo "Phòng Kinh doanh".
2. **KPI › Cấu hình › Chỉ số KPI** — tạo chỉ số mới "S1 — Doanh số đạt được", *Cách tính = Nhập tay*.
3. **KPI › Cấu hình › Bộ KPI** — tạo bộ "Sales": dòng S1 (trọng số 80) + dòng D9 có sẵn (trọng số 20).
4. **Nhân viên › Cấu hình › Tuyển dụng › Vị trí công việc** — tạo chức danh "Nhân viên kinh doanh",
   chọn *Bộ KPI = Sales*.
5. Tạo một nhân viên mới với chức danh đó.
6. **KPI › Đánh giá › Tạo phiếu cho kỳ** — hệ thống **tự nhận ra** nhân viên này mà không cần sửa
   file hay restart module.
7. Nhập S1 và D9, bấm **Tính KPI** → **Gửi duyệt**.

Kịch bản này đã được chạy thử và xác nhận chạy đúng (xem Chương 5.5, dòng "Kịch bản mở rộng vai trò
mới"): wizard tự nhận diện nhân viên, phiếu tự chọn đúng bộ KPI, điểm tính đúng công thức, gửi
duyệt thành công.

---

## Chương 8 — Đối tượng áp dụng và giới hạn

### 8.1. Đối tượng áp dụng

Doanh nghiệp quản lý dự án phần mềm bằng **Odoo Project**, đánh giá nhân sự theo **kỳ** (không theo
từng task), có cấu trúc quản lý trực tiếp rõ ràng.

### 8.2. KPI là công cụ hỗ trợ, không thay thế người quản lý

Hệ thống cho phép quản lý **điều chỉnh mục tiêu** (khi phiếu Nháp), **điều chỉnh điểm** (±10, bắt
buộc lý do) và **chấm chỉ số định tính** (D9) — số liệu tự động không phải tiếng nói cuối cùng.

### 8.3. Giới hạn đã biết

| Giới hạn | Mô tả | Mức ảnh hưởng |
|---|---|---|
| D5, D6 là chỉ số **proxy** (đo gián tiếp) | D5 dùng số lần bị trả về (`review_reject_count`) làm đại diện cho "pass review", không phải dữ liệu review thật từ công cụ review code. D6 dùng cờ `has_unit_test` do quản lý tự xác nhận, không kiểm tra coverage thật | Trung bình — phụ thuộc quản lý xác nhận trung thực |
| Mọi chỉ số phụ thuộc **việc nhập dữ liệu đúng** | Nếu task không gắn `story_points`, bug không phân loại `bug_resolution`/`bug_root_cause`, KPI sẽ sai mà hệ thống không tự phát hiện được — chỉ có thể *cảnh báo* qua "Kiểm tra dữ liệu" (Chương 6.1), không chặn được | Cao — đây là rủi ro vận hành lớn nhất |
| Stage Done phải cấu hình đúng | Nếu stage "Done" của một dự án không bật `Folded`, D1 và D7 của nhân viên làm việc trong dự án đó sẽ sai **mà không có cảnh báo** — đây là phụ thuộc vào hành vi nội bộ của Odoo (`date_end` chỉ ghi khi fold), không kiểm soát được hoàn toàn từ phía module | Cao nếu bị bỏ sót lúc cấu hình dự án mới |
| Chỉ số tự động mới cần code | Thêm chỉ số *Tự động* hoàn toàn mới (ví dụ tính từ `sale.order`) cần viết thêm hàm `_metric_<mã>()` trong `kpi_engine.py` — không thể cấu hình thuần dữ liệu như chỉ số nhập tay | Thấp — là giới hạn tự nhiên, đã nêu rõ ở Chương 2.4 |
| REST API phụ thuộc cấu hình multi-database | Môi trường có nhiều database và chưa đặt `dbfilter` cần thêm header `X-Odoo-Database` khi gọi API — môi trường production (`deploy/`) đã cấu hình `dbfilter` cố định, không gặp vấn đề này | Thấp — chỉ ảnh hưởng môi trường dev |
| Cron cập nhật `days_late` ghi `write_date` dù giá trị không đổi | Đã kiểm chứng bằng script thật (không suy luận): `_cron_update_days_late()` gọi `flush_recordset(["days_late"])` cho mọi task quá hạn chưa xong mỗi ngày, và Odoo luôn ghi `write_date`/`write_uid` cùng lúc flush một field, kể cả khi `days_late` ra cùng giá trị cũ | Thấp — chỉ ảnh hưởng cách sắp xếp "mới cập nhật gần đây" ở các view khác, không ảnh hưởng điểm KPI |

---

## Chương 9 — Hướng phát triển

**Hệ thống đã qua điểm dừng tính năng trước bảo vệ** (xem Chương 5.6) — bản dùng để bảo vệ đóng
băng ở tag `v1.0-bao-ve` (Chương 10), không đổi. Nội dung chương này là kế hoạch mở rộng cho giai
đoạn **sau bảo vệ**, phát triển trực tiếp trên `main` (không tách nhánh riêng — tag đã giữ đúng mốc
bảo vệ nên không cần). **Bước 0+1 (9.1) và Bước 2 (9.2, Tester) đã triển khai** (109/109 test đạt); **Bước 3–6
chưa triển khai**, còn ở dạng thiết kế.

### 9.1. Điểm nghẽn lớn nhất: chỉ số tự động phải viết code — ĐÃ TRIỂN KHAI

Hệ thống đã linh hoạt ở phần **cấu hình** (bộ KPI theo chức danh, chỉ số nhập tay, mục tiêu theo
phòng ban/nhân viên, khối lượng tối thiểu — Chương 2.4, Chương 7). Nhưng mỗi chỉ số **tự động**
(`compute_mode = auto`) vẫn cần một hàm `_metric_<mã>()` viết bằng Python trong `kpi_engine.py`
(giới hạn tự nhiên đã nêu ở Chương 2.4). Hệ quả: thêm một bộ KPI tự động cho team mới (Tester, PM,
BA...) vẫn phải nhờ lập trình viên, dù phần cấu hình (template, trọng số, mục tiêu) đã tự làm được.

**Gỡ điểm nghẽn — chỉ số cấu hình không cần code (`compute_mode = domain`, chi tiết ở Chương 3.3):**
thêm cho `kpi.metric` một cách tính tự động theo kiểu **đếm/tổng/trung bình/tỷ lệ trên domain**,
không cần hàm Python riêng: chọn model dữ liệu nguồn, field người phụ trách và field ngày (tuỳ
chọn, để lọc theo nhân viên/kỳ), domain tử số và domain mẫu số (khi Tỷ lệ). Đây **không phải ý
tưởng mới tự nghĩ ra** — Odoo Community đã làm đúng cách này trong module `gamification`
(`gamification.goal.definition`, đã kiểm tra trên source 19.0): `model_id`, `field_id`,
`field_date_id`, `domain`, `computation_mode` (`count`/`sum`/`manually`, và cả `python` cho code tuỳ
ý). **Chỉ lấy lại phần `domain` + `count`/`sum`** (dữ liệu, an toàn, không chạy được code tuỳ ý) —
**không** lấy lại `computation_mode = python` vì cho nhập Python tuỳ ý qua giao diện là lỗ hổng bảo
mật, đi ngược nguyên tắc "không hardcode nhưng vẫn kiểm soát được" của module này. Thêm `avg`
(trung bình) và `ratio` (tỷ lệ, hai domain riêng cho tử số/mẫu số) so với bản gốc của `gamification`
— cần cho hầu hết chỉ số KPI (D1, D3–D6 đều là tỷ lệ hoặc trung bình, không chỉ đếm/tổng).

Bằng chứng đây là nền móng dùng được, không chỉ ý tưởng: test `test_domain_metric_equivalent_to_d4`
cấu hình một chỉ số thuần domain (không viết dòng code nào) cho ra **đúng kết quả** như hàm Python
`_metric_d4()` trên cùng dữ liệu — kể cả phần khó nhất của D4 (quy bug về task gốc qua quan hệ
`origin_task_id.user_ids`), bằng cách để trống `user_field_id`/`date_field_id` và viết đủ điều kiện
trong domain với biến `user`/`start`/`end`. Có nó, Admin tự tạo chỉ số mới từ dữ liệu Odoo sẵn có
hoàn toàn trên giao diện (xem nút "Thử tính" trên form chỉ số), mở khoá toàn bộ phần mở rộng team ở
9.2 mà không cần sửa `kpi_engine.py` thêm nữa.

### 9.2. Mở rộng sang team khác (theo thứ tự ưu tiên)

Thứ tự dựa trên mức quan trọng trong công ty sản xuất phần mềm và dữ liệu đã có sẵn trong Odoo tới
đâu — team nào dữ liệu có sẵn càng nhiều thì làm càng sớm.

**Ưu tiên 1 — Tester/QA (nâng từ nhập tay lên tự động) — ĐÃ TRIỂN KHAI (Bước 2):** gần Dev nhất, dữ liệu
bug ở Phase 2 dùng lại gần hết. Khi triển khai đã **đổi thiết kế so với bản đề xuất ban đầu**: người log
bug không dùng `create_uid` mà thêm field `bug_reporter_id` (xem Chương 3.3), vì PM có thể log bug hộ tester
hoặc bug được import — dùng `create_uid` sẽ quy sai người. Field này chỉ KPI Manager sửa được, nếu không
tester có thể gán bug người khác log về mình để tăng QA1.

| Mã | Chỉ số | Cách tính | Chiều | Mục tiêu | Trọng số | Khối lượng tối thiểu |
|---|---|---|---|---|---|---|
| QA1 | Số bug hợp lệ tìm được | **Domain, đếm**: `bug_resolution` ∈ {valid, wont_fix}, người = `bug_reporter_id`, ngày = `create_date` | Cao tốt | 15 | 25 | 0 |
| QA2 | Tỷ lệ bug bị từ chối | **Domain, tỷ lệ**: invalid + duplicate / bug đã phân loại (`bug_resolution` khác rỗng) | Thấp tốt | 10% | 20 | 3 |
| QA3 | Tỷ lệ bug đủ phân loại | **Domain, tỷ lệ**: bug có `origin_task_id` và `bug_root_cause` / mọi bug tester log | Cao tốt | 90% | 15 | 3 |
| QA4 | Lỗi lọt production của dự án tham gia | **Python `_metric_qa4()`**: bug production / bug hợp lệ trong các dự án tester đã log bug trong kỳ; khối lượng = số dự án | Thấp tốt | 5% | 25 | 1 dự án |
| QA5 | Đánh giá của quản lý | Nhập tay (như D9) | Cao tốt | 4 | 15 | 0 |

**Vì sao mã là QA1–QA5:** đề xuất ban đầu đặt T1–T5, nhưng T1–T3 đã bị bộ Tester cũ (Phase 8, nhập tay)
chiếm trên database đã cài, mà mã chỉ số là `UNIQUE`. Bản triển khai đầu dùng T4–T8 nhưng "T4" lại trùng tên với
"lỗi lọt production" ở bản thiết kế cũ nên dễ nhầm, vì vậy đổi sang tiền tố **QA** — không trùng mã nào, đọc vào
biết thuộc bộ Tester/QA. Các bản ghi cũ nằm trong dữ liệu `noupdate="1"` nên sửa XML rồi `-u` **không** đổi được
chúng; việc chuyển được làm bằng script nâng cấp một lần, không phải `<function>` chạy mỗi lần `-u`
(lý do: chạy mỗi lần sẽ âm thầm hoàn tác lựa chọn của Admin, ví dụ gắn lại chức danh vào bộ khác):

| Script (nâng cấp từ bản cũ lên 19.0.1.1.0) | Việc làm |
|---|---|
| `migrations/19.0.1.1.0/pre-migrate.py` | Đổi tên xmlid `kpi_metric_t4..t8` → `kpi_metric_qa1..qa5` để dữ liệu XML mới nhận ra bản ghi cũ, không tạo trùng |
| `migrations/19.0.1.1.0/post-migrate.py` | Đổi mã T4–T8 → QA1–QA5; bù `bug_reporter_id`; chuyển chức danh Tester sang bộ "Tester (tự động)", ẩn bộ cũ và T1–T3 (chỉ chuyển khi chức danh còn trỏ về bộ cũ) |

Database mới cài không chạy script (không có bản cũ để nâng), dữ liệu XML đã đúng sẵn. Đã kiểm trên bản sao của `kpi_dev` (script chạy đúng 1 lần ở `-u` đầu, ghi log `pre-migrate`/`post-migrate`):
nâng cấp một lần ra đúng, Admin gắn lại bộ cũ rồi `-u` lần nữa thì lựa chọn được giữ nguyên.

**Rủi ro đã biết của QA1:** có thể bị lách bằng cách tách một lỗi thành nhiều bug để tăng số lượng. Hai lớp
chặn: QA2 (bug trùng/không hợp lệ làm tăng tỷ lệ bị từ chối, tính trừ điểm) và việc quản lý phân loại bug
(`bug_resolution`) trước khi chốt kỳ — hệ thống không tự chặn hoàn toàn được, giống rủi ro của các chỉ số
proxy ở Chương 8.

QA3 gắn trực tiếp với báo cáo kiểm tra dữ liệu (Chương 3.3): tester log bug sạch thì KPI của Dev mới
đúng — một team phụ thuộc chất lượng dữ liệu của team khác.

**Ưu tiên 2 — Team Lead/PM:** Odoo Project có sẵn dữ liệu cấp dự án. `project.milestone` (đã kiểm
tra trên source 19.0) có `deadline`, `is_reached`, `reached_date`.

| Mã | Chỉ số | Nguồn dữ liệu | Chiều |
|---|---|---|---|
| P1 | Tỷ lệ milestone đạt đúng hạn | `reached_date ≤ deadline` | Cao tốt |
| P2 | Điểm KPI trung bình của team | `kpi.evaluation` của nhân viên cấp dưới | Cao tốt |
| P3 | Chất lượng dữ liệu dự án | `kpi.data.quality.report` của dự án phụ trách | Cao tốt |
| P4 | Giờ thực tế so với kế hoạch | `hr_timesheet` so với `allocated_hours` (cần thêm `hr_timesheet` vào `depends`) | Gần 100% tốt |
| P5 | Đánh giá của cấp trên | Nhập tay | Cao tốt |

P3 có ý nghĩa thực tế: PM chịu trách nhiệm về dữ liệu dự án, nên KPI của PM cũng phải phụ thuộc vào
việc dữ liệu có sạch hay không — không chỉ Dev mới bị ràng buộc bởi chất lượng dữ liệu.

**Ưu tiên 3 — BA:** dữ liệu có một phần (`bug_root_cause = requirement`), cần thêm loại task
"Requirement" và cách nối task tính năng với yêu cầu gốc.

| Mã | Chỉ số | Nguồn dữ liệu |
|---|---|---|
| B1 | Tỷ lệ yêu cầu bàn giao đúng hạn | Task loại Requirement |
| B2 | Tỷ lệ bug do yêu cầu sai | `bug_root_cause = requirement`, quy về BA của yêu cầu gốc |
| B3 | Số lần yêu cầu bị sửa sau khi chốt | Đếm lần trả về của task Requirement (dùng lại `review_reject_count`) |

**Để sau (ngoài phạm vi, khác bản chất):**

| Team | Lý do để sau |
|---|---|
| DevOps | Chỉ số chính (DORA) cần dữ liệu CI/CD từ hệ thống ngoài, không có sẵn trong Odoo |
| Support | Odoo Helpdesk là bản Enterprise; trên Community phải dùng task làm ticket, không chuẩn |
| Sales, HR | Không thuộc lõi sản xuất phần mềm — hệ thống đã **chứng minh làm được** bằng demo Sales nhập tay (Chương 7), không cần làm thêm để minh hoạ nguyên tắc không hardcode |

### 9.3. Tính năng khác giúp hệ thống linh hoạt hơn

| # | Tính năng | Vấn đề giải quyết | Cách làm | Giá trị |
|---|---|---|---|---|
| 1 | Chỉ số cấu hình không cần code | Xem 9.1 | Xem 9.1 — **đã triển khai** | Rất cao — mở khoá 9.2 |
| 2 | Cách chấm điểm theo bậc | Hiện chỉ có tỷ lệ tuyến tính (`_score()`, Chương 3.3); nhiều công ty chấm theo bậc, ví dụ ≥90% → 100 điểm, 80–90% → 80 điểm | Mỗi dòng template chọn "Tuyến tính" hoặc "Theo bảng bậc"; bảng bậc là các dòng (từ, đến, điểm) | Cao |
| 3 | Điểm team góp vào điểm cá nhân | Phần mềm là việc nhóm, nhưng điểm hiện hoàn toàn cá nhân | Một dòng template là "Điểm trung bình của team" (lấy từ `kpi.team.report`), trọng số 10–20% | Cao, đúng xu hướng ngành |
| 4 | Kỳ đánh giá khác nhau theo bộ KPI | Dev hợp chu kỳ tháng; BA, PM hợp chu kỳ quý | Thêm `period_type` cho template; wizard tạo phiếu chỉ tạo cho template cùng loại kỳ | Trung bình |
| 5 | Nhân viên kiêm nhiệm | Một người vừa là Dev vừa là Team Lead | Cho phiếu nhận thêm template phụ, gộp dòng và chuẩn hoá trọng số về 100 | Trung bình, phức tạp hơn |

### 9.4. Thứ tự triển khai đề xuất (khi làm tiếp sau bảo vệ)

| Bước | Việc | Lý do thứ tự |
|---|---|---|
| 1 | ~~Chỉ số cấu hình không cần code (9.1)~~ | **Đã triển khai** — xem Chương 3.3 |
| 2 | ~~Bộ Tester tự động (9.2, Ưu tiên 1)~~ | **Đã triển khai** — 109/109 test đạt, xem 9.2 |
| 3 | Chấm điểm theo bậc (9.3 #2) | Nhiều công ty cần ngay khi áp dụng thật |
| 4 | Bộ Team Lead/PM + điểm team (9.2 Ưu tiên 2, 9.3 #3) | Cần dữ liệu milestone, timesheet |
| 5 | Bộ BA (9.2 Ưu tiên 3) | Cần thêm loại task Requirement |
| 6 | Kỳ khác nhau theo bộ KPI, kiêm nhiệm (9.3 #4, #5) | Chỉ cần khi đã có nhiều bộ KPI chạy song song |

### 9.5. Hướng mở rộng khác (đã nêu từ trước)

| Hướng | Nội dung |
|---|---|
| Nhân viên phản hồi đầy đủ hơn | Đã làm bản tham khảo (Mục 6: wizard Tự đánh giá, không cộng điểm, không thêm trạng thái); mở rộng tiếp theo hướng thêm bước "Nhân viên xác nhận" chính thức trong quy trình phiếu nếu cần |
| Đo theo team đầy đủ hơn | Đã làm bản gọn theo dự án (`kpi.team.report`, Chương 3.3); mở rộng tiếp theo hướng các bộ chỉ số DORA, SPACE (deploy frequency, lead time...) — xem 9.2, để sau vì cần tích hợp CI/CD ngoài |
| Đồng bộ Jira, GitLab | Dùng REST API (đã có sẵn khung) để lấy dữ liệu task, review từ công cụ ngoài |
| Coverage thật thay D6 | CI đẩy số liệu coverage thật qua REST API (`POST /api/kpi/evaluations/<id>/metrics/D6`), thay cho cờ tự xác nhận |
| Task Group / WBS | Xây model riêng khi cần quản lý theo nhóm việc có người phụ trách, người hỗ trợ |
| Thông báo | Nhắc hạn nộp phiếu, nhắc duyệt (đã làm riêng phần báo điểm thấp: duyệt phiếu Cần cải thiện tự tạo nhắc việc "Kế hoạch cải thiện" cho quản lý trực tiếp, xem Chương 5.3) |

---

## Chương 10 — Kết luận

Đồ án đã xây dựng hoàn chỉnh module `project_kpi_management` trên Odoo 19, đáp ứng toàn bộ phạm vi
MVP (31/31 hạng mục) và phần lớn phạm vi Nên có/Mở rộng (7/7 hạng mục), tổng cộng 38/38 hạng mục
trong bảng thống kê triển khai, cộng thêm 6 mục mở rộng sau khi đối chiếu với các hệ thống KPI tương
tự (màu xếp loại, chặn xung đột vai trò, nhắc việc PIP, mục tiêu theo phòng ban, chỉ số theo dự án,
tự đánh giá — Chương 9 cũ, nay đã triển khai). Hệ thống có 78 unit test tự động (0 lỗi) cộng với
kiểm thử thủ công trên REST API, báo cáo PDF, phân quyền, luồng nghiệp vụ hoàn chỉnh trên dữ liệu
thật, và kiểm tra qua đúng tài khoản thật bằng XML-RPC (`scripts/pre_defense_check.py`, Chương 5.6)
— cách kiểm tra này tự nó đã bắt được một số lỗi mà unit test (chạy bằng superuser) không bắt được.
Nguyên tắc thiết kế cốt lõi — không hardcode vai trò — đã được kiểm chứng bằng demo trực tiếp
(Chương 7), không chỉ dừng ở khẳng định lý thuyết. Các giới hạn còn tồn tại (Chương 8.3) đều đã được
xác định rõ ràng, có hướng xử lý cụ thể (Chương 9), phù hợp để trình bày minh bạch trước hội đồng.

Bản dùng để bảo vệ được đóng băng ở tag Git `v1.0-bao-ve` — quy trình chuyển đúng về bản này vào
ngày bảo vệ nằm ở Chương 5.7. Phát triển tiếp theo hướng Chương 9 (sau bảo vệ) đi trên `main`, không
ảnh hưởng tag này.

---

## Phụ lục — Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| KPI | Key Performance Indicator — chỉ số đánh giá hiệu suất |
| Proxy metric | Chỉ số đo gián tiếp (dùng dữ liệu có sẵn làm đại diện cho thứ khó đo trực tiếp) |
| Record rule | Cơ chế lọc dữ liệu theo quyền trong Odoo (ai thấy bản ghi nào) |
| Compute field | Field tính tự động từ field khác, có thể `store=True` (lưu vào DB) hoặc không |
| `models.Constraint` | Cú pháp khai báo ràng buộc SQL trong Odoo 19 (thay `_sql_constraints` cũ) |
| `xmlid` | Định danh duy nhất của một bản ghi dữ liệu, dạng `module.ten_ban_ghi` |
| `noupdate="1"` | Thuộc tính trong data XML: lệnh cập nhật module (`-u`) không ghi đè bản ghi này |
