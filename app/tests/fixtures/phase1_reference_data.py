from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace


async def _role(db_session, role_name: RoleNameEnum) -> Role:
    role = await db_session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name)
        db_session.add(role)
        await db_session.flush()
    return role


async def _workspace(db_session, name: str) -> Workspace:
    workspace = Workspace(name=name)
    db_session.add(workspace)
    await db_session.flush()
    return workspace


async def _pause_reason(
    db_session,
    workspace: Workspace,
    slug: str,
    *,
    name: str | None = None,
) -> PauseReason:
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=name or slug,
        slug=slug,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


@pytest.fixture
async def backfill_shift_reference_data(db_session) -> None:
    """Only the role and pause catalog row looked up by the backfill test helpers."""
    await _role(db_session, RoleNameEnum.WORKER)
    workspace = await _workspace(db_session, "phase1-backfill-reference")
    await _pause_reason(db_session, workspace, "pause_coffee_break")


@pytest.fixture
async def transition_reason_reference_data(db_session) -> None:
    """The smallest catalog and historical population used by retirement assertions."""
    workspace = await _workspace(db_session, "phase1-transition-reference")
    user = User(
        username="phase1-transition-user",
        email="phase1-transition-user@example.com",
        password="test-password-hash",
    )
    db_session.add(user)
    await db_session.flush()

    ended_shift = await _pause_reason(db_session, workspace, "pause_ended_shift")
    case_created = await _pause_reason(db_session, workspace, "pause_case_created")
    section = WorkingSection(workspace_id=workspace.client_id, name="phase1-transition-section")
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.PAUSED,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()

    entered = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    for index in range(7):
        db_session.add(
            StepStateRecord(
                workspace_id=workspace.client_id,
                step_id=step.client_id,
                state=TaskStepStateEnum.PAUSED,
                pause_reason_id=case_created.client_id,
                entered_at=entered + timedelta(minutes=index),
                exited_at=entered + timedelta(minutes=index + 1),
                created_by_id=user.client_id,
                credited_user_id=user.client_id,
            )
        )
    db_session.add(
        StepStateRecord(
            workspace_id=workspace.client_id,
            step_id=step.client_id,
            state=TaskStepStateEnum.PAUSED,
            pause_reason_id=ended_shift.client_id,
            entered_at=entered + timedelta(hours=1),
            exited_at=entered + timedelta(hours=1, minutes=1),
            created_by_id=user.client_id,
            credited_user_id=user.client_id,
        )
    )
    await db_session.flush()


@pytest.fixture
async def kiosk_reference_data(db_session) -> None:
    """The catalog row and roles required before the kiosk test creates its actors."""
    workspace = await _workspace(db_session, "phase1-kiosk-reference")
    await _pause_reason(db_session, workspace, "pause_ended_shift")
    await _role(db_session, RoleNameEnum.MANAGER)
    await _role(db_session, RoleNameEnum.WORKER)


@pytest.fixture
async def worker_shift_reference_data(db_session) -> None:
    """The workspace, role, and pause reason resolved by shift reconstruction helpers."""
    workspace = await _workspace(db_session, "phase1-worker-shift-reference")
    await _role(db_session, RoleNameEnum.WORKER)
    await _pause_reason(db_session, workspace, "pause_lunch_break")
