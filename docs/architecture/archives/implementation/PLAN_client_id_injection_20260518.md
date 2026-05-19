# PLAN_client_id_injection_20260518

## Metadata

- Plan ID: `PLAN_client_id_injection_20260518`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T21:10:00Z`
- Related issue/ticket: `client-id-injection`
- Intention plan: _none — architectural principle from `backend/architecture/40_identity.md` line 137_

---

## Goal and intent

- **Goal:** Implement the architecture's documented principle that create commands may accept a caller-provided `client_id` for optimistic frontend flows. Every create command that produces a directly addressable entity must accept an optional `client_id` in its request payload. If provided and valid, it is used as the primary key instead of the server-generated default.
- **Business/user intent:** The frontend pre-generates `client_id` values (prefixed ULIDs) before making network calls. This allows it to: (1) immediately link polymorphic records (e.g. image links) to entities that haven't been created server-side yet; (2) perform optimistic UI updates without waiting for server round-trips; (3) safely retry creation on network failure using the same pre-generated ID.
- **Non-goals:** Junction/association tables (TaskItem, TaskStepDependency, TaskStepAssignmentRecord, WorkingSectionMembership) — these are never directly addressed by the frontend and do not benefit from client_id injection. Bootstrap/seed commands. Idempotent-on-conflict retry semantics (deferred — duplicate client_id raises ConflictError for now).

---

## Prerequisite

None. This plan is self-contained.

---

## Scope

- **In scope:**
  - New shared utility: `services/commands/utils/client_id.py` — format validation helper
  - Items domain: `create_item.py`, `find_or_create_item.py`, `items/requests/__init__.py`, `routers/api_v1/items.py`
  - Customers domain: `create_customer.py`, `find_or_create_customer.py`, `customers/requests/__init__.py`, `routers/api_v1/customers.py`
  - Tasks domain: `create_task.py`, `create_task_note.py`, `add_task_step.py`, `tasks/requests/__init__.py`, `task_steps/requests/__init__.py`, `routers/api_v1/tasks.py`
  - Cases domain: `create_case.py`, `create_conversation.py`, `send_message.py`, `cases/requests/__init__.py` (or equivalent), `routers/api_v1/cases.py`
  - Working sections domain: `create_working_section.py`, `working_sections/requests/__init__.py`, `routers/api_v1/working_sections.py`
  - Item upholsteries domain: `create_item_upholstery.py`, `items/requests/__init__.py` (upholstery input), `routers/api_v1/item_upholsteries.py`
  - Upholstery inventories domain: `create_upholstery_inventory.py`, `upholstery/requests/__init__.py` (or equivalent), `routers/api_v1/upholstery_inventories.py`
- **Out of scope:** junction tables, bootstrap commands, queries, state-transition commands (resolve/cancel/fail/transition)
- **Assumptions:** `IdentityMixin.client_id` uses a SQLAlchemy `default=lambda: generate_id(prefix)`. Passing `client_id=value` to a model constructor overrides the default — this is standard SQLAlchemy behaviour; no ORM changes are needed.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. Every in-scope create command accepts `client_id: str | None = None` in its request model. If `None`, server generates as before.
2. If a `client_id` is provided, it is validated for correct prefix format before any DB operation. Invalid format → `ValidationError`.
3. If a `client_id` is provided that already exists in the DB (any workspace) → `ConflictError("Provided client_id is already in use.")`.
4. If a `client_id` passes validation and is not a duplicate, the model is created with that exact `client_id` as the primary key.
5. For `find_or_create_*` commands: the provided `client_id` is ONLY used on the CREATE path. On the FIND path (record already exists), the provided `client_id` is silently ignored and the existing record's `client_id` is returned. This is explicit — do NOT error when find path is taken with a provided `client_id`.
6. All in-scope router body models accept `client_id: str | None = None`. Routers that use `body.model_dump(exclude_unset=True)` pass it through automatically — no handler logic change needed.
7. Routers that use `body.model_dump()` (without `exclude_unset=True`) must be audited — `client_id: None` will be present in `incoming_data` but the command must handle `None` gracefully (it does, since `client_id is None` skips validation and uses the default).
8. Nested inputs in `CreateTaskRequest`: `FindOrCreateItemInput`, `TaskNoteInput`, `TaskStepInput` all accept `client_id: str | None = None`. The create_task command propagates each to the respective session helper or inline creation block.
9. The shared utility `validate_provided_client_id(value, prefix)` raises `ValidationError` if `value` does not match `{prefix}_{26-char-ULID}` format.
10. No existing tests break — all `client_id` fields default to `None`, making the change fully backward-compatible.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/40_identity.md`: the documented principle (line 137) and ULID format
- `backend/architecture/40_identity_local.md`: prefix registry for all local models
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, request parsing, error raising
- `backend/architecture/05_errors.md`: `ValidationError`, `ConflictError`
- `backend/architecture/09_routers.md`: body model wiring
- `backend/architecture/21_naming_conventions.md`: naming

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: prefix registry — use this to confirm the exact prefix for each model before writing `validate_provided_client_id` calls

