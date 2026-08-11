"""WORKER-1: Process step state transition events — update analytics stats tables."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.constants import TIME_BEARING_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.infra.execution.db import task_db_session
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_completion_reconcile_deltas,
    apply_reconcile_deltas,
    reconcile_user_day_completions,
    reconcile_user_day_time,
)
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.infra.events.worker_shift_realtime import emit_worker_shift_state

logger = logging.getLogger(__name__)


async def handle_process_step_transition(raw: dict, task_id: str) -> None:
    """WORKER-1: Dispatch step transition payload to all applicable aggregation rules."""
    payload = StepTransitionPayload(**raw)  # validates at entry; raises TypeError on mismatch

    async with task_db_session() as session:
        closing_record = await _fetch_closing_record(session, payload)
        if closing_record is None:
            logger.warning("record_not_found | closing_record_id=%s task_id=%s", payload.closing_record_id, task_id)
            return
        task_step = await _fetch_task_step(session, payload.step_id, payload.workspace_id)
        if task_step is None:
            logger.warning("step_not_found | step_id=%s task_id=%s", payload.step_id, task_id)

        # Fetch assigned worker display name snapshot for user-scoped stats.
        # If the worker record is deleted after the transition was recorded, the snapshot
        # falls back to "" — this is intentional; approximate analytics, not an error.
        credited_user_display_name = ""
        if payload.credited_user_id:
            credited_user = await _fetch_user(session, payload.credited_user_id)
            if credited_user:
                credited_user_display_name = credited_user.username

        now = datetime.now(timezone.utc)
        closing_state = TaskStepStateEnum(payload.closing_state)

        # TIME (concurrency-averaged). When a time-bearing record closed, recompute-and-SET
        # the credited worker's day from records (idempotent; batch time is averaged by real
        # concurrency). marked_wrong records are excluded inside the sweep.
        if payload.credited_user_id and closing_state in TIME_BEARING_STATES:
            work_date = datetime.fromisoformat(payload.entered_at).date()
            result = await reconcile_user_day_time(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, work_date, now,
            )
            await apply_reconcile_deltas(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, work_date, now, result,
            )
            await _recompute_step_time_totals(session, payload.workspace_id, payload.step_id, now)
            logger.info(
                "step_time_recomputed | workspace_id=%s user_id=%s step_id=%s work_date=%s closing_state=%s",
                payload.workspace_id, payload.credited_user_id, payload.step_id, work_date, closing_state.value,
            )

        shift_reconcile = None
        if payload.credited_user_id:
            shift_reconcile = await reconcile_worker_shift_state(
                session,
                payload.workspace_id,
                payload.credited_user_id,
                now,
            )

        # COMPLETION + ISSUES. Recompute-and-SET from records, exactly like the time path
        # above, so a worker retry cannot double-count: replaying the same transition
        # recomputes identical counts and the Σ deltas collapse to zero. (The queue is
        # at-least-once — the handler commits in its own session, and the task is only
        # marked COMPLETED in a later one, so re-execution is always possible.)
        # Applies regardless of recorded_time_marked_wrong: inaccurate time does not
        # suppress the fact that the step completed or that it carried issues.
        new_state = TaskStepStateEnum(payload.new_state)
        if new_state == TaskStepStateEnum.COMPLETED and payload.credited_user_id:
            completion_date = datetime.fromisoformat(payload.exited_at).date()
            completion_result = await reconcile_user_day_completions(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, completion_date, now,
            )
            await apply_completion_reconcile_deltas(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, completion_date, now, completion_result,
            )
            await _recompute_step_completion_totals(
                session, payload.workspace_id, payload.step_id, task_step
            )

        if task_step is not None:
            task_step.updated_at = datetime.now(timezone.utc)
        await session.commit()

        # A step transition is what moves a worker between WORKING, IN_PAUSE and IDLE, and
        # that derivation happens here rather than in the request that transitioned the
        # step — so this is the only place that can announce it. Gated on `changed`: most
        # transitions leave the shift state where it was (one of several batched steps
        # pausing, say) and a broadcast per step would be noise.
        if shift_reconcile is not None and shift_reconcile.changed:
            await emit_worker_shift_state(
                session,
                payload.workspace_id,
                payload.credited_user_id,
            )


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


async def _recompute_step_time_totals(
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


async def _recompute_step_completion_totals(
    session: AsyncSession,
    workspace_id: str,
    step_id: str,
    step: TaskStep | None,
) -> None:
    """SET the step's own completion/issue counters from records.

    Mirrors _recompute_step_time_totals: absolute assignment rather than increment, so a
    replayed transition cannot inflate them.
    """
    if step is None:
        return

    completed_count = await session.scalar(
        select(func.count())
        .select_from(StepStateRecord)
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.step_id == step_id,
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.is_deleted.is_(False),
        )
    )
    issues_count = await session.scalar(
        select(func.count())
        .select_from(ItemIssue)
        .where(
            ItemIssue.workspace_id == workspace_id,
            ItemIssue.step_id == step_id,
            ItemIssue.is_deleted.is_(False),
        )
    )

    step.total_completed_count = completed_count or 0
    # Resolved mirrors total: reaching COMPLETED is what resolves a step's issues.
    step.total_issues_count = issues_count or 0
    step.total_issues_resolved_count = issues_count or 0


async def _fetch_closing_record(session: AsyncSession, payload: StepTransitionPayload) -> StepStateRecord | None:
    """Fetch the StepStateRecord being closed."""
    result = await session.execute(
        select(StepStateRecord).where(
            StepStateRecord.client_id == payload.closing_record_id,
            StepStateRecord.workspace_id == payload.workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def _fetch_user(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by ID."""
    result = await session.execute(
        select(User).where(User.client_id == user_id)
    )
    return result.scalar_one_or_none()


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

