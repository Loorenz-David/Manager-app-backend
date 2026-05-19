# PLAN_step_state_machine_20260518

## Metadata

- Plan ID: `PLAN_step_state_machine_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-5`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement CMD-12 `transition_step_state` — the step state machine driver. This command atomically closes the current `StepStateRecord`, opens a new one, applies task-level state side effects, and publishes an outbox event for the analytics worker. This is the most complex command in the system.
- **Business/user intent:** Workers drive all time-recording and progress-tracking by transitioning step states. Every transition is immutably recorded in `step_state_records`. The outbox event triggers the analytics pipeline.
- **Non-goals:** Analytics worker (Plan 6). WebSocket / realtime push (deferred — see open questions in intention plan). No new models or migrations.

---

## Prerequisite

**Plans 1, 2, 3, and 4 must be completed before this plan.** Specifically:
- `StepStateRecord` rows must be created by CMD-9 (Plan 3) for steps to have an open record to close.
- `recalculate_readiness` must exist in `_readiness.py` (Plan 4).
- `TaskType.PROCESS_STEP_TRANSITION` must be added to `domain/execution/enums.py` as part of this plan (Step 1 below).
- `create_instant_task` from `services/infra/execution/task_factory.py` must be callable.

---

## Scope

- **In scope:**
  - Add `TaskType.PROCESS_STEP_TRANSITION` to `domain/execution/enums.py`
  - Add `domain/execution/payloads/step_transition.py` — payload dataclass
  - New command: `services/commands/task_steps/transition_step_state.py` — CMD-12
  - Request models appended to `services/commands/task_steps/requests/__init__.py`
  - Route additions to `routers/api_v1/tasks.py`
  - Add `PROCESS_STEP_TRANSITION` to the task router's `QUEUE_MAP` (pointing to `queue:analytics`)
- **Out of scope:** Analytics handler (Plan 6). No changes to existing commands.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. `POST /api/v1/tasks/{task_id}/steps/{step_id}/transition` accepts `{new_state, reason?, description?}` and performs the state transition atomically: closes current open `StepStateRecord` (`exited_at = now`) + opens new `StepStateRecord` (`state = new_state, entered_at = now`). Both happen in the same `maybe_begin` transaction.
2. After the transition, `step.latest_state_record_id` is updated to the new `StepStateRecord.client_id`. This update is transactionally coupled (inside the same `maybe_begin` block).
3. After the transition, `step.state` is updated to `new_state`.
4. **Task state side effects:**
   - If `new_state == WORKING` AND `task.state == ASSIGNED` → `task.state = WORKING`.
   - If `new_state == COMPLETED` → call `recalculate_readiness` on ALL dependent steps (steps that have `this step` as a prerequisite). Also: if all non-deleted task steps are now in terminal states → `task.state = READY`.
5. After closing the old record, `create_instant_task` is called with `task_type = TaskType.PROCESS_STEP_TRANSITION` and the step transition payload. The outbox event is published inside the same transaction as the record close (atomic with the domain write).
6. Invalid state transitions raise `ValidationError`. The full allowed-transitions table is defined below and enforced in code.
7. A step in a terminal state (`COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`) cannot be transitioned. Raise `ConflictError`.
8. `step.updated_at` and `step.updated_by_id` are set after each transition.
9. A side-effect stub `_dispatch_section_side_effects(step, new_state, session)` is defined as an empty async function in the command module, called after the transition and before the outbox event. It is a clearly marked extension point for future notification/socket implementation.

---

## Allowed transitions (enforced in code)

```python
_ALLOWED_TRANSITIONS: dict[TaskStepStateEnum, set[TaskStepStateEnum]] = {
    TaskStepStateEnum.PENDING:      {TaskStepStateEnum.WORKING},
    TaskStepStateEnum.WORKING:      {TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT, TaskStepStateEnum.COMPLETED, TaskStepStateEnum.FAILED, TaskStepStateEnum.CANCELLED},
    TaskStepStateEnum.PAUSED:       {TaskStepStateEnum.WORKING, TaskStepStateEnum.ENDED_SHIFT, TaskStepStateEnum.FAILED, TaskStepStateEnum.CANCELLED},
    TaskStepStateEnum.ENDED_SHIFT:  {TaskStepStateEnum.WORKING, TaskStepStateEnum.FAILED, TaskStepStateEnum.CANCELLED},
    # Terminal states: no transitions allowed
    TaskStepStateEnum.COMPLETED:    set(),
    TaskStepStateEnum.SKIPPED:      set(),
    TaskStepStateEnum.FAILED:       set(),
    TaskStepStateEnum.CANCELLED:    set(),
    TaskStepStateEnum.BLOCKED:      set(),
}
```

