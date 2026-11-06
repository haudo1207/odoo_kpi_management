# Flow kiểm chứng logic — rà code từng tính năng

Khác với hai file đã có:

- `KICH_BAN_DEMO.md` — trình diễn trên sân khấu, có chọn lọc theo thời gian.
- `FLOW_TU_KIEM_CHUNG_TRUOC_BAO_VE.md` — kiểm **hành vi qua giao diện** (bấm nút, xem kết quả).

File này là để **tự đọc code** của từng tính năng, đối chiếu với công thức/thiết kế đã ghi trong
`Nhom7_BaoCao.md` (Chương 3), rồi **tính tay một ví dụ cụ thể** so với số hệ thống trả ra — vì test
pass không đồng nghĩa logic đúng (code sai mà test viết theo đúng cái sai đó vẫn pass). Đi theo
đúng 48 mục của `HUONG_DAN_SU_DUNG.md`; mục nào không có logic/thuật toán (chỉ là field thuần tuý)
được ghi rõ **Không áp dụng** thay vì bỏ qua không nhắc tới.

Cách dùng mỗi mục: mở đúng **Vị trí code**, đọc hàm, so với **Logic kỳ vọng**, rồi làm đúng
**Cách tự kiểm** (thường là tính tay 1 ví dụ bằng dữ liệu trong `seeded`, so với số hệ thống ra).
Tick khi đã tự đọc code và tính tay khớp — không tick nếu chỉ đọc mô tả trong báo cáo rồi tin theo.

---

## Phần A — Dữ liệu Odoo gốc được tái sử dụng (10 mục)

Không có logic riêng của module KPI — đây là field/hành vi chuẩn của Odoo. **Không áp dụng** cho cả
10 mục (1–10): không có hàm nào trong `project_kpi_management` để rà, trừ cách các hàm ở Phần C/D
*đọc* dữ liệu này (đã kiểm ở các mục tương ứng bên dưới, ví dụ mục 25, 28, 29).

---

## Phần B — Field/tính năng tuỳ biến thêm vào Odoo gốc (14 mục)

- [ ] **11. Phân loại task (`task_type`).** Không áp dụng — field Selection thuần, không có hàm
  compute. Chỉ cần xác nhận các hàm ở `kpi_engine.py` lọc đúng giá trị `feature`/`bug` (xem mục 25).
- [ ] **12. Story point.** Không áp dụng — field Float thuần.
- [ ] **13. Truy vết bug (`origin_task_id`, `is_production_bug`).** **Vị trí code:**
  `models/project_task.py`, ràng buộc `domain="[('id','!=',id)]"`. **Logic kỳ vọng:** 1 task không
  được chọn chính nó làm task gốc. **Cách tự kiểm:** thử set `origin_task_id` = chính task đó qua
  `odoo shell` (bỏ qua domain UI) → phải bị chặn bởi constraint Python, không chỉ domain giao diện.
- [ ] **14. Kết quả xử lý bug (`bug_resolution`).** **Vị trí code:** `models/kpi_engine.py`, hàm
  `_counted_bugs()`. **Logic kỳ vọng:** chỉ `bug_resolution ∈ {valid, wont_fix}` **và**
  `bug_root_cause = code` được tính là "bug tính KPI" (D3, D4). **Cách tự kiểm:** đọc đúng điều kiện
  lọc trong `_counted_bugs()`, đối chiếu với mô tả ở `Nhom7_BaoCao.md` mục 3.4 "Quy tắc Bug tính
  KPI" — tính tay số bug hợp lệ của 1 nhân viên trong `seeded`, so với D3/D4 hệ thống ra.
- [ ] **15. Nguyên nhân bug (`bug_root_cause`).** **Vị trí code:** `_counted_bugs()` (loại
  `requirement`/`environment` khỏi D3/D4) và `models/kpi_engine.py` hàm `_metric_b2()` (module đã
  merge vào BA, lấy đúng bug `bug_root_cause = requirement`). **Cách tự kiểm:** với phiếu `lan` (BA)
  trong `seeded`, đọc `_metric_b2()`: bug → `origin_task_id` → `requirement_id` → đúng BA phụ trách;
  tính tay B2 = 2/3 so với điểm hệ thống.
