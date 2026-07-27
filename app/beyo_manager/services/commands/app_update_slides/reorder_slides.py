from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.app_update_presentations.slide_order import resequenced_orders
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._sequencing import (
    apply_sequence_orders,
)
from beyo_manager.services.commands.app_update_slides.requests import (
    parse_reorder_slides_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def reorder_slides(ctx: ServiceContext) -> dict:
    request = parse_reorder_slides_request(ctx.incoming_data)
    order_map = resequenced_orders(request.ordered_slide_ids)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        result = await ctx.session.execute(
            select(AppUpdatePresentationSlide).where(
                AppUpdatePresentationSlide.presentation_id == request.presentation_id,
                AppUpdatePresentationSlide.is_deleted.is_(False),
            )
        )
        slides = result.scalars().all()
        slides_by_id = {s.client_id: s for s in slides}

        if set(slides_by_id) != set(order_map):
            raise ValidationError(
                "ordered_slide_ids must list exactly the presentation's current slides."
            )

        await apply_sequence_orders(ctx.session, slides_by_id, order_map)

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
