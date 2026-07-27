from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations.requests import (
    parse_update_presentation_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_SETTABLE = (
    "title",
    "summary",
    "presentation_type",
    "category",
    "audience_mode",
    "display_priority",
    "is_dismissible",
)


async def update_presentation(ctx: ServiceContext) -> dict:
    request = parse_update_presentation_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        presentation = await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.client_id
        )
        # Only overwrite fields the client explicitly sent.
        provided = request.model_dump(exclude_unset=True)
        for field in _SETTABLE:
            if field in provided:
                setattr(presentation, field, provided[field])
        if "starts_at" in provided:
            presentation.starts_at = request.starts_at
        if "expires_at" in provided:
            presentation.expires_at = request.expires_at
        presentation.updated_by_id = ctx.user_id

    full = await load_presentation_full(ctx.session, ctx.workspace_id, request.client_id)
    return {"presentation": serialize_presentation_full(full)}
