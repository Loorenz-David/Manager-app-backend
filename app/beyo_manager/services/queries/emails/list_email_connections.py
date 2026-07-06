from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_connection
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_email_connections(ctx: ServiceContext) -> dict:
    owner_user_id = ctx.query_params.get("owner_user_id")
    if owner_user_id and ctx.role_name not in (ADMIN, MANAGER):
        raise PermissionDenied("You do not have access to another user's email connections.")

    target_user_id = owner_user_id or ctx.user_id
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(EmailConnection)
        .where(
            EmailConnection.workspace_id == ctx.workspace_id,
            EmailConnection.owner_user_id == target_user_id,
            EmailConnection.deleted_at.is_(None),
        )
        .order_by(EmailConnection.created_at.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    page = rows[:limit]
    return {
        "email_connections": [serialize_email_connection(item) for item in page],
        "email_connections_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }
