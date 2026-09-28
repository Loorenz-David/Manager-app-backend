"""`GET /api/v1/stock-report/snapshots/versions/active` — the workspace's active
version with its `progress` (`_version_progress.py`), or `null` when no version has
been created yet: that is the board's normal empty state, not a refusal
(`GET /items` is empty then too), so it is a 200.

`progress` sums, and `filtered_snapshot_count` counts, the snapshots the `priority`
query parameter selects — the same parameter, with the same meaning, as `GET /items`
(`_priority_filter.py`); the stored `snapshot_count` is never filtered. It is
parsed before any statement, so a bad value is a 422 whether or not a version exists.

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
from beyo_manager.services.commands.stock_report._predicates import version_is_active
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report._priority_filter import (
    parse_priority_filter,
)
from beyo_manager.services.queries.stock_report._version_progress import (
    load_version_progress,
)


async def get_stock_report_active_snapshot_version(ctx: ServiceContext) -> dict:
    priorities = parse_priority_filter(ctx.query_params.get("priority"))
    # The active pair, never a draft (drafts are open too, 2026-09-28).
    version = await ctx.session.scalar(
        select(StockReportSnapshotVersion).where(
            StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
            version_is_active(),
        )
    )
    if version is None:
        return {"stock_report_snapshot_version": None}
    progress = await load_version_progress(
        ctx.session, ctx.workspace_id, [version.client_id], priorities=priorities
    )
    return {
        "stock_report_snapshot_version": {
            **serialize_stock_report_snapshot_version(version),
            **progress[version.client_id],
        }
    }
