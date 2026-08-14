"""Soft-delete a projection without touching committed evaluation history."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import serialize_item_cost_evaluation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.services.commands.item_economics._common import audit
from beyo_manager.services.commands.item_economics.requests import parse_client_id_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item_cost_projection(ctx: ServiceContext) -> dict:
    request = parse_client_id_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        projection = await ctx.session.scalar(
            select(ItemCostEvaluation).where(
                ItemCostEvaluation.workspace_id == ctx.workspace_id,
                ItemCostEvaluation.client_id == request.client_id,
                ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.PROJECTION,
                ItemCostEvaluation.is_deleted.is_(False),
            )
        )
        if projection is None:
            raise NotFound("Item cost projection not found.")
        projection.is_deleted = True
        projection.deleted_at = datetime.now(timezone.utc)
        projection.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        await audit(ctx, "item_cost_evaluation.deleted", "item_cost_evaluation", projection.client_id)
    return {"evaluation": serialize_item_cost_evaluation(projection)}
