"""`serialize_row_with_active_snapshot` — the read-back shared by every command that
answers with one `{"stock_report_item": <row>}` (the two priority routes, the
missing-quantity route, apply-priorities).

Reads the row, its category **by id** (a soft-deleted category still serializes its
name — MC-16) and the row's active snapshot, all with `populate_existing=True` so the
Core statements the callers ran are what gets serialized, never a stale identity-map
instance (plan §3.3: the `text()` statements do not synchronise the session).
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)


async def load_active_snapshot(session, workspace_id, row_id):
    return await session.scalar(
        select(StockReportItemSnapshot)
        .where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            StockReportItemSnapshot.closed_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )


async def serialize_row_with_active_snapshot(session, workspace_id, client_id) -> dict:
    row = (
        await session.execute(
            select(StockReportItem)
            .where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.client_id == client_id,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    category = await session.get(ItemCategory, row.item_category_id)
    snapshot = await load_active_snapshot(session, workspace_id, client_id)
    return serialize_stock_report_item(row, category=category, snapshot=snapshot)
