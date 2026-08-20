from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import load_live_worked_seconds
from beyo_manager.services.tasks.analytics.process_step_transition import _recompute_step_time_totals


UTC = timezone.utc


async def _seed_workspace(db_session):
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_live_{token}", name=f"Live {token}")
    user = User(
        client_id=f"usr_live_{token}",
        username=f"live_{token}",
        email=f"live_{token}@example.test",
        password="secret",
    )
    section = WorkingSection(
        client_id=f"wsec_live_{token}",
        workspace_id=workspace.client_id,
        name="Live section",
        order_list=1,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(section)
    await db_session.flush()
    task = await _add_task(db_session, workspace, user, token, 1)
    return workspace, user, section, task, token


async def _add_task(db_session, workspace, user, token: str, number: int) -> Task:
    task = Task(
        client_id=f"tsk_live_{token}_{number}",
        workspace_id=workspace.client_id,
        task_scalar_id=number,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _add_user(db_session, workspace, token: str, suffix: str) -> User:
    user = User(
        client_id=f"usr_live_{token}_{suffix}",
        username=f"live_{token}_{suffix}",
        email=f"live_{token}_{suffix}@example.test",
        password="secret",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _add_step_record(
    db_session,
    workspace,
    user,
    section,
    task,
    token: str,
    number: int,
    entered_at: datetime,
    *,
    exited_at: datetime | None = None,
    state: TaskStepStateEnum = TaskStepStateEnum.WORKING,
    allows_batch_working: bool = True,
    settled: int = 0,
    record_created_by_id: str | None = "__default__",
    credited_user_id: str | None = None,
    record_deleted: bool = False,
    step_deleted: bool = False,
    record_marked_wrong: bool = False,
    step_marked_wrong: bool = False,
    create_record: bool = True,
):
    step = TaskStep(
        client_id=f"tsp_live_{token}_{number}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        sequence_order=number,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=settled,
        allows_batch_working=allows_batch_working,
        recorded_time_marked_wrong=step_marked_wrong,
        is_deleted=step_deleted,
        created_at=entered_at,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = None
    if create_record:
        record = StepStateRecord(
            client_id=f"ssr_live_{token}_{number}",
            workspace_id=workspace.client_id,
            step_id=step.client_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user.client_id if record_created_by_id == "__default__" else record_created_by_id,
            credited_user_id=credited_user_id,
            recorded_time_marked_wrong=record_marked_wrong,
            is_deleted=record_deleted,
        )
        db_session.add(record)
        await db_session.flush()
        step.latest_state_record_id = record.client_id
        await db_session.flush()
    return step, record


def _ctx(db_session, workspace_id: str, user_id: str, now: datetime) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id},
        incoming_data={},
        query_params={},
        session=db_session,
        now=now,
    )


@pytest.mark.integration
async def test_c3_row_1_distinct_workers_are_not_divided_by_section_records(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    second_user = await _add_user(db_session, workspace, token, "second")
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    second, _ = await _add_step_record(
        db_session, workspace, second_user, section, task, token, 2, start,
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first, second], start + timedelta(minutes=30)
    )
    assert result == {first.client_id: 1800, second.client_id: 1800}


@pytest.mark.integration
async def test_c3_row_2_sweep_changes_divisor_mid_interval(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    second, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 2, start + timedelta(minutes=20)
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first, second], start + timedelta(minutes=30)
    )
    assert result == {first.client_id: 1500, second.client_id: 300}


@pytest.mark.integration
async def test_c3_row_3_cross_task_open_record_is_in_the_divisor(db_session):
    # D1: two overlapping 30-minute cross-task records yield 900 seconds each.
    workspace, user, section, task, token = await _seed_workspace(db_session)
    other_task = await _add_task(db_session, workspace, user, token, 2)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    await _add_step_record(db_session, workspace, user, section, other_task, token, 2, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first], start + timedelta(minutes=30)
    )
    assert result == {first.client_id: 900}


@pytest.mark.integration
async def test_c3_row_4_closed_overlap_shapes_the_open_record_share(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    await _add_step_record(
        db_session, workspace, user, section, task, token, 2, start,
        exited_at=start + timedelta(minutes=20),
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first], start + timedelta(minutes=30)
    )
    assert result == {first.client_id: 1200}


