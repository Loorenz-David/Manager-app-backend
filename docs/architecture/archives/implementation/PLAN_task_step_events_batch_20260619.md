# PLAN_task_step_events_batch_20260619

## Metadata

- Plan ID: `PLAN_task_step_events_batch_20260619`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T18:48:21Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Convert all step-level socket events (`task:step-created`, `task:step-deleted`, `task:step-state-changed`, `task:step-readiness-changed`) from one-event-per-step to a single batch event per operation, and add a `task:step-created` batch emission to `create_task`.
- Business/user intent: When a user creates or modifies multiple steps in one operation the frontend currently receives N separate socket events and must re-render N times. A single batch event lets the frontend invalidate lists in one pass without intermediate flicker or redundant queries.
- Non-goals: Changing the shape of task-level events (`task:updated`, `task:state-changed`, `task:created`) — they are already single-entity events and remain unchanged.

## Scope

- In scope:
  - New `BatchWorkspaceEvent` dataclass in `domain_event.py`.
  - New `broadcast_items_to_room` method on `ConnectionManager` and matching `push_workspace_event_items` in `realtime_push.py`.
  - `socket_handler.py` routing branch for `BatchWorkspaceEvent`.
  - `event_bus.py` type annotation update to accept `Event | BatchWorkspaceEvent`.
  - `create_task.py`: emit `task:step-created` batch alongside `task:created` when steps are created inline.
  - `add_task_steps.py`: replace per-step `task:step-created` and `task:step-readiness-changed` loop with single `BatchWorkspaceEvent` each.
  - `remove_task_step.py` (`_dispatch_remove_step_events`): replace per-step `task:step-deleted` and `task:step-readiness-changed` loop with single `BatchWorkspaceEvent` each.
  - `transition_step_state.py`: replace per-step `task:step-state-changed` loop (main step + optional auto-paused step) with a single `BatchWorkspaceEvent`.
- Out of scope:
  - Frontend changes (the frontend must adapt to the new list payload — this plan only covers the backend emission).
  - Batching `task:updated` or `task:state-changed` (task-level, always one entity per operation).
  - `task:step-readiness-changed` in `add_step_dependency.py` or `remove_step_dependency.py` (not listed as part of this change; may be a follow-up).
- Assumptions:
  - `python-socketio`'s `sio.emit(event, data, room=room)` accepts a `list` as `data` and serialises it to the correct Socket.IO wire format: `42["event_name",[...]]`.
  - The frontend socket listeners for step events currently expect `{client_id, ...}` (single dict). They must be updated in parallel to expect `[{client_id, ...}, ...]`.

## Clarifications required

- [x] Confirm that `sio.emit` with a `list` payload works as expected in the deployed socket library version — **resolved**: `async_manager.py` line 27 shows `elif data is not None: data = [data]`, which wraps a list into `[data]`. The packet becomes `[event_name] + [[...]]` = `[event_name, [...]]`, producing exactly `42["event_name",[...]]` on the wire. No issue.
- [x] Confirm the frontend is ready to adapt its step-event listeners to accept an array payload before this is deployed — **resolved by user**: frontend changes will be made in parallel; not a deploy blocker.

## Acceptance criteria

1. After `create_task` with `N ≥ 1` steps, exactly one `task:step-created` event is emitted whose payload is a JSON array of N objects, each with `client_id` and `working_section_id`.
2. After `add_task_steps` with `N` steps, the socket stream contains exactly one `task:step-created` event with an array of N objects (no per-step event loop).
3. After `remove_task_step` / `remove_task_steps` with `N` steps, the socket stream contains exactly one `task:step-deleted` event with an array of N objects.
4. After `transition_step_state`, the socket stream contains exactly one `task:step-state-changed` event with an array of 1–2 objects (main step, plus auto-paused step if applicable).
5. Any `task:step-readiness-changed` events in the same operations are also emitted as a single batch.
6. No regression: `task:updated`, `task:state-changed`, `task:created` retain their existing single-object payload shape.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/contracts/09_routers.md`: router wiring pattern (no router changes expected but useful for context)
- `backend/docs/architecture/contracts/06_commands.md`: command pattern, event dispatch convention

### Local extensions loaded

- None required.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add / flush / error-raising` shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`

Permitted (relational reads — understanding what exists):
- Reading `socket_handler.py` to understand routing branches (already done above)
- Reading `domain_event.py`, `event_bus.py`, `realtime_push.py`, `manager.py` to understand the existing push stack (already done)
- Reading the four command files being modified to understand their current dispatch calls (already done)

### Skill selection

- Primary skill: command modification
- Router trigger terms: step, event, batch, socket, dispatch
- Excluded alternatives: none

## Implementation plan

### Step 1 — Add `BatchWorkspaceEvent` to `domain_event.py`

File: `backend/app/beyo_manager/services/infra/events/domain_event.py`

Add a new dataclass. It does **not** inherit from `Event` because it has no single `client_id`:

```python
@dataclass(kw_only=True)
class BatchWorkspaceEvent:
    """Broadcast a list payload to all users in a workspace room."""
    event_name: str
    workspace_id: str
    items: list[dict]
