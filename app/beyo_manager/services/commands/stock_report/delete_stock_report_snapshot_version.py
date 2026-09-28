"""`delete_stock_report_snapshot_version` —
`DELETE /api/v1/stock-report/snapshots/versions/{client_id}` (plan §4.8, drafts only).

A draft is hard-deleted with its snapshots; an activated version is never deleted
(closing is its lifecycle, `states.md` §2) — 422 `STOCK_REPORT_VERSION_NOT_DRAFT`.
Nothing references a draft: history records point at rows, `quantity_resolved` is 0,
no assignment points at a snapshot, and a repair record's target id is a plain
string.

Locks: advisory -> **the version `FOR UPDATE` first** -> the draft's snapshots
`FOR UPDATE` -> its `ACTIVE` scheduler row. The version comes before its snapshots
because the demand webhook (§4.9) locks a draft's version row before inserting into it: whichever of the two
holds the version row, the other waits, and this delete then sees every snapshot
the webhook added — a snapshot inserted between a snapshot statement and the
version statement would otherwise fail the version `DELETE` on the FK. The `ACTIVE`
scheduler row of a scheduled draft is locked last and `CANCELED` (plan §5.2); the
row is kept, not deleted, as the runner's record.

`stock_report_snapshot_version:deleted` is pushed before the HTTP response returns:
the dispatch is awaited after the transaction block (FQ-7).
"""

from __future__ import annotations

from sqlalchemy import delete, select

from beyo_manager.domain.stock_report.snapshot_rules import is_version_draft
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._version_schedule import (
    cancel_activation_schedulers,
    lock_activation_schedulers,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_DRAFT_MESSAGE,
    find_version,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def delete_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)
        version = await find_version(
            ctx.session, ctx.workspace_id, client_id, for_update=True
        )
        if not is_version_draft(version):
            raise ValidationError(VERSION_NOT_DRAFT_MESSAGE)
        await ctx.session.execute(
            select(StockReportItemSnapshot.client_id)
            .where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                StockReportItemSnapshot.version_id == version.client_id,
            )
            .order_by(StockReportItemSnapshot.client_id)
            .with_for_update()
        )
        await lock_activation_schedulers(ctx.session, [version.client_id])
        await cancel_activation_schedulers(ctx.session, version.client_id, now=ctx.now)
        await ctx.session.execute(
            delete(StockReportItemSnapshot).where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                StockReportItemSnapshot.version_id == version.client_id,
            )
        )
        await ctx.session.execute(
            delete(StockReportSnapshotVersion).where(
                StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
                StockReportSnapshotVersion.client_id == version.client_id,
            )
        )
        event = WorkspaceEvent(
            event_name="stock_report_snapshot_version:deleted",
            client_id=version.client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        )

    await dispatch([event])
    return {"client_id": client_id}
