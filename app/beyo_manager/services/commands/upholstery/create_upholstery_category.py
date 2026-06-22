from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_create_upholstery_category_request,
)
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext


async def create_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_category_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "upc")

    async with ctx.session.begin():
        if request.client_id is not None:
            dup = await ctx.session.get(UpholsteryCategory, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")

        name_conflict = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.name == request.name,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        if name_conflict.scalar_one_or_none() is not None:
            raise ConflictError("An upholstery category with this name already exists in the workspace.")

        cat_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            cat_kwargs["client_id"] = request.client_id

        category = UpholsteryCategory(
            **cat_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            image_url=request.image_url,
            favorite=request.favorite,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(category)

    return {"upholstery_category": serialize_upholstery_category(category, upholstery_count=0)}
