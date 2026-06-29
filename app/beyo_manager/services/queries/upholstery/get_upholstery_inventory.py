"""Query for getting a single upholstery inventory."""

from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery._supplier_names import load_supplier_name_for_upholstery


async def get_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Get a single upholstery inventory by client_id."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(
            UpholsteryInventory,
            Upholstery.image_url,
            Upholstery.name,
            Upholstery.code,
            Upholstery.page_link,
            Upholstery.favorite,
        )
        .outerjoin(Upholstery, Upholstery.client_id == UpholsteryInventory.upholstery_id)
        .where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.client_id == client_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise NotFound("UpholsteryInventory not found.")
    inv, image_url, upholstery_name, upholstery_code, page_link, favorite = row
    supplier_name = await load_supplier_name_for_upholstery(
        session=ctx.session,
        workspace_id=ctx.workspace_id,
        upholstery_id=inv.upholstery_id,
    )

    return {
        "inventory": serialize_upholstery_inventory(
            inv,
            image_url=image_url,
            upholstery_name=upholstery_name,
            upholstery_code=upholstery_code,
            page_link=page_link,
            supplier_name=supplier_name,
            favorite=favorite,
        )
    }
