from sqlalchemy import func, or_, outerjoin, select

from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState
from beyo_manager.services.context import ServiceContext


async def get_email_unread_counts(ctx: ServiceContext) -> dict:
    connection_client_id = ctx.query_params.get("connection_client_id")
    entity_type = ctx.query_params.get("entity_type")
    entity_client_id = ctx.query_params.get("entity_client_id")

    join_expr = outerjoin(
        EmailThread,
        EmailThreadUserState,
        (EmailThreadUserState.thread_id == EmailThread.client_id)
        & (EmailThreadUserState.user_id == ctx.user_id),
    )
    stmt = (
        select(func.count())
        .select_from(join_expr)
        .where(
            EmailThread.workspace_id == ctx.workspace_id,
            EmailThread.last_inbound_message_at.is_not(None),
            or_(
                EmailThreadUserState.last_read_at.is_(None),
                EmailThread.last_inbound_message_at > EmailThreadUserState.last_read_at,
            ),
        )
    )
    if connection_client_id:
        stmt = stmt.where(EmailThread.connection_id == connection_client_id)
    if entity_type:
        stmt = stmt.where(EmailThread.entity_type == entity_type)
    if entity_client_id:
        stmt = stmt.where(EmailThread.entity_client_id == entity_client_id)
    result = await ctx.session.execute(stmt)
    return {"unread_count": int(result.scalar() or 0)}
