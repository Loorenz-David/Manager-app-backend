from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
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
from beyo_manager.services.queries.worker_stats.list_workers_insights import list_workers_insights
from beyo_manager.services.queries.worker_stats.list_workers_last_interacted_step import (
    list_workers_last_interacted_step,
)
from beyo_manager.services.queries.worker_stats.list_workers_totals import list_workers_totals


def _ctx(db_session, *, workspace_id: str, query_params: dict | None = None) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_mgr", "role_name": "manager", "username": "mgr"},
        incoming_data={},
        query_params=query_params or {},
        session=db_session,
    )


async def _seed_worker(db_session, workspace_id: str, *, username: str | None = None) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}", username=username or f"user_{suffix}",
        email=f"{suffix}@e.com", password="s",
    )
    db_session.add(user)
    # Roles are global singletons (unique name) — reuse the seeded one or create it.
    role = (await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))).scalar_one_or_none()
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


@pytest.mark.integration
@freeze_time("2026-07-15T12:00:00+00:00")
async def test_totals_returns_settled_daily_stats_and_live_running(db_session):
    # Freeze at a fixed mid-day instant: the live-running detection windows the open
    # interval to `now`'s UTC day, so a `now - 30min` interval seeded within ~30 min of
    # UTC midnight would otherwise fall on the previous day and be missed.
    ws = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    now = datetime.now(timezone.utc)
    work_date = now.date()
    # Settled daily row (what reconcile would have written).
    db_session.add(
        UserDailyWorkStats(
            workspace_id=ws.client_id, user_id=worker.client_id, user_display_name_snapshot="w",
            work_date=work_date, total_working_seconds=3600, total_pause_seconds=600, total_completed_count=2,
        )
    )
    # One currently-open WORKING interval → live running, nothing settled from it.
    step = await _seed_step(db_session, ws.client_id, worker.client_id)
    db_session.add(
        StepStateRecord(
            workspace_id=ws.client_id, step_id=step.client_id, state=TaskStepStateEnum.WORKING,
            entered_at=now - timedelta(minutes=30), exited_at=None, created_at=now - timedelta(minutes=30),
            created_by_id=worker.client_id, credited_user_id=worker.client_id,
        )
    )
    await db_session.flush()

    out = await list_workers_totals(_ctx(db_session, workspace_id=ws.client_id))

    assert out["workers_pagination"] == {"has_more": False, "limit": 50, "offset": 0, "total": 1}
    assert len(out["workers"]) == 1
    w = out["workers"][0]
    assert set(w) == {"user", "daily_stats", "running"}
    assert w["user"]["client_id"] == worker.client_id
    assert w["daily_stats"] == {
        "date_from": work_date.isoformat(),
        "date_to": work_date.isoformat(),
        "total_working_seconds": 3600,
        "total_pause_seconds": 600,
        "total_completed_count": 2,
        "time_quality": {
            "strategy": "median",
            "working": {"trusted": 3600, "wasted": 0, "inaccurate_step_count": 0, "estimated_fill": 0.0, "trusted_sample_size": 0},
            "paused": {"trusted": 600, "wasted": 0, "inaccurate_step_count": 0, "estimated_fill": 0.0, "trusted_sample_size": 0},
        },
    }
    # Live add-on from the open interval (excluded from settled daily_stats).
    assert w["running"]["working_open_count"] == 1
    assert w["running"]["working_seconds"] > 0
    assert w["running"]["pause_open_count"] == 0


