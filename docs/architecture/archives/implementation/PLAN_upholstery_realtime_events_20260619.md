# PLAN_upholstery_realtime_events_20260619

## Metadata

- Plan ID: `PLAN_upholstery_realtime_events_20260619`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T10:30:20Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Add `event_bus.dispatch()` calls to all upholstery and item-upholstery commands that currently mutate state without emitting real-time socket events.
- Business/user intent: The frontend real-time layer must receive signals when upholstery data changes so it can invalidate queries without polling. Several commands perform DB mutations but never call `event_bus.dispatch()`, leaving the frontend stale until a manual refresh.
- Non-goals: New routes, new models, new migrations, new worker tasks, changes to existing event names or the event bus routing logic.

## Scope

- In scope:
  - Adding `event_bus.dispatch()` calls to 7 command files
  - Defining 7 new `WorkspaceEvent` event names
  - Updating the frontend event catalog handoff document with the new events, types, and handler matrix rows
- Out of scope:
  - Changing existing dispatch patterns in commands that already emit events (`mark_requirements_ordered`, `mark_requirements_in_use`, `mark_requirements_completed`, `create_upholstery_order`, `receive_upholstery_order`, `set_current_stored_amount_inventory`)
  - Socket handler, connection manager, or event bus routing
  - Frontend code

## Clarifications required

(none — all information available from code audit)

## Acceptance criteria

1. `update_requirement_quantity` emits `item:upholstery-updated` and `item:upholstery-requirement-state-changed` after a successful mutation; emits nothing when delta is zero (early return path unchanged).
2. `create_item_upholstery` emits `item:upholstery-created` alongside the existing `item:updated`.
3. `update_item_upholstery` emits `item:upholstery-updated` alongside the existing `item:updated`.
4. `delete_item_upholstery` emits `item:upholstery-deleted` alongside the existing `item:updated`.
5. `update_upholstery` emits `upholstery:updated`.
6. `update_upholstery_inventory` emits `upholstery:inventory-updated`.
7. `delete_upholstery_inventory` emits `upholstery:inventory-deleted`; additionally emits `upholstery:deleted` only when the parent upholstery was also soft-deleted.
8. The event catalog handoff document lists all 7 new events with TypeScript payload types and handler matrix rows.

## Contracts and skills

### Contracts loaded

- `backend/architecture/11_infra_events.md`: `event_bus.dispatch()` contract, `WorkspaceEvent` constructor shape, dispatch-after-commit rule
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: command pattern, `maybe_begin` transaction utility, where dispatch calls must be placed relative to the transaction boundary
- `backend/architecture/56_realtime_layer.md`: established event naming conventions, payload shape rule (`client_id` always present, no full entity data, workspace routing is implicit)

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` transaction utility details

### File read intent — pattern vs. relational

Before reading any implementation file, apply the test:

> "Am I reading this to understand how to structure my new code — or to understand what existing code does?"

Prohibited (pattern reads — contracts already cover these):
- Reading other commands to understand how to structure `WorkspaceEvent` or `dispatch()` → `11_infra_events.md` covers this

Permitted (relational reads — understanding what exists):
- Reading each of the 7 target command files to confirm exact import paths, local variable names, and the precise line after which the dispatch must be inserted
- Reading `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md` to understand the current structure before appending new entries

### Skill selection

- Primary skill: none — this is a pattern application task (inserting established `event_bus.dispatch()` calls into existing commands)
- Excluded alternatives: no new routes, no new models

## Implementation plan

### Step 1 — Load contracts

Read in order:
1. `backend/architecture/11_infra_events.md`
2. `backend/architecture/06_commands.md` then `backend/architecture/06_commands_local.md`
3. `backend/architecture/56_realtime_layer.md`

### Step 2 — Item upholstery commands

#### 2a. `create_item_upholstery.py`

File: `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`

Both `event_bus` and `WorkspaceEvent` are already imported.

The existing dispatch at the end of `create_item_upholstery()` sends only `item:updated` for the parent item. Add `item:upholstery-created` for the newly created ItemUpholstery entity in the same dispatch call:

```python
# BEFORE
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=request.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])

# AFTER
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=request.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
    WorkspaceEvent(
        event_name="item:upholstery-created",
        client_id=iup_client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])
```

No new imports needed.

#### 2b. `update_and_delete_item_upholstery.py`

File: `backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py`

Both `event_bus` and `WorkspaceEvent` are already imported.

**`update_item_upholstery`** — extend the existing dispatch:

```python
# BEFORE
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=iup.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])

# AFTER
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=iup.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
    WorkspaceEvent(
        event_name="item:upholstery-updated",
        client_id=iup.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])
