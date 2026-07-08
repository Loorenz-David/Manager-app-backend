# PLAN_realtime_event_hooks_20260519

## Metadata

- Plan ID: `PLAN_realtime_event_hooks_20260519`
- Status: `archived`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-19T12:00:00Z`
- Last updated at (UTC): `2026-05-19T08:33:04Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_realtime_event_layer_20260519.md`

---

## Goal and intent

- **Goal:** Wire `event_bus.dispatch()` into all 28 public task and item commands so the frontend receives workspace-scoped WebSocket events after every mutating command commits.
- **Business/user intent:** Multi-user shop floor requires real-time sync. Without events, every user sees stale state until reload. The socket infrastructure is already live; this plan connects the domain commands to it.
- **Non-goals:** Push notification delivery (separate plan). Frontend event handlers. New socket infrastructure. History record creation (separate plan). No new models, no migrations.

---

## Scope

- **In scope:**
  - Add `await event_bus.dispatch(pending_events)` after the `async with maybe_begin` block in 27 command files covering 28 public commands.
  - Update `assign_worker_to_step` return value to expose `worker_id`.
  - Capture readiness before/after `recalculate_readiness()` in `transition_step_state`, `add_step_dependency`, `remove_step_dependency`, `remove_task_step` and emit `task:step-readiness-changed` conditionally.
  - Emit `task:state-changed` from `transition_step_state` and `remove_task_step` when task state changes as a side effect.

- **Out of scope:**
  - Modifying `_create_history_record_in_session` or any session helper.
  - Modifying `_dispatch_section_side_effects` stub — leave as-is.
  - Tests, routers, serializers.

- **Assumptions:**
  - `expire_on_commit=False` is configured on the session factory — entity attributes remain accessible after `async with maybe_begin` exits.
  - `event_bus.dispatch` is async (`async def dispatch(...)`).
  - All task/step/item ORM models have a `workspace_id` column.
  - `ctx.workspace_id` is always set for these commands.

---

## Clarifications required

*(None — all blocking questions resolved before plan creation.)*

---

## Acceptance criteria

1. All 28 commands call `await event_bus.dispatch(pending_events)` after their `async with maybe_begin` block, never inside it.
2. `assign_worker_to_step` returns `{"assignment_id": ..., "worker_id": step.assigned_worker_id}`.
3. `transition_step_state`, `add_step_dependency`, `remove_step_dependency`, `remove_task_step` emit `task:step-readiness-changed` only when readiness actually changes (before ≠ after).
4. `transition_step_state` and `remove_task_step` emit `task:state-changed` when task state changes as a side effect.
5. No command imports `beyo_manager.sockets.manager` or `services.infra.events.realtime_push` directly.
6. Event names match the registry in the intention plan exactly (e.g. `task:state-changed`, not `task:state_changed`).
7. Bulk requirement commands (`mark_requirements_ordered`, `resolve_requirements_after_stock`) skip dispatch when `resolved_ids` is empty.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layer boundaries — events dispatched from command layer only
- `backend/architecture/04_context.md`: `ctx.workspace_id`, `ctx.user_id`, `ctx.identity` shape
- `backend/architecture/06_commands.md`: commands structure, `maybe_begin` transaction pattern
- `backend/architecture/11_infra_events.md`: event bus — `dispatch` after commit, never inside transaction; handler registration; `WorkspaceEvent` / `build_workspace_event` usage
- `backend/architecture/13_sockets.md`: event name convention `<domain>:<verb>`, payload rules, `push_workspace_refresh` vs `push_workspace_batch` routing

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` transaction utility; session call safety rules

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`11_infra_events.md`, `13_sockets.md`)
- **What exists** → reading is legitimate

Permitted relational reads (already done in planning):
- All 27 command files — to identify entity variables, workspace_id source, and return values
- `services/infra/events/build_event.py` — exact function signatures
- `services/infra/events/event_bus.py` — confirmed `async def dispatch`
- `services/infra/events/domain_event.py` — `WorkspaceEvent` fields

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

---

## Cross-cutting rules (apply to every step)

### Imports to add (declare once per file, at the top of existing imports)

**Every command file in this plan gets:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**Commands that construct `WorkspaceEvent` directly also get:**
```python
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```
*(Which files need `WorkspaceEvent` is stated explicitly in each step.)*

