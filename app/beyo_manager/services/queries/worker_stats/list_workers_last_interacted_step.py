from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.analytics.serializers import (
    build_running_totals,
    serialize_insight,
    serialize_user_daily_work_stats,
)
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.compute_worker_insights import compute_worker_insights
from beyo_manager.services.queries.working_sections.step_record_payload import (
    build_step_record_payload,
    load_step_with_latest_record,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT)


# ─────────────────────────────────────────────────────────────────────────────
# >>> TEMP MOCK INSIGHTS — REMOVE BEFORE PRODUCTION <<<
# Frontend testing scaffold only. The dev DB has no analytics history, so real
# insights never fire. When a worker has NO real insights, we fall back to a
# representative mock set so the UI can be built/tested. This self-disables the
# moment real insights exist (only empty lists are replaced). To remove: delete
# this block, the `Insight` import below, and the `or _mock_insights_for(...)`
# fallback in the assembly loop. Grep "TEMP MOCK INSIGHTS" to find every touch.
from beyo_manager.domain.analytics.insights.results import Insight  # noqa: E402  # TEMP MOCK INSIGHTS

_MOCK_INSIGHT_POOL = [  # TEMP MOCK INSIGHTS
    Insight("completion_surge", "positive", "completed_count", 9.0, 4.0, 5.0, 1.25, 4, "high"),
    Insight("deep_focus", "positive", "focus_ratio", 0.94, 0.72, 0.22, 0.306, 3, "medium"),
    Insight("on_a_roll", "positive", "completed_count", 4.0, 3.0, 4.0, None, 6, "high"),
    Insight("faster_pace", "positive", "throughput", 2.4, 1.5, 0.9, 0.6, 4, "medium"),
    Insight("rising_pauses", "negative", "avg_pause_seconds", 780.0, 300.0, 480.0, 1.6, 4, "high"),
    Insight("completion_dip", "negative", "completed_count", 2.0, 6.0, -4.0, -0.667, 4, "medium"),
    Insight("leaving_steps_mid_shift", "negative", "shift_end_count", 3.0, 1.0, 2.0, 2.0, 3, "low"),
    Insight("choppy_work", "negative", "fragmentation", 4.5, 2.0, 2.5, 1.25, 3, "low"),
    Insight("quality_watch", "negative", "resolve_rate", 0.55, 0.9, -0.35, -0.389, 4, "medium"),
]


def _mock_insights_for(index: int) -> list[Insight]:  # TEMP MOCK INSIGHTS
    # Every 4th worker shows none (valid empty state); the rest get a rotating
    # 1–3 slice so the list exercises mixed polarities and severities.
    if index % 4 == 3:
        return []
    pool = _MOCK_INSIGHT_POOL * 2  # allow wraparound
    start = index % len(_MOCK_INSIGHT_POOL)
    return pool[start:start + 1 + (index % 3)]
# >>> END TEMP MOCK INSIGHTS <<<
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_work_date(raw_work_date: str | None) -> date:
    if not raw_work_date:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(raw_work_date)
    except ValueError as exc:
        raise ValidationError("work_date must be a valid ISO date in YYYY-MM-DD format.") from exc


def _worker_role_filter():
    # Workers are identified by their base workspace role. Specialization
    # (wood_worker, upholstery_worker, …) is orthogonal — a specialized user is
    # still a base-role ``worker`` — so we match on the base Role name only.
    return Role.name == RoleNameEnum.WORKER.value


def _worker_membership_query(ctx: ServiceContext, columns):
    return (
        select(*columns)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .join(Role, Role.client_id == WorkspaceRole.role_id)
        .where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
            _worker_role_filter(),
        )
    )


