# PLAN_task_crud_queries_router_20260518

## Metadata

- Plan ID: `PLAN_task_crud_queries_router_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-1`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement the core task lifecycle commands (CMD-1 through CMD-8), both task queries (QUERY-1 compressed list, QUERY-2 full detail), and the `/api/v1/tasks` router. After this plan, tasks can be created, updated, resolved, cancelled, failed, soft-deleted, and queried. Items can be added/removed from tasks.
- **Business/user intent:** Sellers, managers, and admins can create work orders. Managers can update, assign, resolve, fail, or cancel them. The task list powers the main operational dashboard.
- **Non-goals:**
  - Notes in task creation payload — requires `_create_task_note_in_session` from Plan 2 (task notes). CMD-1 is implemented here WITHOUT notes-in-payload; Plan 2 adds that capability as an amendment to CMD-1.
  - Task step commands — covered in Plans 3, 4, 5.
  - Analytics — covered in Plan 6.
  - No new models or migrations — all tables exist.

---

## Prerequisite

**Plan 0 (`PLAN_find_or_create_item_20260518`) must be completed and its bash test must pass before implementing CMD-1 in this plan.** CMD-1 calls `find_or_create_item` as a subordinate command.

---

## Scope

- **In scope:**
  - New directory: `services/commands/tasks/` + `services/commands/tasks/requests/`
  - New directory: `services/queries/tasks/`
  - 8 new command files: `create_task.py`, `update_task.py`, `delete_task.py`, `resolve_task.py`, `cancel_task.py`, `fail_task.py`, `add_item_to_task.py`, `remove_item_from_task.py`
  - Request models: `services/commands/tasks/requests/__init__.py`
  - Query file: `services/queries/tasks/tasks.py`
  - New router: `routers/api_v1/tasks.py`
  - Router registration in `routers/api_v1/__init__.py`
- **Out of scope:** Notes-in-payload for CMD-1 (Plan 2), task step routes (Plans 3-5), analytics (Plan 6).
- **Assumptions:** `find_or_create_item` and `find_or_create_customer` both exist and pass their bash tests. All task, task_item, item tables exist. Working section table exists (`working_sections`).

---

## Clarifications required

_None. All design decisions are locked in the intention plan._

---

## Acceptance criteria

1. `PUT /api/v1/tasks` creates a task and returns `{client_id, task_scalar_id}`. `task_scalar_id` is a positive integer unique within the workspace.
2. Seller role creates tasks with `state = pending` always, regardless of payload. Manager/admin may receive `working_section_ids` in payload to create an already-assigned task.
3. CMD-1 with customer data: calls `find_or_create_customer` in subordinate mode; populates `customer_id` + all five contact snapshot fields from the customer record.
4. CMD-1 with item data: calls `find_or_create_item` in subordinate mode; creates `TaskItem` row with `role = primary`.
5. CMD-1 with item issues in payload: calls `_create_item_issue_in_session` for each issue, within the same transaction.
6. CMD-1 with item upholstery in payload: calls `_create_item_upholstery_in_session`, within the same transaction.
7. Two concurrent CMD-1 calls in the same workspace receive different `task_scalar_id` values (no collision). The `pg_advisory_xact_lock` approach prevents races.
8. `PATCH /api/v1/tasks/{task_id}` updates only the fields present in the request body (`model_fields_set` semantics). Omitted fields are not overwritten.
9. `DELETE /api/v1/tasks/{task_id}` soft-deletes: `is_deleted = True`, `deleted_at = now()`.
10. `POST /api/v1/tasks/{task_id}/resolve` sets `state = resolved`, `closed_at = now()`. Valid from any non-terminal state.
11. `POST /api/v1/tasks/{task_id}/cancel` sets `state = cancelled`, `closed_at = now()`. Guards against cancelling an already-terminal task.
12. `POST /api/v1/tasks/{task_id}/fail` sets `state = failed`, `closed_at = now()`. Guards against failing an already-terminal task.
13. `POST /api/v1/tasks/{task_id}/items` inserts a `TaskItem` row. Enforces: one active PRIMARY per task (returns `ConflictError` if a PRIMARY already exists and a new PRIMARY is requested).
14. `DELETE /api/v1/tasks/{task_id}/items/{item_id}` sets `removed_at + removed_by_id` on the `TaskItem` row.
15. `GET /api/v1/tasks` returns compressed paginated list. All filters (working_section, state, step_state, step_readiness, priority, task_type, return_source, date ranges, upholstery requirement state, deleted_at) narrow the result correctly. Default ordering is `ready_by_at ASC NULLS LAST`, then `priority DESC` (urgent first), then `created_at ASC`.
16. `GET /api/v1/tasks/{task_id}` returns full uncompressed payload: all task fields + item + item_upholstery + requirements + task_steps.
17. `q` string filter on list endpoint searches: `title`, `additional_details` (text cast), `primary_phone_number`, `secondary_phone_number`, `primary_email`, `secondary_email`, `item.article_number`, `item.sku`, `item.designer`, `item.item_position`, `item.item_category_snapshot`, `item.item_major_category_snapshot`, `item_upholstery.name`, `item_upholstery.code` — all via `ILIKE`.

