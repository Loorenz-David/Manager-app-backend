from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_mark_upholstery_favorite_request
from beyo_manager.services.context import ServiceContext


async def mark_upholstery_favorite(ctx: ServiceContext) -> dict:
    request = parse_mark_upholstery_favorite_request(ctx.incoming_data)

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

        upholstery.favorite = request.favorite
        upholstery.updated_by_id = ctx.user_id

        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == upholstery.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory = inv_result.scalar_one_or_none()
        category = None
        if upholstery.upholstery_category_id:
            cat_result = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.client_id == upholstery.upholstery_category_id,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            category = cat_result.scalar_one_or_none()

    return {"upholstery": serialize_upholstery(upholstery, inventory, category)}
