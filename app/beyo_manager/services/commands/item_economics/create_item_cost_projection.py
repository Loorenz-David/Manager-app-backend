"""Create a calculator-backed, soft-deletable item-cost scenario."""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import serialize_item_cost_evaluation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    UNSET,
    _commit_item_cost_evaluation_in_session,
)
from beyo_manager.services.commands.item_economics.requests import (
    parse_create_item_cost_projection_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_item_cost_projection(ctx: ServiceContext) -> dict:
    request = parse_create_item_cost_projection_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        source = None
        if request.source == "committed":
            source = await ctx.session.scalar(
                select(ItemCostEvaluation).where(
                    ItemCostEvaluation.workspace_id == ctx.workspace_id,
                    ItemCostEvaluation.task_id == request.task_client_id,
                    ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                    ItemCostEvaluation.superseded_at.is_(None),
                    ItemCostEvaluation.is_deleted.is_(False),
                )
            )
            if source is None:
                raise NotFound("Current committed evaluation not found.")
        elif request.source == "projection":
            source = await ctx.session.scalar(
                select(ItemCostEvaluation).where(
                    ItemCostEvaluation.workspace_id == ctx.workspace_id,
                    ItemCostEvaluation.task_id == request.task_client_id,
                    ItemCostEvaluation.client_id == request.source_projection_id,
                    ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.PROJECTION,
                    ItemCostEvaluation.is_deleted.is_(False),
                )
            )
            if source is None:
                raise NotFound("Item cost projection not found.")
        source_terms = None
        if source is not None:
            source_terms = list((await ctx.session.scalars(
                select(ItemCostEvaluationTerm).where(
                    ItemCostEvaluationTerm.evaluation_id == source.client_id,
                ).order_by(ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
            )).all())
        evaluation, _ = await _commit_item_cost_evaluation_in_session(
            ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=request.task_client_id,
            user_id=ctx.user_id,
            expected_sale_price_minor=(
                request.expected_sale_price_minor
                if "expected_sale_price_minor" in ctx.incoming_data else UNSET
            ),
            purchase_cost_minor=(
                request.purchase_cost_minor
                if "purchase_cost_minor" in ctx.incoming_data else UNSET
            ),
            label=request.label,
            source_evaluation=source,
            source_terms=source_terms,
            audit_event="item_cost_evaluation.projected",
            kind=ItemCostEvaluationKindEnum.PROJECTION,
        )
        terms = list((await ctx.session.scalars(
            select(ItemCostEvaluationTerm).where(
                ItemCostEvaluationTerm.evaluation_id == evaluation.client_id,
            ).order_by(ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
        )).all())
    return {"evaluation": serialize_item_cost_evaluation(evaluation, terms)}
