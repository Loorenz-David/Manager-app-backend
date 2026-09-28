"""`set_stock_report_item_snapshot_missing_quantity` —
`PATCH /api/v1/stock-report/items/{client_id}/missing-quantity` (the active-version
shortcut) and `PATCH …/snapshots/versions/{version_id}/items/{client_id}/missing-quantity`
(draft versions, 2026-09-28; plan §4.6).

The manual half of `quantity_missing` (the automatic half is the creation-time clamp
in `_snapshot_missing.py`). A worker or manager marks how many of the snapshot's
still-uncovered units are missing from the inventory, or lowers that number ("there
is, search"). The value is absolute, never a delta.

Bound (owner ruling 2026-09-26): `0 <= quantity_missing <= missing_quantity_ceiling`,
the ceiling being the snapshot's **effective** requested quantity (the manual
override, else Scanner's — the live row on a draft, the frozen column once
activated) minus the row's **live** counters and the snapshot's `quantity_resolved`
(units Scanner already processed against this demand cannot be missing; 0 on a
draft).

On a **draft** the body may be `null` (O-9): a number **types** the draft's own
value, `null` **clears** it so the row borrows the active version's again. `null` on
the active version is 422 `STOCK_REPORT_VERSION_NOT_DRAFT` — an activated snapshot
always has its own number (`ck_…_missing_set_once_activated`). The same stored
value, `null` included, is a 200 no-op with no event. No history: this command never
wrote any.

Locks: row -> its target snapshot (MC-1 order; no advisory lock — no position
moves). The shortcut / versioned mapping is `_target_snapshot.py`'s.
"""

from __future__ import annotations

from sqlalchemy import update

from beyo_manager.domain.stock_report.snapshot_rules import (
    effective_quantity_requested,
    is_version_active,
    missing_quantity_ceiling,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    serialize_row_with_version_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_item_snapshots,
    lock_stock_report_items,
)
from beyo_manager.services.commands.stock_report._target_snapshot import (
    check_locked_target,
    discover_target_snapshot,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_DRAFT_MESSAGE,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_snapshot_missing_quantity_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

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


async def set_stock_report_item_snapshot_missing_quantity(ctx: ServiceContext) -> dict:
    request = parse_set_stock_report_item_snapshot_missing_quantity_request(
        ctx.incoming_data
    )
    target = request.quantity_missing
    events = []

    async with maybe_begin(ctx.session):
        locked_rows = await lock_stock_report_items(
            ctx.session, ctx.workspace_id, [request.client_id]
        )
        row = locked_rows.get(request.client_id)
        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        # Unlocked discovery, then the lock, then the decision on the locked read.
        target_snapshot = await discover_target_snapshot(
            ctx.session, ctx.workspace_id, row.client_id, request.version_id
        )
        discovered = target_snapshot.snapshot
        locked = await lock_stock_report_item_snapshots(
            ctx.session, ctx.workspace_id, [discovered.client_id]
        )
        snapshot = locked.get(discovered.client_id)
        version = await check_locked_target(
            ctx.session, ctx.workspace_id, target_snapshot, snapshot
        )

        if target is None:
            if is_version_active(version):
                raise ValidationError(VERSION_NOT_DRAFT_MESSAGE)
        else:
            requested = effective_quantity_requested(snapshot, row=row)
            ceiling = missing_quantity_ceiling(
                quantity_requested=requested,
                quantity_in_queue=row.quantity_in_queue,
                quantity_in_progress=row.quantity_in_progress,
                quantity_awaiting=row.quantity_awaiting,
                quantity_resolved=snapshot.quantity_resolved,
            )
            if target < 0 or target > ceiling:
                raise ValidationError(
                    f"STOCK_REPORT_MISSING_EXCEEDS_CEILING: {target} is outside 0..{ceiling}; "
                    f"only {ceiling} of the snapshot's {requested} "
                    "requested units are still uncovered."
                )

        if target == snapshot.quantity_missing:
            # No write, no stamp, no event (the §14B B2 rule of the priority routes).
            return {
                "stock_report_item": await serialize_row_with_version_snapshot(
                    ctx.session, ctx.workspace_id, row.client_id, version.client_id
                )
            }

        values = (
            (
                await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == snapshot.client_id,
                    )
                    .values(
                        quantity_missing=target,
                        updated_by_id=ctx.user_id or None,
                        updated_at=ctx.now,
                    )
                    .returning(*_RETURNING)
                )
            )
            .mappings()
            .one()
        )
        events.append(
            build_stock_report_item_snapshot_updated_event(
                client_id=snapshot.client_id,
                workspace_id=ctx.workspace_id,
                values=values,
            )
        )
        payload = await serialize_row_with_version_snapshot(
            ctx.session, ctx.workspace_id, row.client_id, version.client_id
        )

    await dispatch(events)
    return {"stock_report_item": payload}