---

## Contracts and skills

### Contracts loaded

Read these contracts **in full** before writing any code.

- `backend/architecture/01_architecture.md`: overall structure
- `backend/architecture/04_context.md`: `ServiceContext` access patterns
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound`, `ConflictError` — exact import paths
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, subordinate mode, session call safety rules, subordinate-command event rule
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset pagination pattern, query structure
- `backend/architecture/09_routers.md`: router handler skeleton, `build_ok`, `build_err`, `model_dump(exclude_unset=True)`
- `backend/architecture/21_naming_conventions.md`: naming

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/tasks/task.py` | All column names, enums imported |
| `models/tables/tasks/task_item.py` | Columns, `removed_at` pattern |
| `models/tables/tasks/README.md` | State machine rules, partial index names, task type enum naming |
| `models/tables/items/item.py` | Column names for JOIN queries |
| `models/tables/items/item_upholstery.py` | Column names |
| `models/tables/items/item_upholstery_requirement.py` | Column names + state enum |
| `models/tables/tasks/task_step.py` | Column names for filters |
| `services/commands/customers/find_or_create_customer.py` | Exact subordinate call pattern |
| `services/commands/items/find_or_create_item.py` | Exact subordinate call pattern + `was_created` key |
| `services/commands/items/create_item_issue.py` | `_create_item_issue_in_session` signature |
| `services/commands/items/create_item_upholstery.py` | `_create_item_upholstery_in_session` signature |
| `services/queries/customers/customers.py` | 2-step query pattern (IDs then batch load) |
| `services/queries/utils/string_filter.py` | `apply_string_filter` signature |
| `domain/tasks/enums.py` | All enum class names and values |
| `domain/task_steps/enums.py` | `TaskStepStateEnum`, `TaskStepReadinessStatusEnum` |

### Prohibited pattern reads

- Do NOT read other commands to learn `maybe_begin` or error shape — contracts cover this.
- Do NOT read other routers to learn handler wiring — `09_routers.md` covers this.

---

## Implementation plan

Execute steps in order. Do not skip ahead.

### Step 1 — Create directory structure

Create the following empty `__init__.py` files to establish the module hierarchy:
- `services/commands/tasks/__init__.py`
- `services/commands/tasks/requests/__init__.py`
- `services/commands/task_steps/__init__.py`
- `services/commands/task_steps/requests/__init__.py`
- `services/queries/tasks/__init__.py`

### Step 2 — Add request models: `services/commands/tasks/requests/__init__.py`

This file contains all Pydantic request models for task commands. Follow the exact parse-function pattern in `services/commands/customers/requests/__init__.py` (top-level `PydanticValidationError` import, shared `_raise_validation_error`, one parse function per request model).

**Models to include:**

