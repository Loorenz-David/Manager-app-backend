import asyncio
from datetime import datetime, timedelta, timezone
from importlib import import_module
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import delete, event, func, select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
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
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users._reconstruct_shift_middle import (
    reconstruct_shift_middle,
)
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
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
    workspace = await db_session.scalar(select(Workspace).order_by(Workspace.client_id))
    worker = await _seed_user(db_session, "shift-worker")
    worker_role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one()
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
    reason = "pause_lunch_break" if state is TaskStepStateEnum.PAUSED else None
    pause_reason_id = (
        await db_session.scalar(
            select(PauseReason.client_id).where(
                PauseReason.slug == reason,
            )
        )
        if reason is not None
        else None
    )
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=state,
        pause_reason_id=pause_reason_id,
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
    reason: str | None = None,
    pause_reason_id: str | None = None,
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
    resolved_pause_reason_id = pause_reason_id
    if resolved_pause_reason_id is None:
        resolved_pause_reason_id = (
            await db_session.scalar(
                select(PauseReason.client_id).where(
                    PauseReason.slug == reason,
                )
            )
            if reason is not None
            else None
        )
    db_session.add(
        StepStateRecord(
            workspace_id=workspace.client_id, step_id=step.client_id, state=state,
            pause_reason_id=resolved_pause_reason_id,
            entered_at=entered_at, exited_at=exited_at,
            created_by_id=worker.client_id, credited_user_id=worker.client_id,
        )
    )
    await db_session.flush()


async def _seed_declared_state(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    reason: str,
    entered_at: datetime,
    exited_at: datetime | None,
) -> UserDeclaredStateRecord:
    suffix = uuid4().hex
    pause_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"{reason.replace('_', ' ').title()} {suffix}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"{reason}-{suffix}",
        created_by_id=worker.client_id,
    )
    db_session.add(pause_reason)
    await db_session.flush()
    declared = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=pause_reason.client_id,
        entered_at=entered_at,
        exited_at=exited_at,
        created_by_id=worker.client_id,
        closed_by_id=None,
    )
    db_session.add(declared)
    await db_session.flush()
    return declared


async def _seed_pause_reason(
    db_session,
    workspace: Workspace,
    actor: User,
    *,
    name: str,
    pause_type: PauseTypeEnum = PauseTypeEnum.PERSONAL,
    requires_description: bool = False,
    is_deleted: bool = False,
    image_url: str | None = None,
) -> PauseReason:
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"{name} {uuid4().hex}",
        image_url=image_url,
        pause_type=pause_type,
        requires_description=requires_description,
        created_by_id=actor.client_id,
        is_deleted=is_deleted,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


async def _run_worker_command_in_new_session(
    command,
    *,
    workspace_id: str,
    worker_id: str,
    incoming_data: dict,
):
    async for session in get_db_session():
        return await command(
            ServiceContext(
                identity={
                    "workspace_id": workspace_id,
                    "user_id": worker_id,
                    "role_name": RoleNameEnum.WORKER.value,
                },
                incoming_data=incoming_data,
                session=session,
            )
        )
    raise AssertionError("Database session generator yielded no session")


async def _cleanup_committed_worker_command_rows(
    db_session,
    *,
    workspace_id: str,
    worker_id: str,
    pause_reason_ids: list[str],
) -> None:
    await db_session.rollback()
    await db_session.execute(
        delete(UserDeclaredStateRecord).where(
            UserDeclaredStateRecord.workspace_id == workspace_id,
            UserDeclaredStateRecord.user_id == worker_id,
        )
    )
    await db_session.execute(
        delete(UserShiftStateRecord).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == worker_id,
        )
    )
    await db_session.execute(
        delete(PauseReason).where(PauseReason.client_id.in_(pause_reason_ids))
    )
    await db_session.execute(
        delete(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == worker_id,
        )
    )
    await db_session.execute(delete(User).where(User.client_id == worker_id))
    await db_session.commit()


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


