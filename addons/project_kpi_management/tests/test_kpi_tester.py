from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiTester(TransactionCase):
    """Bước 2 (Chương 9.2): bộ KPI Tester tự động — QA1-QA3 chỉ cấu hình, QA4 hàm Python, QA5 nhập tay."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["kpi.engine"]
        today = fields.Date.today()
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.tester = new_test_user(cls.env, login="kpi_tester_qa", groups="base.group_user,project.group_project_user")
        cls.other = new_test_user(cls.env, login="kpi_tester_other", groups="base.group_user,project.group_project_user")
        cls.employee = cls.env["hr.employee"].create({
            "name": "Tester QA", "user_id": cls.tester.id,
            "job_id": cls.env.ref("project_kpi_management.hr_job_tester").id,
        })
        cls.project = cls.env["project.project"].create({"name": "Tester test"})
        cls.metrics = {m.code: m for m in cls.env["kpi.metric"].search([])}

    def _bug(self, reporter=None, resolution=False, cause=False, origin=True, **vals):
        origin_task = self.env["project.task"].create({"name": "Gốc", "project_id": self.project.id}) if origin else False
        return self.env["project.task"].create({
            "name": "Bug", "project_id": self.project.id, "task_type": "bug",
            "bug_reporter_id": (reporter or self.tester).id, "bug_resolution": resolution,
            "bug_root_cause": cause, "origin_task_id": origin_task.id if origin_task else False, **vals,
        })

    def _compute(self, code):
        return self.engine.compute_actual(self.metrics[code], self.employee, self.date_from, self.date_to)

    def _scenario(self):
        """Tester: 4 valid (1 production), 1 wont_fix, 1 duplicate, 1 invalid, 1 chưa phân loại;
        6/8 bug có cả task gốc và nguyên nhân. Người khác: 1 bug valid trong cùng dự án."""
        for i in range(4):
            self._bug(resolution="valid", cause="code", is_production_bug=(i == 0))
        self._bug(resolution="wont_fix", cause="requirement")
        self._bug(resolution="duplicate", cause="code")
        self._bug(resolution="invalid", origin=False)
        self._bug()
        self._bug(reporter=self.other, resolution="valid", cause="code")

    # ---- Cấu hình, không code ----

    def test_t4_t6_have_no_python_code(self):
        for code in ("QA1", "QA2", "QA3"):
            with self.subTest(code=code):
                self.assertEqual(self.metrics[code].compute_mode, "domain")
                self.assertFalse(hasattr(self.engine, f"_metric_{code.lower()}"))
        self.assertTrue(hasattr(self.engine, "_metric_qa4"))
        self.assertEqual(self.metrics["QA5"].compute_mode, "manual")

    # ---- Từng chỉ số ----

    def test_t4_counts_valid_bugs_of_reporter_only(self):
        self._scenario()
        self.assertEqual(self._compute("QA1"), (5, 5))

    def test_t4_ignores_bugs_outside_period(self):
        self._bug(resolution="valid", cause="code")
        self.assertEqual(
            self.engine.compute_actual(self.metrics["QA1"], self.employee, self.date_from - timedelta(days=60), self.date_from - timedelta(days=30)),
            (0, 0),
        )

    def test_t5_t6_ratio(self):
        self._scenario()
        actual5, volume5 = self._compute("QA2")
        self.assertAlmostEqual(actual5, 2 / 7 * 100)   # duplicate + invalid / bug đã phân loại
        self.assertEqual(volume5, 7)
        actual6, volume6 = self._compute("QA3")
        self.assertAlmostEqual(actual6, 75.0)           # 6 / 8
        self.assertEqual(volume6, 8)

    def test_below_min_volume_not_applicable(self):
        self._bug(resolution="valid", cause="code")
        self._bug(resolution="invalid", cause="code")
        ev = self._evaluation()
        ev.action_compute_kpi()
        for code in ("QA2", "QA3"):  # 2 bug < min_volume 3
            line = ev.line_ids.filtered(lambda l: l.metric_id.code == code)
            self.assertFalse(line.is_applicable, code)

    def test_t7_only_projects_where_tester_logged_bugs(self):
        self._scenario()
        other_project = self.env["project.project"].create({"name": "Dự án khác"})
        self.env["project.task"].create({
            "name": "Bug dự án khác", "project_id": other_project.id, "task_type": "bug",
            "bug_reporter_id": self.other.id, "bug_resolution": "valid", "is_production_bug": True,
        })
        actual, volume = self._compute("QA4")
        self.assertEqual(volume, 1)  # chỉ dự án tester có log bug
        self.assertAlmostEqual(actual, 1 / 6 * 100)  # 1 production / 6 bug hợp lệ trong dự án (kể cả của người khác)

    def test_t7_no_project_not_applicable(self):
        self.assertEqual(self._compute("QA4"), (0.0, 0))

    # ---- bug_reporter_id ----

    def test_bug_reporter_defaults_to_creator(self):
        creator = new_test_user(
            self.env, login="kpi_tester_creator",
            groups="base.group_user,project.group_project_manager,project_kpi_management.group_kpi_manager",
        )
        bug = self.env["project.task"].with_user(creator).create(
            {"name": "Bug", "project_id": self.project.id, "task_type": "bug"}
        )
        self.assertEqual(bug.bug_reporter_id, creator)

    def test_bug_reporter_only_manager_edits(self):
        bug = self._bug(resolution="valid", cause="code")
        manager = new_test_user(
            self.env, login="kpi_tester_manager",
            groups="base.group_user,project.group_project_manager,project_kpi_management.group_kpi_manager",
        )
        with self.assertRaises(AccessError):
            bug.with_user(self.tester).write({"bug_reporter_id": self.other.id})
        with self.assertRaises(AccessError):
            self.env["project.task"].with_user(self.tester).create({
                "name": "Bug", "project_id": self.project.id, "task_type": "bug", "bug_reporter_id": self.other.id,
            })
        bug.with_user(manager).write({"bug_reporter_id": self.other.id})
        self.assertEqual(bug.bug_reporter_id, self.other)

    def test_migrate_backfills_old_bugs(self):
        bug = self._bug()
        self.env.flush_all()
        self.env.cr.execute("UPDATE project_task SET bug_reporter_id = NULL WHERE id = %s", (bug.id,))
        bug.invalidate_recordset()
        self.assertFalse(bug.bug_reporter_id)
        self.env["project.task"]._migrate_bug_reporter_id()
        self.assertEqual(bug.bug_reporter_id, bug.create_uid)

    def test_migrate_tester_template_on_upgraded_database(self):
        """Mô phỏng database đã cài bản cũ: chức danh còn trỏ về bộ Tester cũ (noupdate nên XML
        không đổi được) — hàm migration phải chuyển sang bộ mới và ẩn bộ/chỉ số cũ."""
        Metric, Data = self.env["kpi.metric"], self.env["ir.model.data"]
        old_metrics = Metric.create([
            {"code": f"OLD{i}", "name": f"Cũ {i}", "category": "delivery", "compute_mode": "manual"} for i in range(3)
        ])
        old_template = self.env["kpi.template"].create({
            "name": "Tester cũ", "line_ids": [
                (0, 0, {"metric_id": old_metrics[0].id, "target": 1, "weight": 50}),
                (0, 0, {"metric_id": old_metrics[1].id, "target": 1, "weight": 50}),
            ],
        })
        for xmlid, record in (
            ("kpi_template_tester", old_template), ("kpi_metric_t1", old_metrics[0]),
            ("kpi_metric_t2", old_metrics[1]), ("kpi_metric_t3", old_metrics[2]),
        ):
            Data.search([("module", "=", "project_kpi_management"), ("name", "=", xmlid)]).unlink()
            Data.create({"module": "project_kpi_management", "name": xmlid, "model": record._name, "res_id": record.id})
        job = self.env.ref("project_kpi_management.hr_job_tester")
        job.kpi_template_id = old_template
        self.env["hr.job"]._migrate_tester_template()
        self.assertEqual(job.kpi_template_id, self.env.ref("project_kpi_management.kpi_template_tester_auto"))
        self.assertFalse(old_template.active)
        self.assertFalse(any(old_metrics.mapped("active")))
        self.env["hr.job"]._migrate_tester_template()  # chạy lại không lỗi

    # ---- Phiếu đầy đủ khớp bảng tính tay ----

    def _evaluation(self):
        period = self.env["kpi.period"].create({"name": "Kỳ tester", "date_from": self.date_from, "date_to": self.date_to})
        return self.env["kpi.evaluation"].create({"employee_id": self.employee.id, "period_id": period.id})

    def test_full_evaluation_matches_hand_calculation(self):
        self._scenario()
        ev = self._evaluation()
        self.assertEqual(ev.template_id, self.env.ref("project_kpi_management.kpi_template_tester_auto"))
        ev.line_ids.filtered(lambda l: l.metric_id.code == "QA5").actual = 3
        ev.action_compute_kpi()
        # QA1 5/15=33.33%·25 + QA2 10/28.57=35%·20 + QA3 75/90=83.33%·15 + QA4 5/16.67=30%·25 + QA5 3/4=75%·15
        self.assertAlmostEqual(ev.kpi_score, 8.33333 + 7 + 12.5 + 7.5 + 11.25, places=3)
        self.assertEqual(ev.applicable_weight, 100)
