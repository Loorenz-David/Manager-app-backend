"""`GET /api/v1/stock-report/snapshots/versions` — the workspace's board versions:
drafts first (newest created first), then the active and the closed ones by
`active_at` newest first, so a manager can pick the one whose order to copy or the
draft to prepare. The exact key is `active_at DESC NULLS FIRST, created_at DESC,
client_id DESC` (draft versions, 2026-09-28; plan §6).

`state` (G-2) is a comma list of `draft|active|closed` parsed by
`_version_state_filter.py`; omitted → every state (the folder model shows every
card). `priority` selects what `progress` sums, as on `GET /items`; the version
rows themselves are never filtered by it.

A genuinely new list surface, so it follows `07_queries_local` in full: offset
pagination, `limit + 1` for `has_more`, the `<plural>_pagination` key on both paths.

Each row carries `progress` and `filtered_snapshot_count` — the same keys
`GET …/versions/active` returns, from the same engine (`_version_progress.py`): one
aggregate statement for the whole page, so a page costs two statements whatever its
size (22_performance). `progress` is attached here, not by the serializer, which
stays column-only. A draft's progress is live: its rows' live counters against the
live requested (or the override) and the effective missing.
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
from beyo_manager.services.queries.stock_report._priority_filter import (
    parse_priority_filter,
)
from beyo_manager.services.queries.stock_report._version_progress import (
    load_version_progress,
)
from beyo_manager.services.queries.stock_report._version_state_filter import (
    parse_version_state_filter,
    version_state_predicate,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 20  # owner ruling 2026-09-26: 20 for the history, not the contract's 50


async def list_stock_report_snapshot_versions(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    priorities = parse_priority_filter(ctx.query_params.get("priority"))
    states = parse_version_state_filter(ctx.query_params.get("state"))

    statement = select(StockReportSnapshotVersion).where(
        StockReportSnapshotVersion.workspace_id == ctx.workspace_id
    )
    state_predicate = version_state_predicate(states)
    if state_predicate is not None:
        statement = statement.where(state_predicate)
    result = await ctx.session.execute(
        statement.order_by(
            StockReportSnapshotVersion.active_at.desc().nulls_first(),
            StockReportSnapshotVersion.created_at.desc(),
            StockReportSnapshotVersion.client_id.desc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    progress = await load_version_progress(
        ctx.session,
        ctx.workspace_id,
        [version.client_id for version in page],
        priorities=priorities,
    )

    return {
        "stock_report_snapshot_versions": [
            {
                **serialize_stock_report_snapshot_version(version),
                **progress[version.client_id],
            }
            for version in page
        ],
        "stock_report_snapshot_versions_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
