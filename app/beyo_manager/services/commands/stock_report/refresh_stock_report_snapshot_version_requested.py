"""`refresh_stock_report_snapshot_version_requested` —
`POST /api/v1/stock-report/snapshots/versions/{client_id}/refresh-requested` (draft
versions, 2026-09-28; plan §4.3, O-6). **The active version only**: a draft is live
already and a closed version is history — either is 422
`STOCK_REPORT_VERSION_NOT_ACTIVE` (v8 replaces v7's `STOCK_REPORT_VERSION_IS_CLOSED`
on this route).

Four writes, in order:

(a) re-freeze `quantity_requested_scanner` from the live rows where it differs —
    changed snapshots only, so an unchanged row gets no event;
(b) with `keep_manual_requested: false`, clear every manual override, with one
    `quantity_requested_override` history record per cleared snapshot (source
    `scanner`, the freshly frozen value) — O-7; with `true` (the default) the
    overrides are untouched and a later revert lands on the refreshed value;
(c) add a snapshot for every live row the version has none for, stamped with the
    **version's** `active_at`, not now (P-15), counters copied, resolved 0, no
    history, no per-snapshot event; `snapshot_count` follows;
(d) clamp `quantity_missing` to its effective ceiling in one bulk statement.

Events: `stock_report_item_snapshot:updated` per snapshot touched by (a), (b) or
(d), the two requested columns in `extra` (§4.10b) — a refresh that changes only the
Scanner column emits it — plus one `stock_report_snapshot_version:refreshed`
(`snapshot_count`, `changed`, `added`, `keep_manual_requested`). `changed` counts
the snapshots whose **effective** requested changed: an overridden row whose Scanner
value moved is not counted (its event still goes out). Progress can go down (R-10):
a refresh re-freezes what the version set out to do.

Locks: advisory -> every live row FOR UPDATE (sorted) -> the version's open
snapshots FOR UPDATE -> the version.
"""

from __future__ import annotations

from sqlalchemy import DateTime, bindparam, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportQuantityRequestedSourceEnum,
)
from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.domain.stock_report.snapshot_rules import is_version_active
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
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import (
    SNAPSHOT_OPEN_SQL,
    snapshot_is_open,
)
from beyo_manager.services.commands.stock_report._snapshot_missing import (
    SNAPSHOT_EVENT_RETURNING_COLUMNS,
    SNAPSHOT_EVENT_RETURNING_SQL,
    clamp_version_missing_quantities,
)
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_ACTIVE_MESSAGE,
    find_version,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_refresh_stock_report_snapshot_version_requested_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

_REFREEZE_STATEMENT = (
    text(
        "UPDATE stock_report_item_snapshots AS s "
        "SET quantity_requested_scanner = r.quantity_requested, "
        "updated_at = :now, updated_by_id = :actor "
        "FROM stock_report_items AS r "
        "WHERE r.client_id = s.stock_report_item_id "
        "AND s.workspace_id = :ws AND s.version_id = :v "
        f"AND {SNAPSHOT_OPEN_SQL} AND r.is_deleted IS FALSE "
        "AND s.quantity_requested_scanner <> r.quantity_requested "
        f"{SNAPSHOT_EVENT_RETURNING_SQL}"
    )
    .bindparams(bindparam("now", type_=DateTime(timezone=True)))
    .columns(**SNAPSHOT_EVENT_RETURNING_COLUMNS)
)

