# PLAN_pending_step_completion_20260602

## Metadata

- Plan ID: `PLAN_pending_step_completion_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T08:10:47Z`
- Related issue/ticket: N/A
- Intention plan: N/A

## Goal and intent

- Goal: Change the `COMPLETED` step state transition from an immediate atomic write into a server-side deferred intent with a 5-second undo window. A `DelayedScheduler` row owns the delay; a background worker finalizes the completion if no cancellation arrives; a new `DELETE` endpoint cancels the pending intent.
- Business/user intent: Prevent irreversible data writes from a misclicked "Complete" button on mobile. The undo window is server-owned so it survives app close, tab reload, device sleep, and network drop.
- Non-goals: Applying the delay to FAILED or CANCELLED transitions (those are intentional actions; can be extended later). Showing a visible "pending" state to other users (step stays WORKING during the window — Option A chosen explicitly). Any changes to the step state machine enum itself.

## Scope

- In scope:
  - DB migration: two new PostgreSQL enum values (`delayed_scheduler_type_enum`, `task_type_enum`)
  - Two new Python enum values in `domain/schedulers/enums.py` and `domain/execution/enums.py`
  - Modified `transition_step_state` command: COMPLETED branch defers to scheduler instead of writing inline
  - New cancel command: `services/commands/task_steps/cancel_pending_step_completion.py`
  - New worker task handler: `services/tasks/task_steps/finalize_pending_step_completion.py`
  - New worker process file: `workers/task_steps_worker.py`
  - QUEUE_MAP entry in `services/infra/execution/task_router.py`
  - `DELAYED_TYPE_TO_TASK_TYPE` entry in `services/infra/schedulers/delayed_scheduler_runner.py`
  - Cancel route `DELETE /{task_id}/steps/{step_id}/pending-completion` in `routers/api_v1/tasks.py`
- Out of scope:
  - New model tables or columns (uses existing `DelayedScheduler` table as-is)
  - FAILED / CANCELLED deferred transitions
  - Frontend changes (this plan delivers the backend contract only)
- Assumptions:
  - `DelayedScheduler.event_client_id` is already indexed — confirmed in `models/tables/schedulers/delayed_scheduler.py` line 42.
  - `SchedulerStateEnum.CANCELED` (single-l spelling) is the correct cancel state — confirmed in `domain/schedulers/enums.py`.
  - `completion_requested_at` stored in `payload_snapshot` is used for both the closing `exited_at` of the WORKING record and the `entered_at` of the COMPLETED record, preserving accurate time accounting independent of worker fire latency.
  - The step remains in WORKING state during the 5-second window (Option A). No intermediate state is introduced.
  - `delayed_scheduler_runner` polls every 10 seconds with a 10-second `POLL_INTERVAL_SECONDS`. The window is 5 seconds by design — the scheduler will fire on the next poll cycle after `scheduled_for` passes, giving an effective delay of 5–15 seconds. This is acceptable for the undo UX.

## Clarifications required

(All resolved before writing this plan.)

## Acceptance criteria

