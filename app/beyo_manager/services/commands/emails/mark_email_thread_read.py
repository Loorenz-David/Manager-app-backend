from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def mark_email_thread_read(ctx: ServiceContext) -> dict:
    thread_client_id = str(ctx.incoming_data.get("thread_client_id") or "").strip()
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
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

        state_result = await ctx.session.execute(
            select(EmailThreadUserState)
            .where(
                EmailThreadUserState.thread_id == thread.client_id,
                EmailThreadUserState.user_id == ctx.user_id,
            )
            .with_for_update()
        )
        state = state_result.scalar_one_or_none()
        if state is None:
            ctx.session.add(
                EmailThreadUserState(
                    thread_id=thread.client_id,
                    user_id=ctx.user_id,
                    last_read_at=now,
                )
            )
        else:
            state.last_read_at = now

    return {"marked_read": True}
