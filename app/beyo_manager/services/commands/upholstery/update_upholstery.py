from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_update_upholstery_request
from beyo_manager.services.context import ServiceContext


async def update_upholstery(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.client_id == request.client_id,
                Upholstery.is_deleted.is_(False),
            )
        )
        upholstery = result.scalar_one_or_none()
        if upholstery is None:
            raise NotFound("Upholstery not found.")

        if request.name is not None and request.name != upholstery.name:
            name_conflict = await ctx.session.execute(
                select(Upholstery).where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.name == request.name,
                    Upholstery.is_deleted.is_(False),
                    Upholstery.client_id != upholstery.client_id,
                )
            )
            if name_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery with this name already exists in the workspace.")

        if request.code is not None and request.code != upholstery.code:
            code_conflict = await ctx.session.execute(
                select(Upholstery).where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.code == request.code,
                    Upholstery.is_deleted.is_(False),
                    Upholstery.client_id != upholstery.client_id,
                )
            )
            if code_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery with this code already exists in the workspace.")

        if request.name is not None:
            upholstery.name = request.name
        if request.code is not None:
            upholstery.code = request.code
        if request.image_url is not None:
            upholstery.image_url = request.image_url
        if request.favorite is not None:
            upholstery.favorite = request.favorite

        upholstery.updated_by_id = ctx.user_id

        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == upholstery.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory = inv_result.scalar_one_or_none()

    return {"upholstery": serialize_upholstery(upholstery, inventory)}