### Dispatch placement rule

`await event_bus.dispatch(pending_events)` is **always** placed **after** the `async with maybe_begin(ctx.session):` block closes and **before** the `return` statement. Never inside the `async with` block.

### Entity and workspace_id resolution

| Situation | Use |
|---|---|
| Entity ORM object loaded, has `workspace_id` | `build_workspace_event(entity, "event:name", extra={...})` |
| Only a string `client_id` available (no entity object) | `WorkspaceEvent(event_name=..., client_id=string, workspace_id=ctx.workspace_id, extra={...})` |
| Event about a parent entity (e.g. task) but only child loaded | `WorkspaceEvent(event_name="task:updated", client_id=child.task_id, workspace_id=ctx.workspace_id, extra={})` |
| Batch — multiple entity IDs changed | `WorkspaceEvent(event_name=..., client_id="", workspace_id=ctx.workspace_id, extra={"ids": id_list, ...})` |

### `build_workspace_event` signature

```python
build_workspace_event(
    entity,           # ORM object with .client_id and optionally .workspace_id
    event_name: str,
    *,
    workspace_id: str | None = None,   # falls back to entity.workspace_id
    extra: dict | None = None,
) -> WorkspaceEvent
```

---

## Implementation plan

---

### Step 1 — `services/commands/tasks/create_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:created"),
    ])
    return {"client_id": task.client_id, "task_scalar_id": task.task_scalar_id}
```

*`task.workspace_id` is set in the constructor (`workspace_id=ctx.workspace_id`). Accessible after the block because `expire_on_commit=False`.*

---

### Step 2 — `services/commands/tasks/update_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": task.client_id}
```

---

### Step 3 — `services/commands/tasks/delete_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:deleted"),
    ])
    return {"client_id": task.client_id}
```

---

### Step 4 — `services/commands/tasks/cancel_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:state-changed", extra={"new_state": TaskStateEnum.CANCELLED.value}),
    ])
    return {"client_id": task.client_id}
```

*`TaskStateEnum` is already imported in this file.*

---

### Step 5 — `services/commands/tasks/resolve_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:state-changed", extra={"new_state": TaskStateEnum.RESOLVED.value}),
    ])
    return {"client_id": task.client_id}
```

---

### Step 6 — `services/commands/tasks/fail_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:state-changed", extra={"new_state": TaskStateEnum.FAILED.value}),
    ])
    return {"client_id": task.client_id}
```

---

### Step 7 — `services/commands/tasks/add_item_to_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": task_item.client_id}
```

*`task` is fetched and validated inside the block and is accessible after it.*

---

### Step 8 — `services/commands/tasks/remove_item_from_task.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`task` is NOT fetched in this command. Use `task_item.task_id` (the task's `client_id`) and `ctx.workspace_id`.

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=task_item.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": task_item.client_id}
```

---

### Step 9 — `services/commands/tasks/create_task_note.py`

**Imports to add** (in the public `create_task_note` function's file — top-level imports):
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block in `create_task_note` (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": note.client_id}
```

*`task` is fetched inside the block and accessible after. Do NOT modify `_create_task_note_in_session`.*

---

### Step 10 — `services/commands/tasks/update_task_note.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`task` is NOT fetched in this command. Use `note.task_id` (the task's `client_id`) and `ctx.workspace_id`.

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=note.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": note.client_id}
```

---

### Step 11 — `services/commands/tasks/delete_task_note.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=note.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": note.client_id}
```

---

### Step 12 — `services/commands/task_steps/transition_step_state.py`

This command has three possible event emissions:
1. **Always:** `task:step-state-changed` for the step.
2. **Conditionally:** `task:step-readiness-changed` for each dependent step whose `readiness_status` actually changed.
3. **Conditionally:** `task:state-changed` for the task if its state changed as a side effect (ASSIGNED → WORKING, or all steps terminal → READY).

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**Before `async with maybe_begin(ctx.session):` add these two lines:**
```python
    readiness_changes: list[tuple] = []
    old_task_state = None
```

**Inside `async with maybe_begin(ctx.session):`, immediately after the `task` null-check (after `if task is None: raise NotFound(...)`):**
```python
        old_task_state = task.state
```

**Inside the `if request.new_state == TaskStepStateEnum.COMPLETED:` branch, replace the inner loop body:**

Current code:
```python
                if dep_step is not None:
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)
```

Replace with:
```python
                if dep_step is not None:
                    old_dep_readiness = dep_step.readiness_status
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)
                    readiness_changes.append((dep_step, old_dep_readiness))
