"""`credit_snapshot_resolved` — the snapshot's completion memory.

Owner ruling (2026-09-26, addendum): a snapshot's `quantity_awaiting` increments when
units reach awaiting and does **not** decrement when Scanner resolves them —
`quantity_requested` is frozen, so completion is too. The row cannot tell us that
(resolution frees its awaiting counter, and an assignment carries no resolved
timestamp), so the one thing stored on the snapshot is `quantity_resolved`: the sum of
the quantities of this row's assignments that reached `resolved` / `resolved_early`
while the snapshot was active. Monotonic — terminal states are never left (MC-1) —
and never frozen or zeroed at close or on cascade. The wire `quantity_awaiting` is the
live/frozen awaiting plus this; the missing ceiling counts it as covered.

This is the single credit path, called from the two places a terminal target is
written (`resolve_processed_group`, and `move_assignment` should a caller ever move
to a terminal state directly). One ORM statement on one mapper — no cross-mapper
criteria, so `synchronize_session` evaluates it — with `RETURNING` for the event.
Zero rows (no active snapshot for the row) is a no-op. The caller holds the row lock
and the snapshot lock (`lock_stock_report_item_snapshots`, between rows and
assignments in the MC-1 order).
"""

from __future__ import annotations

from sqlalchemy import update

from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
)

_RETURNING = (
    StockReportItemSnapshot.client_id,
    StockReportItemSnapshot.stock_report_item_id,
    StockReportItemSnapshot.version_id,
    StockReportItemSnapshot.priority,
    StockReportItemSnapshot.priority_order,
    StockReportItemSnapshot.quantity_missing,
    StockReportItemSnapshot.quantity_resolved,
)


async def credit_snapshot_resolved(session, *, row_id, workspace_id, quantity, now):
    if quantity <= 0:
        return []
    result = await session.execute(
        update(StockReportItemSnapshot)
        .where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            StockReportItemSnapshot.closed_at.is_(None),
        )
        .values(
            quantity_resolved=StockReportItemSnapshot.quantity_resolved + quantity,
            updated_at=now,
        )
        .returning(*_RETURNING)
    )
    return [
        build_stock_report_item_snapshot_updated_event(
            client_id=values["client_id"], workspace_id=workspace_id, values=values
        )
        for values in result.mappings().all()
    ]
