"""Completion/issue counters must survive replay.

The analytics queue is at-least-once: the handler commits its work in one session and
the task is only marked COMPLETED in a later one, so any failure in between re-runs the
handler. These counters used to be blind `+= 1` increments, which inflated on every
retry. They are now recomputed-and-SET from records, mirroring the time path in
test_reconcile_user_time.py.

Tested at the reconcile level rather than through handle_process_step_transition on
purpose: the handler opens its own session and commits, which would escape the
db_session fixture's rollback and write into whatever database the suite points at.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import (
    WorkingSectionDailyWorkStats,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_completion_reconcile_deltas,
    reconcile_user_day_completions,
)
from beyo_manager.services.tasks.analytics.process_step_transition import (
    _recompute_step_completion_totals,
)

DAY = date(2026, 7, 18)
BASE = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 18, 23, 0, tzinfo=timezone.utc)


async def _mk(db_session):
    suffix = uuid4().hex[:8]
    ws = Workspace(client_id=f"ws_{suffix}", name="W")
    user = User(
        client_id=f"usr_{suffix}", username=f"u_{suffix}", email=f"{suffix}@e.com", password="s"
    )
    db_session.add_all([ws, user])
    await db_session.flush()
    section = WorkingSection(
        client_id=f"wsec_{suffix}",
        workspace_id=ws.client_id,
        name="Sew",
        allows_batch_working=True,
    )
    db_session.add(section)
    await db_session.flush()
    return ws, user, section


async def _completed_step(db_session, ws, section, user, *, at_min, credited_user=None):
    """A step whose COMPLETED record entered at BASE+at_min (the completion instant)."""
    suffix = uuid4().hex[:8]
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=ws.client_id,
        task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    step = TaskStep(
        client_id=f"tsp_{suffix}",
        workspace_id=ws.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=True,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=ws.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.COMPLETED,
        entered_at=BASE + timedelta(minutes=at_min),
        exited_at=None,
        created_at=BASE + timedelta(minutes=at_min),
        created_by_id=user.client_id,
        credited_user_id=(credited_user.client_id if credited_user else None),
    )
    db_session.add(record)
    await db_session.flush()
    return step, record


async def _add_issues(db_session, ws, section, user, step, count):
    suffix = uuid4().hex[:8]
    category = ItemCategory(
        client_id=f"itc_{suffix}",
        workspace_id=ws.client_id,
        name="Chair",
        major_category=list(ItemMajorCategoryEnum)[0],
    )
    db_session.add(category)
    await db_session.flush()
    item = Item(
        client_id=f"itm_{suffix}",
        workspace_id=ws.client_id,
        item_category_id=category.client_id,
    )
    db_session.add(item)
    await db_session.flush()
    for _ in range(count):
        db_session.add(
            ItemIssue(
                workspace_id=ws.client_id,
                item_id=item.client_id,
                step_id=step.client_id,
                worker_id=user.client_id,
                working_section_id=section.client_id,
                item_category_id=category.client_id,
                issue_type_snapshot="scratch",
                intensity=1,
            )
        )
    await db_session.flush()


async def _reconcile(db_session, ws, user, day=DAY):
    result = await reconcile_user_day_completions(
        db_session, ws.client_id, user.client_id, "u", day, NOW
    )
    await apply_completion_reconcile_deltas(
        db_session, ws.client_id, user.client_id, "u", day, NOW, result
    )
    await db_session.flush()
    return result


async def _snapshot(db_session, ws, user, section, day=DAY):
    """The completion columns across all four rollup tables."""

    async def _row(model, *conditions):
        return (await db_session.execute(select(model).where(*conditions))).scalar_one_or_none()

    def _vals(row):
        if row is None:
            return None
        return (
            row.total_completed_count,
            row.total_issues_count,
            row.total_issues_resolved_count,
        )

    return {
        "user_daily": _vals(
            await _row(
                UserDailyWorkStats,
                UserDailyWorkStats.workspace_id == ws.client_id,
                UserDailyWorkStats.user_id == user.client_id,
                UserDailyWorkStats.work_date == day,
            )
        ),
        "lifetime": _vals(
            await _row(
                UserLifetimeStats,
                UserLifetimeStats.workspace_id == ws.client_id,
                UserLifetimeStats.user_id == user.client_id,
            )
        ),
        "user_section_daily": _vals(
            await _row(
                UserSectionDailyWorkStats,
                UserSectionDailyWorkStats.workspace_id == ws.client_id,
                UserSectionDailyWorkStats.user_id == user.client_id,
                UserSectionDailyWorkStats.working_section_id == section.client_id,
                UserSectionDailyWorkStats.work_date == day,
            )
        ),
        "section_daily": _vals(
            await _row(
                WorkingSectionDailyWorkStats,
                WorkingSectionDailyWorkStats.workspace_id == ws.client_id,
                WorkingSectionDailyWorkStats.working_section_id == section.client_id,
                WorkingSectionDailyWorkStats.work_date == day,
            )
        ),
    }


@pytest.mark.integration
async def test_replaying_the_same_reconcile_does_not_inflate_any_rollup(db_session):
    """THE regression guard for the retry double-count.

    A blind `+= 1` passes the first assertion and fails the second.
    """
    ws, user, section = await _mk(db_session)
    for minute in (0, 30, 60):
        await _completed_step(db_session, ws, section, user, at_min=minute)

    await _reconcile(db_session, ws, user)
    first = await _snapshot(db_session, ws, user, section)
    assert first["user_daily"][0] == 3

    await _reconcile(db_session, ws, user)
    second = await _snapshot(db_session, ws, user, section)

    assert second == first, "replaying the reconcile changed a rollup — counters are not idempotent"


@pytest.mark.integration
async def test_all_four_rollups_agree_on_the_completion_count(db_session):
    ws, user, section = await _mk(db_session)
    for minute in (0, 30):
        await _completed_step(db_session, ws, section, user, at_min=minute)

    await _reconcile(db_session, ws, user)
    snap = await _snapshot(db_session, ws, user, section)

    assert [v[0] for v in snap.values()] == [2, 2, 2, 2]


@pytest.mark.integration
async def test_issues_are_counted_per_completed_step_and_survive_replay(db_session):
    ws, user, section = await _mk(db_session)
    step, _ = await _completed_step(db_session, ws, section, user, at_min=0)
    await _add_issues(db_session, ws, section, user, step, count=3)

    await _reconcile(db_session, ws, user)
    first = await _snapshot(db_session, ws, user, section)
    # Resolved mirrors total: reaching COMPLETED is what resolves a step's issues.
    assert first["user_daily"] == (1, 3, 3)

    await _reconcile(db_session, ws, user)
    assert await _snapshot(db_session, ws, user, section) == first


@pytest.mark.integration
async def test_completion_is_attributed_to_the_credited_user_not_the_performer(db_session):
    """A manager closing a step on a worker's behalf credits the worker."""
    ws, performer, section = await _mk(db_session)
    worker = User(
        client_id=f"usr_{uuid4().hex[:8]}",
        username=f"w_{uuid4().hex[:6]}",
        email=f"{uuid4().hex[:8]}@e.com",
        password="s",
    )
    db_session.add(worker)
    await db_session.flush()

    await _completed_step(db_session, ws, section, performer, at_min=0, credited_user=worker)

    await _reconcile(db_session, ws, worker)
    await _reconcile(db_session, ws, performer)

    credited = await _snapshot(db_session, ws, worker, section)
    assert credited["user_daily"][0] == 1
    assert credited["lifetime"][0] == 1

    performer_daily = (
        await db_session.execute(
            select(UserDailyWorkStats).where(
                UserDailyWorkStats.workspace_id == ws.client_id,
                UserDailyWorkStats.user_id == performer.client_id,
                UserDailyWorkStats.work_date == DAY,
            )
        )
    ).scalar_one_or_none()
    assert performer_daily is None or performer_daily.total_completed_count == 0


