from . import models
from . import wizard


def post_init_hook(env):
    """Task đã Done trước khi cài module có thể thiếu date_end (stage Done không fold).
    Bù bằng lần đổi stage cuối, để D1 và D7 dùng được dữ liệu cũ."""
    tasks = env["project.task"].with_context(active_test=False).search([
        ("state", "=", "1_done"),
        ("date_end", "=", False),
    ])
    for task in tasks:
        task.date_end = task.date_last_stage_update or task.write_date
