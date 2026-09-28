"""`GET /api/v1/stock-report/snapshots/versions/{client_id}` — one version, in any
state, with its `progress` and `filtered_snapshot_count` (`_version_progress.py`)
under the same `priority` parameter as the list and the active read (draft
versions, 2026-09-28; plan §6). Absent or foreign → 404. Roles: every role, as the
list (workers and sellers may read a draft — card 2).

Declared **after** `/snapshots/versions/active` and `/snapshots/versions/draft-count`
in the router: FastAPI matches the first declared route, and either literal segment
would otherwise be read as a client id (P-23).
"""

from __future__ import annotations

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report._versions import find_version
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report._priority_filter import (
    parse_priority_filter,
)
from beyo_manager.services.queries.stock_report._version_progress import (
    load_version_progress,
)


async def get_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    priorities = parse_priority_filter(ctx.query_params.get("priority"))
    version = await find_version(
        ctx.session, ctx.workspace_id, ctx.incoming_data.get("client_id")
    )
    progress = await load_version_progress(
        ctx.session, ctx.workspace_id, [version.client_id], priorities=priorities
    )
    return {
        "stock_report_snapshot_version": {
            **serialize_stock_report_snapshot_version(version),
            **progress[version.client_id],
        }
    }
