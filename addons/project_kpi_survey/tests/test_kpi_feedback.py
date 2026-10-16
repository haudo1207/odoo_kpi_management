from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiFeedback(TransactionCase):
    """Đợt D1 (v1.7): phản hồi 360 độ qua survey. Chạy riêng: --test-tags /project_kpi_survey (cần module survey)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        today = fields.Date.today()
        cls.period = env["kpi.period"].create({"name": "Kỳ 360", "date_from": today - timedelta(days=20), "date_to": today + timedelta(days=10)})
        group = "base.group_user,project_kpi_management."
        cls.manager = new_test_user(env, login="fb_manager", groups=group + "group_kpi_manager")
        cls.other_manager = new_test_user(env, login="fb_other_manager", groups=group + "group_kpi_manager")
        cls.user = new_test_user(env, login="fb_employee", groups=group + "group_kpi_user")
        manager_employee = env["hr.employee"].create({"name": "QL 360", "user_id": cls.manager.id})
        cls.employee = env["hr.employee"].create({
            "name": "NV 360", "user_id": cls.user.id, "parent_id": manager_employee.id,
            "job_id": env.ref("project_kpi_management.hr_job_developer").id,
        })
        cls.reviewers = [new_test_user(env, login=f"fb_rev{i}", groups="base.group_user") for i in range(4)]
        cls.survey = env.ref("project_kpi_survey.survey_360")
        cls.template = env.ref("project_kpi_survey.kpi_template_developer_360")

    def _evaluation(self):
        return self.env["kpi.evaluation"].create({
            "employee_id": self.employee.id, "period_id": self.period.id, "template_id": self.template.id,
        })

    def _invite(self, ev, reviewers, user=None):
        wizard = self.env["kpi.feedback.invite.wizard"].with_user(user or self.manager).create({
            "evaluation_id": ev.id, "reviewer_ids": [(6, 0, [r.id for r in reviewers])],
        })
        return wizard.action_invite()

    def _answer(self, request, score):
        """Trả lời đúng đường controller khảo sát dùng: _save_lines cho từng câu rồi _mark_done."""
        answer = request.user_input_id
        for question in self.survey.question_ids:
            choice = question.suggested_answer_ids.filtered(lambda a: a.answer_score == score)
            answer._save_lines(question, choice.id)
        answer._mark_done()

    def _f1_line(self, ev):
        return ev.line_ids.filtered(lambda l: l.metric_id.code == "F1")

    # ---- Chỉ số F1 ----

    def test_below_three_answers_not_applicable_and_hidden(self):
        ev = self._evaluation()
        self._invite(ev, self.reviewers[:3])
        for request, score in zip(ev.feedback_request_ids[:2], (5, 4)):
            self._answer(request, score)
        ev.action_compute_kpi()
        line = self._f1_line(ev)
        self.assertEqual((line.volume, line.actual, line.is_applicable), (2, 0.0, False))
        self.assertEqual((ev.feedback_invited_count, ev.feedback_done_count, ev.feedback_score_visible), (3, 2, False))
        self.assertEqual(ev.feedback_avg_score, 0.0)  # không lộ điểm của 1-2 người

    def test_three_answers_average_matches_hand_calculation(self):
        """Ba người chấm toàn 5, toàn 4, toàn 3 → 100%, 80%, 60% (tổng điểm / tối đa 20) → trung bình 80%;
        mục tiêu F1 là 80 → đạt 100% mục tiêu."""
        ev = self._evaluation()
        self._invite(ev, self.reviewers[:3])
        for request, score in zip(ev.feedback_request_ids, (5, 4, 3)):
            self._answer(request, score)
        ev.action_compute_kpi()
        line = self._f1_line(ev)
        self.assertEqual((line.volume, line.is_applicable), (3, True))
        self.assertAlmostEqual(line.actual, 80.0)
        self.assertAlmostEqual(line.score, 100.0)
        self.assertAlmostEqual(ev.feedback_avg_score, 80.0)
        self.assertTrue(ev.feedback_score_visible)
        self.assertEqual(sum(ev.template_id.line_ids.mapped("weight")), 100)

    def test_unfinished_and_test_entries_ignored(self):
        ev = self._evaluation()
        self._invite(ev, self.reviewers)
        requests = ev.feedback_request_ids
        for request in requests[:3]:
            self._answer(request, 4)
        # người thứ tư mới trả lời dở dang (chưa nộp): không tính
        partial = requests[3].user_input_id
        partial._save_lines(self.survey.question_ids[0], self.survey.question_ids[0].suggested_answer_ids[0].id)
        self.assertNotEqual(partial.state, "done")
        ev.action_compute_kpi()
        self.assertEqual(self._f1_line(ev).volume, 3)
        # một bản test đã hoàn thành cũng không tính
        requests[3].user_input_id.sudo().test_entry = True
        self._answer(requests[3], 1)
        ev.action_compute_kpi()
        self.assertEqual(self._f1_line(ev).volume, 3)
        self.assertAlmostEqual(self._f1_line(ev).actual, 80.0)

    def test_late_answer_does_not_change_submitted_evaluation(self):
        ev = self._evaluation()
        self._invite(ev, self.reviewers)
        for request in ev.feedback_request_ids[:3]:
            self._answer(request, 4)
        ev.action_compute_kpi()
        before = self._f1_line(ev).actual
        ev.write({"state": "submitted"})
        self._answer(ev.feedback_request_ids[3], 1)  # đến muộn, rất thấp
        self.assertEqual(self._f1_line(ev).actual, before)   # phiếu đã khoá, không tự đổi
        with self.assertRaises(UserError):
            ev.action_compute_kpi()

    # ---- Quy tắc mời ----

    def test_invite_rules(self):
        ev = self._evaluation()
        with self.assertRaises(UserError):
            self._invite(ev, [self.user])                       # chính nhân viên
        with self.assertRaises(UserError):
            self._invite(ev, [])                                # không chọn ai
        self._invite(ev, self.reviewers[:1])
        with self.assertRaises(UserError):
            self._invite(ev, self.reviewers[:1])                # mời trùng
        with self.assertRaises(AccessError):
            self._invite(ev, self.reviewers[1:2], user=self.other_manager)  # không phải quản lý của nhân viên
        ev.write({"state": "submitted"})
        with self.assertRaises(UserError):
            self._invite(ev, self.reviewers[1:2])               # phiếu không còn Nháp

    def test_reminder_per_reviewer_and_done_when_answered(self):
        ev = self._evaluation()
        self._invite(ev, self.reviewers[:2])
        act_type = self.env.ref("project_kpi_survey.mail_activity_type_feedback")
        for request in ev.feedback_request_ids:
            acts = request.activity_ids.filtered(lambda a: a.activity_type_id == act_type)
            self.assertEqual((len(acts), acts.user_id), (1, request.reviewer_id))
            self.assertIn("/survey/", acts.note)  # có link khảo sát riêng
        first = ev.feedback_request_ids[0]
        self._answer(first, 5)
        self.assertEqual(first.state, "done")
        self.assertFalse(first.activity_ids.filtered(lambda a: a.activity_type_id == act_type))  # tự đánh dấu xong
        self.assertTrue(ev.feedback_request_ids[1].activity_ids)

    # ---- Quyền và ẩn danh ----

    def test_manager_sees_invitees_but_not_answers(self):
        ev = self._evaluation()
        self._invite(ev, self.reviewers[:3])
        for request in ev.feedback_request_ids:
            self._answer(request, 5)
        requests = self.env["kpi.feedback.request"].with_user(self.manager).search([("evaluation_id", "=", ev.id)])
        self.assertEqual(len(requests), 3)                      # xem được ai được mời và trạng thái
        self.assertEqual(set(requests.mapped("state")), {"done"})
        with self.assertRaises(AccessError):                    # nhưng không đọc được nội dung/điểm câu trả lời
            self.env["survey.user_input"].with_user(self.manager).check_access("read")
        with self.assertRaises(AccessError):
            requests[0].user_input_id.scoring_percentage
        own = self.env["kpi.feedback.request"].with_user(self.reviewers[0]).search([])
        self.assertEqual(own.reviewer_id, self.reviewers[0])    # người được mời chỉ thấy lời mời của chính mình
        self.assertEqual(self.env["kpi.feedback.request"].with_user(self.other_manager).search_count([("evaluation_id", "=", ev.id)]), 0)