@pytest.mark.integration
async def test_c4_open_paused_record_has_no_live_term(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        state=TaskStepStateEnum.PAUSED,
    )
    assert await load_live_worked_seconds(db_session, workspace.client_id, [step], start + timedelta(minutes=10)) == {step.client_id: 0}


@pytest.mark.integration
async def test_c4_record_marked_wrong_has_no_live_term(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        record_marked_wrong=True,
    )
    assert await load_live_worked_seconds(db_session, workspace.client_id, [step], start + timedelta(minutes=10)) == {step.client_id: 0}


@pytest.mark.integration
async def test_c4_step_marked_wrong_drops_it_and_releases_sibling_share(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    marked, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        step_marked_wrong=True,
    )
    sibling, _ = await _add_step_record(db_session, workspace, user, section, task, token, 2, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [marked, sibling], start + timedelta(minutes=10)
    )
    assert result == {marked.client_id: 0, sibling.client_id: 600}


@pytest.mark.integration
async def test_c4_deleted_record_is_excluded_defensively(db_session):
    """No shipped command sets ``StepStateRecord.is_deleted = True``; the only hard ``DELETE`` is ``reset/phases/delete_step_state_records.py`` (whole workspace). This row is defense-in-depth (§3.1A D)."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        record_deleted=True,
    )
    assert await load_live_worked_seconds(db_session, workspace.client_id, [step], start + timedelta(minutes=10)) == {step.client_id: 0}


@pytest.mark.integration
async def test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped(db_session):
    """Missing attribution tests the ``if user_id is not None`` deletion; future-entry tests the both-args clock-read shape, per the review log's consumption entry."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    now = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    future, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, now)
    missing, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 2, now - timedelta(minutes=10),
        record_created_by_id=None,
    )
    assert await load_live_worked_seconds(db_session, workspace.client_id, [future, missing], now) == {
        future.client_id: 0,
        missing.client_id: 0,
    }


async def _close_at_t(db_session, workspace, user, section, task, step, record, token, t):
    ctx = _ctx(db_session, workspace.client_id, user.client_id, t)
    return await _apply_step_transition(
        ctx,
        step,
        task,
        record,
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=None,
        description=None,
        credited_user_id=user.client_id,
        now=t,
        transition_reason=None,
    )


@pytest.mark.integration
async def test_c5_t2_batch_row_rejoins_settlement_within_one_second(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, first_record = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    second, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 2, start + timedelta(minutes=20)
    )
    t = start + timedelta(minutes=30)
    before = await load_live_worked_seconds(db_session, workspace.client_id, [first, second], t)
    await _close_at_t(db_session, workspace, user, section, task, first, first_record, token, t)
    await _recompute_step_time_totals(db_session, workspace.client_id, first.client_id, t)
    await db_session.flush()
    assert before[first.client_id] == 1500
    assert abs(first.total_working_seconds - before[first.client_id]) <= 1


@pytest.mark.integration
async def test_c5_t2_single_open_record_rejoins_settlement_within_one_second(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, record = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        allows_batch_working=False,
    )
    t = start + timedelta(minutes=30)
    before = await load_live_worked_seconds(db_session, workspace.client_id, [step], t)
    await _close_at_t(db_session, workspace, user, section, task, step, record, token, t)
    await _recompute_step_time_totals(db_session, workspace.client_id, step.client_id, t)
    await db_session.flush()
    assert before[step.client_id] == 1800
    assert abs(step.total_working_seconds - before[step.client_id]) <= 1


@pytest.mark.integration
async def test_c6_deleted_step_still_divides_live_sibling(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    deleted, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start,
        step_deleted=True,
    )
    sibling, _ = await _add_step_record(db_session, workspace, user, section, task, token, 2, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [sibling], start + timedelta(minutes=10)
    )
    assert result == {sibling.client_id: 300}
    assert deleted.client_id not in result


