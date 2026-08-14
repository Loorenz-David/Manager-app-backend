"""Promote a live projection through the same commit procedure."""

from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import serialize_item_cost_evaluation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    _commit_item_cost_evaluation_in_session,
)
from beyo_manager.services.commands.item_economics.requests import parse_client_id_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus


async def promote_item_cost_projection(ctx: ServiceContext) -> dict:
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
        source_terms = list((await ctx.session.scalars(
            select(ItemCostEvaluationTerm).where(
                ItemCostEvaluationTerm.evaluation_id == projection.client_id,
            ).order_by(ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
        )).all())
        evaluation, pending_events = await _commit_item_cost_evaluation_in_session(
            ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=projection.task_id,
            user_id=ctx.user_id,
            label=projection.label,
            promoted_from_id=projection.client_id,
            source_evaluation=projection,
            source_terms=source_terms,
            audit_event="item_cost_evaluation.promoted",
        )
        terms = list((await ctx.session.scalars(
            select(ItemCostEvaluationTerm).where(
                ItemCostEvaluationTerm.evaluation_id == evaluation.client_id,
            ).order_by(ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
        )).all())
    await event_bus.dispatch(pending_events)
    return {"evaluation": serialize_item_cost_evaluation(evaluation, terms)}
