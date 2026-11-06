# Hướng dẫn sử dụng — Project KPI & Performance Management

Tài liệu này đi qua **từng tính năng một**, theo đúng danh sách gốc trong
`Nhom7_BaoCao_ThongKeTinhNang.xlsx` (sheet "danh sách tính năng" — 37 mục, "Chỉ số các vai trò khác",
"Mở rộng sau Chương 9" — 12 mục), không gộp tắt thành bảng tóm lược. Mỗi mục có cách dùng cụ thể
(field nào, menu nào, nút nào). Khác với Chương 6 của `Nhom7_BaoCao.md` (tóm tắt theo vai trò), file
này là bản tra cứu đầy đủ theo từng tính năng.

## Mục lục

- [Phần A — Dữ liệu Odoo gốc được tái sử dụng (10 mục)](#phần-a--dữ-liệu-odoo-gốc-được-tái-sử-dụng-10-mục)
- [Phần B — Field/tính năng tuỳ biến thêm vào Odoo gốc (14 mục)](#phần-b--fieldtính-năng-tuỳ-biến-thêm-vào-odoo-gốc-14-mục)
- [Phần C — Màn hình/tính năng xây mới (13 mục)](#phần-c--màn-hìnhtính-năng-xây-mới-13-mục)
- [Phần D — Tính năng mở rộng sau triển khai cơ bản (11 mục)](#phần-d--tính-năng-mở-rộng-sau-triển-khai-cơ-bản-11-mục)
- [Phụ lục — Bảng công thức toàn bộ chỉ số](#phụ-lục--bảng-công-thức-toàn-bộ-chỉ-số)

---

## Phần A — Dữ liệu Odoo gốc được tái sử dụng (10 mục)

Các mục này là tính năng Odoo gốc, module KPI chỉ đọc lại dữ liệu, không thêm field. Cách dùng là
cách dùng chuẩn của Odoo Project/Employees/Calendar.

**1. Deadline, ngày hoàn thành (Project).** Trên form task, đặt **Hạn chót** (`date_deadline`) khi
giao việc. Ngày hoàn thành (`date_end`) hệ thống tự ghi khi task chuyển vào stage có cờ **Folded**
— đây là nguồn tính D1 (đúng hạn) và số ngày trễ. **Bắt buộc**: với mỗi dự án, vào **Project ›
Cấu hình › Giai đoạn dự án**, mở stage "Done"/"Hoàn thành" và bật **Folded**.

**2. Trạng thái task (Project).** Dùng 4 trạng thái chuẩn của Odoo: Đang làm, Yêu cầu chỉnh sửa
(`02_changes_requested`), Đã duyệt review (`03_approved`), Hoàn thành (`1_done`), Huỷ
(`1_canceled`). Chuyển trạng thái bằng các nút trên task hoặc kéo thẻ Kanban sang cột tương ứng —
đây là nguồn cho D5 (pass review lần đầu); task Huỷ không tính vào bất kỳ chỉ số nào.

**3. Mức ưu tiên (Project).** Đặt cờ sao (Low/Medium/High/Urgent) trên task như bình thường. D7
(thời gian sửa bug nghiêm trọng) chỉ lọc bug có mức **High** hoặc **Urgent**.

**4. Thời gian xử lý (Project).** Trường `working_hours_close` của Odoo (tính theo lịch làm việc,
không tính giờ ngủ/cuối tuần) tự có khi task đóng — không cần làm gì thêm, đây là nguồn tính D7.

**5. Giao việc (Project).** Gán **Người phụ trách** (`user_ids`) trên mỗi task như bình thường —
toàn bộ Engine quy task/bug về đúng nhân viên dựa vào trường này.

**6. Tổ chức task (Project).** Dùng các quan hệ có sẵn của Odoo: task cha/con (`parent_id`), cột
mốc (`milestone_id`), task phụ thuộc (`depend_on_ids`), nhãn (`tag_ids`) để nhóm công việc — module
KPI không tạo thêm khái niệm "nhóm việc" (Task Group) riêng, dùng lại các quan hệ này.

**7. Nhân viên (Employees).** Mỗi nhân viên (`hr.employee`) cần có **Người dùng liên quan**
(`user_id`, để Engine đọc đúng task/bug) và **Quản lý** (`parent_id`, tab "Thông tin làm việc") —
xác định ai là người duyệt và áp dụng phân quyền theo nhóm.

**8. Chức danh (Employees).** Vào **Nhân viên › Cấu hình › Vị trí công việc**, mỗi chức danh
(`hr.job`) là căn cứ để gắn đúng 1 Bộ KPI (xem mục 21).

**9. Lịch sự kiện (Calendar).** Khi có buổi chia sẻ kiến thức nội bộ, tạo sự kiện trong **Lịch**,
chọn loại sự kiện **"Chia sẻ kiến thức"** (đã tạo sẵn trong dữ liệu cấu hình) — nguồn tính D8.

**10. Chatter (Discuss).** Mọi phiếu KPI đều có tab trao đổi (chatter) chuẩn của Odoo ở cuối form —
mọi thao tác duyệt/trả về/mở lại/điều chỉnh điểm đều tự ghi log ở đây, dùng để tra lại lịch sử.

---

## Phần B — Field/tính năng tuỳ biến thêm vào Odoo gốc (14 mục)

Các field này module KPI thêm trực tiếp vào model Odoo gốc (`project.task`, `hr.job`,
`hr.employee`, Settings) — xuất hiện ngay trên view gốc, không phải màn hình riêng.

**11. Phân loại task.** Field **Loại task** (`task_type`) trên task: chọn **Feature** hoặc **Bug**.
Bắt buộc chọn đúng vì nhiều chỉ số lọc theo loại này (D6 chỉ tính Feature, D3/D4 chỉ tính Bug).

**12. Story point.** Field **Story point** (`story_points`) trên task — nhập số điểm ước lượng.
Nguồn tính D2 (tổng story point hoàn thành trong kỳ).

**13. Truy vết bug.** Trên task loại Bug: field **Task gốc** (`origin_task_id`, chọn task Feature bị
lỗi) và cờ **Lỗi production** (`is_production_bug`). Trên task Feature, tab **Bug liên quan**
(`bug_ids`) tự hiện danh sách bug trỏ về nó. Nguồn tính D3, D4.

**14. Kết quả xử lý bug.** Field **Kết quả** (`bug_resolution`) trên task Bug: valid / wont_fix /
duplicate / invalid. Chỉ `valid` và `wont_fix` được tính là "bug tính KPI".

**15. Nguyên nhân bug.** Field **Nguyên nhân** (`bug_root_cause`) trên task Bug: code / requirement
/ environment. Chọn `requirement` thì bug này tự chuyển qua tính cho BA (B2) thay vì Developer.

**16. Đếm lần bị trả về.** Field **Số lần bị trả về** (`review_reject_count`) — chỉ đọc, hệ thống
tự tăng mỗi khi task chuyển trạng thái lùi về "Yêu cầu chỉnh sửa". Nguồn tính D5.

**17. Đánh dấu unit test.** Field **Có unit test** (`has_unit_test`) trên task Feature — **chỉ tài
khoản thuộc nhóm Manager mới tick được** (nhân viên thường bị khoá ô này). Nguồn tính D6.

**18. Ngày hoàn thành (ghi đè).** Không phải thao tác người dùng — hệ thống tự ghi lại `date_end`
ngay khi task chuyển sang trạng thái Hoàn thành, kể cả khi stage Kanban hiện tại không fold (khắc
phục hành vi gốc của Odoo là xoá `date_end` khi đổi sang stage không fold).

**19. Số ngày trễ.** Field **Số ngày trễ** (`days_late`, chỉ đọc) tự tính mỗi ngày (tác vụ nền) —
so `date_end`/hôm nay với `date_deadline`. Dùng để lọc nhanh task trễ hạn trên danh sách.

**20. Giao diện task.** Trên danh sách/form task có thêm các bộ lọc nhanh: **Bug**, **Lỗi
production**, **Trễ hạn**, **Bị trả về**, **Bug chưa phân loại** — dùng để rà soát dữ liệu trước khi
tính KPI, nằm ở thanh tìm kiếm phía trên danh sách task.

**21. Gắn KPI theo chức danh.** Trên form chức danh (`hr.job`, mục 8), field **Bộ KPI**
(`kpi_template_id`) — chọn bộ KPI sẽ áp dụng cho mọi nhân viên giữ chức danh này.

**22. Phân quyền nền.** Không phải thao tác trực tiếp — nhóm "KPI Manager" tự kế thừa quyền "Project
Manager" có sẵn của Odoo, nên quản lý KPI cũng thao tác được trên Project như Project Manager.

**23. Hồ sơ nhân viên.** Trên form nhân viên có thêm nút thông minh **"Phiếu KPI"** (góc trên bên
phải) — bấm vào để xem nhanh toàn bộ lịch sử phiếu đánh giá của người đó.

**24. Cấu hình (Settings).** Vào **Settings › KPI** (hoặc **KPI › Cấu hình › Thiết lập**): chỉnh
ngưỡng xếp loại, điểm trần tối đa, biên độ điều chỉnh điểm — xem chi tiết ở mục 30 trong Phần C.

---

## Phần C — Màn hình/tính năng xây mới (13 mục)

Đây là các model/màn hình hoàn toàn mới, không có trong Odoo gốc.

**25. Danh mục chỉ số (`kpi.metric`).** Vào **KPI › Cấu hình › Chỉ số KPI** → Tạo mới: nhập Mã,
Tên, Nhóm, Đơn vị, Chiều (Cao là tốt/Thấp là tốt) và chọn **Cách tính**: *Tự động (code)* (chỉ số đã
có sẵn hàm tính, chỉ chọn, không cấu hình thêm), *Tự động (cấu hình)* (không cần biết lập trình —
chọn model nguồn, trường người, trường ngày, phép tính Đếm/Tổng/Trung bình, và nhập domain lọc dữ
liệu như `[('state','=','1_done')]`), hoặc *Nhập tay* (quản lý tự chấm trên phiếu). Có nút **"Thử
tính"** ngay trên form để xem kết quả thử cho 1 nhân viên + 1 kỳ, không cần tạo phiếu thật.

**26. Bộ KPI theo vai trò (`kpi.template`, `kpi.template.line`).** Vào **KPI › Cấu hình › Bộ KPI** →
Tạo bộ mới, thêm từng dòng chỉ số kèm **Mục tiêu** và **Trọng số** (tổng các dòng bắt buộc = 100).
Gắn bộ này vào Chức danh (mục 21). Mỗi bộ có thể đặt riêng **Loại kỳ** (tháng/sprint/quý).

**27. Kỳ đánh giá (`kpi.period`).** Vào **KPI › Đánh giá › Kỳ đánh giá** → Tạo kỳ (tháng/sprint/
quý), đặt ngày bắt đầu/kết thúc, mở/đóng kỳ. Khi kỳ kết thúc, hệ thống tự động tạo phiếu cho nhân
viên liên quan (tác vụ nền chạy hằng ngày).

**28. Phiếu đánh giá (`kpi.evaluation`, `kpi.evaluation.line`).** Vào **KPI › Đánh giá › Phiếu đánh
giá**. Vòng đời: Nháp (nhân viên có thể **Tự đánh giá**) → quản lý bấm **Tính KPI** → chấm chỉ số
nhập tay, **Điều chỉnh điểm** nếu cần (bắt buộc ghi lý do) → **Gửi duyệt** (tạo nhắc việc cho người
duyệt) → người duyệt **Duyệt**/**Trả về** (ghi lý do)/**Mở lại** (ghi lý do) → sau khi Đã duyệt,
nhân viên nhận nhắc việc **Xác nhận kết quả**.

**29. KPI Engine (`kpi.engine`).** Không phải màn hình — đây là bộ hàm chạy ngầm mỗi khi bấm "Tính
KPI" hoặc tạo phiếu, tự tính các chỉ số *Tự động*. Người dùng không thao tác trực tiếp vào đây.

**30. Phân quyền KPI (groups, access, record rules).** 3 nhóm: Nhân viên (chỉ phiếu của mình), KPI
Manager (tính KPI, chấm D9, điều chỉnh điểm, gửi duyệt, VÀ tự Duyệt/Trả về/Mở lại được phiếu của
nhân viên mình quản lý trực tiếp), KPI Administrator (toàn quyền mọi phiếu, chủ yếu lo cấu hình) —
gán nhóm cho người dùng ở **Settings › Người dùng & Công ty › Người dùng**, mục "Quản lý KPI". Hệ
thống chỉ còn chặn đúng 1 xung đột vai trò: không ai được tự duyệt/trả về/mở lại phiếu của CHÍNH
MÌNH, kể cả khi có thêm quyền Admin hay Manager — quản lý trực tiếp duyệt phiếu của nhân viên mình
quản lý là luồng bình thường, không phải xung đột.

**31. Dashboard cơ bản (Pivot/Graph/List).** Vào **KPI › Báo cáo › Dashboard** — xem theo nhân viên,
chỉ số, kỳ, xếp loại, team/dự án; chuyển qua lại giữa 3 kiểu xem (Pivot/Graph/List) bằng nút góc
trên bên phải.

**32. Báo cáo tổng hợp và chi tiết.** **KPI › Báo cáo › Báo cáo tổng hợp** (danh sách/pivot toàn bộ
phiếu) và **KPI › Báo cáo › Báo cáo chi tiết** (xem từng dòng chỉ số: mục tiêu, thực tế, điểm, trọng
số, ghi chú).

**33. Chỉ số kiểm tra dữ liệu.** **KPI › Báo cáo › Kiểm tra chất lượng dữ liệu** — xem tỷ lệ bug có
task gốc, tỷ lệ bug đã phân loại đủ, tỷ lệ task có story point, theo từng dự án — dùng để phát hiện
dữ liệu nguồn chưa sạch trước khi tin vào điểm KPI.

**34. Bộ KPI Tester tự động.** Có sẵn trong dữ liệu cấu hình, gắn vào chức danh "Kiểm thử phần mềm
(QA)" (mục 21) — không cần tạo thêm, chỉ cần gán chức danh này cho nhân viên Tester. Chi tiết công
thức QA1–QA5 ở Phụ lục.

**35. Tự động hoá cuối kỳ (`ir.cron`).** Không phải thao tác người dùng — 3 tác vụ chạy nền: tự tạo
phiếu khi kỳ kết thúc (hằng ngày), tự cập nhật số ngày trễ (hằng ngày), tạm tính giữa kỳ cho phiếu
Nháp (hằng tuần). Biết để không thắc mắc khi thấy phiếu tự xuất hiện.

**36. Báo cáo in PDF.** Trên mỗi phiếu đánh giá, bấm nút **In** (góc trên) → chọn "Phiếu đánh giá
KPI" → tải file PDF — dùng để lưu trữ hoặc ký tay ngoài hệ thống.

**37. REST API.** 3 endpoint dùng cho công cụ ngoài (không thao tác qua giao diện): `GET` danh sách
phiếu, `GET` chi tiết 1 phiếu, `POST` ghi điểm cho chỉ số nhập tay — xác thực bằng **API key**
(tạo ở **Settings › Người dùng › [chọn người dùng] › Khoá API**). API chạy đúng theo quyền của chủ
API key, record rule KPI vẫn áp dụng như trên giao diện.

---

## Phần D — Tính năng mở rộng sau triển khai cơ bản (11 mục)

Nhóm này lấy từ sheet "Mở rộng sau Chương 9" — các tính năng được bổ sung sau bản lõi, một số đã
nhắc ở Phần C nhưng có thêm chi tiết vận hành dưới đây.

**D1. Chỉ số cấu hình không cần code.** Chính là mục 25 (Cách tính = *Tự động (cấu hình)*) — nhắc
lại vì đây là tính năng cho phép KPI Administrator tự thêm chỉ số *Tự động* mới mà không cần nhờ
lập trình viên, miễn là logic chỉ cần đếm/tổng/trung bình/tỷ lệ trên 1 domain.

**D2. Bộ KPI Tester tự động.** Xem mục 34.

**D3. Bảng bậc điểm.** Trên mỗi dòng chỉ số trong Bộ KPI (mục 26), có thể gắn một **Bảng bậc**
(`kpi.score.scale`, tạo ở **KPI › Cấu hình › Bảng bậc điểm**) thay vì chấm tuyến tính theo % đạt mục
tiêu. Bảng bậc được **chụp (snapshot)** vào đúng lúc tạo phiếu — sửa bảng bậc sau đó không đổi điểm
phiếu cũ.

**D4. Bộ Team Lead/PM.** Gắn vào chức danh Team Lead/PM — gồm P1–P5 (công thức ở Phụ lục). P2 (điểm
trung bình cấp dưới) tự loại phiếu "thiếu dữ liệu"/chưa gửi duyệt khỏi phép tính — không cần tạo
phiếu theo đúng thứ tự. P4 chỉ có khi cài thêm module `project_kpi_timesheet`.

**D5. Bộ Business Analyst.** Gắn vào chức danh BA — gồm B1–B4. Trên task Feature, field **Yêu cầu
gốc** (`requirement_id`) trỏ về task loại Yêu cầu — khi một bug bị đánh dấu nguyên nhân "yêu cầu
sai" (mục 15), bug đó tự quy về B2 của đúng BA phụ trách thay vì tính cho Developer.

**D6. Nhắc việc + tự đánh giá + báo cáo phòng ban.** Nhắc việc (activity) tự giao đúng người ở mỗi
bước của vòng đời phiếu (xem mục 28) — không cần cấu hình gì thêm ngoài đặt **Người duyệt mặc định**
ở Settings (mục 24). Nhân viên tự đánh giá qua nút **Tự đánh giá** trên phiếu Nháp, xác nhận kết quả
qua nút **Xác nhận kết quả** sau khi Đã duyệt. Báo cáo theo phòng ban ở **KPI › Báo cáo › Theo
phòng ban**.

**D7. Kỳ riêng theo bộ KPI + mục tiêu riêng.** Loại kỳ đặt ở mục 26. Mục tiêu riêng theo nhân
viên/phòng ban tạo ở **KPI › Cấu hình › Mục tiêu riêng** — có nút **gợi ý mục tiêu** tính từ lịch sử
(phân vị 25/50/75 của các kỳ đã duyệt), bấm "Áp dụng mức Dễ/Vừa/Khó" để điền nhanh hoặc tự sửa tay.

**D8. Màn hình tổng quan KPI.** **KPI › Tổng quan** (menu đầu tiên của app) — Kanban theo từng kỳ:
tổng số phiếu, số theo trạng thái, số "Cần cải thiện"/"Thiếu dữ liệu"/"Chờ xác nhận". Bấm vào mỗi
con số để mở đúng danh sách phiếu. Số liệu tự lọc theo phân quyền.

**D9. Phản hồi 360 độ.** Chỉ có khi cài `project_kpi_survey`. Trên phiếu dùng bộ có chỉ số F1, bấm
**Mời đánh giá 360** → chọn tối thiểu 3 người. Người được mời nhận nhắc việc kèm link khảo sát.
Điểm F1 chỉ hiện khi đủ 3 người trở lên trả lời (dưới ngưỡng hiện "Không áp dụng"), quản lý không
xem được câu trả lời riêng lẻ.

**D10. Mức đáp ứng kỹ năng (S1).** Chỉ có khi cài `project_kpi_skills`. So **kỹ năng khai báo của
nhân viên** (tab Kỹ năng trên hồ sơ nhân viên, Odoo gốc `hr_skills`) với **kỹ năng yêu cầu của chức
danh** — chụp lại đúng thời điểm tạo phiếu, không đổi theo chức danh/kỹ năng hiện tại.

**D11. Chặn xung đột vai trò.** Không phải thao tác bật/tắt — đây là ràng buộc luôn luôn có hiệu
lực: người duyệt một phiếu không được là chính nhân viên đó (tự duyệt phiếu của mình), kể cả khi
người đó có thêm quyền Admin hay Manager. Quản lý trực tiếp duyệt phiếu của nhân viên mình quản lý
KHÔNG còn bị coi là xung đột (xem mục 30) — đây là thay đổi so với bản đầu, nơi quản lý trực tiếp
từng bị chặn luôn.

> Sheet "Mở rộng sau Chương 9" còn 1 dòng ghi chú kỹ thuật **"2 lỗi logic sửa 2026-10-23"**
> (`date_end` không còn bị ghi đè khi đổi stage; đổi mã chỉ số Tự động không còn hàm tương ứng bị
> chặn khi lưu) — đây là bản ghi sửa lỗi (changelog), không phải một tính năng có cách dùng riêng,
> nên không có mục hướng dẫn sử dụng tương ứng.

---

## Phụ lục — Bảng công thức toàn bộ chỉ số

### Bộ Developer (D1–D9)

| Mã | Nhóm | Tên chỉ số | Công thức | Đơn vị | Chiều | Cách tính | Mục tiêu | Trọng số |
|---|---|---|---|---|---|---|---|---|
| D1 | Tiến độ | Hoàn thành đúng hạn | Task xong đúng hạn / Task có deadline trong kỳ × 100 | % | Cao là tốt | Tự động (code) | 90 | 20% |
| D2 | Tiến độ | Story point hoàn thành | Tổng story_points của task Done trong kỳ | SP | Cao là tốt | Tự động (code) | 20 | 10% |
| D3 | Chất lượng | Mật độ lỗi | Bug tính KPI (valid/wont_fix, nguyên nhân code) / SP hoàn thành | bug/SP | Thấp là tốt | Tự động (code) | 0,3 | 15% |
| D4 | Chất lượng | Lỗi lọt production | Bug production tính KPI / Tổng bug tính KPI × 100 | % | Thấp là tốt | Tự động (code) | 5 | 15% |
| D5 | Quy trình | Pass review lần đầu | Task chưa từng bị trả về / Task đã qua review × 100 | % | Cao là tốt | Tự động (code) | 80 | 10% |
| D6 | Quy trình | Có unit test | Task Feature có unit test / Task Feature Done × 100 | % | Cao là tốt | Tự động (code) | 70 | 10% |
| D7 | Chất lượng | Thời gian sửa bug nghiêm trọng | Trung bình working_hours_close của bug High/Urgent | giờ | Thấp là tốt | Tự động (code) | 24 | 5% |
| D8 | Cộng tác | Chia sẻ kiến thức | Số sự kiện calendar.event gắn nhãn "Chia sẻ kiến thức" trong kỳ | sự kiện | Cao là tốt | Tự động (code) | 1 | 5% |
| D9 | Cộng tác | Đánh giá của quản lý | Quản lý chấm thang 1–5: làm việc nhóm, hỗ trợ đồng nghiệp, thái độ | điểm | Cao là tốt | Nhập tay | 4 | 10% |

### Các bộ KPI vai trò khác

| Mã | Nhóm | Tên chỉ số | Đơn vị | Chiều | Cách tính | Dùng trong bộ KPI |
|---|---|---|---|---|---|---|
| QA1 | Chất lượng | Số bug hợp lệ tìm được | bug | Cao là tốt | Tự động (cấu hình) | Tester (tự động) |
| QA2 | Chất lượng | Tỷ lệ bug bị từ chối | % | Thấp là tốt | Tự động (cấu hình) | Tester (tự động) |
| QA3 | Quy trình | Tỷ lệ bug đủ phân loại | % | Cao là tốt | Tự động (cấu hình) | Tester (tự động) |
| QA4 | Chất lượng | Lỗi lọt production của dự án tham gia | % | Thấp là tốt | Tự động (code) | Tester (tự động) |
| QA5 | Cộng tác | Đánh giá của quản lý (Tester) | điểm | Cao là tốt | Nhập tay | Tester (tự động) |
| P1 | Tiến độ | Tỷ lệ milestone đạt đúng hạn | % | Cao là tốt | Tự động (cấu hình) | Team Lead / PM |
| P2 | Cộng tác | Điểm KPI trung bình của team | điểm | Cao là tốt | Tự động (code) | Team Lead / PM |
| P3 | Quy trình | Chất lượng dữ liệu dự án | % | Cao là tốt | Tự động (code) | Team Lead / PM |
| P4 | Tiến độ | Giờ thực tế so với kế hoạch | % lệch | Thấp là tốt | Tự động (code) | Team Lead / PM (có giờ làm) |
| P5 | Cộng tác | Đánh giá của cấp trên (Lead/PM) | điểm | Cao là tốt | Nhập tay | Team Lead / PM |
| B1 | Tiến độ | Yêu cầu hoàn thành đúng hạn | % | Cao là tốt | Tự động (cấu hình) | Business Analyst |
| B2 | Chất lượng | Mật độ bug do yêu cầu sai | bug/yêu cầu | Thấp là tốt | Tự động (code) | Business Analyst |
| B3 | Quy trình | Yêu cầu qua review lần đầu | % | Cao là tốt | Tự động (cấu hình) | Business Analyst |
| B4 | Cộng tác | Đánh giá của quản lý (BA) | điểm | Cao là tốt | Nhập tay | Business Analyst |
| S1 | Quy trình | Mức đáp ứng kỹ năng | % | Cao là tốt | Tự động (code) | Developer (có năng lực) |
| F1 | Cộng tác | Phản hồi 360 độ | % | Cao là tốt | Tự động (code) | Developer (có phản hồi 360) |

---

*Tài liệu tham chiếu: `Nhom7_BaoCao_ThongKeTinhNang.xlsx` (danh sách tính năng gốc, cả 4 sheet),
`Nhom7_BaoCao.md` Chương 2–3 (kiến trúc & thiết kế CSDL chi tiết), `KICH_BAN_DEMO.md` (kịch bản
trình diễn).*