```

**`delete_item_upholstery`** — extend the existing dispatch:

```python
# BEFORE
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=iup.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])

# AFTER
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:updated",
        client_id=iup.item_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
    WorkspaceEvent(
        event_name="item:upholstery-deleted",
        client_id=iup.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])
```

No new imports needed.

#### 2c. `update_requirement_quantity.py`

File: `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`

**Add missing imports** (currently absent from this file):

```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

**Dispatch placement:** The function has an early-exit guard deep inside the `async with` block:

```python
if delta == Decimal("0"):
    return {}
```

This exits the function entirely before the `async with` block closes, so no events are needed for that path. All other paths (MISSING_QUANTITY initial assignment, or delta != 0 adjustment) reach the final `return {}` at the bottom of the function. Replace that final `return {}` with the dispatch block:

```python
# BEFORE (at end of function, after async with block)
return {}

# AFTER
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="item:upholstery-updated",
        client_id=iup.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
    WorkspaceEvent(
        event_name="item:upholstery-requirement-state-changed",
        client_id=iup.client_id,
        workspace_id=ctx.workspace_id,
        extra={"new_state": active_req.state.value},
    ),
])
return {}
```

**Variable scope note:** `iup` and `active_req` are defined inside the `async with maybe_begin(ctx.session):` block. Python does not have block scoping — both variables remain accessible after the block closes. `active_req.state` holds the new enum value set during the mutation; it does not require a DB round-trip and will not raise `DetachedInstanceError`.

**`client_id` convention:** Following the same pattern as `mark_requirements_in_use` and `mark_requirements_completed`, the `client_id` for `item:upholstery-requirement-state-changed` is the **item upholstery's** `client_id` (`iup.client_id`), not the requirement row's own id. The frontend tracks state at the item-upholstery level.

### Step 3 — Upholstery entity commands

#### 3a. `update_upholstery.py`

File: `backend/app/beyo_manager/services/commands/upholstery/update_upholstery.py`

**Add imports:**

```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

After the closing `async with ctx.session.begin():` block, replace `return {}` with:

```python
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="upholstery:updated",
        client_id=upholstery.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])
return {}
```

#### 3b. `update_upholstery_inventory.py`

File: `backend/app/beyo_manager/services/commands/upholstery/update_upholstery_inventory.py`

**Add imports:**

```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

After the closing `async with ctx.session.begin():` block, replace `return {}` with:

```python
await event_bus.dispatch([
    WorkspaceEvent(
        event_name="upholstery:inventory-updated",
        client_id=inv.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
])
return {}
```

#### 3c. `delete_upholstery_inventory.py`

File: `backend/app/beyo_manager/services/commands/upholstery/delete_upholstery_inventory.py`

**Add imports:**

```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
```

`delete_upholstery_inventory` soft-deletes both the `UpholsteryInventory` record and its parent `Upholstery`. The parent query uses `scalar_one_or_none()` so `upholstery` may be `None` if the parent was already deleted by other means. Build the event list conditionally:

After the closing `async with ctx.session.begin():` block, replace `return {}` with:

```python
pending_events: list = [
    WorkspaceEvent(
        event_name="upholstery:inventory-deleted",
        client_id=inv.client_id,
        workspace_id=ctx.workspace_id,
        extra={},
    ),
]
if upholstery is not None:
    pending_events.append(
        WorkspaceEvent(
            event_name="upholstery:deleted",
            client_id=upholstery.client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        )
    )
await event_bus.dispatch(pending_events)
return {}
```

### Step 4 — Update the event catalog handoff document

Both files below carry identical content and must receive the same edits:
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`
- `frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`

Apply all four sub-steps to both files.

---

#### 4a — Insert "Item upholsteries" section

**Anchor — insert immediately before this line:**
```
### Working sections
```

**Content to insert (including the blank line before the next section heading):**
```
### Item upholsteries

All item upholstery events are workspace-scoped. `client_id` refers to the **ItemUpholstery** entity, not the parent item.

```ts
// An upholstery selection was added to an item
'item:upholstery-created': (payload: { client_id: string }) => void;

// Upholstery selection or quantity changed (includes upholstery swap)
'item:upholstery-updated': (payload: { client_id: string }) => void;

// Item upholstery was soft-deleted
'item:upholstery-deleted': (payload: { client_id: string }) => void;
```

---

```

---

#### 4b — Insert "Upholstery entities" section

**Anchor — insert immediately after the closing `---` that follows the `### Working sections` block.**

The `### Working sections` block ends with:
```
'working_section:deleted': (payload: { client_id: string }) => void;
```

