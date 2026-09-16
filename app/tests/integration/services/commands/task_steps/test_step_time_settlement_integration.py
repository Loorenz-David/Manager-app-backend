"""Settlement of a step's own time totals inside the transition transaction.

Covers HANDOFF_TO_BACKEND_step_time_settlement_window_20260916 acceptance criteria 1-8:
no read may observe a closed time-bearing record without also observing its contribution
in `step.total_working_seconds`.

Every assertion here is written to fail if `settle_closed_step_time` is removed from the
write path — the "not settled" value is stated explicitly wherever it is the discriminator.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.task_steps import _settle_step_time
from beyo_manager.services.commands.task_steps.transition_step_state import transition_step_state
from beyo_manager.services.commands.task_steps.transition_step_state_batch import (
    transition_step_state_batch,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import (
    load_live_worked_seconds,
)
from beyo_manager.services.tasks.analytics.process_step_transition import (
    handle_process_step_transition,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# --------------------------------------------------------------------------- seeding


async def _seed_base(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(name=f"settle-{suffix}")
    user = User(
        username=f"settle-{suffix}",
        email=f"settle-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING,
        created_by_id=user.client_id,
    )
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"settle-sec-{suffix}",
        created_by_id=user.client_id,
    )
    db_session.add_all([task, section])
    await db_session.flush()
    return workspace, user, task, section


async def _add_step(
    db_session, workspace, user, task, section, *, batchable: bool = False
) -> TaskStep:
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.PENDING,
        assigned_worker_id=user.client_id,
        allows_batch_working=batchable,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    return step


async def _add_record(
    db_session,
    workspace,
    user,
    step,
    *,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
) -> StepStateRecord:
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
    if exited_at is None:
        step.state = state
        step.latest_state_record_id = record.client_id
        await db_session.flush()
    return record


def _ctx(db_session, workspace, user, task, step, new_state, **extra) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": user.client_id,
            "role_name": "worker",
            "username": "settle-tester",
        },
        incoming_data={
            "task_id": task.client_id,
            "step_id": step.client_id,
            "new_state": new_state.value,
            **extra,
        },
        session=db_session,
    )


async def _worked_seconds(db_session, workspace, step) -> int:
    """Read through the shared basis all four item-economics surfaces use."""
    await db_session.refresh(step)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [step], datetime.now(timezone.utc)
    )
    return result[step.client_id]


def _payload_for(step, task, workspace, user, closing_record, *, closing_state, new_state):
    return asdict(
        StepTransitionPayload(
            step_id=step.client_id,
            task_id=task.client_id,
            workspace_id=workspace.client_id,
            closing_record_id=closing_record.client_id,
            closing_state=closing_state.value,
            new_state=new_state.value,
            performed_by_user_id=user.client_id,
            credited_user_id=user.client_id,
            assigned_worker_id=step.assigned_worker_id,
            working_section_id=step.working_section_id,
            working_section_name_snapshot=step.working_section_name_snapshot,
            entered_at=closing_record.entered_at.isoformat(),
            exited_at=closing_record.exited_at.isoformat(),
            step_task_id=task.client_id,
            closing_record_marked_wrong=closing_record.recorded_time_marked_wrong,
        )
    )


# ------------------------------------------------------- AC1 / AC7: the worked example


async def test_ac1_ac7_pause_publishes_the_just_closed_run_without_the_worker(db_session):
    """1430 settled + a 58 s run + pause reads 1488 on the first request after the commit.

    The analytics worker is never invoked. Before this change the read returned 1430.
    """
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)

    # A settled history of exactly 1430 s, established the way the worker would.
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=4000),
        exited_at=now - timedelta(seconds=2570),
    )
    await _settle_step_time.settle_step_time_totals(
        db_session, workspace.client_id, step.client_id, now
    )
    await db_session.flush()
    assert step.total_working_seconds == 1430, "fixture must start from the handoff's 1430"

    # The run the worker is about to pause.
    open_record = await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=58),
        exited_at=None,
    )

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
    )

    await db_session.refresh(open_record)
    run_seconds = round((open_record.exited_at - open_record.entered_at).total_seconds())
    assert run_seconds == 58, f"scenario drifted off the worked example: {run_seconds}s"

    worked = await _worked_seconds(db_session, workspace, step)
    assert worked == 1488, f"expected 1430 + 58; 1430 means the run was never settled (got {worked})"


async def test_ac8_two_reads_with_no_work_between_them_agree(db_session):
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=300),
        exited_at=None,
    )
    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
    )

    first = await _worked_seconds(db_session, workspace, step)
    second = await _worked_seconds(db_session, workspace, step)
    assert first == second
    assert first >= 300, "the paused run must be in the settled total, not pending"


# --------------------------------------------- AC2: the surfaces sharing the basis


async def test_ac2_production_time_and_budget_signals_see_the_settled_run(db_session):
    """The two named surfaces must not lose the run at the moment it is paused.

    Each is read twice: once while the run is open (live share) and once immediately after
    the pause commits, with the analytics worker stopped. The figure may not go backwards —
    an unsettled close is exactly what made it drop before.
    """
    from tests.integration.services.queries.item_economics.test_budget_allocations_query import (
        _seed as _seed_economics,
    )
    from beyo_manager.services.queries.item_economics.get_task_production_time import (
        get_task_production_time,
    )
    from beyo_manager.services.queries.item_economics.get_task_budget_signals import (
        get_task_budget_signals,
    )

    values = await _seed_economics(db_session)
    workspace, user, _section, task = values[0], values[1], values[2], values[3]
    step = values[11][1]  # the PENDING "live" step, settled at 0

    now = datetime.now(timezone.utc)
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=120),
        exited_at=None,
    )

    def _production_ctx():
        return ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
                "role_name": "manager",
            },
            incoming_data={"task_client_id": task.client_id},
            query_params={},
            session=db_session,
            now=datetime.now(timezone.utc),
        )

    def _signals_ctx():
        return ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
                "role_name": "manager",
            },
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=datetime.now(timezone.utc),
        )

    def _signal_seconds(payload) -> int:
        row = next(
            r for r in payload["budget_signals"] if r["task_id"] == task.client_id
        )
        return int(row["actual_worked_seconds"] or 0)

    production_open = await get_task_production_time(_production_ctx())
    signals_open = _signal_seconds(await get_task_budget_signals(_signals_ctx()))
    open_seconds = int(production_open["budget"]["actual_worker_seconds"] or 0)
    assert open_seconds >= 120, "fixture never accrued the live run"
    assert signals_open >= 120

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
    )
    await db_session.flush()

    production_paused = await get_task_production_time(_production_ctx())
    signals_paused = _signal_seconds(await get_task_budget_signals(_signals_ctx()))
    paused_seconds = int(production_paused["budget"]["actual_worker_seconds"] or 0)

    assert paused_seconds >= open_seconds, (
        f"production-time dropped from {open_seconds}s to {paused_seconds}s across the pause "
        "— the closed run was not settled"
    )
    assert signals_paused >= signals_open, (
        f"budget-signals dropped from {signals_open}s to {signals_paused}s across the pause"
    )


# ------------------------------------ AC3 / AC4: the worker agrees, and replay is inert


async def test_ac3_ac4_worker_recompute_and_its_replay_change_nothing(db_session):
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=900),
        exited_at=now - timedelta(seconds=600),
    )
    open_record = await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=200),
        exited_at=None,
    )

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
    )
    await db_session.refresh(open_record)
    payload = _payload_for(
        step, task, workspace, user, open_record,
        closing_state=TaskStepStateEnum.WORKING,
        new_state=TaskStepStateEnum.PAUSED,
    )
    settled_by_request = await _worked_seconds(db_session, workspace, step)
    await db_session.commit()

    # AC3 — the worker's own recompute agrees with what the request already published.
    await handle_process_step_transition(payload, "settle-ac3")
    after_worker = await _worked_seconds(db_session, workspace, step)
    assert after_worker == settled_by_request

    # AC4 — replaying the same payload is still inert.
    await handle_process_step_transition(payload, "settle-ac3-replay")
    after_replay = await _worked_seconds(db_session, workspace, step)
    assert after_replay == settled_by_request


# ------------------------------------------------- AC5: concurrency averaging preserved


async def test_ac5_settled_value_is_concurrency_averaged_not_wall_clock(db_session):
    """Two batchable steps open together for 600 s: pausing one settles 300 s, not 600 s."""
    workspace, user, task, section = await _seed_base(db_session)
    step_a = await _add_step(db_session, workspace, user, task, section, batchable=True)
    step_b = await _add_step(db_session, workspace, user, task, section, batchable=True)
    now = datetime.now(timezone.utc)
    started = now - timedelta(seconds=600)

    record_a = await _add_record(
        db_session, workspace, user, step_a,
        state=TaskStepStateEnum.WORKING, entered_at=started, exited_at=None,
    )
    await _add_record(
        db_session, workspace, user, step_b,
        state=TaskStepStateEnum.WORKING, entered_at=started, exited_at=None,
    )

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step_a, TaskStepStateEnum.PAUSED)
    )
    await db_session.refresh(record_a)
    real_seconds = (record_a.exited_at - record_a.entered_at).total_seconds()

    await db_session.refresh(step_a)
    settled = step_a.total_working_seconds
    assert settled == pytest.approx(real_seconds / 2, abs=2), (
        f"expected the halved share ~{real_seconds / 2:.0f}s, got {settled}s "
        "(the full duration would mean averaging was bypassed)"
    )

    # And the worker lands on the same halved figure.
    payload = _payload_for(
        step_a, task, workspace, user, record_a,
        closing_state=TaskStepStateEnum.WORKING,
        new_state=TaskStepStateEnum.PAUSED,
    )
    await db_session.commit()
    await handle_process_step_transition(payload, "settle-ac5")
    await db_session.refresh(step_a)
    assert step_a.total_working_seconds == settled


# ------------------- AC6: completion, the auto-paused sibling, and batch transitions


async def test_ac6_completion_settles_the_closing_run(db_session):
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=450),
        exited_at=None,
    )
    result = await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.COMPLETED)
    )
    worked = await _worked_seconds(db_session, workspace, step)
    assert worked >= 450, f"a completed step published {worked}s for a 450s run"
    assert result["total_working_seconds"] == worked


async def test_ac6_auto_paused_conflicting_step_is_settled_too(db_session):
    """Starting step B auto-pauses step A; A's closed run must be settled in the same commit."""
    workspace, user, task, section = await _seed_base(db_session)
    step_a = await _add_step(db_session, workspace, user, task, section)
    step_b = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)

    await _add_record(
        db_session, workspace, user, step_a,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=360),
        exited_at=None,
    )
    await _add_record(
        db_session, workspace, user, step_b,
        state=TaskStepStateEnum.PENDING,
        entered_at=now - timedelta(seconds=10),
        exited_at=None,
    )

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step_b, TaskStepStateEnum.WORKING)
    )

    await db_session.refresh(step_a)
    assert step_a.state == TaskStepStateEnum.PAUSED, "fixture did not exercise the auto-pause"
    worked_a = await _worked_seconds(db_session, workspace, step_a)
    assert worked_a >= 360, (
        f"the auto-paused step published {worked_a}s for a 360s run — 0 means it was left unsettled"
    )


