"""WORKER-1: Process step state transition events — update analytics stats tables."""

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.item_cost_result import ItemCostResultPayload
from beyo_manager.domain.task_steps.constants import TERMINAL_TASK_STATES, TIME_BEARING_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.infra.execution.db import task_db_session
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_completion_reconcile_deltas,
    apply_reconcile_deltas,
    reconcile_user_day_completions,
    reconcile_user_day_time,
)
from beyo_manager.services.commands.task_steps._settle_step_time import settle_step_time_totals
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.infra.events.worker_shift_realtime import emit_worker_shift_state

logger = logging.getLogger(__name__)

# The step-grain time recompute now lives with the transition write path, which calls it in
# the same transaction that closes a record (see `_settle_step_time` for why). The worker
# still runs it: it is recompute-and-SET, so the second run is a no-op that also covers the
# paths the request could not settle. Re-exported under its historical name because the
# averaged-time backfill script and four integration modules import it from here.
_recompute_step_time_totals = settle_step_time_totals


async def handle_process_step_transition(raw: dict, task_id: str) -> None:
    """WORKER-1: Dispatch step transition payload to all applicable aggregation rules."""
    payload = StepTransitionPayload(**raw)  # validates at entry; raises TypeError on mismatch

    async with task_db_session() as session:
        closing_record = await _fetch_closing_record(session, payload)
        if closing_record is None:
            logger.warning("record_not_found | closing_record_id=%s task_id=%s", payload.closing_record_id, task_id)
            return
        task_step = await _fetch_task_step(session, payload.step_id, payload.workspace_id)
        if task_step is None:
            logger.warning("step_not_found | step_id=%s task_id=%s", payload.step_id, task_id)

        # Fetch assigned worker display name snapshot for user-scoped stats.
        # If the worker record is deleted after the transition was recorded, the snapshot
        # falls back to "" — this is intentional; approximate analytics, not an error.
        credited_user_display_name = ""
        if payload.credited_user_id:
            credited_user = await _fetch_user(session, payload.credited_user_id)
            if credited_user:
                credited_user_display_name = credited_user.username

        now = datetime.now(timezone.utc)
        closing_state = TaskStepStateEnum(payload.closing_state)

        # TIME (concurrency-averaged). When a time-bearing record closed, recompute-and-SET
        # the credited worker's day from records (idempotent; batch time is averaged by real
        # concurrency). marked_wrong records are excluded inside the sweep.
        if payload.credited_user_id and closing_state in TIME_BEARING_STATES:
            work_date = datetime.fromisoformat(payload.entered_at).date()
            result = await reconcile_user_day_time(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, work_date, now,
            )
            await apply_reconcile_deltas(
                session, payload.workspace_id, payload.credited_user_id,
                credited_user_display_name, work_date, now, result,
            )
            await _recompute_step_time_totals(session, payload.workspace_id, payload.step_id, now)
            task = await session.scalar(
                select(Task).where(
                    Task.workspace_id == payload.workspace_id,
                    Task.client_id == payload.task_id,
                    Task.is_deleted.is_(False),
                )
            )
            if task is not None and (
                task.state == TaskStateEnum.READY or task.state in TERMINAL_TASK_STATES
            ):
                await create_instant_task(
                    session=session,
                    task_type=TaskType.PROCESS_ITEM_COST_RESULT,
                    payload=asdict(ItemCostResultPayload(
                        workspace_id=payload.workspace_id,
                        task_id=payload.task_id,
                    )),
                )
            logger.info(
                "step_time_recomputed | workspace_id=%s user_id=%s step_id=%s work_date=%s closing_state=%s",
                payload.workspace_id, payload.credited_user_id, payload.step_id, work_date, closing_state.value,
            )

        shift_reconcile = None
        if payload.credited_user_id:
            shift_reconcile = await reconcile_worker_shift_state(
                session,
                payload.workspace_id,
                payload.credited_user_id,
                now,
            )

        # COMPLETION + ISSUES. Recompute-and-SET from records, exactly like the time path
        # above, so a worker retry cannot double-count: replaying the same transition
        # recomputes identical counts and the Σ deltas collapse to zero. (The queue is
        # at-least-once — the handler commits in its own session, and the task is only
        # marked COMPLETED in a later one, so re-execution is always possible.)
        # Applies regardless of recorded_time_marked_wrong: inaccurate time does not
        # suppress the fact that the step completed or that it carried issues.
        new_state = TaskStepStateEnum(payload.new_state)
        if new_state == TaskStepStateEnum.COMPLETED:
            # User-scoped rollups need somebody to credit. Section-wide totals are derived
            # from those per-user deltas, so they require a credited user too — a narrowing
            # from the pre-recompute path, which incremented section-daily unconditionally.
            # Defensive rather than reachable: every driver of the transition core resolves
            # a non-empty credited user, and no stored record lacks attribution.
            if payload.credited_user_id:
                completion_date = datetime.fromisoformat(payload.exited_at).date()
                completion_result = await reconcile_user_day_completions(
                    session, payload.workspace_id, payload.credited_user_id,
                    credited_user_display_name, completion_date, now,
                )
                await apply_completion_reconcile_deltas(
                    session, payload.workspace_id, payload.credited_user_id,
                    credited_user_display_name, completion_date, now, completion_result,
                )
            # Step-grain counters are a pure function of the step's OWN records and need no
            # credited user, so they must not sit behind that gate — the pre-recompute path
            # incremented task_step.total_completed_count unconditionally.
            await _recompute_step_completion_totals(
                session, payload.workspace_id, payload.step_id, task_step
            )

        if task_step is not None:
            task_step.updated_at = datetime.now(timezone.utc)
        await session.commit()

        # A step transition is what moves a worker between WORKING, IN_PAUSE and IDLE, and
        # that derivation happens here rather than in the request that transitioned the
        # step — so this is the only place that can announce it. Gated on `changed`: most
        # transitions leave the shift state where it was (one of several batched steps
        # pausing, say) and a broadcast per step would be noise.
        if shift_reconcile is not None and shift_reconcile.changed:
            await emit_worker_shift_state(
                session,
                payload.workspace_id,
                payload.credited_user_id,
            )


