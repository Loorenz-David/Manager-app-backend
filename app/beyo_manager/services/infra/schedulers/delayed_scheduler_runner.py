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
from beyo_manager.workers.heartbeat import (
    PROGRESS_MAX_IDLE_SECONDS,
    error_backoff_seconds,
    progress_enabled,
    touch_progress,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS       = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep even when no jobs are due
WAKE_CHECK_INTERVAL_SECONDS = 2     # re-check is_sleeping() at this cadence
ERROR_RETRY_MINUTES         = 15

DELAYED_TYPE_TO_TASK_TYPE: dict[DelayedSchedulerTypeEnum, TaskType] = {
    DelayedSchedulerTypeEnum.NOTIFY_TO_CUSTOMER: TaskType.DELAYED_NOTIFY_TO_CUSTOMER,
    DelayedSchedulerTypeEnum.SEND_REPORT:        TaskType.DELAYED_SEND_REPORT,
    DelayedSchedulerTypeEnum.REMINDER:           TaskType.DELAYED_REMINDER,
    DelayedSchedulerTypeEnum.BATCH_NOTIFICATION: TaskType.DELAYED_BATCH_NOTIFICATION,
    DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION: TaskType.DELAYED_STEP_COMPLETION,
    DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION: (
        TaskType.STOCK_REPORT_VERSION_ACTIVATION
    ),
}


async def run_delayed_scheduler_runner() -> None:
    logger.info("Delayed scheduler runner started.")
    next_due_at: datetime | None = None
    consecutive_errors = 0

    while True:
        # Everything that can fail is inside the try: a transient Redis or database
        # error is logged and retried after a backoff instead of ending the process.
        # Progress is touched only after the iteration's database work returned.
        try:
            if ActivityTracker.is_sleeping():
                await _sleep_while_sleeping(next_due_at)
                if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                    if progress_enabled():
                        # Not due yet, but readiness needs a database poll at least
                        # every PROGRESS_MAX_IDLE_SECONDS.
                        next_due_at = await _get_next_scheduled_for()
                        touch_progress()
                    continue
                ActivityTracker.touch()  # due time arrived — wake the system before firing

            await _fire_due_schedulers()
            await _retry_errored_schedulers()
            next_due_at = await _get_next_scheduled_for()
        except Exception:
            consecutive_errors += 1
            logger.exception(
                "delayed_scheduler_runner: poll error | consecutive_errors=%d", consecutive_errors
            )
            await asyncio.sleep(error_backoff_seconds(consecutive_errors))
            continue
        consecutive_errors = 0
        touch_progress()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _sleep_while_sleeping(next_due_at: datetime | None) -> None:
    """While in-app sleep lasts: wait until the next due time, capped (and capped at
    PROGRESS_MAX_IDLE_SECONDS when the progress file is on)."""
    cap = SCHEDULER_SLEEP_CAP_SECONDS
    if progress_enabled():
        cap = min(cap, PROGRESS_MAX_IDLE_SECONDS)
    if next_due_at is not None:
        sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
        sleep_for = min(sleep_for, cap)
    else:
        sleep_for = cap
    deadline = datetime.now(timezone.utc) + timedelta(seconds=sleep_for)
    while ActivityTracker.is_sleeping():
        remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            break
        await asyncio.sleep(min(WAKE_CHECK_INTERVAL_SECONDS, remaining))


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
