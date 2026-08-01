"""The `ended_shift` time bucket survives the collapse of the step state that named it.

`compute_record_contributions` emits one `.state` string that six consumers bucket on. This
module pins that string — and the totals derived from it — across the whole rollout, and it
asserts **different things of the two paths**, because only one of them is meant to hold
still:

* **Clock-out force-close** — the system stopped a step that was still being worked and
  nobody said why. Its span stays in `total_ended_shift_seconds` / `_count`, byte-identical
  before and after. Every assertion here is an equality that must never move.
* **A worker's own pick of an "ended shift" pause reason** — a pause with a stated reason,
  and the numbers **move** to `total_pause_seconds`, attributed to the reason the worker
  chose. Asserting equality there would pin the behaviour this change deliberately alters.

The consumers are asserted **one by one**. They share `compute_record_contributions`, but
each buckets its own way, and three of them were missing from the original trace — so a
passing assertion on the shared helper is not evidence about any of them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.tasks.serializers import serialize_step
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
)
from beyo_manager.services.commands.users._reconstruct_shift_middle import (
    reconstruct_shift_middle,
)
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions
from beyo_manager.services.queries.analytics.estimation_sample import (
    load_trusted_step_duration_sample,
)
from beyo_manager.services.queries.analytics.reconcile_user_time import reconcile_user_day_time
from beyo_manager.services.queries.worker_stats.get_worker_daily_step_breakdown import (
    get_worker_daily_step_breakdown,
)
from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    get_worker_linear_timeline_breakdown,
)
from beyo_manager.services.queries.worker_stats.list_workers_totals import list_workers_totals
from beyo_manager.services.tasks.analytics.process_step_transition import (
    _recompute_step_time_totals,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# The state the worker app sends when a worker picks a pause reason from the sheet.
#
# It used to depend on *which* reason: `pause-reason-transition.ts` mapped the row whose slug
# is `pause_ended_shift` onto a different state-machine target, so picking a reason silently
# chose a state. That file is gone and every reason now sends `paused`
# (`PauseReasonSheetPage.tsx`, both call sites).
#
# The assertions below were written against the old payload and failed on it — a worker's
# pick landed in the unattributed off-shift bucket instead of being credited to the reason
# they gave. They are the specification; this constant is only the transport.
_WORKER_PICK_NEW_STATE = TaskStepStateEnum.PAUSED

DAY_ONE = datetime(2026, 7, 20, tzinfo=timezone.utc)
DAY_TWO = DAY_ONE + timedelta(days=1)

CLOCK_IN = DAY_ONE.replace(hour=8)
STEP_STARTED = DAY_ONE.replace(hour=9)
CLOCK_OUT = DAY_ONE.replace(hour=17)
RESUMED = DAY_TWO.replace(hour=8)
COMPLETED = DAY_TWO.replace(hour=9)

WORKED_SECONDS = int((CLOCK_OUT - STEP_STARTED).total_seconds())        # 28_800
OFF_SHIFT_SECONDS = int((RESUMED - CLOCK_OUT).total_seconds())          # 54_000
SECOND_DAY_WORKED_SECONDS = int((COMPLETED - RESUMED).total_seconds())  # 3_600


# --------------------------------------------------------------------------- seeding


async def _seed_workspace_and_worker(db_session) -> tuple[Workspace, User]:
    """A workspace with one worker who is an active member of it.

    Membership matters: two of the six consumers resolve the worker through it and raise
    rather than return zeros without it.
    """
    suffix = uuid4().hex[:12]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Bucket {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"worker_{suffix}",
        email=f"{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    # Roles are global singletons keyed by name — reuse the seeded row when there is one.
    role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one_or_none()
    if role is None:
        role = Role(client_id=f"rol_{suffix}", name=RoleNameEnum.WORKER)
        db_session.add(role)
        await db_session.flush()
    workspace_role = WorkspaceRole(
        client_id=f"wsr_{suffix}", workspace_id=workspace.client_id, role_id=role.client_id
    )
    db_session.add(workspace_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            client_id=f"wsm_{suffix}",
            user_id=user.client_id,
            workspace_id=workspace.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return workspace, user


async def _seed_working_step(
    db_session,
    workspace: Workspace,
    user: User,
    *,
    entered_at: datetime,
) -> tuple[TaskStep, Task, StepStateRecord]:
    """One step the worker is currently working, with its open `WORKING` record."""
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
        state=TaskStepStateEnum.WORKING,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=False,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        assigned_worker_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=entered_at,
        exited_at=None,
        created_by_id=user.client_id,
        credited_user_id=user.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step, task, record


async def _seed_pause_reason(db_session, workspace: Workspace, user: User, name: str) -> PauseReason:
    """An ordinary workspace-editable pause reason — which is all `pause_ended_shift` is (E4)."""
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=name,
        slug=None,
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
        created_by_id=user.client_id,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


def _ctx(db_session, workspace: Workspace, user: User, **kwargs) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": user.client_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=kwargs.pop("incoming_data", {}),
        query_params=kwargs.pop("query_params", {}),
        session=db_session,
    )


def _patch_transition_side_effects(monkeypatch) -> None:
    """Silence the outbox task and notification fan-out; touch no bucketing."""

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_targets(*_args, **_kwargs):
        return []

    module = "beyo_manager.services.commands.task_steps._step_transition_core"
    monkeypatch.setattr(f"{module}.create_instant_task", _noop)
    monkeypatch.setattr(f"{module}.resolve_task_step_notification_targets", _no_targets)


async def _open_record(db_session, step_id: str) -> StepStateRecord:
    return (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id == step_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()


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


async def _shift_records(db_session, workspace_id: str, user_id: str) -> list[UserShiftStateRecord]:
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


async def _run_clock_out_scenario(db_session, monkeypatch) -> tuple[Workspace, User, TaskStep]:
    """The unattributed path, end to end through the real clock-out command.

    Day one: clock in 08:00, start a step at 09:00, clock out at 17:00 with it still open —
    the system force-closes it. Day two: resume at 08:00 and complete at 09:00.

    Nothing here seeds a state by hand: the row the clock-out writes is whatever the writer
    writes, which is what makes the assertions downstream survive the writer cutover.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, task, _ = await _seed_working_step(
        db_session, workspace, worker, entered_at=STEP_STARTED
    )

    transitioned = await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_OUT,
        changed_by_id=worker.client_id,
    )
    assert transitioned == 1, "clock-out must have force-closed exactly the open working step"

    ctx = _ctx(db_session, workspace, worker)
    await _apply_step_transition(
        ctx,
        step,
        task,
        await _open_record(db_session, step.client_id),
        new_state=TaskStepStateEnum.WORKING,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=RESUMED,
    )
    await _apply_step_transition(
        ctx,
        step,
        task,
        await _open_record(db_session, step.client_id),
        new_state=TaskStepStateEnum.COMPLETED,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=COMPLETED,
    )
    await db_session.flush()
    return workspace, worker, step