async def test_ac6_batch_transition_settles_every_step(db_session):
    workspace, user, task, section = await _seed_base(db_session)
    steps = [
        await _add_step(db_session, workspace, user, task, section, batchable=True)
        for _ in range(3)
    ]
    now = datetime.now(timezone.utc)
    for step in steps:
        await _add_record(
            db_session, workspace, user, step,
            state=TaskStepStateEnum.WORKING,
            entered_at=now - timedelta(seconds=300),
            exited_at=None,
        )

    result = await transition_step_state_batch(
        ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
                "role_name": "worker",
                "username": "settle-tester",
            },
            incoming_data={
                "items": [
                    {"task_id": task.client_id, "step_id": s.client_id} for s in steps
                ],
                "new_state": TaskStepStateEnum.PAUSED.value,
                "pause_reason_id": None,
                "description": None,
            },
            session=db_session,
        )
    )

    # Three concurrent batchable steps share the wall clock, so each settles ~100s.
    for step in steps:
        worked = await _worked_seconds(db_session, workspace, step)
        assert worked == pytest.approx(100, abs=3), (
            f"batched step published {worked}s; 0 would mean it was left unsettled"
        )
    for item in result["items"]:
        assert item["total_working_seconds"] > 0


async def test_ac6_clock_out_settles_the_step_it_force_pauses(db_session):
    """Clock-out reaches the shared core, so its forced pause settles like any other close.

    This is the open question the handoff raised: the clock-out path does not close records
    by a private route, it hands each one to `_apply_step_transition`.
    """
    from beyo_manager.services.commands.users._clock_worker_shift import (
        clock_in_shift_for_user,
        clock_out_shift_for_user,
    )

    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    clock_in = now - timedelta(seconds=1200)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, user.client_id, clock_in, user.client_id
    )
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=600),
        exited_at=None,
    )

    paused_ids = await clock_out_shift_for_user(
        db_session, workspace.client_id, user.client_id, now, changed_by_id=user.client_id
    )
    assert step.client_id in paused_ids, "fixture did not exercise the clock-out force-pause"

    worked = await _worked_seconds(db_session, workspace, step)
    assert worked == pytest.approx(600, abs=2), (
        f"clock-out published {worked}s for a 600s run — 0 means it was left unsettled"
    )


