# PLAN_task_notes_20260518

## Metadata

- Plan ID: `PLAN_task_notes_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-2`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement task notes (CMD-16 `create_task_note`, CMD-17 `update_task_note`, CMD-18 `delete_task_note`), add the `_create_task_note_in_session` session-level helper, add an Alembic migration to add `updated_at` and `updated_by_id` to the `task_notes` table, and amend CMD-1 (`create_task`) to call the helper for each note in the task creation payload.
- **Business/user intent:** Workers, sellers, managers, and admins can attach structured notes to tasks during creation and at any later point. Notes have `note_type` (enum) and `content` (JSON). Notes are soft-deleted, never hard-deleted.
- **Non-goals:** Note querying (notes are returned within QUERY-2 task detail — that is covered in Plan 1). No realtime events for notes.

---

## Prerequisite

**Plan 1 (`PLAN_task_crud_queries_router_20260518`) must be completed before this plan.** The migration in this plan adds columns to `task_notes`; CMD-1 is amended in this plan. The task router already exists.

---

## Scope

- **In scope:**
  - Alembic migration: add `updated_at` (DateTime, timezone=True, nullable) and `updated_by_id` (FK → `users.client_id`, nullable) to `task_notes`
  - Update `models/tables/tasks/task_note.py` to include the two new columns
  - New request models in `services/commands/tasks/requests/__init__.py` (append)
  - New command: `services/commands/tasks/create_task_note.py` — CMD-16 (exposes `_create_task_note_in_session`)
  - New command: `services/commands/tasks/update_task_note.py` — CMD-17
  - New command: `services/commands/tasks/delete_task_note.py` — CMD-18
  - Amend `services/commands/tasks/create_task.py` (CMD-1): handle `notes` field in creation payload
  - Add routes to existing `routers/api_v1/tasks.py`
- **Out of scope:** Note querying endpoints (beyond what QUERY-2 already returns), search/filter on notes.
- **Assumptions:** `task_notes` table exists. `TaskNoteTypeEnum` values exist in `domain/tasks/enums.py`.

---

## Clarifications required

_None. All decisions locked in intention plan._

---

## Acceptance criteria

1. `POST /api/v1/tasks/{task_id}/notes` creates a `TaskNote` with `note_type` and `content`. Returns `{client_id}`. Accessible to all roles (ADMIN, MANAGER, SELLER, WORKER).
2. `PATCH /api/v1/tasks/{task_id}/notes/{note_id}` updates `content` and/or `note_type` on a non-deleted note. Sets `updated_at` and `updated_by_id`. Returns `{client_id}`. Requires migration to be applied.
3. `DELETE /api/v1/tasks/{task_id}/notes/{note_id}` soft-deletes: `is_deleted = True`, `deleted_at`, `deleted_by_id`. Returns `{client_id}`.
4. `PUT /api/v1/tasks` with a `notes` array in the payload creates each note atomically in the same transaction as the task. Notes are created via `_create_task_note_in_session`. If a note fails, the entire task creation rolls back.
5. `_create_task_note_in_session` has no `maybe_begin` — it is a session-level helper called inside the caller's active transaction. It must not open its own transaction.
6. CMD-17 (`update_task_note`) raises `NotFound` if the note does not exist or is already deleted. Raises `ConflictError` if attempting to update a deleted note.
7. Migration is applied before CMD-17 routes are tested. CMD-16 and CMD-18 work before the migration (they do not reference `updated_at`/`updated_by_id`).
8. The `task_notes` model file is updated to include both new columns so ORM operations do not fail after migration.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: structure
- `backend/architecture/04_context.md`: `ServiceContext`
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound`, `ConflictError`
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, session helper pattern, subordinate-command event rule
- `backend/architecture/09_routers.md`: router handler wiring
- `backend/architecture/21_naming_conventions.md`: naming
- `backend/architecture/30_migrations.md`: Alembic migration pattern

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/tasks/task_note.py` | All existing columns, enum, index names |
| `domain/tasks/enums.py` | `TaskNoteTypeEnum` values |
| `services/commands/items/create_item_issue.py` | Session-level helper pattern (no `maybe_begin`) |
| `services/commands/tasks/create_task.py` | How to amend CMD-1 to call `_create_task_note_in_session` |

