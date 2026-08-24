from sqlalchemy import select

from beyo_manager.domain.pause_reasons.serializers import (
    serialize_configured_pause_reason,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.pause_reasons.eligibility import load_pause_reason_links


async def get_pause_reason(ctx: ServiceContext) -> dict:
    pause_reason = await ctx.session.scalar(
        select(PauseReason).where(
            PauseReason.workspace_id == ctx.workspace_id,
            PauseReason.client_id == ctx.incoming_data.get("client_id"),
            PauseReason.is_deleted.is_(False),
        )
    )
    if pause_reason is None:
        raise NotFound("Pause reason not found.")
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