1. `POST /{task_id}/steps/{step_id}/transition` with `new_state=completed` returns `{ "pending_completion_id": "dsch_xxx", "expires_at": "<iso>" }` and does NOT write `step.state = completed` immediately.
2. If no cancel request arrives within 5 seconds, the worker finalizes the completion: `step.state` becomes `completed`, `StepStateRecord` is closed and a new COMPLETED record is opened, dependency readiness is recalculated, task state side effects fire, analytics task is enqueued, notification pins fire, and realtime events are dispatched.
3. `DELETE /{task_id}/steps/{step_id}/pending-completion` called within the window sets the `DelayedScheduler.state = canceled` and returns `{ "cancelled": true }`. The worker handler then becomes a no-op (the scheduler is never fired because its state is no longer ACTIVE).
4. `DELETE` called after the window expires (scheduler already FIRED) returns a `ConflictError` — the pending intent no longer exists.
5. Non-COMPLETED transitions (WORKING, PAUSED, ENDED_SHIFT, FAILED, CANCELLED) remain synchronous and unchanged.
6. Analytics `PROCESS_STEP_TRANSITION` task is enqueued from the worker (not the HTTP handler) with correct `entered_at` / `exited_at` drawn from the payload's `completion_requested_at`.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: layered structure — enum → model → command → router
- `../../../architecture/04_context.md`: `ServiceContext` usage, `user_id` / `workspace_id` extraction
- `../../../architecture/05_errors.md`: `ConflictError`, `NotFound` raise patterns
- `../../../architecture/06_commands.md` + `../../../architecture/06_commands_local.md`: command signature, `maybe_begin`, session.add / flush / error raising
- `../../../architecture/09_routers.md`: `run_service`, `build_ok` / `build_err`, handler wiring
- `../../../architecture/16_background_jobs.md`: worker handler signature, queue consumption pattern
- `../../../architecture/21_naming_conventions.md`: file names, function names
- `../../../architecture/30_migrations.md`: Alembic migration for PostgreSQL enum additions
- `../../../architecture/37_scheduled_jobs.md`: `DelayedScheduler` usage pattern
- `../../../architecture/40_identity.md`: workspace scoping on every query

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: `maybe_begin` transaction utility, session call safety, subordinate-command event rule.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead.
- **What exists** → reading is legitimate.

Permitted reads for this plan:
- `models/tables/schedulers/delayed_scheduler.py` — field names (`event_client_id`, `state`, `payload_snapshot`, `type`, `scheduled_for`)
- `models/tables/tasks/task_step.py` — field names for validation and update
- `models/tables/tasks/step_state_record.py` — field names for record creation
- `models/tables/tasks/task.py` — field names for task state side effects
- `domain/schedulers/enums.py` — `SchedulerStateEnum`, `DelayedSchedulerTypeEnum`
- `domain/execution/enums.py` — `TaskType`
- `services/commands/task_steps/transition_step_state.py` — extract the existing COMPLETED branch logic verbatim for the worker handler
- `services/infra/schedulers/delayed_scheduler_runner.py` — verify `DELAYED_TYPE_TO_TASK_TYPE` dict location for the new entry
- `services/infra/execution/task_router.py` — verify `QUEUE_MAP` dict location for the new entry
- `workers/analytics_worker.py` — confirm `run_worker` call pattern before creating `task_steps_worker.py`
- `routers/api_v1/tasks.py` — confirm existing step route patterns before adding the cancel route

Prohibited (pattern reads — contracts cover these):
- Reading another command to understand session.add / flush shape → `06_commands.md`
- Reading another router handler to understand wiring → `09_routers.md`
- Reading another worker file to understand handler signature → `16_background_jobs.md`

### Skill selection

- Primary skill: command + worker pattern (`06_commands.md`, `16_background_jobs.md`)
- Router trigger terms: `transition`, `pending-completion`, `cancel`
- Excluded alternatives: query pattern (`07_queries.md`) — all operations here write state

---

## Implementation plan

### Step 1 — DB migration: add two new enum values

Create a new Alembic migration file. The migration must be additive-only (no drop, no rename).

```sql
-- upgrade
ALTER TYPE delayed_scheduler_type_enum ADD VALUE IF NOT EXISTS 'pending_step_completion';
ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'delayed_step_completion';

-- downgrade: PostgreSQL does not support removing enum values.
-- Leave downgrade as a no-op (pass) or document that manual intervention is required.
```

**Why two enums:** `delayed_scheduler_type_enum` maps to `DelayedScheduler.type`; `task_type_enum` maps to `ExecutionTask.task_type`. Both are PostgreSQL native enums confirmed by `SAEnum(..., create_type=True)` in their respective model files.

---

### Step 2 — Add new enum values to Python enums

**File: `beyo_manager/domain/schedulers/enums.py`**

Add to `DelayedSchedulerTypeEnum`:

```python
PENDING_STEP_COMPLETION = "pending_step_completion"
```

**File: `beyo_manager/domain/execution/enums.py`**

Add to `TaskType`:

```python
DELAYED_STEP_COMPLETION = "delayed_step_completion"
```

No other changes to these files.

---

### Step 3 — Register the new scheduler type in `delayed_scheduler_runner.py`

