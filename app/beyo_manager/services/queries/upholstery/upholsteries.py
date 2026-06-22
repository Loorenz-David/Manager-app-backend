"""QUERY-1: List Upholsteries | QUERY-2: Get Upholstery by ID."""

from sqlalchemy import exists, or_, select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def list_upholsteries(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    in_stock_raw = ctx.query_params.get("in_stock")
    favorite_raw = ctx.query_params.get("favorite")
    upholstery_category_ids = _split_csv(ctx.query_params.get("upholstery_category_ids"))

    stmt = select(Upholstery).where(
        Upholstery.workspace_id == ctx.workspace_id,
        Upholstery.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Upholstery.name.ilike(pattern),
                Upholstery.code.ilike(pattern),
            )
        )

    if favorite_raw is not None:
        favorite = str(favorite_raw).strip().lower() == "true"
        stmt = stmt.where(Upholstery.favorite.is_(favorite))

    if upholstery_category_ids:
        stmt = stmt.where(Upholstery.upholstery_category_id.in_(upholstery_category_ids))

    if in_stock_raw is not None:
        in_stock = str(in_stock_raw).strip().lower() == "true"
        conditions = (
            [
                UpholsteryInventoryConditionEnum.AVAILABLE,
                UpholsteryInventoryConditionEnum.LOW_STOCK,
            ]
            if in_stock
            else [UpholsteryInventoryConditionEnum.OUT_OF_STOCK]
        )
        stmt = stmt.where(
            exists(
                select(UpholsteryInventory.upholstery_id).where(
                    UpholsteryInventory.upholstery_id == Upholstery.client_id,
                    UpholsteryInventory.workspace_id == ctx.workspace_id,
                    UpholsteryInventory.is_deleted.is_(False),
                    UpholsteryInventory.inventory_condition.in_(conditions),
                )
            )
        )

    stmt = (
        stmt.order_by(
            Upholstery.list_order.asc().nulls_last(),
            Upholstery.favorite.desc(),
            Upholstery.created_at.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    upholstery_ids = [u.client_id for u in page] if page else []

    # Batch-load active inventory per upholstery — single query, no N+1.
    # The partial unique index guarantees at most one active row per upholstery_id.
    inventory_map: dict[str, UpholsteryInventory] = {}
    category_map: dict[str, UpholsteryCategory] = {}
    if page:
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id.in_(upholstery_ids),
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory_map = {inv.upholstery_id: inv for inv in inv_result.scalars().all()}

        category_ids = list({u.upholstery_category_id for u in page if u.upholstery_category_id})
        if category_ids:
            cat_result = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.client_id.in_(category_ids),
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            category_map = {cat.client_id: cat for cat in cat_result.scalars().all()}

    return {
        "upholsteries": [
            serialize_upholstery(
                u,
                inventory_map.get(u.client_id),
                category_map.get(u.upholstery_category_id) if u.upholstery_category_id else None,
            )
            for u in page
        ],
        "upholsteries_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_upholstery(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Upholstery).where(
            Upholstery.workspace_id == ctx.workspace_id,
            Upholstery.client_id == client_id,
            Upholstery.is_deleted.is_(False),
        )
    )
    upholstery = result.scalar_one_or_none()
    if upholstery is None:
        raise NotFound("Upholstery not found.")

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
