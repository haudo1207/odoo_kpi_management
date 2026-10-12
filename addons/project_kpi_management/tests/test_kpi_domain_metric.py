from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKpiDomainMetric(TransactionCase):
    """Bước 1 (Chương 9.1): chỉ số cấu hình không cần code — kiểm tra hợp lệ khi lưu và phân quyền."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task_model = cls.env["ir.model"].search([("model", "=", "project.task")], limit=1)
        cls.partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        cls.task_name_field = cls.env["ir.model.fields"].search(
            [("model_id", "=", cls.task_model.id), ("name", "=", "name")], limit=1
        )
        cls.partner_name_field = cls.env["ir.model.fields"].search(
            [("model_id", "=", cls.partner_model.id), ("name", "=", "name")], limit=1
        )

    def _vals(self, **extra):
        return {
            "code": "DOMAIN_TEST", "name": "Chỉ số cấu hình test", "category": "quality",
            "compute_mode": "domain", "source_model_id": self.task_model.id, "aggregation": "count",
            "numerator_domain": "[]", **extra,
        }

    def test_model_outside_allowed_list_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["kpi.metric"].create(self._vals(source_model_id=self.partner_model.id))

    def test_field_from_other_model_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["kpi.metric"].create(self._vals(user_field_id=self.partner_name_field.id))

    def test_invalid_domain_syntax_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["kpi.metric"].create(self._vals(numerator_domain="[('khong_ton_tai', '=', 1)"))  # thiếu ]

    def test_ratio_without_denominator_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["kpi.metric"].create(self._vals(aggregation="ratio", denominator_domain=""))

    def test_sum_without_value_field_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["kpi.metric"].create(self._vals(aggregation="sum"))

    def test_valid_config_saved(self):
        metric = self.env["kpi.metric"].create(self._vals())
        self.assertEqual(metric.compute_mode, "domain")

    def test_only_admin_writes_domain_config(self):
        user = new_test_user(self.env, login="kpi_domain_metric_user", groups="project_kpi_management.group_kpi_user")
        with self.assertRaises(AccessError):
            self.env["kpi.metric"].with_user(user).create(self._vals())
