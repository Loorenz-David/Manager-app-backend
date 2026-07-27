from beyo_manager.domain.app_update_presentations.action_route import (
    validate_action_route,
)
from beyo_manager.domain.app_update_presentations.composition_schemas import (
    validate_background_color,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_slide_for_write,
)
from beyo_manager.services.commands.app_update_slides.requests import (
    parse_update_slide_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_SETTABLE = (
    "title",
    "description",
    "layout_type",
    "action_label",
    "action_route",
    "playback_mode",
    "duration_ms",
    "composition_schema_version",
    "background_color",
)


async def update_slide(ctx: ServiceContext) -> dict:
    request = parse_update_slide_request(ctx.incoming_data)
    provided = request.model_dump(exclude_unset=True)
    if "action_route" in provided:
        validate_action_route(request.action_route)
    if "background_color" in provided:
        validate_background_color(request.background_color)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        slide = await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )
        for field in _SETTABLE:
            if field in provided:
                setattr(slide, field, provided[field])

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
