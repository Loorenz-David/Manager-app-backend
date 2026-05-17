from sqlalchemy import desc, select

from beyo_manager.domain.presence.serializers import serialize_view_record
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_self_view_records(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(UserAppViewRecord)
        .where(UserAppViewRecord.user_id == ctx.user_id)
        .order_by(desc(UserAppViewRecord.started_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "view_records": [serialize_view_record(r) for r in page],
        "view_records_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
