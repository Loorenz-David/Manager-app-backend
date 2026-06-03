# PLAN_issue_mode_20260603

## Metadata

- Plan ID: `PLAN_issue_mode_20260603`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-03T00:00:00Z`
- Last updated at (UTC): `2026-06-03T12:40:54Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add an `issue_mode` field to `IssueType` so the backend can communicate whether a given issue type is *graded* (intensity is a meaningful 1–N value, frontend shows a grade selector) or a *switch* (binary on/off, frontend always sends `intensity=1`). Snapshot the mode at the moment an `ItemIssue` is created so that analytics and display remain correct even if the mode later changes.
- Business/user intent: Not every issue type needs a numeric grade. Workers use different UIs for graded vs. switch issues. The backend is the authority on which mode each type has, but it does not enforce the intensity value — that is the frontend's responsibility. This enables the frontend to render the correct input widget by inspecting the issue type's mode.
- Non-goals: Backend validation that `intensity == 1` when `issue_mode == switch`. Changing how intensity is stored or validated on `ItemIssue`. Any changes to the analytics queries themselves.

## Scope

- In scope:
  - Add `IssueModeEnum` (`graded`, `switch`) to `domain/issue_types/enums.py`.
  - Add `issue_mode` column to `IssueType` model and table (non-nullable, server default `graded` for existing rows, ORM default `graded`).
  - Add `issue_mode_snapshot` column to `ItemIssue` model and table (nullable String(32) snapshot of the mode at creation time).
  - Update `serialize_issue_type` to include `issue_mode`.
  - Update `serialize_item_issue` to include `issue_mode_snapshot`.
  - Update `CreateIssueTypeRequest` and `_CreateIssueTypeBody` to require `issue_mode`.
  - Update `UpdateIssueTypeRequest` and `_UpdateIssueTypeBody` to accept optional `issue_mode`.
  - Update `create_issue_type` command to persist `issue_mode`.
  - Update `update_issue_type` command to update `issue_mode` when provided.
  - Update `_validate_issue_references_batch` in `batch_create_item_issues.py` to return the issue type mode map, and use it to populate `issue_mode_snapshot` on each created `ItemIssue`.
  - One Alembic migration covering all schema changes.

- Out of scope:
  - Any frontend changes.
  - Backend enforcement that `intensity == 1` for switch-mode issues.
  - Adding an `issue_mode` filter to `list_issue_types` query (no requirement stated).
  - History-record logging for mode changes.

- Assumptions:
  - `issue_mode` defaults to `graded` for all existing `IssueType` rows (server default in migration).
  - `issue_mode_snapshot` on `ItemIssue` is nullable to safely migrate existing rows without backfill. New issues will always have it set when `issue_type_id` is provided. When `issue_type_id` is None (custom issue), `issue_mode_snapshot` is also None.
  - The ORM default for `IssueType.issue_mode` is `IssueModeEnum.GRADED` so existing code paths that create issue types without providing the field still work (bootstrap, seed scripts).
  - The postgres enum type will be named `issue_mode_enum`.
  - `configure_sa_enum_values` (already used in the model file) is applied to `SAEnum` before use, following the existing pattern in `issue_type.py`.

## Clarifications required

_None — scope is fully defined._

## Acceptance criteria

1. `IssueType` model has `issue_mode: Mapped[IssueModeEnum]`, nullable=False, ORM default `IssueModeEnum.GRADED`.
2. `ItemIssue` model has `issue_mode_snapshot: Mapped[str | None]`, nullable=True.
3. `serialize_issue_type` output includes `"issue_mode": row.issue_mode.value`.
4. `serialize_item_issue` output includes `"issue_mode_snapshot": issue.issue_mode_snapshot`.
5. `PUT /api/v1/issue-types` requires `issue_mode` in the request body (`graded` or `switch`); omitting it returns a validation error.
6. `PATCH /api/v1/issue-types/{client_id}` accepts optional `issue_mode`; providing it updates the type; omitting it leaves it unchanged.
7. When a batch of item issues is created and `issue_type_id` is provided, the resulting `ItemIssue` rows have `issue_mode_snapshot` set to the issue type's current `issue_mode` value.
8. When `issue_type_id` is None in a batch create, `issue_mode_snapshot` is None on the created row.
9. Alembic migration applies cleanly with `alembic upgrade head` and rolls back cleanly with `alembic downgrade -1`.
10. `IssueModeEnum` is defined in `domain/issue_types/enums.py` alongside `IssueSourceEnum`.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline layered architecture rules
- `../../../architecture/04_context.md`: ServiceContext shape
- `../../../architecture/05_errors.md`: error imports
- `../../../architecture/06_commands.md`: command structure
- `../../../architecture/06_commands_local.md`: `maybe_begin`, session-call safety
- `../../../architecture/03_models.md`: SQLAlchemy model conventions, `IdentityMixin`, `configure_sa_enum_values`
- `../../../architecture/09_routers.md`: router handler wiring
- `../../../architecture/21_naming_conventions.md`: snake_case field naming
- `../../../architecture/30_migrations.md`: Alembic migration conventions
- `../../../architecture/46_serialization.md`: serializer output shape rules
- `../../../architecture/46_serialization_local.md`: app-specific serializer delta

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: `maybe_begin` utility
- `../../../architecture/46_serialization_local.md`: app-specific serializer rules

