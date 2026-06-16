from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskPriorityEnum
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _build_order_by(order_by: str | None):
    priority_rank = case(
        (Task.priority == TaskPriorityEnum.URGENT, 4),
        (Task.priority == TaskPriorityEnum.HIGH, 3),
        (Task.priority == TaskPriorityEnum.NORMAL, 2),
        (Task.priority == TaskPriorityEnum.LOW, 1),
        else_=0,
    )

    field_map = {
        "ready_by_at": Task.ready_by_at,
        "created_at": Task.created_at,
        "scheduled_start_at": Task.scheduled_start_at,
        "scheduled_end_at": Task.scheduled_end_at,
        "priority": priority_rank,
    }

    if not order_by:
        return [Task.ready_by_at.asc().nulls_last(), priority_rank.desc(), Task.created_at.asc()]

    order_clauses = []
    for part in [p.strip() for p in order_by.split(",") if p.strip()]:
        if ":" in part:
            field, direction = part.split(":", 1)
        else:
            field, direction = part, "asc"
        column = field_map.get(field)
        if column is None:
            continue
        if direction.lower() == "desc":
            order_clauses.append(column.desc())
        elif field == "ready_by_at":
            order_clauses.append(column.asc().nulls_last())
        else:
            order_clauses.append(column.asc())

    return order_clauses or [Task.ready_by_at.asc().nulls_last(), priority_rank.desc(), Task.created_at.asc()]


async def get_upholstery_orders_count(ctx: ServiceContext) -> dict:
    states_list = _split_csv(ctx.query_params.get("states"))

    stmt = (
        select(UpholsteryOrder.state, func.count().label("count"))
        .where(
            UpholsteryOrder.workspace_id == ctx.workspace_id,
            UpholsteryOrder.is_deleted.is_(False),
        )
        .group_by(UpholsteryOrder.state)
    )
    if states_list:
        stmt = stmt.where(UpholsteryOrder.state.in_(states_list))

    rows = (await ctx.session.execute(stmt)).all()
    by_state = {row.state.value: row.count for row in rows}
    return {
        "total": sum(by_state.values()),
        "by_state": by_state,
    }


