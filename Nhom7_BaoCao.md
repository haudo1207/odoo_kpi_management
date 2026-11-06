**Project KPI & Performance Management trên Odoo 19**

Tên đồ án: Xây dựng module quản lý và đánh giá KPI nhân sự (project\_kpi\_management) trên nền tảng Odoo 19, tích hợp với module Project có sẵn.

Mã nguồn: addons/project\_kpi\_management/ (module chính) và ba module cầu nối addons/project\_kpi\_timesheet/, addons/project\_kpi\_skills/, addons/project\_kpi\_survey/.

**Mục lục**  
•	Chương 1 — Yêu cầu  
•	Chương 2 — Kiến trúc hệ thống  
•	Chương 3 — Thiết kế cơ sở dữ liệu  
•	Chương 4 — Triển khai  
•	Chương 5 — Kiểm thử

**Chương 1 — Yêu cầu**  
**1.1. Bối cảnh và lý do chọn đề tài**  
Doanh nghiệp quản lý dự án phần mềm bằng Odoo Project có đủ dữ liệu công việc (task, bug, deadline, story point...) nhưng Odoo không có sẵn công cụ tổng hợp dữ liệu đó thành KPI đánh giá nhân sự. Quản lý phải tự tổng hợp thủ công, không nhất quán, không lưu vết. Đồ án xây dựng module đóng vai trò cầu nối: biến dữ liệu công việc đã có sẵn trong Odoo thành bộ chỉ số KPI tính tự động, có quy trình phê duyệt và báo cáo.  
**1.2. Mục tiêu**  
Cho phép định nghĩa bộ chỉ số KPI theo từng vai trò (chức danh), không hardcode trong code.  
Tự động tính toán phần lớn chỉ số từ dữ liệu Project có sẵn (task, bug, lịch).  
Có phiếu đánh giá theo nhân viên/kỳ, đi qua quy trình duyệt có lưu vết, cho phép quản lý điều chỉnh nhưng bắt buộc giải trình.  
Có báo cáo/dashboard giúp quản lý cấp trên thấy ai điểm thấp, thấp ở đâu, và dữ liệu có đáng tin không.  
Cho phép mở rộng sang vai trò khác (QA, Sales...) chỉ bằng cấu hình, không sửa code (trừ trường hợp cần công thức tính tự động hoàn toàn mới).  
**1.3. Đối tượng áp dụng**  
Doanh nghiệp phần mềm vừa và nhỏ, quản lý công việc bằng Odoo Project, có cấu trúc quản lý trực tiếp rõ ràng (mỗi nhân viên có một quản lý), đánh giá hiệu suất theo kỳ (tháng/sprint/quý) chứ không theo từng task riêng lẻ.  
**1.4. Yêu cầu chức năng**

| Mã | Vai trò | Yêu cầu |
| :---- | :---- | :---- |
| YC-01 | KPI Administrator | Định nghĩa chỉ số KPI (mã, tên, nhóm, chiều, cách tính) |
| YC-02 | KPI Administrator | Định nghĩa bộ KPI theo vai trò (nhiều chỉ số, mục tiêu, trọng số), ràng buộc tổng trọng số \= 100 |
| YC-03 | KPI Administrator | Gắn bộ KPI vào chức danh (hr.job) |
| YC-04 | Nhân viên (Developer) | Dữ liệu công việc (task, bug) được ghi nhận đủ để tính KPI: loại task, story point, phân loại bug, số lần trả về, có unit test |
| YC-05 | KPI Administrator / Manager | Tạo kỳ đánh giá (tháng/sprint/quý), đóng/mở kỳ |
| YC-06 | Quản lý trực tiếp | Tạo phiếu đánh giá cho nhân viên mình quản lý, trong một kỳ cụ thể |
| YC-07 | Hệ thống | Tự động tính phần lớn chỉ số của mỗi bộ KPI từ dữ liệu Project/Calendar có sẵn (ví dụ 8/9 chỉ số Developer D1–D8); chỉ số nhập tay (D9...) do quản lý chấm; chỉ số *cấu hình* (compute\_​mode \=​ domain) không cần viết hàm Python |
| YC-08 | Quản lý trực tiếp | Điều chỉnh điểm cuối trong biên độ cho phép, bắt buộc ghi lý do khi điều chỉnh khác 0 |
| YC-09 | Quản lý trực tiếp (đội mình) / KPI Administrator (phiếu còn lại) | Phiếu đi qua quy trình Nháp → Gửi duyệt → Duyệt; Trả về/Mở lại phải ghi lý do, lưu vết. Quản lý trực tiếp tự Duyệt/Trả về/Mở lại được phiếu của chính nhân viên mình quản lý, không cần thêm quyền Admin; KPI Administrator xử lý các phiếu còn lại |
| YC-10 | KPI Administrator / Manager | Xem báo cáo: xu hướng điểm theo kỳ, phân bố xếp loại, phân tích theo chỉ số, kiểm tra chất lượng dữ liệu, chỉ số cấp team/dự án, màn hình tổng quan theo kỳ |
| YC-11 | KPI Administrator | Tạo phiếu hàng loạt theo kỳ (và theo phòng ban nếu cần) |
| YC-12 | KPI Administrator | Chỉnh ngưỡng xếp loại, điểm trần, biên độ điều chỉnh, người duyệt mặc định qua giao diện Settings, không sửa code |
| YC-13 | Hệ thống | Mọi vai trò chỉ xem/sửa đúng phạm vi của mình (phân quyền), chặn xung đột vai trò duy nhất còn lại: không ai được tự Duyệt/Trả về/Mở lại phiếu của CHÍNH MÌNH, kể cả có thêm quyền Admin/Manager |
| YC-14 | Hệ thống | Tự động tạo phiếu khi kỳ kết thúc (không cần quản lý nhớ tạo tay); tạm tính giữa kỳ cho phiếu Nháp |
| YC-15 | Nhân viên/Quản lý | In phiếu đánh giá ra PDF để lưu trữ/ký tay |
| YC-16 | Công cụ ngoài (CI, quản lý test) | Đọc/ghi dữ liệu phiếu qua REST API có xác thực |
| YC-17 | Nhân viên | Tự đánh giá (điểm tự chấm cho chỉ số nhập tay, nhận xét) trước khi phiếu được duyệt; xác nhận (đồng ý/không đồng ý) sau khi phiếu Đã duyệt |
| YC-18 | Nhân viên khác (đồng nghiệp/cấp dưới) | Phản hồi 360 độ qua khảo sát khi được quản lý mời, ẩn danh một phần (module project\_​kpi\_​survey) |
| YC-19 | KPI Administrator | Cấu hình bộ KPI theo nhiều bậc điểm liên tục (không chỉ công thức tuyến tính 2 chiều), chụp bậc đã áp dụng vào dòng phiếu |
| YC-20 | Hệ thống | Mở rộng chỉ số từ dữ liệu giờ làm (Timesheet, module project\_​kpi\_​timesheet) và năng lực khai báo (hr\_​skills, module project\_​kpi\_​skills), chỉ bật khi các module gốc tương ứng được cài |
| YC-21 | KPI Administrator | Đặt mục tiêu riêng theo nhân viên hoặc phòng ban cho một dòng chỉ số, có gợi ý mục tiêu tính từ phân bố dữ liệu lịch sử (phân vị 25/50/75) |
| YC-22 | KPI Administrator | Đặt loại kỳ (tháng/sprint/quý) theo từng bộ KPI, không bắt buộc mọi bộ dùng chung một loại kỳ |
| YC-23 | Hệ thống | Nhắc việc tự động: chấm D9 khi tạo phiếu, duyệt phiếu khi gửi, lập kế hoạch cải thiện (PIP) khi xếp loại thấp; nếu quản lý không đủ quyền đọc phiếu thì chuyển cho người duyệt mặc định |
| YC-24 | KPI Administrator | Bộ KPI riêng cho vai trò Tester (QA1–QA5), Team Lead/PM (P1–P5), BA (B1–B4), chứng minh mở rộng vai trò chỉ bằng cấu hình |

