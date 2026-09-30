"""A shift that outlives its work day is closed at its OWN boundary (units B-8, B-9).

Owner decisions (2026-09-30): the work day ends at UTC midnight; an open shift that survives
it is closed at ``work_day_end(started_at)`` — never at "now" — whoever notices first (the
nightly sweep, however late, or any shift command / reconcile); work after the boundary
belongs to the next day; `GET /current` stays read-only and reports the stale shift as not
clocked in.

The sweep runs in its own session in production. Here it is handed the test session through
a thin wrapper whose ``begin()`` joins the already-open test transaction, so nothing commits
and the fixture's rollback cleans up.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import delete, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
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
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users._clock_worker_shift import clock_in_shift_for_user
from beyo_manager.services.commands.users.clock_in_worker_shift import clock_in_worker_shift
from beyo_manager.services.commands.users.clock_out_worker_shift import clock_out_worker_shift
from beyo_manager.services.commands.users.close_declared_worker_state import (
    close_declared_worker_state,
)
from beyo_manager.services.commands.users.declare_worker_state import declare_worker_state
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.commands.users.toggle_worker_shift import toggle_worker_shift
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_current_worker_shift_state import (
    get_current_worker_shift_state,
)
from beyo_manager.services.tasks.users import auto_clock_out_open_shifts as sweep_module
from tests.fixtures.phase2_row_factories import adopt_or_create_role, create_test_workspace


pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
TODAY = datetime(2026, 7, 15, tzinfo=timezone.utc)
YESTERDAY = TODAY - timedelta(days=1)


# --- seeding -----------------------------------------------------------------------


async def _seed_workspace_worker(db_session) -> tuple[Workspace, User]:
    workspace = await create_test_workspace(db_session, "stale-shift-workspace")
    suffix = uuid4().hex
    worker = User(
        username=f"stale-shift-worker-{suffix}",
        email=f"stale-shift-worker-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(worker)
    await db_session.flush()
    worker_role = await adopt_or_create_role(db_session, RoleNameEnum.WORKER)
    workspace_role = await db_session.scalar(
        select(WorkspaceRole).where(
            WorkspaceRole.workspace_id == workspace.client_id,
            WorkspaceRole.role_id == worker_role.client_id,
            WorkspaceRole.specialization.is_(None),
        )
    )
    if workspace_role is None:
        workspace_role = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=worker_role.client_id,
            is_system=True,
        )
        db_session.add(workspace_role)
        await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            user_id=worker.client_id,
            workspace_id=workspace.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return workspace, worker


def _ctx(db_session, workspace: Workspace, worker: User, incoming_data=None) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": worker.client_id,
            "role_name": RoleNameEnum.WORKER.value,
        },
        incoming_data=incoming_data or {},
        query_params={"user_id": None},
        session=db_session,
    )


async def _seed_open_step(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    entered_at: datetime,
    state: TaskStepStateEnum = TaskStepStateEnum.WORKING,
) -> TaskStep:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"stale-shift-section-{suffix}",
        created_by_id=worker.client_id,
    )
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=worker.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=state,
        working_section_id=section.client_id,
        assigned_worker_id=worker.client_id,
        created_by_id=worker.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=state,
        entered_at=entered_at,
        exited_at=None,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def _seed_personal_reason(db_session, workspace: Workspace, worker: User) -> PauseReason:
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Stale shift reason {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


async def _project(db_session, workspace, worker, state, entered_at, *, reason=None) -> None:
    """Simulate the pre-fix live reconcile appending a projection to the open shift."""
    open_row = await _open_row(db_session, workspace, worker)
    open_row.exited_at = entered_at
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            state=state,
            entered_at=entered_at,
            exited_at=None,
            changed_by_id=None,
            reason=reason,
            manually_recorded=False,
        )
    )
    await db_session.flush()


async def _shift_records(db_session, workspace, worker) -> list[UserShiftStateRecord]:
    rank = {UserShiftStateEnum.STARTED_SHIFT: 0, UserShiftStateEnum.ENDED_SHIFT: 2}
    records = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == worker.client_id,
            )
        )
    ).scalars().all()
    return sorted(records, key=lambda r: (r.entered_at, rank.get(r.state, 1)))


async def _open_row(db_session, workspace, worker) -> UserShiftStateRecord | None:
    return (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == worker.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def _markers(db_session, workspace, worker, state) -> list[datetime]:
    return [
        record.entered_at
        for record in await _shift_records(db_session, workspace, worker)
        if record.state is state
    ]


async def _step_records(db_session, step: TaskStep) -> list[StepStateRecord]:
    return list(
        (
            await db_session.execute(
                select(StepStateRecord)
                .where(StepStateRecord.step_id == step.client_id)
                .order_by(StepStateRecord.entered_at)
            )
        ).scalars().all()
    )


def _assert_shift_inside(records, start: datetime, end: datetime) -> None:
    """Every record of the shift started at ``start`` ends by ``end``, none backwards."""
    in_shift = [r for r in records if start <= r.entered_at < end]
    assert in_shift
    for record in in_shift:
        assert record.exited_at is not None, record.state
        assert record.entered_at <= record.exited_at <= end, (
            record.state,
            record.entered_at,
            record.exited_at,
        )


# --- the sweep (B-8) -----------------------------------------------------------------


class _JoinedSession:
    """The test session, with ``begin()`` joining the transaction already in progress."""

    def __init__(self, session) -> None:
        self._session = session

    def begin(self):
        return maybe_begin(self._session)

    def __getattr__(self, name):
        return getattr(self._session, name)


@pytest.fixture
def run_sweep(db_session, monkeypatch):
    emitted: list[tuple[str, str, list[str]]] = []

    async def _sessions():
        yield _JoinedSession(db_session)

    async def _emit_state(session, workspace_id, user_id):
        emitted.append(("state", workspace_id, [user_id]))

    async def _emit_paused(workspace_id, step_ids):
        emitted.append(("paused", workspace_id, list(step_ids)))

    monkeypatch.setattr(sweep_module, "get_db_session", _sessions)
    monkeypatch.setattr(sweep_module, "emit_worker_shift_state", _emit_state)
    monkeypatch.setattr(sweep_module, "emit_steps_paused", _emit_paused)

    async def _run():
        await sweep_module.handle_auto_clock_out_open_shifts({}, "task_stale_shift_test")
        return emitted

    return _run


async def _clean_slate(db_session) -> None:
    # The sweep scans globally; open rows another test left committed are not ours.
    await db_session.execute(
        delete(UserShiftStateRecord).where(UserShiftStateRecord.exited_at.is_(None))
    )
    await db_session.flush()


@freeze_time(NOW)
async def test_sweep_closes_each_stale_shift_at_its_own_midnight(db_session, run_sweep) -> None:
    await _clean_slate(db_session)
    ws_1, one_day = await _seed_workspace_worker(db_session)
    ws_3, three_days = await _seed_workspace_worker(db_session)
    ws_t, today = await _seed_workspace_worker(db_session)
    one_day_start = YESTERDAY + timedelta(hours=8)
    three_days_start = TODAY - timedelta(days=3) + timedelta(hours=8)
    await clock_in_shift_for_user(
        db_session, ws_1.client_id, one_day.client_id, one_day_start, one_day.client_id
    )
    await clock_in_shift_for_user(
        db_session, ws_3.client_id, three_days.client_id, three_days_start, three_days.client_id
    )
    await clock_in_shift_for_user(
        db_session, ws_t.client_id, today.client_id, TODAY + timedelta(hours=6), today.client_id
    )

    await run_sweep()

    one_day_records = await _shift_records(db_session, ws_1, one_day)
    three_day_records = await _shift_records(db_session, ws_3, three_days)
    assert await _markers(db_session, ws_1, one_day, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    # Its own midnight — not today's, which would have made a 64-hour shift.
    assert await _markers(db_session, ws_3, three_days, UserShiftStateEnum.ENDED_SHIFT) == [
        TODAY - timedelta(days=2)
    ]
    assert await _open_row(db_session, ws_1, one_day) is None
    assert await _open_row(db_session, ws_3, three_days) is None
    _assert_shift_inside(one_day_records, one_day_start, TODAY)
    _assert_shift_inside(three_day_records, three_days_start, TODAY - timedelta(days=2))
    ended = next(r for r in three_day_records if r.state is UserShiftStateEnum.ENDED_SHIFT)
    assert ended.changed_by_id is None
    # Today's shift is inside its work day and untouched.
    assert await _markers(db_session, ws_t, today, UserShiftStateEnum.ENDED_SHIFT) == []
    assert await _open_row(db_session, ws_t, today) is not None


@freeze_time(NOW)
async def test_sweep_is_idempotent(db_session, run_sweep) -> None:
    await _clean_slate(db_session)
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        TODAY - timedelta(days=3) + timedelta(hours=8),
        worker.client_id,
    )

    await run_sweep()
    first = [
        (r.client_id, r.state, r.entered_at, r.exited_at)
        for r in await _shift_records(db_session, workspace, worker)
    ]
    await run_sweep()
    second = [
        (r.client_id, r.state, r.entered_at, r.exited_at)
        for r in await _shift_records(db_session, workspace, worker)
    ]

    assert first == second
    assert [row[1] for row in first].count(UserShiftStateEnum.ENDED_SHIFT) == 1


@freeze_time(NOW)
async def test_sweep_leaves_post_boundary_work_to_the_new_day_opened_by_reconcile(
    db_session, run_sweep
) -> None:
    await _clean_slate(db_session)
    workspace, worker = await _seed_workspace_worker(db_session)
    shift_start = YESTERDAY + timedelta(hours=8)
    before_step_start = YESTERDAY + timedelta(hours=22)
    after_step_start = TODAY + timedelta(hours=7)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, shift_start, worker.client_id
    )
    # Worked across midnight on one step, and started another this morning — while the
    # stale shift was still open, so the (pre-fix) live reconcile projected today's work
    # onto it, and a declaration made and closed this morning is on record too.
    before_step = await _seed_open_step(db_session, workspace, worker, entered_at=before_step_start)
    await _project(db_session, workspace, worker, UserShiftStateEnum.WORKING, before_step_start)
    after_step = await _seed_open_step(db_session, workspace, worker, entered_at=after_step_start)
    await _project(db_session, workspace, worker, UserShiftStateEnum.WORKING, after_step_start)
    reason = await _seed_personal_reason(db_session, workspace, worker)
    morning_declaration = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=reason.client_id,
        entered_at=TODAY + timedelta(hours=6),
        exited_at=TODAY + timedelta(hours=6, minutes=30),
        created_by_id=worker.client_id,
    )
    db_session.add(morning_declaration)
    await db_session.flush()

    emitted = await run_sweep()

    records = await _shift_records(db_session, workspace, worker)
    # The old shift: closed at its own midnight, nothing in it reaches past it.
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    _assert_shift_inside(records, shift_start, TODAY)
    old_shift_middle = [
        (r.state, r.entered_at, r.exited_at)
        for r in records
        if r.state not in (UserShiftStateEnum.STARTED_SHIFT, UserShiftStateEnum.ENDED_SHIFT)
        and r.entered_at < TODAY
    ]
    assert old_shift_middle == [
        (UserShiftStateEnum.IDLE, shift_start, before_step_start),
        (UserShiftStateEnum.WORKING, before_step_start, TODAY),
    ]
    # The step worked across midnight is paused AT midnight, as ended-shift.
    before_records = await _step_records(db_session, before_step)
    assert [(r.state, r.entered_at, r.exited_at) for r in before_records] == [
        (TaskStepStateEnum.WORKING, before_step_start, TODAY),
        (TaskStepStateEnum.PAUSED, TODAY, None),
    ]
    assert before_records[1].transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    # This morning's step is the new day's: untouched, still working.
    after_records = await _step_records(db_session, after_step)
    assert [(r.state, r.entered_at, r.exited_at) for r in after_records] == [
        (TaskStepStateEnum.WORKING, after_step_start, None),
    ]
    # ...and the reconcile opened the new day's shift from it.
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.STARTED_SHIFT) == [
        shift_start,
        after_step_start,
    ]
    open_row = await _open_row(db_session, workspace, worker)
    assert open_row is not None
    assert open_row.state is UserShiftStateEnum.WORKING
    assert open_row.entered_at == NOW
    # The morning declaration is left exactly as recorded.
    await db_session.refresh(morning_declaration)
    assert morning_declaration.exited_at == TODAY + timedelta(hours=6, minutes=30)
    assert ("paused", workspace.client_id, [before_step.client_id]) in emitted

    # Idempotent: the new day's shift is inside its work day; nothing changes.
    before = [(r.client_id, r.entered_at, r.exited_at) for r in records]
    await run_sweep()
    after = [
        (r.client_id, r.entered_at, r.exited_at)
        for r in await _shift_records(db_session, workspace, worker)
    ]
    assert after == before


@freeze_time(NOW)
async def test_sweep_closes_a_post_boundary_open_declaration_where_it_began(
    db_session, run_sweep
) -> None:
    await _clean_slate(db_session)
    workspace, worker = await _seed_workspace_worker(db_session)
    shift_start = YESTERDAY + timedelta(hours=8)
    declared_at = TODAY + timedelta(hours=7, minutes=30)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, shift_start, worker.client_id
    )
    reason = await _seed_personal_reason(db_session, workspace, worker)
    declaration = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=reason.client_id,
        entered_at=declared_at,
        exited_at=None,
        created_by_id=worker.client_id,
    )
    db_session.add(declaration)
    await _project(
        db_session,
        workspace,
        worker,
        UserShiftStateEnum.IN_PAUSE,
        declared_at,
        reason=reason.client_id,
    )

    await run_sweep()

    await db_session.refresh(declaration)
    # Closing it at the boundary would be a negative span; it is not the old shift's.
    assert declaration.exited_at == declared_at
    assert declaration.closed_by_id is None
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _open_row(db_session, workspace, worker) is None
    _assert_shift_inside(await _shift_records(db_session, workspace, worker), shift_start, TODAY)


# --- the kiosk and the other shift commands (B-9) --------------------------------------


async def _stale_shift(db_session) -> tuple[Workspace, User, datetime]:
    workspace, worker = await _seed_workspace_worker(db_session)
    shift_start = YESTERDAY + timedelta(hours=8)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, shift_start, worker.client_id
    )
    return workspace, worker, shift_start


async def test_current_reports_a_stale_shift_as_not_clocked_in_without_writing(
    db_session,
) -> None:
    workspace, worker, _ = await _stale_shift(db_session)
    before = [
        (r.client_id, r.state, r.entered_at, r.exited_at)
        for r in await _shift_records(db_session, workspace, worker)
    ]

    with freeze_time(NOW):
        result = await get_current_worker_shift_state(_ctx(db_session, workspace, worker))

    assert result == {
        "user_id": worker.client_id,
        "clocked_in": False,
        "shift_started_at": None,
        "state": None,
        "state_entered_at": None,
        "pause_reason": None,
        "declared_state": None,
        "stale_shift_closed_at": TODAY.isoformat(),
    }
    # Read-only: the shift is still open in the database until a write closes it.
    after = [
        (r.client_id, r.state, r.entered_at, r.exited_at)
        for r in await _shift_records(db_session, workspace, worker)
    ]
    assert after == before
    assert await _open_row(db_session, workspace, worker) is not None


async def test_clock_in_on_a_stale_shift_closes_it_at_its_boundary_and_opens_a_new_one(
    db_session,
) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)
    step = await _seed_open_step(
        db_session, workspace, worker, entered_at=YESTERDAY + timedelta(hours=10)
    )

    with freeze_time(NOW):
        result = await clock_in_worker_shift(_ctx(db_session, workspace, worker))
        current = await get_current_worker_shift_state(_ctx(db_session, workspace, worker))

    assert result == {"action": "clock_in", "user_id": worker.client_id}
    records = await _shift_records(db_session, workspace, worker)
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.STARTED_SHIFT) == [
        shift_start,
        NOW,
    ]
    _assert_shift_inside(records, shift_start, TODAY)
    open_row = await _open_row(db_session, workspace, worker)
    assert (open_row.state, open_row.entered_at) == (UserShiftStateEnum.IDLE, NOW)
    step_records = await _step_records(db_session, step)
    assert step_records[-1].state is TaskStepStateEnum.PAUSED
    assert step_records[-1].entered_at == TODAY
    assert current["clocked_in"] is True
    assert current["shift_started_at"] == NOW.isoformat()
    assert current["stale_shift_closed_at"] is None


async def test_toggle_on_a_stale_shift_closes_it_at_its_boundary_then_clocks_in(
    db_session,
) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)
    step = await _seed_open_step(
        db_session, workspace, worker, entered_at=YESTERDAY + timedelta(hours=10)
    )

    with freeze_time(NOW):
        result = await toggle_worker_shift(_ctx(db_session, workspace, worker))

    # Yesterday's shift is never closed at the tap time; the tap is the new day's clock-in.
    assert result == {
        "action": "clock_in",
        "user_id": worker.client_id,
        "transitioned_steps": 1,
    }
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.STARTED_SHIFT) == [
        shift_start,
        NOW,
    ]
    _assert_shift_inside(await _shift_records(db_session, workspace, worker), shift_start, TODAY)
    assert (await _step_records(db_session, step))[-1].entered_at == TODAY


async def test_clock_out_on_a_stale_shift_closes_it_at_its_boundary_not_now(
    db_session,
) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)

    with freeze_time(NOW):
        result = await clock_out_worker_shift(_ctx(db_session, workspace, worker))

    assert result["action"] == "clock_out"
    assert result["_clock_out_at"] == TODAY
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _open_row(db_session, workspace, worker) is None
    _assert_shift_inside(await _shift_records(db_session, workspace, worker), shift_start, TODAY)


async def test_declare_on_a_stale_shift_closes_it_and_refuses(db_session) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)
    reason = await _seed_personal_reason(db_session, workspace, worker)

    with freeze_time(NOW):
        with pytest.raises(ConflictError, match="must be clocked in"):
            await declare_worker_state(
                _ctx(db_session, workspace, worker, {"pause_reason_id": reason.client_id})
            )

    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _open_row(db_session, workspace, worker) is None


async def test_close_declared_on_a_stale_shift_closes_it_at_its_boundary_and_refuses(
    db_session,
) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)
    reason = await _seed_personal_reason(db_session, workspace, worker)
    declaration = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=reason.client_id,
        entered_at=YESTERDAY + timedelta(hours=15),
        exited_at=None,
        created_by_id=worker.client_id,
    )
    db_session.add(declaration)
    await db_session.flush()

    with freeze_time(NOW):
        with pytest.raises(ConflictError, match="No declared state is open"):
            await close_declared_worker_state(_ctx(db_session, workspace, worker))

    await db_session.refresh(declaration)
    assert declaration.exited_at == TODAY
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]


async def test_reconcile_on_a_stale_shift_closes_it_and_opens_the_new_day_from_working_step(
    db_session,
) -> None:
    workspace, worker, shift_start = await _stale_shift(db_session)
    after_step_start = TODAY + timedelta(hours=7)
    after_step = await _seed_open_step(db_session, workspace, worker, entered_at=after_step_start)

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, worker.client_id, NOW
    )

    assert outcome.changed is True
    assert outcome.auto_clocked_in is True
    assert outcome.state is UserShiftStateEnum.WORKING
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [TODAY]
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.STARTED_SHIFT) == [
        shift_start,
        after_step_start,
    ]
    _assert_shift_inside(await _shift_records(db_session, workspace, worker), shift_start, TODAY)
    assert [r.state for r in await _step_records(db_session, after_step)] == [
        TaskStepStateEnum.WORKING
    ]


async def test_reconcile_closes_a_chain_of_finished_days_each_at_its_own_boundary(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    first_start = TODAY - timedelta(days=3) + timedelta(hours=8)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, first_start, worker.client_id
    )
    # A step started the next day and never stopped: its day is over too.
    step_start = TODAY - timedelta(days=2) + timedelta(hours=10)
    step = await _seed_open_step(db_session, workspace, worker, entered_at=step_start)

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, worker.client_id, NOW
    )

    assert outcome.state is None
    assert outcome.changed is True
    assert outcome.paused_step_ids == (step.client_id,)
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.STARTED_SHIFT) == [
        first_start,
        step_start,
    ]
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [
        TODAY - timedelta(days=2),
        TODAY - timedelta(days=1),
    ]
    assert await _open_row(db_session, workspace, worker) is None
    step_records = await _step_records(db_session, step)
    assert [(r.state, r.entered_at, r.exited_at) for r in step_records] == [
        (TaskStepStateEnum.WORKING, step_start, TODAY - timedelta(days=1)),
        (TaskStepStateEnum.PAUSED, TODAY - timedelta(days=1), None),
    ]


async def test_in_day_shift_behaviour_is_unchanged(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    shift_start = TODAY + timedelta(hours=7)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, shift_start, worker.client_id
    )

    with freeze_time(NOW):
        current = await get_current_worker_shift_state(_ctx(db_session, workspace, worker))
        with pytest.raises(ConflictError, match="already clocked in"):
            await clock_in_worker_shift(_ctx(db_session, workspace, worker))
        result = await toggle_worker_shift(_ctx(db_session, workspace, worker))

    assert current["clocked_in"] is True
    assert current["shift_started_at"] == shift_start.isoformat()
    assert current["stale_shift_closed_at"] is None
    assert result["action"] == "clock_out"
    assert result["_clock_out_at"] == NOW
    assert await _markers(db_session, workspace, worker, UserShiftStateEnum.ENDED_SHIFT) == [NOW]