```

**After the `async with maybe_begin(ctx.session):` block closes (before `return`):**
```python
    pending_events: list = [
        build_workspace_event(step, "task:step-state-changed", extra={"new_state": request.new_state.value}),
    ]
    for dep_step, old_dep_readiness in readiness_changes:
        if dep_step.readiness_status != old_dep_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=dep_step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": dep_step.readiness_status.value},
            ))
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
    return {"step_id": step.client_id, "new_state": request.new_state.value}
```

*Do NOT modify `_dispatch_section_side_effects` — leave the empty stub as-is.*
*`step.workspace_id` is set, so `build_workspace_event(step, ...)` auto-detects it.*

---

### Step 13 — `services/commands/task_steps/assign_worker_to_step.py`

Two changes: add event dispatch AND update the return value to include `worker_id`.

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(step, "task:step-assigned", extra={"user_id": step.assigned_worker_id}),
    ])
    return {"assignment_id": new_assignment.client_id, "worker_id": step.assigned_worker_id}
```

*`step.assigned_worker_id` is set by `_assign_worker_to_step_in_session` before the block exits.*
*`step.workspace_id` is set, so `build_workspace_event(step, ...)` auto-detects workspace_id.*
*The return value gains `"worker_id"` — this is a non-breaking addition.*

---

### Step 14 — `services/commands/task_steps/add_task_step.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

The event is about the TASK (not the step), using `request.task_id` as `client_id`.

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=request.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"step_id": step.client_id}
```

---

### Step 15 — `services/commands/task_steps/remove_task_step.py`

Three possible event emissions:
1. **Always:** `task:updated` for the task.
2. **Conditionally:** `task:step-readiness-changed` for affected steps whose readiness changed.
3. **Conditionally:** `task:state-changed` if task state changed (to PENDING or READY).

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**Before `async with maybe_begin(ctx.session):` add:**
```python
    readiness_changes: list[tuple] = []
    old_task_state_rts = None
```

**Inside `async with maybe_begin(ctx.session):`, immediately after `task` null-check:**
```python
        old_task_state_rts = task.state
```

**Inside the prerequisite-edges loop (step 6b), replace the inner block body:**

Current code:
```python
            if affected_step is not None:
                if affected_step.total_dependencies > 0:
                    affected_step.total_dependencies -= 1
                if affected_step.completed_dependencies > affected_step.total_dependencies:
                    affected_step.completed_dependencies = affected_step.total_dependencies
                recalculate_readiness(affected_step)
```

Replace with:
```python
            if affected_step is not None:
                old_aff_readiness = affected_step.readiness_status
                if affected_step.total_dependencies > 0:
                    affected_step.total_dependencies -= 1
                if affected_step.completed_dependencies > affected_step.total_dependencies:
                    affected_step.completed_dependencies = affected_step.total_dependencies
                recalculate_readiness(affected_step)
                readiness_changes.append((affected_step, old_aff_readiness))
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    pending_events: list = [
        build_workspace_event(task, "task:updated"),
    ]
    for affected_step, old_aff_readiness in readiness_changes:
        if affected_step.readiness_status != old_aff_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=affected_step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": affected_step.readiness_status.value},
            ))
    if task.state != old_task_state_rts:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
    return {"step_id": step.client_id}
```

---

### Step 16 — `services/commands/task_steps/add_step_dependency.py`

Two possible event emissions:
1. **Always:** `task:updated` for the task (dependency graph changed).
2. **Conditionally:** `task:step-readiness-changed` if `dependent_step.readiness_status` changed after `recalculate_readiness`.

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**Before `async with maybe_begin(ctx.session):` add:**
```python
    old_readiness = None
```

**Inside `async with maybe_begin(ctx.session):`, immediately before `recalculate_readiness(dependent_step)`:**
```python
        old_readiness = dependent_step.readiness_status
        dependent_step.total_dependencies += 1
        recalculate_readiness(dependent_step)
