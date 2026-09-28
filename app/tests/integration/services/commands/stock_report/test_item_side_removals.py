"""Plan 11 C2/C3 — the item-side removal hooks: `remove_item_from_task.py` (PRIMARY
unlink, MC-14 row 2) and `delete_item.py` (item deletion, MC-14 row 3).

Fixture: F0 with A created through `CR`. One representative row per distinct code
path; row-by-row transcription and mutation arming belong to the tester.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.items.delete_item import delete_item
from beyo_manager.services.commands.tasks.add_item_to_task import add_item_to_task
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.tasks.remove_item_from_task import (
    remove_item_from_task,
)
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    seed_stock_report_workspace,
)

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


async def _second_item(db_session, seeded, suffix, *, related_on_task=None):
    from beyo_manager.domain.items.enums import ItemStateEnum

    item = Item(
        client_id=f"itm_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add(item)
    await db_session.flush()
    if related_on_task is not None:
        db_session.add(
            TaskItem(
                client_id=f"tim_{suffix}_{seeded.workspace.client_id}",
                workspace_id=seeded.workspace.client_id,
                task_id=related_on_task.client_id,
                item_id=item.client_id,
                role=TaskItemRoleEnum.RELATED,
                created_by_id=seeded.manager.client_id,
            )
        )
        await db_session.flush()
    return item


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


def _capture_unlink_events(monkeypatch):
    return capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.tasks.remove_item_from_task.event_bus.dispatch",
    )


def _capture_delete_item_events(monkeypatch):
    return capture_dispatch(
        monkeypatch, "beyo_manager.services.commands.items.delete_item.event_bus.dispatch"
    )


async def _remove_item_from_task(db_session, seeded, task, item):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="manager",
        incoming_data={"task_id": task.client_id, "item_id": item.client_id},
    )
    return await remove_item_from_task(ctx)


async def _delete_item(db_session, seeded, item):
    ctx = make_ctx(
        db_session, seeded, role_name="manager", incoming_data={"client_id": item.client_id}
    )
    return await delete_item(ctx)


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


# ---------------------------------------------------------------------------
# C2 — remove_item_from_task
# ---------------------------------------------------------------------------


async def test_c2a_unlinking_primary_item_removes_its_active_assignment(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    captured = _capture_unlink_events(monkeypatch)

    await _remove_item_from_task(db_session, seeded, seeded.task, seeded.item)

    task_item = (
        await db_session.execute(
            select(TaskItem).where(
                TaskItem.task_id == seeded.task.client_id,
                TaskItem.item_id == seeded.item.client_id,
            )
        )
    ).scalar_one()
    assert task_item.removed_at is not None
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    task = await db_session.get(Task, seeded.task.client_id)
    assert task.is_stock_assignment is False
    names = [event.event_name for event in captured]
    assert "stock_task_assignment:deleted" in names
    assert "stock_report_item:updated" in names
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c2b_unlinking_a_related_item_does_nothing_to_the_primarys_assignment(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    related = await _second_item(db_session, seeded, "c2b", related_on_task=seeded.task)
    captured = _capture_unlink_events(monkeypatch)

    await _remove_item_from_task(db_session, seeded, seeded.task, related)

    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is False
    assert await _counters(db_session, row.client_id) == (1, 0, 0)
    assert [event.event_name for event in captured] == ["task:updated"]
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c2c_swap_then_create_on_the_new_primary_succeeds(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    replacement = await _second_item(db_session, seeded, "c2c")

    await _remove_item_from_task(db_session, seeded, seeded.task, seeded.item)

    add_ctx = make_ctx(
        db_session,
        seeded,
        role_name="manager",
        incoming_data={
            "task_id": seeded.task.client_id,
            "item_id": replacement.client_id,
            "role": "primary",
        },
    )
    await add_item_to_task(add_ctx)

    # The bite of this row is the `CR` half (plan 11 C2(c), L-28): the removal
    # assertion is deliberately *after* it, so a surviving A fails the create
    # rather than short-circuiting on C2(a)'s clause (charter rule 12).
    new_assignment_id = await _CR(db_session, seeded, row, seeded.task, replacement)
    new_assignment = await _fresh_assignment(db_session, new_assignment_id)
    assert new_assignment.is_deleted is False
    assert await _counters(db_session, row.client_id) == (1, 0, 0)
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


# ---------------------------------------------------------------------------
# C3 — delete_item
# ---------------------------------------------------------------------------


async def test_c3a_deleting_item_removes_its_active_assignment_task_untouched(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _delete_item(db_session, seeded, seeded.item)

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.is_deleted is True
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    # Read the Task back from the database, not from the identity map: a defect
    # that deleted the task with a Core statement would leave the cached instance
    # saying `False` and this row could not fail.
    task = (
        await db_session.execute(
            select(Task)
            .where(Task.client_id == seeded.task.client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert task.is_deleted is False
    assert task.state == seeded.task.state
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c3b_deleting_item_leaves_a_failed_assignment_untouched_in_counters(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.FAILED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _delete_item(db_session, seeded, seeded.item)

    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_delete_item_absent_raises_not_found(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    with pytest.raises(NotFound):
        await _delete_item(db_session, seeded, type("Item", (), {"client_id": "itm_absent"}))


async def test_c6b_repair_record_carries_the_remove_item_from_task_trigger(db_session):
    """C6(b) (§12A): drift repaired inside the PRIMARY-unlink hook is stamped
    `inline:remove_item_from_task`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :id"),
        {"id": row.client_id},
    )

    await _remove_item_from_task(db_session, seeded, seeded.task, seeded.item)

    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].trigger == "inline:remove_item_from_task"


async def test_c6c_repair_record_carries_the_delete_item_trigger(db_session):
    """C6(c) (§12A): drift repaired inside the item-deletion hook is stamped
    `inline:delete_item`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :id"),
        {"id": row.client_id},
    )

    await _delete_item(db_session, seeded, seeded.item)

    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].trigger == "inline:delete_item"
