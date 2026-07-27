from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations._loaders import (
    full_graph_options,
)


async def get_presentation(ctx: ServiceContext) -> dict:
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

    return {"presentation": serialize_presentation_full(presentation)}
