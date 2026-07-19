from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_GET_TTL = 900


async def get_pending_upload_download_url(ctx: ServiceContext) -> dict:
    upload = await ctx.session.get(PendingUpload, (ctx.incoming_data or {}).get("pending_upload_client_id"))
    if upload is None or upload.workspace_id != ctx.workspace_id:
        raise NotFound("PendingUpload not found")
    storage = get_storage_client()
    return {
        "download_url": storage.generate_presigned_get_url(upload.storage_key, _GET_TTL),
        # Stable URLs are backdated, so the returned URL has less than _GET_TTL left.
        "expires_in_seconds": storage.presigned_get_remaining_seconds(upload.storage_key, _GET_TTL),
    }
