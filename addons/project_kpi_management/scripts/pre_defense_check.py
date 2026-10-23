#!/usr/bin/env python3
"""Kiểm tra nhanh trước buổi bảo vệ — chạy qua XML-RPC thật, đăng nhập bằng đúng tài khoản sẽ
dùng khi demo (admin, quocviet, an), không phải TransactionCase giả lập (TransactionCase chạy
bằng superuser nên env.su=True, bỏ qua một số kiểm tra chỉ áp dụng cho người dùng thật — xem
Chương 5.4 trong Nhom7_BaoCao.md).

Vì sao cần script riêng (không chỉ chạy lại unit test):
  - Sửa code trên đĩa không tự áp dụng cho một server Odoo đang chạy liên tục — phải nạp lại
    module (-u) hoặc khởi động lại tiến trình trước. Script này exercise đúng đường API thật mà
    buổi bảo vệ sẽ dùng, nên bắt được đúng loại lỗi "test đạt nhưng hệ thống đang chạy vẫn sai".

Cách chạy, SAU KHI đã nạp lại module:
    docker compose exec odoo odoo -d kpi_dev -u project_kpi_management --stop-after-init
    docker compose restart odoo    # hoặc chỉ cần 1 trong 2 lệnh trên, restart là đủ nếu không đổi field
    docker compose exec odoo python3 /mnt/extra-addons/project_kpi_management/scripts/pre_defense_check.py --db kpi_dev

Script tự dọn dữ liệu nó tạo ra (kỳ test riêng, phiếu test riêng) ở cuối, kể cả khi có check nào
đó FAIL — không ảnh hưởng dữ liệu demo dùng để trình bày thật. Không cần cài thêm thư viện gì.
"""
import argparse
import sys
import time
import xmlrpc.client

DEMO_LOGINS = {
    "admin": "admin",
    "quocviet": "quocviet",
    "an": "an",
    "binh": "binh",
    "chi": "chi",
}


class Session:
    def __init__(self, url, db, passwords):
        self.url = url
        self.db = db
        self.passwords = passwords
        self.common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        self._uid_cache = {}
        self.cleanups = []  # list[callable]
        self.failures = []

    def uid(self, login):
        if login not in self._uid_cache:
            pwd = self.passwords[login]
            uid = self.common.authenticate(self.db, login, pwd, {})
            if not uid:
                raise RuntimeError(f"Không đăng nhập được với tài khoản '{login}'.")
            self._uid_cache[login] = uid
        return self._uid_cache[login]

    def call(self, login, model, method, *args, **kwargs):
        uid = self.uid(login)
        pwd = self.passwords[login]
        return self.models.execute_kw(self.db, uid, pwd, model, method, list(args), kwargs)

    def ref(self, xmlid, required=True):
        module, name = xmlid.split(".", 1)
        rows = self.call("admin", "ir.model.data", "search_read",
                          [("module", "=", module), ("name", "=", name)], fields=["res_id", "model"])
        if not rows:
            if required:
                raise RuntimeError(f"Không tìm thấy xmlid {xmlid}.")
            return None, None
        return rows[0]["model"], rows[0]["res_id"]

    def ok(self, name):
        print(f"[OK]   {name}")

    def fail(self, name, detail):
        self.failures.append(name)
        print(f"[FAIL] {name}: {detail}")

    def add_cleanup(self, fn):
        self.cleanups.append(fn)

    def run_cleanups(self):
        for fn in reversed(self.cleanups):
            try:
                fn()
            except Exception as e:  # cố dọn hết, không để 1 lỗi chặn các bước dọn còn lại
                print(f"[WARN] dọn dẹp lỗi: {e}")


def ensure_demo_loaded(s):
    # _load_scenario() là private method (không gọi qua RPC được) và chạy action qua RPC cần thêm
    # quyền kỹ thuật không chắc có sẵn — script chỉ XÁC NHẬN dữ liệu mẫu đã có, không tự nạp.
    # Nếu chưa có: vào menu KPI > Cấu hình > "Nạp dữ liệu mẫu" trước, rồi chạy lại script.
    model, _ = s.ref("project_kpi_management.demo_employee_an", required=False)
    if not model:
        print("[FAIL] Dữ liệu mẫu chưa được nạp. Vào menu KPI > Cấu hình > 'Nạp dữ liệu mẫu' rồi chạy lại.")
        sys.exit(2)


def make_test_period(s):
    suffix = time.strftime("%Y%m%d-%H%M%S")
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra trước bảo vệ {suffix}",
        "period_type": "sprint",
        "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    return period_id


def _force_unlink_evaluation(s, ev_id):
    """Phiếu chỉ xoá được ở Nháp — nếu check đã Gửi/Duyệt phiếu thật để kiểm tra, phải mở lại
    trước khi dọn, không để sót phiếu test trong database dùng để trình bày thật. Cả 2 chế độ
    "return" (từ Đã gửi) và "reopen" (từ Đã duyệt) của wizard đều đưa thẳng về Nháp."""
    state = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["state"])[0]["state"]
    if state in ("approved", "submitted"):
        mode = "reopen" if state == "approved" else "return"
        wiz_id = s.call("admin", "kpi.evaluation.reason.wizard", "create",
                         {"evaluation_id": ev_id, "mode": mode, "reason": "Dọn dữ liệu kiểm tra trước bảo vệ"})
        s.call("admin", "kpi.evaluation.reason.wizard", "action_confirm", [wiz_id])
    s.call("admin", "kpi.evaluation", "unlink", [ev_id])


def create_evaluation(s, employee_xmlid, period_id, employee_id=None):
    if employee_id is None:
        _, employee_id = s.ref(employee_xmlid)
    ev_id = s.call("admin", "kpi.evaluation", "create", {
        "employee_id": employee_id, "period_id": period_id,
    })
    s.add_cleanup(lambda: _force_unlink_evaluation(s, ev_id))
    return ev_id


