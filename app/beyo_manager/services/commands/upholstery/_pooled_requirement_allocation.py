from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation


PoolMode = Literal["ordered", "stored"]


def calculate_pooled_requirement_pool(
    inventory: UpholsteryInventory,
    candidates: list[ItemUpholsteryRequirement],
    mode: PoolMode,
) -> Decimal:
    total_candidate_need = sum((req.amount_meters or Decimal("0")) for req in candidates)
    in_need_excluding_candidates = (inventory.current_amount_in_need_meters or Decimal("0")) - total_candidate_need
    stored = inventory.current_stored_amount_meters or Decimal("0")
    ordered = inventory.current_amount_ordered_meters or Decimal("0")

    if mode == "ordered":
        return stored + ordered - in_need_excluding_candidates
    return stored - in_need_excluding_candidates


def allocate_pooled_requirements(
    *,
    inventory: UpholsteryInventory,
    ordered_candidates: list[ItemUpholsteryRequirement],
    target_state: ItemUpholsteryRequirementStateEnum,
    mode: PoolMode,
    actor_id: str,
    timestamp_field: str | None,
) -> list[str]:
    running_pool = calculate_pooled_requirement_pool(
        inventory=inventory,
        candidates=ordered_candidates,
        mode=mode,
    )
    result = run_skip_and_continue_allocation(
        candidates=ordered_candidates,
        running_pool=running_pool,
        target_state=target_state,
        timestamp_field=timestamp_field,
    )

    resolved_set = set(result["resolved"])
    for req in ordered_candidates:
        if req.item_upholstery_id in resolved_set:
            req.updated_by_id = actor_id

    return result["resolved"]


async def fetch_earliest_ready_by_at(
    session: AsyncSession,
    workspace_id: str,
    item_upholstery_ids: list[str],
) -> dict[str, datetime | None]:
    if not item_upholstery_ids:
        return {}

    stmt = (
        select(
            ItemUpholstery.client_id.label("item_upholstery_id"),
            func.min(Task.ready_by_at).label("earliest_ready_by_at"),
        )
        .select_from(ItemUpholstery)
        .join(
            Item,
            and_(
                Item.client_id == ItemUpholstery.item_id,
                Item.workspace_id == workspace_id,
                Item.is_deleted.is_(False),
            ),
        )
        .join(
            TaskItem,
            and_(
                TaskItem.item_id == Item.client_id,
                TaskItem.workspace_id == workspace_id,
                TaskItem.removed_at.is_(None),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskItem.task_id,
                Task.workspace_id == workspace_id,
                Task.is_deleted.is_(False),
                Task.ready_by_at.is_not(None),
            ),
        )
        .where(
            ItemUpholstery.client_id.in_(item_upholstery_ids),
            ItemUpholstery.workspace_id == workspace_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .group_by(ItemUpholstery.client_id)
    )
    rows = (await session.execute(stmt)).all()
    return {row.item_upholstery_id: row.earliest_ready_by_at for row in rows}
