"""Integration coverage for the deferred (undo-window) step completion worker.

Regression focus: this handler used to evaluate the readiness predicate inline and assign
`task.state = READY` itself, which skipped `reconcile_task_side_effects` and left a
qualifying task permanently without its post-handling and customer-coordination rows —
permanently, because every other caller of the predicate early-returns once the state is
already READY. The tests below pin the side effects, not just the state, so a future
inline reimplementation fails here rather than in production.

The undo-window scheduler that feeds this handler is currently disabled in
`transition_step_state` (the block is commented out for later re-enablement), so this path
does not run today. That is exactly why it is worth covering: the bug is dormant, and
whoever switches the window back on should not have to rediscover it.
"""

from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import (
    TaskReturnSourceEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.tasks.task_steps import finalize_pending_step_completion as module


_scalar_id_counter = itertools.count(1)


class _NestedTxSession:
    """Delegates to the test session but maps `begin()` onto a SAVEPOINT.

    The handler owns its transaction (`async with session.begin()`), which cannot be
    opened on a session the test fixture has already written through. A nested
    transaction gives the handler the same commit/rollback semantics while leaving the
    fixture's outer rollback in charge of cleanup — nothing this test writes survives.
    """

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def begin(self):
        return self._session.begin_nested()


def _patch_worker(monkeypatch, session) -> list:
    dispatched: list = []

    async def _fake_get_db_session() -> AsyncIterator[object]:
        yield _NestedTxSession(session)

    async def _noop_create_instant_task(**_kwargs):
        return None

    async def _noop_targets(*_args, **_kwargs):
        return []

    async def _dispatch(events):
        dispatched.append(events)

    monkeypatch.setattr(module, "get_db_session", _fake_get_db_session)
    monkeypatch.setattr(module, "create_instant_task", _noop_create_instant_task)
    monkeypatch.setattr(module, "resolve_task_step_notification_targets", _noop_targets)
    monkeypatch.setattr(module.event_bus, "dispatch", _dispatch)
    return dispatched


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


async def _seed_task(db_session, *, workspace_id, user_id, task_type, **fields) -> Task:
    suffix = uuid4().hex[:8]
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=task_type,
        state=TaskStateEnum.WORKING,
        created_by_id=user_id,
        **fields,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _seed_working_step(db_session, *, workspace_id, task_id, user_id) -> TaskStep:
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
        state=TaskStepStateEnum.WORKING,
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
        state=TaskStepStateEnum.WORKING,
        entered_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        created_by_id=user_id,
        credited_user_id=user_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


def _payload(*, step, task, workspace_id, user_id) -> dict:
    return {
        "step_id": step.client_id,
        "task_id": task.client_id,
        "workspace_id": workspace_id,
        "completion_requested_at": datetime.now(timezone.utc).isoformat(),
        "performed_by_user_id": user_id,
        "credited_user_id": user_id,
        "pause_reason_id": None,
        "description": None,
    }


async def _post_handling_for(db_session, task_id) -> TaskPostHandling | None:
    return await db_session.scalar(
        select(TaskPostHandling).where(TaskPostHandling.task_id == task_id)
    )


async def _coordination_for(db_session, task_id) -> TaskCustomerCoordination | None:
    return await db_session.scalar(
        select(TaskCustomerCoordination).where(TaskCustomerCoordination.task_id == task_id)
    )


@pytest.mark.integration
async def test_last_step_completion_creates_post_handling(db_session, monkeypatch):
    """The regression: a RETURN task finishing through the undo window must get its
    post-handling instance, exactly as one finishing through the normal path does."""
    _patch_worker(monkeypatch, db_session)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_type=TaskTypeEnum.RETURN,
        return_source=TaskReturnSourceEnum.STORE_RETURN,
    )
    step = await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )

    await module.handle_finalize_pending_step_completion(
        _payload(step=step, task=task, workspace_id=workspace.client_id, user_id=user.client_id),
        "exec_task_1",
    )

    await db_session.refresh(task)
    assert task.state == TaskStateEnum.READY
    assert await _post_handling_for(db_session, task.client_id) is not None


@pytest.mark.integration
async def test_last_step_completion_creates_customer_coordination(db_session, monkeypatch):
    """A non-store RETURN also calls for a customer-coordination instance."""
    _patch_worker(monkeypatch, db_session)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_type=TaskTypeEnum.RETURN,
        return_source=TaskReturnSourceEnum.AFTER_PURCHASE,
    )
    step = await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )

    await module.handle_finalize_pending_step_completion(
        _payload(step=step, task=task, workspace_id=workspace.client_id, user_id=user.client_id),
        "exec_task_2",
    )

    await db_session.refresh(task)
    assert task.state == TaskStateEnum.READY
    assert await _coordination_for(db_session, task.client_id) is not None


@pytest.mark.integration
async def test_non_qualifying_task_type_gets_no_instances(db_session, monkeypatch):
    """Delegating to the shared predicate must not widen applicability: an INTERNAL task
    reaches READY with no auxiliary rows, as before."""
    _patch_worker(monkeypatch, db_session)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_type=TaskTypeEnum.INTERNAL,
    )
    step = await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )

    await module.handle_finalize_pending_step_completion(
        _payload(step=step, task=task, workspace_id=workspace.client_id, user_id=user.client_id),
        "exec_task_3",
    )

    await db_session.refresh(task)
    assert task.state == TaskStateEnum.READY
    assert await _post_handling_for(db_session, task.client_id) is None
    assert await _coordination_for(db_session, task.client_id) is None


@pytest.mark.integration
async def test_task_stays_open_while_another_step_is_unfinished(db_session, monkeypatch):
    """Completing one of two steps must not flip the task or create anything early."""
    _patch_worker(monkeypatch, db_session)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_type=TaskTypeEnum.RETURN,
        return_source=TaskReturnSourceEnum.STORE_RETURN,
    )
    step = await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )
    await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )

    await module.handle_finalize_pending_step_completion(
        _payload(step=step, task=task, workspace_id=workspace.client_id, user_id=user.client_id),
        "exec_task_4",
    )

    await db_session.refresh(task)
    assert task.state == TaskStateEnum.WORKING
    assert await _post_handling_for(db_session, task.client_id) is None


@pytest.mark.integration
async def test_completion_is_recorded_on_the_step(db_session, monkeypatch):
    _patch_worker(monkeypatch, db_session)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        task_type=TaskTypeEnum.INTERNAL,
    )
    step = await _seed_working_step(
        db_session, workspace_id=workspace.client_id, task_id=task.client_id, user_id=user.client_id
    )

    await module.handle_finalize_pending_step_completion(
        _payload(step=step, task=task, workspace_id=workspace.client_id, user_id=user.client_id),
        "exec_task_5",
    )

    await db_session.refresh(step)
    assert step.state == TaskStepStateEnum.COMPLETED
    assert step.closed_at is not None
    latest = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == step.client_id,
            StepStateRecord.exited_at.is_(None),
        )
    )
    assert latest.state == TaskStepStateEnum.COMPLETED