def check_role_conflict_and_pip(s, period_id):
    """Mục 2 + Mục 3: quản lý được gán thêm quyền Admin không tự duyệt được phiếu nhân viên mình
    quản lý; phiếu Cần cải thiện khi duyệt tạo đúng nhắc việc PIP."""
    ev_id = create_evaluation(s, "project_kpi_management.demo_employee_binh", period_id)
    s.call("admin", "kpi.evaluation", "write", [ev_id], {
        "manual_rating": "improve", "manual_rating_note": "Script kiểm tra trước bảo vệ",
    })
    manual_line_ids = s.call("admin", "kpi.evaluation.line", "search",
                              [("evaluation_id", "=", ev_id), ("compute_mode", "=", "manual")])
    s.call("admin", "kpi.evaluation.line", "write", manual_line_ids, {"actual_entered": True})
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    s.call("admin", "kpi.evaluation", "action_submit", [ev_id])

    _, admin_group_id = s.ref("project_kpi_management.group_kpi_admin")
    _, quocviet_id = s.ref("project_kpi_management.demo_user_manager")
    had_admin_before = s.call("admin", "res.users", "has_group", [quocviet_id], "project_kpi_management.group_kpi_admin")
    if not had_admin_before:
        s.call("admin", "res.users", "write", [quocviet_id], {"group_ids": [(4, admin_group_id)]})
        s.add_cleanup(lambda: s.call("admin", "res.users", "write", [quocviet_id], {"group_ids": [(3, admin_group_id)]}))

    try:
        s.call("quocviet", "kpi.evaluation", "action_approve", [ev_id])
        s.fail("Chặn xung đột vai trò", "quản lý vẫn duyệt được phiếu nhân viên mình quản lý")
    except xmlrpc.client.Fault as e:
        if "quản lý trực tiếp" in e.faultString or "chính nhân viên" in e.faultString:
            s.ok("Chặn xung đột vai trò (quocviet bị chặn đúng)")
        else:
            s.fail("Chặn xung đột vai trò", f"bị chặn nhưng sai lý do: {e.faultString[:200]}")

    s.call("admin", "kpi.evaluation", "action_approve", [ev_id])
    rating = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["final_rating"])[0]["final_rating"]
    if rating != "improve":
        s.fail("Nhắc việc PIP", f"final_rating mong đợi 'improve', thực tế '{rating}'")
        return
    _, pip_type_id = s.ref("project_kpi_management.mail_activity_type_pip")
    activities = s.call("admin", "mail.activity", "search_count",
                         [("res_model", "=", "kpi.evaluation"), ("res_id", "=", ev_id),
                          ("activity_type_id", "=", pip_type_id)])
    if activities == 1:
        s.ok("Nhắc việc PIP được tạo đúng 1 lần khi duyệt phiếu Cần cải thiện")
    else:
        s.fail("Nhắc việc PIP", f"mong đợi 1 activity, thực tế {activities}")


def check_self_assessment(s, period_id):
    """Mục 6: nhân viên tự đánh giá qua wizard bằng chính tài khoản của mình."""
    ev_id = create_evaluation(s, "project_kpi_management.demo_employee_an", period_id)
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    line_ids = s.call("admin", "kpi.evaluation.line", "search",
                       [("evaluation_id", "=", ev_id), ("compute_mode", "=", "manual")])
    try:
        wiz_id = s.call("an", "kpi.self.assessment.wizard", "create", {
            "evaluation_id": ev_id,
            "employee_comment": "Tự đánh giá từ script kiểm tra trước bảo vệ",
            "line_ids": [(0, 0, {"evaluation_line_id": line_ids[0], "self_score": 5})],
        })
        s.call("an", "kpi.self.assessment.wizard", "action_confirm", [wiz_id])
        comment = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["employee_comment"])[0]["employee_comment"]
        if comment and "kiểm tra trước bảo vệ" in comment:
            s.ok("Tự đánh giá: nhân viên ghi được nhận xét qua wizard")
        else:
            s.fail("Tự đánh giá", f"employee_comment không khớp: {comment!r}")
    except xmlrpc.client.Fault as e:
        s.fail("Tự đánh giá", e.faultString[:200])

    try:
        s.call("quocviet", "kpi.evaluation", "write", [ev_id], {"employee_comment": "Ghi trực tiếp, không qua wizard"})
        s.fail("Tự đánh giá (chặn ghi trực tiếp)", "người khác ghi trực tiếp được employee_comment")
    except xmlrpc.client.Fault:
        s.ok("Tự đánh giá: người khác không ghi trực tiếp được employee_comment")

    # self_score cùng bản chất employee_comment: quản lý có quyền ghi dòng phiếu khi Nháp (để
    # nhập D9), nên dễ lách — phải chặn riêng, cả write() lẫn create()
    try:
        s.call("quocviet", "kpi.evaluation.line", "write", line_ids, {"self_score": 9})
        s.fail("Tự đánh giá (chặn self_score write)", "quản lý ghi trực tiếp được self_score")
    except xmlrpc.client.Fault:
        s.ok("Tự đánh giá: quản lý không ghi trực tiếp được self_score")

    try:
        s.call("quocviet", "kpi.evaluation.line", "create", {
            "evaluation_id": ev_id, "metric_id": s.call("admin", "kpi.evaluation.line", "read", line_ids[:1], fields=["metric_id"])[0]["metric_id"][0],
            "self_score": 9,
        })
        s.fail("Tự đánh giá (chặn self_score create)", "quản lý tạo dòng kèm self_score được")
    except xmlrpc.client.Fault:
        s.ok("Tự đánh giá: quản lý không tạo được dòng phiếu kèm self_score")

    try:
        _, binh_id = s.ref("project_kpi_management.demo_employee_binh")
        stray_id = s.call("quocviet", "kpi.evaluation", "create", {
            "employee_id": binh_id, "period_id": period_id, "employee_comment": "Tạo kèm luôn",
        })
        s.add_cleanup(lambda: _force_unlink_evaluation(s, stray_id))  # không mong đợi tới đây, dọn phòng khi có
        s.fail("Tự đánh giá (chặn employee_comment create)", "quản lý tạo phiếu kèm employee_comment được")
    except xmlrpc.client.Fault:
        s.ok("Tự đánh giá: quản lý không tạo được phiếu kèm employee_comment")


