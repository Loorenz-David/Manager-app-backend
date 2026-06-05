from sqlalchemy import func, select

from beyo_manager.domain.images.enums import ImageEventTypeEnum, ImageLinkEntityTypeEnum, ImageSourceTypeEnum, ImageStorageProviderEnum
from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.models.tables.images.image_event import ImageEvent
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.services.commands.images._annotation_utils import parse_annotation_items
from beyo_manager.services.context import ServiceContext


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

    image_url = _require_non_empty_str(raw_item.get("image_url"), f"{prefix}image_url")
    if not image_url.startswith("http://") and not image_url.startswith("https://"):
        raise ValidationError(f"{prefix}image_url must be an absolute URL starting with http:// or https://")

    entity_type_raw = _require_non_empty_str(raw_item.get("entity_type"), f"{prefix}entity_type")
    try:
        entity_type = ImageLinkEntityTypeEnum(entity_type_raw)
    except ValueError as exc:
        options = ", ".join(sorted(value.value for value in ImageLinkEntityTypeEnum))
        raise ValidationError(f"{prefix}entity_type must be one of: {options}") from exc

    entity_client_id = _require_non_empty_str(raw_item.get("entity_client_id"), f"{prefix}entity_client_id")

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
        "image_url": image_url,
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
        seen_image_ids: set[str] = set()
        for item in normalized_items:
            image_client_id = item.get("image_client_id")
            if image_client_id:
                if image_client_id in seen_image_ids:
                    raise ValidationError("duplicate image_client_id in items")
                seen_image_ids.add(image_client_id)
        return normalized_items, True

    return [_normalize_item(data)], False


async def create_from_url(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    items, is_batch = _normalize_request_items(data)
    serialized_images: list[dict] = []

    async with ctx.session.begin():
        for item in items:
            image_kwargs = {
                "image_url": item["image_url"],
                "storage_provider": ImageStorageProviderEnum.EXTERNAL,
                "source_type": ImageSourceTypeEnum.EXTERNAL_URL,
                "source_reference": None,
                "file_size_bytes": None,
                "width_px": item["width_px"],
                "height_px": item["height_px"],
                "created_by_id": ctx.user_id,
            }
            if item["image_client_id"]:
                image_kwargs["client_id"] = item["image_client_id"]

            image = Image(**image_kwargs)
            ctx.session.add(image)
            await ctx.session.flush()

            next_order = (
                await ctx.session.execute(
                    select(func.count(ImageLink.client_id)).where(
                        ImageLink.entity_type == item["entity_type"],
                        ImageLink.entity_client_id == item["entity_client_id"],
                    )
                )
            ).scalar_one()
            ctx.session.add(
                ImageLink(
                    image_id=image.client_id,
                    entity_type=item["entity_type"],
                    entity_client_id=item["entity_client_id"],
                    display_order=next_order,
                )
            )

            event = ImageEvent(
                image_id=image.client_id,
                type=ImageEventTypeEnum.LINK_EXTERNAL_IMAGE,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(event)
            await ctx.session.flush()
            image.last_event_id = event.client_id
            image.last_event = event

            created_annotations: list[ImageAnnotation] = []
            for annotation_type, annotation_payload, accuracy in item["annotations"]:
                annotation = ImageAnnotation(
                    image_id=image.client_id,
                    annotation_type=annotation_type,
                    data=annotation_payload,
                    accuracy=accuracy,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(annotation)
                created_annotations.append(annotation)
            if created_annotations:
                image.image_annotations = created_annotations

            serialized_images.append(serialize_image(image, include_annotations=bool(created_annotations)))

    if is_batch:
        return {"images": serialized_images}
    return {"image": serialized_images[0]}
