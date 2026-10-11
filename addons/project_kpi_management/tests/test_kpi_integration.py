import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


class KpiFixtureMixin:
    """Quản lý + nhân viên trong nhóm + nhân viên nhóm khác, cùng chức danh Developer."""

    @classmethod
    def _setup_people(cls, prefix):
        env = cls.env
        cls.template = env.ref("project_kpi_management.kpi_template_developer")
        cls.job = env["hr.job"].create({"name": f"Dev {prefix}", "kpi_template_id": cls.template.id})
        cls.manager = new_test_user(env, login=f"{prefix}_mgr", groups="base.group_user,project_kpi_management.group_kpi_manager")
        cls.dev = new_test_user(env, login=f"{prefix}_dev", groups="base.group_user")
        cls.outsider = new_test_user(env, login=f"{prefix}_out", groups="base.group_user")
        Employee = env["hr.employee"]
        cls.emp_manager = Employee.create({"name": f"{prefix} quản lý", "user_id": cls.manager.id})
        cls.emp_dev = Employee.create({"name": f"{prefix} dev", "user_id": cls.dev.id, "job_id": cls.job.id,
                                       "parent_id": cls.emp_manager.id})
        cls.emp_out = Employee.create({"name": f"{prefix} nhóm khác", "user_id": cls.outsider.id, "job_id": cls.job.id})


@tagged("post_install", "-at_install")
class TestKpiCronReport(KpiFixtureMixin, TransactionCase):
    """Phase 9: tác vụ cuối kỳ, báo cáo PDF."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_people("cron")
        today = fields.Date.today()
        Period = cls.env["kpi.period"]
        # Kỳ mẫu (nếu có) đã hết hạn: đánh dấu đã chạy để test chỉ xét kỳ của test
        Period.search([]).write({"auto_generated": True})
        cls.past = Period.create({"name": "Kỳ đã qua", "date_from": today - timedelta(days=40), "date_to": today - timedelta(days=1)})
        cls.current = Period.create({"name": "Kỳ đang chạy", "date_from": today - timedelta(days=5), "date_to": today + timedelta(days=5)})

    def test_cron_generates_once_for_finished_periods(self):
        self.env["kpi.period"]._cron_generate_evaluations()
        self.assertTrue(self.past.auto_generated)
        employees = self.past.evaluation_ids.employee_id  # gồm cả nhân viên mẫu nếu database có demo
        self.assertTrue(self.emp_dev | self.emp_out <= employees)
        self.assertNotIn(self.emp_manager, employees)  # chức danh chưa gắn bộ KPI: bỏ qua
        self.assertTrue(all(self.past.evaluation_ids.mapped("computed_date")))
        self.assertFalse(self.current.evaluation_ids)  # kỳ chưa kết thúc: chưa tạo
        count = len(self.past.evaluation_ids)
        self.env["kpi.period"]._cron_generate_evaluations()
        self.assertEqual(len(self.past.evaluation_ids), count)  # chạy lại không tạo trùng

    def test_cron_skips_closed_period(self):
        self.past.action_close()
        self.env["kpi.period"]._cron_generate_evaluations()
        self.assertFalse(self.past.evaluation_ids)

    def test_pdf_report_content(self):
        ev = self.env["kpi.evaluation"].create({"employee_id": self.emp_dev.id, "period_id": self.current.id})
        ev.line_ids.filtered(lambda l: l.metric_id.code == "D9").actual = 4
        html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "project_kpi_management.action_report_kpi_evaluation", ev.ids)
        html = html.decode()
        for text in ("Phiếu đánh giá KPI", self.emp_dev.name, "D9", "Điểm cuối", self.emp_manager.name):
            self.assertIn(text, html)


@tagged("post_install", "-at_install")
class TestKpiApi(KpiFixtureMixin, HttpCase):
    """Phase 9: REST API, xác thực bằng API key (Bearer), tuân theo phân quyền KPI."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_people("api")
        today = fields.Date.today()
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ API", "date_from": today - timedelta(days=10), "date_to": today})
        cls.ev_dev = cls.env["kpi.evaluation"].create({"employee_id": cls.emp_dev.id, "period_id": cls.period.id})
        cls.ev_out = cls.env["kpi.evaluation"].create({"employee_id": cls.emp_out.id, "period_id": cls.period.id})
        expiration = fields.Datetime.now() + timedelta(days=1)
        Keys = cls.env["res.users.apikeys"]
        cls.key_manager = Keys.with_user(cls.manager)._generate(None, "test", expiration)
        cls.key_dev = Keys.with_user(cls.dev)._generate(None, "test", expiration)

    def _call(self, path, key=None, payload=None):
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        if payload is None:
            response = self.url_open(path, headers=headers)
        else:
            headers["Content-Type"] = "application/json"
            response = self.url_open(path, data=json.dumps(payload), headers=headers)
        return response.status_code, (response.json() if response.headers.get("Content-Type", "").startswith("application/json") else None)

    def test_requires_api_key(self):
        status, _ = self._call("/api/kpi/evaluations")
        self.assertEqual(status, 401)
        status, _ = self._call("/api/kpi/evaluations", key="sai-key")
        self.assertEqual(status, 401)

    def test_list_respects_record_rules(self):
        status, body = self._call(f"/api/kpi/evaluations?period_id={self.period.id}", key=self.key_manager)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in body["items"]], [self.ev_dev.id])  # không thấy phiếu nhóm khác
        status, body = self._call(f"/api/kpi/evaluations?period_id={self.period.id}", key=self.key_dev)
        self.assertEqual(body["count"], 1)

    def test_detail_and_not_found(self):
        status, body = self._call(f"/api/kpi/evaluations/{self.ev_dev.id}", key=self.key_manager)
        self.assertEqual(status, 200)
        self.assertEqual(len(body["lines"]), 9)
        self.assertEqual(body["employee"]["id"], self.emp_dev.id)
        status, _ = self._call(f"/api/kpi/evaluations/{self.ev_out.id}", key=self.key_manager)
        self.assertEqual(status, 404)  # có tồn tại nhưng không được xem: trả 404, không lộ thông tin

    def test_post_manual_metric(self):
        url = f"/api/kpi/evaluations/{self.ev_dev.id}/metrics/D9"
        status, body = self._call(url, key=self.key_manager, payload={"actual": 5, "remark": "Hỗ trợ đồng nghiệp tốt"})
        self.assertEqual(status, 200)
        d9 = next(line for line in body["lines"] if line["metric"] == "D9")
        self.assertEqual((d9["actual"], d9["score"], d9["remark"]), (5.0, 120.0, "Hỗ trợ đồng nghiệp tốt"))
        self.assertTrue(self.ev_dev.line_ids.filtered(lambda l: l.metric_id.code == "D9").actual_entered)

    def test_post_rejected(self):
        base = f"/api/kpi/evaluations/{self.ev_dev.id}/metrics"
        status, _ = self._call(f"{base}/D1", key=self.key_manager, payload={"actual": 90})
        self.assertEqual(status, 400)  # chỉ số tự động
        status, _ = self._call(f"{base}/D9", key=self.key_manager, payload={"value": 4})
        self.assertEqual(status, 400)  # thiếu trường actual
        status, _ = self._call(f"{base}/XX", key=self.key_manager, payload={"actual": 4})
        self.assertEqual(status, 404)
        status, _ = self._call(f"{base}/D9", key=self.key_dev, payload={"actual": 5})
        self.assertEqual(status, 403)  # nhân viên chỉ được xem phiếu của mình, không được sửa
