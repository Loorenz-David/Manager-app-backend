from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.app_update_presentations.slide_order import resequenced_orders
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._sequencing import (
    apply_sequence_orders,
)
from beyo_manager.services.commands.app_update_slide_media.requests import (
    parse_reorder_slide_media_request,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_slide_for_write,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def reorder_slide_media(ctx: ServiceContext) -> dict:
    request = parse_reorder_slide_media_request(ctx.incoming_data)
    order_map = resequenced_orders(request.ordered_media_ids)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )
        result = await ctx.session.execute(
            select(AppUpdateSlideMedia).where(
                AppUpdateSlideMedia.slide_id == request.slide_id,
                AppUpdateSlideMedia.is_deleted.is_(False),
            )
        )
        media_rows = result.scalars().all()
        media_by_id = {m.client_id: m for m in media_rows}

        if set(media_by_id) != set(order_map):
            raise ValidationError(
                "ordered_media_ids must list exactly the slide's current media."
            )

        await apply_sequence_orders(ctx.session, media_by_id, order_map)

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
