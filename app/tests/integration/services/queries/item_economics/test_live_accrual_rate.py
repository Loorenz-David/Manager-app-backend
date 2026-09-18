"""Live accrual rate — the forward twin of `worked_seconds`.

Covers HANDOFF_TO_BACKEND_live_accrual_rate_20260916's eight acceptance criteria: a client
must be able to learn how fast a step is currently being credited, so a batched timer ticks
at 1/N instead of 1/1 and snaps back on pause.

FIXTURE WARNING: `TaskStep.allows_batch_working` defaults to False, and a non-batchable step
always reports a rate of 1.0. Every batching assertion here therefore leans on
`_add_step_record`, whose `allows_batch_working` default is True — build batching fixtures
anywhere else and they pass vacuously.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction

import pytest

from beyo_manager.domain.item_economics.budget_division import attach_live_accrual
from beyo_manager.domain.item_economics.division_serializers import _rate_decimal
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.services.queries.item_economics.live_worked_seconds import (
    load_live_worked_seconds,
    load_live_worked_time,
)

from tests.integration.services.queries.item_economics.test_live_worked_seconds import (
    _add_step_record,
    _add_task,
    _add_user,
    _seed_workspace,
)

UTC = timezone.utc
T0 = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)


def _at(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


pytestmark = pytest.mark.integration


# ------------------------------------------------------------- AC1, AC2: the divisor


async def test_ac1_ac2_three_concurrent_batched_steps_each_earn_a_third(db_session):
    """The reported defect: three steps in a batch, six seconds of wall clock, 2 s each.

    The client was adding a full second per second to all three and losing ~4 s per card on
    pause. `"0.3333"` is what lets it add the right amount instead.
    """
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i,
            _at(0), settled=1430,
        ))[0]
        for i in range(3)
    ]

    live = await load_live_worked_time(db_session, workspace.client_id, steps, _at(6))

    for step in steps:
        assert live.accrual_rate[step.client_id] == Fraction(1, 3)
        assert live.concurrency[step.client_id] == 3
        assert _rate_decimal(live.accrual_rate[step.client_id]) == "0.3333"
        # 6 wall-clock seconds shared three ways == 2 s credited each.
        assert live.seconds[step.client_id] == 1432

    assert sum(live.accrual_rate.values()) == 1


async def test_ac3_pausing_one_of_three_reprices_the_survivors_on_the_next_read(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    rows = [
        await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0)
        )
        for i in range(3)
    ]
    steps = [step for step, _record in rows]

    live = await load_live_worked_time(db_session, workspace.client_id, steps, _at(6))
    assert all(live.accrual_rate[s.client_id] == Fraction(1, 3) for s in steps)

    # Close the third step's record — the pause.
    rows[2][1].exited_at = _at(6)
    await db_session.flush()

    after = await load_live_worked_time(db_session, workspace.client_id, steps, _at(7))
    assert after.accrual_rate[steps[0].client_id] == Fraction(1, 2)
    assert after.accrual_rate[steps[1].client_id] == Fraction(1, 2)
    assert after.concurrency[steps[0].client_id] == 2
    assert _rate_decimal(after.accrual_rate[steps[0].client_id]) == "0.5000"
    # The paused one is simply absent — the serializers publish that as null.
    assert steps[2].client_id not in after.accrual_rate
    assert steps[2].client_id not in after.concurrency


async def test_paused_siblings_do_not_dilute_the_working_step(db_session):
    """Their open question 1: one working, two paused → the working step earns the full 1.0."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    working, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0)
    )
    paused = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0),
            state=TaskStepStateEnum.PAUSED,
        ))[0]
        for i in (1, 2)
    ]

    live = await load_live_worked_time(
        db_session, workspace.client_id, [working, *paused], _at(6)
    )
    assert live.accrual_rate[working.client_id] == Fraction(1)
    assert live.concurrency[working.client_id] == 1
    # Paused records are not WORKING, so they publish no live rate of their own either.
    for step in paused:
        assert step.client_id not in live.accrual_rate