def check_tester(s, period_id):
    """Bước 2: bộ KPI Tester tự động. Tự tạo tester + dự án + 3 bug riêng (không phụ thuộc dữ liệu
    mẫu), đăng nhập bằng chính tester để xác nhận không tự sửa được bug_reporter_id, rồi Admin tính
    phiếu và đối chiếu điểm với bảng tính tay."""
    suffix = time.strftime("%H%M%S")
    login = f"chk_tester_{suffix}"
    s.passwords[login] = login
    _, user_group = s.ref("base.group_user")
    _, project_group = s.ref("project.group_project_user")
    user_id = s.call("admin", "res.users", "create", {
        "name": f"Tester kiểm tra {suffix}", "login": login, "password": login,
        "group_ids": [(6, 0, [user_group, project_group])],
    })

    def _drop_user():
        try:
            s.call("admin", "res.users", "unlink", [user_id])
        except xmlrpc.client.Fault:
            s.call("admin", "res.users", "write", [user_id], {"active": False})  # còn tham chiếu: chỉ ẩn
    s.add_cleanup(_drop_user)
    _, job_id = s.ref("project_kpi_management.hr_job_tester")
    employee_id = s.call("admin", "hr.employee", "create", {
        "name": f"Tester kiểm tra {suffix}", "user_id": user_id, "job_id": job_id,
    })
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [employee_id]))
    project_id = s.call("admin", "project.project", "create", {"name": f"Dự án kiểm tra Tester {suffix}"})
    s.add_cleanup(lambda: s.call("admin", "project.project", "unlink", [project_id]))
    bug_ids = []
    for resolution, cause in (("valid", "code"), ("valid", "requirement"), ("invalid", "code")):
        origin_id = s.call("admin", "project.task", "create", {"name": "Task gốc", "project_id": project_id})
        bug_id = s.call("admin", "project.task", "create", {
            "name": "Bug kiểm tra", "project_id": project_id, "task_type": "bug", "bug_reporter_id": user_id,
            "bug_resolution": resolution, "bug_root_cause": cause, "origin_task_id": origin_id,
        })
        bug_ids.append(bug_id)
        s.add_cleanup(lambda i=origin_id: s.call("admin", "project.task", "unlink", [i]))
        s.add_cleanup(lambda i=bug_id: s.call("admin", "project.task", "unlink", [i]))

    try:
        s.call(login, "project.task", "write", [bug_ids[0]], {"bug_reporter_id": 1})
        s.fail("Tester không tự sửa bug_reporter_id", "tester ghi được bug_reporter_id")
    except xmlrpc.client.Fault as e:
        if "người phát hiện bug" in e.faultString:
            s.ok("Tester không tự sửa được bug_reporter_id (bị chặn đúng lý do)")
        else:
            s.fail("Tester không tự sửa bug_reporter_id", f"bị chặn nhưng sai lý do: {e.faultString[:200]}")

    ev_id = create_evaluation(s, None, period_id, employee_id=employee_id)
    t8_lines = s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "QA5")])
    s.call("admin", "kpi.evaluation.line", "write", t8_lines, {"actual": 4})
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    score = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["kpi_score"])[0]["kpi_score"]
    # QA1 2/15·25 + QA2 10/33.33·20 + QA3 100/90·15 + QA4 (0% → trần 120)·25 + QA5 4/4·15 = 71.0
    if abs(score - 71.0) < 0.01:
        s.ok("Phiếu Tester: admin tính ra 71.0 điểm, khớp bảng tính tay")
    else:
        s.fail("Phiếu Tester", f"mong đợi 71.0, thực tế {score}")

    # Bước 3: chấm điểm theo bậc, đi qua nút Tính KPI. QA1 = 2 bug / mục tiêu 4 = 50% đạt → bậc 50% = 60 điểm
    # (tuyến tính sẽ ra 50). Tính tay trước khi chạy.
    scale_id = s.call("admin", "kpi.score.scale", "create", {
        "name": f"Bậc kiểm tra {suffix}",
        "step_ids": [(0, 0, {"pct_from": f, "score": sc}) for f, sc in ((0, 0), (50, 60), (100, 100))],
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.score.scale", "unlink", [scale_id]))
    _, qa1_id = s.ref("project_kpi_management.kpi_metric_qa1")
    template_id = s.call("admin", "kpi.template", "create", {
        "name": f"Bậc kiểm tra {suffix}",
        "line_ids": [(0, 0, {"metric_id": qa1_id, "target": 4, "weight": 100, "scale_id": scale_id})],
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.template", "unlink", [template_id]))
    period2 = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra bậc {suffix}", "period_type": "sprint", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period2]))
    ev2 = s.call("admin", "kpi.evaluation", "create", {"employee_id": employee_id, "period_id": period2, "template_id": template_id})
    s.add_cleanup(lambda: _force_unlink_evaluation(s, ev2))
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev2])
    score2 = s.call("admin", "kpi.evaluation", "read", [ev2], fields=["kpi_score"])[0]["kpi_score"]
    if abs(score2 - 60.0) < 0.01:
        s.ok("Chấm theo bậc: nút Tính KPI ra 60 điểm (50% đạt mục tiêu → bậc 60), khớp bảng tính tay")
    else:
        s.fail("Chấm theo bậc", f"mong đợi 60.0, thực tế {score2}")


def _make_pm(s, suffix, job_xmlid="project_kpi_management.hr_job_pm"):
    """Tạo PM (hoặc vai trò khác theo job) + dự án do người đó quản lý (project.user_id),
    trả về (login, user_id, employee_id, project_id)."""
    login = f"chk_pm_{suffix}"
    s.passwords[login] = login
    _, user_group = s.ref("base.group_user")
    user_id = s.call("admin", "res.users", "create", {
        "name": f"PM kiểm tra {suffix}", "login": login, "password": login, "group_ids": [(6, 0, [user_group])],
    })

    def _drop_user():
        try:
            s.call("admin", "res.users", "unlink", [user_id])
        except xmlrpc.client.Fault:
            s.call("admin", "res.users", "write", [user_id], {"active": False})
    s.add_cleanup(_drop_user)
    _, job_id = s.ref(job_xmlid)
    employee_id = s.call("admin", "hr.employee", "create", {"name": f"PM kiểm tra {suffix}", "user_id": user_id, "job_id": job_id})
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [employee_id]))
    project_id = s.call("admin", "project.project", "create", {"name": f"Dự án PM kiểm tra {suffix}", "user_id": user_id})
    s.add_cleanup(lambda: s.call("admin", "project.project", "unlink", [project_id]))
    return login, user_id, employee_id, project_id


