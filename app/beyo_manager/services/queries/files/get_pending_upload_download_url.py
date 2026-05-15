from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_GET_TTL = 900


async def get_pending_upload_download_url(ctx: ServiceContext) -> dict:
    upload = await ctx.session.get(PendingUpload, (ctx.incoming_data or {}).get("pending_upload_client_id"))
    if upload is None or upload.workspace_id != ctx.workspace_id:
        raise NotFound("PendingUpload not found")
    return {"download_url": get_storage_client().generate_presigned_get_url(upload.storage_key, _GET_TTL), "expires_in_seconds": _GET_TTL}
