"""Worker/seller budget status with an explicit money-free result surface."""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_status import (
    TaskBudgetStatus,
    _build_evaluated_status,
    _empty_status,
    _load_task_and_item,
)
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.domain.item_economics.configuration import resolve_item_economics_status
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs


async def get_task_budget_status_worker(ctx: ServiceContext) -> TaskBudgetStatus:
    task, item = await _load_task_and_item(ctx)
    # Keep this literal boundary local to the worker service. It is a separate
    # money-redaction producer and must not inherit a future manager change.
    evaluation = await ctx.session.scalar(
        select(ItemCostEvaluation).where(
            ItemCostEvaluation.workspace_id == ctx.workspace_id,
            ItemCostEvaluation.task_id == task.client_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.superseded_at.is_(None),
            ItemCostEvaluation.is_deleted.is_(False),
        )
    )
    binding = "detached" if item is None else ("bound" if evaluation is None or evaluation.item_id == item.client_id else "mismatched")
    if evaluation is None:
        if item is None:
            return _empty_status(EconomicsStatusEnum.NOT_EVALUATED, binding=binding, item_id=None)
        selection, terms = await _load_preview_inputs(ctx, item, now=ctx.now)
        valuation = await ctx.session.scalar(
            select(ItemValuation).where(
                ItemValuation.workspace_id == ctx.workspace_id,
                ItemValuation.item_id == item.client_id,
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        )
        return _empty_status(
            resolve_item_economics_status(valuation, selection, terms),
            binding=binding,
            item_id=item.client_id,
        )
    return await _build_evaluated_status(ctx, task, item, evaluation, binding)
