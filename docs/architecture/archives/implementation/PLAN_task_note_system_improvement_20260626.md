# PLAN_task_note_system_improvement_20260626

## Metadata

- Plan ID: `PLAN_task_note_system_improvement_20260626`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-26T00:00:00Z`
- Last updated at (UTC): `2026-06-26T10:56:46Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/improving_note_system.txt`

---

## Goal and intent

- **Goal:** Improve the `TaskNote` model and its associated routers and services so that notes carry structured `content` (list of blocks), a `plain_text` derivative, a `users_read_list` JSONB field, and can have images attached. Extract note retrieval into its own dedicated query endpoint and remove notes from the `get_task` response.
- **Business/user intent:** Allow the frontend to display richer notes (formatted content, who has read them, attached images) without coupling note data loading to the main task fetch. Enable marking notes as "read by" users in a lightweight, independent call.
- **Non-goals:** Changing the `TaskNoteTypeEnum` values, adding WebSocket events for note reads, pagination of notes (first version returns all notes for a task).

---

## Scope

### In scope

1. `TaskNote` model — add `plain_text` (String, nullable) and `users_read_list` (JSONB, default `[]`).
2. `ImageLinkEntityTypeEnum` — add `NOTE = "note"`.
3. `ImageLink` model — add `major_entity_type` (String 64, nullable) and `major_entity_client_id` (String 128, nullable).
4. `create_task_note` service — migrate `content` from `dict` to `list[block]`, validate with `validate_content`, support `plain_text` and `users_read_list`, extract note-write logic into `write_task_note` helper.
5. `update_task_note` service — same content type change, support `plain_text` update, delegate to `write_task_note` helper for content.
6. New helper `note_writes.py` — `write_task_note(...)` mirrors `write_case_message`, validates content blocks via `validate_content`.
7. New command service `append_note_read_by.py` — appends a list of strings to `TaskNote.users_read_list`; the function signature is intentionally independent of what the strings represent.
8. New query service `get_task_notes.py` — fetches all notes for a given task_id, enriches with `created_by`/`updated_by` (User + WorkspaceMembership + WorkspaceRole + Role), fetches ImageLinks with entity_type=NOTE, and serializes via new serializer.
9. Task serializers — replace `serialize_note` with `serialize_note_with_images`; new serializer includes `created_by`, `updated_by` (using `serialize_user_compact_with_role`), `plain_text`, `users_read_list`, and `note_images` list.
10. `get_task` query — remove the `task_notes` key from the response dict and remove the `TaskNote` query inside that function.
11. Task router `tasks.py` — update body models for `route_create_note` and `route_update_note`; add `GET /{task_id}/notes` and `POST /{task_id}/notes/{note_id}/read-by` routes.
12. Request models (`services/commands/tasks/requests/__init__.py`) — update `CreateTaskNoteRequest` and `UpdateTaskNoteRequest`; add `MarkNoteReadByRequest`.
13. Single Alembic migration for all DB changes above.
14. Frontend handoff document at `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`.

### Out of scope

- WebSocket / realtime events for note creation or read receipts.
- Pagination of note list (return all).
- Image upload for notes (ImageLink rows are already created by the image upload flow; this plan only adds the entity type and enables querying).
- Changing existing `TaskNoteTypeEnum` values.
- Worker-side notification when a note is created.

### Assumptions

- The image upload service already creates `ImageLink` rows with an `entity_type` and `entity_client_id`; adding `NOTE` to the enum is sufficient to enable image attachment without modifying the upload flow.
- `users_read_list` is append-only from the API; the service never shrinks the list.
- Content mention processing for task notes already has the `ContentMentionLinkEntityTypeEnum.TASK_NOTE_MENTION` value defined (`domain/content/enums.py` line 14).
- `serialize_user_compact_with_role` requires role data; the `get_task_notes` query must join `WorkspaceMembership → WorkspaceRole → Role` for every unique creator/updater user_id, matching the pattern used in `list_users`.

---

## Clarifications required

*(none — intention is clear and all referenced models/helpers have been inspected)*

---

## Acceptance criteria

1. `POST /{task_id}/notes` accepts `content: list[block]`, `plain_text: str`, `users_read_list: list[str] | None`, saves all fields, and returns `{"client_id": "tno_..."}`.
2. `PATCH /{task_id}/notes/{note_id}` accepts `content: list[block] | None`, `plain_text: str | None`, updates them, and returns `{"client_id": "tno_..."}`.
3. `POST /{task_id}/notes/{note_id}/read-by` with `{"user_ids": [...]}` appends to `users_read_list` without duplicates and returns `{"client_id": "tno_..."}`.
4. `GET /{task_id}/notes` returns a list of objects each shaped as `{note: {..., created_by, updated_by, plain_text, users_read_list}, note_images: [...]}`.
5. `GET /{task_id}` no longer includes a `task_notes` key.
6. `ImageLinkEntityTypeEnum` has `NOTE = "note"` and the Alembic migration reflects the enum change.
7. `ImageLink` table has `major_entity_type` and `major_entity_client_id` nullable columns.
8. `task_notes` table has `plain_text` (nullable text) and `users_read_list` (JSONB, nullable, server_default `'[]'`) columns.
9. Migration file applies cleanly with `alembic upgrade head`.

---

## Contracts and skills

### Selected contracts

Core (always loaded):
- `architecture/01_architecture.md`: layer discipline, no cross-layer imports
- `architecture/04_context.md`: `ServiceContext` shape, `user_id`, `workspace_id`
- `architecture/05_errors.md`: `NotFound`, `ValidationError`, `ConflictError` — when and how to raise
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command structure, `maybe_begin`, session call safety rules
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: query structure, offset pagination
- `architecture/09_routers.md`: handler wiring, `build_ok` / `build_err`, `run_service`
- `architecture/21_naming_conventions.md`: file naming, function naming
- `architecture/40_identity.md`: `IdentityMixin`, `CLIENT_ID_PREFIX` convention
- `architecture/41_user.md`: User model and workspace membership
- `architecture/42_event.md`: event dispatch pattern
- `architecture/48_presence.md`: not applicable but loaded as core

CRUD + realtime bundle additions:
- `architecture/03_models.md`: SQLAlchemy model conventions (`Mapped`, `mapped_column`, JSONB)
- `architecture/08_domain.md`: domain enums and serializers live in `domain/<entity>/`
- `architecture/30_migrations.md`: Alembic migration file conventions

### Local extensions loaded

- `architecture/06_commands_local.md`: `maybe_begin` transaction utility, subordinate-command event rule
- `architecture/07_queries_local.md`: offset pagination override (no cursor pagination)

### File read intent — pattern vs. relational

**Pattern reads (prohibited — contracts already define these):**
- Reading another command to understand `session.add / flush / error-raising` shape → `06_commands.md`
- Reading another router to understand handler skeleton → `09_routers.md`
- Reading another serializer to understand output dict shape → use the contract, not an existing file

**Relational reads (legitimate):**
- `app/beyo_manager/models/tables/tasks/task_note.py` — exact column names and types currently on the model ✓ read
- `app/beyo_manager/models/tables/images/image_link.py` — existing columns before adding new ones ✓ read
- `app/beyo_manager/models/tables/notifications/notification_pin.py` — pattern for `major_entity_type` / `major_entity_client_id` columns ✓ read
- `app/beyo_manager/domain/images/enums.py` — existing `ImageLinkEntityTypeEnum` values ✓ read
- `app/beyo_manager/domain/content/enums.py` — `InputContentTypeEnum`, `ContentMentionLinkEntityTypeEnum` ✓ read
- `app/beyo_manager/services/commands/cases/message_writes.py` — `write_case_message` shape to mirror ✓ read
- `app/beyo_manager/services/infra/content.py` — `validate_content` / `process_content_mentions` signatures ✓ read
- `app/beyo_manager/domain/users/serializers.py` — `serialize_user_compact_with_role` parameters ✓ read
- `app/beyo_manager/services/queries/users/list_users.py` — join pattern for User + WorkspaceMembership + WorkspaceRole + Role ✓ read
- `app/beyo_manager/domain/images/serializers.py` — `serialize_image` signature ✓ read
- `app/beyo_manager/services/commands/tasks/requests/__init__.py` — existing request models to update ✓ read
- `app/beyo_manager/services/commands/tasks/create_task_note.py` — current implementation to refactor ✓ read
- `app/beyo_manager/services/commands/tasks/update_task_note.py` — current implementation to refactor ✓ read
- `app/beyo_manager/services/queries/tasks/tasks.py` — locate `task_notes` block to remove ✓ read

### Skill selection

- Primary skill: `architecture/06_commands.md` (command writes), `architecture/07_queries.md` (query reads)
- Router trigger terms: `tasks`, `notes`, `read-by`
- Excluded alternatives: `16_background_jobs.md` — no background work; `13_sockets.md` — no realtime events for notes in this iteration

---

## Implementation plan

### Step 1 — Extend `ImageLinkEntityTypeEnum`

**File:** `app/beyo_manager/domain/images/enums.py`

Add `NOTE = "note"` to `ImageLinkEntityTypeEnum`:

```python
class ImageLinkEntityTypeEnum(StrEnum):
    ITEM = "item"
    CASE = "case"
    CASE_CONVERSATION_MESSAGE = "case_conversation_message"
    ITEM_CATEGORY = "item_category"
    NOTE = "note"   # ← ADD
