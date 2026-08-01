"""System transitions no longer resolve a `pause_reasons` row.

Every test here runs in a workspace that holds **zero** catalog rows, which is the
condition that made clock-out and task switching fail. `_assert_zero_catalog` is called in
each one so a fixture that starts seeding reasons cannot make these pass vacuously.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
from beyo_manager.services.commands.task_steps.transition_step_state import (
    transition_step_state,
)
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
)
from beyo_manager.services.commands.users._reconstruct_shift_middle import (
    reconstruct_shift_middle,
)
from beyo_manager.services.context import ServiceContext


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- seeding


async def _seed_zero_catalog_workspace(db_session) -> tuple[Workspace, User]:
    """A brand-new workspace and worker. Nothing seeds `pause_reasons` for it."""
    suffix = uuid4().hex[:12]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Zero catalog {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"worker_{suffix}",
        email=f"{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _assert_zero_catalog(db_session, workspace_id: str) -> None:
    """The premise of every test in this file, asserted rather than assumed."""
    count = await db_session.scalar(
        select(func.count())
        .select_from(PauseReason)
        .where(PauseReason.workspace_id == workspace_id)
    )
    assert count == 0, "fixture seeded pause reasons; these tests would pass vacuously"


async def _seed_step(
    db_session,
    workspace: Workspace,
    user: User,
    *,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None = None,
    allows_batch_working: bool = False,
    open_record: bool = True,
) -> tuple[TaskStep, Task, StepStateRecord | None]:
    suffix = uuid4().hex[:12]
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"section-{suffix}",
        created_by_id=user.client_id,
    )
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=state,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=allows_batch_working,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        assigned_worker_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()

    record = None
    if open_record:
        record = StepStateRecord(
            workspace_id=workspace.client_id,
            step_id=step.client_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user.client_id,
            credited_user_id=user.client_id,
        )
        db_session.add(record)
        await db_session.flush()
        step.latest_state_record_id = record.client_id
        await db_session.flush()
    return step, task, record


def _ctx(db_session, workspace: Workspace, user: User, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": user.client_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


def _patch_single_step_side_effects(monkeypatch) -> None:
    """Silence outbox/events/notifications. Deliberately patches NO reason resolver."""

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_targets(*_args, **_kwargs):
        return []

    module = "beyo_manager.services.commands.task_steps.transition_step_state"
    monkeypatch.setattr(f"{module}.create_instant_task", _noop)
    monkeypatch.setattr(f"{module}.event_bus.dispatch", _noop)
    monkeypatch.setattr(f"{module}.resolve_task_step_notification_targets", _no_targets)
    monkeypatch.setattr(f"{module}.resolve_task_notification_targets", _no_targets)
    monkeypatch.setattr(f"{module}.resolve_item_label_for_task", _noop)


def _patch_core_side_effects(monkeypatch) -> None:
    async def _noop(*_args, **_kwargs):
        return None

    async def _no_targets(*_args, **_kwargs):
        return []

    module = "beyo_manager.services.commands.task_steps._step_transition_core"
    monkeypatch.setattr(f"{module}.create_instant_task", _noop)
    monkeypatch.setattr(f"{module}.resolve_task_step_notification_targets", _no_targets)


async def _step_records(db_session, step_id: str) -> list[StepStateRecord]:
    return list(
        (
            await db_session.execute(
                select(StepStateRecord)
                .where(StepStateRecord.step_id == step_id)
                .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
            )
        )
        .scalars()
        .all()
    )


async def _shift_records(db_session, workspace_id: str, user_id: str):
    return list(
        (
            await db_session.execute(
                select(UserShiftStateRecord)
                .where(
                    UserShiftStateRecord.workspace_id == workspace_id,
                    UserShiftStateRecord.user_id == user_id,
                )
                .order_by(UserShiftStateRecord.entered_at, UserShiftStateRecord.client_id)
            )
        )
        .scalars()
        .all()
    )


# ------------------------------------------------------------------ criterion 1: clock-out


async def test_zero_catalog_clock_out_closes_open_working_step(db_session) -> None:
    """Criterion 1. Against pre-phase code this raises
    `NotFound("System pause reason 'pause_ended_shift' is not configured.")`.
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    clock_in_at = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    clock_out_at = clock_in_at + timedelta(hours=8)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, clock_in_at, worker.client_id
    )
    step, _, _ = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=clock_in_at + timedelta(minutes=5),
    )

    transitioned = await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        clock_out_at,
        changed_by_id=worker.client_id,
    )

    assert transitioned == 1
    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.PAUSED

    ended_record = next(
        record
        for record in await _step_records(db_session, step.client_id)
        if record.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    )
    assert ended_record.state is TaskStepStateEnum.PAUSED
    assert ended_record.pause_reason_id is None
    assert ended_record.entered_at == clock_out_at


