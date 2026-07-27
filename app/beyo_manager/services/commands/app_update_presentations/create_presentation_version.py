import logging

from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.app_update_presentations.versioning import next_version_number
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.services.commands.app_update_presentations._copy_presentation_children_in_session import (
    copy_presentation_children_in_session,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations.requests import (
    parse_presentation_ref_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

logger = logging.getLogger(__name__)


async def create_presentation_version(ctx: ServiceContext) -> dict:
    request = parse_presentation_ref_request(ctx.incoming_data)
    new_client_id = generate_id(AppUpdatePresentation.CLIENT_ID_PREFIX)

    async with maybe_begin(ctx.session):
        source = await load_presentation_full(
            ctx.session, ctx.workspace_id, request.client_id
        )

        versions_result = await ctx.session.execute(
            select(AppUpdatePresentation.version).where(
                AppUpdatePresentation.logical_client_id == source.logical_client_id,
                AppUpdatePresentation.workspace_id == ctx.workspace_id,
            )
        )
        next_version = next_version_number(versions_result.scalars().all())

        new_presentation = AppUpdatePresentation(
            client_id=new_client_id,
            logical_client_id=source.logical_client_id,
            version=next_version,
            workspace_id=ctx.workspace_id,
            title=source.title,
            summary=source.summary,
            status=PresentationStatusEnum.DRAFT,
            presentation_type=source.presentation_type,
            category=source.category,
            audience_mode=source.audience_mode,
            display_priority=source.display_priority,
            is_dismissible=source.is_dismissible,
            starts_at=source.starts_at,
            expires_at=source.expires_at,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(new_presentation)
        await ctx.session.flush()

        await copy_presentation_children_in_session(
            ctx.session, source, new_presentation
        )

    logger.info(
        "app_update_presentation new version created | source_id=%s new_id=%s "
        "logical_client_id=%s version=%s workspace_id=%s",
        request.client_id,
        new_client_id,
        source.logical_client_id,
        next_version,
        ctx.workspace_id,
    )

    full = await load_presentation_full(ctx.session, ctx.workspace_id, new_client_id)
    return {"presentation": serialize_presentation_full(full)}