async def test_full_declared_state_loop_rebuilds_all_declared_time_without_idle_collapse(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)

    def at(minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)

    reasons = [
        PauseReason(
            workspace_id=workspace.client_id,
            name=f"Cleaning {uuid4().hex}",
            pause_type=PauseTypeEnum.PERSONAL,
            created_by_id=worker.client_id,
        ),
        PauseReason(
            workspace_id=workspace.client_id,
            name=f"Meeting {uuid4().hex}",
            pause_type=PauseTypeEnum.PERSONAL,
            created_by_id=worker.client_id,
        ),
    ]
    db_session.add_all(reasons)
    await db_session.flush()
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )

    with freeze_time(at(10)):
        await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": reasons[0].client_id},
            )
        )

    working_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=at(20),
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        at(20),
    )
    open_working = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == working_step.client_id,
            StepStateRecord.state == TaskStepStateEnum.WORKING,
            StepStateRecord.exited_at.is_(None),
        )
    )
    task = await db_session.get(Task, working_step.task_id)
    await _apply_step_transition(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value),
        working_step,
        task,
        open_working,
        new_state=TaskStepStateEnum.COMPLETED,
        pause_reason_id=None,
        description=None,
        credited_user_id=worker.client_id,
        now=at(30),
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        at(30),
    )

    with freeze_time(at(40)):
        await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": reasons[1].client_id},
            )
        )
    await clock_out_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        at(50),
        worker.client_id,
    )

    declared = (
        await db_session.execute(
            select(UserDeclaredStateRecord)
            .where(
                UserDeclaredStateRecord.workspace_id == workspace.client_id,
                UserDeclaredStateRecord.user_id == worker.client_id,
            )
            .order_by(UserDeclaredStateRecord.entered_at)
        )
    ).scalars().all()
    records = await _ordered_shift_records(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert [(row.entered_at, row.exited_at) for row in declared] == [
        (at(10), at(20)),
        (at(40), at(50)),
    ]
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 10),
        (UserShiftStateEnum.IN_PAUSE, 10, 20),
        (UserShiftStateEnum.WORKING, 20, 30),
        (UserShiftStateEnum.IDLE, 30, 40),
        (UserShiftStateEnum.IN_PAUSE, 40, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    rebuilt_declared = [
        row
        for row in records
        if row.state is UserShiftStateEnum.IN_PAUSE and row.manually_recorded
    ]
    assert [row.reason for row in rebuilt_declared] == [
        reasons[0].client_id,
        reasons[1].client_id,
    ]


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
                            reason="pause_lunch_break")
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
    pause_reason_id = await db_session.scalar(
        select(PauseReason.client_id).where(PauseReason.slug == "pause_lunch_break")
    )
    assert pause.reason == pause_reason_id
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
        reason="pause_lunch_break",
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


async def test_clock_out_reconstructs_declared_intervals_and_clamps_open_source(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)

    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    await _seed_step_record(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=at(5),
        exited_at=at(15),
    )
    closed_declared = await _seed_declared_state(
        db_session,
        workspace,
        worker,
        reason="pause_coffee_break",
        entered_at=at(20),
        exited_at=at(30),
    )
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            state=UserShiftStateEnum.IN_PAUSE,
            entered_at=at(32),
            exited_at=at(35),
            changed_by_id=worker.client_id,
            reason="legacy meeting",
            manually_recorded=True,
        )
    )
    open_declared = await _seed_declared_state(
        db_session,
        workspace,
        worker,
        reason="pause_lunch_break",
        entered_at=at(40),
        exited_at=None,
    )

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, at(50), worker.client_id
    )

    await db_session.refresh(open_declared)
    records = await _ordered_shift_records(
        db_session, workspace.client_id, worker.client_id
    )
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 5),
        (UserShiftStateEnum.WORKING, 5, 15),
        (UserShiftStateEnum.IDLE, 15, 20),
        (UserShiftStateEnum.IN_PAUSE, 20, 30),
        (UserShiftStateEnum.IDLE, 30, 32),
        (UserShiftStateEnum.IN_PAUSE, 32, 35),
        (UserShiftStateEnum.IDLE, 35, 40),
        (UserShiftStateEnum.IN_PAUSE, 40, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    pauses = {
        record.entered_at: record
        for record in records
        if record.state is UserShiftStateEnum.IN_PAUSE
    }
    assert pauses[at(20)].reason == closed_declared.pause_reason_id
    assert pauses[at(20)].manually_recorded is True
    assert pauses[at(32)].reason == "legacy meeting"
    assert pauses[at(32)].manually_recorded is True
    assert pauses[at(40)].reason == open_declared.pause_reason_id
    assert pauses[at(40)].manually_recorded is True
    assert open_declared.exited_at == at(50)
    assert open_declared.closed_by_id is None


async def test_declared_pause_owns_reconstruction_overlap_with_step_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)

    step_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"step-pause-{uuid4().hex}",
        created_by_id=worker.client_id,
    )
    db_session.add(step_reason)
    await db_session.flush()
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    await _seed_step_record(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=at(5),
        exited_at=at(50),
        pause_reason_id=step_reason.client_id,
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        worker,
        reason="pause_lunch_break",
        entered_at=at(20),
        exited_at=None,
    )

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, at(50), worker.client_id
    )

    records = await _ordered_shift_records(
        db_session, workspace.client_id, worker.client_id
    )
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 5),
        (UserShiftStateEnum.IN_PAUSE, 5, 20),
        (UserShiftStateEnum.IN_PAUSE, 20, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    step_pause, declared_pause = [
        record for record in records if record.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert step_pause.reason == step_reason.client_id
    assert step_pause.manually_recorded is False
    assert declared_pause.reason == declared.pause_reason_id
    assert declared_pause.manually_recorded is True


async def test_declared_pause_owns_reconstruction_overlap_with_open_step_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)

    step_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Open step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"open-step-pause-{uuid4().hex}",
        created_by_id=worker.client_id,
    )
    db_session.add(step_reason)
    await db_session.flush()
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    await _seed_step_record(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=at(5),
        exited_at=None,
        pause_reason_id=step_reason.client_id,
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        worker,
        reason="pause_lunch_break",
        entered_at=at(20),
        exited_at=None,
    )

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, at(50), worker.client_id
    )

    records = await _ordered_shift_records(
        db_session, workspace.client_id, worker.client_id
    )
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 5),
        (UserShiftStateEnum.IN_PAUSE, 5, 20),
        (UserShiftStateEnum.IN_PAUSE, 20, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    step_pause, declared_pause = [
        record for record in records if record.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert step_pause.reason == step_reason.client_id
    assert step_pause.manually_recorded is False
    assert declared_pause.reason == declared.pause_reason_id
    assert declared_pause.manually_recorded is True


async def test_legacy_manual_pause_owns_reconstruction_after_open_step_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)

    step_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Legacy priority step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"legacy-priority-step-pause-{uuid4().hex}",
        created_by_id=worker.client_id,
    )
    db_session.add(step_reason)
    await db_session.flush()
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    await _seed_step_record(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=at(5),
        exited_at=None,
        pause_reason_id=step_reason.client_id,
    )
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    current.exited_at = at(20)
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            state=UserShiftStateEnum.IN_PAUSE,
            entered_at=at(20),
            exited_at=None,
            changed_by_id=worker.client_id,
            reason="Cleaning the bench",
            manually_recorded=True,
        )
    )
    await db_session.flush()

    await clock_out_shift_for_user(
        db_session, workspace.client_id, worker.client_id, at(50), worker.client_id
    )

    records = await _ordered_shift_records(
        db_session, workspace.client_id, worker.client_id
    )
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 5),
        (UserShiftStateEnum.IN_PAUSE, 5, 20),
        (UserShiftStateEnum.IN_PAUSE, 20, 50),
        (UserShiftStateEnum.ENDED_SHIFT, 50, 50),
    ]
    step_pause, manual_pause = [
        record for record in records if record.state is UserShiftStateEnum.IN_PAUSE
    ]
    assert step_pause.reason == step_reason.client_id
    assert step_pause.manually_recorded is False
    assert manual_pause.reason == "Cleaning the bench"
    assert manual_pause.manually_recorded is True
    assert manual_pause.changed_by_id == worker.client_id


