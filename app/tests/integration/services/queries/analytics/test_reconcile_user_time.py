from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_reconcile_deltas,
    reconcile_user_day_time,
)
from beyo_manager.services.tasks.analytics.process_step_transition import _recompute_step_time_totals

DAY = date(2026, 7, 18)
BASE = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 18, 23, 0, tzinfo=timezone.utc)


async def _mk(db_session):
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    user = User(client_id=f"usr_{suffix}", username=f"u_{suffix}", email=f"{suffix}@e.com", password="s")
    db_session.add_all([ws, user])
    await db_session.flush()
    section = WorkingSection(client_id=f"wsec_{suffix}", workspace_id=ws.client_id, name="Sew",
                             allows_batch_working=True)
    db_session.add(section)
    await db_session.flush()
    return ws, user, section


async def _batch_step(
    db_session,
    ws,
    section,
    user,
    *,
    start_min,
    end_min,
    batchable=True,
    inaccurate=False,
):
    suffix = uuid4().hex[:8]
    task = Task(client_id=f"tsk_{suffix}", workspace_id=ws.client_id, task_scalar_id=int(suffix[:6], 16),
                task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    db_session.add(task)
    await db_session.flush()
    step = TaskStep(client_id=f"tsp_{suffix}", workspace_id=ws.client_id, task_id=task.client_id,
                    working_section_id=section.client_id, working_section_name_snapshot=section.name,
                    allows_batch_working=batchable, state=TaskStepStateEnum.COMPLETED,
                    readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0,
                    completed_dependencies=0, created_by_id=user.client_id,
                    recorded_time_marked_wrong=inaccurate)
    db_session.add(step)
    await db_session.flush()
    rec = StepStateRecord(workspace_id=ws.client_id, step_id=step.client_id, state=TaskStepStateEnum.WORKING,
                          entered_at=BASE + timedelta(minutes=start_min),
                          exited_at=BASE + timedelta(minutes=end_min),
                          created_at=BASE + timedelta(minutes=start_min),
                          created_by_id=user.client_id, credited_user_id=user.client_id)
    db_session.add(rec)
    await db_session.flush()
    return step


@pytest.mark.integration
async def test_flagged_step_moves_whole_time_to_wasted_facts(db_session):
    ws, user, section = await _mk(db_session)
    step = await _batch_step(
        db_session,
        ws,
        section,
        user,
        start_min=0,
        end_min=60,
        inaccurate=True,
    )

    result = await reconcile_user_day_time(db_session, ws.client_id, user.client_id, "u", DAY, NOW)
    await apply_reconcile_deltas(db_session, ws.client_id, user.client_id, "u", DAY, NOW, result)
    await _recompute_step_time_totals(db_session, ws.client_id, step.client_id, NOW)
    await db_session.flush()

    daily = (await db_session.execute(
        select(UserDailyWorkStats).where(
            UserDailyWorkStats.workspace_id == ws.client_id,
            UserDailyWorkStats.user_id == user.client_id,
            UserDailyWorkStats.work_date == DAY,
        )
    )).scalar_one()
    section_row = (await db_session.execute(
        select(WorkingSectionDailyWorkStats).where(
            WorkingSectionDailyWorkStats.workspace_id == ws.client_id,
            WorkingSectionDailyWorkStats.working_section_id == section.client_id,
            WorkingSectionDailyWorkStats.work_date == DAY,
        )
    )).scalar_one()
    lifetime = (await db_session.execute(
        select(UserLifetimeStats).where(
            UserLifetimeStats.workspace_id == ws.client_id,
            UserLifetimeStats.user_id == user.client_id,
        )
    )).scalar_one()

    assert daily.total_working_seconds == 0
    assert daily.inaccurate_working_seconds == 3600
    assert daily.inaccurate_step_count == 1
    assert section_row.inaccurate_working_seconds == 3600
    assert section_row.inaccurate_step_count == 1
    assert lifetime.inaccurate_working_seconds == 3600
    assert lifetime.inaccurate_step_count == 1
    assert step.total_working_seconds == 0
    assert step.inaccurate_working_seconds == 3600


@pytest.mark.integration
async def test_batch_of_5_averages_and_sums_to_real_time(db_session):
    ws, user, section = await _mk(db_session)
    # 5 batchable steps each WORKING [0,60] -> each 12 min; day total = 60 min.
    for _ in range(5):
        await _batch_step(db_session, ws, section, user, start_min=0, end_min=60)

    result = await reconcile_user_day_time(db_session, ws.client_id, user.client_id, "u", DAY, NOW)
    await apply_reconcile_deltas(db_session, ws.client_id, user.client_id, "u", DAY, NOW, result)
    await db_session.flush()

    daily = (await db_session.execute(
        select(UserDailyWorkStats).where(UserDailyWorkStats.workspace_id == ws.client_id,
                                         UserDailyWorkStats.user_id == user.client_id,
                                         UserDailyWorkStats.work_date == DAY))).scalar_one()
    assert daily.total_working_seconds == 3600            # real 60 min, not 5 * 3600
    assert daily.total_working_count == 5                 # 5 closed intervals

    section_row = (await db_session.execute(
        select(WorkingSectionDailyWorkStats).where(
            WorkingSectionDailyWorkStats.workspace_id == ws.client_id,
            WorkingSectionDailyWorkStats.working_section_id == section.client_id,
            WorkingSectionDailyWorkStats.work_date == DAY))).scalar_one()
    assert section_row.total_working_seconds == 3600

    lifetime = (await db_session.execute(
        select(UserLifetimeStats).where(UserLifetimeStats.workspace_id == ws.client_id,
                                        UserLifetimeStats.user_id == user.client_id))).scalar_one()
    assert lifetime.total_working_seconds == 3600


@pytest.mark.integration
async def test_reconcile_is_idempotent(db_session):
    ws, user, section = await _mk(db_session)
    for _ in range(3):
        await _batch_step(db_session, ws, section, user, start_min=0, end_min=60)  # 3 -> each 20 min, day 60

    for _ in range(2):  # run twice
        result = await reconcile_user_day_time(db_session, ws.client_id, user.client_id, "u", DAY, NOW)
        await apply_reconcile_deltas(db_session, ws.client_id, user.client_id, "u", DAY, NOW, result)
        await db_session.flush()

    daily = (await db_session.execute(
        select(UserDailyWorkStats).where(UserDailyWorkStats.workspace_id == ws.client_id,
                                         UserDailyWorkStats.user_id == user.client_id,
                                         UserDailyWorkStats.work_date == DAY))).scalar_one()
    lifetime = (await db_session.execute(
        select(UserLifetimeStats).where(UserLifetimeStats.workspace_id == ws.client_id,
                                        UserLifetimeStats.user_id == user.client_id))).scalar_one()
    assert daily.total_working_seconds == 3600            # not doubled
    assert lifetime.total_working_seconds == 3600          # delta maths stayed consistent across runs


@pytest.mark.integration
async def test_step_time_totals_averaged(db_session):
    ws, user, section = await _mk(db_session)
    # 3 batchable steps [0,60] -> each step's TaskStep.total_working_seconds = 20 min (not 60).
    steps = [await _batch_step(db_session, ws, section, user, start_min=0, end_min=60) for _ in range(3)]

    await _recompute_step_time_totals(db_session, ws.client_id, steps[0].client_id, NOW)
    await db_session.flush()
    await db_session.refresh(steps[0])
    assert steps[0].total_working_seconds == 1200      # 3600 / 3, not 3600
    assert steps[0].total_working_count == 1


@pytest.mark.integration
async def test_non_batch_step_keeps_full_time(db_session):
    ws, user, section = await _mk(db_session)
    # One non-batch step [0,60] overlapping one batch step [0,60].
    await _batch_step(db_session, ws, section, user, start_min=0, end_min=60, batchable=False)
    await _batch_step(db_session, ws, section, user, start_min=0, end_min=60, batchable=True)

    result = await reconcile_user_day_time(db_session, ws.client_id, user.client_id, "u", DAY, NOW)
    await apply_reconcile_deltas(db_session, ws.client_id, user.client_id, "u", DAY, NOW, result)
    await db_session.flush()

    daily = (await db_session.execute(
        select(UserDailyWorkStats).where(UserDailyWorkStats.workspace_id == ws.client_id,
                                         UserDailyWorkStats.user_id == user.client_id,
                                         UserDailyWorkStats.work_date == DAY))).scalar_one()
    # non-batch full 3600 + batch alone-in-lane 3600 = 7200
    assert daily.total_working_seconds == 7200
