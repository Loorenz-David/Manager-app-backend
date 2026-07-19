"""WORKER-1: Process step state transition events — update analytics stats tables."""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.constants import TIME_BEARING_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.infra.execution.db import task_db_session
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_reconcile_deltas,
    reconcile_user_day_time,
)

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

        # Issues rule: applies regardless of recorded_time_marked_wrong
        new_state = TaskStepStateEnum(payload.new_state)
        if new_state == TaskStepStateEnum.COMPLETED:
            await _apply_step_completed(session, payload, credited_user_display_name, task_step)
            await _apply_issues_at_completion(session, payload, credited_user_display_name, task_step)

        if task_step is not None:
            task_step.updated_at = datetime.now(timezone.utc)
        await session.commit()


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


async def _apply_issues_at_completion(
    session: AsyncSession,
    payload: StepTransitionPayload,
    worker_display_name: str,
    task_step: TaskStep | None,
) -> None:
    """Apply increments for issues when step completes."""
    issues_result = await session.execute(
        select(ItemIssue).where(
            ItemIssue.workspace_id == payload.workspace_id,
            ItemIssue.step_id == payload.step_id,
            ItemIssue.is_deleted.is_(False),
        )
    )
    issues = issues_result.scalars().all()
    if not issues:
        return

    total_count = len(issues)
    resolved_count = total_count

    work_date = datetime.fromisoformat(payload.entered_at).date()

    if payload.credited_user_id:
        await _increment_user_daily(
            session, payload, work_date, worker_display_name,
            issues_count=total_count, issues_resolved_count=resolved_count
        )
        await _increment_user_lifetime(
            session, payload, worker_display_name,
            issues_count=total_count, issues_resolved_count=resolved_count
        )
        await _increment_user_section_daily(
            session, payload, work_date, worker_display_name,
            issues_count=total_count, issues_resolved_count=resolved_count
        )

    await _increment_section_daily(
        session, payload, work_date,
        issues_count=total_count, issues_resolved_count=resolved_count
    )
    if task_step is not None:
        task_step.total_issues_count += total_count
        task_step.total_issues_resolved_count += resolved_count


async def _apply_step_completed(
    session: AsyncSession,
    payload: StepTransitionPayload,
    worker_display_name: str,
    task_step: TaskStep | None,
) -> None:
    """Increment completion counters on the UTC date the step completed."""
    work_date = datetime.fromisoformat(payload.exited_at).date()

    if payload.credited_user_id:
        await _increment_user_daily(
            session, payload, work_date, worker_display_name, completed_count=1
        )
        await _increment_user_lifetime(
            session, payload, worker_display_name, completed_count=1
        )
        await _increment_user_section_daily(
            session, payload, work_date, worker_display_name, completed_count=1
        )

    await _increment_section_daily(session, payload, work_date, completed_count=1)
    if task_step is not None:
        task_step.total_completed_count += 1
    logger.info(
        "step_completed_metrics_increment | workspace_id=%s step_id=%s credited_user_id=%s "
        "working_section_id=%s work_date=%s completed_count=1 task_step_found=%s",
        payload.workspace_id,
        payload.step_id,
        payload.credited_user_id,
        payload.working_section_id,
        work_date.isoformat(),
        task_step is not None,
    )


