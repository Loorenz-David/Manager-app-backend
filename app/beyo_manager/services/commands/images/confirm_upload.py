from sqlalchemy import func, select

from beyo_manager.config import settings
from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.domain.images.enums import ImageEventTypeEnum, ImageLinkEntityTypeEnum, ImageSourceReferenceEnum, ImageSourceTypeEnum, ImageStorageProviderEnum
from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_event import ImageEvent
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_ENTITY_EVENT_MAP = {
    ImageLinkEntityTypeEnum.ITEM: ImageEventTypeEnum.UPLOAD_ITEM_IMAGE,
    ImageLinkEntityTypeEnum.CASE: ImageEventTypeEnum.UPLOAD_CASE_IMAGE,
    ImageLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE: ImageEventTypeEnum.UPLOAD_MESSAGE_IMAGE,
}


async def confirm_upload(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    pending_upload_client_id = data.get("pending_upload_client_id")
    entity_type = ImageLinkEntityTypeEnum(data.get("entity_type"))
    entity_client_id = data.get("entity_client_id")

    async with ctx.session.begin():
        upload = await ctx.session.get(PendingUpload, pending_upload_client_id)
        if upload is None:
            raise NotFound("PendingUpload not found")
        if upload.status != PendingUploadStatusEnum.PENDING:
            raise ValidationError("upload already confirmed or expired")

        metadata = get_storage_client().head_object(upload.storage_key)
        if not metadata:
            raise ValidationError("file has not been uploaded yet")

        provider_key = (settings.storage_provider or "").strip().lower()
        provider_map = {
            "s3": ImageStorageProviderEnum.S3,
            "localstack": ImageStorageProviderEnum.S3,
            "local": ImageStorageProviderEnum.EXTERNAL,
        }
        provider = provider_map.get(provider_key)
        if provider is None:
            raise ValidationError(f"Unsupported STORAGE_PROVIDER: {settings.storage_provider!r}")
        source_ref = ImageSourceReferenceEnum.S3_IMAGE_URL if provider == ImageStorageProviderEnum.S3 else None
        image = Image(
            image_url=upload.storage_key,
            storage_provider=provider,
            source_type=ImageSourceTypeEnum.UPLOADED,
            source_reference=source_ref,
            file_size_bytes=metadata["content_length"],
            created_by_id=ctx.user_id,
        )
        ctx.session.add(image)
        await ctx.session.flush()

        next_order = (await ctx.session.execute(
            select(func.count(ImageLink.client_id)).where(
                ImageLink.entity_type == entity_type,
                ImageLink.entity_client_id == entity_client_id,
            )
        )).scalar_one()
        ctx.session.add(ImageLink(image_id=image.client_id, entity_type=entity_type, entity_client_id=entity_client_id, display_order=next_order))

        event = ImageEvent(image_id=image.client_id, type=_ENTITY_EVENT_MAP[entity_type], created_by_id=ctx.user_id)
        ctx.session.add(event)
        await ctx.session.flush()
        image.last_event_id = event.client_id
        upload.status = PendingUploadStatusEnum.CONFIRMED
        upload.size_bytes = metadata["content_length"]
    return {"image": serialize_image(image)}
