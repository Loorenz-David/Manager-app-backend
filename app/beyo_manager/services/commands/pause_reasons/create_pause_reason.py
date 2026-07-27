from sqlalchemy import select

from beyo_manager.domain.pause_reasons.events import PauseReasonEvent
from beyo_manager.domain.pause_reasons.serializers import serialize_pause_reason
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.services.commands.pause_reasons.requests import parse_create_pause_reason_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.commands.utils.transaction import maybe_begin


async def create_pause_reason(ctx: ServiceContext) -> dict:
    request = parse_create_pause_reason_request(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        conflict = await ctx.session.scalar(
            select(PauseReason).where(
                PauseReason.workspace_id == ctx.workspace_id,
                PauseReason.name == request.name,
                PauseReason.is_deleted.is_(False),
            )
        )
        if conflict is not None:
            raise ConflictError("A pause reason with this name already exists in the workspace.")

        pause_reason = PauseReason(
            workspace_id=ctx.workspace_id,
            name=request.name,
            image_url=request.image_url,
            pause_type=request.pause_type,
            description=request.description,
            requires_description=request.requires_description,
            is_system_managed=False,
            slug=None,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(pause_reason)
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(pause_reason, PauseReasonEvent.CREATED, workspace_id=ctx.workspace_id)
        )

    await dispatch(pending_events)
    return {"pause_reason": serialize_pause_reason(pause_reason)}
