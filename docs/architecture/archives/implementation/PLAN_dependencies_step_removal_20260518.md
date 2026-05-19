# PLAN_dependencies_step_removal_20260518

## Metadata

- Plan ID: `PLAN_dependencies_step_removal_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-4`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement the dependency system between task steps (CMD-14 `add_step_dependency`, CMD-15 `remove_step_dependency`) and step removal (CMD-10 `remove_task_step`). Introduce the `_recalculate_readiness` shared helper used by all three commands (and later by CMD-12). After this plan, managers can define prerequisite relationships between steps and remove steps from a task.
- **Business/user intent:** Some working sections depend on others completing first (e.g., a finishing step cannot start until a repair step is done). The dependency graph enforces this ordering through `readiness_status` on each step.
- **Non-goals:** Step state transitions (CMD-12 — Plan 5), analytics (Plan 6). The `_recalculate_readiness` helper created here is the definitive shared implementation — Plan 5 imports it without modification.

---

## Prerequisite

**Plan 3 must be completed.** Steps must exist before dependencies can be added. CMD-10 references `StepStateRecord` to close the open record — that record is created by CMD-9 (Plan 3).

---

## Scope

- **In scope:**
  - Shared helper: `services/commands/task_steps/_readiness.py`
  - New command: `services/commands/task_steps/add_step_dependency.py` — CMD-14
  - New command: `services/commands/task_steps/remove_step_dependency.py` — CMD-15
  - New command: `services/commands/task_steps/remove_task_step.py` — CMD-10
  - Request models appended to `services/commands/task_steps/requests/__init__.py`
  - Route additions to `routers/api_v1/tasks.py`
- **Out of scope:** Cycle detection algorithms (only the self-loop check from the DB constraint; full cycle detection is a domain guard Copilot may stub as a TODO). No new migrations.
- **Assumptions:** `task_step_dependencies` table exists with `dependent_step_id`, `prerequisite_step_id`, `removed_at`, `workspace_id`. `StepStateRecord` and `TaskStepReadinessStatusEnum` exist.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. `_recalculate_readiness(step)` sets `readiness_status`:
   - `total_dependencies == 0` → `READY`
   - `completed_dependencies == total_dependencies AND total_dependencies > 0` → `READY`
   - `completed_dependencies == 0 AND total_dependencies > 0` → `BLOCKED`
   - `0 < completed_dependencies < total_dependencies` → `PARTIAL`
   This function takes `step: TaskStep` only (already loaded); it does NOT query the DB. It reads `step.total_dependencies` and `step.completed_dependencies` — both counters are kept up-to-date by the commands.

2. `POST /api/v1/tasks/{task_id}/steps/{step_id}/dependencies` inserts a `TaskStepDependency` edge, increments `step.total_dependencies`, calls `_recalculate_readiness(step)`. Returns `{dependency_id}`.

3. Adding a self-loop dependency (step depends on itself) raises `ValidationError`. The DB constraint `ck_task_step_dependencies_no_self_ref` would also catch it, but validate in code first.

4. Adding a duplicate active dependency (same pair, `removed_at IS NULL`) raises `ConflictError`.

5. Both steps in a dependency must belong to the same task. Raise `ValidationError` if not.

6. `DELETE /api/v1/tasks/{task_id}/steps/{step_id}/dependencies/{dependency_id}` sets `removed_at` on the edge, decrements `step.total_dependencies`, and calls `_recalculate_readiness(step)`. Returns `{dependency_id}`.

7. Decrement guard: `total_dependencies` must not go below `completed_dependencies`. If removing the edge would make `total_dependencies < completed_dependencies`, also decrement `completed_dependencies` to match. (This situation should not arise under normal use, but guard defensively.)