- [ ] **16. Đếm lần bị trả về (`review_reject_count`).** **Vị trí code:** `models/project_task.py`,
  override `write()`. **Logic kỳ vọng:** tăng 1 mỗi khi `state` chuyển **vào** `02_changes_requested`
  (không tăng khi ghi lại cùng trạng thái cũ). **Cách tự kiểm:** đọc điều kiện so `vals.get('state')`
  với `state` cũ trong `write()` trước khi tăng — xác nhận không tăng nhầm khi `write()` được gọi mà
  không đổi `state` (ví dụ sửa trường khác).
- [ ] **17. Đánh dấu unit test (`has_unit_test`).** **Vị trí code:** `models/project_task.py`,
  `create()`/`write()` kiểm `self.env.user.has_group(...)` cho field này, và `kpi_can_review`
  (compute) khoá UI. **Cách tự kiểm:** gọi thẳng `write({'has_unit_test': True})` qua `odoo shell`
  bằng user không phải Manager → phải bị `AccessError`/chặn ở code, không chỉ ẩn trên form.
- [ ] **18. Ngày hoàn thành (ghi đè `date_end`).** **Vị trí code:** `models/project_task.py`,
  override `write()`, chạy **sau** `super().write()`. **Logic kỳ vọng:** khi `state` chuyển thành
  `1_done`, tự ghi `date_end = fields.Datetime.now()` bất kể stage hiện tại có `fold` hay không (bù
  lại hành vi gốc của Odoo là xoá field này khi rời stage fold). **Cách tự kiểm:** đọc đúng thứ tự
  gọi `super().write()` trước, ghi đè `date_end` sau — nếu đảo ngược thứ tự thì Odoo gốc sẽ xoá giá
  trị ngay sau khi module vừa ghi.
- [ ] **19. Số ngày trễ (`days_late`).** **Vị trí code:** `models/project_task.py`, field compute +
  cron `_cron_update_days_late()`. **Logic kỳ vọng:** so `date_end` (nếu đã Done) hoặc hôm nay (nếu
  chưa) với `date_deadline`; task Huỷ hoặc chưa có deadline → 0. **Cách tự kiểm:** tính tay cho 1 task
  trễ hạn chưa xong trong `seeded`, so với `days_late` hiển thị; đọc thêm điều kiện cron chỉ `write()`
  khi giá trị thật sự đổi (tránh ghi `write_date` thừa mỗi ngày).
- [ ] **20. Bộ lọc giao diện task.** Không áp dụng — chỉ là `<filter domain="...">` trong view XML,
  không có logic Python.
- [ ] **21. Gắn KPI theo chức danh (`kpi_template_id`).** Không áp dụng — field Many2one thuần,
  logic đọc field này nằm ở mục 28 (`kpi.evaluation.create()`).
- [ ] **22. Phân quyền nền (KPI Manager kế thừa Project Manager).** **Vị trí code:**
  `security/kpi_security.xml`, `implied_ids` của group KPI Manager. **Cách tự kiểm:** đọc đúng dòng
  `implied_ids` trỏ về `project.group_project_manager` — không phải gán quyền Project Manager bằng
  tay trong data nhân viên (nếu làm vậy sẽ không tự động áp dụng cho nhân viên mới gán nhóm).
- [ ] **23. Smart button "Phiếu KPI".** **Vị trí code:** `models/hr_employee.py`, field compute
  `kpi_evaluation_count` + action mở danh sách lọc theo `employee_id`. **Cách tự kiểm:** đọc đúng
  domain của action trỏ về `employee_id = self.id`, không phải lọc nhầm theo `user_id`.
