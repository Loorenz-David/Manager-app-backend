"""Batch step state transition — atomic, multi-step driver reusing `_apply_step_transition`.

Validates every item up front (atomic all-or-nothing: any invalid item rejects the whole
batch and mutates nothing), applies each transition via the shared core inside one
transaction, then dispatches a single coalesced realtime event plus coalesced notifications.

Only batch-capable steps (`allows_batch_working = True`) are accepted, so the one-active-step
auto-pause guard never fires in this path. See PLAN_batch_step_transition_20260623.
"""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.tasks.notification_targets import resolve_task_notification_targets
from beyo_manager.domain.tasks.serializers import serialize_step_state_record_light
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.commands.task_steps.requests import parse_batch_transition_step_state_request
from beyo_manager.services.commands.task_steps.transition_step_state import _ALLOWED_TRANSITIONS
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent, WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


def _format_batch_errors(errors: list[dict]) -> str:
    parts = [f"{e['step_id']}: {e['error']}" for e in errors]
    return "Batch transition rejected — " + "; ".join(parts)


async def transition_step_state_batch(ctx: ServiceContext) -> dict:
    """Atomically transition 1..N batch-capable steps to one target state; coalesced events/notifications."""
    request = parse_batch_transition_step_state_request(ctx.incoming_data)
    new_state = request.new_state
    # v1: a batch credits the performer; per-item credited_user_id is not supported.
    credited_user_id = ctx.user_id

    step_ids = [item.step_id for item in request.items]

    changed_tasks: list[Task] = []
    state_changed_items: list[dict] = []
    result_items: list[dict] = []

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # --- Batch-load steps, tasks, and open records (3 queries, independent of N) ---
        steps = (
            await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.client_id.in_(step_ids),
                    TaskStep.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        steps_by_id = {s.client_id: s for s in steps}

        task_ids = {s.task_id for s in steps}
        tasks = (
            (
                await ctx.session.execute(
                    select(Task).where(
                        Task.workspace_id == ctx.workspace_id,
                        Task.client_id.in_(task_ids),
                        Task.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            if task_ids
            else []
        )
        tasks_by_id = {t.client_id: t for t in tasks}

        open_records = (
            await ctx.session.execute(
                select(StepStateRecord).where(
                    StepStateRecord.workspace_id == ctx.workspace_id,
                    StepStateRecord.step_id.in_(step_ids),
                    StepStateRecord.exited_at.is_(None),
                )
            )
        ).scalars().all()
        open_record_by_step = {r.step_id: r for r in open_records}

        # --- Phase 1: validate everything, mutate nothing (atomic all-or-nothing) ---
        errors: list[dict] = []
        for item in request.items:
            sid = item.step_id
            step = steps_by_id.get(sid)
            if step is None:
                errors.append({"step_id": sid, "error": "Task step not found."})
                continue
            if step.task_id != item.task_id:
                errors.append({"step_id": sid, "error": "Step does not belong to the provided task."})
                continue
            if not step.allows_batch_working:
                errors.append({"step_id": sid, "error": "Step is not batch-capable."})
                continue
            if tasks_by_id.get(step.task_id) is None:
                errors.append({"step_id": sid, "error": "Task not found."})
                continue
            if step.state in TERMINAL_STEP_STATES:
                errors.append({"step_id": sid, "error": f"Step is in terminal state {step.state.value}."})
                continue
            if new_state not in _ALLOWED_TRANSITIONS.get(step.state, set()):
                errors.append(
                    {"step_id": sid, "error": f"Cannot transition from {step.state.value} to {new_state.value}."}
                )
                continue
            if open_record_by_step.get(sid) is None:
                errors.append({"step_id": sid, "error": "No open state record found for this step."})
                continue

        if errors:
            raise ValidationError(_format_batch_errors(errors))

        # Capture original task states to detect net changes after applying all steps.
        old_task_states = {t.client_id: t.state for t in tasks}

        # --- Phase 2: apply each transition via the shared core ---
        step_pin_union: set[str] = set()
        # Keyed by client_id; last write wins (monotone toward READY within a batch).
        readiness_by_step: dict[str, str] = {}
        for item in request.items:
            step = steps_by_id[item.step_id]
            task = tasks_by_id[step.task_id]
            closing_record = open_record_by_step[item.step_id]
            applied = await _apply_step_transition(
                ctx,
                step,
                task,
                closing_record,
                new_state=new_state,
                reason=request.reason,
                description=request.description,
                credited_user_id=credited_user_id,
                now=now,
                mark_closing_record_inaccurate=item.mark_closing_record_inaccurate,
            )
            state_changed_items.append(applied.step_changed_item)
            if applied.auto_paused_item is not None:
                state_changed_items.append(applied.auto_paused_item)
            step_pin_union.update(applied.step_pin_user_ids)
            for r in applied.readiness_changed_items:
                readiness_by_step[r["client_id"]] = r["new_readiness"]
            result_items.append(
                {
                    "step_id": item.step_id,
                    "new_state": new_state.value,
                    "last_state_record": serialize_step_state_record_light(applied.new_record),
                }
            )

        # --- Coalesced notifications ---
        # Step-level: one notification to the deduped union of step watchers (no N-fold pings).
        if step_pin_union:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(
                    NotificationPayload(
                        notification_type="task_step_state_changed",
                        user_ids=sorted(step_pin_union),
                        title="Steps updated",
                        body=f"{len(request.items)} steps changed to {new_state.value}",
                    )
                ),
            )

        # Task-level: one notification per distinct task whose state net-changed.
        actor = ctx.identity.get("username") or "someone"
        changed_tasks = [t for t in tasks if t.state != old_task_states.get(t.client_id)]
        for task in changed_tasks:
            task_pin_user_ids = list(
                await resolve_task_notification_targets(
                    ctx.session,
                    ctx.workspace_id,
                    task.client_id,
                    task.created_by_id,
                    ctx.user_id,
                    {"state": task.state.value},
                )
            )
            if task_pin_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(
                        NotificationPayload(
                            notification_type="task_state_changed",
                            user_ids=task_pin_user_ids,
                            title=f"Task #{task.task_scalar_id} {task.state.value}",
                            body=f"#{task.task_scalar_id} · by {actor}",
                            entity_type="task",
                            entity_client_id=task.client_id,
                            exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                        )
                    ),
                )

    # --- Post-commit: single coalesced realtime dispatch ---
    pending_events: list = [
        BatchWorkspaceEvent(
            event_name="task:step-state-changed",
            workspace_id=ctx.workspace_id,
            items=state_changed_items,
        ),
    ]
    for task in changed_tasks:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    for step_id, new_readiness in readiness_by_step.items():
        pending_events.append(
            WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=step_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": new_readiness},
            )
        )
    await event_bus.dispatch(pending_events)

    return {"items": result_items}
