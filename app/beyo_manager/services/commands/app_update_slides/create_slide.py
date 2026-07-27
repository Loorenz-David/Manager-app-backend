from beyo_manager.domain.app_update_presentations.action_route import (
    validate_action_route,
)
from beyo_manager.domain.app_update_presentations.composition_schemas import (
    validate_background_color,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    next_slide_sequence_order,
)
from beyo_manager.services.commands.app_update_slides.requests import (
    parse_create_slide_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_slide(ctx: ServiceContext) -> dict:
    request = parse_create_slide_request(ctx.incoming_data)
    validate_action_route(request.action_route)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        sequence_order = await next_slide_sequence_order(
            ctx.session, request.presentation_id
        )
        slide = AppUpdatePresentationSlide(
            presentation_id=request.presentation_id,
            sequence_order=sequence_order,
            title=request.title,
            description=request.description,
            action_label=request.action_label,
            action_route=request.action_route,
        )
        if request.layout_type is not None:
            slide.layout_type = request.layout_type
        if request.playback_mode is not None:
            slide.playback_mode = request.playback_mode
        if request.duration_ms is not None:
            slide.duration_ms = request.duration_ms
        if request.composition_schema_version is not None:
            slide.composition_schema_version = request.composition_schema_version
        if request.background_color is not None:
            slide.background_color = validate_background_color(request.background_color)
        ctx.session.add(slide)
        await ctx.session.flush()

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
