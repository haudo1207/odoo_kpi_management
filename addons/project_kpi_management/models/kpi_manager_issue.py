from odoo import api, fields, models


class KpiManagerIssue(models.TransientModel):
    """Lỗi cấu hình mà Admin cần sửa tận gốc: quản lý trực tiếp của nhân viên (có bộ KPI) chưa có tài khoản hoặc chưa
    thuộc nhóm KPI Manager — người đó không đọc được phiếu của nhân viên nên nhắc việc phải chuyển cho người duyệt
    mặc định (xem kpi.evaluation._kpi_assignee). Báo cáo Kiểm tra dữ liệu theo dự án nên không chứa được lỗi theo
    nhân viên này; hr.employee chỉ đọc được bởi nhóm Nhân sự nên danh sách được dựng bằng sudo, mở từ menu."""

    _name = "kpi.manager.issue"
    _description = "Quản lý trực tiếp chưa có quyền KPI"

    employee_name = fields.Char("Nhân viên", readonly=True)
    job_name = fields.Char("Chức danh", readonly=True)
    manager_name = fields.Char("Quản lý trực tiếp", readonly=True)
    reason = fields.Char("Vấn đề", readonly=True)

    @api.model
    def action_open(self):
        manager_group = "project_kpi_management.group_kpi_manager"
        vals_list = []
        for employee in self.env["hr.employee"].sudo().search([("user_id", "!=", False)]):
            if not (employee.job_id.kpi_template_id and employee.parent_id):
                continue
            user = employee.parent_id.user_id
            if not user:
                reason = "Quản lý trực tiếp chưa có tài khoản người dùng."
            elif not user.has_group(manager_group):
                reason = "Quản lý trực tiếp chưa thuộc nhóm KPI Manager (không đọc được phiếu của nhân viên)."
            else:
                continue
            vals_list.append({
                "employee_name": employee.name, "job_name": employee.job_id.name,
                "manager_name": employee.parent_id.name, "reason": reason,
            })
        records = self.create(vals_list)
        return {
            "type": "ir.actions.act_window", "name": "Quản lý chưa có quyền KPI", "res_model": self._name,
            "view_mode": "list", "domain": [("id", "in", records.ids)], "target": "current",
            "help": "Không có vấn đề nào.",
        }
