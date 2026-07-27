from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.pause_reasons.events import PauseReasonEvent
from beyo_manager.domain.pause_reasons.guards import can_delete_pause_reason
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
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
        if not can_delete_pause_reason(pause_reason):
            raise ConflictError("This pause reason is managed by the system and cannot be deleted.")

        pause_reason.is_deleted = True
        pause_reason.deleted_at = datetime.now(timezone.utc)
        pause_reason.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(pause_reason, PauseReasonEvent.DELETED, workspace_id=ctx.workspace_id)
        )

    await dispatch(pending_events)
    return {}
