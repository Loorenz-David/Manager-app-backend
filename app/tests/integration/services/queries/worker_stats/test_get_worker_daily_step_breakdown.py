from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-15", "limit": 50, "offset": 0}),
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
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-15", "sort_by": "completed", "order": "desc", "limit": 50, "offset": 0}),
    )

    listed = [i["client_id"] for i in out["steps"]["items"]]
    assert listed == [step_done.client_id]                 # only completed step shown
    assert out["totals"]["working_seconds"] == 3600        # totals still full-day


@pytest.mark.integration
async def test_breakdown_aggregates_records_across_a_date_range(db_session):
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    # Day 1 (07-15): 1h working. Day 2 (07-16): 30m working. A record on 07-17 is outside.
    step = await _seed_step(db_session, ws.client_id, worker.client_id)
    d1 = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    d2 = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
    d3 = datetime(2026, 7, 17, 9, tzinfo=timezone.utc)
    await _record(db_session, workspace_id=ws.client_id, step_id=step.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=d1, exited=d1 + timedelta(hours=1))
    await _record(db_session, workspace_id=ws.client_id, step_id=step.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=d2, exited=d2 + timedelta(minutes=30))
    await _record(db_session, workspace_id=ws.client_id, step_id=step.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=d3, exited=d3 + timedelta(hours=2))

    out = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=worker.client_id,
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-16", "limit": 50, "offset": 0}),
    )

    # Range sums 07-15 + 07-16 only (5400s); 07-17 excluded.
    assert out["date_from"] == "2026-07-15"
    assert out["date_to"] == "2026-07-16"
    assert out["totals"]["working_seconds"] == 5400
    assert out["steps"]["items"][0]["contribution"]["working_seconds"] == 5400


async def _completed_step(db_session, ws_id: str, section_id: str, user_id: str, *, marked: bool = False):
    suffix = uuid4().hex[:8]
    task = Task(
        client_id=f"tsk_{suffix}", workspace_id=ws_id, task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user_id,
    )
    db_session.add(task)
    await db_session.flush()
    step = TaskStep(
        client_id=f"tsp_{suffix}", workspace_id=ws_id, task_id=task.client_id,
        working_section_id=section_id, working_section_name_snapshot="S",
        state=TaskStepStateEnum.COMPLETED, readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0, completed_dependencies=0, created_by_id=user_id,
        recorded_time_marked_wrong=marked,
    )
    db_session.add(step)
    await db_session.flush()
    return step


@pytest.mark.integration
async def test_breakdown_returns_real_median_iqr_per_step(db_session):
    # A flagged step's estimated_fill_by_strategy must always expose REAL mean/median/iqr,
    # independent of the selected time_strategy (the "compare all three" contract).
    ws = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)
    section = WorkingSection(client_id=f"wsec_{uuid4().hex[:8]}", workspace_id=ws.client_id, name="S")
    db_session.add(section)
    await db_session.flush()

    # 4 trusted completed steps in the lookback (before the view day), skewed durations.
    for i, secs in enumerate([600, 600, 600, 6000]):
        s = await _completed_step(db_session, ws.client_id, section.client_id, worker.client_id)
        entered = datetime(2026, 7, 8 + i, 9, tzinfo=timezone.utc)
        await _record(db_session, workspace_id=ws.client_id, step_id=s.client_id, user_id=worker.client_id,
                      state=TaskStepStateEnum.WORKING, entered=entered, exited=entered + timedelta(seconds=secs))

    # One flagged completed step on the view day.
    flagged = await _completed_step(db_session, ws.client_id, section.client_id, worker.client_id, marked=True)
    f_at = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    await _record(db_session, workspace_id=ws.client_id, step_id=flagged.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=f_at, exited=f_at + timedelta(seconds=9000))

    # Default request (no time_strategy → "median") — per-step strategies are always all-three.
    out = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=worker.client_id,
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-15", "limit": 50, "offset": 0}),
    )

    f = {i["client_id"]: i for i in out["steps"]["items"]}[flagged.client_id]
    assert f["is_time_inaccurate"] is True
    assert f["contribution"]["working_seconds"] == 0     # whole step left trusted
    assert f["wasted"]["working_seconds"] == 9000        # whole step wasted
    fill = f["estimated_fill_by_strategy"]["working"]
    # median/iqr computed from the sample [600,600,600,6000] (6000 trimmed) → 600, NOT collapsed.
    assert fill["median"] == 600.0
    assert fill["iqr"] == 600.0
    # mean rides stored section aggregates (none seeded here) → 0.0: proves the three are distinct.
    assert fill["mean"] == 0.0


