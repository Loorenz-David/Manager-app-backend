from sqlalchemy import delete

from beyo_manager.domain.app_update_presentations.composition_schemas import (
    CURRENT_COMPOSITION_SCHEMA_VERSION,
    validate_animation,
    validate_background_color,
    validate_layout,
    validate_style,
)
from beyo_manager.domain.app_update_presentations.element_rules import (
    validate_element_payload,
    validate_element_timing,
)
from beyo_manager.domain.app_update_presentations.enums import SlideElementTypeEnum
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.app_update_presentations.slide_timeline import (
    validate_slide_timeline,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slide_composition._validate_media_refs_in_session import (
    validate_media_refs_in_session,
)
from beyo_manager.services.commands.app_update_slide_composition.requests import (
    parse_slide_composition_replace_request,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_slide_for_write,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def replace_slide_composition(ctx: ServiceContext) -> dict:
    """Atomically replace a draft slide's whole timeline: playback settings plus
    the full ordered set of timeline elements."""
    request = parse_slide_composition_replace_request(ctx.incoming_data)
    validate_background_color(request.background_color)

    element_types = [e.element_type for e in request.elements]
    # Slide-level timeline rules (playback/duration vs element mix).
    validate_slide_timeline(request.playback_mode, request.duration_ms, element_types)

    # Validate each element and pre-compute its persisted config.
    prepared: list[dict] = []
    for index, element in enumerate(request.elements):
        validate_element_payload(
            element.element_type,
            media_id=element.media_id,
            text_content=element.text_content,
            index=index,
        )
        validate_element_timing(
            element.start_ms,
            element.end_ms,
            slide_duration_ms=request.duration_ms,
            index=index,
        )
        if element.style is not None and element.element_type != SlideElementTypeEnum.TEXT:
            raise ValidationError(f"Element {index}: style is only valid for text elements.")
        prepared.append(
            {
                "element_type": element.element_type,
                "layer_index": element.layer_index,
                "start_ms": element.start_ms,
                "end_ms": element.end_ms,
                "media_id": element.media_id,
                "text_content": element.text_content,
                "layout": validate_layout(element.layout),
                "style": validate_style(element.style),
                "enter_animation": validate_animation(element.enter_animation),
                "exit_animation": validate_animation(element.exit_animation),
            }
        )

    media_ids = [p["media_id"] for p in prepared if p["media_id"]]

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        slide = await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )
        await validate_media_refs_in_session(ctx.session, request.slide_id, media_ids)

        # Update slide timeline settings.
        slide.playback_mode = request.playback_mode
        slide.duration_ms = request.duration_ms
        slide.composition_schema_version = (
            request.composition_schema_version or CURRENT_COMPOSITION_SCHEMA_VERSION
        )
        slide.background_color = request.background_color

        # Atomic replace: clear existing elements, insert the new ordered set.
        await ctx.session.execute(
            delete(AppUpdateSlideElement).where(
                AppUpdateSlideElement.slide_id == request.slide_id
            )
        )
        await ctx.session.flush()

        for sequence_order, spec in enumerate(prepared):
            ctx.session.add(
                AppUpdateSlideElement(
                    slide_id=request.slide_id,
                    sequence_order=sequence_order,
                    **spec,
                )
            )
        await ctx.session.flush()

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
