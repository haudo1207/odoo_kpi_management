from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiReports(TransactionCase):
    """Phase 6–8: báo cáo, kiểm tra dữ liệu, tạo phiếu hàng loạt, Settings, template Tester."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("project_kpi_management.kpi_template_developer")
        cls.job = cls.env["hr.job"].create({"name": "Dev báo cáo", "kpi_template_id": cls.template.id})
        cls.job_no_kpi = cls.env["hr.job"].create({"name": "Kế toán"})
        cls.dept_a = cls.env["hr.department"].create({"name": "Phòng A"})
        cls.dept_b = cls.env["hr.department"].create({"name": "Phòng B"})
        today = fields.Date.today()
        cls.period = cls.env["kpi.period"].create({
            "name": "Kỳ báo cáo", "date_from": today - timedelta(days=20), "date_to": today + timedelta(days=5),
        })
        cls.project = cls.env["project.project"].create({"name": "Dự án báo cáo"})

    def _employee(self, name, dept, job=None, with_user=True):
        user = new_test_user(self.env, login=f"kpi_rep_{name}") if with_user else self.env["res.users"]
        return self.env["hr.employee"].create({
            "name": name, "user_id": user.id, "department_id": dept.id, "job_id": (job or self.job).id,
        })

    def _fill_and_submit(self, ev):
        ev.line_ids.write({"actual": 100, "volume": 100})
        ev.computed_date = fields.Datetime.now()
        ev.action_submit()

    # ---- Phase 7: tạo phiếu hàng loạt ----

    def _wizard(self, **vals):
        form = Form(self.env["kpi.evaluation.generate.wizard"])
        form.period_id = self.period
        for dept in vals.get("departments", ()):
            form.department_ids.add(dept)
        form.compute = vals.get("compute", True)
        return form.save()

    def test_generate_wizard(self):
        e1 = self._employee("a1", self.dept_a)
        e2 = self._employee("a2", self.dept_a)
        self._employee("a3", self.dept_a, with_user=False)        # thiếu tài khoản: bỏ qua
        self._employee("a4", self.dept_a, job=self.job_no_kpi)    # chức danh chưa gắn bộ KPI: bỏ qua
        e5 = self._employee("b1", self.dept_b)
        wizard = self._wizard(departments=[self.dept_a])
        self.assertEqual(wizard.preview_count, 2)
        wizard.action_generate()
        evaluations = self.period.evaluation_ids
        self.assertEqual(evaluations.employee_id, e1 | e2)
        self.assertTrue(all(evaluations.mapped("computed_date")))
        with self.assertRaises(UserError):  # chạy lại: không còn ai cần tạo
            self._wizard(departments=[self.dept_a]).action_generate()
        self._wizard().action_generate()   # không lọc phòng ban: thêm nhân viên phòng B
        self.assertIn(e5, self.period.evaluation_ids.employee_id)
        self.assertEqual(self.period.evaluation_count, len(self.period.evaluation_ids))

    def test_recompute_server_action(self):
        e1, e2 = self._employee("r1", self.dept_a), self._employee("r2", self.dept_a)
        draft, submitted = self.env["kpi.evaluation"].create([
            {"employee_id": e.id, "period_id": self.period.id} for e in (e1, e2)
        ])
        self._fill_and_submit(submitted)
        action = self.env.ref("project_kpi_management.kpi_evaluation_action_recompute")
        action.with_context(active_model="kpi.evaluation", active_ids=(draft | submitted).ids).run()
        self.assertTrue(draft.computed_date)
        self.assertEqual(submitted.state, "submitted")  # phiếu không ở Nháp được bỏ qua, không báo lỗi

    # ---- Phase 7: Settings ----

    def _settings(self, **vals):
        settings = self.env["res.config.settings"].create(vals)
        settings.execute()

    def test_settings_change_rating_after_recompute(self):
        # Bộ KPI chỉ có D9 (nhập tay): Tính KPI không ghi số liệu nào, điểm đổi được là nhờ tính lại bắt buộc
        d9 = self.env.ref("project_kpi_management.kpi_metric_d9")
        manual_only = self.env["kpi.template"].create({
            "name": "Chỉ D9", "line_ids": [(0, 0, {"metric_id": d9.id, "target": 4, "weight": 100})],
        })
        ev = self.env["kpi.evaluation"].create({
            "employee_id": self._employee("s1", self.dept_a).id, "period_id": self.period.id, "template_id": manual_only.id,
        })
        ev.line_ids.actual = 4  # đúng mục tiêu → 100 điểm
        self.assertEqual(ev.rating, "excellent")
        self._settings(kpi_rating_excellent=110, kpi_rating_good=90, kpi_rating_pass=75)
        self.assertEqual(ev.rating, "excellent")  # chưa tính lại: giữ kết quả cũ
        ev.action_compute_kpi()
        self.assertEqual(ev.rating, "good")      # 100 < ngưỡng mới 110

    def test_settings_validation(self):
        with self.assertRaises(ValidationError):
            self._settings(kpi_rating_excellent=90, kpi_rating_good=95, kpi_rating_pass=75)
        with self.assertRaises(ValidationError):
            self._settings(kpi_score_cap=80)

    # ---- Phase 6: bug phát sinh muộn ----

    def test_late_bugs(self):
        employee = self._employee("l1", self.dept_a)
        feature = self.env["project.task"].create({
            "name": "F", "project_id": self.project.id, "user_ids": [(6, 0, employee.user_id.ids)], "story_points": 5,
        })
        feature.write({"state": "1_done"})
        bug_vals = {"project_id": self.project.id, "task_type": "bug", "origin_task_id": feature.id,
                    "bug_resolution": "valid", "bug_root_cause": "code"}
        early = self.env["project.task"].create({"name": "Bug sớm", **bug_vals})
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": self.period.id})
        self._fill_and_submit(ev)
        ev.action_approve()
        late = self.env["project.task"].create({"name": "Bug muộn", **bug_vals})
        # create_date là thời điểm bắt đầu transaction: đặt lại để mô phỏng thứ tự thời gian thật
        self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id = %s", (ev.approved_date - timedelta(days=1), early.id))
        self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id = %s", (ev.approved_date + timedelta(hours=1), late.id))
        (early | late).invalidate_recordset(["create_date"])
        ev.invalidate_recordset(["late_bug_count"])
        self.assertEqual(ev.late_bug_count, 1)
        self.assertEqual(self.env["project.task"].search(ev.action_view_late_bugs()["domain"]), late)

    # ---- Phase 6: kiểm tra dữ liệu, báo cáo theo chỉ số ----

    def test_data_quality_report(self):
        Task = self.env["project.task"]
        base = {"project_id": self.project.id}
        Task.create({"name": "F có SP", "story_points": 3, **base}).write({"state": "1_done"})
        Task.create({"name": "F thiếu SP", **base}).write({"state": "1_done"})
        Task.create({"name": "Bug thiếu gốc", "task_type": "bug", "bug_resolution": "valid", "bug_root_cause": "code", **base})
        Task.create({"name": "Bug chưa phân loại", "task_type": "bug", **base})
        self.env.flush_all()
        row = self.env["kpi.data.quality.report"].search([("project_id", "=", self.project.id)])
        self.assertEqual((row.done_feature_count, row.done_without_sp, row.sp_rate), (2, 1, 50.0))
        self.assertEqual((row.bug_count, row.bug_without_origin, row.bug_unclassified), (2, 2, 1))
        self.assertEqual((row.origin_rate, row.classified_rate), (0.0, 50.0))
        self.assertEqual(row.done_without_date_end, 0)  # date_end luôn được ghi khi Done

    def test_team_report_by_project(self):
        """Mục 5: chỉ số cấp team = dự án, cùng cách làm với kpi.data.quality.report."""
        Task = self.env["project.task"]
        base = {"project_id": self.project.id}
        on_time = Task.create({"name": "F đúng hạn", "task_type": "feature", **base})
        on_time.write({"state": "1_done"})
        late = Task.create({
            "name": "F trễ", "task_type": "feature",
            "date_deadline": fields.Datetime.now() - timedelta(days=5), **base,
        })
        late.write({"state": "1_done"})
        self.assertGreater(late.days_late, 0)

        bug1 = Task.create({
            "name": "Bug production", "task_type": "bug", "bug_resolution": "valid",
            "is_production_bug": True, **base,
        })
        bug1.write({"state": "1_done"})
        bug2 = Task.create({"name": "Bug thường", "task_type": "bug", "bug_resolution": "valid", **base})
        bug2.write({"state": "1_done"})

        past = fields.Datetime.now() - timedelta(hours=2)
        self.env.cr.execute("UPDATE project_task SET create_date = %s WHERE id IN %s", (past, (bug1.id, bug2.id)))
        (bug1 + bug2).invalidate_recordset(["create_date"])
        self.env.flush_all()

        row = self.env["kpi.team.report"].search([("project_id", "=", self.project.id)])
        self.assertEqual((row.feature_done_count, row.feature_on_time_count), (2, 1))
        self.assertAlmostEqual(row.on_time_rate, 50.0, places=4)
        self.assertEqual(row.bug_count, 2)
        self.assertAlmostEqual(row.bug_density, 1.0, places=4)
        self.assertEqual(row.production_bug_count, 1)
        self.assertAlmostEqual(row.production_bug_rate, 50.0, places=4)
        self.assertAlmostEqual(row.avg_bug_fix_hours, 2.0, places=1)

    def test_team_report_attributes_bug_to_origin_project(self):
        """Mục 5: bug nằm ở dự án "Bug tổng" nhưng task gốc thuộc dự án khác thì tính vào dự án
        của task gốc, đúng quy ước D3/D4 (kpi_engine.py: "quy về ... task gốc"), không tính vào
        dự án chứa bug. Bug không có task gốc thì vẫn giữ dự án của chính nó."""
        Task = self.env["project.task"]
        bug_project = self.env["project.project"].create({"name": "Bug tổng"})
        feature = Task.create({"name": "Feature ở dự án báo cáo", "project_id": self.project.id})
        cross_bug = Task.create({
            "name": "Bug chéo dự án", "project_id": bug_project.id, "task_type": "bug",
            "bug_resolution": "valid", "origin_task_id": feature.id,
        })
        orphan_bug = Task.create({
            "name": "Bug không có task gốc", "project_id": bug_project.id, "task_type": "bug",
            "bug_resolution": "valid",
        })
        self.env.flush_all()

        report_project = self.env["kpi.team.report"].search([("project_id", "=", self.project.id)])
        report_bug_project = self.env["kpi.team.report"].search([("project_id", "=", bug_project.id)])
        self.assertEqual(report_project.bug_count, 1)  # cross_bug quy về đây, theo task gốc
        self.assertEqual(report_bug_project.bug_count, 1)  # chỉ orphan_bug còn ở lại dự án của chính nó

    def test_line_report_fields_and_employee_button(self):
        employee = self._employee("rp1", self.dept_b)
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": self.period.id})
        line = ev.line_ids[:1]
        self.assertEqual((line.employee_id, line.period_id, line.department_id), (employee, self.period, self.dept_b))
        self.assertEqual(employee.kpi_evaluation_count, 1)
        self.assertEqual(employee.action_view_kpi_evaluations()["domain"], [("employee_id", "=", employee.id)])

    # ---- Phase 8: vai trò mới chỉ bằng dữ liệu ----

    def test_tester_template_without_code(self):
        job = self.env.ref("project_kpi_management.hr_job_tester", raise_if_not_found=False)
        if not job:
            self.skipTest("Database không có dữ liệu mẫu.")
        employee = self._employee("qa1", self.dept_a, job=job)
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": self.period.id})
        # Bước 2: bộ Tester tự động (QA1-QA5) thay bộ nhập tay cũ; số liệu tự tính xem test_kpi_tester.py
        self.assertEqual(ev.template_id, self.env.ref("project_kpi_management.kpi_template_tester_auto"))
        values = {"QA1": 15, "QA2": 20, "QA3": 90, "QA4": 5, "QA5": 4}
        for line in ev.line_ids:
            line.write({"actual": values[line.metric_id.code], "volume": 10})
        # QA1 100, QA2 thấp tốt 10/20 = 50, QA3 100, QA4 100, QA5 100
        self.assertAlmostEqual(ev.kpi_score, (100 * 25 + 50 * 20 + 100 * 15 + 100 * 25 + 100 * 15) / 100)
