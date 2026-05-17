import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.infra.jobs.handlers.notification import handle_notification
from beyo_manager.services.tasks.notifications.create_notifications import handle_create_notifications
from beyo_manager.services.tasks.notifications.send_push_notification import handle_send_push_notification
from beyo_manager.services.infra.jobs.handlers.reminder import handle_reminder

HANDLER_MAP = {
    TaskType.NOTIFICATION:               handle_notification,
    TaskType.CREATE_NOTIFICATIONS:       handle_create_notifications,
    TaskType.SEND_PUSH_NOTIFICATION:     handle_send_push_notification,
    TaskType.DELAYED_NOTIFY_TO_CUSTOMER: handle_notification,
    TaskType.DELAYED_REMINDER:           handle_reminder,
    TaskType.DELAYED_BATCH_NOTIFICATION: handle_notification,
    TaskType.RECURRING_REMINDER:         handle_reminder,
}

async def main() -> None:
    await init_db()
    await run_worker("queue:notifications", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
