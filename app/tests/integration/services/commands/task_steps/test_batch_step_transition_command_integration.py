from __future__ import annotations

import itertools
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.task_steps.transition_step_state_batch import (
    transition_step_state_batch,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent


def _ctx(db_session, *, workspace_id, user_id, items, new_state) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={
            "items": items,
            "new_state": new_state.value,
            "reason": None,
            "description": None,
        },
        session=db_session,
    )


async def _seed_workspace_user(db_session) -> tuple[Workspace, User]:
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


_scalar_id_counter = itertools.count(1)


async def _seed_task(db_session, *, workspace_id, user_id, state=TaskStateEnum.ASSIGNED) -> Task:
    suffix = uuid4().hex[:8]
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.INTERNAL,
        state=state,
        created_by_id=user_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _seed_step(
    db_session,
    *,
    workspace_id,
    task_id,
    user_id,
    state,
    allows_batch_working=True,
    with_open_record=True,
) -> TaskStep:
    suffix = uuid4().hex[:8]
    section = WorkingSection(
        client_id=f"wsec_{suffix}",
        workspace_id=workspace_id,
        name=f"Section {suffix}",
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        client_id=f"tsp_{suffix}",
        workspace_id=workspace_id,
        task_id=task_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=f"Section {suffix}",
        allows_batch_working=allows_batch_working,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()

    if with_open_record:
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


def _patch_batch_side_effects(monkeypatch, *, capture: list | None = None) -> None:
    async def _noop_create_instant_task(**_kwargs):
        return None

    async def _noop_targets(*_args, **_kwargs):
        return []

    async def _dispatch(events):
        if capture is not None:
            capture.append(events)

    # Outbox + notification target resolution live in both the core and the batch command.
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps._step_transition_core.create_instant_task",
        _noop_create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps._step_transition_core.resolve_task_step_notification_targets",
        _noop_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state_batch.create_instant_task",
        _noop_create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state_batch.resolve_task_notification_targets",
        _noop_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state_batch.event_bus.dispatch",
        _dispatch,
    )


async def _state_of(db_session, step_id) -> TaskStepStateEnum:
    step = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == step_id))
    return step.state


@pytest.mark.integration
@pytest.mark.parametrize(
    "current_state,new_state",
    [
        (TaskStepStateEnum.PENDING, TaskStepStateEnum.WORKING),
        (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED),
        (TaskStepStateEnum.PAUSED, TaskStepStateEnum.WORKING),
        (TaskStepStateEnum.WORKING, TaskStepStateEnum.COMPLETED),
    ],
)
async def test_batch_transitions_all_steps(db_session, monkeypatch, current_state, new_state):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    steps = [
        await _seed_step(
            db_session,
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            user_id=user.client_id,
            state=current_state,
        )
        for _ in range(3)
    ]
    items = [{"task_id": task.client_id, "step_id": s.client_id} for s in steps]

    result = await transition_step_state_batch(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, items=items, new_state=new_state)
    )

    assert {r["step_id"] for r in result["items"]} == {s.client_id for s in steps}
    for s in steps:
        assert await _state_of(db_session, s.client_id) == new_state


@pytest.mark.integration
async def test_batch_transition_spans_multiple_tasks(db_session, monkeypatch):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task_a = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    task_b = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step_a = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task_a.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.PENDING,
    )
    step_b = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task_b.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.PENDING,
    )
    items = [
        {"task_id": task_a.client_id, "step_id": step_a.client_id},
        {"task_id": task_b.client_id, "step_id": step_b.client_id},
    ]

    await transition_step_state_batch(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
             items=items, new_state=TaskStepStateEnum.WORKING)
    )

    assert await _state_of(db_session, step_a.client_id) == TaskStepStateEnum.WORKING
    assert await _state_of(db_session, step_b.client_id) == TaskStepStateEnum.WORKING
    refreshed_a = await db_session.scalar(select(Task).where(Task.client_id == task_a.client_id))
    refreshed_b = await db_session.scalar(select(Task).where(Task.client_id == task_b.client_id))
    assert refreshed_a.state == TaskStateEnum.WORKING
    assert refreshed_b.state == TaskStateEnum.WORKING