### **1.5. Yêu cầu phi chức năng**

| Mã | Yêu cầu |
| :---- | :---- |
| PCN-01 | Chạy trên Odoo 19 Community (không phụ thuộc tính năng Enterprise, ví dụ không dùng hr\_​appraisal) |
| PCN-02 | Không hardcode vai trò/chỉ số trong code — toàn bộ nằm trong dữ liệu cấu hình |
| PCN-03 | Không xây lại tính năng Odoo gốc đã có (deadline, trạng thái, mức ưu tiên, nhân viên, lịch, chatter) |
| PCN-04 | Dữ liệu tính KPI minh bạch: mỗi dòng chỉ số có cờ "Áp dụng", loại trừ rõ ràng khi thiếu dữ liệu, không âm thầm tính sai |
| PCN-05 | Có kiểm thử tự động bao phủ từng quy tắc nghiệp vụ (không chỉ happy case) |
| PCN-06 | Giao diện bằng tiếng Việt, tương thích khi cài thêm gói ngôn ngữ Odoo |
| PCN-07 | REST API xác thực bằng API key chuẩn Odoo, tuân thủ phân quyền ghi/đọc như trên giao diện |
| PCN-08 | Triển khai production có HTTPS, không public cổng database |

**Chương 2 — Kiến trúc hệ thống**  
**2.1. Kiến trúc tổng quan (4 tầng)**  
\+---------------------------------------------------------------+  
 \| Tang vao/ra       	REST API (controllers/api.py), Bao cao PDF  \|  
 \|                			   (report/), Cron (data/ir\_cron\_data.xml) 	\|  
 \+-----------------------------------------------------------------+  
 \| Tang trinh bay  	  Views (list/form/search/pivot/graph/kanban),\|  
 \|                  		 Wizard (wizard/), Settings               	\|  
 \+-----------------------------------------------------------------+  
 \| Tang nghiep vu   	 kpi.metric, kpi.template(.line),         	\|  
 \|             		      kpi.target.override, kpi.score.scale(.step),\|  
 \|             		      kpi.period, kpi.evaluation(.line),       	\|  
 \|          		         kpi.engine, kpi.data.quality.report,     	\|  
 \|          		         kpi.team.report                           	\|  
 \+-----------------------------------------------------------------+  
 \| Tang tich hop   	  Mo rong project.task, project.milestone, 	\|  
 \|   				hr.job, hr.employee, res.config.settings \-   \|  
 \|           		        ghi them field KPI vao model co san  	\|  
 \+---------------------------------------------------------------+

**2.2. Luồng dữ liệu chính**  
Một chức danh (hr.job) được gắn một bộ KPI (kpi.template), bộ KPI gồm các dòng chỉ số (kpi.template.line: mục tiêu, trọng số, khối lượng tối thiểu). Khi tạo phiếu đánh giá (kpi.evaluation) cho một nhân viên trong một kỳ (kpi.period), hệ thống chụp các dòng này thành kpi.evaluation.line.  
Khi bấm "Tính KPI", kpi.engine.compute\_actual(metric, employee, kỳ, job, evaluation) được gọi cho từng dòng: chỉ số tự động chạy hàm \_metric\_\<mã\>() (đọc project.task, calendar.event, project.milestone... qua sudo()); chỉ số cấu hình (compute\_mode \= domain) chạy \_compute\_domain\_metric(), ghép domain đã cấu hình trên kpi.metric với điều kiện người/kỳ rồi search\_count()/search().mapped(). Mỗi module cầu nối (Timesheet, Skills, Survey) bổ sung thêm hàm \_metric\_\<mã\>() riêng qua \_inherit \= "kpi.engine".  
Kết quả (actual, volume) được dùng để tính is\_applicable (đủ khối lượng tối thiểu), score (công thức 2 chiều hoặc tra bảng bậc, có trần), weighted\_score. Điểm phiếu kpi\_score \= Σ(score×weight)/Σweight trên các dòng áp dụng, cộng manager\_adjustment ra final\_score, suy ra rating; nếu trọng số áp dụng quá thấp (insufficient\_data) thì dùng manual\_rating thay thế — kết quả cuối cùng là final\_rating, dùng cho mọi báo cáo.  
**2.3. Nguyên tắc thiết kế cốt lõi**  
Đây là nguyên tắc xuyên suốt toàn bộ thiết kế kiến trúc:

