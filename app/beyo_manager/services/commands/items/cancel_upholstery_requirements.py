"""Shared cancellation helpers for unfinished upholstery requirements.

The helpers in this module run inside the caller's transaction.  They mutate
database state and return a description of the requirements they cancelled,
but deliberately leave post-commit event dispatch to the owning command.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    adjust_need,
    rollback_in_use_to_stored,
)


ACTIVE_TASK_STATES = frozenset(
    {
        TaskStateEnum.PENDING,
        TaskStateEnum.ASSIGNED,
        TaskStateEnum.WORKING,
        TaskStateEnum.STALLED,
        TaskStateEnum.READY,
    }
)

DEMAND_REQUIREMENT_STATES = frozenset(
    {
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        ItemUpholsteryRequirementStateEnum.ORDERED,
    }
)

UNFINISHED_REQUIREMENT_STATES = frozenset(
    {
        ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
        *DEMAND_REQUIREMENT_STATES,
        ItemUpholsteryRequirementStateEnum.IN_USE,
    }
)


@dataclass(frozen=True)
class CancelledRequirement:
    requirement_id: str
    item_upholstery_id: str
    upholstery_inventory_id: str | None
    previous_state: ItemUpholsteryRequirementStateEnum
    amount_meters: Decimal


async def cancel_requirements_in_session(
    *,
    session: AsyncSession,
    workspace_id: str,
    requirements: Iterable[ItemUpholsteryRequirement],
    actor_id: str | None,
    now: datetime | None = None,
) -> list[CancelledRequirement]:
    """Fail unfinished requirements and reverse their inventory projections."""

    failed_at = now or datetime.now(timezone.utc)
    cancelled: list[CancelledRequirement] = []

    for requirement in sorted(requirements, key=lambda row: row.client_id):
        previous_state = requirement.state
        if previous_state not in UNFINISHED_REQUIREMENT_STATES:
            continue

        amount_meters = requirement.amount_meters or Decimal("0")
        inventory_id = requirement.upholstery_inventory_id

        if inventory_id is not None and amount_meters > Decimal("0"):
            if previous_state in DEMAND_REQUIREMENT_STATES:
                await adjust_need(
                    session=session,
                    workspace_id=workspace_id,
                    upholstery_inventory_id=inventory_id,
                    delta=-amount_meters,
                )
            elif previous_state == ItemUpholsteryRequirementStateEnum.IN_USE:
                await rollback_in_use_to_stored(
                    session=session,
                    workspace_id=workspace_id,
                    upholstery_inventory_id=inventory_id,
                    quantity=amount_meters,
                )

        requirement.state = ItemUpholsteryRequirementStateEnum.FAILED
        requirement.failed_at = failed_at
        requirement.updated_at = failed_at
        requirement.updated_by_id = actor_id
        cancelled.append(
            CancelledRequirement(
                requirement_id=requirement.client_id,
                item_upholstery_id=requirement.item_upholstery_id,
                upholstery_inventory_id=inventory_id,
                previous_state=previous_state,
                amount_meters=amount_meters,
            )
        )

    if cancelled:
        await session.flush()
    return cancelled


async def cancel_unfinished_item_requirements_in_session(
    *,
    session: AsyncSession,
    workspace_id: str,
    item_ids: Iterable[str],
    actor_id: str | None,
    now: datetime | None = None,
) -> list[CancelledRequirement]:
    """Load and cancel every unfinished requirement for active item contexts."""

    unique_item_ids = sorted(set(item_ids))
    if not unique_item_ids:
        return []

    requirements = await load_unfinished_item_requirements(
        session=session,
        workspace_id=workspace_id,
        item_ids=unique_item_ids,
        lock_rows=True,
    )

    return await cancel_requirements_in_session(
        session=session,
        workspace_id=workspace_id,
        requirements=requirements,
        actor_id=actor_id,
        now=now,
    )


async def load_unfinished_item_requirements(
    *,
    session: AsyncSession,
    workspace_id: str,
    item_ids: Iterable[str],
    lock_rows: bool,
) -> list[ItemUpholsteryRequirement]:
    """Load unfinished requirements for active item upholstery contexts."""

    unique_item_ids = sorted(set(item_ids))
    if not unique_item_ids:
        return []

    statement = (
        select(ItemUpholsteryRequirement)
        .join(
            ItemUpholstery,
            ItemUpholstery.client_id
            == ItemUpholsteryRequirement.item_upholstery_id,
        )
        .where(
            ItemUpholstery.workspace_id == workspace_id,
            ItemUpholstery.item_id.in_(unique_item_ids),
            ItemUpholstery.is_deleted.is_(False),
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
            ItemUpholsteryRequirement.state.in_(UNFINISHED_REQUIREMENT_STATES),
        )
        .order_by(ItemUpholsteryRequirement.client_id.asc())
    )
    if lock_rows:
        statement = statement.with_for_update(of=ItemUpholsteryRequirement)
    return (await session.execute(statement)).scalars().all()


async def lock_and_filter_items_without_active_tasks(
    *,
    session: AsyncSession,
    workspace_id: str,
    item_ids: Iterable[str],
    excluding_task_id: str | None = None,
    lock_rows: bool = True,
) -> list[str]:
    """Return items with no other active task, under deterministic row locks.

    Items are locked first so a concurrent TaskItem insert referencing one of
    them cannot pass its foreign-key check until this transaction completes.
    Existing TaskItem and Task rows are then locked in stable ID order.
    """

    unique_item_ids = sorted(set(item_ids))
    if not unique_item_ids:
        return []

    if lock_rows:
        await session.execute(
            select(Item)
            .where(
                Item.workspace_id == workspace_id,
                Item.client_id.in_(unique_item_ids),
            )
            .order_by(Item.client_id.asc())
            .with_for_update()
        )

    task_item_statement = (
        select(TaskItem)
        .where(
            TaskItem.workspace_id == workspace_id,
            TaskItem.item_id.in_(unique_item_ids),
            TaskItem.removed_at.is_(None),
        )
        .order_by(TaskItem.client_id.asc())
    )
    if lock_rows:
        task_item_statement = task_item_statement.with_for_update()
    task_items = (
        await session.execute(task_item_statement)
    ).scalars().all()

    linked_task_ids = sorted({task_item.task_id for task_item in task_items})
    tasks_by_id: dict[str, Task] = {}
    if linked_task_ids:
        task_statement = (
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.client_id.in_(linked_task_ids),
            )
            .order_by(Task.client_id.asc())
            .execution_options(populate_existing=True)
        )
        if lock_rows:
            task_statement = task_statement.with_for_update()
        tasks = (await session.execute(task_statement)).scalars().all()
        tasks_by_id = {task.client_id: task for task in tasks}

    item_ids_with_active_tasks = {
        task_item.item_id
        for task_item in task_items
        if task_item.task_id != excluding_task_id
        and (task := tasks_by_id.get(task_item.task_id)) is not None
        and not task.is_deleted
        and task.state in ACTIVE_TASK_STATES
    }
    items_still_linked_to_excluded_task = (
        {
            task_item.item_id
            for task_item in task_items
            if task_item.task_id == excluding_task_id
        }
        if excluding_task_id is not None
        else set(unique_item_ids)
    )
    return [
        item_id
        for item_id in unique_item_ids
        if item_id in items_still_linked_to_excluded_task
        and item_id not in item_ids_with_active_tasks
    ]
