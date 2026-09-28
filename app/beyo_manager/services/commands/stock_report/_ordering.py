"""Dense ordering — MC-7's shift statements (master plan §6.5, phase 12), retargeted
to the item snapshots on 2026-09-26 when priority left the row, and to **one
version's** snapshots on 2026-09-28 when drafts arrived.

A *group* is `(version_id, priority)` over **open** snapshots (`closed_at IS
NULL`), `priority ∈ {high, medium, low}`; orders are 1-based and dense. A draft's
`high` group is numbered independently of the board's. Every shift here is **one**
column-referencing `UPDATE … RETURNING`, never a read-then-assign and never an ORM
attribute write (master plan §9 rule 3): each returned row's fields feed one
`stock_report_item_snapshot:updated`.

The caller holds `pg_advisory_xact_lock(hashtext('stock_report_order:' || ws))` and
the group's `FOR UPDATE`, and has read its positions **after** those locks (MC-7
"Serialization").
"""

from __future__ import annotations

from sqlalchemy import func, select, update

from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_open

# The fields of a `stock_report_item_snapshot:updated` payload, plus the
# snapshot's own id so the caller can address each shifted neighbour.
_RETURNING_COLUMNS = (
    StockReportItemSnapshot.client_id,
    StockReportItemSnapshot.stock_report_item_id,
    StockReportItemSnapshot.version_id,
    StockReportItemSnapshot.priority,
    StockReportItemSnapshot.priority_order,
    StockReportItemSnapshot.quantity_missing,
    StockReportItemSnapshot.quantity_resolved,
    StockReportItemSnapshot.quantity_requested_scanner,
    StockReportItemSnapshot.quantity_requested_manual,
)


def _group_where(version_id, priority):
    return (
        StockReportItemSnapshot.version_id == version_id,
        StockReportItemSnapshot.priority == priority,
        snapshot_is_open(),
    )


async def _shift(session, *, version_id, priority, low, high, delta):
    """One column-referencing UPDATE over the order band `[low, high]`; `high=None`
    means "everything from `low` upwards"."""
    if high is not None and low > high:
        return []
    band = [StockReportItemSnapshot.priority_order >= low]
    if high is not None:
        band.append(StockReportItemSnapshot.priority_order <= high)
    statement = (
        update(StockReportItemSnapshot)
        .where(*_group_where(version_id, priority), *band)
        .values(priority_order=StockReportItemSnapshot.priority_order + delta)
        .returning(*_RETURNING_COLUMNS)
    )
    return [dict(row) for row in (await session.execute(statement)).mappings().all()]


async def close_priority_gap(session, *, version_id, priority, removed_order):
    """MC-7 "source closes its gap": every snapshot of the group ordered **after** the
    vacated position moves down one.

    `removed_order` is the position the leaving snapshot held. It still sits at
    `removed_order`, so the band starting at `removed_order + 1` is what keeps it out
    of the shift — that matters for the deletion cascade, where the snapshot is
    closed (or, on a draft, deleted) afterwards and keeps its own `priority_order`.
    """
    if removed_order is None:
        return []
    return await _shift(
        session,
        version_id=version_id,
        priority=priority,
        low=removed_order + 1,
        high=None,
        delta=-1,
    )


async def append_to_priority_group(session, *, version_id, priority):
    """MC-7's `max + 1` (1 when the group is empty), computed over the group as it
    stands — the mover is never a member of its destination group when this is
    called (`X == Y` is short-circuited by the caller as a no-op, B2).
    """
    current_max = await session.scalar(
        select(func.max(StockReportItemSnapshot.priority_order)).where(
            *_group_where(version_id, priority)
        )
    )
    return (current_max or 0) + 1


async def shift_within_group(session, *, version_id, priority, from_order, to_order):
    """MC-7's two in-group bands, by direction.

    `from_order` is the mover's current position `p`, `to_order` its target `t`:

    - `t < p` — the rows in `[t, p−1]` move **up** one (`+1`). `p` itself is not in
      the band: the mover is written separately by the caller.
    - `t > p` — the rows in `[p+1, t]` move **down** one (`−1`). Again `p` is
      excluded — shifting the block the mover is leaving would carry the mover with
      it.

    Returns the shifted neighbours only; the mover never appears here, and no
    `priority_order_change` record is written for a neighbour (MC-6).
    """
    if to_order == from_order:
        return []
    if to_order < from_order:
        return await _shift(
            session,
            version_id=version_id,
            priority=priority,
            low=to_order,
            high=from_order - 1,
            delta=1,
        )
    return await _shift(
        session,
        version_id=version_id,
        priority=priority,
        low=from_order + 1,
        high=to_order,
        delta=-1,
    )
