from sqlalchemy import and_, func, select

from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


def build_primary_item_upholstery_group_columns(workspace_id: str, task_id_column):
    """Scalar subqueries resolving a task to one upholstery group:
    (key, image_url, master upholstery client_id).

    An item can carry several upholsteries but a row can only live in one group
    of a paginated list, so the alphabetically-first key picks a deterministic
    representative; both columns come from that same representative row. The key
    falls back through item-level then master-level name/code, mirroring
    serialize_upholstery. NULL key means the primary item has no upholstery;
    callers should sort it last as the "no upholstery" bucket.
    """
    key_expr = func.coalesce(
        ItemUpholstery.name, Upholstery.name, ItemUpholstery.code, Upholstery.code
    )

    def _representative(selected):
        return (
            select(selected)
            .select_from(TaskItem)
            .join(
                Item,
                and_(
                    Item.client_id == TaskItem.item_id,
                    Item.workspace_id == workspace_id,
                    Item.is_deleted.is_(False),
                ),
            )
            .join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
            )
            .join(
                Upholstery,
                and_(
                    Upholstery.client_id == ItemUpholstery.upholstery_id,
                    Upholstery.workspace_id == workspace_id,
                    Upholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .where(
                TaskItem.task_id == task_id_column,
                TaskItem.workspace_id == workspace_id,
                TaskItem.removed_at.is_(None),
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
            )
            .order_by(key_expr.asc().nullslast(), ItemUpholstery.client_id.asc())
            .limit(1)
            .scalar_subquery()
        )

    return (
        _representative(key_expr),
        _representative(Upholstery.image_url),
        _representative(Upholstery.client_id),
    )


def _meters(value) -> str | None:
    return str(value) if value is not None else None


async def load_upholstery_group_inventories(
    session, workspace_id: str, upholstery_ids: list[str]
) -> dict[str, dict]:
    """Batch-load the current inventory amounts for a page's group upholsteries.

    Returns {upholstery_id: payload}, meters serialized as strings to match
    serialize_upholstery_inventory.
    """
    if not upholstery_ids:
        return {}
    result = await session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.upholstery_id.in_(upholstery_ids),
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    return {
        inv.upholstery_id: {
            "client_id": inv.client_id,
            "upholstery_id": inv.upholstery_id,
            "inventory_condition": inv.inventory_condition.value,
            "current_stored_amount_meters": _meters(inv.current_stored_amount_meters),
            "current_amount_in_use_meters": _meters(inv.current_amount_in_use_meters),
            "current_amount_in_need_meters": _meters(inv.current_amount_in_need_meters),
            "current_amount_ordered_meters": _meters(inv.current_amount_ordered_meters),
        }
        for inv in result.scalars().all()
    }
