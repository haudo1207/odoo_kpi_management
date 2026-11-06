# Kịch bản demo — Project KPI & Performance Management

Mục tiêu: trình bày đầy đủ các điểm nổi bật trong ~17–20 phút, tốn ít thời gian thao tác tay nhất có
thể bằng cách tận dụng dữ liệu đã có sẵn (bản sao lưu `seeded`), chỉ làm tay những chỗ **cần chứng
minh hệ thống tính thật / chạy thật / xử lý thật**, không phải hiển thị số đã có sẵn.

## Ký hiệu dùng trong file này

- 🖐️ **Thao tác tay** — phải tự nhập/bấm trực tiếp lúc demo (đây là phần hội đồng thấy bạn "làm thật").
- 📂 **Dùng dữ liệu có sẵn** — đã nằm sẵn trong bản sao lưu `seeded`, chỉ cần mở ra xem và nói, **không**
  tạo lại từ đầu.
- ⏱️ Thời gian gợi ý cho từng phần.

## Chuẩn bị trước buổi demo (làm trước, KHÔNG tính vào thời gian trình bày)

1. Khôi phục từ bản sao lưu **`seeded`** (không dùng `clean`) — vì `seeded` đã có sẵn 8 phiếu ở nhiều
   trạng thái khác nhau, kỳ năng lực và kỳ phản hồi 360 có lời mời chưa trả lời. Dùng `seeded` giúp
   bỏ qua hầu hết công đoạn "tạo phiếu, tính KPI, gửi duyệt" cho từng nhân viên mẫu — đỡ tốn thời
   gian nhất so với bắt đầu từ `clean`.

   ```bash
   bash addons/project_kpi_management/scripts/restore_defense.sh seeded
   ```

2. Script tự chạy `prepare_defense.sh` sau khi khôi phục — chờ dòng `KẾT QUẢ: tất cả OK — có thể
   demo.` mới tiếp tục.

3. 🖐️ **Trước khi trình bày thật, tự dạo một lượt (tổng duyệt) qua toàn bộ các màn hình ở Phần 5 bên
   dưới** để biết chính xác trạng thái hiện tại của từng phiếu trong `seeded` (phiếu nào đã Đã duyệt,
   phiếu nào còn Nháp...), và xác nhận còn phiếu nào ở trạng thái Nháp dùng bộ "Developer (có phản
   hồi 360)" chưa mời đủ 3 người — để dùng cho Phần 4. Số điểm liệt kê trong file này là số đã tính
   tay sẵn theo kịch bản dữ liệu mẫu gốc nên đúng, nhưng **trạng thái quy trình** (Nháp/Gửi
   duyệt/Đã duyệt) của từng phiếu có thể đã đổi nếu bạn từng thao tác thêm sau khi khôi phục — đi một
   lượt trước để không bị bất ngờ trên sân khấu.

4. Kiểm tra sẵn **Thiết lập › Quy trình** có "Người duyệt mặc định" = `admin` (dùng cho Phần 6), và
   phiếu của An ở trạng thái đã tính KPI (để Phần 6 xuất PDF ngay không cần tính lại).

5. Mở sẵn 2–3 tab trình duyệt: một đăng nhập `admin`, các tab còn lại ẩn danh/cửa sổ khác để đăng
   nhập nhanh các vai trò còn lại (`quocviet`, `phuc`, `an`, `binh`, `chi`, `ha`, `dung`, `khoa`,
   `lan`...). Mật khẩu trùng tên đăng nhập.

## Danh sách tài khoản dùng khi demo