+ hr.job.kpi\_template\_id (Many2one) — mỗi chức danh tự chọn bộ KPI của mình, không có đoạn code nào kiểm tra if job.name \== 'Developer'.  
+ kpi.template.line chỉ là bảng ánh xạ (chỉ số, mục tiêu, trọng số, khối lượng tối thiểu) — thêm dòng mới là thao tác dữ liệu thuần tuý.  
+ kpi.evaluation.create() chọn bộ KPI theo employee.job\_id.kpi\_template\_id, hoàn toàn generic.  
+ kpi.period.\_eligible\_employees() lọc nhân viên đủ điều kiện tạo phiếu chỉ dựa vào job\_id.kpi\_template\_id.line\_ids khác rỗng — không biết và không cần biết tên chức danh.

Hệ thống đã được kiểm chứng trực tiếp: tạo một phòng ban, một chỉ số nhập tay, một bộ KPI, một chức danh, một nhân viên hoàn toàn mới — chỉ bằng thao tác dữ liệu (ORM/giao diện), không sửa một dòng code nào — toàn bộ luồng (wizard tạo phiếu hàng loạt tự nhận diện, tính điểm, gửi duyệt) chạy đúng ngay lập tức.  
Giới hạn tự nhiên (không tránh được): chỉ số Tự động (compute\_mode \= auto) cần một hàm \_metric\_\<mã\>() trong kpi\_engine.py, vì "tính tự động" nghĩa là phải có thuật toán đọc dữ liệu — không thể tự sinh ra từ cấu hình. Đây là ranh giới giữa tự động và nhập tay, không phải lỗ hổng thiết kế. Chỉ số Nhập tay (compute\_mode \= manual) không có giới hạn này.  
**2.4. Tích hợp với Odoo gốc**

| Model gốc | Field/khả năng được tái sử dụng |
| :---- | :---- |
| project.​task | date\_​deadline, date\_end, state, priority, working\_​hours\_​close, user\_ids |
| project.​task.​type | Field fold có sẵn (ẩn trong Kanban) |
| hr.​employee | user\_id, parent\_​id, job\_id, department\_​id (qua hr.version) |
| hr.job | Model chức danh có sẵn |
| hr.​department | Model phòng ban có sẵn, không đổi |
| calendar.​event | user\_id, categ\_​ids, start/stop |
| mail.​thread, mail.​activity.​mixin | Lịch sử (chatter) |
| res.​config.​settings | Cơ chế Settings app chuẩn |
| res.​groups.​privilege (Odoo 19\) | Cơ chế nhóm quyền mới |

**Chương 3 — Thiết kế cơ sở dữ liệu**  
**3.1. Danh sách model**

| \# | Model | Loại | Vai trò |
| :---- | :---- | :---- | :---- |
| 1 | kpi.metric | Bảng thật | Danh mục chỉ số KPI |
| 2 | kpi.​template | Bảng thật | Bộ KPI theo vai trò |
| 3 | kpi.​template.​line | Bảng thật | Dòng chỉ số trong bộ KPI |
| 4 | kpi.period | Bảng thật | Kỳ đánh giá |
| 5 | kpi.​evaluation | Bảng thật | Phiếu đánh giá |
| 6 | kpi.​evaluation.​line | Bảng thật | Dòng chỉ số trong phiếu |
| 7 | kpi.​data.​quality.​report | SQL view (\_​auto \=​ False) | Báo cáo chất lượng dữ liệu, chỉ đọc |
| 8 | kpi.engine | AbstractModel, không bảng | Thuật toán tính chỉ số tự động (D1–D8, QA1–QA3/QA4, P2/P3, B2) \+ chỉ số cấu hình domain; mỗi module cầu nối mở rộng bằng \_inherit để thêm \_​metric\_​\<mã\>() riêng |
| 9 | kpi.demo | AbstractModel, không bảng | Nạp kịch bản mẫu |
| 10 | kpi.​evaluation.​reason.​wizard | TransientModel | Lý do Trả về/Mở lại |
| 11 | kpi.​evaluation.​generate.​wizard | TransientModel | Tạo phiếu hàng loạt |
| 12 | project.​task (mở rộng) | Bảng gốc Odoo | Thêm field KPI |
| 13 | hr.job (mở rộng) | Bảng gốc Odoo | Thêm kpi\_​template\_​id |
| 14 | hr.​employee (mở rộng) | Bảng gốc Odoo | Thêm smart button |
| — | project.​milestone (mở rộng) | Bảng gốc Odoo | Thêm is\_​reached\_​on\_​time |
| 15 | res.​config.​settings (mở rộng) | TransientModel gốc Odoo | Thêm 7 tham số |
| 16 | kpi.​target.​override | Bảng thật | Mục tiêu riêng theo nhân viên/phòng ban cho một dòng chỉ số |
| 17 | kpi.​team.​report | SQL view (\_​auto \=​ False) | Chỉ số cấp team (dự án): đúng hạn, mật độ lỗi, lỗi production, giờ sửa bug |
| 18 | kpi.​self.​assessment.​wizard(.line) | TransientModel | Nhân viên tự đánh giá |
| 19 | kpi.​metric.​test.​wizard | TransientModel | Nút "Thử tính" cho chỉ số cấu hình |
| 20 | kpi.​score.​scale | Model | Bảng bậc điểm: tên \+ các bậc; chỉ Admin sửa |
| 21 | kpi.​score.​scale.​step | Model | Một bậc: pct\_from (% đạt mục tiêu bắt đầu), score, pct\_to (compute) |
| 22 | kpi.​acknowledge.​wizard | TransientModel | Nhân viên xác nhận kết quả sau khi phiếu Đã duyệt |
| 23 | kpi.​manager.​issue | TransientModel | Danh sách "Quản lý chưa có quyền KPI" |
| — | kpi.​feedback.​request, kpi.​feedback.​invite.​wizard | Model, TransientModel | Chỉ có khi cài project\_​kpi\_​survey: lời mời đánh giá 360 (ai được mời, đã trả lời chưa) và wizard "Mời đánh giá 360" |
| — | survey.user\_​input (mở rộng, chỉ khi cài project\_​kpi\_​survey) | Bảng gốc Odoo | Ghi đè \_​mark\_​done(): nộp bài xong thì tự đóng nhắc việc "Đánh giá 360" tương ứng |

**3.2. Chi tiết từng bảng**