### File read intent — pattern vs. relational

Permitted relational reads (understanding what exists):

| File | What to extract |
|---|---|
| `models/base/identity.py` | Confirm `default=lambda: generate_id(prefix)` — verify constructor override works |
| `services/commands/items/requests/__init__.py` | Existing `FindOrCreateItemRequest`, `CreateItemRequest` field shapes |
| `services/commands/customers/requests/__init__.py` | Existing request field shapes |
| `services/commands/tasks/requests/__init__.py` | `CreateTaskRequest`, `TaskNoteInput`, `TaskStepInput`, `FindOrCreateItemInput` |
| `services/commands/task_steps/requests/__init__.py` | `AddTaskStepRequest` field shape |
| `services/commands/cases/requests/__init__.py` (if exists) | Case request shapes |
| `services/commands/working_sections/requests/__init__.py` (if exists) | Working section request shapes |
| `models/tables/cases/case.py` (or equivalent) | Confirm `CLIENT_ID_PREFIX` for Case, Conversation, Message |
| `models/tables/working_sections/working_section.py` | Confirm `CLIENT_ID_PREFIX = "wsec"` |
| `models/tables/tasks/task_note.py` | Confirm `CLIENT_ID_PREFIX = "tno"` |
| `models/tables/tasks/task_step.py` | Confirm `CLIENT_ID_PREFIX = "tsp"` |
| `routers/api_v1/items.py` | Current body model shapes for items router |
| `routers/api_v1/customers.py` | Current body model shapes |
| `routers/api_v1/tasks.py` | `_CreateTaskBody`, `_AddTaskStepBody` shapes |
| `routers/api_v1/cases.py` | All create body shapes |
| `routers/api_v1/working_sections.py` | Create body shape |
| `routers/api_v1/item_upholsteries.py` | `_CreateBody` shape |
| `routers/api_v1/upholstery_inventories.py` | `_CreateBody` shape |

Prohibited (contract already covers these):
- Reading another command to understand session.add / flush / error-raising — use `06_commands.md`
- Reading another router to understand handler skeleton — use `09_routers.md`

---

## Implementation plan

### Step 0 — Shared utility: `services/commands/utils/client_id.py`

Create this file (it may not exist yet). If the file already exists and has a `validate_provided_client_id` function, skip creation and use what's there.

```python
import re

from beyo_manager.errors.validation import ValidationError

# Crockford Base32: 0-9, A-Z excluding I, L, O, U — 32 valid chars, 26 chars = ULID
_ULID_RE = re.compile(r'^[0-9A-HJKMNP-TV-Z]{26}$')


def validate_provided_client_id(value: str, expected_prefix: str) -> None:
    """Raise ValidationError if value is not a valid prefixed ULID for the given prefix.

    Valid format: {expected_prefix}_{26-char Crockford Base32 ULID}
    Example:      itm_01ARYZ6S41TSV4RRFFQ69G5FAV
    """
    prefix_with_sep = f"{expected_prefix}_"
    if not value.startswith(prefix_with_sep):
        raise ValidationError(
            f"client_id must start with '{prefix_with_sep}'. Got: {value!r}"
        )
    ulid_part = value[len(prefix_with_sep):]
    if not _ULID_RE.match(ulid_part):
        raise ValidationError(
            f"client_id has an invalid ULID segment (must be 26 Crockford Base32 chars). Got: {ulid_part!r}"
        )
```

