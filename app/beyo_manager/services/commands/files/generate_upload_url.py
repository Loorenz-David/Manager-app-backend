import os
import uuid
from datetime import datetime, timedelta, timezone

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

ALLOWED_MIME_TYPES = {
    "record_attachment": ["image/jpeg", "image/png", "image/webp", "application/pdf", "text/plain"],
    "case_attachment":   ["image/jpeg", "image/png", "image/webp", "application/pdf", "text/plain"],
    "import": ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
}
MAX_FILE_SIZE_BYTES = {
    "record_attachment": 10 * 1024 * 1024,
    "case_attachment":   10 * 1024 * 1024,
    "import":            50 * 1024 * 1024,
}
_PRESIGN_TTL = 300


def _build_storage_key(environment: str, workspace_id: str, use_case: str, file_name: str) -> str:
    ext = os.path.splitext(file_name)[1].lower()[:10]
    return f"{environment}/{workspace_id}/{use_case}/{uuid.uuid4()}{ext}"


async def generate_upload_url(ctx: ServiceContext) -> dict:
    from beyo_manager.config import settings

    data = ctx.incoming_data or {}
    use_case = data.get("use_case", "record_attachment")
    file_name = data.get("file_name", "")
    content_type = data.get("content_type", "")
    size_bytes = data.get("file_size_bytes")

    if content_type not in ALLOWED_MIME_TYPES.get(use_case, []):
        raise ValidationError(f"content_type '{content_type}' is not allowed for {use_case}")
    if len(file_name) > 255:
        raise ValidationError("file_name must be 255 characters or fewer")
    if size_bytes and size_bytes > MAX_FILE_SIZE_BYTES.get(use_case, 10 * 1024 * 1024):
        raise ValidationError("file exceeds maximum allowed size")

    storage_key = _build_storage_key(settings.environment, ctx.workspace_id, use_case, file_name)
    upload_url = get_storage_client().generate_presigned_put_url(storage_key, content_type, _PRESIGN_TTL)
    upload = PendingUpload(
        workspace_id=ctx.workspace_id,
        created_by_id=ctx.user_id,
        storage_key=storage_key,
        file_name=file_name,
        content_type=content_type,
        status=PendingUploadStatusEnum.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        size_bytes=size_bytes,
    )
    async with ctx.session.begin():
        ctx.session.add(upload)
    return {"upload_url": upload_url, "pending_upload_client_id": upload.client_id, "storage_key": storage_key, "expires_in_seconds": _PRESIGN_TTL}
