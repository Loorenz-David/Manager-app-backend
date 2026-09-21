"""`process_items_processed` — the processed webhook's owning command (phase 9;
master plan §6.5; intention §8B MC-8/MC-10, §14F F5-F8).

verify -> parse -> one owning transaction (X3: nothing on `ctx.session` before it) ->
workspace check (MC-8 step 4) -> unlocked discovery (items, then their active
assignments) -> sorted locks (rows, then assignments; X2) -> per-entry decision in
request order, on the §14F F5 ladder -> grouped resolution per row
(`resolve_processed_group`) -> dispatch -> response in request order.

The task is never touched (F3): this command writes only `stock_task_assignments`,
`stock_report_items` and, through the goal step, `stock_report_history_records`.
"""

from __future__ import annotations

from sqlalchemy import select, text

from beyo_manager.domain.stock_report.enums import (
    ACTIVE_ASSIGNMENT_STATES,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_items,
    lock_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report._move_assignment import (
    resolve_processed_group,
)
from beyo_manager.services.commands.stock_report.items_processed_request import (
    parse_items_processed_body,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.location_tracker.webhook_verifier import (
    verify_location_tracker_webhook,
)


async def process_items_processed(ctx) -> dict:
    workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])
    numbers = parse_items_processed_body(ctx.incoming_data["raw_body"])

    if ctx.session.in_transaction():
        raise RuntimeError(
            "process_items_processed requires a session with no open transaction — "
            "the caller must not issue any statement before this call (X3)"
        )

    stripped_by_index = [(index, number, number.strip()) for index, number in enumerate(numbers)]

    events: list = []
    outcomes: list[tuple[str, str | None]] = [None] * len(numbers)  # type: ignore[list-item]

    async with maybe_begin(ctx.session):
        # Workspace check (MC-8 step 4).
        workspace_row = (
            await ctx.session.execute(
                text("SELECT 1 FROM workspaces WHERE client_id = :ws"),
                {"ws": workspace_id},
            )
        ).first()
        if workspace_row is None:
            raise LocationTrackerWebhookAuthError("Unauthorized.")

        stripped_numbers = {stripped for _, _, stripped in stripped_by_index}

        # Discovery, unlocked — items by article_number (exact, case-sensitive; MC-10
        # step 1: no inner folding).
        item_rows = (
            await ctx.session.execute(
                select(Item.client_id, Item.article_number).where(
                    Item.workspace_id == workspace_id,
                    Item.is_deleted.is_(False),
                    Item.article_number.in_(stripped_numbers),
                )
            )
        ).all()
        item_id_by_number = {row.article_number: row.client_id for row in item_rows}

        # Discovery, unlocked — each item's non-deleted active assignment (at most
        # one, MC-4's partial unique index).
        item_ids = list(item_id_by_number.values())
        assignment_id_by_item_id: dict[str, str] = {}
        row_id_by_assignment_id: dict[str, str] = {}
        if item_ids:
            assignment_rows = (
                await ctx.session.execute(
                    select(
                        StockTaskAssignment.client_id,
                        StockTaskAssignment.stock_report_item_id,
                        StockTaskAssignment.item_id,
                    ).where(
                        StockTaskAssignment.workspace_id == workspace_id,
                        StockTaskAssignment.is_deleted.is_(False),
                        StockTaskAssignment.item_id.in_(item_ids),
                        StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
                    )
                )
            ).all()
            for assignment_row in assignment_rows:
                assignment_id_by_item_id[assignment_row.item_id] = assignment_row.client_id
                row_id_by_assignment_id[
                    assignment_row.client_id
                ] = assignment_row.stock_report_item_id

        # Locks, ascending, one statement each (X2): rows, then their candidate
        # assignments (MC-1 lock order steps 4-5).
        candidate_row_ids = sorted(set(row_id_by_assignment_id.values()))
        locked_rows = await lock_stock_report_items(
            ctx.session, workspace_id, candidate_row_ids
        )
        candidate_assignment_ids = sorted(row_id_by_assignment_id.keys())
        locked_assignments = await lock_stock_task_assignments(
            ctx.session, workspace_id, candidate_assignment_ids
        )

        # Re-read state after the lock; decide per entry, in request order, on the
        # §14F F5 ladder — a duplicate later in the request sees the earlier one's
        # effect (MC-10 step 3), tracked here by mutating `working_state` in place.
        working_state = {
            aid: assignment.state for aid, assignment in locked_assignments.items()
        }
        moved_assignment_ids: list[str] = []
        for index, raw_number, stripped in stripped_by_index:
            item_id = item_id_by_number.get(stripped)
            if item_id is None:
                outcomes[index] = (raw_number, "ignored", "item_not_found")
                continue
            assignment_id = assignment_id_by_item_id.get(item_id)
            if assignment_id is None:
                outcomes[index] = (raw_number, "ignored", "no_open_assignment")
                continue
            state = working_state[assignment_id]
            if state not in ACTIVE_ASSIGNMENT_STATES:
                outcomes[index] = (raw_number, "ignored", "no_open_assignment")
                continue
            if state == StockTaskAssignmentStateEnum.AWAITING:
                target = StockTaskAssignmentStateEnum.RESOLVED
                reason = None
            else:
                target = StockTaskAssignmentStateEnum.RESOLVED_EARLY
                reason = "early"
            outcomes[index] = (raw_number, "resolved", reason)
            working_state[assignment_id] = target
            if assignment_id not in moved_assignment_ids:
                moved_assignment_ids.append(assignment_id)

        # Grouped resolution, rows ascending (D6 "Processed, grouped per row").
        moved_by_row: dict[str, list] = {}
        for assignment_id in moved_assignment_ids:
            assignment = locked_assignments[assignment_id]
            moved_by_row.setdefault(assignment.stock_report_item_id, []).append(assignment)
        for row_id in sorted(moved_by_row):
            row_events = await resolve_processed_group(
                ctx.session,
                moved_by_row[row_id],
                row=locked_rows[row_id],
                workspace_id=workspace_id,
                now=ctx.now,
                trigger="items_processed",
            )
            events.extend(row_events)

    await dispatch(events)

    results = [
        {"article_number": raw_number, "outcome": outcome, "reason": reason}
        for raw_number, outcome, reason in outcomes
    ]
    return {"results": results}
