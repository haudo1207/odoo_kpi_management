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
└── tests/                           19 file, 183 test

addons/project_kpi_timesheet/            Module cầu nối (Bước 4): P4 + bộ "Team Lead / PM (có giờ làm)", 6 test riêng
addons/project_kpi_skills/               Module cầu nối (Đợt D2): S1 mức đáp ứng kỹ năng + bộ "Developer (có năng lực)", 9 test riêng
addons/project_kpi_survey/               Module cầu nối (Đợt D1): F1 phản hồi 360 độ qua survey + bộ "Developer (có phản hồi 360)", 8 test riêng
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
| 20 | `kpi.score.scale` | Model | Bảng bậc điểm (Bước 3, Chương 9.3): tên + các bậc; chỉ Admin sửa |
| 21 | `kpi.score.scale.step` | Model | Một bậc: `pct_from` (% đạt mục tiêu bắt đầu), `score`, `pct_to` (compute) |
| 22 | `kpi.acknowledge.wizard` | TransientModel | Nhân viên xác nhận kết quả sau khi phiếu Đã duyệt (Đợt A2, Chương 9.6) |
| 23 | `kpi.manager.issue` | TransientModel | Danh sách "Quản lý chưa có quyền KPI" (lỗi cấu hình cần sửa tận gốc, Đợt B) |
| — | `kpi.feedback.request`, `kpi.feedback.invite.wizard` | Model, TransientModel | Chỉ có khi cài `project_kpi_survey` (Đợt D1): lời mời đánh giá 360 (ai được mời, đã trả lời chưa) và wizard "Mời đánh giá 360" |

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
| `ack_decision`, `ack_comment`, `ack_date` | Selection (agree/disagree), Text, Datetime | copy=False, readonly | Đợt A2 — nhân viên xác nhận kết quả SAU khi Đã duyệt; chỉ ghi qua wizard bằng `sudo()` (chặn ghi trực tiếp ở `create`/`write`, kể cả admin); mở lại phiếu thì xoá |
| `last_computed_date` | Datetime | copy=False, readonly | Đợt A3 — lần tính gần nhất, kể cả tạm tính tự động; `computed_date` vẫn chỉ ghi khi quản lý chủ động Tính KPI (điều kiện Gửi duyệt) |
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
| `task_type` | Selection (feature/bug/requirement), required, default feature | Phân loại; `requirement` thêm ở Bước 5 (BA) |
| `story_points` | Float, digits(16,1) | D2, D3 |
| `origin_task_id` | Many2one tự tham chiếu (`domain="[('id','!=',id)]"`) | D3, D4 — bug trỏ về task gốc |
| `bug_ids` | One2many ngược của `origin_task_id` | Hiển thị trên task gốc |
| `is_production_bug` | Boolean | D4 |
| `bug_resolution` | Selection (valid/wont_fix/duplicate/invalid) | Lọc bug tính KPI |
| `bug_root_cause` | Selection (code/requirement/environment) | Lọc bug tính KPI |
| `requirement_id` | Many2one tự tham chiếu (domain: task loại Yêu cầu, cùng dự án) | B2 (Bước 5) — Feature trỏ về yêu cầu gốc; ràng buộc: phải là task loại Yêu cầu khác, cùng dự án |
| `is_on_time` | Boolean, compute, store | B1 (Bước 5) — task đã xong, có deadline, `days_late = 0` (cùng quy tắc ngày địa phương với D1; D1 giữ nguyên) |
| `bug_reporter_id` | Many2one `res.users`, default người tạo | QA1–QA4 (Bước 2) — người phát hiện bug; **không dùng `create_uid`** vì PM có thể log bug hộ tester hoặc bug được import. Chỉ KPI Manager trở lên ghi được (kiểm ở `create`/`write`, và khoá trên form); bug cũ được bù `bug_reporter_id = create_uid` đúng một lần khi nâng lên 19.0.1.1.0 (`migrations/19.0.1.1.0/post-migrate.py`) |
| `review_reject_count`, `review_approve_count` | Integer, readonly | D5 — tăng trong `write()` khi đổi state |
| `has_unit_test` | Boolean | D6 — chỉ KPI Manager ghi được (kiểm ở `create`/`write`) |
| `kpi_can_review` | Boolean, compute | Khoá ô `has_unit_test` trên form nếu không phải Manager |
| `days_late` | Integer, compute, store | D1 — so `date_end`/hôm nay với `date_deadline`, cron cập nhật hằng ngày |

#### Field mở rộng trên `hr.job`, `hr.employee`, `res.config.settings`

| Model | Field | Ghi chú |
|---|---|---|
| `kpi.period` | `dashboard_*` (compute, không lưu: số phiếu theo trạng thái, điểm TB đã duyệt, Cần cải thiện, thiếu dữ liệu, chờ xác nhận, lỗi dữ liệu hiện tại) | Đợt C1 — màn hình tổng quan; một `_read_group` cho mọi kỳ, không dùng sudo (record rule tự áp dụng) |
| `kpi.template` / `kpi.period` | `period_type` (Selection tháng/sprint/quý, mặc định tháng) | Đợt B1 — wizard và cron chỉ tạo phiếu cho bộ KPI cùng loại kỳ; không đổi loại kỳ của bộ khi còn phiếu ở kỳ đang mở |
| `kpi.target.override` | `suggestion_easy/medium/hard`, `suggestion_note` (compute, không lưu) | Đợt B2 — gợi ý mục tiêu từ lịch sử, nút Áp dụng |
| `hr.job` | `kpi_template_id` (Many2one, `ondelete=restrict`) | Trung tâm của nguyên tắc "không hardcode vai trò" |
| `project.milestone` | `is_reached_on_time` (Boolean, compute, store) | P1 (Bước 4) — đã đạt và `reached_date ≤ deadline` |
| `kpi.template.line` / `kpi.evaluation.line` | `scale_id` / `scale_json`, `scale_name`, `achievement_pct` | Bước 3 — bảng bậc điểm, chụp vào dòng phiếu |
| `hr.employee` | `kpi_evaluation_count` (Integer, compute) | Cho smart button "Phiếu KPI" |
| `res.config.settings` | `kpi_default_approver_id` (Many2one `res.users`; phải là KPI Admin), `kpi_score_cap`, `kpi_adjustment_max`, `kpi_min_applicable_weight`, `kpi_rating_excellent`, `kpi_rating_good`, `kpi_rating_pass` (đều Float, `config_parameter=...`) | Lưu ở `ir.config_parameter`, đọc qua `get_kpi_param()` |

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

### 5.3. Danh sách test case (183 test, 19 file)

#### `tests/test_kpi_config.py` — 10 test (Phase 1: chỉ số, bộ KPI; thêm test phiên bản đồng đều)

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

#### `tests/test_kpi_demo_scenario.py` — 17 test (đối chiếu bảng tính tay; từ Bước 2 trở đi thêm test cho Dung, Phúc, Lan, người duyệt mặc định và lịch sử gợi ý — mô tả ở các mục tương ứng bên dưới)

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

#### `tests/test_kpi_score_scale.py` — 12 test (Bước 3, Chương 9.3: chấm điểm theo bậc)

| Test | Kiểm tra |
|---|---|
| `test_scale_validation` | Bảng rỗng, hở khoảng từ 0, hai bậc cùng điểm bắt đầu (chồng nhau), sửa bậc đầu khỏi 0 đều bị chặn |
| `test_scale_steps_cover_without_overlap` | Các bậc liền nhau, không chồng, bậc cuối không giới hạn |
| `test_only_admin_edits_scale` | Quản lý không tạo được bảng bậc |
| `test_lookup_boundaries` | Đúng ở biên: 49,99 → bậc dưới, 50 → bậc trên... |
| `test_click_compute_kpi_uses_scale` | **Qua nút "Tính KPI"**: 17/20 SP = 85% → bậc 80% = 75 điểm (tuyến tính ra 85) |
| `test_without_scale_stays_linear` | Không gắn bảng bậc thì giữ cách tính tuyến tính cũ |
| `test_not_applicable_skips_lookup` | Chỉ số Không áp dụng không tra bậc (kể cả bảng cho 0% được 50 điểm) |
| `test_lower_is_better_zero_actual_takes_cap_before_lookup` | Thấp tốt, thực tế = 0: % đạt lấy trần 120 rồi mới tra bậc; điểm tra được vẫn bị chặn trần |
| `test_editing_scale_does_not_change_existing_evaluation` | Sửa bảng bậc sau khi tạo phiếu: phiếu cũ giữ nguyên điểm (JSON đã chụp), phiếu mới nhận bảng mới |
| `test_invalid_scale_written_around_the_form_blocks_evaluation` | Bảng bị sửa thẳng từng bậc (bỏ qua form) thì không tạo được phiếu |
| `test_cannot_archive_scale_in_active_template` | Không ẩn bảng bậc khi bộ KPI hoạt động còn dùng |
| `test_percent_and_scale_name_shown_on_pdf_and_api` | PDF hiện % đạt mục tiêu và tên bảng bậc |

**Module `project_kpi_skills` — 9 test riêng** (`tests/test_kpi_skills.py`, chạy bằng `-i project_kpi_skills --test-tags /project_kpi_skills`; cần `hr_skills`). Chức danh yêu cầu Python 75, Odoo 50, SQL 50:

| Test | Kiểm tra |
|---|---|
| `test_pass_fail_and_exceed` | Python 100 (vượt), Odoo 50 (đúng mức), SQL 25 (không đạt) → 2/3 = 66,67%, khối lượng 3 |
| `test_missing_skill_counts_as_failed` | Thiếu SQL → 2/3; không có kỹ năng nào → 0% |
| `test_expired_skill_ignored` | Kỹ năng nhân viên hết hạn trước cuối kỳ không tính |
| `test_expired_job_requirement_ignored` | Yêu cầu của chức danh đã hết hạn không vào mẫu số |
| `test_job_without_required_skills_is_not_applicable` | Chức danh không yêu cầu kỹ năng → khối lượng 0, "Không áp dụng" |
| `test_old_period_unchanged_after_skill_upgrade` | Nâng mức SQL sau kỳ (bản cũ đóng, bản mới bắt đầu hôm nay): kỳ đã qua tính lại vẫn theo mức cũ, kỳ hiện tại theo mức mới |
| `test_uses_job_snapshotted_on_evaluation` | Đổi chức danh sau khi tạo phiếu: vẫn so theo chức danh đã chụp trên phiếu |
| `test_click_compute_on_evaluation` | Qua nút Tính KPI: S1 66,67% so với mục tiêu 80% → điểm dòng 83,33; bộ "Developer (có năng lực)" đủ trọng số 100 |
| `test_demo_skills_scenario` | Dữ liệu mẫu: An Python 100, Odoo 50, SQL 25 → 2/3 |

**Module `project_kpi_survey` — 8 test riêng** (`tests/test_kpi_feedback.py`, chạy bằng `-i project_kpi_survey --test-tags /project_kpi_survey`; cần `survey`). Trả lời khảo sát đi đúng đường controller dùng (`_save_lines` rồi `_mark_done`); mỗi câu trả lời chấm theo tổng điểm / tối đa 20 (4 câu × 5):

| Test | Kiểm tra |
|---|---|
| `test_below_three_answers_not_applicable_and_hidden` | 2 câu trả lời: F1 "Không áp dụng", giá trị 0 và phiếu không hiện điểm trung bình (không lộ ai chấm bao nhiêu) |
| `test_three_answers_average_matches_hand_calculation` | 3 người chấm toàn 5, toàn 4, toàn 3 → 100%, 80%, 60% → trung bình 80%; mục tiêu 80 → điểm dòng 100; bộ có F1 đủ trọng số 100 |
| `test_unfinished_and_test_entries_ignored` | Câu trả lời dở dang và bản test (`test_entry`) không tính |
| `test_late_answer_does_not_change_submitted_evaluation` | Phiếu đã gửi: câu trả lời đến muộn không đổi điểm (phiếu đã khoá, không tính lại) |
| `test_invite_rules` | Chặn: mời chính nhân viên, không chọn ai, mời trùng, quản lý không phải của nhân viên, phiếu không còn Nháp |
| `test_reminder_per_reviewer_and_done_when_answered` | Mỗi người được mời một nhắc việc kèm link khảo sát riêng; trả lời xong nhắc việc tự đánh dấu xong |
| `test_manager_sees_invitees_but_not_answers` | Quản lý thấy ai được mời và đã trả lời chưa, nhưng không đọc được `survey.user_input` (nội dung, điểm từng người); người được mời chỉ thấy lời mời của mình |
| `test_permission_checks_happen_before_any_sudo_write` | Kiểm tra quyền (đúng quản lý, đúng trạng thái Nháp) chạy TRƯỚC mọi `sudo()`: người không đủ quyền hoặc phiếu không còn Nháp bị chặn mà không tạo lời mời hay câu trả lời nào |

