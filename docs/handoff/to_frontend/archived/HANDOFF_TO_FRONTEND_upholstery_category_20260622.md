# HANDOFF_TO_FRONTEND_upholstery_category_20260622

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_category_20260622`
- Created at (UTC): `2026-06-22T09:14:43Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_category_20260622.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_category_20260622.md`

## Backend delivery context

- What backend implemented:
  - A new workspace-scoped `UpholsteryCategory` entity with create, list, get, update, soft-delete, and favorite-toggle support.
  - Upholstery create/update support for linking a category by `upholstery_category_id`.
  - Upholstery list filtering by comma-separated `upholstery_category_ids`.
  - Nested `upholstery_category` payloads on upholstery create/get/list/favorite/list-order responses when a linked category is active.
- API or contract changes:
  - New endpoint family under `/api/v1/upholstery-categories`.
  - `PUT /api/v1/upholsteries` and `PATCH /api/v1/upholsteries/{client_id}` accept `upholstery_category_id`.
  - `GET /api/v1/upholsteries` accepts `upholstery_category_ids`.
  - Upholstery payloads now include `upholstery_category`.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Add category CRUD UI against `/api/v1/upholstery-categories`.
2. Send `upholstery_category_id` when creating or updating an upholstery that belongs to a category.
3. Use `upholstery_category_ids` as a CSV query param when filtering upholsteries by folder/category.
4. Treat `upholstery_category: null` as uncategorized, including the case where the linked category was soft-deleted.

## Interface details

- Common success envelope: `{ ok: true, data: <payload>, warnings: [] }`
- Common error envelope: `{ ok: false, error: <message> }`

### 1) PUT `/api/v1/upholstery-categories`

- Auth roles: `admin`, `manager`
- Request body:
  - `client_id`: optional string. If supplied, must use the `upc` prefix.
  - `name`: required string, trimmed, non-blank.
  - `image_url`: optional string or `null`.
  - `favorite`: optional boolean, default `false`.
- Response payload:
  - `{ upholstery_category: <category> }` — same full shape as section 2/3, including `upholstery_count: 0` (always zero on creation)
- Error cases:
  - `409` when the provided `client_id` already exists or the workspace already has the same category `name`.
  - `422` for blank `name` or malformed payload.

### 2) GET `/api/v1/upholstery-categories`

- Auth roles: `admin`, `manager`, `worker`
- Query params:
  - `limit`: optional integer, default `50`, max `200`
  - `offset`: optional integer, default `0`
  - `q`: optional string; matches `name ILIKE %q%`
  - `favorite`: optional boolean
- Response payload:
  - `upholstery_categories`: array of category objects
  - `upholstery_categories_pagination`: `{ has_more, limit, offset }`
- Category object shape:
```json
{
  "client_id": "upc_01...",
  "workspace_id": "wsp_01...",
  "name": "Velvet",
  "image_url": "https://cdn.example.com/velvet.jpg",
  "favorite": false,
  "created_at": "2026-06-22T10:00:00+00:00",
  "created_by_id": "usr_01...",
  "updated_at": null,
  "updated_by_id": null,
  "is_deleted": false,
  "upholstery_count": 3
}
```

### 3) GET `/api/v1/upholstery-categories/{client_id}`

- Auth roles: `admin`, `manager`, `worker`
- Response payload:
  - `{ upholstery_category: <category> }`
- Notes:
  - Same shape as above, including `upholstery_count`.
  - Returns `404` if the category does not exist in the workspace or was soft-deleted.

### 4) PATCH `/api/v1/upholstery-categories/{client_id}`

- Auth roles: `admin`, `manager`
- Request body:
  - `name`: optional string, non-blank when provided
  - `image_url`: optional string; send explicit `null` to clear an existing image URL
- Request behavior:
  - Omitted fields are no-ops (existing values preserved).
  - `name: null` is a no-op (name cannot be cleared).
  - `image_url: null` clears the stored value.
- Response payload:
  - `{}`
- Error cases:
  - `404` if not found
  - `409` on duplicate `name`

### 5) DELETE `/api/v1/upholstery-categories/{client_id}`

- Auth roles: `admin`, `manager`
- Behavior:
  - Soft-deletes the category.
- Response payload:
  - `{}`

### 6) PATCH `/api/v1/upholstery-categories/{client_id}/favorite`

- Auth roles: `admin`, `manager`
- Request body:
  - `favorite`: required boolean
- Response payload:
  - `{ upholstery_category: <category> }` — same full shape as section 3, including `upholstery_count`

### 7) PUT `/api/v1/upholsteries`

- New request field:
  - `upholstery_category_id`: optional string or `null`
- New response field inside `upholstery`:
```json
"upholstery_category": {
  "id": "upc_01...",
  "name": "Velvet",
  "image_url": "https://cdn.example.com/velvet.jpg"
}
```
- Validation:
  - If `upholstery_category_id` is provided, it must reference an active category in the same workspace or the backend returns `404`.

### 8) PATCH `/api/v1/upholsteries/{client_id}`

- New request field:
  - `upholstery_category_id`: optional string
- Behavior:
  - Omitted field: no category change.
  - Explicit `null`: clears the category link.
  - Non-null value: validates the category exists in the same workspace.

### 9) GET `/api/v1/upholsteries`

- New query param:
  - `upholstery_category_ids`: optional CSV string, for example `upc_01a,upc_01b`
- New response field on each upholstery item:
  - `upholstery_category` object or `null`

### 10) GET `/api/v1/upholsteries/{client_id}`

- New response field:
  - `upholstery_category` object or `null`

## Validation notes

- Backend validation run:
  - Import checks for the new router, query module, and serializer passed.
  - Alembic migration upgrade passed.
  - Alembic schema drift check passed after aligning existing query-index metadata.
- Suggested frontend validation:
  - Verify category create/list/update/delete/favorite flows against real JWT auth.
  - Verify upholstery forms preserve the current category when the field is omitted on partial update.
  - Verify an upholstery linked to a deleted category renders as uncategorized.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_category_20260622.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_category_20260622.md`
- Related debug plan (optional): —
