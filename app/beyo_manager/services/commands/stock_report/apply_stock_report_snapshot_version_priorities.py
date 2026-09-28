"""`apply_stock_report_snapshot_version_priorities` —
`POST /api/v1/stock-report/snapshots/versions/{client_id}/apply-priorities`.

Copies a **source** version's `priority` / `priority_order` onto a **target** version
(`merge_priority_orders`, `domain/stock_report/snapshot_rules.py`): rows present in
both take the source's priority, rows absent from the source keep theirs, and every
group is renumbered densely with the source members first. `{client_id}` is the
source; the target is the optional body's `target_version_id` — `null` or absent is
the active version, resolved **after** the advisory lock (R-3), a draft's id is that
draft (draft versions, 2026-09-28; plan §4.4). A no-body call is exactly v6.

Refusals: the target must be open (`STOCK_REPORT_TARGET_VERSION_IS_CLOSED`); the
source may be closed, active or another draft but never the target — the exact v6
case, the active source with the target omitted, keeps its published identity
`STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`, every other source = target is
`STOCK_REPORT_SOURCE_IS_TARGET` (P-8). Only priorities move: the source's manual
requested values are not copied. Target omitted and no active version → 200 with
`changed: 0`, as in v6.

One history record per changed row (`priority_change` when the priority moved, else
`priority_order_change`) **only when the target is active** — draft edits write no
history — carrying the snapshot's effective requested quantity and its source
(Q-10); one `stock_report_item_snapshot:updated` per changed snapshot; the response
serializes each changed row with the **target** version's snapshot (P-7).

Locks: advisory -> the target's open snapshots (one statement). The write is one
`UPDATE … FROM (VALUES …)` `text()` statement (plan §3.3) carrying the target's id
beside the open predicate, re-read afterwards with `populate_existing` for the
response.
"""

from __future__ import annotations

from sqlalchemy import select, text

