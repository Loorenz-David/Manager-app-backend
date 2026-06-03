import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum, TaskType
from beyo_manager.domain.schedulers.enums import DelayedSchedulerTypeEnum, SchedulerStateEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.services.infra.execution.task_factory import create_execution_task
from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS      = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep even when no jobs are due
ERROR_RETRY_MINUTES         = 15

DELAYED_TYPE_TO_TASK_TYPE: dict[DelayedSchedulerTypeEnum, TaskType] = {
    DelayedSchedulerTypeEnum.NOTIFY_TO_CUSTOMER: TaskType.DELAYED_NOTIFY_TO_CUSTOMER,
    DelayedSchedulerTypeEnum.SEND_REPORT:        TaskType.DELAYED_SEND_REPORT,
    DelayedSchedulerTypeEnum.REMINDER:           TaskType.DELAYED_REMINDER,
    DelayedSchedulerTypeEnum.BATCH_NOTIFICATION: TaskType.DELAYED_BATCH_NOTIFICATION,
    DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION: TaskType.DELAYED_STEP_COMPLETION,
}


async def run_delayed_scheduler_runner() -> None:
    logger.info("Delayed scheduler runner started.")
    next_due_at: datetime | None = None

    while True:
        if ActivityTracker.is_sleeping():
            if next_due_at is not None:
                sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
                sleep_for = min(sleep_for, SCHEDULER_SLEEP_CAP_SECONDS)
            else:
                sleep_for = SCHEDULER_SLEEP_CAP_SECONDS
            await asyncio.sleep(sleep_for)
            if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                continue
            ActivityTracker.touch()  # due time arrived — wake the system before firing

        try:
            await _fire_due_schedulers()
            await _retry_errored_schedulers()
        except Exception:
            logger.exception("delayed_scheduler_runner: poll error")

        next_due_at = await _get_next_scheduled_for()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _fire_due_schedulers() -> None:
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(DelayedScheduler).where(
                DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
                DelayedScheduler.scheduled_for <= now,
            ).limit(50)
        )
        due = result.scalars().all()
        fired = errors = 0

        for scheduler in due:
            try:
                await create_execution_task(
                    session=session,
                    task_type=DELAYED_TYPE_TO_TASK_TYPE[scheduler.type],
                    payload=scheduler.payload_snapshot,
                    origin_source=EventTaskOriginSourceEnum.DELAYED_SCHEDULER,
                    origin_id=scheduler.client_id,
                    scheduled_at=scheduler.scheduled_for,
                    event_client_id=scheduler.event_client_id,
                )
                scheduler.state    = SchedulerStateEnum.FIRED
                scheduler.fired_at = now
                ActivityTracker.touch()
                fired += 1
            except Exception as exc:
                logger.exception(
                    "delayed_scheduler | fire_failed | id=%s type=%s",
                    scheduler.client_id, scheduler.type,
                )
                scheduler.state      = SchedulerStateEnum.ERROR
                scheduler.last_error = str(exc)[:1024]
                scheduler.updated_at = now
                errors += 1

        if fired or errors:
            await session.commit()
            logger.info("delayed_scheduler_runner | fired=%d errors=%d", fired, errors)


async def _retry_errored_schedulers() -> None:
    """Reset ERROR-state schedulers after a cooldown so transient failures self-recover."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=ERROR_RETRY_MINUTES)
    async for session in get_db_session():
        result = await session.execute(
            select(DelayedScheduler).where(
                DelayedScheduler.state == SchedulerStateEnum.ERROR,
                DelayedScheduler.scheduled_for > now,   # target time not yet past
                DelayedScheduler.updated_at < cutoff,
            ).limit(20)
        )
        errored = result.scalars().all()
        for scheduler in errored:
            scheduler.state      = SchedulerStateEnum.ACTIVE
            scheduler.last_error = None
            scheduler.updated_at = now
            logger.warning("delayed_scheduler | error_retry | id=%s", scheduler.client_id)
        if errored:
            await session.commit()


async def _get_next_scheduled_for() -> datetime | None:
    """Return the earliest future scheduled_for across all ACTIVE delayed schedulers."""
    async for session in get_db_session():
        result = await session.execute(
            select(func.min(DelayedScheduler.scheduled_for)).where(
                DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
                DelayedScheduler.scheduled_for > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()
