"""Session-bound orchestration for worker insights.

Reusable entrypoint: any service (this list endpoint, a worker-detail view, a
digest email job, a "flag struggling workers" notification worker) calls this with
a set of user ids and a target date and gets structured :class:`Insight` objects
back — no presentation, no assumptions about the caller.

One bounded window read per call; the pure engine does the rest.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from beyo_manager.domain.analytics.insights.config import DEFAULT_CONFIG, InsightsConfig, lookback_days
from beyo_manager.domain.analytics.insights.engine import evaluate
from beyo_manager.domain.analytics.insights.results import DailyStats, Insight
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.services.context import ServiceContext


async def compute_worker_insights(
    ctx: ServiceContext,
    user_ids: list[str],
    target_date: date,
    config: InsightsConfig = DEFAULT_CONFIG,
) -> dict[str, list[Insight]]:
    """Return insights per user id for ``target_date`` (empty list when none)."""
    if not user_ids:
        return {}

    start_date = target_date - timedelta(days=lookback_days(config))
    rows = await ctx.session.execute(
        select(
            UserDailyWorkStats.user_id,
            UserDailyWorkStats.work_date,
            UserDailyWorkStats.total_working_seconds,
            UserDailyWorkStats.total_pause_seconds,
            UserDailyWorkStats.total_ended_shift_seconds,
            UserDailyWorkStats.total_completed_count,
            UserDailyWorkStats.total_working_count,
            UserDailyWorkStats.total_pause_count,
            UserDailyWorkStats.total_ended_shift_count,
            UserDailyWorkStats.total_issues_count,
            UserDailyWorkStats.total_issues_resolved_count,
        ).where(
            UserDailyWorkStats.workspace_id == ctx.workspace_id,
            UserDailyWorkStats.user_id.in_(user_ids),
            UserDailyWorkStats.work_date >= start_date,
            UserDailyWorkStats.work_date <= target_date,
        )
    )

    by_user: dict[str, dict[date, DailyStats]] = defaultdict(dict)
    for row in rows.all():
        by_user[row.user_id][row.work_date] = DailyStats(
            work_date=row.work_date,
            working_seconds=row.total_working_seconds,
            pause_seconds=row.total_pause_seconds,
            ended_shift_seconds=row.total_ended_shift_seconds,
            completed_count=row.total_completed_count,
            working_count=row.total_working_count,
            pause_count=row.total_pause_count,
            ended_shift_count=row.total_ended_shift_count,
            issues_count=row.total_issues_count,
            issues_resolved_count=row.total_issues_resolved_count,
        )

    target_in_progress = target_date == datetime.now(timezone.utc).date()
    return {
        user_id: evaluate(
            by_user.get(user_id, {}),
            target_date,
            config,
            target_in_progress=target_in_progress,
        )
        for user_id in user_ids
    }
