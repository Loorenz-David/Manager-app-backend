from sqlalchemy import select

from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client


async def confirm_upload(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    storage_key = data.get("storage_key")
    async with ctx.session.begin():
        upload = (await ctx.session.execute(
            select(PendingUpload).where(
                PendingUpload.storage_key == storage_key,
                PendingUpload.workspace_id == ctx.workspace_id,
                PendingUpload.status == PendingUploadStatusEnum.PENDING,
            )
        )).scalar_one_or_none()
        if upload is None:
            raise NotFound("Upload not found or already confirmed.")

        metadata = get_storage_client().head_object(upload.storage_key)
        if metadata is None:
            raise ValidationError("File was not uploaded successfully. Please try again.")
        if metadata.get("content_type") and metadata["content_type"] != upload.content_type:
            raise ValidationError("Uploaded file content type does not match the requested content type.")

        upload.status = PendingUploadStatusEnum.CONFIRMED
        upload.size_bytes = metadata["content_length"]
    return {"status": "confirmed", "storage_key": upload.storage_key, "size_bytes": upload.size_bytes}
