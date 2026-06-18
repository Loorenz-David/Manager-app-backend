# HANDOFF_TO_FRONTEND_upholstery_inventories_list_get_20260618

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_inventories_list_get_20260618`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Owner agent: `backend`
- Source plan: n/a — incremental serializer update
- Source summary: n/a

## Backend delivery context

- What backend implemented:
  - `GET /api/v1/upholstery-inventories` — list with offset pagination (partial serialization)
  - `GET /api/v1/upholstery-inventories/{client_id}` — single full-detail fetch
  - `PATCH /api/v1/upholstery-inventories/{client_id}/current-stored-amount` — absolute stored-stock correction endpoint
  - `DELETE /api/v1/upholstery-inventories/{client_id}` — soft delete; returns empty object on success
  - Both endpoints now include `image_url` sourced from the parent `Upholstery` record via a single JOIN (no N+1)
  - List endpoint uses a lightweight partial shape; detail endpoint returns the full inventory shape
- API or contract changes:
  - `image_url` field added to both response shapes
  - `upholstery_name` and `upholstery_code` added to both response shapes
  - `upholstery_id` added to list item partial shape
  - List items now expose `current_amount_ordered_meters` (decimal string) from inventory state
  - List items now use a partial shape (subset of fields) — not the full inventory object
  - New absolute stock-adjustment endpoint updates only `current_stored_amount_meters` and may cause related requirement state changes server-side
- Feature flags/toggles: none

## Frontend action required

1. Update the list schema to use the partial `UpholsteryInventoryPartial` shape defined below
2. Update the detail schema to use the full `UpholsteryInventory` shape defined below
3. Both shapes now include `image_url` — integrate into UI where applicable
4. Both shapes now include `upholstery_name` and `upholstery_code`; list shape also includes `upholstery_id`
5. List items now include `current_amount_ordered_meters` (`string | null`) from inventory state (replaces previous `total_orders`)
6. Implement delete action using `DELETE /{client_id}` — expect an empty `{}` response on success; remove the item from local state on `200 OK`
7. Use `PATCH /{client_id}/current-stored-amount` when the UI needs to set stock to an absolute value, including decreases
8. Use `in_stock=true|false` for stock filtering on the inventory list route
9. After a successful stock-set call, refetch the affected inventory detail or refresh the list row because requirement availability may have changed elsewhere in the workspace

## Interface details

---

### 1. List Upholstery Inventories

**Endpoint:** `GET /api/v1/upholstery-inventories`

**Auth:** JWT — roles: `admin`, `manager`, `worker`

**Query params:**

| Param    | Type    | Default | Constraints      |
|----------|---------|---------|------------------|
| `limit`  | integer | `50`    | min `1`, max `200` |
| `offset` | integer | `0`     | min `0`          |
| `q`      | string  | n/a     | optional text search across upholstery `name` and `code` |
| `favorite` | boolean | n/a | optional; `true` returns only upholsteries marked as favorite |
| `in_stock` | boolean | n/a | optional; `true` = only `available` and `low_stock`, `false` = only `out_of_stock` |

**Response shape** (`200 OK`):

```json
{
  "upholstery_inventories_pagination": {
    "items": [ UpholsteryInventoryPartial ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

**`UpholsteryInventoryPartial` schema:**

| Field                           | Type              | Nullable | Notes                                                      |
|---------------------------------|-------------------|----------|------------------------------------------------------------|
| `client_id`                     | `string`          | no       | Prefixed ID: `inv_...`                                     |
| `workspace_id`                  | `string`          | no       | Prefixed ID: `ws_...`                                      |
| `upholstery_id`                 | `string`          | no       | Prefixed ID: `uph_...`                                     |
| `upholstery_name`               | `string`          | yes      | Name from parent `Upholstery`; `null` if missing relation  |
| `upholstery_code`               | `string`          | yes      | Code from parent `Upholstery`; `null` if missing relation  |
| `image_url`                     | `string`          | yes      | From parent `Upholstery` record; `null` if not set         |
| `inventory_condition`           | `string` (enum)   | no       | `"available"` \| `"low_stock"` \| `"out_of_stock"`        |
| `current_stored_amount_meters`  | `string` (decimal)| yes      | Serialized as string to preserve precision; e.g. `"12.500"` |
| `current_amount_ordered_meters` | `string` (decimal)| yes      | Mirrors inventory aggregate state for active ordered amount |
| `updated_at`                    | `string` (ISO 8601)| yes     | `null` if never updated                                    |

---

### 2. Get Upholstery Inventory

**Endpoint:** `GET /api/v1/upholstery-inventories/{client_id}`

**Auth:** JWT — roles: `admin`, `manager`, `worker`

**Path params:**

| Param       | Type   | Notes                      |
|-------------|--------|----------------------------|
| `client_id` | string | Prefixed ID: `inv_...`     |

**Response shape** (`200 OK`):

```json
{
  "inventory": UpholsteryInventory
}
```

**`UpholsteryInventory` schema:**

| Field                                    | Type               | Nullable | Notes                                                       |
|------------------------------------------|--------------------|----------|-------------------------------------------------------------|
| `client_id`                              | `string`           | no       | Prefixed ID: `inv_...`                                      |
| `workspace_id`                           | `string`           | no       | Prefixed ID: `ws_...`                                       |
| `upholstery_id`                          | `string`           | no       | Prefixed ID: `uph_...`                                      |
| `upholstery_name`                        | `string`           | yes      | Name from parent `Upholstery`; `null` if missing relation   |
| `upholstery_code`                        | `string`           | yes      | Code from parent `Upholstery`; `null` if missing relation   |
| `image_url`                              | `string`           | yes      | From parent `Upholstery` record; `null` if not set          |
| `inventory_condition`                    | `string` (enum)    | no       | `"available"` \| `"low_stock"` \| `"out_of_stock"`         |
| `current_stored_amount_meters`           | `string` (decimal) | yes      | e.g. `"12.500"`                                             |
| `current_amount_in_use_meters`           | `string` (decimal) | yes      |                                                             |
| `current_amount_in_need_meters`          | `string` (decimal) | yes      |                                                             |
| `current_amount_ordered_meters`          | `string` (decimal) | yes      |                                                             |
| `total_upholstery_used_meters`           | `string` (decimal) | yes      |                                                             |
| `total_upholstery_used_inventory_meters` | `string` (decimal) | yes      |                                                             |
| `total_upholstery_used_surplus_meters`   | `string` (decimal) | yes      |                                                             |
| `total_upholstery_surplus_meters`        | `string` (decimal) | yes      |                                                             |
| `low_stock_threshold_meters`             | `string` (decimal) | yes      |                                                             |
| `minimum_to_have`                        | `integer`          | yes      |                                                             |
| `maximum_to_have`                        | `integer`          | yes      |                                                             |
| `projected_inventory_value_minor`        | `integer`          | yes      | Value in minor currency units (e.g. cents)                  |
| `currency`                               | `string` (enum)    | yes      | `"swedish_krona"` \| `"danish_krona"` \| `"euro"`; `null` if not set |
| `planning_position`                      | `string`           | yes      |                                                             |
| `latest_projection_history_id`           | `string`           | yes      |                                                             |
| `created_at`                             | `string` (ISO 8601)| no       |                                                             |
| `created_by_id`                          | `string`           | yes      | Prefixed ID: `usr_...`                                      |
| `updated_at`                             | `string` (ISO 8601)| yes      | `null` if never updated                                     |
| `updated_by_id`                          | `string`           | yes      | Prefixed ID: `usr_...`                                      |
| `is_deleted`                             | `boolean`          | no       | Always `false` for live records                             |

---

### 3. Delete Upholstery Inventory

**Endpoint:** `DELETE /api/v1/upholstery-inventories/{client_id}`

**Auth:** JWT — roles: `admin`, `manager`

**Path params:**

| Param       | Type   | Notes                  |
|-------------|--------|------------------------|
| `client_id` | string | Prefixed ID: `inv_...` |

**Response shape** (`200 OK`):

```json
{}
```

Empty object — no body payload on success. The record is soft-deleted server-side (`is_deleted = true`); it will no longer appear in list or get endpoints.

---

### 4. Set Current Stored Amount

**Endpoint:** `PATCH /api/v1/upholstery-inventories/{client_id}/current-stored-amount`

**Auth:** JWT — roles: `admin`, `manager`

**Path params:**

| Param       | Type   | Notes                  |
|-------------|--------|------------------------|
| `client_id` | string | Prefixed ID: `uin_...` |

**Request body:**

```json
{
  "current_stored_amount_meters": "12.500"
}
```

**Request schema:**

| Field                           | Type               | Nullable | Notes                                                                |
|---------------------------------|--------------------|----------|----------------------------------------------------------------------|
| `current_stored_amount_meters`  | `string \| number` | no       | Absolute stored amount in meters; backend rounds to 3 decimals; must be `>= 0` |

Frontend note:
- Treat this as a full replacement, not a delta. Sending `"2.000"` means "set stored stock to exactly 2.000 meters".
- Prefer sending a decimal-safe string from the client to avoid float drift.

**Response shape** (`200 OK`):

```json
{}
```

Empty object on success.

**Behavior contract:**

- This endpoint updates only `current_stored_amount_meters`.
- It does not modify planning fields such as `minimum_to_have`, `maximum_to_have`, `projected_inventory_value_minor`, `currency`, or `planning_position`.
- Backend recomputes `inventory_condition` immediately after the stored amount change.
- If stock increases, backend may promote eligible upholstery requirements from `ordered` or `needs_ordering` to `available`.
- If stock decreases, backend may demote lower-priority `available` requirements back to `needs_ordering`.
- Those requirement changes are backend-driven side effects; the endpoint itself still returns `{}`.
- `current_amount_in_need_meters` is not decremented by these availability recalculations, so frontend should continue to treat it as an aggregate demand field rather than "remaining unresolved demand".

---

## Error cases

| Status | Condition                                                    |
|--------|--------------------------------------------------------------|
| `401`  | Missing or invalid JWT                                       |
| `403`  | Authenticated user lacks required role                       |
| `404`  | `client_id` not found (detail and delete endpoints)          |
| `422` / domain validation error payload | Invalid body, including negative `current_stored_amount_meters` |

## Validation notes

- Backend validation run: manual — server running locally, endpoints responding `200 OK`
- Suggested frontend validation:
  - All decimal fields are strings — parse with a decimal/bigdecimal library, not `parseFloat`
  - `inventory_condition` is a closed enum — guard unknown values defensively
  - `image_url` may be `null` even when the upholstery exists (not all upholsteries have images)
  - `upholstery_name` and `upholstery_code` may be `null` when parent upholstery relation is missing
  - `current_amount_ordered_meters` is a decimal string from inventory state; do not parse with float if precision matters
  - `current_stored_amount_meters` on the PATCH endpoint is absolute, not additive
  - Successful PATCH returns `{}` only; refresh local inventory data after success instead of expecting an updated payload
  - `q` searches upholstery `name` and `code` only for now; more fields may be added later without changing the parameter name

## Trace links

- Parent plan: n/a
- Parent summary: n/a
- Related debug plan: n/a
