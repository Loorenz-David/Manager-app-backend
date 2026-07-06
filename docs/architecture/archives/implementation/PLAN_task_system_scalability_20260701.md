# PLAN_task_system_scalability_20260701

## Metadata

- Plan ID: `PLAN_task_system_scalability_20260701`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-01T00:00:00Z`
- Last updated at (UTC): `2026-07-01T12:51:50Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Add the `assortment` column to the Task model and propagate it through serializer, update service, and router; introduce a focused `task_post_handling` service and router for the five post-handling fields; extract the two implicit task-state transitions (`ASSIGNED → WORKING`, `* → READY`) into reusable, self-sufficient helper services in the task commands directory; update all callers of that duplicated logic (`transition_step_state`, `_step_transition_core`, `remove_task_step`, `add_task_steps`); add ORM relationship declarations to the Task model; run the Alembic migration; produce the frontend handoff document.
- Business/user intent: Unlock post-completion handling workflows on tasks (fulfillment routing, scheduling, assortment tracking) and decouple state-transition side effects so the "task becomes ready" logic can be expanded in one place rather than multiple files.
- Non-goals: Implementing actual post-handling business logic beyond the field update; changing the event shape or notification strategy; touching the worker runtime, analytics pipeline, or CI config.

## Scope

- In scope:
  - `Task` model: add `assortment: String(255) nullable` column + ORM `relationship()` declarations for `task_steps` and `task_items`
  - Alembic migration: single `ADD COLUMN assortment VARCHAR(255) NULL` on `tasks`
  - `serialize_task` serializer: add `assortment` field
  - `UpdateTaskRequest` + `_UpdateTaskBody` + `_DIRECT_FIELDS` in `update_task`: add `assortment`
  - New package `beyo_manager/services/task_post_handling/` with command `update_task_post_handling.py` covering fields: `fulfillment_method`, `scheduled_start_at`, `scheduled_end_at`, `task_type`, `assortment`
  - New router handler `PATCH /{task_id}/post-handling` wired in `routers/api_v1/tasks.py`
  - New helper `services/commands/tasks/_task_state_transitions.py` exporting two functions: `maybe_advance_task_to_working` and `maybe_evaluate_task_ready` — both receive an already-loaded `Task` instance from the caller; `maybe_evaluate_task_ready` issues one `select(TaskStep)` internally to check all step states; neither opens its own transaction (caller owns `maybe_begin`)
  - Refactor `transition_step_state.py` (lines 331–349), `_step_transition_core.py` (lines 203–222), `remove_task_step.py` (lines 205–209), and `add_task_steps.py` (line 139) to delegate to those helpers
  - Frontend handoff document at `docs/handoff/to_frontend/`

- Out of scope:
  - Post-handling business logic (webhook triggers, fulfillment routing, downstream notifications)
  - Changing any existing step-transition event shape or notification text
  - Filtering or querying by `assortment`

- Assumptions:
  - There is a single Alembic head; if not, a merge migration must be generated first
  - `assortment` is free-text; no enum is required
  - The post-handling route requires `ADMIN | MANAGER` roles (same as `update_task_schedule`)
  - `task_type` can be updated post-creation via the post-handling route; no guard beyond the terminal-state check is needed for this plan
  - ORM relationships are `lazy="noload"` (never eagerly loaded) — callers continue to use explicit `select()` queries

## Clarifications required

- [x] Should `task_type` changes via post-handling fire a history record? — **Yes**: call `_create_history_record_in_session` the same way `update_task` does. Also fire `build_workspace_event(task, "task:updated")`.
- [x] ORM `relationship()` lazy mode? — **`lazy="noload"`**: pure scaffolding, no on-demand or pre-loading. Existing explicit `select()` queries are unaffected. Future queries can opt in with `selectinload()` explicitly.

## Acceptance criteria

1. `PATCH /tasks/{task_id}` accepts `assortment` and returns it in `GET /tasks/{task_id}`
2. `PATCH /tasks/{task_id}/post-handling` accepts `{ fulfillment_method, scheduled_start_at, scheduled_end_at, task_type, assortment }` (all optional), rejects terminal tasks, and emits a `task:updated` realtime event
3. `transition_step_state` and `_step_transition_core` contain no inline task-state mutation for WORKING/READY — both delegate to helpers
4. `remove_task_step` and `add_task_steps` delegate their task-state mutations to the same helpers
5. Migration applies cleanly against the current head with no conflicts
6. Handoff document describes the new route's request/response shape

## Contracts and skills

### Contracts loaded