**Location:** `beyo_manager/services/commands/utils/client_id.py`

Import path for all commands: `from beyo_manager.services.commands.utils.client_id import validate_provided_client_id`

---

### Step 1 — Items domain

#### 1a. `services/commands/items/requests/__init__.py`

Add `client_id: str | None = None` to:
- `CreateItemRequest`
- `FindOrCreateItemRequest`
- `FindOrCreateItemInput` (the nested input used inside `CreateTaskRequest` — this is important for inline task creation)

#### 1b. `services/commands/items/create_item.py`

After parsing the request, inside `maybe_begin`, before creating the `Item`:

```python
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id

# At top of command, after parse:
if request.client_id is not None:
    validate_provided_client_id(request.client_id, "itm")
    existing = await ctx.session.get(Item, request.client_id)
    if existing is not None:
        raise ConflictError("Provided client_id is already in use.")

item = Item(
    client_id=request.client_id,   # None → default fires; value → override
    workspace_id=ctx.workspace_id,
    # ... all other fields ...
)
```

**CRITICAL:** `Item(client_id=None, ...)` — SQLAlchemy will still use the `default` when `None` is passed, because `default` fires on INSERT when the column value resolves to `None`. Verify this assumption by reading `models/base/identity.py`. If the default does NOT fire for `None`, use: `item = Item(client_id=request.client_id or generate_id("itm"), ...)` explicitly.

> **Verification step:** Read `models/base/identity.py` and confirm how the default interacts with an explicit `None` value passed to the constructor. If `default` fires only when the key is absent (not when `None` is passed), then pass `client_id=request.client_id` only when it is not `None`:
> ```python
> kwargs = {}
> if request.client_id is not None:
>     kwargs["client_id"] = request.client_id
> item = Item(workspace_id=..., **kwargs)
> ```
> This pattern works regardless of SQLAlchemy version and is the safest approach. **Use this pattern across ALL commands in this plan.**

#### 1c. `services/commands/items/find_or_create_item.py`

The find path returns early inside `maybe_begin`. The provided `client_id` is only used on the CREATE path:

```python
if request.client_id is not None:
    validate_provided_client_id(request.client_id, "itm")
    # Duplicate check only needed on create path — done below

# ... existing lookup logic ...
if existing_item is not None:
    # FIND PATH: provided client_id is silently ignored — return existing
    return {"client_id": existing_item.client_id, "was_created": False}

# CREATE PATH
if request.client_id is not None:
    dup = await ctx.session.get(Item, request.client_id)
    if dup is not None:
        raise ConflictError("Provided client_id is already in use.")

kwargs = {}
if request.client_id is not None:
    kwargs["client_id"] = request.client_id
item = Item(workspace_id=..., **kwargs, ...)
```

**IMPORTANT:** Move the format validation BEFORE the lookup so it fails fast on bad input before any DB query.

#### 1d. `routers/api_v1/items.py`

Add `client_id: str | None = None` to:
- `_CreateItemBody`
- `_FindOrCreateItemBody` (or whatever the find-or-create body is named)

Routers that use `body.model_dump(exclude_unset=True)` need no handler logic change — `client_id` passes through automatically.

---

### Step 2 — Customers domain

Same pattern as Step 1. Prefix: `"cus"`.

#### 2a. `services/commands/customers/requests/__init__.py`

Add `client_id: str | None = None` to:
- `CreateCustomerRequest`
- `FindOrCreateCustomerRequest`

#### 2b. `services/commands/customers/create_customer.py`

