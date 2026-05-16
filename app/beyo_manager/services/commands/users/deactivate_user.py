from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.deactivate_user_request import (
    parse_deactivate_user_request,
)
from beyo_manager.services.context import ServiceContext


async def deactivate_user(ctx: ServiceContext) -> dict:
    request = parse_deactivate_user_request(ctx.incoming_data)

    if request.user_client_id == ctx.user_id:
        raise ValidationError("user_client_id: cannot deactivate your own account.")

    async with ctx.session.begin():
        membership = await ctx.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_client_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise NotFound("User not found or already inactive in workspace.")

        membership.is_active = False

    return {}