```
*(This replaces the existing two-line block `dependent_step.total_dependencies += 1` / `recalculate_readiness(dependent_step)` with the same two lines plus the capture line above them.)*

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    pending_events: list = [
        WorkspaceEvent(
            event_name="task:updated",
            client_id=dependent_step.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ]
    if old_readiness is not None and dependent_step.readiness_status != old_readiness:
        pending_events.append(WorkspaceEvent(
            event_name="task:step-readiness-changed",
            client_id=dependent_step.client_id,
            workspace_id=ctx.workspace_id,
            extra={"new_readiness": dependent_step.readiness_status.value},
        ))
    await event_bus.dispatch(pending_events)
    return {"dependency_id": edge.client_id}
```

---

### Step 17 — `services/commands/task_steps/remove_step_dependency.py`

Two possible event emissions:
1. **Conditionally (step not None):** `task:updated` and optionally `task:step-readiness-changed`.
2. **If step is None (already soft-deleted):** skip dispatch entirely — the task was already notified when the step was deleted.

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**Before `async with maybe_begin(ctx.session):` add:**
```python
    old_readiness = None
```

**Inside `async with maybe_begin(ctx.session):`, inside `if step is not None:`, immediately before the existing decrement lines:**
```python
        if step is not None:
            old_readiness = step.readiness_status
            if step.total_dependencies > 0:
                step.total_dependencies -= 1
            if step.completed_dependencies > step.total_dependencies:
                step.completed_dependencies = step.total_dependencies
            recalculate_readiness(step)
```
*(Add `old_readiness = step.readiness_status` as the first line inside `if step is not None:`.)*

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    if step is not None:
        pending_events: list = [
            WorkspaceEvent(
                event_name="task:updated",
                client_id=step.task_id,
                workspace_id=ctx.workspace_id,
                extra={},
            ),
        ]
        if old_readiness is not None and step.readiness_status != old_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": step.readiness_status.value},
            ))
        await event_bus.dispatch(pending_events)
    return {"dependency_id": edge.client_id}
```

---

### Step 18 — `services/commands/task_steps/mark_step_time_inaccurate.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

The event is about the TASK (not the step record), using `step.task_id` as `client_id`.

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=step.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"record_id": record.client_id}
```

---

### Step 19 — `services/commands/items/create_item.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(item, "item:created"),
    ])
    return {"client_id": item.client_id}
```

---

### Step 20 — `services/commands/items/update_item.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(item, "item:updated"),
    ])
    return {"client_id": item.client_id}
```

---

### Step 21 — `services/commands/items/delete_item.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    await event_bus.dispatch([
        build_workspace_event(item, "item:deleted"),
    ])
    return {}
```

---

### Step 22 — `services/commands/items/create_item_upholstery.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`iup_client_id` is a string, not an entity object. The event signals that the ITEM was updated (an upholstery was added to it). Use `request.item_id` as `client_id`.

**After `async with maybe_begin(ctx.session):` block in `create_item_upholstery` (before `return`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=request.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": iup_client_id}
```

*Do NOT modify `_create_item_upholstery_in_session`.*

---

### Step 23 — `services/commands/items/update_and_delete_item_upholstery.py`

This file contains two public commands: `update_item_upholstery` and `delete_item_upholstery`. Both get dispatch calls. The event signals that the parent ITEM was updated.

**Imports to add (once, at the top of the file):**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**`update_item_upholstery` — after `async with maybe_begin(ctx.session):` block (before `return {}`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=iup.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}
```

**`delete_item_upholstery` — after `async with maybe_begin(ctx.session):` block (before `return {}`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=iup.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}
```

*`iup.item_id` is available after the block (expire_on_commit=False).*

---

### Step 24 — `services/commands/items/mark_requirements_completed.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`ItemUpholsteryRequirementStateEnum` is already imported in this file.

**After `async with maybe_begin(ctx.session):` block (before `return {}`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:upholstery-requirement-state-changed",
            client_id=request.item_upholstery_id,
            workspace_id=ctx.workspace_id,
            extra={"new_state": ItemUpholsteryRequirementStateEnum.COMPLETED.value},
        ),
    ])
    return {}