async def _recompute_step_completion_totals(
    session: AsyncSession,
    workspace_id: str,
    step_id: str,
    step: TaskStep | None,
) -> None:
    """SET the step's own completion/issue counters from records.

    Mirrors _recompute_step_time_totals: absolute assignment rather than increment, so a
    replayed transition cannot inflate them.
    """
    if step is None:
        return

    completed_count = await session.scalar(
        select(func.count())
        .select_from(StepStateRecord)
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.step_id == step_id,
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.is_deleted.is_(False),
        )
    )
    issues_count = await session.scalar(
        select(func.count())
        .select_from(ItemIssue)
        .where(
            ItemIssue.workspace_id == workspace_id,
            ItemIssue.step_id == step_id,
            ItemIssue.is_deleted.is_(False),
        )
    )

    step.total_completed_count = completed_count or 0
    # Resolved mirrors total: reaching COMPLETED is what resolves a step's issues.
    step.total_issues_count = issues_count or 0
    step.total_issues_resolved_count = issues_count or 0


async def _fetch_closing_record(session: AsyncSession, payload: StepTransitionPayload) -> StepStateRecord | None:
    """Fetch the StepStateRecord being closed."""
    result = await session.execute(
        select(StepStateRecord).where(
            StepStateRecord.client_id == payload.closing_record_id,
            StepStateRecord.workspace_id == payload.workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def _fetch_user(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by ID."""
    result = await session.execute(
        select(User).where(User.client_id == user_id)
    )
    return result.scalar_one_or_none()


async def _fetch_task_step(session: AsyncSession, step_id: str, workspace_id: str) -> TaskStep | None:
    """Fetch a non-deleted TaskStep by ID."""
    result = await session.execute(
        select(TaskStep).where(
            TaskStep.client_id == step_id,
            TaskStep.workspace_id == workspace_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()
