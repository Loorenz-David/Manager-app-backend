# PLAN_task_steps_list_rich_and_count_20260627

## Metadata

- Plan ID: `PLAN_task_steps_list_rich_and_count_20260627`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-27T00:00:00Z`
- Last updated at (UTC): `2026-06-27T09:57:10Z`
- Related issue/ticket: `n/a`
- Intention plan: `n/a`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_steps_list_rich_and_count_20260627.md`

## Goal and intent

- Goal: (1) Upgrade `list_task_steps` to return the same rich step shape that `get_task` returns under `"task_steps"`. (2) Add a new fast `GET /{task_id}/steps/counts` endpoint that returns step counts grouped by state.
- Business/user intent: The list endpoint currently returns a compact representation missing `latest_state_records` and several aggregate fields. Clients need the full shape for consistency with the task detail view. The counts endpoint lets clients render state badges without fetching the full list.
- Non-goals: No changes to any command/mutation service. No changes to `get_task`. No migration required.

## Scope

- In scope:
  - Rewrite `app/beyo_manager/services/queries/tasks/list_task_steps.py` to use `selectinload(TaskStep.latest_state_record)` and serialize with `serialize_step` + `serialize_step_latest_state_record` from `beyo_manager.domain.tasks.serializers`.
  - Create `app/beyo_manager/services/queries/tasks/count_task_step_states.py` with a single `GROUP BY state` query.
  - Add `GET /{task_id}/steps/counts` handler in `app/beyo_manager/routers/api_v1/tasks.py`.
- Out of scope:
  - `serialize_task_step_compact` and its file — do not delete (other callers may exist).
  - Pagination shape key (`steps_pagination`) — keep unchanged.
  - Roles — keep same as existing `route_list_task_steps`: `[ADMIN, MANAGER, WORKER]`.
- Assumptions:
  - `TaskStep.latest_state_record` is a lazy-loadable relationship already defined and usable via `selectinload` (confirmed in model: `task_step.py` line 104).
  - `serialize_step` and `serialize_step_latest_state_record` are stable and already imported in `get_task`'s file.
  - No other file currently imports `list_task_steps` output shape and depends on the compact fields (`working_section_name`, `working_section_image`).

## Clarifications required

- (none — all information is confirmed from reading existing code)

## Acceptance criteria