```
CreateTaskRequest:
  task_type: TaskTypeEnum  (required)
  title: str | None
  summary: str | None
  priority: TaskPriorityEnum = NORMAL
  ready_by_at: datetime | None
  scheduled_start_at: datetime | None
  scheduled_end_at: datetime | None
  return_source: TaskReturnSourceEnum | None
  item_location: TaskItemLocationEnum | None
  return_method: TaskReturnMethodEnum | None
  fulfillment_method: TaskFulfillmentMethodEnum | None
  additional_details: dict | None
  # Customer snapshot fields (populate from customer lookup or override)
  customer_id: str | None  # if provided, skip find_or_create_customer; link directly
  customer_display_name: str | None
  primary_phone_number: str | None
  secondary_phone_number: str | None
  primary_email: str | None
  secondary_email: str | None
  customer_address: dict | None
  # Item (triggers find_or_create_item)
  item: FindOrCreateItemInput | None
  # Item issues and upholstery (created in same transaction after item is linked)
  item_issues: list[ItemIssueInput] | None
  item_upholstery: ItemUpholsteryInput | None

FindOrCreateItemInput: mirrors FindOrCreateItemRequest fields (article_number, sku, all updatable item fields)
ItemIssueInput: mirrors ItemIssueCreateInput from items requests
ItemUpholsteryInput: mirrors ItemUpholsteryCreateInput from items requests

UpdateTaskRequest:
  client_id: str
  title: str | None  (model_fields_set semantics — only update if present)
  summary: str | None
  priority: TaskPriorityEnum | None
  ready_by_at: datetime | None
  scheduled_start_at: datetime | None
  scheduled_end_at: datetime | None
  return_source: TaskReturnSourceEnum | None
  item_location: TaskItemLocationEnum | None
  return_method: TaskReturnMethodEnum | None
  fulfillment_method: TaskFulfillmentMethodEnum | None
  additional_details: dict | None

TerminalTaskRequest:
  client_id: str   (used by resolve, cancel, fail)

AddItemToTaskRequest:
  task_id: str
  item_id: str
  role: TaskItemRoleEnum

RemoveItemFromTaskRequest:
  task_id: str
  item_id: str
```

**Parse functions:** one per model, following the standard pattern: `PydanticValidationError` catch → extract first error → `raise ValidationError(f"{field}: {msg}")`.

### Step 3 — CMD-1: `services/commands/tasks/create_task.py`

**Imports needed:**
```python
from datetime import datetime, timezone
from dataclasses import asdict
from sqlalchemy import func, select, text
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum, TaskItemRoleEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.customers.find_or_create_customer import find_or_create_customer
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.items.create_item_issue import _create_item_issue_in_session
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.items.requests import CreateItemIssueRequest, CreateItemUpholsteryRequest
from beyo_manager.services.commands.tasks.requests import parse_create_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
```

**Role guard:**
```python
SELLER_ROLES = {"seller"}  # import from roles module
```
If `ctx.role` is in `SELLER_ROLES`, override `state = TaskStateEnum.PENDING` regardless of payload.

**`task_scalar_id` generation — CRITICAL:**
Inside the `async with maybe_begin(ctx.session):` block, before inserting Task:
```python
# Acquire advisory lock scoped to workspace to prevent concurrent scalar_id collisions
await ctx.session.execute(
    text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
    {"workspace_id": ctx.workspace_id},
)
scalar_id_result = await ctx.session.execute(
    select(func.coalesce(func.max(Task.task_scalar_id), 0) + 1).where(
        Task.workspace_id == ctx.workspace_id
    )
)
task_scalar_id = scalar_id_result.scalar_one()
```
This lock is transaction-scoped — it releases on commit or rollback automatically.

**Customer linking:**
If `request.customer_id` is directly provided: set `task.customer_id = request.customer_id` and copy contact snapshot fields from the request. If customer data is provided without `customer_id`: call `find_or_create_customer` in subordinate mode by building a sub-`ServiceContext` with the customer data. After the call, fetch the customer object to populate contact snapshot fields (`primary_phone_number`, `secondary_phone_number`, `primary_email`, `secondary_email`, `address`). Fill snapshot fields from request first; fall back to customer record for missing values.

**Item linking:**
If `request.item` is provided: call `find_or_create_item` in subordinate mode. Then create `TaskItem(workspace_id, task_id=task.client_id, item_id=item_result["client_id"], role=PRIMARY, created_by_id=ctx.user_id)`. Flush after adding.

**Item issues:**
After item is linked, if `request.item_issues` is not empty: for each issue, call `_create_item_issue_in_session(session=ctx.session, workspace_id=ctx.workspace_id, item_id=item_id, issue_data=..., user_id=ctx.user_id)`.

**Item upholstery:**
If `request.item_upholstery` is not None: validate `source == INTERNAL → upholstery_id required`; call `_create_item_upholstery_in_session`.

**Notes in payload:** NOT implemented in this plan. `create_task` receives and ignores a `notes` field if present. Plan 2 amends this.

