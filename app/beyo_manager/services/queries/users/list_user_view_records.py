from sqlalchemy import desc, select

from beyo_manager.domain.presence.serializers import serialize_view_record
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_user_view_records(ctx: ServiceContext) -> dict:
    user_client_id = ctx.incoming_data.get("user_client_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    membership = await ctx.session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise NotFound("User not found in workspace.")

    result = await ctx.session.execute(
        select(UserAppViewRecord)
        .where(UserAppViewRecord.user_id == user_client_id)
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
