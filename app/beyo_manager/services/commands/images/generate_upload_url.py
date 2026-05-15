import os
import uuid
from datetime import datetime, timedelta, timezone

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
_MAX_SIZE_BYTES = 20 * 1024 * 1024
_PRESIGN_TTL = 900


def _build_storage_key(workspace_id: str, entity_type: str, entity_client_id: str, file_name: str) -> str:
    ext = os.path.splitext(file_name)[1].lower()[:10]
    return f"images/{workspace_id}/{entity_type}/{entity_client_id}/{uuid.uuid4()}{ext}"


async def generate_upload_url(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    entity_type = data.get("entity_type")
    entity_client_id = data.get("entity_client_id")
    file_name = data.get("file_name", "")
    content_type = data.get("content_type", "")
    size_bytes = data.get("file_size_bytes")

    if not entity_type or not entity_client_id:
        raise ValidationError("entity_type and entity_client_id are required")
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"content_type '{content_type}' is not allowed")
    if size_bytes and size_bytes > _MAX_SIZE_BYTES:
        raise ValidationError("file exceeds maximum allowed size")

    storage_key = _build_storage_key(ctx.workspace_id, entity_type, entity_client_id, file_name)
    upload_url = get_storage_client().generate_presigned_put_url(storage_key, content_type, _PRESIGN_TTL)
    upload = PendingUpload(
        workspace_id=ctx.workspace_id,
        created_by_id=ctx.user_id,
        storage_key=storage_key,
        file_name=file_name,
        content_type=content_type,
        status=PendingUploadStatusEnum.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_PRESIGN_TTL),
        size_bytes=size_bytes,
    )
    async with ctx.session.begin():
        ctx.session.add(upload)
        await ctx.session.flush()
    return {"upload_url": upload_url, "pending_upload_client_id": upload.client_id, "storage_key": storage_key, "expires_in": _PRESIGN_TTL}