**Return:**
```python
return {"client_id": task.client_id, "task_scalar_id": task.task_scalar_id}
```

### Step 4 — CMD-2: `services/commands/tasks/update_task.py`

`_DIRECT_FIELDS` set (all nullable — all use `model_fields_set` semantics):
```python
_DIRECT_FIELDS = {
    "title", "summary", "priority", "ready_by_at",
    "scheduled_start_at", "scheduled_end_at", "return_source",
    "item_location", "return_method", "fulfillment_method", "additional_details",
}
```

Flow:
1. Parse request; look up task by `client_id` (workspace_id + is_deleted=False) → 404 if not found.
2. Guard: cannot update a terminal task (`state in {RESOLVED, FAILED, CANCELLED}`).
3. Loop `_DIRECT_FIELDS` via `model_fields_set`.
4. `CheckConstraint` invariant: if both `scheduled_start_at` and `scheduled_end_at` are set after update, `end >= start`. Raise `ValidationError` if violated.
5. Set `updated_at = now()`, `updated_by_id = ctx.user_id`.
6. Return `{"client_id": task.client_id}`.

### Step 5 — CMD-3: `services/commands/tasks/delete_task.py`

Flow: look up task → 404 if not found; raise `ConflictError` if already deleted; set `is_deleted = True`, `deleted_at = now()`. Return `{"client_id": task.client_id}`.

### Step 6 — CMD-4/5/6: terminal state commands

**`resolve_task.py` (CMD-4):**
- Allowed from: any non-terminal state (PENDING, ASSIGNED, WORKING, STALLED, READY).
- Guard: raise `ConflictError("Task is already in a terminal state.")` if `state in TERMINAL_STATES`.
- Set `state = RESOLVED`, `closed_at = now()`, `updated_at = now()`, `updated_by_id`.
- Return `{"client_id": task.client_id}`.

**`cancel_task.py` (CMD-5):**
- Same terminal guard.
- Set `state = CANCELLED`, `closed_at`, `updated_at`, `updated_by_id`.

**`fail_task.py` (CMD-6):**
- Same terminal guard.
- Set `state = FAILED`, `closed_at`, `updated_at`, `updated_by_id`.

**`TERMINAL_STATES` constant:** define as a module-level frozenset in a shared location (e.g., `domain/tasks/enums.py` or inline in each command — preference: inline to avoid coupling, it is a small set).
```python
_TERMINAL_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})
```

### Step 7 — CMD-7: `services/commands/tasks/add_item_to_task.py`

Flow:
1. Parse request (task_id, item_id, role).
2. Look up task by `task_id` → 404 if not found / deleted.
3. Look up item by `item_id` → 404 if not found / deleted.
4. If `role == PRIMARY`: check for existing active PRIMARY → `select(TaskItem).where(task_id, role=PRIMARY, removed_at IS NULL)`. If found: raise `ConflictError("Task already has an active primary item.")`.
5. Check no active row for (task_id, item_id): `select(TaskItem).where(task_id, item_id, removed_at IS NULL)`. If found: raise `ConflictError("Item already active on this task.")`.
6. Create `TaskItem(workspace_id, task_id, item_id, role, created_by_id=ctx.user_id)`.
7. Flush. Return `{"client_id": task_item.client_id}`.

### Step 8 — CMD-8: `services/commands/tasks/remove_item_from_task.py`

Flow:
1. Parse request (task_id, item_id).
2. Find active `TaskItem` where `task_id + item_id + removed_at IS NULL` → 404 if not found.
3. Set `removed_at = datetime.now(timezone.utc)`, `removed_by_id = ctx.user_id`.
4. Return `{"client_id": task_item.client_id}`.

### Step 9 — QUERY-1 + QUERY-2: `services/queries/tasks/tasks.py`

**QUERY-1 — `list_tasks` — 2-step pattern:**

Step A: Build the task ID query with all filters and pagination. Query only `Task.client_id` (scalar) to keep the filter pass lean.

```
stmt = select(Task.client_id).where(
    Task.workspace_id == ctx.workspace_id,
)
```

Apply `deleted_at` filter (default: `is_deleted = False`; if `deleted_at=true` param: `is_deleted = True`).

