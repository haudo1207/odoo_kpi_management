import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KpiScoreScale(models.Model):
    """Bước 3 (Chương 9.3): bảng bậc điểm. Tra theo % đạt mục tiêu (không theo giá trị thực tế) nên một
    bảng dùng chung được cho nhiều chỉ số, kể cả khi mục tiêu đổi theo phòng ban. Mỗi bậc chỉ khai báo
    điểm bắt đầu (% từ); bậc kéo dài tới điểm bắt đầu của bậc kế tiếp (không gồm), bậc cuối không giới hạn
    — nên các khoảng không thể chồng nhau và phủ liên tục từ 0 (xem _check_steps)."""

    _name = "kpi.score.scale"
    _description = "Bảng bậc điểm KPI"
    _order = "name"

    name = fields.Char("Tên bảng bậc", required=True)
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("kpi.score.scale.step", "scale_id", string="Các bậc", copy=True)
    description = fields.Text("Mô tả")

    @api.constrains("name", "step_ids")  # name có mặt ở mọi lần tạo: bảng rỗng cũng bị bắt
    def _check_steps(self):
        for scale in self:
            starts = scale.step_ids.mapped("pct_from")
            if not starts:
                raise ValidationError(f"Bảng bậc \"{scale.name}\" phải có ít nhất một bậc.")
            if len(set(starts)) != len(starts):
                raise ValidationError(f"Bảng bậc \"{scale.name}\": có hai bậc bắt đầu cùng một mức % (các khoảng chồng nhau).")
            if min(starts) != 0:
                raise ValidationError(
                    f"Bảng bậc \"{scale.name}\": bậc thấp nhất phải bắt đầu từ 0% để phủ liên tục, không để hở khoảng."
                )

    @api.constrains("active")
    def _check_archive_in_active_template(self):
        # Cùng quy tắc với chỉ số: không ẩn khi bộ KPI đang hoạt động còn dùng (phiếu tạo mới vẫn chụp nó).
        # Xoá thì ondelete="restrict" trên kpi.template.line.scale_id đã chặn.
        archived = self.filtered(lambda s: not s.active)
        lines = self.env["kpi.template.line"].search([
            ("scale_id", "in", archived.ids), ("template_id.active", "=", True),
        ]) if archived else self.env["kpi.template.line"]
        if lines:
            raise ValidationError(
                "Không thể ẩn bảng bậc đang được dùng trong bộ KPI: %s.\n"
                "Hãy gỡ bảng bậc khỏi các bộ KPI này trước." % ", ".join(lines.template_id.mapped("name"))
            )

    def _snapshot(self):
        """JSON chụp vào dòng phiếu: danh sách [% từ, điểm] tăng dần theo % từ. Phiếu đã tạo giữ nguyên
        bảng bậc này, sửa bảng bậc sau đó không đổi điểm phiếu cũ (giống mục tiêu).
        Kiểm tra lại tính hợp lệ NGAY lúc dùng: dù bảng bị ghi sai bằng đường bỏ qua form (API ghi thẳng vào
        từng bậc) thì cũng không tạo được phiếu, sai số không đi vào điểm."""
        self.ensure_one()
        self._check_steps()
        return json.dumps([[s.pct_from, s.score] for s in self.step_ids.sorted("pct_from")])

    @staticmethod
    def lookup(scale_json, pct):
        """Điểm của bậc chứa `pct`: bậc có % từ lớn nhất mà vẫn ≤ pct."""
        score = 0.0
        for pct_from, step_score in sorted(json.loads(scale_json)):
            if pct >= pct_from:
                score = step_score
        return score


class KpiScoreScaleStep(models.Model):
    _name = "kpi.score.scale.step"
    _description = "Bậc của bảng bậc điểm KPI"
    _order = "scale_id, pct_from"

    scale_id = fields.Many2one("kpi.score.scale", required=True, ondelete="cascade", index=True)
    pct_from = fields.Float("Từ % đạt mục tiêu", digits=(16, 2), required=True)
    pct_to = fields.Float("Đến % (không gồm)", digits=(16, 2), compute="_compute_pct_to")
    score = fields.Float("Điểm", digits=(16, 2), required=True)

    _pct_from_positive = models.Constraint("CHECK(pct_from >= 0)", "% đạt mục tiêu bắt đầu không được âm.")
    _score_positive = models.Constraint("CHECK(score >= 0)", "Điểm của bậc không được âm.")

    @api.depends("scale_id.step_ids.pct_from")
    def _compute_pct_to(self):
        for step in self:
            later = step.scale_id.step_ids.filtered(lambda s: s.pct_from > step.pct_from).mapped("pct_from")
            step.pct_to = min(later) if later else 0.0  # 0 = không giới hạn (bậc cuối)