| Đăng nhập | Vai trò | Dùng để |
|---|---|---|
| `admin` | KPI Administrator | Cấu hình, Tổng quan, Báo cáo, Settings, tạo chỉ số mới, tạo phiếu hàng loạt |
| `quocviet` | KPI Manager (quản lý An, Bình, Chi, Phúc, Lan) | Bị chặn khi duyệt phiếu nhân viên mình quản lý dù được gán thêm quyền Admin; nhận nhắc việc "Duyệt phiếu KPI" |
| `phuc` | KPI Manager / PM (quản lý Dung, Khoa, Hà) | Bộ Team Lead/PM, nhận nhắc việc "Hoàn tất phiếu" của Dung/Khoa/Hà |
| `an`, `binh`, `chi`, `ha` | Developer | Xem phiếu, Tự đánh giá, Xác nhận kết quả, trả lời khảo sát 360 khi được mời |
| `dung`, `khoa` | Tester/QA (Khoa thiếu dữ liệu) | Bộ Tester tự động |
| `lan` | BA | Bộ Business Analyst |

---

## Phần 1 — Mở đầu: Tổng quan hệ thống (⏱ 1 phút) — 📂 dùng dữ liệu có sẵn

🖐️ Đăng nhập `admin` → vào thẳng **KPI › Tổng quan** (menu đầu tiên của app).

📂 Thẻ kỳ mẫu đã có đủ số (Nháp/Đã gửi/Đã duyệt/Cần cải thiện/Thiếu dữ liệu/Chờ xác nhận) — không
cần tạo gì, chỉ nói: đây là bức tranh tổng của một kỳ, mỗi con số bấm vào mở đúng danh sách phiếu
tương ứng (record rule tự áp dụng, quản lý khác sẽ thấy số khác admin).

🖐️ Bấm thử vào số **"Cần cải thiện"** để mở đúng danh sách phiếu đó — đây là nơi bạn sẽ quay lại ở
Phần 2.

## Phần 2 — Luồng chính: engine tính thật + quy trình duyệt có nhắc việc (⏱ 6 phút) — 🖐️ thao tác tay là chính

Đây là phần **bắt buộc làm trực tiếp**, gộp cả việc chứng minh con số tính từ dữ liệu task/bug thật
lẫn toàn bộ vòng đời một phiếu: Nháp → Tự đánh giá → Gửi duyệt → Nhắc việc → Chặn xung đột → Duyệt →
Nhắc việc xác nhận → Xác nhận kết quả.

1. 🖐️ Vẫn ở `admin`: **KPI › Đánh giá › Tạo phiếu cho kỳ** → chọn kỳ mẫu. Nếu wizard báo "không có
   nhân viên nào cần tạo phiếu" (vì tác vụ cuối kỳ hoặc `seeded` đã tạo sẵn), nói ngay đó chính là tác
   vụ tự động đã chạy, rồi đi tiếp sang bước 2 — không cần cố tạo lại.
2. 📂/🖐️ Mở phiếu của **An** → bấm **Tính KPI** (nếu đã tính sẵn thì chỉ cần mở xem, không bấm lại) →
   kết quả **113,31 — Xuất sắc**. Giải thích nhanh: điểm này cộng từ 9 chỉ số D1–D9, mỗi dòng có thể
   bấm vào xem công thức/nguồn dữ liệu (task, bug cụ thể).
3. 🖐️ Mở phiếu của **Bình** → Tính KPI → **73,90 — Cần cải thiện**.
4. 🖐️ **Tự đánh giá:** đăng nhập `binh` → mở phiếu của mình (đang Nháp) → bấm **Tự đánh giá** → nhập
   điểm tự chấm cho D9 + một dòng nhận xét ngắn → lưu. Nói rõ: đây chỉ để tham khảo, không thay thế
   điểm quản lý chấm chính thức.
5. 🖐️ Quay lại `admin` (hoặc `quocviet`) → nhập điều chỉnh `+2` kèm lý do ở ô `adjustment_note`
   (bắt buộc) → lưu → **Gửi duyệt**.
6. 🖐️ Mở chuông **Hoạt động** (activity) của `admin` → chỉ ra nhắc việc **"Duyệt phiếu KPI"** vừa
   được hệ thống tự giao cho người duyệt mặc định khi phiếu chuyển sang Gửi duyệt (activity chỉ giao
   được cho đúng 1 người cố định nên không tự giao cho `quocviet`, dù `quocviet` là quản lý trực
   tiếp của Bình).
