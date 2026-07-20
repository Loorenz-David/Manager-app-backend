from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import delete, func, select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
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
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
)
from beyo_manager.services.commands.users.clock_in_worker_shift import clock_in_worker_shift
from beyo_manager.services.commands.users.clock_out_worker_shift import clock_out_worker_shift
from beyo_manager.services.commands.users.pause_worker_shift import pause_worker_shift
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.commands.users.resume_worker_shift import resume_worker_shift
from beyo_manager.services.commands.users.toggle_worker_shift import toggle_worker_shift
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.tasks.users.auto_clock_out_open_shifts import (
    handle_auto_clock_out_open_shifts,
)


pytestmark = pytest.mark.asyncio


async def _seed_user(db_session, label: str) -> User:
    suffix = uuid4().hex
    user = User(
        username=f"{label}-{suffix}",
        email=f"{label}-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_workspace_worker(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex
    workspace = Workspace(name=f"worker-shift-{suffix}")
    worker = await _seed_user(db_session, "shift-worker")
    db_session.add(workspace)
    await db_session.flush()
    worker_role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one()
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


def _ctx(
    db_session,
    workspace: Workspace,
    actor: User,
    role_name: str,
    incoming_data: dict | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": actor.client_id,
            "role_name": role_name,
        },
        incoming_data=incoming_data or {},
        session=db_session,
    )


async def _seed_open_step(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    state: TaskStepStateEnum,
    entered_at: datetime,
) -> TaskStep:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"shift-command-section-{suffix}",
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
    reason = (
        StepEventReasonEnum.PAUSE_LUNCH_BREAK
        if state is TaskStepStateEnum.PAUSED
        else None
    )
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=state,
        reason=reason,
        entered_at=entered_at,
        exited_at=None,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    return step


async def _open_shift_record(db_session, workspace_id: str, user_id: str):
    return (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def _seed_step_record(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    reason: StepEventReasonEnum | None = None,
) -> None:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id, name=f"recon-{suffix}", created_by_id=worker.client_id,
    )
    task = Task(
        workspace_id=workspace.client_id, task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.PENDING, created_by_id=worker.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id, task_id=task.client_id, state=state,
        working_section_id=section.client_id, assigned_worker_id=worker.client_id,
        created_by_id=worker.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    db_session.add(
        StepStateRecord(
            workspace_id=workspace.client_id, step_id=step.client_id, state=state, reason=reason,
            entered_at=entered_at, exited_at=exited_at,
            created_by_id=worker.client_id, credited_user_id=worker.client_id,
        )
    )
    await db_session.flush()


_MARKER_RANK = {UserShiftStateEnum.STARTED_SHIFT: 0, UserShiftStateEnum.ENDED_SHIFT: 2}


async def _ordered_shift_records(db_session, workspace_id: str, user_id: str):
    recs = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
            )
        )
    ).scalars().all()
    return sorted(recs, key=lambda r: (r.entered_at, _MARKER_RANK.get(r.state, 1)))


def _minute_seq(records, base: datetime):
    def m(dt: datetime) -> int:
        return round((dt - base).total_seconds() / 60)

    return [(r.state, m(r.entered_at), m(r.exited_at)) for r in records]


async def test_clock_out_reconstructs_middle_from_step_history(db_session) -> None:
    # Reproduces the "analytics worker was down during the shift" case: step activity is
    # recorded but the live reconcile never ran, so no working/pause/idle shift records
    # exist. Clock-out must rebuild the full middle from step history.
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(m: int) -> datetime:
        return base + timedelta(minutes=m)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    # No reconcile between these — the worker was "down".
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=at(5), exited_at=at(20))
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.PAUSED,
                            entered_at=at(20), exited_at=at(30),
                            reason=StepEventReasonEnum.WAITING_FOR_UPHOLSTERY)
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=at(30), exited_at=at(45))

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, at(50), worker.client_id
    )

    records = await _ordered_shift_records(db_session, workspace.client_id, worker.client_id)
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 5),
        (UserShiftStateEnum.WORKING, 5, 20),
        (UserShiftStateEnum.IN_PAUSE, 20, 30),
        (UserShiftStateEnum.WORKING, 30, 45),
        (UserShiftStateEnum.IDLE, 45, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    pause = next(r for r in records if r.state is UserShiftStateEnum.IN_PAUSE)
    assert pause.reason == "waiting_for_upholstery"
    assert pause.manually_recorded is False
    assert await _open_shift_record(db_session, workspace.client_id, worker.client_id) is None


async def test_clock_out_excludes_carryover_pause_from_previous_day(db_session) -> None:
    # A step paused yesterday and still open at today's clock-in must NOT label this shift's
    # pre-work time with yesterday's reason — that time is idle until the worker acts today.
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 8, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    # Paused since YESTERDAY, resolved 20 min into today's shift.
    await _seed_step_record(
        db_session, workspace, worker, state=TaskStepStateEnum.PAUSED,
        entered_at=base - timedelta(days=1), exited_at=base + timedelta(minutes=20),
        reason=StepEventReasonEnum.PAUSE_LUNCH_BREAK,
    )
    # Real work starts 20 min in (a fresh working record entered during the shift).
    await _seed_step_record(
        db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
        entered_at=base + timedelta(minutes=20), exited_at=base + timedelta(minutes=50),
    )
    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base + timedelta(minutes=60), worker.client_id
    )
    assert await _ordered_shift_records(db_session, workspace.client_id, worker.client_id) is not None
    seq = _minute_seq(
        await _ordered_shift_records(db_session, workspace.client_id, worker.client_id), base
    )
    assert seq == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 20),  # pre-work idle, NOT yesterday's lunch
        (UserShiftStateEnum.WORKING, 20, 50),
        (UserShiftStateEnum.IDLE, 50, 60),
        (UserShiftStateEnum.ENDED_SHIFT, 60, 60),
    ]


