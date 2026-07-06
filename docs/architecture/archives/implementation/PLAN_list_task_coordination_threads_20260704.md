# PLAN_list_task_coordination_threads_20260704

## Metadata

- Plan ID: `PLAN_list_task_coordination_threads_20260704`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T14:16:58Z`
- Related issue/ticket: —
- Intention plan: —

---

## Goal and intent

- **Goal:** Add `GET /api/v1/tasks/customer-coordination/threads` — a paginated inbox-style endpoint that lists email threads linked to task customer coordination records, joining in the task so the frontend can display task context alongside each thread without a second request.
- **Business/user intent:** Staff need an inbox that shows all outbound coordination emails and any customer replies. They want to filter by coordination state and task type/state, and see unread threads surfaced at the top.
- **Non-goals:**
  - No `connection_client_id` filter — the endpoint is entity-scoped, not connection-scoped. Connection is transport, not a filter concern here.
  - No new models, migrations, or writes of any kind.
  - No caching — this is a user-specific, unread-aware feed that must reflect real-time state.

---

## Scope

- **In scope:**
  - New query file: `app/beyo_manager/services/queries/tasks/list_task_coordination_threads.py`
  - New route in `app/beyo_manager/routers/api_v1/tasks.py`: `GET /customer-coordination/threads`
  - Append Section 5 to `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md`

- **Out of scope:**
  - Modifying `serialize_email_thread`, `serialize_task`, or `serialize_task_customer_coordination`
  - Any other router or query file
  - Tests (not required for this plan)

- **Assumptions:**
  - Every `EmailThread` with `entity_type = task_customer_coordination` has exactly one `TaskCustomerCoordination` record reachable via `entity_client_id = tcc.client_id`. The JOIN is safe — no row multiplication.
  - `EmailThreadUserState` is 0..1 per (thread, user). LEFT JOIN produces no row multiplication.
  - `Task.is_deleted` exists and is a boolean column (confirmed from existing queries).
  - `TaskCustomerCoordinationStateEnum` values are the valid inputs for `coordination_states` filter.
  - `TaskStateEnum` values are valid for `task_states` filter.
  - `TaskTypeEnum` values are valid for `task_types` filter.

---

## Clarifications required

None — design was fully resolved in conversation before this plan was written.

---

## Acceptance criteria

1. `GET /api/v1/tasks/customer-coordination/threads` returns a paginated list of objects, each containing a `thread` key (email thread shape with `is_unread`) and a `task` key (full task shape with `customer_coordination` array containing the single TCC linked to that thread).
2. Unread threads appear before read threads in the response. Within each group, threads are ordered by `last_message_at DESC NULLS LAST`.
3. Optional filters `coordination_states`, `task_states`, and `task_types` (all CSV strings) narrow the result set correctly. Omitting any filter returns all matching records.
4. Pagination follows the offset pattern: `has_more`, `limit`, `offset` returned under `coordination_threads_pagination`.
5. `workspace_id` is the mandatory first WHERE condition; threads from other workspaces are never returned.
6. The handoff doc has a new Section 5 documenting this endpoint with its query params, response shape, and error responses.

---

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: layered architecture — no business logic in routers
- `architecture/04_context.md`: `ServiceContext` signature — `query_params` carries filter params from router to query
- `architecture/05_errors.md`: error types and when to raise them
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: query signature, offset pagination override (local wins — cursor pagination does NOT apply here)
- `architecture/09_routers.md`: route handler shape, route declaration order rule (static paths before `/{id}`)
- `architecture/21_naming_conventions.md`: file and function naming
- `architecture/40_identity.md`: workspace scope enforcement

### Local extensions loaded

- `architecture/07_queries_local.md`: **offset pagination replaces cursor pagination**. Use `limit + 1` trick, return `has_more / limit / offset` under `<entity_plural>_pagination`.

### File read intent — pattern vs. relational

Permitted (relational — understanding what already exists):
- `app/beyo_manager/domain/emails/serializers.py` — to confirm `serialize_email_thread(thread, user_state)` signature
- `app/beyo_manager/domain/tasks/serializers.py` — to confirm `serialize_task(task, customer_coordination_instances=[...])` signature
- `app/beyo_manager/models/tables/emails/email_thread.py` — exact column names (`entity_type`, `entity_client_id`, `last_message_at`, `last_inbound_message_at`)
- `app/beyo_manager/models/tables/emails/email_thread_user_state.py` — `last_read_at` column name
- `app/beyo_manager/models/tables/tasks/task_customer_coordination.py` — `client_id`, `task_id`, `state` column names
- `app/beyo_manager/models/tables/tasks/task.py` — `client_id`, `is_deleted`, `state`, `task_type` column names
- `app/beyo_manager/routers/api_v1/tasks.py` — to identify the correct insertion point (after `POST /customer-coordination/email-batch`, before `GET /{task_id}`)

Prohibited (pattern reads — contract covers these):
- Reading any other query file to understand session/select shape → use `07_queries.md`
- Reading any other router to understand handler wiring → use `09_routers.md`

### Skill selection

- Primary skill: `07_queries.md` (query with multi-table JOIN)
- Router trigger: `09_routers.md` (GET route registration)
- Excluded: no commands, no models, no migrations

---

## Implementation plan

### Step 1 — Create the query file

**File:** `app/beyo_manager/services/queries/tasks/list_task_coordination_threads.py`

**Imports needed:**
- `sqlalchemy`: `case`, `or_`, `select`
- `beyo_manager.domain.emails.enums`: `EmailThreadEntityTypeEnum`
- `beyo_manager.domain.emails.serializers`: `serialize_email_thread`
- `beyo_manager.domain.tasks.serializers`: `serialize_task`, `serialize_task_customer_coordination`
- `beyo_manager.models.tables.emails.email_thread`: `EmailThread`
- `beyo_manager.models.tables.emails.email_thread_user_state`: `EmailThreadUserState`
- `beyo_manager.models.tables.tasks.task`: `Task`
- `beyo_manager.models.tables.tasks.task_customer_coordination`: `TaskCustomerCoordination`
- `beyo_manager.services.context`: `ServiceContext`

**Constants:**
```python
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
```

**CSV parser (local — same pattern as `count_task_customer_coordination_states.py`):**
```python
def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]
```

**Query construction:**

Build a single SELECT over four sources:
```
EmailThread
  JOIN TaskCustomerCoordination ON tcc.client_id = thread.entity_client_id
  JOIN Task ON task.client_id = tcc.task_id AND task.is_deleted = false
  LEFT JOIN EmailThreadUserState ON user_state.thread_id = thread.client_id
                                  AND user_state.user_id = ctx.user_id