async def list_upholstery_orders(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    states_list = _split_csv(ctx.query_params.get("states"))

    stmt = (
        select(UpholsteryOrder, Upholstery)
        .select_from(UpholsteryOrder)
        .outerjoin(
            UpholsteryInventory,
            and_(
                UpholsteryInventory.client_id == UpholsteryOrder.upholstery_inventory_id,
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.is_deleted.is_(False),
            ),
        )
        .outerjoin(
            Upholstery,
            and_(
                Upholstery.client_id == UpholsteryInventory.upholstery_id,
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.is_deleted.is_(False),
            ),
        )
        .where(
            UpholsteryOrder.workspace_id == ctx.workspace_id,
            UpholsteryOrder.is_deleted.is_(False),
        )
    )

    if states_list:
        stmt = stmt.where(UpholsteryOrder.state.in_(states_list))

    if q:
        q_like = f"%{q}%"
        q_subq = (
            select(UpholsteryOrder.client_id)
            .distinct()
            .select_from(UpholsteryOrder)
            .outerjoin(
                UpholsteryInventory,
                and_(
                    UpholsteryInventory.client_id == UpholsteryOrder.upholstery_inventory_id,
                    UpholsteryInventory.workspace_id == ctx.workspace_id,
                    UpholsteryInventory.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                Upholstery,
                and_(
                    Upholstery.client_id == UpholsteryInventory.upholstery_id,
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                ItemUpholsteryRequirement,
                and_(
                    ItemUpholsteryRequirement.upholstery_inventory_id == UpholsteryOrder.upholstery_inventory_id,
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                ItemUpholstery,
                and_(
                    ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                Item,
                and_(
                    Item.client_id == ItemUpholstery.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
            )
            .outerjoin(
                TaskItem,
                and_(
                    TaskItem.item_id == Item.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                ),
            )
            .outerjoin(
                Task,
                and_(
                    Task.client_id == TaskItem.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .where(
                UpholsteryOrder.workspace_id == ctx.workspace_id,
                UpholsteryOrder.is_deleted.is_(False),
                or_(
                    Upholstery.name.ilike(q_like),
                    Upholstery.code.ilike(q_like),
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
                ),
            )
        )
        stmt = stmt.where(UpholsteryOrder.client_id.in_(q_subq))

    stmt = stmt.order_by(UpholsteryOrder.created_at.desc()).offset(offset).limit(limit + 1)

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "orders_pagination": {
            "items": [
                {
                    "client_id": order.client_id,
                    "upholstery_id": upholstery.client_id if upholstery else None,
                    "upholstery_name": upholstery.name if upholstery else None,
                    "upholstery_code": upholstery.code if upholstery else None,
                    "upholstery_image_url": upholstery.image_url if upholstery else None,
                    "order_amount_meters": float(order.order_amount_meters),
                    "expected_receive_at": order.expected_receive_at.isoformat() if order.expected_receive_at else None,
                    "received_at": order.received_at.isoformat() if order.received_at else None,
                    "state": order.state.value,
                    "supplier_id": order.supplier_id,
                }
                for order, upholstery in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def list_upholstery_order_items(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    upholstery_ids_list = _split_csv(ctx.query_params.get("upholstery_ids"))
    requirement_states_list = _split_csv(ctx.query_params.get("requirement_states"))

    if not upholstery_ids_list:
        return {
            "tasks_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": False,
            }
        }

    stmt = select(Task.client_id).where(
        Task.workspace_id == ctx.workspace_id,
        Task.is_deleted.is_(False),
    )

    upholstery_subq = (
        select(TaskItem.task_id)
        .join(
            Item,
            and_(
                Item.client_id == TaskItem.item_id,
                Item.workspace_id == ctx.workspace_id,
                Item.is_deleted.is_(False),
            ),
        )
        .join(
            ItemUpholstery,
            and_(
                ItemUpholstery.item_id == Item.client_id,
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.is_deleted.is_(False),
                ItemUpholstery.upholstery_id.in_(upholstery_ids_list),
            ),
        )
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.removed_at.is_(None),
        )
        .distinct()
    )
    stmt = stmt.where(Task.client_id.in_(upholstery_subq))

    if requirement_states_list:
        requirement_subq = (
            select(TaskItem.task_id)
            .join(
                Item,
                and_(
                    Item.client_id == TaskItem.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
            )
            .join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                    ItemUpholstery.upholstery_id.in_(upholstery_ids_list),
                ),
            )
            .join(
                ItemUpholsteryRequirement,
                and_(
                    ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                    ItemUpholsteryRequirement.state.in_(requirement_states_list),
                ),
            )
            .where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.removed_at.is_(None),
            )
            .distinct()
        )
        stmt = stmt.where(Task.client_id.in_(requirement_subq))

    if q:
        q_like = f"%{q}%"
        q_subq = (
            select(Task.client_id)
            .distinct()
            .select_from(Task)
            .join(
                TaskItem,
                and_(
                    TaskItem.task_id == Task.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                ),
                isouter=True,
            )
            .join(
                Item,
                and_(
                    Item.client_id == TaskItem.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .join(
                Upholstery,
                and_(
                    Upholstery.client_id == ItemUpholstery.upholstery_id,
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .where(
                Task.workspace_id == ctx.workspace_id,
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
                    Upholstery.name.ilike(q_like),
                    Upholstery.code.ilike(q_like),
                ),
            )
        )
        stmt = stmt.where(Task.client_id.in_(q_subq))

    stmt = stmt.order_by(*_build_order_by(None)).offset(offset).limit(limit + 1)

    page_ids = [row[0] for row in (await ctx.session.execute(stmt)).all()]
    has_more = len(page_ids) > limit
    page_ids = page_ids[:limit]
    if not page_ids:
        return {
            "tasks_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        }

    tasks = (
        await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id.in_(page_ids),
            )
        )
    ).scalars().all()
    task_map = {task.client_id: task for task in tasks}

    task_items = (
        await ctx.session.execute(
            select(TaskItem).where(
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.task_id.in_(page_ids),
                TaskItem.removed_at.is_(None),
            )
        )
    ).scalars().all()

    primary_item_ids = [ti.item_id for ti in task_items if ti.role.value == "primary"]
    items_map = {}
    if primary_item_ids:
        items = (
            await ctx.session.execute(
                select(Item).where(
                    Item.workspace_id == ctx.workspace_id,
                    Item.client_id.in_(primary_item_ids),
                    Item.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        items_map = {item.client_id: item for item in items}

    task_to_primary_item_id = {
        ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"
    }

    item_images_map: dict[str, list] = {}
    if primary_item_ids:
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id.in_(primary_item_ids),
                ),
            )
            .options(selectinload(Image.last_event))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, item_id in img_result.all():
            image_list = item_images_map.setdefault(item_id, [])
            image_list.append(serialize_image(image) if not image_list else serialize_image_light(image))

    iup_map: dict[str, ItemUpholstery] = {}
    if primary_item_ids:
        upholsteries = (
            await ctx.session.execute(
                select(ItemUpholstery).where(
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.item_id.in_(primary_item_ids),
                    ItemUpholstery.upholstery_id.in_(upholstery_ids_list),
                    ItemUpholstery.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        for iup in upholsteries:
            iup_map.setdefault(iup.item_id, iup)

    items_payload = []
    for task_id in page_ids:
        task = task_map.get(task_id)
        if task is None:
            continue
        primary_item_id = task_to_primary_item_id.get(task_id)
        primary_item = items_map.get(primary_item_id)
        iup = iup_map.get(primary_item_id) if primary_item_id else None
        items_payload.append(
            {
                "task": serialize_task(task),
                "primary_item": serialize_item(primary_item),
                "item_images": item_images_map.get(primary_item_id, []),
                "item_upholstery": {
                    "client_id": iup.client_id,
                    "amount_meters": float(iup.amount_meters) if iup.amount_meters is not None else None,
                }
                if iup is not None
                else None,
            }
        )

    return {
        "tasks_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
