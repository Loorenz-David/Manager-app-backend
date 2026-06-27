from sqlalchemy import func, select

from beyo_manager.config import settings
from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.domain.images.enums import ImageEventTypeEnum, ImageLinkEntityTypeEnum, ImageSourceReferenceEnum, ImageSourceTypeEnum, ImageStorageProviderEnum
from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.services.commands.images._annotation_utils import parse_annotation_items
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.models.tables.images.image_event import ImageEvent
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client

_ENTITY_EVENT_MAP = {
    ImageLinkEntityTypeEnum.ITEM: ImageEventTypeEnum.UPLOAD_ITEM_IMAGE,
    ImageLinkEntityTypeEnum.CASE: ImageEventTypeEnum.UPLOAD_CASE_IMAGE,
    ImageLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE: ImageEventTypeEnum.UPLOAD_MESSAGE_IMAGE,
    ImageLinkEntityTypeEnum.ITEM_CATEGORY: ImageEventTypeEnum.UPLOAD_ITEM_IMAGE,
    ImageLinkEntityTypeEnum.NOTE: ImageEventTypeEnum.UPLOAD_NOTE_IMAGE,
}


def _require_non_empty_str(raw_value: object, field_name: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValidationError(f"{field_name} is required")
    return raw_value.strip()


def _parse_positive_int(raw_value: object, field_name: str) -> int | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool) or not isinstance(raw_value, int) or raw_value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer")
    return raw_value


def _normalize_item(raw_item: object, *, prefix: str = "") -> dict:
    if not isinstance(raw_item, dict):
        raise ValidationError(f"{prefix.rstrip('.')} must be an object")

    pending_upload_client_id = _require_non_empty_str(raw_item.get("pending_upload_client_id"), f"{prefix}pending_upload_client_id")
    entity_type_raw = _require_non_empty_str(raw_item.get("entity_type"), f"{prefix}entity_type")
    entity_client_id = _require_non_empty_str(raw_item.get("entity_client_id"), f"{prefix}entity_client_id")

    try:
        entity_type = ImageLinkEntityTypeEnum(entity_type_raw)
    except ValueError as exc:
        options = ", ".join(sorted(value.value for value in ImageLinkEntityTypeEnum))
        raise ValidationError(f"{prefix}entity_type must be one of: {options}") from exc

    image_client_id = raw_item.get("image_client_id")
    if image_client_id is not None:
        image_client_id = _require_non_empty_str(image_client_id, f"{prefix}image_client_id")
        if not image_client_id.startswith("img_"):
            raise ValidationError(f"{prefix}image_client_id must start with 'img_'")

    width_px = _parse_positive_int(raw_item.get("width_px"), f"{prefix}width_px")
    height_px = _parse_positive_int(raw_item.get("height_px"), f"{prefix}height_px")

    raw_annotations = raw_item.get("image_annotations")
    annotations: list[tuple] = []
    if raw_annotations:
        annotations = parse_annotation_items(raw_annotations, prefix=f"{prefix}image_annotations")

    return {
        "pending_upload_client_id": pending_upload_client_id,
        "entity_type": entity_type,
        "entity_client_id": entity_client_id,
        "image_client_id": image_client_id,
        "width_px": width_px,
        "height_px": height_px,
        "annotations": annotations,
    }


def _normalize_request_items(data: dict) -> tuple[list[dict], bool]:
    raw_items = data.get("items")
    if raw_items is not None:
        if not isinstance(raw_items, list):
            raise ValidationError("items must be an array")
        if not raw_items:
            raise ValidationError("items must not be empty")

        normalized_items = [_normalize_item(item, prefix=f"items[{index}].") for index, item in enumerate(raw_items)]
        seen_pending_uploads: set[str] = set()
        seen_image_ids: set[str] = set()
        for item in normalized_items:
            pending_upload_client_id = item["pending_upload_client_id"]
            if pending_upload_client_id in seen_pending_uploads:
                raise ValidationError("duplicate pending_upload_client_id in items")
            seen_pending_uploads.add(pending_upload_client_id)

            image_client_id = item.get("image_client_id")
            if image_client_id:
                if image_client_id in seen_image_ids:
                    raise ValidationError("duplicate image_client_id in items")
                seen_image_ids.add(image_client_id)
        return normalized_items, True

    return [_normalize_item(data)], False


def _resolve_storage_provider() -> tuple[ImageStorageProviderEnum, ImageSourceReferenceEnum | None]:
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
    return provider, source_ref


async def confirm_upload(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    items, is_batch = _normalize_request_items(data)
    provider, source_ref = _resolve_storage_provider()
    created_images: list[Image] = []

    async with ctx.session.begin():
        for item in items:
            upload = await ctx.session.get(PendingUpload, item["pending_upload_client_id"])
            if upload is None:
                raise NotFound("PendingUpload not found")
            if upload.status != PendingUploadStatusEnum.PENDING:
                raise ValidationError("upload already confirmed or expired")

            metadata = get_storage_client().head_object(upload.storage_key)
            if not metadata:
                raise ValidationError("file has not been uploaded yet")

            image_kwargs = {
                "image_url": upload.storage_key,
                "storage_provider": provider,
                "source_type": ImageSourceTypeEnum.UPLOADED,
                "source_reference": source_ref,
                "file_size_bytes": metadata["content_length"],
                "width_px": item["width_px"],
                "height_px": item["height_px"],
                "created_by_id": ctx.user_id,
            }
            if item["image_client_id"]:
                image_kwargs["client_id"] = item["image_client_id"]

            image = Image(**image_kwargs)
            ctx.session.add(image)
            await ctx.session.flush()

            next_order = (await ctx.session.execute(
                select(func.count(ImageLink.client_id)).where(
                    ImageLink.entity_type == item["entity_type"],
                    ImageLink.entity_client_id == item["entity_client_id"],
                )
            )).scalar_one()
            ctx.session.add(
                ImageLink(
                    image_id=image.client_id,
                    entity_type=item["entity_type"],
                    entity_client_id=item["entity_client_id"],
                    display_order=next_order,
                )
            )

            event_type = _ENTITY_EVENT_MAP.get(item["entity_type"])
            if event_type is None:
                raise ValidationError(f"Unsupported entity_type for image upload event: {item['entity_type']}")
            event = ImageEvent(image_id=image.client_id, type=event_type, created_by_id=ctx.user_id)
            ctx.session.add(event)
            await ctx.session.flush()
            image.last_event_id = event.client_id

            for annotation_type, annotation_payload, accuracy in item["annotations"]:
                ctx.session.add(
                    ImageAnnotation(
                        image_id=image.client_id,
                        annotation_type=annotation_type,
                        data=annotation_payload,
                        accuracy=accuracy,
                        created_by_id=ctx.user_id,
                    )
                )

            upload.status = PendingUploadStatusEnum.CONFIRMED
            upload.size_bytes = metadata["content_length"]
            created_images.append(image)

    if is_batch:
        return {"images": [serialize_image(image) for image in created_images]}
    return {"image": serialize_image(created_images[0])}