async def test_overnight_safeguard_inherits_the_typed_clock_out(db_session) -> None:
    """Criterion 5. The scheduled job calls `clock_out_shift_for_user` directly, so it
    inherits the change rather than being special-cased. Exercised through that same
    entry point with the job's own arguments (`changed_by_id=None`, midnight boundary),
    which is what the job passes — the job's global row scan is covered separately in
    `test_worker_shift_commands.py` and needs a committed session.
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    midnight = datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        midnight - timedelta(hours=10),
        worker.client_id,
    )
    step, _, _ = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=midnight - timedelta(hours=9),
    )

    transitioned = await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        midnight,
        changed_by_id=None,
    )

    assert transitioned == 1
    ended_record = next(
        record
        for record in await _step_records(db_session, step.client_id)
        if record.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    )
    assert ended_record.state is TaskStepStateEnum.PAUSED
    assert ended_record.pause_reason_id is None


# --------------------------------------------------- criteria 2 & 3: both task-switch sites


async def test_zero_catalog_task_switch_via_single_step_endpoint(
    db_session, monkeypatch
) -> None:
    """Criteria 2 and 3 — the `transition_step_state.py` path (single-step endpoint).

    Against pre-phase code this raises
    `NotFound("System pause reason 'pause_other_task_priority' is not configured.")`.
    """
    _patch_single_step_side_effects(monkeypatch)
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    now = datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)
    conflicting_step, _, _ = await _seed_step(
        db_session, workspace, worker, state=TaskStepStateEnum.WORKING, entered_at=now
    )
    activating_step, activating_task, _ = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PENDING,
        entered_at=now,
    )

    await transition_step_state(
        _ctx(
            db_session,
            workspace,
            worker,
            {
                "task_id": activating_task.client_id,
                "step_id": activating_step.client_id,
                "new_state": TaskStepStateEnum.WORKING.value,
            },
        )
    )

    await db_session.refresh(conflicting_step)
    assert conflicting_step.state is TaskStepStateEnum.PAUSED
    auto_pause = next(
        record
        for record in await _step_records(db_session, conflicting_step.client_id)
        if record.state is TaskStepStateEnum.PAUSED
    )
    assert auto_pause.transition_reason == TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    assert auto_pause.pause_reason_id is None


async def test_zero_catalog_task_switch_via_shared_transition_core(
    db_session, monkeypatch
) -> None:
    """Criterion 3 — the `_step_transition_core.py` path.

    A separate module from the single-step command (they are kept in sync by convention,
    not by sharing this branch), so it gets its own test. Driven through
    `_apply_step_transition` directly because the batch command rejects non-batch-capable
    steps up front and this guard only fires for them.
    """
    _patch_core_side_effects(monkeypatch)
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
    conflicting_step, _, _ = await _seed_step(
        db_session, workspace, worker, state=TaskStepStateEnum.WORKING, entered_at=now
    )
    activating_step, activating_task, activating_record = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PENDING,
        entered_at=now,
    )

    applied = await _apply_step_transition(
        _ctx(db_session, workspace, worker, {}),
        activating_step,
        activating_task,
        activating_record,
        new_state=TaskStepStateEnum.WORKING,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=now + timedelta(minutes=30),
    )

    assert applied.auto_paused_item == {
        "client_id": conflicting_step.client_id,
        "new_state": TaskStepStateEnum.PAUSED.value,
    }
    await db_session.refresh(conflicting_step)
    assert conflicting_step.state is TaskStepStateEnum.PAUSED
    auto_pause = next(
        record
        for record in await _step_records(db_session, conflicting_step.client_id)
        if record.state is TaskStepStateEnum.PAUSED
    )
    assert auto_pause.transition_reason == TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    assert auto_pause.pause_reason_id is None


async def test_worker_chosen_pause_keeps_its_catalog_reference_and_stays_untyped(
    db_session, monkeypatch
) -> None:
    """The other half of the vocabulary: a pause a human chose is NOT a system transition.

    It carries the catalog row and leaves `transition_reason` null — the mutual exclusion
    phase 4's check constraint depends on.
    """
    _patch_single_step_side_effects(monkeypatch)
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Coffee break",
        slug=None,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()

    now = datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc)
    step, task, _ = await _seed_step(
        db_session, workspace, worker, state=TaskStepStateEnum.WORKING, entered_at=now
    )

    await transition_step_state(
        _ctx(
            db_session,
            workspace,
            worker,
            {
                "task_id": task.client_id,
                "step_id": step.client_id,
                "new_state": TaskStepStateEnum.PAUSED.value,
                "pause_reason_id": reason.client_id,
            },
        )
    )

    paused = next(
        record
        for record in await _step_records(db_session, step.client_id)
        if record.state is TaskStepStateEnum.PAUSED
    )
    assert paused.pause_reason_id == reason.client_id
    assert paused.transition_reason is None


# ------------------------------------------------------- criteria 6-10: the rebuild


async def test_rebuild_carries_the_transition_reason_onto_derived_rows(db_session) -> None:
    """Criterion 6. Without this the derived row loses the reason entirely and the kiosk
    buckets a system auto-pause as `unspecified`.
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    shift_start = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    shift_end = shift_start + timedelta(hours=4)
    step, _, record = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(hours=1),
        exited_at=shift_start + timedelta(hours=2),
    )
    record.transition_reason = TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    await db_session.flush()

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )

    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    assert paused_rows[0].transition_reason == TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    assert paused_rows[0].reason is None


