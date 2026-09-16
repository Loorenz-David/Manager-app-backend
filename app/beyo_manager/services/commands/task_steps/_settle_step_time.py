"""Settle a step's own time totals from its records — shared by the write path and the worker.

`settle_step_time_totals` is the single implementation of the step-grain recompute. It was
extracted from `services/tasks/analytics/process_step_transition.py`, which still calls it
(re-exported there under its historical name `_recompute_step_time_totals`).

It is recompute-and-SET, never increment: it reads every time-bearing record of the step and
assigns the totals absolutely. Running it in the transition transaction and again in the
analytics worker therefore converges on the same values, and a replayed worker task cannot
inflate them.

WHY THE WRITE PATH CALLS IT
    `load_live_worked_seconds` sums `step.total_working_seconds` plus the share of any record
    still open. Between the transaction that sets `exited_at` and the analytics worker's
    recompute, a just-closed run belongs to neither source, so the four item-economics
    surfaces briefly served a total missing that run (measured at 100–300 ms; see
    docs/handoff/from_frontend/HANDOFF_TO_BACKEND_step_time_settlement_window_20260916.md).
    Settling in the same transaction closes that window: no reader can observe a closed
    time-bearing record without also observing its contribution.

THE GATE
    `settle_closed_step_time` reproduces the analytics worker's own condition exactly
    (`payload.credited_user_id and closing_state in TIME_BEARING_STATES`). The two must stay
    identical — if the write path settled under a condition the worker does not share, the
    worker's later recompute would disagree with what the request already published.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TIME_BEARING_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions

_STEP_TIME_FIELDS = {
    "working": ("total_working_seconds", "total_working_count"),
    "paused": ("total_pause_seconds", "total_pause_count"),
    "ended_shift": ("total_ended_shift_seconds", "total_ended_shift_count"),
}

_STEP_INACCURATE_TIME_FIELDS = {
    "working": "inaccurate_working_seconds",
    "paused": "inaccurate_pause_seconds",
    "ended_shift": "inaccurate_ended_shift_seconds",
}


async def _fetch_task_step(session: AsyncSession, step_id: str, workspace_id: str) -> TaskStep | None:
    """Fetch a non-deleted TaskStep by ID."""
    result = await session.execute(
        select(TaskStep).where(
            TaskStep.client_id == step_id,
            TaskStep.workspace_id == workspace_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _rate(session: AsyncSession, user_id: str, workspace_id: str) -> Decimal | None:
    profile = (
        await session.execute(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == user_id,
                UserWorkProfile.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    return profile.salary_per_hour_before_tax if profile else None


async def settle_step_time_totals(
    session: AsyncSession, workspace_id: str, step_id: str, now: datetime
) -> None:
    """Recompute a step's TaskStep.total_*_seconds/counts from its records (averaged).

    Each record's averaged share is computed in its credited user's concurrency context;
    settled (closed) records only, matching the daily totals.
    """
    step = await _fetch_task_step(session, step_id, workspace_id)
    if step is None:
        return

    records = (
        await session.execute(
            select(
                StepStateRecord.credited_user_id,
                StepStateRecord.created_by_id,
                StepStateRecord.entered_at,
                StepStateRecord.exited_at,
            ).where(
                StepStateRecord.workspace_id == workspace_id,
                StepStateRecord.step_id == step_id,
                StepStateRecord.is_deleted.is_(False),
                StepStateRecord.state.in_(TIME_BEARING_STATES),
            )
        )
    ).all()

    windows: dict[str, list[datetime | None]] = defaultdict(lambda: [None, None])
    for r in records:
        uid = r.credited_user_id or r.created_by_id
        if uid is None:
            continue
        end = r.exited_at or now
        span = windows[uid]
        span[0] = r.entered_at if span[0] is None else min(span[0], r.entered_at)
        span[1] = end if span[1] is None else max(span[1], end)

    totals: dict[str, list[float | int]] = {
        "working": [0.0, 0],
        "paused": [0.0, 0],
        "ended_shift": [0.0, 0],
    }
    inaccurate_totals = {"working": 0.0, "paused": 0.0, "ended_shift": 0.0}
    costed_seconds_by_user: dict[str, float] = defaultdict(float)  # working + pause, for cost
    buffer = timedelta(days=1)
    for uid, (start, end) in windows.items():
        contributions = await compute_record_contributions(
            session, workspace_id, uid, start - buffer, end + buffer, now
        )
        for c in contributions:
            if c.step_id != step_id or c.is_open or c.state not in totals:
                continue
            inaccurate_totals[c.state] += c.wasted_seconds
            if not c.marked_wrong:
                totals[c.state][0] += c.seconds
                totals[c.state][1] += 1
            if c.state in ("working", "paused"):
                costed_seconds_by_user[uid] += c.seconds

    for state, (sec_field, cnt_field) in _STEP_TIME_FIELDS.items():
        setattr(step, sec_field, int(round(totals[state][0])))
        setattr(step, cnt_field, totals[state][1])
        setattr(step, _STEP_INACCURATE_TIME_FIELDS[state], int(round(inaccurate_totals[state])))

    cost_minor = 0
    for uid, seconds in costed_seconds_by_user.items():
        rate = await _rate(session, uid, workspace_id)
        if rate is not None:
            cost_minor += int(
                ((Decimal(int(round(seconds))) / Decimal(3600)) * rate * Decimal(100)).to_integral_value()
            )
    step.total_cost_minor = cost_minor
    step.updated_at = now


async def settle_closed_step_time(
    session: AsyncSession,
    *,
    workspace_id: str,
    step_id: str,
    closing_state: TaskStepStateEnum,
    credited_user_id: str | None,
    now: datetime,
) -> None:
    """Settle `step_id` in the transaction that just closed one of its time-bearing records.

    The gate mirrors `handle_process_step_transition`'s exactly, so the value this publishes
    is the value the worker will recompute. A PENDING or terminal closing state carries no
    time, so those transitions pay nothing.

    The caller's pending mutations are flushed first: the sweep reads the records back out of
    the database, so `exited_at` and any inaccurate-time flag must already be visible to it.

    Raises whatever the sweep raises. That is deliberate — the settlement is part of the
    transition's transaction, so a failure rolls the transition back rather than committing a
    state that reintroduces the unsettled window.
    """
    if not credited_user_id or closing_state not in TIME_BEARING_STATES:
        return
    await session.flush()
    await settle_step_time_totals(session, workspace_id, step_id, now)


__all__ = ["settle_step_time_totals", "settle_closed_step_time"]