#### **kpi.metric — Danh mục chỉ số**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| code | Char | required, UNIQUE | Mã ngắn (D1, QA1...) |
| name | Char | required | Tên đầy đủ |
| category | Selection | required | delivery/quality/process/collaboration |
| unit | Char |   | Đơn vị hiển thị (%, giờ, SP...) |
| direction | Selection | required, default higher | higher (cao tốt) / lower (thấp tốt) |
| compute\_​mode | Selection | required, default auto | auto (hàm Python \_​metric\_​\<mã\>()) / domain (cấu hình, không cần code) / manual (nhập tay) |
| description | Text |   | Mô tả công thức |
| active | Boolean | default True | Ẩn (archive) bị chặn nếu còn bộ KPI đang dùng |

display\_​name tự ghép "\<code\> — \<name\>".

**Chỉ số cấu hình (compute\_​mode \=​ domain) — không cần viết code:**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| source\_​model\_​id | Many2one → ir.model | chỉ cho project.​task, project.​milestone, calendar.​event | Model lấy dữ liệu |
| user\_​field\_​id | Many2one → ir.​model.​fields | phải thuộc source\_​model\_​id | Field người phụ trách — để trống nếu điều kiện người đã viết sẵn trong domain |
| date\_​field\_​id | Many2one → ir.​model.​fields | phải thuộc source\_​model\_​id, kiểu Date/Datetime | Field ngày để lọc theo kỳ |
| aggregation | Selection | required khi compute\_​mode \=​ domain | count / sum / avg / ratio |
| value\_​field\_​id | Many2one → ir.​model.​fields | bắt buộc nếu sum/avg | Field số để Tổng/Trung bình |
| numerator\_​domain | Char | required, phải ast.literal\_​eval được | Domain Odoo dạng literal thuần; dùng chuỗi \$CURRENT\_​USER\_​ID/\$PERIOD\_​START/\$PERIOD\_​END làm giữ chỗ cho giá trị động |
| denominator\_​domain | Char | bắt buộc nếu aggregation \=​ ratio | Domain mẫu số |

Thiết kế lấy nguyên mẫu từ gamification.​goal.​definition (Odoo 19 Community): model \+ field \+ domain \+ chế độ tính (count/sum/avg). Chỉ lấy phần domain/count/sum/avg — **không** có lựa chọn chạy code Python tuỳ ý qua giao diện (đó là lỗ hổng bảo mật). Khi lưu, hệ thống kiểm tra: model phải trong danh sách cho phép, field phải đúng model/kiểu, và chạy thử search\_​count() thật với domain để bắt lỗi cú pháp ngay lúc lưu, không đợi tới lúc tính KPI.

Các nguyên tắc an toàn/chính xác của cơ chế này:

> > 1\.         Domain được đọc bằng ast.literal\_​eval — chỉ parse literal Python thuần (list/tuple/str/số...), không chạy được biểu thức hay truy cập thuộc tính tuỳ ý, an toàn hơn safe\_​eval. Việc tham chiếu người/kỳ dùng 3 chuỗi giữ chỗ cố định (\$CURRENT\_​USER\_​ID, \$PERIOD\_​START, \$PERIOD\_​END), được thay bằng giá trị thật sau khi đã parse xong.

> > 2\.         Lọc kỳ đúng kiểu field ngày: field Date (ví dụ project.​milestone.​deadline) lọc bằng chính kiểu Date; field Datetime (ví dụ project.task.date\_​deadline) dùng mốc UTC như các chỉ số Python — kpi.engine.\_​domain\_​field\_​bounds() tự chọn đúng loại mốc theo date\_​field\_​id.ttype.

> > 3\.         Nút "Thử tính" tự kiểm tra quyền trong action\_​open\_​test\_​wizard() (has\_​group), không chỉ ẩn ở view — gọi thẳng qua RPC bỏ qua nút vẫn bị chặn đúng.

> > 4\.         Chỉ số cấu hình và hàm Python tương đương xử lý giống nhau với bản ghi đã lưu trữ (active \=​ False) — cả hai đều dùng search()/search\_​count() nên mặc định đều loại bản ghi đã lưu trữ.

**Giới hạn đã biết:** domain không so sánh được hai field trên cùng bản ghi (ví dụ cần date\_​end \<=​ date\_​deadline) — phải giữ hàm Python cho các chỉ số kiểu này, hoặc thêm field compute stored dạng cờ (is\_​on\_​time) để domain chỉ cần so với giá trị cố định. Đi qua quan hệ (quy bug về task gốc) không thuộc giới hạn này.

kpi.engine.\_​compute\_​domain\_​metric(): ghép domain cấu hình với điều kiện người/kỳ (nếu có khai báo user\_​field\_​id/date\_​field\_​id), rồi search\_​count/search().​mapped() theo aggregation. Trả về (actual, volume) đúng khuôn với các hàm \_​metric\_​\<mã\>() hiện có — không cần sửa gì ở kpi.​evaluation/kpi.​evaluation.​line.

Nút **"Thử tính"** trên form chỉ số (chỉ hiện khi compute\_​mode \=​ domain, chỉ KPI Admin): mở wizard kpi.​metric.​test.​wizard, chọn một nhân viên và một kỳ, xem ngay actual/volume — không cần tạo phiếu thật để biết domain viết có đúng không.

#### **kpi.​template — Bộ KPI theo vai trò**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| name | Char | required |   |
| description | Text |   |   |
| active | Boolean | default True | Ẩn bị chặn nếu còn chức danh dùng (job\_ids) |
| line\_ids | One2many → kpi.​template.​line |   | copy=True |
| job\_ids | One2many ← hr.job.kpi\_​template\_​id |   | Chỉ đọc, hiển thị chức danh đang dùng |
| total\_​weight | Integer, compute |   | Tổng trọng số các dòng |

Ràng buộc: tổng trọng số phải \= 100 **nếu** đã có ít nhất 1 dòng (template rỗng được phép lưu). Đặt trên template (không đặt trên dòng) vì form tách thao tác sửa/thêm dòng thành nhiều lệnh ghi riêng — ràng buộc trên dòng sẽ bắt sai trạng thái "nửa chừng".

