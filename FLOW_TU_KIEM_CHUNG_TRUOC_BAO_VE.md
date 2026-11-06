# Flow tự tổng duyệt / kiểm chứng toàn bộ tính năng (trước buổi bảo vệ)

Đây **không phải** kịch bản trình diễn trên sân khấu (xem `KICH_BAN_DEMO.md` cho việc đó) — đây là
flow để **bạn tự đi qua lần lượt cả 48 mục** trong `HUONG_DAN_SU_DUNG.md` (37 mục sheet "danh sách
tính năng" + 11 mục sheet "Mở rộng sau Chương 9"), tự tay bấm và xác nhận từng tính năng chạy đúng
trước ngày bảo vệ. Không giới hạn thời gian, làm kỹ hơn là nhanh.

## Trước khi bắt đầu

1. Hai lớp kiểm tra tự động đã có — chạy trước, đỡ phải tự kiểm tay những phần này:
   ```bash
   bash addons/project_kpi_management/scripts/run_all_tests.sh        # 208 unit test
   bash addons/project_kpi_management/scripts/prepare_defense.sh kpi_defense   # 23 mục qua tài khoản thật
   ```
   Phải thấy `TẤT CẢ TEST ĐẠT` và `KẾT QUẢ: tất cả OK — có thể demo.`
2. Flow này **bổ sung** cho 2 lớp trên — tập trung vào những phần script không chạm tới: dữ liệu nền
   Odoo gốc (Phần A/B), các màn hình giao diện (báo cáo, Settings, PDF, REST API), và đi lại bằng
   mắt những phần script chỉ kiểm tra số liệu qua API chứ chưa chắc bạn đã tự thấy trên UI.
3. Dùng bản sao lưu **`seeded`** cho các mục chỉ cần **mở ra xem số có sẵn** (ghi "📂 xem seeded" bên
   dưới); dùng kỳ/bản ghi **tự tạo mới** (trên `seeded` hoặc một kỳ test riêng) cho các mục cần **tạo
   mới để xác nhận** (ghi "🖐️ tự tạo"). Nếu lỡ làm hỏng dữ liệu `seeded`, khôi phục lại bằng
   `restore_defense.sh seeded`.
4. Tick vào từng ô khi đã tự mắt thấy đúng kết quả mong đợi — đừng tick nếu chỉ "chắc là đúng".

---

## Phần A — Dữ liệu Odoo gốc được tái sử dụng (10 mục)

- [ ] **1. Deadline/ngày hoàn thành.** 🖐️ Tạo 1 task mới, đặt Hạn chót = hôm nay, chuyển sang stage
  Done (đã bật Folded) → mở lại task, bật chế độ nhà phát triển nếu cần để thấy `date_end` đã có giá
  trị → tạo/tính phiếu chứa task này → D1 tính đúng (đúng hạn).
- [ ] **2. Trạng thái task.** 🖐️ Chuyển 1 task Done lùi về "Yêu cầu chỉnh sửa" rồi chuyển lại Done →
  `review_reject_count` tăng 1 → tính phiếu, D5 giảm tương ứng.
- [ ] **3. Mức ưu tiên.** 🖐️ Tạo 1 bug mức Low và 1 bug mức Urgent, cùng thời gian xử lý → tính
  phiếu D7: chỉ bug Urgent được tính vào trung bình.
- [ ] **4. Thời gian xử lý.** 📂 Mở 1 bug High/Urgent đã đóng trong `seeded`, xác nhận có giá trị
  `working_hours_close` (xem qua debug mode hoặc suy từ điểm D7 đã tính đúng).
- [ ] **5. Giao việc.** 🖐️ Gán 1 task cho 2 người cùng lúc (`user_ids`) → tính phiếu cả hai người,
  xác nhận cả hai đều được tính task đó.
- [ ] **6. Tổ chức task.** 🖐️ Mở form task, xác nhận chọn được task cha, milestone, task phụ thuộc,
  nhãn — không có lỗi giao diện.
- [ ] **7. Nhân viên (user_id/parent_id).** 🖐️ Mở hồ sơ 1 nhân viên, xác nhận có Người dùng liên
  quan và Quản lý trực tiếp đã gán đúng — thử gửi duyệt 1 phiếu của nhân viên đó, xác nhận nhắc việc
  đi đúng tới người quản lý này.
- [ ] **8. Chức danh.** 🖐️ Mở 1 chức danh bất kỳ, xác nhận field Bộ KPI đã gắn đúng.
- [ ] **9. Lịch sự kiện "Chia sẻ kiến thức".** 🖐️ Tạo 1 sự kiện lịch, gán đúng loại "Chia sẻ kiến
  thức", người tổ chức là nhân viên mẫu → tính phiếu, D8 tăng đúng 1.
- [ ] **10. Chatter.** 📂 Mở 1 phiếu đã qua Gửi duyệt → Duyệt trong `seeded`, xác nhận tab trao đổi
  có đủ log các bước.

---

## Phần B — Field/tính năng tuỳ biến thêm vào Odoo gốc (14 mục)

- [ ] **11. Phân loại task.** 🖐️ Tạo 1 task Feature và 1 task Bug, xác nhận chọn được `task_type`
  trên form.
- [ ] **12. Story point.** 🖐️ Nhập story point cho 1 task Done trong kỳ → D2 cộng đúng.
- [ ] **13. Truy vết bug.** 🖐️ Tạo bug, chọn Task gốc, tick Lỗi production → D4 tính đúng bug này là
  production.
- [ ] **14. Kết quả xử lý bug.** 🖐️ Tạo 4 bug với 4 giá trị `bug_resolution` khác nhau → xác nhận
  chỉ valid/wont_fix được tính vào D3/D4 (so điểm trước/sau khi đổi giá trị 1 bug).
- [ ] **15. Nguyên nhân bug.** 🖐️ Đổi 1 bug sang `bug_root_cause = requirement`, có liên kết BA qua
  `requirement_id` → xác nhận bug này biến mất khỏi D3/D4 của Developer và xuất hiện ở B2 của BA.
- [ ] **16. Đếm lần bị trả về.** 🖐️ Thử sửa tay field `review_reject_count` trên form task → xác
  nhận field chỉ đọc (readonly), không sửa được trực tiếp.
- [ ] **17. Đánh dấu unit test.** 🖐️ Đăng nhập 1 tài khoản Nhân viên thường, mở task Feature, xác
  nhận ô "Có unit test" bị khoá; đăng nhập Manager, xác nhận tick được.
- [ ] **18. Ngày hoàn thành (ghi đè).** 🖐️ Chuyển 1 task Done sang stage khác không fold rồi xem lại
  — `date_end` vẫn giữ nguyên giá trị cũ (không bị xoá/ghi đè bằng thời điểm hiện tại).
- [ ] **19. Số ngày trễ.** 📂 Mở 1 task trễ hạn trong `seeded`, xác nhận `days_late` > 0 đúng số
  ngày thực tế.
- [ ] **20. Bộ lọc giao diện task.** 🖐️ Trên danh sách task, thử lần lượt các bộ lọc **Bug**, **Lỗi
  production**, **Trễ hạn**, **Bị trả về**, **Bug chưa phân loại** — xác nhận mỗi bộ lọc ra đúng tập
  con hợp lý.
- [ ] **21. Gắn KPI theo chức danh.** 🖐️ Đổi `kpi_template_id` của 1 chức danh thử nghiệm sang 1 bộ
  khác → tạo phiếu mới cho nhân viên giữ chức danh đó → xác nhận phiếu dùng đúng bộ KPI mới.
- [ ] **22. Phân quyền nền (KPI Manager kế thừa Project Manager).** 🖐️ Đăng nhập `quocviet`/`phuc` →
  vào app Project, xác nhận có quyền Project Manager (sửa được task của team mình).
- [ ] **23. Smart button "Phiếu KPI".** 🖐️ Mở hồ sơ 1 nhân viên, bấm nút "Phiếu KPI" → xác nhận mở
  đúng danh sách phiếu của người đó.
- [ ] **24. Cấu hình (Settings).** 🖐️ Đổi tạm ngưỡng xếp loại hoặc điểm trần ở Settings → bấm "Tính
  lại KPI" hàng loạt trên vài phiếu Nháp → xác nhận xếp loại đổi theo ngưỡng mới → **đổi lại giá trị
  cũ sau khi kiểm tra xong**, tránh ảnh hưởng dữ liệu demo thật.

---

## Phần C — Màn hình/tính năng xây mới (13 mục)

- [ ] **25. Chỉ số KPI + "Thử tính".** 🖐️ Tạo 1 chỉ số *Tự động (cấu hình)* mới (model `project.task`,
  domain `[('state','=','1_done')]`) → bấm **Thử tính** cho 1 nhân viên + kỳ mẫu → xác nhận ra số hợp
  lý (so khớp tay với số task Done của người đó).
- [ ] **26. Bộ KPI (ràng buộc tổng trọng số = 100).** 🖐️ Thử tạo 1 bộ KPI với tổng trọng số ≠ 100 →
  xác nhận bị chặn khi lưu; sửa lại đúng 100 → lưu được.
- [ ] **27. Kỳ đánh giá.** 🖐️ Tạo 1 kỳ test, đóng kỳ → thử tạo phiếu mới trong kỳ đã đóng → xác nhận
  bị chặn.
- [ ] **28. Phiếu đánh giá (vòng đời đầy đủ).** 🖐️ Đi hết 1 lượt: Nháp → Tự đánh giá (nhân viên) →
  Tính KPI → Điều chỉnh điểm có lý do → Gửi duyệt → Duyệt bằng quản lý trực tiếp (không cần quyền
  Admin) → thử tự Duyệt/Mở lại bằng chính tài khoản nhân viên trên phiếu (bị chặn, xung đột vai trò)
  → nhân viên Xác nhận kết quả. (Có thể dùng đúng luồng An/Bình ở `KICH_BAN_DEMO.md` Phần 2 — kết
  quả kỳ vọng: An 113,31 Xuất sắc, Bình 73,90 + điều chỉnh).
- [ ] **29. KPI Engine.** 🖐️ Bấm Tính KPI trên ít nhất 1 phiếu của mỗi bộ (Developer, Tester,
  Lead/PM, BA) → xác nhận không có lỗi/traceback nào hiện ra.
- [ ] **30. Phân quyền KPI + chặn xung đột vai trò.** 🖐️ Đăng nhập lần lượt `an` (chỉ thấy phiếu của
  mình, không tự duyệt được phiếu của mình kể cả nếu được gán thêm quyền Admin), `quocviet` (chỉ
  thấy team mình, TỰ DUYỆT được phiếu team mình mà không cần quyền Admin, nhưng không duyệt được
  phiếu đội khác), `admin` (thấy và duyệt được tất cả) — xác nhận đúng phạm vi mỗi vai trò.
- [ ] **31. Dashboard (Pivot/Graph/List).** 🖐️ Mở **KPI › Báo cáo › Dashboard**, chuyển qua cả 3
  kiểu xem → xác nhận không lỗi, số liệu hợp lý theo nhân viên/kỳ/xếp loại.
- [ ] **32. Báo cáo tổng hợp và chi tiết.** 🖐️ Mở cả hai màn hình, xác nhận dữ liệu khớp với số đã
  biết (ví dụ điểm An, Bình).
- [ ] **33. Chỉ số kiểm tra dữ liệu.** 🖐️ Mở **KPI › Báo cáo › Kiểm tra chất lượng dữ liệu** → cố
  tình để 1 task Done thiếu story point → xác nhận tỷ lệ giảm đúng, rồi sửa lại.
- [ ] **34. Bộ Tester tự động.** 📂 Xem `seeded`: phiếu `dung` 55,875 điểm — Cần cải thiện → xác
  nhận duyệt phiếu này tạo đúng 1 nhắc việc PIP cho `phuc`.
- [ ] **35. Tự động hoá cuối kỳ (cron).** 🖐️ Vào **Settings › Kỹ thuật › Tác vụ được lên lịch**
  (cần bật chế độ nhà phát triển), xác nhận 3 cron (tạo phiếu cuối kỳ, cập nhật số ngày trễ, tạm tính
  giữa kỳ) tồn tại và đang Active — không cần chờ chạy thật, chỉ cần xác nhận có cấu hình đúng.
- [ ] **36. Báo cáo in PDF.** 🖐️ Mở phiếu của An, bấm **In** → tải PDF → mở file, xác nhận đủ thông
  tin (tên, điểm, từng chỉ số, tên quản lý).
- [ ] **37. REST API.** 🖐️ Tạo API key ở Settings → gọi `curl` tới endpoint GET danh sách phiếu với
  key đó → xác nhận trả về đúng JSON; thử gọi thiếu key → xác nhận bị từ chối (401).

---

## Phần D — Tính năng mở rộng sau triển khai cơ bản (11 mục)

- [ ] **D1. Chỉ số cấu hình không cần code.** Trùng mục 25 ở trên — tick lại nếu đã làm.
- [ ] **D2. Bộ Tester tự động.** Trùng mục 34 ở trên.
- [ ] **D3. Bảng bậc điểm.** 🖐️ Gắn "Bậc 4 mức (mẫu)" vào 1 dòng chỉ số → tạo phiếu mới có 85% đạt
  mục tiêu → xác nhận điểm ra 75 (theo bậc) chứ không phải 85 (tuyến tính) → sửa bảng bậc sau đó →
  xác nhận phiếu cũ **không đổi điểm**.
- [ ] **D4. Bộ Team Lead/PM.** 📂 Xem `seeded`: phiếu `phuc` sau khi Dung/Khoa/Hà đã Gửi duyệt → P2 =
  79,01 trên 2 phiếu (Khoa bị loại vì thiếu dữ liệu), điểm Phúc 84,86.
- [ ] **D5. Bộ Business Analyst.** 📂 Xem `seeded`: phiếu `lan` — 75,828 điểm, B2 tính đúng 1 bug
  "yêu cầu sai"; mở phiếu `binh` xác nhận D3 không tính bug đó.
- [ ] **D6. Nhắc việc + tự đánh giá + báo cáo phòng ban.** ✅ Đã có `pre_defense_check.py` mục 2, 3,
  9 kiểm tự động qua tài khoản thật — chỉ cần đọc lại log script, không bắt buộc làm tay lại; nếu
  muốn chắc hơn, tự mắt xem 1 lượt chuông nhắc việc đổi đúng người qua từng bước (tạo phiếu → quản
  lý, gửi duyệt → người duyệt, duyệt → nhân viên).
- [ ] **D7. Kỳ riêng theo bộ KPI + mục tiêu riêng.** ✅ `pre_defense_check.py` mục 4, 11 đã kiểm tự
  động (không đổi được loại kỳ khi còn phiếu mở; gợi ý mục tiêu D2 ra 13,5/15/16,5). Tự mắt xem 1 lần
  nút "Áp dụng mức Vừa" có điền đúng vào ô Mục tiêu không.
- [ ] **D8. Màn hình tổng quan KPI.** ✅ `pre_defense_check.py` mục 12 đã kiểm số liệu qua API — tự
  mắt mở **KPI › Tổng quan** xem bố cục thẻ kỳ có hiển thị đúng, bấm thử 1–2 con số có mở đúng danh
  sách phiếu không (phần hiển thị trực quan script không kiểm được).
- [ ] **D9. Phản hồi 360 độ.** ✅ `pre_defense_check.py` mục 14 đã kiểm (khi cài `project_kpi_survey`)
  — tự mắt làm 1 lượt mời thật + trả lời thật (xem `KICH_BAN_DEMO.md` Phần 4) để chắc chắn giao diện
  mời/khảo sát hoạt động mượt, không chỉ đúng ở tầng dữ liệu.
- [ ] **D10. Mức đáp ứng kỹ năng (S1).** ✅ `pre_defense_check.py` mục 13 đã kiểm (khi cài
  `project_kpi_skills`) — 66,67% cho An. Tự mắt mở tab Kỹ năng của An để đối chiếu trực quan.
- [ ] **D11. Chặn xung đột vai trò.** ✅ `pre_defense_check.py` mục 1 đã kiểm tự động — trùng mục 30
  ở Phần C, không cần làm lại nếu đã tick ở đó.

---

## Tổng kết

| Phần | Số mục | Đã có script tự động hỗ trợ | Cần tự tay kiểm hoàn toàn |
|---|---|---|---|
| A — Dữ liệu Odoo gốc | 10 | 0 | 10 |
| B — Field tuỳ biến | 14 | 0 | 14 |
| C — Màn hình xây mới | 13 | ~2 (gián tiếp qua unit test) | ~11 |
| D — Mở rộng | 11 (4 trùng A/C) | 7 | 4 mới (D3–D5, D9 nên làm tay thêm) |

Sau khi tick hết, nếu còn ô nào sai/lỗi — ghi lại ngay (file/dòng nếu biết, hoặc chỉ cần mô tả thao
tác) rồi báo lại để sửa trước ngày dừng thay đổi (xem `TRIEN_KHAI_HE_THONG.md`/Chương 5.7 báo cáo).
