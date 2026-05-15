from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.context import ServiceContext


async def get_image(ctx: ServiceContext) -> dict:
    image = await ctx.session.get(
        Image,
        (ctx.incoming_data or {}).get("image_client_id"),
        options=[selectinload(Image.last_event), selectinload(Image.events), selectinload(Image.image_annotations)],
    )
    if image is None or image.deleted_at is not None:
        raise NotFound("Image not found")
    return {"image": serialize_image(image, include_events=True, include_annotations=True)}