---

## Implementation plan

### Step 1 — Alembic migration

**File:** new migration in `alembic/versions/` — create with `alembic revision --autogenerate -m "add_updated_at_updated_by_to_task_notes"` OR write manually.

**Migration `upgrade()`:**
```python
op.add_column("task_notes", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
op.add_column("task_notes", sa.Column("updated_by_id",
    sa.String(64),
    sa.ForeignKey("users.client_id", name="fk_task_notes_updated_by_id", ondelete="RESTRICT"),
    nullable=True
))
```

**Migration `downgrade()`:**
```python
op.drop_constraint("fk_task_notes_updated_by_id", "task_notes", type_="foreignkey")
op.drop_column("task_notes", "updated_by_id")
op.drop_column("task_notes", "updated_at")
```

**Apply before proceeding to CMD-17 tests.**

### Step 2 — Update `models/tables/tasks/task_note.py`

Add the two new columns to the `TaskNote` model class after `created_by_id`:

```python
updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
updated_by_id: Mapped[str | None] = mapped_column(
    String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
)
```

Do NOT remove or reorder existing columns.

### Step 3 — Add request models to `services/commands/tasks/requests/__init__.py`

Append these to the end of the file (do not modify existing models):

```
CreateTaskNoteRequest:
  task_id: str
  note_type: TaskNoteTypeEnum
  content: dict

UpdateTaskNoteRequest:
  client_id: str
  note_type: TaskNoteTypeEnum | None   (model_fields_set semantics)
  content: dict | None

DeleteTaskNoteRequest:
  client_id: str

TaskNoteInput:  (nested input used in CreateTaskRequest notes list)
  note_type: TaskNoteTypeEnum
  content: dict
```

Also amend `CreateTaskRequest` to include:
```python
notes: list[TaskNoteInput] | None = None
```

Add parse functions: `parse_create_task_note_request`, `parse_update_task_note_request`, `parse_delete_task_note_request`.

### Step 4 — CMD-16: `services/commands/tasks/create_task_note.py`

This file defines both the public command `create_task_note(ctx)` AND the session-level helper `_create_task_note_in_session`.

**`_create_task_note_in_session` signature:**
```python
async def _create_task_note_in_session(
    session: AsyncSession,
    workspace_id: str,
    task_id: str,
    note_type: TaskNoteTypeEnum,
    content: dict,
    user_id: str,
) -> TaskNote:
```

**Body:** create `TaskNote(workspace_id, task_id, note_type, content, created_by_id=user_id)`, `session.add(note)`, `await session.flush()`. Return `note`. **No `maybe_begin` — no transaction management. This function assumes it is called inside an active session.**

**`create_task_note(ctx: ServiceContext) -> dict`:**
```python
async def create_task_note(ctx: ServiceContext) -> dict:
    request = parse_create_task_note_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        # Verify task exists and belongs to workspace
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
        note = await _create_task_note_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=request.task_id,
            note_type=request.note_type,
            content=request.content,
            user_id=ctx.user_id,
        )
    return {"client_id": note.client_id}
```

### Step 5 — CMD-17: `services/commands/tasks/update_task_note.py`

Flow:
1. Parse request (client_id, note_type?, content?).
2. `async with maybe_begin(ctx.session):`
3. Fetch `TaskNote` by `client_id + workspace_id`. 404 if not found.
4. Raise `ConflictError` if `note.is_deleted`.
5. Apply `model_fields_set` semantics: if `note_type` in `request.model_fields_set`, set it; if `content` in `request.model_fields_set`, set it.
6. Set `note.updated_at = datetime.now(timezone.utc)`, `note.updated_by_id = ctx.user_id`.
7. Return `{"client_id": note.client_id}`.

