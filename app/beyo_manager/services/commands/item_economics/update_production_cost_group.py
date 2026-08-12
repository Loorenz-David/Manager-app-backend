from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
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
        group.name = request.name
        group.updated_by_id = ctx.user_id
        try:
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        await audit(ctx, "production_cost_group.updated", "production_cost_group", group.client_id)
    return {"production_cost_group": serialize_production_cost_group(group)}