_RETURNING = (
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


async def refresh_stock_report_snapshot_version_requested(
    ctx: ServiceContext,
) -> dict:
    request = parse_refresh_stock_report_snapshot_version_requested_request(
        ctx.incoming_data
    )
    events = []
    changed = 0
    added = 0

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
        rows_by_id = {row.client_id: row for row in rows}
        snapshots = (
            (
                await ctx.session.execute(
                    select(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.version_id == request.client_id,
                        snapshot_is_open(),
                    )
                    .order_by(StockReportItemSnapshot.client_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        version = await find_version(ctx.session, ctx.workspace_id, request.client_id)
        if not is_version_active(version):
            raise ValidationError(VERSION_NOT_ACTIVE_MESSAGE)
        initial_snapshot_values = {s.client_id: snapshot_values(s) for s in snapshots}

        # (a) re-freeze where Scanner moved.
        refrozen = (
            (
                await ctx.session.execute(
                    _REFREEZE_STATEMENT,
                    {
                        "now": ctx.now,
                        "actor": ctx.user_id or None,
                        "ws": ctx.workspace_id,
                        "v": version.client_id,
                    },
                )
            )
            .mappings()
            .all()
        )
        for values in refrozen:
            if values["quantity_requested_manual"] is None:
                changed += 1
            events.append(
                build_stock_report_item_snapshot_updated_event(
                    client_id=values["client_id"],
                    workspace_id=ctx.workspace_id,
                    values=values,
                )
            )

        # (b) the overrides.
        if not request.keep_manual_requested:
            cleared = (
                (
                    await ctx.session.execute(
                        update(StockReportItemSnapshot)
                        .where(
                            StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                            StockReportItemSnapshot.version_id == version.client_id,
                            snapshot_is_open(),
                            StockReportItemSnapshot.quantity_requested_manual.is_not(
                                None
                            ),
                        )
                        .values(
                            quantity_requested_manual=None,
                            updated_by_id=ctx.user_id or None,
                            updated_at=ctx.now,
                        )
                        .returning(*_RETURNING)
                        .execution_options(synchronize_session=False)
                    )
                )
                .mappings()
                .all()
            )
            for values in sorted(cleared, key=lambda v: v["client_id"]):
                before = initial_snapshot_values[values["client_id"]]
                if (
                    before["quantity_requested_manual"]
                    != values["quantity_requested_scanner"]
                ):
                    changed += 1
                row = rows_by_id.get(values["stock_report_item_id"])
                ctx.session.add(
                    StockReportHistoryRecord(
                        workspace_id=ctx.workspace_id,
                        stock_report_item_id=values["stock_report_item_id"],
                        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE,
                        quantity_requested=values["quantity_requested_scanner"],
                        quantity_requested_source=(
                            StockReportQuantityRequestedSourceEnum.SCANNER
                        ),
                        quantity_awaiting=(
                            row.quantity_awaiting if row is not None else 0
                        ),
                        priority=values["priority"],
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

        # (c) rows created since the version went live join it, frozen now.
        held = set(
            (
                await ctx.session.scalars(
                    select(StockReportItemSnapshot.stock_report_item_id).where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.version_id == version.client_id,
                    )
                )
            ).all()
        )
        new_rows = [row for row in rows if row.client_id not in held]
        if new_rows:
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
                        "active_at": version.active_at,
                        "created_at": ctx.now,
                    }
                    for row in new_rows
                ],
            )
            added = len(new_rows)
            await ctx.session.execute(
                update(StockReportSnapshotVersion)
                .where(StockReportSnapshotVersion.client_id == version.client_id)
                .values(
                    snapshot_count=(
                        select(func.count())
                        .select_from(StockReportItemSnapshot)
                        .where(StockReportItemSnapshot.version_id == version.client_id)
                        .scalar_subquery()
                    )
                )
                .execution_options(synchronize_session=False)
            )

        # (d) the missing ceiling moved with the requested quantities.
        events.extend(
            await clamp_version_missing_quantities(
                ctx.session,
                version_id=version.client_id,
                workspace_id=ctx.workspace_id,
                actor_user_id=ctx.user_id,
                now=ctx.now,
            )
        )

        version = await find_version(ctx.session, ctx.workspace_id, version.client_id)
        payload = serialize_stock_report_snapshot_version(version)
        events.append(
            WorkspaceEvent(
                event_name="stock_report_snapshot_version:refreshed",
                client_id=version.client_id,
                workspace_id=ctx.workspace_id,
                extra={
                    "snapshot_count": version.snapshot_count,
                    "changed": changed,
                    "added": added,
                    "keep_manual_requested": request.keep_manual_requested,
                },
            )
        )

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {
        "stock_report_snapshot_version": payload,
        "changed": changed,
        "added": added,
    }