Apply the `kwargs` constructor pattern with `validate_provided_client_id(request.client_id, "cus")` + duplicate check on `Customer` model.

#### 2c. `services/commands/customers/find_or_create_customer.py`

Same as `find_or_create_item`: validate on entry, skip duplicate check on find path, apply on create path only.

#### 2d. `routers/api_v1/customers.py`

Add `client_id: str | None = None` to `_CreateCustomerBody` and the find-or-create body model.

---

### Step 3 — Tasks domain

#### 3a. `services/commands/tasks/requests/__init__.py`

Add `client_id: str | None = None` to:
- `CreateTaskRequest` — for the Task itself (prefix `"tsk"`)
- `TaskNoteInput` — for inline notes within task creation (prefix `"tno"`)
- `TaskStepInput` — for inline steps within task creation (prefix `"tsp"`)
- `FindOrCreateItemInput` — for the item embedded in task creation (prefix `"itm"`)

#### 3b. `services/commands/task_steps/requests/__init__.py`

Add `client_id: str | None = None` to `AddTaskStepRequest` (prefix `"tsp"`).

#### 3c. `services/commands/tasks/create_task.py`

Three injection points:

**Task itself:**
```python
if request.client_id is not None:
    validate_provided_client_id(request.client_id, "tsk")
    if await ctx.session.get(Task, request.client_id) is not None:
        raise ConflictError("Provided client_id is already in use.")
kwargs = {}
if request.client_id is not None:
    kwargs["client_id"] = request.client_id
task = Task(workspace_id=..., **kwargs, ...)
```

**Item inside task (`FindOrCreateItemInput`):**
The call to `find_or_create_item` passes `item_ctx = ServiceContext(incoming_data=request.item.model_dump(exclude_unset=True), ...)`. Since `FindOrCreateItemInput` now has `client_id: str | None = None`, and `model_dump(exclude_unset=True)` only includes it if the frontend provided it, this flows through automatically with NO additional changes in `create_task.py`. The `find_or_create_item` command handles it internally.

**Inline steps (in the steps loop):**
```python
for step_input in request.steps:
    if step_input.client_id is not None:
        validate_provided_client_id(step_input.client_id, "tsp")
        if await ctx.session.get(TaskStep, step_input.client_id) is not None:
            raise ConflictError(f"Provided client_id for step is already in use.")
    kwargs = {}
    if step_input.client_id is not None:
        kwargs["client_id"] = step_input.client_id
    step = TaskStep(workspace_id=..., **kwargs, ...)
```

**Inline notes (in the notes loop — via `_create_task_note_in_session`):**
`_create_task_note_in_session` needs to accept `client_id: str | None = None` as a parameter (see Step 3d).

#### 3d. `services/commands/tasks/create_task_note.py`

**Update `_create_task_note_in_session` signature:**
```python
async def _create_task_note_in_session(
    session: AsyncSession,
    workspace_id: str,
    task_id: str,
    note_type: TaskNoteTypeEnum,
    content: dict,
    user_id: str,
    client_id: str | None = None,   # NEW
) -> TaskNote:
    if client_id is not None:
        validate_provided_client_id(client_id, "tno")
        if await session.get(TaskNote, client_id) is not None:
            raise ConflictError("Provided client_id is already in use.")
    kwargs = {}
    if client_id is not None:
        kwargs["client_id"] = client_id
    note = TaskNote(workspace_id=workspace_id, task_id=task_id, note_type=note_type, content=content, created_by_id=user_id, **kwargs)
    session.add(note)
    await session.flush()
    return note
```

**Update `create_task_note` command** (the public command, not the helper):
Parse `client_id` from `ctx.incoming_data` and pass to `_create_task_note_in_session`.

**Update `create_task.py` notes loop** to pass `note_input.client_id` to the helper:
```python
await _create_task_note_in_session(
    session=ctx.session,
    workspace_id=ctx.workspace_id,
    task_id=task.client_id,
    note_type=note_input.note_type,
    content=note_input.content,
    user_id=ctx.user_id,
    client_id=note_input.client_id,   # NEW — None if not provided
)
```

