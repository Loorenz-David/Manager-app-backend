"""`process_stock_demand_deleted` — the Scanner delete webhook's owning command
(phase 13A; master plan §6.5/§6.6; intention §14E, §8B MC-8/MC-9, §5A MC-1/MC-16,
§7A MC-7, §4B MC-17, §9D MC-19).

deadline -> verify -> parse -> one owning transaction -> dispatch -> response, in
that order. Inside the transaction, in MC-1's global lock order:

    set_config -> workspace check -> **advisory lock** -> category resolution ->
    identity discovery -> assignment id discovery -> tasks (class 3) ->
    rows (class 4) -> their active snapshots + priority groups -> assignments
    (class 5) -> re-read ->
    one cascade per candidate row, ascending `client_id` -> deadline check

The advisory lock is taken **before** discovery (carried question Q1): every path
that soft-deletes a row holds it first, so the live set discovered next cannot shrink
before the row locks are taken. Each class is acquired in exactly **one** sorted
statement whatever the number of candidate rows (Q2), and each cascade closes its own
gap from the positions as they stand after the previous cascade in this transaction
(MC-7).

Never reads `ctx.workspace_id` (it is `""` on a webhook path — master plan §9 rule 5):
the workspace comes from the verifier's return value and is passed explicitly to every
subordinate. `time` is imported as the module and referenced as `time.monotonic()` so
a test can replace the name `process_stock_demand_deleted.time` without freezing the
event-loop clock.
"""

from __future__ import annotations

import time

from sqlalchemy import select, text

