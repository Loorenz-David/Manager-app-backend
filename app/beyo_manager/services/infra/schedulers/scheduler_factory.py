from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    RecurringSchedulerIntervalValueEnum,
    RecurringSchedulerTypeEnum,
    SchedulerOriginSourceEnum,
    SchedulerStateEnum,
)
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.schedulers.recurring_scheduler import RecurringScheduler


async def create_delayed_scheduler(
    session: AsyncSession,
    scheduler_type: DelayedSchedulerTypeEnum,
    scheduled_for: datetime,
    payload: dict,
    origin_source: SchedulerOriginSourceEnum = SchedulerOriginSourceEnum.COMMAND,
    origin_id: str | None = None,
    event_client_id: str | None = None,
) -> DelayedScheduler:
    """Single entry point for creating delayed scheduler rows."""
    scheduler = DelayedScheduler(
        type=scheduler_type,
        state=SchedulerStateEnum.ACTIVE,
        scheduled_for=scheduled_for,
        payload_snapshot=payload,
        origin_source=origin_source,
        origin_id=origin_id,
        event_client_id=event_client_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(scheduler)
    return scheduler


async def create_recurring_scheduler(
    session: AsyncSession,
    scheduler_type: RecurringSchedulerTypeEnum,
    interval: int,
    interval_value: RecurringSchedulerIntervalValueEnum,
    payload: dict,
    origin_source: SchedulerOriginSourceEnum = SchedulerOriginSourceEnum.COMMAND,
    origin_id: str | None = None,
    event_client_id: str | None = None,
) -> RecurringScheduler:
    """Single entry point for creating recurring scheduler rows."""
    scheduler = RecurringScheduler(
        type=scheduler_type,
        state=SchedulerStateEnum.ACTIVE,
        interval=interval,
        interval_value=interval_value,
        payload_snapshot=payload,
        origin_source=origin_source,
        origin_id=origin_id,
        event_client_id=event_client_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(scheduler)
    return scheduler
