from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import (
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
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


async def _add_step_record(
    db_session,
    workspace_id: str,
    user_id: str,
    step_id: str,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    reason: str | None = None,
) -> None:
    pause_reason_id = None
    if reason is not None:
        # Scoped to this test's own workspace (PauseReason is workspace-scoped data) —
        # find-or-create rather than assuming some other workspace's row happens to exist in
        # whatever database this suite runs against. Keyed on (workspace_id, name) — not
        # `slug`, which has a table-WIDE unique index (shared across every workspace) reserved
        # for the real bootstrap-seeded rows; reusing one of those slugs here would collide
        # with whatever workspace first claimed it in this database.
        pause_reason_id = await db_session.scalar(
            select(PauseReason.client_id).where(
                PauseReason.workspace_id == workspace_id,
                PauseReason.name == reason,
            )
        )
        if pause_reason_id is None:
            pause_reason = PauseReason(
                workspace_id=workspace_id,
                name=reason,
                pause_type=PauseTypeEnum.PERSONAL,
            )
            db_session.add(pause_reason)
            await db_session.flush()
            pause_reason_id = pause_reason.client_id
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step_id,
            state=state,
            pause_reason_id=pause_reason_id,
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
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.WORKING,
        base,
        pause_at,
    )
    await _add_step_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        TaskStepStateEnum.PAUSED,
        pause_at,
        idle_at,
        reason="pause_coffee_break",
    )
    await _add_step_record(
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

    assert set(out) == {"user", "timeline", "pause_reasons", "segments", "segments_truncated"}
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
    # Block owner follows the most-recently-started step pause, not the worker-level
    # reason ("cleaning station"); the only step pause here is coffee break.
    pause_reason_id = await db_session.scalar(
        select(PauseReason.client_id).where(
            PauseReason.workspace_id == workspace.client_id,
            PauseReason.name == "pause_coffee_break",
        )
    )
    assert paused["reason"] == pause_reason_id
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
        "pause_reason",
        "description",
        "entered_at",
        "exited_at",
        "is_open",
        "ended_by",
    }
    # working["steps"][0] is not itself paused (it's the WORKING step in this segment), so its
    # own pause_reason is None; check the segment that actually is paused instead.
    assert paused["steps"][0]["pause_reason"]["client_id"] == pause_reason_id
    assert paused["steps"][0]["pause_reason"]["name"] == "pause_coffee_break"
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


@freeze_time("2026-07-15T12:00:00+00:00")
async def test_breakdown_keeps_live_open_behavior(db_session) -> None:
    # Freeze time so the service's internal `datetime.now()` is a fixed mid-day instant;
    # otherwise, when the suite runs within ~10 min of UTC midnight, `base` lands on the
    # previous day and the open record clamps to the day boundary instead of "now".
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
    await _add_step_record(
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


async def test_segment_steps_are_scoped_to_the_shift(db_session) -> None:
    # A step paused on a PREVIOUS day, still open and overlapping today's paused segment,
    # must not appear in that segment's steps[] — the detail is scoped to the same shift as
    # the segment state (mirrors the reconstruction), so no carryover leaks in.
    workspace = Workspace(name=f"steps-scope-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)

    async def _mk_step():
        suffix = uuid4().hex[:8]
        section = WorkingSection(workspace_id=workspace.client_id, name=f"sec-{suffix}")
        task = Task(
            workspace_id=workspace.client_id, task_scalar_id=int(suffix[:6], 16),
            task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=worker.client_id,
        )
        db_session.add_all([section, task])
        await db_session.flush()
        step = TaskStep(
            workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id,
            working_section_name_snapshot=section.name, state=TaskStepStateEnum.COMPLETED,
            created_by_id=worker.client_id,
        )
        db_session.add(step)
        await db_session.flush()
        return step

    carry_step = await _mk_step()
    inshift_step = await _mk_step()

    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)

    def at(mn):
        return base + timedelta(minutes=mn)

    _add_shift_record(db_session, workspace.client_id, worker.client_id,
                      UserShiftStateEnum.STARTED_SHIFT, base, base)
    _add_shift_record(db_session, workspace.client_id, worker.client_id,
                      UserShiftStateEnum.IN_PAUSE, at(10), at(20), reason="pause_lunch_break")
    _add_shift_record(db_session, workspace.client_id, worker.client_id,
                      UserShiftStateEnum.ENDED_SHIFT, at(30), at(30))
    # carryover pause from yesterday, still open into and overlapping the paused segment
    await _add_step_record(db_session, workspace.client_id, worker.client_id, carry_step.client_id,
                     TaskStepStateEnum.PAUSED, base - timedelta(days=1), at(15),
                     reason="pause_other_task_priority")
    # legitimate in-shift pause
    await _add_step_record(db_session, workspace.client_id, worker.client_id, inshift_step.client_id,
                     TaskStepStateEnum.PAUSED, at(10), at(20),
                     reason="pause_lunch_break")
    await db_session.flush()

    out = await get_worker_linear_timeline_breakdown(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=worker.client_id, work_date="2026-07-15")
    )
    paused = next(s for s in out["segments"] if s["state"] == "paused")
    step_ids = {st["step_id"] for st in paused["steps"]}
    assert inshift_step.client_id in step_ids
    assert carry_step.client_id not in step_ids  # carryover excluded — belongs to a prior shift
