from beyo_manager.domain.images.enums import ImageAnnotationTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.services.commands.images._annotation_utils import (
    normalize_payload_for_type,
    parse_annotation_items,
    parse_annotation_type,
    validate_payload_for_type,
)
from beyo_manager.services.context import ServiceContext


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
        annotations_to_create = parse_annotation_items(batch_items, prefix="items")

        async with ctx.session.begin():
            image = await ctx.session.get(Image, data.get("image_client_id"))
            if image is None or image.deleted_at is not None:
                raise NotFound("Image not found")

            created_annotations: list[ImageAnnotation] = []
            for annotation_type, annotation_payload, item_accuracy in annotations_to_create:
                annotation = ImageAnnotation(
                    image_id=image.client_id,
                    annotation_type=annotation_type,
                    data=annotation_payload,
                    accuracy=item_accuracy if item_accuracy is not None else accuracy,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(annotation)
                created_annotations.append(annotation)

        return {"created_annotation_client_ids": [annotation.client_id for annotation in created_annotations]}

    ann_type = parse_annotation_type(data.get("annotation_type"), field_name="annotation_type")
    normalized_payload = normalize_payload_for_type(ann_type, payload)
    validate_payload_for_type(ann_type, normalized_payload)

    async with ctx.session.begin():
        image = await ctx.session.get(Image, data.get("image_client_id"))
        if image is None or image.deleted_at is not None:
            raise NotFound("Image not found")
        annotation = ImageAnnotation(image_id=image.client_id, annotation_type=ann_type, data=normalized_payload, accuracy=accuracy, created_by_id=ctx.user_id)
        ctx.session.add(annotation)
    return {"client_id": annotation.client_id}