async def test_reconstruction_clamps_open_declared_interval_without_closing_source(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    shift_end = base + timedelta(minutes=30)
    await clock_in_shift_for_user(
        db_session, workspace.client_id, worker.client_id, base, worker.client_id
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        worker,
        reason="pause_coffee_break",
        entered_at=base + timedelta(minutes=10),
        exited_at=None,
    )

    await reconstruct_shift_middle(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        shift_end,
    )

    records = await _ordered_shift_records(
        db_session, workspace.client_id, worker.client_id
    )
    assert _minute_seq(records, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 10),
        (UserShiftStateEnum.IN_PAUSE, 10, 30),
    ]
    rebuilt_pause = next(
        record for record in records if record.state is UserShiftStateEnum.IN_PAUSE
    )
    assert rebuilt_pause.reason == declared.pause_reason_id
    assert rebuilt_pause.manually_recorded is True
    assert declared.exited_at is None


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
    assert "analytics" not in clock_in_result
    assert clocked_in.state is UserShiftStateEnum.IDLE
    assert clock_out_result["action"] == "clock_out"
    assert clock_out_result["analytics"] is None
    assert await _open_shift_record(db_session, workspace.client_id, worker.client_id) is None
    assert {marker.state for marker in markers} == {
        UserShiftStateEnum.STARTED_SHIFT,
        UserShiftStateEnum.ENDED_SHIFT,
    }
    assert all(marker.entered_at == marker.exited_at for marker in markers)


async def test_direct_clock_in_rejects_existing_open_shift(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    ctx = _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    result = await clock_in_worker_shift(ctx)

    assert result == {"action": "clock_in", "user_id": worker.client_id}

    with pytest.raises(ConflictError):
        await clock_in_worker_shift(ctx)


async def test_direct_clock_out_rejects_worker_without_open_shift(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    ctx = _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)

    with pytest.raises(ConflictError):
        await clock_out_worker_shift(ctx)


async def test_direct_clock_out_ignores_supplied_clock_out_at(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_worker_shift(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )
    requested_clock_out_at = "2000-01-01T00:00:00+00:00"

    with freeze_time("2026-07-30T12:00:00+00:00"):
        await clock_out_worker_shift(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"clock_out_at": requested_clock_out_at},
            )
        )

    ended_shift = await db_session.scalar(
        select(UserShiftStateRecord).where(
            UserShiftStateRecord.workspace_id == workspace.client_id,
            UserShiftStateRecord.user_id == worker.client_id,
            UserShiftStateRecord.state == UserShiftStateEnum.ENDED_SHIFT,
        )
    )
    assert ended_shift.entered_at == datetime(2026, 7, 30, 12, tzinfo=timezone.utc)


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

    with pytest.raises(PermissionDenied):
        await clock_out_worker_shift(
            _ctx(
                db_session,
                workspace,
                manager,
                RoleNameEnum.MANAGER.value,
            )
        )

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

    clock_out_result = await clock_out_worker_shift(manager_ctx)
    assert clock_out_result == {
        "action": "clock_out",
        "user_id": worker.client_id,
        "transitioned_steps": 0,
        "analytics": None,
    }
    with pytest.raises(ConflictError):
        await clock_out_worker_shift(manager_ctx)


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
    assert result["analytics"] is None
    assert working_step.state is TaskStepStateEnum.ENDED_SHIFT
    assert paused_step.state is TaskStepStateEnum.PAUSED
    assert paused_open == 1
    assert transition_tasks >= 1