#### **kpi.​template.​line — Dòng chỉ số trong bộ KPI**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| template\_​id | Many2one → kpi.​template | required, ondelete=​cascade |   |
| sequence | Integer | default 10 |   |
| metric\_​id | Many2one → kpi.metric | required, ondelete=​restrict |   |
| target | Float | digits(16,2) | Mục tiêu |
| weight | Integer | required, CHECK 0–100 | Trọng số (%) |
| min\_​volume | Float | CHECK ≥ 0 | Khối lượng tối thiểu để chỉ số được áp dụng |
| direction, unit, compute\_​mode | related → metric\_​id.\* |   |   |

Ràng buộc SQL: UNIQUE(template\_​id, metric\_​id) (một chỉ số không lặp trong 1 bộ KPI), CHECK(weight BETWEEN 0 AND 100), CHECK(min\_​volume \>=​ 0).

\_​resolve\_​target(overrides, employee\_​id, department\_​id): mục tiêu dùng khi chụp phiếu, ưu tiên kpi.​target.​override của nhân viên, rồi của phòng ban, cuối cùng mới dùng target mặc định ở trên.

#### **kpi.​target.​override — Mục tiêu riêng theo nhân viên/phòng ban**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| template\_​line\_​id | Many2one → kpi.​template.​line | required, ondelete=​cascade | Dòng chỉ số muốn đặt mục tiêu riêng |
| employee\_​id | Many2one → hr.​employee |   | Để trống nếu override theo phòng ban |
| department\_​id | Many2one → hr.​department |   | Để trống nếu override theo nhân viên |
| target | Float | required, digits(16,2) | Mục tiêu riêng, thay cho mục tiêu mặc định của template |

Ràng buộc SQL: đúng một trong hai (employee\_​id xor department\_​id), UNIQUE(template\_​line\_​id, employee\_​id) và UNIQUE(template\_​line\_​id, department\_​id). Chỉ dùng lúc tạo phiếu, không ảnh hưởng phiếu đã tạo trước đó — đúng nguyên tắc chụp dữ liệu.

#### **kpi.period — Kỳ đánh giá**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| name | Char | required |   |
| period\_​type | Selection | required, default month | month/sprint/quarter |
| date\_​from, date\_to | Date | required | CHECK date\_​from \<=​ date\_​to |
| state | Selection | required, default open | open/closed |
| evaluation\_​ids | One2many ← kpi.evaluation.period\_​id |   |   |
| evaluation\_​count | Integer, compute |   | Cho smart button |
| auto\_​generated | Boolean | readonly, copy=False | Đánh dấu cron đã chạy cho kỳ này — mỗi kỳ chỉ 1 lần |

#### **kpi.​evaluation — Phiếu đánh giá (kế thừa mail.​thread, mail.​activity.​mixin)**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| name | Char, compute, store |   | "\<nhân viên\> — \<kỳ\>" |
| employee\_​id | Many2one → hr.​employee | required |   |
| job\_id, department\_​id | Many2one, readonly |   | Chụp lúc tạo |
| period\_​id | Many2one → kpi.period | required |   |
| template\_​id | Many2one → kpi.​template | required |   |
| line\_ids | One2many → kpi.​evaluation.​line |   | Chụp từ template khi tạo |
| state | Selection | default draft | draft/submitted/approved |
| computed\_​date | Datetime, readonly | copy=False | Thời điểm bấm Tính KPI gần nhất |
| approved\_​date | Datetime, readonly | copy=False | Thời điểm Duyệt |
| late\_​bug\_​count | Integer, compute |   | Bug tính KPI phát sinh sau approved\_​date |
| applicable\_​weight | Integer, compute, store |   | Σ trọng số các dòng Áp dụng |
| insufficient\_​data | Boolean, compute, store |   | applicable\_​weight \< 50 (tham số) |
| kpi\_​score | Float, compute, store |   | Σ(score×weight)/Σweight trên dòng áp dụng |
| manager\_​adjustment | Float | digits(16,2) | ±10 (tham số), bắt buộc có adjustment\_​note nếu khác 0 |
| adjustment\_​note | Text |   |   |
| final\_​score | Float, compute, store |   | kpi\_​score \+ manager\_​adjustment |
| rating | Selection, compute, store |   | Xếp loại tự động, False nếu insufficient\_​data |
| manual\_​rating, manual\_​rating\_​note | Selection, Text |   | Dùng khi insufficient\_​data |
| final\_​rating | Selection, compute, store |   | manual\_​rating nếu thiếu dữ liệu, ngược lại rating — dùng cho mọi báo cáo |
| ack\_​decision, ack\_​comment, ack\_date | Selection, Text, Datetime | copy=False, readonly | Nhân viên xác nhận kết quả sau khi Đã duyệt; chỉ ghi qua wizard bằng sudo() |
| last\_​computed\_​date | Datetime | copy=False, readonly | Lần tính gần nhất, kể cả tạm tính tự động |
| employee\_​comment | Text | copy=False | Nhân viên tự nhận xét, chỉ tham khảo, ghi qua wizard bằng sudo() |
| is\_​own\_​evaluation | Boolean, compute | không store | True nếu người đang xem là chính nhân viên trên phiếu |

Ràng buộc SQL: UNIQUE(employee\_​id, period\_​id). Ràng buộc Python: biên độ điều chỉnh, kỳ phải đang mở khi tạo phiếu Nháp, khoá toàn bộ field thuộc \_​LOCKED\_​FIELDS khi không ở Nháp.

employee\_​comment chặn ghi trực tiếp ở cả create() lẫn write() cho mọi lời gọi không qua sudo(), bất kể trạng thái hay quyền — vì quản lý vốn có quyền ghi trên kpi.​evaluation khi phiếu còn Nháp nên nếu chỉ khoá theo trạng thái thì vẫn ghi hộ được field này. Chỉ wizard Tự đánh giá (ghi bằng sudo()) mới ghi được. self\_​score trên kpi.​evaluation.​line dùng cùng cơ chế.

