"""`row_values` — the four-key quantity snapshot of a stock-report row (master plan
§6.5, ledger D-6, phase 12; shrunk from six keys on 2026-09-26 when `priority` and
`priority_order` moved to the item snapshot — see `_snapshot_values.py`).

One shared helper, not a fourth copy: the shape existed three times in the tree
(`create_stock_task_assignments`, `sync_task_stock_assignments`,
`delete_stock_task_assignments`) and is load-bearing, so divergence is the failure
mode.

**The trap, stated:** the value must match what `coalesce_stock_report_events`
compares against — the `extra` dict of a `stock_report_item:updated` event
(`_events.py`). A key here that the event does not carry, or the reverse, makes an
unchanged row emit a spurious `:updated`.
"""

from __future__ import annotations


def row_values(row) -> dict:
    return {
        "quantity_requested": row.quantity_requested,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
    }
