from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image_annotation import ImageAnnotation
from beyo_manager.services.context import ServiceContext


async def delete_annotation(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    image_client_id = data.get("image_client_id")
    annotation_client_id = data.get("annotation_client_id")

    async with ctx.session.begin():
        annotation = await ctx.session.get(ImageAnnotation, annotation_client_id)
        if annotation is None or annotation.image_id != image_client_id:
            raise NotFound("Image annotation not found")
        await ctx.session.delete(annotation)

    return {"client_id": annotation_client_id, "deleted": True}
