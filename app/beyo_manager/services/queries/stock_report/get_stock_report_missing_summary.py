"""`GET /api/v1/stock-report/snapshots/missing-summary` — the buyer's counter: how
many units are marked missing across the active snapshots, and on how many rows.
One aggregate statement; a computed dict, so no resource shape (46_serialization
"Exempt cases")."""

from __future__ import annotations

from sqlalchemy import case, func, select

from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_active
from beyo_manager.services.context import ServiceContext


async def get_stock_report_missing_summary(ctx: ServiceContext) -> dict:
    total, items = (
        await ctx.session.execute(
            select(
                func.coalesce(func.sum(StockReportItemSnapshot.quantity_missing), 0),
                func.coalesce(
                    func.sum(
                        case((StockReportItemSnapshot.quantity_missing > 0, 1), else_=0)
                    ),
                    0,
                ),
            ).where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                # The board only: a draft's (typed or borrowed) missing is a
                # plan, not the buyer's counter. No row join, so no effective
                # value is needed — an active snapshot's own column is its number.
                snapshot_is_active(),
            )
        )
    ).one()
    return {"quantity_missing_total": int(total), "items_with_missing": int(items)}
