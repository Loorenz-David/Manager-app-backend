# PLAN_list_task_steps_by_task_20260620

## Metadata

- Plan ID: `PLAN_list_task_steps_by_task_20260620`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Last updated at (UTC): `2026-06-20T13:35:18Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add `GET /{task_id}/steps` endpoint to the tasks router that returns the task steps belonging to a given task, with working section display fields embedded in each step.
- Business/user intent: Clients need to display a full step list for a task (progress overview, worker assignments, dependency status) without having to query by working section.
- Non-goals: No write operations. No filtering/search parameters (plain offset list). No change to the existing `list_working_section_steps` service.

## Scope

- In scope:
  - New serializer `serialize_task_step_compact` in `domain/task_steps/serializers.py`
  - New query service `services/queries/tasks/list_task_steps.py`
  - New `GET /{task_id}/steps` handler in `routers/api_v1/tasks.py`
- Out of scope:
  - Filtering / search parameters
  - Mutations / side effects
  - Changes to existing serializers in `domain/tasks/serializers.py`
- Assumptions:
  - Task existence is validated inside the query (raises `NotFound` if not found or deleted).
  - Working section data is fetched via a SQL join, not a selectinload, because only `name` and `image` are needed.
  - `workspace_id` is scoped through `ctx.workspace_id` as mandated by the query contract.

## Clarifications required

_(none — all field names confirmed from model files)_

## Acceptance criteria

1. `GET /tasks/{task_id}/steps?limit=50&offset=0` returns `{ "steps_pagination": { "items": [...], "limit": 50, "offset": 0, "has_more": false } }`.
2. Each item contains exactly: `client_id`, `task_id`, `state`, `readiness_status`, `sequence_order`, `working_section_id`, `assigned_worker_id`, `total_dependencies`, `completed_dependencies`, `working_section_name`, `working_section_image`, `created_at`, `closed_at`.
3. Requesting a non-existent or deleted `task_id` returns `404 NotFound`.
4. Response is scoped to `ctx.workspace_id` — steps from other workspaces are never returned.
5. Pagination contract is satisfied: `has_more` is derived from fetching `limit + 1` rows; both empty-list and non-empty paths return `steps_pagination`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: overall layering rules
- `backend/architecture/04_context.md`: `ServiceContext` usage
- `backend/architecture/05_errors.md`: `NotFound` import path
- `backend/architecture/07_queries.md`: query signature, serialization rules, workspace scope enforcement
- `backend/architecture/07_queries_local.md`: offset-based pagination replaces cursor-based; `_MAX_LIMIT`/`_DEFAULT_LIMIT` constants required
- `backend/architecture/08_domain.md`: serializer placement in `domain/<domain>/serializers.py`
- `backend/architecture/09_routers.md`: router handler wiring, `ServiceContext` construction, `build_ok` / `build_err`
- `backend/architecture/21_naming_conventions.md`: function and module naming
- `backend/architecture/40_identity.md`: `client_id` as the public identifier
- `backend/architecture/41_user.md`: `ctx.workspace_id`, `ctx.user_id`

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination overrides cursor pagination; completion gate checklist applies

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another query service to understand `select()` / `execute()` / pagination shape → `07_queries.md` + `07_queries_local.md`
- Reading another router handler to understand `ServiceContext` construction → `09_routers.md`
- Reading another serializer to understand return dict shape → `08_domain.md` / `07_queries.md`

Permitted (relational reads — understanding what exists):
- `models/tables/tasks/task_step.py` — confirmed field names (already read: `client_id`, `task_id`, `state`, `readiness_status`, `sequence_order`, `working_section_id`, `assigned_worker_id`, `total_dependencies`, `completed_dependencies`, `created_at`, `closed_at`, `is_deleted`)
- `models/tables/working_sections/working_section.py` — confirmed `name`, `image` field names (already read)
- `models/tables/tasks/task.py` — to confirm `client_id`, `is_deleted` field names (read only if needed to write the task-existence check)
- `routers/api_v1/tasks.py` — to identify where to insert the new route (already read; no `GET /{task_id}/steps` exists)

### Skill selection

- Primary skill: query + router (no specific skill file; follows `07_queries.md` + `09_routers.md`)
- Router trigger terms: `list`, `steps`, `task_id`
- Excluded alternatives: command pattern — this is read-only

## Implementation plan

### Step 1 — Create `domain/task_steps/serializers.py`

Create the file (module does not yet exist):

```
backend/app/beyo_manager/domain/task_steps/serializers.py
```

Content:

```python
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection


def serialize_task_step_compact(step: TaskStep, working_section: WorkingSection | None) -> dict:
    return {
        "client_id": step.client_id,
        "task_id": step.task_id,
        "state": step.state.value,
        "readiness_status": step.readiness_status.value,
        "sequence_order": step.sequence_order,
        "working_section_id": step.working_section_id,
        "assigned_worker_id": step.assigned_worker_id,
        "total_dependencies": step.total_dependencies,
        "completed_dependencies": step.completed_dependencies,
        "working_section_name": working_section.name if working_section else None,
        "working_section_image": working_section.image if working_section else None,
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "closed_at": step.closed_at.isoformat() if step.closed_at else None,
    }
```

Rules applied:
- Pure function, no DB access.
- `isoformat()` on all datetime fields.
- Enum fields serialized via `.value`.
- Only `client_id` exposed as identifier (never internal integer PK).

---

### Step 2 — Create `services/queries/tasks/list_task_steps.py`

Create the file:

```
backend/app/beyo_manager/services/queries/tasks/list_task_steps.py
```

Content:

```python
from sqlalchemy import select

from beyo_manager.domain.task_steps.serializers import serialize_task_step_compact
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_task_steps(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    # Verify task exists and belongs to this workspace
    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    if task_result.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    # Fetch steps joined with their working section
    stmt = (
        select(TaskStep, WorkingSection)
        .join(
            WorkingSection,
            WorkingSection.client_id == TaskStep.working_section_id,
            isouter=True,
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.is_deleted.is_(False),
        )
        .order_by(
            TaskStep.sequence_order.asc().nullslast(),
            TaskStep.created_at.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    items = [
        serialize_task_step_compact(step, working_section)
        for step, working_section in page
    ]

    return {
        "steps_pagination": {
            "items": items,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
```

Rules applied:
- `workspace_id` is the first `where()` condition on every table queried.
- Offset-based pagination per `07_queries_local.md`.
- `limit + 1` fetch to determine `has_more` without a count query.
- Both empty and non-empty paths return `steps_pagination`.
- `WorkingSection` joined with `isouter=True` so steps with a missing WS (data integrity issue) still appear rather than silently disappearing.
- No lazy loading — all data comes from the single query.

---

### Step 3 — Add `GET /{task_id}/steps` handler to `routers/api_v1/tasks.py`

Insert the new handler **before** `@router.post("/{task_id}/steps")` (line 459) to keep GET above write operations on the same sub-path.

Add import at the top of the file alongside the other query imports:

```python
from beyo_manager.services.queries.tasks.list_task_steps import list_task_steps
```

Add the handler:

```python
@router.get("/{task_id}/steps")
async def route_list_task_steps(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Roles: `ADMIN`, `MANAGER`, `WORKER` — mirrors the `list_working_section_steps_route` access pattern; SELLER has no operational need to enumerate raw steps.

---

### Step 4 — Create frontend handoff doc

After all three implementation steps are complete, create the file:

```
backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md
```

Use the template at `backend/docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`.
Write the file with exactly the content below (substitute nothing — all values are already resolved):

```markdown
# HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_list_task_steps_by_task_20260620.md`
- Source summary: `—`

## Backend delivery context

- What backend implemented: New read-only endpoint that returns all task steps belonging to a specific task, each enriched with the name and image of its working section.
- API or contract changes: New `GET` route added to the tasks router at `/{task_id}/steps`. No existing routes modified.
- Feature flags/toggles (if any): None.

## Frontend action required

1. Call `GET /tasks/{task_id}/steps` (with optional `limit` / `offset` query params) wherever the UI needs to display the step list for a task.
2. Handle the `404` error case — show a suitable empty or error state when the task no longer exists.
3. Use `steps_pagination.has_more` to decide whether to show a "load more" / pagination control.

## Interface details

- Endpoint: `GET /tasks/{task_id}/steps`
- Auth: JWT required. Allowed roles: `ADMIN`, `MANAGER`, `WORKER`.

### Request shape

Path parameter:
| Param | Type | Description |
|---|---|---|
| `task_id` | `string` | Client ID of the task (prefix `tsk`) |

Query parameters:
| Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | `integer` | `50` | `200` | Max steps per page |
| `offset` | `integer` | `0` | — | Number of steps to skip |

### Response shape — success `200`

```json
{
  "steps_pagination": {
    "items": [
      {
        "client_id": "tsp_abc123",
        "task_id": "tsk_xyz789",
        "state": "pending",
        "readiness_status": "ready",
        "sequence_order": 1,
        "working_section_id": "wsec_def456",
        "assigned_worker_id": "usr_ghi012",
        "total_dependencies": 2,
        "completed_dependencies": 1,
        "working_section_name": "Assembly",
        "working_section_image": "https://cdn.example.com/assembly.png",
        "created_at": "2026-06-18T10:00:00+00:00",
        "closed_at": null
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Field reference

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `string` | No | Step ID (prefix `tsp`) |
| `task_id` | `string` | No | Parent task ID (prefix `tsk`) |
| `state` | `string` (enum) | No | `pending` · `working` · `paused` · `ended_shift` · `blocked` · `completed` · `skipped` · `failed` · `cancelled` |
| `readiness_status` | `string` (enum) | No | `ready` · `partial` · `blocked` |
| `sequence_order` | `integer` | Yes | Display order within the task; `null` if unset |
| `working_section_id` | `string` | No | ID of the working section this step belongs to (prefix `wsec`) |
| `assigned_worker_id` | `string` | Yes | User ID of the assigned worker; `null` if unassigned |
| `total_dependencies` | `integer` | No | How many prerequisite steps this step has |
| `completed_dependencies` | `integer` | No | How many of those prerequisites are done |
| `working_section_name` | `string` | Yes | Display name of the working section; `null` only on data integrity issue |
| `working_section_image` | `string` (URL) | Yes | Image URL for the working section; `null` if none set |
| `created_at` | `string` (ISO 8601) | No | When the step was created |
| `closed_at` | `string` (ISO 8601) | Yes | When the step reached a terminal state; `null` if still active |

#### Pagination fields

| Field | Type | Description |
|---|---|---|
| `limit` | `integer` | The limit that was applied |
| `offset` | `integer` | The offset that was applied |
| `has_more` | `boolean` | `true` if there are more steps beyond this page |

### Error cases

| HTTP status | When |
|---|---|
| `401 Unauthorized` | Missing or invalid JWT |
| `403 Forbidden` | Authenticated user does not have `ADMIN`, `MANAGER`, or `WORKER` role |
| `404 Not Found` | `task_id` does not exist or belongs to a different workspace |

## Validation notes

- Backend validation run: endpoint should be manually exercised against a task with known steps, with `limit=1` to confirm `has_more: true`, and again with an invalid `task_id` to confirm `404`.
- Suggested frontend validation:
  - Guard rendering on `steps_pagination.items` being an array (never `undefined`).
  - Treat `working_section_name: null` and `working_section_image: null` gracefully — render a fallback icon/label.
  - `readiness_status === "blocked"` should surface a visual indicator (step cannot start).
  - `completed_dependencies < total_dependencies` means dependencies are still pending — surface this in the UI alongside `readiness_status`.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_list_task_steps_by_task_20260620.md`
- Parent summary: `—`
- Related debug plan (optional): `—`
```

---

## Risks and mitigations

- Risk: Route `GET /{task_id}/steps` conflicts with `POST /{task_id}/steps` (FastAPI method dispatch).
  Mitigation: FastAPI routes on different HTTP methods at the same path are independent; no conflict. Confirmed by existing `DELETE /{task_id}/steps` and `POST /{task_id}/steps` already coexisting.

- Risk: WorkingSection row missing (FK reference to a soft-deleted or orphaned record).
  Mitigation: `isouter=True` on the JOIN means the step is still returned with `working_section_name: null` and `working_section_image: null` rather than silently dropped.

- Risk: Large task with many steps exhausts memory.
  Mitigation: `_MAX_LIMIT = 200` cap; client must paginate.

## Validation plan

- `GET /tasks/{valid_task_id}/steps` with no params: expect `200`, `steps_pagination.items` list, `steps_pagination.has_more` present.
- `GET /tasks/{valid_task_id}/steps?limit=1&offset=0`: expect `has_more: true` if task has >1 step.
- `GET /tasks/nonexistent_id/steps`: expect `404`.
- Each item in `items` contains all 13 required fields: `client_id`, `task_id`, `state`, `readiness_status`, `sequence_order`, `working_section_id`, `assigned_worker_id`, `total_dependencies`, `completed_dependencies`, `working_section_name`, `working_section_image`, `created_at`, `closed_at`.
- Empty task (no steps): expect `items: []`, `has_more: false`.

## Review log

_(none yet)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
