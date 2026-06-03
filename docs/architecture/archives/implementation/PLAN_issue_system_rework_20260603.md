# PLAN_issue_system_rework_20260603

## Metadata

- Plan ID: `PLAN_issue_system_rework_20260603`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-03T00:00:00Z`
- Last updated at (UTC): `2026-06-03T08:31:19Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Rework the issue system so that issues are logged as snapshots at the moment a worker starts a task step — capturing issue type, intensity (frontend-provided integer), and contextual IDs (step, worker, working section, item category). Remove the old time-estimate-based severity/category-config system. Add issue-type management commands (create, update, batch-delete) that also manage linkage to working sections and item categories.
- Business/user intent: Workers select issues (filtered by working section and item category) at step-start time. Each issue is stored with a numeric intensity chosen by the worker. Over time, analytics can correlate step completion time with issue types and intensity levels, enabling better step-duration estimates. Managers can configure issue types once and link them to the relevant working sections and item categories (with optional placement descriptions).
- Non-goals: Realtime socket broadcast of issue operations. Changing existing working-section CRUD, task-step lifecycle, or item CRUD outside the embedded issue creation path. Building the analytics queries themselves (just the data foundation).

## Scope

- In scope:
  - Delete `IssueSeverity` table/model and all references.
  - Delete `IssueCategoryConfig` table/model and all references.
  - Replace `ItemIssue` model columns with the new snapshot-centric schema.
  - Create new `ItemCategoryIssueType` table (maps issue type to item category, with optional placement_of_issue).
  - New commands: `batch_create_item_issues`, `batch_delete_item_issues` (replace the three old item-issue commands).
  - New commands (issue-type management): `create_issue_type`, `update_issue_type`, `delete_issue_types` (batch).
  - Update `create_item` and `create_task` to use the new batch-create helper.
  - Update `serialize_item_issue` and `list_item_issues_by_item_id` (renamed to `get_item_issues`) with new shape + filters.
  - Update `items.py` router: replace old issue endpoints with new batch-create, batch-delete, and filterable GET.
  - Update `issue_types.py` router: add create/update/delete endpoints; remove `category_configs_router` entirely.
  - One Alembic migration covering all schema changes.
  - Clean up bootstrap and reset phases that seed/delete severity and category-config records.

- Out of scope:
  - `IssueType` table schema itself (unchanged).
  - `WorkingSectionSupportedIssueType` table schema (unchanged; existing link creation not changed).
  - Analytics queries over the new data.
  - Any frontend changes.
  - History records for issue operations (no history logging on issue create/delete).
  - Realtime event dispatch for issue operations.

- Assumptions:
  - `step_id`, `worker_id`, `working_section_id`, `item_category_id` are all required (nullable=False) on `ItemIssue`. They are captured as snapshot context at step-start time and will not change.
  - `issue_type_snapshot` is required (nullable=False) on `ItemIssue`. It captures the issue-type name at creation time so analytics remain valid even after issue type deletion.
  - `placement_of_issue_snapshot` is optional (nullable=True).
  - `intensity` is an Integer >= 1, nullable=False.
  - `ItemIssue` retains soft-delete columns (`is_deleted`, `deleted_at`, `deleted_by_id`) even though the spec does not list them, to remain consistent with the app-wide soft-delete convention.
  - When deleting an `IssueType`, we manually NULL `issue_type_id` on linked `ItemIssue` rows in the delete command (the soft-delete of `IssueType` does not trigger the DB-level FK cascade). The `ItemIssue.issue_type_id` FK keeps `ondelete="RESTRICT"` since the type is never hard-deleted.
  - `ItemCategoryIssueType` link records use hard-delete (same as `WorkingSectionSupportedIssueType`).
  - When updating an issue type's linkages, the diff approach is used: compute what changed and add/remove records only for deltas.
  - The existing `GET /{client_id}/issues` route is upgraded in-place (same URL, expanded parameters). No new URL segment is introduced.
  - Batch-create issues endpoint: `POST /api/v1/items/{client_id}/issues` with a list body (replaces old single-issue POST).
  - Batch-delete issues endpoint: `DELETE /api/v1/items/{client_id}/issues` accepts `[{"item_issue_id": "string"}]`.

## Clarifications required

- [ ] `Should batch_delete_item_issues validate that all issue_ids belong to the given item_id path param, or is workspace-level ownership sufficient?` — If an issue_id from one item is accidentally sent with another item's client_id, the current assumption is workspace-level scoping is sufficient and item-level check is optional. Blocks safe request-validation design.
- [ ] `For update_issue_type: when a linked_item_category_ids entry already exists but with a different placement_of_issue, should the existing record be updated in-place or deleted-and-recreated?` — Affects whether the client_id of the link record is stable. Blocks migration of existing link data if any.