```

---

### Step 2 — Extend `ImageLink` model

**File:** `app/beyo_manager/models/tables/images/image_link.py`

Add two nullable columns after `created_at`, mirroring `NotificationPin`:

```python
major_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
major_entity_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
```

No index is required here by default (consult migration needs if queries require it).

---

### Step 3 — Extend `TaskNote` model

**File:** `app/beyo_manager/models/tables/tasks/task_note.py`

Add two columns after the existing `content` column:

```python
from sqlalchemy.dialects.postgresql import JSONB

plain_text: Mapped[str | None] = mapped_column(String, nullable=True)
users_read_list: Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default="'[]'")
```

Change the existing `content` column type from `JSON` to `JSON` (no change to the column type — JSON is correct for a list; the type annotation changes from `dict` to `list` only in Python type hints, not the SA column type).

---

### Step 4 — Alembic migration

**File:** `app/migrations/versions/<hash>_improve_task_notes_and_image_links.py`

Generate with:
```
alembic revision --autogenerate -m "improve_task_notes_and_image_links"
```

The migration must include:

```python
# 1. Add columns to task_notes
op.add_column('task_notes', sa.Column('plain_text', sa.String(), nullable=True))
op.add_column('task_notes', sa.Column('users_read_list', postgresql.JSONB(), nullable=True,
              server_default=sa.text("'[]'")))

