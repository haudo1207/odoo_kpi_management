# Flow vận hành hệ thống từ đầu đến cuối (thứ tự phụ thuộc)

Khác với 3 file đã có (`KICH_BAN_DEMO.md` trình diễn, `FLOW_TU_KIEM_CHUNG_TRUOC_BAO_VE.md` kiểm hành
vi, `FLOW_KIEM_CHUNG_LOGIC_TAT_CA_TINH_NANG.md` đọc code) — file này trả lời câu hỏi **"làm cái này
trước, mới làm được cái kia"**: đúng kiểu "có dự án mới có task, có task mới tính KPI được". Đi từ hệ
thống hoàn toàn trống đến khi có 1 phiếu KPI tính xong và duyệt xong, theo đúng thứ tự bắt buộc — làm
sai thứ tự thì bước sau sẽ không làm được hoặc ra sai số. Số trong ngoặc `(mục X)` / `(DX)` tham
chiếu đúng mục trong `HUONG_DAN_SU_DUNG.md` để tra cách dùng chi tiết.

## Sơ đồ tổng quan

```
Giai đoạn 0        Giai đoạn 1          Giai đoạn 2           Giai đoạn 3      Giai đoạn 4            Giai đoạn 5
Tổ chức & nhân sự → Cấu hình KPI       → Dự án & dữ liệu task → Kỳ đánh giá   → Tính & duyệt phiếu   → Theo dõi/xuất
(phòng ban,          (chỉ số, bộ KPI,     (BẮT BUỘC có trước     (phiếu chỉ      (Engine CHỈ đọc được    (chỉ có dữ
 chức danh,           gắn chức danh,       khi tính KPI —         tạo được        nếu Giai đoạn 2 đã      liệu SAU
 nhân viên,           Settings)            thiếu thì "Thiếu       sau khi có      đủ, không thì ra         khi có
 nhóm quyền)                               dữ liệu"/sai số)       Bộ KPI +        "Thiếu dữ liệu")         phiếu Đã
                                                                  nhân viên                                 duyệt)
```

Mỗi giai đoạn **phải xong trước** mới sang giai đoạn kế — không phải tuỳ chọn thứ tự.

---

## Giai đoạn 0 — Tổ chức & nhân sự (nền tảng, làm trước tất cả)

1. **Tạo phòng ban** (Nhân viên › Phòng ban) — cần có trước khi gán nhân viên và trước khi dùng mục
   tiêu riêng theo phòng ban (D7).
2. **Tạo chức danh** (mục 8) — chưa gắn Bộ KPI vội, vì Bộ KPI chưa tồn tại ở bước này.
3. **Tạo nhân viên** (mục 7): gán **Người dùng liên quan** (`user_id`) và **Quản lý trực tiếp**
   (`parent_id`) — thiếu 2 field này thì Engine không đọc được task của người đó (`test_employee_
   without_user`) và hệ thống không biết ai duyệt.
4. **Gán nhóm quyền KPI** cho từng user (Nhân viên / KPI Manager / KPI Administrator) (mục 30) —
   quản lý trực tiếp ở bước 3 nên thuộc nhóm KPI Manager, nếu không nhắc việc duyệt sẽ tự chuyển
   sang người duyệt mặc định (xem Giai đoạn 1, bước 8) thay vì đúng quản lý. Nhóm KPI Manager tự kế thừa
   quyền Project Manager có sẵn của Odoo (mục 22) nên không cần gán thêm quyền Project riêng.

---

## Giai đoạn 1 — Cấu hình KPI (trước khi có dữ liệu task, vì cần Bộ KPI để gắn vào chức danh)

5. **Tạo Chỉ số KPI** (mục 25) — nếu dùng *Tự động (cấu hình)*, bấm "Thử tính" ngay để chắc domain
   đúng trước khi gắn vào bộ (đỡ phải sửa lại bộ sau).
