"""Manager drill-down: the per-task-step breakdown behind a worker's totals.

Answers "where did the worked/paused/ended-shift/completed totals come from" by
aggregating that worker's `StepStateRecord`s per step over an inclusive UTC date range
(`date_from`..`date_to`, both defaulting to today), with the same attribution and
bucketing rules the analytics worker uses (so the settled figures reconcile with the
summed `user_daily_work_stats`). The currently-open interval is surfaced separately as
`active_record` and excluded from the settled totals.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.analytics.serializers import (
    build_running_totals_averaged,
    serialize_estimated_fill_by_strategy,
    serialize_step_contribution,
    serialize_time_quality,
    serialize_user_range_work_stats_full,
)
from beyo_manager.domain.analytics.estimation import (
    estimate_fill,
    iqr_trimmed_mean,
    median as sample_median,
    resolve as resolve_time_strategy,
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
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions
from beyo_manager.services.queries.analytics.estimation_sample import (
    ESTIMATION_MIN_SAMPLE,
    ESTIMATION_MIN_TRUSTED_STEPS,
    estimation_window,
    load_trusted_step_duration_sample,
)
from beyo_manager.services.queries.tasks.step_light_bundle import load_step_light_bundle
from beyo_manager.services.queries.worker_stats._roster import resolve_date_range

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_SORT_BY = frozenset({"contribution", "working", "paused", "completed", "last_activity"})
_ORDER = frozenset({"asc", "desc"})
_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT)
# States that can represent work by the credited user. Everything else (notably
# PENDING) is a lifecycle marker, not labor — see `_credited` below.
_WORK_STATES = _TIME_STATES + (TaskStepStateEnum.COMPLETED,)


def _credited(user_id):
    """Attribute a record to a worker.

    `credited_user_id` is the explicit "whose work is this" field; it is only set
    on transition records (`_step_transition_core`). Step-creation records are
    written as PENDING with `created_by_id` set and `credited_user_id` left NULL
    on purpose — creating a task is not working on it. The COALESCE fallback is
    still required because ~97% of time-bearing records predate that field, so
    callers MUST additionally restrict to `_WORK_STATES`; otherwise the fallback
    silently reads "created by" as "worked by" and pulls in every sibling step
    the creator never touched (including steps assigned to other workers).
    """
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id) == user_id


async def get_worker_daily_step_breakdown(ctx: ServiceContext) -> dict:
    user_id = ctx.incoming_data.get("user_id")
    date_from, date_to = resolve_date_range(ctx.query_params)
    try:
        time_strategy = resolve_time_strategy(ctx.query_params.get("time_strategy", "median"))
    except ValueError as exc:
        raise ValidationError("time_strategy must be one of mean, median, or iqr.") from exc
    only_inaccurate = str(ctx.query_params.get("only_inaccurate", "false")).lower() in {
        "1", "true", "yes"
    }
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

    # Inclusive range → half-open UTC window [range_start, range_end).
    range_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    range_end = datetime.combine(date_to, time.min, tzinfo=timezone.utc) + timedelta(days=1)

    # One aggregation over the worker's records in the range, grouped by step. exited_at is
    # NOT filtered in WHERE (the closed-only rule lives in the metric FILTERs), so the
    # result includes open-only steps and a last_activity_at for every touched step.
    # State IS filtered to `_WORK_STATES`: a step must have been worked or completed by
    # this user to appear. Without it, PENDING creation records credit the task's creator
    # for every sibling step (see `_credited`), which surfaced steps with zero time that
    # the user never worked. Dropping them cannot change any total — the per-step seconds
    # come from `compute_record_contributions`, which already filters to `_TIME_STATES`,
    # and `completed_count` here only counts COMPLETED records.
    agg_rows = (
        await ctx.session.execute(
            select(
                StepStateRecord.step_id.label("step_id"),
                TaskStep.working_section_id.label("working_section_id"),
                TaskStep.recorded_time_marked_wrong.label("is_time_inaccurate"),
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
                StepStateRecord.is_deleted.is_(False),
                StepStateRecord.state.in_(_WORK_STATES),
                StepStateRecord.entered_at >= range_start,
                StepStateRecord.entered_at < range_end,
            )
            .group_by(
                StepStateRecord.step_id,
                TaskStep.working_section_id,
                TaskStep.recorded_time_marked_wrong,
            )
        )
    ).all()

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
                StepStateRecord.is_deleted.is_(False),
                StepStateRecord.exited_at.is_(None),
                # Time-bearing states only: a COMPLETED record is also exited_at NULL
                # (terminal) but is a finished step, not a running interval.
                StepStateRecord.state.in_(_TIME_STATES),
                StepStateRecord.entered_at >= range_start,
                StepStateRecord.entered_at < range_end,
            )
        )
    ).all()
    active_record_by_step = {
        row.step_id: {"state": row.state.value, "entered_at": row.entered_at.isoformat()}
        for row in open_rows
    }

    now = datetime.now(timezone.utc)

    # Concurrency-averaged per-record settled/running seconds (batch time divided by real overlap).
    contributions = await compute_record_contributions(
        ctx.session, ctx.workspace_id, user_id, range_start - timedelta(days=1), range_end + timedelta(days=1), now
    )

    # Live "running" add-on: open intervals' averaged running seconds per state — only when
    # the range includes today (a live interval only exists "now").
    running = build_running_totals_averaged(
        [(c.state, c.seconds) for c in contributions if c.is_open] if date_from <= now.date() <= date_to else [],
        now,
    )
    avg_seconds: dict[str, dict[str, float]] = defaultdict(
        lambda: {"working": 0.0, "paused": 0.0, "ended_shift": 0.0}
    )
    for c in contributions:
        if c.is_open or c.step_is_deleted or not (date_from <= c.entered_at.date() <= date_to):
            continue
        avg_seconds[c.step_id][c.state] += c.seconds

    wasted_seconds: dict[str, dict[str, float]] = defaultdict(
        lambda: {"working": 0.0, "paused": 0.0, "ended_shift": 0.0}
    )
    inaccurate_records_by_step: dict[str, list[dict]] = defaultdict(list)
    inaccurate_step_ids: set[str] = set()
    for contribution in contributions:
        if (
            contribution.is_open
            or contribution.step_is_deleted
            or not (date_from <= contribution.entered_at.date() <= date_to)
        ):
            continue
        if contribution.marked_wrong:
            inaccurate_step_ids.add(contribution.step_id)
            wasted_seconds[contribution.step_id][contribution.state] += contribution.wasted_seconds
            inaccurate_records_by_step[contribution.step_id].append(
                {
                    "record_id": contribution.record_id,
                    "state": contribution.state,
                    "entered_at": contribution.entered_at.isoformat(),
                    "exited_at": contribution.exited_at.isoformat() if contribution.exited_at else None,
                    "wasted_seconds": float(contribution.wasted_seconds),
                }
            )

    def _avg(step_id: str, state: str) -> int:
        return int(round(avg_seconds.get(step_id, {}).get(state, 0.0)))

    section_rows = (
        await ctx.session.execute(
            select(
                UserSectionDailyWorkStats.working_section_id,
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_working_seconds), 0).label("working"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_pause_seconds), 0).label("pause"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_ended_shift_seconds), 0).label("ended"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_completed_count), 0).label("completed"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.inaccurate_step_count), 0).label("inaccurate_steps"),
            )
            .where(
                UserSectionDailyWorkStats.workspace_id == ctx.workspace_id,
                UserSectionDailyWorkStats.user_id == user_id,
                UserSectionDailyWorkStats.work_date >= date_from,
                UserSectionDailyWorkStats.work_date <= date_to,
            )
            .group_by(UserSectionDailyWorkStats.working_section_id)
        )
    ).all()
    section_stats = {row.working_section_id: row for row in section_rows}

    # Always load the sample: the breakdown returns all three strategies per step for
    # side-by-side comparison, so median/iqr must be real regardless of `time_strategy`
    # (which only selects the top-level usable total). One query for a single worker.
    window_start, window_end = estimation_window(date_to)
    samples = await load_trusted_step_duration_sample(
        ctx.session,
        ctx.workspace_id,
        user_id,
        window_start,
        window_end,
        now,
    )

    def _mean_per_step(section_id: str, state: str) -> float:
        section = section_stats.get(section_id)
        if section is None:
            return 0.0
        field = {"working": "working", "paused": "pause", "ended_shift": "ended"}[state]
        trusted = int(getattr(section, field))
        denominator = int(section.completed) - int(section.inaccurate_steps)
        # Too few trusted completed steps in the section → estimate is noise; suppress.
        return trusted / denominator if denominator >= ESTIMATION_MIN_TRUSTED_STEPS else 0.0

    def _estimated_for_step(section_id: str, state: str) -> dict[str, float]:
        fallback = _mean_per_step(section_id, state)
        sample = samples.get((section_id, state), [])
        values = {
            "mean": fallback,
            "median": fallback,
            "iqr": fallback,
        }
        if len(sample) >= ESTIMATION_MIN_SAMPLE:
            values["median"] = sample_median(sample)
            values["iqr"] = iqr_trimmed_mean(sample)
        return {
            strategy: estimate_fill(1, value)
            for strategy, value in values.items()
        }

    estimated_by_step: dict[str, dict[str, dict[str, float]]] = {}
    estimated_totals: dict[str, dict[str, float]] = {
        "mean": {"working": 0.0, "paused": 0.0, "ended_shift": 0.0},
        "median": {"working": 0.0, "paused": 0.0, "ended_shift": 0.0},
        "iqr": {"working": 0.0, "paused": 0.0, "ended_shift": 0.0},
    }
    for row in agg_rows:
        if not bool(row.is_time_inaccurate) or row.step_id not in inaccurate_step_ids:
            continue
        estimated_by_step[row.step_id] = {
            state: _estimated_for_step(row.working_section_id, state)
            for state in ("working", "paused", "ended_shift")
        }
        for state, state_values in estimated_by_step[row.step_id].items():
            for strategy, value in state_values.items():
                estimated_totals[strategy][state] += value

    # Settled totals — full day, over every step, independent of sort/filter/pagination.
    totals = serialize_step_contribution(
        working_seconds=sum(_avg(r.step_id, "working") for r in agg_rows),
        pause_seconds=sum(_avg(r.step_id, "paused") for r in agg_rows),
        ended_shift_seconds=sum(_avg(r.step_id, "ended_shift") for r in agg_rows),
        completed_count=int(sum(int(r.completed_count) for r in agg_rows)),
    )
    wasted = serialize_step_contribution(
        working_seconds=sum(int(round(wasted_seconds[r.step_id]["working"])) for r in agg_rows),
        pause_seconds=sum(int(round(wasted_seconds[r.step_id]["paused"])) for r in agg_rows),
        ended_shift_seconds=sum(int(round(wasted_seconds[r.step_id]["ended_shift"])) for r in agg_rows),
    )
    estimated = {
        strategy: serialize_step_contribution(
            working_seconds=int(round(values["working"])),
            pause_seconds=int(round(values["paused"])),
            ended_shift_seconds=int(round(values["ended_shift"])),
        )
        for strategy, values in estimated_totals.items()
    }
    selected_estimated = estimated[time_strategy.value]
    usable = serialize_step_contribution(
        working_seconds=totals["working_seconds"] + selected_estimated["working_seconds"],
        pause_seconds=totals["pause_seconds"] + selected_estimated["pause_seconds"],
        ended_shift_seconds=totals["ended_shift_seconds"] + selected_estimated["ended_shift_seconds"],
        completed_count=totals["completed_count"],
    )

    # Display set + ordering.
    #
    # `working` / `paused` / `completed` are *filter* intentions, not just sorts: each one
    # answers "where did THIS total come from", so a step with nothing to contribute to that
    # metric must not be listed (it would render as a 0h 0m card padding the list).
    # `contribution` / `last_activity` stay unfiltered — they are "everything touched" views.
    #
    # A step qualifies for a time intention when it holds settled time in that state, OR is
    # live in it right now (open interval — zero settled but actively accruing), OR — for
    # `working` only — is flagged inaccurate: those carry 0 trusted seconds by definition,
    # and their time lives in `wasted` / `estimated_fill_by_strategy`, so excluding them
    # would hide exactly the steps the estimation UI exists to surface.
    def _keeps(row, state: str) -> bool:
        if _avg(row.step_id, state) > 0:
            return True
        if active_record_by_step.get(row.step_id, {}).get("state") == state:
            return True
        return state == "working" and bool(row.is_time_inaccurate)

    display = list(agg_rows)
    if only_inaccurate:
        display = [r for r in display if bool(r.is_time_inaccurate)]
    if sort_by == "completed":
        display = [r for r in display if r.last_completed_at is not None]
    elif sort_by == "working":
        display = [r for r in display if _keeps(r, "working")]
    elif sort_by == "paused":
        display = [r for r in display if _keeps(r, "paused")]

    reverse = order == "desc"
    display.sort(key=lambda r: r.step_id)  # stable final tie-break
    if sort_by == "contribution":
        display.sort(key=lambda r: int(r.completed_count), reverse=True)
        display.sort(key=lambda r: _avg(r.step_id, "working"), reverse=True)
        display.sort(key=lambda r: r.step_id in active_record_by_step, reverse=True)
    elif sort_by == "working":
        display.sort(key=lambda r: _avg(r.step_id, "working"), reverse=reverse)
    elif sort_by == "paused":
        display.sort(key=lambda r: _avg(r.step_id, "paused"), reverse=reverse)
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
        step_estimates = estimated_by_step.get(
            row.step_id,
            {
                state: {"mean": 0.0, "median": 0.0, "iqr": 0.0}
                for state in ("working", "paused", "ended_shift")
            },
        )
        step_wasted = wasted_seconds.get(
            row.step_id,
            {"working": 0.0, "paused": 0.0, "ended_shift": 0.0},
        )
        items.append(
            {
                **serialize_step(step),
                "task": serialize_task_light(task) if task else None,
                "item": serialize_item_worker_light(item, item_reqs, bundle.upholstery_by_id),
                "item_images": bundle.images_by_item.get(primary_item_id, []) if primary_item_id else [],
                "contribution": serialize_step_contribution(
                    working_seconds=_avg(row.step_id, "working"),
                    pause_seconds=_avg(row.step_id, "paused"),
                    ended_shift_seconds=_avg(row.step_id, "ended_shift"),
                    completed_count=int(row.completed_count),
                ),
                "is_time_inaccurate": bool(row.is_time_inaccurate),
                "wasted": serialize_step_contribution(
                    working_seconds=int(round(step_wasted["working"])),
                    pause_seconds=int(round(step_wasted["paused"])),
                    ended_shift_seconds=int(round(step_wasted["ended_shift"])),
                ),
                "estimated_fill_by_strategy": {
                    state: serialize_estimated_fill_by_strategy(**values)
                    for state, values in step_estimates.items()
                },
                "inaccurate_records": inaccurate_records_by_step.get(row.step_id, []),
                "active_record": active_record_by_step.get(row.step_id),
                "last_activity_at": row.last_activity_at.isoformat() if row.last_activity_at else None,
                "last_completed_at": row.last_completed_at.isoformat() if row.last_completed_at else None,
            }
        )

    daily_row = (
        await ctx.session.execute(
            select(
                func.coalesce(func.sum(UserDailyWorkStats.total_working_seconds), 0).label("working"),
                func.coalesce(func.sum(UserDailyWorkStats.total_pause_seconds), 0).label("pause"),
                func.coalesce(func.sum(UserDailyWorkStats.total_ended_shift_seconds), 0).label("ended_shift"),
                func.coalesce(func.sum(UserDailyWorkStats.total_completed_count), 0).label("completed"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_working_seconds), 0).label("inaccurate_working"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_pause_seconds), 0).label("inaccurate_pause"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_step_count), 0).label("inaccurate_steps"),
            ).where(
                UserDailyWorkStats.workspace_id == ctx.workspace_id,
                UserDailyWorkStats.user_id == user_id,
                UserDailyWorkStats.work_date >= date_from,
                UserDailyWorkStats.work_date <= date_to,
            )
        )
    ).one()
    # Per-state confidence backing the SELECTED strategy's fill: view-range trusted-completed
    # count for mean; lookback sample size (or fallback view-range count) per flagged section
    # for median/iqr — mirrors the roster so the frontend's confidence gate is consistent.
    if time_strategy.value == "mean":
        daily_working_n = daily_pause_n = max(0, int(daily_row.completed) - int(daily_row.inaccurate_steps))
    else:
        daily_working_n = daily_pause_n = 0
        for sec_id, srow in section_stats.items():
            s_steps = int(srow.inaccurate_steps)
            if s_steps == 0:
                continue
            view_n = max(0, int(srow.completed) - s_steps)
            w_s = samples.get((sec_id, "working"), [])
            p_s = samples.get((sec_id, "paused"), [])
            daily_working_n += len(w_s) if len(w_s) >= ESTIMATION_MIN_SAMPLE else view_n
            daily_pause_n += len(p_s) if len(p_s) >= ESTIMATION_MIN_SAMPLE else view_n

    daily_quality = {
        "strategy": time_strategy.value,
        "working": serialize_time_quality(
            int(daily_row.working),
            int(daily_row.inaccurate_working),
            int(daily_row.inaccurate_steps),
            float(selected_estimated["working_seconds"]),
            daily_working_n,
        ),
        "paused": serialize_time_quality(
            int(daily_row.pause),
            int(daily_row.inaccurate_pause),
            int(daily_row.inaccurate_steps),
            float(selected_estimated["pause_seconds"]),
            daily_pause_n,
        ),
    }
    daily_stats = serialize_user_range_work_stats_full(
        date_from,
        date_to,
        total_working_seconds=int(daily_row.working),
        total_pause_seconds=int(daily_row.pause),
        total_ended_shift_seconds=int(daily_row.ended_shift),
        total_completed_count=int(daily_row.completed),
        time_quality=daily_quality,
    )

    return {
        "user": serialize_user_worker_stat(user),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "totals": totals,
        "usable": usable,
        "wasted": wasted,
        "estimated": estimated,
        "inaccurate_step_count": len(inaccurate_step_ids),
        "time_strategy": time_strategy.value,
        "daily_stats": daily_stats,
        "running": running,
        "steps": {
            "items": items,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        },
    }