# ----------------------------------------------------------- gate and failure policy


async def test_starting_work_pays_no_settlement(db_session, monkeypatch):
    """PENDING closes no time-bearing record, so the sweep must not run at all."""
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.PENDING,
        entered_at=now - timedelta(seconds=30),
        exited_at=None,
    )

    calls = []
    real = _settle_step_time.settle_step_time_totals

    async def spy(*args, **kwargs):
        calls.append(args)
        return await real(*args, **kwargs)

    monkeypatch.setattr(_settle_step_time, "settle_step_time_totals", spy)

    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.WORKING)
    )
    assert calls == [], "a PENDING close must not pay for the concurrency sweep"

    # The other half of the gate: pausing the run this just started MUST settle. Without
    # this leg the test would still pass with settlement removed from the write path.
    await transition_step_state(
        _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
    )
    assert len(calls) == 1, "closing the WORKING run must settle the step"


async def test_failed_settlement_fails_the_transition(db_session, monkeypatch):
    """Stated policy: settlement failure rolls the transition back, it does not commit half."""
    workspace, user, task, section = await _seed_base(db_session)
    step = await _add_step(db_session, workspace, user, task, section)
    now = datetime.now(timezone.utc)
    record = await _add_record(
        db_session, workspace, user, step,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(seconds=120),
        exited_at=None,
    )

    async def boom(*args, **kwargs):
        raise RuntimeError("settlement exploded")

    monkeypatch.setattr(_settle_step_time, "settle_step_time_totals", boom)

    with pytest.raises(RuntimeError, match="settlement exploded"):
        await transition_step_state(
            _ctx(db_session, workspace, user, task, step, TaskStepStateEnum.PAUSED)
        )

    await db_session.rollback()
    surviving = await db_session.scalar(
        select(StepStateRecord).where(StepStateRecord.client_id == record.client_id)
    )
    assert surviving is None or surviving.exited_at is None, (
        "the record close must not survive a failed settlement"
    )
