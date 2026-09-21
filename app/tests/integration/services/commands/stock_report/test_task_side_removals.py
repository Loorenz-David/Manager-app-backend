"""Plan 11 C1 — the task-deletion hook in `delete_task.py` (master plan §6.1b,
intention §5B MC-14 row 1). Every non-deleted assignment of the task, any state,
removed through `remove_assignment` before the task itself is soft-deleted.

Fixture: F0 with A created through `CR`. This file exercises one representative row
per distinct code path; row-by-row transcription and mutation arming belong to the
tester (see the implementer handoff).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.tasks.delete_task import delete_task
from tests.helpers.stock_report import assert_stock_report_clean, make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


async def _make_row(db_session, seeded, *, criteria=None, quantity_requested=10):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _second_pair(db_session, seeded, suffix):
    next_scalar_id = (
        await db_session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    task = Task(
        client_id=f"tsk_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item = Item(
        client_id=f"itm_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add_all([task, item])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    return task, item


async def _CR(db_session, seeded, row, task, item):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": task.client_id,
                    "item_id": item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    return result["stock_task_assignments"][0]["client_id"]


async def _delete_task(db_session, seeded, task):
    ctx = make_ctx(
        db_session, seeded, role_name="manager", incoming_data={"client_id": task.client_id}
    )
    return await delete_task(ctx)


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _counters(db_session, row_id):
    return (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()


async def test_c1a_deleting_task_removes_active_assignment_and_updates_counters(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _delete_task(db_session, seeded, seeded.task)

    task = await db_session.get(Task, seeded.task.client_id)
    assert task.is_deleted is True
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert assignment.deleted_by_id == seeded.manager.client_id
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1b_deleting_task_removes_resolved_assignment_without_counter_change(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _delete_task(db_session, seeded, seeded.task)

    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert await _counters(db_session, row.client_id) == (0, 0, 0)


async def test_c1c_deleting_task_removes_every_non_deleted_assignment_of_the_task(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    a_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    a = await _fresh_assignment(db_session, a_id)
    await move_assignment(
        db_session, a, S.FAILED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    row2 = await _make_row(db_session, seeded, criteria={}, quantity_requested=1)
    b_id = await _CR(db_session, seeded, row2, seeded.task, seeded.item)

    await _delete_task(db_session, seeded, seeded.task)

    a = await _fresh_assignment(db_session, a_id)
    b = await _fresh_assignment(db_session, b_id)
    assert a.is_deleted is True
    assert b.is_deleted is True
    assert await _counters(db_session, row2.client_id) == (0, 0, 0)
