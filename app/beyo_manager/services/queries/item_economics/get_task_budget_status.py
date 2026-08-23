"""Manager-facing live budget status for one task."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from collections.abc import Mapping

from sqlalchemy import select

from beyo_manager.domain.item_economics.calculator import (
    calculate_actual_worker_minutes,
    calculate_consumed_cost_minor,
    calculate_percent_consumed,
    calculate_remaining_worker_minutes,
    calculate_variance_cost_minor,
    calculate_variance_worker_minutes,
)
from beyo_manager.domain.item_economics.configuration import resolve_item_economics_status
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum, ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.typical_filters import (
    TypicalFilterSpec,
    derive_spec_from_primary_item,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import load_live_worked_seconds


@dataclass
class TaskBudgetStatus:
    status: EconomicsStatusEnum
    item_binding: str
    actual_worker_seconds: int | None
    actual_worker_minutes: Decimal | None
    remaining_worker_minutes: Decimal | None
    percent_consumed: Decimal | None
    variance_worker_minutes: Decimal | None
    production_budget_minor: int | None
    allowed_worker_minutes: Decimal | None
    consumed_cost_minor: int | None
    variance_cost_minor: int | None
    evaluation_id: str | None
    item_id: str | None
    result: ItemCostResult | None
    typical_filter_spec: TypicalFilterSpec | None = None


async def _load_task_and_item(ctx: ServiceContext) -> tuple[Task, Item | None]:
    task = await ctx.session.scalar(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == ctx.incoming_data.get("task_client_id"),
            Task.is_deleted.is_(False),
        )
    )
    if task is None:
        raise NotFound("Task not found.")
    primary = await ctx.session.scalar(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id == task.client_id,
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskItem.removed_at.is_(None),
        )
    )
    if primary is None:
        return task, None
    item = await ctx.session.scalar(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == primary.item_id,
            Item.is_deleted.is_(False),
        )
    )
    return task, item


def _empty_status(
    status: EconomicsStatusEnum,
    *,
    binding: str,
    item_id: str | None,
    typical_filter_spec: TypicalFilterSpec | None,
) -> TaskBudgetStatus:
    return TaskBudgetStatus(
        status=status,
        item_binding=binding,
        actual_worker_seconds=None,
        actual_worker_minutes=None,
        remaining_worker_minutes=None,
        percent_consumed=None,
        variance_worker_minutes=None,
        production_budget_minor=None,
        allowed_worker_minutes=None,
        consumed_cost_minor=None,
        variance_cost_minor=None,
        evaluation_id=None,
        item_id=item_id,
        result=None,
        typical_filter_spec=typical_filter_spec,
    )


async def get_task_budget_status(
    ctx: ServiceContext,
    *,
    live_seconds: Mapping[str, int] | None = None,
) -> TaskBudgetStatus:
    task, item = await _load_task_and_item(ctx)
    typical_filter_spec = None if item is None else derive_spec_from_primary_item(item)
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
            return _empty_status(
                EconomicsStatusEnum.NOT_EVALUATED,
                binding=binding,
                item_id=None,
                typical_filter_spec=typical_filter_spec,
            )
        selection, terms = await _load_preview_inputs(ctx, item, now=ctx.now)
        valuation = await ctx.session.scalar(
            select(ItemValuation).where(
                ItemValuation.workspace_id == ctx.workspace_id,
                ItemValuation.item_id == item.client_id,
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        )
        status = resolve_item_economics_status(valuation, selection, terms)
        return _empty_status(
            status,
            binding=binding,
            item_id=item.client_id,
            typical_filter_spec=typical_filter_spec,
        )

    return await _build_evaluated_status(
        ctx,
        task,
        item,
        evaluation,
        binding,
        typical_filter_spec=typical_filter_spec,
        live_seconds=live_seconds,
    )


async def _build_evaluated_status(
    ctx: ServiceContext,
    task: Task,
    item: Item | None,
    evaluation: ItemCostEvaluation,
    binding: str,
    *,
    typical_filter_spec: TypicalFilterSpec | None,
    live_seconds: Mapping[str, int] | None = None,
) -> TaskBudgetStatus:
    """Build the shared evaluated read model after a caller's own filter."""
    if live_seconds is None:
        steps = (
            await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        live_seconds = await load_live_worked_seconds(
            ctx.session,
            ctx.workspace_id,
            steps,
            ctx.now,
        )
    actual_seconds = sum(live_seconds.values())
    actual_minutes = calculate_actual_worker_minutes(actual_seconds)
    allowed = Decimal(evaluation.allowed_worker_minutes)
    status = EconomicsStatusEnum.INFEASIBLE if allowed <= 0 else EconomicsStatusEnum.OK
    consumed = calculate_consumed_cost_minor(actual_seconds, evaluation.cost_per_worker_minute_minor_snapshot)
    remaining = calculate_remaining_worker_minutes(allowed, actual_minutes)
    percent = calculate_percent_consumed(allowed, actual_minutes)
    variance_minutes = calculate_variance_worker_minutes(allowed, actual_minutes)
    variance_cost = calculate_variance_cost_minor(evaluation.production_budget_minor, consumed)
    result = await ctx.session.scalar(
        select(ItemCostResult).where(
            ItemCostResult.workspace_id == ctx.workspace_id,
            ItemCostResult.task_id == task.client_id,
        )
    )
    return TaskBudgetStatus(
        status=status,
        item_binding=binding,
        actual_worker_seconds=actual_seconds,
        actual_worker_minutes=actual_minutes,
        remaining_worker_minutes=remaining,
        percent_consumed=percent,
        variance_worker_minutes=variance_minutes,
        production_budget_minor=evaluation.production_budget_minor,
        allowed_worker_minutes=allowed,
        consumed_cost_minor=consumed,
        variance_cost_minor=variance_cost,
        evaluation_id=evaluation.client_id,
        item_id=evaluation.item_id,
        result=result,
        typical_filter_spec=typical_filter_spec,
    )
