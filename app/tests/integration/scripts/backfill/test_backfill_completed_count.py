from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from scripts.backfill.backfill_completed_count import _collect_counts, _write_counts


async def _seed_user(db_session) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_completed_step(
    db_session,
    *,
    workspace_id: str,
    performer_id: str,
    credited_user_id: str | None,
    completed_at: datetime,
) -> TaskStep:
    unique = uuid4().hex[:8]
    section = WorkingSection(
        client_id=f"wsec_{unique}",
        workspace_id=workspace_id,
        name=f"Section {unique}",
    )
    db_session.add(section)
    await db_session.flush()

    task = Task(
        client_id=f"tsk_{unique}",
        workspace_id=workspace_id,
        task_scalar_id=int(unique[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=performer_id,
    )
    db_session.add(task)
    await db_session.flush()

    step = TaskStep(
        client_id=f"tsp_{unique}",
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=performer_id,
    )
    db_session.add(step)
    await db_session.flush()

    record = StepStateRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.COMPLETED,
        entered_at=completed_at,
        exited_at=None,
        created_at=completed_at,
        created_by_id=performer_id,
        credited_user_id=credited_user_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def _daily_count(db_session, workspace_id: str, user_id: str, work_date) -> int | None:
    result = await db_session.execute(
        select(UserDailyWorkStats.total_completed_count).where(
            UserDailyWorkStats.workspace_id == workspace_id,
            UserDailyWorkStats.user_id == user_id,
            UserDailyWorkStats.work_date == work_date,
        )
    )
    return result.scalar_one_or_none()


@pytest.mark.integration
async def test_backfill_credits_credited_user_and_falls_back_to_performer(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    db_session.add(workspace)
    await db_session.flush()

    performer = await _seed_user(db_session)
    credited = await _seed_user(db_session)
    completed_at = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
    work_date = completed_at.date()

    # Completion credited to another user -> counts go to the credited user.
    await _seed_completed_step(
        db_session,
        workspace_id=workspace.client_id,
        performer_id=performer.client_id,
        credited_user_id=credited.client_id,
        completed_at=completed_at,
    )
    # Completion with no explicit credit -> falls back to the performer.
    await _seed_completed_step(
        db_session,
        workspace_id=workspace.client_id,
        performer_id=performer.client_id,
        credited_user_id=None,
        completed_at=completed_at,
    )

    counts = await _collect_counts(db_session, None)
    await _write_counts(db_session, counts)
    await db_session.flush()

    assert await _daily_count(db_session, workspace.client_id, credited.client_id, work_date) == 1
    assert await _daily_count(db_session, workspace.client_id, performer.client_id, work_date) == 1

    lifetime = await db_session.execute(
        select(UserLifetimeStats.total_completed_count).where(
            UserLifetimeStats.workspace_id == workspace.client_id,
            UserLifetimeStats.user_id == credited.client_id,
        )
    )
    assert lifetime.scalar_one() == 1


@pytest.mark.integration
async def test_backfill_is_idempotent(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    db_session.add(workspace)
    await db_session.flush()

    performer = await _seed_user(db_session)
    completed_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    work_date = completed_at.date()

    for _ in range(3):
        await _seed_completed_step(
            db_session,
            workspace_id=workspace.client_id,
            performer_id=performer.client_id,
            credited_user_id=None,
            completed_at=completed_at,
        )

    # First run.
    counts = await _collect_counts(db_session, None)
    await _write_counts(db_session, counts)
    await db_session.flush()
    first = await _daily_count(db_session, workspace.client_id, performer.client_id, work_date)

    # Second run must produce identical values (absolute set, not increment).
    counts = await _collect_counts(db_session, None)
    await _write_counts(db_session, counts)
    await db_session.flush()
    second = await _daily_count(db_session, workspace.client_id, performer.client_id, work_date)

    assert first == 3
    assert second == 3
