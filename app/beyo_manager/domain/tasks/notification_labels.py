from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem


async def resolve_item_label_for_task(session: AsyncSession, task_id: str) -> str | None:
    """Return the primary active item's article number or sku for a task."""
    result = await session.execute(
        select(Item.article_number, Item.sku)
        .join(TaskItem, Item.client_id == TaskItem.item_id)
        .where(
            TaskItem.task_id == task_id,
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskItem.removed_at.is_(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return row.article_number or row.sku


async def resolve_scalar_and_item_label(
    session: AsyncSession,
    task_id: str,
) -> tuple[int | None, str | None]:
    """Return task scalar id and primary active item label in one query."""
    result = await session.execute(
        select(Task.task_scalar_id, Item.article_number, Item.sku)
        .outerjoin(
            TaskItem,
            (TaskItem.task_id == Task.client_id)
            & (TaskItem.role == TaskItemRoleEnum.PRIMARY)
            & TaskItem.removed_at.is_(None),
        )
        .outerjoin(Item, Item.client_id == TaskItem.item_id)
        .where(Task.client_id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        return None, None
    return row.task_scalar_id, (row.article_number or row.sku)
