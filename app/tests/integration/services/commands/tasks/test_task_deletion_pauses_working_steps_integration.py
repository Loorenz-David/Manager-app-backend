"""A deleted task must not leave a step WORKING.

Nothing may touch a deleted task's steps — clock-out included — so an open WORKING record
on one keeps accruing work time for as long as the task stays deleted. `delete_task`
pauses those steps; `restore_task` closes the interval at the deletion instant for tasks
deleted before that rule existed.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.commands.tasks.restore_task import restore_task
from beyo_manager.services.context import ServiceContext


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_scalar_id_counter = itertools.count(1)


def _ctx(db_session, *, workspace_id, user_id, task_id):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "manager",
        },
        incoming_data={"client_id": task_id},
        session=db_session,
    )


async def _seed(db_session) -> tuple[Workspace, User, User, Task]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    manager = User(
        client_id=f"usr_m_{suffix}",
        username=f"manager_{suffix}",
        email=f"m_{suffix}@example.com",
        password="secret",
    )
    worker = User(
        client_id=f"usr_w_{suffix}",
        username=f"worker_{suffix}",
        email=f"w_{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, manager, worker])
    await db_session.flush()
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.PRE_ORDER,
        state=TaskStateEnum.WORKING,
        created_by_id=manager.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    return workspace, manager, worker, task


async def _seed_step(db_session, *, workspace_id, task_id, worker_id, state, entered_at) -> TaskStep:
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
        allows_batch_working=False,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=worker_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        state=state,
        entered_at=entered_at,
        created_by_id=worker_id,
        credited_user_id=worker_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def _records(db_session, step_id: str) -> list[StepStateRecord]:
    return list(
        (
            await db_session.execute(
                select(StepStateRecord)
                .where(StepStateRecord.step_id == step_id)
                .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
            )
        ).scalars()
    )


def _capture(monkeypatch) -> list[list[str]]:
    paused: list[list[str]] = []

    async def _noop(*_args, **_kwargs):
        return None

    async def _emit(_workspace_id, step_ids):
        paused.append(list(step_ids))

    for module in ("delete_task", "restore_task"):
        prefix = f"beyo_manager.services.commands.tasks.{module}"
        monkeypatch.setattr(f"{prefix}.event_bus.dispatch", _noop)
        monkeypatch.setattr(f"{prefix}.emit_steps_paused", _emit)
    return paused


async def test_delete_pauses_a_working_step_and_credits_the_worker(db_session, monkeypatch):
    paused = _capture(monkeypatch)
    workspace, manager, worker, task = await _seed(db_session)
    started = datetime.now(timezone.utc) - timedelta(hours=1)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        worker_id=worker.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=started,
    )

    await delete_task(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=manager.client_id, task_id=task.client_id)
    )

    await db_session.refresh(task)
    await db_session.refresh(step)
    working, pause = await _records(db_session, step.client_id)
    assert step.state == TaskStepStateEnum.PAUSED
    assert step.latest_state_record_id == pause.client_id
    assert working.exited_at == task.deleted_at
    assert pause.state == TaskStepStateEnum.PAUSED
    assert pause.entered_at == task.deleted_at
    assert pause.exited_at is None
    assert pause.transition_reason == TransitionReasonEnum.TASK_DELETED.value
    assert pause.pause_reason_id is None
    assert pause.description == "task deleted"
    # The interrupted work is the worker's, not the deleting manager's.
    assert pause.credited_user_id == worker.client_id
    assert paused == [[step.client_id]]


async def test_delete_leaves_steps_that_are_not_working_alone(db_session, monkeypatch):
    paused = _capture(monkeypatch)
    workspace, manager, worker, task = await _seed(db_session)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        worker_id=worker.client_id,
        state=TaskStepStateEnum.PENDING,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    await delete_task(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=manager.client_id, task_id=task.client_id)
    )

    await db_session.refresh(step)
    assert step.state == TaskStepStateEnum.PENDING
    assert len(await _records(db_session, step.client_id)) == 1
    assert paused == [[]]


async def test_restore_closes_a_stale_working_interval_at_the_deletion(db_session, monkeypatch):
    """A task deleted before delete_task paused steps: its WORKING record is still open."""
    paused = _capture(monkeypatch)
    workspace, manager, worker, task = await _seed(db_session)
    now = datetime.now(timezone.utc)
    deleted_at = now - timedelta(hours=5)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        worker_id=worker.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=deleted_at - timedelta(hours=2),
    )
    task.is_deleted = True
    task.deleted_at = deleted_at
    task.deleted_by_id = manager.client_id
    await db_session.flush()

    await restore_task(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=manager.client_id, task_id=task.client_id)
    )

    await db_session.refresh(step)
    working, pause = await _records(db_session, step.client_id)
    assert step.state == TaskStepStateEnum.PAUSED
    # Two hours of work, not seven: the five deleted hours are not counted.
    assert working.exited_at == deleted_at
    assert pause.entered_at == deleted_at
    assert pause.transition_reason == TransitionReasonEnum.TASK_DELETED.value
    assert pause.credited_user_id == worker.client_id
    assert paused == [[step.client_id]]


async def test_restore_after_a_pausing_delete_changes_no_step(db_session, monkeypatch):
    paused = _capture(monkeypatch)
    workspace, manager, worker, task = await _seed(db_session)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        worker_id=worker.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    ctx_args = dict(workspace_id=workspace.client_id, user_id=manager.client_id, task_id=task.client_id)

    await delete_task(_ctx(db_session, **ctx_args))
    await restore_task(_ctx(db_session, **ctx_args))

    await db_session.refresh(step)
    # Still paused, not resumed: the worker picks it up again.
    assert step.state == TaskStepStateEnum.PAUSED
    assert len(await _records(db_session, step.client_id)) == 2
    assert paused == [[step.client_id], []]