@pytest.mark.integration
async def test_removing_a_record_pulls_the_counters_back_down(db_session):
    """Proves SET-not-increment: a retracted completion must be able to decrement."""
    ws, user, section = await _mk(db_session)
    _, record = await _completed_step(db_session, ws, section, user, at_min=0)
    await _completed_step(db_session, ws, section, user, at_min=30)

    await _reconcile(db_session, ws, user)
    assert (await _snapshot(db_session, ws, user, section))["user_daily"][0] == 2

    record.is_deleted = True
    await db_session.flush()
    await _reconcile(db_session, ws, user)

    after = await _snapshot(db_session, ws, user, section)
    assert after["user_daily"][0] == 1
    assert after["lifetime"][0] == 1, "the Σ table must follow the recomputed value downward"


@pytest.mark.integration
async def test_step_level_counters_are_set_not_incremented(db_session):
    ws, user, section = await _mk(db_session)
    step, _ = await _completed_step(db_session, ws, section, user, at_min=0)
    await _add_issues(db_session, ws, section, user, step, count=2)

    for _ in range(3):
        await _recompute_step_completion_totals(db_session, ws.client_id, step.client_id, step)
        await db_session.flush()

    assert step.total_completed_count == 1
    assert step.total_issues_count == 2
    assert step.total_issues_resolved_count == 2
