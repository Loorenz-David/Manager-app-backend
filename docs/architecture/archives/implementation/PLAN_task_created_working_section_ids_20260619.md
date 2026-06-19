# PLAN_task_created_working_section_ids_20260619

## Metadata

- Plan ID: `PLAN_task_created_working_section_ids_20260619`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T10:51:38Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Improve task step real-time coverage across three commands: enrich `task:created` with `working_section_ids`, and add `task:step-created` / `task:step-deleted` events when steps are added or removed after task creation.
- Business/user intent: The frontend real-time layer must know both that a task exists and which working sections it touches. Workers and managers need granular step-level signals so section-specific views can filter and react without fetching the full task on every workspace broadcast. Adding or removing steps after task creation currently emits only a generic `task:updated` — step-level events close that gap.
- Non-goals: Changes to `transition_step_state` (already correct), changes to the event bus routing, frontend implementation.

## Scope

- In scope:
  - `create_task.py`: initialize `created_steps` before the conditional block; add `working_section_ids` to `task:created` payload
  - `add_task_steps.py`: add `task:step-created` per new step with `working_section_id` in payload
  - `remove_task_step.py`: add `task:step-deleted` per removed step with `working_section_id`; pass removed steps into `_dispatch_remove_step_events`
  - Event catalog handoff documents: add two new event types, update `task:created` signature, update `ServerToClientEvents` type block and handler matrix
- Out of scope:
  - `transition_step_state.py` — already dispatches `task:step-state-changed` correctly
  - New worker tasks or notification creation
  - Frontend implementation

## Clarifications required

(none)

## Acceptance criteria

1. `task:created` payload is `{ client_id: string; working_section_ids: string[] }` — empty array when created without steps.
2. `add_task_steps` dispatches one `task:step-created` event per new step with `{ client_id, working_section_id }`.
3. `remove_task_step` and `remove_task_steps` each dispatch one `task:step-deleted` event per removed step with `{ client_id, working_section_id }`.
4. Both new event types appear in the `ServerToClientEvents` type block and handler responsibility matrix in both handoff documents.

## Contracts and skills

### Contracts loaded

- `backend/architecture/11_infra_events.md`: `build_workspace_event` / `WorkspaceEvent` extra field contract, dispatch-after-commit rule
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: command pattern, dispatch placement relative to transaction boundary
- `backend/architecture/56_realtime_layer.md`: payload shape rule — `{ client_id, ...extra }`; workspace broadcast routing

### File read intent — pattern vs. relational

Permitted (relational reads):
- Reading each of the three target command files to confirm exact variable names, existing dispatch patterns, and function signatures before editing
- Reading `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md` to locate anchors before editing

## Implementation plan

---

### Step 1 — Edit `create_task.py`

File: `backend/app/beyo_manager/services/commands/tasks/create_task.py`

**Change 1 — initialize `created_steps` before the conditional block.**

Locate inside the `async with maybe_begin(ctx.session):` block:

```python
        if request.steps:
            now = datetime.now(timezone.utc)
            created_steps: list[TaskStep] = []
```

Replace with:

```python
        created_steps: list[TaskStep] = []
        if request.steps:
            now = datetime.now(timezone.utc)
```

(Remove the `created_steps` initialisation from inside the `if` block — it now sits one line above at the same indentation level, so it is always defined even when no steps are provided.)

**Change 2 — pass `working_section_ids` in the dispatch.**

Locate the dispatch at the end of the function:

```python
    await event_bus.dispatch([
        build_workspace_event(task, "task:created"),
    ])
```

Replace with:

```python
    await event_bus.dispatch([
        build_workspace_event(
            task,
            "task:created",
            extra={"working_section_ids": [s.working_section_id for s in created_steps]},
        ),
    ])
```

No new imports needed.

---

### Step 2 — Edit `add_task_steps.py`

File: `backend/app/beyo_manager/services/commands/task_steps/add_task_steps.py`

`WorkspaceEvent` is already imported. No new imports needed.

Locate the dispatch block at the end of the function:

```python
    pending_events: list = [build_workspace_event(task, "task:updated")]
    for step in readiness_changed:
        pending_events.append(
            WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": step.readiness_status.value},
            )
        )
    await event_bus.dispatch(pending_events)
```

Replace with:

