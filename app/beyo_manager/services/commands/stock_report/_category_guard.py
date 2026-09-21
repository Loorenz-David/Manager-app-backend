"""`assert_item_category_change_allowed` — the category guard on both item writers
(master plan §6.5; intention §5B MC-14 "category change refused"). The caller holds
the Item lock and has re-read the stored category (`populate_existing`) before
calling.
"""

from sqlalchemy import select

from beyo_manager.domain.stock_report.enums import ACTIVE_ASSIGNMENT_STATES
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)

_MESSAGE = "Unassign this item from the stock report before changing its category."


async def assert_item_category_change_allowed(
    session, *, workspace_id, item_id, current_category_id, incoming_category_id
) -> None:
    if incoming_category_id == current_category_id:
        return  # None-aware: setting the same value is not a change
    active = await session.execute(
        select(StockTaskAssignment.client_id)
        .where(
            StockTaskAssignment.workspace_id == workspace_id,
            StockTaskAssignment.item_id == item_id,
            StockTaskAssignment.is_deleted.is_(False),
            StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
        )
        .limit(1)
    )
    if active.first() is not None:
        raise ConflictError(_MESSAGE)
