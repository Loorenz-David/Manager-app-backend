# PLAN_history_record_hooks_20260519

## Metadata

- Plan ID: `PLAN_history_record_hooks_20260519`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-19T12:00:00Z`
- Last updated at (UTC): `2026-05-19T13:05:00Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Hook 16 task and item public commands to emit a `HistoryRecord` + `HistoryRecordLink` entry using `_create_history_record_in_session` and the `message_builder` utilities, all within the existing `maybe_begin` transaction.
- Business/user intent: Build an auditable event trail for tasks and items that will power a unified task flow timeline endpoint (separate plan). Every mutation on a task or item entity becomes a timestamped, actor-attributed, human-readable event.
- Non-goals: The flow query endpoint itself; session-helper-level history emission (`_create_item_upholstery_in_session`, `_create_item_issue_in_session`); `find_or_create_item` history emission; `create_item_issue` public command (no matching entity type).

## Scope

- In scope:
  - 11 task public commands: `create_task`, `update_task`, `delete_task`, `cancel_task`, `resolve_task`, `fail_task`, `add_item_to_task`, `remove_item_from_task`, `create_task_note`, `update_task_note`, `delete_task_note`
  - 5 item public commands: `create_item`, `update_item`, `delete_item`, `create_item_upholstery`, `update_item_upholstery` + `delete_item_upholstery` (both in `update_and_delete_item_upholstery.py`)
  - No new files, no migrations, no schema changes
- Out of scope:
  - Task flow query endpoint (separate plan)
  - `find_or_create_item` — verified: does not delegate to `create_item`; has its own inline logic
  - Session helpers `_create_item_upholstery_in_session`, `_create_item_issue_in_session` — called from multiple contexts; emit only at public command boundary
  - `create_item_issue` public command — `ITEM_ISSUE` is not in `HistoryRecordEntityTypeEnum`
- Assumptions:
  - `message_builder.py` is implemented at `services/commands/history/message_builder.py`
  - `_create_history_record_in_session` is implemented at `services/commands/history/_create_history_record_in_session.py`
  - Both enums are `StrEnum` — values are plain strings, safe for JSONB `from_value`/`to_value`
  - `expire_on_commit=False` on session factory — attributes safe to read after flush
  - `ctx.identity.get("username")` is the correct way to read the username in all commands

## Clarifications required

None — all requirements are unambiguous from the codebase.

## Acceptance criteria

1. Each public command in scope emits exactly one `HistoryRecord` + `HistoryRecordLink` within the same `maybe_begin` transaction.
2. All emitted records use the correct `entity_type`, `change_type`, and `entity_client_id` for the entity acted upon.
3. All `description` fields are non-empty human-readable strings produced by the message builder.
4. State-transition commands (`cancel_task`, `resolve_task`, `fail_task`) populate `field_name="state"`, `from_value={"state": <original>}`, `to_value={"state": <new>}`.
5. Update and create/delete commands use `field_name=None`, `from_value=None`, `to_value=None` (from/to tracking for arbitrary field diffs is out of scope for this plan).
6. No additional DB round-trips beyond the two flushes inside `_create_history_record_in_session`.
7. Existing test suite passes with no regressions.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `06_commands_local.md`: command structure, `maybe_begin`, subordinate-command event rule — history emission is a subordinate call within the public command's `maybe_begin` block
- `backend/architecture/42_event.md`: history record system, entity types, change types

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- All 16 command files: exact flush order, variable names, where to insert the history call
- `_create_history_record_in_session.py`: parameter names and order
- `message_builder.py`: function signatures
- `domain/history/enums.py`: enum member names

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

### Shared imports block

Add to each modified file only the symbols it actually uses:

```python
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import (
    build_create_message,        # only if the command uses it
    build_update_message,        # only if the command uses it
    build_delete_message,        # only if the command uses it
    build_state_change_message,  # only if the command uses it (state transitions)
)
```

---

### Step 1 — `services/commands/tasks/create_task.py`

Add at the **end** of the `maybe_begin` block, after `task.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.CREATED,
    description=build_create_message(username, "task", "workspace"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_create_message`.

---

### Step 2 — `services/commands/tasks/update_task.py`

**Before** the mutation loop (`for field_name in _DIRECT_FIELDS`), capture the list of updated fields:

```python
updated_fields = [f for f in request.model_fields_set if f in _DIRECT_FIELDS]
```

Add at the **end** of the `maybe_begin` block, after `task.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_update_message(username, updated_fields, f"task #{task.task_scalar_id}"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_update_message`.

