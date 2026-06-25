# PLAN_task_step_ready_by_at_20260625

## Metadata

- Plan ID: `PLAN_task_step_ready_by_at_20260625`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T11:42:46Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/task_step_correction.txt`

## Goal and intent

- Goal: Add `ready_by_at` (`DateTime(timezone=True), nullable=True`) to the `TaskStep` model; propagate it through creation flows (create task + add steps), expose a new bulk-update route, and include it in all relevant serializers.
- Business/user intent: Task steps need their own deadline so that individual sections within a task can have different target completion dates, independent of the parent task deadline.
- Non-goals: Changing business logic around task state transitions; propagating `ready_by_at` to step-state records or events payloads beyond what is listed in scope.

## Scope

- In scope:
  - `TaskStep` model: add `ready_by_at: Mapped[datetime | None]` column identical in definition to `Task.ready_by_at`.
  - Alembic migration: `ADD COLUMN ready_by_at TIMESTAMPTZ NULL` on `task_steps`.
  - `TaskStepInput` (tasks requests): add `ready_by_at: datetime | None = None`.
  - `StepInputItem` (task_steps requests): add `ready_by_at: datetime | None = None`.
  - `_TaskStepInputBody` (router Pydantic model in `tasks.py`): add `ready_by_at: datetime | None = None`.
  - `create_task.py`: pass `ready_by_at` to `TaskStep(...)` — use `step_input.ready_by_at` if provided, else fall back to `request.ready_by_at` (the task-level value).
  - `add_task_steps.py`: same fallback logic — use `step_input.ready_by_at` if provided, else fall back to `task.ready_by_at` (loaded from DB).
  - New command service: `services/commands/task_steps/update_task_step_ready_by_at.py` — accepts `task_id` + list of `{step_id, ready_by_at}` items, validates ownership, bulk-updates, fires `task:step-updated` batch event.
  - New router: `PATCH /{task_id}/steps/ready-by-at` in `tasks.py` — roles `[ADMIN, MANAGER]`.
  - Serializer `serialize_task_step_compact`: add `"ready_by_at": step.ready_by_at.isoformat() if step.ready_by_at else None`.
  - Serializer `serialize_step`: same addition.
  - Frontend handoff document.

- Out of scope:
  - Changing `StepStateRecord` or any event payload schema beyond dispatching the new update event.
  - Filtering/querying tasks by step `ready_by_at`.
  - Updating `ready_by_at` during state transitions.

- Assumptions:
  - PostgreSQL; Alembic is used for schema changes.
  - The fallback rule (step-level overrides task-level) applies only at write time (creation / explicit update). No retroactive backfill of existing steps from the task's deadline is required.
  - The new PATCH route updates `ready_by_at` only (not other step fields).
  - Roles for the new route: `ADMIN`, `MANAGER` (same as `route_add_task_step`).

## Clarifications required

_(none — all behaviours are fully specified in the intention doc)_

## Acceptance criteria

1. `GET /tasks/{task_id}` response includes `ready_by_at` on every step object in its steps list.
2. `GET /tasks/{task_id}/steps` response includes `ready_by_at` on every step object.
3. `PUT /tasks` with `steps[].ready_by_at` persists the field per step; steps without the field inherit the task-level `ready_by_at` (or `null` if that is also absent).
4. `POST /tasks/{task_id}/steps` with `ready_by_at` per item behaves identically to point 3 (fallback to `task.ready_by_at` from DB).
5. `PATCH /tasks/{task_id}/steps/ready-by-at` updates `ready_by_at` on the listed steps, returns `{"step_ids": [...]}`, and rejects unknown/wrong-task step IDs with a `404`.
6. Working-section routes (`get_user_last_active_step_record_route`, `list_working_section_steps_route`) include `ready_by_at` in step serialization.
7. Migration is reversible (downgrade drops the column without data loss risk since it is nullable).

## Contracts and skills

### Contracts loaded

- `../architecture/01_architecture.md`: project structure baseline
- `../architecture/04_context.md`: `ServiceContext` usage
- `../architecture/05_errors.md`: `NotFound`, `ConflictError`, `ValidationError` raise patterns
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: `maybe_begin`, session.add / flush / event dispatch shape
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: offset pagination baseline (not directly used in new command but consulted for consistency)
- `../architecture/09_routers.md`: handler wiring, `build_ok` / `build_err`, `run_service`, `require_roles`
- `../architecture/21_naming_conventions.md`: file and function naming
- `../architecture/30_migrations.md`: Alembic migration conventions
- `../architecture/03_models.md`: SQLAlchemy model patterns (`Mapped`, `mapped_column`, `DateTime(timezone=True)`)
- `../architecture/46_serialization.md`: serializer output shape rules
- `../architecture/42_event.md`: event dispatch pattern (`BatchWorkspaceEvent`, `build_workspace_event`)

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin` transaction utility; subordinate-command event rule.
- `../architecture/07_queries_local.md`: offset pagination override (awareness only; not modified).

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

