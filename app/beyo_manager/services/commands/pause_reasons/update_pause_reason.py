from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.pause_reasons.events import PauseReasonEvent
from beyo_manager.domain.pause_reasons.serializers import (
    serialize_configured_pause_reason,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.services.commands.pause_reasons.requests import (
    parse_update_pause_reason_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.pause_reasons.eligibility import (
    load_pause_reason_links,
    sync_pause_reason_links,
    validate_pause_reason_link_targets,
)


async def update_pause_reason(ctx: ServiceContext) -> dict:
    request = parse_update_pause_reason_request(ctx.incoming_data)
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

        fields = request.model_dump(exclude_unset=True)
        linked_user_ids = None
        linked_working_section_ids = None
        if "linked_user_ids" in fields or "linked_working_section_ids" in fields:
            (
                linked_user_ids,
                linked_working_section_ids,
            ) = await validate_pause_reason_link_targets(
                ctx.session,
                workspace_id=ctx.workspace_id,
                user_ids=fields.get("linked_user_ids", []),
                working_section_ids=fields.get("linked_working_section_ids", []),
            )
            if "linked_user_ids" not in fields:
                linked_user_ids = None
            if "linked_working_section_ids" not in fields:
                linked_working_section_ids = None
        if "name" in fields and fields["name"] != pause_reason.name:
            conflict = await ctx.session.scalar(
                select(PauseReason).where(
                    PauseReason.workspace_id == ctx.workspace_id,
                    PauseReason.name == fields["name"],
                    PauseReason.is_deleted.is_(False),
                    PauseReason.client_id != pause_reason.client_id,
                )
            )
            if conflict is not None:
                raise ConflictError(
                    "A pause reason with this name already exists in the workspace."
                )

        try:
            async with ctx.session.begin_nested():
                for field in (
                    "name",
                    "image_url",
                    "pause_type",
                    "description",
                    "requires_description",
                ):
                    if field in fields:
                        setattr(pause_reason, field, fields[field])
                pause_reason.updated_by_id = ctx.user_id
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
                pause_reason, PauseReasonEvent.UPDATED, workspace_id=ctx.workspace_id
            )
        )

    await dispatch(pending_events)
    user_links, section_links = await load_pause_reason_links(
        ctx.session,
        workspace_id=ctx.workspace_id,
        pause_reason_ids=[pause_reason.client_id],
    )
    return {
        "pause_reason": serialize_configured_pause_reason(
            pause_reason,
            linked_user_ids=user_links[pause_reason.client_id],
            linked_working_section_ids=section_links[pause_reason.client_id],
        )
    }
