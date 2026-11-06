# Kịch bản demo Developer — tự thao tác tay từ Giai đoạn 0 đến Giai đoạn 5

Khác với `KICH_BAN_DEMO.md` (bản trình diễn trước hội đồng, dùng backup `seeded` để tiết kiệm thời
gian, đi qua nhiều vai trò), file này là bản **rà soát riêng cho vai trò Developer**, đi đúng từng
bước của `FLOW_VAN_HANH_TU_DAU_DEN_CUOI.md` theo thứ tự Giai đoạn 0 → 5, và **không dùng dữ liệu có
sẵn của bất kỳ bước nào** — kể cả Chức danh, Bộ KPI, nhân viên đều dựng tay bằng tên hoàn toàn mới
(`R&D Beta` / `Lập trình viên Beta` / `Lâm`, `Huy`) để chắc chắn mọi thứ chạy đúng từ con số 0, không
bị dữ liệu mẫu có sẵn (An, Bình, Chi, Hà...) che giấu lỗi. Mục đích là **bằng chứng tự kiểm**, không
phải kịch bản trình diễn có canh giờ — vì vậy không cắt bớt bước nào, kể cả bước chỉ xác nhận cấu
hình đã đúng.

Số trong ngoặc `(mục X)` / `(DX)` tham chiếu đúng mục trong `HUONG_DAN_SU_DUNG.md`. Mọi bước đều
🖐️ thao tác tay qua giao diện — không dùng `prepare_defense.sh`, không chờ cron.

## Một lưu ý kỹ thuật trước khi bắt đầu (Giai đoạn 1)

