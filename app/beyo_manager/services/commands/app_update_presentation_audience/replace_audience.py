from sqlalchemy import delete

from beyo_manager.domain.app_update_presentations.audience_rules import (
    validate_audience_mode,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.models.tables.app_update_presentations.presentation_app_target import (
    AppUpdatePresentationAppTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_role_target import (
    AppUpdatePresentationRoleTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_user_target import (
    AppUpdatePresentationUserTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_workspace_target import (
    AppUpdatePresentationWorkspaceTarget,
)
from beyo_manager.services.commands.app_update_presentation_audience._validate_targets_in_session import (
    validate_targets_in_session,
)
from beyo_manager.services.commands.app_update_presentation_audience.requests import (
    parse_replace_audience_request,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def replace_audience(ctx: ServiceContext) -> dict:
    request = parse_replace_audience_request(ctx.incoming_data)

    # De-duplicate within each dimension (OR semantics — duplicates are noise).
    app_keys = list(dict.fromkeys(request.app_keys))
    role_keys = list(dict.fromkeys(request.role_keys))
    workspace_ids = list(dict.fromkeys(request.workspace_ids))
    user_ids = list(dict.fromkeys(request.user_ids))

    validate_audience_mode(request.audience_mode, len(user_ids))

    async with maybe_begin(ctx.session):
        presentation = await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        await validate_targets_in_session(
            ctx.session, ctx.workspace_id, workspace_ids, user_ids
        )

        pid = presentation.client_id
        # Atomic replace: clear all existing target rows, then insert the new set.
        for target_model in (
            AppUpdatePresentationAppTarget,
            AppUpdatePresentationRoleTarget,
            AppUpdatePresentationWorkspaceTarget,
            AppUpdatePresentationUserTarget,
        ):
            await ctx.session.execute(
                delete(target_model).where(target_model.presentation_id == pid)
            )

        for app_key in app_keys:
            ctx.session.add(
                AppUpdatePresentationAppTarget(presentation_id=pid, app_key=app_key)
            )
        for role_key in role_keys:
            ctx.session.add(
                AppUpdatePresentationRoleTarget(presentation_id=pid, role_key=role_key)
            )
        for workspace_id in workspace_ids:
            ctx.session.add(
                AppUpdatePresentationWorkspaceTarget(
                    presentation_id=pid, workspace_id=workspace_id
                )
            )
        for user_id in user_ids:
            ctx.session.add(
                AppUpdatePresentationUserTarget(presentation_id=pid, user_id=user_id)
            )

        presentation.audience_mode = request.audience_mode
        presentation.updated_by_id = ctx.user_id
        await ctx.session.flush()

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
