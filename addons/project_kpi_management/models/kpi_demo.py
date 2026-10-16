from datetime import date, datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, models

XMLID = "project_kpi_management.%s"


class KpiDemo(models.AbstractModel):
    """Nạp kịch bản dữ liệu mẫu cho 3 nhân viên (chỉ gọi từ data/kpi_demo.xml).

    Kịch bản nằm ở tháng trước so với ngày cài, mốc là thứ Hai đầu tiên của tháng (M).
    Kết quả mong đợi của từng chỉ số có trong bảng tính tay của lộ trình
    và được kiểm bằng tests/test_kpi_demo_scenario.py.
    Viết bằng Python vì phải ghi date_end và create_date sau khi tạo task: Odoo ghi đè
    date_end theo stage khi tạo, và create_date không ghi được qua ORM (D7 tính từ đó).
    """

    _name = "kpi.demo"
    _description = "Dữ liệu mẫu KPI"

    @api.model
    def _load_scenario(self):
        # Người duyệt mặc định = admin, để demo thấy ngay nhắc việc duyệt phiếu mà không phải nhớ vào Thiết lập.
        # Chỉ đặt trong dữ liệu mẫu (không phải data của module) và không ghi đè giá trị đã có: doanh nghiệp thật tự cấu hình.
        # admin không là quản lý trực tiếp của nhân viên mẫu nào nên không vướng quy tắc xung đột vai trò.
        params = self.env["ir.config_parameter"].sudo()
        if not params.get_param("project_kpi_management.default_approver_id"):
            params.set_param("project_kpi_management.default_approver_id", str(self.env.ref("base.user_admin").id))
        if self.env.ref(XMLID % "demo_period_previous_month", raise_if_not_found=False):
            return  # demo được nạp lại khi -u: không tạo trùng
        today = date.today()
        first = (today.replace(day=1) - relativedelta(months=1))
        last = today.replace(day=1) - timedelta(days=1)
        monday = first + timedelta(days=(7 - first.weekday()) % 7)
        tz = pytz.timezone(self.env.company.resource_calendar_id.tz or "UTC")

        def at(day, hour):
            """Ngày M+day, giờ địa phương → Datetime UTC (naive) để ghi vào Odoo."""
            local = tz.localize(datetime.combine(monday + timedelta(days=day), datetime.min.time()) + timedelta(hours=hour))
            return local.astimezone(pytz.utc).replace(tzinfo=None)

        xmlids = []
        period = self.env["kpi.period"].create({
            "name": f"Tháng {first:%m/%Y} (dữ liệu mẫu)",
            "period_type": "month",
            "date_from": first,
            "date_to": last,
        })
        xmlids.append(("demo_period_previous_month", period))

        # Quản lý trực tiếp: tự tạo, không mượn nhân viên demo gốc của Odoo (base.user_demo),
        # để kịch bản mẫu của module KPI không lẫn tên/phòng ban tiếng Anh của Odoo.
        dev_job = self.env.ref(XMLID % "hr_job_developer")
        department = dev_job.department_id
        manager_user = self.env["res.users"].create({
            "name": "Phạm Quốc Việt", "login": "quocviet", "password": "quocviet", "tz": tz.zone,
            "group_ids": [(4, self.env.ref(XMLID % "group_kpi_manager").id)],
        })
        manager_employee = self.env["hr.employee"].create({
            "name": "Phạm Quốc Việt",
            "user_id": manager_user.id,
            "job_id": self.env.ref(XMLID % "hr_job_manager").id,
            "department_id": department.id,
        })
        xmlids += [("demo_user_manager", manager_user), ("demo_employee_manager", manager_employee)]

        employees = {}
        for key, name, login in (("an", "Nguyễn Văn An", "an"), ("binh", "Trần Thị Bình", "binh"), ("chi", "Lê Minh Chi", "chi")):
            user = self.env["res.users"].create({
                "name": name, "login": login, "password": login, "tz": tz.zone,
            })
            employee = self.env["hr.employee"].create({
                "name": name,
                "user_id": user.id,
                "job_id": dev_job.id,
                "department_id": department.id,
                "parent_id": manager_employee.id,
            })
            employees[key] = employee
            xmlids += [(f"demo_user_{key}", user), (f"demo_employee_{key}", employee)]

        # Stage riêng của dự án mẫu, không mượn project.project_stage_0/1/2 (chỉ có khi cài
        # --with-demo của module project) — nhờ vậy kịch bản này cài được mà không cần demo gốc.
        Stage = self.env["project.task.type"]
        stage_new, stage_doing, done_stage = Stage.create([
            {"name": "Mới", "sequence": 1},
            {"name": "Đang làm", "sequence": 2},
            {"name": "Hoàn thành", "sequence": 3, "fold": True},
        ])
        # Phúc (PM, Bước 4): quản lý dự án mẫu — "dự án của Lead" xác định bằng project.user_id
        pm_user = self.env["res.users"].create({"name": "Hoàng Văn Phúc", "login": "phuc", "password": "phuc", "tz": tz.zone})
        pm_employee = self.env["hr.employee"].create({
            "name": "Hoàng Văn Phúc", "user_id": pm_user.id, "job_id": self.env.ref(XMLID % "hr_job_pm").id,
            "department_id": department.id, "parent_id": manager_employee.id,
        })
        xmlids += [("demo_user_phuc", pm_user), ("demo_employee_phuc", pm_employee)]
        project = self.env["project.project"].create({
            "name": "Website bán hàng (dữ liệu mẫu KPI)",
            "type_ids": [(6, 0, [stage_new.id, stage_doing.id, done_stage.id])],
            "user_id": pm_user.id,
        })
        # 3 milestone trong kỳ: đúng hạn, trễ 2 ngày, chưa đạt → P1 = 1/3. reached_date tự đặt bằng ngày hôm nay
        # khi tick is_reached nên ghi thẳng SQL để có ngày đạt trong quá khứ.
        Milestone = self.env["project.milestone"]
        for key, name, deadline_day, reached_day in (("m1", "Bản demo nội bộ", 5, 4), ("m2", "Thanh toán", 10, 12), ("m3", "Phát hành", 15, None)):
            milestone = Milestone.create({"name": name, "project_id": project.id, "deadline": monday + timedelta(days=deadline_day)})
            if reached_day is not None:
                Milestone.flush_model()
                self.env.cr.execute(
                    "UPDATE project_milestone SET is_reached = TRUE, reached_date = %s WHERE id = %s",
                    (monday + timedelta(days=reached_day), milestone.id),
                )
                milestone.invalidate_recordset()
                self.env.add_to_compute(Milestone._fields["is_reached_on_time"], milestone)
            xmlids.append((f"demo_milestone_{key}", milestone))
        Task = self.env["project.task"]

        def task(key, owner, name, sp=0, deadline=None, done=None, approve=0, reject=0, unit=False,
                 task_type="feature", **bug):
            created = bug.pop("created", None)
            target_project = bug.pop("project", None) or project
            t = Task.create({
                "name": name, "project_id": target_project.id, "user_ids": [(6, 0, [employees[owner].user_id.id])],
                "task_type": task_type, "story_points": sp, "has_unit_test": unit,
                "date_deadline": at(deadline, 18) if deadline is not None else False,
                **bug,
            })
            if done is not None:
                t.write({"stage_id": done_stage.id, "state": "1_done"})
                t.write({"date_end": done})  # ghi sau: Odoo đặt date_end = lúc ghi stage
            t.write({"review_approve_count": approve, "review_reject_count": reject})
            if created:
                # create_date không ghi được qua ORM; D7 = working_hours_close tính từ create_date
                self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id = %s", (created, t.id))
                t.invalidate_recordset(["create_date"])
                self.env.add_to_compute(Task._fields["working_hours_close"], t)
            xmlids.append((f"demo_task_{key}", t))
            return t

        # ---- An: hoàn thành tốt ----
        t1 = task("t1", "an", "Trang danh mục sản phẩm", sp=5, deadline=2, done=at(1, 10), approve=1, unit=True)
        t2 = task("t2", "an", "Giỏ hàng", sp=8, deadline=4, done=at(4, 10), approve=1, unit=True)
        t3 = task("t3", "an", "Thanh toán VNPay", sp=8, deadline=9, done=at(8, 10), approve=1, reject=1, unit=True)
        task("t4", "an", "Trang liên hệ", sp=3, deadline=11, done=at(11, 10), approve=1)
        bug_code = {"bug_root_cause": "code"}
        task("b1", "an", "Lỗi cộng sai số lượng giỏ hàng", task_type="bug", origin_task_id=t2.id,
             bug_resolution="valid", priority="2", done=at(7, 15), created=at(7, 9), **bug_code)
        task("b2", "an", "Lỗi timeout VNPay", task_type="bug", origin_task_id=t3.id,
             bug_resolution="valid", priority="1", done=at(9, 10), created=at(8, 9), **bug_code)
        task("b3", "an", "Lỗi ảnh danh mục (trùng)", task_type="bug", origin_task_id=t1.id,
             bug_resolution="duplicate", done=at(3, 10), **bug_code)

        # ---- Bình: trễ hạn, có lỗi production ----
        t5 = task("t5", "binh", "Đăng nhập Google", sp=5, deadline=1, done=at(3, 10), approve=1, reject=1, unit=True)
        t6 = task("t6", "binh", "Quản lý đơn hàng", sp=5, deadline=8, done=at(8, 10), approve=1)
        t7 = task("t7", "binh", "Mã giảm giá", sp=3, deadline=10, done=at(10, 10), approve=1, reject=2, unit=True)
        task("t8", "binh", "Báo cáo doanh thu", sp=3, deadline=15)  # quá hạn, chưa xong
        t9 = task("t9", "binh", "Xuất hoá đơn PDF", sp=2, deadline=16, done=at(16, 10), approve=1)
        task("b4", "binh", "Không đăng nhập được bằng Google", task_type="bug", origin_task_id=t5.id,
             bug_resolution="valid", is_production_bug=True, priority="3", done=at(15, 11), created=at(14, 9), **bug_code)
        task("b5", "binh", "Đơn hàng mất trạng thái", task_type="bug", origin_task_id=t6.id,
             bug_resolution="valid", priority="2", done=at(18, 17), created=at(14, 8), **bug_code)
        task("b6", "binh", "Mã giảm giá áp dụng hai lần", task_type="bug", origin_task_id=t7.id,
             bug_resolution="wont_fix", done=at(16, 10), **bug_code)
        task("b7", "binh", "Đơn hàng thiếu trường ghi chú", task_type="bug", origin_task_id=t6.id,
             bug_resolution="valid", bug_root_cause="requirement", done=at(17, 10))
        task("b8", "binh", "Sai số tiền trên hoá đơn", task_type="bug", origin_task_id=t9.id,
             bug_resolution="valid", priority="1", done=at(18, 10), **bug_code)

        # ---- Chi: mới vào giữa kỳ, chưa đủ dữ liệu ----
        task("t10", "chi", "Trang hồ sơ khách hàng", sp=3, deadline=18)

        # ---- Hà (Developer, cấp dưới thứ 3 của PM Phúc): đủ dữ liệu, ở dự án riêng ----
        # Để dự án chính (Phúc quản lý, P3 của Phúc và QA4 của Dung) không đổi. 3 Feature xong đúng hạn, đã qua review
        # lần đầu, có unit test, không bug: phiếu đủ dữ liệu → vào P2, khác Khoa (mới vào, thiếu dữ liệu → bị loại).
        ha_user = self.env["res.users"].create({"name": "Lý Thanh Hà", "login": "ha", "password": "ha", "tz": tz.zone})
        ha_employee = self.env["hr.employee"].create({
            "name": "Lý Thanh Hà", "user_id": ha_user.id, "job_id": dev_job.id,
            "department_id": department.id, "parent_id": pm_employee.id,
        })
        employees["ha"] = ha_employee
        xmlids += [("demo_user_ha", ha_user), ("demo_employee_ha", ha_employee)]
        second_project = self.env["project.project"].create({
            "name": "Ứng dụng di động (dữ liệu mẫu KPI)",
            "type_ids": [(6, 0, [stage_new.id, stage_doing.id, done_stage.id])],
        })
        for key, name, deadline, done in (("h1", "Màn hình đăng nhập", 4, 3), ("h2", "Danh sách đơn hàng", 9, 8), ("h3", "Thông báo đẩy", 14, 13)):
            task(key, "ha", name, sp=5, deadline=deadline, done=at(done, 10), approve=1, unit=True, project=second_project)

        # ---- Lan (BA, Bước 5): 3 yêu cầu trong dự án chính; bug b7 (nguyên nhân "yêu cầu sai") quy về Lan ----
        lan_user = self.env["res.users"].create({"name": "Trịnh Thu Lan", "login": "lan", "password": "lan", "tz": tz.zone})
        lan_employee = self.env["hr.employee"].create({
            "name": "Trịnh Thu Lan", "user_id": lan_user.id, "job_id": self.env.ref(XMLID % "hr_job_ba").id,
            "department_id": department.id, "parent_id": manager_employee.id,
        })
        employees["lan"] = lan_employee
        xmlids += [("demo_user_lan", lan_user), ("demo_employee_lan", lan_employee)]
        r1 = task("r1", "lan", "Yêu cầu: giỏ hàng", deadline=3, done=at(2, 10), approve=1, task_type="requirement")
        task("r2", "lan", "Yêu cầu: thanh toán", deadline=6, done=at(8, 10), approve=1, reject=1, task_type="requirement")
        task("r3", "lan", "Yêu cầu: báo cáo doanh thu", deadline=12, done=at(11, 10), approve=1, task_type="requirement")
        t6.requirement_id = r1  # t6 (Quản lý đơn hàng) hiện thực yêu cầu r1; b7 là bug "yêu cầu sai" của t6

        # ---- Dung (Tester, Bước 2): 10 bug tự log, bộ KPI Tester tự động ----
        # Bug không giao cho ai và nguyên nhân khác "code", nên không lọt vào D3/D4/D7 của An, Bình.
        tester_job = self.env.ref(XMLID % "hr_job_tester")
        dung_user = self.env["res.users"].create({
            "name": "Đỗ Thị Dung", "login": "dung", "password": "dung", "tz": tz.zone,
        })
        dung_employee = self.env["hr.employee"].create({
            "name": "Đỗ Thị Dung", "user_id": dung_user.id, "job_id": tester_job.id,
            "department_id": department.id, "parent_id": pm_employee.id,
        })
        # Khoa: tester mới vào, chưa log bug nào. Cùng Dung là 2 cấp dưới của PM Phúc — để demo P2 chuyển từ
        # "Không áp dụng" sang có số khi cả hai phiếu được Gửi duyệt (P2 cần ≥ 2 phiếu cấp dưới đã chốt).
        khoa_user = self.env["res.users"].create({"name": "Vũ Minh Khoa", "login": "khoa", "password": "khoa", "tz": tz.zone})
        khoa_employee = self.env["hr.employee"].create({
            "name": "Vũ Minh Khoa", "user_id": khoa_user.id, "job_id": tester_job.id,
            "department_id": department.id, "parent_id": pm_employee.id,
        })
        xmlids += [
            ("demo_user_dung", dung_user), ("demo_employee_dung", dung_employee),
            ("demo_user_khoa", khoa_user), ("demo_employee_khoa", khoa_employee),
        ]
        origins = [t1, t2, t3, t5, t6, t7, t9, t1]
        # (kết quả xử lý, nguyên nhân, có task gốc, lỗi production)
        dung_bugs = [("valid", "requirement")] * 5 + [
            ("valid", "environment"), ("wont_fix", "requirement"), ("duplicate", "requirement"),
            ("invalid", False), (False, False),
        ]
        for i, (resolution, cause) in enumerate(dung_bugs):
            bug = Task.create({
                "name": f"Bug tester Dung #{i + 1}", "project_id": project.id, "task_type": "bug",
                "bug_reporter_id": dung_user.id, "bug_resolution": resolution, "bug_root_cause": cause,
                "origin_task_id": origins[i].id if i < 8 else False,
                "is_production_bug": i == 5,
            })
            self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id = %s", (at(2 + i, 10), bug.id))
            bug.invalidate_recordset(["create_date"])
            xmlids.append((f"demo_task_dung_bug{i + 1}", bug))

        # ---- Lịch sử cho gợi ý mục tiêu (Đợt B2): phòng ban riêng, 4 kỳ đã duyệt, không đụng nhân viên của kịch bản chính ----
        # D2 (story point) lần lượt 12, 14, 16, 18 → gợi ý (cao là tốt): Dễ 13,5 / Vừa 15 / Khó 16,5
        history_department = self.env["hr.department"].create({"name": "Phòng Kỹ thuật (lịch sử mẫu)"})
        history_employee = self.env["hr.employee"].create({
            "name": "Ngô Minh Tuấn (lịch sử mẫu)", "job_id": dev_job.id, "department_id": history_department.id,
        })
        xmlids += [("demo_department_history", history_department), ("demo_employee_history", history_employee)]
        for months_back, sp in ((4, 12), (3, 14), (2, 16), (1, 18)):
            start = first - relativedelta(months=months_back)
            end = start + relativedelta(months=1) - timedelta(days=1)
            hist_period = self.env["kpi.period"].create({
                "name": f"Tháng {start:%m/%Y} (lịch sử mẫu)", "period_type": "month", "date_from": start, "date_to": end,
            })
            hist_ev = self.env["kpi.evaluation"].create({"employee_id": history_employee.id, "period_id": hist_period.id})
            hist_ev.line_ids.write({"volume": 10})  # mọi chỉ số được áp dụng → phiếu đủ dữ liệu
            hist_ev.line_ids.filtered(lambda l: l.metric_id.code == "D2").actual = sp
            hist_ev.write({"state": "approved", "approved_date": datetime.combine(end, datetime.min.time())})
            hist_period.state = "closed"

        # ---- D8: buổi chia sẻ kiến thức ----
        sharing = self.env.ref(XMLID % "calendar_event_type_knowledge_sharing")
        Event = self.env["calendar.event"].with_context(no_mail_to_attendees=True, mail_create_nosubscribe=True)
        for key, owner, name, day in (("e1", "an", "Chia sẻ: thanh toán VNPay", 10), ("e2", "binh", "Chia sẻ: OAuth Google", 17)):
            event = Event.create({
                "name": name, "user_id": employees[owner].user_id.id, "categ_ids": [(6, 0, [sharing.id])],
                "start": at(day, 14), "stop": at(day, 15),
            })
            xmlids.append((f"demo_event_{key}", event))

        Task.flush_model()
        self.env["ir.model.data"]._update_xmlids([
            {"xml_id": XMLID % name, "record": record, "noupdate": True} for name, record in xmlids
        ])
