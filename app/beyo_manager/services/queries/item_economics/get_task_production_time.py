"""Task-scoped, section-keyed production-time read model."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
    divide_production_budget,
    _loaded_latest_state_record,
)
from beyo_manager.domain.item_economics.division_serializers import serialize_task_production_time
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.live_worked_seconds import load_live_worked_seconds
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import typical_times_statement


async def get_task_production_time(ctx: ServiceContext) -> dict:
    """Compose the manager budget status with the task's section view."""

    task_id = ctx.incoming_data.get("task_client_id")
    steps = (
        await ctx.session.execute(
            select(TaskStep)
            .options(selectinload(TaskStep.latest_state_record))
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
            .order_by(TaskStep.client_id.asc())
        )
    ).scalars().all()
    live_seconds = await load_live_worked_seconds(
        ctx.session,
        ctx.workspace_id,
        steps,
        ctx.now,
    )
    status = await get_task_budget_status(ctx, live_seconds=live_seconds)
    division_steps = [
        DivisionStep(
            client_id=step.client_id,
            state=step.state,
            working_section_id=step.working_section_id,
            # Strict indexing is deliberate and fail-loud: a fallback would silently restore settled values and mask C3's population row.
            total_working_seconds=live_seconds[step.client_id],
            sequence_order=step.sequence_order,
            working_section_name_snapshot=step.working_section_name_snapshot,
            typical_worker_seconds=None,
            is_deleted=step.is_deleted,
            created_at=step.created_at,
            latest_state_record=_loaded_latest_state_record(step),
        )
        for step in steps
    ]
    section_ids = {step.working_section_id for step in steps}
    sections = (
        await ctx.session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id.in_(section_ids),
                WorkingSection.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    section_by_id = {section.client_id: section for section in sections}

    typicals_by_section: dict[str, int | None] = {}
    typical_details: dict[str, dict] = {}
    if section_ids:
        typical_result = await ctx.session.execute(
            typical_times_statement(ctx.workspace_id, now=ctx.now).where(
                WorkingSection.client_id.in_(section_ids)
            )
        )
        for row in typical_result:
            typicals_by_section[row.client_id] = (
                int(row.typical_worker_seconds)
                if row.typical_worker_seconds is not None
                else None
            )
            typical_details[row.client_id] = {
                "typical_worker_seconds": typicals_by_section[row.client_id],
                "sample_count": int(row.sample_count or 0),
                "method": TYPICAL_METHOD,
                "window_days": TYPICAL_WINDOW_DAYS,
                "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
            }

    division = divide_production_budget(
        status.allowed_worker_minutes
        if status.status in {EconomicsStatusEnum.OK, EconomicsStatusEnum.INFEASIBLE}
        else None,
        division_steps,
        typicals_by_section,
        section_by_id,
    )
    return serialize_task_production_time(
        {
            "task_id": task_id,
            "status": status.status,
            "item_binding": status.item_binding,
            "allowed_worker_minutes": status.allowed_worker_minutes,
            "actual_worker_seconds": status.actual_worker_seconds,
            "actual_worker_minutes": status.actual_worker_minutes,
            "remaining_worker_minutes": status.remaining_worker_minutes,
            "percent_consumed": status.percent_consumed,
            "result": status.result,
            "division": division,
            "typicals": typical_details,
        }
    )


__all__ = ["get_task_production_time"]
