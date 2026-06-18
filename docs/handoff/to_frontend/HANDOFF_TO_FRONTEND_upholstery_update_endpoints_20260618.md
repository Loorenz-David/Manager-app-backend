# HANDOFF_TO_FRONTEND_upholstery_update_endpoints_20260618

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_update_endpoints_20260618`
- Created at (UTC): `2026-06-18T16:20:05Z`
- Owner agent: `backend`
- Source plan: n/a — direct endpoint documentation request
- Source summary: n/a

## Backend delivery context

- What backend implemented:
  - `PATCH /api/v1/upholsteries/{client_id}` updates mutable upholstery fields.
  - `PATCH /api/v1/upholstery-inventories/{client_id}` updates mutable inventory planning fields.
- API or contract changes:
  - `PATCH /api/v1/upholsteries/{client_id}` now returns `{}` on success instead of an `upholstery` payload.
  - This document reflects the current request and response contracts the frontend should target.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Wire upholstery edit forms to `PATCH /api/v1/upholsteries/{client_id}` using only the supported mutable fields listed below.
2. Wire inventory planning edit forms to `PATCH /api/v1/upholstery-inventories/{client_id}` using only the supported mutable fields listed below.
3. Treat omitted fields and explicit `null` the same on both endpoints: they mean “leave existing value unchanged”, not “clear the field”.
4. Do not rely on either PATCH endpoint returning the updated record; both return an empty object on success, so the frontend should refetch or update local state separately.

## Interface details

- Endpoint(s):
  - `PATCH /api/v1/upholsteries/{client_id}`
  - `PATCH /api/v1/upholstery-inventories/{client_id}`

### 1. Update Upholstery

- Auth:
  - JWT required
  - Roles: `admin`, `manager`

- Path params:
  - `client_id: string`
  - Prefixed ID, e.g. `uph_...`

- Request shape:

```json
{
  "name": "Velvet Ember",
  "code": "VEL-EMBER",
  "image_url": "https://cdn.example.com/upholstery.jpg",
  "favorite": true
}
```

- Request field contract:
  - `name: string | null`
  - `code: string | null`
  - `image_url: string | null`
  - `favorite: boolean | null`

- Request behavior:
  - Any field may be omitted.
  - `name` is trimmed; blank strings are rejected.
  - `name: null`, `code: null`, `image_url: null`, and `favorite: null` do not clear the stored value; they are treated as no-op because the command only applies non-`None` fields.
  - `name` must be unique within the workspace among non-deleted upholsteries.
  - `code` must be unique within the workspace among non-deleted upholsteries when provided.

- Response shape:

```json
{}
```

- Response field notes:
  - Success returns an empty object only.
  - Frontend must refetch the upholstery detail/list or patch local state itself if the updated values should be shown immediately.

- Error cases:
  - `401`: missing or invalid JWT
  - `403`: authenticated user lacks `admin` or `manager` role
  - `404`: upholstery not found in the current workspace
  - Domain validation error: blank `name`
  - Domain conflict error: duplicate `name` or duplicate `code` in the workspace

### 2. Update Upholstery Inventory

- Auth:
  - JWT required
  - Roles: `admin`, `manager`

- Path params:
  - `client_id: string`
  - Prefixed ID, e.g. `uin_...`

- Request shape:

```json
{
  "low_stock_threshold_meters": "2.500",
  "minimum_to_have": 3,
  "maximum_to_have": 10,
  "projected_inventory_value_minor": 125000,
  "currency": "swedish_krona",
  "planning_position": "A-12"
}
```

- Request field contract:
  - `low_stock_threshold_meters: string | number | null`
  - `minimum_to_have: integer | null`
  - `maximum_to_have: integer | null`
  - `projected_inventory_value_minor: integer | null`
  - `currency: "swedish_krona" | "danish_krona" | "euro" | null`
  - `planning_position: string | null`

- Request behavior:
  - Any field may be omitted.
  - `low_stock_threshold_meters` must be greater than `0` when provided.
  - As implemented today, `minimum_to_have`, `maximum_to_have`, and `projected_inventory_value_minor` are optional integer fields at the router layer; frontend should keep them non-negative to stay aligned with create-time and model constraints.
  - Explicit `null` does not clear a stored value; it is treated as no-op because the command only applies non-`None` fields.
  - This endpoint does not update actual stock counters such as `current_stored_amount_meters`, `current_amount_in_need_meters`, or `current_amount_ordered_meters`.

- Response shape:

```json
{}
```

- Response field notes:
  - Success returns an empty object only.
  - Frontend must refetch the inventory detail or patch local state itself if the updated values should be shown immediately.

- Error cases:
  - `401`: missing or invalid JWT
  - `403`: authenticated user lacks `admin` or `manager` role
  - `404`: inventory not found in the current workspace
  - Domain validation error: invalid threshold value (for example `<= 0`)

## Validation notes

- Backend validation run:
  - Contract update only for `PATCH /api/v1/upholsteries/{client_id}` response body.
  - No focused automated test exists for this route in the current backend test suite.

- Suggested frontend validation:
  - Do not send blank-string `name`; trim client-side before submit.
  - Treat decimal fields as decimal-safe strings where precision matters.
  - Do not assume `null` clears fields on these PATCH endpoints; use a dedicated clear behavior only after the backend supports it explicitly.
  - For `PATCH /api/v1/upholstery-inventories/{client_id}`, plan for empty `{}` success responses and refresh view state after save.

## Trace links

- Parent plan:
  - n/a
- Parent summary:
  - n/a
- Related debug plan (optional):
  - n/a