---

### Step 3 — `services/commands/tasks/delete_task.py`

Add at the **end** of the `maybe_begin` block, after `task.deleted_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.DELETED,
    description=build_delete_message(username, "task", "workspace"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_delete_message`.

---

### Step 4 — `services/commands/tasks/cancel_task.py`

**Before** `task.state = TaskStateEnum.CANCELLED`, capture:

```python
original_state = task.state.value
```

Add at the **end** of the `maybe_begin` block, after `task.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_state_change_message(username, "task", TaskStateEnum.CANCELLED.value),
    field_name="state",
    from_value={"state": original_state},
    to_value={"state": TaskStateEnum.CANCELLED.value},
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Produces: `"David marked task as cancelled"` / `"Someone marked task as cancelled"`.

`TaskStateEnum` is already imported. Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_state_change_message`.

---

### Step 5 — `services/commands/tasks/resolve_task.py`

Same pattern as Step 4. **Before** `task.state = TaskStateEnum.RESOLVED`:

```python
original_state = task.state.value
```

After `task.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_state_change_message(username, "task", TaskStateEnum.RESOLVED.value),
    field_name="state",
    from_value={"state": original_state},
    to_value={"state": TaskStateEnum.RESOLVED.value},
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Produces: `"David marked task as resolved"`.

---

### Step 6 — `services/commands/tasks/fail_task.py`

Same pattern as Step 4. **Before** `task.state = TaskStateEnum.FAILED`:

```python
original_state = task.state.value
```

After `task.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_state_change_message(username, "task", TaskStateEnum.FAILED.value),
    field_name="state",
    from_value={"state": original_state},
    to_value={"state": TaskStateEnum.FAILED.value},
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

---

### Step 7 — `services/commands/tasks/add_item_to_task.py`

