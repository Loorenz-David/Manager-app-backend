from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_production_cost_groups(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    result = await ctx.session.execute(
        select(ProductionCostGroup)
        .where(
            ProductionCostGroup.workspace_id == ctx.workspace_id,
            ProductionCostGroup.is_deleted.is_(False),
        )
        .order_by(ProductionCostGroup.name.asc(), ProductionCostGroup.client_id.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    return {
        "production_cost_groups": [serialize_production_cost_group(row) for row in rows[:limit]],
        "production_cost_groups_pagination": {
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        },
    }
