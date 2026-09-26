"""`GET /api/v1/stock-report/snapshots/versions` — the workspace's board versions,
newest first, so a manager can pick the one whose order to copy.

A genuinely new list surface, so it follows `07_queries_local` in full: offset
pagination, `limit + 1` for `has_more`, the `<plural>_pagination` key on both paths.

Each row carries `progress` — the same object `GET …/versions/active` returns, from the
same engine (`_version_progress.py`): one aggregate statement for the whole page, so a
page costs two statements whatever its size (22_performance). `progress` is attached
here, not by the serializer, which stays column-only.
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

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 20  # owner ruling 2026-09-26: 20 for the history, not the contract's 50


async def list_stock_report_snapshot_versions(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(StockReportSnapshotVersion)
        .where(StockReportSnapshotVersion.workspace_id == ctx.workspace_id)
        .order_by(
            StockReportSnapshotVersion.active_at.desc(),
            StockReportSnapshotVersion.client_id.desc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    progress = await load_version_progress(
        ctx.session, ctx.workspace_id, [version.client_id for version in page]
    )

    return {
        "stock_report_snapshot_versions": [
            {
                **serialize_stock_report_snapshot_version(version),
                "progress": progress[version.client_id],
            }
            for version in page
        ],
        "stock_report_snapshot_versions_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