## Acceptance criteria

1. `item_issues` table has exactly these columns (plus `is_deleted`, `deleted_at`, `deleted_by_id` for soft-delete): `client_id`, `workspace_id`, `item_id`, `step_id`, `worker_id`, `working_section_id`, `item_category_id`, `issue_type_id` (nullable), `issue_type_snapshot`, `placement_of_issue_snapshot` (nullable), `intensity`, `created_at`, `updated_at`.
2. `issue_severities` and `issue_category_configs` tables are dropped; no model, query, command, router, or bootstrap/reset reference remains.
3. `POST /api/v1/items/{client_id}/issues` accepts a list of issue objects and creates them atomically; returns `{"item_issue_ids": [...]}`.
4. `DELETE /api/v1/items/{client_id}/issues` accepts `[{"item_issue_id": "string"}]` and soft-deletes the listed issues.
5. `GET /api/v1/items/{client_id}/issues` accepts `q`, `working_section_id`, `item_category_id`, `issue_type_id`, `limit`, `offset` and returns `{"item_issues_pagination": {"items": [...], "limit": ..., "offset": ..., "has_more": ...}}`.
6. Each serialized item issue contains exactly: `client_id`, `workspace_id`, `item_id`, `step_id`, `worker_id`, `working_section_id`, `item_category_id`, `issue_type_id`, `issue_type_snapshot`, `placement_of_issue_snapshot`, `intensity`, `created_at`, `updated_at`.
7. `PUT /api/v1/issue-types` creates an issue type and its working-section/item-category links in one transaction.
8. `PATCH /api/v1/issue-types/{client_id}` updates name and re-syncs links (add/remove deltas).
9. `DELETE /api/v1/issue-types` (body: `[{"issue_type_id": "string"}]`) soft-deletes the issue types, hard-deletes their link records, and NULLs `issue_type_id` on related `ItemIssue` rows — all in one transaction.
10. `item_category_issue_types` table exists with columns: `client_id`, `workspace_id`, `item_category_id`, `issue_type_id`, `placement_of_issue` (nullable); unique on `(workspace_id, item_category_id, issue_type_id)`.
11. `create_item` and `create_task` accept the new issue shape (including `step_id`, `worker_id`, `working_section_id`, `item_category_id`, `issue_type_snapshot`, `intensity`) when embedding issues inline.
12. Alembic migration applies cleanly with `alembic upgrade head` and rolls back cleanly with `alembic downgrade -1`.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline layered architecture rules
- `../../../architecture/04_context.md`: ServiceContext shape, how incoming_data and query_params flow
- `../../../architecture/05_errors.md`: NotFound, ValidationError, ConflictError — correct imports
- `../../../architecture/06_commands.md`: command structure, session.add/flush/error-raising shape
- `../../../architecture/06_commands_local.md`: `maybe_begin` transaction utility, session-call safety rules
- `../../../architecture/07_queries.md`: query service structure, batch-load pattern
- `../../../architecture/07_queries_local.md`: offset pagination (not cursor); `has_more` via limit+1 probe
- `../../../architecture/09_routers.md`: FastAPI handler wiring, `run_service`, `build_ok`/`build_err`
- `../../../architecture/03_models.md`: SQLAlchemy model conventions, `IdentityMixin`, `CLIENT_ID_PREFIX`
- `../../../architecture/21_naming_conventions.md`: snake_case fields, table naming, file naming
- `../../../architecture/25_soft_delete.md`: soft-delete columns, filter rules (`is_deleted.is_(False)`)
- `../../../architecture/30_migrations.md`: Alembic migration file conventions, op.* calls
- `../../../architecture/46_serialization.md`: serializer output shape, no ORM lazy loads in serializers
- `../../../architecture/46_serialization_local.md`: app-specific serializer delta
- `../../../architecture/55_query_filters_local.md`: `apply_string_filter` utility at `services/queries/utils/string_filter.py`

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: adds `maybe_begin`, subordinate-command helper pattern
- `../../../architecture/07_queries_local.md`: overrides cursor pagination with offset; `has_more` = fetch limit+1 rows
- `../../../architecture/46_serialization_local.md`: app-specific serializer rules
- `../../../architecture/55_query_filters_local.md`: `apply_string_filter(stmt, q, string_filters, allowed_columns)`

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `models/__init__.py` to verify import order and registration
- Reading `routers/api_v1/__init__.py` (the app factory) to find where category_configs_router is registered
- Reading `domain/items/enums.py` to verify which enums are used only by deleted code
- Reading `services/commands/tasks/requests/__init__.py` to understand the existing `ItemIssueInput` shape
- Reading `services/commands/bootstrap/bootstrap_app.py` and `reset/reset_app.py` to locate phase references

### Skill selection