1. `GET /{task_id}/steps` response items contain all fields from `serialize_step` plus a `latest_state_records` key (matching `get_task`'s `"task_steps"` items exactly).
2. `GET /{task_id}/steps` no longer contains `working_section_name` or `working_section_image` (removed with compact serializer).
3. `GET /{task_id}/steps/counts` returns `{"counts_by_state": {"pending": N, "working": N, ...}}` with all states present in the DB for that task.
4. `GET /{task_id}/steps/counts` returns 404 if the task does not exist (same guard as `list_task_steps`).
5. No existing tests or imports break.

## Contracts and skills

### Contracts loaded

- `n/a`: Plan is self-contained from direct code reading.

### Local extensions loaded

- `n/a`

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Permitted reads already done:
- `services/queries/tasks/list_task_steps.py` — to understand current query strategy and pagination shape.
- `services/queries/tasks/tasks.py` (`get_task`) — to confirm target serialization shape under `"task_steps"`.
- `domain/tasks/serializers.py` — to confirm `serialize_step` and `serialize_step_latest_state_record` signatures.
- `domain/task_steps/serializers.py` — to confirm what compact serializer currently produces.
- `models/tables/tasks/task_step.py` — to confirm `latest_state_record` relationship exists.
- `domain/task_steps/enums.py` — to confirm all possible `TaskStepStateEnum` values.
- `routers/api_v1/tasks.py` — to confirm route placement and import block.

### Skill selection

- Primary skill: `n/a` (standard query service + router handler pattern)
- Router trigger terms: `steps`, `counts`
- Excluded alternatives: `n/a`

## Implementation plan

### Step 1 — Rewrite `list_task_steps.py`

File: `app/beyo_manager/services/queries/tasks/list_task_steps.py`

Replace the entire file with the following logic:

- Remove imports: `WorkingSection`, `serialize_task_step_compact`.
- Add imports: `selectinload` from `sqlalchemy.orm`; `serialize_step`, `serialize_step_latest_state_record` from `beyo_manager.domain.tasks.serializers`.
- Change the query:
  - Remove the `.join(WorkingSection, ...)` clause.
  - Add `.options(selectinload(TaskStep.latest_state_record))`.
  - Select only `TaskStep` (not the tuple `(TaskStep, WorkingSection)`).
- Change serialization from:
  ```python
  serialize_task_step_compact(step, working_section)
  ```
  to:
  ```python
  {
      **serialize_step(step),
      "latest_state_records": serialize_step_latest_state_record(step.latest_state_record),
  }
  ```
- Keep pagination wrapper key `steps_pagination`, and fields `items`, `limit`, `offset`, `has_more` unchanged.
- Keep the task-existence guard (`raise NotFound("Task not found.")`) unchanged.

### Step 2 — Create `count_task_step_states.py`

New file: `app/beyo_manager/services/queries/tasks/count_task_step_states.py`

```python
from sqlalchemy import func, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext


async def count_task_step_states(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    if task_result.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    rows = (
        await ctx.session.execute(
            select(TaskStep.state, func.count(TaskStep.client_id))
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
            .group_by(TaskStep.state)
        )
    ).all()

    counts_by_state = {state.value: count for state, count in rows}
    return {"counts_by_state": counts_by_state}
```

### Step 3 — Add router handler for counts

File: `app/beyo_manager/routers/api_v1/tasks.py`

1. Add import at top of import block (alongside existing query imports):
   ```python
   from beyo_manager.services.queries.tasks.count_task_step_states import count_task_step_states
   ```

2. Insert new handler **after** `route_list_task_steps` (after line 627) and **before** `route_add_task_step`:
   ```python
   @router.get("/{task_id}/steps/counts")
   async def route_count_task_step_states(
       task_id: str,
       claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
       session: AsyncSession = Depends(get_db),
   ):
       ctx = ServiceContext(
           incoming_data={"task_id": task_id},
           identity=claims,
           session=session,
       )
       outcome = await run_service(count_task_step_states, ctx)
       if not outcome.success:
           return build_err(outcome.error)
       return build_ok(outcome.data)
   ```

   Placement note: Define `route_count_task_step_states` immediately after `route_list_task_steps` so the static segment `counts` is registered before any `{step_id}` parameter routes, avoiding routing ambiguity.

## Risks and mitigations

- Risk: `serialize_task_step_compact` fields (`working_section_name`, `working_section_image`) were consumed by a frontend caller that has not been updated.
  Mitigation: The plan owner must coordinate with the frontend before deploying. The new `serialize_step` shape contains `working_section_name_snapshot` and `assigned_worker_display_name_snapshot` which are equivalent snapshot fields.

- Risk: `selectinload(TaskStep.latest_state_record)` issues N+1 queries if ORM relationship is lazy by default and not properly eager-loaded.
  Mitigation: `selectinload` is explicitly applied — SQLAlchemy will batch the relationship load in a single IN query. No N+1 risk.

- Risk: `GET /{task_id}/steps/counts` route shadow conflict with `GET /{task_id}/steps/{step_id}` if registered after it.
  Mitigation: Explicitly place `route_count_task_step_states` before any `/{task_id}/steps/{step_id}` handlers in the router file.

## Validation plan

- Manual: `GET /tasks/{task_id}/steps` — verify response items contain `latest_state_records`, `total_working_seconds`, `total_cost_minor`, etc. and do NOT contain `working_section_name` or `working_section_image`.
- Manual: `GET /tasks/{task_id}/steps/counts` — verify response is `{"counts_by_state": {"pending": N, ...}}` with correct totals matching step list.
- Manual: `GET /tasks/{non_existent_id}/steps/counts` — verify 404 response.
- Regression: `GET /tasks/{task_id}` (`get_task`) — verify unchanged.

## Review log

- `2026-06-27` `codex`: Plan created.
- `2026-06-27T09:57:10Z` `codex`: Implemented the rich task-step list response, added `GET /api/v1/tasks/{task_id}/steps/counts`, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_steps_list_rich_and_count_20260627.md`, and archived this plan.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
