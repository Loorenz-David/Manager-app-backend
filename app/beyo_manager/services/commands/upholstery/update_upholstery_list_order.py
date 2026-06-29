from sqlalchemy import select, update as sa_update

from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_update_upholstery_list_order_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery._supplier_names import load_supplier_name_for_upholstery


async def update_upholstery_list_order(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_list_order_request(ctx.incoming_data)

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

        if request.list_order is not None:
            await ctx.session.execute(
                sa_update(Upholstery)
                .where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.is_deleted.is_(False),
                    Upholstery.client_id != upholstery.client_id,
                    Upholstery.list_order.is_not(None),
                    Upholstery.list_order >= request.list_order,
                )
                .values(list_order=Upholstery.list_order + 1)
                .execution_options(synchronize_session=False)
            )

        upholstery.list_order = request.list_order
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
        supplier_name = await load_supplier_name_for_upholstery(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_id=upholstery.client_id,
        )

    return {
        "upholstery": serialize_upholstery(
            upholstery,
            inventory,
            category,
            supplier_name=supplier_name,
        )
    }