#### **kpi.​evaluation.​line — Dòng chỉ số trong phiếu**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| evaluation\_​id | Many2one, ondelete=​cascade | required |   |
| employee\_​id, period\_​id, department\_​id, job\_id, category | related, store=True |   | Lưu sẵn để pivot/group by không phải join nhiều cấp |
| metric\_​id | Many2one → kpi.metric | required, ondelete=​restrict |   |
| target | Float | digits(16,2) | Chụp từ template, sửa được khi phiếu Nháp |
| weight | Integer |   | Chụp từ template |
| min\_​volume | Float | digits(16,2) | Chụp từ template |
| volume | Float |   | Engine ghi (chỉ số auto) |
| actual | Float |   | Engine ghi (auto) hoặc quản lý nhập (manual) |
| actual\_​entered | Boolean |   | Đánh dấu chỉ số nhập tay đã được chấm — tránh nhầm "chưa nhập" với "nhập 0" |
| is\_​applicable | Boolean, compute, store |   | volume \>=​ min\_​volume |
| score | Float, compute, store |   | 2 chiều, trần \= tham số score\_​cap (mặc định 120\) |
| weighted\_​score | Float, compute, store |   | score × weight / 100 |
| remark | Text |   |   |
| self\_​score | Float | copy=False | Nhân viên tự chấm (chỉ chỉ số nhập tay), chỉ tham khảo, không cộng vào điểm. Chặn ghi trực tiếp giống employee\_​comment |

**Công thức tính điểm** (\_score(), static method):

neu direction la "lower" (thap la tot):  
 	score \= cap neu actual \<= 0, nguoc lai target / actual \* 100  
 neu direction la "higher" (cao la tot):  
 	score \= cap neu target \<= 0, nguoc lai actual / target \* 100  
 ket qua gioi han trong \[0, cap\]

Chỉ áp dụng khi is\_​applicable \=​ True; dòng không áp dụng có score \= 0 và bị loại khỏi cả tử số lẫn mẫu số khi tính kpi\_​score của phiếu.

#### **kpi.​score.​scale / kpi.​score.​scale.​step — Bảng bậc điểm liên tục**

| Model | Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- | :---- |
| kpi.​score.​scale | name | Char | required | Tên bảng bậc |
|   | active | Boolean | default True | Ẩn bị chặn nếu còn kpi.​template.​line đang dùng |
|   | step\_ids | One2many → .step |   | copy=True |
| kpi.​score.​scale.​step | scale\_id | Many2one, ondelete=​cascade | required |   |
|   | pct\_from | Float, digits(16,2) | required, CHECK ≥ 0 | % đạt mục tiêu bắt đầu của bậc |
|   | pct\_to | Float, compute |   | % bắt đầu của bậc kế tiếp (không gồm); bậc cuối không giới hạn |
|   | score | Float, digits(16,2) | required, CHECK ≥ 0 | Điểm của bậc |

Tra theo % đạt mục tiêu (actual/target hoặc target/actual tuỳ chiều), không theo giá trị thực tế — một bảng dùng chung được cho nhiều chỉ số, kể cả khi mục tiêu đổi theo phòng ban/nhân viên. Các bậc không chồng khoảng và phủ liên tục từ 0% (bậc thấp nhất bắt buộc pct\_​from \=​ 0). kpi.template.line.scale\_​id (tuỳ chọn — không gắn thì dùng công thức 2 chiều mặc định) được chụp lại vào dòng phiếu lúc tạo bằng \_​snapshot(), nên sửa bảng bậc sau đó không đổi điểm phiếu cũ. Trần điểm (score\_​cap) vẫn áp dụng sau khi tra bậc.

#### **kpi.​feedback.​request — Lời mời đánh giá 360 độ (chỉ có khi cài project\_​kpi\_​survey)**

| Field | Kiểu | Ràng buộc | Ghi chú |
| :---- | :---- | :---- | :---- |
| evaluation\_​id | Many2one → kpi.​evaluation | required, ondelete=​cascade |   |
| employee\_​id | related → evaluation\_​id.employee\_​id, store |   | Nhân viên được đánh giá |
| reviewer\_​id | Many2one → res.users | required | Người được mời đánh giá |
| survey\_​id | Many2one → survey.​survey | required, readonly | Khảo sát dùng (mẫu "Phản hồi 360 độ") |
| user\_​input\_​id | Many2one → survey.user\_​input | readonly, ondelete=​set null, copy=False | Câu trả lời riêng của người này |
| state | Selection, compute, store | pending/done | Theo user\_​input\_​id.state \=​=​ "done" |

Ràng buộc SQL: UNIQUE(evaluation\_​id, reviewer\_​id). Kế thừa mail.​thread, mail.​activity.​mixin để gắn nhắc việc riêng cho từng người được mời. F1 (chỉ số 360\) là trung bình scoring\_​percentage của các câu trả lời done, min\_​volume \=​ 3\.

#### **kpi.​data.​quality.​report — Báo cáo chất lượng dữ liệu (SQL view)**

Không phải bảng thật (\_​auto \=​ False), tạo bằng CREATE VIEW trong init(), nhóm theo project.task.project\_​id. Các field: done\_​feature\_​count, done\_​without\_​sp, done\_​count, done\_​without\_​date\_​end, bug\_​count, bug\_​without\_​origin, bug\_​unclassified, và 3 tỷ lệ phần trăm tương ứng.

#### **kpi.​team.​report — Chỉ số KPI theo dự án (SQL view)**

Cùng cách làm với kpi.​data.​quality.​report ở trên, nhưng đo hiệu quả của cả team (team \= dự án) thay vì chất lượng nhập liệu. Các field: feature\_​done\_​count, feature\_​on\_​time\_​count, on\_​time\_​rate (%), bug\_​count, bug\_​density (bug/feature), production\_​bug\_​count, production\_​bug\_​rate (%), avg\_​bug\_​fix\_​hours. Không quy trách nhiệm cá nhân, không tính điểm — chỉ là báo cáo.

Bug được quy về dự án của task gốc (origin\_​task\_​id.project\_​id), không phải dự án chứa bản ghi bug. Bug không có task gốc thì giữ nguyên dự án của chính nó.

#### **Field mở rộng trên project.​task**

