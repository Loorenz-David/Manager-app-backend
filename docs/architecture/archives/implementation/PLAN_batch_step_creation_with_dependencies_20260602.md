# PLAN_batch_step_creation_with_dependencies_20260602

## Metadata

- Plan ID: `PLAN_batch_step_creation_with_dependencies_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T15:55:48Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Wire `TaskStepDependency` edges automatically at step-creation time based on the `WorkingSectionDependency` configuration, and convert the `add_task_step` command + route to accept a batch of steps in one call.
- Business/user intent: Steps created in any context (task creation or post-creation batch add) must start with the correct `total_dependencies`, `completed_dependencies`, and `readiness_status` values — matching the working section dependency graph — without any manual follow-up. A batch-capable route also reduces round trips for the common case of assigning multiple sections to a task at once.
- Non-goals: Changing how `WorkingSectionDependency` is configured (that remains in `edit_working_section`). Changing `_sync_step_dependencies_for_section_in_session` (that path handles config changes, not step creation). Cycle detection at step creation time (the dependency graph is already validated when section config is saved).

## Scope

- In scope:
  - New file `services/commands/task_steps/_wire_new_step_dependencies.py` containing:
    - `_compute_dependency_edges()` — pure in-memory function, no DB access
    - `wire_batch_steps_into_dependency_graph()` — async, 2 DB queries, mutates step counters, inserts edges, flushes
  - Rewrite `services/commands/task_steps/add_task_step.py` to accept a list of step inputs, create all steps in a loop, call `wire_batch_steps_into_dependency_graph` once after the loop, and return `{"step_ids": [...]}`.
  - Add `AddTaskStepsRequest` (plural) and `StepInputItem` models to `services/commands/task_steps/requests/__init__.py`; keep `AddTaskStepRequest` (singular) only if still used elsewhere — if not, remove it.
  - Update `create_task.py` to collect created steps into a list and call `wire_batch_steps_into_dependency_graph` once after the step loop.
  - Update `routers/api_v1/tasks.py`: change `route_add_task_step` body from `_AddTaskStepBody` (single) to `list[_TaskStepInputBody]`; remove the now-duplicate `_AddTaskStepBody` class; update `ServiceContext` construction to pass `{"task_id": task_id, "steps": [s.model_dump() for s in body]}`.
  - Dispatch `task:step-readiness-changed` events for any pre-existing steps whose readiness changes due to backward wiring in `add_task_step`.

- Out of scope:
  - Changes to `_sync_step_dependencies_for_section_in_session` or `edit_working_section`.
  - Changes to `remove_task_step` (dependency cleanup on removal is an existing separate concern).
  - Cycle detection at step creation time.
  - Changing the route URL or HTTP method.
  - Any migration (no schema changes).

- Assumptions:
  - `WorkingSectionDependency` rows have no `removed_at`/`is_deleted` — they are managed by full replace in `edit_working_section`, so any row present is active.
  - A new step is always created with state `PENDING`, so it never increments `completed_dependencies` of backward-wired existing dependent steps.
  - Only `COMPLETED` prerequisite state increments `completed_dependencies` — matching the existing behavior in `_add_edges_for_sections` and `finalize_pending_step_completion`.
  - Existing terminal dependent steps (`COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`) do not receive backward edges — they are done and tracking new blockers is meaningless.
  - Within a single batch, if two new steps are in sections where one depends on the other, the forward wiring of the dependent step against the prerequisite step (already in `new_by_section`) covers that pair — no separate backward pass between new steps is needed.
  - `_TaskStepInputBody` (already in the router, used by `_CreateTaskBody.steps`) has the exact same fields as `_AddTaskStepBody` — the latter is removed and the route reuses the former.
  - The single-step case is a batch of size 1 — no separate per-step code path is needed.
  - Duplicate client_id validation for each step in the batch loops over items before creating any, to fail fast before any DB writes.

## Clarifications required

_None — scope is fully defined._

## Acceptance criteria

1. `POST /{task_id}/steps` accepts `[{"working_section_id": "...", ...}, ...]` (a JSON array) and returns `{"step_ids": ["tsp_...", ...]}`.
2. Each created step has `total_dependencies` and `completed_dependencies` set correctly based on the section dependency graph and the states of existing prerequisite steps in the same task.
3. `readiness_status` on each new step is `READY`, `PARTIAL`, or `BLOCKED` as computed by `recalculate_readiness`, not unconditionally `READY`.
4. Existing non-terminal steps in dependent sections get their `total_dependencies` incremented and `readiness_status` recalculated when new prerequisite steps are created for them.
5. `task:step-readiness-changed` events are dispatched for existing steps whose readiness changes due to backward wiring.
6. Steps created via `create_task` also get correct dependency edges (same logic, same helper).
7. If the working section has no `WorkingSectionDependency` rows, the helper returns immediately with zero extra work.
8. The total DB query overhead for wiring is **2 queries** regardless of batch size — one for section deps, one for existing relevant steps.
9. A batch with a duplicate `client_id` across items raises `ConflictError` before any step is written.
10. A batch with `working_section_id` not found raises `NotFound` before any step is written.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline
- `../../../architecture/06_commands.md`: command mutation pattern, session.add / flush / error-raising shape
- `../../../architecture/06_commands_local.md`: `maybe_begin`, session call safety, subordinate-command event rule
- `../../../architecture/07_queries.md`: batch-load pattern (for the wiring helper)
- `../../../architecture/09_routers.md`: handler wiring, ServiceContext construction
- `../../../architecture/21_naming_conventions.md`: snake_case, file naming
- `../../../architecture/24_multi_tenancy.md`: workspace_id on every query
- `../../../architecture/25_soft_delete.md`: is_deleted / removed_at filter rules
- `../../../architecture/46_serialization.md`: output shape

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: `maybe_begin` transaction utility, subordinate-command event rule

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead
- **What exists** → reading is legitimate

Permitted (relational reads — understanding what exists):
- Reading `add_task_step.py` for the step creation sequence (flush order, worker assignment, task state side-effect)
- Reading `create_task.py` for the step loop structure and flush points
- Reading `_sync_step_dependencies.py` for `_add_edges_for_sections` logic (to match the counter/readiness behavior)
- Reading `requests/__init__.py` for current request model structure
- Reading `routers/api_v1/tasks.py` for `route_add_task_step` and `_TaskStepInputBody` to confirm field overlap with `_AddTaskStepBody`
- Reading `task_step_dependency.py` and `working_section_dependency.py` for exact column names
- Reading `domain/task_steps/constants.py` for `TERMINAL_STEP_STATES`
- Reading `domain/task_steps/readiness.py` for `recalculate_readiness` signature

Prohibited:
- Reading another command to understand session.add / flush shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`

