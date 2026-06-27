# PLAN_task_note_corrections_20260626

## Metadata

- Plan ID: `PLAN_task_note_corrections_20260626`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-26T00:00:00Z`
- Last updated at (UTC): `2026-06-26T12:23:27Z`
- Related issue/ticket: `—`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_note_system_improvement_20260626.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_note_system_improvement_20260626.md`

---

## Goal and intent

- **Goal:** Apply six targeted corrections to the task-note implementation produced by `PLAN_task_note_system_improvement_20260626`, and add two improvements: batch note creation on the standalone notes endpoint, and explicit frontend documentation of notes inside `POST /tasks`.
- **Business/user intent:** Prevent soft-deleted notes from surfacing to the frontend, keep history records consistent with the rest of the codebase, fix an invalid SQL server-default, align minor type/doc inconsistencies, and let clients create multiple notes in one round-trip — both inline during task creation and via the dedicated notes endpoint.
- **Non-goals:** Adding pagination to `GET /{task_id}/notes`, adding realtime events, or changing any enum values beyond what C1 requires.

---

## Scope

### In scope

1. **(C1)** Fix `server_default="[]"` → `text("'[]'::jsonb")` in `TaskNote` model. Add `text` to the existing sqlalchemy import. No migration needed — the DB schema is already correct.
2. **(C2)** Add `TaskNote.is_deleted.is_(False)` filter to the `get_task_notes` query.
3. **(I1)** Replace `ctx.username` with `ctx.identity.get("username")` in `create_task_note.py` and `update_task_note.py`.
4. **(I2)** Add `task_id` to `MarkNoteReadByRequest` and validate `note.task_id == request.task_id` in `append_note_read_by` service. Router already passes `task_id` — no router change needed.
5. **(I3)** Add `"deleted_at": null` to the note object example in the frontend handoff document.
6. **(M1)** Align `content` type annotation: change `list[dict]` → `list` in both router body models (`_TaskNoteInputBody` and `_UpdateNoteBody`) to match the request model, which owns the canonical definition.
7. **(IMP-A)** Make `POST /{task_id}/notes` accept a **list** of note objects. Update `route_create_note` body, add `CreateBatchTaskNotesRequest` to requests, and update `create_task_note` service to loop over the list and return `{"client_ids": [...]}`. The `write_task_note` helper is called for each item — no change to the helper itself.
8. **(IMP-B)** Document `POST /tasks` note-injection in the handoff: the task creation endpoint already supports a `notes` list with optional client-side `client_id` per note using the `tno_` prefix. No code change needed — documentation only.

### Out of scope

- Any migration file changes (DB schema is already correct for all fixes).
- Changing the behavior of `update_task_note` with respect to task_id validation (pre-existing gap, not introduced by this plan).
- Updating the archive summary about `UPLOAD_NOTE_IMAGE` out-of-plan scope (documentation-only change that does not affect runtime behavior).
- Adding `notes` batch to `_CreateTaskBody` in the router — it already accepts `list[_TaskNoteInputBody]` and the service already iterates via `write_task_note`. No code change needed there.

### Assumptions

- No other code depends on `ctx.username` vs `ctx.identity.get("username")` in a way that would break by switching back to `None`.
- The `MarkNoteReadByRequest` change (adding `task_id: str`) is backward-compatible with the existing router, which already passes `task_id` in `incoming_data`.
- `text` from `sqlalchemy` can be added to the existing `from sqlalchemy import ...` line in `task_note.py`.
- Changing `POST /{task_id}/notes` from a single-body to a list-body is a **breaking change** for any frontend caller that currently sends a single object. The handoff must document this clearly.
- The response shape for `POST /{task_id}/notes` changes from `{"client_id": "tno_..."}` to `{"client_ids": ["tno_..."]}`. The handoff must reflect this.
- `TaskNoteInput` (already defined in `requests/__init__.py`) captures all per-note fields (`client_id`, `note_type`, `content`, `plain_text`, `users_read_list`) and can be reused inside `CreateBatchTaskNotesRequest` without duplication.

---

## Clarifications required

*(none — all fixes are precise and unambiguous)*

---

## Acceptance criteria

1. `TaskNote.users_read_list` column definition uses `server_default=text("'[]'::jsonb")`. Running `alembic check` produces no unexpected migration for this column.
2. `GET /{task_id}/notes` does not return notes with `is_deleted=true` in the default call.
3. History records for `create_task_note` and `update_task_note` store `username_snapshot=None` (not `""`) when the identity has no username — matching all other task commands.
4. `POST /{task_id}/notes/{note_id}/read-by` where `note_id` belongs to a different task than `task_id` returns a `NotFound` error (or equivalent 404 response).
5. The handoff document example shows `"deleted_at": null` inside the `note` object.
6. Router body models `_TaskNoteInputBody.content` and `_UpdateNoteBody.content` use `list` (not `list[dict]`).
7. `POST /{task_id}/notes` accepts a JSON array body (list of note objects). Sending a single note requires wrapping it: `[{...}]`. Response is `{"client_ids": ["tno_...", ...]}`.
8. The handoff documents `POST /api/v1/tasks` note injection with `notes: list` and the `tno_` client_id prefix convention.