Validation logic:
```python
allowed = _ALLOWED_TRANSITIONS.get(step.state, set())
if new_state not in allowed:
    raise ValidationError(
        f"Cannot transition from {step.state.value} to {new_state.value}."
    )
```

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: structure
- `backend/architecture/04_context.md`: `ServiceContext`
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound`, `ConflictError`
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, subordinate-command event rule (**subordinate commands must NOT fire their own events — this command IS the owner and IS allowed to fire the event**), circular FK pointer update
- `backend/architecture/09_routers.md`: router wiring
- `backend/architecture/16_background_jobs.md`: `create_instant_task` usage, payload dataclass with `asdict()`, atomic event creation inside the domain transaction
- `backend/architecture/21_naming_conventions.md`: naming

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/tasks/step_state_record.py` | All columns: `step_id`, `state`, `reason`, `description`, `accuracy`, `entered_at`, `exited_at`, `taken_from_average`, `created_by_id` |
| `models/tables/tasks/task_step.py` | `latest_state_record_id` circular FK, `state`, `task_id`, `working_section_id`, `assigned_worker_id` |
| `models/tables/tasks/task_step_dependency.py` | To query dependent steps: `prerequisite_step_id == step.client_id, removed_at IS NULL` |
| `models/tables/tasks/task.py` | `state` column, `TaskStateEnum.WORKING`, `TaskStateEnum.READY` |
| `models/tables/tasks/README.md` | Step state machine rules, active record rule, circular FK update rule |
| `services/infra/execution/task_factory.py` | `create_instant_task(session, task_type, payload)` exact signature |
| `domain/execution/enums.py` | `TaskType` enum — where to append `PROCESS_STEP_TRANSITION` |
| `domain/execution/payloads/notification.py` | Payload dataclass pattern: `@dataclass(frozen=True)`, `asdict()` usage |
| `services/commands/task_steps/_readiness.py` | `recalculate_readiness(step)` signature |
| `services/commands/task_steps/add_step_dependency.py` | Pattern for querying dependent steps |
| `domain/task_steps/enums.py` | Full enum for `StepEventReasonEnum`, `TaskStepStateEnum` |

---

## Implementation plan

### Step 1 — Add `TaskType.PROCESS_STEP_TRANSITION` to `domain/execution/enums.py`

Append to the `TaskType` enum:
```python
# Analytics — step state transition event
PROCESS_STEP_TRANSITION = "process_step_transition"
```

Add to the task router's `QUEUE_MAP` in `workers/task_router_process.py`:
```python
TaskType.PROCESS_STEP_TRANSITION: "queue:analytics",
```

**Note:** `queue:analytics` is a new queue name. The analytics worker (Plan 6) will subscribe to it. The task router will start routing these tasks immediately; the worker is not yet consuming them — tasks will queue up until Plan 6 creates the consumer. This is safe: tasks stay in the DB as `OPEN` until a worker claims them.

### Step 2 — Payload dataclass: `domain/execution/payloads/step_transition.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class StepTransitionPayload:
    step_id: str
    task_id: str
    workspace_id: str
    closing_record_id: str      # client_id of the StepStateRecord being closed (exited_at set)
    closing_state: str          # the state of the record being closed (old state)
    new_state: str              # the state being entered
    assigned_worker_id: str | None
    working_section_id: str
    entered_at: str             # ISO 8601 string of the closing record's entered_at
    exited_at: str              # ISO 8601 string of the closing record's exited_at (now)
    step_task_id: str           # same as task_id — included for worker convenience
```

**Payload rules (from `16_background_jobs.md`):**
- All fields are JSON-serialisable (strings, not datetime objects). Convert `datetime` to `isoformat()` before putting in the payload.
- Always use `dataclasses.asdict()` to build the dict passed to `create_instant_task`.
- Always deserialise with `StepTransitionPayload(**raw)` as the first line of the handler.

### Step 3 — Request models append: `services/commands/task_steps/requests/__init__.py`

```
TransitionStepStateRequest:
  step_id: str
  task_id: str
  new_state: TaskStepStateEnum
  reason: StepEventReasonEnum | None = None
  description: str | None = None
