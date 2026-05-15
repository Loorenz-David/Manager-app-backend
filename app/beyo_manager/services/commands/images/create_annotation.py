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


async def create_annotation(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    ann_type = ImageAnnotationTypeEnum(data.get("annotation_type"))
    payload = data.get("data") or {}
    accuracy = data.get("accuracy")
    if accuracy is not None and not 0 <= accuracy <= 100:
        raise ValidationError("accuracy must be 0-100")
    missing = _REQUIRED_KEYS.get(ann_type, set()) - payload.keys()
    if missing:
        raise ValidationError(f"missing required keys for {ann_type.value}: {sorted(missing)}")
    async with ctx.session.begin():
        image = await ctx.session.get(Image, data.get("image_client_id"))
        if image is None or image.deleted_at is not None:
            raise NotFound("Image not found")
        annotation = ImageAnnotation(image_id=image.client_id, annotation_type=ann_type, data=payload, accuracy=accuracy, created_by_id=ctx.user_id)
        ctx.session.add(annotation)
    return {"client_id": annotation.client_id}
