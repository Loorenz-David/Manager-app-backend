from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, task_id: str, steps: list[dict]) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={"task_id": task_id, "steps": steps},
        session=db_session,
    )


@pytest.mark.integration
async def test_adding_a_batch_of_steps_reopens_ready_task(db_session, monkeypatch):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    worker_a = User(
        client_id=f"usr_a_{suffix}",
        username=f"worker_a_{suffix}",
        email=f"worker_a_{suffix}@example.com",
        password="secret",
    )
    worker_b = User(
        client_id=f"usr_b_{suffix}",
        username=f"worker_b_{suffix}",
        email=f"worker_b_{suffix}@example.com",
        password="secret",
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.READY,
        created_by_id=user.client_id,
    )
    section_a = WorkingSection(
        client_id=f"wsec_a_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Section A {suffix}",
    )
    section_b = WorkingSection(
        client_id=f"wsec_b_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Section B {suffix}",
    )
    worker_role = Role(client_id=f"role_{suffix}", name=RoleNameEnum.WORKER)
    workspace_worker_role = WorkspaceRole(
        client_id=f"wsr_{suffix}",
        workspace_id=workspace.client_id,
        role_id=worker_role.client_id,
        is_system=True,
    )
    db_session.add_all([workspace, user, worker_a, worker_b, worker_role])
    await db_session.flush()
    db_session.add(workspace_worker_role)
    await db_session.flush()
    db_session.add_all(
        [
            task,
            section_a,
            section_b,
            WorkspaceMembership(
                workspace_id=workspace.client_id,
                user_id=worker_a.client_id,
                workspace_role_id=workspace_worker_role.client_id,
            ),
            WorkspaceMembership(
                workspace_id=workspace.client_id,
                user_id=worker_b.client_id,
                workspace_role_id=workspace_worker_role.client_id,
            ),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=section_a.client_id,
                user_id=worker_a.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=section_a.client_id,
                user_id=worker_b.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=section_b.client_id,
                user_id=worker_a.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=section_b.client_id,
                user_id=worker_b.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
        ]
    )
    await db_session.flush()

    dispatched_events: list[list] = []

    async def _capture(events):
        dispatched_events.append(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.add_task_steps.event_bus.dispatch",
        _capture,
    )

    result = await add_task_steps(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
            steps=[
                {"working_section_id": section_a.client_id},
                {"working_section_id": section_b.client_id},
            ],
        )
    )

    await db_session.refresh(task)
    created_steps = (
        await db_session.execute(
            select(TaskStep).where(TaskStep.task_id == task.client_id).order_by(TaskStep.client_id)
        )
    ).scalars().all()

    assert result["step_ids"]
    assert len(created_steps) == 2
    assert all(step.state == TaskStepStateEnum.PENDING for step in created_steps)
    assert task.state == TaskStateEnum.WORKING

    notification_tasks = (
        await db_session.execute(
            select(ExecutionTask, ExecutionPayload)
            .join(ExecutionPayload, ExecutionPayload.execution_task_id == ExecutionTask.client_id)
            .where(
                ExecutionTask.task_type == TaskType.CREATE_NOTIFICATIONS,
                ExecutionPayload.payload["entity_client_id"].as_string() == task.client_id,
            )
        )
    ).all()
    assert len(notification_tasks) == 1
    _, notification_payload = notification_tasks[0]
    assert notification_payload.payload["notification_type"] == "task_steps_reopened"
    assert notification_payload.payload["user_ids"] == sorted(
        [worker_a.client_id, worker_b.client_id]
    )
    assert notification_payload.payload["entity_client_id"] == task.client_id

    state_events = [event for event in dispatched_events[0] if event.event_name == "task:state-changed"]
    assert len(state_events) == 1
    assert state_events[0].extra == {"new_state": TaskStateEnum.WORKING.value}
