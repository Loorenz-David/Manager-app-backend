# INTENTION_item_crud_and_issues_20260517

## Metadata

- Intention ID: `INTENTION_item_crud_and_issues_20260517`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-17T00:00:00Z`
- Last updated at (UTC): `2026-05-17T18:35:00Z`

## Goal

Deliver the complete CRUD and query layer for `Item` and `ItemIssue`, including serializers for `Item`, `ItemIssue`, and the updated `ItemUpholstery` serializer — so that items can be created (with optional embedded issues and an optional item upholstery regardless of category), updated, soft-deleted, listed, and retrieved with their full composition in a single API response.

## Why this matters

Items are the primary production unit of the workshop. Without create/read/update/delete commands at the item level, no production workflow can be initiated. The create command is the entry point that stitches together the three sub-domains: the item itself, any known issues it arrives with, and its upholstery material requirement if applicable. Having a standalone `create_item_issue` atomic command also enables issues to be added to existing items at any later point, which is required for field-discovered defects during production. The serializers defined here establish the canonical shape consumed by all downstream API clients and higher-level task commands.

## Pre-conditions (separate plans that must be implemented first)

| Plan | What it delivers | Why this intention depends on it |
|------|-----------------|----------------------------------|
| `PLAN_maybe_begin_transaction_utility` | `maybe_begin` async context manager at `services/commands/utils/transaction.py`; refactors all 9 existing item lifecycle commands to use it | CMD-1 through CMD-4 and all higher-level commands require propagation-aware transactions; this intention assumes `maybe_begin` and the refactored commands are already in place |

## Success criteria

1. `PUT /api/v1/items` creates an `Item` row, atomically creates any `ItemIssue` rows from the embedded `item_issues` list, and — if `item_upholstery` is present — calls the item upholstery creation helper inline; all three writes share a single transaction.
2. `POST /api/v1/items/{client_id}/issues` creates one `ItemIssue` linked to an existing active item in the workspace.
3. `PATCH /api/v1/items/{client_id}` updates only `Item` columns (no cascading writes to issues or upholstery); correctly re-snapshots `item_category_snapshot` and `item_major_category_snapshot` when `item_category_id` changes.
4. `DELETE /api/v1/items/{client_id}` soft-deletes the item.
5. `GET /api/v1/items` returns a paginated list of active items with `issue_count` per item and an `item_category` object drawn from snapshot columns — no join to `item_categories` required at query time; accepts `q` filter across seven columns spanning three tables using `ILIKE` + `EXISTS` subqueries.
6. `GET /api/v1/items/{client_id}` returns the full item composition: item fields + `item_issues` list + `item_upholstery` object with its requirements list (included whenever an `ItemUpholstery` row exists — not gated on category).
7. `serialize_item_list` returns all item fields including `item_category` object from snapshot columns and `issue_count: int`.
8. `serialize_item_detail` returns all item fields including `item_issues: [...]` and `item_upholstery: {...} | null`.
9. `serialize_item_issue` returns all issue fields including `started_at` and `resolved_at`.
10. `serialize_item_upholstery` is extended with an `item_upholstery_requirements` list parameter; both list and get-by-id callers pass the requirements in — requirements are batch-loaded, never lazy-loaded inside the serializer.
11. A migration adds `item_category_snapshot` and `item_major_category_snapshot` columns to the `items` table and replaces the `article_number` / `sku` partial unique indexes to also filter `is_deleted = false`.
12. All endpoints respect workspace isolation.

## Scope boundary

- **In scope:**
  - `Item` CRUD commands: create, update, soft-delete
  - `Item` queries: list (with `q` cross-table filter, `issue_count`, snapshot-based category) and get-by-id
  - `ItemIssue` create-atomic command (usable standalone or inline during item creation)
  - Serializers: `serialize_item_list`, `serialize_item_detail`, `serialize_item_issue`, and extending `serialize_item_upholstery` with requirements list
  - Router for `/api/v1/items` and nested `/{client_id}/issues` endpoint
  - `item_category_snapshot` + `item_major_category_snapshot` snapshot columns on `items` table + migration
  - Migration fixing `article_number` / `sku` unique indexes to add `AND is_deleted = false`
  - Updating `item.py` model to reflect both migration changes
  - Refactoring `create_item_upholstery` to extract `_create_item_upholstery_in_session` session-level helper (callable inline from CMD-1)
  - Updating both `list_item_upholsteries` and `get_item_upholstery` query callers for the new `serialize_item_upholstery` signature

- **Out of scope:**
  - `maybe_begin` utility and refactoring of all existing lifecycle commands — covered by the pre-condition plan
  - `ItemIssue` state transitions — higher-level task-command responsibility
  - `ItemUpholstery` standalone CRUD (already implemented)
  - `ItemCategory` CRUD (categories are pre-seeded or managed separately)
  - Item state transitions (`ItemStateEnum`) — driven by task-level orchestrators
  - Batch item creation or import flows
  - Backfilling snapshot columns for existing items (snapshot columns are nullable; existing rows remain null)

- **Non-goals:**
  - Replacing or modifying the upholstery lifecycle commands already implemented
  - Any analytics or aggregate computation at this layer

---

## Design decisions (resolved)

### Snapshot columns for item category (`item_category_snapshot`, `item_major_category_snapshot`)

Loading `item_category` for a paginated list of items would require either a JOIN or a batch-fetch on each page load. To keep QUERY-1 a single lightweight query, the `items` table stores category name and major_category as snapshot columns populated at create/update time:

- `item_category_snapshot: String(255) | null` — copy of `ItemCategory.name`
- `item_major_category_snapshot: String(64) | null` — copy of `ItemCategory.major_category` enum value (e.g., `"seat"`, `"wood"`)

**Population rules:**
- **CMD-1**: if `item_category_id` is provided → load `ItemCategory`, copy `name` and `major_category.value` into snapshots; if `item_category_id` is null → both snapshots remain null.
- **CMD-3**: if `item_category_id` is in the update payload and non-null → reload category and re-snapshot; if `item_category_id` is explicitly set to null → clear both snapshot columns to null.
- Snapshots are never written directly by the caller — they are always derived from the category row at write time.

The snapshots are used in both list and detail serializers. QUERY-2 (get-by-id) also reads from the snapshot columns; it does not re-load the `item_categories` table.

---

### `item_upholstery` is not gated on item category

Any item — regardless of `major_category` — may have an `ItemUpholstery`. The serializer always includes the `item_upholstery` key (null if no row exists). CMD-1 allows the `item_upholstery` field for any item. QUERY-2 always loads `ItemUpholstery` if one exists, unconditionally. This removes the SEAT/WOOD split from the API layer entirely; category is an informational field only.

---

### `article_number` and `sku` unique indexes — migration required

The current partial indexes filter only on `IS NOT NULL`. Soft-deleting an item with a given `article_number` and then re-creating one with the same value would hit a DB unique violation. The migration drops both indexes and recreates them with `WHERE article_number IS NOT NULL AND is_deleted = false` (and same for `sku`).

---

### `maybe_begin` transaction pattern

Defined in the pre-condition plan. Every command in this intention uses `async with maybe_begin(ctx.session):` so it participates in a parent transaction if one is open, or opens its own if not. The implementation plan for this intention can import from `services/commands/utils/transaction.py` and assume the utility exists.

---

### `serialize_item_upholstery` breaking change — both list and detail callers

Adding `requirements: list[ItemUpholsteryRequirement]` as a parameter breaks both existing callers:
- `get_item_upholstery` (already listed as modified)
- `list_item_upholsteries` (must be added to modified files)

For `list_item_upholsteries`, requirements are batch-loaded after pagination (one query with `WHERE item_upholstery_id IN (...) AND is_deleted = false`), grouped into a dict by `item_upholstery_id`, and passed into `serialize_item_upholstery` per row.

---

### CMD-3 — null vs omit semantics

Pydantic cannot natively distinguish "field absent from payload" from "field present with value null." CMD-3 must use `model.model_fields_set` to know which fields were explicitly included in the request. Only fields in `model_fields_set` are written; fields absent from the payload are left unchanged. Explicit null in the payload clears the column.

---

## Command catalogue

---

### CMD-1 — Create Item (atomic, with optional issues and optional item upholstery)

**Endpoint:** `PUT /api/v1/items`

**Roles:** `ADMIN`, `MANAGER`

**Inputs:**
- `article_number: str | None` — at least one of `article_number` or `sku` must be non-null
- `sku: str | None` — at least one of `article_number` or `sku` must be non-null
- `item_category_id: str | None` — optional; if provided must exist in workspace and not be soft-deleted
- `quantity: int` — defaults to `1` if missing
- `designer: str | None`
- `height_in_cm: int | None`
- `width_in_cm: int | None`
- `depth_in_cm: int | None`
- `item_value_minor: int | None`
- `item_cost_minor: int | None`
- `item_currency: ItemCurrencyEnum | None`
- `item_position: str | None`
- `external_id: str | None`
- `external_url: str | None`
- `external_source: str | None`
- `external_order_id: str | None`
- `item_issues: list[ItemIssueInput] | None` — optional; each entry:
  - `issue_type_id: str | None`
  - `issue_severity_id: str | None`
  - `base_time_seconds: int | None`
  - `time_multiplier: Decimal | None`
  - `issue_name_snapshot: str | None`
  - `severity_name_snapshot: str | None`
  - All fields nullable; any combination is valid.
- `item_upholstery: ItemUpholsteryInput | None` — optional (allowed for any item, regardless of category):
  - `upholstery_id: str | None` — required when `source = internal`; null when `source = customer`
  - `source: ItemUpholsterySourceEnum` — `internal` | `customer`
  - `name: str | None` — mandatory when `source = customer`; resolved from `Upholstery` registry when `source = internal` and omitted
  - `code: str | None` — mandatory when `source = customer`; resolved from `Upholstery` registry when `source = internal` and omitted
  - `amount_meters: Decimal | None`
  - `time_to_fix_in_seconds: int | None`

**Guards:**
- At least one of `article_number` or `sku` must be non-null and non-empty.
- If `item_category_id` is provided: `ItemCategory` must exist in workspace and not be soft-deleted.
- `quantity` must be >= 1 (coerce missing to 1; reject < 1 with `ValidationError`).
- For `item_upholstery`:
  - `source = internal` → `upholstery_id` must be non-null. The `Upholstery` row must exist in workspace and not be soft-deleted — raise `NotFound("Upholstery not found.")` if it does not.
  - `source = customer` → `name` and `code` are mandatory; `upholstery_id` must be null.

**Behavior:**
1. Validate guards.
2. `async with maybe_begin(ctx.session):`
3. If `item_category_id` provided: load `ItemCategory`; populate `item_category_snapshot = category.name`, `item_major_category_snapshot = category.major_category.value`.
4. Create `Item` row with `state = PENDING`, snapshot columns set, `created_by_id` from JWT.
5. Flush to obtain `item.client_id`.
6. **If `item_issues` non-empty**: for each entry call `_create_item_issue_in_session(session, workspace_id, item.client_id, fields, created_by_id)` — flush only, no begin/commit.
7. **If `item_upholstery` present**:
   - If `source = internal` and `name`/`code` not in payload: load `Upholstery` row by `upholstery_id` in workspace; populate `name` and `code` (note: `code` is nullable on `Upholstery` — may be null even after lookup).
   - Call `_create_item_upholstery_in_session(session, workspace_id, item.client_id, upholstery_payload, created_by_id)` — the refactored session-level helper. This helper does NOT re-verify item existence (the caller just created it).
8. Commit.
9. Return `{ "client_id": item.client_id }`.

---

### CMD-2 — Create Item Issue (standalone atomic command)

**Endpoint:** `POST /api/v1/items/{client_id}/issues`

**Roles:** `ADMIN`, `MANAGER`

**Inputs:**
- `item_id: str` — path parameter; must be an active item in the workspace
- `issue_type_id: str | None`
- `issue_severity_id: str | None`
- `base_time_seconds: int | None`
- `time_multiplier: Decimal | None`
- `issue_name_snapshot: str | None`
- `severity_name_snapshot: str | None`

**Guards:** Item must exist in workspace and not be soft-deleted.

**Session-level helper `_create_item_issue_in_session(session, workspace_id, item_id, fields, created_by_id)`:**
Creates `ItemIssue` with `state = PENDING` and flushes. No begin/commit. Usable inside any open transaction.

**Standalone command behavior:**
1. Verify item exists.
2. `async with maybe_begin(ctx.session):` — opens own transaction.
3. Call `_create_item_issue_in_session(...)`.
4. Commit.
5. Return `{ "client_id": issue.client_id }`.

---

### CMD-3 — Update Item

**Endpoint:** `PATCH /api/v1/items/{client_id}`

**Roles:** `ADMIN`, `MANAGER`

**Inputs (all optional — only fields present in `model_fields_set` are written):**
- `article_number`, `sku`, `item_category_id`, `quantity`, `designer`, `height_in_cm`, `width_in_cm`, `depth_in_cm`, `item_value_minor`, `item_cost_minor`, `item_currency`, `item_position`, `external_id`, `external_url`, `external_source`, `external_order_id`

**Null vs omit:** Uses Pydantic `model_fields_set` to distinguish "field explicitly set to null" (clears the column) from "field not present in payload" (leaves the column unchanged). Only fields in `model_fields_set` are written.

**Guards:**
- Item must exist in workspace and not be soft-deleted.
- If `item_category_id` is in `model_fields_set` and non-null: target `ItemCategory` must exist in workspace and not be soft-deleted.
- If `quantity` is in `model_fields_set`: must be >= 1.

**Behavior:**
1. Load `Item` by `client_id` and `workspace_id`.
2. For each field in `model_fields_set`: apply to the item.
3. **If `item_category_id` is in `model_fields_set`**:
   - If non-null: load `ItemCategory`; update `item_category_snapshot` and `item_major_category_snapshot`.
   - If null: clear both snapshot columns to null.
4. Set `updated_at = now()`, `updated_by_id` from JWT.
5. `async with maybe_begin(ctx.session):` — commit.
6. Return `{ "client_id": item.client_id }`.

**Note:** `state` is never a valid field in this payload.

---

### CMD-4 — Delete Item (soft delete)

**Endpoint:** `DELETE /api/v1/items/{client_id}`

**Roles:** `ADMIN`, `MANAGER`

**Guards:** Item must exist in workspace and not already be soft-deleted.

**Behavior:**
1. Load `Item` by `client_id` and `workspace_id`.
2. Set `is_deleted = true`, `deleted_at = now()`, `deleted_by_id` from JWT.
3. `async with maybe_begin(ctx.session):` — commit.
4. Return `{ "client_id": item.client_id }`.

**Note:** Soft-delete does not cascade to `ItemIssue`, `ItemUpholstery`, or `ItemUpholsteryRequirement` rows.

---

### QUERY-1 — List Items

**Endpoint:** `GET /api/v1/items`

**Roles:** `ADMIN`, `MANAGER`, `WORKER`

**Query params:**
- `q: str | None` — cross-table ILIKE filter
- `limit: int` — default 50, max 200
- `offset: int` — default 0

**`q` filter — columns searched:**

| Column | Table | Method |
|--------|-------|--------|
| `article_number` | `items` | direct `ilike` |
| `sku` | `items` | direct `ilike` |
| `item_position` | `items` | direct `ilike` |
| `designer` | `items` | direct `ilike` |
| `issue_name_snapshot` | `item_issues` | `EXISTS` subquery |
| `name` | `item_upholsteries` | `EXISTS` subquery |
| `code` | `item_upholsteries` | `EXISTS` subquery |

All seven joined by OR with `ILIKE '%q%'`. `EXISTS` subqueries include `is_deleted = false` filters on the joined tables.

**Behavior:**
1. Base query: `Item.workspace_id == workspace_id AND Item.is_deleted == false`.
2. If `q`: apply the seven-column OR filter.
3. Order by `created_at DESC`. Apply `limit + 1` / `offset` pagination.
4. Batch-fetch `issue_count` for the returned item IDs:
   ```sql
   SELECT item_id, count(*) FROM item_issues
   WHERE item_id IN (...) AND is_deleted = false
   GROUP BY item_id
   ```
   Build a `{item_id: count}` dict; missing keys → count 0.
5. Serialize each item with `serialize_item_list(item, issue_count)` — snapshot columns supply the category object, no join needed.
6. Return `{ "items_pagination": { "items": [...], "limit": int, "offset": int, "has_more": bool } }`.

---

### QUERY-2 — Get Item by ID

**Endpoint:** `GET /api/v1/items/{client_id}`

**Roles:** `ADMIN`, `MANAGER`, `WORKER`

**Behavior:**
1. Load `Item` by `client_id` and `workspace_id` — raise `NotFound` if absent or soft-deleted.
2. Load all non-deleted `ItemIssue` rows for the item.
3. Load the non-deleted `ItemUpholstery` row for the item (if any — at most one).
4. If `ItemUpholstery` exists: load all non-deleted `ItemUpholsteryRequirement` rows for it.
5. Serialize with `serialize_item_detail(item, issues, upholstery, requirements)`.
   - `item_upholstery` is null when no `ItemUpholstery` row exists; present otherwise (no category gating).
   - `item_category` object built from snapshot columns on the item row — no separate category query.
6. Return `{ "item": ... }`.

---

## Serializer contract

### serialize_item_list (new)

```
{
  "client_id": str,
  "article_number": str | null,
  "sku": str | null,
  "state": str,
  "item_category": {
    "client_id": str,                  # item.item_category_id
    "name": str,                       # item.item_category_snapshot
    "major_category": str              # item.item_major_category_snapshot
  } | null,                            # null when item_category_id is null
  "quantity": int,
  "designer": str | null,
  "height_in_cm": int | null,
  "width_in_cm": int | null,
  "depth_in_cm": int | null,
  "item_value_minor": int | null,
  "item_cost_minor": int | null,
  "item_currency": str | null,
  "item_position": str | null,
  "external_id": str | null,
  "external_url": str | null,
  "external_source": str | null,
  "external_order_id": str | null,
  "created_at": str,
  "created_by_id": str | null,
  "updated_at": str | null,
  "issue_count": int
}
```

### serialize_item_detail (new)

Same as list, replacing `issue_count` with full nested keys:

```
{
  ...all list fields (without issue_count)...,
  "item_issues": [...],             # list of serialize_item_issue; [] if none
  "item_upholstery": {...} | null   # serialize_item_upholstery with requirements; null if no row
}
```

### serialize_item_issue (new)

```
{
  "client_id": str,
  "item_id": str,
  "issue_type_id": str | null,
  "issue_severity_id": str | null,
  "state": str,
  "base_time_seconds": int | null,
  "time_multiplier": str | null,        # Decimal as string
  "issue_name_snapshot": str | null,
  "severity_name_snapshot": str | null,
  "created_at": str,
  "created_by_id": str | null,
  "started_at": str | null,
  "resolved_at": str | null,
  "updated_at": str | null,
  "updated_by_id": str | null
}
```

### serialize_item_upholstery (extend existing at `domain/items/serializers.py`)

Updated signature:

```python
def serialize_item_upholstery(
    iup: ItemUpholstery,
    requirements: list[ItemUpholsteryRequirement],
) -> dict:
```

Adds to output:

```
{
  ...existing fields...,
  "item_upholstery_requirements": [...]   # list of serialize_upholstery_requirement; [] if none
}
```

---

## Migration

One migration (or two sequential migrations, ordered below):

**Part 1 — Fix `article_number` / `sku` unique indexes on `items`:**
```sql
-- Drop old partial indexes
DROP INDEX IF EXISTS uix_items_workspace_article_number;
DROP INDEX IF EXISTS uix_items_workspace_sku;

