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
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.task_steps.transition_step_state import transition_step_state
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, task_id: str, step_id: str) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={
            "task_id": task_id,
            "step_id": step_id,
            "new_state": TaskStepStateEnum.WORKING.value,
        },
        session=db_session,
    )


async def _seed_workspace_user_and_task(db_session) -> tuple[Workspace, User, Task]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(task)
    await db_session.flush()
    return workspace, user, task


async def _seed_step(
    db_session,
    *,
    workspace_id: str,
    task_id: str,
    user_id: str,
    step_id: str,
    state: TaskStepStateEnum,
    allows_batch_working: bool,
) -> TaskStep:
    section = WorkingSection(
        client_id=f"wsec_{step_id}",
        workspace_id=workspace_id,
        name=f"Section {step_id}",
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        client_id=step_id,
        workspace_id=workspace_id,
        task_id=task_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=f"Section {step_id}",
        allows_batch_working=allows_batch_working,
        state=state,
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
        state=state,
        entered_at=datetime.now(timezone.utc),
        created_by_id=user_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


def _patch_transition_side_effects(monkeypatch) -> None:
    async def _fake_create_instant_task(**_kwargs):
        return None

    async def _fake_dispatch(_events):
        return None

    async def _fake_resolve_step_targets(*_args, **_kwargs):
        return []

    async def _fake_resolve_task_targets(*_args, **_kwargs):
        return []

    async def _fake_item_label(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.create_instant_task",
        _fake_create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.event_bus.dispatch",
        _fake_dispatch,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.resolve_task_step_notification_targets",
        _fake_resolve_step_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.resolve_task_notification_targets",
        _fake_resolve_task_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.resolve_item_label_for_task",
        _fake_item_label,
    )


@pytest.mark.integration
async def test_starting_non_batch_step_pauses_only_other_non_batch_steps(db_session, monkeypatch):
    _patch_transition_side_effects(monkeypatch)
    workspace, user, task = await _seed_workspace_user_and_task(db_session)
    paused_target = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_non_batch_existing",
        state=TaskStepStateEnum.WORKING,
        allows_batch_working=False,
    )
    unaffected_batch = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_batch_existing",
        state=TaskStepStateEnum.WORKING,
        allows_batch_working=True,
    )
    activating_step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_non_batch_new",
        state=TaskStepStateEnum.PENDING,
        allows_batch_working=False,
    )

    await transition_step_state(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
            step_id=activating_step.client_id,
        )
    )

    refreshed_non_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == paused_target.client_id))
    refreshed_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == unaffected_batch.client_id))
    refreshed_activating = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == activating_step.client_id))

    assert refreshed_non_batch is not None
    assert refreshed_batch is not None
    assert refreshed_activating is not None
    assert refreshed_non_batch.state == TaskStepStateEnum.PAUSED
    assert refreshed_batch.state == TaskStepStateEnum.WORKING
    assert refreshed_activating.state == TaskStepStateEnum.WORKING


@pytest.mark.integration
async def test_starting_batch_step_does_not_pause_existing_non_batch_step(db_session, monkeypatch):
    _patch_transition_side_effects(monkeypatch)
    workspace, user, task = await _seed_workspace_user_and_task(db_session)
    existing_non_batch = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_non_batch_working",
        state=TaskStepStateEnum.WORKING,
        allows_batch_working=False,
    )
    batch_step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_batch_pending",
        state=TaskStepStateEnum.PENDING,
        allows_batch_working=True,
    )

    await transition_step_state(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
            step_id=batch_step.client_id,
        )
    )

    refreshed_non_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == existing_non_batch.client_id))
    refreshed_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == batch_step.client_id))
    assert refreshed_non_batch is not None
    assert refreshed_batch is not None
    assert refreshed_non_batch.state == TaskStepStateEnum.WORKING
    assert refreshed_batch.state == TaskStepStateEnum.WORKING

    paused_records = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id == existing_non_batch.client_id,
                StepStateRecord.state == TaskStepStateEnum.PAUSED,
            )
        )
    ).scalars().all()
    assert paused_records == []


@pytest.mark.integration
async def test_starting_non_batch_step_does_not_pause_existing_batch_step(db_session, monkeypatch):
    _patch_transition_side_effects(monkeypatch)
    workspace, user, task = await _seed_workspace_user_and_task(db_session)
    existing_batch = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_batch_working",
        state=TaskStepStateEnum.WORKING,
        allows_batch_working=True,
    )
    non_batch_step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        step_id="tsp_non_batch_pending",
        state=TaskStepStateEnum.PENDING,
        allows_batch_working=False,
    )

    await transition_step_state(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
            step_id=non_batch_step.client_id,
        )
    )

    refreshed_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == existing_batch.client_id))
    refreshed_non_batch = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == non_batch_step.client_id))
    assert refreshed_batch is not None
    assert refreshed_non_batch is not None
    assert refreshed_batch.state == TaskStepStateEnum.WORKING
    assert refreshed_non_batch.state == TaskStepStateEnum.WORKING

    batch_paused_records = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id == existing_batch.client_id,
                StepStateRecord.state == TaskStepStateEnum.PAUSED,
            )
        )
    ).scalars().all()
    assert batch_paused_records == []
