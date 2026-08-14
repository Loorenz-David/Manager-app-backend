"""Read committed evaluation history and speculative projections for one task."""

from __future__ import annotations

import logging

from sqlalchemy import select

from beyo_manager.domain.item_economics.calculator import REDERIVE_MISMATCH, rederive
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.serializers import serialize_item_cost_evaluation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.context import ServiceContext


logger = logging.getLogger(__name__)


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    if value.__class__.__name__ == "Decimal":
        return str(value)
    return value


async def list_task_evaluations(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_client_id") or ctx.incoming_data.get("task_id")
    task = await ctx.session.scalar(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    if task is None:
        raise NotFound("Task not found.")

    evaluations = list((await ctx.session.scalars(
        select(ItemCostEvaluation).where(
            ItemCostEvaluation.workspace_id == ctx.workspace_id,
            ItemCostEvaluation.task_id == task.client_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.is_deleted.is_(False),
        ).order_by(ItemCostEvaluation.committed_at.desc(), ItemCostEvaluation.client_id.desc())
    )).all())
    projections = list((await ctx.session.scalars(
        select(ItemCostEvaluation).where(
            ItemCostEvaluation.workspace_id == ctx.workspace_id,
            ItemCostEvaluation.task_id == task.client_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.PROJECTION,
            ItemCostEvaluation.is_deleted.is_(False),
        ).order_by(ItemCostEvaluation.created_at.desc(), ItemCostEvaluation.client_id.desc())
    )).all())
    rows = evaluations + projections
    terms_by_evaluation: dict[str, list[ItemCostEvaluationTerm]] = {row.client_id: [] for row in rows}
    if rows:
        term_rows = list((await ctx.session.scalars(
            select(ItemCostEvaluationTerm).where(
                ItemCostEvaluationTerm.workspace_id == ctx.workspace_id,
                ItemCostEvaluationTerm.evaluation_id.in_(terms_by_evaluation),
            ).order_by(ItemCostEvaluationTerm.evaluation_id.asc(), ItemCostEvaluationTerm.created_at.asc(), ItemCostEvaluationTerm.client_id.asc())
        )).all())
        for term in term_rows:
            terms_by_evaluation[term.evaluation_id].append(term)

    def serialize(row: ItemCostEvaluation) -> dict:
        result = rederive(row, terms_by_evaluation[row.client_id])
        error = None
        if isinstance(result, dict) and result.get("marker") == REDERIVE_MISMATCH:
            logger.error(
                "item_economics integrity check failed | evaluation_id=%s error=%s",
                row.client_id,
                REDERIVE_MISMATCH,
            )
            error = _json_safe(result)
        return serialize_item_cost_evaluation(row, terms_by_evaluation[row.client_id], error=error)

    return {
        "evaluations": [serialize(row) for row in evaluations],
        "projections": [serialize(row) for row in projections],
    }
