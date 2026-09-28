"""`GET /api/v1/stock-report/snapshots/versions/draft-count` — the hub's Drafts
badge (G-3, owner-requested 2026-09-28): one `count(*)` over the workspace's
versions whose state is `draft` (exactly `active_at IS NULL` under
`closed_implies_activated`, through `_predicates.py`). No params, no body, no event
of its own — the frontend refetches on the version `:created` / `:activated` /
`:deleted` events. Roles: every role, as the list.
"""

from __future__ import annotations

from sqlalchemy import func, select

from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._predicates import version_is_draft
from beyo_manager.services.context import ServiceContext


async def count_stock_report_draft_versions(ctx: ServiceContext) -> dict:
    count = await ctx.session.scalar(
        select(func.count()).where(
            StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
            version_is_draft(),
        )
    )
    return {"draft_count": int(count or 0)}