- Primary skill: `../../../architecture/06_commands.md` (CRUD + domain command layer)
- Router trigger terms: `issue`, `item_issue`, `issue_type`
- Excluded alternatives: `16_background_jobs.md` — no async workers needed; `13_sockets.md` — no realtime broadcast for issue operations; `11_infra_events.md` — issue create/delete does not fire workspace events

## Implementation plan

### Step 1 — New model: `ItemCategoryIssueType`

Create `backend/app/beyo_manager/models/tables/items/item_category_issue_type.py`:
- `CLIENT_ID_PREFIX = "icit"`
- `__tablename__ = "item_category_issue_types"`
- Columns: `workspace_id` (String(64), FK `workspaces.client_id` RESTRICT, index), `item_category_id` (String(64), FK `item_categories.client_id` RESTRICT, index), `issue_type_id` (String(64), FK `issue_types.client_id` RESTRICT, index), `placement_of_issue` (String(255), nullable=True)
- No soft-delete columns (hard-delete link, same as `WorkingSectionSupportedIssueType`)
- `UniqueConstraint("workspace_id", "item_category_id", "issue_type_id", name="uq_item_category_issue_types_unique")`

### Step 2 — Rewrite model: `ItemIssue`

Replace `backend/app/beyo_manager/models/tables/items/item_issue.py` with new schema:
- Keep: `IdentityMixin` (client_id), `workspace_id`, `item_id`, `issue_type_id`, `created_at`, `updated_at`, `is_deleted`, `deleted_at`, `deleted_by_id`
- Remove: `issue_severity_id`, `state` (and `ItemIssueStateEnum` import), `base_time_seconds`, `time_multiplier`, `issue_name_snapshot`, `severity_name_snapshot`, `created_by_id`, `started_at`, `resolved_at`, `updated_by_id`, old `Index` / `CheckConstraint` blocks
- Add columns:
  - `step_id`: `String(64)`, FK `task_steps.client_id` RESTRICT, nullable=False, index=True
  - `worker_id`: `String(64)`, FK `users.client_id` RESTRICT, nullable=False, index=True
  - `working_section_id`: `String(64)`, FK `working_sections.client_id` RESTRICT, nullable=False, index=True
  - `item_category_id`: `String(64)`, FK `item_categories.client_id` RESTRICT, nullable=False, index=True
  - `issue_type_id`: `String(64)`, FK `issue_types.client_id` RESTRICT, nullable=True, index=True (nullable so it can be NULLed on issue-type deletion)
  - `issue_type_snapshot`: `String(255)`, nullable=False
  - `placement_of_issue_snapshot`: `String(255)`, nullable=True
  - `intensity`: `Integer`, nullable=False
- Add `CheckConstraint("intensity >= 1", name="ck_item_issues_intensity_positive")`
- New compound index: `Index("ix_item_issues_workspace_item", "workspace_id", "item_id")`
- New compound index: `Index("ix_item_issues_workspace_step", "workspace_id", "step_id")`
- Remove `SAEnum` import and `ItemIssueStateEnum` — no longer needed

### Step 3 — Update `models/__init__.py`

File: `backend/app/beyo_manager/models/__init__.py`
- Remove: `from beyo_manager.models.tables.issue_types import issue_severity`
- Remove: `from beyo_manager.models.tables.issue_types import issue_category_config`
- Remove comment `# --- Issue category config (depends on issue_type and item_category) ---`
- Add after the existing item_issue import: `from beyo_manager.models.tables.items import item_category_issue_type  # noqa: F401`
- Change comment for item_issue section to clarify new dependency: `# --- Item issues (depends on item, issue_type, task_steps, working_sections) ---`

### Step 4 — Remove `ItemIssueStateEnum` from enums (if unused after deletion)

Read `backend/app/beyo_manager/domain/items/enums.py` and remove `ItemIssueStateEnum` if it is only referenced by `item_issue.py` and the deleted command files. Confirm no other file references it before deleting.

### Step 5 — Alembic migration

Create `backend/app/migrations/versions/<hash>_issue_system_rework.py`:

