from sqlalchemy import and_, or_, outerjoin, select

from beyo_manager.domain.emails.serializers import serialize_email_thread
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_email_threads(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    unread_only = str(ctx.query_params.get("unread_only", "false")).lower() == "true"
    connection_client_id = ctx.query_params.get("connection_client_id")
    entity_type = ctx.query_params.get("entity_type")
    entity_client_id = ctx.query_params.get("entity_client_id")

    join_expr = outerjoin(
        EmailThread,
        EmailThreadUserState,
        and_(
            EmailThreadUserState.thread_id == EmailThread.client_id,
            EmailThreadUserState.user_id == ctx.user_id,
        ),
    )
    stmt = (
        select(EmailThread, EmailThreadUserState)
        .select_from(join_expr)
        .where(EmailThread.workspace_id == ctx.workspace_id)
    )
    if connection_client_id:
        stmt = stmt.where(EmailThread.connection_id == connection_client_id)
    if entity_type and entity_client_id:
        stmt = stmt.where(
            EmailThread.entity_type == entity_type,
            EmailThread.entity_client_id == entity_client_id,
        )
    if unread_only:
        stmt = stmt.where(
            EmailThread.last_inbound_message_at.is_not(None),
            or_(
                EmailThreadUserState.last_read_at.is_(None),
                EmailThread.last_inbound_message_at > EmailThreadUserState.last_read_at,
            ),
        )
    result = await ctx.session.execute(
        stmt.order_by(EmailThread.last_message_at.desc().nullslast()).offset(offset).limit(limit + 1)
    )
    rows = result.all()
    page = rows[:limit]
    return {
        "email_threads": [serialize_email_thread(thread, state) for thread, state in page],
        "email_threads_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }
