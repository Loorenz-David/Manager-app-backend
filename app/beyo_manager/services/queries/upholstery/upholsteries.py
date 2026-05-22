"""QUERY-1: List Upholsteries | QUERY-2: Get Upholstery by ID."""

from sqlalchemy import and_, or_, select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholsteries(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

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

    stmt = stmt.order_by(Upholstery.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    images_map: dict[str, Image] = {}
    if page:
        upholstery_ids = [u.client_id for u in page]
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.UPHOLSTERY,
                    ImageLink.entity_client_id.in_(upholstery_ids),
                ),
            )
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, entity_id in img_result.all():
            if entity_id not in images_map:
                images_map[entity_id] = image

    # Batch-load active inventory per upholstery — single query, no N+1.
    # The partial unique index guarantees at most one active row per upholstery_id.
    inventory_map: dict[str, UpholsteryInventory] = {}
    if page:
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id.in_(upholstery_ids),
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory_map = {inv.upholstery_id: inv for inv in inv_result.scalars().all()}

    return {
        "upholsteries": [
            serialize_upholstery(u, images_map.get(u.client_id), inventory_map.get(u.client_id))
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

    img_result = await ctx.session.execute(
        select(Image)
        .join(
            ImageLink,
            and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.UPHOLSTERY,
                ImageLink.entity_client_id == upholstery.client_id,
            ),
        )
        .where(Image.deleted_at.is_(None))
        .order_by(ImageLink.display_order.asc())
        .limit(1)
    )
    primary_image = img_result.scalar_one_or_none()

    return {"upholstery": serialize_upholstery(upholstery, primary_image, inventory)}