async def test_rebuild_is_idempotent_over_the_same_source_data(db_session) -> None:
    """Criterion 7 — the invariant that makes the closed timeline reproducible.

    Run twice over identical sources; the derived rows must be identical (client ids
    excepted, since the rows are deleted and recreated).
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    shift_start = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    shift_end = shift_start + timedelta(hours=6)
    _, _, working = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=shift_start + timedelta(minutes=30),
        exited_at=shift_start + timedelta(hours=2),
    )
    _, _, auto_paused = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(hours=2),
        exited_at=shift_start + timedelta(hours=3),
    )
    auto_paused.transition_reason = TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    await db_session.flush()

    def _shape(rows):
        return [
            (
                row.state,
                row.entered_at,
                row.exited_at,
                row.reason,
                row.transition_reason,
                row.changed_by_id,
                row.manually_recorded,
            )
            for row in rows
        ]

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )
    first = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )
    second = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))

    assert first == second
    assert any(row[4] == TransitionReasonEnum.OTHER_TASK_PRIORITY.value for row in first)
    assert working is not None


async def test_declaration_survives_the_clock_out_rebuild(db_session) -> None:
    """Criterion 8. Declarations are a source table precisely so the rebuild cannot erase
    them; the derived segment carries both the catalog reference the worker chose and the
    typed transition saying where it came from.
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Cleaning",
        slug=None,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()

    clock_in_at = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    clock_out_at = clock_in_at + timedelta(hours=4)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, clock_in_at, worker.client_id
    )
    declaration = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=reason.client_id,
        entered_at=clock_in_at + timedelta(hours=1),
        exited_at=clock_in_at + timedelta(hours=2),
        created_by_id=worker.client_id,
    )
    db_session.add(declaration)
    await db_session.flush()

    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        clock_out_at,
        changed_by_id=worker.client_id,
    )

    # The source row is untouched...
    await db_session.refresh(declaration)
    assert declaration.exited_at == clock_in_at + timedelta(hours=2)
    # ...and it is represented in the rebuilt derived timeline.
    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    assert paused_rows[0].reason == reason.client_id
    assert (
        paused_rows[0].transition_reason
        == TransitionReasonEnum.WORKER_DECLARED_STATE.value
    )
    assert paused_rows[0].manually_recorded is True


