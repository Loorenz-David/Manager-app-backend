"""`snapshot_values` — the eight-key baseline of an item snapshot, the snapshot twin
of `_row_values.row_values`.

It must equal, key for key, the `extra` of a `stock_report_item_snapshot:updated`
event (`_events.build_stock_report_item_snapshot_updated_event`): the coalescer drops
a snapshot's last `:updated` when its payload equals this baseline. Same trap as the
row helper — `priority` is the enum's **`.value`**, never the member, because the
event carries the string and a member never equals a string.

The two requested columns are the **stored** ones (draft versions, 2026-09-28), not
the effective value: this is built from the ORM instance without the row, and
several RETURNING statements have no row join. Every RETURNING that feeds the event
builder carries both (`_ordering._RETURNING_COLUMNS` and its siblings).
"""

from __future__ import annotations


def snapshot_values(snapshot) -> dict:
    return {
        "stock_report_item_id": snapshot.stock_report_item_id,
        "version_id": snapshot.version_id,
        "priority": snapshot.priority.value if snapshot.priority is not None else None,
        "priority_order": snapshot.priority_order,
        "quantity_missing": snapshot.quantity_missing,
        "quantity_resolved": snapshot.quantity_resolved,
        "quantity_requested_scanner": snapshot.quantity_requested_scanner,
        "quantity_requested_manual": snapshot.quantity_requested_manual,
    }
