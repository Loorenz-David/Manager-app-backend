from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext


async def create_upholstery(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uph")

    async with ctx.session.begin():
        uph_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Upholstery, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            uph_kwargs["client_id"] = request.client_id

        name_conflict = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.name == request.name,
                Upholstery.is_deleted.is_(False),
            )
        )
        if name_conflict.scalar_one_or_none() is not None:
            raise ConflictError("An upholstery with this name already exists in the workspace.")

        if request.code is not None:
            code_conflict = await ctx.session.execute(
                select(Upholstery).where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.code == request.code,
                    Upholstery.is_deleted.is_(False),
                )
            )
            if code_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery with this code already exists in the workspace.")

        upholstery = Upholstery(
            **uph_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            code=request.code,
            image_url=request.image_url,
            favorite=request.favorite,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(upholstery)
        await ctx.session.flush()

        initial_stock = request.current_stored_amount_meters or Decimal("0")
        if initial_stock <= Decimal("0"):
            inventory_condition = UpholsteryInventoryConditionEnum.OUT_OF_STOCK
        elif (
            request.low_stock_threshold_meters is not None
            and initial_stock <= request.low_stock_threshold_meters
        ):
            inventory_condition = UpholsteryInventoryConditionEnum.LOW_STOCK
        else:
            inventory_condition = UpholsteryInventoryConditionEnum.AVAILABLE

        inventory = UpholsteryInventory(
            workspace_id=ctx.workspace_id,
            upholstery_id=upholstery.client_id,
            inventory_condition=inventory_condition,
            current_stored_amount_meters=initial_stock,
            current_amount_in_need_meters=Decimal("0"),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            low_stock_threshold_meters=request.low_stock_threshold_meters,
            minimum_to_have=request.minimum_to_have,
            maximum_to_have=request.maximum_to_have,
            projected_inventory_value_minor=request.projected_inventory_value_minor,
            currency=request.currency,
            planning_position=request.planning_position,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(inventory)

    return {"upholstery": serialize_upholstery(upholstery, inventory)}