-- Recreate with is_deleted = false guard
CREATE UNIQUE INDEX uix_items_workspace_article_number
    ON items (workspace_id, article_number)
    WHERE article_number IS NOT NULL AND is_deleted = false;

CREATE UNIQUE INDEX uix_items_workspace_sku
    ON items (workspace_id, sku)
    WHERE sku IS NOT NULL AND is_deleted = false;
```

**Part 2 — Add snapshot columns to `items`:**
```sql
ALTER TABLE items
    ADD COLUMN item_category_snapshot VARCHAR(255),
    ADD COLUMN item_major_category_snapshot VARCHAR(64);
```

Existing rows remain null in both columns (no backfill required — snapshots are populated on the next create or update of each item).

---

## Files to create / modify

### New files

| File | Purpose |
|------|---------|
| `backend/app/beyo_manager/services/commands/items/create_item.py` | CMD-1 |
| `backend/app/beyo_manager/services/commands/items/create_item_issue.py` | CMD-2 + `_create_item_issue_in_session` helper |
| `backend/app/beyo_manager/services/commands/items/update_item.py` | CMD-3 |
| `backend/app/beyo_manager/services/commands/items/delete_item.py` | CMD-4 |
| `backend/app/beyo_manager/services/queries/items/items.py` | QUERY-1 + QUERY-2 |
| `backend/app/beyo_manager/routers/api_v1/items.py` | Router: items + issues endpoints |
| `backend/app/migrations/versions/<rev>_item_snapshot_columns_and_fix_unique_indexes.py` | Migration: snapshot columns + fixed partial indexes |

### Modified files

| File | Change |
|------|--------|
| `backend/app/beyo_manager/models/tables/items/item.py` | Add `item_category_snapshot` and `item_major_category_snapshot` columns; update `__table_args__` unique index conditions to include `AND is_deleted = false` |
| `backend/app/beyo_manager/domain/items/serializers.py` | Add `serialize_item_list`, `serialize_item_detail`, `serialize_item_issue`; update `serialize_item_upholstery` to accept `requirements` list parameter |
| `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py` | Replace `ctx.session.begin()` with `maybe_begin`; extract `_create_item_upholstery_in_session` helper (skips item existence check — caller is responsible) |
| `backend/app/beyo_manager/services/queries/items/item_upholsteries.py` | Update `get_item_upholstery` and `list_item_upholsteries` to batch-load requirements and pass them into the updated `serialize_item_upholstery` call |
| `backend/app/beyo_manager/services/commands/items/requests/__init__.py` | Add `CreateItemRequest`, `CreateItemIssueRequest`, `UpdateItemRequest` |
| `backend/app/beyo_manager/routers/api_v1/__init__.py` | Import and register items router |

---

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_maybe_begin_transaction_utility` | `backend/docs/architecture/archives/implementation/PLAN_maybe_begin_transaction_utility_20260517.md` | `archived` | `maybe_begin` utility + refactor of all 9 existing item lifecycle commands |
| `PLAN_item_crud_and_issues_20260517` | `backend/docs/architecture/archives/implementation/PLAN_item_crud_and_issues_20260517.md` | `archived` | Migration, model update, CMD-1 through CMD-4, QUERY-1 through QUERY-2, all serializers, and router |

