"""Integration coverage for `force_task_ready`.

The claims worth pinning are the ones that motivated the design: the forced closes land
on SKIPPED (never COMPLETED, so administrative closure stays distinguishable from real
throughput in analytics), the task reaches READY through `maybe_evaluate_task_ready`
rather than a direct column write (so the READY side effects still run), a stepless task
can be forced at all, and the accrued time on an interrupted step is credited to the
worker who accrued it rather than to the manager pressing the button.
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
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.force_task_ready import force_task_ready
from beyo_manager.services.context import ServiceContext


_scalar_id_counter = itertools.count(1)


def _ctx(db_session, *, workspace_id, user_id, task_id, reason="customer withdrew", mark_inaccurate=True):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={
            "client_id": task_id,
            "reason": reason,
            "mark_inaccurate": mark_inaccurate,
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
    credited_user_id=None,
    entered_at=None,
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
        allows_batch_working=False,
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
            entered_at=entered_at or datetime.now(timezone.utc),
            created_by_id=user_id,
            credited_user_id=credited_user_id,
        )
        db_session.add(record)
        await db_session.flush()
        step.latest_state_record_id = record.client_id
        await db_session.flush()
    return step


def _patch_side_effects(monkeypatch, *, capture: list | None = None, outbox: list | None = None):
    async def _capture_instant_task(**kwargs):
        if outbox is not None:
            outbox.append(kwargs)
        return None

    async def _noop_targets(*_args, **_kwargs):
        return []

    async def _dispatch(events):
        if capture is not None:
            capture.append(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps._step_transition_core.create_instant_task",
        _capture_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps._step_transition_core.resolve_task_step_notification_targets",
        _noop_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.force_task_ready.create_instant_task",
        _capture_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.force_task_ready.resolve_task_notification_targets",
        _noop_targets,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.force_task_ready.event_bus.dispatch",
        _dispatch,
    )


async def _reload_step(db_session, step_id) -> TaskStep:
    return await db_session.scalar(select(TaskStep).where(TaskStep.client_id == step_id))


async def _latest_record(db_session, step_id) -> StepStateRecord:
    return await db_session.scalar(
        select(StepStateRecord)
        .where(StepStateRecord.step_id == step_id, StepStateRecord.exited_at.is_(None))
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "open_state",
    [TaskStepStateEnum.PENDING, TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED],
)
async def test_open_steps_are_skipped_and_task_becomes_ready(db_session, monkeypatch, open_state):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    steps = [
        await _seed_step(
            db_session,
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            user_id=user.client_id,
            state=open_state,
        )
        for _ in range(3)
    ]

    result = await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    assert result["state"] == TaskStateEnum.READY.value
    assert set(result["skipped_step_ids"]) == {s.client_id for s in steps}
    assert task.state == TaskStateEnum.READY
    for s in steps:
        reloaded = await _reload_step(db_session, s.client_id)
        assert reloaded.state == TaskStepStateEnum.SKIPPED
        assert reloaded.closed_at is not None


@pytest.mark.integration
async def test_never_writes_completed(db_session, monkeypatch):
    """The whole point of choosing SKIPPED: a forced close must not read as throughput."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.WORKING,
    )

    await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    records = (
        await db_session.execute(
            select(StepStateRecord).where(StepStateRecord.step_id == step.client_id)
        )
    ).scalars().all()
    assert TaskStepStateEnum.COMPLETED not in {r.state for r in records}


@pytest.mark.integration
async def test_synthetic_records_are_typed_and_carry_the_reason(db_session, monkeypatch):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.PENDING,
    )

    await force_task_ready(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task.client_id,
            reason="warehouse closed early",
        )
    )

    record = await _latest_record(db_session, step.client_id)
    assert record.state == TaskStepStateEnum.SKIPPED
    assert record.transition_reason == TransitionReasonEnum.FORCED_READY.value
    assert record.description == "warehouse closed early"
    # A typed system transition must not borrow a workspace catalog row.
    assert record.pause_reason_id is None