async def _get_or_create_user_daily(
    session: AsyncSession, workspace_id: str, user_id: str, work_date: date, display_name: str
) -> UserDailyWorkStats:
    """Get or create UserDailyWorkStats row."""
    result = await session.execute(
        select(UserDailyWorkStats).where(
            UserDailyWorkStats.workspace_id == workspace_id,
            UserDailyWorkStats.user_id == user_id,
            UserDailyWorkStats.work_date == work_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserDailyWorkStats(
            workspace_id=workspace_id,
            user_id=user_id,
            user_display_name_snapshot=display_name,
            work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_user_lifetime(
    session: AsyncSession, workspace_id: str, user_id: str, display_name: str
) -> UserLifetimeStats:
    """Get or create UserLifetimeStats row."""
    result = await session.execute(
        select(UserLifetimeStats).where(
            UserLifetimeStats.workspace_id == workspace_id,
            UserLifetimeStats.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserLifetimeStats(
            workspace_id=workspace_id,
            user_id=user_id,
            user_display_name_snapshot=display_name,
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_user_section_daily(
    session: AsyncSession, workspace_id: str, user_id: str, section_id: str, work_date: date,
    display_name: str, section_name: str | None = None,
) -> UserSectionDailyWorkStats:
    """Get or create UserSectionDailyWorkStats row."""
    result = await session.execute(
        select(UserSectionDailyWorkStats).where(
            UserSectionDailyWorkStats.workspace_id == workspace_id,
            UserSectionDailyWorkStats.user_id == user_id,
            UserSectionDailyWorkStats.working_section_id == section_id,
            UserSectionDailyWorkStats.work_date == work_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserSectionDailyWorkStats(
            workspace_id=workspace_id,
            user_id=user_id,
            working_section_id=section_id,
            section_name_snapshot=section_name or "",
            user_display_name_snapshot=display_name,
            work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_section_daily(
    session: AsyncSession, workspace_id: str, section_id: str, section_name: str | None, work_date: date
) -> WorkingSectionDailyWorkStats:
    """Get or create WorkingSectionDailyWorkStats row."""
    result = await session.execute(
        select(WorkingSectionDailyWorkStats).where(
            WorkingSectionDailyWorkStats.workspace_id == workspace_id,
            WorkingSectionDailyWorkStats.working_section_id == section_id,
            WorkingSectionDailyWorkStats.work_date == work_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = WorkingSectionDailyWorkStats(
            workspace_id=workspace_id,
            working_section_id=section_id,
            section_name_snapshot=section_name or "",
            work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row


async def _increment_user_daily(
    session: AsyncSession,
    payload: StepTransitionPayload,
    work_date: date,
    worker_display_name: str,
    *,
    working_seconds: int = 0,
    working_count: int = 0,
    pause_seconds: int = 0,
    pause_count: int = 0,
    ended_shift_seconds: int = 0,
    ended_shift_count: int = 0,
    issues_count: int = 0,
    issues_resolved_count: int = 0,
    completed_count: int = 0,
    cost_minor: int = 0,
) -> None:
    """Increment UserDailyWorkStats row."""
    row = await _get_or_create_user_daily(
        session, payload.workspace_id, payload.credited_user_id, work_date, worker_display_name
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
    row.total_completed_count += completed_count
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)


async def _increment_user_lifetime(
    session: AsyncSession,
    payload: StepTransitionPayload,
    worker_display_name: str,
    *,
    working_seconds: int = 0,
    working_count: int = 0,
    pause_seconds: int = 0,
    pause_count: int = 0,
    ended_shift_seconds: int = 0,
    ended_shift_count: int = 0,
    issues_count: int = 0,
    issues_resolved_count: int = 0,
    completed_count: int = 0,
    cost_minor: int = 0,
) -> None:
    """Increment UserLifetimeStats row."""
    row = await _get_or_create_user_lifetime(
        session, payload.workspace_id, payload.credited_user_id, worker_display_name
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
    row.total_completed_count += completed_count
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)


async def _increment_user_section_daily(
    session: AsyncSession,
    payload: StepTransitionPayload,
    work_date: date,
    worker_display_name: str,
    *,
    working_seconds: int = 0,
    working_count: int = 0,
    pause_seconds: int = 0,
    pause_count: int = 0,
    ended_shift_seconds: int = 0,
    ended_shift_count: int = 0,
    issues_count: int = 0,
    issues_resolved_count: int = 0,
    completed_count: int = 0,
    cost_minor: int = 0,
) -> None:
    """Increment UserSectionDailyWorkStats row."""
    row = await _get_or_create_user_section_daily(
        session, payload.workspace_id, payload.credited_user_id, payload.working_section_id,
        work_date, worker_display_name, payload.working_section_name_snapshot,
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
    row.total_completed_count += completed_count
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)


async def _increment_section_daily(
    session: AsyncSession,
    payload: StepTransitionPayload,
    work_date: date,
    *,
    working_seconds: int = 0,
    working_count: int = 0,
    pause_seconds: int = 0,
    pause_count: int = 0,
    ended_shift_seconds: int = 0,
    ended_shift_count: int = 0,
    issues_count: int = 0,
    issues_resolved_count: int = 0,
    completed_count: int = 0,
    cost_minor: int = 0,
) -> None:
    """Increment WorkingSectionDailyWorkStats row."""
    row = await _get_or_create_section_daily(
        session, payload.workspace_id, payload.working_section_id,
        payload.working_section_name_snapshot, work_date
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
    row.total_completed_count += completed_count
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)