@pytest.mark.integration
async def test_batch_is_atomic_when_one_item_invalid(db_session, monkeypatch):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    valid_a = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.WORKING,
    )
    valid_b = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.WORKING,
    )
    # Terminal step cannot transition — should reject the whole batch.
    terminal = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.COMPLETED,
    )
    items = [
        {"task_id": task.client_id, "step_id": valid_a.client_id},
        {"task_id": task.client_id, "step_id": valid_b.client_id},
        {"task_id": task.client_id, "step_id": terminal.client_id},
    ]

    with pytest.raises(ValidationError):
        await transition_step_state_batch(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
                 items=items, new_state=TaskStepStateEnum.PAUSED)
        )

    # Nothing changed.
    assert await _state_of(db_session, valid_a.client_id) == TaskStepStateEnum.WORKING
    assert await _state_of(db_session, valid_b.client_id) == TaskStepStateEnum.WORKING
    paused_records = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id.in_([valid_a.client_id, valid_b.client_id]),
                StepStateRecord.state == TaskStepStateEnum.PAUSED,
            )
        )
    ).scalars().all()
    assert paused_records == []


@pytest.mark.integration
async def test_batch_rejects_non_batch_step(db_session, monkeypatch):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    non_batch = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.WORKING, allows_batch_working=False,
    )
    items = [{"task_id": task.client_id, "step_id": non_batch.client_id}]

    with pytest.raises(ValidationError):
        await transition_step_state_batch(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
                 items=items, new_state=TaskStepStateEnum.PAUSED)
        )

    assert await _state_of(db_session, non_batch.client_id) == TaskStepStateEnum.WORKING


@pytest.mark.integration
async def test_batch_emits_single_coalesced_event(db_session, monkeypatch):
    captured: list = []
    _patch_batch_side_effects(monkeypatch, capture=captured)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
                            state=TaskStateEnum.WORKING)
    steps = [
        await _seed_step(
            db_session, workspace_id=workspace.client_id, task_id=task.client_id,
            user_id=user.client_id, state=TaskStepStateEnum.WORKING,
        )
        for _ in range(3)
    ]
    items = [{"task_id": task.client_id, "step_id": s.client_id} for s in steps]

    # working -> paused does not change the (already WORKING) task state, so only the
    # coalesced step-state-changed event should be dispatched.
    await transition_step_state_batch(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
             items=items, new_state=TaskStepStateEnum.PAUSED)
    )

    assert len(captured) == 1
    events = captured[0]
    batch_events = [e for e in events if isinstance(e, BatchWorkspaceEvent)]
    assert len(batch_events) == 1
    assert batch_events[0].event_name == "task:step-state-changed"
    assert {i["client_id"] for i in batch_events[0].items} == {s.client_id for s in steps}
    assert all(i["new_state"] == TaskStepStateEnum.PAUSED.value for i in batch_events[0].items)
    # No task:state-changed event since task was already WORKING.
    assert len(events) == 1


@pytest.mark.integration
async def test_batch_complete_honors_per_step_mark_inaccurate(db_session, monkeypatch):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
                            state=TaskStateEnum.WORKING)
    flagged = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.WORKING,
    )
    unflagged = await _seed_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id,
        user_id=user.client_id, state=TaskStepStateEnum.WORKING,
    )
    items = [
        {"task_id": task.client_id, "step_id": flagged.client_id, "mark_closing_record_inaccurate": True},
        {"task_id": task.client_id, "step_id": unflagged.client_id, "mark_closing_record_inaccurate": False},
    ]

    await transition_step_state_batch(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
             items=items, new_state=TaskStepStateEnum.COMPLETED)
    )

    flagged_step = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == flagged.client_id))
    unflagged_step = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == unflagged.client_id))
    assert flagged_step.recorded_time_marked_wrong is True
    assert unflagged_step.recorded_time_marked_wrong is False
    # The closing WORKING record of the flagged step is marked inaccurate.
    flagged_closing = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == flagged.client_id,
            StepStateRecord.state == TaskStepStateEnum.WORKING,
        )
    )
    assert flagged_closing.recorded_time_marked_wrong is True


@pytest.mark.integration
async def test_batch_completing_all_steps_marks_task_ready(db_session, monkeypatch):
    _patch_batch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
                            state=TaskStateEnum.WORKING)
    steps = [
        await _seed_step(
            db_session, workspace_id=workspace.client_id, task_id=task.client_id,
            user_id=user.client_id, state=TaskStepStateEnum.WORKING,
        )
        for _ in range(2)
    ]
    items = [{"task_id": task.client_id, "step_id": s.client_id} for s in steps]

    await transition_step_state_batch(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id,
             items=items, new_state=TaskStepStateEnum.COMPLETED)
    )

    for s in steps:
        assert await _state_of(db_session, s.client_id) == TaskStepStateEnum.COMPLETED
    refreshed = await db_session.scalar(select(Task).where(Task.client_id == task.client_id))
    assert refreshed.state == TaskStateEnum.READY
