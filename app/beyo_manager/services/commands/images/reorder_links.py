from sqlalchemy import select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext


async def reorder_links(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    entity_type = ImageLinkEntityTypeEnum(data.get("entity_type"))
    entity_client_id = data.get("entity_client_id")
    ordered_client_ids = data.get("ordered_image_client_ids", [])
    async with ctx.session.begin():
        images = {img.client_id: img for img in (await ctx.session.execute(select(Image).where(Image.client_id.in_(ordered_client_ids)))).scalars().all()}
        links = {link.image_id: link for link in (await ctx.session.execute(select(ImageLink).where(ImageLink.entity_type == entity_type, ImageLink.entity_client_id == entity_client_id))).scalars().all()}
        for position, client_id in enumerate(ordered_client_ids):
            if client_id not in images:
                raise ValidationError(f"image '{client_id}' not found")
            link = links.get(client_id)
            if link is None:
                raise ValidationError(f"image '{client_id}' is not linked to this entity")
            link.display_order = position
    return {"reordered": len(ordered_client_ids)}