```python
    pending_events: list = [build_workspace_event(task, "task:updated")]
    for step in created_steps:
        pending_events.append(
            WorkspaceEvent(
                event_name="task:step-created",
                client_id=step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"working_section_id": step.working_section_id},
            )
        )
    for step in readiness_changed:
        pending_events.append(
            WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": step.readiness_status.value},
            )
        )
    await event_bus.dispatch(pending_events)
```

`created_steps` is already populated in scope at this point in the function.

---

### Step 3 — Edit `remove_task_step.py`

File: `backend/app/beyo_manager/services/commands/task_steps/remove_task_step.py`

**Change 1 — pass `steps_to_remove` out of `_remove_task_steps_in_session`.**

The helper currently returns `tuple[Task, TaskStateEnum, list[tuple[TaskStep, object]]]`. The removed steps (`steps_to_remove`) are local to `_remove_task_steps_in_session` and are not currently returned. Extend the return to include them.

Locate the return statement at the end of `_remove_task_steps_in_session`:

```python
    await ctx.session.flush()
    return task, old_task_state, readiness_changes
```

Replace with:

```python
    await ctx.session.flush()
    return task, old_task_state, readiness_changes, steps_to_remove
```

Update the function return type annotation accordingly:

```python
# BEFORE
async def _remove_task_steps_in_session(
    *,
    ctx: ServiceContext,
    task_id: str,
    step_ids: list[str],
) -> tuple[Task, TaskStateEnum, list[tuple[TaskStep, object]]]:

# AFTER
async def _remove_task_steps_in_session(
    *,
    ctx: ServiceContext,
    task_id: str,
    step_ids: list[str],
) -> tuple[Task, TaskStateEnum, list[tuple[TaskStep, object]], list[TaskStep]]:
```

**Change 2 — extend `_dispatch_remove_step_events` to accept and emit the removed steps.**

Locate the function signature and body:

```python
async def _dispatch_remove_step_events(
    *,
    ctx: ServiceContext,
    task: Task,
    old_task_state: TaskStateEnum,
    readiness_changes: list[tuple[TaskStep, object]],
) -> None:
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
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
```

Replace with:

```python
async def _dispatch_remove_step_events(
    *,
    ctx: ServiceContext,
    task: Task,
    old_task_state: TaskStateEnum,
    readiness_changes: list[tuple[TaskStep, object]],
    removed_steps: list[TaskStep],
) -> None:
    pending_events: list = [
        build_workspace_event(task, "task:updated"),
    ]
    for step in removed_steps:
        pending_events.append(WorkspaceEvent(
            event_name="task:step-deleted",
            client_id=step.client_id,
            workspace_id=ctx.workspace_id,
            extra={"working_section_id": step.working_section_id},
        ))
    for affected_step, old_aff_readiness in readiness_changes:
        if affected_step.readiness_status != old_aff_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=affected_step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": affected_step.readiness_status.value},
            ))
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
```

**Change 3 — update both callers to unpack the new return value and pass `removed_steps`.**

`remove_task_step`:

```python
# BEFORE
async with maybe_begin(ctx.session):
    task, old_task_state, readiness_changes = await _remove_task_steps_in_session(
        ctx=ctx,
        task_id=request.task_id,
        step_ids=[request.step_id],
    )

await _dispatch_remove_step_events(
    ctx=ctx,
    task=task,
    old_task_state=old_task_state,
    readiness_changes=readiness_changes,
)

# AFTER
async with maybe_begin(ctx.session):
    task, old_task_state, readiness_changes, removed_steps = await _remove_task_steps_in_session(
        ctx=ctx,
        task_id=request.task_id,
        step_ids=[request.step_id],
    )

await _dispatch_remove_step_events(
    ctx=ctx,
    task=task,
    old_task_state=old_task_state,
    readiness_changes=readiness_changes,
    removed_steps=removed_steps,
)
```

`remove_task_steps` (bulk variant):

```python
# BEFORE
async with maybe_begin(ctx.session):
    task, old_task_state, readiness_changes = await _remove_task_steps_in_session(
        ctx=ctx,
        task_id=request.task_id,
        step_ids=step_ids,
    )

await _dispatch_remove_step_events(
    ctx=ctx,
    task=task,
    old_task_state=old_task_state,
    readiness_changes=readiness_changes,
)

# AFTER
async with maybe_begin(ctx.session):
    task, old_task_state, readiness_changes, removed_steps = await _remove_task_steps_in_session(
        ctx=ctx,
        task_id=request.task_id,
        step_ids=step_ids,
    )

await _dispatch_remove_step_events(
    ctx=ctx,
    task=task,
    old_task_state=old_task_state,
    readiness_changes=readiness_changes,
    removed_steps=removed_steps,
)
```