async def test_declare_auto_pauses_working_step_and_updates_live_state(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Cleaning",
        requires_description=True,
        image_url="https://example.com/cleaning.png",
    )
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )
    steps = [
        await _seed_open_step(
            db_session,
            workspace,
            worker,
            state=TaskStepStateEnum.WORKING,
            entered_at=base + timedelta(minutes=5 + index),
        )
        for index in range(2)
    ]

    with freeze_time(base + timedelta(minutes=10)):
        result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {
                    "pause_reason_id": reason.client_id,
                    "description": "  Cleaning section B  ",
                },
            )
        )

    for step in steps:
        await db_session.refresh(step)
    declared = await db_session.scalar(
        select(UserDeclaredStateRecord).where(
            UserDeclaredStateRecord.workspace_id == workspace.client_id,
            UserDeclaredStateRecord.user_id == worker.client_id,
            UserDeclaredStateRecord.exited_at.is_(None),
        )
    )
    paused_steps = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id.in_([step.client_id for step in steps]),
                StepStateRecord.state == TaskStepStateEnum.PAUSED,
                StepStateRecord.exited_at.is_(None),
            )
        )
    ).scalars().all()
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert result == {
        "declared_state": {
            "id": declared.client_id,
            "pause_reason": {
                "id": reason.client_id,
                "name": reason.name,
                "image_url": "https://example.com/cleaning.png",
            },
            "description": "Cleaning section B",
            "entered_at": (base + timedelta(minutes=10)).isoformat(),
        },
        "shift_state": UserShiftStateEnum.IN_PAUSE.value,
        "paused_steps": 2,
    }
    assert all(step.state is TaskStepStateEnum.PAUSED for step in steps)
    assert len(paused_steps) == 2
    assert all(record.pause_reason_id == reason.client_id for record in paused_steps)
    assert all(record.description is None for record in paused_steps)
    assert all(record.credited_user_id == worker.client_id for record in paused_steps)
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == reason.client_id
    assert current.manually_recorded is True


async def test_declare_overrides_live_projection_without_touching_open_step_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    declared_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Meeting",
    )
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )
    paused_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.PAUSED,
        entered_at=base + timedelta(minutes=5),
    )
    paused_record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == paused_step.client_id,
            StepStateRecord.state == TaskStepStateEnum.PAUSED,
            StepStateRecord.exited_at.is_(None),
        )
    )
    original_record_id = paused_record.client_id
    original_reason_id = paused_record.pause_reason_id
    original_entered_at = paused_record.entered_at
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        base + timedelta(minutes=6),
    )

    with freeze_time(base + timedelta(minutes=10)):
        result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": declared_reason.client_id},
            )
        )

    await db_session.refresh(paused_step)
    await db_session.refresh(paused_record)
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert result["paused_steps"] == 0
    assert paused_step.state is TaskStepStateEnum.PAUSED
    assert paused_record.client_id == original_record_id
    assert paused_record.entered_at == original_entered_at
    assert paused_record.exited_at is None
    assert paused_record.pause_reason_id == original_reason_id
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == declared_reason.client_id
    assert current.manually_recorded is True


async def test_declare_validation_matrix(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    valid_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Valid",
    )
    def worker_ctx(reason_id, description=None):
        return _ctx(
            db_session,
            workspace,
            worker,
            RoleNameEnum.WORKER.value,
            {"pause_reason_id": reason_id, "description": description},
        )

    with pytest.raises(
        ConflictError,
        match="Worker must be clocked in to declare a state.",
    ):
        await declare_worker_state(worker_ctx(valid_reason.client_id))
    assert await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    ) is None

    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        datetime.now(timezone.utc),
        worker.client_id,
    )
    foreign_workspace = Workspace(name=f"foreign-{uuid4().hex}")
    db_session.add(foreign_workspace)
    await db_session.flush()
    foreign_reason = await _seed_pause_reason(
        db_session,
        foreign_workspace,
        worker,
        name="Foreign",
    )
    deleted_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Deleted",
        is_deleted=True,
    )
    blocker_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Blocker",
        pause_type=PauseTypeEnum.BLOCKER,
    )
    described_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Needs description",
        requires_description=True,
    )

    for hidden_reason in (foreign_reason, deleted_reason):
        with pytest.raises(NotFound):
            await declare_worker_state(worker_ctx(hidden_reason.client_id))
    with pytest.raises(ValidationError):
        await declare_worker_state(worker_ctx(blocker_reason.client_id))
    with pytest.raises(ValidationError):
        await declare_worker_state(worker_ctx(described_reason.client_id, "  "))
    with pytest.raises(ValidationError):
        await declare_worker_state(worker_ctx(valid_reason.client_id, "x" * 513))