async def test_non_batchable_step_beside_batched_ones_keeps_a_full_second(db_session):
    """Documented divergence from their AC1: these rates legitimately sum above 1.

    Starting a batchable step never auto-pauses a running non-batchable one, so the two
    coexist. Each rate is individually correct; only the sum-to-one invariant fails.
    """
    workspace, user, section, task, token = await _seed_workspace(db_session)
    solo, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0),
        allows_batch_working=False,
    )
    batched = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0),
        ))[0]
        for i in (1, 2)
    ]

    live = await load_live_worked_time(
        db_session, workspace.client_id, [solo, *batched], _at(6)
    )
    assert live.accrual_rate[solo.client_id] == Fraction(1)
    for step in batched:
        # Divisor is 2, not 3 — the non-batch step is outside it.
        assert live.accrual_rate[step.client_id] == Fraction(1, 2)
    assert sum(live.accrual_rate.values()) == 2


async def test_cross_task_open_record_divides_a_requested_step(db_session):
    """Why the client cannot compute this: the divisor spans tasks it never asked for."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    requested, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0)
    )
    other_task = await _add_task(db_session, workspace, user, token, 2)
    await _add_step_record(
        db_session, workspace, user, section, other_task, token, 1, _at(0)
    )

    # Only the first task's step is requested, yet its rate is halved by the unseen peer.
    live = await load_live_worked_time(db_session, workspace.client_id, [requested], _at(6))
    assert live.accrual_rate[requested.client_id] == Fraction(1, 2)
    assert live.concurrency[requested.client_id] == 2


# ------------------------------------------------- AC4, AC6, AC7: absence and consistency


async def test_ac4_a_step_with_no_open_record_reports_nothing(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    settled_only, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0),
        exited_at=_at(60), settled=250,
    )

    live = await load_live_worked_time(db_session, workspace.client_id, [settled_only], _at(600))
    assert live.seconds[settled_only.client_id] == 250
    assert live.accrual_rate == {}
    assert live.concurrency == {}
    assert live.task_rate([settled_only.client_id]) is None


async def test_ac6_two_reads_at_the_same_instant_agree(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0)
        ))[0]
        for i in range(2)
    ]
    first = await load_live_worked_time(db_session, workspace.client_id, steps, _at(30))
    second = await load_live_worked_time(db_session, workspace.client_id, steps, _at(30))
    assert first.accrual_rate == second.accrual_rate
    assert first.concurrency == second.concurrency


async def test_ac7_worked_seconds_grows_by_rate_times_elapsed(db_session):
    """The property the frontend actually measured: the rate predicts the growth."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0)
        ))[0]
        for i in range(3)
    ]

    early = await load_live_worked_time(db_session, workspace.client_id, steps, _at(30))
    late = await load_live_worked_time(db_session, workspace.client_id, steps, _at(90))
    elapsed = 60

    for step in steps:
        grew = late.seconds[step.client_id] - early.seconds[step.client_id]
        predicted = early.accrual_rate[step.client_id] * elapsed
        assert abs(grew - predicted) <= 1, f"{grew} vs predicted {float(predicted)}"


async def test_just_started_record_reports_a_rate_before_it_has_earned_a_second(db_session):
    """Nothing credited yet, but already accruing — the client must not stall for a poll.

    Read one second after the start: the new step's averaged share rounds to 0 s while its
    forward rate is already 1/2. (`compute_record_contributions` filters `entered_at <
    window_end`, so a record stamped at exactly `now` is invisible to the read — a
    pre-existing boundary that cannot arise in practice, since a transition always commits
    before a read observes it.)
    """
    workspace, user, section, task, token = await _seed_workspace(db_session)
    older, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0)
    )
    fresh, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, _at(60)
    )

    live = await load_live_worked_time(db_session, workspace.client_id, [older, fresh], _at(61))
    assert live.seconds[fresh.client_id] == 0
    assert live.accrual_rate[fresh.client_id] == Fraction(1, 2)
    assert live.accrual_rate[older.client_id] == Fraction(1, 2)


