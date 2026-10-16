#!/usr/bin/env python3
"""Kiểm tra nhanh trước buổi bảo vệ — chạy qua XML-RPC thật, đăng nhập bằng đúng tài khoản sẽ
dùng khi demo (admin, quocviet, an), không phải TransactionCase giả lập (TransactionCase chạy
bằng superuser nên env.su=True, bỏ qua một số kiểm tra chỉ áp dụng cho người dùng thật — xem
Chương 5.4 trong PHASE_11_TAI_LIEU_DU_AN.md).

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
    args = parser.parse_args()

    passwords = {
        "admin": args.admin_password,
        "quocviet": args.quocviet_password,
        "an": args.an_password,
    }
    s = Session(args.url, args.db, passwords)
    try:
        ensure_demo_loaded(s)
        period_id = make_test_period(s)
        check_role_conflict_and_pip(s, period_id)
        check_self_assessment(s, period_id)
        check_target_override(s, period_id)
        check_tester(s, period_id)
    finally:
        s.run_cleanups()

    print()
    if s.failures:
        print(f"KẾT QUẢ: {len(s.failures)} mục FAIL — {', '.join(s.failures)}")
        sys.exit(1)
    print("KẾT QUẢ: tất cả OK — có thể demo.")


if __name__ == "__main__":
    main()
