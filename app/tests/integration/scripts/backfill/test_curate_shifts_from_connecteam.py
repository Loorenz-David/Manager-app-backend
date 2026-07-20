from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from scripts.backfill.curate_shifts_from_connecteam import (
    _resolve_workers,
    curate_worker_shift,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_MARKER_RANK = {UserShiftStateEnum.STARTED_SHIFT: 0, UserShiftStateEnum.ENDED_SHIFT: 2}


async def _seed_worker(db_session, *, connecteam_user_id: str | None = None):
    suffix = uuid4().hex[:8]
    workspace = Workspace(name=f"curate-{suffix}")
    worker = User(username=f"curate-{suffix}", email=f"curate-{suffix}@e.com", password="s")
    db_session.add_all([workspace, worker])
    await db_session.flush()
    role = (await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))).scalar_one()
    ws_role = WorkspaceRole(workspace_id=workspace.client_id, role_id=role.client_id)
    db_session.add(ws_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=workspace.client_id, user_id=worker.client_id,
            workspace_role_id=ws_role.client_id, is_active=True,
        )
    )
    if connecteam_user_id is not None:
        db_session.add(
            UserWorkProfile(
                workspace_id=workspace.client_id, user_id=worker.client_id,
                connecteam_user_id=connecteam_user_id, created_by_id=worker.client_id,
            )
        )
    await db_session.flush()
    return workspace, worker


async def _seed_step_record(db_session, workspace, worker, *, state, entered_at, exited_at, reason=None):
    suffix = uuid4().hex[:8]
    section = WorkingSection(workspace_id=workspace.client_id, name=f"sec-{suffix}")
    task = Task(
        workspace_id=workspace.client_id, task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.WORKING, created_by_id=worker.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id,
        state=state, created_by_id=worker.client_id,
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


async def _ordered(db_session, workspace_id, user_id, base):
    recs = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
            )
        )
    ).scalars().all()
    recs.sort(key=lambda r: (r.entered_at, _MARKER_RANK.get(r.state, 1)))

    def m(dt):
        return round((dt - base).total_seconds() / 60)

    return [(r.state, m(r.entered_at), m(r.exited_at)) for r in recs]


async def test_curate_builds_full_timeline_within_real_bounds(db_session):
    workspace, worker = await _seed_worker(db_session)
    base = datetime(2026, 3, 10, 8, tzinfo=timezone.utc)

    def at(mn):
        return base + timedelta(minutes=mn)

    # Real Connecteam shift is 08:00–09:00. Step activity: working, upholstery pause, working.
    # An activity BEFORE the shift must be excluded (real bounds are authoritative).
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=at(-30), exited_at=at(-10))  # before clock-in → excluded
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=at(10), exited_at=at(25))
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.PAUSED,
                            entered_at=at(25), exited_at=at(40),
                            reason=StepEventReasonEnum.WAITING_FOR_UPHOLSTERY)
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=at(40), exited_at=at(55))

    wrote = await curate_worker_shift(
        db_session, workspace_id=workspace.client_id, user_id=worker.client_id,
        start_at=at(0), end_at=at(60),
    )
    assert wrote is True
    assert await _ordered(db_session, workspace.client_id, worker.client_id, base) == [
        (UserShiftStateEnum.STARTED_SHIFT, 0, 0),
        (UserShiftStateEnum.IDLE, 0, 10),
        (UserShiftStateEnum.WORKING, 10, 25),
        (UserShiftStateEnum.IN_PAUSE, 25, 40),
        (UserShiftStateEnum.WORKING, 40, 55),
        (UserShiftStateEnum.IDLE, 55, 60),
        (UserShiftStateEnum.ENDED_SHIFT, 60, 60),
    ]


async def test_curate_is_idempotent(db_session):
    workspace, worker = await _seed_worker(db_session)
    base = datetime(2026, 3, 10, 8, tzinfo=timezone.utc)
    await _seed_step_record(db_session, workspace, worker, state=TaskStepStateEnum.WORKING,
                            entered_at=base + timedelta(minutes=10), exited_at=base + timedelta(minutes=50))
    kwargs = dict(workspace_id=workspace.client_id, user_id=worker.client_id,
                  start_at=base, end_at=base + timedelta(minutes=60))
    await curate_worker_shift(db_session, **kwargs)
    first = await _ordered(db_session, workspace.client_id, worker.client_id, base)
    await curate_worker_shift(db_session, **kwargs)  # re-run
    assert await _ordered(db_session, workspace.client_id, worker.client_id, base) == first


async def test_curate_two_split_shifts_same_day(db_session):
    workspace, worker = await _seed_worker(db_session)
    base = datetime(2026, 3, 10, 8, tzinfo=timezone.utc)
    # morning shift 08:00–10:00, afternoon 13:00–15:00
    await curate_worker_shift(db_session, workspace_id=workspace.client_id, user_id=worker.client_id,
                              start_at=base, end_at=base + timedelta(hours=2))
    await curate_worker_shift(db_session, workspace_id=workspace.client_id, user_id=worker.client_id,
                              start_at=base + timedelta(hours=5), end_at=base + timedelta(hours=7))
    started = [
        r for r in (
            await db_session.execute(
                select(UserShiftStateRecord).where(
                    UserShiftStateRecord.user_id == worker.client_id,
                    UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
                )
            )
        ).scalars().all()
    ]
    assert len(started) == 2  # both shifts preserved — curating the second didn't touch the first


async def test_resolve_workers_maps_connecteam_id(db_session):
    workspace, worker = await _seed_worker(db_session, connecteam_user_id="9170357")
    mapping = await _resolve_workers(db_session, {"9170357", "does-not-exist"})
    assert mapping == {"9170357": (workspace.client_id, worker.client_id)}
