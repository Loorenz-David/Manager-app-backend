from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.pause_reasons.events import PauseReasonEvent
from beyo_manager.domain.pause_reasons.serializers import (
    serialize_configured_pause_reason,
)
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.base.identity import generate_id
from beyo_manager.services.commands.pause_reasons.requests import (
    parse_create_pause_reason_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.pause_reasons.eligibility import (
    sync_pause_reason_links,
    validate_pause_reason_link_targets,
)


async def create_pause_reason(ctx: ServiceContext) -> dict:
    request = parse_create_pause_reason_request(ctx.incoming_data)
    pending_events = []

    async with maybe_begin(ctx.session):
        (
            linked_user_ids,
            linked_working_section_ids,
        ) = await validate_pause_reason_link_targets(
            ctx.session,
            workspace_id=ctx.workspace_id,
            user_ids=request.linked_user_ids,
            working_section_ids=request.linked_working_section_ids,
        )
        conflict = await ctx.session.scalar(
            select(PauseReason).where(
                PauseReason.workspace_id == ctx.workspace_id,
                PauseReason.name == request.name,
                PauseReason.is_deleted.is_(False),
            )
        )
        if conflict is not None:
            raise ConflictError(
                "A pause reason with this name already exists in the workspace."
            )

        pause_reason_id = generate_id(PauseReason.CLIENT_ID_PREFIX)
        pause_reason = PauseReason(
            client_id=pause_reason_id,
            workspace_id=ctx.workspace_id,
            name=request.name,
            image_url=request.image_url,
            pause_type=request.pause_type,
            description=request.description,
            requires_description=request.requires_description,
            is_system_managed=False,
            slug=f"custom_{pause_reason_id}",
            created_by_id=ctx.user_id,
        )
        try:
            async with ctx.session.begin_nested():
                ctx.session.add(pause_reason)
                await ctx.session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "A pause reason with this name already exists in the workspace."
            ) from exc

        await sync_pause_reason_links(
            ctx.session,
            workspace_id=ctx.workspace_id,
            pause_reason_id=pause_reason.client_id,
            linked_user_ids=linked_user_ids,
            linked_working_section_ids=linked_working_section_ids,
        )
        await ctx.session.flush()
        pending_events.append(
            build_workspace_event(
                pause_reason, PauseReasonEvent.CREATED, workspace_id=ctx.workspace_id
            )
        )

    await dispatch(pending_events)
    return {
        "pause_reason": serialize_configured_pause_reason(
            pause_reason,
            linked_user_ids=linked_user_ids,
            linked_working_section_ids=linked_working_section_ids,
        )
    }
