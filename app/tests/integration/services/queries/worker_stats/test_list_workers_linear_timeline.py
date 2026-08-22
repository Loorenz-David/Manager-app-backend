from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
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
from tests.fixtures.phase2_row_factories import adopt_or_create_role


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
    role = await adopt_or_create_role(db_session, RoleNameEnum.WORKER)
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
    reason: str | None = None,
    transition_reason: str | None = None,
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
            pause_reason_id=(
                await db_session.scalar(
                    select(PauseReason.client_id).where(
                        PauseReason.slug == reason,
                    )
                )
                if reason is not None
                else None
            ),
            transition_reason=transition_reason,
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

    assert set(out) == {"workers", "workers_pagination", "pause_reasons"}
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
    # "custom tool cleanup" is a manually-recorded free-text shift pause, not a pause_reason_id,
    # so it never resolves against the pause_reasons table.
    assert out["pause_reasons"] == {}


async def test_roster_resolves_pause_reason_lookup_map(db_session) -> None:
    # UserShiftStateRecord.reason is an unconstrained string that, for step-sourced pauses,
    # now carries an opaque pause_reason_id rather than the old readable enum value — the
    # roster response must resolve it via a sibling lookup map, same as the per-worker
    # breakdown endpoint, instead of leaving the frontend with a bare client_id.
    workspace = Workspace(name=f"shift-pause-lookup-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    pause_reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Lunch break",
        pause_type=PauseTypeEnum.PERSONAL,
    )
    db_session.add(pause_reason)
    await db_session.flush()

    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.STARTED_SHIFT, base, base,
    )
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.IN_PAUSE, base, base + timedelta(minutes=30),
        reason=pause_reason.client_id,
    )
    ended_at = base + timedelta(minutes=30)
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.ENDED_SHIFT, ended_at, ended_at,
    )

    out = await list_workers_linear_timeline(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            query_params={"date_from": "2026-07-15", "date_to": "2026-07-15"},
        )
    )

    assert out["workers"][0]["timeline"]["pause_by_reason"] == {pause_reason.client_id: 1800}
    assert out["pause_reasons"] == {
        pause_reason.client_id: {
            "name": "Lunch break",
            "image_url": None,
            "pause_type": "personal",
        }
    }


async def test_roster_completed_count_is_scoped_to_recorded_shifts(db_session) -> None:
    # completed_count counts only completions that fall inside a recorded shift, so it
    # stays consistent with the shift-based time buckets: a completion outside any shift
    # (a day never clocked in) does not count.
    workspace = Workspace(name=f"shift-completed-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    shift_start = base
    shift_end = base + timedelta(hours=8)
    # Recorded shift 09:00–17:00 on 2026-07-15.
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start,
    )
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.WORKING, shift_start, shift_end,
    )
    _add_shift_record(
        db_session, workspace.client_id, worker.client_id,
        UserShiftStateEnum.ENDED_SHIFT, shift_end, shift_end,
    )
    # In-shift completion → counts. Boundary completion exactly at ended_shift → counts.
    await _add_step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.COMPLETED, shift_start + timedelta(hours=2),
    )
    await _add_step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.COMPLETED, shift_end,
    )
    # Same-day completion OUTSIDE the shift (before clock-in) → must NOT count.
    await _add_step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.COMPLETED, shift_start - timedelta(hours=1),
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
    assert timeline["completed_count"] == 2  # two in-shift; the pre-shift one excluded
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
        reason="pause_lunch_break",
    )
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        # A step the shift ended under: paused, and typed so the sweep still reads it as
        # off-shift time rather than as the worker being paused while present.
        TaskStepStateEnum.PAUSED,
        base - timedelta(hours=20),
        exited_at=base,
        transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
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