@pytest.mark.integration
async def test_c7_window_anchors_at_minimum_open_entry(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    first_start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    second_start = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    now = datetime(2026, 1, 2, 11, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, first_start)
    second, _ = await _add_step_record(db_session, workspace, user, section, task, token, 2, second_start)
    await _add_step_record(
        db_session, workspace, user, section, task, token, 3,
        first_start - timedelta(minutes=30),
        exited_at=first_start + timedelta(minutes=30),
    )
    result = await load_live_worked_seconds(db_session, workspace.client_id, [first, second], now)
    assert result[first.client_id] == 90900
    assert result[second.client_id] == 1800


@pytest.mark.integration
async def test_c8_loader_is_deterministic_and_does_not_read_its_module_clock(db_session, monkeypatch):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    now = start + timedelta(minutes=10)
    first = await load_live_worked_seconds(db_session, workspace.client_id, [step], now)
    second = await load_live_worked_seconds(db_session, workspace.client_id, [step], now)
    calls = []

    class AdvancingClock:
        @classmethod
        def now(cls, tz=None):
            calls.append(tz)
            return now + timedelta(seconds=5 * len(calls))

    import beyo_manager.services.queries.item_economics.live_worked_seconds as live_module

    monkeypatch.setattr(live_module, "datetime", AdvancingClock)
    third = await load_live_worked_seconds(db_session, workspace.client_id, [step], now)
    assert first == second == third == {step.client_id: 600}
    assert calls == []


@pytest.mark.integration
async def test_c9_service_context_stamps_and_honors_aware_utc_now(monkeypatch, db_session):
    explicit = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    ctx = _ctx(db_session, "ws_context", "usr_context", explicit)
    assert ctx.now is explicit
    assert ctx.now.tzinfo is UTC

    import beyo_manager.services.context as context_module

    t0 = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    calls = []

    class StubDatetime:
        @classmethod
        def now(cls, tz=None):
            calls.append(tz)
            return t0 + timedelta(seconds=len(calls) - 1)

    monkeypatch.setattr(context_module, "datetime", StubDatetime)
    first = ServiceContext(identity={}, incoming_data={}, session=db_session)
    second = ServiceContext(identity={}, incoming_data={}, session=db_session)
    assert first.now == t0
    assert second.now == t0 + timedelta(seconds=1)
    assert calls == [UTC, UTC]


@pytest.mark.integration
async def test_c9_naive_now_fails_closed_at_the_loader_boundary(db_session):
    """Measured under §1A HC-3A (round 4d): the naive bind is silently shifted by the client host's local UTC offset (not "normalized"), so the un-guarded behaviour is a wrong live term or a ``TypeError`` from the sweep, depending on the host and the timestamps; either way the loader must fail closed at its own boundary."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    with pytest.raises(TypeError, match="load_live_worked_seconds"):
        await load_live_worked_seconds(
            db_session, workspace.client_id, [step], datetime(2026, 1, 10, 9, 10)
        )


@pytest.mark.integration
async def test_c11_nonzero_settled_term_is_added_to_live_share(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    with_open, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start, settled=100,
        allows_batch_working=False,
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [with_open], start + timedelta(minutes=10)
    )
    assert result == {with_open.client_id: 700}


@pytest.mark.integration
async def test_c11_nonzero_settled_term_is_returned_without_open_record(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    settled_only, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 2, start,
        settled=250, create_record=False,
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [settled_only], start + timedelta(minutes=10)
    )
    assert result == {settled_only.client_id: 250}


@pytest.mark.integration
async def test_c12_loader_output_values_are_ints(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first], start + timedelta(minutes=10)
    )
    assert result and all(isinstance(value, int) for value in result.values())


@pytest.mark.integration
async def test_c12_half_even_rounding_is_applied_to_each_half_second_share(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(db_session, workspace, user, section, task, token, 1, start)
    second, _ = await _add_step_record(db_session, workspace, user, section, task, token, 2, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first, second], start + timedelta(seconds=61)
    )
    assert result == {first.client_id: 30, second.client_id: 30}


@pytest.mark.integration
async def test_c12_rounding_locus_is_share_before_settled_addition(db_session):
    """The odd settled value isolates the locus because half-even and half-up agree at 31.5."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    first, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start, settled=1,
    )
    second, _ = await _add_step_record(db_session, workspace, user, section, task, token, 2, start)
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [first, second], start + timedelta(seconds=63)
    )
    assert result == {first.client_id: 33, second.client_id: 32}


@pytest.mark.integration
async def test_c10_loader_never_persists_live_seconds_on_task_step(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    start = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    step, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, start, settled=0
    )
    result = await load_live_worked_seconds(
        db_session, workspace.client_id, [step], start + timedelta(minutes=10)
    )
    step_id = step.client_id
    assert result[step_id] == 600
    assert not any(isinstance(obj, TaskStep) for obj in db_session.dirty)
    db_session.expire_all()
    persisted = await db_session.scalar(
        select(TaskStep.total_working_seconds).where(TaskStep.client_id == step_id)
    )
    assert persisted == 0
