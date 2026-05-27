import logging
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.models.tables.images.image_event import ImageEvent
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

logger = logging.getLogger(__name__)


async def _run_soft_delete(ctx: ServiceContext, image: Image) -> dict:
    if image.deleted_at is not None:
        raise ValidationError("image is already deleted")
    image.deleted_at = datetime.now(timezone.utc)
    image.deleted_by_id = ctx.user_id
    return {"client_id": image.client_id}


async def _run_hard_delete(ctx: ServiceContext, image: Image) -> dict:
    try:
        get_storage_client().delete_object(image.image_url)
    except Exception:
        logger.warning("Image object deletion failed during hard delete", extra={"image_client_id": image.client_id}, exc_info=True)

    image.last_event_id = None
    await ctx.session.flush()
    await ctx.session.execute(sa_delete(ImageLink).where(ImageLink.image_id == image.client_id))
    await ctx.session.execute(sa_delete(ImageAnnotation).where(ImageAnnotation.image_id == image.client_id))
    await ctx.session.execute(sa_delete(ImageEvent).where(ImageEvent.image_id == image.client_id))
    await ctx.session.delete(image)
    return {"client_id": image.client_id, "deleted": True, "hard_deleted": True}


async def soft_delete_image(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    hard_delete = bool(data.get("hard_delete"))

    async with ctx.session.begin():
        image = await ctx.session.get(Image, data.get("image_client_id"))
        if image is None:
            raise NotFound("Image not found")
        if hard_delete:
            return await _run_hard_delete(ctx, image)
        return await _run_soft_delete(ctx, image)