### Skill selection

- Primary skill: `06_commands.md` — command mutation pattern
- Secondary: `07_queries.md` — batch-load pattern for the wiring helper
- Router trigger terms: `route_add_task_step`, `_AddTaskStepBody`
- Excluded alternatives: `30_migrations.md` — no schema changes; `13_sockets.md` — no new event types

## Implementation plan

### Step 1 — New file: `_wire_new_step_dependencies.py`

Create `beyo_manager/services/commands/task_steps/_wire_new_step_dependencies.py`:

```python
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency


def _compute_dependency_edges(
    new_steps: list[TaskStep],
    existing_steps: list[TaskStep],
    section_prereqs: dict[str, set[str]],
    section_dependents: dict[str, set[str]],
) -> tuple[list[tuple[TaskStep, TaskStep]], list[TaskStep]]:
    """
    Pure in-memory. Mutates step counters and readiness in place.
    Returns:
      - edges: list of (dependent_step, prerequisite_step) to persist
      - readiness_changed: existing steps whose readiness_status changed
    """
    new_by_section: dict[str, list[TaskStep]] = {}
    for s in new_steps:
        new_by_section.setdefault(s.working_section_id, []).append(s)

    existing_by_section: dict[str, list[TaskStep]] = {}
    for s in existing_steps:
        existing_by_section.setdefault(s.working_section_id, []).append(s)

    edges: list[tuple[TaskStep, TaskStep]] = []

    # Forward: each new step wires against all prereq steps (existing + other new)
    for step in new_steps:
        for prereq_sec in section_prereqs.get(step.working_section_id, set()):
            for prereq in (
                existing_by_section.get(prereq_sec, [])
                + new_by_section.get(prereq_sec, [])
            ):
                edges.append((step, prereq))
                step.total_dependencies += 1
                if prereq.state == TaskStepStateEnum.COMPLETED:
                    step.completed_dependencies += 1
        recalculate_readiness(step)

    # Backward: existing non-terminal dependent steps wire against each new step
    readiness_changed: list[TaskStep] = []
    for step in existing_steps:
        if step.state in TERMINAL_STEP_STATES:
            continue
        old_readiness = step.readiness_status
        for prereq_sec in section_prereqs.get(step.working_section_id, set()):
            for new_prereq in new_by_section.get(prereq_sec, []):
                edges.append((step, new_prereq))
                step.total_dependencies += 1
                # new steps are always PENDING — completed_dependencies unchanged
        recalculate_readiness(step)
        if step.readiness_status != old_readiness:
            readiness_changed.append(step)

    return edges, readiness_changed


async def wire_batch_steps_into_dependency_graph(
    session: AsyncSession,
    workspace_id: str,
    new_steps: list[TaskStep],
    task_id: str,
    user_id: str,
) -> list[TaskStep]:
    """
    Wires TaskStepDependency edges for a batch of newly created (already flushed) steps.
    Returns existing steps whose readiness_status changed (for event dispatch by caller).
    Issues exactly 2 DB queries regardless of batch size.
    """
    if not new_steps:
        return []

    section_ids = {s.working_section_id for s in new_steps}

    # Query 1: section-level config, both directions
    dep_rows = (
        await session.execute(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                or_(
                    WorkingSectionDependency.dependent_section_id.in_(section_ids),
                    WorkingSectionDependency.prerequisite_section_id.in_(section_ids),
                ),
            )
        )
    ).scalars().all()

    if not dep_rows:
        return []

    section_prereqs: dict[str, set[str]] = {}
    section_dependents: dict[str, set[str]] = {}
    for row in dep_rows:
        section_prereqs.setdefault(row.dependent_section_id, set()).add(row.prerequisite_section_id)
        section_dependents.setdefault(row.prerequisite_section_id, set()).add(row.dependent_section_id)

    relevant_sections = set(section_prereqs.keys()) | set(section_dependents.keys())
    new_step_ids = {s.client_id for s in new_steps}

    # Query 2: existing steps in the task from relevant sections
    existing_rows = (
        await session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.working_section_id.in_(relevant_sections),
                TaskStep.client_id.notin_(new_step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()

    edges, readiness_changed = _compute_dependency_edges(
        new_steps=new_steps,
        existing_steps=list(existing_rows),
        section_prereqs=section_prereqs,
        section_dependents=section_dependents,
    )

    for dep_step, prereq_step in edges:
        session.add(
            TaskStepDependency(
                workspace_id=workspace_id,
                dependent_step_id=dep_step.client_id,
                prerequisite_step_id=prereq_step.client_id,
                created_by_id=user_id,
            )
        )

    await session.flush()
    return readiness_changed
```

