import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.tasks.email_inbox_sync_handler import handle_email_inbox_sync
from beyo_manager.services.tasks.location_tracker.handle_push_item_locations import (
    handle_push_item_locations,
)
from beyo_manager.models.database import init_db
from beyo_manager.workers.heartbeat import start_heartbeat
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.emails.handle_sync_email_threads_targeted import (
    handle_sync_email_threads_targeted,
)
from beyo_manager.services.tasks.emails.handle_send_email_messages import (
    handle_send_email_messages,
)
from beyo_manager.services.tasks.task_steps.finalize_pending_step_completion import (
    handle_finalize_pending_step_completion,
)
from beyo_manager.services.tasks.users.auto_clock_out_open_shifts import (
    handle_auto_clock_out_open_shifts,
)
from beyo_manager.services.tasks.connecteam.handle_connecteam_process_time_activity import (
    handle_connecteam_process_time_activity,
)
from beyo_manager.services.tasks.stock_report.handle_activate_stock_report_snapshot_version import (
    handle_activate_stock_report_snapshot_version,
)

HANDLER_MAP = {
    TaskType.DELAYED_STEP_COMPLETION: handle_finalize_pending_step_completion,
    TaskType.EMAIL_INBOX_SYNC: handle_email_inbox_sync,
    TaskType.EMAIL_SYNC_TARGETED: handle_sync_email_threads_targeted,
    TaskType.SEND_EMAIL_MESSAGES: handle_send_email_messages,
    TaskType.LOCATION_TRACKER_PUSH_LOCATIONS: handle_push_item_locations,
    TaskType.AUTO_CLOCK_OUT_OPEN_SHIFTS: handle_auto_clock_out_open_shifts,
    TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY: handle_connecteam_process_time_activity,
    TaskType.STOCK_REPORT_VERSION_ACTIVATION: handle_activate_stock_report_snapshot_version,
}


async def main() -> None:
    await init_db()
    start_heartbeat()
    await run_worker("queue:tasks", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
