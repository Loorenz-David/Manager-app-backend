from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.services.commands.item_economics._common import audit, get_group, translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import parse_production_cost_group_update_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def update_production_cost_group(ctx: ServiceContext) -> dict:
    request = parse_production_cost_group_update_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        group = await get_group(ctx, request.client_id)
        exists = await ctx.session.scalar(
            select(ProductionCostGroup.client_id).where(
                ProductionCostGroup.workspace_id == ctx.workspace_id,
                ProductionCostGroup.name == request.name,
                ProductionCostGroup.client_id != group.client_id,
                ProductionCostGroup.is_deleted.is_(False),
            )
        )
        if exists is not None:
            raise ValidationError("ITEM_COST_GROUP_NAME_TAKEN: group name is already used")
        if request.major_category is not None and request.major_category != group.major_category:
            basis_exists = await ctx.session.scalar(
                select(ProductionCostBasisVersion.client_id)
                .where(ProductionCostBasisVersion.production_cost_group_id == group.client_id)
                .limit(1)
            )
            if basis_exists is not None:
                raise ValidationError(
                    "ITEM_COST_GROUP_CATEGORY_IMMUTABLE: "
                    f"group {group.client_id} already has a basis version and remains {group.major_category.value}"
                )
            category_exists = await ctx.session.scalar(
                select(ProductionCostGroup.client_id).where(
                    ProductionCostGroup.workspace_id == ctx.workspace_id,
                    ProductionCostGroup.major_category == request.major_category,
                    ProductionCostGroup.client_id != group.client_id,
                    ProductionCostGroup.is_deleted.is_(False),
                )
            )
            if category_exists is not None:
                raise ValidationError(
                    f"ITEM_COST_GROUP_CATEGORY_TAKEN: active group already exists for {request.major_category.value}"
                )
        group.name = request.name
        if request.major_category is not None:
            group.major_category = request.major_category
        group.updated_by_id = ctx.user_id
        try:
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        await audit(ctx, "production_cost_group.updated", "production_cost_group", group.client_id)
    return {"production_cost_group": serialize_production_cost_group(group)}
