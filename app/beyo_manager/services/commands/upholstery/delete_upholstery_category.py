from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_delete_upholstery_category_request,
)
from beyo_manager.services.context import ServiceContext


async def delete_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_delete_upholstery_category_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.client_id == request.client_id,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFound("Upholstery category not found.")

        category.is_deleted = True
        category.deleted_at = datetime.now(timezone.utc)
        category.deleted_by_id = ctx.user_id

    return {}
