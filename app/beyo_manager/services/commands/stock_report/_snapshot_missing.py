"""`clamp_snapshot_missing_quantity` — the automatic half of `quantity_missing`.

The invariant (owner ruling 2026-09-26): on an **active** snapshot,
`quantity_missing <= max(0, effective requested − (row.in_queue + row.in_progress
+ row.awaiting + snapshot.quantity_resolved))` — `missing_quantity_ceiling` in
`domain/stock_report/snapshot_rules.py`, the requested value being the effective one
(`_predicates.EFFECTIVE_QUANTITY_REQUESTED_SQL`: the manual override, else the
frozen Scanner column). Only one move raises the covered quantity — an assignment's
**creation** — so `move_assignment` calls this once, after its counter statement,
when `is_creation`. Someone marked the units missing; a manager then found one and
assigned it directly: the missing count falls to what is still uncovered.

Drafts are never clamped here (a draft's missing is a guide, settled and clamped at
activation); the predicate is the active pair.

One guarded statement: it touches the snapshot only when the invariant is violated,
so a no-op costs no write and no event. Written as `text()` — an ORM `update()` whose
criteria name another mapper's columns cannot be evaluated in Python and would fall
back to `synchronize_session="fetch"` silently (plan §3.3). The caller holds the row
lock and the snapshot lock (`lock_stock_report_item_snapshots`).
"""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, bindparam, text

from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
)
from beyo_manager.services.commands.stock_report._predicates import (
    EFFECTIVE_QUANTITY_REQUESTED_SQL,
    SNAPSHOT_ACTIVE_SQL,
)

_CEILING_SQL = (
    f"GREATEST(0, {EFFECTIVE_QUANTITY_REQUESTED_SQL} - "
    "(r.quantity_in_queue + r.quantity_in_progress + r.quantity_awaiting "
    "+ s.quantity_resolved))"
)

# Every RETURNING that feeds the event builder carries the event's eight keys.
SNAPSHOT_EVENT_RETURNING_SQL = (
    "RETURNING s.client_id AS client_id, "
    "s.stock_report_item_id AS stock_report_item_id, "
    "s.version_id AS version_id, s.priority AS priority, "
    "s.priority_order AS priority_order, s.quantity_missing AS quantity_missing, "
    "s.quantity_resolved AS quantity_resolved, "
    "s.quantity_requested_scanner AS quantity_requested_scanner, "
    "s.quantity_requested_manual AS quantity_requested_manual"
)
SNAPSHOT_EVENT_RETURNING_COLUMNS = dict(
    client_id=String,
    stock_report_item_id=String,
    version_id=String,
    priority=String,
    priority_order=Integer,
    quantity_missing=Integer,
    quantity_resolved=Integer,
    quantity_requested_scanner=Integer,
    quantity_requested_manual=Integer,
)

_CLAMP_STATEMENT = (
    text(
        "UPDATE stock_report_item_snapshots AS s "
        f"SET quantity_missing = {_CEILING_SQL}, "
        "updated_at = :now, updated_by_id = :actor "
        "FROM stock_report_items AS r "
        "WHERE r.client_id = s.stock_report_item_id "
        "AND s.workspace_id = :ws AND s.stock_report_item_id = :row_id "
        f"AND {SNAPSHOT_ACTIVE_SQL} "
        f"AND s.quantity_missing > {_CEILING_SQL} "
        f"{SNAPSHOT_EVENT_RETURNING_SQL}"
    )
    .bindparams(bindparam("now", type_=DateTime(timezone=True)))
    .columns(**SNAPSHOT_EVENT_RETURNING_COLUMNS)
)


async def clamp_snapshot_missing_quantity(
    session, *, row_id, workspace_id, actor_user_id, now
):
    result = await session.execute(
        _CLAMP_STATEMENT,
        {
            "now": now,
            "actor": actor_user_id or None,
            "ws": workspace_id,
            "row_id": row_id,
        },
    )
    return [
        build_stock_report_item_snapshot_updated_event(
            client_id=values["client_id"], workspace_id=workspace_id, values=values
        )
        for values in result.mappings().all()
    ]