### File read intent — pattern vs. relational

Permitted reads (understanding what exists):
- `domain/issue_types/enums.py` — to know the existing enum class structure and add `IssueModeEnum` alongside `IssueSourceEnum`
- `models/tables/issue_types/issue_type.py` — to know the exact column order, `SAEnum` import alias, and `configure_sa_enum_values` usage for adding `issue_mode`
- `models/tables/items/item_issue.py` — to know the exact column order for inserting `issue_mode_snapshot`
- `services/commands/items/batch_create_item_issues.py` — to understand `_validate_issue_references_batch` return signature and how to thread the mode map through to the creation loop (this is existing behavior — not pattern reading)
- `services/commands/issue_types/create_issue_type.py` / `update_issue_type.py` — to know the exact `IssueType(...)` constructor call site (relational read)
- `services/commands/issue_types/requests/__init__.py` — to know the current field list for insert/update (relational read)
- `routers/api_v1/issue_types.py` — to know the body class field lists (relational read)

### Skill selection

- Primary skill: `../../../architecture/06_commands.md` (model addition + command update)
- Router trigger terms: `issue_mode`, `graded`, `switch`
- Excluded alternatives: `13_sockets.md` — no realtime events; `16_background_jobs.md` — no async workers

## Implementation plan

### Step 1 — Add `IssueModeEnum` to `domain/issue_types/enums.py`

Append to the existing file:

```python
class IssueModeEnum(enum.Enum):
    GRADED = "graded"
    SWITCH = "switch"
```

### Step 2 — Add `issue_mode` column to `IssueType` model

File: `backend/app/beyo_manager/models/tables/issue_types/issue_type.py`

- Add import: `from beyo_manager.domain.issue_types.enums import IssueSourceEnum, IssueModeEnum`
  (replacing the existing single-name import)
- Add column after `source`:
  ```python
  issue_mode: Mapped[IssueModeEnum] = mapped_column(
      SAEnum(IssueModeEnum, name="issue_mode_enum", create_type=True),
      nullable=False,
      default=IssueModeEnum.GRADED,
  )
  ```
  `SAEnum` here is already the configured alias from `configure_sa_enum_values(SAEnum)` at the top of the file.

### Step 3 — Add `issue_mode_snapshot` column to `ItemIssue` model

File: `backend/app/beyo_manager/models/tables/items/item_issue.py`

- Add column after `issue_type_snapshot`:
  ```python
  issue_mode_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
  ```
  No FK. No index needed — it is a low-cardinality snapshot field used for display, not filtering.

### Step 4 — Alembic migration

Create `backend/app/migrations/versions/<hash>_add_issue_mode.py`:

Upgrade:
1. Create the postgres enum type:
   ```python
   _issue_mode_enum = postgresql.ENUM("graded", "switch", name="issue_mode_enum", create_type=False)
   _issue_mode_enum.create(op.get_bind(), checkfirst=True)
   ```
2. Add column to `issue_types`:
   ```python
   op.add_column(
       "issue_types",
       sa.Column(
           "issue_mode",
           postgresql.ENUM("graded", "switch", name="issue_mode_enum", create_type=False),
           nullable=True,
       ),
   )
   op.execute("UPDATE issue_types SET issue_mode = 'graded' WHERE issue_mode IS NULL")
   op.alter_column("issue_types", "issue_mode", nullable=False)
   ```