### Step 2 — Request model: add `AddTaskStepsRequest`

In `beyo_manager/services/commands/task_steps/requests/__init__.py`, add after the existing models:

```python
class StepInputItem(BaseModel):
    client_id: str | None = None
    working_section_id: str
    sequence_order: int | None = None
    worker_id: str | None = None


class AddTaskStepsRequest(BaseModel):
    task_id: str
    steps: list[StepInputItem]


def parse_add_task_steps_request(data: dict) -> AddTaskStepsRequest:
    try:
        return AddTaskStepsRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e
```

Do not remove `AddTaskStepRequest` (singular) yet — verify it is not referenced elsewhere before removing. If the only caller was `add_task_step.py` and that file is fully rewritten, remove it in the same edit.

### Step 3 — Rewrite `add_task_step.py`

Replace the entire body of `beyo_manager/services/commands/task_steps/add_task_step.py`:

Key structure:
1. Parse `AddTaskStepsRequest`.
2. Validate no duplicate `client_id` values within the batch (fail before any DB write).
3. Load the task; guard against terminal task state.
4. Load and validate all unique working sections in the batch in one query (`working_section_id.in_(all_section_ids)`); build `section_map: dict[str, WorkingSection]`.
5. Loop over step inputs:
   a. If `client_id` provided: check for duplicate via `session.get`, raise `ConflictError` if found.
   b. Create `TaskStep` (state=`PENDING`, readiness=`READY`, `total_dependencies=0`, `completed_dependencies=0`).
   c. `session.add(step)` + `await session.flush()`.
   d. Create `StepStateRecord` (state=`PENDING`, `entered_at=now`, `exited_at=None`).
   e. `session.add(record)` + `await session.flush()`.
   f. `step.latest_state_record_id = record.client_id`.
   g. Task state side-effect: if `task.state == PENDING` (check once, flip to `ASSIGNED`, update `task.updated_at` / `task.updated_by_id`).
   h. Worker assignment: call `_resolve_worker_for_section` + `_assign_worker_to_step_in_session` as before.
   i. Append step to `created_steps` list.