@pytest.mark.integration
async def test_stepless_task_can_be_forced_ready(db_session, monkeypatch):
    """The case organic readiness can never reach: `maybe_evaluate_task_ready` rejects a
    task with no steps unless `allow_stepless` is passed, and only this command passes it."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.PENDING,
    )

    result = await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    assert result["skipped_step_ids"] == []
    assert task.state == TaskStateEnum.READY


@pytest.mark.integration
async def test_already_terminal_steps_are_left_alone(db_session, monkeypatch):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    done = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.COMPLETED,
    )
    open_step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.PENDING,
    )

    result = await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    assert result["skipped_step_ids"] == [open_step.client_id]
    # A genuinely completed step keeps its COMPLETED state and its credit.
    assert (await _reload_step(db_session, done.client_id)).state == TaskStepStateEnum.COMPLETED


@pytest.mark.integration
async def test_interrupted_time_is_credited_to_the_worker_not_the_forcer(db_session, monkeypatch):
    """A WORKING step carries real accrued seconds. The analytics worker recomputes them
    against `credited_user_id`, so crediting the manager would move another person's
    hours onto them."""
    outbox: list = []
    _patch_side_effects(monkeypatch, outbox=outbox)
    workspace, manager = await _seed_workspace_user(db_session)
    worker = User(
        client_id=f"usr_{uuid4().hex[:8]}",
        username=f"worker_{uuid4().hex[:6]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password="secret",
    )
    db_session.add(worker)
    await db_session.flush()

    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=manager.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=worker.client_id,
        state=TaskStepStateEnum.WORKING,
        credited_user_id=worker.client_id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=manager.client_id, task_id=task.client_id)
    )

    payloads = [kw["payload"] for kw in outbox if kw["payload"].get("step_id") == step.client_id]
    assert payloads, "expected a PROCESS_STEP_TRANSITION payload for the forced step"
    assert payloads[0]["credited_user_id"] == worker.client_id
    assert payloads[0]["performed_by_user_id"] == manager.client_id


@pytest.mark.integration
async def test_interrupted_time_is_flagged_inaccurate(db_session, monkeypatch):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    reloaded = await _reload_step(db_session, step.client_id)
    assert reloaded.recorded_time_marked_wrong is True
    assert reloaded.taken_from_average is True


@pytest.mark.integration
async def test_pending_step_carries_no_time_so_nothing_is_flagged(db_session, monkeypatch):
    """A PENDING close is not time-bearing — flagging it would claim a recorded time that
    never existed."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.PENDING,
    )

    await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    reloaded = await _reload_step(db_session, step.client_id)
    assert reloaded.recorded_time_marked_wrong is False


@pytest.mark.integration
@pytest.mark.parametrize(
    "state", [TaskStateEnum.RESOLVED, TaskStateEnum.CANCELLED, TaskStateEnum.FAILED]
)
async def test_terminal_task_is_rejected(db_session, monkeypatch, state):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session, workspace_id=workspace.client_id, user_id=user.client_id, state=state
    )

    with pytest.raises(ConflictError):
        await force_task_ready(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
        )


@pytest.mark.integration
async def test_already_ready_task_is_rejected(db_session, monkeypatch):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.READY,
    )

    with pytest.raises(ConflictError):
        await force_task_ready(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
        )


@pytest.mark.integration
async def test_step_without_an_open_record_rejects_the_whole_call(db_session, monkeypatch):
    """All-or-nothing: a task must not be left half-skipped."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    healthy = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.PENDING,
    )
    await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.PENDING,
        with_open_record=False,
    )

    with pytest.raises(ValidationError):
        await force_task_ready(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
        )

    assert (await _reload_step(db_session, healthy.client_id)).state == TaskStepStateEnum.PENDING
    assert task.state != TaskStateEnum.READY


@pytest.mark.integration
async def test_blocked_step_is_forceable(db_session, monkeypatch):
    """`_ALLOWED_TRANSITIONS` leaves BLOCKED with no exit at all; the private force map
    gives it one, so a blocked step cannot make a task permanently unforceable."""
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    step = await _seed_step(
        db_session,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        user_id=user.client_id,
        state=TaskStepStateEnum.BLOCKED,
    )

    await force_task_ready(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    )

    assert (await _reload_step(db_session, step.client_id)).state == TaskStepStateEnum.SKIPPED
    assert task.state == TaskStateEnum.READY


@pytest.mark.integration
async def test_blank_reason_is_rejected(db_session, monkeypatch):
    _patch_side_effects(monkeypatch)
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)

    with pytest.raises(ValidationError):
        await force_task_ready(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                task_id=task.client_id,
                reason="   ",
            )
        )