def check_lead(s):
    """Bước 4: bộ KPI Team Lead / PM. Tự tạo PM, dự án, 2 milestone (1 đúng hạn, 1 quá hạn chưa đạt), tính phiếu
    bằng nút Tính KPI. Tính tay trước: P1 = 1/2 = 50% → 50/80 = 62.5% đạt; P2, P3 Không áp dụng (chưa có cấp dưới
    chốt phiếu, dự án chưa đủ dữ liệu); P5 = 4 → 100%. Điểm = (62.5×25 + 100×30) / 55 = 82.95."""
    suffix = time.strftime("%H%M%S")
    _, _, employee_id, project_id = _make_pm(s, suffix)
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra Lead {suffix}", "period_type": "sprint", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    today = time.strftime("%Y-%m-%d")
    future = time.strftime("%Y-%m-%d", time.localtime(time.time() + 5 * 86400))
    past = time.strftime("%Y-%m-%d", time.localtime(time.time() - 5 * 86400))
    m1 = s.call("admin", "project.milestone", "create", {"name": "Đúng hạn", "project_id": project_id, "deadline": future})
    s.call("admin", "project.milestone", "write", [m1], {"is_reached": True})
    m2 = s.call("admin", "project.milestone", "create", {"name": "Quá hạn", "project_id": project_id, "deadline": past})
    s.add_cleanup(lambda: s.call("admin", "project.milestone", "unlink", [m1, m2]))
    ev_id = create_evaluation(s, None, period_id, employee_id=employee_id)
    p5 = s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "P5")])
    s.call("admin", "kpi.evaluation.line", "write", p5, {"actual": 4})
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    score = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["kpi_score"])[0]["kpi_score"]
    expected = (62.5 * 25 + 100 * 30) / 55
    if abs(score - expected) < 0.01:
        s.ok(f"Phiếu Lead/PM: admin tính ra {expected:.2f} điểm (P1 50%, P2 và P3 Không áp dụng), khớp bảng tính tay")
    else:
        s.fail("Phiếu Lead/PM", f"mong đợi {expected:.2f}, thực tế {score}")


def check_ba(s):
    """Bước 5: bộ KPI BA. Tự tạo BA, dự án, 3 yêu cầu (2 đúng hạn, 1 trễ; 2 qua review lần đầu), 1 Feature hiện thực
    yêu cầu đầu và 1 bug "yêu cầu sai" của Feature đó (quy về BA, không về Developer). Tính tay trước khi chạy:
    B1 = 2/3 → 74,07% ·25; B2 = 1/3 bug/yêu cầu, mục tiêu 0,3 → 90% ·30; B3 = 2/3 → 95,24% ·25; B4 = 4 → 100% ·20 = 89,33."""
    suffix = time.strftime("%H%M%S")
    _, user_id, employee_id, project_id = _make_pm(s, suffix + "b", "project_kpi_management.hr_job_ba")
    now = time.time()
    fmt = lambda days: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now + days * 86400))

    def task(vals):
        task_id = s.call("admin", "project.task", "create", {"project_id": project_id, **vals})
        s.add_cleanup(lambda: s.call("admin", "project.task", "unlink", [task_id]))
        return task_id

    requirements = []
    for deadline, approve, reject in ((5, 1, 0), (-5, 1, 1), (5, 1, 0)):
        req = task({"name": "Yêu cầu", "task_type": "requirement", "user_ids": [(6, 0, [user_id])],
                    "date_deadline": fmt(deadline)})
        s.call("admin", "project.task", "write", [req], {"state": "1_done", "review_approve_count": approve,
                                                         "review_reject_count": reject})
        requirements.append(req)
    feature = task({"name": "Feature", "requirement_id": requirements[0]})
    task({"name": "Bug yêu cầu sai", "task_type": "bug", "origin_task_id": feature, "bug_resolution": "valid",
          "bug_root_cause": "requirement"})
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra BA {suffix}", "period_type": "sprint", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    ev_id = create_evaluation(s, None, period_id, employee_id=employee_id)
    b4 = s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "B4")])
    s.call("admin", "kpi.evaluation.line", "write", b4, {"actual": 4})
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    score = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["kpi_score"])[0]["kpi_score"]
    expected = (200 / 3 / 90 * 100 * 25 + 90 * 30 + 200 / 3 / 70 * 100 * 25 + 100 * 20) / 100
    if abs(score - expected) < 0.01:
        s.ok(f"Phiếu BA: admin tính ra {expected:.2f} điểm (bug yêu cầu sai quy về BA), khớp bảng tính tay")
    else:
        s.fail("Phiếu BA", f"mong đợi {expected:.2f}, thực tế {score}")


