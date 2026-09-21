"""`row_values` — the six-key snapshot of a stock-report row (master plan §6.5,
ledger D-6, phase 12).

One shared helper, not a fourth copy: the shape existed three times in the tree
(`create_stock_task_assignments`, `sync_task_stock_assignments`,
`delete_stock_task_assignments`) and is load-bearing, so divergence is the failure
mode. Phase 12 creates it and those three copies are replaced by it in the same act.

**The trap, stated:** the value must match what `coalesce_stock_report_events`
compares against — the `extra` dict of a `stock_report_item:updated` event, which
carries `priority` as **`.value`, never the enum member** (`_events.py`). An enum
member compared against a string never matches, so an unchanged row would still emit
a spurious `:updated`.
"""

from __future__ import annotations


def row_values(row) -> dict:
    return {
        "quantity_requested": row.quantity_requested,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
        "priority": row.priority.value if row.priority is not None else None,
        "priority_order": row.priority_order,
    }
