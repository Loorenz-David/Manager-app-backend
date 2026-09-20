from sqlalchemy import select, update

from beyo_manager.domain.stock_report.enums import (
    ACTIVE_ASSIGNMENT_STATES,
    StockReportRepairTargetKindEnum,
    StockTaskAssignmentStateEnum,
    TERMINAL_ASSIGNMENT_STATES,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_updated_event,
    build_stock_task_assignment_event,
)
from beyo_manager.services.commands.stock_report._repair_records import (
    write_repair_record,
)
from beyo_manager.services.queries.stock_report.consistency import (
    recompute_row_counters,
)


class _AssignmentDeleteSentinel:
    """`move_assignment`'s `target` sentinel: soft-delete the assignment (MC-1)."""

    def __repr__(self):
        return "ASSIGNMENT_DELETE"


ASSIGNMENT_DELETE = _AssignmentDeleteSentinel()


class IllegalAssignmentMove(RuntimeError):
    """The requested transition is not a cell of MC-1's table — a programming error,
    never a domain error."""


_COUNTER_COLUMN = {
    StockTaskAssignmentStateEnum.IN_QUEUE: "quantity_in_queue",
    StockTaskAssignmentStateEnum.IN_PROGRESS: "quantity_in_progress",
    StockTaskAssignmentStateEnum.AWAITING: "quantity_awaiting",
}

_RETURNING_COLUMNS = (
    StockReportItem.quantity_requested,
    StockReportItem.quantity_in_queue,
    StockReportItem.quantity_in_progress,
    StockReportItem.quantity_awaiting,
    StockReportItem.priority,
    StockReportItem.priority_order,
)


def _assert_allowed_move(from_state, target, is_creation):
    """MC-1's allowed-move table (as amended by §14F F1-F2), written from the two
    frozensets plus the two named Scanner-only cells — never a hand-typed state list
    (master plan §9 rule 16)."""
    if is_creation:
        if target in ACTIVE_ASSIGNMENT_STATES:
            return
        raise IllegalAssignmentMove(f"illegal creation move ∅ -> {target!r}")
    if target is ASSIGNMENT_DELETE:
        return  # every non-creation state may be deleted
    if from_state == target:
        return  # '=' cell; move_assignment short-circuits this before writing anything
    if from_state in TERMINAL_ASSIGNMENT_STATES:
        raise IllegalAssignmentMove(
            f"illegal move from terminal state {from_state!r} to {target!r}"
        )
    if target in ACTIVE_ASSIGNMENT_STATES:
        return  # sync moves between active states
    if target == StockTaskAssignmentStateEnum.FAILED:
        return  # sync -> failed, from any active state
    if target == StockTaskAssignmentStateEnum.RESOLVED:
        if from_state == StockTaskAssignmentStateEnum.AWAITING:
            return  # Scanner-only exit
        raise IllegalAssignmentMove(
            f"illegal move {from_state!r} -> resolved (Scanner exits only from awaiting)"
        )
    if target == StockTaskAssignmentStateEnum.RESOLVED_EARLY:
        if from_state in (
            StockTaskAssignmentStateEnum.IN_QUEUE,
            StockTaskAssignmentStateEnum.IN_PROGRESS,
        ):
            return  # Scanner-only exit (§14F F2); never from awaiting
        raise IllegalAssignmentMove(f"illegal move {from_state!r} -> resolved_early")
    raise IllegalAssignmentMove(f"illegal move {from_state!r} -> {target!r}")


def _delta_vector(from_state, target, quantity, is_creation):
    """§5 rule 5: -q on *from*'s counter if *from* is active, +q on *to*'s if *to* is
    active. Terminal targets and DELETE add nothing."""
    deltas = {"quantity_in_queue": 0, "quantity_in_progress": 0, "quantity_awaiting": 0}
    if not is_creation and from_state in ACTIVE_ASSIGNMENT_STATES:
        deltas[_COUNTER_COLUMN[from_state]] -= quantity
    if target in ACTIVE_ASSIGNMENT_STATES:
        deltas[_COUNTER_COLUMN[target]] += quantity
    return deltas