def check_workflow(s):
    """Đợt A (v1.3): nhắc việc theo quy trình + nhân viên xác nhận kết quả, qua tài khoản thật. Tự tạo quản lý,
    nhân viên, kỳ, phiếu; đặt người duyệt mặc định = admin và khôi phục giá trị cũ ở cuối."""
    suffix = time.strftime("%H%M%S")
    _, g_user = s.ref("base.group_user")
    _, g_kpi_user = s.ref("project_kpi_management.group_kpi_user")
    _, g_kpi_manager = s.ref("project_kpi_management.group_kpi_manager")
    _, job_id = s.ref("project_kpi_management.hr_job_developer")

    def make_user(tag, groups):
        login = f"chk_wf_{tag}_{suffix}"
        s.passwords[login] = login
        uid = s.call("admin", "res.users", "create", {
            "name": f"WF {tag} {suffix}", "login": login, "password": login, "group_ids": [(6, 0, groups)],
        })

        def drop():
            try:
                s.call("admin", "res.users", "unlink", [uid])
            except xmlrpc.client.Fault:
                s.call("admin", "res.users", "write", [uid], {"active": False})
        s.add_cleanup(drop)
        return login, uid

    _, manager_uid = make_user("mgr", [g_user, g_kpi_manager])
    emp_login, emp_uid = make_user("emp", [g_user, g_kpi_user])
    manager_emp = s.call("admin", "hr.employee", "create", {"name": f"WF quản lý {suffix}", "user_id": manager_uid})
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [manager_emp]))
    employee_id = s.call("admin", "hr.employee", "create", {
        "name": f"WF nhân viên {suffix}", "user_id": emp_uid, "job_id": job_id, "parent_id": manager_emp,
    })
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [employee_id]))
    old_approver = s.call("admin", "ir.config_parameter", "get_param", "project_kpi_management.default_approver_id")
    s.call("admin", "ir.config_parameter", "set_param", "project_kpi_management.default_approver_id", str(s.uid("admin")))
    s.add_cleanup(lambda: s.call("admin", "ir.config_parameter", "set_param",
                                 "project_kpi_management.default_approver_id", old_approver or False))
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra quy trình {suffix}", "period_type": "sprint", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    ev_id = create_evaluation(s, None, period_id, employee_id=employee_id)

    def activities(xmlid, user_uid):
        _, type_id = s.ref(xmlid)
        return s.call("admin", "mail.activity", "search_count", [
            ("res_model", "=", "kpi.evaluation"), ("res_id", "=", ev_id),
            ("activity_type_id", "=", type_id), ("user_id", "=", user_uid),
        ])

    admin_uid = s.uid("admin")
    ok = activities("project_kpi_management.mail_activity_type_complete", manager_uid) == 1
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    s.call("admin", "kpi.evaluation.line", "write",
           s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", ev_id)]), {"actual": 100, "volume": 100})
    s.call("admin", "kpi.evaluation", "action_submit", [ev_id])
    ok = ok and activities("project_kpi_management.mail_activity_type_complete", manager_uid) == 0
    ok = ok and activities("project_kpi_management.mail_activity_type_approve", admin_uid) == 1
    s.call("admin", "kpi.evaluation", "action_approve", [ev_id])
    ok = ok and activities("project_kpi_management.mail_activity_type_approve", admin_uid) == 0
    ok = ok and activities("project_kpi_management.mail_activity_type_ack", emp_uid) == 1
    if ok:
        s.ok("Nhắc việc quy trình: tạo phiếu → quản lý; gửi duyệt → người duyệt; duyệt → nhân viên; mỗi bước tự đánh dấu xong nhắc việc cũ")
    else:
        s.fail("Nhắc việc quy trình", "số nhắc việc theo từng bước không như mong đợi")

    try:
        s.call("admin", "kpi.evaluation", "write", [ev_id], {"ack_decision": "agree"})
        s.fail("Xác nhận kết quả (chặn ghi trực tiếp)", "ghi trực tiếp được ack_decision")
    except xmlrpc.client.Fault:
        s.ok("Xác nhận kết quả: không ghi trực tiếp được (kể cả admin), chỉ qua wizard của chính nhân viên")
    try:
        wiz = s.call(emp_login, "kpi.acknowledge.wizard", "create", {"evaluation_id": ev_id, "decision": "agree"})
        s.call(emp_login, "kpi.acknowledge.wizard", "action_confirm", [wiz])
        row = s.call("admin", "kpi.evaluation", "read", [ev_id], fields=["ack_decision", "state"])[0]
        if row["ack_decision"] == "agree" and row["state"] == "approved" and \
                activities("project_kpi_management.mail_activity_type_ack", emp_uid) == 0:
            s.ok("Xác nhận kết quả: nhân viên xác nhận qua wizard, phiếu vẫn Đã duyệt, nhắc việc xác nhận hoàn tất")
        else:
            s.fail("Xác nhận kết quả", f"trạng thái sau xác nhận không đúng: {row}")
    except xmlrpc.client.Fault as e:
        s.fail("Xác nhận kết quả", e.faultString[:200])


def check_default_approver(s):
    """Người duyệt mặc định phải đã được đặt và là KPI Admin — nếu không, nhắc việc duyệt phiếu sẽ "không có gì xảy ra"
    ngay lúc demo. Dữ liệu mẫu tự đặt admin; database cũ thì đặt ở KPI › Cấu hình › Thiết lập › Quy trình."""
    value = s.call("admin", "ir.config_parameter", "get_param", "project_kpi_management.default_approver_id")
    if not value:
        s.fail("Người duyệt mặc định", "chưa đặt (vào Thiết lập › Quy trình)")
        return
    is_admin = s.call("admin", "res.users", "has_group", [int(value)], "project_kpi_management.group_kpi_admin")
    if is_admin:
        s.ok("Người duyệt mặc định đã đặt và là KPI Admin")
    else:
        s.fail("Người duyệt mặc định", f"user {value} không thuộc nhóm KPI Administrator")


def check_period_type_and_suggestion(s):
    """Đợt B (v1.4): (1) không đổi loại kỳ của bộ KPI khi còn phiếu ở kỳ đang mở; (2) gợi ý mục tiêu từ 3 kỳ đã duyệt
    (D2 = 10, 20, 30 → Dễ 15 / Vừa 20 / Khó 25, tính tay trước khi chạy). Tự tạo dữ liệu, tự dọn."""
    suffix = time.strftime("%H%M%S")
    _, d2_id = s.ref("project_kpi_management.kpi_metric_d2")
    template_id = s.call("admin", "kpi.template", "create", {
        "name": f"Kiểm tra kỳ {suffix}", "period_type": "quarter",
        "line_ids": [(0, 0, {"metric_id": d2_id, "target": 20, "weight": 100})],
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.template", "unlink", [template_id]))
    job_id = s.call("admin", "hr.job", "create", {"name": f"Job kiểm tra kỳ {suffix}", "kpi_template_id": template_id})
    s.add_cleanup(lambda: s.call("admin", "hr.job", "unlink", [job_id]))
    department_id = s.call("admin", "hr.department", "create", {"name": f"Phòng kiểm tra {suffix}"})
    s.add_cleanup(lambda: s.call("admin", "hr.department", "unlink", [department_id]))
    employee_id = s.call("admin", "hr.employee", "create", {
        "name": f"NV kiểm tra kỳ {suffix}", "job_id": job_id, "department_id": department_id,
    })
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [employee_id]))
    approved = []
    for index, actual in enumerate((10, 20, 30)):
        start = f"{2001 + index}-01-01"
        period_id = s.call("admin", "kpi.period", "create", {
            "name": f"Lịch sử kiểm tra {suffix}-{index}", "period_type": "quarter", "date_from": start, "date_to": f"{2001 + index}-03-31",
        })
        s.add_cleanup(lambda i=period_id: s.call("admin", "kpi.period", "unlink", [i]))
        ev_id = s.call("admin", "kpi.evaluation", "create", {"employee_id": employee_id, "period_id": period_id, "template_id": template_id})
        s.add_cleanup(lambda i=ev_id: _force_unlink_evaluation(s, i))
        line_ids = s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", ev_id)])
        s.call("admin", "kpi.evaluation.line", "write", line_ids, {"actual": actual, "volume": 10})
        approved.append(ev_id)
    # (1) còn phiếu ở kỳ đang mở → không đổi được loại kỳ
    try:
        s.call("admin", "kpi.template", "write", [template_id], {"period_type": "month"})
        s.fail("Đổi loại kỳ bộ KPI", "đổi được dù còn phiếu ở kỳ đang mở")
    except xmlrpc.client.Fault:
        s.ok("Bộ KPI còn phiếu ở kỳ đang mở thì không đổi được loại kỳ")
    for ev_id in approved:
        s.call("admin", "kpi.evaluation", "write", [ev_id], {"state": "approved"})
    # (2) gợi ý mục tiêu
    line_id = s.call("admin", "kpi.template.line", "search", [("template_id", "=", template_id)])[0]
    override_id = s.call("admin", "kpi.target.override", "create", {
        "template_line_id": line_id, "department_id": department_id, "target": 1,
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.target.override", "unlink", [override_id]))
    row = s.call("admin", "kpi.target.override", "read", [override_id],
                 fields=["suggestion_easy", "suggestion_medium", "suggestion_hard"])[0]
    if (row["suggestion_easy"], row["suggestion_medium"], row["suggestion_hard"]) == (15.0, 20.0, 25.0):
        s.ok("Gợi ý mục tiêu từ lịch sử: Dễ 15 / Vừa 20 / Khó 25, khớp bảng tính tay")
    else:
        s.fail("Gợi ý mục tiêu", f"mong đợi (15, 20, 25), thực tế {row}")


def check_dashboard(s):
    """Đợt C1: màn hình tổng quan. Tự tạo kỳ + 2 phiếu (1 Nháp, 1 Đã duyệt), đăng nhập Admin đọc số liệu kỳ qua XML-RPC:
    tổng 2, Nháp 1, Đã duyệt 1, điểm TB = điểm cuối của phiếu đã duyệt (tính tay: chỉ có một phiếu duyệt); nút "Đã duyệt"
    mở đúng 1 phiếu."""
    suffix = time.strftime("%H%M%S")
    _, job_id = s.ref("project_kpi_management.hr_job_developer")
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra tổng quan {suffix}", "period_type": "month", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    evs = []
    for tag in ("nháp", "duyệt"):
        if tag == "nháp":
            emp = s.call("admin", "hr.employee", "create", {"name": f"NV tổng quan {tag} {suffix}", "job_id": job_id})
            s.add_cleanup(lambda i=emp: s.call("admin", "hr.employee", "unlink", [i]))
        else:  # phiếu sẽ được Tính KPI nên nhân viên cần tài khoản
            _, _, emp, _ = _make_pm(s, suffix + "d", "project_kpi_management.hr_job_developer")
        ev = s.call("admin", "kpi.evaluation", "create", {"employee_id": emp, "period_id": period_id})
        s.add_cleanup(lambda i=ev: _force_unlink_evaluation(s, i))
        evs.append(ev)
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [evs[1]])
    s.call("admin", "kpi.evaluation.line", "write",
           s.call("admin", "kpi.evaluation.line", "search", [("evaluation_id", "=", evs[1])]), {"actual": 100, "volume": 100})
    s.call("admin", "kpi.evaluation", "action_submit", [evs[1]])
    s.call("admin", "kpi.evaluation", "action_approve", [evs[1]])
    row = s.call("admin", "kpi.period", "read", [period_id], fields=[
        "dashboard_total_count", "dashboard_draft_count", "dashboard_approved_count", "dashboard_avg_score"])[0]
    final = s.call("admin", "kpi.evaluation", "read", [evs[1]], fields=["final_score"])[0]["final_score"]
    action = s.call("admin", "kpi.period", "action_open_approved", [period_id])
    opened = s.call("admin", "kpi.evaluation", "search", action["domain"])
    if (row["dashboard_total_count"], row["dashboard_draft_count"], row["dashboard_approved_count"]) == (2, 1, 1) \
            and abs(row["dashboard_avg_score"] - final) < 0.01 and opened == [evs[1]]:
        s.ok("Màn hình tổng quan: số liệu kỳ khớp (2 phiếu = 1 Nháp + 1 Đã duyệt, điểm TB = điểm phiếu đã duyệt), nút mở đúng phiếu")
    else:
        s.fail("Màn hình tổng quan", f"số liệu/nút không khớp: {row}, nút mở {opened}")


def _module_installed(s, name):
    return bool(s.call("admin", "ir.module.module", "search_count", [("name", "=", name), ("state", "=", "installed")]))


def check_skills_bridge(s):
    """Đợt D2: chỉ chạy khi module project_kpi_skills đã cài. Chức danh yêu cầu Python 75, Odoo 50, SQL 50; nhân viên có
    Python 100, Odoo 50, SQL 25 → đạt 2/3 → S1 = 66,67%, mục tiêu 80% → điểm dòng 83,33 (tính tay trước khi chạy)."""
    if not _module_installed(s, "project_kpi_skills"):
        print("[SKIP] S1 (mức đáp ứng kỹ năng): module project_kpi_skills chưa cài trên database này")
        return
    suffix = time.strftime("%H%M%S")
    skill_type = s.call("admin", "hr.skill.type", "create", {
        "name": f"Kỹ năng kiểm tra {suffix}",
        "skill_ids": [(0, 0, {"name": n}) for n in ("Python", "Odoo", "SQL")],
        "skill_level_ids": [(0, 0, {"name": f"M{p}", "level_progress": p}) for p in (25, 50, 75, 100)],
    })
    s.add_cleanup(lambda: s.call("admin", "hr.skill.type", "unlink", [skill_type]))
    type_row = s.call("admin", "hr.skill.type", "read", [skill_type], fields=["skill_ids", "skill_level_ids"])[0]
    skills = {r["name"]: r["id"] for r in s.call("admin", "hr.skill", "read", type_row["skill_ids"], fields=["name"])}
    levels = {r["level_progress"]: r["id"] for r in s.call("admin", "hr.skill.level", "read", type_row["skill_level_ids"], fields=["level_progress"])}
    _, template_id = s.ref("project_kpi_skills.kpi_template_developer_skills")
    job_id = s.call("admin", "hr.job", "create", {"name": f"Dev kỹ năng kiểm tra {suffix}", "kpi_template_id": template_id})
    s.add_cleanup(lambda: s.call("admin", "hr.job", "unlink", [job_id]))
    for name, progress in (("Python", 75), ("Odoo", 50), ("SQL", 50)):
        s.call("admin", "hr.job.skill", "create", {
            "job_id": job_id, "skill_type_id": skill_type, "skill_id": skills[name], "skill_level_id": levels[progress],
            "valid_from": "2000-01-01",
        })
    _, _, employee_id, _ = _make_pm(s, suffix + "k", "project_kpi_management.hr_job_developer")
    s.call("admin", "hr.employee", "write", [employee_id], {"job_id": job_id})
    for name, progress in (("Python", 100), ("Odoo", 50), ("SQL", 25)):
        s.call("admin", "hr.employee.skill", "create", {
            "employee_id": employee_id, "skill_type_id": skill_type, "skill_id": skills[name],
            "skill_level_id": levels[progress], "valid_from": "2000-01-01",
        })
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra kỹ năng {suffix}", "period_type": "month", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    ev_id = create_evaluation(s, None, period_id, employee_id=employee_id)
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    line = s.call("admin", "kpi.evaluation.line", "search_read",
                  [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "S1")], fields=["actual", "volume", "score"])[0]
    if abs(line["actual"] - 200 / 3) < 0.01 and line["volume"] == 3 and abs(line["score"] - 200 / 3 / 80 * 100) < 0.01:
        s.ok("S1 mức đáp ứng kỹ năng: 2/3 kỹ năng đạt → 66,67%, điểm dòng 83,33, khớp bảng tính tay")
    else:
        s.fail("S1 mức đáp ứng kỹ năng", f"mong đợi 66,67 / khối lượng 3 / điểm 83,33, thực tế {line}")


def check_feedback_bridge(s):
    """Đợt D1: chỉ chạy khi module project_kpi_survey đã cài. Quản lý (đăng nhập thật) mời 3 người đánh giá 360 cho một phiếu
    Nháp: mỗi người nhận đúng 1 nhắc việc kèm link, người được mời chỉ thấy lời mời của mình, quản lý KHÔNG đọc được
    survey.user_input (không xem được từng câu trả lời), và chưa có câu trả lời nào thì F1 là "Không áp dụng".
    (Việc trả lời khảo sát đi qua controller của module survey nên được kiểm bằng unit test, không qua XML-RPC.)"""
    if not _module_installed(s, "project_kpi_survey"):
        print("[SKIP] F1 (phản hồi 360): module project_kpi_survey chưa cài trên database này")
        return
    suffix = time.strftime("%H%M%S")
    _, g_user = s.ref("base.group_user")
    _, g_manager = s.ref("project_kpi_management.group_kpi_manager")
    _, job_id = s.ref("project_kpi_management.hr_job_developer")
    _, template_id = s.ref("project_kpi_survey.kpi_template_developer_360")
    _, act_type = s.ref("project_kpi_survey.mail_activity_type_feedback")

    def make_user(tag, groups):
        login = f"chk_fb_{tag}_{suffix}"
        s.passwords[login] = login
        uid = s.call("admin", "res.users", "create", {
            "name": f"FB {tag} {suffix}", "login": login, "password": login, "group_ids": [(6, 0, groups)],
        })

        def drop():
            try:
                s.call("admin", "res.users", "unlink", [uid])
            except xmlrpc.client.Fault:
                s.call("admin", "res.users", "write", [uid], {"active": False})
        s.add_cleanup(drop)
        return login, uid

    mgr_login, mgr_uid = make_user("mgr", [g_user, g_manager])
    emp_login, emp_uid = make_user("emp", [g_user])
    reviewers = [make_user(f"rev{i}", [g_user]) for i in range(3)]
    mgr_emp = s.call("admin", "hr.employee", "create", {"name": f"FB quản lý {suffix}", "user_id": mgr_uid})
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [mgr_emp]))
    emp_id = s.call("admin", "hr.employee", "create", {
        "name": f"FB nhân viên {suffix}", "user_id": emp_uid, "job_id": job_id, "parent_id": mgr_emp,
    })
    s.add_cleanup(lambda: s.call("admin", "hr.employee", "unlink", [emp_id]))
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra 360 {suffix}", "period_type": "month", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    ev_id = s.call("admin", "kpi.evaluation", "create", {"employee_id": emp_id, "period_id": period_id, "template_id": template_id})
    s.add_cleanup(lambda: _force_unlink_evaluation(s, ev_id))

    def drop_answers():  # câu trả lời khảo sát không tự xoá theo phiếu
        ids = [r["user_input_id"][0] for r in s.call("admin", "kpi.feedback.request", "search_read", [("evaluation_id", "=", ev_id)],
                                                    fields=["user_input_id"]) if r["user_input_id"]]
        if ids:
            s.call("admin", "survey.user_input", "unlink", ids)
    s.add_cleanup(drop_answers)

    wiz = s.call(mgr_login, "kpi.feedback.invite.wizard", "create", {
        "evaluation_id": ev_id, "reviewer_ids": [(6, 0, [uid for _, uid in reviewers])],
    })
    s.call(mgr_login, "kpi.feedback.invite.wizard", "action_invite", [wiz])
    requests = s.call("admin", "kpi.feedback.request", "search", [("evaluation_id", "=", ev_id)])
    per_reviewer_ok = all(
        s.call("admin", "mail.activity", "search_count", [("res_model", "=", "kpi.feedback.request"), ("res_id", "in", requests),
                                                           ("activity_type_id", "=", act_type), ("user_id", "=", uid)]) == 1
        for _, uid in reviewers
    )
    own_ok = len(s.call(reviewers[0][0], "kpi.feedback.request", "search", [])) == 1
    try:
        s.call(mgr_login, "survey.user_input", "search", [])
        hidden_ok = False
    except xmlrpc.client.Fault:
        hidden_ok = True
    try:
        s.call(emp_login, "kpi.feedback.invite.wizard", "create", {"evaluation_id": ev_id})
        employee_blocked = False
    except xmlrpc.client.Fault:
        employee_blocked = True
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    f1 = s.call("admin", "kpi.evaluation.line", "search_read", [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "F1")],
                fields=["volume", "is_applicable"])[0]
    if len(requests) == 3 and per_reviewer_ok and own_ok and hidden_ok and employee_blocked and f1["volume"] == 0 and not f1["is_applicable"]:
        s.ok("Phản hồi 360: mời 3 người → 3 nhắc việc riêng; người được mời chỉ thấy lời mời của mình; quản lý không đọc được câu trả lời; F1 chưa có câu trả lời thì Không áp dụng")
    else:
        s.fail("Phản hồi 360", f"requests={len(requests)} nhắc_việc={per_reviewer_ok} chỉ_thấy_của_mình={own_ok} "
                               f"ẩn_câu_trả_lời={hidden_ok} nhân_viên_không_mời={employee_blocked} F1={f1}")