#### `tests/test_kpi_dashboard.py` — 7 test (Đợt C1: màn hình tổng quan)

Dữ liệu cố định, số đếm tính tay trước khi chạy: team của quản lý Q1 có Nháp, Đã gửi (75), Đã duyệt 100 (đã xác nhận), Đã duyệt 50 (Cần cải thiện), Đã duyệt thiếu dữ liệu (100); team của Q2 có Đã duyệt 75.

| Test | Kiểm tra |
|---|---|
| `test_numbers_match_hand_count_for_admin` | Admin: 6 phiếu = 1 Nháp + 1 Đã gửi + 4 Đã duyệt; điểm TB (100 + 50 + 100 + 75)/4 = 81,25; Cần cải thiện 1; thiếu dữ liệu 1; chờ xác nhận 3 |
| `test_manager_sees_only_own_team` | Cùng một kỳ: quản lý Q1 thấy 5 phiếu, đã duyệt 3, TB 83,33, chờ xác nhận 2; quản lý Q2 thấy 1 phiếu — khác Admin vì không dùng sudo |
| `test_each_button_opens_exactly_its_evaluations` | 7 nút (tất cả, Nháp, Đã gửi, Đã duyệt, Cần cải thiện, Thiếu dữ liệu, Chờ xác nhận) mở đúng tập phiếu |
| `test_button_respects_viewer_permissions` | Nút của quản lý Q1 không đưa phiếu team Q2 vào danh sách |
| `test_number_of_queries_does_not_grow_with_periods` | Đọc 1 kỳ và 8 kỳ tốn số truy vấn như nhau (một `_read_group`, không `search_count` từng kỳ) |
| `test_data_issues_are_current_and_only_for_managers_on_open_periods` | Lỗi dữ liệu là số hiện tại (+3 khi thêm Feature thiếu SP và bug thiếu gốc/phân loại), chỉ hiện cho quản lý trở lên và chỉ trên kỳ đang mở |
| `test_dashboard_is_the_first_menu_and_view_is_valid` | Kanban hợp lệ, mặc định lọc kỳ đang mở, "Tổng quan" là menu đầu của app KPI |

#### `tests/test_kpi_period_types.py` — 4 test (Đợt B1: kỳ riêng theo bộ KPI)

| Test | Kiểm tra |
|---|---|
| `test_wizard_creates_only_matching_period_type` | Wizard chỉ tạo phiếu cho bộ KPI cùng loại kỳ (tháng vs quý), cả kỳ tháng lẫn kỳ quý |
| `test_cron_creates_only_matching_period_type` | Tác vụ cuối kỳ cũng chỉ tạo đúng loại kỳ |
| `test_cannot_change_period_type_with_open_period_evaluations` | Còn phiếu ở kỳ đang mở thì không đổi loại kỳ của bộ; đóng kỳ rồi thì đổi được |
| `test_p2_quarterly_lead_averages_per_person_over_monthly_evaluations` | PM theo quý, cấp dưới theo tháng: A 3 phiếu (50, 75, 100), B 1 phiếu (50) → P2 = (75 + 50) / 2 = 62,5 trên 2 người (gộp phiếu sẽ ra 68,75, sai); phiếu của kỳ dài hơn kỳ PM không tính |

(Khi PM và cấp dưới cùng theo tháng, quy tắc mới cho đúng kết quả cũ. **Phúc có hai con số điểm, cùng một dữ liệu mẫu, khác thời điểm:** **80,226** khi cấp dưới CHƯA chốt phiếu nào — P2 "Không áp dụng" nên điểm chuẩn hoá trên trọng số 75 = (P1 41,667%·25 + P3 98,765%·20 + P5 100%·30) / 75; và **84,862** sau khi Dung và Hà đã Gửi duyệt — P2 = 79,0139 áp dụng, trọng số đủ 100 = (P1 41,667%·25 + P2 98,767%·25 + P3 98,765%·20 + P5 100%·30) / 100. Cả hai đều tính tay trước khi chạy và nằm trong `test_kpi_demo_scenario.py`; 84,86 cũng là số thấy được khi chạy thử qua XML-RPC trên database dựng mới.)

#### `tests/test_kpi_target_suggestion.py` — 7 test (Đợt B2: gợi ý mục tiêu)

| Test | Kiểm tra |
|---|---|
| `test_percentiles_higher_is_better` | Kết quả 10, 20, 30, 40 → Dễ 17,5 / Vừa 25 / Khó 32,5 (phân vị 25/50/75) |
| `test_lower_is_better_reverses_difficulty` | Chỉ số thấp là tốt: Dễ = phân vị 75, Khó = phân vị 25 (0,325 / 0,25 / 0,175) |
| `test_only_six_latest_periods` | Chỉ lấy 6 kỳ gần nhất: kỳ cũ nhất (1000) bị loại |
| `test_needs_three_periods` | Ít hơn 3 kỳ thì báo "Chưa đủ dữ liệu", nút Áp dụng bị từ chối |
| `test_excludes_unapproved_insufficient_not_applicable_and_other_period_type` | Bỏ phiếu chưa duyệt, thiếu dữ liệu, dòng Không áp dụng, khác loại kỳ |
| `test_employee_scope_uses_only_that_employees_history` | Mục tiêu riêng cho nhân viên chỉ dùng lịch sử của nhân viên đó, của phòng ban thì dùng cả phòng |
| `test_apply_buttons_write_target_and_stay_editable` | Ba nút Áp dụng ghi vào `target`; quản lý vẫn sửa tay được |

(`tests/test_kpi_demo_scenario.py` có thêm `test_demo_default_approver_is_admin` và `test_demo_history_gives_target_suggestions`: phòng lịch sử mẫu, D2 = 12, 14, 16, 18 → 13,5 / 15 / 16,5.)

#### `tests/test_kpi_workflow.py` — 17 test (Đợt A, Chương 9.6: nhắc việc, xác nhận, tạm tính, báo cáo phòng ban)

| Test | Kiểm tra |
|---|---|
| `test_create_reminds_manager_to_complete` | Tạo phiếu → nhắc việc "Hoàn tất phiếu KPI" giao quản lý trực tiếp |
| `test_submit_closes_complete_and_reminds_approver` | Gửi duyệt → nhắc hoàn tất tự đánh dấu xong, nhắc duyệt giao người duyệt mặc định; gọi lại không tạo trùng |
| `test_approve_closes_approver_reminder_and_reminds_employee` | Duyệt → nhắc duyệt xong, nhắc nhân viên xác nhận |
| `test_return_to_draft_cancels_approve_and_reminds_again` | Trả về nháp (qua wizard) → huỷ nhắc duyệt, nhắc hoàn tất lại |
| `test_no_default_approver_means_no_approve_reminder` | Chưa đặt người duyệt: không tạo nhắc duyệt, ghi chú vào chatter |
| `test_approver_in_role_conflict_is_skipped` | Người duyệt mặc định lại là quản lý của phiếu thì bỏ qua |
| `test_manager_without_kpi_group_falls_back_to_approver` | Quản lý không thuộc nhóm KPI (không đọc được phiếu) → nhắc việc chuyển cho người duyệt mặc định |
| `test_settings_approver_must_be_admin` | Settings chặn người duyệt mặc định không phải KPI Admin |
| `test_employee_acknowledges_after_approval` | Nhân viên xác nhận qua wizard, phiếu vẫn Đã duyệt, nhắc việc xác nhận xong |
| `test_disagree_requires_comment` | Chọn Có ý kiến thì bắt buộc ghi nội dung |
| `test_only_own_employee_and_only_after_approval` | Chỉ chính nhân viên, chỉ sau khi Đã duyệt |
| `test_acknowledgement_not_writable_directly` | Quản lý không ghi/tạo kèm ack trực tiếp được |
| `test_reopen_clears_acknowledgement` | Mở lại phiếu xoá xác nhận cũ |
| `test_cron_provisional_compute_touches_only_engine_lines` | Cron tạm tính: chỉ ghi dòng do engine tính; D9 nhập tay, mục tiêu đã sửa giữ nguyên; không đặt `computed_date`; phiếu đã gửi không bị đụng |
| `test_manual_compute_sets_both_dates` | Quản lý bấm Tính KPI đặt cả `computed_date` và `last_computed_date` |
| `test_manager_without_kpi_permission_is_listed` | Danh sách "Quản lý chưa có quyền KPI" gồm nhân viên có quản lý thiếu nhóm KPI Manager hoặc chưa có tài khoản, không gồm quản lý hợp lệ |
| `test_department_reports` | Các action báo cáo theo phòng ban tải được, gom nhóm theo `department_id` đã chụp |

#### `tests/test_kpi_ba.py` — 10 test (Bước 5, Chương 9.2: bộ BA)

| Test | Kiểm tra |
|---|---|
| `test_b1_b3_have_no_python_code` | B1, B3 là chỉ số domain, không có hàm `_metric_b1/b3`; B2 có hàm riêng; B4 nhập tay |
| `test_requirement_link_validation` | `requirement_id` phải là task Yêu cầu, cùng dự án |
| `test_is_on_time_flag` | Cờ đúng hạn: đúng / trễ / chưa xong / không deadline |
| `test_open_requirement_not_yet_due_is_not_on_time` | Yêu cầu đang làm dở, chưa tới hạn: `is_on_time` = False dù `days_late` = 0 (cờ yêu cầu đã xong), không vào tử số B1, chỉ ở mẫu số |
| `test_b1_on_time_ratio` | B1: bỏ task huỷ, ngoài kỳ, không phải Yêu cầu; quá hạn chưa xong tính trễ |
| `test_b3_first_review_pass` | B3: chỉ tính yêu cầu đã qua review, bị trả về thì không đạt lần đầu |
| `test_same_bug_not_for_developer_but_for_ba` | **Cùng một bug**: không tính cho Developer (D3, D4), tính cho BA (B2) |
| `test_b2_only_counted_bugs_of_requirement_cause` | B2 bỏ bug trùng, bug nguyên nhân code, yêu cầu ngoài kỳ |
| `test_untraceable_requirement_bug_reported_in_data_quality` | Cột "không truy được yêu cầu gốc" đếm đúng; bug đó không tính cho BA |
| `test_click_compute_matches_hand_calculation` | Qua nút Tính KPI: phiếu BA ra 89,328 đúng bảng tính tay |