# 2. Add columns to image_links
op.add_column('image_links', sa.Column('major_entity_type', sa.String(64), nullable=True))
op.add_column('image_links', sa.Column('major_entity_client_id', sa.String(128), nullable=True))

# 3. Extend the PostgreSQL enum image_link_entity_type_enum with new value
op.execute("ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'note'")
```

**Downgrade must:**
- Drop the four columns.
- Note: removing an enum value from a PostgreSQL enum is not directly possible without recreating; the downgrade should document this limitation and skip the enum rollback (or recreate the enum without 'note').

After generating, run `alembic upgrade head` to verify the migration applies cleanly.

---

### Step 5 — `write_task_note` helper

**New file:** `app/beyo_manager/services/commands/tasks/note_writes.py`

Mirrors `services/commands/cases/message_writes.py`. This helper is the only place that constructs a `TaskNote` row and processes content mentions.

```python
from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.content import process_content_mentions, validate_content
from beyo_manager.errors.validation import ConflictError
from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum


async def write_task_note(
    ctx: ServiceContext,
    *,
    task_id: str,
    note_type: TaskNoteTypeEnum,
    content: list,
    plain_text: str,
    users_read_list: list[str] | None = None,
    client_id: str | None = None,
) -> TaskNote:
    if client_id is not None:
        validate_provided_client_id(client_id, "tno")
        existing = await ctx.session.get(TaskNote, client_id)
        if existing is not None:
            raise ConflictError("Provided client_id is already in use.")

    blocks = validate_content(content)
    normalized_content = [block.__dict__ for block in blocks]

    note_kwargs: dict = {}
    if client_id is not None:
        note_kwargs["client_id"] = client_id

    note = TaskNote(
        **note_kwargs,
        workspace_id=ctx.workspace_id,
        task_id=task_id,
        note_type=note_type,
        content=normalized_content,
        plain_text=plain_text,
        users_read_list=users_read_list or [],
        created_by_id=ctx.user_id,
    )
    ctx.session.add(note)
    await ctx.session.flush()

    await process_content_mentions(
        ctx.session,
        normalized_content,
        ContentMentionLinkEntityTypeEnum.TASK_NOTE_MENTION,
        note.client_id,
        ctx.user_id,
    )
    return note