**File: `beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py`**

Add one entry to `DELAYED_TYPE_TO_TASK_TYPE`:

```python
DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION: TaskType.DELAYED_STEP_COMPLETION,
```

No other changes to this file.

---

### Step 4 — Register the new task type in `task_router.py`

**File: `beyo_manager/services/infra/execution/task_router.py`**

Add one entry to `QUEUE_MAP`:

```python
TaskType.DELAYED_STEP_COMPLETION: "queue:step_completions",
```

A dedicated queue name avoids coupling with existing workers and allows independent scaling.

No other changes to this file.

---

### Step 5 — Modify `transition_step_state` for the COMPLETED branch

**File: `beyo_manager/services/commands/task_steps/transition_step_state.py`**

The overall function structure is unchanged. The ONLY modification is what happens when `request.new_state == TaskStepStateEnum.COMPLETED`.

**Add import at top of file:**
```python
from datetime import timedelta
from beyo_manager.domain.schedulers.enums import DelayedSchedulerTypeEnum, SchedulerOriginSourceEnum
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
```

**Replace the existing COMPLETED branch** (currently steps 6–9 execute inline) with an early-return path:

Inside `async with maybe_begin(ctx.session):`, after step 3 (task fetched) and after `credited_user_id` is resolved:

```python
# Early-exit path for COMPLETED: defer to a scheduled job with undo window.
if request.new_state == TaskStepStateEnum.COMPLETED:
    COMPLETION_DELAY_SECONDS = 5
    scheduled_for = now + timedelta(seconds=COMPLETION_DELAY_SECONDS)
    scheduler = DelayedScheduler(
        type=DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION,
        state=SchedulerStateEnum.ACTIVE,
        origin_source=SchedulerOriginSourceEnum.COMMAND,
        event_client_id=step.client_id,
        scheduled_for=scheduled_for,
        payload_snapshot={
            "step_id": step.client_id,
            "task_id": task.client_id,
            "workspace_id": ctx.workspace_id,
            "completion_requested_at": now.isoformat(),
            "performed_by_user_id": ctx.user_id,
            "credited_user_id": credited_user_id,
            "reason": request.reason.value if request.reason else None,
            "description": request.description,
        },
    )
    ctx.session.add(scheduler)
    await ctx.session.flush()
    return {
        "pending_completion_id": scheduler.client_id,
        "expires_at": scheduled_for.isoformat(),
    }
```

The existing code below this block (steps 5–9: closing StepStateRecord, opening new one, task side effects, analytics, notifications, events) is only reached for non-COMPLETED transitions and is left **completely unchanged**.

**Import `SchedulerStateEnum`** — it is already available in `domain/schedulers/enums.py`; add to the import from that module.

**Critical constraint:** The `return` inside the `async with maybe_begin(ctx.session):` block exits the block normally, triggering commit. The `event_bus.dispatch` call and the `return` of the final dict at the bottom of the function are NOT reached for COMPLETED transitions.

---

### Step 6 — New cancel command

**New file: `beyo_manager/services/commands/task_steps/cancel_pending_step_completion.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.schedulers.enums import DelayedSchedulerTypeEnum, SchedulerStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def cancel_pending_step_completion(ctx: ServiceContext) -> dict:
    step_id = ctx.incoming_data["step_id"]
    task_id = ctx.incoming_data["task_id"]

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # 1. Verify the step exists and belongs to this workspace/task.
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == step_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        # 2. Find the active pending completion scheduler for this step.
        scheduler_result = await ctx.session.execute(
            select(DelayedScheduler).where(
                DelayedScheduler.event_client_id == step.client_id,
                DelayedScheduler.type == DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION,
                DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
            )
        )
        scheduler = scheduler_result.scalar_one_or_none()
        if scheduler is None:
            raise ConflictError("No active pending completion found for this step. The undo window may have expired.")

        # 3. Cancel the scheduler. The delayed_scheduler_runner skips non-ACTIVE rows.
        scheduler.state = SchedulerStateEnum.CANCELED
        scheduler.updated_at = now

    return {"cancelled": True}
```

