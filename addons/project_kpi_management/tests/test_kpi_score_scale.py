from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiScoreScale(TransactionCase):
    """Bước 3 (Chương 9.3): chấm điểm theo bậc — tra theo % đạt mục tiêu, chụp vào dòng phiếu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.metrics = {m.code: m for m in cls.env["kpi.metric"].search([])}
        today = fields.Date.today()
        cls.date_from, cls.date_to = today - timedelta(days=20), today + timedelta(days=10)
        cls.period = cls.env["kpi.period"].create({"name": "Kỳ bậc", "date_from": cls.date_from, "date_to": cls.date_to})
        cls.user = new_test_user(cls.env, login="kpi_scale_dev")
        cls.employee = cls.env["hr.employee"].create({"name": "Dev bậc", "user_id": cls.user.id})
        cls.scale = cls._scale("Bậc chuẩn", [(0, 0), (50, 50), (80, 75), (100, 100)])

    @classmethod
    def _scale(cls, name, steps):
        return cls.env["kpi.score.scale"].create({
            "name": name, "step_ids": [(0, 0, {"pct_from": f, "score": s}) for f, s in steps],
        })

    def _template(self, code, target, scale, min_volume=0):
        return self.env["kpi.template"].create({
            "name": f"Bậc {code} {scale.name}",
            "line_ids": [(0, 0, {"metric_id": self.metrics[code].id, "target": target, "weight": 100,
                                 "min_volume": min_volume, "scale_id": scale.id})],
        })

    def _evaluation(self, template, employee=None):
        return self.env["kpi.evaluation"].create({
            "employee_id": (employee or self.employee).id, "period_id": self.period.id, "template_id": template.id,
        })

    # ---- Kiểm tra bảng bậc ----

    def test_scale_validation(self):
        Scale = self.env["kpi.score.scale"]
        with self.assertRaises(ValidationError):
            Scale.create({"name": "Rỗng"})
        with self.assertRaises(ValidationError):  # hở từ 0 tới 50
            self._scale("Hở", [(50, 50), (100, 100)])
        with self.assertRaises(ValidationError):  # hai bậc cùng điểm bắt đầu: chồng nhau
            self._scale("Chồng", [(0, 0), (80, 70), (80, 90)])
        step = self.scale.step_ids.filtered(lambda s: s.pct_from == 0)
        with self.assertRaises(ValidationError):  # sửa bậc đầu khỏi 0 làm hở
            self.scale.write({"step_ids": [(1, step.id, {"pct_from": 10})]})  # form lưu qua bảng bậc

    def test_scale_steps_cover_without_overlap(self):
        steps = self.scale.step_ids.sorted("pct_from")
        self.assertEqual(steps.mapped("pct_to"), [50, 80, 100, 0])  # liên tục; 0 = bậc cuối không giới hạn

    def test_only_admin_edits_scale(self):
        user = new_test_user(self.env, login="kpi_scale_user", groups="project_kpi_management.group_kpi_manager")
        with self.assertRaises(AccessError):
            self.env["kpi.score.scale"].with_user(user).create({"name": "X", "step_ids": [(0, 0, {"pct_from": 0, "score": 0})]})

    def test_lookup_boundaries(self):
        lookup = self.env["kpi.score.scale"].lookup
        snapshot = self.scale._snapshot()
        self.assertEqual(
            [lookup(snapshot, p) for p in (0, 49.99, 50, 79.99, 80, 99.99, 100, 120)], [0, 0, 50, 50, 75, 75, 100, 100]
        )

    # ---- Phiếu ----

    def test_click_compute_kpi_uses_scale(self):
        """Đi qua đúng nút "Tính KPI": 17/20 SP = 85% → bậc 80% = 75 điểm (tuyến tính sẽ ra 85)."""
        project = self.env["project.project"].create({"name": "DA bậc"})
        task = self.env["project.task"].create({
            "name": "T", "project_id": project.id, "user_ids": [(6, 0, self.user.ids)], "story_points": 17,
        })
        task.write({"state": "1_done"})
        task.write({"date_end": fields.Datetime.now() - timedelta(days=2)})
        ev = self._evaluation(self._template("D2", 20, self.scale))
        ev.action_compute_kpi()
        line = ev.line_ids
        self.assertAlmostEqual(line.achievement_pct, 85.0)
        self.assertEqual(line.score, 75)
        self.assertAlmostEqual(ev.kpi_score, 75.0)

    def test_without_scale_stays_linear(self):
        template = self._template("D2", 20, self.scale)
        template.line_ids.scale_id = False
        line = self._evaluation(template).line_ids
        line.write({"actual": 17, "volume": 17})
        self.assertAlmostEqual(line.score, 85.0)

    def test_not_applicable_skips_lookup(self):
        scale = self._scale("Bậc nền 50", [(0, 50), (100, 100)])  # nếu lỡ tra bậc, 0% cũng được 50 điểm
        line = self._evaluation(self._template("D4", 5, scale, min_volume=1)).line_ids
        line.write({"actual": 0, "volume": 0})
        self.assertFalse(line.is_applicable)
        self.assertEqual(line.score, 0.0)

    def test_lower_is_better_zero_actual_takes_cap_before_lookup(self):
        scale = self._scale("Bậc trần", [(0, 0), (100, 100), (120, 130)])  # bậc cao nhất vượt trần 120
        line = self._evaluation(self._template("D4", 5, scale, min_volume=1)).line_ids
        line.write({"actual": 0, "volume": 5})
        self.assertEqual(line.achievement_pct, 120.0)   # trần, chưa phải giá trị thực tế
        self.assertEqual(line.score, 120.0)             # tra bậc ra 130, vẫn bị chặn trần
        line.write({"actual": 10})                       # lower: 5/10 = 50% → bậc 0 điểm
        self.assertEqual((line.achievement_pct, line.score), (50.0, 0.0))

    def test_editing_scale_does_not_change_existing_evaluation(self):
        template = self._template("D2", 20, self.scale)
        old_line = self._evaluation(template).line_ids
        old_line.write({"actual": 17, "volume": 17})
        self.assertEqual(old_line.score, 75)
        self.scale.step_ids.filtered(lambda s: s.pct_from == 80).score = 90  # sửa bảng bậc sau khi tạo phiếu
        old_line.write({"actual": 17.5})                                      # buộc tính lại điểm
        self.assertEqual(old_line.score, 75)                                  # vẫn theo bảng đã chụp
        other = self.env["hr.employee"].create({"name": "Dev bậc 2", "user_id": new_test_user(self.env, login="kpi_scale_dev2").id})
        new_line = self._evaluation(template, other).line_ids
        new_line.write({"actual": 17, "volume": 17})
        self.assertEqual(new_line.score, 90)                                  # phiếu mới nhận bảng mới