**Note:** `TaskNote` does not have `workspace_id` on the SELECT guard — check the model. If `workspace_id` is a column on `TaskNote`, filter by it. If not, filter via `task_id` → `Task.workspace_id`.

Correct approach: `TaskNote` has a `workspace_id` column (verified from model read). Use it directly.

### Step 6 — CMD-18: `services/commands/tasks/delete_task_note.py`

Flow:
1. Parse request (client_id).
2. Fetch `TaskNote` by `client_id + workspace_id`. 404 if not found. `ConflictError` if already deleted.
3. Set `is_deleted = True`, `deleted_at = now()`, `deleted_by_id = ctx.user_id`.
4. Return `{"client_id": note.client_id}`.

### Step 7 — Amend CMD-1: `services/commands/tasks/create_task.py`

Add import:
```python
from beyo_manager.services.commands.tasks.create_task_note import _create_task_note_in_session
from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum
```

In the `async with maybe_begin(ctx.session):` block, **after the task is flushed** (so `task.client_id` is available), add:
```python
if request.notes:
    for note_input in request.notes:
        await _create_task_note_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=task.client_id,
            note_type=note_input.note_type,
            content=note_input.content,
            user_id=ctx.user_id,
        )
```

Also update `CreateTaskRequest` (in requests) to include `notes: list[TaskNoteInput] | None = None` (done in Step 3 above).

### Step 8 — Add routes to `routers/api_v1/tasks.py`

**Add these imports:**
```python
from beyo_manager.services.commands.tasks.create_task_note import create_task_note
from beyo_manager.services.commands.tasks.update_task_note import update_task_note
from beyo_manager.services.commands.tasks.delete_task_note import delete_task_note
```

**Route body models to add:**
```python
class _CreateNoteBody(BaseModel):
    note_type: TaskNoteTypeEnum
    content: dict

class _UpdateNoteBody(BaseModel):
    note_type: TaskNoteTypeEnum | None = None
    content: dict | None = None
```

**Routes to add** (insert before or after the items routes — order is not ambiguous here since paths are distinct):
```
POST   "/{task_id}/notes"               → route_create_note   (ALL roles)
PATCH  "/{task_id}/notes/{note_id}"     → route_update_note   (ALL roles)
DELETE "/{task_id}/notes/{note_id}"     → route_delete_note   (ALL roles)
```

**Handler pattern for PATCH:**
```python
ctx = ServiceContext(
    incoming_data={"client_id": note_id, **body.model_dump(exclude_unset=True)},
    identity=claims,
    session=session,
)
```

---

## Risks and mitigations

- **Risk:** CMD-17 tests fail before migration is applied — `updated_at`/`updated_by_id` columns don't exist.
  **Mitigation:** Acceptance criterion 7 explicitly stages migration before CMD-17 tests. Bash test script for CMD-17 must verify migration is applied first.

- **Risk:** `_create_task_note_in_session` accidentally wraps its operations in a `maybe_begin` (copy-paste from other helpers).
  **Mitigation:** Step 4 states explicitly: **No `maybe_begin`**. If a helper has `maybe_begin`, it cannot be called safely from within CMD-1's transaction without risk of premature commit.

- **Risk:** CMD-1 amendment breaks existing CMD-1 tests from Plan 1.
  **Mitigation:** `notes` field in `CreateTaskRequest` defaults to `None`. Existing tests that don't pass `notes` are unaffected.

---

## Validation plan

Save to `backend/tests/tasks/test_task_notes.sh`. Run after Plan 1 tests pass.

```bash
# 1. Create task without notes (must still work after CMD-1 amendment)
# 2. Create task WITH notes → notes appear in GET /tasks/{id} response
# 3. POST /tasks/{id}/notes → new note created, returns {client_id}
# 4. PATCH /tasks/{id}/notes/{note_id} → note_type/content updated; updated_at set
# 5. DELETE /tasks/{id}/notes/{note_id} → soft-deleted; subsequent GET shows is_deleted
# 6. Attempt PATCH on deleted note → 409 ConflictError
# 7. Attempt POST note on non-existent task → 404
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