3. Add column to `item_issues`:
   ```python
   op.add_column("item_issues", sa.Column("issue_mode_snapshot", sa.String(length=32), nullable=True))
   ```

Downgrade:
1. Drop `issue_mode_snapshot` from `item_issues`
2. Drop `issue_mode` from `issue_types`
3. Drop the postgres enum type `issue_mode_enum`

### Step 5 — Update `serialize_issue_type`

File: `backend/app/beyo_manager/domain/issue_types/serializers.py`

Add `"issue_mode": row.issue_mode.value` to the returned dict, after `"source"`:
```python
def serialize_issue_type(
    row: IssueType,
    linked_working_section_ids: list[str] | None = None,
    linked_item_category_ids: list[dict] | None = None,
) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "source": row.source.value,
        "issue_mode": row.issue_mode.value,
        "linked_working_section_ids": linked_working_section_ids or [],
        "linked_item_category_ids": linked_item_category_ids or [],
        "created_at": row.created_at.isoformat(),
        "created_by_id": row.created_by_id,
    }
```

Also add the `IssueModeEnum` import if needed (it is not currently imported here, but since the value is accessed via `.value` off the ORM row attribute, no import is strictly needed unless referenced explicitly).

### Step 6 — Update `serialize_item_issue`

File: `backend/app/beyo_manager/domain/items/serializers.py`

Add `"issue_mode_snapshot": issue.issue_mode_snapshot` after `"issue_type_snapshot"`:
```python
def serialize_item_issue(issue: ItemIssue) -> dict:
    return {
        "client_id": issue.client_id,
        "workspace_id": issue.workspace_id,
        "item_id": issue.item_id,
        "step_id": issue.step_id,
        "worker_id": issue.worker_id,
        "working_section_id": issue.working_section_id,
        "item_category_id": issue.item_category_id,
        "issue_type_id": issue.issue_type_id,
        "issue_type_snapshot": issue.issue_type_snapshot,
        "issue_mode_snapshot": issue.issue_mode_snapshot,
        "placement_of_issue_snapshot": issue.placement_of_issue_snapshot,
        "intensity": issue.intensity,
        "created_at": issue.created_at.isoformat(),
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }
```

### Step 7 — Update `CreateIssueTypeRequest` and `UpdateIssueTypeRequest`

File: `backend/app/beyo_manager/services/commands/issue_types/requests/__init__.py`

- Add import: `from beyo_manager.domain.issue_types.enums import IssueModeEnum`
- In `CreateIssueTypeRequest`: add required field `issue_mode: IssueModeEnum` (no default — omitting it must be a validation error)
- In `UpdateIssueTypeRequest`: add optional field `issue_mode: IssueModeEnum | None = None`

No new parse functions needed — the existing `parse_create_issue_type_request` and `parse_update_issue_type_request` will automatically handle the new fields.

### Step 8 — Update `create_issue_type` command

File: `backend/app/beyo_manager/services/commands/issue_types/create_issue_type.py`

In the `IssueType(...)` constructor call, add `issue_mode=request.issue_mode`:
```python
issue_type = IssueType(
    workspace_id=ctx.workspace_id,
    name=request.issue_type_name,
    source=IssueSourceEnum.MANUAL,
    issue_mode=request.issue_mode,
    created_by_id=ctx.user_id,
)
```

### Step 9 — Update `update_issue_type` command

File: `backend/app/beyo_manager/services/commands/issue_types/update_issue_type.py`

After the name-update block and before the working-section diff, add:
```python
if request.issue_mode is not None:
    issue_type.issue_mode = request.issue_mode
```

### Step 10 — Update `_validate_issue_references_batch` to return mode map

File: `backend/app/beyo_manager/services/commands/items/batch_create_item_issues.py`

Change the return type of `_validate_issue_references_batch` from `None` to `dict[str, str]` — a map of `{issue_type_id: issue_mode_value}`.

Currently the function fetches `IssueType.client_id` only. Change the IssueType query to fetch both `client_id` and `issue_mode`, and build a map:

```python
# Replace the existing IssueType validation block:
if issue_type_ids:
    rows = (await session.execute(
        select(IssueType.client_id, IssueType.issue_mode).where(
            IssueType.workspace_id == workspace_id,
            IssueType.client_id.in_(issue_type_ids),
            IssueType.is_deleted.is_(False),
        )
    )).all()
    found_types = {row.client_id for row in rows}
    if issue_type_ids != found_types:
        raise NotFound(f"Issue type(s) not found: {', '.join(sorted(issue_type_ids - found_types))}")
    issue_mode_map = {row.client_id: row.issue_mode.value for row in rows}
else:
    issue_mode_map = {}

return issue_mode_map
```