async def _apply_counter_delta(session, *, row_id, deltas, workspace_id, trigger, now):
    """The guarded, column-referencing counter UPDATE, with inline self-heal on a
    would-be negative counter (MC-1)."""
    stmt = (
        update(StockReportItem)
        .where(
            StockReportItem.client_id == row_id,
            (StockReportItem.quantity_in_queue + deltas["quantity_in_queue"]) >= 0,
            (StockReportItem.quantity_in_progress + deltas["quantity_in_progress"])
            >= 0,
            (StockReportItem.quantity_awaiting + deltas["quantity_awaiting"]) >= 0,
        )
        .values(
            quantity_in_queue=StockReportItem.quantity_in_queue
            + deltas["quantity_in_queue"],
            quantity_in_progress=StockReportItem.quantity_in_progress
            + deltas["quantity_in_progress"],
            quantity_awaiting=StockReportItem.quantity_awaiting
            + deltas["quantity_awaiting"],
        )
        .returning(*_RETURNING_COLUMNS)
    )
    row = (await session.execute(stmt)).mappings().first()
    if row is not None:
        return dict(row)

    # Self-heal: 0 rows means exactly "a counter would go negative" (the row is
    # already locked and exists). stored_before is read fresh, never from a stale
    # ORM instance (MC-1 re-check, round 7).
    stored_before = (
        (
            await session.execute(
                select(
                    StockReportItem.quantity_in_queue,
                    StockReportItem.quantity_in_progress,
                    StockReportItem.quantity_awaiting,
                ).where(StockReportItem.client_id == row_id)
            )
        )
        .mappings()
        .one()
    )
    recomputed = await recompute_row_counters(session, row_id)
    repaired = (
        (
            await session.execute(
                update(StockReportItem)
                .where(StockReportItem.client_id == row_id)
                .values(**recomputed)
                .returning(*_RETURNING_COLUMNS)
            )
        )
        .mappings()
        .first()
    )
    if repaired is None:
        raise RuntimeError(
            f"stock-report counter self-heal affected 0 rows for {row_id}"
        )
    for field, recomputed_value in recomputed.items():
        stored_value = stored_before[field]
        delta = deltas[field]
        if stored_value + delta != recomputed_value:
            await write_repair_record(
                session,
                workspace_id=workspace_id,
                target_kind=StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
                target_client_id=row_id,
                field=field,
                stored_value=stored_value,
                recomputed_value=recomputed_value,
                trigger=f"inline:{trigger}",
                created_by_id=None,
                now=now,
                delta=delta,
            )
    return dict(repaired)


async def move_assignment(
    session,
    assignment,
    target,
    *,
    workspace_id,
    actor_user_id,
    now,
    trigger,
    is_creation=False,
):
    """The one operation that moves an assignment and its unit counters (MC-1). The
    caller holds the row lock and the assignment lock and has re-read `state` /
    `is_deleted`. Never reads `ctx`, never commits, never dispatches."""
    from_state = None if is_creation else assignment.state
    if (
        not is_creation
        and target is not ASSIGNMENT_DELETE
        and assignment.state == target
    ):
        return []
    _assert_allowed_move(from_state, target, is_creation)

    # Step 1 — own columns, flushed before any recomputation (MC-1 write order).
    if is_creation:
        assignment.state = target
        session.add(assignment)
    elif target is ASSIGNMENT_DELETE:
        assignment.is_deleted = True
        assignment.deleted_at = now
        assignment.deleted_by_id = actor_user_id or None
    else:
        assignment.state = target
        assignment.updated_by_id = actor_user_id or None
        assignment.updated_at = now
    await session.flush()

    quantity = assignment.quantity
    deltas = _delta_vector(from_state, target, quantity, is_creation)

    # Step 2 (+ inline self-heal) — the guarded counter statement.
    values = await _apply_counter_delta(
        session,
        row_id=assignment.stock_report_item_id,
        deltas=deltas,
        workspace_id=workspace_id,
        trigger=trigger,
        now=now,
    )

    # Step 5 — events, built only from RETURNING values (MC-1, MC-19).
    if is_creation:
        kind = "created"
    elif target is ASSIGNMENT_DELETE:
        kind = "deleted"
    else:
        kind = "state-changed"
    event_state = (
        assignment.state.value if target is ASSIGNMENT_DELETE else target.value
    )
    events = [
        build_stock_task_assignment_event(
            kind,
            client_id=assignment.client_id,
            workspace_id=workspace_id,
            stock_report_item_id=assignment.stock_report_item_id,
            task_id=assignment.task_id,
            state=event_state,
        )
    ]
    if any(value != 0 for value in deltas.values()):
        events.append(
            build_stock_report_item_updated_event(
                client_id=assignment.stock_report_item_id,
                workspace_id=workspace_id,
                values=values,
            )
        )
    return events
