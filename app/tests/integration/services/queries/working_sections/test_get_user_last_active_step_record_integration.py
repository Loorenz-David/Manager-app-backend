from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_user_last_active_step_record import (
    get_user_last_active_step_record,
)


def _ctx(db_session, *, workspace_id: str, user_id: str) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "worker",
            "username": "tester",
        },
        incoming_data={},
        query_params={},
        session=db_session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_step_with_record(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    task_scalar_id: int,
    created_at: datetime,
    task_deleted: bool = False,
    step_deleted: bool = False,
    allows_batch_working: bool = False,
    state: TaskStepStateEnum = TaskStepStateEnum.WORKING,
    exited_at: datetime | None = None,
) -> TaskStep:
    unique = uuid4().hex[:8]
    section = WorkingSection(
        client_id=f"wsec_{unique}",
        workspace_id=workspace_id,
        name=f"Section {unique}",
        allows_batch_working=allows_batch_working,
    )
    db_session.add(section)
    await db_session.flush()

    task = Task(
        client_id=f"tsk_{unique}",
        workspace_id=workspace_id,
        task_scalar_id=task_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user_id,
        is_deleted=task_deleted,
        deleted_at=created_at if task_deleted else None,
        deleted_by_id=user_id if task_deleted else None,
    )
    db_session.add(task)
    await db_session.flush()

    step = TaskStep(
        client_id=f"tsp_{unique}",
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=allows_batch_working,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user_id,
        is_deleted=step_deleted,
        deleted_at=created_at if step_deleted else None,
        deleted_by_id=user_id if step_deleted else None,
    )
    db_session.add(step)
    await db_session.flush()

    record = StepStateRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        state=state,
        entered_at=created_at,
        exited_at=exited_at,
        created_at=created_at,
        created_by_id=user_id,
    )
    db_session.add(record)
    await db_session.flush()

    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


@pytest.mark.integration
async def test_returns_non_deleted_step_when_deleted_task_has_newer_active_record(db_session):
    workspace, user = await _seed_workspace_and_user(db_session)
    now = datetime.now(timezone.utc)
    valid_step = await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=1,
        created_at=now - timedelta(minutes=5),
    )
    await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=2,
        created_at=now,
        task_deleted=True,
    )

    result = await get_user_last_active_step_record(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    )

    assert result["user_last_active_step_record"] is not None
    assert result["user_last_active_step_record"]["client_id"] == valid_step.client_id
    assert result["active_batch_steps"] is None


@pytest.mark.integration
async def test_returns_none_when_only_active_records_belong_to_deleted_tasks(db_session):
    workspace, user = await _seed_workspace_and_user(db_session)
    now = datetime.now(timezone.utc)
    await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=1,
        created_at=now,
        task_deleted=True,
    )

    result = await get_user_last_active_step_record(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    )

    assert result == {"user_last_active_step_record": None, "active_batch_steps": None}


@pytest.mark.integration
async def test_excludes_deleted_task_steps_from_active_batch_steps(db_session):
    workspace, user = await _seed_workspace_and_user(db_session)
    now = datetime.now(timezone.utc)
    primary_step = await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=1,
        created_at=now - timedelta(minutes=2),
        allows_batch_working=True,
    )
    included_batch_step = await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=2,
        created_at=now - timedelta(minutes=1),
        allows_batch_working=True,
    )
    await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=3,
        created_at=now,
        task_deleted=True,
        allows_batch_working=True,
    )

    result = await get_user_last_active_step_record(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    )

    assert result["user_last_active_step_record"] is not None
    assert result["user_last_active_step_record"]["client_id"] == included_batch_step.client_id
    assert result["active_batch_steps"] is not None
    assert [step["client_id"] for step in result["active_batch_steps"]] == [
        included_batch_step.client_id,
        primary_step.client_id,
    ]


@pytest.mark.integration
async def test_excludes_deleted_steps_from_primary_selection(db_session):
    workspace, user = await _seed_workspace_and_user(db_session)
    now = datetime.now(timezone.utc)
    valid_step = await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=1,
        created_at=now - timedelta(minutes=5),
    )
    await _seed_step_with_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_scalar_id=2,
        created_at=now,
        step_deleted=True,
    )

    result = await get_user_last_active_step_record(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    )

    assert result["user_last_active_step_record"] is not None
    assert result["user_last_active_step_record"]["client_id"] == valid_step.client_id
