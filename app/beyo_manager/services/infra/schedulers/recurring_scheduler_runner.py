import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum, TaskType
from beyo_manager.domain.schedulers.enums import (
    RecurringSchedulerTypeEnum,
    SchedulerStateEnum,
)
# Re-exported: the grid is the scheduling rule, and callers (an eligibility CLI, tests)
# import it from here or from the domain module without starting the runner.
from beyo_manager.domain.schedulers.recurring_grid import (  # noqa: F401
    INTERVAL_UNIT_TO_SECONDS,
    grid_point,
    recurring_grid_point,
    recurring_is_due,
    recurring_next_run_at,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.schedulers.recurring_scheduler import RecurringScheduler
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
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep between checks when sleeping
WAKE_CHECK_INTERVAL_SECONDS = 2     # re-check is_sleeping() at this cadence
BATCH_SIZE                  = 200   # prevents unbounded memory load

RECURRING_TYPE_TO_TASK_TYPE: dict[RecurringSchedulerTypeEnum, TaskType] = {
    RecurringSchedulerTypeEnum.SEND_REPORT: TaskType.RECURRING_SEND_REPORT,
    RecurringSchedulerTypeEnum.REMINDER:    TaskType.RECURRING_REMINDER,
    RecurringSchedulerTypeEnum.PIN_TASK:    TaskType.RECURRING_PIN_TASK,
    RecurringSchedulerTypeEnum.AUTO_CLOCK_OUT_OPEN_SHIFTS: TaskType.AUTO_CLOCK_OUT_OPEN_SHIFTS,
}


async def run_recurring_scheduler_runner() -> None:
    logger.info("Recurring scheduler runner started.")
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
                        next_due_at = await _get_next_run_at()
                        touch_progress()
                    continue
                ActivityTracker.touch()  # due time arrived — wake the system before firing

            await _fire_due_recurring_schedulers()
            next_due_at = await _get_next_run_at()
        except Exception:
            consecutive_errors += 1
            logger.exception(
                "recurring_scheduler_runner: poll error | consecutive_errors=%d", consecutive_errors
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


async def _fire_due_recurring_schedulers() -> None:
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(RecurringScheduler)
            .where(RecurringScheduler.state == SchedulerStateEnum.ACTIVE)
            .limit(BATCH_SIZE)
        )
        candidates = result.scalars().all()
        fired = errors = 0

        for scheduler in candidates:
            try:
                due = _is_due(scheduler, now)
            except ValueError as exc:
                # A non-positive interval has no grid. Record it on the row and skip it,
                # rather than let one bad row stop every other scheduler from firing.
                message = str(exc)[:1024]
                if scheduler.last_error != message:  # record once, not every poll
                    scheduler.last_error = message
                    errors += 1
                continue
            if not due:
                continue
            try:
                await create_execution_task(
                    session=session,
                    task_type=RECURRING_TYPE_TO_TASK_TYPE[scheduler.type],
                    payload=scheduler.payload_snapshot,
                    origin_source=EventTaskOriginSourceEnum.RECURRING_SCHEDULER,
                    origin_id=scheduler.client_id,
                    scheduled_at=now,
                    event_client_id=scheduler.event_client_id,
                )
                # The grid slot this fire serves, not the wall time: a late fire must not
                # re-anchor the schedule, and missed slots collapse into this one fire.
                scheduler.last_interval = recurring_grid_point(scheduler, now)
                ActivityTracker.touch()
                fired += 1
            except Exception as exc:
                logger.exception(
                    "recurring_scheduler | fire_failed | id=%s type=%s",
                    scheduler.client_id, scheduler.type,
                )
                scheduler.last_error = str(exc)[:1024]
                errors += 1

        if fired or errors:   # commit both successes and error updates
            await session.commit()
            logger.info("recurring_scheduler_runner | fired=%d errors=%d", fired, errors)


async def _get_next_run_at() -> datetime | None:
    """Compute earliest next fire time across all ACTIVE recurring schedulers."""
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(RecurringScheduler)
            .where(RecurringScheduler.state == SchedulerStateEnum.ACTIVE)
            .limit(BATCH_SIZE)
        )
        schedulers = result.scalars().all()
        next_times = []
        for s in schedulers:
            try:
                next_times.append(recurring_next_run_at(s, now))
            except ValueError:
                continue
        return min(next_times) if next_times else None


def _is_due(scheduler: RecurringScheduler, now: datetime) -> bool:
    return recurring_is_due(scheduler, now)