async def test_clock_out_empty_shift_is_idle_throughout(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base + timedelta(minutes=30), worker.client_id
    )
    records = await _ordered_shift_records(db_session, workspace.client_id, worker.client_id)
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 30),
        (UserShiftStateEnum.ENDED_SHIFT, 30, 30),
    ]


async def test_clock_out_preserves_manual_pause(db_session) -> None:
    # A manual shift pause (created synchronously, so always present) must survive the
    # clock-out rebuild — re-emitted as IN_PAUSE with manually_recorded=True and its reason.
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace.client_id, user_id=worker.client_id,
            state=UserShiftStateEnum.IN_PAUSE,
            entered_at=base + timedelta(minutes=10), exited_at=base + timedelta(minutes=20),
            changed_by_id=worker.client_id, reason="cleaning station", manually_recorded=True,
        )
    )
    await db_session.flush()

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base + timedelta(minutes=30), worker.client_id
    )

    records = await _ordered_shift_records(db_session, workspace.client_id, worker.client_id)
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 10),
        (UserShiftStateEnum.IN_PAUSE, 10, 20),
        (UserShiftStateEnum.IDLE, 20, 30),
        (UserShiftStateEnum.ENDED_SHIFT, 30, 30),
    ]
    manual = next(r for r in records if r.state is UserShiftStateEnum.IN_PAUSE)
    assert manual.manually_recorded is True
    assert manual.reason == "cleaning station"


async def test_clock_toggle_clocks_in_then_out(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    ctx = _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)

    clock_in_result = await toggle_worker_shift(ctx)
    clocked_in = await _open_shift_record(db_session, workspace.client_id, worker.client_id)
    clock_out_result = await toggle_worker_shift(ctx)

    markers = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == worker.client_id,
                UserShiftStateRecord.state.in_(
                    (UserShiftStateEnum.STARTED_SHIFT, UserShiftStateEnum.ENDED_SHIFT)
                ),
            )
        )
    ).scalars().all()
    assert clock_in_result["action"] == "clock_in"
    assert clocked_in.state is UserShiftStateEnum.IDLE
    assert clock_out_result["action"] == "clock_out"
    assert await _open_shift_record(db_session, workspace.client_id, worker.client_id) is None
    assert {marker.state for marker in markers} == {
        UserShiftStateEnum.STARTED_SHIFT,
        UserShiftStateEnum.ENDED_SHIFT,
    }
    assert all(marker.entered_at == marker.exited_at for marker in markers)


async def test_direct_clock_in_rejects_existing_open_shift(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    ctx = _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    await clock_in_worker_shift(ctx)

    with pytest.raises(ConflictError):
        await clock_in_worker_shift(ctx)


async def test_manager_can_clock_worker_on_behalf_and_worker_cannot_clock_peer(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    manager = await _seed_user(db_session, "shift-manager")
    manager_ctx = _ctx(
        db_session,
        workspace,
        manager,
        RoleNameEnum.MANAGER.value,
        {"user_id": worker.client_id},
    )

    await clock_in_worker_shift(manager_ctx)
    open_record = await _open_shift_record(db_session, workspace.client_id, worker.client_id)

    assert open_record.changed_by_id == manager.client_id

    peer = await _seed_user(db_session, "shift-peer")
    peer_ctx = _ctx(
        db_session,
        workspace,
        worker,
        RoleNameEnum.WORKER.value,
        {"user_id": peer.client_id},
    )
    with pytest.raises(PermissionDenied):
        await clock_in_worker_shift(peer_ctx)


async def test_clock_out_transitions_working_steps_and_leaves_paused_steps_open(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    now = datetime.now(timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        now - timedelta(hours=1),
        worker.client_id,
    )
    working_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(minutes=40),
    )
    paused_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=now - timedelta(minutes=20),
    )
    ctx = _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)

    result = await clock_out_worker_shift(ctx)
    await db_session.refresh(working_step)
    await db_session.refresh(paused_step)

    paused_open = await db_session.scalar(
        select(func.count(StepStateRecord.client_id)).where(
            StepStateRecord.workspace_id == workspace.client_id,
            StepStateRecord.step_id == paused_step.client_id,
            StepStateRecord.state == TaskStepStateEnum.PAUSED,
            StepStateRecord.exited_at.is_(None),
        )
    )
    transition_tasks = await db_session.scalar(
        select(func.count(ExecutionTask.client_id)).where(
            ExecutionTask.task_type == TaskType.PROCESS_STEP_TRANSITION
        )
    )
    assert result["transitioned_steps"] == 1
    assert working_step.state is TaskStepStateEnum.ENDED_SHIFT
    assert paused_step.state is TaskStepStateEnum.PAUSED
    assert paused_open == 1
    assert transition_tasks >= 1


