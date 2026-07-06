# PLAN_task_customer_coordination_20260704

## Metadata

- Plan ID: `PLAN_task_customer_coordination_20260704`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T12:55:39Z`
- Related issue/ticket: `n/a`
- Intention plan: `n/a`

## Goal and intent

- Goal: Introduce a `TaskCustomerCoordination` tracking record that is automatically created when a task transitions to the `ready` state. Expose query filtering, a completion command, and a state-count query over these records — mirroring the existing `TaskPostHandling` feature set.
- Business/user intent: Allow coordinators to track and manage customer-facing outreach for each ready task independently of the post-handling process.
- Non-goals: No customer notification sending; no frontend beyond the API contract; no changes to `TaskPostHandling` logic.

## Scope

- In scope:
  - New `TaskCustomerCoordinationStateEnum` (`pending`, `coordinating`, `completed`)
  - New `TaskCustomerCoordination` model table in `models/tables/tasks/`
  - Alembic migration for the new table and new SA enum
  - Register model in `models/__init__.py`
  - Add `TASK_CUSTOMER_COORDINATION` to `HistoryRecordEntityTypeEnum`
  - Add `TASK_CUSTOMER_COORDINATION` to `EmailThreadEntityTypeEnum`
  - In-session helper `_create_customer_coordination_in_session`
  - Update `maybe_evaluate_task_ready` in `_task_state_transitions.py` to also create the coordination record
  - New `serialize_task_customer_coordination` serializer; extend `serialize_task` with `customer_coordination` key
  - Extend `list_tasks` query service and `route_list_tasks` router with `customer_coordination_states` param
  - New command `complete_task_customer_coordination` with history record + event dispatch
  - New router endpoint `POST /{task_id}/customer-coordination/complete`
  - New query service `count_task_customer_coordination_states`
  - New router endpoint `GET /customer-coordination/counts`
- Out of scope: Email sending, push notifications, `get_task` detail endpoint changes, worker-facing views.
- Assumptions:
  - `maybe_begin` transaction utility is available (contract `06_commands_local.md`)
  - The `_create_history_record_in_session` helper signature is stable
  - `EmailThreadEntityTypeEnum` values are stored as strings in the DB; adding a new variant does not require a migration of that enum

## Clarifications required

- None — pattern is fully established by TaskPostHandling. EmailThreadEntityTypeEnum uses `str, enum.Enum` so the new variant is additive.

## Acceptance criteria

1. When a task transitions to `ready`, a `TaskCustomerCoordination` record with state `pending` is created — unless a non-completed record already exists for that task.
2. `GET /tasks?customer_coordination_states=pending` returns tasks that have a coordination record in the `pending` state, each serialized with a `customer_coordination` array; tasks without a matching record have `customer_coordination: null`.
3. `POST /tasks/{task_id}/customer-coordination/complete` transitions the active (non-completed) coordination record to `completed`, writes a history record, and dispatches an event.
4. `GET /tasks/customer-coordination/counts` returns per-state counts scoped to the workspace.
5. `TaskCustomerCoordination` transitions appear in the polymorphic history table under entity type `task_customer_coordination`.
6. `EmailThread` can be linked to a `TaskCustomerCoordination` instance via entity type `task_customer_coordination`.

## Contracts and skills

### Contracts loaded

- `../architecture/01_architecture.md`: overall layering rules
- `../architecture/04_context.md`: ServiceContext shape
- `../architecture/05_errors.md`: NotFound / ValidationError raising
- `../architecture/06_commands.md`: command structure, session.add / flush / error-raising shape
- `../architecture/06_commands_local.md`: `maybe_begin` transaction utility, subordinate-command event rule
- `../architecture/07_queries.md`: query service shape
- `../architecture/07_queries_local.md`: offset pagination override
- `../architecture/09_routers.md`: handler wiring, `run_service`, `build_ok`/`build_err`
- `../architecture/21_naming_conventions.md`: file/class/field naming
- `../architecture/03_models.md`: SQLAlchemy model conventions, IdentityMixin, `configure_sa_enum_values`
- `../architecture/30_migrations.md`: Alembic migration rules
- `../architecture/08_domain.md`: domain enum placement

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin` utility — used in `complete_task_customer_coordination`
- `../architecture/07_queries_local.md`: offset pagination — used in count query

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `_create_post_handling_in_session.py` — already done, needed to understand exact guard logic and history call signature
- Reading `complete_task_post_handling.py` — already done, needed to understand completion command pattern
- Reading `count_task_post_handling_states.py` — already done, needed to understand count query output shape
- Reading `tasks.py` (query) — already done, needed to understand `upholstery_requirement_states` join pattern and `post_handling_map` pattern
- Reading `tasks.py` (router) — already done, needed to understand param forwarding and route naming

