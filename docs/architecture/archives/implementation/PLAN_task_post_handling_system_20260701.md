# PLAN_task_post_handling_system_20260701

## Metadata

- Plan ID: `PLAN_task_post_handling_system_20260701`
- Status: `archived`
- Owner agent: `Claude`
- Created at (UTC): `2026-07-01T00:00:00Z`
- Last updated at (UTC): `2026-07-01T13:31:08Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Introduce a `TaskPostHandling` model that tracks the post-production process for a task after it reaches READY state. Add state evaluation logic, create/sync/complete command services, two new routes (complete + list), a list-query filter by post-handling state, and wire the system into existing task state transitions and task update flows.
- Business/user intent: Operators need a dedicated lifecycle record for what happens to a task after work is finished (e.g. delivery scheduling, collection of assortment info). This record captures state (PENDING → FILLED → COMPLETED) and provides a query surface for filtering tasks by their post-handling progress.
- Non-goals: No worker-facing UI changes, no deletion/archive of post-handling instances, no automated completion.

## Scope

- In scope:
  - `TaskPostHandling` model with `workspace_id`, `task_id`, `state`, `created_at`, `updated_at`
  - `TaskPostHandlingStateEnum` (PENDING, FILLED, COMPLETED) in task enums
  - `TASK_POST_HANDLING` added to `HistoryRecordEntityTypeEnum`
  - Pure evaluator function: `evaluate_post_handling_state(task) → TaskPostHandlingStateEnum | None`
  - Inner session helper: `_create_post_handling_in_session` — creates instance; skips if non-completed one already exists; skips unsupported task types
  - Inner session helper: `_sync_post_handling_state_in_session` — finds active (non-completed) instance; re-evaluates; updates state + history if changed
  - Standalone command: `complete_task_post_handling` — marks instance COMPLETED; validates current state is FILLED (overridable with `force=True`); accepts `post_handling_id` or resolves from `task_id`
  - `serialize_task_post_handling` serializer
  - `serialize_task` extended with optional `post_handling_instances` parameter (key always present, null when not loaded)
  - Wiring `_create_post_handling_in_session` into `maybe_evaluate_task_ready` (after task transitions to READY, inside same transaction)
  - Wiring `_sync_post_handling_state_in_session` into `update_task` and `update_task_post_handling` (in a second `maybe_begin` block after the update commits)
  - New query service `list_task_post_handlings` — returns all instances for a task_id
  - `list_tasks` extended with `post_handling_states` CSV filter + conditional `post_handling` key in item payload
  - `get_task` extended to always load and serialize post-handling instances
  - Two new routes: `POST /{task_id}/post-handling/complete` and `GET /{task_id}/post-handling`
  - `GET /` route extended with `post_handling_states` query param
  - Alembic migration: new table `task_post_handlings`, new enum `task_post_handling_state_enum`, ALTER existing `history_record_entity_type_enum`
  - Update handoff document

- Out of scope:
  - Deletion/soft-delete of `TaskPostHandling` instances
  - Automated completion triggers
  - Expanding the evaluator beyond RETURN and PRE_ORDER task types

- Assumptions:
  - The Alembic chain has a single head: `1f6a0c9b3d2e`. New migration's `down_revision = "1f6a0c9b3d2e"`.
  - `history_record_entity_type_enum` is a PostgreSQL enum already present in the DB (`create_type=False` on the ORM). Adding a value uses `ALTER TYPE ... ADD VALUE IF NOT EXISTS`.
  - PostgreSQL does not support removing enum values on downgrade; the downgrade for the ALTER TYPE step is a no-op.
  - `maybe_begin` follows the contract: subordinate mode (no commit) when inside an active transaction; owner mode (commits on exit) when called at the top level.
  - Async SQLAlchemy: ORM object attributes expire after a transaction commits. Any helper that needs task fields must either receive the task within an active transaction, or re-query it itself.

## Clarifications required

- None. All design questions are resolved in the scope above.

## Acceptance criteria

1. `TaskPostHandling` table exists in DB and is migrated as a single Alembic head.
2. When a task transitions to READY, a `TaskPostHandling` record is created (if none already exists in non-completed state and task_type is RETURN or PRE_ORDER).
3. `evaluate_post_handling_state` returns `None` for unsupported task types, `PENDING` when task is not READY, `FILLED` when task is READY and the type-specific fill conditions are met, `PENDING` when READY but conditions unmet.
4. After `update_task` or `update_task_post_handling` commits, the active post-handling instance's state is re-evaluated and updated if it changed.
5. `POST /{task_id}/post-handling/complete` marks the active (non-completed) instance as COMPLETED; requires state == FILLED unless `force=True`; returns `{"client_id": "tph_..."}`.
6. `GET /{task_id}/post-handling` returns all post-handling instances for a task.
7. `GET /` (list tasks) accepts `post_handling_states` CSV param; only joins the post-handling table when the param is present.
8. Task list response items include `"post_handling": null` when the filter was not used, and `"post_handling": [...]` when it was.
9. `GET /{task_id}` response includes `"post_handling": [...]` for the task (always loaded in detail view).
10. All state transitions on `TaskPostHandling` generate a history record via `_create_history_record_in_session`.
11. `py_compile` passes for all new and modified modules.
12. Alembic reports a single head after migration applied.

## Contracts and skills

### Contracts loaded

- `backend/task_system/architecture/01_architecture.md`: overall system layering
- `backend/task_system/architecture/04_context.md`: `ServiceContext` shape, `workspace_id`, `user_id`, `identity`, `incoming_data`, `query_params`
- `backend/task_system/architecture/05_errors.md`: `NotFound`, `ValidationError` usage
- `backend/task_system/architecture/06_commands.md` + `06_commands_local.md`: `maybe_begin` rules, `session.flush()`, no own commit in subordinate helpers, event dispatch outside `maybe_begin`
- `backend/task_system/architecture/07_queries.md` + `07_queries_local.md`: offset pagination, query structure
- `backend/task_system/architecture/09_routers.md`: thin router, `build_ok`/`build_err`, `run_service`, role guards
- `backend/task_system/architecture/03_models.md`: model conventions (`IdentityMixin`, `Base`, `CLIENT_ID_PREFIX`)
- `backend/task_system/architecture/08_domain.md`: enum + serializer placement
- `backend/task_system/architecture/11_infra_events.md`: `event_bus.dispatch`, `build_workspace_event`
- `backend/task_system/architecture/30_migrations.md`: single-head discipline, `alembic upgrade head`
- `backend/task_system/architecture/21_naming_conventions.md`: file/class/table naming
- `backend/task_system/architecture/40_identity.md`: `IdentityMixin`, `CLIENT_ID_PREFIX`, ULID generation

### File read intent — pattern vs. relational

Permitted relational reads (done before writing plan):
- `task.py`: exact FK fields and column types for the new model
- `history_record.py` + `history_record_link.py`: polymorphic system shape
- `enums.py` (domain/tasks): existing enum values
- `serializers.py`: existing `serialize_task` signature
- `_task_state_transitions.py`: where to insert the create-post-handling call
- `update_task.py`, `update_task_post_handling.py`, `update_task_schedule.py`: transaction and sync patterns
- `tasks.py` (queries): list_tasks structure, subquery pattern for filters
- `tasks.py` (router): existing route signatures, role lists
- `history/enums.py`: exact enum values for `HistoryRecordEntityTypeEnum`
- `identity.py`: `IdentityMixin` and `generate_id` — no separate prefix registry; prefix is set as `CLIENT_ID_PREFIX` class var

## Implementation plan

### Step 1 — Add `TaskPostHandlingStateEnum` to task enums

File: `app/beyo_manager/domain/tasks/enums.py`

Append at end of file:

```python
class TaskPostHandlingStateEnum(enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    COMPLETED = "completed"
```

---

### Step 2 — Add `TASK_POST_HANDLING` to `HistoryRecordEntityTypeEnum`

File: `app/beyo_manager/domain/history/enums.py`

Add to `HistoryRecordEntityTypeEnum`:
```python
TASK_POST_HANDLING = "task_post_handling"
```

---

### Step 3 — Create `TaskPostHandling` model

File (new): `app/beyo_manager/models/tables/tasks/task_post_handling.py`

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class TaskPostHandling(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tph"
    __tablename__ = "task_post_handlings"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[TaskPostHandlingStateEnum] = mapped_column(
        SAEnum(TaskPostHandlingStateEnum, name="task_post_handling_state_enum", create_type=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Note: History records are linked via the polymorphic `history_record_links` table using `entity_type = "task_post_handling"` and `entity_client_id = tph.client_id`. No SQLAlchemy relationship is declared on the model — records are written and read via `_create_history_record_in_session` and query helpers, same as for `Task`.

---

### Step 4 — Add `serialize_task_post_handling` to serializers and extend `serialize_task`

File: `app/beyo_manager/domain/tasks/serializers.py`

**4a.** Add import at top of file:
```python
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
```

**4b.** Add new function after `serialize_task`:
```python
def serialize_task_post_handling(tph: TaskPostHandling) -> dict:
    return {
        "client_id": tph.client_id,
        "task_id": tph.task_id,
        "state": tph.state.value,
        "created_at": tph.created_at.isoformat() if tph.created_at else None,
        "updated_at": tph.updated_at.isoformat() if tph.updated_at else None,
    }
```

**4c.** Change `serialize_task` signature to accept optional `post_handling_instances`:
```python
def serialize_task(task: Task, post_handling_instances: list[TaskPostHandling] | None = None) -> dict:
```

**4d.** Add `"post_handling"` key at the end of the returned dict in `serialize_task`:
```python
"post_handling": (
    [serialize_task_post_handling(ph) for ph in post_handling_instances]
    if post_handling_instances is not None
    else None
),
```

All existing callers of `serialize_task(task)` are unaffected — the new parameter defaults to `None` so `post_handling` is always present in the response (as `null` when not loaded).

---

### Step 5 — Create state evaluator

File (new): `app/beyo_manager/domain/tasks/_post_handling_state_evaluator.py`

Pure function. No DB access. No imports from services.

```python
from beyo_manager.domain.tasks.enums import (
    TaskPostHandlingStateEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.models.tables.tasks.task import Task


_SUPPORTED_TASK_TYPES = frozenset({TaskTypeEnum.RETURN, TaskTypeEnum.PRE_ORDER})


def evaluate_post_handling_state(task: Task) -> TaskPostHandlingStateEnum | None:
    """Return the correct post-handling state for the task, or None if unsupported."""
    if task.task_type not in _SUPPORTED_TASK_TYPES:
        return None

    if task.state != TaskStateEnum.READY:
        return TaskPostHandlingStateEnum.PENDING

    # Task is READY — evaluate fill conditions by type
    if task.task_type == TaskTypeEnum.PRE_ORDER:
        filled = bool(task.fulfillment_method) or bool(
            task.scheduled_start_at is not None or task.scheduled_end_at is not None
        )
    elif task.task_type == TaskTypeEnum.RETURN:
        filled = bool(task.assortment)
    else:
        filled = False

    return TaskPostHandlingStateEnum.FILLED if filled else TaskPostHandlingStateEnum.PENDING
```

---

### Step 6 — Create inner session helper: `_create_post_handling_in_session`

File (new): `app/beyo_manager/services/commands/task_post_handling/_create_post_handling_in_session.py`

This helper runs **inside the caller's `maybe_begin` block**. It must NOT open its own transaction or call `commit`. Call `session.flush()` after `session.add`.

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks._post_handling_state_evaluator import evaluate_post_handling_state
from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _create_post_handling_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> TaskPostHandling | None:
    """Create a TaskPostHandling record for the task if one does not already exist
    in a non-completed state. Returns None if skipped."""

    initial_state = evaluate_post_handling_state(task)
    if initial_state is None:
        return None  # unsupported task type

    # Check for existing non-completed instance
    existing = (
        await session.execute(
            select(TaskPostHandling).where(
                TaskPostHandling.workspace_id == workspace_id,
                TaskPostHandling.task_id == task.client_id,
                TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        return None  # already has an active instance

    instance = TaskPostHandling(
        workspace_id=workspace_id,
        task_id=task.client_id,
        state=initial_state,
        created_at=now,
    )
    session.add(instance)
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.CREATED,
        description=f"Post-handling record created with state {initial_state.value}",
        field_name="state",
        from_value=None,
        to_value={"state": initial_state.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    return instance
```

---

### Step 7 — Create inner session helper: `_sync_post_handling_state_in_session`

File (new): `app/beyo_manager/services/commands/task_post_handling/_sync_post_handling_state_in_session.py`

This helper runs **inside the caller's `maybe_begin` block**. It loads the task itself (the task passed in may be stale after a prior commit — see Step 11 on why the task is always reloaded from DB here).

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks._post_handling_state_evaluator import evaluate_post_handling_state
from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _sync_post_handling_state_in_session(
    session: AsyncSession,
    task_id: str,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> bool:
    """Re-evaluate and update the active post-handling instance for the task.
    Returns True if state was changed, False if nothing to do."""

    # Load fresh task within this transaction (callers may have a stale reference post-commit)
    task = (
        await session.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.client_id == task_id,
                Task.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        return False

    new_state = evaluate_post_handling_state(task)
    if new_state is None:
        return False  # unsupported task type

    # Find active (non-completed) instance
    instance = (
        await session.execute(
            select(TaskPostHandling).where(
                TaskPostHandling.workspace_id == workspace_id,
                TaskPostHandling.task_id == task_id,
                TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()

    if instance is None:
        return False  # no active instance to sync

    if instance.state == new_state:
        return False  # no change

    old_state = instance.state
    instance.state = new_state
    instance.updated_at = now
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.UPDATED,
        description=f"Post-handling state changed from {old_state.value} to {new_state.value}",
        field_name="state",
        from_value={"state": old_state.value},
        to_value={"state": new_state.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    return True
```

---

### Step 8 — Create standalone command: `complete_task_post_handling`

File (new): `app/beyo_manager/services/commands/task_post_handling/complete_task_post_handling.py`

Full command with own `maybe_begin` and event dispatch. Accepts `post_handling_id` or `task_id` to locate the active instance. `force=True` bypasses the FILLED state requirement.

```python
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


class CompleteTaskPostHandlingRequest(BaseModel):
    task_id: str | None = None
    post_handling_id: str | None = None
    force: bool = False


def parse_complete_task_post_handling_request(data: dict) -> CompleteTaskPostHandlingRequest:
    try:
        return CompleteTaskPostHandlingRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def complete_task_post_handling(ctx: ServiceContext) -> dict:
    request = parse_complete_task_post_handling_request(ctx.incoming_data)

    if request.post_handling_id is None and request.task_id is None:
        raise ValidationError("Either post_handling_id or task_id is required.")

    async with maybe_begin(ctx.session):
        if request.post_handling_id is not None:
            result = await ctx.session.execute(
                select(TaskPostHandling).where(
                    TaskPostHandling.workspace_id == ctx.workspace_id,
                    TaskPostHandling.client_id == request.post_handling_id,
                )
            )
            instance = result.scalar_one_or_none()
        else:
            result = await ctx.session.execute(
                select(TaskPostHandling).where(
                    TaskPostHandling.workspace_id == ctx.workspace_id,
                    TaskPostHandling.task_id == request.task_id,
                    TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
                )
            )
            instance = result.scalar_one_or_none()

        if instance is None:
            raise NotFound("Active task post-handling instance not found.")

        if instance.state == TaskPostHandlingStateEnum.COMPLETED:
            raise ValidationError("Post-handling instance is already completed.")

        if not request.force and instance.state != TaskPostHandlingStateEnum.FILLED:
            raise ValidationError(
                "Post-handling instance must be in state 'filled' to complete. Use force=true to override."
            )

        old_state = instance.state
        now = datetime.now(timezone.utc)
        instance.state = TaskPostHandlingStateEnum.COMPLETED
        instance.updated_at = now

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
            entity_client_id=instance.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=f"Post-handling marked completed (from {old_state.value})",
            field_name="state",
            from_value={"state": old_state.value},
            to_value={"state": TaskPostHandlingStateEnum.COMPLETED.value},
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        build_workspace_event(instance, "task_post_handling:completed"),
    ])
    return {"client_id": instance.client_id}
```

---

### Step 9 — Wire create helper into `maybe_evaluate_task_ready`

File: `app/beyo_manager/services/commands/tasks/_task_state_transitions.py`

**9a.** Add imports:
```python
from datetime import datetime
# existing imports remain; add:
from beyo_manager.services.commands.task_post_handling._create_post_handling_in_session import (
    _create_post_handling_in_session,
)
```

**9b.** At the end of `maybe_evaluate_task_ready`, after setting `task.state = TaskStateEnum.READY` and before `return True`, add:

```python
    await _create_post_handling_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        updated_by_id=updated_by_id,
        username_snapshot=None,  # no identity available here; callers can pass if needed
    )
    return True
```

Wait — the existing helper signature uses `updated_by_id` not `user_id`. Change `_create_post_handling_in_session` parameter name to `user_id` as designed in Step 6 and pass `user_id=updated_by_id` here:

```python
    await _create_post_handling_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
    return True
```

The full updated tail of `maybe_evaluate_task_ready` (replacing the current `task.state = ...; return True` block):

```python
    task.state = TaskStateEnum.READY
    task.updated_at = now
    task.updated_by_id = updated_by_id

    await _create_post_handling_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
    return True
```

---

### Step 10 — Wire sync helper into `update_task`

File: `app/beyo_manager/services/commands/tasks/update_task.py`

**10a.** Add imports:
```python
from beyo_manager.services.commands.task_post_handling._sync_post_handling_state_in_session import (
    _sync_post_handling_state_in_session,
)
```

**10b.** After the existing `async with maybe_begin(ctx.session):` block (which commits the task update) and **before** `await event_bus.dispatch(...)`, add a second `maybe_begin` block:

```python
    async with maybe_begin(ctx.session):
        username = ctx.identity.get("username")
        await _sync_post_handling_state_in_session(
            ctx.session,
            task.client_id,
            workspace_id=ctx.workspace_id,
            now=datetime.now(timezone.utc),
            user_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([build_workspace_event(task, "task:updated")])
```

Note: `task.client_id` is safe to access on an expired ORM object because `client_id` is the primary key and is never expired by SQLAlchemy.

---

### Step 11 — Wire sync helper into `update_task_post_handling`

File: `app/beyo_manager/services/commands/task_post_handling/update_task_post_handling.py`

**11a.** Add imports:
```python
from beyo_manager.services.commands.task_post_handling._sync_post_handling_state_in_session import (
    _sync_post_handling_state_in_session,
)
```

**11b.** After the existing `async with maybe_begin(ctx.session):` block and before `await event_bus.dispatch(...)`:

```python
    async with maybe_begin(ctx.session):
        await _sync_post_handling_state_in_session(
            ctx.session,
            task.client_id,
            workspace_id=ctx.workspace_id,
            now=datetime.now(timezone.utc),
            user_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([build_workspace_event(task, "task:updated")])
```

Note: `username` is already assigned in the existing code before the dispatch; reuse it here.

---

### Step 12 — Create query service: `list_task_post_handlings`

File (new): `app/beyo_manager/services/queries/tasks/list_task_post_handlings.py`

```python
from sqlalchemy import select

from beyo_manager.domain.tasks.serializers import serialize_task_post_handling
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.context import ServiceContext


async def list_task_post_handlings(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found.")

    result = await ctx.session.execute(
        select(TaskPostHandling).where(
            TaskPostHandling.workspace_id == ctx.workspace_id,
            TaskPostHandling.task_id == task_id,
        ).order_by(TaskPostHandling.created_at.asc())
    )
    instances = result.scalars().all()

    return {
        "post_handling": [serialize_task_post_handling(ph) for ph in instances]
    }
```

---

### Step 13 — Extend `list_tasks` and `get_task` in query service

File: `app/beyo_manager/services/queries/tasks/tasks.py`

**13a.** Add import at top:
```python
from beyo_manager.domain.tasks.serializers import serialize_task_post_handling
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
```

**13b.** In `list_tasks`, read and parse the new query param after existing param declarations:
```python
post_handling_states = _split_csv(ctx.query_params.get("post_handling_states"))
```

**13c.** Add the filter (subquery pattern, consistent with existing filters) after the `upholstery_requirement_states` block:
```python
if post_handling_states:
    ph_subq = (
        select(TaskPostHandling.task_id)
        .where(
            TaskPostHandling.workspace_id == ctx.workspace_id,
            TaskPostHandling.state.in_(post_handling_states),
        )
        .distinct()
    )
    stmt = stmt.where(Task.client_id.in_(ph_subq))
```

**13d.** After loading `task_map` on the page, load post-handling instances when filter is active:
```python
post_handling_map: dict[str, list[TaskPostHandling]] = {}
if post_handling_states:
    ph_result = await ctx.session.execute(
        select(TaskPostHandling).where(
            TaskPostHandling.workspace_id == ctx.workspace_id,
            TaskPostHandling.task_id.in_(page_ids),
        )
    )
    for ph in ph_result.scalars().all():
        post_handling_map.setdefault(ph.task_id, []).append(ph)
```

**13e.** In the `items_payload` construction, pass the list (or None) to `serialize_task`:
```python
items_payload.append(
    {
        "task": serialize_task(
            task,
            post_handling_instances=post_handling_map.get(task_id) if post_handling_states else None,
        ),
        "primary_item": serialize_item(primary_item),
        "item_images": item_images_map.get(primary_item_id, []),
    }
)
```

**13f.** In `get_task`, after loading `steps`, load post-handling instances for the task:
```python
post_handling_result = await ctx.session.execute(
    select(TaskPostHandling).where(
        TaskPostHandling.workspace_id == ctx.workspace_id,
        TaskPostHandling.task_id == task.client_id,
    ).order_by(TaskPostHandling.created_at.asc())
)
post_handling_instances = post_handling_result.scalars().all()
```

**13g.** In the `get_task` return dict, change `"task": serialize_task(task)` to:
```python
"task": serialize_task(task, post_handling_instances=list(post_handling_instances)),
```

---

### Step 14 — Add routes and query param to task router

File: `app/beyo_manager/routers/api_v1/tasks.py`

**14a.** Add imports at top:
```python
from beyo_manager.services.commands.task_post_handling.complete_task_post_handling import complete_task_post_handling
from beyo_manager.services.queries.tasks.list_task_post_handlings import list_task_post_handlings
```

**14b.** Add body model near other body models:
```python
class _CompleteTaskPostHandlingBody(BaseModel):
    post_handling_id: str | None = None
    force: bool = False
```

**14c.** Add `post_handling_states` query param to `route_list_tasks`:
```python
post_handling_states: str | None = Query(None),
```
And include it in the `query_params` dict:
```python
"post_handling_states": post_handling_states,
```

**14d.** Add new route for listing post-handling instances (place after `route_get_task_flow_records`):
```python
@router.get("/{task_id}/post-handling")
async def route_list_task_post_handlings(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_post_handlings, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**14e.** Add new route for completing a post-handling instance (place after the listing route):
```python
@router.post("/{task_id}/post-handling/complete")
async def route_complete_task_post_handling(
    task_id: str,
    body: _CompleteTaskPostHandlingBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(complete_task_post_handling, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Note: the `task_id` path param is passed via `incoming_data` as a fallback; the service also accepts `post_handling_id` from the body.

---

### Step 15 — Write Alembic migration

File (new): `app/migrations/versions/3c4d5e6f7a8b_add_task_post_handling_table.py`

```python
"""add task_post_handlings table

Revision ID: 3c4d5e6f7a8b
Revises: 1f6a0c9b3d2e
Create Date: 2026-07-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "1f6a0c9b3d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add TASK_POST_HANDLING to the existing polymorphic history entity type enum.
    # ALTER TYPE ... ADD VALUE cannot be executed inside a transaction on some PG versions,
    # so use COMMIT before if running in transactional DDL mode.
    op.execute("ALTER TYPE history_record_entity_type_enum ADD VALUE IF NOT EXISTS 'task_post_handling'")

    # Create the state enum for task_post_handlings
    op.execute(
        "CREATE TYPE task_post_handling_state_enum AS ENUM ('pending', 'filled', 'completed')"
    )

    op.create_table(
        "task_post_handlings",
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(64),
            sa.ForeignKey("workspaces.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(64),
            sa.ForeignKey("tasks.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.Enum(
                "pending", "filled", "completed",
                name="task_post_handling_state_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_task_post_handlings_workspace_id", "task_post_handlings", ["workspace_id"])
    op.create_index("ix_task_post_handlings_task_id", "task_post_handlings", ["task_id"])
    op.create_index("ix_task_post_handlings_state", "task_post_handlings", ["state"])


def downgrade() -> None:
    op.drop_index("ix_task_post_handlings_state", table_name="task_post_handlings")
    op.drop_index("ix_task_post_handlings_task_id", table_name="task_post_handlings")
    op.drop_index("ix_task_post_handlings_workspace_id", table_name="task_post_handlings")
    op.drop_table("task_post_handlings")
    op.execute("DROP TYPE IF EXISTS task_post_handling_state_enum")
    # Note: PostgreSQL does not support removing values from an existing enum type.
    # The 'task_post_handling' value added to history_record_entity_type_enum is not reversed.
```

**Run migration after creation:**
```bash
cd app && ../.venv/bin/alembic upgrade head
```

Verify single head:
```bash
../.venv/bin/alembic heads
```

---

### Step 16 — Update handoff document

File: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_post_handling_20260701.md`

Append a new section after the existing `## Validation notes` section (keep all existing content; add below):

```markdown
---

## Update: Task post-handling lifecycle (2026-07-01)

### New endpoints

#### `GET /api/v1/tasks/{task_id}/post-handling`
Returns all post-handling instances for a task (ordered oldest-first).
Access: ADMIN, MANAGER, SELLER.

Response:
```json
{
  "post_handling": [
    {
      "client_id": "tph_...",
      "task_id": "tsk_...",
      "state": "pending",
      "created_at": "2026-07-01T10:00:00Z",
      "updated_at": null
    }
  ]
}
```

States: `pending` → `filled` → `completed`.

#### `POST /api/v1/tasks/{task_id}/post-handling/complete`
Marks the active (non-completed) post-handling instance as completed.
Access: ADMIN, MANAGER, SELLER.

Request body (all optional):
```json
{
  "post_handling_id": "tph_...",
  "force": false
}
```

- If `post_handling_id` is omitted, uses `task_id` from URL to find the active instance.
- Requires state == `filled` unless `force: true`.

Response:
```json
{ "client_id": "tph_..." }
```

Error cases:
- `404` if no active post-handling instance found.
- `400` if instance is already completed.
- `400` if state is not `filled` and `force` is not `true`.

Realtime event: emits `task_post_handling:completed` on success.

### Modified endpoint: `GET /api/v1/tasks` (list tasks)

New query parameter: `post_handling_states` (CSV string, e.g. `"pending,filled"`).
- When present, filters tasks to only those with a post-handling instance in one of the specified states.
- When absent, no join to the post-handling table is made.

Task items in the response now include a `post_handling` key inside `task`:
- `null` when the `post_handling_states` filter was not used.
- An array of post-handling objects when the filter was active (same shape as the GET endpoint above).

### Modified endpoint: `GET /api/v1/tasks/{task_id}`

The task object now always includes:
```json
{
  "post_handling": [ ... ]
}
```
The array is empty `[]` if no instances have been created yet.

### Post-handling state lifecycle

A `TaskPostHandling` record is automatically created when a task transitions to `READY` state, for tasks of type `RETURN` or `PRE_ORDER`. Other task types do not get post-handling records.

**State transitions:**
- `PENDING`: created automatically; task is READY but fill conditions are not yet met.
- `FILLED`: automatically set (via update_task or update_task_post_handling) when fill conditions are met:
  - `PRE_ORDER`: requires `fulfillment_method` set, OR at least one of `scheduled_start_at`/`scheduled_end_at` set.
  - `RETURN`: requires `assortment` set (non-null, non-empty).
- `COMPLETED`: set manually via `POST /{task_id}/post-handling/complete`.

State changes emit history records accessible via `GET /{task_id}/flow-records`.
```

---

### Step 17 — Validate

Run for each new and modified module:
```bash
.venv/bin/python -m py_compile app/beyo_manager/models/tables/tasks/task_post_handling.py
.venv/bin/python -m py_compile app/beyo_manager/domain/tasks/enums.py
.venv/bin/python -m py_compile app/beyo_manager/domain/history/enums.py
.venv/bin/python -m py_compile app/beyo_manager/domain/tasks/serializers.py
.venv/bin/python -m py_compile app/beyo_manager/domain/tasks/_post_handling_state_evaluator.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/task_post_handling/_create_post_handling_in_session.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/task_post_handling/_sync_post_handling_state_in_session.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/task_post_handling/complete_task_post_handling.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/tasks/_task_state_transitions.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/tasks/update_task.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/task_post_handling/update_task_post_handling.py
.venv/bin/python -m py_compile app/beyo_manager/services/queries/tasks/list_task_post_handlings.py
.venv/bin/python -m py_compile app/beyo_manager/services/queries/tasks/tasks.py
.venv/bin/python -m py_compile app/beyo_manager/routers/api_v1/tasks.py
.venv/bin/python -m py_compile app/migrations/versions/3c4d5e6f7a8b_add_task_post_handling_table.py
```

Run migration and verify single head:
```bash
cd app && ../.venv/bin/alembic upgrade head
../.venv/bin/alembic heads  # must show exactly one head: 3c4d5e6f7a8b
```

## Risks and mitigations

- Risk: `ALTER TYPE ... ADD VALUE` may fail if run inside a transaction on older PostgreSQL versions.
  Mitigation: The migration uses `op.execute(...)` directly; Alembic with `transaction_per_migration=True` may need to commit the transaction first. If the migration fails on this step, wrap it with `op.execute("COMMIT")` before the `ALTER TYPE` and `op.execute("BEGIN")` after.

- Risk: `history_record_entity_type_enum` in the ORM uses `create_type=False`; adding the value in Python and in the DB enum must stay in sync.
  Mitigation: Migration adds the value before the table is created; ORM uses `StrEnum` so new values are valid Python at runtime as long as the migration has run.

- Risk: `maybe_evaluate_task_ready` now calls `_create_post_handling_in_session` inside the same transaction as step-state transition. If that helper raises, the entire step transition rolls back.
  Mitigation: The helper only writes a new row + history — no complex logic. Failures are real errors (e.g., DB constraint) that should roll back the parent.

- Risk: `_sync_post_handling_state_in_session` re-queries the task from DB (loads fresh). If called in the context of a test or another `maybe_begin` that hasn't flushed yet, it may read stale data.
  Mitigation: The sync helper is always called in a fresh `maybe_begin` block **after** the task-update transaction has committed; the task is fully persisted before sync runs.

- Risk: `build_workspace_event(instance, "task_post_handling:completed")` — `instance` must have `workspace_id` for `build_workspace_event` to attach the right workspace scope.
  Mitigation: `TaskPostHandling` has `workspace_id` column; `build_workspace_event` can read it via `instance.workspace_id`. If `build_workspace_event` requires a specific model interface, check its implementation and adapt the call accordingly.

## Validation plan

- `py_compile` on all changed files: no syntax errors
- `alembic upgrade head`: migration applies cleanly
- `alembic heads`: single head `3c4d5e6f7a8b`

## Review log

- `2026-07-01` Claude: Initial plan created from intention.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `user`
