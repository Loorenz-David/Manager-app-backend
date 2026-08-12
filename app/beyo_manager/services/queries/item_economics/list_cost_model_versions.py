from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_cost_model_version
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_cost_model_versions(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    result = await ctx.session.execute(
        select(CostModelVersion)
        .where(
            CostModelVersion.workspace_id == ctx.workspace_id,
            CostModelVersion.is_deleted.is_(False),
        )
        .order_by(
            CostModelVersion.effective_from.asc().nullsfirst(),
            CostModelVersion.client_id.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    terms_by_version: dict[str, list[object]] = {row.client_id: [] for row in rows[:limit]}
    if terms_by_version:
        term_result = await ctx.session.execute(
            select(CostModelTerm)
            .where(
                CostModelTerm.workspace_id == ctx.workspace_id,
                CostModelTerm.cost_model_version_id.in_(terms_by_version),
                CostModelTerm.is_deleted.is_(False),
            )
            .order_by(CostModelTerm.cost_model_version_id.asc(), CostModelTerm.created_at.asc(), CostModelTerm.client_id.asc())
        )
        for term in term_result.scalars().all():
            terms_by_version[term.cost_model_version_id].append(term)
    return {
        "cost_model_versions": [
            serialize_cost_model_version(row, terms_by_version[row.client_id])
            for row in rows[:limit]
        ],
        "cost_model_versions_pagination": {
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        },
    }
