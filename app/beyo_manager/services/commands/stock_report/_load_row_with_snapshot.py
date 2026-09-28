"""The read-back shared by every command that answers with one
`{"stock_report_item": <row>}` (the priority routes, the missing-quantity route,
the requested-quantity route, apply-priorities).

Reads the row, its category **by id** (a soft-deleted category still serializes its
name — MC-16) and the row's snapshot **in the version the command edited** — the
active one for the shortcut routes (`serialize_row_with_active_snapshot`), the
target version's for the versioned routes (`serialize_row_with_version_snapshot`,
draft versions 2026-09-28) — all with `populate_existing=True` so the Core statements
the callers ran are what gets serialized, never a stale identity-map instance (plan
§3.3: the `text()` statements do not synchronise the session).

The payload's `active_quantity_missing` is the row's **active** snapshot's number,
read as one correlated scalar subquery (the `apply_stock_demand._active_snapshot_column`
shape) so a draft's row shows the board's missing beside its own.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_active


async def load_active_snapshot(session, workspace_id, row_id):
    return await session.scalar(
        select(StockReportItemSnapshot)
        .where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            snapshot_is_active(),
        )
        .execution_options(populate_existing=True)
    )


async def load_version_snapshot(session, workspace_id, row_id, version_id):
    """The row's snapshot inside `version_id`, whatever the version's state, or
    None when the row has none there."""
    return await session.scalar(
        select(StockReportItemSnapshot)
        .where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            StockReportItemSnapshot.version_id == version_id,
        )
        .execution_options(populate_existing=True)
    )


async def load_active_quantity_missing(session, workspace_id, row_id):
    """The row's active snapshot's `quantity_missing`, or None when it has none."""
    return await session.scalar(
        select(StockReportItemSnapshot.quantity_missing).where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            snapshot_is_active(),
        )
    )


async def _load_row_and_category(session, workspace_id, client_id):
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
    return row, category


async def serialize_row_with_active_snapshot(session, workspace_id, client_id) -> dict:
    row, category = await _load_row_and_category(session, workspace_id, client_id)
    snapshot = await load_active_snapshot(session, workspace_id, client_id)
    return serialize_stock_report_item(
        row,
        category=category,
        snapshot=snapshot,
        active_quantity_missing=(
            snapshot.quantity_missing if snapshot is not None else None
        ),
    )


async def serialize_row_with_version_snapshot(
    session, workspace_id, client_id, version_id
) -> dict:
    row, category = await _load_row_and_category(session, workspace_id, client_id)
    snapshot = await load_version_snapshot(session, workspace_id, client_id, version_id)
    return serialize_stock_report_item(
        row,
        category=category,
        snapshot=snapshot,
        active_quantity_missing=await load_active_quantity_missing(
            session, workspace_id, client_id
        ),
    )