async def test_marked_wrong_record_neither_accrues_nor_dilutes(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    wrong, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0),
        record_marked_wrong=True,
    )
    ok, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, _at(0)
    )

    live = await load_live_worked_time(db_session, workspace.client_id, [wrong, ok], _at(60))
    assert wrong.client_id not in live.accrual_rate
    assert live.accrual_rate[ok.client_id] == Fraction(1), "a disowned record must not divide"


# ------------------------------------------------------- AC5: the task-level rollup


async def test_ac5_task_rate_is_the_exact_sum_of_its_step_rates(db_session):
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0)
        ))[0]
        for i in range(3)
    ]
    live = await load_live_worked_time(db_session, workspace.client_id, steps, _at(6))

    ids = [step.client_id for step in steps]
    # Summed as exact fractions before rounding, so the task reads a clean 1.0000 even
    # though the three rounded step strings only add to 0.9999.
    assert live.task_rate(ids) == Fraction(1)
    assert _rate_decimal(live.task_rate(ids)) == "1.0000"
    rounded_steps = sum(float(_rate_decimal(live.accrual_rate[i])) for i in ids)
    assert abs(rounded_steps - 1.0) <= 0.0001 * len(ids)


async def test_task_rate_sums_across_two_workers_on_one_task(db_session):
    """Two workers on the same task legitimately exceed one second per second."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    mine, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 0, _at(0)
    )
    other = await _add_user(db_session, workspace, token, "second")
    theirs, _ = await _add_step_record(
        db_session, workspace, user, section, task, token, 1, _at(0),
        record_created_by_id=other.client_id,
        credited_user_id=other.client_id,
    )

    live = await load_live_worked_time(db_session, workspace.client_id, [mine, theirs], _at(6))
    # Each worker is alone in their own concurrency context, so each earns a full second.
    assert live.accrual_rate[mine.client_id] == Fraction(1)
    assert live.accrual_rate[theirs.client_id] == Fraction(1)
    assert live.task_rate([mine.client_id, theirs.client_id]) == Fraction(2)


# ------------------------------------------------------- invariants and the overlay


async def test_rate_is_always_one_over_concurrency(db_session):
    """A step holds at most one open record, so this invariant is unconditional."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0),
            allows_batch_working=i != 0,
        ))[0]
        for i in range(4)
    ]
    live = await load_live_worked_time(db_session, workspace.client_id, steps, _at(6))
    assert live.accrual_rate
    for step_id, rate in live.accrual_rate.items():
        assert rate == Fraction(1, live.concurrency[step_id])


async def test_seconds_wrapper_matches_the_full_loader(db_session):
    """The one cost of keeping two public functions, retired."""
    workspace, user, section, task, token = await _seed_workspace(db_session)
    steps = [
        (await _add_step_record(
            db_session, workspace, user, section, task, token, i, _at(0)
        ))[0]
        for i in range(2)
    ]
    wrapper = await load_live_worked_seconds(db_session, workspace.client_id, steps, _at(30))
    full = await load_live_worked_time(db_session, workspace.client_id, steps, _at(30))
    assert wrapper == full.seconds


def test_ac8_excluded_step_rows_report_no_rate():
    """An `excluded` step row publishes null even with a live rate in hand.

    The fixture deliberately supplies a rate for the step so the assertion cannot pass
    merely because nothing was accruing.
    """
    rows = [
        {"step_id": "tsp_a", "share_state": "excluded"},
        {"step_id": "tsp_b", "share_state": "on_track"},
    ]
    attach_live_accrual(
        rows,
        {"tsp_a": Fraction(1, 3), "tsp_b": Fraction(1, 3)},
        {"tsp_a": 3, "tsp_b": 3},
    )
    assert rows[0]["live_accrual_rate"] is None
    assert rows[0]["live_concurrency"] is None
    assert rows[1]["live_accrual_rate"] == Fraction(1, 3)
    assert rows[1]["live_concurrency"] == 3


