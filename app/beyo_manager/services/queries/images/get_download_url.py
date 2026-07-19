from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_GET_TTL = 3600


async def get_download_url(ctx: ServiceContext) -> dict:
    image = await ctx.session.get(Image, (ctx.incoming_data or {}).get("image_client_id"))
    if image is None or image.deleted_at is not None:
        raise NotFound("Image not found")
    storage = get_storage_client()
    return {
        "download_url": storage.generate_presigned_get_url(image.image_url, _GET_TTL),
        # Stable URLs are backdated, so the returned URL has less than _GET_TTL left.
        "expires_in": storage.presigned_get_remaining_seconds(image.image_url, _GET_TTL),
    }