#### 3e. `services/commands/task_steps/add_task_step.py`

```python
if request.client_id is not None:
    validate_provided_client_id(request.client_id, "tsp")
    if await ctx.session.get(TaskStep, request.client_id) is not None:
        raise ConflictError("Provided client_id is already in use.")
kwargs = {}
if request.client_id is not None:
    kwargs["client_id"] = request.client_id
step = TaskStep(workspace_id=..., **kwargs, ...)
```

#### 3f. `routers/api_v1/tasks.py`

Add `client_id: str | None = None` to:
- `_CreateTaskBody`
- `_CreateNoteBody` (or equivalent for note creation)
- `_AddTaskStepBody`
- `_TaskStepInputBody` (nested step within task creation body)
- `_TaskNoteInputBody` (nested note within task creation body, if it exists as a class)
- The `_TaskItemInputBody` (nested item within task creation body — maps to `FindOrCreateItemInput`)

**CRITICAL:** `_CreateTaskBody` uses `body.model_dump(exclude_unset=True)` in `route_create_task`. This means if `client_id` is omitted, it does NOT appear in `incoming_data`. The request model receives the dict, and `client_id` resolves to `None` from its default. This is correct — no handler change needed.

---

### Step 4 — Cases domain

Read `routers/api_v1/cases.py` to identify all create body models and their commands. Apply the same pattern for:

- `Case` — read model file to confirm `CLIENT_ID_PREFIX`. Apply to `create_case.py` and the create body.
- `Conversation` — read model file to confirm prefix. Apply to `create_conversation.py` and body.
- `Message` (CaseConversationMessage) — read model file to confirm prefix. Apply to `send_message.py` and body.

For each:
1. Add `client_id: str | None = None` to the request model / parse function input
2. Apply `validate_provided_client_id` + duplicate check + `kwargs` constructor pattern
3. Add `client_id: str | None = None` to the router body model

---

### Step 5 — Working sections domain

Prefix: `"wsec"` (from `40_identity_local.md`).

Apply to:
- `services/commands/working_sections/create_working_section.py`
- The working section request model (read `working_sections/requests/__init__.py` or equivalent)
- `routers/api_v1/working_sections.py` create body

---

### Step 6 — Item upholsteries domain

Prefix: `"iup"` (from `40_identity_local.md`).

Apply to:
- `services/commands/items/create_item_upholstery.py`
- `ItemUpholsteryInput` in `tasks/requests/__init__.py` (used inline in task creation) — add `client_id: str | None = None`
- The upholstery request model used by the direct endpoint
- `routers/api_v1/item_upholsteries.py` `_CreateBody`

**Note for `_create_item_upholstery_in_session`:** Like `_create_task_note_in_session`, this session helper needs `client_id: str | None = None` added to its signature. The caller in `create_task.py` passes it through from `request.item_upholstery.client_id`.

---

### Step 7 — Upholstery inventories domain

Prefix: `"uin"` (from `40_identity_local.md`).

Apply to:
- `services/commands/upholstery/create_upholstery_inventory.py`
- The request model for upholstery inventory creation
- `routers/api_v1/upholstery_inventories.py` `_CreateBody`

---

## Critical implementation notes

### Constructor override pattern (ALL commands)

Do NOT pass `client_id=None` to the model constructor. Use the `kwargs` pattern:

```python
# CORRECT
kwargs = {}
if request.client_id is not None:
    kwargs["client_id"] = request.client_id
entity = MyModel(workspace_id=..., **kwargs)

# WRONG — may suppress SQLAlchemy default depending on version
entity = MyModel(client_id=request.client_id, workspace_id=...)
```

Verify by reading `models/base/identity.py` to confirm exact default behavior. If unsure, always use the `kwargs` pattern — it is safe in all cases.

### Find-or-create commands