```

---

### Step 6 — Update request models

**File:** `app/beyo_manager/services/commands/tasks/requests/__init__.py`

**Change `TaskNoteInput`:**
```python
class TaskNoteInput(BaseModel):
    client_id: str | None = None
    note_type: TaskNoteTypeEnum
    content: list          # was: dict
    plain_text: str = ""
    users_read_list: list[str] | None = None
```

**Change `CreateTaskNoteRequest`:**
```python
class CreateTaskNoteRequest(BaseModel):
    client_id: str | None = None
    task_id: str
    note_type: TaskNoteTypeEnum
    content: list          # was: dict
    plain_text: str = ""
    users_read_list: list[str] | None = None
```

**Change `UpdateTaskNoteRequest`:**
```python
class UpdateTaskNoteRequest(BaseModel):
    client_id: str
    note_type: TaskNoteTypeEnum | None = None
    content: list | None = None     # was: dict | None
    plain_text: str | None = None   # ← ADD
```

**Add new request model:**
```python
class MarkNoteReadByRequest(BaseModel):
    client_id: str          # note_id from URL
    user_ids: list[str]
```

**Add parser function at the bottom:**
```python
def parse_mark_note_read_by_request(data: dict) -> MarkNoteReadByRequest:
    try:
        return MarkNoteReadByRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
```

---

### Step 7 — Refactor `create_task_note`

**File:** `app/beyo_manager/services/commands/tasks/create_task_note.py`

Replace the inline note construction with a call to `write_task_note`. Remove the private `_create_task_note_in_session` function. The public `create_task_note` function signature does not change.

Key diff:
- Import `write_task_note` from `.note_writes`
- Pass `content=request.content`, `plain_text=request.plain_text`, `users_read_list=request.users_read_list` to `write_task_note`
- Remove the old `content: dict` parameter from the helper (now in `write_task_note`)
- The subordinate helper call from `create_task` (which passes through `_create_task_note_in_session`) must be updated: in `create_task.py`, replace the internal helper call with `write_task_note(ctx, ...)` or keep a thin internal function that calls `write_task_note`. Check whether `create_task.py` calls `_create_task_note_in_session` directly.

> **Read `create_task.py` before editing** — this is a relational read to find whether the helper is called there.

---

### Step 8 — Refactor `update_task_note`

**File:** `app/beyo_manager/services/commands/tasks/update_task_note.py`

- Change `updated_fields` list to include `plain_text` alongside `note_type` and `content`.
- When `content` is in `request.model_fields_set`: call `validate_content(request.content)` and store `[block.__dict__ for block in blocks]` as the new content; also call `process_content_mentions` with `replace=True` to replace existing mention links.
- When `plain_text` is in `request.model_fields_set`: `note.plain_text = request.plain_text`.
- When `note_type` is in `request.model_fields_set`: `note.note_type = request.note_type`.

Import additions: `validate_content` from `services.infra.content`, `process_content_mentions`, `ContentMentionLinkEntityTypeEnum`.

---

### Step 9 — New command: `append_note_read_by`

**New file:** `app/beyo_manager/services/commands/tasks/append_note_read_by.py`

The service appends user_ids to `TaskNote.users_read_list`. The service is intentionally agnostic about what the strings mean — the router is responsible for deciding what to pass.

```python
from sqlalchemy import select
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.tasks.requests import parse_mark_note_read_by_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def append_note_read_by(ctx: ServiceContext) -> dict:
    request = parse_mark_note_read_by_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(TaskNote).where(
                TaskNote.workspace_id == ctx.workspace_id,
                TaskNote.client_id == request.client_id,
                TaskNote.is_deleted.is_(False),
            )
        )
        note = result.scalar_one_or_none()
        if note is None:
            raise NotFound("Task note not found.")

        existing = set(note.users_read_list or [])
        new_entries = [uid for uid in request.user_ids if uid not in existing]
        if new_entries:
            note.users_read_list = list(existing) + new_entries

    return {"client_id": note.client_id}
