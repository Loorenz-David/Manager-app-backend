from datetime import datetime

from sqlalchemy import String, and_, case, cast, distinct, func, or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
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
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_NEEDS_ORDERING = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING


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


async def get_upholstery_order_needs_count(ctx: ServiceContext) -> dict:
    result = await ctx.session.execute(
        select(
            func.count().label("needs_ordering_count"),
            func.count(distinct(ItemUpholsteryRequirement.upholstery_inventory_id)).label("upholstery_count"),
        ).where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
            ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
        )
    )
    row = result.one()
    return {
        "needs_ordering_count": row.needs_ordering_count,
        "upholstery_count": row.upholstery_count,
    }


async def list_upholstery_order_needs(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    needs_agg = (
        select(
            Upholstery.client_id.label("client_id"),
            Upholstery.name.label("name"),
            Upholstery.code.label("code"),
            Upholstery.image_url.label("image_url"),
            func.count(distinct(ItemUpholsteryRequirement.client_id)).label("item_count"),
            func.coalesce(func.sum(ItemUpholsteryRequirement.amount_meters), 0).label("total_amount_meters"),
        )
        .select_from(Upholstery)
        .join(
            UpholsteryInventory,
            and_(
                UpholsteryInventory.upholstery_id == Upholstery.client_id,
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.is_deleted.is_(False),
            ),
        )
        .join(
            ItemUpholsteryRequirement,
            and_(
                ItemUpholsteryRequirement.upholstery_inventory_id == UpholsteryInventory.client_id,
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
                ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
            ),
        )
        .where(
            Upholstery.workspace_id == ctx.workspace_id,
            Upholstery.is_deleted.is_(False),
        )
        .group_by(
            Upholstery.client_id,
            Upholstery.name,
            Upholstery.code,
            Upholstery.image_url,
        )
        .subquery()
    )

    stmt = (
        select(
            needs_agg.c.client_id,
            needs_agg.c.name,
            needs_agg.c.code,
            needs_agg.c.image_url,
            needs_agg.c.item_count,
            needs_agg.c.total_amount_meters,
        )
        .select_from(needs_agg)
        .outerjoin(
            ItemUpholstery,
            and_(
                ItemUpholstery.upholstery_id == needs_agg.c.client_id,
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
    )

    if q:
        q_like = f"%{q}%"
        q_subq = (
            select(Upholstery.client_id)
            .select_from(Upholstery)
            .join(
                UpholsteryInventory,
                and_(
                    UpholsteryInventory.upholstery_id == Upholstery.client_id,
                    UpholsteryInventory.workspace_id == ctx.workspace_id,
                    UpholsteryInventory.is_deleted.is_(False),
                ),
            )
            .join(
                ItemUpholsteryRequirement,
                and_(
                    ItemUpholsteryRequirement.upholstery_inventory_id == UpholsteryInventory.client_id,
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                    ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
                ),
            )
            .join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .join(
                Item,
                and_(
                    Item.client_id == ItemUpholstery.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .join(
                TaskItem,
                and_(
                    TaskItem.item_id == Item.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                ),
                isouter=True,
            )
            .join(
                Task,
                and_(
                    Task.client_id == TaskItem.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.is_deleted.is_(False),
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
            .distinct()
        )
        stmt = stmt.where(needs_agg.c.client_id.in_(q_subq))

    stmt = (
        stmt.group_by(
            needs_agg.c.client_id,
            needs_agg.c.name,
            needs_agg.c.code,
            needs_agg.c.image_url,
            needs_agg.c.item_count,
            needs_agg.c.total_amount_meters,
        )
        .order_by(func.min(Task.ready_by_at).asc().nulls_last(), needs_agg.c.name.asc())
        .offset(offset)
        .limit(limit + 1)
    )

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]
    page_upholstery_ids = [row.client_id for row in page]

    due_date_map: dict[str, datetime | None] = {}
    if page_upholstery_ids:
        ranked_cte = (
            select(
                Upholstery.client_id.label("upholstery_id"),
                Task.ready_by_at.label("ready_by_at"),
                func.row_number().over(
                    partition_by=Upholstery.client_id,
                    order_by=[
                        case((Task.ready_by_at.is_(None), 1), else_=0).asc(),
                        func.abs(
                            func.extract("epoch", Task.ready_by_at)
                            - func.extract("epoch", func.now())
                        ).asc(),
                        Task.created_at.asc(),
                    ],
                ).label("rn"),
            )
            .select_from(Upholstery)
            .join(
                UpholsteryInventory,
                and_(
                    UpholsteryInventory.upholstery_id == Upholstery.client_id,
                    UpholsteryInventory.workspace_id == ctx.workspace_id,
                    UpholsteryInventory.is_deleted.is_(False),
                ),
            )
            .join(
                ItemUpholsteryRequirement,
                and_(
                    ItemUpholsteryRequirement.upholstery_inventory_id == UpholsteryInventory.client_id,
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                    ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
                ),
            )
            .join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
            )
            .join(
                Item,
                and_(
                    Item.client_id == ItemUpholstery.item_id,
                    Item.workspace_id == ctx.workspace_id,
                    Item.is_deleted.is_(False),
                ),
            )
            .join(
                TaskItem,
                and_(
                    TaskItem.item_id == Item.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                ),
            )
            .join(
                Task,
                and_(
                    Task.client_id == TaskItem.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .where(Upholstery.client_id.in_(page_upholstery_ids))
            .cte("ranked")
        )

        due_date_rows = await ctx.session.execute(
            select(ranked_cte.c.upholstery_id, ranked_cte.c.ready_by_at).where(ranked_cte.c.rn == 1)
        )
        due_date_map = {
            row.upholstery_id: row.ready_by_at for row in due_date_rows
        }

    return {
        "upholstery_needs_pagination": {
            "items": [
                {
                    "upholstery_id": row.client_id,
                    "upholstery_name": row.name,
                    "upholstery_code": row.code,
                    "upholstery_image_url": row.image_url,
                    "item_count": row.item_count,
                    "total_amount_meters": float(row.total_amount_meters or 0),
                    "earliest_due_date": (
                        due_date_map[row.client_id].date().isoformat()
                        if due_date_map.get(row.client_id) is not None
                        else None
                    ),
                }
                for row in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_upholstery_order_need_items(ctx: ServiceContext) -> dict:
    upholstery_id = ctx.incoming_data["upholstery_id"]
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

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
                ItemUpholstery.upholstery_id == upholstery_id,
            ),
        )
        .join(
            ItemUpholsteryRequirement,
            and_(
                ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
                ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
            ),
        )
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.removed_at.is_(None),
        )
        .distinct()
    )
    stmt = stmt.where(Task.client_id.in_(upholstery_subq))

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
                    ItemUpholstery.upholstery_id == upholstery_id,
                    ItemUpholstery.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        iup_map = {iup.item_id: iup for iup in upholsteries}

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
