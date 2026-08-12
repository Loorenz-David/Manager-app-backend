from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group_section
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.production_cost_group_section import ProductionCostGroupSection
from beyo_manager.services.commands.item_economics._common import audit, get_group
from beyo_manager.services.commands.item_economics.requests import parse_remove_section_from_cost_group_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def remove_section_from_cost_group(ctx: ServiceContext) -> dict:
    request = parse_remove_section_from_cost_group_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        group = await get_group(ctx, request.production_cost_group_id)
        membership = await ctx.session.scalar(
            select(ProductionCostGroupSection).where(
                ProductionCostGroupSection.workspace_id == ctx.workspace_id,
                ProductionCostGroupSection.production_cost_group_id == group.client_id,
                ProductionCostGroupSection.working_section_id == request.working_section_id,
                ProductionCostGroupSection.removed_at.is_(None),
            )
        )
        if membership is None:
            raise NotFound("Active group membership not found.")
        membership.removed_at = datetime.now(timezone.utc)
        membership.removed_by_id = ctx.user_id
        await ctx.session.flush()
        await audit(ctx, "production_cost_group_section.removed", "production_cost_group_section", membership.client_id)
    return {"production_cost_group_section": serialize_production_cost_group_section(membership)}
