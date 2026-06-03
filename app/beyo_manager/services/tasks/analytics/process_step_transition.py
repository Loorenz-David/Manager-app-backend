"""WORKER-1: Process step state transition events — update analytics stats tables."""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.infra.execution.db import task_db_session

logger = logging.getLogger(__name__)


async def handle_process_step_transition(raw: dict, task_id: str) -> None:
    """WORKER-1: Dispatch step transition payload to all applicable aggregation rules."""
    payload = StepTransitionPayload(**raw)  # validates at entry; raises TypeError on mismatch

    async with task_db_session() as session:
        closing_record = await _fetch_closing_record(session, payload)
        if closing_record is None:
            logger.warning("record_not_found | closing_record_id=%s task_id=%s", payload.closing_record_id, task_id)
            return

        # Fetch assigned worker display name snapshot for user-scoped stats.
        # If the worker record is deleted after the transition was recorded, the snapshot
        # falls back to "" — this is intentional; approximate analytics, not an error.
        credited_user_display_name = ""
        if payload.credited_user_id:
            credited_user = await _fetch_user(session, payload.credited_user_id)
            if credited_user:
                credited_user_display_name = credited_user.username

        # Exclusion rule: skip all time/count increments for inaccurate records
        if not closing_record.recorded_time_marked_wrong:
            interval_seconds = _compute_interval_seconds(payload)
            closing_state = TaskStepStateEnum(payload.closing_state)

            if closing_state == TaskStepStateEnum.WORKING:
                await _apply_working_close(session, payload, interval_seconds, credited_user_display_name)
            elif closing_state == TaskStepStateEnum.PAUSED:
                await _apply_paused_close(session, payload, interval_seconds, credited_user_display_name)
            elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
                await _apply_ended_shift_close(session, payload, interval_seconds, credited_user_display_name)

        # Issues rule: applies regardless of recorded_time_marked_wrong
        new_state = TaskStepStateEnum(payload.new_state)
        if new_state == TaskStepStateEnum.COMPLETED:
            await _apply_issues_at_completion(session, payload, credited_user_display_name)

        await session.commit()


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


def _compute_interval_seconds(payload: StepTransitionPayload) -> int:
    """Compute duration in seconds between entered_at and exited_at."""
    entered = datetime.fromisoformat(payload.entered_at)
    exited = datetime.fromisoformat(payload.exited_at)
    delta = exited - entered
    return max(0, int(delta.total_seconds()))


async def _apply_working_close(
    session: AsyncSession, payload: StepTransitionPayload, interval_seconds: int, worker_display_name: str
) -> None:
    """Apply increments for a closed WORKING record."""
    cost_minor = await _compute_cost_minor(session, payload.credited_user_id, payload.workspace_id, interval_seconds)
    work_date = datetime.fromisoformat(payload.entered_at).date()

    if payload.credited_user_id:
        await _increment_user_daily(
            session, payload, work_date, worker_display_name,
            working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor
        )
        await _increment_user_lifetime(
            session, payload, worker_display_name,
            working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor
        )
        await _increment_user_section_daily(
            session, payload, work_date, worker_display_name,
            working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor
        )

    await _increment_section_daily(
        session, payload, work_date,
        working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor
    )


async def _apply_paused_close(
    session: AsyncSession, payload: StepTransitionPayload, interval_seconds: int, worker_display_name: str
) -> None:
    """Apply increments for a closed PAUSED record."""
    cost_minor = await _compute_cost_minor(session, payload.credited_user_id, payload.workspace_id, interval_seconds)
    work_date = datetime.fromisoformat(payload.entered_at).date()

    if payload.credited_user_id:
        await _increment_user_daily(
            session, payload, work_date, worker_display_name,
            pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor
        )
        await _increment_user_lifetime(
            session, payload, worker_display_name,
            pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor
        )
        await _increment_user_section_daily(
            session, payload, work_date, worker_display_name,
            pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor
        )

    await _increment_section_daily(
        session, payload, work_date,
        pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor
    )


async def _apply_ended_shift_close(
    session: AsyncSession, payload: StepTransitionPayload, interval_seconds: int, worker_display_name: str
) -> None:
    """Apply increments for a closed ENDED_SHIFT record (NOT costed)."""
    work_date = datetime.fromisoformat(payload.entered_at).date()

    if payload.credited_user_id:
        await _increment_user_daily(
            session, payload, work_date, worker_display_name,
            ended_shift_seconds=interval_seconds, ended_shift_count=1
        )
        await _increment_user_lifetime(
            session, payload, worker_display_name,
            ended_shift_seconds=interval_seconds, ended_shift_count=1
        )
        await _increment_user_section_daily(
            session, payload, work_date, worker_display_name,
            ended_shift_seconds=interval_seconds, ended_shift_count=1
        )

    await _increment_section_daily(
        session, payload, work_date,
        ended_shift_seconds=interval_seconds, ended_shift_count=1
    )


async def _apply_issues_at_completion(
    session: AsyncSession, payload: StepTransitionPayload, worker_display_name: str
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


async def _compute_cost_minor(
    session: AsyncSession, worker_id: str | None, workspace_id: str, interval_seconds: int
) -> int:
    """Compute cost in minor units (cents) for a work interval."""
    if not worker_id:
        return 0
    profile_result = await session.execute(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == worker_id,
            UserWorkProfile.workspace_id == workspace_id,
        )
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None or profile.salary_per_hour_before_tax is None:
        return 0
    cost = (Decimal(str(interval_seconds)) / Decimal("3600")) * profile.salary_per_hour_before_tax * Decimal("100")
    return int(cost.to_integral_value())


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
    session: AsyncSession, workspace_id: str, user_id: str, section_id: str, work_date: date, display_name: str
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
            section_name_snapshot=display_name,
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
    cost_minor: int = 0,
) -> None:
    """Increment UserSectionDailyWorkStats row."""
    row = await _get_or_create_user_section_daily(
        session, payload.workspace_id, payload.credited_user_id, payload.working_section_id,
        work_date, worker_display_name
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
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
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)
