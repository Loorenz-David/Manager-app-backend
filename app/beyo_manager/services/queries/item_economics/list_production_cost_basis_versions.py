from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_basis_version
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_production_cost_basis_versions(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    group_id = ctx.incoming_data.get("production_cost_group_id")
    statement = select(ProductionCostBasisVersion).where(
        ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
        ProductionCostBasisVersion.is_deleted.is_(False),
    )
    if group_id is not None:
        statement = statement.where(ProductionCostBasisVersion.production_cost_group_id == group_id)
    result = await ctx.session.execute(
        statement.order_by(
            ProductionCostBasisVersion.effective_from.asc().nullsfirst(),
            ProductionCostBasisVersion.client_id.asc(),
        ).offset(offset).limit(limit + 1)
    )
    rows = result.scalars().all()
    return {
        "production_cost_basis_versions": [serialize_production_cost_basis_version(row) for row in rows[:limit]],
        "production_cost_basis_versions_pagination": {
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        },
    }
