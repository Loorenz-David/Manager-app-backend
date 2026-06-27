# PLAN_task_date_fields_20260625

## Metadata

- Plan ID: `PLAN_task_date_fields_20260625`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T21:03:01Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Create two focused command services and two dedicated `PATCH` routes on the task router — one for `ready_by_at` and one for the scheduling window (`scheduled_start_at` + `scheduled_end_at`) — that write only their respective fields and fire a `task:updated` event.
- Business/user intent: Give the frontend a narrow, intentful API for date changes instead of overloading the general `PATCH /{task_id}`. Each endpoint communicates clear intent and will be easier to extend independently in the future.
- Non-goals: Does not change any other Task field. Does not alter task state. Does not replace or modify the existing `update_task` service or `PATCH /{task_id}` route. No new DB columns or migrations required — all three fields already exist on the `tasks` table.

## Scope

- In scope:
  - Two new request models + parse functions in `services/commands/tasks/requests/__init__.py`
  - Two new command services:
    - `services/commands/tasks/update_task_ready_by_at.py`
    - `services/commands/tasks/update_task_schedule.py`
  - Two new routes in `routers/api_v1/tasks.py`:
    - `PATCH /{task_id}/ready-by-at`
    - `PATCH /{task_id}/schedule`
- Out of scope:
  - Migrations (no schema change; all columns already exist)
  - Filtering or sorting by these fields
  - Any change to the existing `create_task` or `update_task` services

## Assumptions

- Both endpoints block writes on terminal task states (`RESOLVED`, `FAILED`, `CANCELLED`) — same guard as `update_task`.
- Allowed roles: `ADMIN`, `MANAGER` (same as the existing `PATCH /{task_id}`).
- Setting any date field to `null` is valid (clearing the date).
- `update_task_schedule` accepts both `scheduled_start_at` and `scheduled_end_at` in the same request because the DB has a check constraint requiring `end >= start`. Splitting them into separate endpoints would make it impossible to atomically swap both values while respecting the constraint.
- The cross-field validation (`scheduled_end_at >= scheduled_start_at`) applies only when both fields are non-null after the write — identical to the logic already in `update_task`.

## Clarifications required

_None — all decisions are resolved by the assumptions above and the existing `update_task` pattern._

## Acceptance criteria

1. `PATCH /{task_id}/ready-by-at` with a valid datetime returns `200` and `{"data": {"client_id": "tsk_..."}}`.
2. `PATCH /{task_id}/ready-by-at` with `ready_by_at: null` clears the field and returns `200`.
3. `PATCH /{task_id}/schedule` with valid start/end datetimes returns `200` and `{"data": {"client_id": "tsk_..."}}`.
4. `PATCH /{task_id}/schedule` with `scheduled_end_at < scheduled_start_at` (both non-null) returns `422`.
5. `PATCH /{task_id}/schedule` with both fields null clears the schedule and returns `200`.
6. Both endpoints return `404` when the task does not exist in the workspace.
7. Both endpoints return `422` when the task is in a terminal state (`RESOLVED`, `FAILED`, `CANCELLED`).
8. A `WORKER` JWT receives `403` on both endpoints.
9. Each call produces one history record and one `task:updated` workspace event.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/06_commands.md`: command shape, `maybe_begin`, error-raising, history record pattern
- `backend/docs/architecture/09_routers.md`: handler wiring, `ServiceContext`, `run_service`, `build_ok`/`build_err`
- `backend/docs/architecture/46_serialization.md`: request model + parse-function conventions

### Local extensions loaded

_None_

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead
- **What exists** → reading is legitimate

Prohibited (pattern reads):
- Reading `update_task.py` to understand the command shape → `06_commands.md`
- Reading another route handler to understand wiring → `09_routers.md`

Permitted (relational reads):
- Reading `models/tables/tasks/task.py` to verify existing column names and types ✓ (already done — `ready_by_at`, `scheduled_start_at`, `scheduled_end_at` all exist as `DateTime(timezone=True) nullable`)
- Reading `services/commands/tasks/requests/__init__.py` to find the append point ✓ (already done)
- Reading `routers/api_v1/tasks.py` to verify route placement ✓ (already done)

### Skill selection

- Primary skill: command-service creation + router wiring
- Router trigger terms: `ready_by_at`, `scheduled_start_at`, `scheduled_end_at`, `ready-by-at`, `schedule`
- Excluded alternatives: extending `update_task` — mixes responsibilities and blocks future divergence between the two endpoints.

## Implementation plan

### Step 1 — Add request models and parse functions to `requests/__init__.py`

File: `app/beyo_manager/services/commands/tasks/requests/__init__.py`

Append after `UpdateTaskRequest` and its parse function:

```python
class UpdateTaskReadyByAtRequest(BaseModel):
    client_id: str
    ready_by_at: datetime | None = None


class UpdateTaskScheduleRequest(BaseModel):
    client_id: str
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
```

Append the corresponding parse functions (follow the existing `_raise_validation_error` helper already defined in the file):

```python
def parse_update_task_ready_by_at_request(data: dict) -> UpdateTaskReadyByAtRequest:
    try:
        return UpdateTaskReadyByAtRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_task_schedule_request(data: dict) -> UpdateTaskScheduleRequest:
    try:
        return UpdateTaskScheduleRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
