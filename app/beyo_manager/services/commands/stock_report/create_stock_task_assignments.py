"""`create_stock_task_assignments` — MC-13's batch create (master plan §6.5; intention
§9C MC-12, MC-13 as amended by §14F F9/P44).

Six phases, all inside one transaction: 0 parse, 1 in-batch duplicates, 2 locks
(items -> tasks -> stock_report_items, MC-1 order), 3 per-entry refusal checks
(MC-13's closed vocabulary, in order), 4 the property matcher, 5 the writes. Any
phase 1/3 failure refuses the whole batch before anything is locked for a write, and
any phase 4 mismatch without an override refuses it before anything is written.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.stock_report.assignment_checks import (
    evaluate_assignment_checks,
    first_failed_check,
)
from beyo_manager.domain.stock_report.criteria_matcher import (
    evaluate_stock_criteria,
    serialize_criterion_failure,
)
from beyo_manager.domain.stock_report.serializers import serialize_stock_task_assignment
from beyo_manager.domain.stock_report.state_map import ASSIGNMENT_STATE_BY_TASK_STATE
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_items,
    lock_stock_report_item_snapshots,
    lock_stock_report_items,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._task_flag import set_task_stock_flag
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_create_stock_task_assignments_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.queries.stock_report.assignment_check_inputs import (
    fetch_assignment_check_inputs,
)


async def create_stock_task_assignments(ctx: ServiceContext) -> dict:
    request = parse_create_stock_task_assignments_request(ctx.incoming_data)
    entries = request.entries

    # Phase 1 — in-batch duplicates. Every offending index gets a reason (both
    # directions of a repeat, never only the later one); item_id is checked before
    # task_id when an entry could name either.
    item_counts = Counter(entry.item_id for entry in entries)
    task_counts = Counter(entry.task_id for entry in entries)
    reasons: dict[int, str] = {}
    for index, entry in enumerate(entries):
        if item_counts[entry.item_id] > 1:
            reasons[index] = "duplicate_item_in_batch"
        elif task_counts[entry.task_id] > 1:
            reasons[index] = "duplicate_task_in_batch"

    async with maybe_begin(ctx.session):
        item_ids = {entry.item_id for entry in entries}
        task_ids = {entry.task_id for entry in entries}
        row_ids = {entry.stock_report_item_id for entry in entries}

        # Phase 2 — locks, MC-1 order (items -> tasks -> stock_report_items ->
        # stock_report_item_snapshots). The rows' active snapshots are locked because
        # creation is the one move that clamps `quantity_missing` (§5.3); their ids
        # are discovered unlocked first, which only decides what to lock.
        locked_items = await lock_items(ctx.session, ctx.workspace_id, item_ids)
        locked_tasks = await lock_tasks(ctx.session, ctx.workspace_id, task_ids)
        locked_rows = await lock_stock_report_items(
            ctx.session, ctx.workspace_id, row_ids
        )
        active_snapshot_ids = (
            await ctx.session.scalars(
                select(StockReportItemSnapshot.client_id).where(
                    StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                    StockReportItemSnapshot.stock_report_item_id.in_(row_ids),
                    StockReportItemSnapshot.closed_at.is_(None),
                )
            )
        ).all()
        locked_snapshots = await lock_stock_report_item_snapshots(
            ctx.session, ctx.workspace_id, active_snapshot_ids
        )
        initial_row_values = {
            row_id: row_values(row) for row_id, row in locked_rows.items()
        }
        initial_snapshot_values = {
            snapshot_id: snapshot_values(snapshot)
            for snapshot_id, snapshot in locked_snapshots.items()
        }

        (
            primary_pairs,
            processed_pairs,
            active_item_ids,
        ) = await fetch_assignment_check_inputs(
            ctx.session,
            workspace_id=ctx.workspace_id,
            task_ids=task_ids,
            item_ids=item_ids,
        )

        # Phase 3 — per-entry refusal checks, first failing reason wins.
        for index, entry in enumerate(entries):
            if index in reasons:
                continue
            reason = first_failed_check(
                evaluate_assignment_checks(
                    row=locked_rows.get(entry.stock_report_item_id),
                    task=locked_tasks.get(entry.task_id),
                    item=locked_items.get(entry.item_id),
                    task_id=entry.task_id,
                    item_id=entry.item_id,
                    primary_pairs=primary_pairs,
                    processed_pairs=processed_pairs,
                    active_item_ids=active_item_ids,
                )
            )
            if reason is not None:
                reasons[index] = reason

        if reasons:
            raise StockAssignmentRefused(
                [
                    {"index": index, "reason": reasons[index]}
                    for index in sorted(reasons)
                ]
            )

        # Phase 4 — the property matcher (MC-12).
        failures_by_index: dict[int, list] = {}
        mismatch_details = []
        for index, entry in enumerate(entries):
            row = locked_rows[entry.stock_report_item_id]
            item = locked_items[entry.item_id]
            failures = evaluate_stock_criteria(item, row.properties)
            failures_by_index[index] = failures
            if failures and not entry.override_property_mismatch:
                mismatch_details.append(
                    {
                        "index": index,
                        "stock_report_item_id": entry.stock_report_item_id,
                        "task_id": entry.task_id,
                        "item_id": entry.item_id,
                        "failures": [
                            serialize_criterion_failure(failure) for failure in failures
                        ],
                    }
                )
        if mismatch_details:
            raise StockAssignmentPropertyMismatch(mismatch_details)

        # Phase 5 — the writes, ascending item_id (master plan §10: client_id order is
        # not creation order, so the response is sorted at serialization time too).
        events = []
        created: list[StockTaskAssignment] = []
        order = sorted(range(len(entries)), key=lambda i: entries[i].item_id)
        try:
            for index in order:
                entry = entries[index]
                row = locked_rows[entry.stock_report_item_id]
                item = locked_items[entry.item_id]
                task = locked_tasks[entry.task_id]
                target_state = ASSIGNMENT_STATE_BY_TASK_STATE[task.state]
                assignment = StockTaskAssignment(
                    workspace_id=ctx.workspace_id,
                    stock_report_item_id=row.client_id,
                    task_id=task.client_id,
                    item_id=item.client_id,
                    quantity=max(item.quantity, 1),
                    property_mismatch_overridden=bool(
                        failures_by_index[index] and entry.override_property_mismatch
                    ),
                    state=target_state,
                    created_by_id=ctx.user_id or None,
                )
                ctx.session.add(assignment)
                await ctx.session.flush()
                events.extend(
                    await move_assignment(
                        ctx.session,
                        assignment,
                        target_state,
                        workspace_id=ctx.workspace_id,
                        actor_user_id=ctx.user_id,
                        now=ctx.now,
                        trigger="create_assignments",
                        is_creation=True,
                    )
                )
                await set_task_stock_flag(
                    ctx.session, ctx.workspace_id, task.client_id, True
                )
                created.append(assignment)
        except IntegrityError:
            raise StockAssignmentRefused(
                [{"index": index, "reason": "item_already_assigned"}]
            ) from None

        item_ids_for_images = {assignment.item_id for assignment in created}
        images_by_item: dict[str, list] = {}
        if item_ids_for_images:
            image_rows = await ctx.session.execute(
                select(Image, ImageLink.entity_client_id)
                .join(
                    ImageLink,
                    and_(
                        ImageLink.image_id == Image.client_id,
                        ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                        ImageLink.entity_client_id.in_(item_ids_for_images),
                    ),
                )
                .where(Image.deleted_at.is_(None))
                .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
            )
            for image, item_id in image_rows.all():
                images_by_item.setdefault(item_id, []).append(image)

    dispatch_events = coalesce_stock_report_events(
        events,
        initial_row_values=initial_row_values,
        initial_snapshot_values=initial_snapshot_values,
    )
    await dispatch(dispatch_events)

    response_assignments = sorted(created, key=lambda assignment: assignment.item_id)
    return {
        "stock_task_assignments": [
            serialize_stock_task_assignment(
                assignment,
                item=locked_items[assignment.item_id],
                task=locked_tasks[assignment.task_id],
                images=images_by_item.get(assignment.item_id, []),
            )
            for assignment in response_assignments
        ]
    }
