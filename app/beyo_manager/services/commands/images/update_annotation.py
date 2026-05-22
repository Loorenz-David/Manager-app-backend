from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
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


def _normalize_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict) -> dict:
    if annotation_type == ImageAnnotationTypeEnum.ARROW:
        normalized = dict(payload)
        if "from" not in normalized and {"fromX", "fromY"}.issubset(normalized.keys()):
            normalized["from"] = {"x": normalized["fromX"], "y": normalized["fromY"]}
        if "to" not in normalized and {"toX", "toY"}.issubset(normalized.keys()):
            normalized["to"] = {"x": normalized["toX"], "y": normalized["toY"]}
        return normalized
    return payload


def _validate_payload_for_type(annotation_type: ImageAnnotationTypeEnum, payload: dict) -> None:
    missing = _REQUIRED_KEYS.get(annotation_type, set()) - payload.keys()
    if missing:
        raise ValidationError(f"missing required keys for {annotation_type.value}: {sorted(missing)}")


async def update_annotation(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    image_client_id = data.get("image_client_id")
    annotation_client_id = data.get("annotation_client_id")
    payload = data.get("data") or {}

    if not isinstance(payload, dict):
        raise ValidationError("data must be an object")

    has_accuracy = "accuracy" in data
    accuracy = data.get("accuracy")
    if has_accuracy and accuracy is not None and not 0 <= accuracy <= 100:
        raise ValidationError("accuracy must be 0-100")

    async with ctx.session.begin():
        annotation = await ctx.session.get(ImageAnnotation, annotation_client_id)
        if annotation is None or annotation.image_id != image_client_id:
            raise NotFound("Image annotation not found")

        normalized_payload = _normalize_payload_for_type(annotation.annotation_type, payload)
        _validate_payload_for_type(annotation.annotation_type, normalized_payload)

        annotation.data = normalized_payload
        if has_accuracy:
            annotation.accuracy = accuracy

    return {"client_id": annotation.client_id, "updated": True}
