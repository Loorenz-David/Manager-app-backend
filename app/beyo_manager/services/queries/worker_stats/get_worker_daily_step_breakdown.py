"""Manager drill-down: the per-task-step breakdown behind a worker's daily totals.

Answers "where did today's worked/paused/ended-shift/completed totals come from" by
aggregating that worker's `StepStateRecord`s per step for one UTC day, with the same
attribution and bucketing rules the analytics worker uses (so the settled figures
reconcile with the maintained `user_daily_work_stats`). The currently-open interval is
surfaced separately as `active_record` and excluded from the settled totals.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, extract, func, select

from beyo_manager.domain.analytics.serializers import (
    build_running_totals,
    serialize_step_contribution,
    serialize_user_daily_work_stats_full,
)
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.serializers import (
    serialize_item_worker_light,
    serialize_step,
    serialize_task_light,
)
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.step_light_bundle import load_step_light_bundle

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_SORT_BY = frozenset({"contribution", "working", "paused", "completed", "last_activity"})
_ORDER = frozenset({"asc", "desc"})
_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT)


def _resolve_work_date(raw: str | None) -> date:
    if not raw:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError("work_date must be a valid ISO date in YYYY-MM-DD format.") from exc


def _credited(user_id):
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id) == user_id


def _time_sum(state: TaskStepStateEnum):
    seconds = func.greatest(0, extract("epoch", StepStateRecord.exited_at - StepStateRecord.entered_at))
    return func.coalesce(
        func.sum(seconds).filter(
            StepStateRecord.state == state,
            StepStateRecord.exited_at.isnot(None),
            StepStateRecord.recorded_time_marked_wrong.is_(False),
        ),
        0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# >>> TEMP MOCK BREAKDOWN — REMOVE BEFORE PRODUCTION <<<
# Frontend testing scaffold. When the target worker has NO real step records for the
# day (empty breakdown), return a fabricated set so the UI can be built/tested. Self-
# disables the moment real records exist (only the empty case is replaced). To remove:
# delete this block and the `if not agg_rows:` short-circuit inside the service.
# Grep "TEMP MOCK BREAKDOWN" to find every touch.
_MOCK_IMG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='4' height='3'/>"
)


def _mock_daily_step_breakdown(user: dict, work_date: date, sort_by: str, order: str,
                               limit: int, offset: int) -> dict:  # TEMP MOCK BREAKDOWN
    day = work_date.isoformat()

    def _iso(hour: int, minute: int = 0) -> str:
        return f"{day}T{hour:02d}:{minute:02d}:00+00:00"

    def _item(sid, *, state, working, pause, ended, completed, active_state,
              completed_at, activity_at) -> dict:
        short = sid[-6:]
        return {
            "client_id": sid, "task_id": f"tsk_{short}", "state": state,
            "readiness_status": "ready", "sequence_order": 1,
            "working_section_id": "wsec_mock", "assigned_worker_id": user["client_id"],
            "total_dependencies": 0, "completed_dependencies": 0,
            "working_section_name_snapshot": "Assembly (mock)",
            "assigned_worker_display_name_snapshot": user["username"],
            "created_at": _iso(8), "closed_at": None, "ready_by_at": None,
            "total_working_seconds": working, "total_pause_seconds": pause,
            "total_ended_shift_seconds": ended, "total_working_count": 1,
            "total_pause_count": 1 if pause else 0, "total_ended_shift_count": 0,
            "total_issues_count": 0, "total_issues_resolved_count": 0, "total_cost_minor": None,
            "task": {
                "client_id": f"tsk_{short}", "task_type": "internal", "priority": "normal",
                "state": "assigned", "return_source": None, "item_location": None,
                "ready_by_at": None, "scheduled_start_at": None, "scheduled_end_at": None,
                "return_method": None,
            },
            "item": {
                "client_id": f"itm_{short}", "article_number": f"ART-{short}",
                "sku": f"SKU-{short}", "state": "in_progress", "item_category_id": None,
                "quantity": 1, "item_position": None, "item_zone": None,
                "upholstery_requirement": [],
            },
            "item_images": [{
                "client_id": f"img_{short}", "image_url": _MOCK_IMG,
                "width_px": 4, "height_px": 3, "file_size_bytes": 100,
            }],
            "contribution": {
                "working_seconds": working, "pause_seconds": pause,
                "ended_shift_seconds": ended, "completed_count": completed,
            },
            "active_record": {"state": active_state, "entered_at": activity_at} if active_state else None,
            "last_activity_at": activity_at,
            "last_completed_at": completed_at,
        }

    items = [
        _item("tsp_mock_working", state="working", working=1800, pause=300, ended=0,
              completed=0, active_state="working", completed_at=None, activity_at=_iso(11)),
        _item("tsp_mock_completed", state="completed", working=3600, pause=600, ended=0,
              completed=1, active_state=None, completed_at=_iso(10, 10), activity_at=_iso(10, 10)),
        _item("tsp_mock_paused", state="paused", working=600, pause=1500, ended=0,
              completed=0, active_state="paused", completed_at=None, activity_at=_iso(9, 30)),
        _item("tsp_mock_done_early", state="completed", working=2400, pause=200, ended=0,
              completed=1, active_state=None, completed_at=_iso(8, 45), activity_at=_iso(8, 45)),
    ]

    totals = {
        "working_seconds": sum(i["contribution"]["working_seconds"] for i in items),
        "pause_seconds": sum(i["contribution"]["pause_seconds"] for i in items),
        "ended_shift_seconds": sum(i["contribution"]["ended_shift_seconds"] for i in items),
        "completed_count": sum(i["contribution"]["completed_count"] for i in items),
    }
    daily_stats = {
        "work_date": day,
        "total_working_seconds": totals["working_seconds"],
        "total_pause_seconds": totals["pause_seconds"],
        "total_ended_shift_seconds": totals["ended_shift_seconds"],
        "total_completed_count": totals["completed_count"],
    }

    display = [i for i in items if i["last_completed_at"] is not None] if sort_by == "completed" else list(items)
    reverse = order == "desc"
    if sort_by == "contribution":
        display.sort(key=lambda i: (i["active_record"] is not None,
                                    i["contribution"]["working_seconds"],
                                    i["contribution"]["completed_count"]), reverse=True)
    elif sort_by == "working":
        display.sort(key=lambda i: i["contribution"]["working_seconds"], reverse=reverse)
    elif sort_by == "paused":
        display.sort(key=lambda i: i["contribution"]["pause_seconds"], reverse=reverse)
    elif sort_by == "completed":
        display.sort(key=lambda i: i["last_completed_at"], reverse=reverse)
    else:
        display.sort(key=lambda i: i["last_activity_at"], reverse=reverse)

    has_more = offset + limit < len(display)
    mock_now = datetime.now(timezone.utc)
    running = build_running_totals(
        [("working", mock_now - timedelta(minutes=30)), ("paused", mock_now - timedelta(hours=2))],
        mock_now,
    )
    return {
        "user": user, "work_date": day, "totals": totals, "daily_stats": daily_stats,
        "running": running,
        "steps": {
            "items": display[offset:offset + limit],
            "limit": limit, "offset": offset, "has_more": has_more,
        },
    }
# >>> END TEMP MOCK BREAKDOWN <<<
# ─────────────────────────────────────────────────────────────────────────────


async def get_worker_daily_step_breakdown(ctx: ServiceContext) -> dict:
    user_id = ctx.incoming_data.get("user_id")
    work_date = _resolve_work_date(ctx.query_params.get("work_date"))
    sort_by = ctx.query_params.get("sort_by") or "contribution"
    order = ctx.query_params.get("order") or "desc"
    if sort_by not in _SORT_BY:
        raise ValidationError(f"sort_by must be one of {sorted(_SORT_BY)}.")
    if order not in _ORDER:
        raise ValidationError("order must be 'asc' or 'desc'.")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    # Target must be an active member of the caller's workspace.
    user = (
        await ctx.session.execute(
            select(User)
            .join(
                WorkspaceMembership,
                and_(
                    WorkspaceMembership.user_id == User.client_id,
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                ),
            )
            .where(User.client_id == user_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise NotFound("Worker not found in this workspace.")

    day_start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    # One aggregation over the worker's records that day, grouped by step. exited_at is
    # NOT filtered in WHERE (the closed-only rule lives in the metric FILTERs), so the
    # result includes open-only steps and a last_activity_at for every touched step.
    agg_rows = (
        await ctx.session.execute(
            select(
                StepStateRecord.step_id.label("step_id"),
                _time_sum(TaskStepStateEnum.WORKING).label("working_seconds"),
                _time_sum(TaskStepStateEnum.PAUSED).label("pause_seconds"),
                _time_sum(TaskStepStateEnum.ENDED_SHIFT).label("ended_shift_seconds"),
                func.count(StepStateRecord.client_id)
                .filter(StepStateRecord.state == TaskStepStateEnum.COMPLETED)
                .label("completed_count"),
                func.max(StepStateRecord.entered_at).label("last_activity_at"),
                func.max(StepStateRecord.entered_at)
                .filter(StepStateRecord.state == TaskStepStateEnum.COMPLETED)
                .label("last_completed_at"),
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
                Task,
                and_(
                    Task.client_id == TaskStep.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                _credited(user_id),
                StepStateRecord.entered_at >= day_start,
                StepStateRecord.entered_at < day_end,
            )
            .group_by(StepStateRecord.step_id)
        )
    ).all()

    # >>> TEMP MOCK BREAKDOWN: no real records for this worker/day -> fabricate for
    # the frontend. Self-disables once real records exist. Remove with the mock block.
    if not agg_rows:
        return _mock_daily_step_breakdown(
            serialize_user_worker_stat(user), work_date, sort_by, order, limit, offset
        )
    # >>> END TEMP MOCK BREAKDOWN <<<

    # Currently-open interval per step (≤1 each; unique active index). Running time only —
    # never folded into the settled contribution/totals.
    open_rows = (
        await ctx.session.execute(
            select(StepStateRecord.step_id, StepStateRecord.state, StepStateRecord.entered_at)
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
                _credited(user_id),
                StepStateRecord.exited_at.is_(None),
                # Time-bearing states only: a COMPLETED record is also exited_at NULL
                # (terminal) but is a finished step, not a running interval.
                StepStateRecord.state.in_(_TIME_STATES),
                StepStateRecord.entered_at >= day_start,
                StepStateRecord.entered_at < day_end,
            )
        )
    ).all()
    active_record_by_step = {
        row.step_id: {"state": row.state.value, "entered_at": row.entered_at.isoformat()}
        for row in open_rows
    }

    # Live "running" add-on (today only): running time of the open intervals we just
    # loaded, summed per state. Kept out of the settled `totals`; the client shows
    # totals + running and ticks it locally. Zeros for past days.
    now = datetime.now(timezone.utc)
    running = build_running_totals(
        [(row.state.value, row.entered_at) for row in open_rows] if work_date == now.date() else [],
        now,
    )

    # Settled totals — full day, over every step, independent of sort/filter/pagination.
    totals = serialize_step_contribution(
        working_seconds=int(sum(int(r.working_seconds) for r in agg_rows)),
        pause_seconds=int(sum(int(r.pause_seconds) for r in agg_rows)),
        ended_shift_seconds=int(sum(int(r.ended_shift_seconds) for r in agg_rows)),
        completed_count=int(sum(int(r.completed_count) for r in agg_rows)),
    )

    # Display set + ordering. `completed` is a filter intention (only completed steps).
    display = list(agg_rows)
    if sort_by == "completed":
        display = [r for r in display if r.last_completed_at is not None]

    reverse = order == "desc"
    display.sort(key=lambda r: r.step_id)  # stable final tie-break
    if sort_by == "contribution":
        display.sort(key=lambda r: int(r.completed_count), reverse=True)
        display.sort(key=lambda r: int(r.working_seconds), reverse=True)
        display.sort(key=lambda r: r.step_id in active_record_by_step, reverse=True)
    elif sort_by == "working":
        display.sort(key=lambda r: int(r.working_seconds), reverse=reverse)
    elif sort_by == "paused":
        display.sort(key=lambda r: int(r.pause_seconds), reverse=reverse)
    elif sort_by == "completed":
        display.sort(key=lambda r: r.last_completed_at, reverse=reverse)
    else:  # last_activity
        display.sort(key=lambda r: r.last_activity_at, reverse=reverse)

    has_more = offset + limit < len(display)
    page = display[offset:offset + limit]
    page_step_ids = [r.step_id for r in page]

    bundle = await load_step_light_bundle(ctx, page_step_ids)

    items: list[dict] = []
    for row in page:
        step = bundle.steps_by_id.get(row.step_id)
        if step is None:
            continue  # step vanished/deleted between queries — skip defensively
        task = bundle.tasks_by_id.get(step.task_id)
        primary_item_id = bundle.task_to_primary_item_id.get(step.task_id)
        item = bundle.items_by_id.get(primary_item_id) if primary_item_id else None
        item_reqs = bundle.requirements_by_item.get(primary_item_id, []) if primary_item_id else []
        items.append(
            {
                **serialize_step(step),
                "task": serialize_task_light(task) if task else None,
                "item": serialize_item_worker_light(item, item_reqs, bundle.upholstery_by_id),
                "item_images": bundle.images_by_item.get(primary_item_id, []) if primary_item_id else [],
                "contribution": serialize_step_contribution(
                    working_seconds=int(row.working_seconds),
                    pause_seconds=int(row.pause_seconds),
                    ended_shift_seconds=int(row.ended_shift_seconds),
                    completed_count=int(row.completed_count),
                ),
                "active_record": active_record_by_step.get(row.step_id),
                "last_activity_at": row.last_activity_at.isoformat() if row.last_activity_at else None,
                "last_completed_at": row.last_completed_at.isoformat() if row.last_completed_at else None,
            }
        )

    daily_row = (
        await ctx.session.execute(
            select(
                UserDailyWorkStats.total_working_seconds,
                UserDailyWorkStats.total_pause_seconds,
                UserDailyWorkStats.total_ended_shift_seconds,
                UserDailyWorkStats.total_completed_count,
            ).where(
                UserDailyWorkStats.workspace_id == ctx.workspace_id,
                UserDailyWorkStats.user_id == user_id,
                UserDailyWorkStats.work_date == work_date,
            )
        )
    ).one_or_none()
    daily_stats = serialize_user_daily_work_stats_full(
        work_date,
        total_working_seconds=daily_row.total_working_seconds if daily_row else 0,
        total_pause_seconds=daily_row.total_pause_seconds if daily_row else 0,
        total_ended_shift_seconds=daily_row.total_ended_shift_seconds if daily_row else 0,
        total_completed_count=daily_row.total_completed_count if daily_row else 0,
    )

    return {
        "user": serialize_user_worker_stat(user),
        "work_date": work_date.isoformat(),
        "totals": totals,
        "daily_stats": daily_stats,
        "running": running,
        "steps": {
            "items": items,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        },
    }
