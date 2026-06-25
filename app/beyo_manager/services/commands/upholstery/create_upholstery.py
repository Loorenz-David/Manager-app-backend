import logging
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.upholstery.condition_evaluation import evaluate_inventory_condition
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext

logger = logging.getLogger(__name__)


async def create_upholstery(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uph")

    if request.create_category is not None and request.create_category.client_id is not None:
        validate_provided_client_id(request.create_category.client_id, "upc")

    if request.upholstery_inventory_id is not None:
        validate_provided_client_id(request.upholstery_inventory_id, "uin")

    category = None
    async with ctx.session.begin():
        uph_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Upholstery, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            uph_kwargs["client_id"] = request.client_id

        inv_kwargs: dict[str, str] = {}
        if request.upholstery_inventory_id is not None:
            dup_inv = await ctx.session.get(UpholsteryInventory, request.upholstery_inventory_id)
            if dup_inv is not None:
                raise ConflictError("Provided upholstery_inventory_id is already in use.")
            inv_kwargs["client_id"] = request.upholstery_inventory_id

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

        resolved_category_id: str | None = None

        if request.create_category is not None:
            cat_req = request.create_category

            if cat_req.client_id is not None:
                dup_cat = await ctx.session.get(UpholsteryCategory, cat_req.client_id)
                if dup_cat is not None:
                    raise ConflictError("Provided category client_id is already in use.")

            cat_name_conflict = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.name == cat_req.name,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            if cat_name_conflict.scalar_one_or_none() is not None:
                raise ConflictError(
                    "An upholstery category with this name already exists in the workspace."
                )

            cat_kwargs: dict[str, str] = {}
            if cat_req.client_id is not None:
                cat_kwargs["client_id"] = cat_req.client_id

            category = UpholsteryCategory(
                **cat_kwargs,
                workspace_id=ctx.workspace_id,
                name=cat_req.name,
                image_url=cat_req.image_url,
                favorite=cat_req.favorite,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(category)
            await ctx.session.flush()
            resolved_category_id = category.client_id
        elif request.upholstery_category_id is not None:
            category_result = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.client_id == request.upholstery_category_id,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            category = category_result.scalar_one_or_none()
            if category is None:
                raise NotFound("Upholstery category not found.")
            resolved_category_id = category.client_id
        elif request.upholstery_category_name is not None:
            logger.info("[create_upholstery] entering upholstery_category_name branch — name=%r", request.upholstery_category_name)
            cat_by_name = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.name == request.upholstery_category_name,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            category = cat_by_name.scalar_one_or_none()
            logger.info("[create_upholstery] category lookup result — found=%r", category is not None)
            if category is None:
                logger.info("[create_upholstery] creating new category — name=%r", request.upholstery_category_name)
                category = UpholsteryCategory(
                    workspace_id=ctx.workspace_id,
                    name=request.upholstery_category_name,
                    image_url=request.image_url,
                    favorite=False,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(category)
                await ctx.session.flush()
                logger.info("[create_upholstery] new category flushed — client_id=%r", category.client_id)
            resolved_category_id = category.client_id
            logger.info("[create_upholstery] resolved_category_id=%r", resolved_category_id)

        upholstery = Upholstery(
            **uph_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            code=request.code,
            image_url=request.image_url,
            favorite=request.favorite,
            upholstery_category_id=resolved_category_id,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(upholstery)
        await ctx.session.flush()

        initial_stock = request.current_stored_amount_meters or Decimal("0")
        inventory_condition = evaluate_inventory_condition(
            stored=initial_stock,
            in_need=Decimal("0"),
            threshold=request.low_stock_threshold_meters,
        )

        inventory = UpholsteryInventory(
            **inv_kwargs,
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

    return {"upholstery": serialize_upholstery(upholstery, inventory, category)}