---

## Contracts and skills

### Selected contracts

Core (already loaded in parent session — reload if needed):
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command structure, `maybe_begin`, session safety rules
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: query filter conventions
- `architecture/09_routers.md`: body model conventions
- `architecture/03_models.md`: `mapped_column` server_default conventions

### File read intent

All target files were read during the review. No additional relational reads are required before editing.

---

## Implementation plan

### Fix 1 — C1: Correct `server_default` on `TaskNote.users_read_list`

**File:** `app/beyo_manager/models/tables/tasks/task_note.py`

**Step 1a — add `sa` import.** The file currently imports individual names from `sqlalchemy`. Add `import sqlalchemy as sa` OR use the already-imported `text` if available. The cleanest approach is to import `text` from `sqlalchemy` alongside the existing imports:

Check whether `sqlalchemy` is already imported as a module alias. It is not — the file uses `from sqlalchemy import ...` style. Add `text` to that import line:

```python
# current import (approximate)
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Text

# change to
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Text, text
```

**Step 1b — fix server_default:**

```python
# current (line 31)
users_read_list: Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default="[]")

# corrected
users_read_list: Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
```

No migration is needed. The database schema already has the correct `DEFAULT '[]'::jsonb` from the existing migration.

---

### Fix 2 — C2: Filter deleted notes in `get_task_notes`

**File:** `app/beyo_manager/services/queries/tasks/get_task_notes.py`

Add `TaskNote.is_deleted.is_(False)` to the notes query:

```python
# current (lines 32-40)
notes_result = await ctx.session.execute(
    select(TaskNote)
    .where(
        TaskNote.workspace_id == ctx.workspace_id,
        TaskNote.task_id == task.client_id,
    )
    .order_by(TaskNote.created_at.asc())
)

# corrected
notes_result = await ctx.session.execute(
    select(TaskNote)
    .where(
        TaskNote.workspace_id == ctx.workspace_id,
        TaskNote.task_id == task.client_id,
        TaskNote.is_deleted.is_(False),
    )
    .order_by(TaskNote.created_at.asc())
)
```

No other changes in this file.

---

### Fix 3 — I1: Replace `ctx.username` with `ctx.identity.get("username")` in note commands

**File A:** `app/beyo_manager/services/commands/tasks/create_task_note.py`

```python
# current (line 43)
username = ctx.username

# corrected
username = ctx.identity.get("username")
```

**File B:** `app/beyo_manager/services/commands/tasks/update_task_note.py`

```python
# current (line 58)
username = ctx.username

# corrected
username = ctx.identity.get("username")
```

No other changes in either file.

---

### Fix 4 — I2: Add `task_id` validation to `append_note_read_by`

This fix has two parts: update the request model to accept `task_id`, then validate in the service.

**Part A — `app/beyo_manager/services/commands/tasks/requests/__init__.py`**

Update `MarkNoteReadByRequest`:

```python
# current
class MarkNoteReadByRequest(BaseModel):
    client_id: str
    user_ids: list[str]

# corrected
class MarkNoteReadByRequest(BaseModel):
    client_id: str
    task_id: str
    user_ids: list[str]
```

No change to `parse_mark_note_read_by_request` — the parser function is unchanged.

**Part B — `app/beyo_manager/services/commands/tasks/append_note_read_by.py`**

Add a task_id ownership check after the note is fetched:

```python
# current (lines 20-22)
        note = result.scalar_one_or_none()
        if note is None:
            raise NotFound("Task note not found.")

# corrected
        note = result.scalar_one_or_none()
        if note is None or note.task_id != request.task_id:
            raise NotFound("Task note not found.")
```

Using `note is None or note.task_id != request.task_id` deliberately returns the same `NotFound` for both cases to avoid leaking information about note existence in other tasks.

The router already passes `task_id` in `incoming_data` (`{"task_id": task_id, "client_id": note_id, ...}`), so no router change is needed.

---

### Fix 5 — I3: Add `deleted_at` to handoff example

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`

In the "List task notes" section, the note object in the example JSON is missing `deleted_at`. The line:

```json
          "is_deleted": false,
```

must be followed immediately by:

```json
          "deleted_at": null
