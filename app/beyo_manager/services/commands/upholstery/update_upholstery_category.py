from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_update_upholstery_category_request,
)
from beyo_manager.services.context import ServiceContext


async def update_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_category_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.client_id == request.client_id,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFound("Upholstery category not found.")

        if request.name is not None and request.name != category.name:
            name_conflict = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.name == request.name,
                    UpholsteryCategory.is_deleted.is_(False),
                    UpholsteryCategory.client_id != category.client_id,
                )
            )
            if name_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery category with this name already exists in the workspace.")

        if request.name is not None:
            category.name = request.name
        if "image_url" in request.model_fields_set:
            category.image_url = request.image_url
        category.updated_by_id = ctx.user_id

    return {}