- [ ] **24. Cấu hình (Settings).** **Vị trí code:** `models/res_config_settings.py`, `get_kpi_param()`
  / `set_values()`, lưu ở `ir.config_parameter`. **Logic kỳ vọng:** ngưỡng xếp loại phải theo đúng
  thứ tự tăng dần (Cần cải thiện < Đạt < Tốt < Xuất sắc), điểm trần > 100, biên độ điều chỉnh ≥ 0.
  **Cách tự kiểm:** đọc `@api.constrains`/validation trong `set_values()` hoặc model Settings — thử
  nhập ngược thứ tự ngưỡng qua `odoo shell`, xác nhận bị chặn ở code chứ không chỉ ở validation phía
  JS của form.

---

## Phần C — Màn hình/tính năng xây mới (13 mục)

- [ ] **25. Chỉ số KPI — chỉ số cấu hình domain.** **Vị trí code:** `models/kpi_metric.py`,
  `_check_domain_metric_config()`, `kpi.engine._compute_domain_metric()`,
  `substitute_domain_placeholders()`, `_domain_field_bounds()`. **Logic kỳ vọng:** đọc domain bằng
  `ast.literal_eval` (KHÔNG phải `safe_eval` hay `eval`), chỉ thay 3 chuỗi giữ chỗ
  (`$CURRENT_USER_ID`, `$PERIOD_START`, `$PERIOD_END`) **sau khi** đã parse xong; model nguồn giới
  hạn trong danh sách cho phép (`project.task`, `project.milestone`, `calendar.event`); field Date
  và Datetime lọc theo đúng kiểu mốc (không so lẫn, lệch múi giờ ở ngày biên). **Cách tự kiểm:** mở
  đúng dòng gọi `ast.literal_eval` — xác nhận KHÔNG có `safe_eval`/`eval` nào trong đường đi này (đây
  là điểm bảo mật quan trọng nhất của tính năng); dựng 1 chỉ số domain tương đương D4, so kết quả với
  `_metric_d4()` trên cùng dữ liệu (đúng như `test_domain_metric_equivalent_to_d4`, nhưng tự đọc code
  thay vì chỉ tin test).
- [ ] **26. Bộ KPI — ràng buộc tổng trọng số = 100.** **Vị trí code:** `models/kpi_template.py`,
  `@api.constrains('line_ids')`. **Logic kỳ vọng:** ràng buộc đặt trên **template** (không đặt trên
  từng dòng) — lý do: sửa/thêm dòng là nhiều lệnh ghi riêng, ràng buộc trên dòng sẽ bắt sai trạng
  thái "nửa chừng" khi đang sửa cùng lúc nhiều dòng. **Cách tự kiểm:** đọc đúng vị trí decorator (ở
  class `kpi.template`, field `line_ids`, không phải ở `kpi.template.line`); thử qua `odoo shell` sửa
  1 dòng cũ + thêm 1 dòng mới trong cùng lệnh `write()` với tổng đúng 100 → phải lưu được (không bị
  bắt nhầm lỗi "nửa chừng").
- [ ] **27. Kỳ đánh giá — mở/đóng, `auto_generated`.** **Vị trí code:** `models/kpi_period.py`.
  **Logic kỳ vọng:** không tạo được phiếu Nháp mới trong kỳ đã đóng; `auto_generated` chỉ bật đúng 1
  lần cho mỗi kỳ (tránh cron tạo trùng phiếu). **Cách tự kiểm:** đọc điều kiện chặn tạo phiếu trong
  kỳ đóng (ở đâu: `kpi.evaluation.create()` hay `kpi.period`?); đọc cron `_cron_generate_evaluations`
  xác nhận có kiểm tra `auto_generated` trước khi tạo, và set lại thành `True` ngay sau khi tạo xong
  (không phải trước) để tránh race condition giữa 2 lần cron chạy đè nhau.
