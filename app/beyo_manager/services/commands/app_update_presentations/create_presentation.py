from beyo_manager.domain.app_update_presentations.display_priority import (
    default_display_priority,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations.requests import (
    parse_create_presentation_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_presentation(ctx: ServiceContext) -> dict:
    request = parse_create_presentation_request(ctx.incoming_data)

    # Generate the id up front so logical_client_id can equal the first version's
    # own client_id (the logical group anchor).
    client_id = generate_id(AppUpdatePresentation.CLIENT_ID_PREFIX)

    presentation = AppUpdatePresentation(
        client_id=client_id,
        logical_client_id=client_id,
        version=1,
        workspace_id=ctx.workspace_id,
        title=request.title,
        summary=request.summary,
        created_by_id=ctx.user_id,
    )
    if request.presentation_type is not None:
        presentation.presentation_type = request.presentation_type
    if request.category is not None:
        presentation.category = request.category
    if request.audience_mode is not None:
        presentation.audience_mode = request.audience_mode
    # Explicit priority wins; otherwise derive a sensible default from category.
    if request.display_priority is not None:
        presentation.display_priority = request.display_priority
    else:
        presentation.display_priority = default_display_priority(request.category)
    if request.is_dismissible is not None:
        presentation.is_dismissible = request.is_dismissible
    presentation.starts_at = request.starts_at
    presentation.expires_at = request.expires_at

    async with maybe_begin(ctx.session):
        ctx.session.add(presentation)
        await ctx.session.flush()

    full = await load_presentation_full(ctx.session, ctx.workspace_id, client_id)
    return {"presentation": serialize_presentation_full(full)}
