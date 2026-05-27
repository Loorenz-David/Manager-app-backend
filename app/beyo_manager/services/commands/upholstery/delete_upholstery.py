from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.upholstery.requests import parse_delete_upholstery_request
from beyo_manager.services.context import ServiceContext


async def delete_upholstery(ctx: ServiceContext) -> dict:
    request = parse_delete_upholstery_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.client_id == request.client_id,
                Upholstery.is_deleted.is_(False),
            )
        )
        upholstery = result.scalar_one_or_none()
        if upholstery is None:
            raise NotFound("Upholstery not found.")

        upholstery.is_deleted = True
        upholstery.deleted_at = datetime.now(timezone.utc)
        upholstery.deleted_by_id = ctx.user_id
        upholstery.list_order = None

    return {}