- [ ] **28. Phiếu đánh giá — công thức điểm + vòng đời.** **Vị trí code:**
  `models/kpi_evaluation.py`, hàm tĩnh `_score()`, các field compute `is_applicable`, `score`,
  `weighted_score`, `kpi_score`, `final_score`, `rating`, `final_rating`, và `_LOCKED_FIELDS`.
  **Logic kỳ vọng (chép lại công thức để đối chiếu dòng-với-dòng khi đọc code):**
  ```
  if direction == "lower":
      score = cap if actual <= 0 else target / actual * 100
  else:
      score = cap if target <= 0 else actual / target * 100
  return max(min(score, cap), 0.0)
  ```
  Dòng không áp dụng (`volume < min_volume`) có `score = 0` và bị loại khỏi **cả tử số lẫn mẫu số**
  khi tính `kpi_score = Σ(score×weight)/Σweight` — đây là chỗ dễ sai nhất (nhiều hệ thống chỉ loại
  khỏi tử số, quên loại khỏi mẫu số, làm điểm bị pha loãng sai). **Cách tự kiểm:** mở đúng hàm tính
  `kpi_score`, xác nhận mẫu số là `applicable_weight` (tổng trọng số **chỉ của dòng áp dụng**) chứ
  không phải tổng trọng số cố định 100; tính tay điểm An (113,31) hoặc Bình (73,90) trong `seeded`
  theo đúng công thức trên, so với số hệ thống hiển thị.
