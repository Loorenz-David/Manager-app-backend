# PLAN_sync_step_deps_on_section_edit_20260518

## Metadata

- Plan ID: `PLAN_sync_step_deps_on_section_edit_20260518`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-19T09:30:00Z`
- Related issue/ticket: `working-section-dep-sync`
- Intention plan: _none — derived from task step readiness correctness requirement_

---

## Goal and intent

- **Goal:** When `edit_working_section` changes `working_section_dependencies` for section S, atomically propagate that change to all active `TaskStepDependency` edges for task steps that belong to section S, then recalculate `readiness_status` for every affected dependent step within the same database transaction.
- **Business/user intent:** Working section dependencies encode the order in which repair work must be done (e.g. upholstery must finish before assembly). Task steps inherit this ordering as explicit `TaskStepDependency` edges. When the section graph is reconfigured, existing active steps must immediately reflect the new reality — a step that was BLOCKED because of a dependency that no longer exists should become READY; a step that has a new prerequisite that hasn't completed yet should become BLOCKED or PARTIAL.
- **Non-goals:** Steps that are deleted (`is_deleted = True`) or in a terminal state (`COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`) — their history is immutable. Creating task steps for sections that a task doesn't yet have a step for — we only update edges between steps that already exist. Migrating past terminal-step history.

---

## Prerequisite

None. This plan is self-contained.

---

## Scope

- **In scope:**
  - NEW: `services/commands/working_sections/_sync_step_dependencies.py` — session-level helper (no transaction ownership)
  - MODIFY: `services/commands/working_sections/edit_working_section.py` — capture old deps, compute diff, call helper inside existing transaction
- **Out of scope:** New router, new command, migrations (no schema changes needed)
- **Assumptions:**
  - `edit_working_section` owns its transaction via `async with ctx.session.begin()` — the new helper must NOT open another transaction (session-helper pattern, same as `_create_task_note_in_session`)
  - A task may theoretically have more than one step per working section (no unique constraint). The sync handles this correctly by operating on all matching (dep_step, prereq_step) pairs within the same task.
  - `TaskStepDependency` uses soft-delete (`removed_at`). Adding a dependency creates a new row; removing soft-deletes it.
  - The `_TERMINAL_STEP_STATES` frozenset is `{COMPLETED, SKIPPED, FAILED, CANCELLED}` — same definition as in `transition_step_state.py`. Define it locally in the new helper; do NOT import from `transition_step_state.py`.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. After editing section S's dependencies to add section C: every active (non-deleted, non-terminal) task step in section S that shares a task with an active step in section C gains a new active `TaskStepDependency` edge pointing to that step in C.
2. If the prerequisite step in C is already `COMPLETED`, the dependent step's `completed_dependencies` is incremented immediately so readiness reflects the true state.
3. After editing section S's dependencies to remove section R: every active `TaskStepDependency` edge whose dependent step is in section S and whose prerequisite step is in section R is soft-deleted (`removed_at` set). The dependent step's `total_dependencies` is decremented (floored at 0) and `completed_dependencies` is capped at `total_dependencies`. Readiness is recalculated.
4. Both the section dependency change and the step dependency sync are committed atomically — if either fails, neither is committed.
5. Steps that are deleted or in terminal states are never touched.
6. If an active edge already exists between a (dep_step, prereq_step) pair when adding a new section dependency, no duplicate edge is created (guard check).
7. If the set of section dependencies does not change (same old and new), the sync helper is not called (no wasted queries).
8. `recalculate_readiness` is called on every affected dependent step using the existing helper from `_readiness.py`.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: session-helper pattern (no `maybe_begin`), `session.flush()` usage, error raising
- `backend/architecture/05_errors.md`: error classes (none raised in the helper itself — errors from the parent command are sufficient)
- `backend/architecture/21_naming_conventions.md`: `_verb_noun_in_session` naming for session helpers, `_SCREAMING_SNAKE` for module-level constants

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: confirms session-helper pattern — functions called inside a parent `maybe_begin` or `session.begin()` block must not open their own transaction

### File read intent — pattern vs. relational

Permitted relational reads (understanding what exists):

| File | What to extract |
|---|---|
| `services/commands/task_steps/_readiness.py` | `recalculate_readiness` signature and import path |
| `services/commands/task_steps/add_step_dependency.py` | How `total_dependencies` counter is incremented and readiness called |
| `services/commands/task_steps/remove_step_dependency.py` | How `total_dependencies`/`completed_dependencies` are decremented and capped |
| `services/commands/task_steps/transition_step_state.py` | `_TERMINAL_STEP_STATES` values and how `completed_dependencies` is credited on COMPLETED |
| `services/commands/working_sections/edit_working_section.py` | Exact location of the `working_section_dependencies` diff block to know where to inject code |
| `models/tables/tasks/task_step.py` | Field names: `working_section_id`, `state`, `is_deleted`, `total_dependencies`, `completed_dependencies` |
| `models/tables/tasks/task_step_dependency.py` | Field names: `dependent_step_id`, `prerequisite_step_id`, `removed_at`, `removed_by_id`, `workspace_id` |
| `models/tables/working_sections/working_section_dependency.py` | Field names: `dependent_section_id`, `prerequisite_section_id` |
| `domain/task_steps/enums.py` | `TaskStepStateEnum` values — confirm terminal states |

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`