8. `DELETE /api/v1/tasks/{task_id}/steps/{step_id}` removes a step:
   - Sets `step.state = SKIPPED` (terminal).
   - Closes the current open `StepStateRecord` (`exited_at = now()`).
   - Soft-deletes the step (`is_deleted = True`, `closed_at = now()`).
   - Soft-removes all active dependency edges that reference this step (both as `dependent_step_id` and `prerequisite_step_id`): sets `removed_at` on each.
   - For each step that had this step as a prerequisite: decrements `total_dependencies`, calls `_recalculate_readiness`.
   - Checks if all remaining non-deleted steps are now in terminal states → if so, task → `READY`.
   - Special case: if this was the LAST non-deleted step → task → `PENDING` (no steps left = unassigned).

9. CMD-10 closes the open `StepStateRecord` by setting `exited_at = now()` on the record where `step_id = step.client_id AND exited_at IS NULL`. If no open record exists (should not happen under normal flow), proceed without error.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: structure
- `backend/architecture/04_context.md`: `ServiceContext`
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound`, `ConflictError`
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, session call safety
- `backend/architecture/09_routers.md`: router wiring
- `backend/architecture/21_naming_conventions.md`: naming

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/tasks/task_step_dependency.py` | All columns, partial unique index name, self-loop constraint name |
| `models/tables/tasks/task_step.py` | `total_dependencies`, `completed_dependencies`, `readiness_status`, `state`, `is_deleted`, `closed_at` |
| `models/tables/tasks/step_state_record.py` | `exited_at`, `step_id`, partial unique index `uix_step_state_records_active` |
| `models/tables/tasks/README.md` | Dependency rules, active-edge definition, step removal rules |
| `domain/task_steps/enums.py` | `TaskStepReadinessStatusEnum`, `TaskStepStateEnum.SKIPPED`, `TaskStepStateEnum.COMPLETED` |
| `domain/tasks/enums.py` | `TaskStateEnum.READY`, `TaskStateEnum.PENDING` |

---

## Implementation plan

### Step 1 — Shared helper: `services/commands/task_steps/_readiness.py`

This is a **pure Python function** — no async, no DB queries, no `maybe_begin`.

```python
"""Shared readiness recalculation for task steps. Pure function — no DB access."""

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def recalculate_readiness(step: TaskStep) -> None:
    """
    Set step.readiness_status based on dependency counters.
    Caller is responsible for flushing after this call.
    Dependency state is the ONLY input — no external conditions.
    """
    if step.total_dependencies == 0:
        step.readiness_status = TaskStepReadinessStatusEnum.READY
    elif step.completed_dependencies == step.total_dependencies:
        step.readiness_status = TaskStepReadinessStatusEnum.READY
    elif step.completed_dependencies == 0:
        step.readiness_status = TaskStepReadinessStatusEnum.BLOCKED
    else:
        step.readiness_status = TaskStepReadinessStatusEnum.PARTIAL
```

**Rules:**
- Module name starts with underscore (`_readiness.py`) — this is a private shared module. It is NOT a command and has no `ServiceContext` parameter.
- Import as: `from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness`
- Do NOT add any DB queries or side effects to this function ever. New callers are always: load the step, modify counters, call `recalculate_readiness(step)`, flush.

### Step 2 — Request models append: `services/commands/task_steps/requests/__init__.py`

Append (do not modify existing models):

```
AddStepDependencyRequest:
  task_id: str   (for scope verification)
  step_id: str   (the dependent step)
  prerequisite_step_id: str

RemoveStepDependencyRequest:
  task_id: str
  step_id: str
  dependency_id: str

RemoveTaskStepRequest:
  task_id: str
  step_id: str
```

Parse functions: standard pattern.

### Step 3 — CMD-14: `services/commands/task_steps/add_step_dependency.py`

```python
async def add_step_dependency(ctx: ServiceContext) -> dict:
    request = parse_add_step_dependency_request(ctx.incoming_data)

    if request.step_id == request.prerequisite_step_id:
        raise ValidationError("A step cannot depend on itself.")

    async with maybe_begin(ctx.session):
        # Load both steps — verify they belong to same task
        dependent_step = ...  # task_id + workspace_id + is_deleted=False → 404
        prerequisite_step = ...  # prerequisite_step_id + task_id + workspace_id + is_deleted=False → 404

        # Guard: no duplicate active edge
        existing = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.dependent_step_id == request.step_id,
                TaskStepDependency.prerequisite_step_id == request.prerequisite_step_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Dependency edge already exists.")

        edge = TaskStepDependency(
            workspace_id=ctx.workspace_id,
            dependent_step_id=request.step_id,
            prerequisite_step_id=request.prerequisite_step_id,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(edge)

        dependent_step.total_dependencies += 1
        recalculate_readiness(dependent_step)

        await ctx.session.flush()

    return {"dependency_id": edge.client_id}
```