| Field | Kiểu | Dùng cho |
| :---- | :---- | :---- |
| task\_​type | Selection (feature/bug/requirement), required, default feature | Phân loại |
| story\_​points | Float, digits(16,1) | D2, D3 |
| origin\_​task\_​id | Many2one tự tham chiếu | D3, D4 — bug trỏ về task gốc |
| bug\_ids | One2many ngược của origin\_​task\_​id | Hiển thị trên task gốc |
| is\_​production\_​bug | Boolean | D4 |
| bug\_​resolution | Selection (valid/wont\_fix/duplicate/invalid) | Lọc bug tính KPI |
| bug\_​root\_​cause | Selection (code/requirement/environment) | Lọc bug tính KPI |
| requirement\_​id | Many2one tự tham chiếu | Feature trỏ về yêu cầu gốc |
| is\_​on\_​time | Boolean, compute, store | Task đã xong, có deadline, days\_​late \=​ 0 |
| bug\_​reporter\_​id | Many2one res.users, default người tạo | Người phát hiện bug; không dùng create\_​uid vì PM có thể log bug hộ tester hoặc bug được import. Chỉ KPI Manager trở lên ghi được |
| review\_​reject\_​count, review\_​approve\_​count | Integer, readonly | D5 — tăng trong write() khi đổi state |
| has\_​unit\_​test | Boolean | D6 — chỉ KPI Manager ghi được |
| kpi\_​can\_​review | Boolean, compute | Khoá ô has\_​unit\_​test trên form nếu không phải Manager |
| days\_​late | Integer, compute, store | D1 — so date\_end/hôm nay với date\_​deadline, cron cập nhật hằng ngày |

#### **Field mở rộng trên hr.job, hr.​employee, res.​config.​settings**

| Model | Field | Ghi chú |
| :---- | :---- | :---- |
| kpi.period | dashboard\_​\* (compute, không lưu) | Màn hình tổng quan |
| kpi.​template / kpi.period | period\_​type (Selection, mặc định tháng) | Wizard và cron chỉ tạo phiếu cho bộ KPI cùng loại kỳ |
| kpi.​target.​override | suggestion\_​easy/medium/hard, suggestion\_​note (compute) | Gợi ý mục tiêu từ lịch sử, nút Áp dụng |
| hr.job | kpi\_​template\_​id (Many2one, ondelete=​restrict) | Trung tâm của nguyên tắc "không hardcode vai trò" |
| project.​milestone | is\_​reached\_​on\_​time (Boolean, compute, store) | Đã đạt và reached\_​date ≤ deadline |
| kpi.​template.​line / kpi.​evaluation.​line | scale\_id / scale\_​json, scale\_​name, achievement\_​pct | Bảng bậc điểm, chụp vào dòng phiếu |
| hr.​employee | kpi\_​evaluation\_​count (Integer, compute) | Cho smart button "Phiếu KPI" |
| res.​config.​settings | kpi\_​default\_​approver\_​id, kpi\_​score\_​cap, kpi\_​adjustment\_​max, kpi\_​min\_​applicable\_​weight, kpi\_​rating\_​excellent, kpi\_​rating\_​good, kpi\_​rating\_​pass | Lưu ở ir.config\_​parameter |

#### **Wizard (TransientModel)**

| Model | Field chính | Mục đích |
| :---- | :---- | :---- |
| kpi.​evaluation.​reason.​wizard | evaluation\_​id, mode (return/reopen), reason (required) | Bắt buộc lý do khi Trả về nháp/Mở lại, ghi vào chatter |
| kpi.​evaluation.​generate.​wizard | period\_​id, department\_​ids (M2M), compute, preview\_​count (compute) | Tạo phiếu hàng loạt, xem trước số lượng |

**Chương 4 — Triển khai**  
**4.1. Tiêu chí phân loại**

| Nhóm | Định nghĩa |
| :---- | :---- |
| Có sẵn | Field/tính năng Odoo đã có, dùng nguyên |
| Customize | Sửa/mở rộng nghiệp vụ Odoo đã có (thêm field vào model gốc, kế thừa view/group) |
| Xây mới | Thành phần nghiệp vụ mới |

 

| Phạm vi | Định nghĩa |
| :---- | :---- |
| MVP | Bắt buộc để demo được |
| Nên có | Tăng tính thực tế |
| Mở rộng | Làm nếu còn thời gian / đề cương yêu cầu |

### **4.2. Phạm vi đã triển khai**

**Tổng cộng 38 hạng mục:** Có sẵn 10 · Customize 14 · Xây mới 14 — MVP 31 · Nên có 4 · Mở rộng 3\. Toàn bộ 38/38 hạng mục đã triển khai đủ.

| Giai đoạn | Nội dung | Phạm vi |
| :---- | :---- | :---- |
| 1 | kpi.metric, kpi.​template, gắn hr.job | MVP |
| 2 | Field KPI trên project.​task, date\_end, số ngày trễ | MVP |
| 3 | kpi.period, kpi.​evaluation, công thức điểm, quy trình duyệt | MVP |
| 4 | kpi.engine (D1–D8) | MVP |
| 5 | 3 nhóm quyền, record rule | MVP |
| 6 | Dashboard, báo cáo, kiểm tra chất lượng dữ liệu | MVP |
| 7 | Wizard tạo phiếu hàng loạt, Settings | Nên có |
| 8 | Bộ KPI Tester mẫu (chứng minh mở rộng không sửa code) | Nên có |
| 9 | Cron cuối kỳ, báo cáo PDF, REST API | Mở rộng |
| 10 | Cấu hình deploy production | Bàn giao |

**Các đợt mở rộng thêm sau phạm vi gốc** (bổ sung chỉ số theo domain, bộ KPI Tester/Lead-PM/BA tự động, bảng bậc điểm, nhắc việc và xác nhận kết quả, mục tiêu theo phòng ban/nhân viên, màn hình tổng quan, module cầu nối Skills và Survey) đều đã triển khai và được kiểm thử đầy đủ (Chương 5).

### **4.3. Công nghệ sử dụng**

Odoo 19 (Python 3.12, PostgreSQL 16), Docker/Docker Compose, QWeb (báo cáo PDF), nginx \+ Let's Encrypt (production). Không dùng framework/thư viện ngoài hệ sinh thái Odoo chuẩn.

**Chương 5 — Kiểm thử**  
**5.1. Chiến lược kiểm thử**

Unit test tự động (odoo.​tests.​TransactionCase/HttpCase), chạy bằng \--test-tags /project\_​kpi\_​management, trên database tạo mới hoàn toàn mỗi lần.

