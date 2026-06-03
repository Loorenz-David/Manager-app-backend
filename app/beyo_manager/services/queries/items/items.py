"""QUERY-1: List Items | QUERY-2: Get Item by ID."""

from sqlalchemy import and_, exists, func, or_, select

from beyo_manager.domain.items.serializers import serialize_item_detail, serialize_item_list
from beyo_manager.domain.tasks.serializers import serialize_requirement, serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_items(ctx: ServiceContext) -> dict:
    """QUERY-1: List items with optional q filter and issue_count per item."""
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(Item).where(
        Item.workspace_id == ctx.workspace_id,
        Item.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Item.article_number.ilike(pattern),
                Item.sku.ilike(pattern),
                Item.item_position.ilike(pattern),
                Item.designer.ilike(pattern),
                exists(
                    select(1).where(
                        ItemIssue.workspace_id == ctx.workspace_id,
                        ItemIssue.item_id == Item.client_id,
                        ItemIssue.is_deleted.is_(False),
                        ItemIssue.issue_type_snapshot.ilike(pattern),
                    )
                ),
                exists(
                    select(1).where(
                        ItemUpholstery.workspace_id == ctx.workspace_id,
                        ItemUpholstery.item_id == Item.client_id,
                        ItemUpholstery.is_deleted.is_(False),
                        ItemUpholstery.name.ilike(pattern),
                    )
                ),
                exists(
                    select(1).where(
                        ItemUpholstery.workspace_id == ctx.workspace_id,
                        ItemUpholstery.item_id == Item.client_id,
                        ItemUpholstery.is_deleted.is_(False),
                        ItemUpholstery.code.ilike(pattern),
                    )
                ),
            )
        )

    stmt = stmt.order_by(Item.created_at.desc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    issue_counts: dict[str, int] = {}
    if page:
        item_ids = [item.client_id for item in page]
        count_result = await ctx.session.execute(
            select(ItemIssue.item_id, func.count(ItemIssue.client_id).label("cnt"))
            .where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.item_id.in_(item_ids),
                ItemIssue.is_deleted.is_(False),
            )
            .group_by(ItemIssue.item_id)
        )
        issue_counts = {row.item_id: row.cnt for row in count_result}

    return {
        "items_pagination": {
            "items": [serialize_item_list(item, issue_counts.get(item.client_id, 0)) for item in page],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_item(ctx: ServiceContext) -> dict:
    """QUERY-2: Get Item by ID with issues, upholstery, and requirements."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == client_id,
            Item.is_deleted.is_(False),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFound("Item not found.")

    issues_result = await ctx.session.execute(
        select(ItemIssue)
        .where(
            ItemIssue.workspace_id == ctx.workspace_id,
            ItemIssue.item_id == item.client_id,
            ItemIssue.is_deleted.is_(False),
        )
        .order_by(ItemIssue.created_at.asc())
    )
    issues = issues_result.scalars().all()

    iup_result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id == item.client_id,
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    upholstery = iup_result.scalar_one_or_none()

    requirements: list[ItemUpholsteryRequirement] = []
    if upholstery is not None:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement)
            .where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == upholstery.client_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
            .order_by(ItemUpholsteryRequirement.created_at.asc())
        )
        requirements = req_result.scalars().all()

    return {"item": serialize_item_detail(item, issues, upholstery, requirements)}


async def list_item_upholstery_by_item_id(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    item_result = await ctx.session.execute(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == client_id,
            Item.is_deleted.is_(False),
        )
    )
    item = item_result.scalar_one_or_none()
    if item is None:
        raise NotFound("Item not found.")

    upholstery_result = await ctx.session.execute(
        select(ItemUpholstery, Upholstery.image_url, Upholstery.name, Upholstery.code)
        .select_from(ItemUpholstery)
        .join(
            Upholstery,
            and_(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.client_id == ItemUpholstery.upholstery_id,
                Upholstery.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id == item.client_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .order_by(ItemUpholstery.created_at.asc())
    )
    upholstery_rows = upholstery_result.all()
    item_upholstery = [row[0] for row in upholstery_rows]
    image_url_by_item_upholstery_id = {
        row.client_id: image_url
        for row, image_url, _, _ in upholstery_rows
    }
    upholstery_name_by_item_upholstery_id = {
        row.client_id: upholstery_name
        for row, _, upholstery_name, _ in upholstery_rows
    }
    upholstery_code_by_item_upholstery_id = {
        row.client_id: upholstery_code
        for row, _, _, upholstery_code in upholstery_rows
    }

    requirements: list[ItemUpholsteryRequirement] = []
    if item_upholstery:
        item_upholstery_ids = [row.client_id for row in item_upholstery]
        requirements_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement)
            .where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id.in_(item_upholstery_ids),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
            .order_by(ItemUpholsteryRequirement.created_at.asc())
        )
        requirements = requirements_result.scalars().all()

    return {
        "item_upholstery": [
            serialize_upholstery(
                row,
                image_url=image_url_by_item_upholstery_id.get(row.client_id),
                upholstery_name=upholstery_name_by_item_upholstery_id.get(row.client_id),
                upholstery_code=upholstery_code_by_item_upholstery_id.get(row.client_id),
            )
            for row in item_upholstery
        ],
        "requirements": [serialize_requirement(row) for row in requirements],
    }