7. 🖐️ Đăng nhập `quocviet` (quản lý trực tiếp của Bình, nhóm KPI Manager — **không cần** thêm quyền
   Admin) → bấm **Duyệt** phiếu của Bình → **thành công ngay**. Đây là điểm nhấn: quản lý trực tiếp
   tự quyết định được phiếu đội mình, Admin không còn là người duyệt chính mà chủ yếu lo cấu hình.
8. 🖐️ (Minh hoạ xung đột vai trò còn lại) Tạm gán thêm quyền **KPI Administrator** cho `binh` →
   đăng nhập `binh` → thử bấm **Mở lại** chính phiếu của mình → hệ thống **chặn** (không ai được tự
   duyệt/trả về/mở lại phiếu của chính mình, kể cả có quyền Admin). Bỏ lại quyền Admin vừa gán cho
   `binh` ngay sau khi minh hoạ xong.
9. 🖐️ **Xác nhận kết quả:** đăng nhập `binh` → chuông Hoạt động hiện nhắc việc mới **"Xác nhận kết
   quả KPI"** (tự sinh ngay khi phiếu chuyển sang Đã duyệt) → bấm **Xác nhận kết quả** (đồng ý). Nói
   rõ: xác nhận không đổi điểm, chỉ ghi nhận nhân viên đã biết kết quả.
10. 🖐️ Quay lại `admin` → **Tổng quan**, bấm số "Cần cải thiện" đã tăng thêm 1.

## Phần 3 — Mở rộng không cần sửa code (⏱ 3 phút) — 🖐️ thao tác tay là chính

Phần này **phải làm tay toàn bộ** vì đang chứng minh năng lực cấu hình, không phải xem lại cái đã có.

1. 🖐️ `admin` → **KPI › Cấu hình › Chỉ số KPI** → Tạo mới: Cách tính = *"Tự động (cấu hình)"*, model
   `project.task`, người = `user_ids`, ngày = `date_end`, Đếm, domain
   `[('state', '=', '1_done')]`.
2. 🖐️ Bấm nút **"Thử tính"** ngay trên form, chọn An và kỳ mẫu → ra kết quả `7` ngay lập tức, không
   cần lưu phiếu thật. Nhấn mạnh: domain đọc bằng `ast.literal_eval`, không chạy được mã tuỳ ý — an
   toàn hơn cho phép nhập code tuỳ ý qua giao diện.

## Phần 4 — Phản hồi 360 độ trực tiếp (⏱ 2 phút) — 🖐️ thao tác tay là chính

Phần này làm tay để hội đồng thấy luồng mời/trả lời thật, không chỉ xem điểm đã có sẵn.

1. 🖐️ `admin`/`quocviet` → mở phiếu Nháp của **Chi**, kỳ **"Tháng 10/2026 (mẫu phản hồi 360)"**, bộ
   "Developer (có phản hồi 360)" (phiếu này tự có khi nạp kịch bản mẫu, chưa mời ai — không cần tạo
   tay; nếu `seeded` không còn đúng trạng thái, tạo nhanh 1 phiếu mới cho `chi`/`ha` ở kỳ mẫu, chọn
   đúng bộ này) → bấm **Mời đánh giá 360** → chọn 3 người được mời (ví dụ `an`, `binh`, `dung`).
2. 🖐️ Đăng nhập 1 trong 3 người được mời → chuông Hoạt động hiện nhắc việc **"Đánh giá 360"** kèm
   link → bấm vào, trả lời khảo sát ngắn (vài câu) → gửi. Nhắc việc tự đánh dấu xong.
3. 🖐️ Quay lại phiếu (`admin`/`quocviet`) → số người đã trả lời tăng lên 1/3. Nói rõ: dưới 3 người
   trả lời thì điểm F1 vẫn hiện **"Không áp dụng"**, và quản lý **không** xem được câu trả lời của
   từng người riêng lẻ — ngưỡng 3 người là để giữ ẩn danh.