Upgrade operations (in order):
1. Drop FK `item_issues.issue_severity_id` → `issue_severities.client_id`
2. Drop FK `issue_category_configs.issue_type_id` → `issue_types.client_id`
3. Drop FK `issue_category_configs.item_category_id` → `item_categories.client_id`
4. Drop table `issue_category_configs`
5. Drop table `issue_severities`
6. On `item_issues`:
   - Drop indexes: `ix_item_issues_workspace_state`, `ix_item_issues_workspace_item_state`
   - Drop columns: `issue_severity_id`, `state`, `base_time_seconds`, `time_multiplier`, `issue_name_snapshot`, `severity_name_snapshot`, `created_by_id`, `started_at`, `resolved_at`, `updated_by_id`
   - Drop check constraints: `ck_item_issues_base_time_positive`, `ck_item_issues_time_multiplier_positive`
   - Add columns: `step_id VARCHAR(64) NOT NULL`, `worker_id VARCHAR(64) NOT NULL`, `working_section_id VARCHAR(64) NOT NULL`, `item_category_id VARCHAR(64) NOT NULL`, `issue_type_snapshot VARCHAR(255) NOT NULL`, `placement_of_issue_snapshot VARCHAR(255)`, `intensity INTEGER NOT NULL`
   - Add check constraint `ck_item_issues_intensity_positive` on `intensity >= 1`
   - Add FK: `item_issues.step_id` → `task_steps.client_id` RESTRICT
   - Add FK: `item_issues.worker_id` → `users.client_id` RESTRICT
   - Add FK: `item_issues.working_section_id` → `working_sections.client_id` RESTRICT
   - Add FK: `item_issues.item_category_id` → `item_categories.client_id` RESTRICT
   - Create indexes: `ix_item_issues_workspace_item`, `ix_item_issues_workspace_step`
7. Create table `item_category_issue_types` with all columns from Step 1
8. Drop postgres enum type `item_issue_state_enum` (if it exists as a named type)

Downgrade operations (reverse order):
- Undo all of the above in reverse. For the columns dropped from `item_issues`, re-add them as nullable (since existing data would not have values). Re-create the dropped tables as empty.

### Step 6 — Update serializer `serialize_item_issue`

File: `backend/app/beyo_manager/domain/items/serializers.py`

Replace `serialize_item_issue` body:
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
        "placement_of_issue_snapshot": issue.placement_of_issue_snapshot,
        "intensity": issue.intensity,
        "created_at": issue.created_at.isoformat(),
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }
```

Also update `serialize_item_detail` in the same file — it embeds `item_issues` but the signature does not change; the updated serializer handles the new shape.

Update `domain/tasks/serializers.py` — find any `serialize_item_issue` usage that referenced `issue_severity_id`, `state`, etc. and remove those fields (or delegate to the shared serializer above).

### Step 7 — New command: `batch_create_item_issues`

Create `backend/app/beyo_manager/services/commands/items/batch_create_item_issues.py`:

```
_create_item_issues_in_session(
    session, workspace_id, item_id, issues_data: list[ItemIssueCreateInput], user_id
) -> list[str]
```

This session-level helper creates `ItemIssue` rows for every entry in `issues_data`, calls `session.add` for each, and does a single `await session.flush()` after the loop. Returns a list of `client_id` strings.

Each `ItemIssue` is constructed with:
- `workspace_id`, `item_id` from arguments
- `step_id`, `worker_id`, `working_section_id`, `item_category_id` from the input object
- `issue_type_id` from the input (nullable)
- `issue_type_snapshot` from the input (required)
- `placement_of_issue_snapshot` from the input (optional)
- `intensity` from the input

`batch_create_item_issues(ctx) -> dict` standalone command:
1. Parse request: expects `{"item_id": str, "issues": [...]}`
2. `async with maybe_begin(ctx.session):`
3. Verify item exists (select Item where workspace_id, client_id, is_deleted=False) → NotFound if missing
4. Call `_create_item_issues_in_session(...)`
5. Return `{"item_issue_ids": [...]}`

### Step 8 — New command: `batch_delete_item_issues`

Create `backend/app/beyo_manager/services/commands/items/batch_delete_item_issues.py`:

`batch_delete_item_issues(ctx) -> dict`
1. Parse request: expects `{"issues": [{"item_issue_id": str}]}`; validate list is non-empty
2. Extract `requested_ids = {entry["item_issue_id"] for entry in issues}`
3. `async with maybe_begin(ctx.session):`
4. Fetch `ItemIssue` records where `workspace_id == ctx.workspace_id`, `client_id.in_(requested_ids)`, `is_deleted.is_(False)`
5. If `found_ids != requested_ids`: raise `NotFound(f"Item issue(s) not found: {missing}")`
6. Set `is_deleted=True`, `deleted_at=now`, `deleted_by_id=ctx.user_id` for each
7. Return `{}`

### Step 9 — Update `requests/__init__.py` for items commands

File: `backend/app/beyo_manager/services/commands/items/requests/__init__.py`

Remove classes: `CreateItemIssueRequest`, `DeleteItemIssueRequest`, `DeleteItemIssuesRequest`
Remove parse functions: `parse_create_item_issue_request`, `parse_delete_item_issue_request`, `parse_delete_item_issues_request`

Update `ItemIssueCreateInput` (used by `CreateItemRequest` and `create_task`'s `ItemIssueInput`) to new shape:
```python
class ItemIssueCreateInput(BaseModel):
    issue_type_id: str | None = None
    step_id: str
    worker_id: str
    working_section_id: str
    item_category_id: str
    issue_type_snapshot: str
    placement_of_issue_snapshot: str | None = None
    intensity: int

    @field_validator("intensity")
    @classmethod
    def intensity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("intensity must be >= 1.")
        return v