Apply direct task filters via `.where()`:
- `working_section_ids`: `Task.client_id.in_(select(TaskStep.task_id).where(TaskStep.working_section_id.in_(ids), TaskStep.is_deleted.is_(False)))` — EXISTS/IN subquery
- `task_states`: `Task.state.in_(states)`
- `task_step_states`: EXISTS subquery on `task_steps`
- `step_readiness_statuses`: EXISTS subquery on `task_steps`
- `priorities`: `Task.priority.in_(priorities)`
- `task_types`: `Task.task_type.in_(types)`
- `return_sources`: `Task.return_source.in_(sources)`
- `ready_from_date`: `Task.ready_by_at >= ready_from_date`
- `ready_to_date`: `Task.ready_by_at <= ready_to_date`
- `scheduled_from_date`: `Task.scheduled_start_at >= scheduled_from_date`
- `scheduled_to_date`: `Task.scheduled_end_at <= scheduled_to_date`
- `upholstery_requirement_states`: EXISTS subquery through `task_items → items → item_upholsteries → item_upholstery_requirements`

Apply `q` string filter: JOIN `Task` with `Item` (via `TaskItem`) and `ItemUpholstery` to reach the searchable columns. Apply `ILIKE` across: `Task.title`, `Task.primary_phone_number`, `Task.secondary_phone_number`, `Task.primary_email`, `Task.secondary_email`, `Item.article_number`, `Item.sku`, `Item.designer`, `Item.item_position`, `Item.item_category_snapshot`, `Item.item_major_category_snapshot`, `ItemUpholstery.name`, `ItemUpholstery.code`. Use `or_` on all. Apply `.distinct()` when JOIN is active.

Apply `order_by`: parse `order_by` query param (e.g., `"ready_by_at:asc,priority:desc"`); map field names to `Task` columns; default ordering: `Task.ready_by_at.asc().nulls_last(), Task.priority.desc(), Task.created_at.asc()`. Priority ordering: `urgent=4, high=3, normal=2, low=1` — express as `case({URGENT: 4, HIGH: 3, NORMAL: 2, LOW: 1}, value=Task.priority, else_=0).desc()` for priority desc. Or simpler: map string values to their sort-order equivalents.

Apply `.offset(offset).limit(limit + 1)` and determine `has_more`.

Step B: Batch-load related entities for the returned task IDs.
```python
task_ids = [row for row in page_task_ids]  # the page of client_ids

tasks = await load tasks by ids (select(Task).where(Task.client_id.in_(task_ids)))
task_items = await load active task_items (removed_at IS NULL)
item_ids = [ti.item_id for ti in task_items]
items = await load items by ids
item_upholsteries = await load item_upholsteries by item_ids (is_deleted=False, removed_at IS NULL if applicable)
requirements = await load requirements by item_upholstery_ids
task_steps = await load task_steps by task_ids (is_deleted=False)
```

Step C: Assemble and return the compressed shape per the intention plan shape. Sort tasks in the same order as the ID page.

**`_ALLOWED_Q_COLUMNS` dict:** define at module level mapping field name strings to SQLAlchemy column attributes (for `apply_string_filter`). Note that some columns are on `Item` and `ItemUpholstery` — the q filter query needs to JOIN these tables when `q` is active.

**QUERY-2 — `get_task`:**

1. Load `Task` by `client_id` + `workspace_id` (respect deleted_at: if `is_deleted=True`, 404 unless `include_deleted` param is set).
2. Load active `TaskItem` rows; load the PRIMARY item.
3. Load `ItemUpholstery` for that item (if any).
4. Load `ItemUpholsteryRequirement` rows.
5. Load all `TaskStep` rows for the task (non-deleted).
6. Return full payload — no compression. All task columns, all item columns, all step columns (state, readiness_status, total_dependencies, completed_dependencies, assigned_worker_id, assigned_worker_display_name_snapshot, working_section_id, working_section_name_snapshot, sequence_order, created_at, closed_at).

### Step 10 — Router: `routers/api_v1/tasks.py`

**Route layout — exact order matters:**

