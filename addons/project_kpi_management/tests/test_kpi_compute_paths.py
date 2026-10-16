import importlib.util
import json
from datetime import timedelta

from odoo import fields
from odoo.modules import get_module_path
from odoo.tests import Form, HttpCase, TransactionCase, new_test_user, tagged


class ComputePathFixture:
    """Một tester có 2 bug hợp lệ trong một kỳ đã qua (QA1 = 2), dùng để kiểm mọi đường dẫn tới engine.
    Bài học từ lỗi Bước 1: kiểm bằng đúng hành động người dùng bấm, không chỉ gọi thẳng engine."""

    @classmethod
    def _setup_tester(cls, prefix):
        env = cls.env
        today = fields.Date.today()
        env["kpi.period"].search([]).write({"auto_generated": True})  # kỳ có sẵn không lẫn vào cron
        cls.period = env["kpi.period"].create({
            "name": f"Kỳ {prefix}", "date_from": today - timedelta(days=20), "date_to": today - timedelta(days=1),
        })
        cls.user = new_test_user(env, login=f"{prefix}_qa", groups="base.group_user")
        cls.manager = new_test_user(
            env, login=f"{prefix}_mgr", groups="base.group_user,project_kpi_management.group_kpi_manager"
        )
        manager_employee = env["hr.employee"].create({"name": f"{prefix} quản lý", "user_id": cls.manager.id})
        cls.employee = env["hr.employee"].create({
            "name": f"{prefix} tester", "user_id": cls.user.id, "parent_id": manager_employee.id,
            "job_id": env.ref("project_kpi_management.hr_job_tester").id,
        })
        project = env["project.project"].create({"name": f"DA {prefix}"})
        for _ in range(2):
            bug = env["project.task"].create({
                "name": "Bug", "project_id": project.id, "task_type": "bug",
                "bug_reporter_id": cls.user.id, "bug_resolution": "valid",
            })
            env.flush_all()
            env.cr.execute(
                "UPDATE project_task SET create_date = %s WHERE id = %s", (fields.Datetime.now() - timedelta(days=5), bug.id)
            )
        env.invalidate_all()

    def _qa1(self, evaluation):
        return evaluation.line_ids.filtered(lambda l: l.metric_id.code == "QA1").actual


@tagged("post_install", "-at_install")
class TestKpiComputePaths(ComputePathFixture, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tester("paths")

    def test_generate_wizard_computes_domain_metric(self):
        form = Form(self.env["kpi.evaluation.generate.wizard"])
        form.period_id = self.period
        form.compute = True
        form.save().action_generate()
        evaluation = self.period.evaluation_ids.filtered(lambda e: e.employee_id == self.employee)
        self.assertEqual(self._qa1(evaluation), 2)

    def test_recompute_server_action_computes_domain_metric(self):
        evaluation = self.env["kpi.evaluation"].create({"employee_id": self.employee.id, "period_id": self.period.id})
        self.assertEqual(self._qa1(evaluation), 0)
        action = self.env.ref("project_kpi_management.kpi_evaluation_action_recompute")
        action.with_context(active_model="kpi.evaluation", active_ids=evaluation.ids).run()
        self.assertEqual(self._qa1(evaluation), 2)

    def test_cron_computes_domain_metric(self):
        self.env["kpi.period"]._cron_generate_evaluations()
        evaluation = self.period.evaluation_ids.filtered(lambda e: e.employee_id == self.employee)
        self.assertEqual(self._qa1(evaluation), 2)

    def test_single_rule_for_engine_computed(self):
        Metric = self.env["kpi.metric"]
        for mode, expected in (("auto", True), ("domain", True), ("manual", False)):
            self.assertEqual(Metric.new({"compute_mode": mode})._is_engine_computed(), expected)

    def test_module_update_does_not_rerun_migrations(self):
        """Hàm chuyển đổi chỉ được chạy từ migrations/ (một lần), không từ file dữ liệu — dữ liệu nạp lại
        mỗi lần -u sẽ âm thầm hoàn tác lựa chọn của Admin (ví dụ gắn lại chức danh Tester vào bộ khác)."""
        path = get_module_path("project_kpi_management")
        manifest = self.env["ir.module.module"].get_module_info("project_kpi_management")
        for rel in manifest["data"] + manifest.get("demo", []):
            with open(f"{path}/{rel}", encoding="utf-8") as f:
                self.assertNotIn("_migrate_", f.read(), rel)

    def test_post_migrate_script_renames_codes_once(self):
        spec = importlib.util.spec_from_file_location(
            "kpi_post_migrate", get_module_path("project_kpi_management") + "/migrations/19.0.1.1.0/post-migrate.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        metric = self.env.ref("project_kpi_management.kpi_metric_qa1")
        metric.code = "T4"  # trạng thái của database cài bản cũ
        module.migrate(self.env.cr, "19.0.1.0.0")
        self.assertEqual(metric.code, "QA1")
        module.migrate(self.env.cr, "19.0.1.0.0")  # chạy lại không lỗi
        self.assertEqual(metric.code, "QA1")


@tagged("post_install", "-at_install")
class TestKpiComputePathsApi(ComputePathFixture, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tester("pathsapi")
        cls.evaluation = cls.env["kpi.evaluation"].create({"employee_id": cls.employee.id, "period_id": cls.period.id})
        cls.key = cls.env["res.users.apikeys"].with_user(cls.manager)._generate(
            None, "test", fields.Datetime.now() + timedelta(days=1)
        )

    def _post(self, code, actual):
        response = self.url_open(
            f"/api/kpi/evaluations/{self.evaluation.id}/metrics/{code}", data=json.dumps({"actual": actual}),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        return response.status_code

    def test_api_rejects_domain_metric(self):
        self.assertEqual(self._post("QA1", 99), 400)  # chỉ số cấu hình: không nhận số liệu ngoài
        self.assertEqual(self._post("QA4", 99), 400)  # chỉ số Python
        self.assertEqual(self._post("QA5", 4), 200)   # chỉ số nhập tay vẫn nhận
