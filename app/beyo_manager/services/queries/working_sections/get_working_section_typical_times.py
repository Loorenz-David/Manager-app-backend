"""Read the median completed section-total for every live working section."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, case, cast, func, select

from beyo_manager.domain.item_economics.budget_division import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
)
from beyo_manager.domain.item_economics.division_serializers import serialize_typical_times
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext


async def get_working_section_typical_times(ctx: ServiceContext) -> dict:
    """Return live sections, with NULL typicals when fewer than five groups qualify."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=TYPICAL_WINDOW_DAYS)
    grouped_steps = (
        select(
            TaskStep.working_section_id.label("working_section_id"),
            TaskStep.task_id.label("task_id"),
            func.sum(TaskStep.total_working_seconds).label("group_seconds"),
            func.max(TaskStep.closed_at).label("latest_closed_at"),
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.state == TaskStepStateEnum.COMPLETED,
            TaskStep.is_deleted.is_(False),
            TaskStep.recorded_time_marked_wrong.is_(False),
        )
        .group_by(TaskStep.working_section_id, TaskStep.task_id)
        .subquery("completed_section_totals")
    )
    qualifying = grouped_steps.c.latest_closed_at >= cutoff
    sample_count = func.count(grouped_steps.c.task_id).filter(qualifying)
    percentile = func.percentile_cont(0.5).within_group(grouped_steps.c.group_seconds).filter(qualifying)
    typical_seconds = case(
        (sample_count >= TYPICAL_MIN_SAMPLE_SIZE, cast(func.round(percentile), Integer)),
        else_=None,
    )

    statement = (
        select(
            WorkingSection.client_id,
            WorkingSection.name,
            sample_count.label("sample_count"),
            typical_seconds.label("typical_worker_seconds"),
        )
        .outerjoin(
            grouped_steps,
            grouped_steps.c.working_section_id == WorkingSection.client_id,
        )
        .where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.is_deleted.is_(False),
        )
        .group_by(WorkingSection.client_id, WorkingSection.name)
        .order_by(WorkingSection.order_list.asc().nulls_last(), WorkingSection.created_at.asc())
    )
    working_section_ids = ctx.query_params.get("working_section_ids")
    if working_section_ids is not None:
        statement = statement.where(WorkingSection.client_id.in_(working_section_ids))

    result = await ctx.session.execute(statement)
    rows = [
        {
            "working_section_id": row.client_id,
            "section_name": row.name,
            "typical_worker_seconds": int(row.typical_worker_seconds) if row.typical_worker_seconds is not None else None,
            "sample_count": int(row.sample_count or 0),
            "method": TYPICAL_METHOD,
            "window_days": TYPICAL_WINDOW_DAYS,
            "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
        }
        for row in result
    ]
    return serialize_typical_times(rows)


__all__ = ["get_working_section_typical_times"]
