from odoo import api, models


def _valid_on(skills, day):
    """Kỹ năng còn hiệu lực tại một ngày: valid_from <= ngày và (valid_to trống hoặc valid_to >= ngày)."""
    return skills.filtered(lambda s: (not s.valid_from or s.valid_from <= day) and (not s.valid_to or s.valid_to >= day))


def _best_levels(skills):
    """{skill_id: mức cao nhất (level_progress)} — nhiều bản ghi cùng kỹ năng còn hiệu lực thì lấy mức cao nhất."""
    best = {}
    for skill in skills:
        best[skill.skill_id.id] = max(best.get(skill.skill_id.id, 0), skill.level_progress)
    return best


class KpiEngine(models.AbstractModel):
    _inherit = "kpi.engine"

    @api.model
    def _metric_s1(self, ctx):
        """Đợt D2 (S1): mức đáp ứng kỹ năng = số kỹ năng đạt / số kỹ năng yêu cầu của chức danh × 100.
        - Chức danh là chức danh ĐÃ CHỤP trên phiếu (ctx["job"]), không phải chức danh hiện tại.
        - Kỹ năng yêu cầu: hr.job.skill còn hiệu lực tại ngày cuối kỳ; kỹ năng nhân viên: hr.employee.skill còn hiệu lực
          tại cùng ngày. Nhờ hiệu lực theo ngày cuối kỳ, nâng mức kỹ năng SAU kỳ không đổi kết quả của kỳ cũ.
        - Đạt khi nhân viên có cùng kỹ năng với level_progress >= mức yêu cầu (so theo phần trăm tiến độ nên đúng cho mọi
          loại kỹ năng, không phụ thuộc thứ tự mức); thiếu kỹ năng tính là không đạt.
        - Khối lượng = số kỹ năng yêu cầu; chức danh không yêu cầu kỹ năng nào thì khối lượng 0 → "Không áp dụng"."""
        day = ctx["date_to"]
        required = _best_levels(_valid_on(ctx["job"].job_skill_ids, day))
        if not required:
            return 0.0, 0
        owned = _best_levels(_valid_on(ctx["employee"].employee_skill_ids, day))
        passed = sum(1 for skill_id, level in required.items() if owned.get(skill_id, -1) >= level)
        return self._ratio(passed, len(required)), len(required)