async def test_declare_and_close_on_behalf_access_matrix(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    manager = await _seed_user(db_session, "declared-state-manager")
    admin = await _seed_user(db_session, "declared-state-admin")
    reason = await _seed_pause_reason(
        db_session,
        workspace,
        manager,
        name="Meeting",
    )
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        datetime.now(timezone.utc),
        manager.client_id,
    )
    manager_declare_ctx = _ctx(
        db_session,
        workspace,
        manager,
        RoleNameEnum.MANAGER.value,
        {"user_id": worker.client_id, "pause_reason_id": reason.client_id},
    )

    await declare_worker_state(manager_declare_ctx)
    declared = await db_session.scalar(
        select(UserDeclaredStateRecord).where(
            UserDeclaredStateRecord.user_id == worker.client_id,
            UserDeclaredStateRecord.exited_at.is_(None),
        )
    )
    close_result = await close_declared_worker_state(
        _ctx(
            db_session,
            workspace,
            manager,
            RoleNameEnum.MANAGER.value,
            {"user_id": worker.client_id},
        )
    )
    await db_session.refresh(declared)

    assert declared.created_by_id == manager.client_id
    assert declared.closed_by_id == manager.client_id
    assert close_result["closed_declared_state_id"] == declared.client_id

    await declare_worker_state(
        _ctx(
            db_session,
            workspace,
            admin,
            RoleNameEnum.ADMIN.value,
            {"user_id": worker.client_id, "pause_reason_id": reason.client_id},
        )
    )
    admin_declared = await db_session.scalar(
        select(UserDeclaredStateRecord).where(
            UserDeclaredStateRecord.user_id == worker.client_id,
            UserDeclaredStateRecord.exited_at.is_(None),
        )
    )
    await close_declared_worker_state(
        _ctx(
            db_session,
            workspace,
            admin,
            RoleNameEnum.ADMIN.value,
            {"user_id": worker.client_id},
        )
    )
    await db_session.refresh(admin_declared)
    assert admin_declared.created_by_id == admin.client_id
    assert admin_declared.closed_by_id == admin.client_id

    for command, payload in (
        (declare_worker_state, {"pause_reason_id": reason.client_id}),
        (close_declared_worker_state, {}),
    ):
        with pytest.raises(PermissionDenied):
            await command(
                _ctx(
                    db_session,
                    workspace,
                    manager,
                    RoleNameEnum.MANAGER.value,
                    payload,
                )
            )
        with pytest.raises(PermissionDenied):
            await command(
                _ctx(
                    db_session,
                    workspace,
                    worker,
                    RoleNameEnum.WORKER.value,
                    {"user_id": manager.client_id, **payload},
                )
            )
        with pytest.raises(NotFound):
            await command(
                _ctx(
                    db_session,
                    workspace,
                    admin,
                    RoleNameEnum.ADMIN.value,
                    {"user_id": manager.client_id, **payload},
                )
            )


async def test_declare_switch_closes_old_and_opens_new_atomically(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    first_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Cleaning",
    )
    second_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Meeting",
    )
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )

    with freeze_time(base + timedelta(minutes=10)):
        first_result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": first_reason.client_id},
            )
        )
    with freeze_time(base + timedelta(minutes=20)):
        second_result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": second_reason.client_id},
            )
        )

    rows = (
        await db_session.execute(
            select(UserDeclaredStateRecord)
            .where(
                UserDeclaredStateRecord.workspace_id == workspace.client_id,
                UserDeclaredStateRecord.user_id == worker.client_id,
            )
            .order_by(UserDeclaredStateRecord.entered_at)
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].client_id == first_result["declared_state"]["id"]
    assert rows[0].exited_at == base + timedelta(minutes=20)
    assert rows[0].closed_by_id == worker.client_id
    assert rows[1].client_id == second_result["declared_state"]["id"]
    assert rows[1].exited_at is None
    assert sum(row.exited_at is None for row in rows) == 1


async def test_declare_switch_preserves_reason_on_already_paused_step(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    first_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Cleaning",
    )
    second_reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Meeting",
    )
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )
    working_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=base + timedelta(minutes=5),
    )

    with freeze_time(base + timedelta(minutes=10)):
        first_result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": first_reason.client_id},
            )
        )
    paused_record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == working_step.client_id,
            StepStateRecord.state == TaskStepStateEnum.PAUSED,
            StepStateRecord.exited_at.is_(None),
        )
    )
    original_record_id = paused_record.client_id
    original_entered_at = paused_record.entered_at

    with freeze_time(base + timedelta(minutes=20)):
        second_result = await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": second_reason.client_id},
            )
        )

    await db_session.refresh(paused_record)
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert first_result["paused_steps"] == 1
    assert second_result["paused_steps"] == 0
    assert paused_record.client_id == original_record_id
    assert paused_record.entered_at == original_entered_at
    assert paused_record.exited_at is None
    assert paused_record.pause_reason_id == first_reason.client_id
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == second_reason.client_id
    assert current.manually_recorded is True


