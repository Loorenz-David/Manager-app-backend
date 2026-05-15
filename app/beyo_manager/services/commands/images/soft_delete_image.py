from datetime import datetime, timezone

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.context import ServiceContext


async def soft_delete_image(ctx: ServiceContext) -> dict:
    async with ctx.session.begin():
        image = await ctx.session.get(Image, (ctx.incoming_data or {}).get("image_client_id"))
        if image is None:
            raise NotFound("Image not found")
        if image.deleted_at is not None:
            raise ValidationError("image is already deleted")
        image.deleted_at = datetime.now(timezone.utc)
        image.deleted_by_id = ctx.user_id
    return {"client_id": image.client_id}
