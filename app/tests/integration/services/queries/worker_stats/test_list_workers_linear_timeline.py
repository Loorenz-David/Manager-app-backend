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
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    list_workers_linear_timeline,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _ctx(db_session, *, workspace_id: str, query_params: dict | None = None):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": "usr_mgr",
            "role_name": "manager",
            "username": "mgr",
        },
        incoming_data={},
        query_params=query_params or {},
        session=db_session,
    )


async def _seed_worker(db_session, workspace_id: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    role = (
        await db_session.execute(
            select(Role).where(Role.name == RoleNameEnum.WORKER)
        )
    ).scalar_one()
    workspace_role = WorkspaceRole(
        client_id=f"wsr_{suffix}",
        workspace_id=workspace_id,
        role_id=role.client_id,
    )
    db_session.add(workspace_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            client_id=f"wsm_{suffix}",
            user_id=user.client_id,
            workspace_id=workspace_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return user


def _add_shift_record(
    db_session,
    workspace_id: str,
    user_id: str,
    state: UserShiftStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    reason: str | None = None,
    manually_recorded: bool = False,
) -> None:
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            reason=reason,
            manually_recorded=manually_recorded,
        )
    )


async def _add_step_record(
    db_session,
    workspace_id: str,
    user_id: str,
    state: TaskStepStateEnum,
    entered_at: datetime,
    *,
    exited_at: datetime | None = None,
    reason: StepEventReasonEnum | None = None,
) -> None:
    suffix = uuid4().hex[:8]
    section = WorkingSection(
        workspace_id=workspace_id,
        name=f"section-{suffix}",
    )
    task = Task(
        workspace_id=workspace_id,
        task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=state,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step.client_id,
            state=state,
            reason=reason,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user_id,
            credited_user_id=user_id,
        )
    )


async def test_roster_sums_only_recorded_on_shift_durations(db_session) -> None:
    workspace = Workspace(name=f"shift-roster-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.STARTED_SHIFT,
        base,
        base,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.WORKING,
        base,
        base + timedelta(hours=1),
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IN_PAUSE,
        base + timedelta(hours=1),
        base + timedelta(hours=1, minutes=30),
        reason="custom tool cleanup",
        manually_recorded=True,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IDLE,
        base + timedelta(hours=1, minutes=30),
        base + timedelta(hours=1, minutes=45),
    )
    ended_at = base + timedelta(hours=1, minutes=45)
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.ENDED_SHIFT,
        ended_at,
        ended_at,
    )

    out = await list_workers_linear_timeline(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            query_params={
                "date_from": "2026-07-15",
                "date_to": "2026-07-15",
            },
        )
    )

    assert set(out) == {"workers", "workers_pagination"}
    assert len(out["workers"]) == 1
    assert set(out["workers"][0]) == {"user", "timeline"}
    assert set(out["workers"][0]["user"]) == {
        "client_id",
        "username",
        "profile_picture",
        "last_online",
    }
    assert out["workers"][0]["timeline"] == {
        "date_from": "2026-07-15",
        "date_to": "2026-07-15",
        "working_seconds": 3600,
        "pause_seconds": 1800,
        "ended_shift_seconds": 0,
        "idle_seconds": 900,
        "completed_count": 0,
        "pause_by_reason": {"custom tool cleanup": 1800},
    }


async def test_roster_keeps_completed_count_from_step_records(db_session) -> None:
    workspace = Workspace(name=f"shift-completed-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        TaskStepStateEnum.COMPLETED,
        base,
    )
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        TaskStepStateEnum.COMPLETED,
        base + timedelta(days=1),
    )

    out = await list_workers_linear_timeline(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            query_params={
                "date_from": "2026-07-15",
                "date_to": "2026-07-15",
            },
        )
    )

    timeline = out["workers"][0]["timeline"]
    assert timeline["completed_count"] == 1
    assert timeline["working_seconds"] == 0
    assert timeline["pause_seconds"] == 0
    assert timeline["idle_seconds"] == 0
    assert out["workers_pagination"] == {
        "has_more": False,
        "limit": 50,
        "offset": 0,
        "total": 1,
    }


async def test_roster_ignores_step_record_bleed_outside_shift(db_session) -> None:
    workspace = Workspace(name=f"shift-no-bleed-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.STARTED_SHIFT,
        base,
        base,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.WORKING,
        base,
        base + timedelta(hours=1),
    )
    ended_at = base + timedelta(hours=1)
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.ENDED_SHIFT,
        ended_at,
        ended_at,
    )
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        TaskStepStateEnum.PAUSED,
        base - timedelta(weeks=3),
        reason=StepEventReasonEnum.PAUSE_LUNCH_BREAK,
    )
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        TaskStepStateEnum.ENDED_SHIFT,
        base - timedelta(hours=20),
        exited_at=base,
    )

    out = await list_workers_linear_timeline(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            query_params={
                "date_from": "2026-07-15",
                "date_to": "2026-07-15",
            },
        )
    )

    timeline = out["workers"][0]["timeline"]
    assert timeline["working_seconds"] == 3600
    assert timeline["pause_seconds"] == 0
    assert timeline["ended_shift_seconds"] == 0
    assert timeline["idle_seconds"] == 0
