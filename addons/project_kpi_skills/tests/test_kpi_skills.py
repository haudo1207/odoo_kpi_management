from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiSkills(TransactionCase):
    """Đợt D2 (v1.6): S1 — mức đáp ứng kỹ năng. Chạy riêng: --test-tags /project_kpi_skills (cần hr_skills)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        today = fields.Date.today()
        cls.today = today
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.period = env["kpi.period"].create({"name": "Kỳ kỹ năng", "date_from": cls.date_from, "date_to": cls.date_to})
        cls.skill_type = env["hr.skill.type"].create({
            "name": "Kỹ năng test",
            "skill_ids": [(0, 0, {"name": n}) for n in ("Python", "Odoo", "SQL")],
            "skill_level_ids": [(0, 0, {"name": f"M{p}", "level_progress": p}) for p in (25, 50, 75, 100)],
        })
        cls.level = {lv.level_progress: lv for lv in cls.skill_type.skill_level_ids}
        cls.skill = {s.name: s for s in cls.skill_type.skill_ids}
        cls.job = env["hr.job"].create({
            "name": "Dev kỹ năng", "kpi_template_id": env.ref("project_kpi_skills.kpi_template_developer_skills").id,
        })
        for name, progress in (("Python", 75), ("Odoo", 50), ("SQL", 50)):
            cls._job_skill(cls.job, name, progress)
        cls.metric = env.ref("project_kpi_skills.kpi_metric_s1")
        cls.engine = env["kpi.engine"]
        cls._counter = 0

    @classmethod
    def _job_skill(cls, job, name, progress, **vals):
        return cls.env["hr.job.skill"].create({
            "job_id": job.id, "skill_type_id": cls.skill_type.id, "skill_id": cls.skill[name].id,
            "skill_level_id": cls.level[progress].id, "valid_from": cls.today - timedelta(days=400), **vals,
        })

    def _employee(self, skills=(), job=None):
        TestKpiSkills._counter += 1
        employee = self.env["hr.employee"].create({
            "name": f"KN{self._counter}", "user_id": new_test_user(self.env, login=f"sk_{self._counter}").id,
            "job_id": (job or self.job).id,
        })
        for name, progress, vals in skills:
            self._employee_skill(employee, name, progress, **vals)
        return employee

    def _employee_skill(self, employee, name, progress, **vals):
        return self.env["hr.employee.skill"].create({
            "employee_id": employee.id, "skill_type_id": self.skill_type.id, "skill_id": self.skill[name].id,
            "skill_level_id": self.level[progress].id, "valid_from": self.today - timedelta(days=400), **vals,
        })

    def _s1(self, employee, job=None, date_to=None):
        return self.engine.compute_actual(self.metric, employee, self.date_from, date_to or self.date_to, job=job)

    def test_pass_fail_and_exceed(self):
        """Python 100 ≥ 75 (vượt), Odoo 50 ≥ 50 (đúng mức), SQL 25 < 50 (không đạt) → 2/3."""
        employee = self._employee([("Python", 100, {}), ("Odoo", 50, {}), ("SQL", 25, {})])
        actual, volume = self._s1(employee)
        self.assertAlmostEqual(actual, 200 / 3)
        self.assertEqual(volume, 3)

    def test_missing_skill_counts_as_failed(self):
        self.assertAlmostEqual(self._s1(self._employee([("Python", 75, {}), ("Odoo", 50, {})]))[0], 200 / 3)  # thiếu SQL
        self.assertEqual(self._s1(self._employee())[0], 0.0)                                                 # không có gì

    def test_expired_skill_ignored(self):
        expired = {"valid_to": self.today - timedelta(days=30)}  # hết hạn trước cuối kỳ
        employee = self._employee([("Python", 100, {}), ("Odoo", 100, expired), ("SQL", 100, {})])
        self.assertAlmostEqual(self._s1(employee)[0], 200 / 3)  # Odoo đã hết hạn nên không tính

    def test_expired_job_requirement_ignored(self):
        job = self.env["hr.job"].create({"name": "Dev yêu cầu hết hạn"})
        self._job_skill(job, "Python", 75)
        self._job_skill(job, "SQL", 100, valid_to=self.today - timedelta(days=30))  # yêu cầu cũ đã hết hạn
        employee = self._employee([("Python", 75, {})], job=job)
        self.assertEqual(self._s1(employee, job=job), (100.0, 1))

    def test_job_without_required_skills_is_not_applicable(self):
        job = self.env["hr.job"].create({"name": "Không yêu cầu kỹ năng"})
        self.assertEqual(self._s1(self._employee([("Python", 100, {})], job=job), job=job), (0.0, 0))

    def test_old_period_unchanged_after_skill_upgrade(self):
        """Nâng mức SQL sau kỳ: bản cũ được đóng (valid_to = hôm qua), bản mới bắt đầu hôm nay. Kỳ đã qua (cuối kỳ cách
        đây 5 ngày) tính lại vẫn theo mức cũ; kỳ hiện tại theo mức mới."""
        employee = self._employee([("Python", 100, {}), ("Odoo", 50, {})])
        old_sql = self._employee_skill(employee, "SQL", 25, valid_to=self.today - timedelta(days=1))
        past_end = self.today - timedelta(days=5)
        self.assertAlmostEqual(self._s1(employee, date_to=past_end)[0], 200 / 3)   # SQL 25 < 50
        self._employee_skill(employee, "SQL", 100, valid_from=self.today)           # nâng mức hôm nay
        self.assertAlmostEqual(self._s1(employee, date_to=past_end)[0], 200 / 3)   # kỳ cũ không đổi
        self.assertEqual(self._s1(employee)[0], 100.0)                              # kỳ hiện tại theo mức mới
        self.assertTrue(old_sql.valid_to)

    def test_uses_job_snapshotted_on_evaluation(self):
        employee = self._employee([("Python", 100, {}), ("Odoo", 50, {}), ("SQL", 25, {})])
        ev = self.env["kpi.evaluation"].create({
            "employee_id": employee.id, "period_id": self.period.id,
            "template_id": self.env.ref("project_kpi_skills.kpi_template_developer_skills").id,
        })
        self.assertEqual(ev.job_id, self.job)
        other = self.env["hr.job"].create({"name": "Chức danh khác không yêu cầu kỹ năng"})
        employee.job_id = other  # đổi chức danh sau khi tạo phiếu
        ev.action_compute_kpi()
        line = ev.line_ids.filtered(lambda l: l.metric_id == self.metric)
        self.assertEqual((line.volume, round(line.actual, 2)), (3, 66.67))  # vẫn so theo chức danh đã chụp

    def test_click_compute_on_evaluation(self):
        """Qua nút Tính KPI: S1 = 2/3 = 66,67%, mục tiêu 80% → 83,33% đạt mục tiêu → điểm dòng 83,33."""
        employee = self._employee([("Python", 100, {}), ("Odoo", 50, {}), ("SQL", 25, {})])
        ev = self.env["kpi.evaluation"].create({
            "employee_id": employee.id, "period_id": self.period.id,
            "template_id": self.env.ref("project_kpi_skills.kpi_template_developer_skills").id,
        })
        self.assertEqual(sum(ev.template_id.line_ids.mapped("weight")), 100)
        ev.action_compute_kpi()
        line = ev.line_ids.filtered(lambda l: l.metric_id == self.metric)
        self.assertTrue(line.is_applicable)
        self.assertAlmostEqual(line.score, 200 / 3 / 80 * 100)

    def test_demo_skills_scenario(self):
        """Dữ liệu mẫu: An Python 100, Odoo 50, SQL 25 so với chức danh Lập trình viên (Python 75, Odoo 50, SQL 50) → 2/3."""
        self.env["kpi.demo"]._load_scenario()
        an = self.env.ref("project_kpi_management.demo_employee_an")
        job = self.env.ref("project_kpi_management.hr_job_developer")
        actual, volume = self._s1(an, job=job)
        self.assertAlmostEqual(actual, 200 / 3)
        self.assertEqual(volume, 3)
