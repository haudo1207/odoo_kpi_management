"""REST API phiếu đánh giá KPI.

Xác thực: header "Authorization: Bearer <API key>" (Odoo 19, auth='bearer'). API key tạo ở
Hồ sơ người dùng › Bảo mật tài khoản › API Keys. Mọi truy vấn chạy bằng quyền của người sở hữu
key, nên record rule KPI vẫn áp dụng: nhân viên chỉ thấy phiếu của mình, quản lý thấy phiếu của nhóm.

GET  /api/kpi/evaluations                        danh sách phiếu (lọc: period_id, state, limit, offset)
GET  /api/kpi/evaluations/<id>                   chi tiết phiếu kèm từng chỉ số
POST /api/kpi/evaluations/<id>/metrics/<code>    ghi số liệu cho chỉ số nhập tay, body JSON {"actual", "remark"?}
"""
import functools

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request

MAX_LIMIT = 200


def _json(data, status=200):
    return request.make_json_response(data, status=status)


def _handle_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AccessError as e:
            return _json({"error": str(e)}, 403)
        except MissingError as e:
            return _json({"error": str(e)}, 404)
        except (UserError, ValidationError, ValueError) as e:
            return _json({"error": str(e)}, 400)
    return wrapper


def _summary(ev):
    return {
        "id": ev.id,
        "employee": {"id": ev.employee_id.id, "name": ev.employee_id.name},
        "period": {"id": ev.period_id.id, "name": ev.period_id.name,
                   "date_from": str(ev.period_id.date_from), "date_to": str(ev.period_id.date_to)},
        "state": ev.state,
        "kpi_score": round(ev.kpi_score, 2),
        "manager_adjustment": ev.manager_adjustment,
        "final_score": round(ev.final_score, 2),
        "final_rating": ev.final_rating or None,
        "insufficient_data": ev.insufficient_data,
    }


def _detail(ev):
    data = _summary(ev)
    data["lines"] = [{
        "metric": line.metric_id.code,
        "name": line.metric_id.name,
        "compute_mode": line.compute_mode,
        "target": line.target,
        "actual": line.actual,
        "unit": line.unit or None,
        "weight": line.weight,
        "volume": line.volume,
        "is_applicable": line.is_applicable,
        "score": round(line.score, 2),
        "remark": line.remark or None,
    } for line in ev.line_ids]
    return data


class KpiApi(http.Controller):

    def _get_evaluation(self, evaluation_id):
        # search áp dụng record rule: phiếu không được phép xem trả về 404, không lộ là có tồn tại
        ev = request.env["kpi.evaluation"].search([("id", "=", evaluation_id)])
        if not ev:
            raise MissingError(f"Không tìm thấy phiếu {evaluation_id}.")
        return ev

    @http.route("/api/kpi/evaluations", type="http", auth="bearer", methods=["GET"], csrf=False, readonly=True)
    @_handle_errors
    def list_evaluations(self, period_id=None, state=None, limit=50, offset=0, **kw):
        domain = []
        if period_id:
            domain.append(("period_id", "=", int(period_id)))
        if state:
            domain.append(("state", "=", state))
        limit = min(int(limit), MAX_LIMIT)
        Evaluation = request.env["kpi.evaluation"]
        evaluations = Evaluation.search(domain, limit=limit, offset=int(offset))
        return _json({
            "count": Evaluation.search_count(domain),
            "limit": limit,
            "offset": int(offset),
            "items": [_summary(ev) for ev in evaluations],
        })

    @http.route("/api/kpi/evaluations/<int:evaluation_id>", type="http", auth="bearer", methods=["GET"],
                csrf=False, readonly=True)
    @_handle_errors
    def get_evaluation(self, evaluation_id, **kw):
        return _json(_detail(self._get_evaluation(evaluation_id)))

    @http.route("/api/kpi/evaluations/<int:evaluation_id>/metrics/<string:code>", type="http", auth="bearer",
                methods=["POST"], csrf=False)
    @_handle_errors
    def post_metric(self, evaluation_id, code, **kw):
        """Công cụ ngoài (ví dụ CI, công cụ quản lý test) đẩy số liệu cho chỉ số nhập tay.
        Chỉ số tự động không nhận số liệu ngoài vì Tính KPI sẽ ghi đè."""
        ev = self._get_evaluation(evaluation_id)
        payload = request.get_json_data()
        if not isinstance(payload, dict) or "actual" not in payload:
            raise ValueError('Body phải là JSON có trường "actual".')
        line = ev.line_ids.filtered(lambda l: l.metric_id.code == code)
        if not line:
            raise MissingError(f"Phiếu {evaluation_id} không có chỉ số {code}.")
        if line.compute_mode != "manual":
            raise UserError(f"Chỉ số {code} tính tự động, không nhận số liệu từ bên ngoài.")
        vals = {"actual": float(payload["actual"]), "actual_entered": True}
        if "remark" in payload:
            vals["remark"] = payload["remark"]
        line.write(vals)  # quyền ghi, trạng thái Nháp được kiểm như khi sửa trên giao diện
        return _json(_detail(ev))