@pytest.mark.integration
async def test_totals_sums_daily_rows_across_a_date_range(db_session):
    ws = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    # Three past days, each with its own settled row.
    days = [date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]
    for i, d in enumerate(days):
        db_session.add(
            UserDailyWorkStats(
                workspace_id=ws.client_id, user_id=worker.client_id, user_display_name_snapshot="w",
                work_date=d, total_working_seconds=1000 * (i + 1), total_pause_seconds=100,
                total_completed_count=i + 1,
            )
        )
    await db_session.flush()

    # Range covering all three; a fourth day (07-13) is outside and must be excluded.
    out = await list_workers_totals(
        _ctx(db_session, workspace_id=ws.client_id,
             query_params={"date_from": "2026-07-10", "date_to": "2026-07-12"})
    )

    w = out["workers"][0]
    assert w["daily_stats"] == {
        "date_from": "2026-07-10",
        "date_to": "2026-07-12",
        "total_working_seconds": 6000,   # 1000 + 2000 + 3000
        "total_pause_seconds": 300,      # 100 * 3
        "total_completed_count": 6,      # 1 + 2 + 3
        "time_quality": {
            "strategy": "median",
            "working": {"trusted": 6000, "wasted": 0, "inaccurate_step_count": 0, "estimated_fill": 0.0, "trusted_sample_size": 0},
            "paused": {"trusted": 300, "wasted": 0, "inaccurate_step_count": 0, "estimated_fill": 0.0, "trusted_sample_size": 0},
        },
    }
    # Past-only range → no live running.
    assert w["running"]["working_open_count"] == 0
    assert w["running"]["working_seconds"] == 0


@pytest.mark.integration
async def test_totals_mean_estimate_floored_when_trusted_sample_too_thin(db_session):
    # Reproduces the pathological case: 18 of 20 completed steps flagged → only 2 trusted
    # completed steps back the mean, which would explode (18 × trusted/2). The floor
    # suppresses it to 0 and surfaces trusted_sample_size so the frontend can gate.
    ws = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)
    db_session.add(
        UserDailyWorkStats(
            workspace_id=ws.client_id, user_id=worker.client_id, user_display_name_snapshot="w",
            work_date=date(2026, 7, 14),
            total_working_seconds=495, total_pause_seconds=33583, total_completed_count=20,
            inaccurate_working_seconds=119, inaccurate_pause_seconds=22, inaccurate_step_count=18,
        )
    )
    await db_session.flush()

    out = await list_workers_totals(
        _ctx(db_session, workspace_id=ws.client_id,
             query_params={"date_from": "2026-07-14", "date_to": "2026-07-14", "time_strategy": "mean"})
    )
    tq = out["workers"][0]["daily_stats"]["time_quality"]
    assert tq["strategy"] == "mean"
    assert tq["working"]["trusted_sample_size"] == 2   # 20 completed − 18 flagged (view-range)
    assert tq["working"]["wasted"] == 119
    assert tq["paused"]["wasted"] == 22
    # Floored (denominator 2 < 4) — no runaway 4455 / 302247 estimates.
    assert tq["working"]["estimated_fill"] == 0.0
    assert tq["paused"]["estimated_fill"] == 0.0


@pytest.mark.integration
async def test_split_endpoints_share_roster_and_return_disjoint_shapes(db_session):
    ws = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="W")
    db_session.add(ws)
    await db_session.flush()
    # Two workers, deterministic username order (roster orders by username ASC).
    worker_a = await _seed_worker(db_session, ws.client_id, username="worker_a")
    worker_b = await _seed_worker(db_session, ws.client_id, username="worker_b")
    expected_order = [worker_a.client_id, worker_b.client_id]

    ctx = lambda: _ctx(db_session, workspace_id=ws.client_id)  # noqa: E731
    last = await list_workers_last_interacted_step(ctx())
    totals = await list_workers_totals(ctx())
    insights = await list_workers_insights(ctx())

    # Identical roster, ordering, and pagination envelope across the three.
    expected_pagination = {"has_more": False, "limit": 50, "offset": 0, "total": 2}
    for out in (last, totals, insights):
        assert out["workers_pagination"] == expected_pagination
        assert [w["user"]["client_id"] for w in out["workers"]] == expected_order

    # Disjoint, single-responsibility shapes.
    assert all(set(w) == {"user", "last_interacted_step", "batch"} for w in last["workers"])
    assert all(set(w) == {"user", "daily_stats", "running"} for w in totals["workers"])
    assert all(set(w) == {"user", "insights"} for w in insights["workers"])

    # Idle workers: null snapshot, zero-filled totals, empty insights.
    assert last["workers"][0]["last_interacted_step"] is None
    assert last["workers"][0]["batch"] is None
    assert totals["workers"][0]["daily_stats"]["total_working_seconds"] == 0
    assert totals["workers"][0]["running"]["working_open_count"] == 0
    assert insights["workers"][0]["insights"] == []
