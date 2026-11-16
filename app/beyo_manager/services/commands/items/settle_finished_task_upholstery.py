"""Release fabric that a finished task never got.

When a task ends up READY / RESOLVED / CANCELLED / FAILED, any requirement on its items
that is still ``needs_ordering`` or ``ordered`` describes fabric the work never received.
Left alone it stays in the ordering list and inflates the inventory's "in need" total
forever: nothing else ever moves it (incident 2026-11-16, PRE-ORDER 29, task #1014 —
forced ready as a duplicate with its requirement still ``needs_ordering``).

Settling means **cancelling** (requirement -> FAILED, need released through
``cancel_requirements_in_session``), never completing: the fabric was not allocated to
this item, so recording it as used would double-count stock consumed elsewhere (product
owner decision, 2026-11-16). ``available`` / ``in_use`` requirements are deliberately not
touched — that fabric *was* allocated, and the installation step / force-ready already
complete it.

Called at command level, right after ``sync_task_stock_assignments`` and with the same
``changed`` list (every task whose state net-changed in the command), never inside the
``_task_state_transitions`` helpers — a helper-level call could act on an intermediate
READY the transaction never settles on (``remove_task_step``: ready -> in_queue).
``test_task_state_write_sites_are_registered`` enforces both directions.

Lock order: the caller already holds the task row (its own UPDATE); this locks the
requirement rows, then ``adjust_need`` locks the inventory row — the same relative
order ``delete_task`` uses (items -> task -> requirements -> inventory), minus the item
locks, which this path does not take.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.domain.upholstery.enums import InventoryMovementTriggerEnum
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    CancelledRequirement,
    cancel_requirements_in_session,
)
from beyo_manager.services.commands.upholstery._inventory_history import (
    InventoryMovementContext,
)
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

FINISHED_TASK_STATES = frozenset(
    {
        TaskStateEnum.READY,
        TaskStateEnum.RESOLVED,
        TaskStateEnum.CANCELLED,
        TaskStateEnum.FAILED,
    }
)

# A task in one of these still has work ahead, so fabric it is waiting for is real demand.
UNFINISHED_TASK_STATES = frozenset(
    {
        TaskStateEnum.PENDING,
        TaskStateEnum.ASSIGNED,
        TaskStateEnum.WORKING,
        TaskStateEnum.STALLED,
    }
)

SETTLEABLE_REQUIREMENT_STATES = frozenset(
    {
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        ItemUpholsteryRequirementStateEnum.ORDERED,
    }
)


async def settle_finished_task_upholstery(
    session: AsyncSession,
    changed: Iterable[tuple[Task, TaskStateEnum]],
    *,
    workspace_id: str,
    actor_user_id: str | None,
    now: datetime,
    username: str | None = None,
) -> list[WorkspaceEvent]:
    """Cancel ``needs_ordering`` / ``ordered`` requirements of tasks that ended finished.

    ``changed`` is the same ``[(task, original_state), ...]`` list the caller passes to
    ``sync_task_stock_assignments``. Returns the post-commit events for the caller to
    dispatch; idempotent (a second call finds nothing to settle).
    """
    finished_task_ids = sorted(
        {
            task.client_id
            for task, _original_state in changed
            if task.state in FINISHED_TASK_STATES and not task.is_deleted
        }
    )
    if not finished_task_ids:
        return []

    cancelled = await settle_upholstery_for_task_ids(
        session,
        finished_task_ids,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        now=now,
        username=username,
    )
    return requirement_failed_events(workspace_id, cancelled)


async def settle_upholstery_for_task_ids(
    session: AsyncSession,
    task_ids: Iterable[str],
    *,
    workspace_id: str,
    actor_user_id: str | None,
    now: datetime,
    username: str | None = None,
    trigger: InventoryMovementTriggerEnum = InventoryMovementTriggerEnum.TASK_FINISHED,
    note: str | None = None,
) -> list[CancelledRequirement]:
    """Settle by task id; the caller guarantees these tasks are finished.

    Shared by the command-level hook above and the one-off cleanup script.
    """
    task_ids = sorted(set(task_ids))
    if not task_ids:
        return []

    # The caller's state write must be visible to the "other unfinished task" check below.
    await session.flush()

    task_items = (
        await session.execute(
            select(TaskItem.task_id, TaskItem.item_id)
            .where(
                TaskItem.workspace_id == workspace_id,
                TaskItem.task_id.in_(task_ids),
                TaskItem.removed_at.is_(None),
            )
            .order_by(TaskItem.task_id.asc(), TaskItem.item_id.asc())
        )
    ).all()
    if not task_items:
        return []

    item_ids = sorted({row.item_id for row in task_items})
    # An item still on another task with work ahead keeps its demand for that task.
    still_needed_item_ids = set(
        (
            await session.execute(
                select(TaskItem.item_id)
                .join(
                    Task,
                    (Task.client_id == TaskItem.task_id)
                    & (Task.workspace_id == workspace_id),
                )
                .where(
                    TaskItem.workspace_id == workspace_id,
                    TaskItem.item_id.in_(item_ids),
                    TaskItem.removed_at.is_(None),
                    TaskItem.task_id.not_in(task_ids),
                    Task.is_deleted.is_(False),
                    Task.state.in_(UNFINISHED_TASK_STATES),
                )
            )
        ).scalars()
    )

    # First finished task (by id) that links an item owns its ledger attribution.
    task_id_by_item: dict[str, str] = {}
    for row in task_items:
        if row.item_id not in still_needed_item_ids:
            task_id_by_item.setdefault(row.item_id, row.task_id)
    if not task_id_by_item:
        return []

    rows = (
        await session.execute(
            select(ItemUpholsteryRequirement, ItemUpholstery.item_id)
            .join(
                ItemUpholstery,
                ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id,
            )
            .where(
                ItemUpholstery.workspace_id == workspace_id,
                ItemUpholstery.item_id.in_(sorted(task_id_by_item)),
                ItemUpholstery.is_deleted.is_(False),
                ItemUpholsteryRequirement.workspace_id == workspace_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
                ItemUpholsteryRequirement.state.in_(SETTLEABLE_REQUIREMENT_STATES),
            )
            .order_by(ItemUpholsteryRequirement.client_id.asc())
            .with_for_update(of=ItemUpholsteryRequirement)
        )
    ).all()

    cancelled: list[CancelledRequirement] = []
    for requirement, item_id in rows:
        # Re-check after the lock: a concurrent command may have moved it on.
        if requirement.state not in SETTLEABLE_REQUIREMENT_STATES:
            continue
        movement = InventoryMovementContext.system(
            session,
            trigger,
            actor_id=actor_user_id,
            username=username,
            task_id=task_id_by_item[item_id],
            item_id=item_id,
            note=note,
        )
        cancelled.extend(
            await cancel_requirements_in_session(
                session=session,
                workspace_id=workspace_id,
                requirements=[requirement],
                actor_id=actor_user_id,
                now=now,
                movement=movement,
            )
        )
    return cancelled


def requirement_failed_events(
    workspace_id: str, cancelled: Iterable[CancelledRequirement]
) -> list[WorkspaceEvent]:
    """The same event ``delete_task`` sends for each item upholstery it cancels."""
    return [
        WorkspaceEvent(
            event_name="item:upholstery-requirement-state-changed",
            client_id=item_upholstery_id,
            workspace_id=workspace_id,
            extra={"new_state": ItemUpholsteryRequirementStateEnum.FAILED.value},
        )
        for item_upholstery_id in sorted({row.item_upholstery_id for row in cancelled})
    ]