```

---

### Step 2 — Create `update_task_ready_by_at.py`

File: `app/beyo_manager/services/commands/tasks/update_task_ready_by_at.py`

```python
"""CMD: Update Task.ready_by_at and emit task:updated event."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.tasks.requests import parse_update_task_ready_by_at_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


_TERMINAL_STATES = frozenset({TaskStateEnum.RESOLVED, TaskStateEnum.FAILED, TaskStateEnum.CANCELLED})


async def update_task_ready_by_at(ctx: ServiceContext) -> dict:
    request = parse_update_task_ready_by_at_request(ctx.incoming_data)

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

        task.ready_by_at = request.ready_by_at
        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(username, ["ready_by_at"], f"task #{task.task_scalar_id}"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([build_workspace_event(task, "task:updated")])
    return {"client_id": task.client_id}
```

---

### Step 3 — Create `update_task_schedule.py`

File: `app/beyo_manager/services/commands/tasks/update_task_schedule.py`

Both `scheduled_start_at` and `scheduled_end_at` are written in the same transaction so the DB check constraint (`end >= start`) is never violated mid-flight. The cross-field validation mirrors the one already in `update_task`.

```python
"""CMD: Update Task.scheduled_start_at and scheduled_end_at and emit task:updated event."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.tasks.requests import parse_update_task_schedule_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


_TERMINAL_STATES = frozenset({TaskStateEnum.RESOLVED, TaskStateEnum.FAILED, TaskStateEnum.CANCELLED})


async def update_task_schedule(ctx: ServiceContext) -> dict:
    request = parse_update_task_schedule_request(ctx.incoming_data)

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

        task.scheduled_start_at = request.scheduled_start_at
        task.scheduled_end_at = request.scheduled_end_at

        if (
            task.scheduled_start_at is not None
            and task.scheduled_end_at is not None
            and task.scheduled_end_at < task.scheduled_start_at
        ):
            raise ValidationError("scheduled_end_at must be >= scheduled_start_at.")

        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(
                username,
                ["scheduled_start_at", "scheduled_end_at"],
                f"task #{task.task_scalar_id}",
            ),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([build_workspace_event(task, "task:updated")])
    return {"client_id": task.client_id}
```

---

### Step 4 — Wire both routes in `routers/api_v1/tasks.py`

**4a. Add imports** alongside the existing task command imports:

```python
from beyo_manager.services.commands.tasks.update_task_ready_by_at import update_task_ready_by_at
from beyo_manager.services.commands.tasks.update_task_schedule import update_task_schedule
```

**4b. Add router-local body models** (after `_UpdateTaskBody`, before the first `@router` decorator):

```python
class _UpdateReadyByAtBody(BaseModel):
    ready_by_at: datetime | None = None


class _UpdateScheduleBody(BaseModel):
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
```

**4c. Add route handlers** — place both immediately after `route_update_task` (the existing `PATCH /{task_id}`). These paths have a second path segment so they never conflict with `PATCH /{task_id}`:

```python
@router.patch("/{task_id}/ready-by-at")
async def route_update_task_ready_by_at(
    task_id: str,
    body: _UpdateReadyByAtBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_ready_by_at, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/schedule")
async def route_update_task_schedule(
    task_id: str,
    body: _UpdateScheduleBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_schedule, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 5 — Write the frontend handoff document

After all files are created and validated, write:
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_date_fields_20260625.md`

Use the template at `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`.

## Risks and mitigations

- Risk: `ready_by_at` and `scheduled_*` can still be set via the general `PATCH /{task_id}`. Two paths write the same columns.
  Mitigation: Both paths write the same columns; last-write wins. This is intentional — the specialized endpoints are additive, not replacements.

- Risk: `update_task_schedule` receives `scheduled_end_at` without `scheduled_start_at` (or vice versa), leaving the task in a partially cleared state.
  Mitigation: The service always writes both fields from the request simultaneously. If the caller sends only one, the other is set to `null`. This is correct by design — the endpoint owns the full schedule window. The cross-field validation still applies to whatever values land on the model.

- Risk: Forgetting the terminal-state guard in one of the two services.
  Mitigation: Both service implementations include the `_TERMINAL_STATES` check. Codex must not omit it.

## Validation plan

- `curl PATCH /{task_id}/ready-by-at` with valid datetime → `200` + `client_id`.
- `curl PATCH /{task_id}/ready-by-at` with `ready_by_at: null` → `200`, field null in DB.
- `curl PATCH /{task_id}/schedule` with valid start and end → `200` + `client_id`.
- `curl PATCH /{task_id}/schedule` with `end < start` (both non-null) → `422`.
- `curl PATCH /{task_id}/schedule` with both null → `200`, both fields null in DB.
- `curl PATCH /{task_id}/ready-by-at` on a `RESOLVED` task → `422`.
- `curl PATCH /{task_id}/schedule` on a `CANCELLED` task → `422`.
- Confirm one history record per call in the history table.
- Confirm `task:updated` event fires per call.

## Review log

- `2026-06-25` `david`: Clarified that "delivery date" = `scheduled_start_at` + `scheduled_end_at` (existing columns). No new column or migration required. Second service renamed from `update_task_delivery_at` to `update_task_schedule`.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
