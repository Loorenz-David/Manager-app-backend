from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.analytics.serializers import (
    build_running_totals_averaged,
    serialize_time_quality,
    serialize_user_range_work_stats,
)
from beyo_manager.domain.analytics.estimation import (
    TimeEstimationStrategy,
    estimate_fill,
    iqr_trimmed_mean,
    median as sample_median,
    resolve as resolve_time_strategy,
)
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions
from beyo_manager.services.queries.analytics.estimation_sample import (
    ESTIMATION_MIN_SAMPLE,
    ESTIMATION_MIN_TRUSTED_STEPS,
    estimation_window,
    load_trusted_step_duration_sample,
)
from beyo_manager.services.queries.worker_stats._roster import (
    TIME_STATES,
    load_worker_page,
    resolve_date_range,
)


async def list_workers_totals(ctx: ServiceContext) -> dict:
    date_from, date_to = resolve_date_range(ctx.query_params)
    try:
        time_strategy = resolve_time_strategy(ctx.query_params.get("time_strategy", "median"))
    except ValueError as exc:
        raise ValidationError("time_strategy must be one of mean, median, or iqr.") from exc
    workers, workers_pagination = await load_worker_page(
        ctx, roles=(RoleNameEnum.WORKER, RoleNameEnum.MANAGER)
    )
    worker_ids = [user.client_id for user in workers]

    stats_by_user: dict[str, object] = {}
    if worker_ids:
        stats_result = await ctx.session.execute(
            select(
                UserDailyWorkStats.user_id,
                func.coalesce(func.sum(UserDailyWorkStats.total_working_seconds), 0).label("working"),
                func.coalesce(func.sum(UserDailyWorkStats.total_pause_seconds), 0).label("pause"),
                func.coalesce(func.sum(UserDailyWorkStats.total_working_count), 0).label("working_count"),
                func.coalesce(func.sum(UserDailyWorkStats.total_pause_count), 0).label("pause_count"),
                func.coalesce(func.sum(UserDailyWorkStats.total_ended_shift_count), 0).label("ended_count"),
                func.coalesce(func.sum(UserDailyWorkStats.total_completed_count), 0).label("completed"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_working_seconds), 0).label("inaccurate_working"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_pause_seconds), 0).label("inaccurate_pause"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_ended_shift_seconds), 0).label("inaccurate_ended"),
                func.coalesce(func.sum(UserDailyWorkStats.inaccurate_step_count), 0).label("inaccurate_steps"),
            )
            .where(
                UserDailyWorkStats.workspace_id == ctx.workspace_id,
                UserDailyWorkStats.user_id.in_(worker_ids),
                UserDailyWorkStats.work_date >= date_from,
                UserDailyWorkStats.work_date <= date_to,
            )
            .group_by(UserDailyWorkStats.user_id)
        )
        stats_by_user = {row.user_id: row for row in stats_result.all()}

    # Only workers with flagged steps can have a non-zero estimate, so only they need the
    # (per-worker) section-stats + trusted-duration sample. Most workers have none on a
    # given day, so this skips the bulk of the median/iqr sample loads.
    flagged_worker_ids = [
        wid for wid in worker_ids
        if int(getattr(stats_by_user.get(wid), "inaccurate_steps", 0)) > 0
    ]

    section_stats_by_user: dict[str, list[object]] = {}
    if flagged_worker_ids and time_strategy != TimeEstimationStrategy.MEAN:
        section_rows = await ctx.session.execute(
            select(
                UserSectionDailyWorkStats.user_id,
                UserSectionDailyWorkStats.working_section_id,
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_working_seconds), 0).label("working"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_pause_seconds), 0).label("pause"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.total_completed_count), 0).label("completed"),
                func.coalesce(func.sum(UserSectionDailyWorkStats.inaccurate_step_count), 0).label("inaccurate_steps"),
            )
            .where(
                UserSectionDailyWorkStats.workspace_id == ctx.workspace_id,
                UserSectionDailyWorkStats.user_id.in_(flagged_worker_ids),
                UserSectionDailyWorkStats.work_date >= date_from,
                UserSectionDailyWorkStats.work_date <= date_to,
            )
            .group_by(UserSectionDailyWorkStats.user_id, UserSectionDailyWorkStats.working_section_id)
        )
        for row in section_rows.all():
            section_stats_by_user.setdefault(row.user_id, []).append(row)

    samples_by_user: dict[str, dict[tuple[str, str], list[float]]] = {}
    if flagged_worker_ids and time_strategy != TimeEstimationStrategy.MEAN:
        window_start, window_end = estimation_window(date_to)
        for worker_id in flagged_worker_ids:
            samples_by_user[worker_id] = await load_trusted_step_duration_sample(
                ctx.session,
                ctx.workspace_id,
                worker_id,
                window_start,
                window_end,
                datetime.now(timezone.utc),
            )

    def _per_step_mean(trusted_seconds: int, completed: int, step_count: int) -> float:
        # Per-step trusted mean; too few trusted steps (< MIN) → 0 (suppress noisy estimate).
        denominator = completed - step_count
        return trusted_seconds / denominator if denominator >= ESTIMATION_MIN_TRUSTED_STEPS else 0.0

    def _robust(sample: list[float]) -> float:
        return (
            sample_median(sample)
            if time_strategy == TimeEstimationStrategy.MEDIAN
            else iqr_trimmed_mean(sample)
        )

    def _quality_for_user(user_id: str) -> dict:
        row = stats_by_user.get(user_id)
        inaccurate_steps = int(getattr(row, "inaccurate_steps", 0))
        trusted_working = int(getattr(row, "working", 0))
        trusted_pause = int(getattr(row, "pause", 0))
        wasted_working = int(getattr(row, "inaccurate_working", 0))
        wasted_pause = int(getattr(row, "inaccurate_pause", 0))
        completed = int(getattr(row, "completed", 0))

        if time_strategy == TimeEstimationStrategy.MEAN:
            # Per-step mean × flagged count. Confidence = view-range trusted completed steps.
            working_fill = estimate_fill(inaccurate_steps, _per_step_mean(trusted_working, completed, inaccurate_steps))
            pause_fill = estimate_fill(inaccurate_steps, _per_step_mean(trusted_pause, completed, inaccurate_steps))
            working_n = pause_n = max(0, completed - inaccurate_steps)
        else:
            # Per-section: median/iqr of the lookback per-step sample when it's big enough,
            # else the section's view-range per-step mean. Confidence = trusted steps that
            # backed it (lookback sample size, or the fallback's view-range count).
            working_fill = pause_fill = 0.0
            working_n = pause_n = 0
            samples = samples_by_user.get(user_id, {})
            for section_row in section_stats_by_user.get(user_id, []):
                section_steps = int(section_row.inaccurate_steps)
                if section_steps == 0:
                    continue
                section_completed = int(section_row.completed)
                w_sample = samples.get((section_row.working_section_id, "working"), [])
                p_sample = samples.get((section_row.working_section_id, "paused"), [])

                if len(w_sample) >= ESTIMATION_MIN_SAMPLE:
                    w_value, working_n = _robust(w_sample), working_n + len(w_sample)
                else:
                    w_value = _per_step_mean(int(section_row.working), section_completed, section_steps)
                    working_n += max(0, section_completed - section_steps)
                if len(p_sample) >= ESTIMATION_MIN_SAMPLE:
                    p_value, pause_n = _robust(p_sample), pause_n + len(p_sample)
                else:
                    p_value = _per_step_mean(int(section_row.pause), section_completed, section_steps)
                    pause_n += max(0, section_completed - section_steps)

                working_fill += estimate_fill(section_steps, w_value)
                pause_fill += estimate_fill(section_steps, p_value)

        return {
            "strategy": time_strategy.value,
            "working": serialize_time_quality(
                trusted_working, wasted_working, inaccurate_steps, working_fill, working_n
            ),
            "paused": serialize_time_quality(
                trusted_pause, wasted_pause, inaccurate_steps, pause_fill, pause_n
            ),
        }

    now = datetime.now(timezone.utc)
    today = now.date()
    running_by_user: dict[str, dict] = {}
    # Running is the live time of currently-open intervals — only meaningful for "today".
    # It applies as a slice when the requested range includes today; otherwise all zeros.
    if worker_ids and date_from <= today <= date_to:
        day_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
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
                StepStateRecord.state.in_(TIME_STATES),
                StepStateRecord.entered_at >= day_start,
                StepStateRecord.entered_at < day_end,
            )
        )
        workers_with_open = {row.credited_user_id or row.created_by_id for row in open_result.all()}
        for worker in workers_with_open:
            contributions = await compute_record_contributions(
                ctx.session,
                ctx.workspace_id,
                worker,
                day_start - timedelta(days=1),
                day_end + timedelta(days=1),
                now,
            )
            running_by_user[worker] = build_running_totals_averaged(
                [(c.state, c.seconds) for c in contributions if c.is_open],
                now,
            )

    worker_results = []
    for user in workers:
        row = stats_by_user.get(user.client_id)
        worker_results.append(
            {
                "user": serialize_user_worker_stat(user),
                "daily_stats": serialize_user_range_work_stats(
                    date_from,
                    date_to,
                    int(getattr(row, "working", 0)),
                    int(getattr(row, "pause", 0)),
                    int(getattr(row, "completed", 0)),
                    time_quality=_quality_for_user(user.client_id),
                ),
                "running": running_by_user.get(user.client_id)
                or build_running_totals_averaged([], now),
            }
        )

    return {"workers": worker_results, "workers_pagination": workers_pagination}
