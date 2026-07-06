# PLAN_fail_task_customer_coordination_20260705

## Metadata

- Plan ID: `PLAN_fail_task_customer_coordination_20260705`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-05T00:00:00Z`
- Last updated at (UTC): `2026-07-05T07:44:13Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Add a `failed` state to `TaskCustomerCoordination`, a batchable service to transition coordination records to that state, a router endpoint that exposes it, and append the new endpoint to the existing frontend handoff.
- Business/user intent: Allow operators to explicitly mark a customer coordination attempt as failed (e.g. customer unreachable, email bounced, coordination abandoned), distinguishing these records from ones that are still pending or actively coordinating.
- Non-goals: Automatic failure detection, retries, or cascading task-state changes triggered by a failed coordination.

## Scope

- In scope:
  - Add `FAILED = "failed"` to `TaskCustomerCoordinationStateEnum`
  - Alembic migration to extend the `task_customer_coordination_state_enum` Postgres enum
  - New command service `fail_task_customer_coordination.py` (batchable by `coordination_ids` list)
  - New router endpoint `POST /api/v1/tasks/{task_id}/customer-coordination/fail`
  - Append new endpoint documentation to the existing handoff file
- Out of scope:
  - Any changes to the email batch send logic
  - Counts query — `count_task_customer_coordination_states` already groups dynamically by enum value, so `failed` will appear automatically once the enum value exists
  - Thread inbox query — no filter change required

## Clarifications required

_(none — all behaviour can be derived from the existing `complete_task_customer_coordination` pattern)_

## Acceptance criteria

1. `TaskCustomerCoordinationStateEnum` contains `FAILED = "failed"`.
2. Alembic migration runs cleanly (`ALTER TYPE … ADD VALUE IF NOT EXISTS 'failed'`).
3. Calling `POST /api/v1/tasks/{task_id}/customer-coordination/fail` with zero or more `coordination_ids` marks each matching record as `failed`, writes a history record, and dispatches a workspace event.
4. If `coordination_ids` is omitted or empty, the single non-terminal coordination record for `task_id` is marked failed (same fallback as `complete`).
5. Attempting to fail an already-`failed` or `completed` record raises `ValidationError`.
6. Handoff document updated with the new endpoint shape.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/06_commands.md`: command shape, `maybe_begin`, `_create_history_record_in_session`, event dispatch
- `backend/docs/architecture/09_routers.md`: router handler wiring, `ServiceContext`, `run_service`, `build_ok`/`build_err`
- `backend/docs/architecture/46_serialization.md`: response shape conventions

### Local extensions loaded

_(none required)_

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead
- **What exists** → reading is legitimate

Permitted relational reads for this plan:
- `app/beyo_manager/services/commands/task_customer_coordination/complete_task_customer_coordination.py` — exact field names, query shape, guard ordering, event name, history description format
- `app/beyo_manager/routers/api_v1/tasks.py` lines 524–539 — existing `complete` endpoint wiring to match style exactly
- `app/beyo_manager/domain/tasks/enums.py` — confirm current enum members before adding `FAILED`
- `app/migrations/versions/dd861a418d9d_add_send_delivery_fields_to_email_.py` — migration pattern for `ALTER TYPE … ADD VALUE IF NOT EXISTS`

Prohibited:
- Reading other command files to understand `session.add` / flush shape → `06_commands.md`
- Reading other routers to understand handler wiring → `09_routers.md`

### Skill selection

- Primary skill: `backend/docs/architecture/06_commands.md`
- Router trigger terms: `customer-coordination`, `fail`
- Excluded alternatives: none

## Implementation plan

### Step 1 — Extend the enum

File: `app/beyo_manager/domain/tasks/enums.py`

Add `FAILED = "failed"` as the last member of `TaskCustomerCoordinationStateEnum`:

```python
class TaskCustomerCoordinationStateEnum(enum.Enum):
    PENDING = "pending"
    COORDINATING = "coordinating"
    COMPLETED = "completed"
    FAILED = "failed"          # ← add this line
```

### Step 2 — Alembic migration

Create a new migration file at `app/migrations/versions/<hex>_add_failed_to_task_customer_coordination_state_enum.py`.

- `down_revision = '8485202cd902'` (current head as of 2026-07-05)
- Generate a fresh 12-char hex for the `revision` field (do **not** reuse any existing revision ID)

```python
def upgrade() -> None:
    op.execute(
        "ALTER TYPE task_customer_coordination_state_enum ADD VALUE IF NOT EXISTS 'failed'"
    )

def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'failed' remains in task_customer_coordination_state_enum on downgrade.
    pass
