import os
import uuid
from datetime import datetime, timedelta, timezone

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
)
from beyo_manager.services.commands.app_update_slide_media._media_content_types import (
    ALLOWED_CONTENT_TYPES,
    MAX_SIZE_BYTES,
    PRESIGN_TTL,
)
from beyo_manager.services.commands.app_update_slide_media.requests import (
    parse_generate_media_upload_url_request,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_slide_for_write,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client


def _build_storage_key(
    workspace_id: str, presentation_id: str, slide_id: str, file_name: str
) -> str:
    ext = os.path.splitext(file_name)[1].lower()[:10]
    return (
        f"app_update_presentations/{workspace_id}/{presentation_id}/{slide_id}/"
        f"{uuid.uuid4()}{ext}"
    )


async def generate_media_upload_url(ctx: ServiceContext) -> dict:
    request = parse_generate_media_upload_url_request(ctx.incoming_data)

    allowed = ALLOWED_CONTENT_TYPES[request.media_type]
    if request.content_type not in allowed:
        raise ValidationError(
            f"content_type '{request.content_type}' is not allowed for "
            f"media_type '{request.media_type.value}'."
        )
    max_size = MAX_SIZE_BYTES[request.media_type]
    if request.file_size_bytes and request.file_size_bytes > max_size:
        raise ValidationError("file exceeds the maximum allowed size.")

    async with maybe_begin(ctx.session):
        # Draft guard + slide existence, scoped to the workspace.
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )

        storage_key = _build_storage_key(
            ctx.workspace_id, request.presentation_id, request.slide_id, request.file_name
        )
        upload = PendingUpload(
            workspace_id=ctx.workspace_id,
            created_by_id=ctx.user_id,
            storage_key=storage_key,
            file_name=request.file_name,
            content_type=request.content_type,
            status=PendingUploadStatusEnum.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=PRESIGN_TTL),
            size_bytes=request.file_size_bytes,
        )
        ctx.session.add(upload)
        await ctx.session.flush()

    upload_url = get_storage_client().generate_presigned_put_url(
        storage_key, request.content_type, PRESIGN_TTL
    )
    return {
        "upload_url": upload_url,
        "pending_upload_client_id": upload.client_id,
        "storage_key": storage_key,
        "expires_in": PRESIGN_TTL,
    }