```

Parse function: standard pattern.

### Step 4 — CMD-12: `services/commands/task_steps/transition_step_state.py`

**Full implementation:**

```python
"""CMD-12: Atomic step state machine driver with StepStateRecord management and outbox event."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.conflict import ConflictError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness
from beyo_manager.services.commands.task_steps.requests import parse_transition_step_state_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task


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

_ALLOWED_TRANSITIONS: dict[TaskStepStateEnum, set[TaskStepStateEnum]] = {
    TaskStepStateEnum.PENDING:      {TaskStepStateEnum.WORKING},
    TaskStepStateEnum.WORKING:      {TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT,
                                     TaskStepStateEnum.COMPLETED, TaskStepStateEnum.FAILED,
                                     TaskStepStateEnum.CANCELLED},
    TaskStepStateEnum.PAUSED:       {TaskStepStateEnum.WORKING, TaskStepStateEnum.ENDED_SHIFT,
                                     TaskStepStateEnum.FAILED, TaskStepStateEnum.CANCELLED},
    TaskStepStateEnum.ENDED_SHIFT:  {TaskStepStateEnum.WORKING, TaskStepStateEnum.FAILED,
                                     TaskStepStateEnum.CANCELLED},
    TaskStepStateEnum.COMPLETED:    set(),
    TaskStepStateEnum.SKIPPED:      set(),
    TaskStepStateEnum.FAILED:       set(),
    TaskStepStateEnum.CANCELLED:    set(),
    TaskStepStateEnum.BLOCKED:      set(),
}


async def _dispatch_section_side_effects(
    step: TaskStep,
    new_state: TaskStepStateEnum,
    session,
) -> None:
    # TODO: Implement working-section-specific side effects here.
    # This extension point will be used for notifications and socket events.
    # Do not add any logic here until the side-effect interface is designed.
    pass


async def transition_step_state(ctx: ServiceContext) -> dict:
    """Atomically close current StepStateRecord and open a new one; apply task side effects; publish outbox."""
    request = parse_transition_step_state_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # 1. Fetch step (scope: task_id + workspace_id)
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.step_id,
                TaskStep.task_id == request.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        # 2. Validate transition
        if step.state in _TERMINAL_STEP_STATES:
            raise ConflictError(
                f"Step is in terminal state {step.state.value} — no further transitions allowed."
            )
        allowed = _ALLOWED_TRANSITIONS.get(step.state, set())
        if request.new_state not in allowed:
            raise ValidationError(
                f"Cannot transition step from {step.state.value} to {request.new_state.value}."
            )

        # 3. Fetch task
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == step.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        # 4. Close current open StepStateRecord
        open_record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id == step.client_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
        closing_record = open_record_result.scalar_one_or_none()
        if closing_record is None:
            raise ConflictError("No open state record found for this step.")
        closing_record.exited_at = now
        closing_state = closing_record.state  # save before flush
        closing_entered_at = closing_record.entered_at

        # 5. Open new StepStateRecord
        new_record = StepStateRecord(
            workspace_id=ctx.workspace_id,
            step_id=step.client_id,
            state=request.new_state,
            reason=request.reason,
            description=request.description,
            entered_at=now,
            exited_at=None,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(new_record)
        await ctx.session.flush()  # assign new_record.client_id

        # 6. Update step state and latest pointer (circular FK — must be in same transaction)
        step.state = request.new_state
        step.latest_state_record_id = new_record.client_id
        step.updated_at = now
        step.updated_by_id = ctx.user_id

        # 7. Task state side effects
        if request.new_state == TaskStepStateEnum.WORKING and task.state == TaskStateEnum.ASSIGNED:
            task.state = TaskStateEnum.WORKING
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        if request.new_state == TaskStepStateEnum.COMPLETED:
            # Recalculate readiness on all steps that depended on THIS step
            dependent_edges_result = await ctx.session.execute(
                select(TaskStepDependency).where(
                    TaskStepDependency.workspace_id == ctx.workspace_id,
                    TaskStepDependency.prerequisite_step_id == step.client_id,
                    TaskStepDependency.removed_at.is_(None),
                )
            )
            for edge in dependent_edges_result.scalars().all():
                dep_step_result = await ctx.session.execute(
                    select(TaskStep).where(
                        TaskStep.workspace_id == ctx.workspace_id,
                        TaskStep.client_id == edge.dependent_step_id,
                        TaskStep.is_deleted.is_(False),
                    )
                )
                dep_step = dep_step_result.scalar_one_or_none()
                if dep_step is not None:
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)

            # Check if all non-deleted steps are now terminal → task READY
            all_steps_result = await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            all_steps = all_steps_result.scalars().all()
            if all_steps and all(s.state in _TERMINAL_STEP_STATES for s in all_steps):
                if task.state not in _TERMINAL_TASK_STATES:
                    task.state = TaskStateEnum.READY
                    task.updated_at = now
                    task.updated_by_id = ctx.user_id

        # 8. Extension point for section-specific side effects (stub)
        await _dispatch_section_side_effects(step, request.new_state, ctx.session)

        # 9. Publish outbox event for analytics worker (atomic with domain write)
        payload = StepTransitionPayload(
            step_id=step.client_id,
            task_id=task.client_id,
            workspace_id=ctx.workspace_id,
            closing_record_id=closing_record.client_id,
            closing_state=closing_state.value,
            new_state=request.new_state.value,
            assigned_worker_id=step.assigned_worker_id,
            working_section_id=step.working_section_id,
            entered_at=closing_entered_at.isoformat(),
            exited_at=now.isoformat(),
            step_task_id=task.client_id,
        )
        await create_instant_task(
            session=ctx.session,
            task_type=TaskType.PROCESS_STEP_TRANSITION,
            payload=asdict(payload),
        )

    return {"step_id": step.client_id, "new_state": request.new_state.value}
```

**Critical implementation notes:**

1. **Subordinate-command event rule (from `06_commands_local.md`):** CMD-12 is the OWNER of this transaction (it calls `maybe_begin` directly, not as a subordinate). It IS allowed to fire outbox events. Do not suppress the `create_instant_task` call.

2. **`completed_dependencies` increment in COMPLETED path:** Only steps that have this step as a PREREQUISITE get `completed_dependencies += 1`. Do NOT increment the completing step's own counters.

3. **Circular FK update order:** `step.flush()` → `new_record.add()` → `flush()` → `step.latest_state_record_id = new_record.client_id`. The pointer assignment happens AFTER the new record has a `client_id`.

4. **`closing_state` capture:** Capture `closing_record.state` before `flush()`. After `exited_at` is set and flushed, `closing_record.state` is still readable — but capture it early for clarity.

5. **Task READY check includes the current step:** After `step.state = request.new_state`, the current step IS in terminal state (if `COMPLETED`). The `all_steps` query runs after `step.state` is updated in memory — SQLAlchemy identity map will return the updated in-memory step. This means the check correctly includes the current step.

6. **`closed_at` on step:** Closing steps (COMPLETED, FAILED, CANCELLED) should set `step.closed_at = now`. Add this:
   ```python
   if request.new_state in _TERMINAL_STEP_STATES:
       step.closed_at = now
   ```
   Insert this after Step 6 (the step state update block).

### Step 5 — Route in `routers/api_v1/tasks.py`

Add import:
```python
from beyo_manager.services.commands.task_steps.transition_step_state import transition_step_state
```

Body model:
```python
class _TransitionStepBody(BaseModel):
    new_state: TaskStepStateEnum
    reason: StepEventReasonEnum | None = None
    description: str | None = None
```

Route:
```
POST "/{task_id}/steps/{step_id}/transition"
    → route_transition_step_state (ADMIN, MANAGER, WORKER)
```

Handler:
```python
ctx = ServiceContext(
    incoming_data={"step_id": step_id, "task_id": task_id, **body.model_dump()},
    ...
)
```

---

## Risks and mitigations

- **Risk:** `completed_dependencies` increment on the COMPLETED path counts a step that was already counted (duplicate edge with `removed_at` not null). Query guard: `TaskStepDependency.removed_at.is_(None)` ensures only active edges are traversed.

- **Risk:** The outbox `create_instant_task` call fails and rolls back the entire step transition. This is intentional — the transition and the event are atomic. If the task factory fails, the step transition does not partially commit.
  **Mitigation:** This is the correct behavior per `16_background_jobs.md`. Document in a comment: `# Atomic with domain write — both must succeed or both roll back.`

- **Risk:** Calling `recalculate_readiness` after incrementing `completed_dependencies` — the counter must be updated BEFORE the helper is called.
  **Mitigation:** The flow is: `dep_step.completed_dependencies += 1` → `recalculate_readiness(dep_step)` — the increment precedes the call in Step 7.

- **Risk:** `BLOCKED` state in `_ALLOWED_TRANSITIONS` — `BLOCKED` has an empty transition set. But `BLOCKED` is a `TaskStepStateEnum` value — it was in the enum. Note: according to `models/tables/tasks/README.md`, `BLOCKED` in the enum means a dependency is unmet. It is not a state that a step moves into via CMD-12; `readiness_status` is the dependency-blocking indicator. If a step's `state` is somehow `BLOCKED`, no transition is allowed.
  **Mitigation:** Included in `_ALLOWED_TRANSITIONS` with empty set. This is defensive.

---

## Validation plan

Save to `backend/tests/tasks/test_step_state_machine.sh`.

```bash
# Full flow: create task → add step → transition states
# 1. PENDING → WORKING: step.state=working, task.state=working (was assigned), new StepStateRecord open
# 2. WORKING → PAUSED: step.state=paused, old record closed (exited_at set), new record open
# 3. PAUSED → WORKING: step.state=working again, new record open
# 4. WORKING → COMPLETED: step.state=completed, step.closed_at set, latest record closed
# 5. After step COMPLETED: task.state=ready (only step in task)
# 6. After step COMPLETED with dependents: dependent step readiness recalculated
# 7. Invalid transition (COMPLETED → WORKING): 422 ValidationError
# 8. Terminal step transition attempt: 409 ConflictError
# 9. ExecutionTask row created in DB after transition (outbox event exists)
# 10. WORKING → ENDED_SHIFT, then ENDED_SHIFT → WORKING (next shift resume)
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