---

## Implementation plan

### Step 0 — Capture old deps and compute diff in `edit_working_section.py`

Inside the `if "working_section_dependencies" in request.model_fields_set:` block, **before** the `delete(WorkingSectionDependency)` call, add a query to capture the current set of prerequisite section IDs:

```python
old_dep_rows = await ctx.session.execute(
    select(WorkingSectionDependency.prerequisite_section_id).where(
        WorkingSectionDependency.workspace_id == ctx.workspace_id,
        WorkingSectionDependency.dependent_section_id == request.client_id,
    )
)
old_dep_ids: set[str] = set(old_dep_rows.scalars().all())
```

After the existing `delete` + `ctx.session.add` loop that recreates the section dependency records, add:

```python
new_dep_ids_set: set[str] = set(dep_ids)
added_section_ids = new_dep_ids_set - old_dep_ids
removed_section_ids = old_dep_ids - new_dep_ids_set

if added_section_ids or removed_section_ids:
    await _sync_step_dependencies_for_section_in_session(
        session=ctx.session,
        workspace_id=ctx.workspace_id,
        dependent_section_id=request.client_id,
        added_section_ids=added_section_ids,
        removed_section_ids=removed_section_ids,
        user_id=ctx.user_id,
    )
```

This is still inside `async with ctx.session.begin()` — no new transaction opened.

**Import to add:**
```python
from beyo_manager.services.commands.working_sections._sync_step_dependencies import (
    _sync_step_dependencies_for_section_in_session,
)
```

**Edge case — empty new deps:** When `dep_ids = []` (all dependencies removed), the block currently skips the validation/lookup but still runs the `delete`. In this case `new_dep_ids_set = set()`, so `removed_section_ids = old_dep_ids` (everything) and `added_section_ids = set()`. The sync handles this correctly.

The existing code already skips the `dep_ids_found` validation when `dep_ids` is empty, so no change is needed there.

---

### Step 1 — Create `_sync_step_dependencies.py`

**File:** `beyo_manager/services/commands/working_sections/_sync_step_dependencies.py`

```python
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness

_TERMINAL_STEP_STATES = frozenset({
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
    TaskStepStateEnum.CANCELLED,
})


async def _sync_step_dependencies_for_section_in_session(
    session: AsyncSession,
    workspace_id: str,
    dependent_section_id: str,
    added_section_ids: set[str],
    removed_section_ids: set[str],
    user_id: str,
) -> None:
    now = datetime.now(timezone.utc)

    # --- REMOVE PATH ---
    if removed_section_ids:
        await _remove_edges_for_sections(
            session, workspace_id, dependent_section_id, removed_section_ids, now, user_id,
        )

    # --- ADD PATH ---
    if added_section_ids:
        await _add_edges_for_sections(
            session, workspace_id, dependent_section_id, added_section_ids, now, user_id,
        )
```

#### Sub-function: `_remove_edges_for_sections`

Uses two SQLAlchemy aliases for `TaskStep` to join dep and prereq sides:

```python
async def _remove_edges_for_sections(
    session, workspace_id, dependent_section_id, removed_section_ids, now, user_id,
):
    DepStep = aliased(TaskStep)
    PrereqStep = aliased(TaskStep)

    rows = (await session.execute(
        select(TaskStepDependency, DepStep)
        .join(DepStep, and_(
            DepStep.client_id == TaskStepDependency.dependent_step_id,
            DepStep.workspace_id == workspace_id,
            DepStep.working_section_id == dependent_section_id,
            DepStep.is_deleted.is_(False),
            DepStep.state.notin_(_TERMINAL_STEP_STATES),
        ))
        .join(PrereqStep, and_(
            PrereqStep.client_id == TaskStepDependency.prerequisite_step_id,
            PrereqStep.workspace_id == workspace_id,
            PrereqStep.working_section_id.in_(removed_section_ids),
            PrereqStep.is_deleted.is_(False),
        ))
        .where(
            TaskStepDependency.workspace_id == workspace_id,
            TaskStepDependency.removed_at.is_(None),
        )
    )).all()

    for edge, dep_step in rows:
        edge.removed_at = now
        edge.removed_by_id = user_id
        dep_step.total_dependencies = max(dep_step.total_dependencies - 1, 0)
        if dep_step.completed_dependencies > dep_step.total_dependencies:
            dep_step.completed_dependencies = dep_step.total_dependencies
        recalculate_readiness(dep_step)

    await session.flush()
```

#### Sub-function: `_add_edges_for_sections`

Self-join on `task_steps` to find all (dep_step, prereq_step) pairs within the same task, then batch-check for existing active edges to avoid duplicates:

```python
async def _add_edges_for_sections(
    session, workspace_id, dependent_section_id, added_section_ids, now, user_id,
):
    DepStep = aliased(TaskStep)
    PrereqStep = aliased(TaskStep)

    pairs = (await session.execute(
        select(DepStep, PrereqStep)
        .join(PrereqStep, and_(
            PrereqStep.task_id == DepStep.task_id,
            PrereqStep.workspace_id == workspace_id,
            PrereqStep.working_section_id.in_(added_section_ids),
            PrereqStep.is_deleted.is_(False),
        ))
        .where(
            DepStep.workspace_id == workspace_id,
            DepStep.working_section_id == dependent_section_id,
            DepStep.is_deleted.is_(False),
            DepStep.state.notin_(_TERMINAL_STEP_STATES),
        )
    )).all()

    if not pairs:
        return

    dep_step_ids = [dep_step.client_id for dep_step, _ in pairs]

    # Batch guard: collect all already-active edges for these dep steps
    existing_rows = (await session.execute(
        select(
            TaskStepDependency.dependent_step_id,
            TaskStepDependency.prerequisite_step_id,
        )
        .where(
            TaskStepDependency.workspace_id == workspace_id,
            TaskStepDependency.dependent_step_id.in_(dep_step_ids),
            TaskStepDependency.removed_at.is_(None),
        )
    )).all()
    existing_active: set[tuple[str, str]] = {(r[0], r[1]) for r in existing_rows}

    for dep_step, prereq_step in pairs:
        key = (dep_step.client_id, prereq_step.client_id)
        if key in existing_active:
            continue

        edge = TaskStepDependency(
            workspace_id=workspace_id,
            dependent_step_id=dep_step.client_id,
            prerequisite_step_id=prereq_step.client_id,
            created_by_id=user_id,
        )
        session.add(edge)
        existing_active.add(key)  # prevent duplicate within same batch

        dep_step.total_dependencies += 1
        # Credit immediately if the prerequisite step is already completed
        if prereq_step.state == TaskStepStateEnum.COMPLETED:
            dep_step.completed_dependencies += 1
        recalculate_readiness(dep_step)

    await session.flush()
```

---

## Critical implementation notes

### No transaction ownership in the helper

The helper does NOT use `maybe_begin`, `session.begin()`, or any transaction context manager. It relies entirely on the caller's transaction (`edit_working_section` owns `async with ctx.session.begin()`). This is the standard session-helper pattern.

### `aliased` is required

Two joins to the same `task_steps` table require `sqlalchemy.orm.aliased`. Without it, SQLAlchemy cannot distinguish the dep side from the prereq side.

### Counter integrity

