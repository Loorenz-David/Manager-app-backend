"""Purpose-built, post-clock-out summary for the shop-floor kiosk."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.analytics.linear_timeline import UNSPECIFIED_REASON
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    _load_step_and_primary_item,
)
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    _load_pause_reasons_lookup,
    build_recorded_shift_timeline,
    load_recorded_shift_records,
)


_MAX_COMPLETED_ITEMS = 100
_BASELINE_DAYS = 5
_BASELINE_LOOKBACK_DAYS = 14


def _window(work_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


async def _load_completed_steps(
    ctx: ServiceContext,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[str, datetime]]:
    credited = func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)
    rows = await ctx.session.execute(
        select(StepStateRecord.step_id, StepStateRecord.entered_at)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.workspace_id == ctx.workspace_id,
            StepStateRecord.is_deleted.is_(False),
            credited == user_id,
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.entered_at >= window_start,
            StepStateRecord.entered_at < window_end,
        )
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
    )
    return [(row.step_id, row.entered_at) for row in rows.all()]


async def _load_completed_units_by_day(
    ctx: ServiceContext,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> dict[date, int]:
    credited = func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)
    rows = await ctx.session.execute(
        select(
            func.date(StepStateRecord.entered_at).label("work_date"),
            Item.client_id.label("item_id"),
            Item.quantity,
        )
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .join(
            TaskItem,
            and_(
                TaskItem.task_id == TaskStep.task_id,
                TaskItem.workspace_id == ctx.workspace_id,
                TaskItem.removed_at.is_(None),
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
            ),
        )
        .join(
            Item,
            and_(
                Item.client_id == TaskItem.item_id,
                Item.workspace_id == ctx.workspace_id,
                Item.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.workspace_id == ctx.workspace_id,
            StepStateRecord.is_deleted.is_(False),
            credited == user_id,
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.entered_at >= window_start,
            StepStateRecord.entered_at < window_end,
        )
    )
    items_by_day: dict[date, dict[str, int]] = {}
    for row in rows.all():
        work_date = row.work_date
        if isinstance(work_date, str):
            work_date = date.fromisoformat(work_date)
        items_by_day.setdefault(work_date, {})[row.item_id] = row.quantity
    return {
        work_date: sum(item_quantities.values())
        for work_date, item_quantities in items_by_day.items()
    }


async def _load_item_metadata(
    ctx: ServiceContext,
    item_ids: list[str],
) -> tuple[dict[str, str | None], dict[str, int], dict[str, int]]:
    if not item_ids:
        return {}, {}, {}
    image_rows = await ctx.session.execute(
        select(ImageLink.entity_client_id, Image.image_url)
        .join(Image, Image.client_id == ImageLink.image_id)
        .where(
            ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
            ImageLink.entity_client_id.in_(item_ids),
            Image.deleted_at.is_(None),
        )
        .order_by(ImageLink.entity_client_id, ImageLink.display_order, ImageLink.created_at, ImageLink.client_id)
    )
    image_by_item: dict[str, str | None] = {}
    for row in image_rows.all():
        image_by_item.setdefault(row.entity_client_id, row.image_url)

    duration_rows = await ctx.session.execute(
        select(
            TaskItem.item_id,
            func.coalesce(
                func.sum(TaskStep.total_working_seconds),
                0,
            ).label("total_seconds"),
        )
        .join(TaskStep, TaskStep.task_id == TaskItem.task_id)
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.item_id.in_(item_ids),
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.is_deleted.is_(False),
        )
        .group_by(TaskItem.item_id)
    )
    durations = {row.item_id: int(row.total_seconds) for row in duration_rows.all()}

    issue_rows = await ctx.session.execute(
        select(ItemIssue.item_id, func.count(ItemIssue.client_id).label("issues_count"))
        .where(
            ItemIssue.workspace_id == ctx.workspace_id,
            ItemIssue.item_id.in_(item_ids),
            ItemIssue.is_deleted.is_(False),
        )
        .group_by(ItemIssue.item_id)
    )
    issues = {row.item_id: int(row.issues_count) for row in issue_rows.all()}
    return image_by_item, durations, issues


async def _load_sections(
    ctx: ServiceContext,
    section_ids: list[str],
) -> dict[str, str]:
    if not section_ids:
        return {}
    rows = await ctx.session.execute(
        select(WorkingSection.client_id, WorkingSection.name).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id.in_(section_ids),
            WorkingSection.is_deleted.is_(False),
        )
    )
    return {row.client_id: row.name for row in rows.all()}


async def get_worker_clock_out_analytics(
    ctx: ServiceContext,
    user_id: str,
    clock_out_at: datetime,
) -> dict:
    """Return the kiosk's bounded clock-out payload for the resolved target worker."""
    work_date = clock_out_at.date()
    day_start, day_end = _window(work_date)
    week_start = work_date - timedelta(days=work_date.weekday())
    week_end = week_start + timedelta(days=7)
    baseline_start = work_date - timedelta(days=_BASELINE_LOOKBACK_DAYS)
    records_start = min(week_start, baseline_start)
    records_by_user = await load_recorded_shift_records(
        ctx,
        [user_id],
        datetime.combine(records_start, time.min, tzinfo=timezone.utc),
        week_end,
    )
    records = records_by_user.get(user_id, [])
    timeline = build_recorded_shift_timeline(records, day_start, day_end, clock_out_at)

    days: list[dict] = []
    timelines_by_date = {}
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        current_start, current_end = _window(current_date)
        current_timeline = build_recorded_shift_timeline(records, current_start, current_end, clock_out_at)
        timelines_by_date[current_date] = current_timeline
        days.append(
            {
                "date": current_date.isoformat(),
                "working_seconds": current_timeline.working_seconds,
                "pause_seconds": current_timeline.paused_seconds,
                "idle_seconds": current_timeline.idle_seconds,
            }
        )

    completed_steps = await _load_completed_steps(ctx, user_id, day_start, day_end)
    step_ids = [step_id for step_id, _ in completed_steps]
    steps_by_id, item_by_task = await _load_step_and_primary_item(ctx, step_ids)
    completed_by_item: dict[str, tuple[datetime, TaskStep, Item]] = {}
    for step_id, completed_at in completed_steps:
        step = steps_by_id.get(step_id)
        item = item_by_task.get(step.task_id) if step is not None else None
        if step is not None and item is not None:
            completed_by_item[item.client_id] = (completed_at, step, item)
    ordered_completed = sorted(completed_by_item.values(), key=lambda entry: entry[0])
    truncated = len(ordered_completed) > _MAX_COMPLETED_ITEMS
    ordered_completed = ordered_completed[:_MAX_COMPLETED_ITEMS]
    item_ids = [item.client_id for _, _, item in ordered_completed]
    images, durations, issues = await _load_item_metadata(ctx, item_ids)
    section_names = await _load_sections(
        ctx,
        list({step.working_section_id for _, step, _ in ordered_completed}),
    )
    completed_items = [
        {
            "item_id": item.client_id,
            "reference": item.article_number or item.sku,
            "image_url": images.get(item.client_id),
            "working_section": (
                {
                    "client_id": step.working_section_id,
                    "name": section_names.get(
                        step.working_section_id,
                        step.working_section_name_snapshot,
                    ),
                }
                if section_names.get(step.working_section_id, step.working_section_name_snapshot)
                else None
            ),
            "units": item.quantity,
            "total_seconds": durations.get(item.client_id, 0),
            "issues_count": issues.get(item.client_id, 0),
        }
        for _, step, item in ordered_completed
    ]

    reason_ids = {reason_id for reason_id in timeline.pause_by_reason if reason_id != UNSPECIFIED_REASON}
    pause_reasons = await _load_pause_reasons_lookup(ctx, reason_ids)
    if UNSPECIFIED_REASON in timeline.pause_by_reason:
        pause_reasons[UNSPECIFIED_REASON] = {
            "name": "Reason unavailable",
            "image_url": None,
            "pause_type": None,
        }
    totals = {
        key: sum(day[key] for day in days)
        for key in ("working_seconds", "pause_seconds", "idle_seconds")
    }
    completed_units_by_day = await _load_completed_units_by_day(
        ctx,
        user_id,
        datetime.combine(baseline_start, time.min, tzinfo=timezone.utc),
        day_end,
    )
    baseline_rates: list[float] = []
    for offset in range(1, _BASELINE_LOOKBACK_DAYS + 1):
        baseline_date = work_date - timedelta(days=offset)
        baseline_start_at, baseline_end_at = _window(baseline_date)
        baseline_timeline = build_recorded_shift_timeline(records, baseline_start_at, baseline_end_at, clock_out_at)
        if baseline_timeline.working_seconds:
            baseline_rates.append(
                completed_units_by_day.get(baseline_date, 0)
                / (baseline_timeline.working_seconds / 3600)
            )
            if len(baseline_rates) == _BASELINE_DAYS:
                break
    units_today = sum(item["units"] for item in completed_items)
    units_per_hour = round(units_today / (timeline.working_seconds / 3600), 1) if timeline.working_seconds else 0.0
    baseline_units_per_hour = None
    if baseline_rates:
        baseline_units_per_hour = round(sum(baseline_rates) / len(baseline_rates), 1)

    return {
        "date": work_date.isoformat(),
        "timeline": {
            "working_seconds": timeline.working_seconds,
            "pause_seconds": timeline.paused_seconds,
            "idle_seconds": timeline.idle_seconds,
            "pause_by_reason": timeline.pause_by_reason,
        },
        "pause_reasons": pause_reasons,
        "completed_items": completed_items,
        "completed_items_truncated": truncated,
        "week": {"days": days, "totals": totals},
        "rate": {
            "units_per_hour": units_per_hour,
            "baseline_units_per_hour": baseline_units_per_hour,
            "baseline_days": len(baseline_rates),
        },
    }