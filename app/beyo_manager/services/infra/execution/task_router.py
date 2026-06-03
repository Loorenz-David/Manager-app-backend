import asyncio
import logging
from datetime import datetime, timezone, timedelta

import asyncpg
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.infra.redis import get_redis_client
from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)

QUEUE_MAP: dict[TaskType, str] = {
    TaskType.NOTIFICATION:               "queue:notifications",
    TaskType.CREATE_NOTIFICATIONS:       "queue:notifications",
    TaskType.SEND_PUSH_NOTIFICATION:     "queue:notifications",
    TaskType.UPLOAD_IMAGE:               "queue:uploads",
    TaskType.DELIVER_WEBHOOK:            "queue:webhooks",
    TaskType.DELAYED_NOTIFY_TO_CUSTOMER: "queue:notifications",
    TaskType.DELAYED_SEND_REPORT:        "queue:reports",
    TaskType.DELAYED_REMINDER:           "queue:notifications",
    TaskType.DELAYED_BATCH_NOTIFICATION: "queue:notifications",
    TaskType.DELAYED_STEP_COMPLETION:    "queue:tasks",
    TaskType.RECURRING_SEND_REPORT:      "queue:reports",
    TaskType.RECURRING_REMINDER:         "queue:notifications",
    TaskType.RECURRING_PIN_TASK:         "queue:tasks",
    TaskType.RECORD_VIEW_START:          "queue:presence",
    TaskType.RECORD_VIEW_END:            "queue:presence",
    TaskType.PROCESS_STEP_TRANSITION:    "queue:analytics",
}

FALLBACK_POLL_SECONDS    = 30   # safety net for LISTEN/NOTIFY drop — not routing latency
BATCH_SIZE               = 50
STALE_IN_PROGRESS_MINUTES = 90  # must exceed max(HANDLER_TIMEOUT_SECONDS) / 60
STUCK_PENDING_MINUTES    = 5

_notify_event: asyncio.Event = asyncio.Event()


async def _listen_for_task_events() -> None:
    """Dedicated asyncpg LISTEN connection — reconnects automatically on drop."""
    while True:
        try:
            dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(dsn)

            async def _on_notify(conn, pid, channel, payload):
                _notify_event.set()

            await conn.add_listener("task_open", _on_notify)
            logger.info("task_router | LISTEN connection established")

            while not conn.is_closed():
                await asyncio.sleep(10)
                await conn.execute("SELECT 1")  # keepalive
        except Exception:
            logger.exception("task_router | LISTEN connection lost — reconnecting in 5s")
            await asyncio.sleep(5)


async def _sleep_monitor() -> None:
    while True:
        await asyncio.sleep(60)
        if not settings.sleep_mode_enabled:
            continue
        if ActivityTracker.idle_seconds() >= settings.idle_sleep_threshold_seconds:
            if not ActivityTracker.is_sleeping():
                ActivityTracker.enter_sleep()


async def run_task_router() -> None:
    logger.info("Task router started.")
    redis = get_redis_client(settings.redis_url)
    asyncio.create_task(_listen_for_task_events())
    asyncio.create_task(_sleep_monitor())

    while True:
        if ActivityTracker.is_sleeping():
            await asyncio.sleep(30)
            continue

        try:
            await asyncio.wait_for(_notify_event.wait(), timeout=FALLBACK_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
        _notify_event.clear()

        try:
            await _route_open_tasks(redis)
            await _requeue_retry_scheduled_tasks()
            await _cleanup_stale_tasks()
            await _recover_stuck_pending_tasks()
        except Exception:
            logger.exception("task_router: poll error")


async def _route_open_tasks(redis) -> None:
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask)
            .where(ExecutionTask.state == ExecutionTaskStateEnum.OPEN)
            .limit(BATCH_SIZE)
        )
        tasks = result.scalars().all()

        for task in tasks:
            queue_name = QUEUE_MAP.get(task.task_type)
            if not queue_name:
                logger.error(
                    "no queue mapped | task_type=%s task_id=%s",
                    task.task_type, task.client_id,
                )
                continue
            redis.rpush(queue_name, task.client_id)
            task.state = ExecutionTaskStateEnum.PENDING

        if tasks:
            await session.commit()
            depths = {name: redis.llen(name) for name in set(QUEUE_MAP.values())}
            logger.info("task_router | routed=%d queue_depths=%s", len(tasks), depths)


async def _requeue_retry_scheduled_tasks() -> None:
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(
                ExecutionTask.state == ExecutionTaskStateEnum.RETRY_SCHEDULED,
                ExecutionTask.next_retry_at <= now,
            ).limit(BATCH_SIZE)
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.state = ExecutionTaskStateEnum.OPEN
            task.next_retry_at = None

        if tasks:
            await session.commit()
            logger.info("task_router | requeued_retries=%d", len(tasks))


async def _cleanup_stale_tasks() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_IN_PROGRESS_MINUTES)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(
                ExecutionTask.state == ExecutionTaskStateEnum.IN_PROGRESS,
                ExecutionTask.locked_at < cutoff,
            ).limit(BATCH_SIZE)
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.state     = ExecutionTaskStateEnum.OPEN
            task.worker_id = None
            task.locked_at = None
            logger.warning(
                "stale_task_recovered | task_id=%s task_type=%s",
                task.client_id, task.task_type.value,
            )
        if tasks:
            await session.commit()


async def _recover_stuck_pending_tasks() -> None:
    """Reset PENDING tasks older than STUCK_PENDING_MINUTES whose Redis entry was lost."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_PENDING_MINUTES)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(
                ExecutionTask.state == ExecutionTaskStateEnum.PENDING,
                ExecutionTask.created_at < cutoff,
            ).limit(BATCH_SIZE)
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.state = ExecutionTaskStateEnum.OPEN
            logger.warning(
                "stuck_pending_recovered | task_id=%s task_type=%s",
                task.client_id, task.task_type.value,
            )
        if tasks:
            await session.commit()