from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
)
from beyo_manager.domain.stock_report.snapshot_rules import (
    is_version_active,
    merge_priority_orders,
    snapshot_history_quantities,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    serialize_row_with_version_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import (
    SNAPSHOT_OPEN_SQL,
    snapshot_is_open,
    version_is_active,
)
from beyo_manager.services.commands.stock_report._snapshot_missing import (
    SNAPSHOT_EVENT_RETURNING_COLUMNS,
    SNAPSHOT_EVENT_RETURNING_SQL,
)
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report._versions import find_version
from beyo_manager.services.commands.stock_report.requests import (
    parse_apply_stock_report_snapshot_version_priorities_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

SOURCE_VERSION_IS_ACTIVE_MESSAGE = (
    "STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE: the active version cannot be "
    "applied onto itself; pick a previous version."
)
SOURCE_IS_TARGET_MESSAGE = (
    "STOCK_REPORT_SOURCE_IS_TARGET: a version cannot be applied onto itself."
)
TARGET_VERSION_IS_CLOSED_MESSAGE = (
    "STOCK_REPORT_TARGET_VERSION_IS_CLOSED: priorities can only be applied onto "
    "the active version or a draft."
)


async def _resolve_target(session, workspace_id, source, target_version_id):
    """The target version (None when the active one was asked for and there is
    none), with the §4.4 refusals — after the advisory lock."""
    if target_version_id is None:
        if is_version_active(source):
            raise ValidationError(SOURCE_VERSION_IS_ACTIVE_MESSAGE)
        return await session.scalar(
            select(StockReportSnapshotVersion).where(
                StockReportSnapshotVersion.workspace_id == workspace_id,
                version_is_active(),
            )
        )
    target = await find_version(session, workspace_id, target_version_id)
    if target.closed_at is not None:
        raise ValidationError(TARGET_VERSION_IS_CLOSED_MESSAGE)
    if target.client_id == source.client_id:
        raise ValidationError(SOURCE_IS_TARGET_MESSAGE)
    return target


async def apply_stock_report_snapshot_version_priorities(ctx: ServiceContext) -> dict:
    request = parse_apply_stock_report_snapshot_version_priorities_request(
        ctx.incoming_data
    )
    events = []
    changed_row_ids: list[str] = []
    initial_snapshot_values: dict = {}
    target = None

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        source_version = await find_version(
            ctx.session, ctx.workspace_id, request.client_id
        )
        target = await _resolve_target(
            ctx.session, ctx.workspace_id, source_version, request.target_version_id
        )

        target_snapshots = []
        if target is not None:
            target_snapshots = (
                (
                    await ctx.session.execute(
                        select(StockReportItemSnapshot)
                        .where(
                            StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                            StockReportItemSnapshot.version_id == target.client_id,
                            snapshot_is_open(),
                        )
                        .order_by(StockReportItemSnapshot.client_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                )
                .scalars()
                .all()
            )
        source = (
            await ctx.session.execute(
                select(
                    StockReportItemSnapshot.client_id,
                    StockReportItemSnapshot.stock_report_item_id,
                    StockReportItemSnapshot.priority,
                    StockReportItemSnapshot.priority_order,
                ).where(
                    StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                    StockReportItemSnapshot.version_id == source_version.client_id,
                )
            )
        ).all()

        initial_snapshot_values = {
            snapshot.client_id: snapshot_values(snapshot)
            for snapshot in target_snapshots
        }
        changed = merge_priority_orders(target_snapshots, source)
        target_by_id = {snapshot.client_id: snapshot for snapshot in target_snapshots}

        if changed:
            values_sql = ", ".join(
                f"(CAST(:id_{i} AS varchar), "
                f"CAST(:p_{i} AS stock_report_priority_enum), CAST(:o_{i} AS integer))"
                for i in range(len(changed))
            )
            params: dict[str, object] = {
                "ws": ctx.workspace_id,
                "target": target.client_id,
                "actor": ctx.user_id or None,
                "now": ctx.now,
            }
            for i, (snapshot_id, (priority, order)) in enumerate(
                sorted(changed.items())
            ):
                params[f"id_{i}"] = snapshot_id
                params[f"p_{i}"] = priority.value if priority is not None else None
                params[f"o_{i}"] = order
            written = (
                (
                    await ctx.session.execute(
                        text(
                            "UPDATE stock_report_item_snapshots AS s "
                            "SET priority = v.p, priority_order = v.o, "
                            "updated_at = :now, updated_by_id = :actor "
                            f"FROM (VALUES {values_sql}) AS v(id, p, o) "
                            "WHERE s.client_id = v.id AND s.workspace_id = :ws "
                            f"AND s.version_id = :target AND {SNAPSHOT_OPEN_SQL} "
                            f"{SNAPSHOT_EVENT_RETURNING_SQL}"
                        ).columns(**SNAPSHOT_EVENT_RETURNING_COLUMNS),
                        params,
                    )
                )
                .mappings()
                .all()
            )
            if len(written) != len(changed):
                raise RuntimeError(
                    "apply-priorities wrote an unexpected number of snapshots"
                )

            row_ids = sorted({values["stock_report_item_id"] for values in written})
            rows_by_id = {
                row.client_id: row
                for row in (
                    await ctx.session.execute(
                        select(StockReportItem).where(
                            StockReportItem.workspace_id == ctx.workspace_id,
                            StockReportItem.client_id.in_(row_ids),
                        )
                    )
                )
                .scalars()
                .all()
            }
            write_history = is_version_active(target)
            for values in sorted(written, key=lambda v: v["client_id"]):
                before = target_by_id[values["client_id"]]
                row = rows_by_id[values["stock_report_item_id"]]
                new_priority = (
                    StockReportPriorityEnum(values["priority"])
                    if values["priority"] is not None
                    else None
                )
                if write_history:
                    ctx.session.add(
                        StockReportHistoryRecord(
                            workspace_id=ctx.workspace_id,
                            stock_report_item_id=row.client_id,
                            type=(
                                StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE
                                if new_priority != before.priority
                                else StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE
                            ),
                            **snapshot_history_quantities(before, row=row),
                            quantity_awaiting=row.quantity_awaiting,
                            priority=new_priority,
                            priority_order=values["priority_order"],
                            created_by_id=ctx.user_id or None,
                            created_at=ctx.now,
                        )
                    )
                events.append(
                    build_stock_report_item_snapshot_updated_event(
                        client_id=values["client_id"],
                        workspace_id=ctx.workspace_id,
                        values=values,
                    )
                )
            await ctx.session.flush()
            changed_row_ids = row_ids

        payload = [
            await serialize_row_with_version_snapshot(
                ctx.session, ctx.workspace_id, row_id, target.client_id
            )
            for row_id in changed_row_ids
        ]

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"changed": len(changed_row_ids), "stock_report_items": payload}