- `total_dependencies` must never go below 0 — use `max(x - 1, 0)`.
- `completed_dependencies` must never exceed `total_dependencies` — cap with `min(completed, total)` after decrement.
- Call `recalculate_readiness(dep_step)` AFTER updating both counters.

### Prerequisite step credit rule

Only `TaskStepStateEnum.COMPLETED` triggers a `completed_dependencies` credit. `SKIPPED`, `FAILED`, and `CANCELLED` do NOT — a skipped/failed prerequisite does not unblock its dependents (consistent with `transition_step_state.py` which only increments on COMPLETED).

### In-batch deduplication

The `existing_active` set is updated inside the loop with `.add(key)` to prevent creating two edges for the same (dep_step, prereq_step) pair within the same sync batch (e.g. if `added_section_ids` somehow included two sections that resolve to the same step pair — this is a defensive guard).

### Scale

This is an admin operation (editing workspace configuration), not a hot path. The implementation uses two queries per path (one for the join, one for the batch guard), not N+1. This is acceptable.

---

## Risks and mitigations

- **Risk:** A task has two steps in the same prerequisite section (unusual but not forbidden). Both would be linked as prerequisites to the dependent step.
  **Mitigation:** This is correct behavior — if a task has two steps in section C and one step in section S, then step_S gains two dependency edges. The counter correctly increments by 2. The partial unique index prevents duplicates.

- **Risk:** `aliased` joins produce incorrect ORM object hydration — SQLAlchemy may hydrate both aliases into the same identity-map slot.
  **Mitigation:** Use `aliased(TaskStep)` (not `aliased(TaskStep, flat=True)`) and extract separate columns in `select(DepStep, PrereqStep)`. SQLAlchemy correctly tracks aliased instances in the result rows.

- **Risk:** The old dep capture (Step 0) runs a query inside `session.begin()` before the delete. If the section has no existing deps, it returns an empty set — `removed_section_ids` will be empty and the helper is skipped. This is correct.

- **Risk:** Concurrent edits to the same section while the sync is running.
  **Mitigation:** `edit_working_section` already holds the transaction lock. Concurrent transactions will wait. No additional locking needed.

---

## Validation plan

```
# 1. Set up: workspace with sections A, B, C. A depends on B.
#    Create task with step_A and step_B. step_A should have 1 dependency edge to step_B.
#    step_A.total_dependencies == 1, readiness_status == BLOCKED.

# 2. Edit section A to remove dependency on B (new deps: []).
#    After edit: TaskStepDependency edge step_A→step_B has removed_at set.
#    step_A.total_dependencies == 0, readiness_status == READY.

# 3. Edit section A to add dependency on C (new deps: [C]).
#    Task has step_C (not yet completed).
#    After edit: new active TaskStepDependency edge step_A→step_C created.
#    step_A.total_dependencies == 1, completed_dependencies == 0, readiness_status == BLOCKED.

# 4. Same as 3 but step_C is already in state COMPLETED.
#    After edit: edge created AND step_A.completed_dependencies == 1.
#    readiness_status == READY.

# 5. Edit section A to add dependency on C when step_A→step_C edge already exists (active).
#    Guard check prevents duplicate. total_dependencies not double-incremented.

# 6. Edit section A with no change to dependencies (same old and new set).
#    `if added_section_ids or removed_section_ids:` is False. No sync queries fired.

# 7. Task with step_A in terminal state COMPLETED.
#    Edit adds dependency on C. step_A must NOT get a new edge (notin terminal states filter).

# 8. Task has NO step for section C. Edit adds C as dependency.
#    No edge created (join returns no pairs). No error.

# 9. After sync, verify `readiness_status` is consistent with counters:
#    total=0 → READY, total>0 and completed==0 → BLOCKED, 0<completed<total → PARTIAL,
#    completed==total>0 → READY.
```

---

## Review log

- `2026-05-19T09:10:00Z` — implementation started after contract and relational read pass.
- `2026-05-19T09:18:00Z` — added `working_sections/_sync_step_dependencies.py` session helper.
- `2026-05-19T09:22:00Z` — integrated old/new dependency diff and sync call in `edit_working_section.py`.
- `2026-05-19T09:26:00Z` — validation: `.venv/bin/python -m py_compile` on touched files passed.
- `2026-05-19T09:30:00Z` — summary and archive artifacts created; plan moved to archive path.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `copilot`