```

Locate the example block (around line 107) and insert `"deleted_at": null` after `"is_deleted": false`.

---

### Fix 6 — M1: Align `content` type in router body models

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

Change `list[dict]` → `list` in both body models to match the canonical type in the request models:

```python
# current _TaskNoteInputBody (line 108)
content: list[dict]

# corrected
content: list
```

```python
# current _UpdateNoteBody (line 171)
content: list[dict] | None = None

# corrected
content: list | None = None
```

No other changes in this file for Fix 6. Fixes 7 applies additional changes to this same file.

---

### Fix 7 — IMP-A: Batch note creation on `POST /{task_id}/notes`

This fix has three parts: request model, service, and router.

**Part A — add `CreateBatchTaskNotesRequest` to `app/beyo_manager/services/commands/tasks/requests/__init__.py`**

`TaskNoteInput` (already in this file) carries all per-note fields. Reuse it:

```python
class CreateBatchTaskNotesRequest(BaseModel):
    task_id: str
    notes: list[TaskNoteInput]
```

Add a parser function at the bottom of the file alongside the other parsers:

```python
def parse_create_batch_task_notes_request(data: dict) -> CreateBatchTaskNotesRequest:
    try:
        return CreateBatchTaskNotesRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
```

`CreateTaskNoteRequest` is kept as-is — it is still used internally by the old single-note path if anything references it. But `create_task_note` service will switch to `CreateBatchTaskNotesRequest`.

**Part B — update `app/beyo_manager/services/commands/tasks/create_task_note.py`**

Replace the single-note flow with a batch loop. The task lookup, history record, and event dispatch remain the same. Only the note creation becomes a loop:

```python
# NEW imports to add
from beyo_manager.services.commands.tasks.requests import parse_create_batch_task_notes_request

# Remove the old import:
# from beyo_manager.services.commands.tasks.requests import parse_create_task_note_request


async def create_task_note(ctx: ServiceContext) -> dict:
    request = parse_create_batch_task_notes_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        created_ids: list[str] = []
        for note_input in request.notes:
            note = await write_task_note(
                ctx,
                task_id=request.task_id,
                note_type=note_input.note_type,
                content=note_input.content,
                plain_text=note_input.plain_text,
                users_read_list=note_input.users_read_list,
                client_id=note_input.client_id,
            )
            created_ids.append(note.client_id)

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

    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_ids": created_ids}
```

Key points:
- One history record is written per batch call (not per note), matching the existing single-note behavior.
- The return key changes from `"client_id"` (singular) to `"client_ids"` (list). This is a **breaking change** — the handoff must document it.
- Fix 3 (I1) for `ctx.username` is incorporated directly in this rewrite — no separate line edit needed for this file if Fix 7 is applied after Fix 3.

**Part C — update the router `route_create_note` in `app/beyo_manager/routers/api_v1/tasks.py`**

Change the body from a single object to a list, and update `incoming_data` to pass the list under the `notes` key:

```python
# current
@router.post("/{task_id}/notes")
async def route_create_note(
    task_id: str,
    body: _TaskNoteInputBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump()},
        identity=claims,
        session=session,
    )

# corrected
@router.post("/{task_id}/notes")
async def route_create_note(
    task_id: str,
    body: list[_TaskNoteInputBody],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "notes": [note.model_dump() for note in body]},
        identity=claims,
        session=session,
    )
```

Everything else in the handler (outcome check, `run_service`, `build_ok`) is unchanged.

---

### Fix 8 — IMP-B: Document task-creation note injection in the handoff

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`

Two documentation changes are required:

**8a — Update section "3. Create task note" to reflect the batch body**

The request body changes from a single object to an array, and the response key changes from `client_id` to `client_ids`:

```json
// Request body — now an array
[
  {
    "client_id": "tno_01...",
    "note_type": "user_note",
    "content": [{"type": "text", "text": "First note"}],
    "plain_text": "First note",
    "users_read_list": []
  },
  {
    "client_id": "tno_02...",
    "note_type": "user_note",
    "content": [{"type": "text", "text": "Second note"}],
    "plain_text": "Second note"
  }
]

// Success response
{
  "ok": true,
  "data": {
    "client_ids": ["tno_01...", "tno_02..."]
  },
  "warnings": []
}
```

Add the following notes below the example:
- `client_id` is optional per note. When provided, use the `tno_` prefix (e.g. `tno_<ulid>`). The backend validates the prefix and rejects duplicates.
- To create a single note, wrap it in an array: `[{...}]`.
- The array must not be empty. Sending `[]` is a validation error.

**8b — Add a new section "0. Create task (with inline notes)" before section "1. Get task detail"**

This section documents the note-injection capability of `POST /api/v1/tasks`:

```
### 0. Create task with inline notes

- Endpoint:
  - `POST /api/v1/tasks`
- Notes can be created inline during task creation by including a `notes` array in the request body.
- Each note follows the same shape as the standalone create-note endpoint.
- `client_id` per note is optional. When provided, use the `tno_` prefix.
- Notes are committed in the same transaction as the task — all succeed or all fail together.

Request body excerpt:
```json
{
  "task_type": "repair",
  "notes": [
    {
      "client_id": "tno_01...",
      "note_type": "user_note",
      "content": [{"type": "text", "text": "Picked up from customer"}],
      "plain_text": "Picked up from customer",
      "users_read_list": []
    }
  ]
}
```

- Success payload returns `{"client_id": "tsk_...", "task_scalar_id": 123}` — note client_ids are not returned separately from this endpoint. Use `GET /{task_id}/notes` to retrieve them after creation, or pre-generate them client-side using the `tno_` prefix.
```

---

## Risks and mitigations

- **Risk (Fix 4):** Changing `MarkNoteReadByRequest` to require `task_id` — if any other caller (internal or test) builds the incoming_data dict without `task_id`, validation will raise a `ValidationError`. The only caller is the router, which already supplies `task_id`. Test files for this service also need to include `task_id` in test data if they exist.
  **Mitigation:** The router already passes `task_id`; no functional callers are broken. Check any unit tests for `append_note_read_by` and add `task_id` to their fixture dicts.

- **Risk (Fix 1):** `alembic autogenerate` may still detect differences between the model and DB depending on the dialect inspector's interpretation of `text("'[]'::jsonb")` vs the stored default. If `alembic check` produces noise after this fix, the model can use `server_default=sa.text("'[]'::jsonb")` with an aliased import — functionally identical.
  **Mitigation:** Run `alembic check` after the fix to confirm no spurious migration is generated.

- **Risk (Fix 2):** If the frontend currently relies on seeing deleted notes (e.g., to show "this note was removed"), the filter change is a behavioral break. Based on the plan scope and no documented frontend dependency, this is safe.
  **Mitigation:** Documented in handoff as default behavior. An `include_deleted` query param can be added in a future plan if needed.

- **Risk (Fix 7 — breaking change):** `POST /{task_id}/notes` body changes from a single object to an array, and the response key changes from `"client_id"` to `"client_ids"`. Any frontend code sending a single object `{...}` will receive a 422 Unprocessable Entity from FastAPI.
  **Mitigation:** Coordinate frontend migration before deploying. The handoff (Fix 8) explicitly documents this breaking change. Codex must apply Fix 7 and Fix 8 atomically — do not deploy Fix 7 without Fix 8.

- **Risk (Fix 7 — empty array):** If `body` is an empty list `[]`, `create_task_note` would skip the loop and return `{"client_ids": []}` without writing anything. This is technically valid but semantically meaningless and could mask client bugs.
  **Mitigation:** Add a guard in the service: `if not request.notes: raise ValidationError("notes list must not be empty.")`. This should be in the service, not the request model, to keep the request model a plain data container per contract conventions.

---

## Validation plan

- `python3 -m compileall app/beyo_manager`: passes with no errors.
- `alembic check`: reports no pending migrations (Fix 1 correctness).
- `GET /{task_id}/notes` with a task that has a soft-deleted note: the deleted note is absent from the response.
- `POST /{task_id}/notes/{note_id}/read-by` where `note_id` belongs to a different task in the same workspace: returns `{"ok": false, "error": "Task note not found."}`.
- `POST /{task_id}/notes/{note_id}/read-by` with the correct task_id: succeeds and returns `{"client_id": "tno_..."}`.
- Existing unit tests for `create_task_note` and `update_task_note` history records pass (username_snapshot values may change from `""` to `None` in test assertions — update fixtures if needed).
- Handoff document contains `"deleted_at": null` in the example.
- `POST /{task_id}/notes` with a JSON array of two notes: returns `{"ok": true, "data": {"client_ids": ["tno_...", "tno_..."]}}`.
- `POST /{task_id}/notes` with a single-object body (not wrapped in array): returns 422 from FastAPI.
- `POST /{task_id}/notes` with an empty array `[]`: returns a validation error from the service.
- `POST /{task_id}/notes` with a `client_id` carrying the wrong prefix (e.g. `"tsk_abc"`): returns a validation error.
- `POST /{task_id}/notes` with a `client_id` that already exists: returns a conflict error.
- `POST /api/v1/tasks` with a `notes` list: task and all notes committed in the same transaction; `GET /{task_id}/notes` returns them.

---

## Review log

*(empty — correction plan, no prior review)*

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
