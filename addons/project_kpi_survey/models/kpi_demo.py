from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, models

XMLID = "project_kpi_survey.%s"


class KpiDemo(models.AbstractModel):
    _inherit = "kpi.demo"

    @api.model
    def _load_scenario(self):
        super()._load_scenario()
        self._load_feedback_scenario()

    @api.model
    def _load_feedback_scenario(self):
        """Phiếu minh hoạ F1/phản hồi 360 (Chương 9.6/Phần 4 kịch bản demo): phiếu Nháp của Chi, bộ
        "Developer (có phản hồi 360)", kỳ riêng ngay sau kỳ mẫu chính — cố ý CHƯA mời ai, để buổi demo
        mời trực tiếp 3 người trên sân khấu (test_invite_rules/test_reminder... đã kiểm hành vi mời,
        đây chỉ chuẩn bị đúng dữ liệu nền). Idempotent, chỉ nạp khi kịch bản mẫu chính đã có nhân viên Chi."""
        chi = self.env.ref("project_kpi_management.demo_employee_chi", raise_if_not_found=False)
        if not chi or self.env.ref(XMLID % "demo_period_feedback", raise_if_not_found=False):
            return
        start = date.today().replace(day=1)
        end = start + relativedelta(months=1) - timedelta(days=1)
        period = self.env["kpi.period"].create({
            "name": f"Tháng {start:%m/%Y} (mẫu phản hồi 360)", "period_type": "month",
            "date_from": start, "date_to": end,
        })
        template = self.env.ref(XMLID % "kpi_template_developer_360")
        ev = self.env["kpi.evaluation"].create({
            "employee_id": chi.id, "period_id": period.id, "template_id": template.id,
        })
        self.env["ir.model.data"]._update_xmlids([
            {"xml_id": XMLID % "demo_period_feedback", "record": period, "noupdate": True},
            {"xml_id": XMLID % "demo_evaluation_feedback", "record": ev, "noupdate": True},
        ])
