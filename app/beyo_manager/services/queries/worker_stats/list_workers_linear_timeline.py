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
from beyo_manager.domain.transitions.labels import resolve_transition_reason_label
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
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
            # `reason` (catalog id / legacy slug) still wins so existing rows bucket
            # exactly as before; `transition_reason` carries rows the system paused
            # itself, which hold no catalog id at all.
            #
            # This fallback is LOAD-BEARING, not defensive: every clock-out and every
            # task-switch auto-pause now produces a row that reaches it. Delete the
            # middle term and all of that time silently buckets as `unspecified`, with
            # no error anywhere — the roster just stops explaining the largest category
            # of pause it has.
            pause_by_reason[
                record.reason or record.transition_reason or UNSPECIFIED_REASON
            ] += duration

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


async def _load_pause_reasons_lookup(
    ctx: ServiceContext,
    reason_ids: set[str],
) -> dict[str, dict[str, str | None]]:
    """Resolve `pause_by_reason` bucket keys to display fields, matching the shape used by
    `get_worker_linear_timeline_breakdown._load_step_timeline_records`.

    Keys are of two kinds. A `transition_reason` resolves from the code-owned map with no
    database round trip at all (criterion 16 — that is the point of a code-owned
    vocabulary); everything else is a catalog id and is looked up exactly as before.
    """
    transition_labels = {
        reason_id: label
        for reason_id in reason_ids
        if (label := resolve_transition_reason_label(reason_id)) is not None
    }
    reason_ids = reason_ids - transition_labels.keys()
    if not reason_ids:
        return transition_labels
    rows = (
        await ctx.session.execute(
            select(
                PauseReason.client_id,
                PauseReason.name,
                PauseReason.image_url,
                PauseReason.pause_type,
            ).where(
                PauseReason.workspace_id == ctx.workspace_id,
                PauseReason.client_id.in_(reason_ids),
            )
        )
    ).all()
    return {
        **transition_labels,
        **{
            row.client_id: {
                "name": row.name,
                "image_url": row.image_url,
                "pause_type": row.pause_type.value if row.pause_type is not None else None,
            }
            for row in rows
        },
    }


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
    all_reason_ids: set[str] = set()
    for user in workers:
        timeline = build_recorded_shift_timeline(
            records_by_user.get(user.client_id, []),
            window_start,
            window_end,
            now,
        )
        all_reason_ids.update(
            reason_id
            for reason_id in timeline.pause_by_reason
            if reason_id != UNSPECIFIED_REASON
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

    pause_reasons = await _load_pause_reasons_lookup(ctx, all_reason_ids)

    return {
        "workers": worker_results,
        "workers_pagination": workers_pagination,
        "pause_reasons": pause_reasons,
    }