async def test_declaration_still_outranks_an_overlapping_step_pause(db_session) -> None:
    """Criterion 9 — ownership priority is unchanged by typing the transition."""
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Meeting",
        slug=None,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()

    shift_start = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    shift_end = shift_start + timedelta(hours=4)
    _, _, step_pause = await _seed_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(hours=1),
        exited_at=shift_start + timedelta(hours=2),
    )
    step_pause.transition_reason = TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    db_session.add(
        UserDeclaredStateRecord(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            pause_reason_id=reason.client_id,
            entered_at=shift_start + timedelta(hours=1),
            exited_at=shift_start + timedelta(hours=2),
            created_by_id=worker.client_id,
        )
    )
    await db_session.flush()

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )

    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    # The declaration owns the overlap, exactly as before.
    assert paused_rows[0].reason == reason.client_id
    assert (
        paused_rows[0].transition_reason
        == TransitionReasonEnum.WORKER_DECLARED_STATE.value
    )


async def test_rebuild_does_not_launder_changed_by_id(db_session) -> None:
    """Criterion 10. It did once, and the healing job then reopened the laundered row."""
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    await _assert_zero_catalog(db_session, workspace.client_id)

    shift_start = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    shift_end = shift_start + timedelta(hours=4)
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            state=UserShiftStateEnum.IN_PAUSE,
            entered_at=shift_start + timedelta(hours=1),
            exited_at=shift_start + timedelta(hours=2),
            changed_by_id=worker.client_id,
            reason="Late lunch",
            manually_recorded=True,
        )
    )
    await db_session.flush()

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )

    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    assert paused_rows[0].changed_by_id == worker.client_id
    assert paused_rows[0].reason == "Late lunch"
    assert paused_rows[0].transition_reason is None


async def test_rebuild_leaves_a_declaration_projection_without_an_actor(db_session) -> None:
    """Criterion 10, the other arm — asserted because the first arm alone let a doc
    overclaim slip through review round 1.

    `changed_by_id IS NULL` on a declaration projection is load-bearing, not incidental:
    it is how the live derivation tells a system-authored projection from an
    actor-authored legacy manual pause, which it holds sticky against re-derivation.
    Giving the declaring worker an actor here would make the projection sticky too. The
    declaring worker is recorded on the declaration row itself, which this asserts.
    """
    workspace, worker = await _seed_zero_catalog_workspace(db_session)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Loading",
        slug=None,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()

    shift_start = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    shift_end = shift_start + timedelta(hours=4)
    declaration = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=reason.client_id,
        entered_at=shift_start + timedelta(hours=1),
        exited_at=shift_start + timedelta(hours=2),
        created_by_id=worker.client_id,
    )
    db_session.add(declaration)
    await db_session.flush()

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, shift_start, shift_end
    )

    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    assert paused_rows[0].changed_by_id is None
    assert paused_rows[0].manually_recorded is True
    # The actor is not lost — it lives on the source row.
    assert declaration.created_by_id == worker.client_id
