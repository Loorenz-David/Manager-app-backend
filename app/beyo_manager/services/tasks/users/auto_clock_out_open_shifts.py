import logging
from datetime import datetime, time, timezone

from sqlalchemy import func, select

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import clock_out_shift_for_user


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
                await clock_out_shift_for_user(
                    session,
                    row.workspace_id,
                    row.user_id,
                    midnight,
                    changed_by_id=None,
                )
                clocked_out += 1

    logger.info(
        "worker_shift.midnight_safeguard_completed | task_id=%s clocked_out=%d boundary=%s",
        task_id,
        clocked_out,
        midnight.isoformat(),
    )
