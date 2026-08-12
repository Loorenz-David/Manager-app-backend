from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.calculator import calculate_cost_per_worker_minute
from beyo_manager.domain.item_economics.serializers import serialize_production_cost_basis_version
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.services.commands.item_economics._common import admission_error, audit, get_group, today_utc, translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import parse_production_cost_basis_version_create_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_production_cost_basis_version(ctx: ServiceContext) -> dict:
    request = parse_production_cost_basis_version_create_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        group = await get_group(ctx, request.production_cost_group_id)
        open_version = await ctx.session.scalar(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.production_cost_group_id == group.client_id,
                ProductionCostBasisVersion.effective_to.is_(None),
                ProductionCostBasisVersion.is_deleted.is_(False),
            )
        )
        today = today_utc()
        admission_error("ITEM_COST_BASIS_VERSION", request.effective_from, open_version, today)
        rate = calculate_cost_per_worker_minute(
            request.fixed_monthly_cost_minor,
            request.monthly_paid_hours,
            request.planning_utilization_percent,
        )
        if open_version is not None:
            open_version.effective_to = request.effective_from
        version = ProductionCostBasisVersion(
            workspace_id=ctx.workspace_id,
            production_cost_group_id=group.client_id,
            effective_from=request.effective_from,
            fixed_monthly_cost_minor=request.fixed_monthly_cost_minor,
            currency=request.currency,
            monthly_paid_hours=request.monthly_paid_hours,
            planning_utilization_percent=request.planning_utilization_percent,
            cost_per_worker_minute_minor=rate,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(version)
        try:
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        await audit(ctx, "production_cost_basis_version.created", "production_cost_basis_version", version.client_id)
    return {"production_cost_basis_version": serialize_production_cost_basis_version(version)}