@pytest.mark.parametrize("run_number", range(5))
async def test_concurrent_declares_never_report_clocked_in_worker_as_clocked_out(
    db_session,
    monkeypatch,
    run_number: int,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reasons = [
        await _seed_pause_reason(
            db_session,
            workspace,
            worker,
            name=f"Concurrent declaration {run_number}-{index}",
        )
        for index in range(2)
    ]
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    reason_ids = [reason.client_id for reason in reasons]
    await clock_in_shift_for_user(
        db_session,
        workspace_id,
        worker_id,
        datetime.now(timezone.utc),
        worker_id,
    )
    await db_session.commit()

    first_shift_locked = asyncio.Event()
    second_shift_select_started = asyncio.Event()
    release_first_declare = asyncio.Event()
    helper_call_count = 0
    declare_module = import_module(
        "beyo_manager.services.commands.users.declare_worker_state"
    )

    async def controlled_shift_lock(session, workspace_id, user_id):
        nonlocal helper_call_count
        call_index = helper_call_count
        helper_call_count += 1
        if call_index == 1:
            second_shift_select_started.set()
        shift = await load_open_worker_shift_for_update(
            session,
            workspace_id,
            user_id,
        )
        if call_index == 0:
            first_shift_locked.set()
            await release_first_declare.wait()
        return shift

    monkeypatch.setattr(
        declare_module,
        "load_open_worker_shift_for_update",
        controlled_shift_lock,
    )

    try:
        first = asyncio.create_task(
            _run_worker_command_in_new_session(
                declare_worker_state,
                workspace_id=workspace_id,
                worker_id=worker_id,
                incoming_data={"pause_reason_id": reason_ids[0]},
            )
        )
        await asyncio.wait_for(first_shift_locked.wait(), timeout=5)
        second = asyncio.create_task(
            _run_worker_command_in_new_session(
                declare_worker_state,
                workspace_id=workspace_id,
                worker_id=worker_id,
                incoming_data={"pause_reason_id": reason_ids[1]},
            )
        )
        await asyncio.wait_for(second_shift_select_started.wait(), timeout=5)
        release_first_declare.set()
        outcomes = await asyncio.wait_for(
            asyncio.gather(first, second, return_exceptions=True),
            timeout=10,
        )

        false_clocked_out = [
            outcome
            for outcome in outcomes
            if isinstance(outcome, ConflictError)
            and "Worker must be clocked in" in str(outcome)
        ]
        assert false_clocked_out == []
        assert all(isinstance(outcome, dict) for outcome in outcomes)
    finally:
        release_first_declare.set()
        await _cleanup_committed_worker_command_rows(
            db_session,
            workspace_id=workspace_id,
            worker_id=worker_id,
            pause_reason_ids=reason_ids,
        )


@pytest.mark.parametrize("run_number", range(5))
async def test_concurrent_close_and_declare_retain_shift_then_declared_lock_order(
    db_session,
    monkeypatch,
    run_number: int,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reasons = [
        await _seed_pause_reason(
            db_session,
            workspace,
            worker,
            name=f"Concurrent close-declare {run_number}-{index}",
        )
        for index in range(2)
    ]
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    reason_ids = [reason.client_id for reason in reasons]
    await clock_in_shift_for_user(
        db_session,
        workspace_id,
        worker_id,
        datetime.now(timezone.utc),
        worker_id,
    )
    await declare_worker_state(
        _ctx(
            db_session,
            workspace,
            worker,
            RoleNameEnum.WORKER.value,
            {"pause_reason_id": reason_ids[0]},
        )
    )
    await db_session.commit()

    declare_shift_locked = asyncio.Event()
    close_shift_select_started = asyncio.Event()
    release_declare = asyncio.Event()
    close_shift_results = []
    declare_module = import_module(
        "beyo_manager.services.commands.users.declare_worker_state"
    )
    close_module = import_module(
        "beyo_manager.services.commands.users.close_declared_worker_state"
    )

    async def controlled_declare_shift_lock(session, workspace_id, user_id):
        shift = await load_open_worker_shift_for_update(
            session,
            workspace_id,
            user_id,
        )
        declare_shift_locked.set()
        await release_declare.wait()
        return shift

    async def observed_close_shift_lock(session, workspace_id, user_id):
        close_shift_select_started.set()
        shift = await load_open_worker_shift_for_update(
            session,
            workspace_id,
            user_id,
        )
        close_shift_results.append(shift)
        return shift

    monkeypatch.setattr(
        declare_module,
        "load_open_worker_shift_for_update",
        controlled_declare_shift_lock,
    )
    monkeypatch.setattr(
        close_module,
        "load_open_worker_shift_for_update",
        observed_close_shift_lock,
    )

    try:
        declaring = asyncio.create_task(
            _run_worker_command_in_new_session(
                declare_worker_state,
                workspace_id=workspace_id,
                worker_id=worker_id,
                incoming_data={"pause_reason_id": reason_ids[1]},
            )
        )
        await asyncio.wait_for(declare_shift_locked.wait(), timeout=5)
        closing = asyncio.create_task(
            _run_worker_command_in_new_session(
                close_declared_worker_state,
                workspace_id=workspace_id,
                worker_id=worker_id,
                incoming_data={},
            )
        )
        await asyncio.wait_for(close_shift_select_started.wait(), timeout=5)
        release_declare.set()
        outcomes = await asyncio.wait_for(
            asyncio.gather(declaring, closing, return_exceptions=True),
            timeout=10,
        )

        assert all(isinstance(outcome, dict) for outcome in outcomes)
        assert len(close_shift_results) == 1
        assert close_shift_results[0] is not None
    finally:
        release_declare.set()
        await _cleanup_committed_worker_command_rows(
            db_session,
            workspace_id=workspace_id,
            worker_id=worker_id,
            pause_reason_ids=reason_ids,
        )


@pytest.mark.parametrize("run_number", range(5))
async def test_concurrent_declare_and_reconcile_never_lose_open_shift(
    db_session,
    monkeypatch,
    run_number: int,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name=f"Concurrent declare-reconcile {run_number}",
    )
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await clock_in_shift_for_user(
        db_session,
        workspace_id,
        worker_id,
        datetime.now(timezone.utc),
        worker_id,
    )
    await db_session.commit()

    declare_shift_locked = asyncio.Event()
    reconcile_shift_select_started = asyncio.Event()
    release_declare = asyncio.Event()
    listener_registered = False
    declare_module = import_module(
        "beyo_manager.services.commands.users.declare_worker_state"
    )

    async def controlled_declare_shift_lock(session, workspace_id, user_id):
        shift = await load_open_worker_shift_for_update(
            session,
            workspace_id,
            user_id,
        )
        declare_shift_locked.set()
        await release_declare.wait()
        return shift

    monkeypatch.setattr(
        declare_module,
        "load_open_worker_shift_for_update",
        controlled_declare_shift_lock,
    )

    engine = db_session.bind.sync_engine

    def observe_reconcile_shift_select(
        _connection,
        _cursor,
        statement,
        parameters,
        _context,
        _executemany,
    ):
        if (
            "FROM user_shift_state_records" in statement
            and "user_shift_state_records.exited_at IS NULL" in statement
            and "FOR UPDATE" in statement
            and worker_id in parameters
        ):
            reconcile_shift_select_started.set()

    try:
        declaring = asyncio.create_task(
            _run_worker_command_in_new_session(
                declare_worker_state,
                workspace_id=workspace_id,
                worker_id=worker_id,
                incoming_data={"pause_reason_id": reason.client_id},
            )
        )
        await asyncio.wait_for(declare_shift_locked.wait(), timeout=5)
        event.listen(
            engine,
            "before_cursor_execute",
            observe_reconcile_shift_select,
        )
        listener_registered = True

        async def run_reconcile():
            async for session in get_db_session():
                async with session.begin():
                    return await reconcile_worker_shift_state(
                        session,
                        workspace_id,
                        worker_id,
                        datetime.now(timezone.utc),
                    )
            raise AssertionError("Database session generator yielded no session")

        reconciling = asyncio.create_task(run_reconcile())
        await asyncio.wait_for(reconcile_shift_select_started.wait(), timeout=5)
        release_declare.set()
        declare_outcome, reconcile_outcome = await asyncio.wait_for(
            asyncio.gather(declaring, reconciling),
            timeout=10,
        )

        assert declare_outcome["shift_state"] == UserShiftStateEnum.IN_PAUSE.value
        assert reconcile_outcome.state is UserShiftStateEnum.IN_PAUSE
    finally:
        release_declare.set()
        if listener_registered:
            event.remove(
                engine,
                "before_cursor_execute",
                observe_reconcile_shift_select,
            )
        await _cleanup_committed_worker_command_rows(
            db_session,
            workspace_id=workspace_id,
            worker_id=worker_id,
            pause_reason_ids=[reason.client_id],
        )


async def test_close_declaration_without_steps_reconciles_to_idle(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Lunch",
    )
    await clock_in_worker_shift(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )
    await declare_worker_state(
        _ctx(
            db_session,
            workspace,
            worker,
            RoleNameEnum.WORKER.value,
            {"pause_reason_id": reason.client_id},
        )
    )

    result = await close_declared_worker_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    assert result["shift_state"] == UserShiftStateEnum.IDLE.value
    assert current.state is UserShiftStateEnum.IDLE
    assert current.manually_recorded is False
    with pytest.raises(ConflictError, match="No declared state is open."):
        await close_declared_worker_state(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )


async def test_close_declaration_leaves_auto_paused_step_open(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_pause_reason(
        db_session,
        workspace,
        worker,
        name="Cleaning",
    )
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )
    working_step = await _seed_open_step(
        db_session,
        workspace,
        worker,
        state=TaskStepStateEnum.WORKING,
        entered_at=base + timedelta(minutes=5),
    )
    with freeze_time(base + timedelta(minutes=10)):
        await declare_worker_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                {"pause_reason_id": reason.client_id},
            )
        )
    paused_record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.step_id == working_step.client_id,
            StepStateRecord.state == TaskStepStateEnum.PAUSED,
            StepStateRecord.exited_at.is_(None),
        )
    )
    paused_record_id = paused_record.client_id

    with freeze_time(base + timedelta(minutes=20)):
        result = await close_declared_worker_state(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )

    await db_session.refresh(working_step)
    await db_session.refresh(paused_record)
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert result["shift_state"] == UserShiftStateEnum.IN_PAUSE.value
    assert working_step.state is TaskStepStateEnum.PAUSED
    assert paused_record.client_id == paused_record_id
    assert paused_record.exited_at is None
    assert paused_record.pause_reason_id == reason.client_id
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == reason.client_id
    assert current.manually_recorded is False


