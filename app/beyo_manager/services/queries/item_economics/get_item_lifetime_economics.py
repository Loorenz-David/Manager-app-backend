"""Read the item-scoped economics episodes without merging task results."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import (
    serialize_item_cost_evaluation,
    serialize_item_cost_result,
    serialize_item_lifetime_economics,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def get_item_lifetime_economics(ctx: ServiceContext) -> dict:
    item_id = ctx.incoming_data.get("item_client_id")
    item = await ctx.session.scalar(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == item_id,
            Item.is_deleted.is_(False),
        )
    )
    if item is None:
        raise NotFound("Item not found.")

    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    evaluations = list(
        (
            await ctx.session.scalars(
                select(ItemCostEvaluation)
                .where(
                    ItemCostEvaluation.workspace_id == ctx.workspace_id,
                    ItemCostEvaluation.item_id == item.client_id,
                    ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                    ItemCostEvaluation.superseded_at.is_(None),
                    ItemCostEvaluation.is_deleted.is_(False),
                )
                .order_by(
                    ItemCostEvaluation.committed_at.desc(),
                    ItemCostEvaluation.client_id.desc(),
                )
                .offset(offset)
                .limit(limit + 1)
            )
        ).all()
    )
    has_more = len(evaluations) > limit
    evaluations = evaluations[:limit]
    result_rows: dict[str, ItemCostResult] = {}
    if evaluations:
        results = await ctx.session.scalars(
            select(ItemCostResult).where(
                ItemCostResult.workspace_id == ctx.workspace_id,
                ItemCostResult.task_id.in_([row.task_id for row in evaluations]),
            )
        )
        result_rows = {row.task_id: row for row in results.all()}

    episodes: list[dict] = []
    total_seconds = 0
    total_minutes = Decimal("0.00")
    total_consumed = 0
    total_variance_minutes = Decimal("0.00")
    total_variance_cost = 0
    for evaluation in evaluations:
        result = result_rows.get(evaluation.task_id)
        serialized_result = serialize_item_cost_result(result) if result is not None else None
        episodes.append(
            {
                "task_id": evaluation.task_id,
                "task_type_snapshot": evaluation.task_type_snapshot.value,
                "return_source_snapshot": (
                    evaluation.return_source_snapshot.value
                    if evaluation.return_source_snapshot is not None
                    else None
                ),
                "evaluation": serialize_item_cost_evaluation(evaluation, []),
                "result": serialized_result,
            }
        )
        if result is not None:
            total_seconds += result.actual_worker_seconds
            total_minutes += Decimal(result.actual_worker_minutes)
            total_consumed += result.consumed_cost_minor
            total_variance_minutes += Decimal(result.variance_worker_minutes)
            total_variance_cost += result.variance_cost_minor

    return serialize_item_lifetime_economics(
        episodes,
        {
            "actual_worker_seconds": total_seconds,
            "actual_worker_minutes": str(total_minutes),
            "consumed_cost_minor": total_consumed,
            "variance_worker_minutes": str(total_variance_minutes),
            "variance_cost_minor": total_variance_cost,
        },
        limit=limit,
        offset=offset,
        has_more=has_more,
    )