Permitted relational reads already done:
- `models/tables/tasks/task_step.py` — exact existing fields and column types.
- `models/tables/tasks/task.py` — exact `ready_by_at` column definition to replicate.
- `routers/api_v1/tasks.py` — existing route shapes, `_TaskStepInputBody`, role guards.
- `services/commands/tasks/create_task.py` — how `TaskStep` is constructed today (to know where to add `ready_by_at` assignment).
- `services/commands/task_steps/add_task_steps.py` — how steps are constructed and where task is loaded (for fallback).
- `services/commands/tasks/requests/__init__.py` — `TaskStepInput` model to extend.
- `services/commands/task_steps/requests/__init__.py` — `StepInputItem` model to extend.
- `domain/task_steps/serializers.py` — current `serialize_task_step_compact` output shape.
- `domain/tasks/serializers.py` — current `serialize_step` output shape.

Prohibited (not needed — contracts cover pattern):
- Reading another command for `maybe_begin` / session shape — `06_commands.md` covers it.
- Reading another router for handler skeleton — `09_routers.md` covers it.

### Skill selection

- Primary skill: `task_system/backend_contract_goal_mapping_guide.md`
- Goal bundle: `CRUD + realtime` (model change + migration + command + router + serializer + event)
- Router trigger terms: none beyond CRUD; no search, no worker runtime
- Excluded alternatives: `Worker-driven backend` — no background jobs involved; `Replayable async runtime` — not applicable.

## Implementation plan

### Step 1 — Model: add `ready_by_at` to `TaskStep`

**File:** `app/beyo_manager/models/tables/tasks/task_step.py`