# ---------------------------------------------------------- criteria 1 + 2: what clock-out writes


async def test_clock_out_writes_a_paused_row_that_still_buckets_as_ended_shift(
    db_session, monkeypatch
) -> None:
    """Criteria 1 and 2 — the two halves of the change, asserted against the same row.

    The row is `paused`: no code path writes an ended-shift *state*. The bucket is
    `ended_shift`: the metric that quarantines off-shift time from pause time is unaffected.
    Both must be true of one row, or the change has moved the number instead of the label.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, _, _ = await _seed_working_step(db_session, workspace, worker, entered_at=STEP_STARTED)
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_OUT,
        changed_by_id=worker.client_id,
    )

    written = await _open_record(db_session, step.client_id)
    assert written.state is TaskStepStateEnum.PAUSED
    assert written.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    assert written.pause_reason_id is None
    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.PAUSED

    contributions = await compute_record_contributions(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_IN - timedelta(days=1),
        CLOCK_OUT + timedelta(days=1),
        CLOCK_OUT + timedelta(hours=1),
    )
    written_contribution = next(
        c for c in contributions if c.record_id == written.client_id
    )
    assert written_contribution.state == "ended_shift"
    assert written_contribution.is_open is True


# ------------------------------------------- criterion 3a + 7: the clock-out path holds still


async def test_clock_out_force_close_stays_in_the_ended_shift_bucket(db_session, monkeypatch) -> None:
    """Criterion 3, first arm — equality, and it must hold at every point in the rollout.

    Consumers asserted here: `compute_record_contributions` itself (the emitted bucket key)
    and `process_step_transition._recompute_step_time_totals` (the step's published totals).
    """
    workspace, worker, step = await _run_clock_out_scenario(db_session, monkeypatch)

    contributions = await compute_record_contributions(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_IN - timedelta(days=1),
        COMPLETED + timedelta(days=1),
        COMPLETED,
    )
    by_bucket: dict[str, float] = {}
    for contribution in contributions:
        if contribution.is_open:
            continue
        by_bucket[contribution.state] = by_bucket.get(contribution.state, 0.0) + contribution.seconds

    assert by_bucket == {
        "working": float(WORKED_SECONDS + SECOND_DAY_WORKED_SECONDS),
        "ended_shift": float(OFF_SHIFT_SECONDS),
    }, "the force-closed span must be labelled `ended_shift`, and no pause may appear"

    await _recompute_step_time_totals(db_session, workspace.client_id, step.client_id, COMPLETED)
    await db_session.flush()

    assert step.total_ended_shift_seconds == OFF_SHIFT_SECONDS
    assert step.total_ended_shift_count == 1
    assert step.total_working_seconds == WORKED_SECONDS + SECOND_DAY_WORKED_SECONDS
    assert step.total_working_count == 2
    # The unattributed bucket must not leak into pause — that is the corruption the whole
    # `total_ended_shift_seconds` field exists to prevent.
    assert step.total_pause_seconds == 0
    assert step.total_pause_count == 0


async def test_reconcile_user_day_time_buckets_the_clock_out_span_as_ended_shift(
    db_session, monkeypatch
) -> None:
    """Consumer: `services/queries/analytics/reconcile_user_time.py`.

    Missing from the original trace. It buckets through `_accumulate`, keyed on the same
    emitted string, and writes the worker's day row.
    """
    workspace, worker, _ = await _run_clock_out_scenario(db_session, monkeypatch)

    await reconcile_user_day_time(
        db_session,
        workspace.client_id,
        worker.client_id,
        worker.username,
        DAY_ONE.date(),
        COMPLETED,
    )
    await db_session.flush()

    day_one = (
        await db_session.execute(
            select(UserDailyWorkStats).where(
                UserDailyWorkStats.workspace_id == workspace.client_id,
                UserDailyWorkStats.user_id == worker.client_id,
                UserDailyWorkStats.work_date == DAY_ONE.date(),
            )
        )
    ).scalar_one()

    assert day_one.total_ended_shift_seconds == OFF_SHIFT_SECONDS
    assert day_one.total_ended_shift_count == 1
    assert day_one.total_working_seconds == WORKED_SECONDS
    assert day_one.total_pause_seconds == 0
    assert day_one.total_pause_count == 0


async def test_daily_step_breakdown_buckets_the_clock_out_span_as_ended_shift(
    db_session, monkeypatch
) -> None:
    """Consumer: `services/queries/worker_stats/get_worker_daily_step_breakdown.py`.

    Its own `avg_seconds` dict is keyed `working`/`paused`/`ended_shift`; a key the emitter
    stops producing silently drops the seconds rather than raising.
    """
    workspace, worker, step = await _run_clock_out_scenario(db_session, monkeypatch)

    out = await get_worker_daily_step_breakdown(
        _ctx(
            db_session,
            workspace,
            worker,
            incoming_data={"user_id": worker.client_id},
            query_params={
                "date_from": DAY_ONE.date().isoformat(),
                "date_to": DAY_ONE.date().isoformat(),
                "limit": 50,
                "offset": 0,
            },
        )
    )

    assert out["totals"]["ended_shift_seconds"] == OFF_SHIFT_SECONDS
    assert out["totals"]["working_seconds"] == WORKED_SECONDS
    assert out["totals"]["pause_seconds"] == 0
    contribution = next(
        item["contribution"]
        for item in out["steps"]["items"]
        if item["client_id"] == step.client_id
    )
    assert contribution["ended_shift_seconds"] == OFF_SHIFT_SECONDS
    assert contribution["pause_seconds"] == 0


async def test_estimation_sample_buckets_the_clock_out_span_as_ended_shift(
    db_session, monkeypatch
) -> None:
    """Consumer: `services/queries/analytics/estimation_sample.py`.

    Missing from the original trace. It groups its sample by `(section, state)`, so the
    emitted string is a **dictionary key in a published estimate**, not just a filter.
    """
    workspace, worker, step = await _run_clock_out_scenario(db_session, monkeypatch)
    await db_session.refresh(step)

    samples = await load_trusted_step_duration_sample(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_IN - timedelta(days=1),
        COMPLETED + timedelta(days=1),
        COMPLETED,
    )

    section_id = step.working_section_id
    assert samples[(section_id, "ended_shift")] == [float(OFF_SHIFT_SECONDS)]
    assert samples[(section_id, "working")] == [
        float(WORKED_SECONDS + SECOND_DAY_WORKED_SECONDS)
    ]
    assert (section_id, "paused") not in samples


async def test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift(
    db_session, monkeypatch
) -> None:
    """Consumer: `services/queries/worker_stats/list_workers_totals.py`.

    Missing from the original trace, and it is the only consumer that reads
    `compute_record_contributions` for **open** records — the live `running` slice, which
    only exists for today. It publishes `ended_shift_seconds` / `ended_shift_open_count`
    (criterion 10), so the bucket key is visible in the response shape here.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)

    now = datetime.now(timezone.utc)
    clock_in_at = now - timedelta(hours=3)
    clock_out_at = now - timedelta(hours=1)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, clock_in_at, worker.client_id
    )
    await _seed_working_step(
        db_session, workspace, worker, entered_at=clock_in_at + timedelta(minutes=1)
    )
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        clock_out_at,
        changed_by_id=worker.client_id,
    )

    today = now.date().isoformat()
    out = await list_workers_totals(
        _ctx(
            db_session,
            workspace,
            worker,
            query_params={"date_from": today, "date_to": today, "limit": 50, "offset": 0},
        )
    )

    running = next(
        entry["running"]
        for entry in out["workers"]
        if entry["user"]["client_id"] == worker.client_id
    )
    assert running["ended_shift_open_count"] == 1
    assert running["pause_open_count"] == 0
    assert running["working_open_count"] == 0
    # Wall-clock dependent by nature (the service reads `now` itself); one hour ± a minute.
    assert 3540 <= running["ended_shift_seconds"] <= 3660


