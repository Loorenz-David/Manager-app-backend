"""`create_stock_report_snapshot_version` — `POST /api/v1/stock-report/snapshots/versions`.

Opens a new board version, or (draft versions, 2026-09-28; plan §4.1) a **draft**.
The body is optional: a no-body call is exactly the v6 create.

`draft: false` — one `stock_report_item_snapshots` row per **live** stock-report row
(zero-requested rows included — owner ruling 2026-09-26), each with the row's
current `quantity_requested` frozen into `quantity_requested_scanner`, no manual
value, its counters copied, no priority and `quantity_missing = 0` (the closing
board's missing is never carried on a direct create — FQ-14). The previously active
version, if any, is closed in the same transaction: its open snapshots get
`closed_at` and their counters **frozen from the rows** (the "derive while active,
freeze on close" ruling). Drafts are never closed, locked or read on this path:
every predicate is the **active** pair. Postgres enforces "one active version per
workspace" (`uix_stock_report_snapshot_versions_active`); two concurrent creates
serialize on the advisory lock, and the loser closes the winner's.

`draft: true` — the same row lock and one snapshot per live row, but a draft is
**live**: both requested columns NULL (the read shows the row's value until
activation freezes it), `quantity_missing` NULL (borrowed from the active version
until typed — O-9), `active_at` NULL on the version and its snapshots, and the
active version untouched. `scheduled_activation_at` (aware, normalised to UTC by the
request model, strictly after `ctx.now`) and the stored missing flag are written on
the draft; the delayed-scheduler row that fires it is plan §5.2. A schedule (a date,
or the flag `true`) with `draft: false` is refused; the documented default body is
not (R-9).

Locks, in MC-1 order: advisory -> every live row FOR UPDATE (one sorted statement —
a concurrent `move_assignment` must not slide a counter between the freeze and the
copy) -> every active snapshot (the active path only). Holding all rows makes a
concurrent Scanner demand webhook wait up to its `lock_timeout`
(`STOCK_DEMAND_WEBHOOK_TIMEOUT_MS`); Scanner retries. The freeze is a `text()`
`UPDATE … FROM` (plan §3.3) and the copy is one executemany insert, both a single
statement whatever the board's size.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.domain.stock_report.snapshot_rules import version_state
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_active
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_DRAFT_MESSAGE,
    close_active_version,
    closed_version_event,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_create_stock_report_snapshot_version_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

SCHEDULE_IN_THE_PAST_MESSAGE = (
    "STOCK_REPORT_SCHEDULE_IN_THE_PAST: scheduled_activation_at must be after now."
)


def _created_event(version):
    # `state` and `title` (v7 §7.1): a client branches on `extra.state` to
    # refetch the board only for an active create.
    return WorkspaceEvent(
        event_name="stock_report_snapshot_version:created",
        client_id=version.client_id,
        workspace_id=version.workspace_id,
        extra={
            "snapshot_count": version.snapshot_count,
            "state": version_state(version).value,
            "title": version.title,
        },
    )


def validate_schedule(scheduled_activation_at, *, now):
    """`scheduled_activation_at` must lie strictly after the request's clock
    (P-13); shared with the PATCH-version command."""
    if scheduled_activation_at is not None and scheduled_activation_at <= now:
        raise ValidationError(SCHEDULE_IN_THE_PAST_MESSAGE)


def draft_snapshot_values(*, workspace_id, version_id, row, now) -> dict:
    """One draft snapshot of `row` (plan §4.1, §4.9, §4.12 — the create command,
    the demand webhook and the membership repair insert the same shape): no
    requested value, no missing, no priority, counters copied, `active_at` NULL."""
    return {
        "workspace_id": workspace_id,
        "version_id": version_id,
        "stock_report_item_id": row.client_id,
        "quantity_requested_scanner": None,
        "quantity_requested_manual": None,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
        "quantity_missing": None,
        "quantity_resolved": 0,
        "priority": None,
        "priority_order": None,
        "active_at": None,
        "created_at": now,
    }


async def create_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    request = parse_create_stock_report_snapshot_version_request(ctx.incoming_data)
    if not request.draft and request.schedule_requested:
        raise ValidationError(VERSION_NOT_DRAFT_MESSAGE)
    validate_schedule(request.scheduled_activation_at, now=ctx.now)
    events = []

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        rows = (
            (
                await ctx.session.execute(
                    select(StockReportItem)
                    .where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.is_deleted.is_(False),
                    )
                    .order_by(StockReportItem.client_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )

        if request.draft:
            version = StockReportSnapshotVersion(
                workspace_id=ctx.workspace_id,
                title=request.title,
                active_at=None,
                scheduled_activation_at=request.scheduled_activation_at,
                scheduled_activation_keeps_active_missing=(
                    request.scheduled_activation_keeps_active_missing
                ),
                created_at=ctx.now,
                created_by_id=ctx.user_id or None,
                snapshot_count=len(rows),
            )
            ctx.session.add(version)
            await ctx.session.flush()
            if rows:
                await ctx.session.execute(
                    pg_insert(StockReportItemSnapshot),
                    [
                        draft_snapshot_values(
                            workspace_id=ctx.workspace_id,
                            version_id=version.client_id,
                            row=row,
                            now=ctx.now,
                        )
                        for row in rows
                    ],
                )
            events.append(_created_event(version))
            payload = serialize_stock_report_snapshot_version(version)
        else:
            await ctx.session.execute(
                select(StockReportItemSnapshot.client_id)
                .where(
                    StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                    snapshot_is_active(),
                )
                .order_by(StockReportItemSnapshot.client_id)
                .with_for_update()
            )

            previous = await close_active_version(
                ctx.session,
                workspace_id=ctx.workspace_id,
                now=ctx.now,
                actor_user_id=ctx.user_id,
            )
            if previous is not None:
                events.append(closed_version_event(previous))

            version = StockReportSnapshotVersion(
                workspace_id=ctx.workspace_id,
                title=request.title,
                active_at=ctx.now,
                created_at=ctx.now,
                created_by_id=ctx.user_id or None,
                snapshot_count=len(rows),
            )
            ctx.session.add(version)
            await ctx.session.flush()

            if rows:
                await ctx.session.execute(
                    pg_insert(StockReportItemSnapshot),
                    [
                        {
                            "workspace_id": ctx.workspace_id,
                            "version_id": version.client_id,
                            "stock_report_item_id": row.client_id,
                            "quantity_requested_scanner": row.quantity_requested,
                            "quantity_requested_manual": None,
                            "quantity_in_queue": row.quantity_in_queue,
                            "quantity_in_progress": row.quantity_in_progress,
                            "quantity_awaiting": row.quantity_awaiting,
                            "quantity_missing": 0,
                            "quantity_resolved": 0,
                            "priority": None,
                            "priority_order": None,
                            "active_at": ctx.now,
                            "created_at": ctx.now,
                        }
                        for row in rows
                    ],
                )
            events.append(_created_event(version))
            payload = serialize_stock_report_snapshot_version(version)

    await dispatch(events)
    return {"stock_report_snapshot_version": payload}
