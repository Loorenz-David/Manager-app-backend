"""Query for listing upholstery inventories with pagination."""

from sqlalchemy import desc, or_, select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory_partial
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery._supplier_names import (
    load_supplier_names_by_upholstery_ids,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def list_upholstery_inventories(ctx: ServiceContext) -> dict:
    """List upholstery inventories with offset pagination."""
    limit = int(ctx.query_params.get("limit", _DEFAULT_LIMIT))
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    favorite = ctx.query_params.get("favorite")
    in_stock = ctx.query_params.get("in_stock")
    upholstery_category_ids = _split_csv(ctx.query_params.get("upholstery_category_ids"))

    # Guard: limit constraints
    if limit < 1 or limit > _MAX_LIMIT:
        limit = _DEFAULT_LIMIT

    stmt = (
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
            UpholsteryInventory.is_deleted.is_(False),
        )
    )

    if q:
        q_like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Upholstery.name.ilike(q_like),
                Upholstery.code.ilike(q_like),
            )
        )

    if upholstery_category_ids:
        stmt = stmt.where(Upholstery.upholstery_category_id.in_(upholstery_category_ids))

    if favorite is True:
        stmt = stmt.where(Upholstery.favorite.is_(True))

    if in_stock is True:
        stmt = stmt.where(
            UpholsteryInventory.inventory_condition.in_(
                [
                    UpholsteryInventoryConditionEnum.AVAILABLE,
                    UpholsteryInventoryConditionEnum.LOW_STOCK,
                ]
            )
        )
    elif in_stock is False:
        stmt = stmt.where(
            UpholsteryInventory.inventory_condition == UpholsteryInventoryConditionEnum.OUT_OF_STOCK
        )

    # Fetch limit + 1 to determine has_more
    result = await ctx.session.execute(
        stmt.order_by(desc(UpholsteryInventory.created_at)).offset(offset).limit(limit + 1)
    )
    rows = result.all()

    has_more = len(rows) > limit
    items = rows[:limit]
    upholstery_ids = [inv.upholstery_id for inv, *_ in items if inv.upholstery_id]
    supplier_name_map = await load_supplier_names_by_upholstery_ids(
        session=ctx.session,
        workspace_id=ctx.workspace_id,
        upholstery_ids=upholstery_ids,
    )

    return {
        "upholstery_inventories_pagination": {
            "items": [
                serialize_upholstery_inventory_partial(
                    inv,
                    image_url=image_url,
                    upholstery_name=upholstery_name,
                    upholstery_code=upholstery_code,
                    page_link=page_link,
                    supplier_name=supplier_name_map.get(inv.upholstery_id),
                    favorite=favorite,
                )
                for inv, image_url, upholstery_name, upholstery_code, page_link, favorite in items
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
