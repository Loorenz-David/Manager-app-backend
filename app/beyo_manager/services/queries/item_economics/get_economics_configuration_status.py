from sqlalchemy import select

from beyo_manager.domain.item_economics.configuration import resolve_economics_configuration
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.services.commands.item_economics._common import today_utc
from beyo_manager.services.context import ServiceContext


async def get_economics_configuration_status(ctx: ServiceContext) -> dict:
    groups = (
        await ctx.session.execute(
            select(ProductionCostGroup).where(
                ProductionCostGroup.workspace_id == ctx.workspace_id,
                ProductionCostGroup.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    basis_versions = (
        await ctx.session.execute(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    model_versions = (
        await ctx.session.execute(
            select(CostModelVersion).where(
                CostModelVersion.workspace_id == ctx.workspace_id,
                CostModelVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    today = today_utc()
    status = resolve_economics_configuration(groups, basis_versions, model_versions, today)
    one_group = groups[0] if len(groups) == 1 else None
    has_open_basis = bool(
        one_group is not None
        and any(
            version.production_cost_group_id == one_group.client_id
            and version.effective_to is None
            and not version.is_deleted
            for version in basis_versions
        )
    )
    has_open_model = any(version.effective_to is None and not version.is_deleted for version in model_versions)
    evaluable = status.value == "ok"
    return {
        "group_count": len(groups),
        "has_cost_group": bool(groups),
        "has_open_basis_version": has_open_basis,
        "has_open_cost_model_version": has_open_model,
        "evaluable": evaluable,
        "first_failure": None if evaluable else status.value,
    }