```

No event dispatch — read receipts do not trigger workspace events.

---

### Step 10 — New serializer: `serialize_note_with_images`

**File:** `app/beyo_manager/domain/tasks/serializers.py`

**Remove** `serialize_note`. **Add** `serialize_note_with_images`:

```python
from beyo_manager.domain.images.serializers import serialize_image
from beyo_manager.domain.users.serializers import serialize_user_compact_with_role


def serialize_note_with_images(
    note: TaskNote,
    created_by_user=None,
    created_by_role_client_id: str | None = None,
    created_by_role_name: str | None = None,
    created_by_workspace_role_client_id: str | None = None,
    created_by_workspace_role_name: str | None = None,
    updated_by_user=None,
    updated_by_role_client_id: str | None = None,
    updated_by_role_name: str | None = None,
    updated_by_workspace_role_client_id: str | None = None,
    updated_by_workspace_role_name: str | None = None,
    note_images: list | None = None,
) -> dict:
    def _user_compact(user, role_cid, role_name, ws_role_cid, ws_role_name):
        if user is None:
            return None
        return serialize_user_compact_with_role(
            user,
            role_client_id=role_cid or "",
            role_name=role_name or "",
            workspace_role_client_id=ws_role_cid or "",
            workspace_role_name=ws_role_name or "",
        )

    return {
        "note": {
            "client_id": note.client_id,
            "task_id": note.task_id,
            "note_type": note.note_type.value,
            "content": note.content,
            "plain_text": note.plain_text,
            "users_read_list": note.users_read_list or [],
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "created_by": _user_compact(
                created_by_user,
                created_by_role_client_id,
                created_by_role_name,
                created_by_workspace_role_client_id,
                created_by_workspace_role_name,
            ),
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            "updated_by": _user_compact(
                updated_by_user,
                updated_by_role_client_id,
                updated_by_role_name,
                updated_by_workspace_role_client_id,
                updated_by_workspace_role_name,
            ),
            "is_deleted": note.is_deleted,
        },
        "note_images": [serialize_image(img) for img in (note_images or [])],
    }
```

---

### Step 11 — New query service: `get_task_notes`

**New file:** `app/beyo_manager/services/queries/tasks/get_task_notes.py`

Query logic:

1. Load all `TaskNote` rows for `task_id` and `workspace_id`, ordered by `created_at ASC`.
2. Collect all unique user_ids from `created_by_id` and `updated_by_id`.
3. Load users with their role data via the same join used in `list_users`:
   ```sql
   SELECT User, Role.client_id, Role.name, WorkspaceRole.client_id, WorkspaceRole.name
   FROM users
   JOIN workspace_memberships ON workspace_memberships.user_id = users.client_id
   JOIN workspace_roles ON workspace_roles.client_id = workspace_memberships.workspace_role_id
   JOIN roles ON roles.client_id = workspace_roles.role_id
   WHERE workspace_memberships.workspace_id = ctx.workspace_id
     AND users.client_id IN (<user_ids>)
     AND workspace_memberships.is_active IS TRUE
   ```
   Build a map: `users_role_map: dict[str, tuple[User, role_cid, role_name, ws_role_cid, ws_role_name]]`.
4. Collect all note `client_id` values. Load `Image` rows joined via `ImageLink`:
   ```sql
   SELECT Image, ImageLink.entity_client_id
   FROM images
   JOIN image_links ON image_links.image_id = images.client_id
     AND image_links.entity_type = 'note'
     AND image_links.entity_client_id IN (<note_ids>)
   WHERE images.deleted_at IS NULL
   ORDER BY image_links.entity_client_id, image_links.display_order ASC
   ```
   Build a map: `note_images_map: dict[str, list[Image]]`.
5. Serialize each note with `serialize_note_with_images(note, user data from map, images from map)`.
6. Return `{"task_notes": [...]}`

---

### Step 12 — Remove notes from `get_task`

**File:** `app/beyo_manager/services/queries/tasks/tasks.py`

- Remove the `notes_result` query block (lines 410–416 in current file).
- Remove the `"task_notes": [serialize_note(n) for n in notes]` key from the returned dict.
- Remove the import of `serialize_note` from task serializers if it is no longer used elsewhere.

> **Verify** `serialize_note` is not used by any other file before removing the import. A quick grep confirms it is only used in `tasks.py`.

---

### Step 13 — Update task router

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

**Update `_TaskNoteInputBody`:**
```python
class _TaskNoteInputBody(BaseModel):
    client_id: str | None = None
    note_type: TaskNoteTypeEnum
    content: list           # was: dict
    plain_text: str = ""
    users_read_list: list[str] | None = None
