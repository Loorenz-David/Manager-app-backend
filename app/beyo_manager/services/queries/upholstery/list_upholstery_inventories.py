"""Query for listing upholstery inventories with pagination."""

from sqlalchemy import desc, select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholstery_inventories(ctx: ServiceContext) -> dict:
    """List upholstery inventories with offset pagination."""
    limit = int(ctx.query_params.get("limit", _DEFAULT_LIMIT))
    offset = int(ctx.query_params.get("offset", 0))

    # Guard: limit constraints
    if limit < 1 or limit > _MAX_LIMIT:
        limit = _DEFAULT_LIMIT

    # Fetch limit + 1 to determine has_more
    result = await ctx.session.execute(
        select(UpholsteryInventory)
        .where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
        .order_by(desc(UpholsteryInventory.created_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]

    return {
        "upholstery_inventories_pagination": {
            "items": [serialize_upholstery_inventory(inv) for inv in items],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