followed by a closing `---`. Insert the new section after that `---`:

**Content to insert:**
```
### Upholstery entities

All upholstery entity events are workspace-scoped. `client_id` refers to the **Upholstery** entity (4a–4b) or the **UpholsteryInventory** entity (4c–4d) as noted.

```ts
// Upholstery properties changed (name, code, image, favorite)
'upholstery:updated': (payload: { client_id: string }) => void;  // client_id = upholstery

// Upholstery and its inventory were soft-deleted together
'upholstery:deleted': (payload: { client_id: string }) => void;  // client_id = upholstery

// Inventory settings changed (thresholds, planning position, projected value, etc.)
'upholstery:inventory-updated': (payload: { client_id: string }) => void;  // client_id = inventory

// Inventory (and parent upholstery) was soft-deleted
'upholstery:inventory-deleted': (payload: { client_id: string }) => void;  // client_id = inventory
```

---

```

---

#### 4c — Extend the `ServerToClientEvents` type block

**Anchor — locate the line:**
```
  // --- Working sections ---
```

Insert the following block immediately **after** the three `working_section:*` lines and before the closing `};` of the type:

```ts
  // --- Item upholsteries ---
  'item:upholstery-created': (payload: { client_id: string }) => void;
  'item:upholstery-updated': (payload: { client_id: string }) => void;
  'item:upholstery-deleted': (payload: { client_id: string }) => void;

  // --- Upholstery entities ---
  'upholstery:updated':           (payload: { client_id: string }) => void;
  'upholstery:deleted':           (payload: { client_id: string }) => void;
  'upholstery:inventory-updated': (payload: { client_id: string }) => void;
  'upholstery:inventory-deleted': (payload: { client_id: string }) => void;
```

---

#### 4d — Extend the handler responsibility matrix

**Anchor — locate this row in the matrix:**
```
| `working_section:deleted` | `features/working-sections/socket-events.ts` | Remove section detail, invalidate list |
```

Insert the following 7 rows immediately after it:

```
| `item:upholstery-created`      | `features/items/socket-events.ts`         | Invalidate item upholstery list for the parent item |
| `item:upholstery-updated`      | `features/items/socket-events.ts`         | Invalidate item upholstery detail + parent item detail |
| `item:upholstery-deleted`      | `features/items/socket-events.ts`         | Remove item upholstery detail from cache, invalidate parent item detail |
| `upholstery:updated`           | `features/upholstery/socket-events.ts`    | Invalidate upholstery detail + list |
| `upholstery:deleted`           | `features/upholstery/socket-events.ts`    | Remove upholstery detail, invalidate list |
| `upholstery:inventory-updated` | `features/upholstery/socket-events.ts`    | Invalidate upholstery inventory detail |
| `upholstery:inventory-deleted` | `features/upholstery/socket-events.ts`    | Remove inventory detail, invalidate upholstery list |
```

## Risks and mitigations

- Risk: `iup` and `active_req` accessed after the `async with` block in `update_requirement_quantity` raise `DetachedInstanceError`.
  Mitigation: SQLAlchemy only raises `DetachedInstanceError` when accessing a lazy-loaded relationship or column that was never loaded. `iup.client_id` and `active_req.state` were both explicitly read and/or mutated inside the session — they are already in the object's `__dict__`. This pattern matches every other command in the codebase that reads `iup.item_id` etc. after the transaction. Safe.

- Risk: `upholstery` variable may be `None` in `delete_upholstery_inventory` when building the event list.
  Mitigation: The dispatch builds a list conditionally with `if upholstery is not None`. The inventory event always fires; the upholstery event fires only when the parent was found and deleted. Handled in Step 3c.

- Risk: Introducing new event names that the frontend does not yet handle causes silent no-ops.
  Mitigation: Socket events with no registered handler are safely ignored by the Socket.IO client library — no error thrown. The catalog update in Step 4 gives the frontend developer the full list to implement handlers against.

## Validation plan

- `make run` (API server) + `make notification-worker` — start both processes.
- Use the frontend UI or an HTTP client to trigger each mutating command.
- In browser devtools or a socket inspector, confirm each new event name fires with the correct `{ client_id }` payload.
- Confirm `update_requirement_quantity` with an unchanged quantity (same value as existing) does NOT emit any events — the `delta == 0` early return path must be preserved.
- Confirm `delete_upholstery_inventory` emits two events when the parent upholstery is found and one event when it is not.

## Review log

- `2026-06-19T10:30:20Z` — Implemented and summarized by `codex`; plan archived after validation.

## Lifecycle transition

- Current state: `archived`
- Next state: none
- Transition owner: `codex`
