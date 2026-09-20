from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from tests.helpers.stock_report import assert_stock_report_clean, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
PROPERTIES = {"wood_type": "Teak", "upholstery": "Down"}


async def _make_row(db_session, seeded, *, counters=None):
    counters = counters or {}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=PROPERTIES,
        properties_signature=compute_stock_criteria_signature(PROPERTIES),
        quantity_requested=10,
        quantity_in_queue=counters.get("quantity_in_queue", 0),
        quantity_in_progress=counters.get("quantity_in_progress", 0),
        quantity_awaiting=counters.get("quantity_awaiting", 0),
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _make_assignment(db_session, seeded, row, *, item=None, quantity=4, state):
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=(item or seeded.item).client_id,
        quantity=quantity,
        state=state,
    )
    db_session.add(assignment)
    await db_session.flush()
    return assignment


async def _seed_flag(db_session, task, value):
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = :v WHERE client_id = :t"),
        {"v": value, "t": task.client_id},
    )


async def _task_flag(db_session, task_id):
    return await db_session.scalar(
        select(Task.is_stock_assignment).where(Task.client_id == task_id)
    )


async def _repair_records(db_session, workspace_id):
    return (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )


async def _counters(db_session, row_id):
    row = (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()
    return tuple(row)


# ---------------------------------------------------------------------------
# C6 — the MC-15 task-flag recompute
# ---------------------------------------------------------------------------


async def test_c6_a_removing_the_only_assignment_clears_the_flag(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await remove_assignment(
        db_session,
        assignment,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _task_flag(db_session, seeded.task.client_id) is False
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6_b_flag_stays_true_while_a_second_assignment_remains(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    second_item_category = seeded.categories[1]
    from beyo_manager.domain.items.enums import ItemStateEnum
    from beyo_manager.models.tables.items.item import Item

    item2 = Item(
        client_id=f"itm_c6b_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"c6b-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=1,
        item_category_id=second_item_category.client_id,
    )
    db_session.add(item2)
    await db_session.flush()
    await _seed_flag(db_session, seeded.task, True)
    assignment_a = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _make_assignment(
        db_session, seeded, row, item=item2, quantity=1, state=S.RESOLVED
    )
    await remove_assignment(
        db_session,
        assignment_a,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _task_flag(db_session, seeded.task.client_id) is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6_c_flag_flip_never_stamps_task_updated_columns(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    t_seed = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await db_session.execute(
        text(
            "UPDATE tasks SET updated_at = :t, updated_by_id = :u WHERE client_id = :task_id"
        ),
        {"t": t_seed, "u": seeded.worker.client_id, "task_id": seeded.task.client_id},
    )
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await remove_assignment(
        db_session,
        assignment,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    fresh_task = (
        await db_session.execute(
            select(Task.updated_at, Task.updated_by_id).where(
                Task.client_id == seeded.task.client_id
            )
        )
    ).one()
    assert fresh_task.updated_at == t_seed
    assert fresh_task.updated_by_id == seeded.worker.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


# ---------------------------------------------------------------------------
# C5(c) — inline repair instrument (b): DELETE write order
# ---------------------------------------------------------------------------


async def test_c5_c_delete_write_order_self_heals_with_one_repair_record(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :r"),
        {"r": row.client_id},
    )
    await remove_assignment(
        db_session,
        assignment,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    assert records[0].field == "quantity_in_queue"
    assert records[0].stored_value == "0"
    assert records[0].recomputed_value == "0"
    assert records[0].trigger == "inline:delete_assignments"
    from beyo_manager.services.queries.stock_report.consistency import (
        compute_stock_report_divergences,
    )

    assert await compute_stock_report_divergences(db_session, seeded.workspace.client_id) == []
