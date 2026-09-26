"""`set_stock_report_item_priority_order` — MC-7's in-group move (master plan §6.5,
phase 12; intention §7A before/after rows 1–5, §6A MC-6, §14B B2, MC-17, MC-19),
retargeted on 2026-09-26 to the row's **active item snapshot** — see the sibling
`set_stock_report_item_priority.py` for the shared boundary and lock shape.
"""

from __future__ import annotations

from sqlalchemy import update

from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    load_active_snapshot,
    serialize_row_with_active_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._ordering import shift_within_group
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_priority_order_request,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    NO_ACTIVE_SNAPSHOT_MESSAGE,
    find_row,
    lock_snapshot_and_groups,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

_MOVER_RETURNING = (
    StockReportItemSnapshot.client_id,
    StockReportItemSnapshot.stock_report_item_id,
    StockReportItemSnapshot.version_id,
    StockReportItemSnapshot.priority,
    StockReportItemSnapshot.priority_order,
    StockReportItemSnapshot.quantity_missing,
    StockReportItemSnapshot.quantity_resolved,
)


async def set_stock_report_item_priority_order(ctx: ServiceContext) -> dict:
    request = parse_set_stock_report_item_priority_order_request(ctx.incoming_data)
    target = request.priority_order

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        row = await find_row(ctx.session, ctx.workspace_id, request.client_id)
        discovered = await load_active_snapshot(
            ctx.session, ctx.workspace_id, row.client_id
        )
        if discovered is None:
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)
        locked = await lock_snapshot_and_groups(
            ctx.session, ctx.workspace_id, discovered.client_id, (discovered.priority,)
        )
        snapshot = locked.get(discovered.client_id)
        if snapshot is None or snapshot.closed_at is not None:
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)

        priority = snapshot.priority
        if priority is None:
            raise ValidationError(
                "STOCK_REPORT_ROW_HAS_NO_PRIORITY: this stock report item has no "
                "priority, so it has no position to move within."
            )

        # `n` is the group size read **after** the locks (MC-7).
        n = sum(
            1 for candidate in locked.values() if candidate.priority == priority
        )
        if not 1 <= target <= n:
            raise ValidationError(
                f"STOCK_REPORT_TARGET_OUT_OF_RANGE: {target} is outside 1..{n} for "
                f"priority group '{priority.value}'."
            )

        position = snapshot.priority_order
        initial_snapshot_values = {
            client_id: snapshot_values(candidate)
            for client_id, candidate in locked.items()
        }

        if target == position:
            # §14B B2: no write, no record, no stamp, no event.
            return {
                "stock_report_item": await serialize_row_with_active_snapshot(
                    ctx.session, ctx.workspace_id, row.client_id
                )
            }

        shifted = await shift_within_group(
            ctx.session,
            workspace_id=ctx.workspace_id,
            priority=priority,
            from_order=position,
            to_order=target,
        )

        mover = (
            (
                await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == snapshot.client_id,
                    )
                    .values(
                        priority_order=target,
                        updated_by_id=ctx.user_id or None,
                        updated_at=ctx.now,
                    )
                    .returning(*_MOVER_RETURNING)
                )
            )
            .mappings()
            .one()
        )

        # MC-6: one record for the moved row only — shifted neighbours get none —
        # inserted after all mutations.
        ctx.session.add(
            StockReportHistoryRecord(
                workspace_id=ctx.workspace_id,
                stock_report_item_id=row.client_id,
                type=StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE,
                quantity_requested=row.quantity_requested,
                quantity_awaiting=row.quantity_awaiting,
                priority=mover["priority"],
                priority_order=mover["priority_order"],
                created_by_id=ctx.user_id or None,
                created_at=ctx.now,
            )
        )
        await ctx.session.flush()

        events = [
            build_stock_report_item_snapshot_updated_event(
                client_id=snapshot.client_id,
                workspace_id=ctx.workspace_id,
                values=mover,
            )
        ]
        events.extend(
            build_stock_report_item_snapshot_updated_event(
                client_id=neighbour["client_id"],
                workspace_id=ctx.workspace_id,
                values=neighbour,
            )
            for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
        )
        payload = await serialize_row_with_active_snapshot(
            ctx.session, ctx.workspace_id, row.client_id
        )

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"stock_report_item": payload}
