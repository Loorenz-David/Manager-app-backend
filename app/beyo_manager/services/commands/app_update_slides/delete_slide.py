from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    compact_slide_sequence,
    load_slide_for_write,
)
from beyo_manager.services.commands.app_update_slides.requests import (
    parse_delete_slide_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_slide(ctx: ServiceContext) -> dict:
    request = parse_delete_slide_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Presentation lock first, then the slide — the order every path that
        # takes both uses, so concurrent slide/media writes queue instead of
        # deadlocking.
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id, for_update=True
        )
        slide = await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id, for_update=True
        )
        now = datetime.now(timezone.utc)
        slide.is_deleted = True
        slide.deleted_at = now

        # Cascade soft-delete to the slide's media and timeline elements
        # (children are meaningless without their slide).
        media_result = await ctx.session.execute(
            select(AppUpdateSlideMedia).where(
                AppUpdateSlideMedia.slide_id == slide.client_id,
                AppUpdateSlideMedia.is_deleted.is_(False),
            )
        )
        for media in media_result.scalars().all():
            media.is_deleted = True
            media.deleted_at = now

        element_result = await ctx.session.execute(
            select(AppUpdateSlideElement).where(
                AppUpdateSlideElement.slide_id == slide.client_id,
                AppUpdateSlideElement.is_deleted.is_(False),
            )
        )
        for element in element_result.scalars().all():
            element.is_deleted = True
            element.deleted_at = now

        # Close the gap the removed slide leaves in the active 1..N sequence.
        await compact_slide_sequence(
            ctx.session, request.presentation_id, exclude_slide_id=slide.client_id
        )

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
