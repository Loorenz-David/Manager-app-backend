from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps
from beyo_manager.services.commands.working_sections.create_working_section import (
    create_working_section,
)
from beyo_manager.services.commands.working_sections.edit_working_section import (
    edit_working_section,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_worker_working_sections import (
    get_worker_working_sections,
)
from beyo_manager.services.queries.working_sections.get_working_section import (
    get_working_section,
)


def _ctx(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    incoming_data: dict,
    query_params: dict | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        query_params=query_params or {},
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


async def _seed_step_with_state_record(
    db_session,
    *,
    workspace_id: str,
    working_section_id: str,
    user_id: str,
    task_scalar_id: int,
    task_deleted: bool = False,
    step_state: TaskStepStateEnum = TaskStepStateEnum.PENDING,
) -> TaskStep:
    now = datetime.now(timezone.utc)
    task = Task(
        workspace_id=workspace_id,
        task_scalar_id=task_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user_id,
        is_deleted=task_deleted,
        deleted_at=now if task_deleted else None,
        deleted_by_id=user_id if task_deleted else None,
    )
    db_session.add(task)
    await db_session.flush()

    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=working_section_id,
        working_section_name_snapshot="Section",
        allows_batch_working=False,
        state=step_state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()

    record = StepStateRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        state=step_state,
        entered_at=now,
        created_by_id=user_id,
    )
    db_session.add(record)
    await db_session.flush()

    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


@pytest.mark.integration
async def test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)

    async def _fake_dispatch(_events):
        return None

    async def _fake_event_bus_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.working_sections.create_working_section.dispatch",
        _fake_dispatch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.working_sections.edit_working_section.dispatch",
        _fake_dispatch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.add_task_steps.event_bus.dispatch",
        _fake_event_bus_dispatch,
    )

    created_batch = await create_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "name": "Ground oil",
                "allows_batch_working": True,
            },
        )
    )
    created_non_batch = await create_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "name": "Assembly",
            },
        )
    )

    batch_section_id = created_batch["client_id"]
    non_batch_section_id = created_non_batch["client_id"]

    db_session.add_all(
        [
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=batch_section_id,
                user_id=user.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=non_batch_section_id,
                user_id=user.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
        ]
    )

    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()

    first_add_result = await add_task_steps(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_id": task.client_id,
                "steps": [
                    {"working_section_id": batch_section_id},
                    {"working_section_id": non_batch_section_id},
                ],
            },
        )
    )

    initial_steps = (
        await db_session.execute(
            select(TaskStep)
            .where(TaskStep.client_id.in_(first_add_result["step_ids"]))
            .order_by(TaskStep.client_id.asc())
        )
    ).scalars().all()
    snapshot_by_section = {step.working_section_id: step.allows_batch_working for step in initial_steps}

    assert snapshot_by_section[batch_section_id] is True
    assert snapshot_by_section[non_batch_section_id] is False

    get_before_edit = await get_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": batch_section_id},
        )
    )
    assert get_before_edit["working_section"]["allows_batch_working"] is True

    await edit_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "client_id": batch_section_id,
                "allows_batch_working": False,
            },
        )
    )

    get_after_edit = await get_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": batch_section_id},
        )
    )
    assert get_after_edit["working_section"]["allows_batch_working"] is False

    worker_sections = await get_worker_working_sections(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={},
        )
    )
    worker_section_by_id = {
        section["client_id"]: section for section in worker_sections["working_sections"]
    }
    assert worker_section_by_id[batch_section_id]["allows_batch_working"] is False
    assert worker_section_by_id[non_batch_section_id]["allows_batch_working"] is False

    second_add_result = await add_task_steps(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_id": task.client_id,
                "steps": [{"working_section_id": batch_section_id}],
            },
        )
    )
    edited_snapshot_step = await db_session.scalar(
        select(TaskStep).where(TaskStep.client_id == second_add_result["step_ids"][0])
    )
    assert edited_snapshot_step is not None
    assert edited_snapshot_step.allows_batch_working is False

    original_batch_step = await db_session.scalar(
        select(TaskStep).where(TaskStep.client_id == first_add_result["step_ids"][0])
    )
    assert original_batch_step is not None
    assert original_batch_step.allows_batch_working is True


@pytest.mark.integration
async def test_worker_working_sections_excludes_counts_for_deleted_parent_tasks(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)

    async def _fake_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.working_sections.create_working_section.dispatch",
        _fake_dispatch,
    )

    created_section = await create_working_section(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"name": "Cleaning wood"},
        )
    )
    section_id = created_section["client_id"]

    db_session.add(
        WorkingSectionMembership(
            workspace_id=workspace.client_id,
            working_section_id=section_id,
            user_id=user.client_id,
            assigned_at=datetime.now(timezone.utc),
            assigned_by_id=user.client_id,
        )
    )
    await db_session.flush()

    await _seed_step_with_state_record(
        db_session,
        workspace_id=workspace.client_id,
        working_section_id=section_id,
        user_id=user.client_id,
        task_scalar_id=1,
        task_deleted=False,
        step_state=TaskStepStateEnum.PENDING,
    )
    await _seed_step_with_state_record(
        db_session,
        workspace_id=workspace.client_id,
        working_section_id=section_id,
        user_id=user.client_id,
        task_scalar_id=2,
        task_deleted=True,
        step_state=TaskStepStateEnum.PENDING,
    )

    worker_sections = await get_worker_working_sections(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={},
        )
    )

    section = next(s for s in worker_sections["working_sections"] if s["client_id"] == section_id)
    assert section["task_steps_counts"]["pending"] == 1
    assert section["ready_and_pending_count"] == 1
