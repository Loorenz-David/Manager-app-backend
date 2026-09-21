"""Plan 11 — MC-1 lock order for the removal hooks (master plan §9 rule 4: advisory ->
items -> tasks -> stock_report_items -> stock_task_assignments). This file verifies the
*statement order* each hook issues its `FOR UPDATE` locks in; it does not attempt to
force the two-session interleavings of C7(a)/(b) — those rows are declared unable to
force their interleaving in plan 11 §7, and the reviewer performs the structural check
instead (master plan §9 rule 9).
"""

import pytest

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.items.delete_item import delete_item
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.tasks.delete_task import delete_task
from tests.helpers.statement_listener import record_statements
from tests.helpers.stock_report import make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _make_row(db_session, seeded):
    criteria = {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _CR(db_session, seeded, row):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": seeded.task.client_id,
                    "item_id": seeded.item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    return result["stock_task_assignments"][0]["client_id"]


def _for_update_table_order(statements):
    order = []
    for statement in statements:
        if "FOR UPDATE" not in statement:
            continue
        upper = statement.upper()
        for table in ("ITEMS", "TASKS", "STOCK_REPORT_ITEMS", "STOCK_TASK_ASSIGNMENTS"):
            if f"FROM {table} " in upper or f"FROM {table}\n" in upper:
                order.append(table)
                break
    return order


async def test_delete_task_locks_rows_then_assignments_after_the_existing_task_lock(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row)
    ctx = make_ctx(
        db_session, seeded, role_name="manager", incoming_data={"client_id": seeded.task.client_id}
    )
    async with record_statements(db_session) as statements:
        await delete_task(ctx)
    order = _for_update_table_order(statements)
    assert order.index("TASKS") < order.index("STOCK_REPORT_ITEMS") < order.index(
        "STOCK_TASK_ASSIGNMENTS"
    )


async def test_delete_item_locks_item_first_then_rows_then_assignments(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row)
    ctx = make_ctx(
        db_session, seeded, role_name="manager", incoming_data={"client_id": seeded.item.client_id}
    )
    async with record_statements(db_session) as statements:
        await delete_item(ctx)
    order = _for_update_table_order(statements)
    assert order.index("ITEMS") < order.index("STOCK_REPORT_ITEMS") < order.index(
        "STOCK_TASK_ASSIGNMENTS"
    )