```
PUT    ""                                → route_create_task        (ADMIN, MANAGER, SELLER)
GET    ""                                → route_list_tasks         (ADMIN, MANAGER, WORKER, SELLER)
GET    "/{task_id}"                      → route_get_task           (ADMIN, MANAGER, WORKER, SELLER)
PATCH  "/{task_id}"                      → route_update_task        (ADMIN, MANAGER, SELLER)
DELETE "/{task_id}"                      → route_delete_task        (ADMIN, MANAGER)
POST   "/{task_id}/resolve"              → route_resolve_task       (ADMIN, MANAGER, SELLER)
POST   "/{task_id}/cancel"               → route_cancel_task        (ADMIN, MANAGER)
POST   "/{task_id}/fail"                 → route_fail_task          (ADMIN, MANAGER)
POST   "/{task_id}/items"                → route_add_item_to_task   (ADMIN, MANAGER)
DELETE "/{task_id}/items/{item_id}"      → route_remove_item_from_task (ADMIN, MANAGER)
```

**Query params for `GET /`:**
```
limit, offset, q, working_section_ids (comma-separated), task_states (comma-separated),
task_step_states, step_readiness_statuses, priorities, task_types, return_sources,
ready_from_date, ready_to_date, scheduled_from_date, scheduled_to_date,
upholstery_requirement_states, deleted (bool, default False), order_by (string)
```

**Role names:** check existing role constants in `routers/utils/roles.py` — they must include a SELLER constant. If SELLER does not exist, do not create it; use ADMIN+MANAGER only and log a TODO comment for SELLER access.

**Router registration in `routers/api_v1/__init__.py`:**
```python
from beyo_manager.routers.api_v1 import tasks
# ...
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
```

---

## Risks and mitigations

- **Risk:** `pg_advisory_xact_lock(hashtext(:workspace_id))` must be called inside the `maybe_begin` block — not before it. If called before the transaction opens, the lock is not transaction-scoped and will NOT auto-release on commit.
  **Mitigation:** Step 3 explicitly states: inside `async with maybe_begin(ctx.session):`.

- **Risk:** Calling `find_or_create_customer` or `find_or_create_item` in subordinate mode — they each call `maybe_begin` internally. Since CMD-1's `maybe_begin` already opened the transaction, subordinate `maybe_begin` must detect and yield the bare session. Do NOT create a second `ServiceContext` with a fresh session — pass `ctx.session` directly.
  **Mitigation:** Read `06_commands_local.md` for the exact subordinate-mode contract. The sub-command receives the same `ctx.session` — construct a new `ServiceContext` with `session=ctx.session` and `identity=ctx.identity`.

- **Risk:** `task.task_scalar_id` is selected before the `Task` row is flushed. Ensure the MAX query runs on committed rows (other transactions' tasks) — not on the current unflushed task. This is correct: the MAX query scans the DB rows; the current transaction has not inserted yet.
  **Mitigation:** Lock is acquired first; then MAX is queried; then Task is created. Lock prevents a concurrent transaction from getting the same MAX.

- **Risk:** QUERY-1 priority ordering — `TaskPriorityEnum` has string values. SQL `ORDER BY state DESC` is alphabetical, not semantic. Use a `CASE` expression or integer mapping to sort by semantic priority order.
  **Mitigation:** Acceptance criterion 15 specifies `priority DESC` means `urgent > high > normal > low`. Use SQLAlchemy `case()` expression.

- **Risk:** `ConflictError` not in `errors.validation` — check exact import path in `architecture/05_errors.md` before using it.

---

## Validation plan

Save to `backend/tests/tasks/test_task_crud.sh`. Run: `bash tests/tasks/test_task_crud.sh <email> <password>`.

```bash
# Tests to cover:
# 1. Create task (no item, no customer) → returns {client_id, task_scalar_id}
# 2. Two concurrent creates in same workspace → different task_scalar_id
# 3. Create task with item (find_or_create_item creates new) → TaskItem row exists
# 4. Create task with existing article_number → finds existing item, was_created=false in DB
# 5. Update task (PATCH) — only provided fields change
# 6. Resolve task → state=resolved
# 7. Cancel task → state=cancelled
# 8. Fail task → state=failed
# 9. Cannot resolve already-terminal task → 409 ConflictError
# 10. Soft-delete task → is_deleted=true; GET returns 404
# 11. Add item to task (RELATED role) → 200
# 12. Add second PRIMARY item → 409 ConflictError
# 13. Remove item from task → removed_at set
# 14. GET /tasks list — q filter returns matching task
# 15. GET /tasks list — state filter returns only tasks in that state
# 16. GET /tasks/{id} — returns full payload including task_steps (empty array at this stage)
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