- `task_system/architecture/01_architecture.md`: overall system layers and module boundaries
- `task_system/architecture/04_context.md`: `ServiceContext` shape — `ctx.session`, `ctx.workspace_id`, `ctx.user_id`, `ctx.incoming_data`
- `task_system/architecture/05_errors.md`: `NotFound`, `ValidationError`, `ConflictError` usage
- `task_system/architecture/06_commands.md` + `06_commands_local.md`: command structure, `maybe_begin` rules, `session.flush()` as only explicit session call, subordinate-command event rule
- `task_system/architecture/09_routers.md`: handler skeleton, `run_service`, `build_ok` / `build_err`, Pydantic body models
- `task_system/architecture/03_models.md`: SQLAlchemy mapped column conventions, `IdentityMixin`, `Base`
- `task_system/architecture/08_domain.md`: domain enums, serializers, request parsers location
- `task_system/architecture/11_infra_events.md`: `event_bus.dispatch`, `build_workspace_event`
- `task_system/architecture/21_naming_conventions.md`: file naming, function naming
- `task_system/architecture/30_migrations.md`: Alembic async migration conventions, single-head rule

### Local extensions loaded

- `task_system/architecture/06_commands_local.md`: `maybe_begin` subordinate mode (no commit inside block), `session.flush()` only when a DB-generated value is needed immediately, subordinate-command event rule (callers own dispatch)

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add` / `flush` / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- `models/tables/tasks/task.py` — exact column names and types (already read)
- `domain/tasks/serializers.py` — existing `serialize_task` fields (already read)
- `services/commands/tasks/requests/__init__.py` — existing request models (already read)
- `services/commands/task_steps/transition_step_state.py` lines 331–349 — code to extract (already read)
- `services/commands/task_steps/_step_transition_core.py` lines 203–222 — mirrored code to extract (already read)
- `services/commands/task_steps/remove_task_step.py` lines 200–215 — to confirm extraction target
- `services/commands/task_steps/add_task_steps.py` lines 135–142 — to confirm extraction target
- `services/commands/utils/transaction.py` — `maybe_begin` semantics (already read)

### Skill selection

- Primary skill: `task_system/architecture/06_commands.md` (command authoring)
- Router trigger terms: `PATCH`, `/{task_id}/post-handling`
- Excluded alternatives: worker runtime skills — not applicable here

## Implementation plan

### Step 1 — Check and merge Alembic head (pre-condition)

```bash
cd app && alembic heads
```

If more than one head is listed, generate a merge migration before proceeding:

```bash
alembic merge heads -m "merge_heads_before_task_assortment"
```

### Step 2 — Add `assortment` column and ORM relationships to Task model

File: `app/beyo_manager/models/tables/tasks/task.py`

Add after `taken_from_average`:
```python
assortment: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

Add ORM relationship declarations (import `relationship` from `sqlalchemy.orm`). Use `lazy="noload"` so no existing query is affected:
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship

# inside Task class, after columns:
task_steps: Mapped[list["TaskStep"]] = relationship(
    "TaskStep", foreign_keys="TaskStep.task_id",
    primaryjoin="Task.client_id == TaskStep.task_id",
    lazy="noload",
)
task_items: Mapped[list["TaskItem"]] = relationship(
    "TaskItem", foreign_keys="TaskItem.task_id",
    primaryjoin="Task.client_id == TaskItem.task_id",
    lazy="noload",
)
```

### Step 3 — Generate and write Alembic migration

```bash
cd app && alembic revision --autogenerate -m "add_task_assortment_column"
```

Verify the generated file contains only:
```python
op.add_column("tasks", sa.Column("assortment", sa.String(255), nullable=True))
```

No `downgrade` data risk. `downgrade` removes the column.

Run:
```bash
alembic upgrade head
```

Confirm single head after:
```bash
alembic heads
```

### Step 4 — Add `assortment` to `serialize_task`

File: `app/beyo_manager/domain/tasks/serializers.py`

In `serialize_task`, after `"fulfillment_method"`:
```python
"assortment": task.assortment,
```

### Step 5 — Propagate `assortment` through update_task

**`app/beyo_manager/services/commands/tasks/requests/__init__.py`**

In `UpdateTaskRequest`, add:
```python
assortment: str | None = None
```

In `_DIRECT_FIELDS` inside `update_task.py`, add `"assortment"`.

**`app/beyo_manager/routers/api_v1/tasks.py`**

In `_UpdateTaskBody`, add:
```python
assortment: str | None = None
```

### Step 6 — Extract task state transition helpers

Create new file: `app/beyo_manager/services/commands/tasks/_task_state_transitions.py`

This module exports two helpers. Both accept a loaded `Task` ORM object and the already-open session (the caller owns `maybe_begin`). They mutate the task in place and return a `bool` indicating whether the state changed (so the caller can decide whether to fire a notification).

```python
"""Reusable task state side-effect helpers.

These functions mutate the Task ORM object in place. They are designed to run
inside an already-open transaction (callers use maybe_begin and own the commit).
Do NOT call session.commit() here.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep


def maybe_advance_task_to_working(
    task: Task,
    *,
    now: datetime,
    updated_by_id: str,
) -> bool:
    """Transition task ASSIGNED → WORKING when the first step starts working.

    Mutates task in place. Returns True if state changed.
    Caller must be inside a maybe_begin block.
    """
    if task.state == TaskStateEnum.ASSIGNED:
        task.state = TaskStateEnum.WORKING
        task.updated_at = now
        task.updated_by_id = updated_by_id
        return True
    return False


async def maybe_evaluate_task_ready(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    updated_by_id: str,
) -> bool:
    """Transition task to READY when all its steps have reached a terminal state.

    Loads all non-deleted steps for the task, checks universally terminal,
    then mutates task.state in place. Returns True if state changed.
    Caller must be inside a maybe_begin block.
    """
    if task.state in TERMINAL_TASK_STATES:
        return False
    all_steps_result = await session.execute(
        select(TaskStep).where(
            TaskStep.workspace_id == workspace_id,
            TaskStep.task_id == task.client_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    all_steps = all_steps_result.scalars().all()
    if all_steps and all(s.state in TERMINAL_STEP_STATES for s in all_steps):
        task.state = TaskStateEnum.READY
        task.updated_at = now
        task.updated_by_id = updated_by_id
        return True
    return False
```

### Step 7 — Refactor `transition_step_state.py`

File: `app/beyo_manager/services/commands/task_steps/transition_step_state.py`

Import the two helpers:
```python
from beyo_manager.services.commands.tasks._task_state_transitions import (
    maybe_advance_task_to_working,
    maybe_evaluate_task_ready,
)
```

Replace lines 331–349 (the inline task state block) with:
```python
# 7. Task state side effects
if request.new_state == TaskStepStateEnum.WORKING:
    maybe_advance_task_to_working(task, now=now, updated_by_id=ctx.user_id)

if request.new_state in TERMINAL_STEP_STATES:
    await maybe_evaluate_task_ready(
        ctx.session, task,
        workspace_id=ctx.workspace_id,
        now=now,
        updated_by_id=ctx.user_id,
    )
```

Remove the `select(TaskStep)` block that was inline for the READY check — it is now inside `maybe_evaluate_task_ready`.

### Step 8 — Refactor `_step_transition_core.py`

File: `app/beyo_manager/services/commands/task_steps/_step_transition_core.py`

Same imports and same replacement for lines 203–222. The helpers are pure session mutations — no transaction boundary change is needed since `_apply_step_transition` is already transaction-free.

### Step 9 — Refactor `remove_task_step.py` and `add_task_steps.py`

Read lines 200–215 of `remove_task_step.py` and lines 135–142 of `add_task_steps.py` to confirm the exact inline mutations, then replace with calls to:
- `maybe_advance_task_to_working` (add_task_steps ASSIGNED→WORKING, if that logic exists there)
- `maybe_evaluate_task_ready` (remove_task_step's READY branch)

For the PENDING branch in `remove_task_step` (when steps remain), this cannot use the helpers — it stays inline as it is a distinct state (`PENDING`) not covered by the helpers.

### Step 10 — Create `task_post_handling` service

Create package: `app/beyo_manager/services/task_post_handling/__init__.py` (empty)

Create: `app/beyo_manager/services/task_post_handling/update_task_post_handling.py`

```python
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskFulfillmentMethodEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


_TERMINAL_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})

_POST_HANDLING_FIELDS = {
    "fulfillment_method",
    "scheduled_start_at",
    "scheduled_end_at",
    "task_type",
    "assortment",
}


class UpdateTaskPostHandlingRequest(BaseModel):
    client_id: str
    fulfillment_method: TaskFulfillmentMethodEnum | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    task_type: TaskTypeEnum | None = None
    assortment: str | None = None


def _parse(data: dict) -> UpdateTaskPostHandlingRequest:
    try:
        return UpdateTaskPostHandlingRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc


async def update_task_post_handling(ctx: ServiceContext) -> dict:
    request = _parse(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.client_id,
                Task.is_deleted.is_(False),
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")
        if task.state in _TERMINAL_STATES:
            raise ValidationError("Terminal tasks cannot be updated.")

        for field_name in _POST_HANDLING_FIELDS:
            if field_name in request.model_fields_set:
                setattr(task, field_name, getattr(request, field_name))

        if (
            task.scheduled_start_at is not None
            and task.scheduled_end_at is not None
            and task.scheduled_end_at < task.scheduled_start_at
        ):
            raise ValidationError("scheduled_end_at must be >= scheduled_start_at.")

        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        updated_fields = [f for f in _POST_HANDLING_FIELDS if f in request.model_fields_set]
        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(username, updated_fields, f"task #{task.task_scalar_id}"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": task.client_id}
```

### Step 11 — Wire new route in `routers/api_v1/tasks.py`

Add import:
```python
from beyo_manager.services.task_post_handling.update_task_post_handling import update_task_post_handling
```

Add Pydantic body model:
```python
class _UpdateTaskPostHandlingBody(BaseModel):
    fulfillment_method: TaskFulfillmentMethodEnum | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    task_type: TaskTypeEnum | None = None
    assortment: str | None = None
```

Add handler (place after `route_update_task_schedule`):
```python
@router.patch("/{task_id}/post-handling")
async def route_update_task_post_handling(
    task_id: str,
    body: _UpdateTaskPostHandlingBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_post_handling, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

### Step 12 — Write frontend handoff document

Create: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_post_handling_20260701.md`

Use `TEMPLATE_HANDOFF_TO_FRONTEND.md` as base. Document:
- The new `PATCH /{task_id}/post-handling` endpoint
- The updated `assortment` field now returned in the task response
- Event: `task:updated` fires on success (same as `update_task`)
- Note that this file will be expanded with additional post-handling routes

## Risks and mitigations

- Risk: ORM `relationship()` declarations cause unexpected eager loads or cartesian joins in existing queries.
  Mitigation: Use `lazy="noload"` on all new relationships. No existing code uses `task.task_steps` or `task.task_items` as ORM attributes — all existing code uses explicit `select()`. Verify with a grep before adding: `grep -rn "task\.task_steps\|task\.task_items"`.

- Risk: Extracting the READY check changes the query count inside `transition_step_state` (was one `select(TaskStep)` shared with the `all_steps` variable; after extraction it becomes a separate query).
  Mitigation: `maybe_evaluate_task_ready` issues its own `select(TaskStep)`. The previous code already had this query inline — the behavior is identical, just moved. The batch path already had a similar pattern.

- Risk: `_step_transition_core.py` is transaction-free by design. Adding `await maybe_evaluate_task_ready(session, ...)` inside it is safe because the helper only issues a `select` and ORM mutations — no `session.commit()` or new `maybe_begin`.
  Mitigation: Confirmed: `maybe_evaluate_task_ready` does not call `maybe_begin`. It is a pure mutation helper, not a standalone command.

- Risk: `add_task_steps.py` ASSIGNED→WORKING transition may not exist in that file (the grep showed `PENDING → ASSIGNED` at line 139, not WORKING). The WORKING transition lives only in `transition_step_state` and `_step_transition_core`.
  Mitigation: Read `add_task_steps.py` lines 135–145 before refactoring to confirm there is no WORKING mutation there. Only refactor what actually exists.

- Risk: Migration conflicts with another recent migration (multiple heads).
  Mitigation: Step 1 explicitly checks `alembic heads` and merges before proceeding.

## Validation plan

- `alembic heads` after migration: expect exactly one head
- `alembic upgrade head` on a clean DB: expect success with no errors
- `PATCH /tasks/{task_id}` with `{"assortment": "testvalue"}`: expect `200`, `GET /tasks/{task_id}` returns `"assortment": "testvalue"`
- `PATCH /tasks/{task_id}/post-handling` with `{"task_type": "...", "assortment": "abc"}`: expect `200`, `{"client_id": "..."}`
- `PATCH /tasks/{task_id}/post-handling` with `{"scheduled_end_at": "2026-01-01", "scheduled_start_at": "2026-06-01"}`: expect `422` with `"scheduled_end_at must be >= scheduled_start_at"`
- `PATCH /tasks/{task_id}/post-handling` on a RESOLVED task: expect `422`
- Step transition to WORKING on a task in ASSIGNED state: confirm `task.state` becomes WORKING (same as before)
- Step transition to COMPLETED (last step): confirm `task.state` becomes READY (same as before)
- `grep -rn "task\.state = TaskStateEnum.WORKING" app/beyo_manager/services/commands/task_steps/`: expect 0 matches (all delegated)
- `grep -rn "task\.state = TaskStateEnum.READY" app/beyo_manager/services/commands/task_steps/`: expect 0 matches (all delegated)

## Review log

_(empty — awaiting first review)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