```

---

### Step 2 — Add `broadcast_items_to_room` to `manager.py`

File: `backend/app/beyo_manager/sockets/manager.py`

Add a new method alongside `broadcast_to_room`:

```python
async def broadcast_items_to_room(self, room: str, event: str, items: list[dict]) -> None:
    logger.info("[manager] broadcast_items_to_room | event=%s room=%s count=%d", event, room, len(items))
    await sio.emit(event, items, room=room)
```

---

### Step 3 — Add `push_workspace_event_items` to `realtime_push.py`

File: `backend/app/beyo_manager/services/infra/events/realtime_push.py`

```python
async def push_workspace_event_items(workspace_id: str, event_name: str, items: list[dict]) -> None:
    await manager.broadcast_items_to_room(manager.workspace_room(workspace_id), event_name, items)
```

---

### Step 4 — Update `socket_handler.py` to route `BatchWorkspaceEvent`

File: `backend/app/beyo_manager/services/infra/events/handlers/socket_handler.py`

Import `BatchWorkspaceEvent` and `push_workspace_event_items`. Add the routing branch **before** the existing `WorkspaceEvent` branch (most-specific-first ordering):

```python
elif isinstance(event, BatchWorkspaceEvent):
    logger.info(
        "[socket_handler] BatchWorkspaceEvent | event=%s room=workspace:%s count=%d",
        event.event_name,
        event.workspace_id,
        len(event.items),
    )
    await push_workspace_event_items(event.workspace_id, event.event_name, event.items)
```

---

### Step 5 — Update `event_bus.py` type annotation

File: `backend/app/beyo_manager/services/infra/events/event_bus.py`

Import `BatchWorkspaceEvent`. Update the `dispatch` signature so the type checker accepts both:

```python
from .domain_event import BatchWorkspaceEvent, Event

async def dispatch(events: list[Event | BatchWorkspaceEvent]) -> None:
    for event in events:
        for handler in _handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "event handler failed | event=%s handler=%s",
                    event.event_name,
                    handler.__name__,
                )
```

Note: `client_id` is removed from the log format since `BatchWorkspaceEvent` has none.

---

### Step 6 — Update `create_task.py`

File: `backend/app/beyo_manager/services/commands/tasks/create_task.py`

Import `BatchWorkspaceEvent`. After the transaction, if `created_steps` is non-empty, append a `task:step-created` `BatchWorkspaceEvent` to the dispatch list:

**Current dispatch (line 311–317):**
```python
await event_bus.dispatch([
    build_workspace_event(
        task,
        "task:created",
        extra={"working_section_ids": [step.working_section_id for step in created_steps]},
    ),
])
```

**New dispatch:**
```python
pending_events: list = [
    build_workspace_event(
        task,
        "task:created",
        extra={"working_section_ids": [step.working_section_id for step in created_steps]},
    ),
]
if created_steps:
    pending_events.append(
        BatchWorkspaceEvent(
            event_name="task:step-created",
            workspace_id=ctx.workspace_id,
            items=[
                {"client_id": step.client_id, "working_section_id": step.working_section_id}
                for step in created_steps
            ],
        )
    )
await event_bus.dispatch(pending_events)
```

---

### Step 7 — Update `add_task_steps.py`

File: `backend/app/beyo_manager/services/commands/task_steps/add_task_steps.py`

Import `BatchWorkspaceEvent`. Replace the per-step event loop (lines 164–183) with batch events:

**Current (lines 164–183):**
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

**New:**
```python
pending_events: list = [build_workspace_event(task, "task:updated")]
pending_events.append(
    BatchWorkspaceEvent(
        event_name="task:step-created",
        workspace_id=ctx.workspace_id,
        items=[
            {"client_id": step.client_id, "working_section_id": step.working_section_id}
            for step in created_steps
        ],
    )
)
readiness_items = [
    {"client_id": step.client_id, "new_readiness": step.readiness_status.value}
    for step in readiness_changed
]
if readiness_items:
    pending_events.append(
        BatchWorkspaceEvent(
            event_name="task:step-readiness-changed",
            workspace_id=ctx.workspace_id,
            items=readiness_items,
        )
    )
