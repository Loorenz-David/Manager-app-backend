"""`apply_stock_demand` — the D6 statement plan (intention §8B D6; master plan §6.5).

One owner-mode transaction: `set_config` (MC-9), the workspace check (MC-8 step 4),
category resolution, unlocked identity discovery, an absent-identities-only insert
(MC-4, C42), a sorted lock **by identity** (H17 — never by the client_ids step 4/5
happened to see, because a concurrent insert can win the identity between them),
a bulk update of changed rows, a bulk goal-record insert for increases, and the
MC-9 part-1 deadline check as the last action before the block exits.

`time` is imported as the module and referenced as `time.monotonic()` so a test can
replace the name `apply_stock_demand.time` with a `SimpleNamespace` (H19/B6) without
touching the shared `time` module (which would also freeze the asyncio event-loop
clock).
"""

from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import Integer, String, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.stock_report.enums import (
    StockDemandOutcomeEnum,
    StockReportHistoryRecordTypeEnum,
)
from beyo_manager.errors.stock_report import StockDemandDeadlineExceeded
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._demand_lookup import (
    discover_live_rows_by_identity,
    resolve_categories_for_entries,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_updated_event,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import (
    DemandOutcome,
    StockDemandResult,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    refuse_webhook_auth,
)

def _active_snapshot_column(column, workspace_id, row_id):
    """`column` of `row_id`'s active item snapshot as a scalar subquery — NULL when
    the row has no active snapshot (a row created since the last version)."""
    return (
        select(column)
        .where(
            StockReportItemSnapshot.workspace_id == workspace_id,
            StockReportItemSnapshot.stock_report_item_id == row_id,
            StockReportItemSnapshot.closed_at.is_(None),
        )
        .scalar_subquery()
    )


async def apply_stock_demand(
    session,
    *,
    workspace_id: str,
    entries,
    now: datetime,
    deadline: float,
    timeout_ms: int,
) -> StockDemandResult:
    if session.in_transaction():
        raise RuntimeError(
            "apply_stock_demand requires a session with no open transaction — "
            "the caller must not issue any statement before this call (MC-9)"
        )

    outcomes: list[DemandOutcome] = []
    created_client_ids: list[str] = []
    updated_rows: list[object] = []

    async with maybe_begin(session):
        # 1. set_config — the first statement of the request, both limits bound as
        #    distinct parameters (fold O1) so the compiled statement carries $1/$2.
        await session.execute(
            text(
                "SELECT set_config('statement_timeout', :statement_timeout_ms, true), "
                "set_config('lock_timeout', :lock_timeout_ms, true)"
            ),
            {
                "statement_timeout_ms": str(timeout_ms),
                "lock_timeout_ms": str(timeout_ms),
            },
        )

        # 2. Workspace check (MC-8 step 4).
        workspace_row = (
            await session.execute(
                text("SELECT 1 FROM workspaces WHERE client_id = :ws"),
                {"ws": workspace_id},
            )
        ).first()
        if workspace_row is None:
            raise refuse_webhook_auth("workspace_not_found")

        # 3. Categories.
        category_by_key = await resolve_categories_for_entries(
            session, workspace_id=workspace_id, entries=entries
        )

        entries_by_identity: dict[tuple[str, str], object] = {}
        for entry in entries:
            category_id = category_by_key.get(entry.item_category_key)
            if category_id is None:
                outcomes.append(
                    DemandOutcome(
                        index=entry.index,
                        item_category_raw=entry.item_category_raw,
                        properties_raw=entry.properties_raw,
                        outcome=StockDemandOutcomeEnum.CATEGORY_NOT_FOUND,
                    )
                )
                continue
            entries_by_identity[(category_id, entry.properties_signature)] = entry
            outcomes.append(
                DemandOutcome(
                    index=entry.index,
                    item_category_raw=entry.item_category_raw,
                    properties_raw=entry.properties_raw,
                    outcome=StockDemandOutcomeEnum.APPLIED,
                )
            )

        # 4. Discovery, unlocked — decides only which identities step 5 must insert.
        existing_by_identity = await discover_live_rows_by_identity(
            session,
            workspace_id=workspace_id,
            identities=list(entries_by_identity.keys()),
        )

        # 5. Insert the absent identities only.
        absent_identities = sorted(
            identity
            for identity in entries_by_identity
            if identity not in existing_by_identity
        )
        if absent_identities:
            values = [
                {
                    "workspace_id": workspace_id,
                    "item_category_id": category_id,
                    "properties": entries_by_identity[
                        (category_id, signature)
                    ].properties_normalized,
                    "properties_signature": signature,
                    "quantity_requested": 0,
                }
                for category_id, signature in absent_identities
            ]
            insert_result = await session.execute(
                pg_insert(StockReportItem)
                .values(values)
                .on_conflict_do_nothing(
                    index_elements=[
                        "workspace_id",
                        "item_category_id",
                        "properties_signature",
                    ],
                    index_where=text("is_deleted = false"),
                )
                .returning(StockReportItem.client_id)
            )
            created_client_ids = [row.client_id for row in insert_result.all()]

        # 6. Lock — by identity, never by the client_ids steps 4/5 happened to see
        #    (H17): a concurrent insert can win an identity between step 4 and this
        #    lock, and step 5's own ON CONFLICT DO NOTHING then returns nothing for
        #    it, so its locally generated client_id is not the row's id.
        identity_list = list(entries_by_identity.keys())
        locked_by_identity: dict[tuple[str, str], StockReportItem] = {}
        if identity_list:
            locked_rows = (
                (
                    await session.execute(
                        select(StockReportItem)
                        .where(
                            StockReportItem.workspace_id == workspace_id,
                            StockReportItem.is_deleted.is_(False),
                            tuple_(
                                StockReportItem.item_category_id,
                                StockReportItem.properties_signature,
                            ).in_(identity_list),
                        )
                        .order_by(StockReportItem.client_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                )
                .scalars()
                .all()
            )
            locked_by_identity = {
                (row.item_category_id, row.properties_signature): row
                for row in locked_rows
            }

        if len(locked_by_identity) != len(identity_list):
            raise RuntimeError("stock demand identity vanished under lock")

        # 7-8. Bulk update of changed rows; bulk goal-record insert for increases.
        to_update: list[tuple[str, int]] = []
        to_credit: list[tuple[str, int, StockReportItem]] = []
        for identity, entry in entries_by_identity.items():
            row = locked_by_identity[identity]
            if entry.quantity_requested != row.quantity_requested:
                to_update.append((row.client_id, entry.quantity_requested))
                if entry.quantity_requested > row.quantity_requested:
                    to_credit.append((row.client_id, entry.quantity_requested, row))

        if to_update:
            values_sql = ", ".join(
                f"(CAST(:id_{i} AS varchar), CAST(:q_{i} AS integer))"
                for i in range(len(to_update))
            )
            params: dict[str, object] = {}
            for i, (client_id, new_quantity) in enumerate(to_update):
                params[f"id_{i}"] = client_id
                params[f"q_{i}"] = new_quantity
            update_result = await session.execute(
                text(
                    "UPDATE stock_report_items AS r SET quantity_requested = v.q "
                    f"FROM (VALUES {values_sql}) AS v(id, q) "
                    "WHERE r.client_id = v.id "
                    "RETURNING r.client_id AS client_id, "
                    "r.quantity_requested AS quantity_requested, "
                    "r.quantity_in_queue AS quantity_in_queue, "
                    "r.quantity_in_progress AS quantity_in_progress, "
                    "r.quantity_awaiting AS quantity_awaiting"
                ).columns(
                    client_id=String,
                    quantity_requested=Integer,
                    quantity_in_queue=Integer,
                    quantity_in_progress=Integer,
                    quantity_awaiting=Integer,
                ),
                params,
            )
            updated_rows = list(update_result.mappings().all())

        if to_credit:
            # The goal record still snapshots a priority, and since 2026-09-26 that
            # is the row's **active item snapshot's** (null when the row has none).
            # Read as two correlated scalar subqueries inside the one INSERT, so the
            # D6 statement plan keeps its bound (C6: the count is constant in the
            # batch size and at most 8) — a separate SELECT would be a ninth.
            history_values = [
                {
                    "workspace_id": workspace_id,
                    "stock_report_item_id": client_id,
                    "type": StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
                    "quantity_requested": new_quantity,
                    "quantity_awaiting": 0,
                    "priority": _active_snapshot_column(
                        StockReportItemSnapshot.priority, workspace_id, client_id
                    ),
                    "priority_order": _active_snapshot_column(
                        StockReportItemSnapshot.priority_order, workspace_id, client_id
                    ),
                    "created_at": now,
                    "created_by_id": None,
                }
                for client_id, new_quantity, _row in to_credit
            ]
            await session.execute(pg_insert(StockReportHistoryRecord).values(history_values))

        # 9. The deadline check — the last action inside the block.
        if time.monotonic() >= deadline:
            raise StockDemandDeadlineExceeded()

    # Events are built only after the transaction block exits normally (§9 rule 6,
    # MC-19). A row that is `:created` in this request never also gets `:updated`
    # (MC-19 net-change rule; MC-4) — its own quantity settle-up (step 7) is excluded
    # here even though it ran, because the row already got its one event.
    created_ids = set(created_client_ids)
    events: list[WorkspaceEvent] = [
        WorkspaceEvent(
            event_name="stock_report_item:created",
            client_id=client_id,
            workspace_id=workspace_id,
            extra={},
        )
        for client_id in created_client_ids
    ]
    events.extend(
        build_stock_report_item_updated_event(
            client_id=row["client_id"], workspace_id=workspace_id, values=row
        )
        for row in updated_rows
        if row["client_id"] not in created_ids
    )

    return StockDemandResult(outcomes=outcomes, events=events)