Update the function signature:
```python
async def _validate_issue_references_batch(
    session: AsyncSession,
    workspace_id: str,
    issues_data: list[_IssueCreatePayload],
) -> dict[str, str]:
```

### Step 11 — Use mode map in `_create_item_issues_in_session`

File: `backend/app/beyo_manager/services/commands/items/batch_create_item_issues.py`

Update `_create_item_issues_in_session` to receive and use the mode map:

```python
async def _create_item_issues_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    issues_data: list[_IssueCreatePayload],
) -> list[str]:
    issue_mode_map = await _validate_issue_references_batch(session, workspace_id, issues_data)

    item_issue_ids: list[str] = []
    for issue_data in issues_data:
        issue = ItemIssue(
            workspace_id=workspace_id,
            item_id=item_id,
            step_id=issue_data.step_id,
            worker_id=issue_data.worker_id,
            working_section_id=issue_data.working_section_id,
            item_category_id=issue_data.item_category_id,
            issue_type_id=issue_data.issue_type_id,
            issue_type_snapshot=issue_data.issue_type_snapshot,
            issue_mode_snapshot=issue_mode_map.get(issue_data.issue_type_id) if issue_data.issue_type_id else None,
            placement_of_issue_snapshot=issue_data.placement_of_issue_snapshot,
            intensity=issue_data.intensity,
        )
        session.add(issue)
        item_issue_ids.append(issue.client_id)

    await session.flush()
    return item_issue_ids
```

### Step 12 — Update router body classes

File: `backend/app/beyo_manager/routers/api_v1/issue_types.py`

- Add import at the top: `from beyo_manager.domain.issue_types.enums import IssueModeEnum`
- In `_CreateIssueTypeBody`: add required field `issue_mode: IssueModeEnum`
- In `_UpdateIssueTypeBody`: add optional field `issue_mode: IssueModeEnum | None = None`

## Risks and mitigations

- Risk: Existing `IssueType` rows in the database have no `issue_mode` value after the column is added. The migration must backfill them to `graded` before adding the NOT NULL constraint; a two-step `ADD COLUMN nullable → UPDATE → ALTER COLUMN NOT NULL` is required.
  Mitigation: Step 4 uses exactly this pattern.

- Risk: `issue_mode_snapshot` is nullable on `ItemIssue`. Historical rows (before this migration) will have NULL, and new rows where `issue_type_id=None` will also have NULL. Queries or display logic must handle NULL gracefully.
  Mitigation: `serialize_item_issue` returns `None` for the field when unset, consistent with other nullable snapshot fields.

- Risk: The `_validate_issue_references_batch` signature change (now returns `dict[str, str]` instead of `None`) must be reflected at all call sites. Currently only `_create_item_issues_in_session` calls it internally; no external callers exist.
  Mitigation: Both functions are in the same file. Verify with a grep before committing.

- Risk: `IssueType.issue_mode` uses `configure_sa_enum_values(SAEnum)` (the configured alias). The new enum column must use the same `SAEnum` alias, not the raw `sqlalchemy.Enum`, to remain consistent with the file pattern.
  Mitigation: Step 2 notes this explicitly.

## Validation plan

- `alembic upgrade head`: applies cleanly
- `alembic downgrade -1`: rolls back cleanly
- `PUT /api/v1/issue-types` without `issue_mode`: returns 422 validation error
- `PUT /api/v1/issue-types` with `"issue_mode": "graded"`: creates issue type; GET returns `"issue_mode": "graded"`
- `PUT /api/v1/issue-types` with `"issue_mode": "switch"`: creates issue type; GET returns `"issue_mode": "switch"`
- `PATCH /api/v1/issue-types/{id}` with `"issue_mode": "switch"`: updates existing type; GET confirms change
- `POST /api/v1/items/{id}/issues` with a valid `issue_type_id` for a `switch`-mode type: created issue has `"issue_mode_snapshot": "switch"` in response
- `POST /api/v1/items/{id}/issues` with `issue_type_id: null`: created issue has `"issue_mode_snapshot": null` in response
- Import smoke test: no `ImportError` on startup

## Review log

_None yet._

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `david`