```

Add new request classes:
```python
class BatchCreateItemIssueInput(BaseModel):
    issue_type_id: str | None = None
    step_id: str
    worker_id: str
    working_section_id: str
    item_category_id: str
    issue_type_snapshot: str
    placement_of_issue_snapshot: str | None = None
    intensity: int

    @field_validator("intensity")
    @classmethod
    def intensity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("intensity must be >= 1.")
        return v

class BatchCreateItemIssuesRequest(BaseModel):
    item_id: str
    issues: list[BatchCreateItemIssueInput]

    @field_validator("issues")
    @classmethod
    def issues_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("issues must contain at least one entry.")
        return v

class BatchDeleteItemIssueInput(BaseModel):
    item_issue_id: str

class BatchDeleteItemIssuesRequest(BaseModel):
    issues: list[BatchDeleteItemIssueInput]

    @field_validator("issues")
    @classmethod
    def issues_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("issues must contain at least one entry.")
        return v
```

Add parse functions for both new request classes following the existing pattern.

### Step 10 — Update `create_item.py`

File: `backend/app/beyo_manager/services/commands/items/create_item.py`

- Remove import of `_create_item_issue_in_session` and `CreateItemIssueRequest`
- Add import of `_create_item_issues_in_session` from `batch_create_item_issues`
- Replace the `if request.item_issues:` block:
  ```python
  if request.item_issues:
      await _create_item_issues_in_session(
          session=ctx.session,
          workspace_id=ctx.workspace_id,
          item_id=item.client_id,
          issues_data=request.item_issues,
          user_id=ctx.user_id,
      )
  ```
- `CreateItemRequest.item_issues` type changes to `list[ItemIssueCreateInput] | None = None` (already uses `ItemIssueCreateInput`, which is now updated in Step 9)

### Step 11 — Update `create_task.py`

File: `backend/app/beyo_manager/services/commands/tasks/create_task.py`

- Remove import of `_create_item_issue_in_session` and `CreateItemIssueRequest`
- Add import of `_create_item_issues_in_session` from `batch_create_item_issues`
- Replace the `if request.item_issues:` block with a single call to `_create_item_issues_in_session`
- Update `tasks/requests/__init__.py` → `ItemIssueInput` class: replace the old fields (`issue_severity_id`, `base_time_seconds`, `time_multiplier`, `issue_name_snapshot`, `severity_name_snapshot`) with the new `BatchCreateItemIssueInput` fields (`step_id`, `worker_id`, `working_section_id`, `item_category_id`, `issue_type_snapshot`, `placement_of_issue_snapshot`, `intensity`, `issue_type_id`)

### Step 12 — Update tasks router `_TaskItemIssueBody`

File: `backend/app/beyo_manager/routers/api_v1/tasks.py`

Update `_TaskItemIssueBody` to match new `ItemIssueCreateInput` shape:
- Remove: `issue_severity_id`, `base_time_seconds`, `time_multiplier`, `issue_name_snapshot`, `severity_name_snapshot`
- Add: `step_id: str`, `worker_id: str`, `working_section_id: str`, `item_category_id: str`, `issue_type_snapshot: str`, `placement_of_issue_snapshot: str | None = None`, `intensity: int`

### Step 13 — New issue-type command services

Create directory `backend/app/beyo_manager/services/commands/issue_types/` with `__init__.py`.

Create `backend/app/beyo_manager/services/commands/issue_types/requests/__init__.py`:

```python
class ItemCategoryIssueTypeLinkInput(BaseModel):
    item_category_id: str
    placement_of_issue: str | None = None

class CreateIssueTypeRequest(BaseModel):
    issue_type_name: str
    linked_working_section_ids: list[str] = []
    linked_item_category_ids: list[ItemCategoryIssueTypeLinkInput] = []

class UpdateIssueTypeRequest(BaseModel):
    issue_type_id: str
    issue_type_name: str | None = None
    linked_working_section_ids: list[str] | None = None
    linked_item_category_ids: list[ItemCategoryIssueTypeLinkInput] | None = None

class DeleteIssueTypeInput(BaseModel):
    issue_type_id: str

class DeleteIssueTypesRequest(BaseModel):
    issues: list[DeleteIssueTypeInput]

    @field_validator("issues")
    @classmethod
    def issues_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("issues must contain at least one entry.")
        return v
