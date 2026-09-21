"""Dense ordering — MC-7's shift statements (master plan §6.5, phase 12).

A *group* is `(workspace_id, priority)` over non-deleted rows, `priority ∈ {high,
medium, low}`; orders are 1-based and dense. Every shift here is **one**
column-referencing `UPDATE … RETURNING`, never a read-then-assign and never an ORM
attribute write (master plan §9 rule 3): each returned row's six event fields feed
one `stock_report_item:updated` (MC-19).

The caller holds `pg_advisory_xact_lock(hashtext('stock_report_order:' || ws))` and
the group's `FOR UPDATE`, and has read its positions **after** those locks (MC-7
"Serialization").
"""

from __future__ import annotations

from sqlalchemy import func, select, update

from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem

# The six event fields of MC-19's `stock_report_item:updated`, plus the row's own id
# so the caller can address each shifted neighbour.
_RETURNING_COLUMNS = (
    StockReportItem.client_id,
    StockReportItem.quantity_requested,
    StockReportItem.quantity_in_queue,
    StockReportItem.quantity_in_progress,
    StockReportItem.quantity_awaiting,
    StockReportItem.priority,
    StockReportItem.priority_order,
)


def _group_where(workspace_id, priority):
    return (
        StockReportItem.workspace_id == workspace_id,
        StockReportItem.priority == priority,
        StockReportItem.is_deleted.is_(False),
    )


async def _shift(session, *, workspace_id, priority, low, high, delta):
    """One column-referencing UPDATE over the order band `[low, high]`; `high=None`
    means "everything from `low` upwards"."""
    if high is not None and low > high:
        return []
    band = [StockReportItem.priority_order >= low]
    if high is not None:
        band.append(StockReportItem.priority_order <= high)
    statement = (
        update(StockReportItem)
        .where(*_group_where(workspace_id, priority), *band)
        .values(priority_order=StockReportItem.priority_order + delta)
        .returning(*_RETURNING_COLUMNS)
    )
    return [dict(row) for row in (await session.execute(statement)).mappings().all()]


async def close_priority_gap(session, *, workspace_id, priority, removed_order):
    """MC-7 "source closes its gap": every row of the group ordered **after** the
    vacated position moves down one.

    `removed_order` is the position the leaving row held. The leaving row itself
    sits at `removed_order`, so the band starting at `removed_order + 1` is what
    keeps it out of the shift — that matters for the deletion cascade (plan 13
    C1(b)), where the row is still non-deleted at this point and must keep its own
    `priority_order` afterwards.
    """
    if removed_order is None:
        return []
    return await _shift(
        session,
        workspace_id=workspace_id,
        priority=priority,
        low=removed_order + 1,
        high=None,
        delta=-1,
    )


async def append_to_priority_group(session, *, workspace_id, priority):
    """MC-7's `max + 1` (1 when the group is empty), computed over the group as it
    stands — the mover is never a member of its destination group when this is
    called (`X == Y` is short-circuited by the caller as a no-op, B2).
    """
    current_max = await session.scalar(
        select(func.max(StockReportItem.priority_order)).where(
            *_group_where(workspace_id, priority)
        )
    )
    return (current_max or 0) + 1


async def shift_within_group(session, *, workspace_id, priority, from_order, to_order):
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
            workspace_id=workspace_id,
            priority=priority,
            low=to_order,
            high=from_order - 1,
            delta=1,
        )
    return await _shift(
        session,
        workspace_id=workspace_id,
        priority=priority,
        low=from_order + 1,
        high=to_order,
        delta=-1,
    )
