# Hướng dẫn xây dựng module Project KPI — Tuần 1 và Tuần 2

Tài liệu đi lại toàn bộ quá trình xây dựng module `project_kpi_management` trên Odoo 19, **theo đúng thứ tự đã làm**: từ dựng môi trường tới tính KPI tự động và phân quyền. Kết quả cuối tuần 2 là mã nguồn trong repo này (commit "Tuần 2: Phase 4–5"), có 49 unit test đạt.

Mỗi bước gồm 4 phần:
- **Làm gì:** việc cần làm.
- **File:** file tạo hoặc sửa.
- **Mấu chốt:** điều dễ sai, hoặc lý do thiết kế.
- **Kiểm tra:** làm sao biết đã đúng.

Code đầy đủ nằm trong repo. Tài liệu chỉ trích những đoạn quan trọng.

---

## Mục lục

**Tuần 1 — Nền tảng (Phase 0–3)**
1. [Dựng môi trường Docker](#bước-1--dựng-môi-trường-docker)
2. [Tạo database có dữ liệu mẫu](#bước-2--tạo-database-có-dữ-liệu-mẫu)
3. [Tạo khung module](#bước-3--tạo-khung-module)
4. [Đối chiếu source Odoo 19 trước khi thiết kế](#bước-4--đối-chiếu-source-odoo-19-trước-khi-thiết-kế)
5. [Model chỉ số KPI](#bước-5--model-chỉ-số-kpi-kpimetric)
6. [Model bộ KPI theo vai trò](#bước-6--model-bộ-kpi-theo-vai-trò-kpitemplate)
7. [Gắn bộ KPI vào chức danh](#bước-7--gắn-bộ-kpi-vào-chức-danh-hrjob)
8. [Dữ liệu D1–D9 và bộ KPI Developer](#bước-8--dữ-liệu-d1d9-và-bộ-kpi-developer)
9. [Thêm field KPI vào task](#bước-9--thêm-field-kpi-vào-task)
10. [Ghi ngày hoàn thành và đếm lần bị trả về](#bước-10--ghi-ngày-hoàn-thành-và-đếm-lần-bị-trả-về)
11. [Số ngày trễ và tác vụ hằng ngày](#bước-11--số-ngày-trễ-và-tác-vụ-hằng-ngày)
12. [Giao diện task](#bước-12--giao-diện-task)
13. [Dữ liệu demo và bù dữ liệu cũ](#bước-13--dữ-liệu-demo-và-bù-dữ-liệu-cũ)
14. [Kỳ đánh giá](#bước-14--kỳ-đánh-giá-kpiperiod)
15. [Phiếu đánh giá và công thức điểm](#bước-15--phiếu-đánh-giá-và-công-thức-điểm)
16. [Tạo phiếu, khoá phiếu](#bước-16--tạo-phiếu-khoá-phiếu)
17. [Quy trình duyệt và wizard lý do](#bước-17--quy-trình-duyệt-và-wizard-lý-do)
18. [Giao diện phiếu và menu](#bước-18--giao-diện-phiếu-và-menu)
19. [Unit test tuần 1](#bước-19--unit-test-tuần-1)

**Tuần 2 — Lõi KPI (Phase 4–5)**

20. [Khởi tạo Git](#bước-20--khởi-tạo-git)
21. [Đếm lần được duyệt cho D5](#bước-21--đếm-lần-được-duyệt-cho-d5)
22. [KPI Engine](#bước-22--kpi-engine)
23. [Nút Tính KPI trên phiếu](#bước-23--nút-tính-kpi-trên-phiếu)
24. [Dữ liệu mẫu 3 nhân viên và bảng tính tay](#bước-24--dữ-liệu-mẫu-3-nhân-viên-và-bảng-tính-tay)
25. [Sửa lỗi làm tròn điểm](#bước-25--sửa-lỗi-làm-tròn-điểm)
26. [Nhóm quyền KPI](#bước-26--nhóm-quyền-kpi)
27. [Quyền truy cập model](#bước-27--quyền-truy-cập-model)
28. [Record rule](#bước-28--record-rule)
29. [Kiểm tra quyền ở server và giao diện](#bước-29--kiểm-tra-quyền-ở-server-và-giao-diện)
30. [Unit test tuần 2](#bước-30--unit-test-tuần-2)
31. [Kiểm tra bằng đăng nhập 3 vai trò](#bước-31--kiểm-tra-bằng-đăng-nhập-3-vai-trò)
32. [Commit và đẩy lên GitHub](#bước-32--commit-và-đẩy-lên-github)

[Phụ lục: lệnh thường dùng, cấu trúc thư mục, lỗi thường gặp](#phụ-lục)

---

## Chuẩn bị

| Công cụ | Ghi chú |
|---|---|
| Docker Desktop | Bật WSL 2 |
| Git | Kèm Git Bash |
| VS Code | Mở thư mục `D:\Nam4\odoo19-kpi` |
| Python 3 trên máy | Chỉ dùng cho script kiểm tra XML-RPC ở bước 31 |

Đường dẫn dự án không dấu, không khoảng trắng.

---

# TUẦN 1 — NỀN TẢNG

## Bước 1 — Dựng môi trường Docker

**Làm gì:** chạy Odoo 19 và PostgreSQL 16 bằng Docker Compose. Thư mục `addons/` được mount vào container để Odoo đọc module đang viết.

**File:** `docker-compose.yml`, `config/odoo.conf`

```yaml
services:
  db:
    image: postgres:16
    container_name: odoo19-db
    environment: {POSTGRES_USER: odoo, POSTGRES_PASSWORD: odoo, POSTGRES_DB: postgres}
    volumes: [odoo19-db-data:/var/lib/postgresql/data]
  odoo:
    image: odoo:19.0
    container_name: odoo19-web
    depends_on: [db]
    ports: ["8019:8069"]
    environment: {HOST: db, USER: odoo, PASSWORD: odoo}
    volumes:
      - odoo19-web-data:/var/lib/odoo
      - ./addons:/mnt/extra-addons
      - ./config:/etc/odoo
```

```ini
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
db_host = db
db_user = odoo
db_password = odoo
admin_passwd = admin
```

**Mấu chốt:**
- Dùng cổng 8019 để không trùng với dự án Odoo 18 có sẵn trên máy. Tên container và volume cũng khác.
- `admin_passwd = admin` chỉ dùng cho máy dev. Khi deploy phải đổi.

**Kiểm tra:** `docker compose up -d`, rồi mở http://localhost:8019 thấy trang đăng nhập.

## Bước 2 — Tạo database có dữ liệu mẫu

**Làm gì:** tạo database `kpi_dev` để thử nghiệm.

**Mấu chốt:** Odoo 19 **không còn nạp demo mặc định**. Ban đầu (Phase 0) dùng `--with-demo` để có sẵn dự án/task mẫu của module `project`, tiện đối chiếu source. **Từ bước 24, việc này không còn cần thiết nữa**: kịch bản mẫu của module KPI tự tạo stage/dự án riêng, không mượn dữ liệu demo của `project`/`hr` — nên `--with-demo` kéo theo cả loạt nhân viên demo gốc của Odoo (Mitchell Admin, Anita Oliver...) một cách không cần thiết. Cài **không** `--with-demo`, rồi bấm menu **KPI › Cấu hình › Nạp dữ liệu mẫu** khi cần.

## Bước 3 — Tạo khung module

**Làm gì:** tạo cấu trúc thư mục chuẩn, rồi cài module rỗng.

```
addons/project_kpi_management/
├── __init__.py            from . import models, wizard
├── __manifest__.py
├── models/__init__.py
├── wizard/__init__.py
├── views/  data/  tests/
└── security/ir.model.access.csv   (chỉ có dòng tiêu đề)
```

```python
{
    "name": "Project KPI & Performance Management",
    "version": "19.0.1.0.0",
    "depends": ["project", "hr", "calendar"],
    "data": ["security/ir.model.access.csv"],
    "license": "LGPL-3",
    "application": True,
}
```

**Kiểm tra:**

```bash
docker exec odoo19-web odoo -d kpi_dev -i project_kpi_management --with-demo --stop-after-init --http-port 8070
```

Log có dòng `Module project_kpi_management loaded`, và module hiện trong Apps.

> `--http-port 8070`: tiến trình cài đặt chạy song song với server chính trong cùng container, nên phải dùng cổng khác 8069.

## Bước 4 — Đối chiếu source Odoo 19 trước khi thiết kế

**Làm gì:** đọc source trong container trước khi viết code, để không dựa vào tài liệu cũ.

```bash
docker exec odoo19-web grep -n "date_end\|def update_date_end" /usr/lib/python3/dist-packages/odoo/addons/project/models/project_task.py
```

**Phát hiện, và chúng quyết định thiết kế các bước sau:**

| Phát hiện | Hệ quả |
|---|---|
| `date_end` chỉ được ghi khi task vào stage có `fold = True`, và bị **xoá** khi sang stage không fold | Bước 10: tự ghi `date_end` theo trạng thái |
| Stage "Done" của dự án mẫu (`project.project_stage_2`, chỉ có trong demo) có `fold = False` | Bước 13: file demo đặt lại `fold = True` |
| `working_hours_close` (dùng cho D7) tính từ `create_date` đến `date_end` | `date_end` là mốc hoàn thành duy nhất cho cả D1 và D7 |
| `job_id`, `department_id` của nhân viên nằm ở `hr.version`, **không stored** trên `hr.employee` | Bước 16: phiếu lưu bản chụp chức danh, phòng ban |
| `state` của task: `01_in_progress`, `02_changes_requested`, `03_approved`, `04_waiting_normal`, `1_done`, `1_canceled` | Dùng cho D1, D5 |
| Ràng buộc SQL viết bằng `models.Constraint(...)`, không còn `_sql_constraints` | Bước 5, 6 |
| View dùng `<list>` (không còn `<tree>`); `attrs`/`states` bị bỏ, thay bằng `invisible="..."` | Mọi view |
| `name_get()` bị bỏ, thay bằng `_compute_display_name()` | Bước 5 |

## Bước 5 — Model chỉ số KPI (`kpi.metric`)

**File:** `models/kpi_metric.py`, `views/kpi_metric_views.xml`, `security/ir.model.access.csv`

**Làm gì:** model danh mục chỉ số gồm các field `code`, `name`, `category` (Tiến độ / Chất lượng / Quy trình / Cộng tác), `unit`, `direction` (cao tốt / thấp tốt), `compute_mode` (tự động / nhập tay), `description`, `active`.

```python
_code_unique = models.Constraint("UNIQUE(code)", "Mã chỉ số đã tồn tại.")
_rec_names_search = ["code", "name"]          # gõ "D3" trong ô chọn là tìm được

@api.depends("code", "name")
def _compute_display_name(self):
    for metric in self:
        metric.display_name = f"{metric.code} — {metric.name}"

@api.constrains("active")
def _check_archive_in_active_template(self):
    # chặn ẩn chỉ số khi còn bộ KPI đang hoạt động dùng nó
```

**Mấu chốt:**
- Đặt tên `category` chứ không đặt `group`, vì `group` là từ khoá SQL và dễ nhầm với thẻ `<group>` trong view.
- **Quy tắc ẩn:** không cho ẩn chỉ số đang được dùng. Nếu cho ẩn, phiếu tạo mới vẫn chép chỉ số đó vào, nên "ẩn" không có tác dụng thật.
- Model mới nào cũng phải có ngay một dòng trong `ir.model.access.csv`. Tuần 1 tạm cấp cho `base.group_user`, tuần 2 thay bằng nhóm KPI.

**Kiểm tra:** tạo chỉ số trùng mã thì bị chặn. Ô chọn hiển thị dạng "D1 — Hoàn thành đúng hạn".

## Bước 6 — Model bộ KPI theo vai trò (`kpi.template`)

**File:** `models/kpi_template.py` (gồm cả `kpi.template.line`), `views/kpi_template_views.xml`

**Làm gì:** bộ KPI gồm nhiều dòng. Mỗi dòng có `metric_id`, `target`, `weight` (Integer 0–100), `min_volume` (khối lượng tối thiểu để chỉ số được áp dụng).

```python
@api.constrains("line_ids")
def _check_total_weight(self):
    for template in self:
        if template.line_ids and template.total_weight != 100:
            raise ValidationError(...)
```

**Mấu chốt:**
- Ràng buộc tổng = 100 đặt trên **template**, không đặt trên dòng. Lý do: form tách việc sửa và thêm dòng thành nhiều lệnh ghi riêng, nên ràng buộc đặt trên dòng sẽ gặp trạng thái "nửa chừng".
- Template chưa có dòng nào thì vẫn cho lưu.
- **Không** tạo menu hay list riêng cho `kpi.template.line`. Dòng chỉ sửa trong form template, để ràng buộc luôn chạy.
- `weight` để Integer, nên phép so sánh tổng = 100 là chính xác.
- Ràng buộc SQL trên dòng: một chỉ số chỉ xuất hiện một lần trong bộ KPI; trọng số trong 0–100; `min_volume >= 0`.
- Không cho ẩn bộ KPI đang gắn với chức danh.

**Kiểm tra:** lưu bộ KPI có tổng 90 thì bị chặn. Trong cùng một lần lưu, vừa sửa dòng cũ vừa thêm dòng mới sao cho tổng 100 thì lưu được.

## Bước 7 — Gắn bộ KPI vào chức danh (`hr.job`)

**File:** `models/hr_job.py`, `views/hr_job_views.xml`

```python
class HrJob(models.Model):
    _inherit = "hr.job"
    kpi_template_id = fields.Many2one("kpi.template", string="Bộ KPI", ondelete="restrict")
```

**Mấu chốt:** các tab trong form chức danh gốc mặc định bị ẩn. Vì vậy field được chèn ngay dưới tiêu đề: `xpath //div[hasclass('oe_title')]`, `position="after"`.

## Bước 8 — Dữ liệu D1–D9 và bộ KPI Developer

**File:** `data/kpi_metric_data.xml`, `data/kpi_template_data.xml`

**Làm gì:** cài sẵn 9 chỉ số và bộ KPI Developer:

| Mã | Mục tiêu | Trọng số | Khối lượng tối thiểu | Chiều |
|---|---|---|---|---|
| D1 Đúng hạn | 90% | 20 | 3 task có deadline | cao tốt |
| D2 Story point | 20 SP | 10 | 0 (luôn áp dụng) | cao tốt |
| D3 Mật độ lỗi | 0,3 bug/SP | 15 | 1 SP | thấp tốt |
| D4 Lỗi production | 5% | 15 | 1 bug | thấp tốt |
| D5 Pass review | 80% | 10 | 3 task qua review | cao tốt |
| D6 Unit test | 70% | 10 | 1 Feature | cao tốt |
| D7 Sửa bug nghiêm trọng | 24 giờ | 5 | 1 bug High/Urgent | thấp tốt |
| D8 Chia sẻ kiến thức | 1 | 5 | 0 | cao tốt |
| D9 Quản lý chấm (nhập tay) | 4 | 10 | 0 | cao tốt |

**Mấu chốt:**
- Bọc dữ liệu trong `<data noupdate="1">`. Như vậy lệnh `-u` không ghi đè mục tiêu và trọng số đã chỉnh trên giao diện.
- Các dòng bộ KPI khai báo **ngay trong bản ghi template** bằng `(0, 0, {...})`. Nếu khai báo dòng thành bản ghi riêng, ràng buộc tổng 100 sẽ không chạy, và dữ liệu sai lọt vào mà không báo lỗi.

**Thứ tự trong manifest:** security → data → views → menus. File chứa action phải nạp trước file menu tham chiếu tới action đó.

**Kiểm tra:** `-u` không lỗi. KPI › Cấu hình hiện đủ 9 chỉ số, bộ Developer có tổng 100.

## Bước 9 — Thêm field KPI vào task

**File:** `models/project_task.py`

| Field | Kiểu | Dùng cho |
|---|---|---|
| `task_type` | Feature / Bug | Phân loại |
| `story_points` | Float | D2, D3 |
| `origin_task_id`, `bug_ids` | Many2one / One2many | Truy vết bug về task gốc, cho D3 và D4 |
| `is_production_bug` | Boolean | D4 |
| `bug_resolution` | valid / wont_fix / duplicate / invalid | Lọc bug tính KPI |
| `bug_root_cause` | code / requirement / environment | Lọc bug tính KPI |
| `review_reject_count` | Integer, readonly | D5 |
| `has_unit_test` | Boolean | D6 |
| `days_late` | Integer, compute stored | D1, bộ lọc "Trễ hạn" |

**Bug tính KPI** (dùng ở tuần 2): `bug_resolution` ∈ {valid, wont_fix} **và** `bug_root_cause` = code.

## Bước 10 — Ghi ngày hoàn thành và đếm lần bị trả về

**Làm gì:** override `write()` và `create()` của task.

```python
def write(self, vals):
    rejected = self.browse()
    if vals.get("state") == "02_changes_requested":
        rejected = self.filtered(lambda t: t.state != "02_changes_requested")   # lọc TRƯỚC super()
    res = super().write(vals)
    for task in rejected:
        task.review_reject_count += 1
    if {"state", "stage_id", "date_end"} & vals.keys():
        self._ensure_date_end()                                               # chạy SAU super()
    return res

def _ensure_date_end(self):
    missing = self.filtered(lambda t: t.state == "1_done" and not t.date_end)
    if missing:
        missing.write({"date_end": fields.Datetime.now()})
```

**Mấu chốt:**
- Lọc task bị trả về **trước** `super()`, vì sau khi ghi thì không còn biết trạng thái cũ.
- Ghi `date_end` **sau** `super()`, vì Odoo xoá `date_end` khi task đổi sang stage không fold.
- `state` được Odoo tính lại theo stage, và phép gán đó không đi qua `write()`. Override chỉ bắt được các lần người dùng tự đặt trạng thái, và với D5 cùng `date_end` thì như vậy là đủ.

## Bước 11 — Số ngày trễ và tác vụ hằng ngày

**File:** `models/project_task.py`, `data/ir_cron_data.xml`

**Làm gì:** `days_late` so `date_end`, hoặc hôm nay nếu task chưa xong, với `date_deadline`. Đơn vị là **ngày**, theo múi giờ trên lịch làm việc của công ty. Task đã huỷ hoặc không có deadline thì bằng 0.

**Mấu chốt:**
- Đổi sang múi giờ địa phương trước khi lấy ngày, để không lệch một ngày khi đổi từ UTC.
- Field stored nhưng phụ thuộc "hôm nay", nên cần cron hằng ngày `_cron_update_days_late` tính lại cho task chưa xong mà đã quá hạn.

## Bước 12 — Giao diện task

**File:** `views/project_task_views.xml`

- **Form:** thêm tab "Thông tin KPI" sau tab Description. Phần thông tin bug chỉ hiện khi `task_type == 'bug'`. Có bảng "Bug phát sinh từ task này".
- **List:** thêm cột loại task, story point (có tổng), số ngày trễ.
- **Search:** bộ lọc Bug, Lỗi production, Trễ hạn, Bị trả về, Bug chưa phân loại, Bug thiếu task gốc; nhóm theo loại task và nguyên nhân bug.

## Bước 13 — Dữ liệu demo và bù dữ liệu cũ

**File:** `data/kpi_demo.xml` (khoá `demo` của manifest), `__init__.py` (hook)

- Đặt `fold = True` cho `project.project_stage_2`.
- Gắn bộ Developer cho chức danh mẫu `hr.job_developer`.
- Tạo sẵn kỳ "Tháng hiện tại".

**Mấu chốt:**
- File này phải nằm trong khoá **`demo`**, không phải `data`. Database không có demo thì không có các bản ghi này, và đặt trong `data` sẽ làm cài module lỗi.
- Bản ghi demo của module khác có cờ `noupdate`, nên chỉ áp dụng khi **cài mới** (`-i`). Lệnh `-u` bỏ qua chúng.
- Môi trường thật không tự sửa stage được, vì doanh nghiệp tự đặt tên stage. Hướng dẫn sử dụng phải ghi rõ: stage Done phải bật "Folded in Kanban".

> **Cập nhật (bước 24):** `hr.job_developer`, kỳ "Tháng hiện tại" và phần gắn bộ KPI sau đó được
> tách khỏi file này, chuyển sang `data/kpi_org_data.xml` (chức danh, phòng ban riêng của module —
> không mượn `hr.job_developer` nữa) để kịch bản mẫu không cần `--with-demo`. `data/kpi_demo.xml`
> hiện chỉ còn giữ đúng một bản ghi: vá `fold = True` cho `project.project_stage_2`, phòng khi ai
> đó vẫn chọn cài kèm demo của module `project`.

`post_init_hook` bù `date_end` cho task đã Done từ trước khi cài module, lấy theo `date_last_stage_update`:

```python
def post_init_hook(env):
    tasks = env["project.task"].with_context(active_test=False).search([("state", "=", "1_done"), ("date_end", "=", False)])
    for task in tasks:
        task.date_end = task.date_last_stage_update or task.write_date
```

## Bước 14 — Kỳ đánh giá (`kpi.period`)

**File:** `models/kpi_period.py`, `views/kpi_period_views.xml`

Kỳ gồm: tên, loại kỳ (tháng / sprint / quý), từ ngày, đến ngày, trạng thái (mở / đóng). Ràng buộc `CHECK(date_from <= date_to)`. Có nút Đóng kỳ / Mở lại kỳ.

## Bước 15 — Phiếu đánh giá và công thức điểm

**File:** `models/kpi_evaluation.py`

**Chuỗi tính điểm (đều là compute stored):**

```
Dòng phiếu:  volume ≥ min_volume ?  → is_applicable
             actual, target, chiều  → score (trần 120)  → weighted_score
Phiếu:       Σ trọng số dòng được áp dụng                     → applicable_weight
             < 50                                              → insufficient_data
             Σ(score × weight) / applicable_weight             → kpi_score
             kpi_score + manager_adjustment                    → final_score → rating
             insufficient_data ? manual_rating : rating        → final_rating
```

```python
@staticmethod
def _score(actual, target, direction, cap):
    if direction == "lower":
        score = cap if actual <= 0 else target / actual * 100   # thấp tốt, thực tế 0 → trần
    else:
        score = cap if target <= 0 else actual / target * 100
    return max(min(score, cap), 0.0)
```

**Mấu chốt:**
- **Quy tắc "Không áp dụng":** chỉ số dưới khối lượng tối thiểu bị loại khỏi cả tử số lẫn mẫu số. Nhờ vậy người không làm task nào sẽ không được điểm trần 120 ở các chỉ số "thấp tốt".
- **Xếp loại theo khoảng nửa mở:** ≥ 100 Xuất sắc · [90, 100) Tốt · [75, 90) Đạt · < 75 Cần cải thiện. So sánh trên giá trị chưa làm tròn.
- Các tham số (trần, ngưỡng, biên độ) đọc qua `get_kpi_param()` từ `ir.config_parameter`, có giá trị mặc định trong `PARAM_DEFAULTS`.
- Float trong Odoo không phân biệt "chưa nhập" với 0, nên thêm `actual_entered` để biết chỉ số nhập tay đã được chấm chưa.
- `final_rating` là xếp loại dùng cho mọi báo cáo, để không sót các phiếu xếp loại thủ công.

## Bước 16 — Tạo phiếu, khoá phiếu

**Làm gì:**
- `create()`: chụp chức danh và phòng ban của nhân viên; lấy bộ KPI theo chức danh; chép từng dòng bộ KPI sang phiếu (mục tiêu, trọng số, khối lượng tối thiểu).
- Chặn tạo phiếu từ bộ KPI chưa có dòng nào, và chặn tạo phiếu trong kỳ đã đóng.
- Ràng buộc: mỗi nhân viên một phiếu mỗi kỳ (`UNIQUE(employee_id, period_id)`); điều chỉnh trong ±10; điều chỉnh khác 0 thì bắt buộc có lý do.
- **Khoá:** `write()` chặn các field trong `_LOCKED_FIELDS` khi phiếu không ở Nháp. Dòng phiếu chặn ở cả `create`/`write`/`unlink`. Chỉ xoá được phiếu Nháp.

**Mấu chốt:** chụp dữ liệu nghĩa là sửa bộ KPI về sau không ảnh hưởng tới phiếu đã tạo. Chặn ở server chứ không chỉ ẩn trên view, vì người dùng vẫn có thể ghi qua RPC.

## Bước 17 — Quy trình duyệt và wizard lý do

**File:** `models/kpi_evaluation.py`, `wizard/kpi_evaluation_reason_wizard.py`

```
Nháp ──Gửi duyệt──▶ Đã gửi ──Duyệt──▶ Đã duyệt (khoá)
  ▲                    │                   │
  └────Trả về nháp─────┘                   │
  └────────────Mở lại (có lý do)───────────┘
```

**Điều kiện Gửi duyệt:**
- D9 đã chấm.
- Phiếu thiếu dữ liệu thì đã có xếp loại thủ công kèm lý do.

Tuần 2 thêm điều kiện: phiếu đã Tính KPI.

Trả về nháp và Mở lại đi qua wizard (TransientModel) bắt buộc nhập lý do. Lý do được ghi vào lịch sử phiếu bằng `message_post`. Phiếu kế thừa `mail.thread` để có lịch sử này.

## Bước 18 — Giao diện phiếu và menu

**File:** `views/kpi_evaluation_views.xml`, `views/menus.xml`

- **Header:** các nút theo trạng thái, kèm thanh trạng thái.
- **Cảnh báo:** khung màu vàng khi phiếu không đủ dữ liệu.
- **Nhóm Điểm và Xếp loại:** ô lý do bắt buộc khi điều chỉnh khác 0.
- **Bảng dòng chỉ số** (`editable="bottom"`, không thêm hay xoá dòng):
  - Ô Thực tế chỉ sửa được với chỉ số nhập tay.
  - Dòng không áp dụng hiện mờ.
- **Lịch sử:** dùng thẻ `<chatter/>`.

Menu: **KPI › Đánh giá › Phiếu đánh giá** và **KPI › Cấu hình › Chỉ số KPI / Bộ KPI / Kỳ đánh giá**.

## Bước 19 — Unit test tuần 1

**File:** `tests/__init__.py`, `test_kpi_config.py` (9), `test_project_task.py` (6), `test_kpi_evaluation.py` (13 ở tuần 1)

```python
@tagged("post_install", "-at_install")
class TestKpiConfig(TransactionCase):
    def test_total_weight_must_be_100(self):
        with self.assertRaises(ValidationError):
            ...
```

**Mấu chốt:**
- **Không** import `tests` trong `__init__.py` của module.
- Kiểm ràng buộc SQL bằng `IntegrityError`, bọc trong `mute_logger('odoo.sql_db')`.
- Các trường hợp cần có:
  - Tổng trọng số "nửa chừng".
  - `date_end` trên stage không fold.
  - Ngưỡng xếp loại 99,99 và 90.
  - Khoá phiếu; Trả về và Mở lại có lý do.

**Kiểm tra:** chạy lệnh test (xem Phụ lục), log có dòng `0 failed, 0 error(s) of 28 tests`.

---

# TUẦN 2 — LÕI KPI

## Bước 20 — Khởi tạo Git

```bash
cd /d/Nam4/odoo19-kpi
git init -b main
printf '__pycache__/\n*.pyc\n.vscode/\n' > .gitignore
printf '* text=auto eol=lf\n' > .gitattributes
```

**Mấu chốt:** `.gitattributes` giữ ký tự xuống dòng LF. Code chạy trong container Linux, trong khi git trên Windows mặc định đổi sang CRLF.

## Bước 21 — Đếm lần được duyệt cho D5

**File:** `models/project_task.py`

Thêm `review_approve_count`, tự tăng khi `state` chuyển sang `03_approved`, cùng cách làm với `review_reject_count`.

**Mấu chốt:**
- D5 = task chưa từng bị trả về / task **đã qua review** × 100.
- "Đã qua review" là task có số lần duyệt hoặc số lần trả về > 0.
- Nếu chỉ có số lần bị trả về thì task được duyệt ngay lần đầu trông giống hệt task không qua review.

## Bước 22 — KPI Engine

**File:** `models/kpi_engine.py`, `data/kpi_calendar_data.xml`

**Làm gì:** AbstractModel `kpi.engine`. Hàm `compute_actual(metric, employee, date_from, date_to)` gọi `_metric_<mã>()`, mỗi hàm trả về `(actual, volume)`. Chỉ số nhập tay trả về `None`.

```python
method = getattr(self, f"_metric_{metric.code.lower()}", None)
return method(self._context_for(employee, date_from, date_to))
```

| Chỉ số | Thực tế | Khối lượng | Quy tắc |
|---|---|---|---|
| D1 | Task xong đúng hạn / task có deadline trong kỳ × 100 | Số task xét | Chưa xong mà quá hạn tính là trễ; **chưa tới hạn thì chưa xét**; bỏ task huỷ; đúng hạn nghĩa là `days_late == 0` |
| D2 | Tổng SP task xong trong kỳ | SP | — |
| D3 | Bug tính KPI / SP | SP | Bug quy về **người được giao và kỳ hoàn thành của task gốc** |
| D4 | Bug production / bug tính KPI × 100 | Số bug | Như D3 |
| D5 | Chưa từng bị trả về / đã qua review × 100 | Số task qua review | Task xong trong kỳ |
| D6 | Feature có unit test / Feature xong × 100 | Số Feature | — |
| D7 | Trung bình `working_hours_close` | Số bug | Bug High/Urgent, quy cho **người sửa bug**, theo kỳ đóng bug |
| D8 | Số sự kiện nhãn "Chia sẻ kiến thức" do nhân viên tổ chức | Số sự kiện | Nhãn cài sẵn trong `kpi_calendar_data.xml` |

**Mấu chốt:**
- Engine đọc dữ liệu bằng `sudo()`, nên kết quả không phụ thuộc quyền xem task của người bấm.
- Kỳ `[date_from, date_to]` tính theo ngày địa phương. `_period_bounds()` đổi nó sang khoảng UTC `[start, end)` để so với các field Datetime.
- Nhân viên chưa có tài khoản người dùng thì báo lỗi rõ ràng, không trả về số 0.

## Bước 23 — Nút Tính KPI trên phiếu

**File:** `models/kpi_evaluation.py`, `views/kpi_evaluation_views.xml`

```python
def action_compute_kpi(self):
    engine = self.env["kpi.engine"]
    for ev in self:
        if ev.state != "draft":
            raise UserError(...)
        for line in ev.line_ids.filtered(lambda l: l.compute_mode == "auto"):
            actual, volume = engine.compute_actual(line.metric_id, ev.employee_id,
                                                   ev.period_id.date_from, ev.period_id.date_to)
            line.write({"actual": actual, "volume": volume})
        ev.computed_date = fields.Datetime.now()
    return True
```

**Mấu chốt:**
- Thêm `computed_date`. Gửi duyệt bắt buộc đã có giá trị này.
- Nút "Tính KPI" và "Tính lại KPI" chỉ hiện khi phiếu ở Nháp.
- Các hàm `action_*` **trả về `True`**. XML-RPC không gửi được `None`, và lỗi này đã gặp khi kiểm tra ở bước 31.

## Bước 24 — Dữ liệu mẫu 3 nhân viên và bảng tính tay

**File:** `models/kpi_demo.py`, `data/kpi_org_data.xml` (phòng ban, chức danh, bộ KPI Tester — luôn nạp), `data/kpi_demo_scenario_action.xml` (menu bấm để nạp kịch bản)

**Làm gì:** tạo kịch bản ở **tháng trước** so với ngày cài, mốc là thứ Hai đầu tiên của tháng (M).
- 3 tài khoản `an`, `binh`, `chi` (mật khẩu trùng tên đăng nhập). Quản lý trực tiếp tự tạo riêng: `quocviet` / `quocviet` (Phạm Quốc Việt).
- Phòng ban, 2 chức danh ("Lập trình viên", "Trưởng nhóm phát triển") riêng của module, không mượn `hr.dep_rd`/`hr.job_developer` của Odoo.
- Dự án mẫu với **3 stage tự tạo** ("Mới", "Đang làm", "Hoàn thành" có `fold=True`), không mượn `project.project_stage_0/1/2` (chỉ có khi cài demo của module `project`).
- Task, bug và sự kiện có ngày giờ cụ thể.

**Mấu chốt:**
- **Không tự động chạy khi cài module.** Đăng ký qua `ir.actions.server` + menu **KPI › Cấu hình › Nạp dữ liệu mẫu** (`kpi_demo_scenario_action.xml`, nạp ở khoá `data` — luôn có sẵn, không cần `--with-demo`). Bấm khi cần dữ liệu để tự học hoặc demo; test tự gọi hàm trực tiếp trong `setUpClass`.
- Nhờ không mượn dữ liệu demo của `project`/`hr`, kịch bản này **không kéo theo** các nhân viên demo gốc của Odoo (Mitchell Admin, Anita Oliver...) — vốn chỉ xuất hiện khi cài `--with-demo`, một cờ toàn cục không lọc được theo từng module.
- Viết bằng Python thay vì XML, vì 2 lý do:
  - Khi tạo task trong dự án có stage, Odoo **ghi đè `date_end`**. Vì vậy phải ghi `date_end` sau khi tạo.
  - `create_date` (mốc bắt đầu tính D7) **không ghi được qua ORM**, nên phải `UPDATE` bằng SQL rồi tính lại `working_hours_close`.
- Hàm chạy lại được nhiều lần (bấm menu lại, hoặc test gọi lại). Vì vậy hàm thoát sớm nếu đã có xmlid `demo_period_previous_month`, tránh tạo trùng.
- Các bản ghi được gán xmlid bằng `_update_xmlids` để test tham chiếu bằng `env.ref(...)`.

**Bảng tính tay:** lịch làm việc Europe/Brussels, ca 8–12 và 13–17.

| Chỉ số | An | Bình | Chi |
|---|---|---|---|
| D1 (mục tiêu 90%) | 4/4 = 100% → 111,11 | 3/5 = 60% → 66,67 | 1 task < 3 → không áp dụng |
| D2 (20 SP) | 24 → 120 | 15 → 75 | 0 → 0 |
| D3 (0,3) | 2/24 = 0,0833 → 120 | 4/15 = 0,2667 → 112,5 | không áp dụng |
| D4 (5%) | 0/2 = 0% → 120 | 1/4 = 25% → 20 | không áp dụng |
| D5 (80%) | 3/4 = 75% → 93,75 | 2/4 = 50% → 62,5 | không áp dụng |
| D6 (70%) | 3/4 = 75% → 107,14 | 2/4 = 50% → 71,43 | không áp dụng |
| D7 (24h) | 5h → 120 | (10h + 40h)/2 = 25h → 96 | không áp dụng |
| D8 (1) | 1 → 100 | 1 → 100 | 0 → 0 |
| D9 (4, quản lý chấm) | 5 → 120 | 4 → 100 | 4 → 100 |
| **Điểm KPI** | **113,31** Xuất sắc | **73,90**; điều chỉnh +2 → **75,90** Đạt | Trọng số áp dụng 25% → **40**, thiếu dữ liệu, xếp loại thủ công |

Giờ làm việc của D7 tính tay:
- B1 (An) tạo lúc 9h, đóng lúc 15h cùng ngày: 3h + 2h = **5h**.
- B4 (Bình) tạo 9h thứ Hai, đóng 11h thứ Ba: 7h + 3h = **10h**.
- B5 (Bình) tạo 8h thứ Hai, đóng 17h thứ Sáu: 5 × 8h = **40h**.

## Bước 25 — Sửa lỗi làm tròn điểm

**Phát hiện khi đối chiếu bảng tính tay:** D3 của An ra 0,08 thay vì 0,0833.

**Nguyên nhân:** `actual`, `score`, `kpi_score`, `final_score` khai báo `digits=(16, 2)`, nên Odoo **làm tròn khi lưu**. Hệ quả: 99,996 điểm bị lưu thành 100,00 và được xếp "Xuất sắc".

**Sửa:**
- Bỏ `digits` ở model để lưu đủ độ chính xác.
- Chỉ làm tròn khi hiển thị bằng thuộc tính ở view: `<field name="score" digits="[16, 2]"/>`, riêng cột Thực tế dùng `[16, 4]`.
- Thêm test `test_rating_uses_unrounded_score`.

## Bước 26 — Nhóm quyền KPI

**File:** `security/kpi_security.xml` (nạp **trước** `ir.model.access.csv`)

```xml
<record id="res_groups_privilege_kpi" model="res.groups.privilege">      <!-- Odoo 19 -->
    <field name="name">KPI</field>
    <field name="category_id" ref="base.module_category_services"/>
</record>
<record id="group_kpi_user" model="res.groups">
    <field name="privilege_id" ref="res_groups_privilege_kpi"/> ...
<record id="group_kpi_manager" ...>  implied: group_kpi_user + project.group_project_manager
<record id="group_kpi_admin" ...>    implied: group_kpi_manager; user_ids: admin
<record id="base.group_user">        implied thêm group_kpi_user (mọi nhân viên nội bộ)
```

**Mấu chốt:**
- Odoo 19 gắn group vào **privilege** (`privilege_id`), không gắn thẳng vào category như tutorial cũ.
- Field nhóm quyền trên người dùng là `group_ids`, không còn là `groups_id`.
- `group_kpi_user` **không** được kéo theo `base.group_user`. Nếu không sẽ thành vòng lặp, vì `base.group_user` đã kéo theo `group_kpi_user`.

## Bước 27 — Quyền truy cập model

**File:** `security/ir.model.access.csv`

| Model | KPI User | KPI Manager | KPI Admin |
|---|---|---|---|
| Chỉ số, bộ KPI, dòng bộ KPI, kỳ | đọc | đọc (thừa hưởng) | toàn quyền |
| Phiếu, dòng phiếu | đọc | toàn quyền (giới hạn bởi record rule) | toàn quyền |
| Wizard lý do | — | — | toàn quyền |

## Bước 28 — Record rule

| Rule | Nhóm | Domain | Thao tác |
|---|---|---|---|
| Phiếu của mình | User | `employee_id.user_id = user.id` | **chỉ đọc** |
| Nhân viên trực tiếp | Manager | `employee_id.parent_id.user_id = user.id` | tất cả |
| Tất cả | Admin | `(1, '=', 1)` | tất cả |

Dòng phiếu có 3 rule tương tự, đi qua `evaluation_id`.

**Mấu chốt:** Odoo cộng (OR) các rule **theo từng thao tác**. Rule "phiếu của mình" chỉ có `perm_read`, nên quản lý xem được phiếu của mình nhưng **không tự sửa điểm cho mình**.

## Bước 29 — Kiểm tra quyền ở server và giao diện

- **Duyệt, Trả về, Mở lại:** hàm `_check_kpi_admin()` báo `AccessError` nếu người bấm không phải KPI Admin. Nút trên view cũng có `groups=`, nhưng **vẫn phải kiểm ở server** vì vẫn có thể gọi qua RPC.
- **`has_unit_test`:** chỉ KPI Manager được ghi, kiểm ở cả `create()` và `write()` của task. Trên form, ô này khoá nhờ field compute `kpi_can_review`.
- **Tạo phiếu:** đọc nhân viên bằng `sudo()`, vì quản lý không thuộc nhóm HR vẫn cần đọc chức danh nằm ở `hr.version`.
- **Menu:** gốc KPI dành cho `group_kpi_user`; Cấu hình dành cho `group_kpi_manager`.

## Bước 30 — Unit test tuần 2

| File | Số test | Nội dung |
|---|---|---|
| `test_kpi_engine.py` | 9 | Từng quy tắc D1–D8; chỉ số nhập tay bị bỏ qua; nhân viên không có tài khoản |
| `test_kpi_demo_scenario.py` | 4 | So `(actual, volume)` của 3 người × 8 chỉ số với bảng tính tay; điểm, xếp loại; điều chỉnh của Bình; xếp loại thủ công của Chi. Bỏ qua nếu database không có demo |
| `test_kpi_security.py` | 6 | Nhóm mặc định; ai thấy phiếu nào; nhân viên chỉ đọc; quản lý không sửa phiếu của mình hay của nhóm khác; chỉ Admin duyệt; `has_unit_test` |
| `test_kpi_evaluation.py` | +2 | Bắt buộc Tính KPI trước khi gửi; xếp loại dùng điểm chưa làm tròn |

Tạo người dùng test bằng `new_test_user(env, login=..., groups="base.group_user,project_kpi_management.group_kpi_manager")`, rồi thử quyền bằng `record.with_user(user)`.

**Kiểm tra:** `0 failed, 0 error(s) of 49 tests`, chạy trên **database tạo mới** (xem Phụ lục).

## Bước 31 — Kiểm tra bằng đăng nhập 3 vai trò

Ngoài unit test, đăng nhập thật qua XML-RPC:

```python
import xmlrpc.client
URL, DB = "http://localhost:8019", "kpi_dev"
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
obj = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
uid = common.authenticate(DB, "an", "an", {})
print(obj.execute_kw(DB, uid, "an", "kpi.evaluation", "search_count", [[]]))
```

| Tài khoản | Kết quả mong đợi |
|---|---|
| `an` | Thấy 1 phiếu (của mình); sửa phiếu hoặc Tính KPI bị từ chối |
| `quocviet` (quản lý) | Thấy 3 phiếu; Duyệt bị từ chối; sửa chỉ số KPI bị từ chối |
| `admin` | Thấy tất cả; duyệt được |

Trên giao diện:
1. Đăng nhập `quocviet`, tạo phiếu cho An, Bình, Chi ở kỳ "Tháng … (dữ liệu mẫu)".
2. Nhập D9 lần lượt 5, 4, 4, bấm **Tính KPI**, rồi so với bảng tính tay ở bước 24.
3. Đăng nhập `admin` để duyệt.

## Bước 32 — Commit và đẩy lên GitHub

```bash
git add -A
git commit -m "Tuần 2: Phase 4–5"
git remote add origin https://github.com/haudo1207/odoo_kpi_management.git   # lần đầu
git push -u origin main
```

---

# Phụ lục

## Lệnh thường dùng

| Việc | Lệnh |
|---|---|
| Khởi động | `docker compose up -d` (Docker Desktop phải đang chạy) |
| Chỉ sửa logic Python | `docker restart odoo19-web` |
| Thêm/sửa field, view, data, security | `docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management --stop-after-init --http-port 8070` rồi `docker restart odoo19-web` |
| Chạy unit test | `docker exec odoo19-web odoo -d kpi_dev -u project_kpi_management --test-tags /project_kpi_management --stop-after-init --http-port 8070` |
| Xem log | `docker logs -f odoo19-web` |
| Mở shell Odoo | `docker exec -it odoo19-web odoo shell -d kpi_dev --no-http` |

**Tạo lại database từ đầu**, dùng khi cần nạp lại dữ liệu có `noupdate="1"`. Không cần `--with-demo`
(xem bước 24) — database sạch, không có nhân viên demo gốc của Odoo:

```bash
docker stop odoo19-web
docker exec odoo19-db dropdb -U odoo kpi_dev
docker start odoo19-web
docker exec odoo19-web odoo -d kpi_dev -i project_kpi_management --stop-after-init --max-cron-threads=0 --http-port 8070
docker restart odoo19-web
```

Muốn có kịch bản mẫu (An, Bình, Chi) để thử trên giao diện: đăng nhập `admin`, vào **KPI › Cấu
hình › Nạp dữ liệu mẫu**, bấm một lần.

## Cấu trúc thư mục cuối tuần 2

```
odoo19-kpi/
├── docker-compose.yml, config/odoo.conf, .gitignore, .gitattributes
└── addons/project_kpi_management/
    ├── __init__.py              post_init_hook bù date_end
    ├── __manifest__.py
    ├── models/
    │   ├── kpi_metric.py        chỉ số, quy tắc ẩn
    │   ├── kpi_template.py      bộ KPI, dòng, tổng trọng số = 100
    │   ├── hr_job.py            gắn bộ KPI vào chức danh
    │   ├── project_task.py      field KPI, date_end, đếm duyệt/trả về, số ngày trễ
    │   ├── kpi_period.py        kỳ đánh giá
    │   ├── kpi_evaluation.py    phiếu, dòng phiếu, công thức điểm, quy trình
    │   ├── kpi_engine.py        tính D1–D8
    │   └── kpi_demo.py          kịch bản dữ liệu mẫu
    ├── wizard/kpi_evaluation_reason_wizard.py
    ├── security/kpi_security.xml, ir.model.access.csv
    ├── data/  kpi_metric_data, kpi_calendar_data, kpi_template_data, ir_cron_data, kpi_demo (.xml)
    ├── views/ kpi_metric, kpi_template, kpi_period, kpi_evaluation, hr_job, project_task, menus (_views.xml)
    └── tests/ 6 file, 49 test
```

## Lỗi thường gặp

| Hiện tượng | Nguyên nhân, cách xử lý |
|---|---|
| VS Code báo "odoo not found", "Unknown XML ID", "Unknown model" | Source Odoo nằm trong container, VS Code không thấy. Bỏ qua, lấy kết quả cài module làm chuẩn |
| `could not serialize access due to concurrent update` ở `ir_cron` khi `-u` | Server chính đang chạy cron cùng lúc. Chạy lại lệnh, hoặc thêm `--max-cron-threads=0` |
| Git Bash: `Invalid tag C:/Program Files/Git/project_kpi_management` | Git Bash tự đổi đường dẫn bắt đầu bằng `/`. Thêm `MSYS_NO_PATHCONV=1` ở đầu lệnh, hoặc dùng PowerShell |
| `failed to connect to the docker API` | Docker Desktop chưa chạy |
| D1, D7 ra số lạ, task Done không có ngày hoàn thành | Stage Done chưa bật "Folded in Kanban" (bước 4, 13) |
| Sửa XML data mà `-u` không áp dụng | Dữ liệu có `noupdate="1"`: sửa trên giao diện, hoặc tạo lại database |
| `cannot marshal None` khi gọi qua XML-RPC | Hàm được gọi trả về `None`. Các hàm `action_*` phải `return True` |
