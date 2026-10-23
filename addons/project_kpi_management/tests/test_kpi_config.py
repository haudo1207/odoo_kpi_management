from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestKpiConfig(TransactionCase):
    """Phase 1: chỉ số, bộ KPI, ràng buộc trọng số và quy tắc ẩn."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.d1 = cls.env.ref("project_kpi_management.kpi_metric_d1")
        cls.d2 = cls.env.ref("project_kpi_management.kpi_metric_d2")
        cls.d3 = cls.env.ref("project_kpi_management.kpi_metric_d3")
        cls.developer = cls.env.ref("project_kpi_management.kpi_template_developer")

    def _template(self, *weights):
        metrics = [self.d1, self.d2, self.d3]
        return self.env["kpi.template"].create({
            "name": "Test",
            "line_ids": [Command.create({"metric_id": m.id, "weight": w}) for m, w in zip(metrics, weights)],
        })

    def test_data_loaded(self):
        codes = self.env["kpi.metric"].search([]).mapped("code")
        self.assertTrue({f"D{i}" for i in range(1, 10)} <= set(codes))
        self.assertEqual(len(self.developer.line_ids), 9)
        self.assertEqual(self.developer.total_weight, 100)

    def test_display_name_and_search(self):
        self.assertEqual(self.d1.display_name, "D1 — Hoàn thành đúng hạn")
        self.assertIn(self.d3.id, [r[0] for r in self.env["kpi.metric"].name_search("D3")])

    def test_empty_template_allowed(self):
        self.assertTrue(self.env["kpi.template"].create({"name": "Rỗng"}))

    def test_total_weight_must_be_100(self):
        with self.assertRaises(ValidationError):
            self._template(90)
        template = self._template(60, 40)
        with self.assertRaises(ValidationError):
            template.write({"line_ids": [Command.update(template.line_ids[0].id, {"weight": 70})]})
        with self.assertRaises(ValidationError):
            template.write({"line_ids": [Command.delete(template.line_ids[0].id)]})

    def test_update_and_add_line_in_one_save(self):
        # Trường hợp "nửa chừng": sửa dòng cũ và thêm dòng mới trong cùng một lần lưu
        template = self._template(60, 40)
        l1, l2 = template.line_ids
        template.write({"line_ids": [
            Command.update(l1.id, {"weight": 50}),
            Command.update(l2.id, {"weight": 30}),
            Command.create({"metric_id": self.d3.id, "weight": 20}),
        ]})
        self.assertEqual(template.total_weight, 100)

    @mute_logger("odoo.sql_db")
    def test_duplicate_metric_code(self):
        with self.assertRaises(IntegrityError):
            self.env["kpi.metric"].create({"code": "D1", "name": "Trùng", "category": "delivery"})

    @mute_logger("odoo.sql_db")
    def test_duplicate_metric_in_template(self):
        with self.assertRaises(IntegrityError):
            self.env["kpi.template"].create({
                "name": "Trùng",
                "line_ids": [Command.create({"metric_id": self.d1.id, "weight": 50}),
                             Command.create({"metric_id": self.d1.id, "weight": 50})],
            })

    def test_archive_metric_used_in_active_template(self):
        with self.assertRaises(ValidationError):
            self.d1.action_archive()
        unused = self.env["kpi.metric"].create({
            "code": "TX", "name": "Không dùng", "category": "quality", "compute_mode": "manual",
        })
        unused.action_archive()
        self.assertFalse(unused.active)

    def test_archive_template_linked_to_job(self):
        template = self._template(60, 40)
        job = self.env["hr.job"].create({"name": "Job test", "kpi_template_id": template.id})
        with self.assertRaises(ValidationError):
            template.action_archive()
        job.kpi_template_id = False
        template.action_archive()
        self.assertFalse(template.active)

    def test_auto_metric_code_must_have_matching_function(self):
        """Phát hiện khi đọc code lại (chưa có test khoá): đổi mã (hoặc chuyển sang Tự động) mà không
        có hàm _metric_<mã>() tương ứng trong kpi.engine phải báo lỗi NGAY lúc lưu, không đợi tới lúc
        bấm "Tính KPI" (nơi lỗi hiện ra là UserError chung chung, khó truy ngược nguyên nhân)."""
        with self.assertRaises(ValidationError):
            self.d1.code = "D01"  # D1 đang dùng, đổi mã thì không còn hàm _metric_d01()
        self.assertEqual(self.d1.code, "D1")
        metric = self.env["kpi.metric"].create({
            "code": "ZZ", "name": "Không có hàm tính", "category": "quality", "compute_mode": "manual",
        })
        with self.assertRaises(ValidationError):
            metric.compute_mode = "auto"  # chuyển sang Tự động mà chưa có hàm _metric_zz()

    def test_all_kpi_modules_share_one_release_version(self):
        """Phiên bản trong __manifest__ của mọi module KPI đang cài phải giống nhau (và theo dạng 19.0.<phát hành>): một
        số phát hành duy nhất ứng với tag bảo vệ, để phiên bản hiển thị trong Odoo (Apps) không lệch với source."""
        from odoo.modules.module import get_manifest
        names = [m for m in ("project_kpi_management", "project_kpi_timesheet", "project_kpi_skills", "project_kpi_survey")
                 if self.env["ir.module.module"].search_count([("name", "=", m), ("state", "=", "installed")])]
        versions = {name: get_manifest(name)["version"] for name in names}
        self.assertEqual(len(set(versions.values())), 1, versions)
        self.assertRegex(next(iter(versions.values())), r"^19\.0\.\d+\.\d+\.\d+$")
