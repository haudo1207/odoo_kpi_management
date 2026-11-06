# Prompt — Rà soát logic hệ thống `project_kpi_management` khớp thiết kế

> Dùng file này làm prompt đưa cho một phiên Claude (hoặc AI khác) mới, kèm quyền truy cập repo
> `odoo19-kpi`, để rà soát xem code hiện tại có còn khớp đúng thiết kế đã tài liệu hoá hay không.
> Không cần kèm lịch sử hội thoại cũ — file này tự đủ ngữ cảnh. Việt hoá, có thể dịch nếu cần.

## Bối cảnh (dán nguyên vào đầu prompt)

Đây là module Odoo 19 Community `project_kpi_management` (+ 3 module cầu nối
`project_kpi_timesheet`, `project_kpi_skills`, `project_kpi_survey`) — đồ án tốt nghiệp quản lý
KPI nhân sự cho đội phát triển phần mềm. Tài liệu thiết kế gốc là `PHASE_11_TAI_LIEU_DU_AN.md`
(bản đầy đủ) và/hoặc `Nhom7_BaoCao.md` (bản nộp, có thể đã rút gọn) — đọc 1 trong 2 trước khi rà,
ưu tiên bản còn tồn tại và mới nhất. Yêu cầu: đọc trực tiếp code thật trong `addons/`, không suy
diễn từ tên hàm/tên biến, không kết luận "đúng" chỉ vì đọc comment hay tài liệu nói vậy.

## Cách làm việc bắt buộc

1. Đọc code thật bằng `cat -n`/`grep -n`, không chỉ đọc tài liệu rồi tin theo.
2. Với mỗi quy tắc nghiệp vụ, tìm **3 lớp** phải khớp nhau cho một tính năng chạy được thật trên UI,
   không chỉ 1: (a) nút trên view có `groups=` đúng ai được thấy, (b) `ir.model.access.csv` có đúng
   nhóm được tạo/sửa bản ghi của model đó (đặc biệt **TransientModel/wizard** — dễ bị quên nhất),
   (c) logic nghiệp vụ thật (`_check_...`, `@api.constrains`) có đúng ai được phép. Thiếu 1 trong 3
   lớp này là bug thật dù 2 lớp kia đúng — đây là loại lỗi đã từng xảy ra thật trong repo này
   (xem `git log` commit sửa ACL cho `kpi.evaluation.reason.wizard`).
3. Test cũ KHÔNG đủ tin cậy nếu nó chỉ gọi hàm trả về `action_window` dict (ví dụ `action_reopen()`)
   mà không thực sự `create()` + gọi `action_confirm()` trên wizard — việc đó bỏ sót đúng lớp (b) ở
   trên. Khi viết/kiểm test cho một thao tác đi qua wizard, luôn tự `create()` wizard bằng
   `with_user(<user cần test>)` rồi gọi `action_confirm()` thật.
4. Môi trường chạy prompt này (ví dụ `device_bash`) thường **không có Docker** → không chạy được
   `scripts/run_all_tests.sh`/`prepare_defense.sh` thật. Luôn nói rõ giới hạn này, không báo "100%
   chắc chắn" nếu chỉ `py_compile` + đọc code tĩnh. Đề nghị người dùng tự chạy 2 script đó để xác
   nhận bằng Odoo thật.

## Checklist rà soát (theo thứ tự ưu tiên)

### A. Đồng bộ môi trường
- [ ] `git status --short` — có gì chưa commit ngoài dự kiến không.
- [ ] `git log --oneline origin/main..HEAD` và chiều ngược lại — local có đồng bộ remote không.
- [ ] Phiên bản `__manifest__.py` của cả 4 module có giống nhau không (`grep -n "\"version\""`).

### B. Quy trình duyệt phiếu KPI (khu vực rủi ro cao nhất, đã có lịch sử lỗi thật)
- [ ] `kpi_evaluation.py`: `_check_can_approve()` — đúng chủ thể nào được duyệt/trả về/mở lại.
- [ ] `_check_no_role_conflict()` — đúng trường hợp nào bị chặn (hiện tại: chỉ chặn tự duyệt chính
      mình, không chặn quản lý trực tiếp duyệt đội mình).
- [ ] `action_approve()`, `_open_reason_wizard()` (dùng chung cho Trả về/Mở lại) — có gọi đủ cả 2
      hàm check ở trên không.
- [ ] `views/kpi_evaluation_views.xml` — `groups=` trên 3 nút Duyệt/Trả về/Mở lại có khớp với ai
      được phép theo logic ở trên không (đang là `group_kpi_manager`, admin kế thừa nên vẫn thấy).
- [ ] `security/ir.model.access.csv` — **model `kpi.evaluation.reason.wizard`** có đủ dòng cho mọi
      nhóm được phép dùng (hiện tại cần cả `group_kpi_admin` lẫn `group_kpi_manager`) — đây CHÍNH
      LÀ chỗ đã từng thiếu, kiểm kỹ nhất.
- [ ] `security/kpi_security.xml` — comment 2 nhóm `group_kpi_manager`/`group_kpi_admin` có mô tả
      đúng hành vi hiện tại không (dễ bị tài liệu nói một đằng, code một nẻo sau khi sửa).