### Skill selection

- Primary skill: `task_system/SKILL_CRUD_REALTIME.md` (CRUD + realtime goal bundle)
- Router trigger terms: `customer-coordination`
- Excluded alternatives: none

## Implementation plan

### Step 1 — Add `TaskCustomerCoordinationStateEnum` to task domain enums

**File:** `app/beyo_manager/domain/tasks/enums.py`

Append at the end:

```python
class TaskCustomerCoordinationStateEnum(enum.Enum):
    PENDING = "pending"
    COORDINATING = "coordinating"
    COMPLETED = "completed"
```

---

### Step 2 — Add `TASK_CUSTOMER_COORDINATION` to history entity type enum

**File:** `app/beyo_manager/domain/history/enums.py`

Add to `HistoryRecordEntityTypeEnum`:

```python
TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
```

---

### Step 3 — Add `TASK_CUSTOMER_COORDINATION` to email thread entity type enum

**File:** `app/beyo_manager/domain/emails/enums.py`

Add to `EmailThreadEntityTypeEnum`:

```python
TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
```

This allows `EmailThread.entity_type` to be set to `"task_customer_coordination"` when a thread is linked to a coordination record.

---

### Step 4 — Create the `TaskCustomerCoordination` model

**File (new):** `app/beyo_manager/models/tables/tasks/task_customer_coordination.py`

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class TaskCustomerCoordination(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "tcc"
    __tablename__ = "task_customer_coordinations"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[TaskCustomerCoordinationStateEnum] = mapped_column(
        SAEnum(
            TaskCustomerCoordinationStateEnum,
            name="task_customer_coordination_state_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Structural notes:
- `CLIENT_ID_PREFIX = "tcc"` — distinct from `"tph"` used by post-handling
- `create_type=True` — the SA enum is new and must be created by Alembic
- No relationship declared (matches `TaskPostHandling` pattern — queries use explicit joins)

---

### Step 5 — Register new model in `models/__init__.py`

**File:** `app/beyo_manager/models/__init__.py`

After the `task_post_handling` import line, add:

```python
from beyo_manager.models.tables.tasks import task_customer_coordination  # noqa: F401
```

---

### Step 6 — Create Alembic migration

Generate and edit a new migration that:

1. Creates the PostgreSQL enum type `task_customer_coordination_state_enum` with values `('pending', 'coordinating', 'completed')` — use `op.execute("CREATE TYPE ...")` pattern consistent with other migrations in this project.
2. Creates table `task_customer_coordinations` with columns matching the model.
3. Adds indexes on `workspace_id`, `task_id`, `state`.

Downgrade: drop table then drop type.

> Note: `HistoryRecordEntityTypeEnum` and `EmailThreadEntityTypeEnum` both use `StrEnum` / `str, enum.Enum` — their values are stored as plain strings (no DB enum type), so no migration is needed for those additions.

---

### Step 7 — Create `_create_customer_coordination_in_session` helper

**File (new):** `app/beyo_manager/services/commands/task_customer_coordination/_create_customer_coordination_in_session.py`

Logic mirrors `_create_post_handling_in_session` exactly, adapted for this model:

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _create_customer_coordination_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> TaskCustomerCoordination | None:
    existing = (
        await session.execute(
            select(TaskCustomerCoordination).where(
                TaskCustomerCoordination.workspace_id == workspace_id,
                TaskCustomerCoordination.task_id == task.client_id,
                TaskCustomerCoordination.state != TaskCustomerCoordinationStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None

    initial_state = TaskCustomerCoordinationStateEnum.PENDING
    instance = TaskCustomerCoordination(
        workspace_id=workspace_id,
        task_id=task.client_id,
        state=initial_state,
        created_at=now,
    )
    session.add(instance)
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.CREATED,
        description=f"Customer coordination record created with state {initial_state.value}",
        field_name="state",
        from_value=None,
        to_value={"state": initial_state.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    return instance
```

Key differences from the post-handling version:
- No `evaluate_post_handling_state` call — initial state is always `PENDING` unconditionally.
- Guard checks `state != COMPLETED` (same pattern as post-handling).

---

### Step 8 — Update `_task_state_transitions.py`

**File:** `app/beyo_manager/services/commands/tasks/_task_state_transitions.py`

Add import:

```python
from beyo_manager.services.commands.task_customer_coordination._create_customer_coordination_in_session import (
    _create_customer_coordination_in_session,
)
```

Inside `maybe_evaluate_task_ready`, after the existing `_create_post_handling_in_session(...)` call, add:

```python
    await _create_customer_coordination_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
```

Both helpers are called in sequence within the same session flush scope. No additional `flush` is needed between them — `_create_customer_coordination_in_session` calls `flush` internally.

---

### Step 9 — Add serializer for `TaskCustomerCoordination`

**File:** `app/beyo_manager/domain/tasks/serializers.py`

Add import at top:

```python
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
```

Add new serializer function:

```python
def serialize_task_customer_coordination(tcc: TaskCustomerCoordination) -> dict:
    return {
        "client_id": tcc.client_id,
        "task_id": tcc.task_id,
        "state": tcc.state.value,
        "created_at": tcc.created_at.isoformat() if tcc.created_at else None,
        "updated_at": tcc.updated_at.isoformat() if tcc.updated_at else None,
    }
```

Update `serialize_task` signature and body to accept an optional `customer_coordination_instances` parameter (parallel to `post_handling_instances`):

```python
def serialize_task(
    task: Task,
    post_handling_instances: list[TaskPostHandling] | None = None,
    customer_coordination_instances: list[TaskCustomerCoordination] | None = None,
) -> dict:
    return {
        # ... existing fields unchanged ...
        "post_handling": (
            [serialize_task_post_handling(ph) for ph in post_handling_instances]
            if post_handling_instances is not None
            else None
        ),
        "customer_coordination": (
            [serialize_task_customer_coordination(tcc) for tcc in customer_coordination_instances]
            if customer_coordination_instances is not None
            else None
        ),
    }
```

All existing callers that do not pass `customer_coordination_instances` will default to `None` and get `"customer_coordination": null` in the response — backward compatible.

---

### Step 10 — Extend `list_tasks` query service

**File:** `app/beyo_manager/services/queries/tasks/tasks.py`

Add import:

```python
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.domain.tasks.serializers import serialize_task_customer_coordination
```

In `list_tasks`:

**Parse param** (alongside the existing `post_handling_states` parse):

```python
customer_coordination_states = _split_csv(ctx.query_params.get("customer_coordination_states"))
```

**Add subquery filter** (after the `post_handling_states` block, before the `q` block):

```python
if customer_coordination_states:
    cc_subq = (
        select(TaskCustomerCoordination.task_id)
        .where(
            TaskCustomerCoordination.workspace_id == ctx.workspace_id,
            TaskCustomerCoordination.state.in_(customer_coordination_states),
        )
        .distinct()
    )
    stmt = stmt.where(Task.client_id.in_(cc_subq))
```

**Add batch-load block** (after the `post_handling_map` block):

```python
customer_coordination_map: dict[str, list[TaskCustomerCoordination]] = {}
if customer_coordination_states:
    cc_result = await ctx.session.execute(
        select(TaskCustomerCoordination)
        .where(
            TaskCustomerCoordination.workspace_id == ctx.workspace_id,
            TaskCustomerCoordination.task_id.in_(page_ids),
        )
        .order_by(TaskCustomerCoordination.created_at.asc())
    )
    for cc in cc_result.scalars().all():
        customer_coordination_map.setdefault(cc.task_id, []).append(cc)
```

**Pass to `serialize_task`** in the `items_payload` loop:

```python
items_payload.append(
    {
        "task": serialize_task(
            task,
            post_handling_instances=post_handling_map.get(task_id) if post_handling_states else None,
            customer_coordination_instances=customer_coordination_map.get(task_id) if customer_coordination_states else None,
        ),
        "primary_item": serialize_item(primary_item),
        "item_images": item_images_map.get(primary_item_id, []),
    }
)
```

---

### Step 11 — Extend `route_list_tasks` router

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

Add `customer_coordination_states` query param to `route_list_tasks`:

```python
customer_coordination_states: str | None = Query(None),
```

Forward it in the `query_params` dict:

```python
"customer_coordination_states": customer_coordination_states,
```

---

### Step 12 — Create `complete_task_customer_coordination` command

**File (new):** `app/beyo_manager/services/commands/task_customer_coordination/complete_task_customer_coordination.py`

Mirrors `complete_task_post_handling` exactly, adapted for `TaskCustomerCoordination`:

```python
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


class CompleteTaskCustomerCoordinationRequest(BaseModel):
    task_id: str | None = None
    coordination_id: str | None = None


def parse_complete_task_customer_coordination_request(data: dict) -> CompleteTaskCustomerCoordinationRequest:
    try:
        return CompleteTaskCustomerCoordinationRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def complete_task_customer_coordination(ctx: ServiceContext) -> dict:
    request = parse_complete_task_customer_coordination_request(ctx.incoming_data)
    if request.coordination_id is None and request.task_id is None:
        raise ValidationError("Either coordination_id or task_id is required.")

    async with maybe_begin(ctx.session):
        if request.coordination_id is not None:
            filters = [
                TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                TaskCustomerCoordination.client_id == request.coordination_id,
            ]
            if request.task_id:
                filters.append(TaskCustomerCoordination.task_id == request.task_id)
            result = await ctx.session.execute(select(TaskCustomerCoordination).where(*filters))
            instance = result.scalar_one_or_none()
        else:
            result = await ctx.session.execute(
                select(TaskCustomerCoordination).where(
                    TaskCustomerCoordination.workspace_id == ctx.workspace_id,
                    TaskCustomerCoordination.task_id == request.task_id,
                    TaskCustomerCoordination.state != TaskCustomerCoordinationStateEnum.COMPLETED,
                )
            )
            instance = result.scalar_one_or_none()

        if instance is None:
            raise NotFound("Active customer coordination instance not found.")
        if instance.state == TaskCustomerCoordinationStateEnum.COMPLETED:
            raise ValidationError("Customer coordination instance is already completed.")

        old_state = instance.state
        now = datetime.now(timezone.utc)
        instance.state = TaskCustomerCoordinationStateEnum.COMPLETED
        instance.updated_at = now

        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
            entity_client_id=instance.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=f"Customer coordination marked completed (from {old_state.value})",
            field_name="state",
            from_value={"state": old_state.value},
            to_value={"state": TaskCustomerCoordinationStateEnum.COMPLETED.value},
            created_by_id=ctx.user_id,
            username_snapshot=ctx.identity.get("username"),
        )

    await event_bus.dispatch([
        build_workspace_event(instance, "task_customer_coordination:completed", workspace_id=ctx.workspace_id),
    ])
    return {"client_id": instance.client_id}
```

No `force` flag — unlike post-handling, any non-completed record can be completed directly.

---

### Step 13 — Create `count_task_customer_coordination_states` query

**File (new):** `app/beyo_manager/services/queries/tasks/count_task_customer_coordination_states.py`

Mirrors `count_task_post_handling_states`:

```python
from sqlalchemy import func, select

from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.context import ServiceContext


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def count_task_customer_coordination_states(ctx: ServiceContext) -> dict:
    requested_states = _split_csv(ctx.query_params.get("customer_coordination_states"))

    stmt = (
        select(TaskCustomerCoordination.state, func.count(TaskCustomerCoordination.client_id))
        .where(TaskCustomerCoordination.workspace_id == ctx.workspace_id)
        .group_by(TaskCustomerCoordination.state)
    )

    if requested_states:
        stmt = stmt.where(TaskCustomerCoordination.state.in_(requested_states))

    rows = (await ctx.session.execute(stmt)).all()
    raw = {state.value: count for state, count in rows}

    if requested_states:
        return {state: raw.get(state, 0) for state in requested_states}

    return {state.value: raw.get(state.value, 0) for state in TaskCustomerCoordinationStateEnum}
```

---

### Step 14 — Add router endpoints for complete + count

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

Add imports at the top:

```python
from beyo_manager.services.commands.task_customer_coordination.complete_task_customer_coordination import (
    complete_task_customer_coordination,
)
from beyo_manager.services.queries.tasks.count_task_customer_coordination_states import (
    count_task_customer_coordination_states,
)
```

Add request body model (in the body models block):

```python
class _CompleteTaskCustomerCoordinationBody(BaseModel):
    coordination_id: str | None = None
```

Add count route (alongside `route_count_task_post_handling_states` — must appear before `/{task_id}` catch-all routes):

```python
@router.get("/customer-coordination/counts")
async def route_count_task_customer_coordination_states(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    customer_coordination_states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"customer_coordination_states": customer_coordination_states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(count_task_customer_coordination_states, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Add complete route (alongside `route_complete_task_post_handling`):

```python
@router.post("/{task_id}/customer-coordination/complete")
async def route_complete_task_customer_coordination(
    task_id: str,
    body: _CompleteTaskCustomerCoordinationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(complete_task_customer_coordination, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

## Risks and mitigations

- Risk: `route_count_task_customer_coordination_states` path (`/customer-coordination/counts`) is a static segment that must be registered before the `/{task_id}` dynamic path group.
  Mitigation: Place it before any `/{task_id}` route in the router file, following the same placement as `route_count_task_post_handling_states`.

- Risk: `_create_customer_coordination_in_session` is called inside `maybe_evaluate_task_ready` which is itself inside a parent session scope — the inner `flush()` must not commit.
  Mitigation: `flush()` not `commit()` — same pattern as `_create_post_handling_in_session`. No nested `maybe_begin` used here.

- Risk: `HistoryRecordEntityTypeEnum` uses `StrEnum` — the new value is treated as a plain Python string by SQLAlchemy; no migration is needed but the value must exactly match the string stored.
  Mitigation: Use the enum member everywhere; never hardcode the string.

- Risk: Two in-session helpers are now called sequentially in `maybe_evaluate_task_ready`. If the second fails after the first has flushed, the transaction will roll back both.
  Mitigation: This is correct behavior — both records are created atomically within the same transaction.

## Validation plan

- `alembic upgrade head`: migration applies cleanly with no errors.
- `POST /tasks` → step through until task reaches `ready`: verify both a `task_post_handlings` row and a `task_customer_coordinations` row are created with state `pending`.
- `GET /tasks?customer_coordination_states=pending`: returns tasks with a `customer_coordination` array; tasks not matching return in the list only if not filtered by the param (when param omitted, `customer_coordination: null`).
- `POST /tasks/{task_id}/customer-coordination/complete`: transitions state to `completed`, returns `{"client_id": "tcc_..."}`.
- `GET /tasks/customer-coordination/counts`: returns `{"pending": N, "coordinating": N, "completed": N}`.
- Second call to `POST /tasks/{task_id}/customer-coordination/complete` on same task returns 404 (no active record).
- Re-transition task to ready when existing `COMPLETED` record exists: a new `task_customer_coordinations` record is created.
- Re-transition task to ready when existing `PENDING` record exists: no new record is created.

## Review log

_(empty — awaiting first review)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