Add after `closed_at`:
```python
ready_by_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Step 2 — Migration: ADD COLUMN

Create a new Alembic migration in `app/migrations/versions/` (use `alembic revision --autogenerate` or write manually):

```python
"""add_ready_by_at_to_task_steps

Revision ID: <new_hex_id>
Revises: <latest_revision>
Create Date: 2026-06-25 ...
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.add_column(
        "task_steps",
        sa.Column("ready_by_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("task_steps", "ready_by_at")
```

### Step 3 — Request models: extend step input with `ready_by_at`

**File A:** `app/beyo_manager/services/commands/tasks/requests/__init__.py`

In `TaskStepInput`:
```python
ready_by_at: datetime | None = None
```

**File B:** `app/beyo_manager/services/commands/task_steps/requests/__init__.py`

In `StepInputItem`:
```python
ready_by_at: datetime | None = None
```

Also add a new request model for the update command (can live in the same file):
```python
class UpdateStepReadyByAtItem(BaseModel):
    step_id: str
    ready_by_at: datetime | None = None

class UpdateStepReadyByAtRequest(BaseModel):
    task_id: str
    items: list[UpdateStepReadyByAtItem]

    @field_validator("items")
    @classmethod
    def validate_items(cls, value):
        if not value:
            raise ValueError("items must not be empty.")
        if len({i.step_id for i in value}) != len(value):
            raise ValueError("Duplicate step_id values are not allowed.")
        return value

def parse_update_step_ready_by_at_request(data: dict) -> UpdateStepReadyByAtRequest:
    try:
        return UpdateStepReadyByAtRequest.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e
```

### Step 4 — Router Pydantic model: extend `_TaskStepInputBody`

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

In `_TaskStepInputBody`:
```python
ready_by_at: datetime | None = None
```

### Step 5 — `create_task.py`: pass `ready_by_at` with fallback

**File:** `app/beyo_manager/services/commands/tasks/create_task.py`

In the `TaskStep(...)` constructor call (currently at line ~229), add:
```python
ready_by_at=step_input.ready_by_at if step_input.ready_by_at is not None else request.ready_by_at,
```

### Step 6 — `add_task_steps.py`: pass `ready_by_at` with fallback

**File:** `app/beyo_manager/services/commands/task_steps/add_task_steps.py`

`task` is already loaded from the DB before the step loop. In the `TaskStep(...)` constructor call (currently at line ~106), add:
```python
ready_by_at=step_input.ready_by_at if step_input.ready_by_at is not None else task.ready_by_at,
```

### Step 7 — New command service: `update_task_step_ready_by_at.py`

**File:** `app/beyo_manager/services/commands/task_steps/update_task_step_ready_by_at.py`

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps.requests import parse_update_step_ready_by_at_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent


async def update_task_step_ready_by_at(ctx: ServiceContext) -> dict:
    request = parse_update_step_ready_by_at_request(ctx.incoming_data)
    step_ids = [item.step_id for item in request.items]

    async with maybe_begin(ctx.session):
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        steps_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == request.task_id,
                TaskStep.client_id.in_(step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
        steps_by_id = {step.client_id: step for step in steps_result.scalars().all()}

        missing = sorted(set(step_ids) - set(steps_by_id))
        if missing:
            raise NotFound(f"Task step {missing[0]!r} not found.")

        now = datetime.now(timezone.utc)
        for item in request.items:
            step = steps_by_id[item.step_id]
            step.ready_by_at = item.ready_by_at
            step.updated_at = now
            step.updated_by_id = ctx.user_id

    await event_bus.dispatch([
        BatchWorkspaceEvent(
            event_name="task:step-updated",
            workspace_id=ctx.workspace_id,
            items=[{"client_id": sid} for sid in step_ids],
        )
    ])
    return {"step_ids": step_ids}
```

### Step 8 — New router: `PATCH /{task_id}/steps/ready-by-at`

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

Add import:
```python
from beyo_manager.services.commands.task_steps.update_task_step_ready_by_at import update_task_step_ready_by_at
```

Add body model:
```python
class _UpdateStepReadyByAtItem(BaseModel):
    step_id: str
    ready_by_at: datetime | None = None

class _UpdateStepsReadyByAtBody(BaseModel):
    items: list[_UpdateStepReadyByAtItem]
```

Add route after `route_add_task_step` (or alongside other bulk step routes):
```python
@router.patch("/{task_id}/steps/ready-by-at")
async def route_update_task_steps_ready_by_at(
    task_id: str,
    body: _UpdateStepsReadyByAtBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "task_id": task_id,
            "items": [item.model_dump() for item in body.items],
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_step_ready_by_at, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Route ordering note:** FastAPI resolves routes in registration order. `PATCH /{task_id}/steps/ready-by-at` must be registered before any `PATCH /{task_id}/steps/{step_id}` route if such a route ever exists, to avoid `ready-by-at` being captured as a `step_id` path param. No such route exists today, so ordering is safe.

### Step 9 — Serializers

**File A:** `app/beyo_manager/domain/task_steps/serializers.py`

In `serialize_task_step_compact`, add:
```python
"ready_by_at": step.ready_by_at.isoformat() if step.ready_by_at else None,
```

**File B:** `app/beyo_manager/domain/tasks/serializers.py`

In `serialize_step`, add:
```python
"ready_by_at": step.ready_by_at.isoformat() if step.ready_by_at else None,
```

### Step 10 — Frontend handoff document

Create `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625.md` using the template.

## Risks and mitigations

- Risk: Route path `/{task_id}/steps/ready-by-at` conflicts with a future `/{task_id}/steps/{step_id}` PATCH route.
  Mitigation: No such route exists today. Document the ordering requirement in the handoff. If a per-step PATCH is added later, register the literal path first.

- Risk: `update_task_step_ready_by_at` runs N in-loop attribute sets without a batch SQL UPDATE, which is fine for typical step counts per task (< 50) but not for very large batches.
  Mitigation: Acceptable for current use case. If batch sizes become large, replace with a single `UPDATE ... SET ready_by_at = CASE WHEN ... END` statement.

- Risk: Existing `add_task_steps.py` loads the task but currently uses only `task.state`. The fallback reads `task.ready_by_at` which requires no additional query — it is already on the loaded object.
  Mitigation: None needed; confirmed by reading the service.

## Validation plan

- `alembic upgrade head`: migration applies without error; `\d task_steps` shows `ready_by_at timestamptz NULL`.
- `alembic downgrade -1`: column dropped cleanly.
- `PUT /tasks` with `steps: [{"working_section_id": "...", "ready_by_at": "2026-07-01T00:00:00Z"}]`: step returned by `GET /tasks/{id}/steps` has `ready_by_at: "2026-07-01T00:00:00Z"`.
- `PUT /tasks` with step having no `ready_by_at` but task-level `ready_by_at` set: step inherits task value.
- `PATCH /tasks/{task_id}/steps/ready-by-at` with valid items: returns `{"step_ids": [...]}`, DB updated.
- `PATCH /tasks/{task_id}/steps/ready-by-at` with a step that belongs to a different task: returns 404.
- `GET /tasks/{task_id}` step objects include `ready_by_at` field (null or ISO string).
- Working-section step list includes `ready_by_at` field on each step.

## Review log

- `2026-06-25T11:42:46Z` — Implemented in backend code, summary written at `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_step_ready_by_at_20260625.md`, and frontend handoff written at `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `David`
