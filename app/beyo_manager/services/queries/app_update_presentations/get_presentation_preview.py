from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_active,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_view import (
    AppUpdatePresentationView,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations._loaders import (
    full_graph_options,
)


async def get_presentation_preview(ctx: ServiceContext) -> dict:
    """Render any presentation (including drafts) in the consumer 'active' shape
    for authorized administrators. Previewing does not create eligibility through
    the normal active endpoint."""
    client_id = ctx.incoming_data.get("client_id")
    if not client_id:
        raise NotFound("Presentation not found.")

    result = await ctx.session.execute(
        select(AppUpdatePresentation)
        .where(
            AppUpdatePresentation.client_id == client_id,
            AppUpdatePresentation.workspace_id == ctx.workspace_id,
            AppUpdatePresentation.is_deleted.is_(False),
        )
        .options(*full_graph_options())
    )
    presentation = result.scalar_one_or_none()
    if presentation is None:
        raise NotFound("Presentation not found.")

    view_result = await ctx.session.execute(
        select(AppUpdatePresentationView).where(
            AppUpdatePresentationView.presentation_id == client_id,
            AppUpdatePresentationView.acting_user_id == ctx.user_id,
        )
    )
    view = view_result.scalar_one_or_none()

    return {"presentation": serialize_presentation_active(presentation, view)}