6. **Tạo Bộ KPI** (mục 26) — thêm dòng chỉ số, Mục tiêu, Trọng số (tổng = 100). Tuỳ chọn gắn thêm
   **Bảng bậc** (ví dụ áp cho dòng D2 trong kịch bản demo) cho từng dòng, và loại kỳ (tháng/sprint/quý, D7) cho cả bộ.
7. **Gắn Bộ KPI vào Chức danh** (mục 21, quay lại bước 2) — từ giờ nhân viên giữ chức danh này sẽ tự
   được áp đúng bộ KPI khi tạo phiếu ở Giai đoạn 3. Ví dụ có sẵn: Bộ KPI Tester tự động
   (mục 34, trùng D2) đã gắn sẵn vào chức danh "Kiểm thử phần mềm (QA)" — không cần tạo lại, chỉ
   cần gán chức danh này cho nhân viên Tester.
8. **Cấu hình Settings** (mục 24): ngưỡng xếp loại, điểm trần, biên độ điều chỉnh, và **Người duyệt
   mặc định** (phải là KPI Admin) — làm trước khi có phiếu đầu tiên, vì nhắc việc Gửi duyệt ở Giai
   đoạn 4 cần giá trị này ngay.

> Đến đây hệ thống đã sẵn sàng về mặt **cấu hình**, nhưng **chưa tính được điểm nào** vì chưa có dữ
> liệu task/bug/lịch — đây chính là ý "có dự án/task mới tính KPI được".

---

## Giai đoạn 2 — Dự án & dữ liệu công việc (bắt buộc có trước khi tính KPI)

9. **Tạo dự án** (Project app) — gán `user_id` của dự án nếu dùng bộ Team Lead/PM (P1, P3 xác định
   "dự án của Lead" theo field này, cũng là nguồn P4 nếu dùng thêm giờ làm).
10. **Cấu hình stage "Done"/"Hoàn thành" = Folded** (mục 1) — **bắt buộc làm ngay khi tạo dự án**,
    trước khi có task nào chuyển Done. Quên bước này thì D1 và D7 sẽ sai mà không có cảnh báo, và
    phải sửa lại từng task cũ sau đó rất mất công.
11. **Tạo task**, gán Người phụ trách (mục 5), Loại task = Feature/Bug (mục 11), Story point nếu là
    Feature (mục 12), tổ chức task cha/milestone/nhãn nếu cần (mục 6). Đặt **Mức ưu tiên** thực tế
    (mục 3) — D7 chỉ lọc bug mức High/Urgent khi tính thời gian sửa bug nghiêm trọng. Chuyển
    **Trạng thái task** (mục 2: Đang làm → Yêu cầu chỉnh sửa → Đã duyệt review → Hoàn thành) đúng
    luồng review — đây là nguồn cho D5 (tỷ lệ pass review lần đầu).
12. **Với task loại Bug**: gán Task gốc + Lỗi production (mục 13), Kết quả xử lý (mục 14), Nguyên
    nhân (mục 15) — 3 field này quyết định bug có tính vào D3/D4 (Developer) hay B2 (BA, D5) hay
    không tính gì cả (duplicate/invalid).
13. **Khi task chuyển sang Hoàn thành**: đánh dấu Có unit test nếu là Manager (mục 17, D6 cần);
    `date_end` tự ghi (mục 18), `days_late` tự cập nhật (mục 19); nếu từng bị trả về thì
    `review_reject_count` đã tự tăng từ trước (mục 16, D5 cần). Thời gian xử lý `working_hours_close`
    cũng tự tính theo lịch làm việc khi task đóng (mục 4), là nguồn tính D7 (thời gian sửa bug
    nghiêm trọng).
14. **(Chỉ nếu dùng bộ BA, B2)** đổi loại task thành Yêu cầu, task Feature gán `requirement_id` trỏ
    về Yêu cầu đó.
