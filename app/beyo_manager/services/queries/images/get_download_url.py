from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_GET_TTL = 3600


async def get_download_url(ctx: ServiceContext) -> dict:
    image = await ctx.session.get(Image, (ctx.incoming_data or {}).get("image_client_id"))
    if image is None or image.deleted_at is not None:
        raise NotFound("Image not found")
    return {"download_url": get_storage_client().generate_presigned_get_url(image.image_url, _GET_TTL), "expires_in": _GET_TTL}
