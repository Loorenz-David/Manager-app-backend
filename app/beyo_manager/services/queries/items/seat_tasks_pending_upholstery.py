from sqlalchemy import String, and_, distinct, func, or_, cast, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.tasks import _build_order_by

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_SEAT_MAJOR_CATEGORY = "seat"


def _seat_category_match():
    return func.lower(Item.item_major_category_snapshot) == _SEAT_MAJOR_CATEGORY


def _is_internal_selection_pending(upholstery: ItemUpholstery) -> bool:
    return (
        upholstery.source == ItemUpholsterySourceEnum.INTERNAL
        and upholstery.upholstery_id is None
    )


def _resolve_pending_upholstery(
    upholsteries: list[ItemUpholstery],
) -> tuple[str | None, str | None]:
    missing_selection_upholstery = next(
        (upholstery for upholstery in upholsteries if _is_internal_selection_pending(upholstery)),
        None,
    )
    if missing_selection_upholstery is not None:
        return missing_selection_upholstery.client_id, "missing_selection"

    if not upholsteries:
        return None, "missing_selection"

    missing_quantity_upholstery = next(
        (
            upholstery
            for upholstery in upholsteries
            if upholstery.amount_meters is None or upholstery.amount_meters == 0
        ),
        None,
    )
    if missing_quantity_upholstery is not None:
        return missing_quantity_upholstery.client_id, "missing_quantity"

    return (upholsteries[0].client_id if upholsteries else None), None


def _missing_selection_subquery(ctx: ServiceContext):
    return (
        select(TaskItem.task_id)
        .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
        .outerjoin(
            ItemUpholstery,
            and_(
                ItemUpholstery.item_id == Item.client_id,
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.is_deleted.is_(False),
            ),
        )
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            Item.is_deleted.is_(False),
            _seat_category_match(),
            or_(
                ItemUpholstery.client_id.is_(None),
                and_(
                    ItemUpholstery.source == ItemUpholsterySourceEnum.INTERNAL,
                    ItemUpholstery.upholstery_id.is_(None),
                ),
            ),
        )
        .distinct()
    )


def _missing_quantity_subquery(ctx: ServiceContext):
    return (
        select(TaskItem.task_id)
        .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
        .join(
            ItemUpholstery,
            and_(
                ItemUpholstery.item_id == Item.client_id,
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.is_deleted.is_(False),
            ),
        )
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            Item.is_deleted.is_(False),
            _seat_category_match(),
            or_(ItemUpholstery.amount_meters.is_(None), ItemUpholstery.amount_meters == 0),
        )
        .distinct()
    )


async def list_seat_tasks_pending_upholstery(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    missing_selection = bool(ctx.query_params.get("missing_selection", False))
    missing_quantity = bool(ctx.query_params.get("missing_quantity", False))

    stmt = (
        select(Task.client_id)
        .where(
            Task.workspace_id == ctx.workspace_id,
            Task.is_deleted.is_(False),
        )
    )

    missing_selection_subq = _missing_selection_subquery(ctx)
    missing_quantity_subq = _missing_quantity_subquery(ctx)

    if missing_selection and not missing_quantity:
        stmt = stmt.where(Task.client_id.in_(missing_selection_subq))
    elif missing_quantity and not missing_selection:
        stmt = stmt.where(Task.client_id.in_(missing_quantity_subq))
    else:
        stmt = stmt.where(
            or_(
                Task.client_id.in_(missing_selection_subq),
                Task.client_id.in_(missing_quantity_subq),
            )
        )

    if q:
        q_like = f"%{q}%"
        q_subq = (
            select(distinct(Task.client_id))
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
                ),
            )
        )
        stmt = stmt.where(Task.client_id.in_(q_subq))

    stmt = stmt.order_by(*_build_order_by(ctx.query_params.get("order_by")))
    stmt = stmt.offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    task_ids = [row[0] for row in result.all()]

    has_more = len(task_ids) > limit
    page_ids = task_ids[:limit]
    if not page_ids:
        return {
            "tasks_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        }

    tasks_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id.in_(page_ids),
        )
    )
    tasks = tasks_result.scalars().all()
    task_map = {task.client_id: task for task in tasks}

    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(page_ids),
            TaskItem.removed_at.is_(None),
        )
    )
    task_items = task_items_result.scalars().all()

    task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"}
    primary_item_ids = list(task_to_primary_item_id.values())

    items_map: dict[str, Item] = {}
    if primary_item_ids:
        items_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(primary_item_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_map = {item.client_id: item for item in items_result.scalars().all()}

    upholstery_reason_by_item_id: dict[str, str] = {}
    upholstery_id_by_item_id: dict[str, str | None] = {}
    if primary_item_ids:
        upholsteries_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id.in_(primary_item_ids),
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholsteries_by_item_id: dict[str, list[ItemUpholstery]] = {}
        for upholstery in upholsteries_result.scalars().all():
            upholsteries_by_item_id.setdefault(upholstery.item_id, []).append(upholstery)

        for item_id in primary_item_ids:
            upholsteries = upholsteries_by_item_id.get(item_id, [])
            upholstery_id, reason = _resolve_pending_upholstery(upholsteries)
            upholstery_id_by_item_id[item_id] = upholstery_id
            if reason is not None:
                upholstery_reason_by_item_id[item_id] = reason

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

    items_payload = []
    for task_id in page_ids:
        task = task_map.get(task_id)
        if task is None:
            continue
        primary_item_id = task_to_primary_item_id.get(task_id)
        primary_item = items_map.get(primary_item_id)
        items_payload.append(
            {
                "task": serialize_task(task),
                "primary_item": serialize_item(primary_item),
                "pending_upholstery_reason": upholstery_reason_by_item_id.get(primary_item_id),
                "item_upholstery_id": upholstery_id_by_item_id.get(primary_item_id),
                "item_images": item_images_map.get(primary_item_id, []),
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


async def get_seat_tasks_pending_upholstery_counts(ctx: ServiceContext) -> dict:
    missing_selection_subq = _missing_selection_subquery(ctx)
    missing_quantity_subq = _missing_quantity_subquery(ctx)

    sel_result = await ctx.session.execute(
        select(func.count(Task.client_id)).where(
            Task.workspace_id == ctx.workspace_id,
            Task.is_deleted.is_(False),
            Task.client_id.in_(missing_selection_subq),
        )
    )
    missing_selection_total = sel_result.scalar_one() or 0

    qty_result = await ctx.session.execute(
        select(func.count(Task.client_id)).where(
            Task.workspace_id == ctx.workspace_id,
            Task.is_deleted.is_(False),
            Task.client_id.in_(missing_quantity_subq),
        )
    )
    missing_quantity_total = qty_result.scalar_one() or 0

    return {
        "missing_selection_total": missing_selection_total,
        "missing_quantity_total": missing_quantity_total,
    }