15. **(Chỉ nếu dùng bộ Team Lead/PM, D4)** tạo milestone có deadline cho dự án.
16. **(Chỉ nếu dùng bộ Developer có năng lực, S1)** cập nhật tab Kỹ năng trên hồ sơ nhân viên
    **trước** khi tạo phiếu ở Giai đoạn 3 — vì S1 chụp kỹ năng tại ngày cuối kỳ.
17. **(Nếu có buổi chia sẻ kiến thức, mục 9)** tạo sự kiện Lịch, gán đúng loại "Chia sẻ kiến thức".

> Thiếu bất kỳ bước nào ở Giai đoạn 2 không làm hệ thống báo lỗi — chỉ làm chỉ số liên quan ra
> "Không áp dụng" hoặc tính sai âm thầm. Dùng **KPI › Báo cáo › Kiểm tra chất lượng dữ liệu** (mục
> 33) để rà trước khi sang Giai đoạn 3. Có thể rà song song bằng các bộ lọc
> nhanh trên danh sách task (mục 20: Bug, Lỗi production, Trễ hạn, Bị trả về, Bug chưa phân loại).

---

## Giai đoạn 3 — Kỳ đánh giá (chỉ tạo được phiếu sau khi có Bộ KPI + nhân viên + kỳ)

18. **Tạo Kỳ đánh giá** (mục 27): chọn loại kỳ khớp với loại kỳ của Bộ KPI (bước 6) — khác loại kỳ
    thì wizard ở bước kế sẽ không tạo phiếu cho nhân viên đó.
19. **Tạo phiếu đánh giá**: dùng wizard "Tạo phiếu cho kỳ" (mục 28) ngay, hoặc để tác vụ nền tự tạo
    khi kỳ kết thúc (mục 35) — cả hai cách đều chỉ tạo được phiếu cho nhân viên có chức danh đã gắn
    Bộ KPI cùng loại kỳ (bước 7, 18).

---

## Giai đoạn 4 — Tính & duyệt phiếu (Engine chỉ đọc đúng nếu Giai đoạn 2 đã đủ dữ liệu)

20. **(Tuỳ chọn)** Nhân viên **Tự đánh giá** trong khi phiếu còn Nháp (D6).
21. Quản lý bấm **Tính KPI** (mục 29) — Engine đọc đúng dữ liệu task/bug/lịch đã chuẩn bị ở Giai
    đoạn 2; nếu Giai đoạn 2 thiếu, dòng chỉ số tương ứng ra "Không áp dụng".
22. Chấm chỉ số **nhập tay** (D9/QA5/P5/B4 tuỳ bộ) — phiếu không gửi duyệt được nếu còn thiếu chỉ số
    nhập tay nào.
23. Nếu phiếu **Thiếu dữ liệu** (`insufficient_data`, trọng số áp dụng < 50%) → bắt buộc chọn **Xếp
    loại thủ công** mới gửi duyệt được.
24. **Điều chỉnh điểm** nếu cần — bắt buộc ghi lý do khi khác 0.
25. **(Chỉ nếu bộ có F1)** Mời đánh giá 360 (D9) — phải làm khi phiếu **còn Nháp**, không mời được
    sau khi đã Gửi duyệt.
26. **Gửi duyệt** → nhắc việc "Duyệt phiếu KPI" tự giao cho **người duyệt mặc định** (Settings,
    Giai đoạn 1 bước 9) — activity chỉ giao được cho đúng 1 người cố định nên không tự giao cho
    quản lý trực tiếp, nhưng quản lý trực tiếp **vẫn tự vào phiếu và bấm Duyệt được bình thường**
    (xem bước 27) dù không nhận nhắc việc.
