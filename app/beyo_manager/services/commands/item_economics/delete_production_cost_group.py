from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group_section import ProductionCostGroupSection
from beyo_manager.services.commands.item_economics._common import audit, get_group
from beyo_manager.services.commands.item_economics.requests import parse_client_id_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_production_cost_group(ctx: ServiceContext) -> dict:
    request = parse_client_id_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        group = await get_group(ctx, request.client_id)
        in_use = await ctx.session.scalar(
            select(ProductionCostBasisVersion.client_id).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.production_cost_group_id == group.client_id,
                ProductionCostBasisVersion.is_deleted.is_(False),
            ).limit(1)
        )
        if in_use is None:
            in_use = await ctx.session.scalar(
                select(ProductionCostGroupSection.client_id).where(
                    ProductionCostGroupSection.workspace_id == ctx.workspace_id,
                    ProductionCostGroupSection.production_cost_group_id == group.client_id,
                    ProductionCostGroupSection.removed_at.is_(None),
                ).limit(1)
            )
        if in_use is not None:
            raise ValidationError("ITEM_COST_GROUP_IN_USE: group has active configuration")
        group.is_deleted = True
        group.deleted_at = datetime.now(timezone.utc)
        group.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        await audit(ctx, "production_cost_group.deleted", "production_cost_group", group.client_id)
    return {"production_cost_group": serialize_production_cost_group(group)}