async def test_open_legacy_manual_pause_reconciles_to_idle_after_retirement(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    base = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    await clock_in_shift_for_user(
        db_session,
        workspace.client_id,
        worker.client_id,
        base,
        worker.client_id,
    )
    current = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    current.exited_at = base + timedelta(minutes=5)
    legacy_pause = UserShiftStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        state=UserShiftStateEnum.IN_PAUSE,
        entered_at=base + timedelta(minutes=5),
        exited_at=None,
        changed_by_id=worker.client_id,
        reason="Legacy manual pause",
        manually_recorded=True,
    )
    db_session.add(legacy_pause)
    await db_session.flush()

    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        worker.client_id,
        base + timedelta(minutes=6),
    )
    reconciled = await _open_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
    )

    assert outcome.changed is True
    assert legacy_pause.exited_at == base + timedelta(minutes=6)
    assert reconciled.state is UserShiftStateEnum.IDLE
    assert reconciled.manually_recorded is False


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
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    declared_id: str | None = None
    declared_reason_id: str | None = None
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
        declared = await _seed_declared_state(
            db_session,
            workspace,
            worker,
            reason="pause_lunch_break",
            entered_at=midnight - timedelta(hours=8),
            exited_at=None,
        )
        declared_id = declared.client_id
        declared_reason_id = declared.pause_reason_id
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
            closed_declared = await session.get(
                UserDeclaredStateRecord, declared_id
            )
            assert closed_declared.exited_at == midnight
            assert closed_declared.closed_by_id is None

        result = await clock_in_worker_shift(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )
        assert result["action"] == "clock_in"
    finally:
        # Remove everything this test committed so the shared DB stays clean.
        await db_session.rollback()
        if declared_id is not None:
            await db_session.execute(
                delete(UserDeclaredStateRecord).where(
                    UserDeclaredStateRecord.client_id == declared_id
                )
            )
        if declared_reason_id is not None:
            await db_session.execute(
                delete(PauseReason).where(
                    PauseReason.client_id == declared_reason_id
                )
            )
        await db_session.execute(
            delete(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == worker_id,
            )
        )
        await db_session.commit()