```

**Update `_UpdateNoteBody`:**
```python
class _UpdateNoteBody(BaseModel):
    note_type: TaskNoteTypeEnum | None = None
    content: list | None = None     # was: dict | None
    plain_text: str | None = None   # ← ADD
```

**Add new body model:**
```python
class _MarkNoteReadByBody(BaseModel):
    user_ids: list[str]
```

**Update `route_create_note`** — the body already passes `body.model_dump()` so it picks up new fields automatically. No change needed to the handler body.

**Add new route `GET /{task_id}/notes`:**
```python
@router.get("/{task_id}/notes")
async def route_get_task_notes(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_task_notes, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Add new route `POST /{task_id}/notes/{note_id}/read-by`:**
```python
@router.post("/{task_id}/notes/{note_id}/read-by")
async def route_mark_note_read_by(
    task_id: str,
    note_id: str,
    body: _MarkNoteReadByBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": note_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(append_note_read_by, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Add imports at top of router:
```python
from beyo_manager.services.commands.tasks.append_note_read_by import append_note_read_by
from beyo_manager.services.queries.tasks.get_task_notes import get_task_notes
```

---

### Step 14 — Frontend handoff document

**New file:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`

Document:
- All changed endpoints (create note, update note) with new field shapes
- All new endpoints (get notes, mark read-by) with full request/response shapes
- Removed field (`task_notes`) from `GET /{task_id}` response
- Enum change: `ImageLinkEntityTypeEnum` now includes `"note"` — affects image upload entity_type for notes

---

## Risks and mitigations

- **Risk:** `content` type change from `dict` to `list` is a breaking change for the create/update note API. Any existing frontend code sending `content` as a dict will break.
  **Mitigation:** Document in the handoff; frontend must update before or simultaneously. The migration does not change stored JSONB; existing stored content (which is a dict) will still load — only new writes must be lists.

- **Risk:** Existing stored `task_notes.content` rows contain a JSON object (dict), not a list. If the frontend reads these via the new `GET /{task_id}/notes` endpoint, the content field will be a dict, not a list of blocks.
  **Mitigation:** Document that legacy notes may have dict-typed content. A one-time data migration (not in this plan) would normalize old rows. Frontend should handle both shapes defensively during the transition window.

- **Risk:** Removing `task_notes` from `GET /{task_id}` is a breaking change for any frontend code reading task_notes from the task detail response.
  **Mitigation:** Frontend must switch to the new `GET /{task_id}/notes` endpoint before the backend is deployed. Document explicitly in the handoff.

- **Risk:** Adding the `note` value to the `image_link_entity_type_enum` PostgreSQL enum is not reversible without recreating the type.
  **Mitigation:** Alembic downgrade documents this limitation. Acceptable because enum additions are safe (no existing rows reference the new value).

- **Risk:** `users_read_list` JSONB column defaults to `'[]'` server-side; older rows will have `NULL` until touched. The serializer uses `note.users_read_list or []` to guard against this.
  **Mitigation:** Handled in serializer. No data backfill needed.

---

## Validation plan

- `alembic upgrade head`: applies cleanly with no errors.
- `alembic downgrade -1` then `alembic upgrade head`: round-trips without data loss (noting enum caveat).
- `POST /{task_id}/notes` with `content: [{"type": "text", "text": "hello"}]`, `plain_text: "hello"` → returns `client_id`.
- `GET /{task_id}/notes` → returns list with `note.content` as list, `note_images` as `[]` if no images, `created_by` with role.
- `PATCH /{task_id}/notes/{note_id}` with `content: [...]` → updates content, returns `client_id`.
- `POST /{task_id}/notes/{note_id}/read-by` with `user_ids: ["usr_abc"]` → appends, second call with same user_id is idempotent (no duplicate in list).
- `GET /{task_id}` → response does NOT contain `task_notes`.
- `POST /{task_id}/notes` with `content: {"bad": "dict"}` → returns `ValidationError` "content must be a list of blocks".

---

## Review log

*(empty — awaiting implementation)*

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david` (review and approve before codex begins implementation)