- [ ] `_sync_workflow_activities()` — điều kiện bỏ qua nhắc việc do xung đột vai trò (đoạn
      `elif ev.state == "submitted"`) có khớp đúng `_check_no_role_conflict()` hiện tại không.
- [ ] Test: `tests/test_kpi_security.py`, `tests/test_kpi_workflow.py`,
      `tests/test_kpi_demo_scenario.py` — tìm các test liên quan duyệt/trả về/mở lại, xác nhận có
      test nào **thật sự tạo + confirm wizard** (không chỉ gọi `action_reopen()`/`action_return_draft()`
      rồi dừng) cho cả trường hợp Manager lẫn Admin.

### C. Mọi wizard khác (TransientModel) — áp cùng kiểu kiểm tra ở mục B
Với mỗi wizard trong `wizard/*.py`: đọc hàm `action_confirm()` xem logic cho phép ai, rồi đối chiếu
dòng tương ứng trong `ir.model.access.csv`. Danh sách hiện có (cập nhật nếu repo có thêm):
`kpi_evaluation_reason_wizard`, `kpi_evaluation_generate_wizard`, `kpi_self_assessment_wizard(.line)`,
`kpi_acknowledge_wizard`, `kpi_metric_test_wizard`, `kpi_manager_issue`.

### D. Engine tính điểm (`kpi_engine.py` + các module cầu nối)
- [ ] Đối chiếu từng hàm `_metric_<mã>()` với bảng công thức trong Chương 3.4/9.2 của tài liệu thiết
      kế: tử số, mẫu số, quy tắc quy kỳ (vd D3/D4 theo task gốc, D5/D7 theo chính bug/task).
- [ ] Chỉ số `compute_mode = domain` (không cần code) — kiểm `data/kpi_org_data.xml` có đúng model/
      field/domain như tài liệu mô tả không, và validate qua `_check_domain_metric_config`.
- [ ] Không có chỉ số tự động (`compute_mode = auto`) nào thiếu hàm `_metric_<mã>()` tương ứng.

### E. Phân quyền field-level
- [ ] `has_unit_test`, `bug_reporter_id` trên `project.task` — chỉ `group_kpi_manager` ghi được,
      kiểm cả `create()` lẫn `write()`.
- [ ] `employee_comment`, `self_score`, 3 field `ack_*` trên `kpi.evaluation(.line)` — chỉ ghi được
      qua wizard bằng `sudo()`, chặn cả `create()` lẫn `write()` trực tiếp.

### F. REST API (`controllers/api.py`)
- [ ] Không có endpoint nào cho phép duyệt/trả về/mở lại phiếu vòng qua được 2 hàm check ở mục B.
- [ ] Endpoint ghi chỉ số (`POST .../metrics/<code>`) từ chối đúng chỉ số tự động/`domain`.

### G. Dữ liệu mẫu & tài liệu
- [ ] `models/kpi_demo.py` — nhóm quyền gán cho các user mẫu (quocviet, phuc...) có khớp đúng thiết
      kế hiện tại không (không nên gán thừa quyền Admin nếu thiết kế không yêu cầu).
- [ ] `grep -rn "<tên hàm/field cũ đã đổi>" --include="*.md" .` — tìm tài liệu còn mô tả hành vi cũ.
      Phân biệt: nhật ký lịch sử (nói rõ "trước đây", hoặc file ghi chú tuần/giai đoạn cũ) thì giữ
      nguyên là đúng; tài liệu mô tả **hành vi hiện tại** mà vẫn ghi theo kiểu cũ thì phải sửa.

### H. Sạch cú pháp (chạy được luôn, không cần Docker)
```bash
python3 -m py_compile addons/project_kpi_management/**/*.py addons/project_kpi_timesheet/**/*.py \
  addons/project_kpi_skills/**/*.py addons/project_kpi_survey/**/*.py
python3 -c "import xml.dom.minidom as m, glob
for f in glob.glob('addons/**/*.xml', recursive=True):
    try: m.parse(f)
    except Exception as e: print('BAD XML:', f, e)"
grep -c "def test_" addons/*/tests/test_*.py   # đối chiếu tổng số test với con số ghi trong tài liệu
```

## Khi tìm ra lỗi thật

1. Nêu rõ: lớp nào trong 3 lớp (view/ACL/logic) bị lệch, vì sao chưa bị phát hiện trước đó (thường
   là vì test chỉ kiểm 1 lớp).
2. Sửa trực tiếp, kèm test mới thật sự tái hiện đường đi lỗi (không chỉ gọi hàm trả về dict).
3. `py_compile` lại file vừa sửa trước khi báo xong.
4. Không tự ý commit/push nếu người dùng chưa yêu cầu rõ.

## Báo cáo kết quả

Dùng bảng: khu vực | kết quả (khớp thiết kế / có lỗi, mô tả) — không liệt kê dài dòng những phần đã
khớp, chỉ nêu rõ phần có vấn đề và đã sửa gì. Luôn nói rõ giới hạn (không chạy được Docker/test thật
từ môi trường rà soát) ở cuối báo cáo, không khẳng định "100% hoàn thiện" nếu chưa tự chạy
`run_all_tests.sh` + `prepare_defense.sh` thật.
