"""Integration coverage for the `tasks.completed_at` lifecycle.

The column holds the task's *current* completion: stamped when it enters READY or RESOLVED,
cleared when a reopen sends it back to WORKING. What is worth pinning is the asymmetry —
that the stamp happens at the central READY evaluation rather than at its call sites, that a
reopen really clears it (so a reopened task cannot linger in a "recently completed" list),
that a second completion overwrites rather than preserving the first, and that the terminal
FAILED/CANCELLED commands deliberately leave it alone.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks._task_state_transitions import (
    maybe_evaluate_task_ready,
    maybe_reopen_task_to_working,
)
from beyo_manager.services.commands.tasks.cancel_task import cancel_task
from beyo_manager.services.commands.tasks.fail_task import fail_task
from beyo_manager.services.commands.tasks.resolve_task import resolve_task
from beyo_manager.services.context import ServiceContext


_scalar_id_counter = itertools.count(1)


def _ctx(db_session, *, workspace_id, user_id, task_id) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={"client_id": task_id, "reason": "because"},
        query_params={},
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


async def _seed_task(db_session, *, workspace_id, user_id, state, completed_at=None) -> Task:
    task = Task(
        client_id=f"tsk_{uuid4().hex[:8]}",
        workspace_id=workspace_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.INTERNAL,
        state=state,
        completed_at=completed_at,
        created_by_id=user_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _seed_step(db_session, *, workspace_id, task_id, user_id, state) -> TaskStep:
    suffix = uuid4().hex[:8]
    section = WorkingSection(
        client_id=f"wsec_{suffix}", workspace_id=workspace_id, name=f"Section {suffix}"
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        client_id=f"tsp_{suffix}",
        workspace_id=workspace_id,
        task_id=task_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=f"Section {suffix}",
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    return step


def _patch_side_effects(monkeypatch) -> None:
    """Silence the notification/execution fan-out so the state write is what is under test."""

    async def _noop_instant_task(**_kwargs):
        return None

    async def _noop_targets(*_args, **_kwargs):
        return []

    async def _noop_dispatch(_events):
        return None

    async def _noop_reconcile(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks._task_state_transitions.create_instant_task",
        _noop_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks._task_state_transitions.reconcile_task_side_effects",
        _noop_reconcile,
    )
    for module in ("resolve_task", "fail_task", "cancel_task"):
        monkeypatch.setattr(
            f"beyo_manager.services.commands.tasks.{module}.resolve_task_notification_targets",
            _noop_targets,
        )
        monkeypatch.setattr(
            f"beyo_manager.services.commands.tasks.{module}.event_bus.dispatch",
            _noop_dispatch,
        )


async def _reload(db_session, task_id) -> Task:
    return await db_session.scalar(select(Task).where(Task.client_id == task_id))


@pytest.mark.integration
async def test_central_ready_evaluation_stamps_completed_at(db_session, monkeypatch) -> None:
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.WORKING,
    )
    await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.COMPLETED,
    )
    now = datetime.now(timezone.utc)

    changed = await maybe_evaluate_task_ready(
        db_session,
        task,
        workspace_id=workspace.client_id,
        now=now,
        updated_by_id=user.client_id,
    )

    assert changed is True
    assert task.state == TaskStateEnum.READY
    assert task.completed_at == now


@pytest.mark.integration
async def test_ready_evaluation_leaves_completed_at_alone_when_work_is_unfinished(
    db_session, monkeypatch
) -> None:
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.WORKING,
    )
    await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.WORKING,
    )

    changed = await maybe_evaluate_task_ready(
        db_session,
        task,
        workspace_id=workspace.client_id,
        now=datetime.now(timezone.utc),
        updated_by_id=user.client_id,
    )

    assert changed is False
    assert task.state == TaskStateEnum.WORKING
    assert task.completed_at is None


@pytest.mark.integration
async def test_reopen_clears_completed_at(db_session, monkeypatch) -> None:
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.READY,
        completed_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    changed = await maybe_reopen_task_to_working(
        db_session,
        task,
        workspace_id=workspace.client_id,
        now=datetime.now(timezone.utc),
        updated_by_id=user.client_id,
    )

    assert changed is True
    assert task.state == TaskStateEnum.WORKING
    assert task.completed_at is None
    assert (await _reload(db_session, task.client_id)).completed_at is None


@pytest.mark.integration
async def test_second_completion_overwrites_the_first(db_session, monkeypatch) -> None:
    """A task can enter READY more than once. "Most recently completed" means the latest
    stamp wins, not the earliest."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.WORKING,
    )
    await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.COMPLETED,
    )

    first = datetime.now(timezone.utc) - timedelta(hours=3)
    await maybe_evaluate_task_ready(
        db_session, task, workspace_id=workspace.client_id, now=first, updated_by_id=user.client_id
    )
    assert task.completed_at == first

    await maybe_reopen_task_to_working(
        db_session,
        task,
        workspace_id=workspace.client_id,
        now=datetime.now(timezone.utc) - timedelta(hours=2),
        updated_by_id=user.client_id,
    )
    assert task.completed_at is None

    second = datetime.now(timezone.utc)
    await maybe_evaluate_task_ready(
        db_session, task, workspace_id=workspace.client_id, now=second, updated_by_id=user.client_id
    )

    assert task.completed_at == second
    assert task.completed_at > first


@pytest.mark.integration
async def test_resolve_task_stamps_completed_at_alongside_closed_at(
    db_session, monkeypatch
) -> None:
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.READY,
    )

    await resolve_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
        )
    )

    reloaded = await _reload(db_session, task.client_id)
    assert reloaded.state == TaskStateEnum.RESOLVED
    assert reloaded.completed_at is not None
    assert reloaded.completed_at == reloaded.closed_at


@pytest.mark.integration
@pytest.mark.parametrize(
    "command, expected_state",
    [(fail_task, TaskStateEnum.FAILED), (cancel_task, TaskStateEnum.CANCELLED)],
)
async def test_terminal_failure_commands_do_not_stamp_completed_at(
    db_session, monkeypatch, command, expected_state
) -> None:
    """Terminal is not completed: closed_at already carries "left the board"."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.WORKING,
    )

    await command(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
        )
    )

    reloaded = await _reload(db_session, task.client_id)
    assert reloaded.state == expected_state
    assert reloaded.closed_at is not None
    assert reloaded.completed_at is None