@freeze_time("2026-07-15T09:00:00+00:00")
async def test_midnight_safeguard_preserves_open_legacy_manual_pause(
    db_session,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await db_session.execute(
        delete(UserShiftStateRecord).where(UserShiftStateRecord.exited_at.is_(None))
    )
    await db_session.flush()
    midnight = datetime.combine(
        datetime.now(timezone.utc).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    pause_start = midnight - timedelta(hours=8)
    try:
        await clock_in_shift_for_user(
            db_session,
            workspace_id,
            worker_id,
            midnight - timedelta(hours=16),
            worker_id,
        )
        current = await _open_shift_record(db_session, workspace_id, worker_id)
        current.exited_at = pause_start
        db_session.add(
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=worker_id,
                state=UserShiftStateEnum.IN_PAUSE,
                entered_at=pause_start,
                exited_at=None,
                changed_by_id=worker_id,
                reason="Late lunch",
                manually_recorded=True,
            )
        )
        await db_session.commit()

        await handle_auto_clock_out_open_shifts({}, "task_midnight_legacy_pause_test")

        async for session in get_db_session():
            records = await _ordered_shift_records(session, workspace_id, worker_id)
            manual_pause = next(
                record
                for record in records
                if record.state is UserShiftStateEnum.IN_PAUSE
            )
            ended = next(
                record
                for record in records
                if record.state is UserShiftStateEnum.ENDED_SHIFT
            )
            assert manual_pause.entered_at == pause_start
            assert manual_pause.exited_at == midnight
            assert manual_pause.reason == "Late lunch"
            assert manual_pause.manually_recorded is True
            assert ended.entered_at == midnight
            assert ended.exited_at == midnight
            assert await _open_shift_record(session, workspace_id, worker_id) is None
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == worker_id,
            )
        )
        await db_session.commit()