- [ ] **29. KPI Engine — phân phối tới đúng hàm theo `compute_mode`.** **Vị trí code:**
  `models/kpi_metric.py`, hàm `_is_engine_computed()` — **một hàm duy nhất** dùng chung cho mọi
  đường gọi (nút Tính KPI, wizard tạo phiếu hàng loạt, hành động Tính lại, cron, REST API).
  **Logic kỳ vọng:** không có bất kỳ chỗ nào khác tự so `compute_mode == 'auto'` hay `'domain'` một
  cách riêng lẻ — nếu có, đó là lỗi tiềm ẩn y hệt lỗi thật đã phát hiện ở Chương 5.4 ("phiếu không
  tính chỉ số domain khi bấm Tính KPI"). **Cách tự kiểm:** `grep -rn "compute_mode ==" addons/` —
  xác nhận **chỉ** xuất hiện trong định nghĩa của `_is_engine_computed()`, không rải rác nơi khác.
- [ ] **30. Phân quyền KPI — ai duyệt được, chặn xung đột vai trò.** **Vị trí code:**
  `models/kpi_evaluation.py`, `_check_can_approve()` + `_check_no_role_conflict()` (bản sửa theo
  YC-09, thay cho `_check_kpi_admin()` cũ). **Logic kỳ vọng:** `_check_can_approve()` cho qua nếu là
  KPI Administrator (mọi phiếu) HOẶC là quản lý trực tiếp (`employee_id.parent_id.user_id`, nhóm KPI
  Manager) của chính phiếu đó; `_check_no_role_conflict()` chỉ còn chặn đúng 1 trường hợp: người gọi
  là `employee_id.user_id` (chính nhân viên) — dù có thêm quyền Admin/Manager vẫn bị chặn tự duyệt
  phiếu của mình. Cả hai đều kiểm bằng **user thật đang đăng nhập** (`self.env.user`/`self.env.uid`),
  không chỉ dựa vào `has_group(...)` một mình (nếu chỉ dùng `has_group` thì không phân biệt được
  "đúng phiếu của ai"). **Cách tự kiểm:** `grep -n "_check_can_approve\|_check_no_role_conflict" addons/project_kpi_management/models/kpi_evaluation.py` —
  xác nhận cả `action_approve()` và `_open_reason_wizard()` gọi đúng 2 hàm này; thử trên UI: quản lý
  trực tiếp (không có quyền Admin) Duyệt được phiếu đội mình → thành công; tự Duyệt/Mở lại phiếu của
  chính mình (dù có thêm quyền Admin) → bị chặn; quản lý trực tiếp Duyệt phiếu KHÔNG do mình quản lý
  → bị chặn trừ khi có thêm quyền Admin.
- [ ] **31. Dashboard (Pivot/Graph/List).** Không áp dụng logic riêng — view XML pivot/graph/list
  tiêu chuẩn Odoo trên `kpi.evaluation.line` (đã lưu sẵn `employee_id/period_id/department_id/
  job_id/category`, xem mục 28), không có hàm Python tính riêng.
- [ ] **32. Báo cáo tổng hợp và chi tiết.** Không áp dụng logic riêng — view list/pivot tiêu chuẩn.
- [ ] **33. Chỉ số kiểm tra dữ liệu.** **Vị trí code:** `models/kpi_data_quality.py`, `init()` —
  `CREATE VIEW` SQL thuần, `_auto = False`. **Cách tự kiểm:** đọc câu SQL, xác nhận nhóm đúng theo
  `project.task.project_id`; đối chiếu 3 tỷ lệ (`sp_rate`, `origin_rate`, `classified_rate`) với mẫu
  số/tử số đúng định nghĩa trong `Nhom7_BaoCao.md` mục 3.3.
- [ ] **34. Bộ Tester tự động.** **Vị trí code:** `data/kpi_org_data.xml` (QA1–QA3, không có hàm
  Python — tự kiểm bằng cách xác nhận **không tồn tại** hàm `_metric_qa1`/`_metric_qa2`/`_metric_qa3`
  trong `kpi_engine.py`), `models/kpi_engine.py` hàm `_metric_qa4()` (tự suy tập dự án từ dữ liệu
  bug). **Cách tự kiểm:** `grep -n "_metric_qa" addons/project_kpi_management/models/kpi_engine.py`
  — chỉ thấy đúng 1 hàm (`_metric_qa4`), không phải 4 hàm; tính tay QA4 cho `dung` trong `seeded`.
- [ ] **35. Tự động hoá cuối kỳ (cron).** **Vị trí code:** `models/kpi_period.py`
  (`_cron_generate_evaluations`), `models/project_task.py` (`_cron_update_days_late`),
  `models/kpi_evaluation.py` (`_cron_provisional_compute`). **Logic kỳ vọng:** tạm tính giữa kỳ chỉ
  ghi dòng do engine tính (dùng lại `_is_engine_computed()` ở mục 29), **không** đặt `computed_date`
  (chỉ đặt `last_computed_date`) để Gửi duyệt vẫn đòi quản lý chủ động Tính KPI ít nhất 1 lần. **Cách
  tự kiểm:** đọc đúng dòng `_cron_provisional_compute` không set `computed_date`; thử set 1 chỉ số
  nhập tay (D9) trước, chạy cron tạm tính, xác nhận D9 không bị ghi đè.
- [ ] **36. Báo cáo in PDF.** **Vị trí code:** `report/kpi_evaluation_report.xml` (QWeb). **Cách tự
  kiểm:** đọc template, xác nhận lấy đúng field `final_score`, `final_rating`, từng dòng
  `evaluation_line_ids`, và với dòng dùng bảng bậc thì in thêm `achievement_pct`/`scale_name` (xem
  mục D3).
- [ ] **37. REST API.** **Vị trí code:** `controllers/api.py`. **Logic kỳ vọng:** `auth='bearer'`
  (không phải `auth='none'` hay tự parse header tay); danh sách/chi tiết phiếu đi qua ORM bình thường
  (không `sudo()`) để record rule KPI tự áp dụng theo quyền của chủ API key; POST ghi chỉ số nhập tay
  phải gọi `_is_engine_computed()` (mục 29) để từ chối ghi vào chỉ số tự động/cấu hình. **Cách tự
  kiểm:** đọc đúng decorator `auth='bearer'`; `grep -n "sudo()" controllers/api.py` — không nên có,
  hoặc nếu có phải giải thích được tại sao (ví dụ chỉ dùng lúc xác thực key, không dùng khi đọc/ghi
  dữ liệu phiếu).

---

## Phần D — Tính năng mở rộng sau triển khai cơ bản (11 mục)

- [ ] **D1. Chỉ số cấu hình không cần code.** Trùng mục 25.
- [ ] **D2. Bộ Tester tự động.** Trùng mục 34.
- [ ] **D3. Bảng bậc điểm.** **Vị trí code:** `models/kpi_score_scale.py` (validate bậc liên tục,
  không chồng, bắt đầu từ 0%), `models/kpi_evaluation.py` hoặc `kpi_template_line.py` (chụp
  `scale_json` lúc tạo phiếu, tra bậc trong `_score()`/hàm liên quan). **Logic kỳ vọng:** với chiều
  "Thấp là tốt", phải đổi `actual`/`target` thành % đạt mục tiêu **trước**, rồi mới tra bậc (không tra
  trực tiếp trên giá trị thô); `actual = 0` ở chiều Thấp tốt phải lấy % = trần (120%) trước khi tra,
  không phải chia cho 0. **Cách tự kiểm:** đọc đúng thứ tự (đổi % trước, tra bậc sau) trong code;
  tính tay 1 dòng Thấp tốt có `actual = 0` để xác nhận không có lỗi chia cho 0 và % ra đúng trần.
- [ ] **D4. Bộ Team Lead/PM.** **Vị trí code:** `models/kpi_engine.py`, `_metric_p2()`,
  `_metric_p3()`. **Logic kỳ vọng P2:** chỉ lấy phiếu cấp dưới **Đã gửi/Đã duyệt, đủ dữ liệu
  (`insufficient_data = False`), cùng kỳ, kỳ nằm trọn trong kỳ của Lead**; trung bình **theo từng
  người trước, rồi giữa các người** (không gộp phiếu thẳng vào 1 danh sách rồi chia đều — sẽ sai khi
  PM theo quý có cấp dưới theo tháng, 1 người có 3 phiếu sẽ có trọng số gấp 3 người chỉ có 1 phiếu).
  **Cách tự kiểm:** đọc đúng bước "nhóm theo nhân viên rồi mới trung bình" trong `_metric_p2()`; tính
  tay P2 của `phuc` trong `seeded` (79,01 trên 2 phiếu, Khoa bị loại vì thiếu dữ liệu) theo đúng logic
  này, so với số hệ thống.
- [ ] **D5. Bộ Business Analyst.** Trùng mục 15 (`_metric_b2()`) — tính tay B2 = 2/3 cho `lan`.
- [ ] **D6. Nhắc việc + tự đánh giá + báo cáo phòng ban.** **Vị trí code:**
  `models/kpi_evaluation.py`, `_sync_workflow_activities()` (idempotent, gọi sau `create` và mỗi lần
  đổi `state`), và chặn ghi trực tiếp `employee_comment`/`self_score` ở cả `create()` lẫn `write()`
  (chỉ wizard `kpi.self.assessment.wizard`/`kpi.acknowledge.wizard` ghi được qua `sudo()`). **Cách tự
  kiểm:** `grep -n "employee_comment\|self_score" models/kpi_evaluation.py` — xác nhận có chặn ở
  **cả hai** phương thức `create()` và `write()`, không chỉ 1 trong 2 (đây chính là lỗi thật đã phát
  hiện ở Chương 5.4, quản lý từng ghi trực tiếp được field này qua `write()`).
- [ ] **D7. Kỳ riêng theo bộ KPI + mục tiêu riêng.** **Vị trí code:** `models/kpi_target_override.py`
  hoặc nơi tính gợi ý mục tiêu (percentile 25/50/75). **Logic kỳ vọng:** chỉ lấy lịch sử từ phiếu
  **Đã duyệt, đủ dữ liệu, dòng áp dụng, cùng loại kỳ**, tối đa 6 kỳ gần nhất, tối thiểu 3 kỳ; với chỉ
  số "Thấp là tốt" phải **đảo chiều** gán nhãn (Dễ = phân vị cao hơn, Khó = phân vị thấp hơn) — nếu
  không đảo, nhãn "Khó" sẽ hiện ra số dễ hơn với chỉ số thấp-là-tốt. **Cách tự kiểm:** đọc đúng chỗ
  đảo chiều theo `direction`; tính tay ví dụ D2 (10, 20, 30 → Dễ 17,5/Vừa 25/Khó 32,5, cao là tốt) và
  thử tưởng tượng với 1 chỉ số thấp-là-tốt để xác nhận code có đảo đúng không chỉ tin vào ví dụ có
  sẵn trùng chiều "cao là tốt".
- [ ] **D8. Màn hình tổng quan KPI.** **Vị trí code:** `models/kpi_period.py`, các field
  `dashboard_*` (compute không lưu). **Logic kỳ vọng:** dùng **một `_read_group` cho mọi kỳ đang hiển
  thị**, không gọi `search_count()` riêng cho từng kỳ (nếu không, mở màn hình nhiều kỳ sẽ chậm dần).
  **Cách tự kiểm:** đọc đúng code dùng `_read_group` một lần; nếu nghi ngờ, đo số câu truy vấn khi mở
  với 1 kỳ so với 8 kỳ (nên gần bằng nhau, không tăng tuyến tính).
- [ ] **D9. Phản hồi 360 độ.** **Vị trí code:** `project_kpi_survey/models/kpi_feedback.py` (hoặc
  tên tương đương) và wizard mời. **Logic kỳ vọng:** kiểm tra quyền (đúng quản lý, phiếu đang Nháp)
  **trước** khi gọi bất kỳ `sudo()` nào (đây là lỗi thật đã phát hiện: wizard ban đầu đọc khảo sát
  bằng quyền quản lý nên bị `AccessError`, sau sửa chạy `sudo()` nhưng phải đặt SAU bước kiểm quyền,
  không phải trước). **Cách tự kiểm:** đọc đúng thứ tự: kiểm tra điều kiện (ai gọi, trạng thái phiếu)
  bằng quyền thường → nếu hợp lệ mới `sudo()` để tạo lời mời/đọc khảo sát. F1 chỉ hiện khi đủ 3 câu
  trả lời **hoàn thành** (`state = done`, loại `test_entry`).
- [ ] **D10. Mức đáp ứng kỹ năng (S1).** **Vị trí code:** `project_kpi_skills/models/*.py`, hàm tính
  S1. **Logic kỳ vọng:** so theo `level_progress` (0–100), lọc theo hiệu lực tại **ngày cuối kỳ**
  (`valid_from ≤ ngày cuối kỳ` và `valid_to` trống hoặc `≥`), và dùng **chức danh đã chụp trên phiếu**
  (`ev.job_id`), không phải chức danh hiện tại của nhân viên. **Cách tự kiểm:** đọc đúng điều kiện
  lọc theo ngày hiệu lực và nguồn `job_id` lấy từ phiếu chứ không phải `employee.job_id` trực tiếp;
  tính tay S1 = 66,67% cho An (Python 100, Odoo 50, SQL 25 so với yêu cầu 75/50/50).
- [ ] **D11. Chặn xung đột vai trò.** Trùng mục 30.

---

## Tổng kết

| Phần | Số mục | Không áp dụng (field thuần) | Có logic cần rà code |
|---|---|---|---|
| A | 10 | 10 | 0 |
| B | 14 | 5 | 9 |
| C | 13 | 2 | 11 |
| D | 11 (4 trùng A–C) | 0 | 11 (7 mới) |

Khi rà xong một mục mà thấy code **không khớp** với "Logic kỳ vọng" ghi ở trên (hoặc khớp nhưng bạn
tính tay ra số khác), ghi lại rõ: vị trí (file + dòng), bạn kỳ vọng gì, code thực tế làm gì — rồi báo
lại để sửa trước ngày dừng thay đổi, đừng tự sửa logic nghiệp vụ quan trọng nếu chưa chắc chắn.
