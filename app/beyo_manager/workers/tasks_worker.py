import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.tasks.email_inbox_sync_handler import handle_email_inbox_sync
from beyo_manager.services.tasks.location_tracker.handle_push_item_locations import (
    handle_push_item_locations,
)
from beyo_manager.models.database import init_db
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

HANDLER_MAP = {
    TaskType.DELAYED_STEP_COMPLETION: handle_finalize_pending_step_completion,
    TaskType.EMAIL_INBOX_SYNC: handle_email_inbox_sync,
    TaskType.EMAIL_SYNC_TARGETED: handle_sync_email_threads_targeted,
    TaskType.SEND_EMAIL_MESSAGES: handle_send_email_messages,
    TaskType.LOCATION_TRACKER_PUSH_LOCATIONS: handle_push_item_locations,
}


async def main() -> None:
    await init_db()
    await run_worker("queue:tasks", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
