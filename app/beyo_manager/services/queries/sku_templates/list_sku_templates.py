from sqlalchemy import select

from beyo_manager.domain.sku_templates.serializers import serialize_sku_template
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_sku_templates(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    result = await ctx.session.execute(
        select(SkuTemplate)
        .where(
            SkuTemplate.workspace_id == ctx.workspace_id,
            SkuTemplate.is_deleted.is_(False),
        )
        .order_by(SkuTemplate.task_type.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    page = rows[:limit]
    return {
        "sku_templates": [serialize_sku_template(row) for row in page],
        "sku_templates_pagination": {
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        },
    }