**Note:** `prerequisite_step`'s `completed_dependencies` and `total_dependencies` are NOT touched — those belong to the prerequisite's OWN dependencies, not to the steps that depend on it.

### Step 4 — CMD-15: `services/commands/task_steps/remove_step_dependency.py`

```python
async def remove_step_dependency(ctx: ServiceContext) -> dict:
    request = parse_remove_step_dependency_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        edge = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.client_id == request.dependency_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        edge = edge.scalar_one_or_none()
        if edge is None:
            raise NotFound("Dependency edge not found or already removed.")

        # Load dependent step for counter update
        step = ...  # select TaskStep by edge.dependent_step_id + workspace_id + is_deleted=False

        now = datetime.now(timezone.utc)
        edge.removed_at = now
        edge.removed_by_id = ctx.user_id

        # Defensive decrement
        if step.total_dependencies > 0:
            step.total_dependencies -= 1
        if step.completed_dependencies > step.total_dependencies:
            step.completed_dependencies = step.total_dependencies

        recalculate_readiness(step)
        await ctx.session.flush()

    return {"dependency_id": edge.client_id}
```

### Step 5 — CMD-10: `services/commands/task_steps/remove_task_step.py`

This command has the most side effects in this plan. Follow this exact sequence inside one `maybe_begin` block:

```python
async def remove_task_step(ctx: ServiceContext) -> dict:
    request = parse_remove_task_step_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # 1. Fetch step (scope: task_id + workspace_id)
        step = ...  # → 404 if not found; ConflictError if already deleted

        # 2. Fetch task
        task = ...  # → 404 if not found

        # 3. Set step state to SKIPPED (terminal)
        step.state = TaskStepStateEnum.SKIPPED
        step.closed_at = now
        step.updated_at = now
        step.updated_by_id = ctx.user_id

        # 4. Close the open StepStateRecord
        open_record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id == step.client_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
        open_record = open_record_result.scalar_one_or_none()
        if open_record is not None:
            open_record.exited_at = now

        # 5. Soft-delete the step
        step.is_deleted = True
        step.deleted_at = now
        step.deleted_by_id = ctx.user_id

        # 6. Soft-remove ALL active dependency edges referencing this step
        #    (both as dependent and as prerequisite)
        dependent_edges_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.dependent_step_id == step.client_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        for edge in dependent_edges_result.scalars().all():
            edge.removed_at = now
            edge.removed_by_id = ctx.user_id

        prerequisite_edges_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.prerequisite_step_id == step.client_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        for edge in prerequisite_edges_result.scalars().all():
            edge.removed_at = now
            edge.removed_by_id = ctx.user_id
            # Recalculate readiness for the DEPENDENT step of this edge
            affected_step_result = await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.client_id == edge.dependent_step_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            affected_step = affected_step_result.scalar_one_or_none()
            if affected_step is not None:
                if affected_step.total_dependencies > 0:
                    affected_step.total_dependencies -= 1
                if affected_step.completed_dependencies > affected_step.total_dependencies:
                    affected_step.completed_dependencies = affected_step.total_dependencies
                recalculate_readiness(affected_step)

        # 7. Check all remaining non-deleted steps for terminal state
        remaining_steps_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        remaining_steps = remaining_steps_result.scalars().all()

        _TERMINAL_STEP_STATES = frozenset({
            TaskStepStateEnum.COMPLETED,
            TaskStepStateEnum.SKIPPED,
            TaskStepStateEnum.FAILED,
            TaskStepStateEnum.CANCELLED,
        })

        if len(remaining_steps) == 0:
            # Last step removed → task reverts to PENDING
            task.state = TaskStateEnum.PENDING
            task.updated_at = now
            task.updated_by_id = ctx.user_id
        elif all(s.state in _TERMINAL_STEP_STATES for s in remaining_steps):
            # All remaining steps are terminal → task → READY
            task.state = TaskStateEnum.READY
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        await ctx.session.flush()

    return {"step_id": step.client_id}
```