def check_timesheet_bridge(s):
    """Bước 4 (P4): chỉ chạy khi module cầu nối project_kpi_timesheet đã cài. Dự án giờ kế hoạch 100, thực tế 130
    → lệch 30%; mục tiêu 15 (thấp tốt) → 15/30 = 50 điểm. Tính tay trước khi chạy."""
    installed = s.call("admin", "ir.module.module", "search_count",
                       [("name", "=", "project_kpi_timesheet"), ("state", "=", "installed")])
    if not installed:
        print("[SKIP] P4 (giờ so với kế hoạch): module project_kpi_timesheet chưa cài trên database này")
        return
    suffix = time.strftime("%H%M%S")
    _, user_id, employee_id, project_id = _make_pm(s, suffix + "t")
    s.call("admin", "project.project", "write", [project_id], {"allow_timesheets": True, "allocated_hours": 100})
    task_id = s.call("admin", "project.task", "create", {"name": "T", "project_id": project_id})
    s.add_cleanup(lambda: s.call("admin", "project.task", "unlink", [task_id]))
    line_id = s.call("admin", "account.analytic.line", "create", {
        "name": "giờ", "project_id": project_id, "task_id": task_id, "unit_amount": 130, "employee_id": employee_id,
    })
    s.add_cleanup(lambda: s.call("admin", "account.analytic.line", "unlink", [line_id]))
    _, template_id = s.ref("project_kpi_timesheet.kpi_template_lead_timesheet")
    period_id = s.call("admin", "kpi.period", "create", {
        "name": f"Kiểm tra P4 {suffix}", "period_type": "sprint", "date_from": "2000-01-01", "date_to": "2099-12-31",
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.period", "unlink", [period_id]))
    ev_id = s.call("admin", "kpi.evaluation", "create", {"employee_id": employee_id, "period_id": period_id, "template_id": template_id})
    s.add_cleanup(lambda: _force_unlink_evaluation(s, ev_id))
    s.call("admin", "kpi.evaluation", "action_compute_kpi", [ev_id])
    line = s.call("admin", "kpi.evaluation.line", "search_read",
                  [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "P4")], fields=["actual", "score"])[0]
    if abs(line["actual"] - 30) < 0.01 and abs(line["score"] - 50) < 0.01:
        s.ok("P4: 130/100 giờ → lệch 30%, ra 50 điểm, khớp bảng tính tay")
    else:
        s.fail("P4 giờ so với kế hoạch", f"mong đợi lệch 30 / 50 điểm, thực tế {line}")


def check_target_override(s, period_id):
    """Mục 4: mục tiêu riêng theo phòng ban được áp dụng khi tạo phiếu mới."""
    _, chi_id = s.ref("project_kpi_management.demo_employee_chi")
    department_id = s.call("admin", "hr.employee", "read", [chi_id], fields=["department_id"])[0]["department_id"][0]
    _, template_id = s.ref("project_kpi_management.kpi_template_developer")
    d1_lines = s.call("admin", "kpi.template.line", "search",
                       [("template_id", "=", template_id), ("metric_id.code", "=", "D1")])
    original_target = s.call("admin", "kpi.template.line", "read", [d1_lines[0]], fields=["target"])[0]["target"]
    override_target = original_target + 7
    override_id = s.call("admin", "kpi.target.override", "create", {
        "template_line_id": d1_lines[0], "department_id": department_id, "target": override_target,
    })
    s.add_cleanup(lambda: s.call("admin", "kpi.target.override", "unlink", [override_id]))

    ev_id = create_evaluation(s, "project_kpi_management.demo_employee_chi", period_id)
    line = s.call("admin", "kpi.evaluation.line", "search_read",
                   [("evaluation_id", "=", ev_id), ("metric_id.code", "=", "D1")], fields=["target"])[0]
    if line["target"] == override_target:
        s.ok("Mục tiêu theo phòng ban: phiếu mới nhận đúng mục tiêu riêng")
    else:
        s.fail("Mục tiêu theo phòng ban", f"mong đợi {override_target}, thực tế {line['target']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--db", required=True)
    parser.add_argument("--admin-password", default=DEMO_LOGINS["admin"])
    parser.add_argument("--quocviet-password", default=DEMO_LOGINS["quocviet"])
    parser.add_argument("--an-password", default=DEMO_LOGINS["an"])
    parser.add_argument("--skip-demo-checks", action="store_true",
                        help="Chỉ chạy các bước tự tạo dữ liệu (Tester, Lead/PM, P4) — dùng cho database không có dữ liệu mẫu")
    args = parser.parse_args()

    passwords = {
        "admin": args.admin_password,
        "quocviet": args.quocviet_password,
        "an": args.an_password,
    }
    s = Session(args.url, args.db, passwords)
    try:
        period_id = make_test_period(s)
        if not args.skip_demo_checks:
            ensure_demo_loaded(s)
            check_role_conflict_and_pip(s, period_id)
            check_self_assessment(s, period_id)
            check_target_override(s, period_id)
            check_default_approver(s)
        check_tester(s, period_id)
        check_lead(s)
        check_ba(s)
        check_workflow(s)
        check_period_type_and_suggestion(s)
        check_dashboard(s)
        check_skills_bridge(s)
        check_feedback_bridge(s)
        check_timesheet_bridge(s)
    finally:
        s.run_cleanups()

    print()
    if s.failures:
        print(f"KẾT QUẢ: {len(s.failures)} mục FAIL — {', '.join(s.failures)}")
        sys.exit(1)
    print("KẾT QUẢ: tất cả OK — có thể demo.")


if __name__ == "__main__":
    main()
