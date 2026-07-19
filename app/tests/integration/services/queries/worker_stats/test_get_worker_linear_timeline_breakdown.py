from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import (
    StepEventReasonEnum,
    TaskStepStateEnum,
)
from beyo_manager.domain.tasks.enums import (
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    get_worker_linear_timeline_breakdown,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _ctx(db_session, *, workspace_id: str, user_id: str, work_date: str):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": "usr_mgr",
            "role_name": "manager",
            "username": "mgr",
        },
        incoming_data={"user_id": user_id},
        query_params={"date_from": work_date, "date_to": work_date},
        session=db_session,
    )


async def _seed_worker(db_session, workspace_id: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        username=f"timeline-worker-{suffix}",
        email=f"timeline-worker-{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    role = (
        await db_session.execute(
            select(Role).where(Role.name == RoleNameEnum.WORKER)
        )
    ).scalar_one()
    workspace_role = WorkspaceRole(
        workspace_id=workspace_id,
        role_id=role.client_id,
    )
    db_session.add(workspace_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            user_id=user.client_id,
            workspace_id=workspace_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return user


async def _seed_step_with_item(
    db_session,
    workspace_id: str,
    user_id: str,
) -> TaskStep:
    suffix = uuid4().hex[:8]
    section = WorkingSection(
        workspace_id=workspace_id,
        name="Upholstery",
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
    item = Item(
        workspace_id=workspace_id,
        article_number="ART-1",
        sku="SKU-1",
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    db_session.add(item)
    await db_session.flush()
    db_session.add(
        TaskItem(
            workspace_id=workspace_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
        )
    )
    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.COMPLETED,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    return step


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


def _add_step_record(
    db_session,
    workspace_id: str,
    user_id: str,
    step_id: str,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    reason: StepEventReasonEnum | None = None,
) -> None:
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step_id,
            state=state,
            reason=reason,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user_id,
            credited_user_id=user_id,
        )
    )


async def test_breakdown_preserves_contract_and_adds_recorded_markers(db_session) -> None:
    workspace = Workspace(name=f"timeline-contract-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    step = await _seed_step_with_item(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    pause_at = base + timedelta(minutes=20)
    idle_at = base + timedelta(minutes=40)
    ended_at = base + timedelta(minutes=50)
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
        pause_at,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IN_PAUSE,
        pause_at,
        idle_at,
        reason="cleaning station",
        manually_recorded=True,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IDLE,
        idle_at,
        ended_at,
    )
    _add_shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.ENDED_SHIFT,
        ended_at,
        ended_at,
    )
    _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.WORKING,
        base,
        pause_at,
    )
    _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.PAUSED,
        pause_at,
        idle_at,
        reason=StepEventReasonEnum.PAUSE_COFFEE_BREAK,
    )
    _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.COMPLETED,
        idle_at,
        None,
    )

    out = await get_worker_linear_timeline_breakdown(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            work_date="2026-07-15",
        )
    )

    assert set(out) == {"user", "timeline", "segments", "segments_truncated"}
    assert set(out["user"]) == {
        "client_id",
        "username",
        "profile_picture",
        "last_online",
    }
    assert set(out["timeline"]) == {
        "date_from",
        "date_to",
        "working_seconds",
        "pause_seconds",
        "ended_shift_seconds",
        "idle_seconds",
        "completed_count",
        "pause_by_reason",
    }
    assert out["timeline"] == {
        "date_from": "2026-07-15",
        "date_to": "2026-07-15",
        "working_seconds": 1200,
        "pause_seconds": 1200,
        "ended_shift_seconds": 0,
        "idle_seconds": 600,
        "completed_count": 1,
        "pause_by_reason": {"cleaning station": 1200},
    }
    assert [segment["state"] for segment in out["segments"]] == [
        "started_shift",
        "working",
        "paused",
        "idle",
        "ended_shift",
    ]
    assert all(
        set(segment) == {
            "start",
            "end",
            "seconds",
            "state",
            "reason",
            "is_open",
            "steps",
            "manually_recorded",
        }
        for segment in out["segments"]
    )
    started, working, paused, idle, ended = out["segments"]
    assert started["seconds"] == ended["seconds"] == 0
    assert started["steps"] == ended["steps"] == idle["steps"] == []
    assert paused["manually_recorded"] is True
    assert paused["reason"] == "cleaning station"
    assert working["manually_recorded"] is False
    assert working["steps"][0]["ended_by"] == "paused"
    assert paused["steps"][0]["ended_by"] == "completed"
    assert set(working["steps"][0]) == {
        "record_id",
        "step_id",
        "task_id",
        "working_section_id",
        "working_section_name",
        "item",
        "state",
        "reason",
        "entered_at",
        "exited_at",
        "is_open",
        "ended_by",
    }
    assert working["steps"][0]["item"]["article_number"] == "ART-1"
    assert out["segments_truncated"] is False
    duration_segments = [
        segment
        for segment in out["segments"]
        if segment["state"] not in {"started_shift", "ended_shift"}
    ]
    assert sum(segment["seconds"] for segment in duration_segments) == (
        out["timeline"]["working_seconds"]
        + out["timeline"]["pause_seconds"]
        + out["timeline"]["ended_shift_seconds"]
        + out["timeline"]["idle_seconds"]
    )
    assert sum(out["timeline"]["pause_by_reason"].values()) == out["timeline"][
        "pause_seconds"
    ]


async def test_breakdown_keeps_live_open_behavior(db_session) -> None:
    workspace = Workspace(name=f"timeline-live-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    step = await _seed_step_with_item(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
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
        None,
    )
    _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.WORKING,
        base,
        None,
    )

    out = await get_worker_linear_timeline_breakdown(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            work_date=base.date().isoformat(),
        )
    )

    working = out["segments"][1]
    assert working["state"] == "working"
    assert working["is_open"] is True
    assert working["steps"][0]["is_open"] is True
    assert working["steps"][0]["ended_by"] == "still_open"
    assert working["seconds"] >= 9 * 60


async def test_breakdown_unknown_worker_raises_not_found(db_session) -> None:
    workspace = Workspace(name=f"timeline-missing-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    with pytest.raises(NotFound):
        await get_worker_linear_timeline_breakdown(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id="usr_missing",
                work_date="2026-07-15",
            )
        )


async def test_breakdown_empty_worker_has_no_segments(db_session) -> None:
    workspace = Workspace(name=f"timeline-empty-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    out = await get_worker_linear_timeline_breakdown(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            work_date="2026-07-15",
        )
    )
    assert out["segments"] == []
    assert out["timeline"]["working_seconds"] == 0
    assert out["timeline"]["idle_seconds"] == 0