---

### Step 7 — New worker task handler

**New file: `beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py`**

This handler runs the COMPLETED branch logic that was removed from `transition_step_state`. It is called by the `task_steps_worker` after the undo window expires.

```python
"""Worker handler — finalizes a pending step completion after the undo window expires."""

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum, TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.domain.tasks.serializers import serialize_step_state_record_light
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.models.database import get_db_session

logger = logging.getLogger(__name__)

_TERMINAL_STEP_STATES = frozenset({
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
    TaskStepStateEnum.CANCELLED,
})

_TERMINAL_TASK_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})


async def handle_finalize_pending_step_completion(payload: dict) -> None:
    step_id          = payload["step_id"]
    task_id          = payload["task_id"]
    workspace_id     = payload["workspace_id"]
    performed_by     = payload["performed_by_user_id"]
    credited_user_id = payload["credited_user_id"]
    reason_raw       = payload.get("reason")
    description      = payload.get("description")
    reason = StepEventReasonEnum(reason_raw) if reason_raw else None

    # Use completion_requested_at for both exited_at and entered_at so analytics
    # reflects when the user tapped Complete, not when the worker fired.
    completion_requested_at = datetime.fromisoformat(payload["completion_requested_at"])
    now = datetime.now(timezone.utc)

    readiness_changes: list[tuple] = []
    old_task_state = None
    pending_events = []

    async for session in get_db_session():
        async with session.begin():

            # 1. Fetch step — guard: skip if step already moved on.
            step_result = await session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == workspace_id,
                    TaskStep.client_id == step_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            step = step_result.scalar_one_or_none()
            if step is None:
                logger.warning("finalize_pending_step_completion | step_not_found | step_id=%s", step_id)
                return
            if step.state != TaskStepStateEnum.WORKING:
                logger.info(
                    "finalize_pending_step_completion | skipped | step_id=%s current_state=%s",
                    step_id, step.state.value,
                )
                return

            # 2. Fetch task.
            task_result = await session.execute(
                select(Task).where(
                    Task.workspace_id == workspace_id,
                    Task.client_id == task_id,
                    Task.is_deleted.is_(False),
                )
            )
            task = task_result.scalar_one_or_none()
            if task is None:
                logger.warning("finalize_pending_step_completion | task_not_found | task_id=%s", task_id)
                return
            old_task_state = task.state

            # 3. Close the open WORKING StepStateRecord.
            open_record_result = await session.execute(
                select(StepStateRecord).where(
                    StepStateRecord.workspace_id == workspace_id,
                    StepStateRecord.step_id == step.client_id,
                    StepStateRecord.exited_at.is_(None),
                )
            )
            closing_record = open_record_result.scalar_one_or_none()
            if closing_record is None:
                logger.warning(
                    "finalize_pending_step_completion | no_open_record | step_id=%s", step_id
                )
                return
            closing_state = closing_record.state
            closing_entered_at = closing_record.entered_at
            # Use completion_requested_at so analytics reflects user-tap time.
            closing_record.exited_at = completion_requested_at

            # 4. Open new COMPLETED StepStateRecord.
            new_record = StepStateRecord(
                workspace_id=workspace_id,
                step_id=step.client_id,
                state=TaskStepStateEnum.COMPLETED,
                reason=reason,
                description=description,
                entered_at=completion_requested_at,
                exited_at=None,
                created_by_id=performed_by,
            )
            session.add(new_record)
            await session.flush()

            # 5. Update step.
            step.state = TaskStepStateEnum.COMPLETED
            step.latest_state_record_id = new_record.client_id
            step.closed_at = completion_requested_at
            step.updated_at = now
            step.updated_by_id = performed_by

            # 6. Recalculate readiness on dependent steps.
            dependent_edges_result = await session.execute(
                select(TaskStepDependency).where(
                    TaskStepDependency.workspace_id == workspace_id,
                    TaskStepDependency.prerequisite_step_id == step.client_id,
                    TaskStepDependency.removed_at.is_(None),
                )
            )
            for edge in dependent_edges_result.scalars().all():
                dep_step_result = await session.execute(
                    select(TaskStep).where(
                        TaskStep.workspace_id == workspace_id,
                        TaskStep.client_id == edge.dependent_step_id,
                        TaskStep.is_deleted.is_(False),
                    )
                )
                dep_step = dep_step_result.scalar_one_or_none()
                if dep_step is not None:
                    old_dep_readiness = dep_step.readiness_status
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)
                    readiness_changes.append((dep_step, old_dep_readiness))

            # 7. Check if all steps terminal → task READY.
            all_steps_result = await session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            all_steps = all_steps_result.scalars().all()
            if all_steps and all(s.state in _TERMINAL_STEP_STATES for s in all_steps):
                if task.state not in _TERMINAL_TASK_STATES:
                    task.state = TaskStateEnum.READY
                    task.updated_at = now
                    task.updated_by_id = performed_by

            # 8. Analytics outbox task.
            analytics_payload = StepTransitionPayload(
                step_id=step.client_id,
                task_id=task.client_id,
                workspace_id=workspace_id,
                closing_record_id=closing_record.client_id,
                closing_state=closing_state.value,
                new_state=TaskStepStateEnum.COMPLETED.value,
                performed_by_user_id=performed_by,
                credited_user_id=credited_user_id,
                assigned_worker_id=step.assigned_worker_id,
                working_section_id=step.working_section_id,
                working_section_name_snapshot=step.working_section_name_snapshot,
                entered_at=closing_entered_at.isoformat(),
                exited_at=completion_requested_at.isoformat(),
                step_task_id=task.client_id,
            )
            await create_instant_task(
                session=session,
                task_type=TaskType.PROCESS_STEP_TRANSITION,
                payload=asdict(analytics_payload),
            )

            # 9. Notification pins.
            step_pins_result = await session.execute(
                select(NotificationPin.user_id).where(
                    NotificationPin.entity_type == "task_step",
                    NotificationPin.entity_client_id == step.client_id,
                )
            )
            step_pin_user_ids = [
                uid for uid in step_pins_result.scalars().all()
                if uid != performed_by
            ]
            if step_pin_user_ids:
                await create_instant_task(
                    session=session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(NotificationPayload(
                        notification_type="task_step_state_changed",
                        user_ids=step_pin_user_ids,
                        title="Step state changed",
                        body="A step you are following has changed state.",
                        entity_type="task_step",
                        entity_client_id=step.client_id,
                        exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                    )),
                )

            # 10. Build events (collected outside transaction, dispatched below).
            pending_events.append(
                build_workspace_event(step, "task:step-state-changed", extra={"new_state": TaskStepStateEnum.COMPLETED.value})
            )
            for dep_step, old_dep_readiness in readiness_changes:
                if dep_step.readiness_status != old_dep_readiness:
                    pending_events.append(WorkspaceEvent(
                        event_name="task:step-readiness-changed",
                        client_id=dep_step.client_id,
                        workspace_id=workspace_id,
                        extra={"new_readiness": dep_step.readiness_status.value},
                    ))
            if task.state != old_task_state:
                pending_events.append(
                    build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
                )

    await event_bus.dispatch(pending_events)
```

