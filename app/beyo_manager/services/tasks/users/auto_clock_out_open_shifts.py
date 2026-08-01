import logging
from datetime import datetime, time, timezone

from sqlalchemy import func, select

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import clock_out_shift_for_user
from beyo_manager.services.infra.events.worker_shift_realtime import (
    emit_steps_paused,
    emit_worker_shift_state,
)


logger = logging.getLogger(__name__)


async def handle_auto_clock_out_open_shifts(raw: dict, task_id: str) -> None:
    del raw
    now = datetime.now(timezone.utc)
    midnight = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
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
                        latest_started.c.started_at < midnight,
                    )
                    .with_for_update(of=UserShiftStateRecord)
                )
            ).all()
            for row in rows:
                paused_step_ids = await clock_out_shift_for_user(
                    session,
                    row.workspace_id,
                    row.user_id,
                    midnight,
                    changed_by_id=None,
                )
                closed_shifts.append((row.workspace_id, row.user_id, paused_step_ids))
                clocked_out += 1

        for workspace_id, user_id, paused_step_ids in closed_shifts:
            await emit_worker_shift_state(session, workspace_id, user_id)
            await emit_steps_paused(workspace_id, paused_step_ids)

    logger.info(
        "worker_shift.midnight_safeguard_completed | task_id=%s clocked_out=%d boundary=%s",
        task_id,
        clocked_out,
        midnight.isoformat(),
    )
