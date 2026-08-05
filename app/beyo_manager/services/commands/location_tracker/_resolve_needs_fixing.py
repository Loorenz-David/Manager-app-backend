"""Resolve the needs_fixing flag for items whose caller has no task in hand.

update_item, batch_update_item_positions and create_item all move an item's zone without
knowing which task it belongs to, so the flag has to come from the item's live task links.
Callers that *do* hold the task type (create_task, most notably, whose TaskItem row does not
exist yet at push time) pass the flag explicitly instead and never reach this.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.items.location_push import NEEDS_FIXING_TASK_TYPES
from beyo_manager.domain.task_steps.constants import TERMINAL_TASK_STATES
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem


async def resolve_items_needing_fixing(session, item_ids: list[str]) -> set[str]:
    """Return the subset of item_ids linked to an open task of a needs-fixing type.

    One query regardless of how many items are asked about, so batch callers stay at a single
    round trip. "Open" means the task has not reached a terminal state and is not deleted; a
    resolved return leaves the item unflagged on its next move.
    """
    if not item_ids:
        return set()

    result = await session.execute(
        select(TaskItem.item_id)
        .join(Task, Task.client_id == TaskItem.task_id)
        .where(
            TaskItem.item_id.in_(item_ids),
            TaskItem.removed_at.is_(None),
            Task.task_type.in_(NEEDS_FIXING_TASK_TYPES),
            Task.state.notin_(TERMINAL_TASK_STATES),
            Task.is_deleted.is_(False),
        )
        .distinct()
    )
    return set(result.scalars().all())


async def resolve_item_needs_fixing(session, item_id: str) -> bool:
    return item_id in await resolve_items_needing_fixing(session, [item_id])