```

No imports beyond `from alembic import op` are needed.

### Step 3 — Service: `fail_task_customer_coordination.py`

Create `app/beyo_manager/services/commands/task_customer_coordination/fail_task_customer_coordination.py`.

Mirror `complete_task_customer_coordination.py` with the following differences:

**Request model**

```python
class FailTaskCustomerCoordinationRequest(BaseModel):
    task_id: str | None = None
    coordination_ids: list[str] | None = None   # batch: zero or more IDs
```

**Lookup logic**

- If `coordination_ids` is a non-empty list: query all records in that list scoped to `workspace_id` (and optionally `task_id` if provided). Iterate over each.
- If `coordination_ids` is `None` or empty: fall back to the single active record for `task_id` that is not yet `COMPLETED` or `FAILED` (same query shape as `complete`).
- Either `task_id` or a non-empty `coordination_ids` must be present — raise `ValidationError` otherwise.

**Guard per instance**

```python
if instance.state in (
    TaskCustomerCoordinationStateEnum.FAILED,
    TaskCustomerCoordinationStateEnum.COMPLETED,
):
    raise ValidationError(
        f"Customer coordination {instance.client_id} is already {instance.state.value}."
    )
```

**State transition per instance**

```python
old_state = instance.state
instance.state = TaskCustomerCoordinationStateEnum.FAILED
instance.updated_at = now
```

**History record per instance** — use `_create_history_record_in_session` with:

```python
description=f"Customer coordination marked failed (from {old_state.value})"
from_value={"state": old_state.value}
to_value={"state": TaskCustomerCoordinationStateEnum.FAILED.value}
```

**Event dispatch** — after the transaction, dispatch one event per instance:

```python
await event_bus.dispatch([
    build_workspace_event(instance, "task_customer_coordination:failed", workspace_id=ctx.workspace_id)
    for instance in instances
])
```

**Return value**

```python
return {"failed_ids": [instance.client_id for instance in instances]}
```

All instances are processed inside a single `async with maybe_begin(ctx.session)` block.

### Step 4 — Router endpoint

File: `app/beyo_manager/routers/api_v1/tasks.py`

**1. Import the new service** — add alongside the existing `complete_task_customer_coordination` import:

```python
from beyo_manager.services.commands.task_customer_coordination.fail_task_customer_coordination import (
    fail_task_customer_coordination,
)
```

**2. Add request body model** — add alongside `_CompleteTaskCustomerCoordinationBody`:

```python
class _FailTaskCustomerCoordinationBody(BaseModel):
    coordination_ids: list[str] | None = None
```

**3. Add the endpoint** — place immediately after the `route_complete_task_customer_coordination` endpoint (after line 539):

```python
@router.post("/{task_id}/customer-coordination/fail")
async def route_fail_task_customer_coordination(
    task_id: str,
    body: _FailTaskCustomerCoordinationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(fail_task_customer_coordination, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

### Step 5 — Update the frontend handoff

File: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md`

Append a new section `### 6. POST /api/v1/tasks/{task_id}/customer-coordination/fail` before the `## Validation notes` section, documenting:
- Purpose
- Request body (`coordination_ids: string[] | null`)
- Success response `200`: `{ "failed_ids": ["tcc_abc", ...] }`
- Guard behaviour (already-failed or completed raises 400)
- Error responses table (400, 401, 403)
- Update the `## Backend delivery context` section to list this new endpoint under "API or contract changes"
- Update the valid state values note for `customer_coordination_states` throughout the document to include `failed`

## Risks and mitigations

- Risk: Postgres `ALTER TYPE` is transactional in Postgres 12+ but the new value is not visible inside the same transaction on older versions.
  Mitigation: The migration uses `ADD VALUE IF NOT EXISTS` (idempotent). The value is immediately usable by the application after migration commit; no further action needed.

- Risk: `count_task_customer_coordination_states` query may rely on a static list of enum values and need updating.
  Mitigation: Before starting Step 3, read `app/beyo_manager/services/queries/tasks/count_task_customer_coordination_states.py`. If it uses a hard-coded state list, add `FAILED` to it. If it groups dynamically, no change is needed.

## Validation plan

- `grep -n "FAILED" app/beyo_manager/domain/tasks/enums.py` → should return `FAILED = "failed"`
- `python -c "from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum; print(list(TaskCustomerCoordinationStateEnum))"` → `FAILED` in list
- `python -c "from beyo_manager.services.commands.task_customer_coordination.fail_task_customer_coordination import fail_task_customer_coordination"` → no import error
- `python -c "from beyo_manager.routers.api_v1.tasks import router"` → no import error
- Alembic dry-run: `alembic upgrade head --sql` → contains `ALTER TYPE task_customer_coordination_state_enum ADD VALUE IF NOT EXISTS 'failed'`

## Review log

- `2026-07-05T07:44:13Z` — Implemented enum, migration, fail command, router endpoint, and frontend handoff updates. Validation completed with compile and import checks.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `david`
