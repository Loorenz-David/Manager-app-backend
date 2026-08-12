from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_production_cost_basis_version
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.services.commands.item_economics._common import AfterLock, audit, get_basis
from beyo_manager.services.commands.item_economics.requests import parse_client_id_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_production_cost_basis_version(
    ctx: ServiceContext,
    *,
    after_lock: AfterLock | None = None,
) -> dict:
    """Soft-delete a basis version after the locked reference re-check."""
    request = parse_client_id_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        version = await get_basis(ctx, request.client_id, for_update=True)
        if after_lock is not None:
            await after_lock()
        referenced = await ctx.session.scalar(
            select(ItemCostEvaluation.client_id).where(
                ItemCostEvaluation.production_cost_basis_version_id == version.client_id,
            ).limit(1)
        )
        if referenced is not None:
            raise ValidationError("ITEM_COST_BASIS_VERSION_IN_USE: version is referenced by an evaluation")
        version.is_deleted = True
        version.deleted_at = datetime.now(timezone.utc)
        version.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        await audit(ctx, "production_cost_basis_version.deleted", "production_cost_basis_version", version.client_id)
    return {"production_cost_basis_version": serialize_production_cost_basis_version(version)}
