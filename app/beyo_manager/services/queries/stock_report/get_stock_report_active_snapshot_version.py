"""`GET /api/v1/stock-report/snapshots/versions/active` — the workspace's active
version with its `progress` (`_version_progress.py`), or `null` when no version has
been created yet: that is the board's normal empty state, not a refusal
(`GET /items` is empty then too), so it is a 200.

Two statements: the version (at most one — `uix_stock_report_snapshot_versions_active`),
then its progress.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report._version_progress import (
    load_version_progress,
)


async def get_stock_report_active_snapshot_version(ctx: ServiceContext) -> dict:
    version = await ctx.session.scalar(
        select(StockReportSnapshotVersion).where(
            StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
            StockReportSnapshotVersion.closed_at.is_(None),
        )
    )
    if version is None:
        return {"stock_report_snapshot_version": None}
    progress = await load_version_progress(
        ctx.session, ctx.workspace_id, [version.client_id]
    )
    return {
        "stock_report_snapshot_version": {
            **serialize_stock_report_snapshot_version(version),
            "progress": progress[version.client_id],
        }
    }