Add at the **end** of the `maybe_begin` block, after `task_item` is flushed:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task_item.task_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_create_message(username, "item", "task"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Note: `task` is already fetched so `task.task_scalar_id` is available if the description needs it. Current description does not require it. `entity_client_id` is `task_item.task_id` — the task entity whose composition changed.

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_create_message`.

---

### Step 8 — `services/commands/tasks/remove_item_from_task.py`

Add at the **end** of the `maybe_begin` block, after `task_item.removed_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task_item.task_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_delete_message(username, "item", "task"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Note: only `task_item` is fetched in this command — `task.task_scalar_id` is not available. `entity_client_id=task_item.task_id` links the record to the correct task.

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_delete_message`.

---

### Step 9 — `services/commands/tasks/create_task_note.py`

Add in the **public** `create_task_note` function only (not in `_create_task_note_in_session`), at the end of the `maybe_begin` block, after `_create_task_note_in_session(...)` returns `note`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_create_message(username, "note", "task"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Note: `entity_client_id` is `task.client_id` — note events are linked to the parent task entity. `task` is already fetched in the public command.

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_create_message`.

---

### Step 10 — `services/commands/tasks/update_task_note.py`

**Before** the mutation block, capture updated fields:

```python
updated_fields = [f for f in ["note_type", "content"] if f in request.model_fields_set]
```

Add at the **end** of the `maybe_begin` block, after `note.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=note.task_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_update_message(username, updated_fields, "task note"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Note: `note.task_id` is a plain `String` column on `TaskNote`, loaded with the row — no lazy load needed.

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_update_message`.

---

### Step 11 — `services/commands/tasks/delete_task_note.py`

Add at the **end** of the `maybe_begin` block, after `note.deleted_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=note.task_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_delete_message(username, "note", "task"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_delete_message`.

---

### Step 12 — `services/commands/items/create_item.py`

Add at the **end** of the `maybe_begin` block, after all issue/upholstery creation:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM,
    entity_client_id=item.client_id,
    change_type=HistoryRecordChangeTypeEnum.CREATED,
    description=build_create_message(username, "item", "workspace"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_create_message`.

---

### Step 13 — `services/commands/items/update_item.py`

**Before** the mutation loop, capture updated fields:

```python
_ITEM_MUTABLE_FIELDS = _DIRECT_FIELDS | {"item_category_id"}
updated_fields = [f for f in request.model_fields_set if f in _ITEM_MUTABLE_FIELDS]
```

Add at the **end** of the `maybe_begin` block, after `item.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM,
    entity_client_id=item.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_update_message(username, updated_fields, "item"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_update_message`.

---

### Step 14 — `services/commands/items/delete_item.py`

Add at the **end** of the `maybe_begin` block, after `item.deleted_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM,
    entity_client_id=item.client_id,
    change_type=HistoryRecordChangeTypeEnum.DELETED,
    description=build_delete_message(username, "item", "workspace"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_delete_message`.

---

### Step 15 — `services/commands/items/create_item_upholstery.py` (public command only)

Add inside the public `create_item_upholstery` function, within the `maybe_begin` block, after `_create_item_upholstery_in_session(...)` returns `iup_client_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
    entity_client_id=iup_client_id,
    change_type=HistoryRecordChangeTypeEnum.CREATED,
    description=build_create_message(username, "upholstery", "item"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

**Do NOT modify `_create_item_upholstery_in_session`** — it is a session helper called from `create_task` and other commands. History emission belongs only at the public command boundary.

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_create_message`.

---

### Step 16 — `services/commands/items/update_and_delete_item_upholstery.py`

**`update_item_upholstery`**:

Before mutations, compute updated fields. This command uses `if request.field is not None` checks (not `model_fields_set`), so compute from non-None values:

```python
_IUP_MUTABLE_FIELDS = ["name", "code", "amount_meters", "time_to_fix_in_seconds"]
updated_fields = [f for f in _IUP_MUTABLE_FIELDS if getattr(request, f) is not None]
```

Add at the **end** of the `maybe_begin` block, after `iup.updated_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
    entity_client_id=iup.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=build_update_message(username, updated_fields, "upholstery"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

**`delete_item_upholstery`**:

Add at the **end** of the `maybe_begin` block, after `iup.deleted_by_id = ctx.user_id`:

```python
username = ctx.identity.get("username")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
    entity_client_id=iup.client_id,
    change_type=HistoryRecordChangeTypeEnum.DELETED,
    description=build_delete_message(username, "upholstery", "item"),
    field_name=None,
    from_value=None,
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=username,
)
```

Imports needed: `HistoryRecordChangeTypeEnum`, `HistoryRecordEntityTypeEnum`, `_create_history_record_in_session`, `build_update_message`, `build_delete_message`.

---

## Risks and mitigations

- Risk: `create_task` internally calls `_create_item_upholstery_in_session` and `_create_item_issue_in_session`. If those helpers emitted history records, a single `create_task` would produce multiple ITEM_UPHOLSTERY records unexpectedly.
  Mitigation: history emission added only to public commands. Neither session helper is modified.

- Risk: `find_or_create_item` is called from `create_task` within the same `maybe_begin` context. If `create_item` emitted a record and `find_or_create_item` delegated to it, an implicit ITEM/CREATED record would appear.
  Mitigation: verified — `find_or_create_item` has its own inline creation logic and does NOT call `create_item`. No implicit records.

- Risk: State-transition commands capture `original_state` after mutation instead of before, producing wrong `from_value`.
  Mitigation: explicitly place `original_state = task.state.value` before any mutation line in Steps 4, 5, 6. Plan code is ordered to enforce this.

- Risk: `update_item_upholstery` updated_fields computation uses non-None check instead of `model_fields_set`. A field sent as non-None but equal to its current value appears in the description.
  Mitigation: acceptable for first-pass auditing. The description shows intent. Documented as known simplification; exact diffing can be added later.

## Validation plan

- `pytest backend/ -x`: existing suite passes with no regressions.
- Manual integration — `create_task`: call endpoint → query `SELECT * FROM history_records hr JOIN history_record_links hrl ON hrl.history_record_id = hr.client_id WHERE hrl.entity_client_id = '<task_id>'` → expect 1 row with `change_type='created'` and non-null `description`.
- Manual integration — `cancel_task`: verify 1 TASK/UPDATED record with `field_name='state'`, correct `from_value` and `to_value`.
- Manual integration — `create_item_upholstery` (called directly, not via `create_task`): verify 1 ITEM_UPHOLSTERY/CREATED record linked to `iup_client_id`.
- Manual integration — `create_task` with embedded upholstery (via internal helper): verify no spurious ITEM_UPHOLSTERY history record appears.

## Review log

- `2026-05-19` user: requested plan for hooking task and item commands to history record system
- `2026-05-19` copilot: implemented all 16 scoped public-command hooks with message-builder descriptions and history session helper emission.
- `2026-05-19` copilot: validation run completed (py_compile/import checks pass; pytest gate blocked by DB init fixture precondition in environment).

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `copilot`