```

---

### Step 25 — `services/commands/items/mark_requirements_in_use.py`

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`ItemUpholsteryRequirementStateEnum` is already imported in this file.

**After `async with maybe_begin(ctx.session):` block (before `return {}`):**
```python
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:upholstery-requirement-state-changed",
            client_id=request.item_upholstery_id,
            workspace_id=ctx.workspace_id,
            extra={"new_state": ItemUpholsteryRequirementStateEnum.IN_USE.value},
        ),
    ])
    return {}
```

---

### Step 26 — `services/commands/items/mark_requirements_ordered.py`

Multiple item upholsteries may be affected. Dispatch a batch event only if any were resolved. `result_dict["resolved"]` is a list of `item_upholstery_id` strings.

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`ItemUpholsteryRequirementStateEnum` is already imported in this file.

`result_dict` is defined inside the `async with` block but is in function scope in Python — accessible after the block exits.

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    resolved_ids = result_dict["resolved"]
    if resolved_ids:
        await event_bus.dispatch([
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={"ids": resolved_ids, "new_state": ItemUpholsteryRequirementStateEnum.ORDERED.value},
            ),
        ])
    return {"ordered": result_dict["resolved"], "unordered": result_dict["unresolved"]}
```

*When `"ids"` is present in `extra`, the socket handler routes through `push_workspace_batch` instead of `push_workspace_refresh`. No `client_id` is needed for batch events — pass `""`.*

---

### Step 27 — `services/commands/items/resolve_requirements_after_stock.py`

Multiple item upholsteries may be resolved to `AVAILABLE`. Same batch pattern as Step 26.

**Imports to add:**
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`ItemUpholsteryRequirementStateEnum` is already imported in this file.

`result_dict` is defined inside the `async with` block but accessible after (Python function scope).

**After `async with maybe_begin(ctx.session):` block (before `return`):**
```python
    resolved_ids = result_dict["resolved"]
    if resolved_ids:
        await event_bus.dispatch([
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={"ids": resolved_ids, "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value},
            ),
        ])
    return {"resolved": result_dict["resolved"], "unresolved": result_dict["unresolved"]}
```

*Early-return guard already in place: `if not candidates: return {"resolved": [], "unresolved": []}` exits before the `async with` block, so there is no `result_dict` to reference. The dispatch code is after the block, which is only reached when candidates exist.*

---

## Risks and mitigations

- **Risk:** `event_bus.dispatch` called inside the `async with` block (before commit).
  **Mitigation:** All steps in this plan explicitly place dispatch after the block. Code reviewer must verify position.

- **Risk:** `result_dict` referenced outside the `async with` block in steps 26–27 but defined inside.
  **Mitigation:** Python `async with` does not create a new scope — the variable is in function scope. Verified from language spec.

- **Risk:** `task` or `step` attributes expire after commit if `expire_on_commit=True`.
  **Mitigation:** Session factory has `expire_on_commit=False` (confirmed). Attributes remain accessible after block exits.

- **Risk:** `old_readiness` unset if exception raised before `recalculate_readiness` call.
  **Mitigation:** All NotFound / ConflictError exceptions propagate immediately and never reach post-block dispatch code. No guard needed.

- **Risk:** Double `task:state-changed` event in `transition_step_state` (once from the step transition, once from task state change).
  **Mitigation:** `task:step-state-changed` and `task:state-changed` are distinct event names — the frontend handles them independently. No deduplication needed.

---

## Validation plan

- `grep -rn "event_bus.dispatch" backend/app/beyo_manager/services/commands/tasks/`: expect 11 matches (one per task command file).
- `grep -rn "event_bus.dispatch" backend/app/beyo_manager/services/commands/task_steps/`: expect 7 matches.
- `grep -rn "event_bus.dispatch" backend/app/beyo_manager/services/commands/items/`: expect 9 matches across create/update/delete/upholstery/requirements files.
- `grep -rn "manager\|realtime_push" backend/app/beyo_manager/services/commands/`: expect zero matches — commands must not import these.
- Manual smoke test: create a task, observe `task:created` event on WebSocket; cancel it, observe `task:state-changed` with `new_state=cancelled`.
- Manual smoke test: transition a step to COMPLETED when it unblocks a dependent → observe `task:step-state-changed` + `task:step-readiness-changed` on WebSocket.

---

## Review log

*(Empty — no reviews yet.)*

---

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `David Loorenz`
