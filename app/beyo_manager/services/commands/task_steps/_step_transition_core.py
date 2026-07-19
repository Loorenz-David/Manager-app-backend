"""Shared per-step transition core used by the batch transition command.

DRIFT NOTE: the per-step transition sub-processes here MIRROR
`transition_step_state.transition_step_state` (the single-step endpoint). Any change
to the state-machine handling, record close/open, metrics accrual, terminal handling,
task side-effects, or the PROCESS_STEP_TRANSITION outbox in one of the two MUST be
evaluated for the other — they are intentionally kept in sync by convention
(see docs/architecture/.../PLAN_batch_step_transition_20260623, Option B). The
transition-rules map `_ALLOWED_TRANSITIONS` is single-sourced from `transition_step_state`
and used for validation by the batch command, so the legal transitions cannot drift.

This core is transaction-free and dispatch-free: the caller owns the `maybe_begin`
transaction and the single post-commit `event_bus.dispatch`. It does NOT emit
`CREATE_NOTIFICATIONS` (the batch command coalesces notifications); it returns the
resolved step-pin recipients so the caller can dedupe across the batch.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TIME_BEARING_STATES
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.task_steps.notification_targets import resolve_task_step_notification_targets
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps._cascade_completion import cascade_step_completion
from beyo_manager.services.commands.task_steps._user_working_record import fetch_open_user_working_record
from beyo_manager.services.commands.task_steps.mark_step_time_inaccurate import _apply_inaccurate_time_flag
from beyo_manager.services.commands.tasks._task_state_transitions import (
    maybe_advance_task_to_working,
    maybe_evaluate_task_ready,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task


@dataclass
class StepTransitionApplied:
    """Result of applying one step transition (no events dispatched yet)."""
    step_changed_item: dict          # {"client_id": str, "new_state": str}
    new_record: StepStateRecord      # the freshly opened state record
    step_pin_user_ids: list[str]     # step-pin notification recipients (actor excluded)
    auto_paused_item: dict | None = None  # set only if the guard auto-paused another step
    readiness_changed_items: list[dict] = field(default_factory=list)  # downstream steps whose readiness changed


async def _apply_step_transition(
    ctx: ServiceContext,
    step: TaskStep,
    task: Task,
    closing_record: StepStateRecord,
    *,
    new_state: TaskStepStateEnum,
    reason: StepEventReasonEnum | None,
    description: str | None,
    credited_user_id: str,
    now: datetime,
    mark_closing_record_inaccurate: bool = False,
) -> StepTransitionApplied:
    """Apply one already-validated step transition. Mutates ORM objects and emits the per-step
    PROCESS_STEP_TRANSITION outbox task. Does not commit and does not dispatch realtime events.

    Preconditions (validated by the caller): `step`/`task` exist and are workspace-scoped,
    `new_state` is a legal transition from `step.state`, and `closing_record` is the step's open record.
    """
    effective_user_ids = list({ctx.user_id, credited_user_id})
    auto_paused_item: dict | None = None

    # Auto-pause guard (one-active-step rule). Inert for batch-capable steps — kept for fidelity
    # with the single endpoint so this core behaves identically if ever used for a non-batch step.
    if new_state == TaskStepStateEnum.WORKING and not step.allows_batch_working:
        conflicting_record, conflicting_step = await fetch_open_user_working_record(
            ctx.session, effective_user_ids, ctx.workspace_id, exclude_step_id=step.client_id
        )
        if conflicting_record is not None:
            conflicting_closing_entered_at = conflicting_record.entered_at
            conflicting_record.exited_at = now

            auto_pause_description: str | None = None
            primary_task_item_result = await ctx.session.execute(
                select(TaskItem).where(
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.task_id == task.client_id,
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                )
            )
            primary_task_item = primary_task_item_result.scalar_one_or_none()
            if primary_task_item is not None:
                item_result = await ctx.session.execute(
                    select(Item).where(
                        Item.workspace_id == ctx.workspace_id,
                        Item.client_id == primary_task_item.item_id,
                        Item.is_deleted.is_(False),
                    )
                )
                new_item = item_result.scalar_one_or_none()
                if new_item is not None:
                    identifier = new_item.article_number or new_item.sku
                    if identifier:
                        auto_pause_description = f"started working with {identifier}"

            auto_pause_record = StepStateRecord(
                workspace_id=ctx.workspace_id,
                step_id=conflicting_step.client_id,
                state=TaskStepStateEnum.PAUSED,
                reason=StepEventReasonEnum.PAUSE_OTHER_TASK_PRIORITY,
                description=auto_pause_description,
                entered_at=now,
                exited_at=None,
                created_by_id=ctx.user_id,
                # Auto-pause is credited to the performer (matches the payload below).
                credited_user_id=ctx.user_id,
            )
            ctx.session.add(auto_pause_record)
            await ctx.session.flush()

            conflicting_step.state = TaskStepStateEnum.PAUSED
            conflicting_step.latest_state_record_id = auto_pause_record.client_id
            conflicting_step.updated_at = now
            conflicting_step.updated_by_id = ctx.user_id

            # Time totals recomputed async by the analytics worker (see process_step_transition).

            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.PROCESS_STEP_TRANSITION,
                payload=asdict(StepTransitionPayload(
                    step_id=conflicting_step.client_id,
                    task_id=conflicting_step.task_id,
                    workspace_id=ctx.workspace_id,
                    closing_record_id=conflicting_record.client_id,
                    closing_state=TaskStepStateEnum.WORKING.value,
                    new_state=TaskStepStateEnum.PAUSED.value,
                    performed_by_user_id=ctx.user_id,
                    credited_user_id=ctx.user_id,
                    assigned_worker_id=conflicting_step.assigned_worker_id,
                    working_section_id=conflicting_step.working_section_id,
                    working_section_name_snapshot=conflicting_step.working_section_name_snapshot,
                    entered_at=conflicting_closing_entered_at.isoformat(),
                    exited_at=now.isoformat(),
                    step_task_id=conflicting_step.task_id,
                    closing_record_marked_wrong=conflicting_record.recorded_time_marked_wrong,
                )),
            )
            auto_paused_item = {
                "client_id": conflicting_step.client_id,
                "new_state": TaskStepStateEnum.PAUSED.value,
            }

    # Close current open record
    closing_record.exited_at = now
    closing_state = closing_record.state
    closing_entered_at = closing_record.entered_at

    if mark_closing_record_inaccurate and closing_state in TIME_BEARING_STATES:
        _apply_inaccurate_time_flag(closing_record, step, now)

    # Open new record
    new_record = StepStateRecord(
        workspace_id=ctx.workspace_id,
        step_id=step.client_id,
        state=new_state,
        reason=reason,
        description=description,
        entered_at=now,
        exited_at=None,
        created_by_id=ctx.user_id,
        credited_user_id=credited_user_id,
    )
    ctx.session.add(new_record)
    await ctx.session.flush()  # assign new_record.client_id

    if (
        mark_closing_record_inaccurate
        and new_state == TaskStepStateEnum.COMPLETED
        and closing_state in TIME_BEARING_STATES
    ):
        _apply_inaccurate_time_flag(new_record, step, now)

    # Update step state and latest pointer (circular FK — must be in same transaction)
    step.state = new_state
    step.latest_state_record_id = new_record.client_id
    step.updated_at = now
    step.updated_by_id = ctx.user_id

    # Step time totals (TaskStep.total_*_seconds) are recomputed concurrency-averaged
    # by the analytics worker (PROCESS_STEP_TRANSITION) — see process_step_transition.

    if new_state in TERMINAL_STEP_STATES:
        step.closed_at = now

    # Task state side effects
    if new_state == TaskStepStateEnum.WORKING:
        maybe_advance_task_to_working(task, now=now, updated_by_id=ctx.user_id)

    readiness_changes: list = []
    if new_state in TERMINAL_STEP_STATES:
        await maybe_evaluate_task_ready(
            ctx.session,
            task,
            workspace_id=ctx.workspace_id,
            now=now,
            updated_by_id=ctx.user_id,
        )

        if new_state == TaskStepStateEnum.COMPLETED:
            readiness_changes = await cascade_step_completion(ctx.session, ctx.workspace_id, step)

    # Per-step outbox event for analytics worker (atomic with domain write)
    await create_instant_task(
        session=ctx.session,
        task_type=TaskType.PROCESS_STEP_TRANSITION,
        payload=asdict(StepTransitionPayload(
            step_id=step.client_id,
            task_id=task.client_id,
            workspace_id=ctx.workspace_id,
            closing_record_id=closing_record.client_id,
            closing_state=closing_state.value,
            new_state=new_state.value,
            performed_by_user_id=ctx.user_id,
            credited_user_id=credited_user_id,
            assigned_worker_id=step.assigned_worker_id,
            working_section_id=step.working_section_id,
            working_section_name_snapshot=step.working_section_name_snapshot,
            entered_at=closing_entered_at.isoformat(),
            exited_at=now.isoformat(),
            step_task_id=task.client_id,
            closing_record_marked_wrong=closing_record.recorded_time_marked_wrong,
        )),
    )

    # Resolve (but do not emit) step-pin notification recipients — caller coalesces.
    step_pin_user_ids = list(
        await resolve_task_step_notification_targets(
            ctx.session,
            step.client_id,
            ctx.user_id,
            {"state": new_state.value},
        )
    )

    return StepTransitionApplied(
        step_changed_item={"client_id": step.client_id, "new_state": new_state.value},
        new_record=new_record,
        step_pin_user_ids=step_pin_user_ids,
        auto_paused_item=auto_paused_item,
        readiness_changed_items=[
            {"client_id": dep.client_id, "new_readiness": dep.readiness_status.value}
            for dep, _ in readiness_changes
        ],
    )
