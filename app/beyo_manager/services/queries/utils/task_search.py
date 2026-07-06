from sqlalchemy import String, and_, cast, distinct, or_, select

from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem


def build_task_q_subquery(workspace_id: str, q: str):
    q_like = f"%{q}%"
    return (
        select(distinct(Task.client_id))
        .select_from(Task)
        .join(
            TaskItem,
            and_(
                TaskItem.task_id == Task.client_id,
                TaskItem.workspace_id == workspace_id,
                TaskItem.removed_at.is_(None),
            ),
            isouter=True,
        )
        .join(
            Item,
            and_(
                Item.client_id == TaskItem.item_id,
                Item.workspace_id == workspace_id,
                Item.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .join(
            ItemUpholstery,
            and_(
                ItemUpholstery.item_id == Item.client_id,
                ItemUpholstery.workspace_id == workspace_id,
                ItemUpholstery.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .where(
            Task.workspace_id == workspace_id,
            or_(
                Task.title.ilike(q_like),
                cast(Task.additional_details, String).ilike(q_like),
                Task.primary_phone_number.ilike(q_like),
                Task.secondary_phone_number.ilike(q_like),
                Task.primary_email.ilike(q_like),
                Task.secondary_email.ilike(q_like),
                Item.article_number.ilike(q_like),
                Item.sku.ilike(q_like),
                Item.designer.ilike(q_like),
                Item.item_position.ilike(q_like),
                Item.item_category_snapshot.ilike(q_like),
                Item.item_major_category_snapshot.ilike(q_like),
                ItemUpholstery.name.ilike(q_like),
                ItemUpholstery.code.ilike(q_like),
            ),
        )
    )
