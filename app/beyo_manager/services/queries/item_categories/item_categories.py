"""QUERY-1: List ItemCategories | QUERY-2: Get ItemCategory by ID."""

from sqlalchemy import select

from beyo_manager.domain.items.serializers import serialize_item_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_item_categories(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(ItemCategory).where(
        ItemCategory.workspace_id == ctx.workspace_id,
        ItemCategory.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(ItemCategory.name.ilike(pattern))

    stmt = stmt.order_by(ItemCategory.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "item_categories": [serialize_item_category(cat) for cat in page],
        "item_categories_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_item_category(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(ItemCategory).where(
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.client_id == client_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFound("Item category not found.")

    return {"item_category": serialize_item_category(category)}