6. After loop: call `wire_batch_steps_into_dependency_graph(session, workspace_id, created_steps, task_id, user_id)` → capture `readiness_changed`.
7. Build and dispatch events:
   - `task:updated` for the task (always).
   - `task:step-readiness-changed` for each step in `readiness_changed`.
8. Return `{"step_ids": [s.client_id for s in created_steps]}`.

The function is wrapped in `async with maybe_begin(ctx.session):` enclosing steps 3–6. Events are dispatched after the `async with` block closes.

### Step 4 — Update `create_task.py`

In the existing step loop (lines 218–280), collect created steps:

Before the loop, add:
```python
created_steps: list[TaskStep] = []
```

After creating each step and setting `step.latest_state_record_id`, before the worker assignment call, append:
```python
created_steps.append(step)
```

After the loop closes (before `task.updated_at = ...`), add:
```python
from beyo_manager.services.commands.task_steps._wire_new_step_dependencies import (
    wire_batch_steps_into_dependency_graph,
)
if created_steps:
    await wire_batch_steps_into_dependency_graph(
        session=ctx.session,
        workspace_id=ctx.workspace_id,
        new_steps=created_steps,
        task_id=task.client_id,
        user_id=ctx.user_id,
    )
```

The return value (`readiness_changed`) is ignored in `create_task` — all steps are new and there are no pre-existing dependent steps to dispatch events for.

Move the import to the top of the file with the other imports (not inline).

### Step 5 — Update router `routers/api_v1/tasks.py`

1. Remove the `_AddTaskStepBody` class (it is identical to `_TaskStepInputBody`).

2. Update the import:
   ```python
   # remove:
   from beyo_manager.services.commands.task_steps.add_task_step import add_task_step
   # add:
   from beyo_manager.services.commands.task_steps.add_task_step import add_task_steps
   ```

3. Update `route_add_task_step`:
   ```python
   @router.post("/{task_id}/steps")
   async def route_add_task_step(
       task_id: str,
       body: list[_TaskStepInputBody],
       claims: dict = Depends(require_roles([ADMIN, MANAGER])),
       session: AsyncSession = Depends(get_db),
   ):
       ctx = ServiceContext(
           incoming_data={
               "task_id": task_id,
               "steps": [s.model_dump() for s in body],
           },
           identity=claims,
           session=session,
       )
       outcome = await run_service(add_task_steps, ctx)
       if not outcome.success:
           return build_err(outcome.error)
       return build_ok(outcome.data)
   ```

   The handler name stays `route_add_task_step` (URL contract unchanged). The command function is renamed to `add_task_steps` to reflect the batch semantics.

## Risks and mitigations