def test_ac8_no_budget_step_rows_report_their_true_rate():
    """INVERTED 2026-09-18. This leg previously asserted null for `no_budget` step rows.

    That left an unpriced task's timers counting real time: three batched steps each ran 3x
    fast and snapped back on pause — the defect the rate exists to fix, surviving only on
    unpriced tasks. Step rows now carry the true rate on `no_budget` exactly as on priced
    rows; only the budget-signals *task* row stays null there (its actual_worked_seconds is
    a frozen 0). See HANDOFF_TO_FRONTEND_live_accrual_rate_no_budget_steps_20260918.
    """
    rows = [{"step_id": "tsp_a", "share_state": "no_budget"}]
    attach_live_accrual(rows, {"tsp_a": Fraction(1, 3)}, {"tsp_a": 3})
    assert rows[0]["live_accrual_rate"] == Fraction(1, 3), "null here is the retired rule"
    assert rows[0]["live_concurrency"] == 3


def test_attach_live_accrual_sets_both_keys_on_every_row():
    rows = [{"step_id": "tsp_idle", "share_state": "on_track"}]
    attach_live_accrual(rows, {}, {})
    assert rows[0]["live_accrual_rate"] is None
    assert rows[0]["live_concurrency"] is None


# ------------------------------------------- unpriced tasks, end to end through both surfaces


async def test_unpriced_batch_steps_carry_the_true_rate_while_the_task_signal_stays_null(
    db_session,
):
    """Three batched steps on an unpriced task: each step row reads "0.3333" / 3, the
    task's budget-signals row reads null.

    The two rules differ on purpose. The step rows carry a live `worked_seconds` that a
    worker's timer displays, so they need the rate; the signals row publishes a frozen
    `actual_worked_seconds` of 0, so a rate there would describe nothing.
    """
    from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.models.tables.tasks.task_step import TaskStep
    from beyo_manager.services.context import ServiceContext
    from beyo_manager.services.queries.item_economics.get_task_budget_allocations import (
        get_task_budget_allocations,
    )
    from beyo_manager.services.queries.item_economics.get_task_budget_signals import (
        get_task_budget_signals,
    )
    from tests.integration.services.queries.item_economics.test_budget_allocations_query import (
        _seed,
    )

    values = await _seed(db_session)
    workspace, user, section, unpriced = values[0], values[1], values[2], values[4]
    now = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

    step_ids = []
    for i in range(3):
        step = TaskStep(
            client_id=f"tsp_unpriced_batch_{workspace.client_id}_{i}",
            workspace_id=workspace.client_id,
            task_id=unpriced.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.WORKING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=0,
            # The fixture trap: without this every step is non-batchable, reports 1.0,
            # and the "0.3333" assertion below could never have been reached honestly.
            allows_batch_working=True,
            created_by_id=user.client_id,
        )
        db_session.add(step)
        await db_session.flush()
        db_session.add(
            StepStateRecord(
                client_id=f"ssr_unpriced_batch_{workspace.client_id}_{i}",
                workspace_id=workspace.client_id,
                step_id=step.client_id,
                state=TaskStepStateEnum.WORKING,
                entered_at=now - timedelta(seconds=6),
                exited_at=None,
                created_by_id=user.client_id,
                credited_user_id=user.client_id,
            )
        )
        await db_session.flush()
        step_ids.append(step.client_id)

    allocations = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id,
                      "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [unpriced.client_id]},
            session=db_session,
            now=now,
        )
    )
    (task_row,) = allocations["budget_allocations"]
    rows = {row["step_id"]: row for row in task_row["steps"] if row["step_id"] in step_ids}
    assert set(rows) == set(step_ids)
    for step_id in step_ids:
        row = rows[step_id]
        # Pin the path under test: without this the test could pass on a priced task.
        assert row["share_state"] == "no_budget"
        assert row["live_accrual_rate"] == "0.3333", "null here is the retired rule"
        assert row["live_concurrency"] == 3
        # Six wall-clock seconds shared three ways.
        assert row["worked_seconds"] == 2

    signals = await get_task_budget_signals(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id,
                      "role_name": "manager"},
            incoming_data={},
            query_params={"task_ids": [unpriced.client_id]},
            session=db_session,
            now=now,
        )
    )
    (signal_row,) = signals["budget_signals"]
    assert signal_row["budget_state"] == "no_budget"
    assert signal_row["actual_worked_seconds"] == 0
    assert signal_row["live_accrual_rate"] is None