9 chỉ số D1–D9 của bộ Developer là **Tự động (code)** (trừ D9 nhập tay) — nghĩa là mỗi chỉ số gắn
với đúng 1 hàm Python `_metric_d1()` … `_metric_d9()` đã viết sẵn trong `kpi.engine`
(`_check_auto_metric_has_function` bắt buộc hàm phải tồn tại trước khi lưu). Vì vậy **không tạo chỉ
số trùng mã D1–D9 mới** — 9 bản ghi `kpi.metric` mã D1–D9 đã có sẵn trong dữ liệu cấu hình (`clean`)
đúng là phần "tạo mới" của chương trình gốc, demo ở đây chỉ xác nhận chúng tồn tại và dùng lại khi
lập **Bộ KPI "Developer Beta" hoàn toàn mới**. Đây chính là điểm khác với `KICH_BAN_DEMO.md` Phần 7
(vai trò Sales dùng chỉ số *Tự động (cấu hình)*/*Nhập tay* — không cần hàm Python nên tạo mới thoải
mái); Developer dùng *Tự động (code)* nên phần "code" (hàm Python) đã có sẵn, còn **bản ghi cấu
hình** (Chỉ số, Bộ KPI, gán vào Chức danh) thì demo này vẫn dựng tay toàn bộ.

## Chuẩn bị

1. `bash addons/project_kpi_management/scripts/restore_defense.sh clean` → chờ `prepare_defense.sh`
   báo "tất cả OK".
2. Đăng nhập `admin`. Chưa cần tạo user `lam`/`huy` trước — tạo ngay trong Giai đoạn 0.

## Tài khoản sẽ tạo trong demo này

| Tài khoản | Vai trò | Ghi chú |
|---|---|---|
| `admin` (có sẵn) | KPI Administrator | Người duyệt mặc định (Settings); chủ yếu lo cấu hình |
| `lam` (tạo mới) | Quản lý trực tiếp của `huy`, nhóm **KPI Manager** | Tự Duyệt/Trả về/Mở lại được phiếu của Huy, không cần thêm quyền Admin (mục 30) |
| `huy` (tạo mới) | Chức danh "Lập trình viên Beta", nhóm **Nhân viên** mặc định | Người được đánh giá KPI; tạm được gán thêm Admin ở bước 27 chỉ để minh hoạ xung đột vai trò, rồi bỏ lại ngay |

---

## Giai đoạn 0 — Tổ chức & nhân sự (⏱ ~4')

1. 🖐️ **Nhân viên › Phòng ban** → tạo phòng ban **"R&D Beta"**.
2. 🖐️ **Nhân viên › Cấu hình › Vị trí công việc** → tạo chức danh **"Lập trình viên Beta"** (mục 8)
   — để trống Bộ KPI, vì Bộ KPI chưa tồn tại ở bước này.
3. 🖐️ **Nhân viên › Nhân viên** → tạo nhân viên **"Lâm"**, phòng ban "R&D Beta", tab *Thông tin làm
   việc*: gán **Người dùng liên quan** = tạo user mới `lam` (mục 7).
4. 🖐️ Tạo nhân viên **"Huy"**, phòng ban "R&D Beta", **Chức danh** = "Lập trình viên Beta", tab
   *Thông tin làm việc*: **Quản lý** = Lâm, **Người dùng liên quan** = tạo user mới `huy` (mục 7) —
   thiếu 1 trong 2 field này thì Engine không đọc được task của Huy.
5. 🖐️ **Thiết lập › Người dùng & Công ty › Người dùng** → mở user `lam` → tích thêm nhóm **KPI
   Manager** (mục 30) — chỉ cần đúng nhóm này là `lam` đã tự Duyệt/Trả về/Mở lại được phiếu của Huy
   ở Giai đoạn 4, không cần gán thêm quyền Admin nữa (khác bản trước: nhóm KPI Manager cũng tự có
   quyền Project Manager — mục 22 — nên `lam` thao tác được trên dự án ngay không cần gán thêm). User
   `huy` giữ nhóm mặc định "Nhân viên", không đổi gì ở bước này.

---

## Giai đoạn 1 — Cấu hình KPI cho "Lập trình viên Beta" (⏱ ~8')

6. 🖐️ **KPI › Cấu hình › Chỉ số KPI** → xác nhận 9 chỉ số **D1–D9** đã có sẵn (mục 25, xem bảng công
   thức ở Phụ lục `HUONG_DAN_SU_DUNG.md`) — mở D1, bấm **"Thử tính"**, chọn Huy + kỳ bất kỳ → ra kết
   quả hợp lệ (0 hoặc "Không áp dụng", **không lỗi**) dù Huy chưa có task nào. Đây là bằng chứng
   Engine đọc đúng theo nhân viên, không phụ thuộc dữ liệu có sẵn.
7. 🖐️ **KPI › Cấu hình › Bộ KPI** → tạo mới **"Developer Beta"** (mục 26), Loại kỳ = *Tháng*. Thêm
   đủ 9 dòng D1–D9, nhập đúng **Mục tiêu** và **Trọng số** theo Phụ lục (tổng trọng số phải = 100%:
   20+10+15+15+10+10+5+5+10). Tuỳ chọn gắn **Bảng bậc** (D3) cho dòng D1.
8. 🖐️ Quay lại chức danh "Lập trình viên Beta" (bước 2) → gắn **Bộ KPI = "Developer Beta"** (mục
   21) — từ giờ Huy sẽ tự được áp đúng bộ này khi tạo phiếu ở Giai đoạn 3.
9. 🖐️ **Settings › KPI** → xác nhận ngưỡng xếp loại, điểm trần, biên độ điều chỉnh, và **Người duyệt
   mặc định = `admin`** đã có sẵn (mục 24) — không cần đổi, chỉ xác nhận trước khi Huy có phiếu đầu
   tiên.

> Đến đây hệ thống đã sẵn sàng cấu hình cho Developer Beta nhưng **chưa tính được điểm nào** — đúng
> ý "có dự án/task mới tính KPI được".

---

## Giai đoạn 2 — Dự án & dữ liệu công việc của Huy (⏱ ~12')

10. 🖐️ **Project** → tạo dự án **"Beta Sprint 1"**, gán `user_id` của dự án = Lâm (không bắt buộc
    cho Developer, chỉ cần nếu sau này mở rộng sang P1–P5 Team Lead/PM).
11. 🖐️ **Project › Cấu hình › Giai đoạn dự án** → mở stage "Hoàn thành" → bật **Folded** (mục 1)
    **ngay bây giờ**, trước khi có task nào chuyển Hoàn thành — quên bước này thì mọi chỉ số D1/D7
    sẽ sai mà không có cảnh báo.
12. 🖐️ Tạo task **"Build login API"**: Người phụ trách = Huy (mục 5), Loại task = *Feature* (mục
    11), Story point = 5 (mục 12), Mức ưu tiên = Medium (mục 3).
13. 🖐️ Tạo task **"Fix null pointer khi đăng nhập"**: Loại task = *Bug* (mục 11), Task gốc = "Build
    login API" (mục 13), **không** tick Lỗi production, Kết quả = *valid* (mục 14), Nguyên nhân =
    *code* (mục 15), Mức ưu tiên = **High** (mục 3 — để có dữ liệu cho D7).
14. 🖐️ Chuyển task Bug: Đang làm → **Yêu cầu chỉnh sửa** → Đang làm lại (để `review_reject_count` tự
    +1, mục 16, nguồn D5) → **Đã duyệt review** → **Hoàn thành** (mục 2) — kiểm tra
    `working_hours_close` tự có (mục 4), `date_end` tự ghi (mục 18), `days_late` tự cập nhật (mục
    19).
15. 🖐️ Đăng nhập `lam` → mở task Feature "Build login API", chuyển sang Hoàn thành, tick **"Có unit
    test"** (mục 17 — field này **chỉ nhóm Manager mới tick được**, Huy đăng nhập sẽ thấy ô bị khoá).
16. 🖐️ (Tuỳ chọn, D8) **Lịch** → tạo sự kiện loại **"Chia sẻ kiến thức"**, gán Huy tham dự (mục 9).
17. 🖐️ Trên danh sách task, thử các bộ lọc nhanh **Bug / Trễ hạn / Bị trả về** (mục 20) → xác nhận 2
    task của Huy hiện đúng ở từng bộ lọc tương ứng.
18. 🖐️ **KPI › Báo cáo › Kiểm tra chất lượng dữ liệu** (mục 33) → xác nhận Huy không còn cảnh báo
    thiếu dữ liệu nghiêm trọng trước khi sang Giai đoạn 3.

---

## Giai đoạn 3 — Kỳ đánh giá (⏱ ~3')

19. 🖐️ **KPI › Cấu hình › Kỳ đánh giá** → tạo kỳ **"Tháng hiện tại — Beta"**, Loại kỳ = *Tháng*
    (khớp Loại kỳ của Bộ KPI ở bước 7), ngày bắt đầu/kết thúc bao trùm lúc làm task ở Giai đoạn 2
    (mục 27).
20. 🖐️ **KPI › Đánh giá › Tạo phiếu cho kỳ** (mục 28) → chọn kỳ vừa tạo → hệ thống tạo đúng **1
    phiếu Nháp** cho Huy (nhờ chức danh đã gắn Bộ KPI ở bước 8) — nếu báo "không có nhân viên nào
    cần tạo" thì kiểm tra lại bước 8 hoặc bước 19.

---

## Giai đoạn 4 — Tính & duyệt phiếu của Huy (⏱ ~8')

21. 🖐️ (Tuỳ chọn, D6) Đăng nhập `huy` → mở phiếu Nháp → **Tự đánh giá**.
22. 🖐️ `lam` hoặc `admin` mở phiếu Huy → bấm **Tính KPI** (mục 29) → D1–D8 ra số thật (không còn 0
    hoàn toàn vì đã có 2 task), D9 còn trống (chờ nhập tay).
23. 🖐️ Nhập **D9 "Đánh giá của quản lý"** = 4/5.
24. 🖐️ (Tuỳ chọn) **Điều chỉnh điểm** +1, bắt buộc ghi lý do.
25. 🖐️ **Gửi duyệt** — nhắc việc **"Duyệt phiếu KPI"** tự giao cho `admin` (người duyệt mặc định ở
    Settings, bước 9): activity chỉ giao được cho đúng 1 người cố định nên không tự giao cho `lam`,
    nhưng `lam` vẫn tự vào phiếu và bấm Duyệt được bình thường (xem bước 26).
26. 🖐️ Đăng nhập `lam` → bấm **Duyệt** phiếu Huy → **thành công ngay**, không cần thêm quyền Admin
    (`lam` là quản lý trực tiếp của Huy — mục 30). Đây là điểm nhấn: quản lý trực tiếp tự quyết định
    được, Admin không còn là người duyệt chính mà chủ yếu lo cấu hình.
27. 🖐️ (Minh hoạ xung đột vai trò còn lại, mục 30/D11) Tạm gán thêm nhóm **KPI Administrator** cho
    user `huy` → đăng nhập `huy` → bấm **Mở lại** rồi thử **Duyệt** lại chính phiếu của mình → hệ
    thống **chặn** (không ai được tự duyệt/trả về/mở lại phiếu của chính mình, kể cả khi có quyền
    Admin). Xong phần minh hoạ thì bỏ lại nhóm Admin vừa gán cho `huy`, rồi đăng nhập `lam` (hoặc
    `admin`) **Duyệt** lại phiếu Huy cho đúng trạng thái Đã duyệt.
28. 🖐️ Sau khi Đã duyệt → nhắc việc **"Xác nhận kết quả"** tự giao cho Huy (D6) → đăng nhập `huy` →
    xác nhận.

> Mọi thao tác Gửi duyệt/Duyệt/Điều chỉnh ở Giai đoạn này đều tự ghi lại trên tab **Chatter** của
> phiếu (mục 10) — mở lại để xem đúng lịch sử các bước 24–27 theo thứ tự thời gian.

---

## Giai đoạn 5 — Theo dõi & xuất dữ liệu của Huy (⏱ ~5')

29. 🖐️ **KPI › Tổng quan** (D8) → phiếu của Huy xuất hiện đúng trạng thái "Đã duyệt".
30. 🖐️ **Dashboard** (mục 31) và **Báo cáo tổng hợp/chi tiết** (mục 32) → lọc theo phòng ban "R&D
    Beta" → chỉ thấy đúng 1 dòng của Huy.
31. 🖐️ Mở hồ sơ nhân viên Huy → bấm nút thông minh **"Phiếu KPI"** (mục 23) → thấy đúng 1 phiếu vừa
    duyệt.
32. 🖐️ Mở phiếu Huy → **In PDF** (mục 36) → xem nhanh file xuất ra có đủ D1–D9 và điểm cuối cùng.
33. 🖐️ (Verbal) **REST API** (mục 37) — nêu miệng cách gọi, không bắt buộc demo bằng Postman/curl.
34. ℹ️ **Gợi ý mục tiêu** (D7) cần ≥ 3 kỳ trước **đã duyệt** cùng loại kỳ — Huy vừa tạo mới chỉ có
    đúng 1 kỳ nên tính năng này **chưa đủ dữ liệu để demo thật** với vai trò Beta này; giải thích
    miệng cơ chế (dùng lịch sử điểm 3 kỳ gần nhất để đề xuất Mục tiêu mới) thay vì bấm nút thật.

> Muốn mở rộng tiếp sang vai trò khác (Tester, Sales...) thì lặp lại đúng Giai đoạn 0 + 1 này với
> tên mới — xem ví dụ "Sales" đã làm sẵn ở Phần 7 của `KICH_BAN_DEMO.md` (Giai đoạn 6 của
> `FLOW_VAN_HANH_TU_DAU_DEN_CUOI.md`).

---

## Phụ lục — Hành trình dữ liệu của 1 nghiệp vụ (task Bug ở bước 13–14)

Phần phụ lục này không đi theo thứ tự Giai đoạn 0→5 ở trên nữa, mà bám đúng **1 nghiệp vụ cụ thể** đã
tạo ở bước 13–14 — task Bug **"Fix null pointer khi đăng nhập"** — và chỉ thẳng ra nó rơi vào tử
số/mẫu số của những chỉ số nào, ra số bao nhiêu, rồi cuối cùng xuất hiện ở đâu trên phiếu/PDF. Mục
đích: chứng minh dữ liệu không "mất dấu" qua các tầng (task → dòng chỉ số → điểm cuối → báo cáo), và
trả lời được ngay nếu hội đồng hỏi "số này từ đâu ra". Làm nối tiếp ngay sau khi đã xong Giai đoạn 2
ở trên (đã có Huy, Lâm, dự án "Beta Sprint 1", task Feature "Build login API" 5 story point đã Hoàn
thành có unit test, và task Bug "Fix null pointer khi đăng nhập") — không cần dựng lại gì thêm.

### Nghiệp vụ được trace: task Bug "Fix null pointer khi đăng nhập"

6 field/trạng thái trên chính task này quyết định nó rơi vào đúng chỗ nào khi Tính KPI:

| Field / trạng thái trên task | Giá trị đã nhập | Quyết định điều gì |
|---|---|---|
| Loại task (`task_type`) | Bug | Không tính vào D1/D2/D6 (các chỉ số đó chỉ dành cho Feature) |
| Kết quả (`bug_resolution`) | valid | Nằm trong nhóm "bug tính KPI" (chỉ `valid`/`wont_fix` — mục 14) |
| Nguyên nhân (`bug_root_cause`) | code | Tính cho Developer (D3/D4); nếu chọn `requirement` thì bug này chuyển hẳn qua B2 của BA, không còn tính ở đây — mục 15 |
| Lỗi production (`is_production_bug`) | Không tick | Không rơi vào tử số của D4 |
| Mức ưu tiên (`priority`) | High | Đủ điều kiện vào D7 (chỉ tính bug High/Urgent) |
| Trạng thái đã đi qua | Đang làm → Yêu cầu chỉnh sửa → Đang làm → Đã duyệt review → Hoàn thành | `review_reject_count = 1` → KHÔNG được tính là "pass review lần đầu" ở D5 |

> **Lưu ý kỹ thuật dễ bị hỏi vặn:** D3/D4 quy bug về theo **task gốc** ("Build login API") — chính
> xác là theo `origin_task_id.user_ids` và `origin_task_id.date_end`, KHÔNG phải ngày Hoàn thành của
> chính task Bug. Nếu bug được sửa muộn hơn (ở kỳ sau), nó vẫn tính vào đúng kỳ mà task gốc Hoàn
> thành, không phải kỳ Bug được đóng. D5 thì ngược lại — tính theo chính ngày Hoàn thành của task
> Bug. Đọc đúng hàm `_counted_bugs()` so với `_done_tasks()` trong `models/kpi_engine.py` nếu cần
> trả lời chất vấn về điểm này.

### Bước 1 — Tính KPI, xem đúng các dòng chỉ số đổi theo task này

🖐️ Mở phiếu của Huy → bấm **Tính KPI** → mở từng dòng chỉ số sau, so khớp với bảng tính tay:

| Chỉ số | Công thức | Tử số / mẫu số từ đúng dữ liệu đã tạo | actual / volume | Mục tiêu | Nhận xét |
|---|---|---|---|---|---|
| D2 | Tổng story point hoàn thành trong kỳ | Chỉ từ task Feature (5 SP) — Bug không có story point | 5 / 5 | 20 | Chưa đạt mục tiêu (1 task) |
| D3 | Bug tính KPI / SP hoàn thành | 1 bug (đúng task này) / 5 SP | 0,2 / 5 | 0,3 (thấp là tốt) | Tốt — dưới mục tiêu |
| D4 | Bug production / Bug tính KPI × 100 | 0 bug production / 1 bug tính KPI | 0% / 1 | 5% (thấp là tốt) | Xuất sắc — không có bug lọt production |
| D5 | Task chưa từng bị trả về / Task đã qua review × 100 | 0 task pass thẳng / 1 task đã qua review (đúng task Bug này) | 0% / 1 | 80% (cao là tốt) | Kém — vì đã bị trả về đúng 1 lần |
| D7 | TB `working_hours_close` của bug High/Urgent | Đúng 1 bug (task này) | (số giờ thật lúc demo) / 1 | 24 giờ (thấp là tốt) | Số sẽ khác nhau tuỳ thời gian thao tác thật trong buổi demo — không có số cố định để so trước |

Bấm vào từng dòng để mở đúng danh sách bản ghi mà Engine đã đếm (domain filter áp dụng) — đây là
cách "truy ngược" nếu hội đồng nghi ngờ số sai.

### Bước 2 — Vào điểm cuối (`final_score`)

🖐️ Nhập D9 "Đánh giá của quản lý" = 4/5 (chỉ số nhập tay, không liên quan task này) → lưu → xem
**điểm cuối** (`final_score`) trên đầu phiếu. 4 trong 9 dòng chỉ số của Bộ "Developer Beta" — D3, D4,
D5, D7 (tổng **15% + 15% + 10% + 5% = 45% trọng số**) — đổi trực tiếp vì chính task Bug này; D2
(10%) đổi vì task Feature liên quan; D9 (10%) do quản lý chấm tay; D1 (20%), D6 (10%), D8 (5%) ra
"Không áp dụng" vì demo này chưa tạo deadline/sự kiện lịch.

**Điểm cuối là tổng hợp CẢ bộ, không phải chỉ từ 1 task** — nhưng đổi 1 field trên đúng task Bug này
(ví dụ tick lại **Lỗi production**) rồi bấm **Tính lại KPI** sẽ thấy ngay D4 nhảy từ 0% lên 100% và
điểm cuối đổi theo ngay lập tức — đây là phần nên bấm thử trực tiếp lúc demo để chứng minh dữ liệu
đi xuyên suốt thật, không phải số tĩnh gõ sẵn.

### Bước 3 — Lên báo cáo và PDF

🖐️ **In PDF** phiếu Huy (mục 36) → tìm đúng dòng D3/D4/D5/D7 trong file xuất ra, so khớp với bảng ở
Bước 1 — số phải giống hệt, không bị làm tròn khác đi.

🖐️ Mở **Dashboard** (mục 31) → lọc theo chỉ số D3 hoặc D4 → thấy đúng 1 dòng dữ liệu của Huy khớp
đúng số đã tính ở Bước 1.

### Bước 4 — Khép vòng với tracking (ai thay đổi, lúc nào)

🖐️ Mở tab **Chatter** của phiếu Huy (mục 10) → chỉ thẳng vào đúng các dòng log tương ứng với thao
tác vừa làm ở Bước 1–2 (ví dụ dòng "Điểm cuối: … → …" ngay sau khi Tính KPI) kèm tên người thao tác
thật và giờ phút chính xác — đây chính là bằng chứng cho đúng câu hỏi "tracking thay đổi trạng thái,
ai thay đổi, lúc nào" đã hỏi trước đó, áp trực tiếp vào đúng dữ liệu vừa trace ở trên thay vì nói
chung chung.

### Vì sao chọn đúng task Bug này để trace (không phải task khác)

Một task Bug đơn lẻ chạm đồng thời vào D3, D4, D5 và (nếu đủ mức ưu tiên) D7 — 4 chỉ số, 3 nhóm
("Chất lượng" D3/D4/D7, "Quy trình" D5) — là ví dụ gọn nhất nhưng vẫn đủ sức minh hoạ cả điểm mạnh
(D3, D4: không bug production, mật độ lỗi thấp) lẫn điểm yếu (D5: bị trả về 1 lần nên pass-rate
review = 0% trên khối lượng nhỏ) chỉ từ **một** nghiệp vụ, đồng thời đi qua đúng 2 cách quy kỳ khác
nhau (D3/D4 quy theo task gốc, D5 quy theo chính task Bug) — điểm hay bị hỏi vặn nhất khi chất vấn
về tính đúng đắn của Engine.

---

## Bảng đối chiếu với `FLOW_VAN_HANH_TU_DAU_DEN_CUOI.md`

| Giai đoạn | Bước trong file vận hành | Bước trong demo này |
|---|---|---|
| 0 | 1–4 | 1–5 |
| 1 | 5–8 | 6–9 |
| 2 | 9–17 | 10–18 |
| 3 | 18–19 | 19–20 |
| 4 | 20–28 | 21–28 |
| 5 | 29–33 | 29–34 |

Mọi mục/DX xuất hiện trong `FLOW_VAN_HANH_TU_DAU_DEN_CUOI.md` đều có ít nhất 1 bước thao tác tay
tương ứng ở trên, trừ các tính năng gắn với vai trò khác Developer (P1–P5, QA1–QA5, B1–B4, S1, F1) —
không thuộc phạm vi demo riêng cho Developer này.