async def test_manual_pause_is_sticky_until_work_starts_and_resume_requires_manual_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    ctx = _ctx(
        db_session,
        workspace,
        worker,
        RoleNameEnum.WORKER.value,
        {"reason": "  Team meeting  "},
    )
    await clock_in_worker_shift(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )
    await pause_worker_shift(ctx)
    manual_pause = await _open_shift_record(db_session, workspace.client_id, worker.client_id)

    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        datetime.now(timezone.utc),
    )
    still_paused = await _open_shift_record(db_session, workspace.client_id, worker.client_id)
    await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=datetime.now(timezone.utc),
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        datetime.now(timezone.utc),
    )
    working = await _open_shift_record(db_session, workspace.client_id, worker.client_id)

    assert manual_pause.manually_recorded is True
    assert manual_pause.reason == "Team meeting"
    assert manual_pause.changed_by_id == worker.client_id
    assert still_paused.client_id == manual_pause.client_id
    assert working.state is UserShiftStateEnum.WORKING
    with pytest.raises(ConflictError):
        await resume_worker_shift(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )


async def test_resume_manual_pause_opens_idle(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_worker_shift(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )
    await pause_worker_shift(
        _ctx(
            db_session,
            workspace,
            worker,
            RoleNameEnum.WORKER.value,
            {"reason": "Lunch"},
        )
    )

    result = await resume_worker_shift(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    current = await _open_shift_record(db_session, workspace.client_id, worker.client_id)
    assert result["state"] == UserShiftStateEnum.IDLE.value
    assert current.state is UserShiftStateEnum.IDLE
    assert current.manually_recorded is False


@freeze_time("2026-07-15T09:00:00+00:00")
async def test_midnight_safeguard_closes_previous_day_shift_and_allows_new_day(
    db_session,
) -> None:
    # This test must commit (the safeguard runs in its own DB session and only sees
    # committed rows), and the safeguard scans shift records GLOBALLY. So we (a) freeze
    # time for deterministic midnight math, (b) clear any open shift records left behind
    # by earlier committed runs before exercising the global scan, and (c) delete this
    # test's committed rows in a finally so it never pollutes later runs.
    workspace, worker = await _seed_workspace_worker(db_session)
    # Clean slate for the global scan: drop leftover open records from prior committed runs.
    await db_session.execute(
        delete(UserShiftStateRecord).where(UserShiftStateRecord.exited_at.is_(None))
    )
    await db_session.flush()
    midnight = datetime.combine(
        datetime.now(timezone.utc).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    try:
        await clock_in_shift_for_user(
            db_session,
            workspace.client_id,
            worker.client_id,
            midnight - timedelta(hours=16),
            worker.client_id,
        )
        current = await _open_shift_record(db_session, workspace.client_id, worker.client_id)
        current.exited_at = midnight - timedelta(hours=8)
        db_session.add(
            UserShiftStateRecord(
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                state=UserShiftStateEnum.IN_PAUSE,
                entered_at=midnight - timedelta(hours=8),
                exited_at=None,
                changed_by_id=worker.client_id,
                reason="Late lunch",
                manually_recorded=True,
            )
        )
        await db_session.commit()

        await handle_auto_clock_out_open_shifts({}, "task_midnight_test")

        async for session in get_db_session():
            ended = (
                await session.execute(
                    select(UserShiftStateRecord).where(
                        UserShiftStateRecord.workspace_id == workspace.client_id,
                        UserShiftStateRecord.user_id == worker.client_id,
                        UserShiftStateRecord.state == UserShiftStateEnum.ENDED_SHIFT,
                    )
                )
            ).scalar_one()
            assert ended.entered_at == midnight
            assert ended.exited_at == midnight
            assert ended.changed_by_id is None
            assert await _open_shift_record(session, workspace.client_id, worker.client_id) is None

        result = await clock_in_worker_shift(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )
        assert result["action"] == "clock_in"
    finally:
        # Remove everything this test committed so the shared DB stays clean.
        await db_session.execute(
            delete(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id
            )
        )
        await db_session.commit()
