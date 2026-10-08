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

        # Quản lý trực tiếp: Marc Demo (KPI Manager). Admin là KPI Administrator.
        manager_user = self.env.ref("base.user_demo")
        manager_user.group_ids = [(4, self.env.ref(XMLID % "group_kpi_manager").id)]
        manager_employee = manager_user.employee_ids[:1]

        employees = {}
        for key, name, login in (("an", "Nguyễn Văn An", "an"), ("binh", "Trần Thị Bình", "binh"), ("chi", "Lê Minh Chi", "chi")):
            user = self.env["res.users"].create({
                "name": name, "login": login, "password": login, "tz": tz.zone,
            })
            employee = self.env["hr.employee"].create({
                "name": name,
                "user_id": user.id,
                "job_id": self.env.ref("hr.job_developer").id,
                "department_id": self.env.ref("hr.dep_rd").id,
                "parent_id": manager_employee.id,
            })
            employees[key] = employee
            xmlids += [(f"demo_user_{key}", user), (f"demo_employee_{key}", employee)]

        project = self.env["project.project"].create({
            "name": "Website bán hàng (dữ liệu mẫu KPI)",
            "type_ids": [(6, 0, [self.env.ref("project.project_stage_0").id,
                                 self.env.ref("project.project_stage_1").id,
                                 self.env.ref("project.project_stage_2").id])],
        })
        done_stage = self.env.ref("project.project_stage_2")
        Task = self.env["project.task"]

        def task(key, owner, name, sp=0, deadline=None, done=None, approve=0, reject=0, unit=False,
                 task_type="feature", **bug):
            created = bug.pop("created", None)
            t = Task.create({
                "name": name, "project_id": project.id, "user_ids": [(6, 0, [employees[owner].user_id.id])],
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
