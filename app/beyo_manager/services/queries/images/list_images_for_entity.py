from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image_link
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext


async def list_images_for_entity(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    entity_type = ImageLinkEntityTypeEnum(data.get("entity_type"))
    rows = (await ctx.session.execute(
        select(ImageLink)
        .join(Image, Image.client_id == ImageLink.image_id)
        .options(selectinload(ImageLink.image).selectinload(Image.last_event))
        .where(ImageLink.entity_type == entity_type, ImageLink.entity_client_id == data.get("entity_client_id"), Image.deleted_at.is_(None))
        .order_by(ImageLink.display_order)
    )).scalars().all()
    return {"images": [serialize_image_link(link) for link in rows]}
