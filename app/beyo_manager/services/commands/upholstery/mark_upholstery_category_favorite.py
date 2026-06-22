from sqlalchemy import func, select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_mark_upholstery_category_favorite_request,
)
from beyo_manager.services.context import ServiceContext


async def mark_upholstery_category_favorite(ctx: ServiceContext) -> dict:
    request = parse_mark_upholstery_category_favorite_request(ctx.incoming_data)

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

        category.favorite = request.favorite
        category.updated_by_id = ctx.user_id

        count_result = await ctx.session.execute(
            select(func.count(Upholstery.client_id)).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.upholstery_category_id == category.client_id,
                Upholstery.is_deleted.is_(False),
            )
        )
        upholstery_count = int(count_result.scalar() or 0)

    return {
        "upholstery_category": serialize_upholstery_category(
            category,
            upholstery_count=upholstery_count,
        )
    }