No new imports needed — `WorkspaceEvent` is already imported in this file.

---

### Step 4 — Update the event catalog handoff documents

Apply all changes to both files:
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`
- `frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`

#### 4a — Update `task:created` in the Tasks section

**Anchor:**
```
// Task entity created
'task:created': (payload: { client_id: string }) => void;
```

**Replace with:**
```
// Task entity created.
// working_section_ids: client_ids of all working sections the task's initial steps were
// assigned to. Empty array when the task is created without steps.
'task:created': (payload: { client_id: string; working_section_ids: string[] }) => void;
```

#### 4b — Add `task:step-created` and `task:step-deleted` to the Tasks section

**Anchor — insert immediately after the `task:step-state-changed` entry:**
```
// Step transitioned to a new state
'task:step-state-changed': (payload: {
  client_id: string;
  new_state:  string;  // TaskStepStateEnum value — 'pending' | 'working' | 'paused' | 'completed' | etc.
}) => void;
```

**Insert after it:**
```
// A new step was added to an existing task (via add_task_steps, not initial task creation)
// working_section_id: the section this step belongs to — use for section-scoped filtering
'task:step-created': (payload: { client_id: string; working_section_id: string }) => void;

// A step was removed from a task (soft-deleted, set to SKIPPED)
// working_section_id: the section the removed step belonged to
'task:step-deleted': (payload: { client_id: string; working_section_id: string }) => void;
```

#### 4c — Update the `ServerToClientEvents` type block

**Locate:**
```
  'task:created':            (payload: { client_id: string }) => void;
```
**Replace with:**
```
  'task:created':            (payload: { client_id: string; working_section_ids: string[] }) => void;
```

**Locate:**
```
  'task:step-state-changed': (payload: { client_id: string; new_state: string }) => void;
```
**Insert after it:**
```
  'task:step-created':       (payload: { client_id: string; working_section_id: string }) => void;
  'task:step-deleted':       (payload: { client_id: string; working_section_id: string }) => void;
```

#### 4d — Add rows to the handler responsibility matrix

**Anchor — locate:**
```
| `task:step-state-changed` | `features/tasks/socket-events.ts` | Invalidate step detail + task detail |
```

**Insert after it:**
```
| `task:step-created` | `features/tasks/socket-events.ts` | Invalidate task detail (step list); filter by `working_section_id` for section-specific views |
| `task:step-deleted` | `features/tasks/socket-events.ts` | Remove step detail from cache, invalidate task detail; filter by `working_section_id` for section-specific views |
```

---

## Risks and mitigations

- Risk: `created_steps` in `create_task.py` moved outside `if request.steps:` — annotation might confuse type checkers if `TaskStep` import is not at module level.
  Mitigation: `TaskStep` is already imported in `create_task.py` (used for `StepStateRecord` creation). No change needed.

- Risk: `working_section_ids` in `task:created` contains duplicates when two steps share a section.
  Mitigation: The frontend should treat this as "at least one step exists in this section." Deduplication with `new Set()` is trivial at the handler level. Raw list is intentional — it maps one-to-one with the steps created.

- Risk: `_remove_task_steps_in_session` return type change breaks callers.
  Mitigation: There are exactly two callers (`remove_task_step` and `remove_task_steps`) both in the same file. Both are updated in Step 3 Change 3. No other files import this private helper.

- Risk: `steps_to_remove` attributes (specifically `working_section_id`) become inaccessible after session commit due to `DetachedInstanceError`.
  Mitigation: `working_section_id` is a scalar column that was loaded when the step was fetched inside the transaction — it lives in the ORM object's `__dict__` and does not require a DB round-trip. Safe to read after commit. This is the same pattern used throughout the codebase (e.g., `iup.item_id` after commit in item commands).

## Validation plan

- `create_task` with steps in two sections → `task:created` payload includes both `working_section_ids`.
- `create_task` without steps → `task:created` payload has `working_section_ids: []`.
- `add_task_steps` adding two steps to different sections → two `task:step-created` events fire, each with the correct `working_section_id`.
- `remove_task_step` removing one step → `task:step-deleted` fires with the correct `client_id` and `working_section_id`.
- `remove_task_steps` removing two steps → two `task:step-deleted` events fire.
- Confirm `task:updated` still fires in all remove/add scenarios.

## Review log

(empty)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `claude-sonnet-4-6`