(`tests/test_kpi_demo_scenario.py` có thêm `test_lan_ba_evaluation`: BA mẫu Lan — 3 yêu cầu, bug "yêu cầu sai" của task t6 và bug #5 của tester Dung → B2 = 2/3, điểm 75,828, tính tay trước khi chạy. P3 của Phúc ở bản trước Đợt A4 (ảnh chụp toàn dự án) là 59/63; từ Đợt A4 là 32/36, điểm Phúc 80,226.)

#### `tests/test_kpi_lead.py` — 10 test (Bước 4, Chương 9.2: bộ Team Lead / PM)

| Test | Kiểm tra |
|---|---|
| `test_p1_has_no_python_code_and_uses_domain` | P1 là chỉ số domain, không có hàm `_metric_p1` |
| `test_p1_on_time_milestones_of_lead_projects` | P1 chỉ tính milestone có deadline trong kỳ của dự án Lead quản lý; quá hạn chưa đạt tính trễ |
| `test_is_reached_on_time_flag` | Cờ `is_reached_on_time` đúng (đạt đúng hạn / trễ / không deadline) |
| `test_p2_only_closed_evaluations_of_same_period` | P2 chỉ lấy phiếu cấp dưới Đã gửi/Đã duyệt, bỏ phiếu Nháp |
| `test_p2_not_applicable_when_team_not_closed` | Chưa có phiếu cấp dưới chốt → P2 "Không áp dụng", qua nút Tính KPI |
| `test_p2_skips_evaluation_with_insufficient_data` | Phiếu cấp dưới đã chốt nhưng thiếu dữ liệu không vào P2 (giá trị lẫn khối lượng) |
| `test_p2_other_period_ignored_and_no_self_loop` | Phiếu kỳ khác và phiếu của chính Lead không tính |
| `test_p3_clean_ratio_of_lead_projects` | P3 theo kỳ (Đợt A4): 3/6 tiêu chí sạch đúng bảng tính tay, loại dự án khác |
| `test_p3_ignores_records_outside_period` | Task xong và bug tạo ngoài kỳ không ảnh hưởng P3 — tính lại phiếu kỳ cũ cho cùng kết quả |
| `test_template_and_click_compute` | Chức danh PM gắn bộ P1–P5; nút Tính KPI ra điểm đúng khi P2, P3 không áp dụng |

(`tests/test_kpi_demo_scenario.py` có thêm `test_phuc_pm_evaluation`: PM mẫu Phúc, P1 = 33,33%, P3 = 56/60, điểm 80,23 (P3 theo kỳ = 32/36) — tính tay trước khi chạy; và `test_phuc_p2_skips_closed_evaluations_without_enough_data`: kịch bản demo P2 — Phúc có 3 cấp dưới mẫu: Dung (tester, 55,875), Khoa (tester mới, thiếu dữ liệu) và Hà (Developer, đủ dữ liệu, 102,1528). P2 "Không áp dụng" khi chưa ai chốt; sau khi cả ba Gửi duyệt và Tính lại phiếu Phúc thì P2 = (55,875 + 102,1528) / 2 = 79,0139 trên **2** phiếu — Khoa bị loại. Tính tay trước khi chạy.)

**Module `project_kpi_timesheet` — 6 test riêng** (`tests/test_kpi_timesheet.py`, chạy bằng `-i project_kpi_timesheet --test-tags /project_kpi_timesheet`): cài đặt P4 và bộ có giờ làm, lệch cả hai chiều đều bị phạt, bỏ dự án không có giờ kế hoạch hoặc của Lead khác, bỏ timesheet sau cuối kỳ, nút Tính KPI (130/100 giờ → lệch 30% → 50 điểm).

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

**Tổng cộng 206 test, 0 failed, 0 error:** 183 test của module chính (`project_kpi_management`) + 6 của `project_kpi_timesheet` + 9 của `project_kpi_skills` + 8 của `project_kpi_survey`. Lần gần nhất 2026-10-16, đều trên database tạo mới hoàn toàn (không chỉ chạy lại trên database cũ): module chính một mình; module chính + `project_kpi_timesheet`; và **cả ba module cầu nối cài cùng lúc** (203 test tại thời điểm chạy — chưa tính test thêm sau đó) để chắc các hàm `_metric_*` của chúng (đều kế thừa `kpi.engine`) không đè nhau. Từng module cầu nối cũng được chạy riêng bằng `--test-tags`.

**Các lỗi thật phát hiện nhờ kiểm tra qua đường đi thật** (không phải qua unit test gọi thẳng hàm), đã sửa và có test khoá lại:

| Phát hiện | Cách phát hiện | Cách sửa |
|---|---|---|
| Quản lý ghi trực tiếp được `employee_comment`/`self_score` (cả `write()` lẫn `create()`); thiếu `copy=False` trên `self_score` | Script XML-RPC bằng tài khoản thật (5.6) | Chặn ở cả hai đường, thêm `copy=False` |
| Phiếu không tính chỉ số `domain` khi bấm "Tính KPI" (Bước 1 chạy đúng ở engine nhưng phiếu bỏ sót) | Làm Bước 2: test gọi thẳng engine không thấy, test qua nút thì thấy | Một hàm `_is_engine_computed()` dùng chung; test qua wizard, hành động Tính lại, cron, API (Chương 5.3) |
| P2 tính cả phiếu cấp dưới thiếu dữ liệu, kéo điểm Lead xuống khi có nhân viên mới (bản trước khi sửa) | Rà lại kịch bản demo | P2 bỏ phiếu `insufficient_data` |
| Wizard mời 360 đọc khảo sát bằng quyền của quản lý nên bị `AccessError` | Test của module cầu nối | Thao tác khảo sát chạy bằng `sudo()` sau khi đã kiểm tra quyền |
| Server đang chạy chưa nạp code mới sau khi sửa file (lặp lại ba lần) | Script báo lỗi `KeyError`/kết quả cũ dù test đạt | `scripts/prepare_defense.sh` gói bước nạp module + khởi động lại + chờ sẵn sàng + chạy script |
| Quản lý không thuộc nhóm KPI không đọc được phiếu nên Odoo từ chối giao nhắc việc | Test nhắc việc Đợt A | Chỉ giao cho người đọc được phiếu, nếu không thì chuyển cho người duyệt mặc định; có danh sách "Quản lý chưa có quyền KPI" |

**Quan trọng — hạn chế của `TransactionCase`:** unit test chạy bằng superuser (`env.su = True`),
nên bỏ qua một số kiểm tra chỉ áp dụng cho người dùng thật (ví dụ chặn xung đột vai trò). Vì vậy các
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

Kiểm tra 23 mục (15 nhóm, thêm ba bước tuỳ chọn S1, F1 và P4), tự tạo kỳ/phiếu test riêng và tự dọn sạch ở cuối (kể cả khi có bước FAIL),
không ảnh hưởng dữ liệu demo dùng để trình bày:

1. Chặn xung đột vai trò (Mục 2): quản lý được gán thêm quyền Admin vẫn bị chặn khi duyệt phiếu
   nhân viên mình quản lý.
2. Nhắc việc PIP (Mục 3): duyệt phiếu Cần cải thiện tạo đúng 1 nhắc việc.
3. Tự đánh giá (Mục 6, 4 bước): nhân viên ghi được qua wizard; người khác — **kể cả quản lý, vốn
   có quyền ghi phiếu/dòng phiếu khi Nháp** — không ghi trực tiếp được `employee_comment` (qua
   `write()`) lẫn `self_score` (qua cả `write()` và `create()` dòng phiếu mới), và không tạo được
   phiếu mới kèm sẵn `employee_comment`.
4. Mục tiêu theo phòng ban (Mục 4): phiếu mới nhận đúng mục tiêu riêng.
5. Bộ Tester (Bước 2, 2 bước): đăng nhập tester xác nhận không sửa được `bug_reporter_id`; Admin tính phiếu Tester ra đúng 71,0 điểm (tính tay trước).
6. Chấm theo bậc (Bước 3): nút Tính KPI ra 60 điểm với 50% đạt mục tiêu (tuyến tính sẽ ra 50).
7. Bộ Lead/PM (Bước 4): phiếu PM tự tạo ra đúng 82,95 điểm (P1 = 50%, P2 và P3 Không áp dụng).
8. Bộ BA (Bước 5): phiếu BA tự tạo (3 yêu cầu, 1 bug "yêu cầu sai" quy về BA) ra đúng 89,33 điểm.
9. Quy trình (Đợt A, 3 mục): nhắc việc đi đúng người ở từng bước (tạo phiếu → quản lý; gửi duyệt → người duyệt mặc định; duyệt → nhân viên) và tự đánh dấu xong nhắc việc cũ; nhân viên xác nhận kết quả qua wizard, admin cũng không ghi trực tiếp được. Script đặt người duyệt mặc định = admin và khôi phục giá trị cũ ở cuối.
10. Người duyệt mặc định (dữ liệu mẫu tự đặt admin): đã đặt và là KPI Admin — nếu không nhắc việc duyệt phiếu sẽ "không có gì xảy ra" ngay lúc demo.
11. Kỳ riêng theo bộ KPI và gợi ý mục tiêu (Đợt B, 2 mục): không đổi được loại kỳ khi còn phiếu ở kỳ đang mở; 3 kỳ đã duyệt D2 = 10, 20, 30 → gợi ý Dễ 15 / Vừa 20 / Khó 25 (tính tay trước).
12. Màn hình tổng quan (Đợt C1): Admin đọc số liệu kỳ qua XML-RPC (2 phiếu = 1 Nháp + 1 Đã duyệt, điểm TB = điểm phiếu đã duyệt), nút "Đã duyệt" mở đúng 1 phiếu.
13. S1 mức đáp ứng kỹ năng (Đợt D2): chỉ chạy khi module `project_kpi_skills` đã cài (chức danh yêu cầu Python 75, Odoo 50, SQL 50; nhân viên Python 100, Odoo 50, SQL 25 → 66,67%, điểm dòng 83,33); chưa cài thì in `[SKIP]`.
14. F1 phản hồi 360 (Đợt D1): chỉ chạy khi module `project_kpi_survey` đã cài. Quản lý đăng nhập mời 3 người: mỗi người đúng 1 nhắc việc kèm link, người được mời chỉ thấy lời mời của mình, quản lý đọc `survey.user_input` bị từ chối, nhân viên không mời được, F1 chưa có câu trả lời thì Không áp dụng. Việc trả lời khảo sát đi qua controller của module survey nên kiểm bằng unit test, không qua XML-RPC.
15. P4 giờ so với kế hoạch (Bước 4): chỉ chạy khi module cầu nối `project_kpi_timesheet` đã cài (130/100 giờ → 50 điểm); chưa cài thì in `[SKIP]`. Tuỳ chọn `--skip-demo-checks` chỉ chạy các bước tự tạo dữ liệu, dùng cho database không có dữ liệu mẫu.

Cách chạy trước khi bảo vệ:

```bash
bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense   # gói cả ba bước dưới đây
# tương đương làm tay (dễ quên bước giữa):
#   docker compose exec odoo odoo -d kpi_defense -u project_kpi_management --stop-after-init
#   docker compose restart odoo
#   docker compose exec odoo python3 /mnt/extra-addons/project_kpi_management/scripts/pre_defense_check.py --db kpi_defense
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

Container Odoo đọc code trực tiếp từ thư mục `addons` trên đĩa, nên hệ thống đang chạy luôn là mã nguồn đang đứng trên đĩa. Quy ước: **chỉ có MỘT mã nguồn duy nhất, nhánh `main`**, đồng nhất với hệ thống đang chạy — không có bản bảo vệ tách riêng. Mọi đợt thay đổi (Bước 1–5, Đợt A–D) đã hợp nhất vào `main`. Các tag `v1.x-bao-ve` đã đẩy lên GitHub giữ nguyên chỉ như lịch sử, không dùng trong quy trình.

**Điều kiện để một thay đổi được đưa vào `main`** (kỷ luật trước mỗi commit thay cho "lưới an toàn" của tag):

1. Test của cả bốn module đạt (`bash addons/project_kpi_management/scripts/run_all_tests.sh` → `TẤT CẢ TEST ĐẠT`; hiện 206 test = 183 + 6 + 9 + 8).
2. `bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense` in `tất cả OK` và bảng phiên bản đồng đều.
3. Tài liệu đồng bộ với code (số test, tài khoản theo vai trò, kịch bản demo, các con số tính tay).
4. Nếu dữ liệu mẫu thay đổi: tạo lại hai bản sao lưu `clean` và `seeded` (`backup_defense.sh`).

**Ngày dừng:** đặt một ngày dừng cho buổi bảo vệ (đề xuất 1 tuần trước). Sau ngày đó **chỉ commit sửa lỗi chặn demo** (lỗi hiển thị/nhãn gây hiểu nhầm, lỗi làm hỏng kịch bản), mỗi commit vẫn đủ 4 điều kiện trên; không thêm tính năng.

**Cách khuyến nghị: dựng database bảo vệ mới từ `main` hiện tại** (dữ liệu mẫu đầy đủ, kết quả lặp lại được). Lý do: nạp dữ liệu mẫu là
thao tác một lần — database dựng từ bản cũ không có Phúc, Dung, Khoa, Hà, Lan, phòng lịch sử mẫu
và nạp lại thì bị bỏ qua vì kỳ mẫu đã tồn tại.

```bash
git checkout main && git pull --ff-only     # mã nguồn duy nhất
docker exec odoo19-db dropdb -U odoo --force --if-exists kpi_defense
docker exec odoo19-web odoo -d kpi_defense -i project_kpi_skills,project_kpi_survey --stop-after-init   # cài module (kéo theo project_kpi_management, hr_skills, survey)
docker exec odoo19-web sh -c "echo 'env[\"kpi.demo\"]._load_scenario(); env.cr.commit()' | odoo shell -d kpi_defense --max-cron-threads=0 --http-port=8072"
bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense   # nạp lại module, khởi động lại, chờ sẵn sàng, chạy pre_defense_check
# phải in "tất cả OK"; bước P4 in [SKIP] vì không cài hr_timesheet
```

**Phiên bản đồng đều (file, database).** Số phiên bản trong `__manifest__.py` của cả bốn module KPI là **một số phát hành duy nhất** (hiện `19.0.1.7.4`), tăng khi hợp nhất một đợt thay đổi chức năng hoặc dữ liệu; không gắn với tag. Trước đó manifest của module chính dừng ở `19.0.1.1.0` và ba cầu nối ở `19.0.1.0.0` dù code đã qua nhiều đợt — số phiên bản trong Odoo (Apps) không phản ánh bản đang chạy. Nay `prepare_defense.sh` in bảng đối chiếu cho từng module (phiên bản trên đĩa | trong database), cảnh báo nếu cây làm việc có thay đổi chưa commit hoặc không đứng trên `main`, và **dừng nếu số phiên bản lệch**; một test (`test_all_kpi_modules_share_one_release_version`) giữ cho các module không lệch nhau. Khi đổi số phiên bản phải đổi trong cả bốn manifest. Nâng phiên bản ở database đã cài dùng `-u` (script tự làm); thư mục `migrations/19.0.1.1.0` chỉ chạy một lần khi nâng từ phiên bản thấp hơn 1.1.0 nên không chạy lại.

**Sao lưu và khôi phục `kpi_defense` (bắt buộc trước ngày bảo vệ).** Mỗi lần tổng duyệt demo sẽ tạo phiếu, tính điểm, duyệt, xác nhận — database không còn ở trạng thái "thẻ kỳ trống" như kịch bản mở đầu. Vì vậy sao lưu khi database còn sạch rồi khôi phục sau mỗi lần tổng duyệt và sáng ngày bảo vệ:

```bash
bash addons/project_kpi_management/scripts/backup_defense.sh clean     # sao lưu (database + filestore) vào backups/ — thư mục không đưa vào Git
bash addons/project_kpi_management/scripts/restore_defense.sh clean    # khôi phục, rồi tự chạy prepare_defense.sh
```

Đường dẫn filestore là `/var/lib/odoo/.local/share/Odoo/filestore` (kiểm bằng `odoo.tools.config['data_dir']` trong image `odoo:19.0` — **không** phải `/var/lib/odoo/filestore`). Đã chạy thử khôi phục thật hai lần (từ bản `clean` rồi bản `seeded`), cả hai đều qua `prepare_defense.sh` với kết quả tất cả OK. Hai bản sao lưu hiện có: `clean` (vừa dựng, 4 kỳ lịch sử đã duyệt, kỳ mẫu chưa có phiếu và đã đánh dấu `auto_generated` để tác vụ cuối kỳ không tạo sẵn phiếu — nên bước "Tạo phiếu cho kỳ" của kịch bản chạy thật) và `seeded` (có sẵn 8 phiếu ở các trạng thái, kỳ năng lực + 360 với lời mời chưa trả lời — để xem các màn hình).

**Bản sao lưu phải có ở nơi thứ hai.** `backups/` không nằm trong Git nên chỉ có trên một máy; nếu máy hỏng hoặc volume Docker bị xoá thì mất cả database lẫn bản sạch. Chép cả thư mục `backups/` (khoảng 10 MB) sang ổ ngoài hoặc Google Drive. Hai bản sao lưu gắn với dữ liệu mẫu hiện tại: nếu dữ liệu mẫu trên `main` đổi, phải tạo lại bằng `backup_defense.sh` (điều kiện 4 ở trên).

**Chuẩn bị ngày bảo vệ (checklist).**

| Việc | Ghi chú |
|---|---|
| Ngày dừng thay đổi | **____/____/______** (điền: đề xuất 1 tuần trước buổi bảo vệ). Sau ngày này chỉ commit sửa lỗi chặn demo, không thêm tính năng; mỗi commit vẫn đủ 4 điều kiện đưa vào `main` |
| Thử offline một lần | Tắt mạng, chạy `restore_defense.sh clean`, đi hết luồng happy case. Mã của các module KPI không gọi địa chỉ ngoài nào (đã kiểm), Odoo chạy cục bộ không cần internet — nhưng nên tự thấy điều đó |
| Tổng duyệt ≥ 2 lần | Mỗi lần: `restore_defense.sh clean` → luồng happy case → kịch bản Chương 5.8 có canh giờ (10–15 phút). Lần đầu chú ý phần P2: nhắc việc "Hoàn tất phiếu" của Dung, Khoa, Hà đi tới `phuc` |
| Ôn câu hỏi | Tự trả lời theo từng bước demo (cách tính điểm, phân quyền) không nhìn tài liệu |
| Sáng ngày bảo vệ | `git checkout main && git pull --ff-only` → `bash addons/project_kpi_management/scripts/restore_defense.sh clean` → chờ "tất cả OK" → mở trình duyệt |

**Khoá database cho buổi bảo vệ.** Màn hình đăng nhập có ô chọn database khi có nhiều database (`kpi_dev`, `kpi_defense`...); chọn nhầm `kpi_dev` (thiếu Phúc, Lan, Hà...) thì kịch bản demo hỏng ngay từ đầu. Trong `config/odoo.conf` (file thật, không nằm trong Git) thêm rồi khởi động lại container:

```ini
dbfilter = ^kpi_defense$
list_db = False
```

Hai dòng này **đã được đặt** trong `config/odoo.conf` của máy này (mỗi lần chạy test trên database mới sẽ tạo thêm database; có `dbfilter` thì màn hình đăng nhập không bao giờ hiện ô chọn). **Không** chạy test trực tiếp bằng `odoo -d <db tạm> -i ...` khi đang khoá: test API (HttpCase) đi qua HTTP nên bị `dbfilter` chặn (404) — đã gặp thật khi chạy test sau khi khoá. Dùng `bash addons/project_kpi_management/scripts/run_all_tests.sh`: script chạy toàn bộ test của bốn module trên một database tạm bằng bản sao config đã bỏ `dbfilter` (config thật không đổi) rồi tự xoá database và filestore tạm; phải in `TẤT CẢ TEST ĐẠT`. Sau buổi bảo vệ xoá hai dòng này nếu cần dùng nhiều database. Lưu ý: khi đang khoá, `pre_defense_check.py` qua XML-RPC chỉ chạy được với `kpi_defense` (lệnh `odoo -d ...` trên dòng lệnh vẫn dùng được database khác). `config/odoo.conf.example` có sẵn hai dòng này dạng chú thích.

**Module cầu nối cài trên `kpi_defense`:** `project_kpi_skills` (thêm tab Kỹ năng vào hồ sơ nhân viên, ít xáo trộn) và `project_kpi_survey` (thêm app Surveys; khảo sát 360 mẫu nằm trong đó). **Không** cài `hr_timesheet`/`project_kpi_timesheet` (thêm app Timesheet). Các bước tương ứng trong `pre_defense_check.py` tự bỏ qua khi module chưa cài.

**Database duy nhất của môi trường:** chỉ giữ `kpi_defense` (các database kiểm thử/phát triển như `kpi_dev`, `kpi_fresh_check` đã xoá; khi cần chạy test thì dựng database tạm rồi xoá lại).

**Tài khoản test theo vai trò trên `kpi_defense`** (mật khẩu trùng tên đăng nhập):

| Đăng nhập | Họ tên | Vai trò KPI | Dùng để |
|---|---|---|---|
| `admin` | Administrator | **KPI Administrator** | Cấu hình, tạo/duyệt/trả về/mở lại phiếu, Thiết lập, mọi báo cáo; xem Tổng quan toàn bộ |
| `quocviet` | Phạm Quốc Việt | **KPI Manager** | Quản lý trực tiếp của An, Bình, Chi, Phúc, Lan: tính KPI, chấm tay, gửi duyệt; Tổng quan chỉ thấy team mình; bị chặn khi duyệt phiếu nhân viên mình quản lý dù được gán thêm quyền Admin (demo xung đột vai trò) |
| `phuc` | Hoàng Văn Phúc | **KPI Manager** (PM) | Quản lý trực tiếp của Dung, Khoa, Hà; bộ Team Lead/PM (P1, P2, P3, P5) |
| `an`, `binh`, `chi`, `ha` | Nguyễn Văn An, Trần Thị Bình, Lê Minh Chi, Lý Thanh Hà | KPI User — Lập trình viên | Xem phiếu của mình, Tự đánh giá (Nháp), Xác nhận kết quả (Đã duyệt), trả lời khảo sát 360 khi được mời |
| `dung`, `khoa` | Đỗ Thị Dung, Vũ Minh Khoa | KPI User — Tester (QA) | Bộ Tester tự động; Khoa là tester mới (thiếu dữ liệu) |
| `lan` | Trịnh Thu Lan | KPI User — BA | Bộ Business Analyst (B1–B4) |

**Lưu ý cho phần P2 của kịch bản (Chương 5.8):** vì Phúc là KPI Manager nên nhắc việc "Hoàn tất phiếu KPI" của Dung, Khoa, Hà đi tới **Phúc** (không còn chuyển cho admin). Khi demo, mở các phiếu đó từ menu **KPI › Đánh giá**, hoặc đăng nhập `phuc` rồi mở từ chuông nhắc việc.

Mọi quản lý trực tiếp trong dữ liệu mẫu đều thuộc nhóm KPI Manager (có test `test_demo_managers_all_have_kpi_manager_group`); Phúc được thêm nhóm này trong dữ liệu mẫu — trước đó Dung, Khoa, Hà có quản lý không đọc được phiếu của họ và nhắc việc chuyển cho người duyệt mặc định.
Khi đã có database dựng từ mã hiện tại: `git pull --ff-only` rồi chạy lại `prepare_defense.sh <tên database>` (script tự tìm các module KPI đã cài để nạp lại).

Nạp lại module (`-u`) + khởi động lại container là bắt buộc, không phải tuỳ chọn — `prepare_defense.sh` làm sẵn cả hai và chờ server sẵn sàng, để không còn bước nào phải nhớ làm tay. Lý do
đã nêu ở Chương 5.6: sửa file trên đĩa (hoặc cập nhật mã bằng `git pull`) không tự áp dụng cho tiến
trình Odoo đang chạy. Lần `-u` đầu trên database còn ở bản cũ sẽ chạy script nâng cấp `migrations/19.0.1.1.0/` đúng một lần.

### 5.8. Kịch bản demo (10–15 phút, chọn lọc)

Không demo hết được — chọn 4–5 phần đầu (bắt buộc) rồi lấy thêm các phần "nếu còn thời gian" theo câu hỏi của hội đồng, thứ tự từ nền tảng tới mở rộng. **Mở đầu** bằng màn hình **KPI › Tổng quan** (vào app là thấy ngay): thẻ kỳ mẫu lúc đầu còn trống — nói đây là bức tranh tổng của mọi kỳ; sau phần 1 quay lại màn hình này để thấy thẻ đã đầy số và bấm vào số **Cần cải thiện** để đi thẳng vào phiếu cụ thể. Dữ liệu mẫu: kỳ "Tháng ... (dữ liệu mẫu)", tài khoản
`admin` (KPI Admin), `quocviet` và `phuc` (KPI Manager), `an`, `binh`, `chi`, `ha` (Developer), `dung`, `khoa` (tester), `lan` (BA) — bảng vai trò ở Chương 5.7; người duyệt mặc định đã đặt sẵn là `admin`; mật khẩu trùng tên đăng nhập.

| # | Phần (thời gian) | Thao tác | Điều cần nói |
|---|---|---|---|
| 1 | Luồng chính Developer (4') | Vào kỳ mẫu → Tạo phiếu cho kỳ (**lưu ý:** kỳ mẫu đã kết thúc nên tác vụ cuối kỳ có thể đã tự tạo sẵn 8 phiếu ngay sau khi server khởi động — khi đó wizard báo "không có nhân viên nào cần tạo phiếu"; hãy nói đó chính là tác vụ tự động, rồi đi tiếp) → Tính KPI. An 113,31 Xuất sắc, Bình 73,90 Cần cải thiện; điều chỉnh +2 có lý do cho Bình; Gửi duyệt; `quocviet` (được gán thêm quyền Admin) bị chặn khi duyệt phiếu nhân viên mình quản lý; quay lại **Tổng quan**, bấm "Cần cải thiện" trên thẻ kỳ mẫu để vào danh sách phiếu | Số liệu tự tính từ task/bug thật; điểm có thể truy vết; điều chỉnh phải có lý do; tách người quản lý khỏi người duyệt |
| 2 | Tạo chỉ số bằng cấu hình (3') | KPI → Cấu hình → Chỉ số KPI → tạo mới: Cách tính "Tự động (cấu hình)", model `project.task`, người = `user_ids`, ngày = `date_end`, Đếm, domain `[('state', '=', '1_done')]` → bấm **Thử tính** cho An: ra 7 | Thêm chỉ số không cần viết code, domain đọc bằng `ast.literal_eval` nên không chạy được mã tuỳ ý; chỉ Admin dùng được |
| 3 | Bộ Tester không cần code (2') | Mở bộ "Tester (tự động)" (QA1–QA3 là bản ghi cấu hình); Tạo phiếu cho `dung`, nhập QA5 = 4, Tính KPI → QA1 = 7, điểm 55,875 | Một vai trò mới chỉ bằng dữ liệu; `bug_reporter_id` chỉ Manager sửa được để không tự gán bug cho mình |
| 4 | Phụ thuộc giữa các phiếu: P2 (3') | Tạo + Tính phiếu của `phuc`: P2 "Không áp dụng" → tạo phiếu `dung`, `khoa`, `ha` (nhập QA5 = 4 cho Dung/Khoa, D9 = 4 cho Hà; phiếu `khoa` thiếu dữ liệu nên chọn xếp loại tay + lý do), Tính KPI, Gửi duyệt cả ba → Tính lại phiếu `phuc`: P2 ra 79,01 trên 2 phiếu, điểm Phúc 84,86 (đã chạy thử qua XML-RPC trên database dựng mới) | Không cần sắp thứ tự trong wizard; phiếu thiếu dữ liệu (Khoa, nhân viên mới) **không kéo điểm của quản lý xuống** — hệ thống không tự xếp loại phiếu đó thì cũng không dùng nó để chấm người khác |
| 5 | (nếu còn thời gian, 2') Quy trình có nhắc việc | Thiết lập › Quy trình: đặt người duyệt mặc định → Gửi duyệt một phiếu, chuông nhắc việc của người duyệt hiện "Duyệt phiếu KPI" → Duyệt → đăng nhập nhân viên: nhắc "Xác nhận kết quả KPI" → bấm Xác nhận kết quả | Mỗi bước tự giao đúng người và tự đánh dấu xong; xác nhận không đổi điểm, không thêm trạng thái |
| 6 | (nếu còn thời gian, 2') Gợi ý mục tiêu từ lịch sử | Mục tiêu riêng › tạo mới: dòng D2 của bộ Developer, phòng "Phòng Kỹ thuật (lịch sử mẫu)" → hiện Dễ 13,5 / Vừa 15 / Khó 16,5 → bấm "Áp dụng mức Vừa" | Chỉ gợi ý (phân vị 25/50/75 của 4 kỳ đã duyệt), quản lý vẫn sửa được; nhãn theo độ khó nên đúng cả với chỉ số "thấp là tốt" |
| 7 | (nếu còn thời gian, 2') Năng lực: S1 | Kỳ khác → tạo phiếu thủ công cho `an`, chọn bộ "Developer (có năng lực)" → Tính KPI: dòng S1 = 66,67% (Python 100 ≥ 75, Odoo 50 ≥ 50, SQL 25 < 50). Mở hồ sơ `an` tab Kỹ năng để đối chiếu | So kỹ năng với chức danh *đã chụp trên phiếu*; kỹ năng theo ngày hiệu lực nên nâng mức sau kỳ không đổi kết quả kỳ cũ |
| 8 | (nếu còn thời gian, 3') Phản hồi 360 | Phiếu Nháp (bộ "Developer (có phản hồi 360)") → **Mời đánh giá 360** → chọn 3 người → đăng nhập một người được mời: nhắc việc "Đánh giá 360" có link, trả lời khảo sát → nhắc việc tự xong. Quay lại phiếu: số người đã trả lời; dưới 3 người thì chưa hiện điểm | Điểm là trung bình, quản lý không xem được từng câu trả lời; ngưỡng 3 để không lộ ai chấm bao nhiêu |
| 9 | (nếu còn thời gian, 2') Một bug, hai trách nhiệm | Phiếu `lan` (BA): B2 = 2/3 vì bug "yêu cầu sai" của task t6 quy về BA; mở phiếu `binh`: D3 không tính bug đó | Một lần phân loại bug (`bug_root_cause`), trách nhiệm quy đúng người |
| 10 | (nếu còn thời gian, 2') Chấm theo bậc | Bộ KPI → gắn "Bậc 4 mức (mẫu)" vào một dòng → tạo phiếu mới → cột "% đạt mục tiêu" và bậc hiển thị | Phiếu cũ không đổi vì bảng bậc được chụp lúc tạo phiếu |

Trước buổi demo chạy `pre_defense_check.py` (5.6). Không cài `hr_timesheet` trên `kpi_defense`; P4 chỉ nói bằng lời nếu hội đồng hỏi, kèm bằng chứng là test của module cầu nối.

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
6. Xem tình hình các kỳ ở **KPI › Tổng quan** (mặc định là kỳ đang mở; mỗi con số bấm vào để mở đúng danh sách phiếu).
7. Đặt **Người duyệt mặc định** (**Thiết lập › Quy trình**) để nhận nhắc việc khi có phiếu gửi duyệt; xem điểm theo phòng ban ở **KPI › Báo cáo › Theo phòng ban**.

### 6.2. Vai trò Quản lý trực tiếp

1. Mở phiếu của nhân viên mình quản lý, bấm **Tính KPI**.
2. Chấm D9 (thang 1–5), kiểm tra các dòng *Không áp dụng* (nếu có, cần chọn xếp loại thủ công).
3. Điều chỉnh điểm nếu cần (bắt buộc ghi lý do).
4. Bấm **Gửi duyệt**.
5. Xem báo cáo của nhóm mình (**KPI › Báo cáo**) và tổng quan các kỳ (**KPI › Tổng quan**, chỉ gồm số liệu của nhân viên mình quản lý).

### 6.3. Vai trò Nhân viên

Xem phiếu của mình (**KPI › Đánh giá › Phiếu đánh giá**), xem lịch sử thao tác ở tab chatter. Phiếu ở Nháp: bấm **Tự đánh giá**
(chỉ tham khảo). Sau khi phiếu **Đã duyệt**: nhận nhắc việc và bấm **Xác nhận kết quả** (đồng ý, hoặc có ý kiến kèm nội dung).
Ngoài hai việc này nhân viên không sửa được gì.

### 6.4. Cấu hình bắt buộc trước khi dùng thật

**Loại kỳ và mục tiêu (Đợt B1):** mỗi bộ KPI có một loại kỳ (tháng, sprint, quý); Tạo phiếu cho kỳ chỉ tạo cho nhân viên có bộ cùng loại kỳ. Mục tiêu tính theo độ dài kỳ, nên bộ theo quý phải đặt mục tiêu riêng (ví dụ 60 SP/quý thay vì 20 SP/tháng). **Quản lý trực tiếp** của nhân viên nên thuộc nhóm KPI Manager — kiểm tra ở **KPI › Báo cáo › Quản lý chưa có quyền KPI** (nếu không, nhắc việc chuyển cho người duyệt mặc định). **Người duyệt mặc định** đặt ở Thiết lập.

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
| P1 chưa chốt kỳ thì milestone chưa tới hạn tính là chưa đạt | Milestone có deadline trong kỳ nhưng kỳ chưa kết thúc bị tính là chưa đúng hạn | Thấp — chốt phiếu Lead sau khi kỳ kết thúc |
| P4 dùng tổng giờ tới hết kỳ so với giờ kế hoạch cả dự án | `allocated_hours` là của cả dự án, không chia theo kỳ; cần module cầu nối + `hr_timesheet` | Thấp — chỉ khi cài cầu nối |
| Mục tiêu không tự co giãn theo độ dài kỳ | Bộ KPI theo quý cần mục tiêu riêng (20 SP/tháng khác 60 SP/quý); hệ thống không tự nhân | Thấp — nhắc ở hướng dẫn cấu hình (Chương 6.4) |
| P2 chỉ tính phiếu cấp dưới có kỳ nằm trọn trong kỳ của Lead | Kỳ cấp dưới dài hơn hoặc lệch kỳ của Lead (ví dụ Lead theo tháng, cấp dưới theo quý) thì không tính, P2 "Không áp dụng" | Thấp — chọn loại kỳ của Lead dài hơn hoặc bằng cấp dưới |
| "Lỗi dữ liệu" trên thẻ Tổng quan là ảnh chụp hiện tại | Báo cáo Kiểm tra dữ liệu tính theo dự án, không theo kỳ, nên con số này giống nhau trên mọi thẻ; chỉ hiện trên kỳ đang mở và ghi rõ "hiện tại, toàn hệ thống, không theo kỳ" | Thấp |
| Phản hồi 360 **không đảm bảo ẩn danh tuyệt đối** | Quản trị viên Surveys vẫn xem được từng câu trả lời của từng người (survey.user_input); hệ thống chỉ **giảm khả năng nhận diện người chấm** — quản lý KPI không đọc được câu trả lời, phiếu chỉ hiện điểm trung bình, và dưới 3 câu trả lời thì F1 "Không áp dụng" và không hiện số. Ở công ty nhỏ, ngưỡng 3 người chỉ có ý nghĩa khi team đủ đông | Trung bình — cần nói rõ với người tham gia |
| S1 (mức đáp ứng kỹ năng) chỉ có khi cài `hr_skills` + `project_kpi_skills`, và chỉ đúng khi hồ sơ kỹ năng được cập nhật | Kỹ năng và kỹ năng yêu cầu của chức danh do nhân sự/quản lý nhập; so theo mức tiến độ (level_progress) nên các mức của hai bên phải cùng loại kỹ năng | Thấp |
| Gửi duyệt được trước khi kỳ kết thúc | Hệ thống chỉ đòi phiếu Nháp, đã Tính KPI, đã chấm chỉ số nhập tay và (nếu thiếu dữ liệu) có xếp loại tay; **không** chặn theo ngày cuối kỳ, nên quản lý có thể chốt phiếu khi dữ liệu còn thiếu. Quy ước vận hành: chỉ Gửi duyệt sau khi kỳ kết thúc; giữa kỳ dùng Tính KPI / tạm tính hằng tuần để theo dõi. Phiếu đã gửi bị khoá nên dữ liệu đến sau không đổi điểm | Thấp — quy ước vận hành |
| Số tạm tính giữa kỳ | D1 giữa kỳ không bị thấp giả tạo (task có deadline chưa tới và chưa xong bị loại khỏi mẫu số, có test `test_d1_on_time`); nhưng nhiều dòng "Không áp dụng" vì chưa đủ khối lượng tối thiểu, P1/B1 thấp vì milestone/yêu cầu chưa tới hạn tính là chưa đạt (domain không có "hôm nay"), và xếp loại của phiếu Nháp chỉ là tạm tính | Thấp |
| Gợi ý mục tiêu cần ≥ 3 kỳ đã duyệt cùng loại kỳ | Ít hơn thì hiện "Chưa đủ dữ liệu"; phiếu thiếu dữ liệu và dòng Không áp dụng không tham gia | Thấp |
| Cron cập nhật `days_late` ghi `write_date` dù giá trị không đổi | Đã kiểm chứng bằng script thật (không suy luận): `_cron_update_days_late()` gọi `flush_recordset(["days_late"])` cho mọi task quá hạn chưa xong mỗi ngày, và Odoo luôn ghi `write_date`/`write_uid` cùng lúc flush một field, kể cả khi `days_late` ra cùng giá trị cũ | Thấp — chỉ ảnh hưởng cách sắp xếp "mới cập nhật gần đây" ở các view khác, không ảnh hưởng điểm KPI |

---

## Chương 9 — Hướng phát triển

**Trạng thái:** mọi tính năng trong kế hoạch này đã được triển khai trừ **Bước 6** (kỳ khác nhau theo bộ KPI đã làm ở Đợt B1; còn lại nhân viên kiêm nhiệm — xem 9.6 "Không làm"). Mã nguồn dùng để bảo vệ là chính `main` (Chương 5.7, 10), phát triển trực tiếp trên `main`, một mã nguồn duy nhất (không tách nhánh riêng, không có bản bảo vệ riêng). Các Bước 0–5 ở 9.1–9.4 là kế hoạch ban đầu và nay đều đã triển khai; 9.6 ghi các đợt hoàn thiện sau đó.

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

**Ưu tiên 2 — Team Lead/PM — ĐÃ TRIỂN KHAI (Bước 4):** Odoo Project có sẵn dữ liệu cấp dự án. `project.milestone` (đã kiểm
tra trên source 19.0) có `deadline`, `is_reached`, `reached_date`.

| Mã | Chỉ số | Cách tính | Chiều | Mục tiêu | Trọng số | Khối lượng tối thiểu |
|---|---|---|---|---|---|---|
| P1 | Tỷ lệ milestone đạt đúng hạn | **Domain, tỷ lệ** (chỉ cấu hình, không hàm Python): milestone có deadline trong kỳ, `is_reached_on_time` / tổng; dự án của Lead = `project_id.user_id` | Cao tốt | 80% | 25 | 2 milestone |
| P2 | Điểm KPI trung bình của team | **Python `_metric_p2()`**: điểm cuối trung bình phiếu cấp dưới trực tiếp, cùng kỳ, trạng thái Đã gửi/Đã duyệt | Cao tốt | 80 | 25 | 2 phiếu |
| P3 | Chất lượng dữ liệu dự án | **Python `_metric_p3()`**: bản ghi sạch / tổng bản ghi (từ `kpi.data.quality.report`) của dự án Lead quản lý | Cao tốt | 90% | 20 | 10 bản ghi |
| P4 | Giờ thực tế so với kế hoạch | **Module cầu nối `project_kpi_timesheet`**, `_metric_p4()`: \|giờ thực tế / giờ kế hoạch − 1\| × 100 | Thấp tốt | 15% lệch | 15 (bộ có P4) | 1 dự án |
| P5 | Đánh giá của cấp trên | Nhập tay | Cao tốt | 4 | 30 | 0 |

**Các quyết định thiết kế của Bước 4:**

- **Dự án của Lead** là dự án có `project.project.user_id` = người dùng của Lead (P1, P3, P4 dùng chung cách xác định).
- **P1:** thêm cờ lưu sẵn `project.milestone.is_reached_on_time` (đã đạt và `reached_date ≤ deadline`) rồi cấu hình bằng domain — dùng lại cơ chế Bước 1, `kpi.engine` không có hàm `_metric_p1`. Milestone không có deadline không vào mẫu số (lọc theo deadline). Milestone chưa đạt mà quá hạn tính là trễ; kỳ chưa kết thúc thì milestone chưa tới hạn cũng chưa đạt, nên chốt phiếu Lead sau khi kỳ kết thúc.
- **P2 — tránh phải sắp xếp thứ tự trong wizard:** chỉ lấy phiếu cấp dưới **đã Gửi hoặc Đã duyệt trong cùng kỳ và đủ dữ liệu (`insufficient_data = False`)**. Phiếu thiếu dữ liệu (ví dụ nhân viên mới) chỉ tính điểm trên một phần nhỏ chỉ số áp dụng, không phản ánh hiệu suất, nên bị bỏ cả ở giá trị lẫn khối lượng — nếu không quản lý sẽ bị kéo điểm xuống vì có nhân viên mới (bản đầu mắc lỗi này, đã sửa); số phiếu hợp lệ là khối lượng, dưới `min_volume` thì "Không áp dụng" thay vì ra số sai. Quy trình tự nhiên đã đúng (cấp dưới chốt trước, Lead tính sau), và vì không tính phiếu của chính Lead nên không có vòng lặp. Điều đó thay cho ràng buộc "P2 phải tính sau phiếu cấp dưới" đề xuất trước đó.
- **P3 (theo kỳ từ Đợt A4):** tỷ lệ tiêu chí sạch / tổng tiêu chí, chỉ xét bản ghi thuộc kỳ của các dự án Lead quản lý: Feature xong có `date_end` trong kỳ (sạch nếu có story point) và bug tạo trong kỳ (mỗi bug hai tiêu chí: có task gốc, đủ phân loại). Nhờ giới hạn trong kỳ, mở lại rồi tính lại phiếu Lead của kỳ cũ cho cùng kết quả. Bản đầu dùng ảnh chụp hiện tại của báo cáo Kiểm tra dữ liệu. Tiêu chí "task xong thiếu ngày hoàn thành" không dùng cho P3 vì task thiếu `date_end` không xác định được thuộc kỳ nào — lỗi đó vẫn nằm trong báo cáo Kiểm tra dữ liệu.
- **P4 — không thêm chiều "gần 100% tốt":** giá trị thực tế định nghĩa là độ lệch tuyệt đối, chiều "Thấp tốt", nên engine không phải sửa. Giờ thực tế là tổng timesheet tới hết kỳ (giờ kế hoạch là của cả dự án, không chia theo kỳ).
- **Module cầu nối `project_kpi_timesheet`:** `depends: project_kpi_management, hr_timesheet`, `auto_install: True`; P4 và bộ "Team Lead / PM (có giờ làm)" (P1–P5, trọng số 20/20/15/15/30) nằm hoàn toàn trong module này, test riêng trong module này. Khi chưa cài, bộ "Team Lead / PM" gốc vẫn chạy với P1–P3 và P5. Bộ có P4 là bộ riêng, không sửa bộ gốc, để gỡ cầu nối không làm lệch tổng trọng số.
- **Quyết định về `kpi_dev`:** **không** cài `hr_timesheet`/cầu nối trên `kpi_dev` (cài sẽ thêm app Timesheet vào database demo). P4 được kiểm chứng bằng 6 test của module cầu nối trên một database riêng (`-i project_kpi_timesheet`) và bằng bước P4 của `scripts/pre_defense_check.py` (bước này tự bỏ qua nếu cầu nối chưa cài).

**Ưu tiên 3 — BA — ĐÃ TRIỂN KHAI (Bước 5):** thêm loại task `requirement` (filter "Yêu cầu"), Feature trỏ về yêu cầu gốc qua
`requirement_id`; **BA là người trong `user_ids` của task Yêu cầu**.

| Mã | Chỉ số | Cách tính | Chiều | Mục tiêu | Trọng số | Khối lượng tối thiểu |
|---|---|---|---|---|---|---|
| B1 | Yêu cầu hoàn thành đúng hạn | **Domain, tỷ lệ** (chỉ cấu hình): task Yêu cầu có deadline trong kỳ, cờ `is_on_time` / tổng (bỏ task huỷ) | Cao tốt | 90% | 25 | 3 yêu cầu |
| B2 | Mật độ bug do yêu cầu sai | **Python `_metric_b2()`**: bug `bug_root_cause = requirement` (valid/wont_fix) → `origin_task_id` → `requirement_id` → BA, chia cho số yêu cầu BA hoàn thành trong kỳ; quy kỳ theo ngày hoàn thành của yêu cầu (giống D3 quy theo task gốc) | Thấp tốt | 0,3 bug/yêu cầu | 30 | 1 yêu cầu |
| B3 | Yêu cầu qua review lần đầu | **Domain, tỷ lệ**: yêu cầu xong trong kỳ đã qua review (`review_approve_count > 0` hoặc `review_reject_count > 0`) mà `review_reject_count = 0` / yêu cầu xong trong kỳ đã qua review (cùng quy tắc D5) | Cao tốt | 70% | 25 | 3 yêu cầu |
| B4 | Đánh giá của quản lý | Nhập tay | Cao tốt | 4 | 20 | 0 |

**Các quyết định thiết kế của Bước 5:**

- **Cờ `is_on_time` lưu sẵn** để B1 chỉ cần cấu hình; D1 không bị sửa. Dùng `days_late = 0` thay vì so trực tiếp `date_end <= date_deadline` để cùng quy tắc ngày địa phương với D1 (xong muộn trong cùng ngày deadline vẫn đúng hạn).
- **Một lần phân loại bug, trách nhiệm quy đúng người:** bug "yêu cầu sai" bị loại khỏi D3, D4 của Developer (chỉ nguyên nhân `code`) và được tính vào B2 của BA. Có test chứng minh đúng một bug: Developer không bị tính, BA bị tính (`test_same_bug_not_for_developer_but_for_ba`).
- **Bug không quy được về BA:** bug `bug_root_cause = requirement` nhưng task gốc không có `requirement_id` (hoặc bug không có task gốc) không thuộc BA nào — báo cáo Kiểm tra dữ liệu có thêm cột **"Bug do yêu cầu nhưng không truy được yêu cầu gốc"** để quản lý bổ sung liên kết trước khi chốt kỳ.
- **B3 mẫu số:** dùng "đã qua review" như D5 (không dùng trạng thái `03_approved` vì task Done và Approved là hai giá trị loại trừ của cùng field `state`, task đã Done không còn là Approved).
- **Giới hạn:** B1 như P1 — kỳ chưa kết thúc thì yêu cầu chưa tới hạn cũng tính là chưa đúng hạn (domain không có "hôm nay"), nên chốt phiếu BA sau kỳ.

**Để sau (ngoài phạm vi, khác bản chất):**

| Team | Lý do để sau |
|---|---|
| DevOps | Chỉ số chính (DORA) cần dữ liệu CI/CD từ hệ thống ngoài, không có sẵn trong Odoo |
| Support | Odoo Helpdesk là bản Enterprise; trên Community phải dùng task làm ticket, không chuẩn |
| Sales, HR | Không thuộc lõi sản xuất phần mềm — hệ thống đã **chứng minh làm được** bằng demo Sales nhập tay (Chương 7), không cần làm thêm để minh hoạ nguyên tắc không hardcode |

### 9.3. Tính năng khác giúp hệ thống linh hoạt hơn

**Bước 3 — chấm điểm theo bậc (đã triển khai), các quyết định thiết kế:**

- Mỗi dòng bộ KPI có thể gắn một **bảng bậc** (`kpi.score.scale`); để trống thì tính tuyến tính như cũ. Bảng bậc dùng chung được cho nhiều chỉ số.
- **Tra theo % đạt mục tiêu**, không theo giá trị thực tế, nên không phụ thuộc đơn vị và vẫn đúng khi mục tiêu đổi theo phòng ban.
- **Thấp tốt:** đổi sang % đạt mục tiêu trước bằng đúng công thức cũ (`mục tiêu / thực tế`, thực tế = 0 lấy mức trần), rồi mới tra bậc — không cần bảng bậc riêng cho chiều ngược.
- **Chụp JSON vào dòng phiếu** (`scale_json`, `[[% từ, điểm], ...]`), cùng nguyên tắc bất biến với mục tiêu: sửa bảng bậc sau khi tạo phiếu không đổi phiếu cũ.
- **Điểm trần vẫn áp dụng sau khi tra bậc** (bậc cho 130 vẫn ra tối đa 120); chỉ số Không áp dụng không tra bậc.
- **Kiểm tra bảng bậc:** mỗi bậc chỉ khai báo điểm bắt đầu và kéo dài tới bậc kế tiếp (không gồm), bậc cuối không giới hạn — nên khoảng không thể chồng nhau; bậc thấp nhất bắt buộc từ 0% nên phủ liên tục. Bảng rỗng, trùng điểm bắt đầu, hở khỏi 0 đều bị chặn khi lưu. Kiểm tra chạy khi lưu bảng bậc (đường của form) **và chạy lại lúc dùng**: khi tạo phiếu và chụp bảng, bảng không hợp lệ (rỗng, thiếu bậc 0%) bị từ chối — nên dù Admin ghi thẳng vào từng bậc qua API, sai số cũng không đi vào điểm. Không ẩn được bảng bậc khi còn bộ KPI hoạt động dùng; không xoá được (ràng buộc khoá ngoại).
- Phiếu hiện cột "% đạt mục tiêu" và tên bảng bậc (chụp lúc tạo phiếu); PDF in thêm dòng "đạt x% mục tiêu · bậc ..." dưới điểm của dòng dùng bảng bậc; REST API trả `achievement_pct` và `scale` — để nhân viên hiểu vì sao 85% mà được 75 điểm. Dữ liệu mẫu có "Bậc 4 mức (mẫu)" chưa gắn vào bộ nào, để demo gắn trực tiếp.


| # | Tính năng | Vấn đề giải quyết | Cách làm | Giá trị |
|---|---|---|---|---|
| 1 | Chỉ số cấu hình không cần code | Xem 9.1 | Xem 9.1 — **đã triển khai** | Rất cao — mở khoá 9.2 |
| 2 | **ĐÃ TRIỂN KHAI (Bước 3)** — Cách chấm điểm theo bậc | Hiện chỉ có tỷ lệ tuyến tính (`_score()`, Chương 3.3); nhiều công ty chấm theo bậc, ví dụ ≥90% → 100 điểm, 80–90% → 80 điểm | Mỗi dòng template chọn "Tuyến tính" hoặc "Theo bảng bậc"; bảng bậc là các dòng (từ, đến, điểm) | Cao |
| 3 | Điểm team góp vào điểm cá nhân | Phần mềm là việc nhóm, nhưng điểm hiện hoàn toàn cá nhân | Một dòng template là "Điểm trung bình của team" (lấy từ `kpi.team.report`), trọng số 10–20% | Cao, đúng xu hướng ngành |
| 4 | Kỳ đánh giá khác nhau theo bộ KPI | Dev hợp chu kỳ tháng; BA, PM hợp chu kỳ quý | Thêm `period_type` cho template; wizard tạo phiếu chỉ tạo cho template cùng loại kỳ | Trung bình |
| 5 | Nhân viên kiêm nhiệm | Một người vừa là Dev vừa là Team Lead | Cho phiếu nhận thêm template phụ, gộp dòng và chuẩn hoá trọng số về 100 | Trung bình, phức tạp hơn |

### 9.4. Thứ tự triển khai đề xuất (khi làm tiếp sau bảo vệ)

| Bước | Việc | Lý do thứ tự |
|---|---|---|
| 1 | ~~Chỉ số cấu hình không cần code (9.1)~~ | **Đã triển khai** — xem Chương 3.3 |
| 2 | ~~Bộ Tester tự động (9.2, Ưu tiên 1)~~ | **Đã triển khai** — 109/109 test đạt, xem 9.2 |
| 3 | ~~Chấm điểm theo bậc (9.3 #2)~~ | **Đã triển khai** — 121/121 test đạt tại thời điểm đó, xem 9.3 #2 |
| 4 | ~~Bộ Team Lead/PM + điểm team (9.2 Ưu tiên 2, 9.3 #3)~~ | **Đã triển khai** — 130/130 test đạt + 6 test module cầu nối tại thời điểm đó, xem 9.2 |
| 5 | ~~Bộ BA (9.2 Ưu tiên 3)~~ | **Đã triển khai** — 143/143 test đạt tại thời điểm đó, xem 9.2 |
| 6 | Kỳ khác nhau theo bộ KPI, kiêm nhiệm (9.3 #4, #5) | Chỉ cần khi đã có nhiều bộ KPI chạy song song |

### 9.5a. Chỉ số cấu hình biết "hôm nay" (hướng phát triển)

Chỉ số cấu hình bằng domain (Chương 9.1) chỉ có ba chuỗi giữ chỗ: `$CURRENT_USER_ID`, `$PERIOD_START`, `$PERIOD_END`. Domain không biết "hôm nay", nên không phân biệt được việc **chưa tới hạn** với việc **trễ hạn**: đó là lý do D1 (đúng hạn) vẫn viết bằng Python để loại task chưa tới hạn khỏi mẫu số, còn P1 (milestone) và B1 (yêu cầu) giữa kỳ thấp hơn thực tế (Chương 8.3). Hướng cải thiện gọn: thêm chuỗi giữ chỗ `$TODAY` (và có thể `$PERIOD_END` đã có sẵn) được hệ thống thay bằng giá trị thật SAU khi đọc domain bằng `ast.literal_eval`, đúng cách các chuỗi giữ chỗ hiện có — vẫn không chạy biểu thức tuỳ ý. Khi đó có thể chuyển thêm chỉ số sang dạng cấu hình và bỏ giới hạn "milestone chưa tới hạn tính là chưa đạt".

### 9.5. Hướng mở rộng khác (đã nêu từ trước)

| Hướng | Nội dung |
|---|---|
| Nhân viên phản hồi đầy đủ hơn | Đã làm bản tham khảo (Mục 6: wizard Tự đánh giá, không cộng điểm, không thêm trạng thái); mở rộng tiếp theo hướng thêm bước "Nhân viên xác nhận" chính thức trong quy trình phiếu nếu cần |
| Đo theo team đầy đủ hơn | Đã làm bản gọn theo dự án (`kpi.team.report`, Chương 3.3); mở rộng tiếp theo hướng các bộ chỉ số DORA, SPACE (deploy frequency, lead time...) — xem 9.2, để sau vì cần tích hợp CI/CD ngoài |
| Đồng bộ Jira, GitLab | Dùng REST API (đã có sẵn khung) để lấy dữ liệu task, review từ công cụ ngoài |
| Coverage thật thay D6 | CI đẩy số liệu coverage thật qua REST API (`POST /api/kpi/evaluations/<id>/metrics/D6`), thay cho cờ tự xác nhận |
| Task Group / WBS | Xây model riêng khi cần quản lý theo nhóm việc có người phụ trách, người hỗ trợ |
| Thông báo | Nhắc hạn nộp phiếu, nhắc duyệt (đã làm riêng phần báo điểm thấp: duyệt phiếu Cần cải thiện tự tạo nhắc việc "Kế hoạch cải thiện" cho quản lý trực tiếp, xem Chương 5.3) |

### 9.6. Các đợt hoàn thiện sau Bước 5

Sau Bước 5 các tính năng còn lại được chia theo giá trị cho báo cáo và rủi ro; mỗi đợt xong thì kiểm tra đủ (test qua hành động thật, tính tay trước khi chạy, `pre_defense_check.py` trên tài khoản thật, tài liệu) rồi hợp nhất vào `main`. Sau ngày dừng chỉ commit sửa lỗi chặn demo.

| Đợt | Tính năng | Trạng thái |
|---|---|---|
| A (vận hành) | A1 nhắc việc theo quy trình; A2 nhân viên xác nhận kết quả; A3 tạm tính giữa kỳ; A4 P3 theo kỳ; A5 báo cáo theo phòng ban | **Đã triển khai** |
| B (linh hoạt cấu hình) | B1 kỳ riêng theo bộ KPI; B2 gợi ý mục tiêu từ lịch sử | **Đã triển khai** |
| C (trình bày) | C1 màn hình tổng quan KPI (kanban theo kỳ) | **Đã triển khai** |
| D (đánh giá đa chiều) | D2 đánh giá năng lực (`hr_skills`); D1 phản hồi 360 độ (`survey`) | **Đã triển khai cả hai** |

**Quyết định thiết kế của Đợt A:**

- **A1:** nhắc việc chỉ giao được cho MỘT người nên không giao cho cả nhóm Admin — dùng **Người duyệt mặc định** (Thiết lập, phải là KPI Admin). Người nhận phải đọc được phiếu (Odoo từ chối giao nhắc việc cho người không có quyền đọc tài liệu), nên quản lý không thuộc nhóm KPI thì nhắc việc "Hoàn tất" chuyển cho người duyệt mặc định; người duyệt mặc định trùng với nhân viên hoặc quản lý của phiếu (xung đột vai trò) thì bỏ qua và ghi chú vào chatter. Toàn bộ nằm ở một hàm idempotent `_sync_workflow_activities()` gọi sau `create` và mỗi lần đổi `state`, nên Trả về/Mở lại tự đưa nhắc việc về đúng trạng thái.
- **A2:** không thêm trạng thái vào quy trình (sẽ đụng khoá phiếu, quyền, nhắc việc và test của cả hệ thống); làm **sau** khi Đã duyệt bằng wizard cùng cách với Tự đánh giá. Nhân viên chỉ xác nhận được khi phiếu Đã duyệt; chọn "Có ý kiến" bắt buộc ghi nội dung; Mở lại phiếu xoá xác nhận cũ vì kết quả có thể đổi. Xác nhận chỉ ghi nhận ý kiến, không đổi điểm hay trạng thái.
- **A3:** cron hằng tuần gọi lại `action_compute_kpi` cho phiếu Nháp của kỳ đang mở — hàm này vốn chỉ ghi dòng do engine tính (`_is_engine_computed()`) nên không đè D9, mục tiêu đã sửa hay xếp loại tay. Tạm tính **không** đặt `computed_date` (điều kiện để Gửi duyệt) mà ghi `last_computed_date`, để Gửi duyệt vẫn đòi quản lý chủ động bấm Tính KPI ít nhất một lần.
- **A4:** xem Chương 9.2, quyết định P3.
- **A5:** báo cáo gom theo `department_id` **đã chụp trên phiếu** (không nối từ task sang phòng ban bằng SQL, vì phòng ban hiện tại nằm ở `hr.version`): điểm và phân bố xếp loại theo phòng ban, điểm trung bình từng chỉ số theo phòng ban; mặc định chỉ tính phiếu đã duyệt, chỉ số được áp dụng.

**Quyết định thiết kế của Đợt B:**

- **B1:** thêm `period_type` cho bộ KPI (kỳ đã có sẵn trường này), mặc định tháng nên bản ghi cũ không cần migration. `_eligible_employees` lọc theo loại kỳ nên wizard, bản xem trước và cron cùng đúng. Đổi loại kỳ bị chặn khi bộ còn phiếu ở kỳ đang mở. Mục tiêu không tự co giãn theo độ dài kỳ — ghi ở hướng dẫn cấu hình.
- **P2 định nghĩa lại:** lấy phiếu Đã gửi/Đã duyệt, đủ dữ liệu, có kỳ **nằm trọn** trong kỳ của Lead; **trung bình theo từng người trước, rồi giữa các người** (gộp chung mọi phiếu thì người làm đủ 3 tháng của một quý có trọng số gấp 3 người mới vào); khối lượng là số cấp dưới có ít nhất một phiếu hợp lệ nên `min_volume = 2` giữ nguyên ý nghĩa. Cùng loại kỳ thì cho đúng kết quả cũ (điểm Phúc vẫn 80,226 — bằng chứng thay đổi không làm hỏng hành vi hiện có).
- **B2:** gợi ý chỉ là tham khảo (không tự ghi). Nguồn: `actual` của chính chỉ số ở phiếu Đã duyệt, dòng được áp dụng, phiếu đủ dữ liệu, cùng loại kỳ, cùng nhân viên (hoặc cùng phòng ban đã chụp trên phiếu), tối đa 6 kỳ gần nhất, tối thiểu 3 kỳ. Ba mức là phân vị 25/50/75 nội suy tuyến tính, **đặt nhãn Dễ / Vừa / Khó theo độ khó và đảo phân vị theo chiều của chỉ số** (chỉ số "thấp là tốt": số thấp hơn mới là mục tiêu khó hơn, nhãn Thấp/Giữa/Cao sẽ bị hiểu ngược). Giá trị gợi ý hiển thị 4 chữ số lẻ; khi áp dụng, mục tiêu làm tròn theo độ chính xác của trường mục tiêu (2 chữ số).
- **Dữ liệu mẫu:** các bộ KPI mẫu giữ loại kỳ tháng để không phải tính lại số liệu kịch bản demo; trường hợp theo quý được chứng minh bằng test riêng. Lịch sử cho gợi ý nằm ở một phòng ban riêng ("Phòng Kỹ thuật (lịch sử mẫu)") không đụng nhân viên của kịch bản chính, nhưng phòng này hiện trong báo cáo theo phòng ban.
- **Quản lý chưa có quyền KPI:** báo cáo Kiểm tra dữ liệu tính theo dự án nên không chứa được lỗi theo nhân viên này (và `hr.employee` chỉ đọc được bởi nhóm Nhân sự); danh sách được dựng bằng sudo từ menu riêng cạnh báo cáo đó.
- **Dữ liệu mẫu đặt sẵn người duyệt mặc định = admin** (không đặt ở data của module để doanh nghiệp thật tự cấu hình); `scripts/pre_defense_check.py` kiểm tra giá trị này.

**Quyết định thiết kế của Đợt C1:**

- **Nền:** kanban trên `kpi.period` (không OWL/JavaScript), mỗi thẻ một kỳ có nhãn tháng/quý/sprint, thanh tiến độ "x/y đã duyệt", điểm trung bình phiếu đã duyệt, và các con số Nháp / Đã gửi / Đã duyệt / Cần cải thiện / Thiếu dữ liệu / Chờ xác nhận — **mỗi con số là một nút `type="object"`** mở danh sách phiếu với đúng domain (kỳ + trạng thái hoặc xếp loại). "Cần cải thiện" chỉ tính phiếu đã gửi hoặc đã duyệt (xếp loại của phiếu Nháp chỉ là tạm tính).
- **Hiệu năng:** các field số liệu là compute không lưu nhưng tính bằng **một `_read_group` cho mọi kỳ đang hiển thị**, không `search_count` từng kỳ (nếu không mỗi lần mở là hàng chục truy vấn); test khoá bằng so sánh số truy vấn giữa 1 kỳ và 8 kỳ.
- **Phân quyền:** không dùng `sudo()`, record rule tự áp dụng — quản lý chỉ thấy số của team mình, Admin thấy tất cả (test: cùng một kỳ, hai người thấy số khác nhau; nút cũng tôn trọng quyền).
- **Lỗi dữ liệu:** báo cáo Kiểm tra dữ liệu tính theo dự án, không theo kỳ, nên trên thẻ ghi rõ "hiện tại, toàn hệ thống, không theo kỳ", chỉ hiện cho quản lý trở lên và chỉ trên kỳ đang mở; bấm vào mở báo cáo.
- **Mở app:** menu "Tổng quan" có sequence nhỏ nhất nên vào app KPI mở thẳng màn hình này; mặc định lọc kỳ đang mở, bỏ lọc được.
- **Chưa kiểm chứng bằng trình duyệt:** cấu trúc kanban được kiểm bằng `get_views` (hợp lệ), số liệu và nút bằng test; hiển thị trực quan (bố cục thẻ, thanh tiến độ) cần xem bằng mắt khi chạy thử trước buổi bảo vệ.

**Quyết định thiết kế của Đợt D2 (đã đọc source 19.0 trước khi thiết kế):**

- **Nguồn dữ liệu có thật:** `hr.employee.skill` (kỹ năng của nhân viên) và `hr.job.skill` (kỹ năng yêu cầu của chức danh) dùng chung `hr.individual.skill.mixin` — cùng `skill_id`, `skill_level_id`, `level_progress` (0–100), `valid_from`, `valid_to`. So mức bằng `level_progress` nên đúng cho mọi loại kỹ năng, không phụ thuộc thứ tự mức.
- **Module cầu nối `project_kpi_skills`** (`depends: project_kpi_management, hr_skills`, `auto_install: True`): chỉ số **S1 "Mức đáp ứng kỹ năng"** (`_metric_s1()` kế thừa `kpi.engine`) và bộ riêng **"Developer (có năng lực)"** (trọng số D4 và D9 giảm để thêm S1 10%); bộ Developer gốc không đổi, nên số liệu kịch bản demo giữ nguyên.
- **Chức danh đã chụp trên phiếu:** `compute_actual(..., evaluation=ev)` (chức danh lấy từ `ev.job_id`; vẫn nhận `job=` riêng cho nơi không có phiếu) — S1 so theo chức danh lúc tạo phiếu chứ không phải chức danh hiện tại, cùng nguyên tắc chụp như mục tiêu và bảng bậc.
- **Hiệu lực theo ngày cuối kỳ:** chỉ xét bản ghi có `valid_from ≤ ngày cuối kỳ` và (`valid_to` trống hoặc `≥ ngày cuối kỳ`). Odoo tự đóng bản cũ (`valid_to` = hôm qua) khi nâng mức, nên tính lại phiếu kỳ cũ cho cùng kết quả. Nhiều bản ghi cùng kỹ năng còn hiệu lực thì lấy mức cao nhất.
- **Kết quả:** kỹ năng đạt / kỹ năng yêu cầu × 100; khối lượng = số kỹ năng yêu cầu; chức danh không yêu cầu kỹ năng nào → "Không áp dụng". Thiếu kỹ năng tính là không đạt.
- **Dữ liệu mẫu** (nạp bởi `kpi.demo._load_skills_scenario`, idempotent): loại kỹ năng "Kỹ năng kỹ thuật" 4 mức 25/50/75/100; Lập trình viên yêu cầu Python 75, Odoo 50, SQL 50; An có Python 100, Odoo 50, SQL 25 → 2/3.

**Quyết định thiết kế của Đợt D1 (đã đọc source `survey` 19.0 trước khi thiết kế):**

- **Module cầu nối `project_kpi_survey`** (`depends: project_kpi_management, survey`, `auto_install: True`): khảo sát mẫu "Phản hồi 360 độ" nằm trong data — 4 câu chọn 1 đáp án, mỗi đáp án có điểm 1–5 (`answer_score`), bật chấm điểm (`scoring_without_answers`), `access_mode = token` (chỉ người được mời) và bắt buộc đăng nhập. `scoring_percentage` của một câu trả lời = tổng điểm / điểm tối đa (20), nên 4/5 mỗi câu = 80%.
- **Luồng:** phiếu Nháp → quản lý bấm **Mời đánh giá 360**, chọn người → hệ thống tạo câu trả lời riêng cho từng người bằng `survey._create_answer(user=...)` (chạy bằng sudo vì quản lý KPI không có quyền Surveys) và **nhắc việc kèm link** (không gửi email nên demo không cần máy chủ thư; dùng lại cơ chế nhắc việc của Đợt A). Nhắc việc nằm trên `kpi.feedback.request` (không nằm trên phiếu) vì người được mời không đọc được phiếu của người khác. Người đánh giá nộp bài thì `survey.user_input._mark_done` tự đánh dấu xong nhắc việc. "Tính KPI" lấy các câu trả lời đã hoàn thành tới lúc đó.
- **Quy tắc:** người đánh giá phải là người dùng nội bộ, không trùng, không phải chính nhân viên (đã có tự đánh giá riêng); chỉ mời khi phiếu Nháp; phiếu đã gửi thì câu trả lời đến sau không đổi điểm (phiếu đã khoá, không tính lại).
- **F1:** trung bình `scoring_percentage` của câu trả lời `done`, bỏ `test_entry`; khối lượng = số câu trả lời hoàn thành, `min_volume = 3`. Dưới 3 thì hàm trả giá trị 0 chứ không trả điểm của một hai người, và phiếu không hiện điểm trung bình — phiếu chỉ hiện số người đã mời, đã trả lời và điểm trung bình khi đủ ngưỡng.
- **Quyền:** quản lý xem được danh sách người được mời và trạng thái (record rule theo nhân viên trực tiếp), nhưng **không đọc được** `survey.user_input` (ACL của module survey chỉ cấp cho nhóm Surveys); người được mời chỉ thấy lời mời của chính mình. Giới hạn ẩn danh ghi ở Chương 8.3.
- **Phát hiện khi làm:** wizard ban đầu đọc `survey_id.scoring_type` bằng quyền của quản lý nên bị `AccessError` — test bắt được ngay; mọi đọc/ghi khảo sát trong wizard nay chạy bằng sudo.

**Không làm (giữ ở Chương 9):** nhân viên kiêm nhiệm (Bước 6b — gộp hai bộ KPI, chuẩn hoá trọng số, xử lý chỉ số trùng, đụng vào khâu tạo phiếu; rủi ro cao nhất); dải xếp loại cấu hình đầy đủ (`final_rating` đang dùng ở màu, PIP, bộ lọc, báo cáo, API và test — ngưỡng đã chỉnh được ở Thiết lập); OKR, đồng bộ Jira/GitLab, DORA, bộ KPI DevOps/Support (cần hạ tầng ngoài hoặc là hệ thống riêng).

---

## Chương 10 — Kết luận

Đồ án đã xây dựng hoàn chỉnh module `project_kpi_management` trên Odoo 19, đáp ứng toàn bộ phạm vi
MVP (31/31 hạng mục) và phần lớn phạm vi Nên có/Mở rộng (7/7 hạng mục), tổng cộng 38/38 hạng mục
trong bảng thống kê triển khai, cộng thêm 6 mục mở rộng sau khi đối chiếu với các hệ thống KPI tương
tự (màu xếp loại, chặn xung đột vai trò, nhắc việc PIP, mục tiêu theo phòng ban, chỉ số theo dự án,
tự đánh giá — Chương 9 cũ, nay đã triển khai). Hệ thống có 206 unit test tự động (183 ở module chính, 6 + 9 + 8 ở ba module cầu nối; 0 lỗi) cộng với
kiểm thử thủ công trên REST API, báo cáo PDF, phân quyền, luồng nghiệp vụ hoàn chỉnh trên dữ liệu
thật, và kiểm tra qua đúng tài khoản thật bằng XML-RPC (`scripts/pre_defense_check.py`, Chương 5.6)
— cách kiểm tra này tự nó đã bắt được một số lỗi mà unit test (chạy bằng superuser) không bắt được.
Nguyên tắc thiết kế cốt lõi — không hardcode vai trò — đã được kiểm chứng bằng demo trực tiếp
(Chương 7), không chỉ dừng ở khẳng định lý thuyết. Các giới hạn còn tồn tại (Chương 8.3) đều đã được
xác định rõ ràng, có hướng xử lý cụ thể (Chương 9), phù hợp để trình bày minh bạch trước hội đồng.

Hệ thống chỉ có **một mã nguồn duy nhất trên nhánh `main`**, đồng nhất với hệ thống đang chạy; mọi đợt phát triển đã hợp nhất vào đó. Quy trình ngày bảo vệ (`git pull` trên `main` → `restore_defense.sh clean` → chờ "tất cả OK") và kịch bản demo nằm ở Chương 5.7, 5.8. Các tag `v1.x-bao-ve` trên GitHub chỉ là lịch sử.

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