**Note on handler signature:** Read `16_background_jobs.md` to confirm the exact signature the `run_worker` dispatcher expects before finalizing. If it passes the full `ExecutionTask` object instead of a plain `dict`, extract the payload via `task.payload.payload`.

---

### Step 8 — New worker process file

**New file: `beyo_manager/workers/task_steps_worker.py`**

Mirrors the pattern of `analytics_worker.py` exactly.

```python
import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.task_steps.finalize_pending_step_completion import (
    handle_finalize_pending_step_completion,
)

HANDLER_MAP = {
    TaskType.DELAYED_STEP_COMPLETION: handle_finalize_pending_step_completion,
}


async def main() -> None:
    await init_db()
    await run_worker("queue:step_completions", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
```

**Deployment note:** This new worker process must be added to whatever process manager runs the other workers (Docker Compose, Procfile, supervisord). This is out of scope for code changes but must be done before the feature is live.

---

### Step 9 — Add cancel route to `routers/api_v1/tasks.py`

**Add import:**
```python
from beyo_manager.services.commands.task_steps.cancel_pending_step_completion import (
    cancel_pending_step_completion,
)
```

**Add route** (place it adjacent to the existing `transition` route):
```python
@router.delete("/{task_id}/steps/{step_id}/pending-completion")
async def route_cancel_pending_step_completion(
    task_id: str,
    step_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"step_id": step_id, "task_id": task_id},
        query_params={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(cancel_pending_step_completion, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

## Risks and mitigations

- **Risk:** The step is transitioned by someone else (e.g., auto-paused or cancelled by a manager) during the 5-second window, then the worker fires and overwrites that new state.
  **Mitigation:** Step 7 guard — `if step.state != TaskStepStateEnum.WORKING: return`. The worker silently skips if the step is no longer WORKING. This is the correct behavior: the pending completion is stale.

- **Risk:** `delayed_scheduler_runner` polls every 10 seconds, so the effective undo window is 5–15 seconds, not exactly 5.
  **Mitigation:** Document this behavior for the frontend. The frontend timer should show 10–12 seconds to ensure the scheduler fires before the UX timer hides the undo button. Alternatively the `POLL_INTERVAL_SECONDS` can be reduced to 3 seconds in `delayed_scheduler_runner.py` with no other changes.

- **Risk:** Multiple `PENDING_STEP_COMPLETION` schedulers accumulate for the same step if the user taps Complete repeatedly before the window expires.
  **Mitigation:** In Step 5, before creating the `DelayedScheduler`, check for an existing `ACTIVE` scheduler with `event_client_id == step.client_id` and `type == PENDING_STEP_COMPLETION`. If one exists, raise a `ConflictError("A pending completion already exists for this step.")`. This prevents duplicate schedulers.

- **Risk:** `completion_requested_at` stored as ISO string in `payload_snapshot` could fail to parse in the worker if the format changes.
  **Mitigation:** Always use `datetime.isoformat()` for storage and `datetime.fromisoformat()` for parsing — both are standard library. Include a try/except in the worker handler that logs and returns on `ValueError`.

- **Risk:** New worker `task_steps_worker.py` not registered in the process manager means the `queue:step_completions` queue never drains.
  **Mitigation:** Add a note in the deployment checklist. The `task_router.py` will push tasks to `queue:step_completions`; the delayed_scheduler_runner will fire them — they will accumulate as `PENDING` tasks until the worker is started. No data is lost, but completions will be delayed.

- **Risk:** `SchedulerStateEnum.CANCELED` (single-l) vs. common double-l spelling causes a Python enum lookup error.
  **Mitigation:** Confirmed from `domain/schedulers/enums.py` that the value is `"canceled"` (single-l). Use `SchedulerStateEnum.CANCELED` everywhere; do not use string literals for state comparisons.

## Validation plan

- `POST /{task_id}/steps/{step_id}/transition` with `new_state=completed` → response is `{ "pending_completion_id": "dsch_xxx", "expires_at": "..." }`, step remains in `working` state in DB.
- Wait 15 seconds with no cancel → step transitions to `completed` in DB, analytics `PROCESS_STEP_TRANSITION` task is enqueued, readiness of dependent steps recalculated.
- `POST /{task_id}/steps/{step_id}/transition` with `new_state=completed`, then immediately `DELETE /{task_id}/steps/{step_id}/pending-completion` → response `{ "cancelled": true }`, `DelayedScheduler.state = canceled`, step remains `working` after 15 seconds.
- `DELETE` after scheduler already fired → `ConflictError` with message about expired window.
- `POST /transition` with `new_state=working` or `new_state=paused` → immediate synchronous response, step state changes in same HTTP request (unchanged behavior).
- `POST /transition` with `new_state=completed` while an `ACTIVE` scheduler already exists → `ConflictError("A pending completion already exists for this step.")`.
- Worker guard: manually set a step to `paused` (via a second parallel transition) before the scheduler fires → worker logs "skipped", step remains `paused`, no `completed` write.

## Review log

- `2026-06-02` plan author: initial draft

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `david`