The `client_id` validation must happen BEFORE the lookup query (fail fast). The duplicate check happens AFTER the lookup confirms no existing record is found. The find path returns early and the `client_id` is never used.

### Duplicate check scope

Use `await session.get(Model, provided_client_id)` — this queries by primary key and is O(1) with the PK index. It does NOT filter by `workspace_id` because `client_id` is globally unique (ULID collision probability ~0). If the key exists anywhere, reject.

### No changes to `IdentityMixin`

Do NOT modify `IdentityMixin`, `generate_id`, or any base model. The override is purely at the model constructor level in each command.

### Backward compatibility

All `client_id` fields default to `None`. Every existing test and client that omits `client_id` continues to work unchanged. This is a non-breaking additive change.

---

## Risks and mitigations

- **Risk:** SQLAlchemy `default` does not fire when `client_id=None` is passed explicitly.
  **Mitigation:** Always use the `kwargs` constructor pattern — only pass `client_id` when it is not `None`. Verify by reading `models/base/identity.py`.

- **Risk:** Find path in `find_or_create_*` silently ignores a provided `client_id` that conflicts with the found record.
  **Mitigation:** This is intentional and documented in Acceptance Criterion 5. The find path returns the existing record unconditionally. The frontend must handle the case where the returned `client_id` differs from the pre-generated one (treat as a deduplication event).

- **Risk:** Duplicate check using `session.get()` may return a stale identity-map result if the same session has already loaded the entity.
  **Mitigation:** Acceptable — if the session has already loaded the entity, it IS a duplicate within this session. No additional mitigation needed.

- **Risk:** Cases domain model prefixes unknown — Copilot may guess incorrectly.
  **Mitigation:** Step 4 explicitly requires reading model files to confirm `CLIENT_ID_PREFIX` before implementing. Do NOT guess prefixes.

- **Risk:** `_create_task_note_in_session` and `_create_item_upholstery_in_session` are called from `create_task.py` — signature changes must not break callers.
  **Mitigation:** New `client_id` parameter is keyword-only with default `None`. All existing call sites continue to work unchanged.

---

## Validation plan

Save to `backend/tests/client_id_injection/test_client_id_injection.sh`.

```bash
# 1. Create item with pre-generated client_id → item.client_id matches provided value
# 2. Create item without client_id → server generates normally
# 3. Create item with invalid format (wrong prefix) → 400 ValidationError
# 4. Create item with duplicate client_id → 409 ConflictError
# 5. find-or-create item: FIND path with client_id provided → returns existing id, not provided id
# 6. find-or-create item: CREATE path with client_id provided → creates with that client_id
# 7. Create task with client_id → task.client_id matches provided value
# 8. Create task with inline step that has client_id → step.client_id matches provided value
# 9. Create task with inline note that has client_id → note.client_id matches provided value
# 10. Create task with inline item that has client_id → item.client_id matches provided value
# 11. POST /tasks/{id}/steps with client_id → step.client_id matches provided value
# 12. POST /tasks/{id}/notes with client_id → note.client_id matches provided value
# 13. Create customer with client_id → customer.client_id matches provided value
# 14. Create case with client_id → case.client_id matches provided value
# 15. Create conversation with client_id → conversation.client_id matches provided value
# 16. Send message with client_id → message.client_id matches provided value
# 17. Create working section with client_id → working_section.client_id matches
# 18. Create item upholstery with client_id → upholstery.client_id matches
# 19. Create upholstery inventory with client_id → inventory.client_id matches
# 20. Image upload: entity_client_id = pre-generated item id → upload succeeds; after item creation with that id, image link resolves correctly
```

---

## Review log

- `2026-05-18T19:40:00Z` — Scope reviewed against contracts and local extensions; no clarifications required.
- `2026-05-18T19:45:00Z` — Implementation completed for all in-scope domains, summary created, archive record created.
- `2026-05-18T21:10:00Z` — End-to-end validation executed via `backend/tests/client_id_injection/test_client_id_injection.sh`; result `20 passed, 0 failed`.

---

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `copilot`
