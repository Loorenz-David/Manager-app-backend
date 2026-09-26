"""`snapshot_values` — the six-key baseline of an item snapshot, the snapshot twin of
`_row_values.row_values`.

It must equal, key for key, the `extra` of a `stock_report_item_snapshot:updated`
event (`_events.build_stock_report_item_snapshot_updated_event`): the coalescer drops
a snapshot's last `:updated` when its payload equals this baseline. Same trap as the
row helper — `priority` is the enum's **`.value`**, never the member, because the
event carries the string and a member never equals a string.
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
    }