27. **Quản lý trực tiếp** (nhóm KPI Manager, không cần thêm quyền Admin) **hoặc** người duyệt mặc
    định (KPI Administrator) bấm **Duyệt** / **Trả về** (ghi lý do, về lại bước 21) / **Mở lại** (ghi
    lý do) — quản lý trực tiếp tự làm được với đúng nhân viên mình quản lý; hệ thống chỉ còn chặn
    đúng 1 trường hợp: không ai được tự duyệt/trả về/mở lại phiếu của **chính mình**, kể cả khi có
    thêm quyền Admin (mục 30, D11). Mọi thao tác này đều tự ghi lại trên tab Chatter của phiếu (mục
    10) để tra lịch sử sau này.
28. Sau khi **Đã duyệt** → nhắc việc tự giao cho nhân viên **Xác nhận kết quả** (D6).

---

## Giai đoạn 5 — Theo dõi & xuất (chỉ có dữ liệu sau khi có phiếu Đã duyệt)

29. Xem **KPI › Tổng quan** (D8) — số liệu chỉ đầy đủ sau khi có phiếu ở nhiều trạng thái.
30. Xem **Dashboard** (mục 31), **Báo cáo tổng hợp/chi tiết** (mục 32). Ngoài ra có thể xem nhanh lịch sử phiếu
    của từng người qua nút thông minh **"Phiếu KPI"** trên hồ sơ nhân viên (mục 23).
31. **In PDF** phiếu (mục 36) — nên là phiếu đã Tính KPI; hệ thống không chặn in phiếu chưa tính,
    chỉ là PDF sẽ ra điểm 0/rỗng chứ không có cảnh báo.
32. Gọi **REST API** (mục 37) để đọc/ghi từ công cụ ngoài.
33. Dùng lịch sử các kỳ đã duyệt để **gợi ý mục tiêu** (D7) cho kỳ sau — quay lại Giai đoạn 1 bước 6
    để áp mục tiêu mới trước khi mở kỳ kế tiếp.

---

## Giai đoạn 6 — Mở rộng sang vai trò mới (lặp lại Giai đoạn 0 + 1 cho vai trò đó)

34. Tạo phòng ban mới (Giai đoạn 0 bước 1) → chỉ số mới (Giai đoạn 1 bước 5) → Bộ KPI mới (bước 6)
    → chức danh mới (Giai đoạn 0 bước 2, Giai đoạn 1 bước 7) → nhân viên mới (Giai đoạn 0 bước 3) →
    từ đây đi lại đúng Giai đoạn 2 → 3 → 4 như bình thường, không cần sửa file hay restart module.

---

## Bảng tra nhanh: bước nào phụ thuộc bước nào

| Muốn làm | Phải có trước |
|---|---|
| Gắn Bộ KPI vào chức danh (bước 7) | Bộ KPI đã tạo (bước 6), Chức danh đã tạo (bước 2) |
| Task tính được vào D1/D7 đúng | Stage Done đã bật Folded (bước 10) **trước khi** task chuyển Done |
| Tạo phiếu đánh giá (bước 19) | Nhân viên có chức danh gắn Bộ KPI cùng loại kỳ (bước 7, 18) |
| Tính KPI ra đúng số (bước 21) | Dữ liệu task/bug/lịch của Giai đoạn 2 đã đủ và đúng |
| Gửi duyệt (bước 26) | Đã Tính KPI + đủ chỉ số nhập tay + (nếu thiếu dữ liệu) đã chọn xếp loại tay |
| Duyệt thành công (bước 27) | Người duyệt là KPI Administrator, hoặc đúng quản lý trực tiếp của nhân viên trên phiếu — và không phải chính nhân viên đó |
| Mời đánh giá 360 (bước 25) | Phiếu còn ở trạng thái Nháp |
| Gợi ý mục tiêu (bước 33) | Có ≥ 3 kỳ trước đã **Đã duyệt**, cùng loại kỳ |
| In PDF / gọi REST API (bước 31, 32) | Nên đã qua Tính KPI (có `final_score`) — không bị hệ thống chặn nếu chưa, nhưng kết quả trả về sẽ là 0/rỗng |
