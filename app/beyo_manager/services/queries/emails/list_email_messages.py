from sqlalchemy import select

from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.domain.emails.serializers import serialize_email_message
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_email_messages(ctx: ServiceContext) -> dict:
    thread_client_id = str(ctx.incoming_data.get("thread_client_id") or "").strip()
    thread_result = await ctx.session.execute(
        select(EmailThread).where(
            EmailThread.workspace_id == ctx.workspace_id,
            EmailThread.client_id == thread_client_id,
        )
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise NotFound("Email thread not found.")

    connection_result = await ctx.session.execute(
        select(EmailConnection).where(EmailConnection.client_id == thread.connection_id)
    )
    connection = connection_result.scalar_one_or_none()
    if connection is None:
        raise NotFound("Email connection not found.")
    assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)

    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    result = await ctx.session.execute(
        select(EmailMessage)
        .where(EmailMessage.thread_id == thread.client_id)
        .order_by(EmailMessage.sent_or_received_at.asc().nullslast(), EmailMessage.created_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    page = rows[:limit]
    return {
        "email_messages": [serialize_email_message(item) for item in page],
        "email_messages_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }
