from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.pause_reasons.events import PauseReasonEvent
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.services.commands.pause_reasons.requests import parse_delete_pause_reason_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def delete_pause_reason(ctx: ServiceContext) -> dict:
    request = parse_delete_pause_reason_request(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        pause_reason = await ctx.session.scalar(
            select(PauseReason).where(
                PauseReason.workspace_id == ctx.workspace_id,
                PauseReason.client_id == request.client_id,
                PauseReason.is_deleted.is_(False),
            )
        )
        if pause_reason is None:
            raise NotFound("Pause reason not found.")

        # No system-managed delete guard. `can_delete_pause_reason` used to block deletion of rows
        # whose behaviour the backend depended on; no code path resolves a pause reason by slug any
        # more, so there is nothing left to protect. Every row here is workspace data the manager
        # owns. `is_system_managed` survives on the model and in the serializer only because the
        # published schema declares it required — it is uniformly false and carries no meaning.
        pause_reason.is_deleted = True
        pause_reason.deleted_at = datetime.now(timezone.utc)
        pause_reason.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(pause_reason, PauseReasonEvent.DELETED, workspace_id=ctx.workspace_id)
        )

    await dispatch(pending_events)
    return {}