@pytest.mark.integration
async def test_breakdown_excludes_steps_only_created_by_the_user(db_session):
    """A PENDING creation record must not credit its author with the step.

    `credited_user_id` is left NULL on step-creation records on purpose, so the
    `COALESCE(credited_user_id, created_by_id)` attribution would otherwise read
    "created by" as "worked by" and list every sibling step the creator never
    touched — including steps assigned to somebody else.
    """
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    db_session.add(ws)
    await db_session.flush()
    creator = await _seed_worker(db_session, ws.client_id)
    other = await _seed_worker(db_session, ws.client_id)

    # Worked step: a real closed working interval credited to the creator.
    worked = await _seed_step(db_session, ws.client_id, creator.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=worked.client_id, user_id=creator.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(9), exited=_at(10))

    # Sibling step the creator only brought into existence: PENDING, credited to nobody.
    # Mirrors create_task/add_task_steps, which never set credited_user_id.
    sibling = await _seed_step(db_session, ws.client_id, creator.client_id)
    db_session.add(
        StepStateRecord(
            workspace_id=ws.client_id, step_id=sibling.client_id,
            state=TaskStepStateEnum.PENDING, entered_at=_at(9), exited_at=None,
            created_at=_at(9), created_by_id=creator.client_id, credited_user_id=None,
        )
    )
    # Same, but the sibling is later worked by a different person entirely.
    other_step = await _seed_step(db_session, ws.client_id, creator.client_id)
    db_session.add(
        StepStateRecord(
            workspace_id=ws.client_id, step_id=other_step.client_id,
            state=TaskStepStateEnum.PENDING, entered_at=_at(9), exited_at=_at(11),
            created_at=_at(9), created_by_id=creator.client_id, credited_user_id=None,
        )
    )
    await db_session.flush()
    await _record(db_session, workspace_id=ws.client_id, step_id=other_step.client_id, user_id=other.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(11), exited=_at(12))

    out = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=creator.client_id,
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-15", "limit": 50, "offset": 0}),
    )

    listed = {i["client_id"] for i in out["steps"]["items"]}
    assert listed == {worked.client_id}, "creation-only steps must not be listed as worked"
    assert sibling.client_id not in listed
    assert other_step.client_id not in listed          # never leak another worker's step

    # Totals were always computed from time-bearing records, so they are untouched.
    assert out["totals"] == {
        "working_seconds": 3600, "pause_seconds": 0,
        "ended_shift_seconds": 0, "completed_count": 0,
    }

    # The other worker still sees their own step, with their own time.
    out_other = await get_worker_daily_step_breakdown(
        _ctx(db_session, workspace_id=ws.client_id, user_id=other.client_id,
             query_params={"date_from": "2026-07-15", "date_to": "2026-07-15", "limit": 50, "offset": 0}),
    )
    assert {i["client_id"] for i in out_other["steps"]["items"]} == {other_step.client_id}
    assert out_other["totals"]["working_seconds"] == 3600


@pytest.mark.integration
async def test_time_intentions_filter_out_steps_with_nothing_in_that_state(db_session):
    """`working`/`paused` list only steps that contribute to that metric.

    Each intention answers "where did THIS total come from", so zero-contribution
    steps must not pad the list — except when the step is live in that state, or
    (for `working`) flagged inaccurate, whose time lives in wasted/estimated.
    """
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    db_session.add(ws)
    await db_session.flush()
    worker = await _seed_worker(db_session, ws.client_id)

    # Worked 1h, never paused.
    worked_only = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=worked_only.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(9), exited=_at(10))

    # Worked 30m then paused 10m — belongs to both intentions.
    both = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=both.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(10), exited=_at(10, 30))
    await _record(db_session, workspace_id=ws.client_id, step_id=both.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.PAUSED, entered=_at(10, 30), exited=_at(10, 40))

    # Currently paused with ZERO settled pause time — must still show under `paused`.
    live_paused = await _seed_step(db_session, ws.client_id, worker.client_id)
    await _record(db_session, workspace_id=ws.client_id, step_id=live_paused.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(11), exited=_at(11, 20))
    await _record(db_session, workspace_id=ws.client_id, step_id=live_paused.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.PAUSED, entered=_at(11, 20), exited=None)

    # Flagged: 0 trusted seconds, time lives in wasted — must still show under `working`.
    flagged = await _seed_step(db_session, ws.client_id, worker.client_id)
    flagged.recorded_time_marked_wrong = True
    await _record(db_session, workspace_id=ws.client_id, step_id=flagged.client_id, user_id=worker.client_id,
                  state=TaskStepStateEnum.WORKING, entered=_at(12), exited=_at(13))
    await db_session.flush()

    async def _ids(sort_by: str) -> set[str]:
        out = await get_worker_daily_step_breakdown(
            _ctx(db_session, workspace_id=ws.client_id, user_id=worker.client_id,
                 query_params={"date_from": "2026-07-15", "date_to": "2026-07-15",
                               "sort_by": sort_by, "limit": 50, "offset": 0}),
        )
        return {i["client_id"] for i in out["steps"]["items"]}

    # `paused`: only real pause time or a live pause. No worked-only, no flagged.
    assert await _ids("paused") == {both.client_id, live_paused.client_id}

    # `working`: settled work, plus the flagged step whose trusted time is 0.
    assert await _ids("working") == {
        worked_only.client_id, both.client_id, live_paused.client_id, flagged.client_id,
    }

    # `contribution` stays the unfiltered "everything touched" view.
    assert await _ids("contribution") == {
        worked_only.client_id, both.client_id, live_paused.client_id, flagged.client_id,
    }
