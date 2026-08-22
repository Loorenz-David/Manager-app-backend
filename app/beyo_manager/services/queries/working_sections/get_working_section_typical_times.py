"""Read the median completed section-total for every live working section."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import Integer, and_, case, cast, column, func, select, true, values

from beyo_manager.domain.item_economics.budget_division import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
)
from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.domain.item_economics.division_serializers import serialize_typical_times
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections._typical_item_filter import build_item_match


def typical_times_statement(
    workspace_id: str,
    *,
    # The optional request clock keeps the working-sections and price-scenario
    # callers on their existing clock read while E-P/E-A share ctx.now.
    now: datetime | None = None,
    specs: Sequence[TypicalFilterSpec] = (),
):
    """Build the shared grouped-median statement used by E1 and E2."""
    if len(specs) == 0:
        return _no_spec_typical_times_statement(workspace_id, now=now)

    cutoff = (now if now is not None else datetime.now(timezone.utc)) - timedelta(days=TYPICAL_WINDOW_DAYS)
    grouped_steps = (
        select(
            TaskStep.working_section_id.label("working_section_id"),
            TaskStep.task_id.label("task_id"),
            func.sum(TaskStep.total_working_seconds).label("group_seconds"),
            func.max(TaskStep.closed_at).label("latest_closed_at"),
        )
        .where(
            TaskStep.workspace_id == workspace_id,
            TaskStep.state == TaskStepStateEnum.COMPLETED,
            TaskStep.is_deleted.is_(False),
            TaskStep.recorded_time_marked_wrong.is_(False),
        )
        .group_by(TaskStep.working_section_id, TaskStep.task_id)
        .subquery("completed_section_totals")
    )
    spec_index = values(column("spec_index", Integer), name="spec_indices").data(
        [(index,) for index in range(len(specs))]
    ).alias()
    from_clause = (
        WorkingSection.__table__
        .join(spec_index, true())
        .outerjoin(
            grouped_steps,
            grouped_steps.c.working_section_id == WorkingSection.client_id,
        )
        .outerjoin(
            TaskItem,
            and_(
                TaskItem.workspace_id == workspace_id,
                TaskItem.task_id == grouped_steps.c.task_id,
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
            ),
        )
        .outerjoin(
            Item,
            and_(
                Item.workspace_id == workspace_id,
                Item.client_id == TaskItem.item_id,
                Item.is_deleted.is_(False),
            ),
        )
    )
    needs_category_join = False
    predicates = []
    for spec in specs:
        needs_join, predicate = build_item_match(spec)
        needs_category_join = needs_category_join or needs_join
        predicates.append(predicate if predicate is not None else true())
    if needs_category_join:
        from_clause = from_clause.outerjoin(ItemCategory, ItemCategory.client_id == Item.item_category_id)

    qualifying = grouped_steps.c.latest_closed_at >= cutoff
    section_count = func.count(grouped_steps.c.task_id).filter(qualifying)
    section_percentile = func.percentile_cont(0.5).within_group(grouped_steps.c.group_seconds).filter(qualifying)
    section_typical = case(
        (section_count >= TYPICAL_MIN_SAMPLE_SIZE, cast(func.round(section_percentile), Integer)),
        else_=None,
    )
    narrowed_counts = []
    narrowed_typicals = []
    for index, predicate in enumerate(predicates):
        narrowed_qualifying = and_(qualifying, spec_index.c.spec_index == index, predicate)
        narrowed_count = func.count(grouped_steps.c.task_id).filter(narrowed_qualifying)
        narrowed_percentile = func.percentile_cont(0.5).within_group(grouped_steps.c.group_seconds).filter(
            narrowed_qualifying
        )
        narrowed_counts.append(narrowed_count)
        narrowed_typicals.append(
            case(
                (narrowed_count >= TYPICAL_MIN_SAMPLE_SIZE, cast(func.round(narrowed_percentile), Integer)),
                else_=None,
            )
        )

    index = spec_index.c.spec_index
    return (
        select(
            WorkingSection.client_id,
            WorkingSection.name,
            index,
            narrowed_counts[0].label("narrowed_sample_count")
            if len(narrowed_counts) == 1
            else func.coalesce(
                *[case((index == position, count), else_=None) for position, count in enumerate(narrowed_counts)]
            ).label("narrowed_sample_count"),
            narrowed_typicals[0].label("narrowed_typical_worker_seconds")
            if len(narrowed_typicals) == 1
            else func.coalesce(
                *[case((index == position, typical), else_=None) for position, typical in enumerate(narrowed_typicals)]
            ).label("narrowed_typical_worker_seconds"),
            section_count.label("section_sample_count"),
            section_typical.label("section_typical_worker_seconds"),
        )
        .select_from(from_clause)
        .where(
            WorkingSection.workspace_id == workspace_id,
            WorkingSection.is_deleted.is_(False),
        )
        .group_by(WorkingSection.client_id, WorkingSection.name, index)
    )


def _no_spec_typical_times_statement(workspace_id: str, *, now: datetime | None = None):
    """Return the pre-refactor statement unchanged for HC-4."""
    cutoff = (now if now is not None else datetime.now(timezone.utc)) - timedelta(days=TYPICAL_WINDOW_DAYS)
    grouped_steps = (
        select(
            TaskStep.working_section_id.label("working_section_id"),
            TaskStep.task_id.label("task_id"),
            func.sum(TaskStep.total_working_seconds).label("group_seconds"),
            func.max(TaskStep.closed_at).label("latest_closed_at"),
        )
        .where(
            TaskStep.workspace_id == workspace_id,
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
    return (
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
            WorkingSection.workspace_id == workspace_id,
            WorkingSection.is_deleted.is_(False),
        )
        .group_by(WorkingSection.client_id, WorkingSection.name)
    )


async def get_working_section_typical_times(ctx: ServiceContext) -> dict:
    """Return live sections, with NULL typicals when fewer than five groups qualify."""
    statement = typical_times_statement(ctx.workspace_id).order_by(
        WorkingSection.order_list.asc().nulls_last(), WorkingSection.created_at.asc()
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


__all__ = ["get_working_section_typical_times", "typical_times_statement"]