await event_bus.dispatch(pending_events)
```

Remove the `WorkspaceEvent` import if it is no longer used after this change.

---

### Step 8 — Update `remove_task_step.py` (`_dispatch_remove_step_events`)

File: `backend/app/beyo_manager/services/commands/task_steps/remove_task_step.py`

Import `BatchWorkspaceEvent`. Replace per-step loops in `_dispatch_remove_step_events` (lines 225–247):

**Current:**
```python
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

**New:**
```python
pending_events: list = [
    build_workspace_event(task, "task:updated"),
    BatchWorkspaceEvent(
        event_name="task:step-deleted",
        workspace_id=ctx.workspace_id,
        items=[
            {"client_id": step.client_id, "working_section_id": step.working_section_id}
            for step in removed_steps
        ],
    ),
]
readiness_items = [
    {"client_id": step.client_id, "new_readiness": step.readiness_status.value}
    for step, old_readiness in readiness_changes
    if step.readiness_status != old_readiness
]
if readiness_items:
    pending_events.append(
        BatchWorkspaceEvent(
            event_name="task:step-readiness-changed",
            workspace_id=ctx.workspace_id,
            items=readiness_items,
        )
    )
if task.state != old_task_state:
    pending_events.append(
        build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
    )
await event_bus.dispatch(pending_events)
```

Remove the `WorkspaceEvent` import if it is no longer used.

---

### Step 9 — Update `transition_step_state.py`

File: `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`

Import `BatchWorkspaceEvent`. Replace the per-step event list (lines 359–370):

**Current:**
```python
pending_events: list = [
    build_workspace_event(step, "task:step-state-changed", extra={"new_state": request.new_state.value}),
]
if auto_paused_step is not None:
    pending_events.append(
        build_workspace_event(auto_paused_step, "task:step-state-changed", extra={"new_state": TaskStepStateEnum.PAUSED.value})
    )
if task.state != old_task_state:
    pending_events.append(
        build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
    )
await event_bus.dispatch(pending_events)
```

**New:**
```python
state_changed_items = [
    {"client_id": step.client_id, "new_state": request.new_state.value}
]
if auto_paused_step is not None:
    state_changed_items.append(
        {"client_id": auto_paused_step.client_id, "new_state": TaskStepStateEnum.PAUSED.value}
    )
pending_events: list = [
    BatchWorkspaceEvent(
        event_name="task:step-state-changed",
        workspace_id=ctx.workspace_id,
        items=state_changed_items,
    ),
]
if task.state != old_task_state:
    pending_events.append(
        build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
    )
await event_bus.dispatch(pending_events)
```

## Risks and mitigations

- Risk: `sio.emit` rejects a `list` as the data argument or silently wraps it in a different format.
  Mitigation: Write a unit test or manual smoke test immediately after Step 2 by emitting a list payload from the manager and verifying the raw Socket.IO frame on the client.
- Risk: Frontend listeners are broken if they still expect a single `{client_id, ...}` dict and receive an array.
  Mitigation: Coordinate frontend changes in the same deploy. The Acceptance Criteria confirmation point (clarification item 2) must be resolved first.
- Risk: `audit_handler.py` or `webhook_handler.py` reference `event.client_id` on `BatchWorkspaceEvent` and raise `AttributeError`.
  Mitigation: Before implementing, read both handlers and add a `isinstance(event, BatchWorkspaceEvent)` guard or add a `client_id: str | None = None` sentinel to the dataclass.

## Validation plan

- Manual socket trace via the browser DevTools Network → WS tab: create a task with 2 steps and confirm a single `task:step-created` frame with `[{...},{...}]` payload.
- Same check for `add_task_steps` with 3 steps: one `task:step-created` array frame, one `task:updated` frame.
- Same check for `remove_task_steps` with 2 steps: one `task:step-deleted` array frame.
- `transition_step_state` triggering auto-pause: one `task:step-state-changed` frame with 2 items.
- `transition_step_state` without auto-pause: one `task:step-state-changed` frame with 1 item.
- Regression: `task:created`, `task:updated`, `task:state-changed` frames remain single-object dicts.

## Review log

- `2026-06-19` user: initial plan request

## Lifecycle transition

- Current state: `archived`
- Next state: —
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_task_step_events_batch_20260619.md`
- Archive target: `backend/docs/architecture/archives/implementation/PLAN_task_step_events_batch_20260619.md`
