"""Recorded on-shift wall-clock totals per worker over a date range."""

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.analytics.linear_timeline import (
    UNSPECIFIED_REASON,
    LinearTimeline,
)
from beyo_manager.domain.analytics.serializers import serialize_linear_timeline
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats._roster import (
    count_completed_steps,
    load_worker_page,
    resolve_date_range,
)


_DURATION_STATES = {
    UserShiftStateEnum.WORKING,
    UserShiftStateEnum.IN_PAUSE,
    UserShiftStateEnum.IDLE,
}


def build_recorded_shift_timeline(
    records: list[UserShiftStateRecord],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> LinearTimeline:
    """Sum recorded duration states after clamping them to the requested window."""
    seconds = {
        UserShiftStateEnum.WORKING: 0.0,
        UserShiftStateEnum.IN_PAUSE: 0.0,
        UserShiftStateEnum.IDLE: 0.0,
    }
    pause_by_reason: dict[str, float] = defaultdict(float)
    for record in records:
        if record.state not in _DURATION_STATES:
            continue
        start = max(record.entered_at, window_start)
        end = min(record.exited_at or now, window_end)
        if end <= start:
            continue
        duration = (end - start).total_seconds()
        seconds[record.state] += duration
        if record.state is UserShiftStateEnum.IN_PAUSE:
            pause_by_reason[record.reason or UNSPECIFIED_REASON] += duration

    reason_seconds = {
        reason: int(round(duration))
        for reason, duration in sorted(pause_by_reason.items())
    }
    return LinearTimeline(
        working_seconds=int(round(seconds[UserShiftStateEnum.WORKING])),
        paused_seconds=sum(reason_seconds.values()),
        ended_shift_seconds=0,
        idle_seconds=int(round(seconds[UserShiftStateEnum.IDLE])),
        pause_by_reason=reason_seconds,
    )


async def load_recorded_shift_records(
    ctx: ServiceContext,
    user_ids: list[str],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[UserShiftStateRecord]]:
    if not user_ids:
        return {}
    rows = await ctx.session.execute(
        select(UserShiftStateRecord)
        .where(
            UserShiftStateRecord.workspace_id == ctx.workspace_id,
            UserShiftStateRecord.user_id.in_(user_ids),
            UserShiftStateRecord.entered_at < window_end,
            or_(
                UserShiftStateRecord.exited_at.is_(None),
                UserShiftStateRecord.exited_at > window_start,
                (
                    UserShiftStateRecord.state.in_(
                        (
                            UserShiftStateEnum.STARTED_SHIFT,
                            UserShiftStateEnum.ENDED_SHIFT,
                        )
                    )
                    & (UserShiftStateRecord.entered_at >= window_start)
                ),
            ),
        )
        .order_by(
            UserShiftStateRecord.user_id,
            UserShiftStateRecord.entered_at,
            UserShiftStateRecord.client_id,
        )
    )
    records_by_user: dict[str, list[UserShiftStateRecord]] = defaultdict(list)
    for record in rows.scalars():
        records_by_user[record.user_id].append(record)
    return records_by_user


async def list_workers_linear_timeline(ctx: ServiceContext) -> dict:
    date_from, date_to = resolve_date_range(ctx.query_params)
    workers, workers_pagination = await load_worker_page(
        ctx, roles=(RoleNameEnum.WORKER, RoleNameEnum.MANAGER)
    )
    worker_ids = [user.client_id for user in workers]

    now = datetime.now(timezone.utc)
    window_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    window_end = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    records_by_user = await load_recorded_shift_records(
        ctx,
        worker_ids,
        window_start,
        window_end,
    )
    completed_by_user = await count_completed_steps(
        ctx.session,
        ctx.workspace_id,
        worker_ids,
        window_start,
        window_end,
    )

    worker_results = []
    for user in workers:
        timeline = build_recorded_shift_timeline(
            records_by_user.get(user.client_id, []),
            window_start,
            window_end,
            now,
        )
        worker_results.append(
            {
                "user": serialize_user_worker_stat(user),
                "timeline": serialize_linear_timeline(
                    date_from,
                    date_to,
                    timeline,
                    completed_by_user.get(user.client_id, 0),
                ),
            }
        )

    return {
        "workers": worker_results,
        "workers_pagination": workers_pagination,
    }