Kiểm thử thủ công bổ sung cho các phần khó mô phỏng đầy đủ trong unit test: gọi REST API thật qua HTTP bằng API key thật, render PDF thật và đọc nội dung, đăng nhập 3 vai trò qua XML-RPC.

Một test riêng (test\_​happy\_​path\_​full\_​approval\_​cycle) nối liền toàn bộ chu trình (dữ liệu thật → Engine tính thật → Gửi duyệt → Duyệt → khoá) trong một lần chạy.

### **5.2. Môi trường kiểm thử**

Odoo 19.0, PostgreSQL 16, chạy trong container Docker (odoo19-web, odoo19-db).

docker exec odoo19-web odoo \-d kpi\_dev \-u project\_kpi\_management \--test-tags /project\_kpi\_management \--stop-after-init \--http-port 8070

### **5.3. Phạm vi test case**

Tổng cộng 218 test, 0 failed, 0 error, chia trong 22 file:

| Module | File test | Số test | Phạm vi kiểm tra |
| :---- | :---- | :---- | :---- |
| project\_​kpi\_​management | test\_​kpi\_​config.py | 11 | Chỉ số, bộ KPI, ràng buộc tổng trọng số \= 100 |
|   | test\_​kpi\_​domain\_​metric.py | 8 | Chỉ số cấu hình không cần code (domain) |
|   | test\_​kpi\_​target\_​override.py | 4 | Mục tiêu riêng theo nhân viên/phòng ban |
|   | test\_​project\_​task.py | 8 | Dữ liệu task: date\_end, số ngày trễ, liên kết bug |
|   | test\_​kpi\_​evaluation.py | 15 | Phiếu, công thức điểm, quy trình duyệt |
|   | test\_​kpi\_​engine.py | 12 | Engine tính D1–D8 và chỉ số domain |
|   | test\_​kpi\_​demo\_​scenario.py | 22 | Đối chiếu bảng tính tay cho dữ liệu mẫu |
|   | test\_​kpi\_​security.py | 7 | Phân quyền 3 vai trò, quản lý trực tiếp tự duyệt đội mình, chặn tự duyệt chính mình |
|   | test\_​kpi\_​reports.py | 10 | Báo cáo, wizard, Settings, bộ Tester mẫu |
|   | test\_​kpi\_​tester.py | 12 | Bộ KPI Tester tự động (QA1–QA5) |
|   | test\_​kpi\_​compute\_​paths.py | 7 | Mọi đường tính KPI (wizard, cron, API) đều ra kết quả nhất quán |
|   | test\_​kpi\_​score\_​scale.py | 12 | Chấm điểm theo bậc |
|   | test\_​kpi\_​dashboard.py | 7 | Màn hình tổng quan theo kỳ |
|   | test\_​kpi\_​period\_​types.py | 5 | Kỳ riêng theo bộ KPI; kỳ chồng lắp tính trùng dữ liệu (giới hạn đã biết) |
|   | test\_​kpi\_​target\_​suggestion.py | 7 | Gợi ý mục tiêu từ lịch sử |
|   | test\_​kpi\_​workflow.py | 18 | Nhắc việc, xác nhận kết quả, tạm tính, báo cáo phòng ban |
|   | test\_​kpi\_​ba.py | 10 | Bộ Business Analyst (B1–B4) |
|   | test\_​kpi\_​lead.py | 10 | Bộ Team Lead/PM (P1–P5) |
|   | test\_​kpi\_​integration.py | 9 | Cron, báo cáo PDF, REST API, tham số query sai kiểu |
| project\_​kpi\_​timesheet | test\_​kpi\_​timesheet.py | 6 | Chỉ số P4 (giờ thực tế so với kế hoạch) |
| project\_​kpi\_​skills | test\_​kpi\_​skills.py | 10 | Chỉ số S1 (mức đáp ứng kỹ năng); mã chỉ số demo Sales không trùng S1 |
| project\_​kpi\_​survey | test\_​kpi\_​feedback.py | 8 | Phản hồi 360 độ |

Toàn bộ test đều chạy qua đúng hành động người dùng thật (nút, wizard, cron, API) thay vì chỉ gọi thẳng hàm tính, để bảo đảm engine, giao diện và REST API luôn cho cùng một kết quả.

### **5.4. Kết quả kiểm thử**

218/218 test đạt, 0 lỗi trên database tạo mới hoàn toàn (không chạy lại trên database cũ), kiểm tra riêng cho module chính, module chính kết hợp từng module cầu nối, và cả bốn module cài cùng lúc để bảo đảm các hàm tính chỉ số của module cầu nối không đè lên nhau.

Hạn chế của TransactionCase: unit test chạy bằng superuser, nên bỏ qua một số kiểm tra chỉ áp dụng cho người dùng thật (ví dụ chặn xung đột vai trò). Vì vậy kiểm thử tự động được bổ sung bằng kiểm thử thủ công qua tài khoản thật (mục 5.5) để xác nhận hệ thống hoạt động đúng khi dùng thật.

### **5.5. Kiểm thử thủ công bổ sung**

| Hạng mục | Cách kiểm | Kết quả |
| :---- | :---- | :---- |
| REST API qua HTTP thật | Tạo API key thật, gọi curl với GET/POST, kiểm tra round-trip tiếng Việt UTF-8 | Đạt — dữ liệu tiếng Việt (có dấu) ghi/đọc chính xác |
| Báo cáo PDF | Render PDF thật qua \_​render\_​qweb\_​pdf, đọc nội dung từng dòng | Đạt — số liệu khớp bảng tính tay |
| Phân quyền 3 vai trò qua XML-RPC | Đăng nhập thật 3 tài khoản, gọi search\_​count, thử sửa/duyệt trái quyền | Đạt — đúng số phiếu nhìn thấy, đúng chỗ bị từ chối |
| Luồng hoàn chỉnh trên hệ thống sống | Tạo phiếu → Tính KPI → Gửi duyệt → Duyệt, không dùng dữ liệu giả lập | Đạt — điểm khớp bảng tính tay |
| Kịch bản mở rộng vai trò mới | Tạo phòng ban \+ chỉ số \+ bộ KPI \+ chức danh \+ nhân viên hoàn toàn mới, không sửa code | Đạt |
| Dọn phụ thuộc dữ liệu demo gốc Odoo | Cài module không \--with-demo, kiểm tra toàn database | Đạt |

