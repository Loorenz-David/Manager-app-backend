"""The delayed-scheduler row behind a draft's `scheduled_activation_at` (draft
versions, 2026-09-28; plan §5.1, §5.2). This is the delayed scheduler's first live
producer.

At most one `ACTIVE` row per draft, found by `(event_client_id = version_id, type,
state = ACTIVE)`. The column is the truth; the row is how it fires:

| change                  | scheduler row                                        |
|-------------------------|------------------------------------------------------|
| date set or moved       | the `ACTIVE` row `CANCELED`, a new one created        |
| missing flag changed    | nothing — the flag is read from the column at fire   |
| date cleared            | the `ACTIVE` row `CANCELED`                           |
| activated (by hand)     | the `ACTIVE` row `CANCELED`, the column cleared       |
| deleted                 | the `ACTIVE` row `CANCELED`                           |
| fired                   | the runner sets `FIRED`; the activation clears the column |

The payload carries `scheduled_for` so a stale fire — the runner reads `ACTIVE` rows
without a lock and can mark a just-cancelled row `FIRED` — is recognised by the
activation and skipped (P-5). Every caller holds the stock-report advisory lock and
the version row; the scheduler rows are locked last (P-19, Q-18).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import timezone

from sqlalchemy import select, update

from beyo_manager.domain.execution.payloads.stock_report_version_activation import (
    StockReportVersionActivationPayload,
)
from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    SchedulerStateEnum,
)
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.services.infra.schedulers.scheduler_factory import (
    create_delayed_scheduler,
)

ACTIVATION_SCHEDULER_TYPE = DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION


def _active_rows(version_ids):
    return (
        select(DelayedScheduler)
        .where(
            DelayedScheduler.event_client_id.in_(sorted(version_ids)),
            DelayedScheduler.type == ACTIVATION_SCHEDULER_TYPE,
            DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
        )
        .order_by(DelayedScheduler.client_id)
    )


async def lock_activation_schedulers(session, version_ids):
    """The `ACTIVE` activation rows of these versions, `FOR UPDATE`, sorted."""
    if not version_ids:
        return []
    return (
        (
            await session.execute(
                _active_rows(version_ids)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )


async def read_activation_schedulers(session, version_ids):
    """The same rows, unlocked — the consistency check's read."""
    if not version_ids:
        return []
    return (await session.execute(_active_rows(version_ids))).scalars().all()


async def cancel_activation_schedulers(session, version_id, *, now, scheduled_for=None):
    """`CANCELED` every `ACTIVE` activation row of the version (or only the one due
    at `scheduled_for`); returns how many."""
    statement = update(DelayedScheduler).where(
        DelayedScheduler.event_client_id == version_id,
        DelayedScheduler.type == ACTIVATION_SCHEDULER_TYPE,
        DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
    )
    if scheduled_for is not None:
        statement = statement.where(DelayedScheduler.scheduled_for == scheduled_for)
    result = await session.execute(
        statement.values(
            state=SchedulerStateEnum.CANCELED, updated_at=now
        ).execution_options(synchronize_session=False)
    )
    return result.rowcount


async def create_activation_scheduler(session, version, *, scheduled_by_user_id):
    """One `ACTIVE` row firing the draft at its stored `scheduled_activation_at`,
    stamped with the user who set the schedule (§11: a scheduled activation is
    that user's act)."""
    scheduled_for = version.scheduled_activation_at.astimezone(timezone.utc)
    payload = StockReportVersionActivationPayload(
        workspace_id=version.workspace_id,
        version_id=version.client_id,
        scheduled_by_user_id=scheduled_by_user_id or None,
        scheduled_for=scheduled_for.isoformat(),
    )
    scheduler = await create_delayed_scheduler(
        session,
        ACTIVATION_SCHEDULER_TYPE,
        scheduled_for,
        asdict(payload),
        origin_id=version.client_id,
        event_client_id=version.client_id,
    )
    await session.flush()
    return scheduler


async def reschedule_activation(session, version, *, scheduled_by_user_id, now):
    """Bring the scheduler row in step with the column just written: cancel the
    `ACTIVE` row, then create one for the new date if there is a date."""
    await cancel_activation_schedulers(session, version.client_id, now=now)
    if version.scheduled_activation_at is not None:
        await create_activation_scheduler(
            session, version, scheduled_by_user_id=scheduled_by_user_id
        )
