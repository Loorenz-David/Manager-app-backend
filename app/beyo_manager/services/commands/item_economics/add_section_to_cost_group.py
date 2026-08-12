from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_group_section
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.production_cost_group_section import ProductionCostGroupSection
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics._common import audit, get_group, translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import parse_add_section_to_cost_group_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def add_section_to_cost_group(ctx: ServiceContext) -> dict:
    request = parse_add_section_to_cost_group_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        group = await get_group(ctx, request.production_cost_group_id)
        section = await ctx.session.scalar(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id == request.working_section_id,
                WorkingSection.is_deleted.is_(False),
            )
        )
        if section is None:
            raise NotFound("Working section not found.")
        active = await ctx.session.scalar(
            select(ProductionCostGroupSection.client_id).where(
                ProductionCostGroupSection.workspace_id == ctx.workspace_id,
                ProductionCostGroupSection.working_section_id == section.client_id,
                ProductionCostGroupSection.removed_at.is_(None),
            )
        )
        if active is not None:
            raise ValidationError("ITEM_COST_SECTION_ALREADY_GROUPED: section already belongs to a group")
        membership = ProductionCostGroupSection(
            workspace_id=ctx.workspace_id,
            production_cost_group_id=group.client_id,
            working_section_id=section.client_id,
            added_by_id=ctx.user_id,
        )
        ctx.session.add(membership)
        try:
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        await audit(ctx, "production_cost_group_section.added", "production_cost_group_section", membership.client_id)
    return {"production_cost_group_section": serialize_production_cost_group_section(membership)}
