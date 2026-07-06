# PLAN_task_post_handling_counts_20260703

## Metadata

- Plan ID: `PLAN_task_post_handling_counts_20260703`
- Status: `archived`
- Owner agent: `Claude`
- Created at (UTC): `2026-07-03T00:00:00Z`
- Last updated at (UTC): `2026-07-03T08:37:06Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add a single query endpoint that returns the count of tasks with post-handling instances, grouped by post-handling state.
- Business/user intent: The frontend needs a fast badge/summary source to show how many tasks are in each post-handling state without fetching the full task list.
- Non-goals: No schema changes, no new model, no filtering by workspace dimensions other than `workspace_id`, no pagination.

## Scope

- In scope:
  - New query service `count_task_post_handling_states` — single GROUP BY query on `task_post_handlings`; returns all states zero-filled when no filter is passed, or only the requested states when `post_handling_states` is provided.
  - New route `GET /post-handling/counts` registered **before** `GET /{task_id}` in the tasks router (FastAPI matches literal segments before path params).
  - Handoff document updated with the new endpoint.
- Out of scope:
  - Any additional filters (task_type, workspace_role, date ranges).
  - Counting unique tasks vs. counting post-handling records (the count is per post-handling record, not per task — one task has at most one active record so this is equivalent in practice).

## Clarifications required

- None.

## Acceptance criteria

1. `GET /api/v1/tasks/post-handling/counts` with no params returns `{ "pending": N, "filled": N, "completed": N }` where N is the count of post-handling records in that state for the workspace.
2. `GET /api/v1/tasks/post-handling/counts?post_handling_states=pending,filled` returns only `{ "pending": N, "filled": N }`.
3. States with zero records are still included in the response as `0`.
4. Route is accessible to `ADMIN`, `MANAGER`, `SELLER`, `WORKER`.
5. `py_compile` passes for the new service and the modified router.
6. Handoff document is updated.

## Contracts and skills

### Contracts loaded

- `backend/task_system/architecture/07_queries.md` + `07_queries_local.md`: query services read from `ctx.query_params`, return plain dicts, do not use `maybe_begin`.
- `backend/task_system/architecture/09_routers.md`: thin router — declare query params, build `ServiceContext`, delegate to `run_service`.
- `backend/task_system/architecture/21_naming_conventions.md`: file/function naming.

### File read intent

Permitted relational reads (done before writing plan):
- `count_task_step_states.py`: exact GROUP BY + zero-fill pattern used for a counts query in this codebase.
- `tasks.py` (router): exact position of `GET /counts` and `GET /{task_id}` to determine where to insert the new route.

## Implementation plan

### Step 1 — Create query service

File (new): `app/beyo_manager/services/queries/tasks/count_task_post_handling_states.py`

```python
from sqlalchemy import func, select

from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.context import ServiceContext


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def count_task_post_handling_states(ctx: ServiceContext) -> dict:
    requested_states = _split_csv(ctx.query_params.get("post_handling_states"))

    stmt = (
        select(TaskPostHandling.state, func.count(TaskPostHandling.client_id))
        .where(TaskPostHandling.workspace_id == ctx.workspace_id)
        .group_by(TaskPostHandling.state)
    )

    if requested_states:
        stmt = stmt.where(TaskPostHandling.state.in_(requested_states))

    rows = (await ctx.session.execute(stmt)).all()
    raw = {state.value: count for state, count in rows}

    if requested_states:
        return {state: raw.get(state, 0) for state in requested_states}

    return {state.value: raw.get(state.value, 0) for state in TaskPostHandlingStateEnum}
```

Note: `_split_csv` is duplicated here from `tasks.py` to keep this service self-contained. If a shared utility is ever extracted, these can be consolidated.

---

### Step 2 — Add route to tasks router

File: `app/beyo_manager/routers/api_v1/tasks.py`

**2a.** Add import alongside the other query imports at the top of the file:
```python
from beyo_manager.services.queries.tasks.count_task_post_handling_states import (
    count_task_post_handling_states,
)
```

**2b.** Add the route **immediately after** `route_list_task_counts` (the `GET /counts` route) and **before** `route_get_task` (the `GET /{task_id}` route). This ordering is required — FastAPI matches literal path segments before path parameters, but only when the literal route is registered first.

```python
@router.get("/post-handling/counts")
async def route_count_task_post_handling_states(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    post_handling_states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"post_handling_states": post_handling_states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(count_task_post_handling_states, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 3 — Update handoff document

File: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_post_handling_20260701.md`

Append the following block inside the "Update: Task post-handling lifecycle" section, after the "Updated task payloads and filtering" block and before the "Lifecycle notes" block:

```markdown
#### `GET /api/v1/tasks/post-handling/counts`

Returns the count of post-handling records per state for the workspace.
Access: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`.

Query parameter:
- `post_handling_states` (optional, CSV) — e.g. `"pending,filled"`. When omitted, all three states are returned.

Response with no filter:
```json
{
  "pending": 12,
  "filled": 5,
  "completed": 38
}
```

Response with `?post_handling_states=pending,filled`:
```json
{
  "pending": 12,
  "filled": 5
}
```

- States with zero records are always included in the response as `0`.
- The count reflects post-handling records, not tasks. In practice one active record per task means the counts are equivalent.
```

---

### Step 4 — Validate

```bash
.venv/bin/python -m py_compile app/beyo_manager/services/queries/tasks/count_task_post_handling_states.py
.venv/bin/python -m py_compile app/beyo_manager/routers/api_v1/tasks.py
```

Both must exit 0 with no output.

## Risks and mitigations

- Risk: `GET /post-handling/counts` registered after `GET /{task_id}` would cause FastAPI to match `post-handling` as a `task_id` value, returning a 404.
  Mitigation: Step 2b explicitly places the new route immediately after `GET /counts` and before `GET /{task_id}`. The code comment in the router should note the ordering dependency.

- Risk: An invalid string in `post_handling_states` (e.g. `"invalid_state"`) would not match any DB row and simply return `{"invalid_state": 0}` rather than raising a 400.
  Mitigation: Acceptable for now — the endpoint is a fast read and returning zero for unknown states is harmless. Enum validation can be added later if needed.

## Validation plan

- `py_compile` on both changed files: must pass.
- Manual check: confirm new route appears before `/{task_id}` route in the router file.

## Review log

- `2026-07-03` Claude: Plan created.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `user`