- Risk: `_compute_dependency_edges` creates a forward edge from new step A to new step B where B is in a prerequisite section of A — but also a forward edge from new step B to new step A if A's section is a prerequisite of B's section (mutual dependency). This would be a cycle, which the section-level config prevents via `check_for_dependency_cycle`. Since the section config is already validated cycle-free, this cannot happen for same-task steps derived from it.
  Mitigation: No guard needed in the helper; the upstream invariant holds.

- Risk: The backward wiring loop in `_compute_dependency_edges` might process the same existing step twice if its section appears both as a dependent of new step X and a dependent of new step Y (two new prereqs in the same task).
  Mitigation: Process each existing step once by iterating `existing_steps` (not by section). Within that loop, iterate over `section_prereqs.get(step.working_section_id)` and `new_by_section.get(prereq_sec)` — this naturally collects all new prereqs for that step in one pass, creating all backward edges without double-counting the step itself.

- Risk: `_TaskStepInputBody` is referenced by `_CreateTaskBody.steps` — removing `_AddTaskStepBody` must not accidentally touch that reference.
  Mitigation: `_AddTaskStepBody` and `_TaskStepInputBody` are separate classes in the router; only `_AddTaskStepBody` is removed. `_CreateTaskBody.steps: list[_TaskStepInputBody]` is untouched.

- Risk: Worker assignment (`_assign_worker_to_step_in_session`) inside the creation loop triggers a flush that may interleave with the wiring flush. The wiring call happens after all steps are created and all worker assignments are done.
  Mitigation: `wire_batch_steps_into_dependency_graph` issues its own flush at the end. All prior flushes are complete. The wiring flush adds only `TaskStepDependency` rows and counter updates — no conflict with step rows.

- Risk: `create_task.py` calls `wire_batch_steps_into_dependency_graph` inside the same `maybe_begin` transaction. If there are no steps in the request (`request.steps` is None or empty), `created_steps` will be empty and the helper returns immediately (guarded by `if not new_steps: return []`).
  Mitigation: The `if created_steps:` guard in `create_task.py` makes the call explicit and skips the helper entirely when no steps were created.

## Validation plan

- `POST /{task_id}/steps` with `[{"working_section_id": "sec_A"}]` for a section with no configured deps: response is `{"step_ids": ["tsp_..."]}`, step has `total_dependencies=0`, `readiness_status="ready"`.
- `POST /{task_id}/steps` with `[{"working_section_id": "sec_B"}]` where sec_B depends on sec_A and a non-terminal step for sec_A exists in the task: new step has `total_dependencies=1`, `completed_dependencies=0`, `readiness_status="blocked"`.
- `POST /{task_id}/steps` with `[{"working_section_id": "sec_B"}]` where sec_B depends on sec_A and the sec_A step is already `COMPLETED`: new step has `total_dependencies=1`, `completed_dependencies=1`, `readiness_status="ready"`.
- `POST /{task_id}/steps` with `[{"working_section_id": "sec_A"}, {"working_section_id": "sec_B"}]` (batch, sec_B depends on sec_A): sec_B step has `total_dependencies=1`, sec_A step has `total_dependencies=0`.
- `POST /{task_id}/steps` with a new sec_A step when a non-terminal sec_B step already exists in the task (sec_B depends on sec_A): the existing sec_B step's `total_dependencies` increments by 1 and `readiness_status` is recalculated; `task:step-readiness-changed` event is dispatched.
- `PUT /tasks` (create_task) with `steps: [{"working_section_id": "sec_A"}, {"working_section_id": "sec_B"}]`: same dependency wiring as above is present on the created steps.
- `POST /{task_id}/steps` with `[{"client_id": "tsp_dup", ...}, {"client_id": "tsp_dup", ...}]`: `ConflictError` raised before any DB write.
- `POST /{task_id}/steps` with `[{"working_section_id": "nonexistent"}]`: `NotFound` raised before any step is created.
- SQL query count for a batch of N steps: section_deps query + existing_steps query = 2 queries for wiring, regardless of N.

## Review log

- `2026-06-02T15:55:48Z` — Implemented batch step creation, dependency wiring, router contract update, and validation pass.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