## Progress notes

- `2026-05-17`: Intention created from rough notes in `atomic_cmd_item.md` + model/enum analysis.
- `2026-05-17`: All open questions resolved. Transaction propagation pattern (`maybe_begin`) introduced and separated into its own pre-condition plan. Snapshot columns (`item_category_snapshot`, `item_major_category_snapshot`) adopted to avoid N+1 category joins. `item_upholstery` de-gated from category — included for all items when present. `started_at`/`resolved_at` added to `serialize_item_issue`. `list_item_upholsteries` added to modified files with batch requirements loading. Unique index migration identified. `model_fields_set` pattern documented for CMD-3. `NotFound` specified for missing upholstery registry row in CMD-1.
- `2026-05-17`: `PLAN_maybe_begin_transaction_utility_20260517` implemented and archived. `maybe_begin` in place across all 9 item commands; `06_commands_local.md` contract created; `backend_contract_goal_mapping_guide.md` updated. `PLAN_item_crud_and_issues_20260517` created and under construction.
- `2026-05-17`: `PLAN_item_crud_and_issues_20260517` implemented, summarized, and archived. Migration `3a5532f8f0a7` applied; item CRUD + issue command/query/router stack delivered; serializer call sites updated for requirements payload. Endpoint-level verification for all acceptance criteria remains the final gate before setting this intention to `achieved`.

## Open questions

None — all design questions resolved before implementation.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: API-level tests confirm all 12 success criteria, especially endpoint behavior for CMD-1..CMD-4 and QUERY-1..QUERY-2