async def list_workers_last_interacted_step(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    work_date = _resolve_work_date(ctx.query_params.get("work_date"))

    total_result = await ctx.session.execute(
        _worker_membership_query(ctx, [func.count(User.client_id.distinct())])
    )
    total = total_result.scalar() or 0

    workers_result = await ctx.session.execute(
        _worker_membership_query(ctx, [User])
        .order_by(User.username.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    workers = workers_result.scalars().all()
    has_more = len(workers) > limit
    workers = workers[:limit]

    worker_ids = [user.client_id for user in workers]
    stats_by_user: dict[str, dict] = {}
    if worker_ids:
        stats_result = await ctx.session.execute(
            select(
                UserDailyWorkStats.user_id,
                UserDailyWorkStats.total_working_seconds,
                UserDailyWorkStats.total_pause_seconds,
                UserDailyWorkStats.total_completed_count,
            ).where(
                UserDailyWorkStats.workspace_id == ctx.workspace_id,
                UserDailyWorkStats.user_id.in_(worker_ids),
                UserDailyWorkStats.work_date == work_date,
            )
        )
        stats_by_user = {
            row.user_id: serialize_user_daily_work_stats(
                work_date,
                row.total_working_seconds,
                row.total_pause_seconds,
                row.total_completed_count,
            )
            for row in stats_result.all()
        }

    insights_by_user = await compute_worker_insights(ctx, worker_ids, work_date)

    # Live "running" add-on: currently-open (unbooked) intervals per worker, so the
    # frontend can show a live total = daily_stats + running. Only meaningful for today
    # (past days have no live running); kept separate so daily_stats stays settled.
    now = datetime.now(timezone.utc)
    running_by_user: dict[str, dict] = {}
    if worker_ids and work_date == now.date():
        day_start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        open_result = await ctx.session.execute(
            select(
                StepStateRecord.created_by_id,
                StepStateRecord.credited_user_id,
                StepStateRecord.state,
                StepStateRecord.entered_at,
            )
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
                func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id).in_(worker_ids),
                StepStateRecord.exited_at.is_(None),
                StepStateRecord.state.in_(_TIME_STATES),
                StepStateRecord.entered_at >= day_start,
                StepStateRecord.entered_at < day_end,
            )
        )
        open_by_worker: dict[str, list] = defaultdict(list)
        for row in open_result.all():
            worker = row.credited_user_id or row.created_by_id
            open_by_worker[worker].append((row.state.value, row.entered_at))
        running_by_user = {
            worker: build_running_totals(records, now) for worker, records in open_by_worker.items()
        }

    step_rows_by_worker: dict[str, list] = defaultdict(list)
    if worker_ids:
        latest_per_step = (
            select(
                StepStateRecord.created_by_id.label("worker_id"),
                StepStateRecord.step_id.label("step_id"),
                StepStateRecord.entered_at.label("entered_at"),
                StepStateRecord.created_at.label("record_created_at"),
                StepStateRecord.state.label("state"),
                TaskStep.allows_batch_working.label("allows_batch_working"),
                func.row_number()
                .over(
                    partition_by=(StepStateRecord.created_by_id, StepStateRecord.step_id),
                    order_by=(
                        StepStateRecord.entered_at.desc(),
                        StepStateRecord.created_at.desc(),
                        StepStateRecord.client_id.desc(),
                    ),
                )
                .label("step_row_number"),
            )
            .join(
                TaskStep,
                TaskStep.client_id == StepStateRecord.step_id,
            )
            .join(Task, Task.client_id == TaskStep.task_id)
            .where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.created_by_id.in_(worker_ids),
                StepStateRecord.is_deleted.is_(False),
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            )
            .cte("worker_latest_record_per_step")
        )
        latest_records = (
            select(
                latest_per_step.c.worker_id,
                latest_per_step.c.step_id,
                latest_per_step.c.entered_at,
                latest_per_step.c.record_created_at,
                latest_per_step.c.state,
                latest_per_step.c.allows_batch_working,
                func.rank()
                .over(
                    partition_by=latest_per_step.c.worker_id,
                    order_by=latest_per_step.c.entered_at.desc(),
                )
                .label("cohort_rank"),
            )
            .where(latest_per_step.c.step_row_number == 1)
            .subquery("worker_last_step_cohort_ranked")
        )
        step_rows_result = await ctx.session.execute(
            select(latest_records)
            .where(latest_records.c.cohort_rank == 1)
            .order_by(
                latest_records.c.worker_id,
                latest_records.c.record_created_at.desc(),
                latest_records.c.step_id.asc(),
            )
        )
        for row in step_rows_result:
            step_rows_by_worker[row.worker_id].append(row)

    worker_results: list[dict] = []
    for index, user in enumerate(workers):
        cohort = sorted(
            step_rows_by_worker.get(user.client_id, []),
            key=lambda row: (-row.record_created_at.timestamp(), row.step_id),
        )
        payload = None
        batch = None
        if cohort:
            state_order = [row.state for row in cohort]
            state_counts = Counter(state_order)
            winning_state = next(
                state for state in state_order if state_counts[state] == max(state_counts.values())
            )
            representative = next(row for row in cohort if row.state == winning_state)
            step = await load_step_with_latest_record(ctx, representative.step_id)
            if step is not None:
                # cases_summary is viewer-relative; the caller here is a manager,
                # not the step's worker, so omit it rather than report the
                # manager's own unread count against another worker's step.
                payload = await build_step_record_payload(
                    ctx, step, include_cases_summary=False
                )

            if representative.allows_batch_working and len(cohort) >= 2:
                state_value = getattr(representative.state, "value", representative.state)
                batch = {
                    "count": len(cohort),
                    "step_ids": sorted(row.step_id for row in cohort),
                    "shared_entered_at": representative.entered_at.isoformat(),
                    "state": state_value,
                }

        worker_results.append(
            {
                "user": serialize_user_worker_stat(user),
                "daily_stats": stats_by_user.get(
                    user.client_id,
                    serialize_user_daily_work_stats(work_date),
                ),
                "running": running_by_user.get(user.client_id) or build_running_totals([], now),
                "insights": [
                    serialize_insight(i)
                    # TEMP MOCK INSIGHTS: fall back to mock only when there are no real ones.
                    for i in (insights_by_user.get(user.client_id) or _mock_insights_for(index))
                ],
                "last_interacted_step": payload,
                "batch": batch,
            }
        )

    return {
        "workers": worker_results,
        "workers_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
            "total": total,
        },
    }
