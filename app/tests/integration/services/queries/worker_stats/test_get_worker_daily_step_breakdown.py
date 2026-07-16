from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_daily_step_breakdown import (
    get_worker_daily_step_breakdown,
)

DAY = datetime(2026, 7, 15, tzinfo=timezone.utc)


def _at(hour: int, minute: int = 0) -> datetime:
    return DAY.replace(hour=hour, minute=minute)


def _ctx(db_session, *, workspace_id, user_id, query_params) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_mgr", "role_name": "manager", "username": "mgr"},
        incoming_data={"user_id": user_id},
        query_params=query_params,
        session=db_session,
    )


async def _seed_worker(db_session, workspace_id: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(client_id=f"usr_{suffix}", username=f"user_{suffix}", email=f"{suffix}@e.com", password="s")
    db_session.add(user)
    # Roles are global singletons (unique name) — reuse the seeded one or create it.
    role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one_or_none()
    if role is None:
        role = Role(client_id=f"rol_{suffix}", name=RoleNameEnum.WORKER)
        db_session.add(role)
    await db_session.flush()
    ws_role = WorkspaceRole(client_id=f"wsr_{suffix}", workspace_id=workspace_id, role_id=role.client_id)
    db_session.add(ws_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            client_id=f"wsm_{suffix}", user_id=user.client_id,
            workspace_id=workspace_id, workspace_role_id=ws_role.client_id, is_active=True,
        )
    )
    await db_session.flush()
    return user


async def _seed_step(db_session, workspace_id: str, user_id: str) -> TaskStep:
    suffix = uuid4().hex[:8]
    section = WorkingSection(client_id=f"wsec_{suffix}", workspace_id=workspace_id, name=f"S {suffix}")
    db_session.add(section)
    await db_session.flush()
    task = Task(
        client_id=f"tsk_{suffix}", workspace_id=workspace_id, task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user_id,
    )
    db_session.add(task)
    await db_session.flush()
    step = TaskStep(
        client_id=f"tsp_{suffix}", workspace_id=workspace_id, task_id=task.client_id,
        working_section_id=section.client_id, working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.WORKING, readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0, completed_dependencies=0, created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    return step


async def _record(db_session, *, workspace_id, step_id, user_id, state, entered, exited):
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id, step_id=step_id, state=state,
            entered_at=entered, exited_at=exited, created_at=entered,
            created_by_id=user_id, credited_user_id=user_id,
        )
    )
    await db_session.flush()


@pytest.mark.integration
async def test_breakdown_settled_totals_active_record_and_reconciliation(db_session):
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    # Step A: worked 1h (closed) + paused 10m (closed) + completed.
    step_a = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=step_a.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(9), exited=_at(10))
    await _record(db_session, workspace_id=ws.client_id, step_id=step_a.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.PAUSED, entered=_at(10), exited=_at(10, 10))
    await _record(db_session, workspace_id=ws.client_id, step_id=step_a.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.COMPLETED, entered=_at(10, 10), exited=None)

    # Step B: currently working (open record) — running time, zero settled.
    step_b = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=step_b.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(11), exited=None)

    out = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=worker.client_id,
             query_params={"work_date": "2026-07-15", "limit": 50, "offset": 0}),
    )

    # Settled totals reflect only closed intervals; the open interval adds nothing.
    assert out["totals"] == {
        "working_seconds": 3600, "pause_seconds": 600,
        "ended_shift_seconds": 0, "completed_count": 1,
    }

    items = {i["client_id"]: i for i in out["steps"]["items"]}
    assert set(items) == {step_a.client_id, step_b.client_id}  # open-only step still listed

    a = items[step_a.client_id]
    assert a["contribution"] == {"working_seconds": 3600, "pause_seconds": 600, "ended_shift_seconds": 0, "completed_count": 1}
    assert a["active_record"] is None            # completed record is not a running interval
    assert a["last_completed_at"] is not None

    b = items[step_b.client_id]
    assert b["contribution"]["working_seconds"] == 0     # running time excluded from settled
    assert b["active_record"] == {"state": "working", "entered_at": _at(11).isoformat()}

    # contribution sort → active step (B) floats to top.
    assert out["steps"]["items"][0]["client_id"] == step_b.client_id


@pytest.mark.integration
async def test_breakdown_completed_sort_filters_to_completed(db_session):
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    step_worked = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=step_worked.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(9), exited=_at(10))
    step_done = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=step_done.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.COMPLETED, entered=_at(11), exited=None)

    out = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=worker.client_id,
             query_params={"work_date": "2026-07-15", "sort_by": "completed", "order": "desc", "limit": 50, "offset": 0}),
    )

    listed = [i["client_id"] for i in out["steps"]["items"]]
    assert listed == [step_done.client_id]                 # only completed step shown
    assert out["totals"]["working_seconds"] == 3600        # totals still full-day
