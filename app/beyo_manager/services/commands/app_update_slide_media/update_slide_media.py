from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slide_media.requests import (
    parse_update_slide_media_request,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_media_for_write,
    load_slide_for_write,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_SETTABLE = (
    "poster_storage_key",
    "fallback_storage_key",
    "alt_text",
    "mime_type",
    "width",
    "height",
    "duration_ms",
    "is_looping",
)


async def update_slide_media(ctx: ServiceContext) -> dict:
    request = parse_update_slide_media_request(ctx.incoming_data)
    provided = request.model_dump(exclude_unset=True)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )
        media = await load_media_for_write(
            ctx.session, request.slide_id, request.media_id
        )
        for field in _SETTABLE:
            if field in provided:
                setattr(media, field, provided[field])

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
