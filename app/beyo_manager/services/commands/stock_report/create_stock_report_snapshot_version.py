"""`create_stock_report_snapshot_version` — `POST /api/v1/stock-report/snapshots/versions`.

Opens a new board version: one `stock_report_item_snapshots` row per **live**
stock-report row (zero-requested rows included — owner ruling 2026-09-26), each with
the row's current `quantity_requested` frozen into `quantity_requested_scanner`, no
manual value, its counters copied, no priority and `quantity_missing = 0`. Drafts
(2026-09-28) are never closed, locked or read here: every predicate is the
**active** pair. The previously active version, if any, is closed in the same
transaction: its open snapshots get `closed_at` and their counters **frozen from the
rows** (the "derive while active, freeze on close" ruling). Postgres enforces "one
active version per workspace" (`uix_stock_report_snapshot_versions_active`); two
concurrent creates serialize on the advisory lock, and the loser closes the winner's.

Locks, in MC-1 order: advisory -> every live row FOR UPDATE (one sorted statement —
a concurrent `move_assignment` must not slide a counter between the freeze and the
copy) -> every active snapshot. Holding all rows makes a concurrent Scanner demand
webhook wait up to its `lock_timeout` (`STOCK_DEMAND_WEBHOOK_TIMEOUT_MS`); Scanner
retries. The freeze is a `text()` `UPDATE … FROM` (plan §3.3) and the copy is one
executemany insert, both a single statement whatever the board's size.
"""

from __future__ import annotations

from sqlalchemy import DateTime, bindparam, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import (
    SNAPSHOT_ACTIVE_SQL,
    snapshot_is_active,
    version_is_active,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

_FREEZE_STATEMENT = text(
    "UPDATE stock_report_item_snapshots AS s "
    "SET closed_at = :now, "
    "quantity_in_queue = r.quantity_in_queue, "
    "quantity_in_progress = r.quantity_in_progress, "
    "quantity_awaiting = r.quantity_awaiting, "
    "updated_at = :now, updated_by_id = :actor "
    "FROM stock_report_items AS r "
    "WHERE r.client_id = s.stock_report_item_id "
    f"AND s.workspace_id = :ws AND {SNAPSHOT_ACTIVE_SQL}"
).bindparams(bindparam("now", type_=DateTime(timezone=True)))


# Two literal names, not one f-string template: the docs guard expands an
# `event_name=f"…{kind}"` site over the assignment kinds, and this event has no
# `:deleted` or `:state-changed`.
_VERSION_EVENT_NAMES = {
    "created": "stock_report_snapshot_version:created",
    "closed": "stock_report_snapshot_version:closed",
}


def _version_event(kind, version):
    return WorkspaceEvent(
        event_name=_VERSION_EVENT_NAMES[kind],
        client_id=version.client_id,
        workspace_id=version.workspace_id,
        extra={"snapshot_count": version.snapshot_count},
    )


async def create_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    events = []

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        rows = (
            (
                await ctx.session.execute(
                    select(StockReportItem)
                    .where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.is_deleted.is_(False),
                    )
                    .order_by(StockReportItem.client_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        await ctx.session.execute(
            select(StockReportItemSnapshot.client_id)
            .where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                snapshot_is_active(),
            )
            .order_by(StockReportItemSnapshot.client_id)
            .with_for_update()
        )

        previous = await ctx.session.scalar(
            select(StockReportSnapshotVersion)
            .where(
                StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
                version_is_active(),
            )
            .with_for_update()
        )
        if previous is not None:
            await ctx.session.execute(
                _FREEZE_STATEMENT,
                {"now": ctx.now, "actor": ctx.user_id or None, "ws": ctx.workspace_id},
            )
            await ctx.session.execute(
                update(StockReportSnapshotVersion)
                .where(StockReportSnapshotVersion.client_id == previous.client_id)
                .values(closed_at=ctx.now, closed_by_id=ctx.user_id or None)
            )
            await ctx.session.refresh(previous)
            events.append(_version_event("closed", previous))

        version = StockReportSnapshotVersion(
            workspace_id=ctx.workspace_id,
            active_at=ctx.now,
            created_at=ctx.now,
            created_by_id=ctx.user_id or None,
            snapshot_count=len(rows),
        )
        ctx.session.add(version)
        await ctx.session.flush()

        if rows:
            await ctx.session.execute(
                pg_insert(StockReportItemSnapshot),
                [
                    {
                        "workspace_id": ctx.workspace_id,
                        "version_id": version.client_id,
                        "stock_report_item_id": row.client_id,
                        "quantity_requested_scanner": row.quantity_requested,
                        "quantity_requested_manual": None,
                        "quantity_in_queue": row.quantity_in_queue,
                        "quantity_in_progress": row.quantity_in_progress,
                        "quantity_awaiting": row.quantity_awaiting,
                        "quantity_missing": 0,
                        "quantity_resolved": 0,
                        "priority": None,
                        "priority_order": None,
                        "active_at": ctx.now,
                        "created_at": ctx.now,
                    }
                    for row in rows
                ],
            )
        events.append(_version_event("created", version))
        payload = serialize_stock_report_snapshot_version(version)

    await dispatch(events)
    return {"stock_report_snapshot_version": payload}
