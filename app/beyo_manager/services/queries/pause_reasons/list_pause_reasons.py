from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.pause_reasons.serializers import serialize_pause_reason
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_pause_reasons(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    pause_type = ctx.query_params.get("pause_type")

    stmt = select(PauseReason).where(
        PauseReason.workspace_id == ctx.workspace_id,
        PauseReason.is_deleted.is_(False),
    )
    if pause_type is not None:
        try:
            pause_type = PauseTypeEnum(pause_type)
        except ValueError:
            pause_type = None
        if pause_type is not None:
            stmt = stmt.where(PauseReason.pause_type == pause_type)

    result = await ctx.session.execute(
        stmt.order_by(PauseReason.created_at.asc()).offset(offset).limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    return {
        "pause_reasons": [serialize_pause_reason(row) for row in page],
        "pause_reasons_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
