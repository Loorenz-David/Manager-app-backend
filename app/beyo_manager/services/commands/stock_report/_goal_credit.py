from sqlalchemy import select, update

from beyo_manager.domain.stock_report.enums import (
    StockReportRepairTargetKindEnum,
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.services.commands.stock_report._repair_records import (
    write_repair_record,
)
from beyo_manager.services.queries.stock_report.consistency import (
    recompute_goal_total,
)


async def current_goal_record_id(session, stock_report_item_id):
    """The non-deleted quantity_requested_change record with the greatest
    (created_at, client_id) — the row's current goal record (MC-5)."""
    result = await session.execute(
        select(StockReportHistoryRecord.client_id)
        .where(
            StockReportHistoryRecord.stock_report_item_id == stock_report_item_id,
            StockReportHistoryRecord.type
            == StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
            StockReportHistoryRecord.is_deleted.is_(False),
        )
        .order_by(
            StockReportHistoryRecord.created_at.desc(),
            StockReportHistoryRecord.client_id.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _credit_current_goal(session, assignment, now):
    goal_id = await current_goal_record_id(session, assignment.stock_report_item_id)
    if goal_id is None:
        return
    result = await session.execute(
        update(StockReportHistoryRecord)
        .where(StockReportHistoryRecord.client_id == goal_id)
        .values(
            quantity_awaiting=StockReportHistoryRecord.quantity_awaiting
            + assignment.quantity
        )
        .returning(StockReportHistoryRecord.client_id)
    )
    if result.first() is None:
        raise RuntimeError(f"goal credit affected 0 rows for {goal_id}")
    # Own-columns write of the assignment's credit memory, flushed immediately —
    # the same discipline as MC-1's own-columns step.
    assignment.credited_history_record_id = goal_id
    await session.flush()


async def _uncredit(session, assignment, trigger, now):
    record_id = assignment.credited_history_record_id
    if record_id is None:
        return
    quantity = assignment.quantity
    # Clear and flush the memory before any statement on R (MC-5 order), so a
    # recomputation below excludes the assignment being un-credited.
    assignment.credited_history_record_id = None
    await session.flush()
    result = await session.execute(
        update(StockReportHistoryRecord)
        .where(
            StockReportHistoryRecord.client_id == record_id,
            (StockReportHistoryRecord.quantity_awaiting - quantity) >= 0,
        )
        .values(
            quantity_awaiting=StockReportHistoryRecord.quantity_awaiting - quantity
        )
        .returning(StockReportHistoryRecord.client_id)
    )
    if result.first() is not None:
        return

    # Self-heal: 0 rows means the subtraction would go negative.
    stored_before = await session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == record_id
        )
    )
    recomputed = await recompute_goal_total(session, record_id)
    updated = await session.execute(
        update(StockReportHistoryRecord)
        .where(StockReportHistoryRecord.client_id == record_id)
        .values(quantity_awaiting=recomputed)
        .returning(StockReportHistoryRecord.client_id)
    )
    if updated.first() is None:
        raise RuntimeError(f"goal self-heal affected 0 rows for {record_id}")
    await write_repair_record(
        session,
        workspace_id=assignment.workspace_id,
        target_kind=StockReportRepairTargetKindEnum.HISTORY_RECORD,
        target_client_id=record_id,
        field="quantity_awaiting",
        stored_value=stored_before,
        recomputed_value=recomputed,
        trigger=f"inline:{trigger}",
        created_by_id=None,
        now=now,
        delta=-quantity,
    )


async def apply_goal_effect(session, assignment, *, from_state, to_state, trigger, now):
    """MC-5's table, exactly (as amended by §14F F4). Called inside move_assignment
    after the counter statement."""
    if to_state in (
        StockTaskAssignmentStateEnum.AWAITING,
        StockTaskAssignmentStateEnum.RESOLVED_EARLY,
    ):
        # Entering awaiting from ∅/in_queue/in_progress, or resolved_early from
        # in_queue/in_progress (never from awaiting — MC-1 forbids that move):
        # credit the current goal record if one exists.
        if from_state != StockTaskAssignmentStateEnum.AWAITING:
            await _credit_current_goal(session, assignment, now)
        return
    if from_state == StockTaskAssignmentStateEnum.AWAITING:
        if to_state == StockTaskAssignmentStateEnum.RESOLVED:
            return  # kept: resolved work stays counted
        await _uncredit(session, assignment, trigger, now)
        return
    # resolved -> DELETE, resolved_early -> DELETE, or any other case: the credit
    # memory is NULL by construction or must be kept (F4: "never removed") — nothing.