## Phần 5 — Các bộ KPI mở rộng khác (⏱ 3 phút) — 📂 chủ yếu dùng dữ liệu có sẵn, chỉ xem và kể lại

Toàn bộ mục này chỉ cần **mở phiếu đã có sẵn trong `seeded` và đọc số**, không tạo lại — tiết kiệm
phần lớn thời gian so với làm tay từng cái. Nếu một phiếu nào đó trong `seeded` chưa đúng trạng thái
khi bạn tổng duyệt (bước chuẩn bị 3), chỉ cần bấm Tính KPI/Gửi duyệt cho đúng thực trạng, không cần
nhập lại dữ liệu nguồn.

| Bộ KPI | Nhân viên mẫu | Số liệu đã tính sẵn (theo kịch bản dữ liệu mẫu gốc) | Điều cần nói |
|---|---|---|---|
| Tester (QA1–QA5) | `dung` | **55,875 điểm — Cần cải thiện** → duyệt phiếu này tự tạo đúng 1 nhắc việc PIP cho `phuc` | QA1–QA3 không có một dòng code nào, chỉ là dữ liệu cấu hình |
| Team Lead/PM (P1–P5), phụ thuộc P2 | `phuc` | P2 "Không áp dụng" **trước khi** Dung/Khoa/Hà gửi duyệt → sau khi cả ba gửi duyệt, P2 = 79,01 trên 2 phiếu (Khoa thiếu dữ liệu bị loại), điểm Phúc = **84,86** | Không cần sắp thứ tự tạo phiếu; phiếu thiếu dữ liệu của nhân viên mới (Khoa) không kéo điểm quản lý xuống |
| Business Analyst (B1–B4) | `lan` | **75,828 điểm** — B2 tính đúng 1 bug "yêu cầu sai" quy về BA, không tính cho Developer | Một bug, hai trách nhiệm: phân loại nguyên nhân 1 lần, hệ thống tự quy đúng người |
| Developer (có năng lực, S1) | `an` | S1 = 66,67% (Python 100 ≥ 75, Odoo 50 ≥ 50, SQL 25 < 50 — 2/3 đạt), kỳ "Tháng 10/2026 (mẫu năng lực)" | So kỹ năng với chức danh đã **chụp trên phiếu**, không đổi theo chức danh hiện tại |
| Chấm theo bậc | Đặng Gia Khánh (nhân viên mẫu riêng cho mục này), bộ "Developer (chấm theo bậc, mẫu)" | D2: 17/20 SP = 85% đạt mục tiêu → bảng bậc "Bậc 4 mức (mẫu)" cho **75 điểm** (tuyến tính sẽ ra 85) | Phiếu cũ không đổi điểm khi sửa bảng bậc sau đó (đã chụp JSON lúc tạo) |
| Gợi ý mục tiêu từ lịch sử | Phòng "Phòng Kỹ thuật (lịch sử mẫu)", chỉ số D2 | Dễ 13,5 / Vừa 15 / Khó 16,5 (phân vị 25/50/75 của 4 kỳ đã duyệt) | Chỉ là gợi ý, quản lý vẫn sửa tay được |

🖐️ Với mỗi dòng ở bảng trên: chỉ cần **mở đúng phiếu/màn hình tương ứng và trỏ chuột giải thích**,
không bấm Tính KPI lại nếu số đã đúng sẵn.

## Phần 6 — Báo cáo, in PDF và cấu hình hệ thống (⏱ 2 phút) — 📂 chủ yếu, 🖐️ 1 thao tác xuất PDF

1. 📂 `admin` → **KPI › Báo cáo** → lướt nhanh qua từng màn hình, mỗi màn hình chỉ nói 1 câu: Xu
   hướng điểm theo kỳ, Phân bố xếp loại, Phân tích theo chỉ số, Theo phòng ban, Kiểm tra chất lượng
   dữ liệu — toàn bộ dùng dữ liệu `seeded`, không cần nhập gì thêm.
2. 🖐️ Mở phiếu của **An** (đã tính KPI sẵn) → bấm nút **In** → xuất PDF → mở nhanh file xem qua. Đây
   là minh chứng phiếu có thể lưu trữ/ký tay ngoài hệ thống.
