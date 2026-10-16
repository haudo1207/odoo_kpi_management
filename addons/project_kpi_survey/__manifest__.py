{
    "name": "Project KPI - 360 feedback bridge",
    "version": "19.0.1.7.4",
    "summary": "Chỉ số F1 (phản hồi 360 độ) từ khảo sát có chấm điểm",
    "category": "Services/Project",
    "author": "Nam4",
    "license": "LGPL-3",
    "depends": ["project_kpi_management", "survey"],
    "data": [
        "security/ir.model.access.csv",
        "security/kpi_feedback_security.xml",
        "data/survey_360_data.xml",
        "data/kpi_feedback_data.xml",
        "wizard/kpi_feedback_invite_wizard_views.xml",
        "views/kpi_feedback_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
