from odoo.exceptions import AccessError, UserError
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
        # Tự gọi, không còn phụ thuộc --with-demo: kịch bản không tự chạy khi cài module nữa
        # (xem data/kpi_demo_scenario_action.xml), nên test phải nạp lấy để chạy độc lập.
        cls.env["kpi.demo"]._load_scenario()
        cls.period = cls.env.ref("project_kpi_management.demo_period_previous_month")

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

    def test_happy_path_full_approval_cycle(self):
        """Luồng đầy đủ nối liền: dữ liệu task/bug/lịch thật → Engine tính →
        Gửi duyệt → Duyệt → khoá. Các test khác kiểm từng khúc rời (dữ liệu
        thật nhưng dừng ở compute/submit, hoặc đi hết submit/approve nhưng với
        actual/volume chèn tay) — bài này ráp cả chuỗi lại để bắt lỗi chỉ lộ
        ra khi ba bước ghép với nhau, ví dụ compute xong mà submit không nhận,
        hoặc duyệt xong mà phiếu/dòng vẫn còn sửa được."""
        ev = self._evaluate("an")
        self.assertEqual(ev.state, "draft")
        self.assertTrue(ev.computed_date)

        ev.action_submit()
        self.assertEqual(ev.state, "submitted")

        ev.action_approve()
        self.assertEqual(ev.state, "approved")
        self.assertAlmostEqual(ev.final_score, KPI["an"], places=4)
        self.assertEqual(ev.final_rating, "excellent")

        # Phiếu đã duyệt: khoá cả phiếu lẫn từng dòng, không sửa được nữa
        with self.assertRaises(UserError):
            ev.write({"manager_adjustment": 1, "adjustment_note": "thử sửa sau khi duyệt"})
        with self.assertRaises(UserError):
            ev.line_ids[:1].write({"actual": 999})

    def test_admin_manager_role_conflict(self):
        """Mục 2: một người vừa là quản lý trực tiếp vừa được gán thêm KPI Administrator
        không được tự duyệt phiếu của nhân viên mình quản lý (Chương 8.3 cũ), nhưng vẫn
        duyệt được phiếu của nhân viên không do mình quản lý trực tiếp."""
        manager_user = self.env.ref("project_kpi_management.demo_user_manager")
        manager_user.write({"group_ids": [(4, self.env.ref("project_kpi_management.group_kpi_admin").id)]})

        ev_an = self._evaluate("an")
        ev_an.action_submit()
        with self.assertRaises(AccessError):
            ev_an.with_user(manager_user).action_approve()
        self.assertEqual(ev_an.state, "submitted")

        dev_job = self.env.ref("project_kpi_management.hr_job_developer")
        other_user = self.env["res.users"].create({"name": "Đỗ Thu Hương", "login": "huong_test"})
        other_employee = self.env["hr.employee"].create({
            "name": "Đỗ Thu Hương", "user_id": other_user.id,
            "job_id": dev_job.id, "department_id": dev_job.department_id.id,
        })
        ev_other = self.env["kpi.evaluation"].create({"employee_id": other_employee.id, "period_id": self.period.id})
        ev_other.line_ids.filtered(lambda l: l.metric_id.code == "D9").actual = 4
        ev_other.action_compute_kpi()
        # Nhân viên mới tạo, không có task/bug: chỉ D9 áp dụng, không đủ trọng số như "chi"
        ev_other.write({"manual_rating": "pass", "manual_rating_note": "Nhân viên khác nhóm, không có dữ liệu task"})
        ev_other.action_submit()
        ev_other.with_user(manager_user).action_approve()
        self.assertEqual(ev_other.state, "approved")

    def test_pip_activity_on_improve_rating(self):
        """Mục 3: duyệt phiếu Cần cải thiện tạo đúng 1 nhắc việc PIP cho quản lý trực tiếp;
        Mở lại rồi Duyệt lại không tạo trùng nhắc việc."""
        pip_type = self.env.ref("project_kpi_management.mail_activity_type_pip")
        manager_user = self.env.ref("project_kpi_management.demo_user_manager")
        ev = self._evaluate("binh")
        ev.action_submit()
        ev.action_approve()
        self.assertEqual(ev.final_rating, "improve")
        activities = ev.activity_ids.filtered(lambda a: a.activity_type_id == pip_type)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities.user_id, manager_user)

        wizard = self.env["kpi.evaluation.reason.wizard"].create(
            {"evaluation_id": ev.id, "mode": "reopen", "reason": "Kiểm tra lại dữ liệu"}
        )
        wizard.action_confirm()
        self.assertEqual(ev.state, "draft")
        self.assertFalse(ev.activity_ids.filtered(lambda a: a.activity_type_id == pip_type))

        ev.action_submit()
        ev.action_approve()
        self.assertEqual(len(ev.activity_ids.filtered(lambda a: a.activity_type_id == pip_type)), 1)

    def test_no_pip_activity_when_not_improve(self):
        """Mục 3: phiếu không xếp loại Cần cải thiện thì không tạo nhắc việc PIP."""
        pip_type = self.env.ref("project_kpi_management.mail_activity_type_pip")
        ev = self._evaluate("an")
        ev.action_submit()
        ev.action_approve()
        self.assertEqual(ev.final_rating, "excellent")
        self.assertFalse(ev.activity_ids.filtered(lambda a: a.activity_type_id == pip_type))

    def test_self_assessment_wizard(self):
        """Mục 6: nhân viên tự đánh giá qua wizard — chỉ tham khảo, không cộng điểm, không nới
        quyền ghi trực tiếp lên kpi.evaluation."""
        ev = self._evaluate("an")
        an_user = self.env.ref("project_kpi_management.demo_user_an")
        manager_user = self.env.ref("project_kpi_management.demo_user_manager")
        manual_line = ev.line_ids.filtered(lambda l: l.compute_mode == "manual")
        self.assertEqual(len(manual_line), 1)

        def _wizard(user):
            return self.env["kpi.self.assessment.wizard"].with_user(user).create({
                "evaluation_id": ev.id,
                "employee_comment": "Tháng này tôi hoàn thành tốt các task được giao.",
                "line_ids": [(0, 0, {"evaluation_line_id": manual_line.id, "self_score": 5})],
            })

        # Người khác (kể cả quản lý trực tiếp) không tự đánh giá thay được
        with self.assertRaises(AccessError):
            _wizard(manager_user).action_confirm()

        # employee_comment chặn ghi trực tiếp cho MỌI người không qua sudo() — kể cả chính nhân
        # viên (vốn dĩ chỉ có quyền đọc, lẽ ra đã bị AccessError) và quản lý (CÓ quyền ghi trên
        # kpi.evaluation cho manager_adjustment... nên nếu không chặn riêng sẽ ghi hộ được)
        with self.assertRaises(UserError):
            ev.with_user(an_user).write({"employee_comment": "Ghi trực tiếp"})
        with self.assertRaises(UserError):
            ev.with_user(manager_user).write({"employee_comment": "Quản lý ghi hộ"})

        # self_score cùng bản chất: quản lý có quyền ghi dòng phiếu khi Nháp (để nhập D9), nên
        # phải chặn riêng self_score như employee_comment, cả ở write() lẫn create()
        with self.assertRaises(UserError):
            manual_line.with_user(manager_user).write({"self_score": 1})
        binh = self.env.ref("project_kpi_management.demo_employee_binh")
        with self.assertRaises(UserError):
            self.env["kpi.evaluation.line"].with_user(manager_user).create({
                "evaluation_id": ev.id, "metric_id": manual_line.metric_id.id, "self_score": 1,
            })
        with self.assertRaises(UserError):
            self.env["kpi.evaluation"].with_user(manager_user).create({
                "employee_id": binh.id, "period_id": ev.period_id.id, "employee_comment": "Tạo kèm luôn",
            })

        # Đúng người, đúng trạng thái Nháp: ghi được qua wizard
        _wizard(an_user).action_confirm()
        self.assertEqual(ev.employee_comment, "Tháng này tôi hoàn thành tốt các task được giao.")
        self.assertEqual(manual_line.self_score, 5)
        self.assertEqual(ev.final_rating, "excellent")  # self_score không ảnh hưởng xếp loại

        # Phiếu không còn Nháp thì không tự đánh giá được nữa
        ev.action_submit()
        with self.assertRaises(UserError):
            _wizard(an_user).action_confirm()

    def test_copy_does_not_duplicate_self_assessment(self):
        """Góp ý: employee_comment/self_score phải copy=False — nếu không, Nhân bản một phiếu đã
        tự đánh giá sẽ bị chặn create() (Mục 6) với lỗi khó hiểu, thay vì nhân bản bình thường."""
        ev = self._evaluate("an")
        an_user = self.env.ref("project_kpi_management.demo_user_an")
        manual_line = ev.line_ids.filtered(lambda l: l.compute_mode == "manual")
        wiz = self.env["kpi.self.assessment.wizard"].with_user(an_user).create({
            "evaluation_id": ev.id,
            "employee_comment": "Nhận xét gốc",
            "line_ids": [(0, 0, {"evaluation_line_id": manual_line.id, "self_score": 5})],
        })
        wiz.action_confirm()

        other_period = self.env["kpi.period"].create({
            "name": "Kỳ sao chép test", "date_from": "2026-11-01", "date_to": "2026-11-30",
        })
        copy = ev.copy({"period_id": other_period.id})
        self.assertFalse(copy.employee_comment)
        copy_manual_line = copy.line_ids.filtered(lambda l: l.compute_mode == "manual")
        self.assertEqual(copy_manual_line.self_score, 0)
