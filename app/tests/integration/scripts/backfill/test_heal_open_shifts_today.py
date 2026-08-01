"""`heal_open_shifts_today` must heal shifts that are open and leave closed ones alone.

The script had no tests, which is why a change that never touched it could break it. Its
scope test asks *"has this worker done anything since their last clock-out?"* by looking for
a step record in `(WORKING, PAUSED)` entered at or after that clock-out. Clock-out now
**pauses** the step it force-closes, at exactly the clock-out instant — so the record marking
the end of the shift satisfies that test, and a worker who has gone home looks like a worker
mid-task.

With `--execute` that writes a `STARTED_SHIFT` marker at the clock-out instant and reopens
the tail: a clocked-out worker left with an open shift running to now, which the live
derivation then keeps extending.

The seeding here drives the **real** clock-in/clock-out commands rather than hand-writing
records, so these tests are pinned to what the writer actually produces.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
)
from scripts.backfill.heal_open_shifts_today import heal_current_shift


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

DAY = datetime(2026, 7, 20, tzinfo=timezone.utc)
DAY_START = DAY
CLOCK_IN = DAY.replace(hour=8)
STEP_STARTED = DAY.replace(hour=9)
CLOCK_OUT = DAY.replace(hour=17)
NOW = DAY.replace(hour=18)


async def _seed_workspace_and_worker(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:12]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Heal {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"worker_{suffix}",
        email=f"{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_open_working_step(
    db_session, workspace: Workspace, user: User, *, entered_at: datetime
) -> TaskStep:
    suffix = uuid4().hex[:12]
    section = WorkingSection(
        workspace_id=workspace.client_id, name=f"section-{suffix}", created_by_id=user.client_id
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
    return step


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


def _shape(rows):
    return [(r.state, r.entered_at, r.exited_at) for r in rows]


async def _clocked_out_worker(db_session) -> tuple[Workspace, User]:
    """Clocked in at 08:00, worked from 09:00, clocked out at 17:00. Nothing since."""
    workspace, worker = await _seed_workspace_and_worker(db_session)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_IN, worker.client_id
    )
    step = await _seed_open_working_step(
        db_session, workspace, worker, entered_at=STEP_STARTED
    )
    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, CLOCK_OUT, changed_by_id=worker.client_id
    )
    # The premise: clock-out left a `paused` record at exactly the clock-out instant, which
    # is also exactly where the script's shift scope starts. Asserted so this cannot pass
    # vacuously if the writer ever changes again.
    force_closed = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id == step.client_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert force_closed.state is TaskStepStateEnum.PAUSED
    assert force_closed.entered_at == CLOCK_OUT
    assert force_closed.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    return workspace, worker


async def test_worker_who_clocked_out_today_is_skipped(db_session) -> None:
    """The reviewer's reproduction. Fails before the `shift_ended` exclusion.

    Without it the scope query finds the clock-out's own record and reports work in
    progress — `would_heal shift_start=…17:00`.
    """
    workspace, worker = await _clocked_out_worker(db_session)

    outcome = await heal_current_shift(
        db_session, workspace.client_id, worker.client_id, DAY_START, NOW, execute=False
    )

    assert outcome == "skipped_no_current_shift_activity"


async def test_execute_writes_nothing_for_a_worker_who_clocked_out(db_session) -> None:
    """The consequence, asserted separately from the outcome tag.

    A dry run reporting the wrong thing is a bug; `--execute` acting on it is the damage —
    a `STARTED_SHIFT` at the clock-out instant and a reopened tail, leaving a worker who has
    gone home with an open shift running to now.
    """
    workspace, worker = await _clocked_out_worker(db_session)
    before = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))

    outcome = await heal_current_shift(
        db_session, workspace.client_id, worker.client_id, DAY_START, NOW, execute=True
    )

    assert outcome == "skipped_no_current_shift_activity"
    after = _shape(await _shift_records(db_session, workspace.client_id, worker.client_id))
    assert after == before, "healing a closed shift must write nothing at all"
    assert not [row for row in await _shift_records(
        db_session, workspace.client_id, worker.client_id
    ) if row.exited_at is None], "a clocked-out worker must not be left with an open shift"


async def test_worker_still_mid_shift_is_healed(db_session) -> None:
    """The other half: the fix must not turn the script into a no-op.

    The script's primary case — a worker mid-shift whose shift-opening was never recorded,
    so there is no marker at all. They still get one written at the shift's real start, the
    middle rebuilt, and the tail left open for the live derivation to extend.
    """
    workspace, worker = await _seed_workspace_and_worker(db_session)
    await _seed_open_working_step(db_session, workspace, worker, entered_at=STEP_STARTED)

    outcome = await heal_current_shift(
        db_session, workspace.client_id, worker.client_id, DAY_START, NOW, execute=True
    )

    assert outcome.startswith("healed "), outcome
    assert f"shift_start={STEP_STARTED.isoformat()}" in outcome

    rows = await _shift_records(db_session, workspace.client_id, worker.client_id)
    markers = [r for r in rows if r.state is UserShiftStateEnum.STARTED_SHIFT]
    assert len(markers) == 1
    assert markers[0].entered_at == STEP_STARTED
    # No ended-shift marker, and exactly one open segment — the shift is still running.
    assert not [r for r in rows if r.state is UserShiftStateEnum.ENDED_SHIFT]
    open_rows = [r for r in rows if r.exited_at is None]
    assert len(open_rows) == 1
    assert open_rows[0].state is UserShiftStateEnum.WORKING


async def test_worker_who_clocked_back_in_after_clocking_out_is_still_healed(
    db_session,
) -> None:
    """The exclusion must be narrow: it removes the clock-out marker, not the shift after it.

    A worker who clocked out at 17:00 and started again at 17:30 is mid-shift, and their
    second shift begins at the work they did — not at the clock-out that preceded it.
    """
    workspace, worker = await _clocked_out_worker(db_session)
    resumed_at = CLOCK_OUT + timedelta(minutes=30)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, resumed_at, worker.client_id
    )
    await _seed_open_working_step(db_session, workspace, worker, entered_at=resumed_at)

    outcome = await heal_current_shift(
        db_session, workspace.client_id, worker.client_id, DAY_START, NOW, execute=True
    )

    assert outcome.startswith("healed "), outcome
    assert f"shift_start={resumed_at.isoformat()}" in outcome
