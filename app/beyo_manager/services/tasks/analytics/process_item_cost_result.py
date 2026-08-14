"""Recompute the durable item-economics snapshot for one task boundary."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from beyo_manager.domain.execution.payloads.item_cost_result import ItemCostResultPayload
from beyo_manager.domain.item_economics.calculator import (
    calculate_actual_worker_minutes,
    calculate_consumed_cost_minor,
    calculate_variance_cost_minor,
    calculate_variance_worker_minutes,
)
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.infra.execution.db import task_db_session

logger = logging.getLogger(__name__)

_ADMITTED_STATES = frozenset(
    {
        TaskStateEnum.WORKING,
        TaskStateEnum.READY,
        TaskStateEnum.RESOLVED,
        TaskStateEnum.FAILED,
        TaskStateEnum.CANCELLED,
    }
)


async def handle_process_item_cost_result(raw: dict, task_id: str) -> None:
    """Resolve all inputs at handler time and recompute-and-SET the result row."""
    payload = ItemCostResultPayload(**raw)

    async with task_db_session() as session:
        task = await session.scalar(
            select(Task).where(
                Task.workspace_id == payload.workspace_id,
                Task.client_id == payload.task_id,
                Task.is_deleted.is_(False),
            )
        )
        if task is None:
            logger.info("item_cost_result_skipped | task_id=%s reason=task_not_found", payload.task_id)
            return
        if task.state not in _ADMITTED_STATES:
            logger.info(
                "item_cost_result_skipped | task_id=%s reason=state_not_admitted state=%s",
                payload.task_id,
                task.state.value,
            )
            return

        evaluation = await session.scalar(
            select(ItemCostEvaluation).where(
                ItemCostEvaluation.workspace_id == payload.workspace_id,
                ItemCostEvaluation.task_id == payload.task_id,
                ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                ItemCostEvaluation.superseded_at.is_(None),
                ItemCostEvaluation.is_deleted.is_(False),
            )
        )
        if evaluation is None:
            logger.info(
                "item_cost_result_skipped | task_id=%s reason=no_current_committed_evaluation",
                payload.task_id,
            )
            return

        actual_seconds = await session.scalar(
            select(func.coalesce(func.sum(TaskStep.total_working_seconds), 0)).where(
                TaskStep.workspace_id == payload.workspace_id,
                TaskStep.task_id == payload.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        actual_seconds = int(actual_seconds or 0)
        actual_minutes = calculate_actual_worker_minutes(actual_seconds)
        consumed_cost = calculate_consumed_cost_minor(
            actual_seconds,
            evaluation.cost_per_worker_minute_minor_snapshot,
        )
        variance_minutes = calculate_variance_worker_minutes(
            evaluation.allowed_worker_minutes,
            actual_minutes,
        )
        variance_cost = calculate_variance_cost_minor(
            evaluation.production_budget_minor,
            consumed_cost,
        )
        now = datetime.now(timezone.utc)
        values = {
            "workspace_id": payload.workspace_id,
            "task_id": payload.task_id,
            "item_id": evaluation.item_id,
            "evaluation_id": evaluation.client_id,
            "actual_worker_seconds": actual_seconds,
            "actual_worker_minutes": actual_minutes,
            "consumed_cost_minor": consumed_cost,
            "variance_worker_minutes": variance_minutes,
            "variance_cost_minor": variance_cost,
            "task_closed_at": task.closed_at,
            "task_state_snapshot": task.state,
            "calculation_version": evaluation.calculation_version,
            "computed_at": now,
        }
        update_columns = {
            key: values[key]
            for key in (
                "evaluation_id",
                "item_id",
                "actual_worker_seconds",
                "actual_worker_minutes",
                "consumed_cost_minor",
                "variance_worker_minutes",
                "variance_cost_minor",
                "task_closed_at",
                "task_state_snapshot",
                "calculation_version",
                "computed_at",
            )
        }
        statement = insert(ItemCostResult).values(**values).on_conflict_do_update(
            constraint="uq_item_cost_results_task_id",
            set_=update_columns,
        )
        await session.execute(statement)
        await session.commit()
        logger.info(
            "item_cost_result_computed | task_id=%s evaluation_id=%s state=%s",
            payload.task_id,
            evaluation.client_id,
            task.state.value,
        )
