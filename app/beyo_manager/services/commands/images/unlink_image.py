from sqlalchemy import select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext


async def unlink_image(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    async with ctx.session.begin():
        image = await ctx.session.get(Image, data.get("image_client_id"))
        if image is None:
            raise NotFound("Image not found")
        entity_type = ImageLinkEntityTypeEnum(data.get("entity_type"))
        link = (await ctx.session.execute(select(ImageLink).where(
            ImageLink.image_id == image.client_id,
            ImageLink.entity_type == entity_type,
            ImageLink.entity_client_id == data.get("entity_client_id"),
        ))).scalar_one_or_none()
        if link is None:
            raise NotFound("ImageLink not found")
        await ctx.session.delete(link)
    return {"unlinked": True}