# ------------------------------- criterion 3b: the worker's own pick moves to the pause bucket


async def test_worker_picked_ended_shift_pause_left_open_overnight_moves_to_pause(
    db_session, monkeypatch
) -> None:
    """Criterion 3, second arm — and it asserts the **opposite** of the test above.

    A worker who picks a reason named "Ended shift" has stated why the item stopped. That is
    an ordinary pause: the span belongs in `total_pause_seconds` carrying the catalog row the
    worker chose, not in the unattributed `ended_shift` bucket.

    This is the deliberate behaviour change of E1, so it **fails against pre-change code**,
    where the worker app maps that one reason onto a different state-machine target and the
    overnight span lands in `total_ended_shift_seconds`.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)
    reason = await _seed_pause_reason(db_session, workspace, worker, "Ended shift")

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, task, record = await _seed_working_step(
        db_session, workspace, worker, entered_at=STEP_STARTED
    )
    ctx = _ctx(db_session, workspace, worker)

    # The worker picks "Ended shift" from the sheet and goes home, leaving the step paused.
    await _apply_step_transition(
        ctx,
        step,
        task,
        record,
        new_state=_WORKER_PICK_NEW_STATE,
        pause_reason_id=reason.client_id,
        description=None,
        credited_user_id=worker.client_id,
        now=CLOCK_OUT,
    )
    # ...and resumes it the next morning.
    await _apply_step_transition(
        ctx,
        step,
        task,
        await _open_record(db_session, step.client_id),
        new_state=TaskStepStateEnum.WORKING,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=RESUMED,
    )
    await db_session.flush()

    picked = next(
        rec for rec in await _step_records(db_session, step.client_id) if rec.entered_at == CLOCK_OUT
    )
    assert picked.state is TaskStepStateEnum.PAUSED
    assert picked.pause_reason_id == reason.client_id
    # A worker's stated choice is not a system transition. Nothing may type it as one.
    assert picked.transition_reason is None

    await _recompute_step_time_totals(db_session, workspace.client_id, step.client_id, RESUMED)
    await db_session.flush()

    assert step.total_pause_seconds == OFF_SHIFT_SECONDS
    assert step.total_pause_count == 1
    assert step.total_ended_shift_seconds == 0
    assert step.total_ended_shift_count == 0


async def test_worker_picked_ended_shift_pause_is_attributed_to_the_reason_in_the_rebuild(
    db_session, monkeypatch
) -> None:
    """Criterion 5 for the worker's pick — the timeline must credit it to the chosen reason.

    The in-shift part of the same pause. The clock-out rebuild reads step records in
    `WORKING`/`PAUSED`; a state outside that pair is invisible to it and the span falls
    through to `idle`, unattributed. Fails against pre-change code for exactly that reason.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)
    reason = await _seed_pause_reason(db_session, workspace, worker, "Ended shift")

    picked_at = DAY_ONE.replace(hour=16)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, task, record = await _seed_working_step(
        db_session, workspace, worker, entered_at=STEP_STARTED
    )
    await _apply_step_transition(
        _ctx(db_session, workspace, worker),
        step,
        task,
        record,
        new_state=_WORKER_PICK_NEW_STATE,
        pause_reason_id=reason.client_id,
        description=None,
        credited_user_id=worker.client_id,
        now=picked_at,
    )
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_OUT,
        changed_by_id=worker.client_id,
    )

    paused_rows = [
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert len(paused_rows) == 1
    assert paused_rows[0].entered_at == picked_at
    assert paused_rows[0].exited_at == CLOCK_OUT
    assert paused_rows[0].reason == reason.client_id
    assert paused_rows[0].transition_reason is None


# -------------------------------------------------- criterion 5: the rebuild's new input row


async def test_rebuild_reads_a_shift_ended_pause_as_off_shift_and_stays_idempotent(
    db_session, monkeypatch
) -> None:
    """A `paused` record typed `shift_ended` is new input to the clock-out rebuild.

    Before this change the rebuild never saw a step stopped by clock-out — it loaded
    `WORKING`/`PAUSED` only, and such a step was in neither. Now it is `PAUSED` and lands in
    the sweep, so the rebuild has to keep telling the two apart: a pause the worker took is
    `IN_PAUSE`, a span the shift ended under is not the worker being paused at all and falls
    through to `IDLE`. Without the derived bucket the worker would be shown as paused,
    credited to a system transition, for hours they were not on site.

    The second half is the invariant that makes the closed timeline reproducible: run the
    rebuild twice over identical sources and the rows must be identical.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)
    reason = await _seed_pause_reason(db_session, workspace, worker, "Lunch")

    window_start = DAY_ONE.replace(hour=8)
    window_end = DAY_ONE.replace(hour=20)
    step, task, record = await _seed_working_step(
        db_session, workspace, worker, entered_at=DAY_ONE.replace(hour=9)
    )
    ctx = _ctx(db_session, workspace, worker)
    # A pause the worker took, inside the window.
    await _apply_step_transition(
        ctx, step, task, record,
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=reason.client_id,
        description=None,
        credited_user_id=worker.client_id,
        now=DAY_ONE.replace(hour=10),
    )
    await _apply_step_transition(
        ctx, step, task, await _open_record(db_session, step.client_id),
        new_state=TaskStepStateEnum.WORKING,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=DAY_ONE.replace(hour=11),
    )
    # A span the shift ended under, also inside the window — what a repair rebuild over a
    # window containing a clock-out sees.
    await _apply_step_transition(
        ctx, step, task, await _open_record(db_session, step.client_id),
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=DAY_ONE.replace(hour=12),
        transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
    )
    await db_session.flush()

    def _shape(rows):
        return [
            (r.state, r.entered_at, r.exited_at, r.reason, r.transition_reason,
             r.changed_by_id, r.manually_recorded)
            for r in rows
        ]

    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, window_start, window_end
    )
    first = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))
    await reconstruct_shift_middle(
        db_session, workspace.client_id, worker.client_id, window_start, window_end
    )
    second = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))

    assert first == second, "the rebuild must be idempotent over identical source data"

    rows = await _shift_records(db_session, workspace.client_id, worker.client_id)
    paused_rows = [r for r in rows if r.state is UserShiftStateEnum.IN_PAUSE]
    # Exactly one pause — the worker's. The shift-ended span is not one of them.
    assert len(paused_rows) == 1
    assert paused_rows[0].reason == reason.client_id
    assert paused_rows[0].entered_at == DAY_ONE.replace(hour=10)
    assert paused_rows[0].exited_at == DAY_ONE.replace(hour=11)
    assert not any(
        r.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value for r in paused_rows
    ), "a span the shift ended under must not be rebuilt as the worker being paused"
    # It falls through to idle, which is what the shift-end marker then closes.
    idle_after = [
        r for r in rows
        if r.state is UserShiftStateEnum.IDLE and r.entered_at == DAY_ONE.replace(hour=12)
    ]
    assert len(idle_after) == 1


# ------------------------------- the timeline drill-down, whose population also widened


async def test_timeline_drilldown_never_shows_the_clock_out_record_as_a_paused_step(
    db_session, monkeypatch
) -> None:
    """`get_worker_linear_timeline_breakdown` filters step records to `(WORKING, PAUSED)`.

    That tuple never contained the removed member, so the collapse widened what it selects —
    the same class of change that broke the heal script. Here it is harmless, and this test
    is why that is a checked claim rather than a reading: the force-closed record is entered
    at the clock-out instant, so it starts at or after the end of every segment of the shift
    it ended, and the next day's segments exclude it by the shift-scoping guard.

    If either guard ever goes, a worker's timeline grows a paused block covering the night.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, _, _ = await _seed_working_step(db_session, workspace, worker, entered_at=STEP_STARTED)
    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_OUT, changed_by_id=worker.client_id
    )
    force_closed = await _open_record(db_session, step.client_id)

    # The day it ended...
    out = await get_worker_linear_timeline_breakdown(
        _ctx(
            db_session,
            workspace,
            worker,
            incoming_data={"user_id": worker.client_id},
            query_params={
                "date_from": DAY_ONE.date().isoformat(),
                "date_to": DAY_ONE.date().isoformat(),
            },
        )
    )
    shown = {
        record["record_id"]
        for segment in out["segments"]
        for record in segment["steps"]
    }
    assert force_closed.client_id not in shown, (
        "the record that ended the shift must not appear as a step inside it"
    )

    # ...and the morning after, where the carryover guard is the only thing excluding it.
    #
    # Arranging this took three attempts, and the two failures are the reason it looks like
    # this. A step record attaches to a segment only when the segment's shift state maps to
    # the record's own step state (`_STEP_STATE_FOR_SHIFT`: WORKING→WORKING, IN_PAUSE→PAUSED).
    # Yesterday's carryover is `paused`, so the **only** block it can ever land in is an
    # IN_PAUSE one. Give day two no pause and the guard is never consulted: the assertion
    # passes on the shape of the timeline, not on the guard, and deleting the guard leaves it
    # green. (The first version was worse still — day two was idle, so it asserted over an
    # empty set.)
    #
    # So day two pauses a step for a reason. That produces an IN_PAUSE segment which
    # yesterday's carryover overlaps — it is still open, having never been resumed — and which
    # only `entered_at >= current_shift_start` keeps it out of.
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, RESUMED, worker.client_id
    )
    today_step, today_task, today_record = await _seed_working_step(
        db_session, workspace, worker, entered_at=DAY_TWO.replace(hour=9)
    )
    reason = await _seed_pause_reason(db_session, workspace, worker, "Coffee break")
    ctx = _ctx(db_session, workspace, worker)
    await _apply_step_transition(
        ctx, today_step, today_task, today_record,
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=reason.client_id,
        description=None,
        credited_user_id=worker.client_id,
        now=DAY_TWO.replace(hour=10),
    )
    today_pause = await _open_record(db_session, today_step.client_id)
    await _apply_step_transition(
        ctx, today_step, today_task, today_pause,
        new_state=TaskStepStateEnum.WORKING,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=DAY_TWO.replace(hour=11),
    )
    # Clock out again so day two's timeline is rebuilt from those records.
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        DAY_TWO.replace(hour=17),
        changed_by_id=worker.client_id,
    )
    # Yesterday's record must still be open, or it is not a carryover and overlaps nothing.
    await db_session.refresh(force_closed)
    assert force_closed.exited_at is None

    next_day = await get_worker_linear_timeline_breakdown(
        _ctx(
            db_session,
            workspace,
            worker,
            incoming_data={"user_id": worker.client_id},
            query_params={
                "date_from": DAY_TWO.date().isoformat(),
                "date_to": DAY_TWO.date().isoformat(),
            },
        )
    )
    shown_next = {
        record["record_id"]
        for segment in next_day["segments"]
        for record in segment["steps"]
    }
    assert shown_next, (
        "day two produced no step records at all; the assertions below would pass vacuously"
    )
    assert today_record.client_id in shown_next, (
        "today's own work must be present — otherwise the exclusion below is not selective"
    )
    assert force_closed.client_id not in shown_next, (
        "yesterday's carryover must not appear in this morning's timeline"
    )

    # The load-bearing assertion: the paused block exists, and holds *exactly* today's pause.
    # Delete `entered_at >= current_shift_start` and yesterday's carryover joins it — the
    # block goes from one step to two, and a manager reading the timeline sees a step paused
    # during a break it was never part of, carrying yesterday's off-shift span.
    paused_blocks = [
        segment for segment in next_day["segments"] if segment["state"] == "paused"
    ]
    assert len(paused_blocks) == 1, (
        "day two must derive exactly one IN_PAUSE block; without one the carryover has "
        "nothing to attach to and this test cannot see the guard at all"
    )
    assert {record["record_id"] for record in paused_blocks[0]["steps"]} == {
        today_pause.client_id
    }


