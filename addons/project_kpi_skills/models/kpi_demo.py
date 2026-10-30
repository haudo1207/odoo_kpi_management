from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, models

XMLID = "project_kpi_skills.%s"


class KpiDemo(models.AbstractModel):
    _inherit = "kpi.demo"

    @api.model
    def _load_scenario(self):
        super()._load_scenario()
        self._load_skills_scenario()

    @api.model
    def _load_skills_scenario(self):
        """Dữ liệu mẫu D2 (tính tay): loại kỹ năng "Kỹ năng kỹ thuật" 4 mức 25/50/75/100; chức danh Lập trình viên yêu cầu
        Python 75, Odoo 50, SQL 50; An có Python 100, Odoo 50, SQL 25 → đạt 2/3 → S1 = 66,67%. Idempotent, và chỉ nạp khi
        kịch bản mẫu chính đã có nhân viên An. Tách hồ sơ kỹ năng (idempotent riêng) khỏi phiếu minh hoạ S1 bên dưới,
        để gọi lại không bỏ sót phiếu nếu lần trước dừng giữa chừng."""
        an = self.env.ref("project_kpi_management.demo_employee_an", raise_if_not_found=False)
        job = self.env.ref("project_kpi_management.hr_job_developer", raise_if_not_found=False)
        if not an or not job:
            return
        if not self.env.ref(XMLID % "demo_skill_type", raise_if_not_found=False):
            levels = [("Cơ bản", 25), ("Khá", 50), ("Tốt", 75), ("Thành thạo", 100)]
            skill_type = self.env["hr.skill.type"].create({
                "name": "Kỹ năng kỹ thuật",
                "skill_ids": [(0, 0, {"name": name}) for name in ("Python", "Odoo", "SQL")],
                "skill_level_ids": [(0, 0, {"name": name, "level_progress": progress}) for name, progress in levels],
            })
            level = {lv.level_progress: lv for lv in skill_type.skill_level_ids}
            skill = {s.name: s for s in skill_type.skill_ids}
            for name, progress in (("Python", 75), ("Odoo", 50), ("SQL", 50)):
                self.env["hr.job.skill"].create({
                    "job_id": job.id, "skill_type_id": skill_type.id, "skill_id": skill[name].id,
                    "skill_level_id": level[progress].id,
                })
            for name, progress in (("Python", 100), ("Odoo", 50), ("SQL", 25)):
                self.env["hr.employee.skill"].create({
                    "employee_id": an.id, "skill_type_id": skill_type.id, "skill_id": skill[name].id,
                    "skill_level_id": level[progress].id,
                })
            self.env["ir.model.data"]._update_xmlids([
                {"xml_id": XMLID % "demo_skill_type", "record": skill_type, "noupdate": True},
            ])
        self._load_skills_evaluation_demo(an)

    @api.model
    def _load_skills_evaluation_demo(self, an):
        """Phiếu minh hoạ S1 trên bộ "Developer (có năng lực)" (Chương 9.6/Phần 5 kịch bản demo): kỳ
        riêng, ngay sau kỳ mẫu chính, không đụng số liệu D1–D9 của An ở kỳ chính. Chỉ cần "Tính KPI"
        là thấy ngay S1 = 66,67% — không phải tự tạo phiếu bằng tay trước khi demo."""
        if self.env.ref(XMLID % "demo_period_skills", raise_if_not_found=False):
            return
        start = date.today().replace(day=1)
        end = start + relativedelta(months=1) - timedelta(days=1)
        period = self.env["kpi.period"].create({
            "name": f"Tháng {start:%m/%Y} (mẫu năng lực)", "period_type": "month",
            "date_from": start, "date_to": end,
        })
        template = self.env.ref(XMLID % "kpi_template_developer_skills")
        ev = self.env["kpi.evaluation"].create({
            "employee_id": an.id, "period_id": period.id, "template_id": template.id,
        })
        ev.action_compute_kpi()
        self.env["ir.model.data"]._update_xmlids([
            {"xml_id": XMLID % "demo_period_skills", "record": period, "noupdate": True},
            {"xml_id": XMLID % "demo_evaluation_skills", "record": ev, "noupdate": True},
        ])