```

Add parse functions following the existing pattern.

Create `backend/app/beyo_manager/services/commands/issue_types/create_issue_type.py`:

`create_issue_type(ctx) -> dict`
1. Parse `CreateIssueTypeRequest`
2. `async with maybe_begin(ctx.session):`
3. Check uniqueness: `IssueType` where `workspace_id`, `name == request.issue_type_name`, `is_deleted.is_(False)` → raise `ConflictError` if exists
4. Create `IssueType(workspace_id=ctx.workspace_id, name=request.issue_type_name, source=IssueSourceEnum.MANUAL, created_by_id=ctx.user_id)`
5. `session.add(issue_type); await session.flush()`
6. For each `ws_id` in `linked_working_section_ids`: verify `WorkingSection` exists (workspace-scoped, not deleted), create `WorkingSectionSupportedIssueType`, add to session
7. For each link in `linked_item_category_ids`: verify `ItemCategory` exists (workspace-scoped, not deleted), create `ItemCategoryIssueType`, add to session
8. `await session.flush()`
9. Return `{"client_id": issue_type.client_id}`

Create `backend/app/beyo_manager/services/commands/issue_types/update_issue_type.py`:

`update_issue_type(ctx) -> dict`
1. Parse `UpdateIssueTypeRequest`
2. `async with maybe_begin(ctx.session):`
3. Fetch `IssueType` by `issue_type_id`, `workspace_id`, `is_deleted.is_(False)` → NotFound if missing
4. If `issue_type_name` provided and different from current: check uniqueness (same check as create), update `issue_type.name`
5. If `linked_working_section_ids` is not None:
   - Fetch existing `WorkingSectionSupportedIssueType` rows for this issue_type in workspace
   - Compute `existing_ids`, `incoming_ids` sets
   - Delete records in `existing_ids - incoming_ids` (hard-delete via `await session.delete(row)`)
   - For ids in `incoming_ids - existing_ids`: verify section exists, create new link
6. If `linked_item_category_ids` is not None:
   - Fetch existing `ItemCategoryIssueType` rows for this issue_type in workspace
   - Build `existing_map: dict[item_category_id, ItemCategoryIssueType]`
   - `incoming_map: dict[item_category_id, placement_of_issue]` from request
   - Delete records in `existing_map.keys() - incoming_map.keys()`
   - For keys in `incoming_map.keys() - existing_map.keys()`: verify category exists, create new link
   - For keys in `existing_map.keys() & incoming_map.keys()` where placement changed: update in place
7. `issue_type.updated_at = now; issue_type.updated_by_id = ctx.user_id`
8. Return `{"client_id": issue_type.client_id}`

Create `backend/app/beyo_manager/services/commands/issue_types/delete_issue_types.py`:

`delete_issue_types(ctx) -> dict`
1. Parse `DeleteIssueTypesRequest`
2. `requested_ids = {entry.issue_type_id for entry in request.issues}`
3. `async with maybe_begin(ctx.session):`
4. Fetch `IssueType` records where `workspace_id`, `client_id.in_(requested_ids)`, `is_deleted.is_(False)`
5. Verify all requested IDs were found → NotFound if any missing
6. NULL `issue_type_id` on affected `ItemIssue` rows:
   ```python
   await session.execute(
       update(ItemIssue)
       .where(ItemIssue.workspace_id == ctx.workspace_id, ItemIssue.issue_type_id.in_(requested_ids))
       .values(issue_type_id=None)
   )
   ```
7. Hard-delete `WorkingSectionSupportedIssueType` records for these issue_type_ids:
   ```python
   await session.execute(
       delete(WorkingSectionSupportedIssueType)
       .where(WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
              WorkingSectionSupportedIssueType.issue_type_id.in_(requested_ids))
   )
   ```
8. Hard-delete `ItemCategoryIssueType` records for these issue_type_ids similarly
9. Soft-delete each `IssueType`: `is_deleted=True`, `deleted_at=now`, `deleted_by_id=ctx.user_id`
10. Return `{}`

### Step 14 — New query service: `get_item_issues`

Create `backend/app/beyo_manager/services/queries/items/get_item_issues.py`:

`get_item_issues(ctx) -> dict`
1. `item_id = ctx.incoming_data.get("item_id")`
2. Parse query params: `q`, `working_section_id`, `item_category_id`, `issue_type_id`, `limit` (default 50, max 200), `offset` (default 0)
3. Verify item exists: select `Item` where `workspace_id`, `client_id == item_id`, `is_deleted.is_(False)` → NotFound if missing
4. Build `stmt = select(ItemIssue).where(workspace_id, item_id, is_deleted.is_(False))`
5. Apply optional equality filters: `working_section_id`, `item_category_id`, `issue_type_id`
6. Apply `q` filter via `apply_string_filter(stmt, q, None, {"issue_type_snapshot": ItemIssue.issue_type_snapshot, "placement_of_issue_snapshot": ItemIssue.placement_of_issue_snapshot})`
7. `.order_by(ItemIssue.created_at.asc()).offset(offset).limit(limit + 1)`
8. `has_more = len(rows) > limit; page = rows[:limit]`
9. Return `{"item_issues_pagination": {"items": [serialize_item_issue(i) for i in page], "limit": limit, "offset": offset, "has_more": has_more}}`

Also update the existing `list_item_issues_by_item_id` in `services/queries/items/items.py` to delegate to or be replaced by this new service (the router will call `get_item_issues` for the GET endpoint; the old `list_item_issues_by_item_id` function can be removed if it has no other callers).

### Step 15 — Update items router

File: `backend/app/beyo_manager/routers/api_v1/items.py`

Remove:
- Import of `create_item_issue`, `delete_item_issue`, `delete_item_issues`
- Import of `list_item_issues_by_item_id`
- Classes `_CreateIssueBody`, `_DeleteIssuesBody`
- Route handlers: `route_create_item_issue`, `route_delete_item_issue`, `route_delete_item_issues`, `route_list_item_issues`

Add:
- Import `batch_create_item_issues` from commands
- Import `batch_delete_item_issues` from commands
- Import `get_item_issues` from queries
- New body classes:
  ```python
  class _IssueCreateInput(BaseModel):
      issue_type_id: str | None = None
      step_id: str
      worker_id: str
      working_section_id: str
      item_category_id: str
      issue_type_snapshot: str
      placement_of_issue_snapshot: str | None = None
      intensity: int

  class _BatchCreateIssuesBody(BaseModel):
      issues: list[_IssueCreateInput]

  class _BatchDeleteIssueInput(BaseModel):
      item_issue_id: str

  class _BatchDeleteIssuesBody(BaseModel):
      issues: list[_BatchDeleteIssueInput]
  ```
- New route: `POST /{client_id}/issues` → `batch_create_item_issues`, roles `[ADMIN, MANAGER, WORKER]`
  - `ctx.incoming_data = {"item_id": client_id, "issues": body.issues (as dicts)}`
- New route: `DELETE /{client_id}/issues` → `batch_delete_item_issues`, roles `[ADMIN, MANAGER, WORKER]`
  - `ctx.incoming_data = {"issues": body.issues (as dicts)}`
- Updated route: `GET /{client_id}/issues` → `get_item_issues`, with Query params `q`, `working_section_id`, `item_category_id`, `issue_type_id`, `limit`, `offset`
  - `ctx.incoming_data = {"item_id": client_id}`
  - `ctx.query_params = {"q": q, "working_section_id": working_section_id, "item_category_id": item_category_id, "issue_type_id": issue_type_id, "limit": limit, "offset": offset}`

### Step 16 — Update issue_types router

File: `backend/app/beyo_manager/routers/api_v1/issue_types.py`

Remove:
- Import and use of `get_issue_category_config`, `list_issue_category_configs`
- `category_configs_router` definition and all its route handlers

Add:
- Imports: `create_issue_type`, `update_issue_type`, `delete_issue_types`
- Body classes:
  ```python
  class _ItemCategoryLinkBody(BaseModel):
      item_category_id: str
      placement_of_issue: str | None = None

  class _CreateIssueTypeBody(BaseModel):
      issue_type_name: str
      linked_working_section_ids: list[str] = []
      linked_item_category_ids: list[_ItemCategoryLinkBody] = []

  class _UpdateIssueTypeBody(BaseModel):
      issue_type_name: str | None = None
      linked_working_section_ids: list[str] | None = None
      linked_item_category_ids: list[_ItemCategoryLinkBody] | None = None

  class _DeleteIssueTypeInput(BaseModel):
      issue_type_id: str

  class _DeleteIssueTypesBody(BaseModel):
      issues: list[_DeleteIssueTypeInput]
  ```
- `PUT ""` → `create_issue_type`, roles `[ADMIN, MANAGER]`
- `PATCH "/{client_id}"` → `update_issue_type`, roles `[ADMIN, MANAGER]`; passes `issue_type_id=client_id` in incoming_data
- `DELETE ""` → `delete_issue_types`, roles `[ADMIN, MANAGER]`

### Step 17 — Remove `category_configs_router` from app factory

File: `backend/app/beyo_manager/routers/api_v1/__init__.py` (the app factory file identified at line 65):
- Remove: `app.include_router(issue_types.category_configs_router)`

### Step 18 — Delete obsolete files

Remove these files entirely:
- `backend/app/beyo_manager/models/tables/issue_types/issue_severity.py`
- `backend/app/beyo_manager/models/tables/issue_types/issue_category_config.py`
- `backend/app/beyo_manager/services/commands/items/create_item_issue.py`
- `backend/app/beyo_manager/services/commands/items/delete_item_issue.py`
- `backend/app/beyo_manager/services/commands/items/delete_item_issues.py`
- `backend/app/beyo_manager/services/queries/issue_types/issue_category_configs.py`
- `backend/app/beyo_manager/services/commands/bootstrap/phases/seed_issue_category_configs.py`
- `backend/app/beyo_manager/services/commands/bootstrap/phases/seed_issue_severities.py`
- `backend/app/beyo_manager/services/commands/reset/phases/delete_issue_category_configs.py`
- `backend/app/beyo_manager/services/commands/reset/phases/delete_issue_severities.py`

### Step 19 — Update bootstrap and reset orchestrators

File: `backend/app/beyo_manager/services/commands/bootstrap/bootstrap_app.py`:
- Remove imports and phase calls for `seed_issue_category_configs` and `seed_issue_severities`

File: `backend/app/beyo_manager/services/commands/reset/reset_app.py`:
- Remove imports and phase calls for `delete_issue_category_configs` and `delete_issue_severities`

### Step 20 — Clean up domain/issue_types serializers

File: `backend/app/beyo_manager/domain/issue_types/serializers.py`:
- Remove any `IssueCategoryConfig` and `IssueSeverity` serializer functions and their imports

File: `backend/app/beyo_manager/domain/tasks/serializers.py`:
- Update or remove any `serialize_item_issue` duplicate that referenced `issue_severity_id`, `state`, etc. If it has the same name as the one in `domain/items/serializers.py`, check which callers use which and consolidate to the `items` serializer.

## Risks and mitigations

- Risk: The migration drops columns that may have non-null data in production (e.g., `state`, `base_time_seconds`). Existing item issue rows will lose this data permanently.
  Mitigation: This is intentional per spec. Migration must succeed even if rows exist — all dropped columns are non-essential post-rework. Added columns (`step_id`, `worker_id`, `working_section_id`, `item_category_id`, `issue_type_snapshot`, `intensity`) are nullable=False in the ORM but the migration must add them as nullable or with a server default to avoid constraint failure on existing rows. **Decision: add new columns as nullable in the migration (no server default needed), then after data backfill is confirmed, a follow-up migration can add the NOT NULL constraint. For this plan, the ORM model reflects the intended final state (nullable=False) while the migration uses `nullable=True` for the ADD COLUMN operations on existing tables with data.** If the table is empty in all environments, add them as NOT NULL directly.

- Risk: Callers of `list_item_issues_by_item_id` in `items.py` (query) outside the router may break if the function is removed.
  Mitigation: Grep for all call sites before deleting. The function is also imported in `items.py` (items router) — that import is replaced in Step 15.

- Risk: `domain/tasks/serializers.py` may have its own `serialize_item_issue` that duplicates the items one; updating only one will leave stale references.
  Mitigation: In Step 20, consolidate to the `domain/items/serializers.py` version and update all import sites.

- Risk: The `update_issue_type` diff logic for `linked_item_category_ids` must correctly handle the case where placement_of_issue changes on an existing link. If the plan says "update in place," the `client_id` of the `ItemCategoryIssueType` row is preserved; if delete-and-recreate, a new `client_id` is issued. This may affect frontend caching.
  Mitigation: Clarification #2 above. Default plan: update in place (set `placement_of_issue` on the existing row).

- Risk: After soft-deleting `IssueType`, the `issue_type_id` FK on `ItemIssue` points to a soft-deleted row. Analytics queries must filter `IssueType.is_deleted.is_(False)` or accept that the FK may resolve to a soft-deleted type.
  Mitigation: The `issue_type_snapshot` column preserves the name regardless. Analytics should use `issue_type_snapshot` not join via `issue_type_id`. This is by design.

## Validation plan

- `alembic upgrade head`: migration applies cleanly
- `alembic downgrade -1`: migration rolls back cleanly
- `GET /api/v1/items/{id}/issues?q=scratch&working_section_id=ws1&limit=10`: returns filtered list with `has_more`
- `POST /api/v1/items/{id}/issues` with a list of 2 issues: returns `{"item_issue_ids": ["iti_...", "iti_..."]}`
- `DELETE /api/v1/items/{id}/issues` with `[{"item_issue_id": "iti_..."}]`: soft-deletes the issue; subsequent GET no longer returns it
- `PUT /api/v1/issue-types` with name + links: creates IssueType + WorkingSectionSupportedIssueType + ItemCategoryIssueType rows
- `DELETE /api/v1/issue-types` with one `issue_type_id`: IssueType soft-deleted, link records hard-deleted, ItemIssue.issue_type_id set to NULL
- `python -m pytest` (or equivalent): no import errors from removed modules; existing item and task creation tests pass

## Review log

- `2026-06-03T08:31:19Z` `codex`: Implemented the issue-system rework, generated and validated migration `99accdeba8b9`, ran frontend app typechecks, wrote summary, and archived the plan.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