**Critical notes:**

- The removed step is soft-deleted (`is_deleted = True`) but NOT excluded from the `remaining_steps` count — wait: YES it is, because the `remaining_steps` query filters `is_deleted.is_(False)`. The removed step's `is_deleted` was set to `True` before the flush, so SQLAlchemy will see it in its in-memory state as deleted. However, the DB has not yet committed. **This is fine** — SQLAlchemy tracks in-memory object state. When we query with `is_deleted.is_(False)`, SQLAlchemy may return the already-modified step from the identity map. **To be safe: use `.execution_options(populate_existing=True)` or check the step is not the removed one in the result.**

  Simplest approach: after setting `step.is_deleted = True`, filter it out manually:
  ```python
  remaining_steps = [s for s in remaining_steps if s.client_id != step.client_id]
  ```
  This is more reliable than relying on SQLAlchemy's identity-map behavior during a pending flush.

- The soft-deleted step's state is `SKIPPED` (terminal). It should count toward "all terminal" if it were included — but since we exclude deleted steps, we use "all remaining non-deleted" instead.

### Step 6 — Routes in `routers/api_v1/tasks.py`

Add imports:
```python
from beyo_manager.services.commands.task_steps.add_step_dependency import add_step_dependency
from beyo_manager.services.commands.task_steps.remove_step_dependency import remove_step_dependency
from beyo_manager.services.commands.task_steps.remove_task_step import remove_task_step
```

Body models:
```python
class _AddDependencyBody(BaseModel):
    prerequisite_step_id: str
```

Routes:
```
DELETE "/{task_id}/steps/{step_id}"
    → route_remove_task_step (ADMIN, MANAGER)

POST   "/{task_id}/steps/{step_id}/dependencies"
    → route_add_step_dependency (ADMIN, MANAGER)

DELETE "/{task_id}/steps/{step_id}/dependencies/{dependency_id}"
    → route_remove_step_dependency (ADMIN, MANAGER)
```

---

## Risks and mitigations

- **Risk:** `recalculate_readiness` is a pure synchronous function but is called inside an `async` command. This is correct — it only mutates the ORM object in memory. No `await` is needed.
  **Mitigation:** Step 1 signature is `def recalculate_readiness(step: TaskStep) -> None:` — no `async`.

- **Risk:** CMD-10's in-memory flush state issue with the removed step appearing in `remaining_steps` query.
  **Mitigation:** Step 5 explicitly filters: `remaining_steps = [s for s in remaining_steps if s.client_id != step.client_id]`.

- **Risk:** `completed_dependencies` counter drift — CMD-15 and CMD-10 both decrement `total_dependencies`. If a completed prerequisite was removed, the `completed_dependencies` count would be stale (counting a step that no longer depends on anything). The defensive decrement guard handles this.
  **Mitigation:** Both commands include: `if completed > total: completed = total`.

---

## Validation plan

Save to `backend/tests/tasks/test_dependencies_step_removal.sh`.

```bash
# 1. Add dependency between two steps → step.readiness_status = blocked
# 2. Add dependency where one prerequisite is done → partial (setup: add 2 deps, complete 1)
# 3. Self-loop dependency → 422 ValidationError
# 4. Duplicate active dependency → 409 ConflictError
# 5. Cross-task dependency → 404 (step not found under that task)
# 6. Remove dependency → total_dependencies decremented; readiness recalculated
# 7. Remove step → state=SKIPPED, is_deleted=True, open StepStateRecord closed
# 8. Remove last step from task → task.state = PENDING
# 9. Remove second-to-last step where remaining step is terminal → task.state = READY
# 10. Remove step that was a prerequisite → dependent step's total_dependencies decremented; readiness recalculated
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
