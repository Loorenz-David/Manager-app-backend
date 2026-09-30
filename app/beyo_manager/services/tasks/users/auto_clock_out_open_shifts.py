import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.work_day import work_day_start
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import (
    close_stale_open_shift,
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.infra.events.worker_shift_realtime import (
    emit_steps_paused,
    emit_worker_shift_state,
)


logger = logging.getLogger(__name__)


async def handle_auto_clock_out_open_shifts(raw: dict, task_id: str) -> None:
    """Close every open shift that has outlived its work day, each at its OWN boundary.

    A shift started at ``t`` ends at ``work_day_end(t)`` (the next UTC midnight) — not at
    "today's" midnight and not at the time this sweep happens to run. So a sweep that runs
    late, after production slept, or after several missed days produces exactly the shifts
    an on-time sweep would have: one run closes every stale shift at its own boundary.

    Activity the worker recorded after that boundary is not folded into the old shift
    (`close_stale_open_shift`); the reconcile then opens the new day's shift from any
    still-open working step. Idempotent: a closed shift is no longer open, and a shift the
    reconcile opens is inside its own work day unless it is itself stale, in which case
    the reconcile closes it at its boundary too.
    """
    del raw
    now = datetime.now(timezone.utc)
    # `work_day_end(started_at) <= now`  <=>  `started_at < work_day_start(now)`.
    today_start = work_day_start(now)
    latest_started = (
        select(
            UserShiftStateRecord.workspace_id.label("workspace_id"),
            UserShiftStateRecord.user_id.label("user_id"),
            func.max(UserShiftStateRecord.entered_at).label("started_at"),
        )
        .where(UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT)
        .group_by(UserShiftStateRecord.workspace_id, UserShiftStateRecord.user_id)
        .subquery()
    )

    clocked_out = 0
    # (workspace_id, user_id, paused step ids) per closed shift, broadcast once the whole
    # sweep has committed. Collecting rather than emitting inline keeps the transaction
    # free of network calls and guarantees no worker is told their shift ended by a sweep
    # that then rolled back.
    closed_shifts: list[tuple[str, str, list[str]]] = []
    async for session in get_db_session():
        async with session.begin():
            rows = (
                await session.execute(
                    select(
                        UserShiftStateRecord.workspace_id,
                        UserShiftStateRecord.user_id,
                    )
                    .join(
                        latest_started,
                        (latest_started.c.workspace_id == UserShiftStateRecord.workspace_id)
                        & (latest_started.c.user_id == UserShiftStateRecord.user_id),
                    )
                    .where(
                        UserShiftStateRecord.exited_at.is_(None),
                        latest_started.c.started_at < today_start,
                    )
                    .with_for_update(of=UserShiftStateRecord)
                )
            ).all()
            for row in rows:
                current = await load_open_worker_shift_for_update(
                    session, row.workspace_id, row.user_id
                )
                closure = await close_stale_open_shift(
                    session, row.workspace_id, row.user_id, current, now
                )
                if closure is None:
                    continue
                # Work recorded after the boundary belongs to the new day: the reconcile
                # opens that day's shift from a still-open working step (and closes it at
                # its own boundary as well if that step is from an earlier day).
                reconcile = await reconcile_worker_shift_state(
                    session, row.workspace_id, row.user_id, now
                )
                closed_shifts.append(
                    (
                        row.workspace_id,
                        row.user_id,
                        [*closure.paused_step_ids, *reconcile.paused_step_ids],
                    )
                )
                clocked_out += 1

        for workspace_id, user_id, paused_step_ids in closed_shifts:
            await emit_worker_shift_state(session, workspace_id, user_id)
            await emit_steps_paused(workspace_id, paused_step_ids)

    logger.info(
        "worker_shift.midnight_safeguard_completed | task_id=%s clocked_out=%d today_start=%s",
        task_id,
        clocked_out,
        today_start.isoformat(),
    )