```

WHERE conditions (mandatory first, then optional filters):
1. `EmailThread.workspace_id == ctx.workspace_id`  ← mandatory, always first
2. `EmailThread.entity_type == EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value`
3. `Task.is_deleted.is_(False)`
4. If `coordination_states` param is present: `TaskCustomerCoordination.state.in_(coordination_states)`
5. If `task_states` param is present: `Task.state.in_(task_states)`
6. If `task_types` param is present: `Task.task_type.in_(task_types)`

**Unread sort expression (SQLAlchemy `case()`):**

A thread is unread when `last_inbound_message_at IS NOT NULL` AND (`user_state.last_read_at IS NULL` OR `last_inbound_message_at > last_read_at`). Map `True → 0` (unread first), `False → 1`:

```python
is_unread_sort = case(
    (
        EmailThread.last_inbound_message_at.is_not(None)
        & or_(
            EmailThreadUserState.last_read_at.is_(None),
            EmailThread.last_inbound_message_at > EmailThreadUserState.last_read_at,
        )
    ),
    0,
    else_=1,
)
```

**ORDER BY:**
```python
.order_by(is_unread_sort.asc(), EmailThread.last_message_at.desc().nullslast())
```

**Pagination:** offset pattern from `07_queries_local.md` — fetch `limit + 1` rows, slice to `limit`, set `has_more`.

**Result extraction:** `result.all()` returns tuples `(thread, tcc, task, user_state)` where `user_state` may be `None`.

**Serialization per row:**
```python
{
    "thread": serialize_email_thread(thread, user_state),
    "task": serialize_task(task, customer_coordination_instances=[tcc]),
}
```

**Response shape:**
```python
return {
    "coordination_threads": [...],
    "coordination_threads_pagination": {
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
    },
}
```

---

### Step 2 — Add the route to the tasks router

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

**Import to add:**
```python
from beyo_manager.services.queries.tasks.list_task_coordination_threads import (
    list_task_coordination_threads,
)
```

**Route declaration — insert AFTER `POST /customer-coordination/email-batch` and BEFORE `GET /{task_id}`** (static path must precede the wildcard — see `09_routers.md` route ordering rule):

```python
@router.get("/customer-coordination/threads")
async def route_list_task_coordination_threads(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
    coordination_states: str | None = Query(None),
    task_states: str | None = Query(None),
    task_types: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "coordination_states": coordination_states,
            "task_states": task_states,
            "task_types": task_types,
            "limit": limit,
            "offset": offset,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_coordination_threads, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Roles:** `ADMIN, MANAGER, SELLER` — same as the other coordination endpoints. WORKER excluded (workers do not manage coordination).

---

### Step 3 — Update the handoff document

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md`

Append a new **Section 5** after the existing Section 4 (`GET /email-threads/unread-count`).

Section 5 must document:

**Endpoint:** `GET /api/v1/tasks/customer-coordination/threads`

**Description:** Returns a paginated inbox-style list of email threads linked to task customer coordination records. Each item in the list includes the full email thread (with `is_unread` status for the current user) and the full task (with the coordination record for that thread inline under `customer_coordination`). Unread threads are always returned before read threads; within each group, ordering is newest `last_message_at` first.

**Query parameters table:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `coordination_states` | `string` (CSV) | No | Filter by coordination state. Valid values: `pending`, `coordinating`, `completed`. If omitted, all states are included. |
| `task_states` | `string` (CSV) | No | Filter by task state. Valid values: any `TaskStateEnum` value (e.g. `pending`, `ready`, `working`, `done`). |
| `task_types` | `string` (CSV) | No | Filter by task type. Valid values: any `TaskTypeEnum` value (e.g. `pre_order`, `return`, `internal`). |
| `limit` | `int` | No | Max items per page. Default `50`, max `200`. |
| `offset` | `int` | No | Pagination offset. Default `0`. |

**Success response shape `200`:**

```json
{
  "coordination_threads": [
    {
      "thread": {
        "client_id": "eth_xyz",
        "workspace_id": "ws_1",
        "connection_id": "ecn_1",
        "entity_type": "task_customer_coordination",
        "entity_client_id": "tcc_abc",
        "major_entity_type": "task",
        "major_entity_client_id": "tsk_1",
        "topic": null,
        "subject_normalized": "din pre order är klar",
        "last_message_at": "2026-07-04T10:00:00+00:00",
        "last_inbound_message_at": "2026-07-04T11:30:00+00:00",
        "is_unread": true,
        "user_state": {
          "thread_id": "eth_xyz",
          "user_id": "usr_1",
          "last_read_at": "2026-07-04T10:05:00+00:00",
          "muted_at": null,
          "archived_at": null
        },
        "created_at": "2026-07-04T10:00:00+00:00",
        "updated_at": null
      },
      "task": {
        "client_id": "tsk_1",
        "task_type": "pre_order",
        "state": "ready",
        "customer_coordination": [
          {
            "client_id": "tcc_abc",
            "task_id": "tsk_1",
            "state": "pending",
            "created_at": "2026-07-01T10:00:00+00:00",
            "updated_at": null
          }
        ]
      }
    }
  ],
  "coordination_threads_pagination": {
    "has_more": false,
    "limit": 50,
    "offset": 0
  }
}
```

Key notes for the frontend:
- `thread.is_unread` is `true` when `last_inbound_message_at IS NOT NULL` and the user has either never read the thread or the last inbound message arrived after `user_state.last_read_at`.
- `thread.user_state` is `null` if the current user has never opened this thread.
- `task.customer_coordination` always contains exactly one item — the single TCC record linked to this thread. It is never `null` in this endpoint.
- Unread threads are guaranteed to appear before read threads. No client-side re-sorting is needed.
- After reading a thread, call `POST /api/v1/email-threads/{thread_id}/read` to mark it read and update `user_state.last_read_at`.
- To retrieve the messages inside a thread, call `GET /api/v1/email-threads/{thread_id}/messages`.

**Error responses table:**

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Role not allowed (`WORKER` is excluded) |

No `404` — an empty result set returns `200` with `coordination_threads: []`.

Also update the **Frontend action required** section near the top of the handoff to add:

> 5. Use `GET /tasks/customer-coordination/threads` to render the coordination inbox. Filter by `coordination_states` and task properties. Show unread badge from `thread.is_unread`. Call `POST /email-threads/{thread_id}/read` after the user opens a thread.

---

## Risks and mitigations

- **Risk:** The `CASE WHEN` unread sort expression requires Postgres to evaluate all matching rows before paginating — no index can back this sort directly.
  **Mitigation:** Acceptable for this workload. The `entity_type + workspace_id` WHERE clause narrows the set to a single workspace's coordination threads. An index on `(workspace_id, entity_type, last_message_at DESC)` on `email_threads` will make the initial filter fast; the in-memory sort over the filtered set is bounded.

- **Risk:** Route declared after `GET /{task_id}` would shadow the static path.
  **Mitigation:** Step 2 explicitly places the new route before `@router.get("/{task_id}")`. The `09_routers.md` route ordering rule covers this — Codex must verify the final line position before completion.

- **Risk:** `result.all()` on a multi-entity SELECT returns `Row` tuples, not scalars. Using `.scalars().all()` would silently return only the first column.
  **Mitigation:** Step 1 explicitly specifies `result.all()` and destructuring `(thread, tcc, task, user_state)` per row.

---

## Validation plan

- Import check: `python -c "from beyo_manager.services.queries.tasks.list_task_coordination_threads import list_task_coordination_threads"` — no import error.
- Router check: `python -c "from beyo_manager.routers.api_v1.tasks import router"` — no import error.
- Route order check: in `tasks.py`, verify `GET /customer-coordination/threads` is declared before `GET /{task_id}`.
- Pagination gate (from `07_queries_local.md`):
  - [ ] Response includes `coordination_threads_pagination` as a top-level key
  - [ ] `has_more` is derived from `limit + 1` fetch
  - [ ] Router declares `limit: int = Query(50, le=200)` and `offset: int = Query(0, ge=0)`
  - [ ] Router passes `query_params={"limit": limit, "offset": offset, ...}` into `ServiceContext`
  - [ ] `_MAX_LIMIT = 200` and `_DEFAULT_LIMIT = 50` defined in the query module

---

## Review log

_No entries yet._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `user`