3. 📂 `admin` → **KPI › Cấu hình › Thiết lập** → trỏ chuột qua các trường: ngưỡng xếp loại, điểm
   trần, biên độ điều chỉnh, **Người duyệt mặc định** → nói: toàn bộ chỉnh qua giao diện, không sửa
   code, không cần restart module.
4. (Chỉ nếu hội đồng hỏi) **REST API**: nói bằng lời — có xác thực, dùng để công cụ ngoài (CI, quản
   lý test) đọc/ghi dữ liệu phiếu; dẫn chứng là bộ test `test_kpi_integration.py` — không cần demo
   trực tiếp bằng Postman/curl trừ khi được hỏi kỹ và còn thời gian.

## Phần 7 — (Nếu còn thời gian) Minh hoạ mở rộng vai trò hoàn toàn mới (⏱ 3 phút) — 🖐️ thao tác tay toàn bộ

Đây là màn kết hiệu quả nhất nếu còn dư thời gian — dựng một vai trò **"Sales" chưa từng tồn tại**
ngay trên sân khấu, chứng minh nguyên tắc không hardcode vai trò:

1. 🖐️ **Nhân viên › Phòng ban** — tạo "Phòng Kinh doanh".
2. 🖐️ **KPI › Cấu hình › Chỉ số KPI** — tạo "S1 — Doanh số đạt được", Cách tính = *Nhập tay*.
3. 🖐️ **KPI › Cấu hình › Bộ KPI** — tạo bộ "Sales": dòng S1 (trọng số 80) + D9 có sẵn (trọng số 20).
4. 🖐️ **Nhân viên › Cấu hình › Vị trí công việc** — tạo chức danh "Nhân viên kinh doanh", chọn Bộ
   KPI = Sales.
5. 🖐️ Tạo một nhân viên mới gắn chức danh đó.
6. 🖐️ **KPI › Đánh giá › Tạo phiếu cho kỳ** — hệ thống tự nhận ra nhân viên này, không cần sửa file
   hay restart module.
7. 🖐️ Nhập S1 và D9 → Tính KPI → Gửi duyệt.

## Phần 8 — Dự phòng nếu demo lỗi giữa chừng

- Nếu một thao tác bị lỗi/màn hình treo: không cố sửa trên sân khấu — nói "để đảm bảo đúng dữ liệu
  đã kiểm chứng, mình khôi phục lại bản sao lưu sạch" rồi chạy lại `restore_defense.sh seeded`
  (mất khoảng vài chục giây) và tiếp tục từ phần đang dở.
- Luôn có backup `clean` dự phòng nếu `seeded` bị thao tác nhầm trong lúc tổng duyệt và không còn
  đúng kịch bản — `backup_defense.sh`/`restore_defense.sh` thao tác giống nhau cho cả hai bản.
- Nếu Phần 4 (mời 360) không còn phiếu Nháp phù hợp và không kịp tạo mới: bỏ qua, chuyển thẳng sang
  dòng 360 trong bảng Phần 5 (xem kết quả có sẵn) thay vì làm trực tiếp.

## Checklist thời gian tổng (ước lượng ~17–20 phút nếu đủ cả 7 phần)

| Phần | Thời gian | Bắt buộc? |
|---|---|---|
| 1. Tổng quan | 1' | Bắt buộc |
| 2. Luồng Developer + nhắc việc + xác nhận | 6' | Bắt buộc |
| 3. Chỉ số cấu hình không cần code | 3' | Bắt buộc |
| 4. Phản hồi 360 trực tiếp | 2' | Bắt buộc |
| 5. Các bộ KPI mở rộng (xem nhanh) | 3' | Bắt buộc |
| 6. Báo cáo, PDF, cấu hình hệ thống | 2' | Bắt buộc |
| 7. Dựng vai trò Sales hoàn toàn mới | 3' | Nếu còn thời gian / hội đồng muốn xem thêm |