from beyo_manager.config import settings
from beyo_manager.domain.stock_report.enums import StockDemandDeletedOutcomeEnum
from beyo_manager.errors.stock_report import StockDemandDeadlineExceeded
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._delete_stock_report_item_cascade import (
    cascade_delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report._demand_lookup import (
    discover_live_rows_by_identity,
    resolve_categories_for_entries,
)
from beyo_manager.services.commands.stock_report._events import (
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    lock_active_snapshots_and_groups,
)
from beyo_manager.services.commands.stock_report.stock_demand_deleted_request import (
    parse_stock_demand_deleted_body,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    refuse_webhook_auth,
    verify_location_tracker_webhook,
)


async def _lock_rows(session, workspace_id, candidate_row_ids):
    """Class 4 — the candidate rows, in one `SELECT … FOR UPDATE ORDER BY client_id`
    (MC-1). The priority groups moved to the snapshot table on 2026-09-26 and are
    locked next, by `lock_active_snapshots_and_groups` (one statement, Q2)."""
    rows = (
        (
            await session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                    StockReportItem.client_id.in_(candidate_row_ids),
                )
                .order_by(StockReportItem.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {row.client_id: row for row in rows}


async def process_stock_demand_deleted(ctx) -> dict:
    timeout_ms = settings.stock_demand_webhook_timeout_ms
    deadline = time.monotonic() + timeout_ms / 1000  # first line — MC-9 part 1 (E9)

    workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])
    entries = parse_stock_demand_deleted_body(ctx.incoming_data["raw_body"])

    if ctx.session.in_transaction():
        raise RuntimeError(
            "process_stock_demand_deleted requires a session with no open "
            "transaction — the caller must not issue any statement before this "
            "call (X3)"
        )

    outcome_by_index: dict[int, StockDemandDeletedOutcomeEnum] = {}
    events: list = []
    initial_row_values: dict[str, dict] = {}

    async with maybe_begin(ctx.session):
        # 1. set_config — the first statement of the request (MC-9 D5; E9).
        await ctx.session.execute(
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
            await ctx.session.execute(
                text("SELECT 1 FROM workspaces WHERE client_id = :ws"),
                {"ws": workspace_id},
            )
        ).first()
        if workspace_row is None:
            raise refuse_webhook_auth("workspace_not_found")

        # 3. The ordering advisory lock (MC-1 class 1), taken BEFORE discovery.
        await acquire_stock_report_order_lock(ctx.session, workspace_id)

        # 4. Category resolution — one SELECT over the request's key set (MC-8).
        category_by_key = await resolve_categories_for_entries(
            ctx.session, workspace_id=workspace_id, entries=entries
        )
        identity_by_index: dict[int, tuple[str, str]] = {}
        for entry in entries:
            category_id = category_by_key.get(entry.item_category_key)
            if category_id is None:
                outcome_by_index[entry.index] = (
                    StockDemandDeletedOutcomeEnum.CATEGORY_NOT_FOUND
                )
                continue
            identity_by_index[entry.index] = (
                category_id,
                entry.properties_signature,
            )

        # 5. Identity discovery — one unlocked SELECT, live rows only. Nothing is
        #    ever inserted here (§14E E4 "nothing is created").
        live_by_identity = await discover_live_rows_by_identity(
            ctx.session,
            workspace_id=workspace_id,
            identities=list(identity_by_index.values()),
        )
        row_id_by_index: dict[int, str] = {}
        for index, identity in identity_by_index.items():
            row_id = live_by_identity.get(identity)
            if row_id is None:
                outcome_by_index[index] = StockDemandDeletedOutcomeEnum.NOT_FOUND
            else:
                row_id_by_index[index] = row_id
                outcome_by_index[index] = StockDemandDeletedOutcomeEnum.DELETED
        candidate_row_ids = sorted(set(row_id_by_index.values()))

        # 6. Assignment id discovery, unlocked — it decides only which ids to lock.
        discovered_assignments = []
        if candidate_row_ids:
            discovered_assignments = (
                await ctx.session.execute(
                    select(
                        StockTaskAssignment.client_id, StockTaskAssignment.task_id
                    ).where(
                        StockTaskAssignment.workspace_id == workspace_id,
                        StockTaskAssignment.stock_report_item_id.in_(
                            candidate_row_ids
                        ),
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            ).all()

        # 7-9. The three lock classes, one sorted statement each.
        await lock_tasks(
            ctx.session,
            workspace_id,
            {task_id for _assignment_id, task_id in discovered_assignments},
        )
        locked_rows: dict[str, StockReportItem] = {}
        if candidate_row_ids:
            locked_rows = await _lock_rows(ctx.session, workspace_id, candidate_row_ids)
        locked_snapshots = await lock_active_snapshots_and_groups(
            ctx.session, workspace_id, candidate_row_ids
        )
        await lock_stock_task_assignments(
            ctx.session,
            workspace_id,
            {assignment_id for assignment_id, _task_id in discovered_assignments},
        )

        # 10. Re-read. A candidate missing from the locked set is impossible while
        #     every row-deleting path takes the advisory lock first (Q1); a 500 that
        #     Scanner retries beats a silent `not_found` hiding a lock-order
        #     regression.
        for row_id in candidate_row_ids:
            if row_id not in locked_rows:
                raise RuntimeError(
                    f"stock report row {row_id} vanished between discovery and lock"
                )

        initial_row_values = {
            row_id: row_values(row) for row_id, row in locked_rows.items()
        }
        initial_snapshot_values = {
            snapshot_id: snapshot_values(snapshot)
            for snapshot_id, snapshot in locked_snapshots.items()
        }

        # 11. One cascade per candidate row, ascending `client_id`. Each closes its
        #     own gap from the positions the previous cascade left (MC-7).
        for row_id in candidate_row_ids:
            events.extend(
                await cascade_delete_stock_report_item(
                    ctx.session,
                    locked_rows[row_id],
                    workspace_id=workspace_id,
                    actor_user_id=None,
                    now=ctx.now,
                    trigger="stock_demand_deleted",
                )
            )

        # 12. The deadline check — the last action inside the block (E9).
        if time.monotonic() >= deadline:
            raise StockDemandDeadlineExceeded()

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values=initial_row_values,
            initial_snapshot_values=initial_snapshot_values,
        )
    )

    return {
        "results": [
            {
                "itemCategory": entry.item_category_raw,
                "properties": entry.properties_raw,
                "outcome": outcome_by_index[entry.index].value,
            }
            for entry in entries
        ]
    }
