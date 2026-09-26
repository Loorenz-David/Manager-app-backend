"""`apply_stock_report_snapshot_version_priorities` —
`POST /api/v1/stock-report/snapshots/versions/{client_id}/apply-priorities`.

Copies a **closed** version's `priority` / `priority_order` onto the active version
(`merge_priority_orders`, `domain/stock_report/snapshot_rules.py`): rows present in
both take the source's priority, rows absent from the source keep theirs, and every
group is renumbered densely with the source members first. One history record per
changed row (`priority_change` when the priority moved, else `priority_order_change`),
one `stock_report_item_snapshot:updated` per changed snapshot.

Locks: advisory -> every active snapshot (one statement). The write is one
`UPDATE … FROM (VALUES …)` `text()` statement (plan §3.3), re-read afterwards with
`populate_existing` for the response.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, select, text

from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
)
from beyo_manager.domain.stock_report.snapshot_rules import merge_priority_orders
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    serialize_row_with_active_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch


async def apply_stock_report_snapshot_version_priorities(ctx: ServiceContext) -> dict:
    source_version_id = ctx.incoming_data.get("client_id")
    events = []
    changed_row_ids: list[str] = []

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        source_version = await ctx.session.scalar(
            select(StockReportSnapshotVersion).where(
                StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
                StockReportSnapshotVersion.client_id == source_version_id,
            )
        )
        if source_version is None:
            raise NotFound("Stock report snapshot version not found.")
        if source_version.closed_at is None:
            raise ValidationError(
                "STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE: the active version cannot be "
                "applied onto itself; pick a previous version."
            )

        active = (
            (
                await ctx.session.execute(
                    select(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.closed_at.is_(None),
                    )
                    .order_by(StockReportItemSnapshot.client_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        source = (
            await ctx.session.execute(
                select(
                    StockReportItemSnapshot.client_id,
                    StockReportItemSnapshot.stock_report_item_id,
                    StockReportItemSnapshot.priority,
                    StockReportItemSnapshot.priority_order,
                ).where(
                    StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                    StockReportItemSnapshot.version_id == source_version.client_id,
                )
            )
        ).all()

        initial_snapshot_values = {
            snapshot.client_id: snapshot_values(snapshot) for snapshot in active
        }
        changed = merge_priority_orders(active, source)
        active_by_id = {snapshot.client_id: snapshot for snapshot in active}

        if changed:
            values_sql = ", ".join(
                f"(CAST(:id_{i} AS varchar), "
                f"CAST(:p_{i} AS stock_report_priority_enum), CAST(:o_{i} AS integer))"
                for i in range(len(changed))
            )
            params: dict[str, object] = {
                "ws": ctx.workspace_id,
                "actor": ctx.user_id or None,
                "now": ctx.now,
            }
            for i, (snapshot_id, (priority, order)) in enumerate(
                sorted(changed.items())
            ):
                params[f"id_{i}"] = snapshot_id
                params[f"p_{i}"] = priority.value if priority is not None else None
                params[f"o_{i}"] = order
            written = (
                (
                    await ctx.session.execute(
                        text(
                            "UPDATE stock_report_item_snapshots AS s "
                            "SET priority = v.p, priority_order = v.o, "
                            "updated_at = :now, updated_by_id = :actor "
                            f"FROM (VALUES {values_sql}) AS v(id, p, o) "
                            "WHERE s.client_id = v.id AND s.workspace_id = :ws "
                            "AND s.closed_at IS NULL "
                            "RETURNING s.client_id AS client_id, "
                            "s.stock_report_item_id AS stock_report_item_id, "
                            "s.version_id AS version_id, s.priority AS priority, "
                            "s.priority_order AS priority_order, "
                            "s.quantity_missing AS quantity_missing, "
                            "s.quantity_resolved AS quantity_resolved"
                        ).columns(
                            client_id=String,
                            stock_report_item_id=String,
                            version_id=String,
                            priority=String,
                            priority_order=Integer,
                            quantity_missing=Integer,
                            quantity_resolved=Integer,
                        ),
                        params,
                    )
                )
                .mappings()
                .all()
            )
            if len(written) != len(changed):
                raise RuntimeError(
                    "apply-priorities wrote an unexpected number of snapshots"
                )

            row_ids = sorted({values["stock_report_item_id"] for values in written})
            rows_by_id = {
                row.client_id: row
                for row in (
                    await ctx.session.execute(
                        select(StockReportItem).where(
                            StockReportItem.workspace_id == ctx.workspace_id,
                            StockReportItem.client_id.in_(row_ids),
                        )
                    )
                )
                .scalars()
                .all()
            }
            for values in sorted(written, key=lambda v: v["client_id"]):
                before = active_by_id[values["client_id"]]
                row = rows_by_id[values["stock_report_item_id"]]
                new_priority = (
                    StockReportPriorityEnum(values["priority"])
                    if values["priority"] is not None
                    else None
                )
                ctx.session.add(
                    StockReportHistoryRecord(
                        workspace_id=ctx.workspace_id,
                        stock_report_item_id=row.client_id,
                        type=(
                            StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE
                            if new_priority != before.priority
                            else StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE
                        ),
                        quantity_requested=row.quantity_requested,
                        quantity_awaiting=row.quantity_awaiting,
                        priority=new_priority,
                        priority_order=values["priority_order"],
                        created_by_id=ctx.user_id or None,
                        created_at=ctx.now,
                    )
                )
                events.append(
                    build_stock_report_item_snapshot_updated_event(
                        client_id=values["client_id"],
                        workspace_id=ctx.workspace_id,
                        values=values,
                    )
                )
            await ctx.session.flush()
            changed_row_ids = row_ids

        payload = [
            await serialize_row_with_active_snapshot(
                ctx.session, ctx.workspace_id, row_id
            )
            for row_id in changed_row_ids
        ]

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"changed": len(changed_row_ids), "stock_report_items": payload}
