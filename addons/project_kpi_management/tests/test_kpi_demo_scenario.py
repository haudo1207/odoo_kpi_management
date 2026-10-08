from odoo.tests import TransactionCase, tagged

# Bảng tính tay (lộ trình, Phase 4): (actual, volume) mong đợi của từng chỉ số
EXPECTED = {
    "an": {
        "D1": (100.0, 4), "D2": (24, 24), "D3": (2 / 24, 24), "D4": (0.0, 2), "D5": (75.0, 4),
        "D6": (75.0, 4), "D7": (5.0, 1), "D8": (1, 1),
    },
    "binh": {
        "D1": (60.0, 5), "D2": (15, 15), "D3": (4 / 15, 15), "D4": (25.0, 4), "D5": (50.0, 4),
        "D6": (50.0, 4), "D7": (25.0, 2), "D8": (1, 1),
    },
    "chi": {
        "D1": (0.0, 1), "D2": (0, 0), "D3": (0.0, 0), "D4": (0.0, 0), "D5": (0.0, 0),
        "D6": (0.0, 0), "D7": (0.0, 0), "D8": (0, 0),
    },
}
# D9 do quản lý chấm; điểm KPI, xếp loại mong đợi
D9 = {"an": 5, "binh": 4, "chi": 4}
KPI = {"an": 113.311508, "binh": 73.901190, "chi": 40.0}
APPLICABLE = {"an": 100, "binh": 100, "chi": 25}
RATING = {"an": "excellent", "binh": "improve", "chi": False}


@tagged("post_install", "-at_install")
class TestKpiDemoScenario(TransactionCase):
    """Phase 4 — Hoàn thành khi: bấm Tính KPI ra đúng điểm như bảng tính tay cho 3 nhân viên mẫu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.period = cls.env.ref("project_kpi_management.demo_period_previous_month", raise_if_not_found=False)

    def setUp(self):
        super().setUp()
        if not self.period:
            self.skipTest("Database không có dữ liệu mẫu (cài không kèm demo).")

    def _evaluate(self, key):
        employee = self.env.ref(f"project_kpi_management.demo_employee_{key}")
        ev = self.env["kpi.evaluation"].create({"employee_id": employee.id, "period_id": self.period.id})
        ev.line_ids.filtered(lambda l: l.metric_id.code == "D9").actual = D9[key]
        ev.action_compute_kpi()
        return ev

    def test_actual_per_metric(self):
        for key, expected in EXPECTED.items():
            ev = self._evaluate(key)
            for code, (actual, volume) in expected.items():
                line = ev.line_ids.filtered(lambda l: l.metric_id.code == code)
                with self.subTest(employee=key, metric=code):
                    self.assertAlmostEqual(line.actual, actual, places=4)
                    self.assertAlmostEqual(line.volume, volume, places=4)

    def test_scores_and_ratings(self):
        for key in EXPECTED:
            ev = self._evaluate(key)
            with self.subTest(employee=key):
                self.assertEqual(ev.applicable_weight, APPLICABLE[key])
                self.assertAlmostEqual(ev.kpi_score, KPI[key], places=4)
                self.assertEqual(ev.rating, RATING[key])

    def test_binh_adjustment_reaches_pass(self):
        # Kịch bản demo: quản lý điều chỉnh +2 có lý do, Bình lên mức Đạt
        ev = self._evaluate("binh")
        ev.write({"manager_adjustment": 2, "adjustment_note": "Hỗ trợ xử lý sự cố production ngoài giờ"})
        self.assertAlmostEqual(ev.final_score, 75.901190, places=4)
        self.assertEqual(ev.final_rating, "pass")

    def test_chi_insufficient_data(self):
        ev = self._evaluate("chi")
        self.assertTrue(ev.insufficient_data)
        ev.write({"manual_rating": "pass", "manual_rating_note": "Nhân viên mới vào giữa kỳ"})
        ev.action_submit()
        self.assertEqual((ev.state, ev.final_rating), ("submitted", "pass"))