# ----------------------------------------------- criterion 6: the morning after the clock-out


async def test_clocking_in_after_a_clock_out_left_a_step_open_derives_idle(
    db_session, monkeypatch
) -> None:
    """Criterion 6, and it needs its own test rather than an inherited one.

    Clock-out leaves the force-closed step open in a state the live derivation *queries*
    once the collapse lands. Without the `entered_at_or_after` guard at
    `reconcile_worker_shift_state.py:172`, yesterday's still-open row would derive the worker
    into `in_pause` on this morning's clock-in. The guard exists; today it is redundant for
    this case because the state it filters is never queried, and this change makes it
    load-bearing.
    """
    _patch_transition_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_and_worker(db_session)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step, _, _ = await _seed_working_step(db_session, workspace, worker, entered_at=STEP_STARTED)
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        CLOCK_OUT,
        changed_by_id=worker.client_id,
    )

    # The step is still open, entered yesterday at 17:00.
    left_open = await _open_record(db_session, step.client_id)
    assert left_open.entered_at == CLOCK_OUT
    assert left_open.exited_at is None

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, RESUMED, worker.client_id
    )
    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, worker.client_id, RESUMED + timedelta(minutes=1)
    )

    assert outcome.state is UserShiftStateEnum.IDLE, (
        "yesterday's still-open step must not derive this morning's worker into in_pause"
    )
    open_shift_row = next(
        row
        for row in await _shift_records(db_session, workspace.client_id, worker.client_id)
        if row.exited_at is None
    )
    assert open_shift_row.state is UserShiftStateEnum.IDLE


# ---------------------------------------------------------------- criterion 10: the payloads


async def test_step_payload_keeps_its_ended_shift_fields(db_session, monkeypatch) -> None:
    """Criterion 10 — published names and meanings, read out of the real serializer.

    `total_ended_shift_seconds` / `_count` ship in every step payload, including the
    reassigned-steps endpoints. Only their derivation moves; the payload may not.
    """
    workspace, worker, step = await _run_clock_out_scenario(db_session, monkeypatch)
    await _recompute_step_time_totals(db_session, workspace.client_id, step.client_id, COMPLETED)
    await db_session.flush()

    payload = serialize_step(step)

    assert payload["total_ended_shift_seconds"] == OFF_SHIFT_SECONDS
    assert payload["total_ended_shift_count"] == 1
    assert payload["total_pause_seconds"] == 0
