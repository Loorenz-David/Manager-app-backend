from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.services.context import ServiceContext

_REQUIRED_KEYS = {
    ImageAnnotationTypeEnum.DRAW: {"points", "color"},
    ImageAnnotationTypeEnum.ARROW: {"from", "to"},
    ImageAnnotationTypeEnum.CIRCLE: {"cx", "cy", "r"},
    ImageAnnotationTypeEnum.RECTANGLE: {"x", "y", "w", "h"},
    ImageAnnotationTypeEnum.TEXT: {"x", "y", "text"},
    ImageAnnotationTypeEnum.MEASUREMENT: {"from", "to", "unit", "value"},
    ImageAnnotationTypeEnum.HIGHLIGHT: {"x", "y", "w", "h"},
}

_ANNOTATION_TYPE_VALUES = ", ".join(sorted(annotation_type.value for annotation_type in ImageAnnotationTypeEnum))


def _parse_annotation_type(raw_value: str | None, *, field_name: str) -> ImageAnnotationTypeEnum:
    if not raw_value:
        raise ValidationError(f"{field_name} is required")
    try:
        return ImageAnnotationTypeEnum(raw_value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be one of: {_ANNOTATION_TYPE_VALUES}") from exc


def _validate_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict, *, prefix: str = "") -> None:
    missing = _REQUIRED_KEYS.get(annotation_type, set()) - payload.keys()
    if missing:
        raise ValidationError(f"{prefix}missing required keys for {annotation_type.value}: {sorted(missing)}")


def _normalize_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict) -> dict:
    # Frontend arrow drawings may send scalar endpoints instead of nested points.
    # Normalize to backend canonical keys while preserving original fields.
    if annotation_type == ImageAnnotationTypeEnum.ARROW:
        normalized = dict(payload)
        if "from" not in normalized and {"fromX", "fromY"}.issubset(normalized.keys()):
            normalized["from"] = {"x": normalized["fromX"], "y": normalized["fromY"]}
        if "to" not in normalized and {"toX", "toY"}.issubset(normalized.keys()):
            normalized["to"] = {"x": normalized["toX"], "y": normalized["toY"]}
        return normalized
    return payload


async def create_annotation(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    payload = data.get("data") or {}
    if not isinstance(payload, dict):
        raise ValidationError("data must be an object")

    accuracy = data.get("accuracy")
    if accuracy is not None and not 0 <= accuracy <= 100:
        raise ValidationError("accuracy must be 0-100")

    batch_items = payload.get("items")
    if batch_items is not None:
        if not isinstance(batch_items, list):
            raise ValidationError("data.items must be an array when provided")
        if not batch_items:
            raise ValidationError("data.items must not be empty")

        annotations_to_create: list[tuple[ImageAnnotationTypeEnum, dict]] = []
        for index, item in enumerate(batch_items):
            if not isinstance(item, dict):
                raise ValidationError(f"items[{index}] must be an object")
            item_type = _parse_annotation_type(item.get("tool"), field_name=f"items[{index}].tool")
            normalized_item = _normalize_payload_for_type(item_type, item)
            _validate_payload_for_type(item_type, normalized_item, prefix=f"items[{index}] ")
            annotations_to_create.append((item_type, normalized_item))

        async with ctx.session.begin():
            image = await ctx.session.get(Image, data.get("image_client_id"))
            if image is None or image.deleted_at is not None:
                raise NotFound("Image not found")

            created_annotations: list[ImageAnnotation] = []
            for annotation_type, annotation_payload in annotations_to_create:
                annotation = ImageAnnotation(
                    image_id=image.client_id,
                    annotation_type=annotation_type,
                    data=annotation_payload,
                    accuracy=accuracy,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(annotation)
                created_annotations.append(annotation)

        return {"created_annotation_client_ids": [annotation.client_id for annotation in created_annotations]}

    ann_type = _parse_annotation_type(data.get("annotation_type"), field_name="annotation_type")
    normalized_payload = _normalize_payload_for_type(ann_type, payload)
    _validate_payload_for_type(ann_type, normalized_payload)

    async with ctx.session.begin():
        image = await ctx.session.get(Image, data.get("image_client_id"))
        if image is None or image.deleted_at is not None:
            raise NotFound("Image not found")
        annotation = ImageAnnotation(image_id=image.client_id, annotation_type=ann_type, data=normalized_payload, accuracy=accuracy, created_by_id=ctx.user_id)
        ctx.session.add(annotation)
    return {"client_id": annotation.client_id}
