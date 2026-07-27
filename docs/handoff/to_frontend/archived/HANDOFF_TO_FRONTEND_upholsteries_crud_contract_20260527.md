# HANDOFF_TO_FRONTEND_upholsteries_crud_contract_20260527

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholsteries_crud_contract_20260527`
- Created at (UTC): `2026-05-27T06:42:43Z`
- Owner agent: `copilot`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholsteries_crud_20260527.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholsteries_crud_20260527.md`

## Backend delivery context

- What backend implemented:
  - Dedicated upholstery CRUD router at `/api/v1/upholsteries`.
  - Atomic create flow: creates both upholstery and linked inventory.
  - Favorite toggles (single + batch), list ordering update, soft delete.
  - List query filters: `q`, `in_stock`, `favorite`.
- API or contract changes:
  - Upholstery list/get routes were moved out of `item_upholsteries` into a dedicated router, keeping the same URL prefix.
- Feature flags/toggles:
  - None.

## Global response envelope

- Success:

```json
{
  "ok": true,
  "warnings": [],
  "data": {}
}
```

- Error:

```json
{
  "ok": false,
  "error": "..."
}
```

## Auth and roles

- Read endpoints (`GET /api/v1/upholsteries`, `GET /api/v1/upholsteries/{client_id}`): `ADMIN`, `MANAGER`, `WORKER`
- Write endpoints (PUT/PATCH/DELETE): `ADMIN`, `MANAGER`

## Shared upholstery object shape

Returned in list/get/create/update/favorite/list-order responses:

```json
{
  "client_id": "uph_01ABC...",
  "name": "Linen A",
  "code": "LIN-A",
  "image_url": "https://...",
  "favorite": false,
  "list_order": 3,
  "current_stored_amount_meters": "12.500",
  "inventory_condition": "available"
}
```

Notes:
- `current_stored_amount_meters` is computed as:
  - `max(current_stored_amount_meters - current_amount_in_need_meters, 0)`
  - serialized as string, or `null` if no inventory/current stock data.
- `inventory_condition` values come from backend enum:
  - `available`, `low_stock`, `out_of_stock`

---

## 1) Create upholstery

### Endpoint

- `PUT /api/v1/upholsteries`

### Body

```json
{
  "client_id": "uph_01ABC...",
  "name": "Linen A",
  "code": "LIN-A",
  "image_url": "https://...",
  "favorite": false,
  "current_stored_amount_meters": 12.5,
  "low_stock_threshold_meters": 5,
  "minimum_to_have": 3,
  "maximum_to_have": 20,
  "projected_inventory_value_minor": 12000,
  "currency": "euro",
  "planning_position": "A-12"
}
```

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01ABC...",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://...",
      "favorite": false,
      "list_order": null,
      "current_stored_amount_meters": "12.500",
      "inventory_condition": "available"
    }
  }
}
```

### Data schema (inside `data`)

```json
{
  "upholsteries": [
    {
      "client_id": "string",
      "name": "string",
      "code": "string | null",
      "image_url": "string | null",
      "favorite": "boolean",
      "list_order": "number | null",
      "current_stored_amount_meters": "string | null",
      "inventory_condition": "available | low_stock | out_of_stock | null"
    }
  ],
  "upholsteries_pagination": {
    "has_more": "boolean",
    "limit": "number",
    "offset": "number"
  }
}
```

### Behavior notes

- Creates upholstery and inventory in one transaction.
- If `current_stored_amount_meters` is omitted, backend uses `0`.
- Initial `inventory_condition` is derived as:
  - `out_of_stock` if initial stock `<= 0`
  - `low_stock` if initial stock `> 0` and `<= low_stock_threshold_meters`
  - `available` otherwise

### Validation / error cases

- `name` blank -> validation error.
- `low_stock_threshold_meters <= 0` -> validation error.
- `current_stored_amount_meters < 0` -> validation error.
- `minimum_to_have`, `maximum_to_have`, `projected_inventory_value_minor` < 0 -> validation error.
- duplicate `client_id` / duplicate `name` / duplicate `code` in workspace -> conflict error.

---

## 2) List upholsteries

### Endpoint

- `GET /api/v1/upholsteries`

### Query params

- `limit: number` (default `50`, max `200`)
- `offset: number` (default `0`)
- `q: string | null` (ILIKE search on `name` or `code`)
- `in_stock: boolean | null`
- `favorite: boolean | null`

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholsteries": [
      {
        "client_id": "uph_01ABC...",
        "name": "Linen A",
        "code": "LIN-A",
        "image_url": "https://...",
        "favorite": true,
        "list_order": 1,
        "current_stored_amount_meters": "8.000",
        "inventory_condition": "low_stock"
      }
    ],
    "upholsteries_pagination": {
      "has_more": true,
      "limit": 50,
      "offset": 0
    }
  }
}
```

### Data schema (inside `data`)

```json
{
  "upholstery": {
    "client_id": "string",
    "name": "string",
    "code": "string | null",
    "image_url": "string | null",
    "favorite": "boolean",
    "list_order": "number | null",
    "current_stored_amount_meters": "string | null",
    "inventory_condition": "available | low_stock | out_of_stock | null"
  }
}
```

### Filter semantics

- `favorite=true|false`: exact boolean filter.
- `in_stock=true`: includes only upholsteries with an active inventory row where condition is `available` or `low_stock`.
- `in_stock=false`: includes only upholsteries with an active inventory row where condition is `out_of_stock`.

Important:
- `in_stock=false` does not include records without active inventory rows.

### Sort order

1. `list_order ASC` with nulls last
2. `favorite DESC`
3. `created_at ASC`

---

## 3) Get upholstery by id

### Endpoint

- `GET /api/v1/upholsteries/{client_id}`

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01ABC...",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://...",
      "favorite": false,
      "list_order": null,
      "current_stored_amount_meters": "0.000",
      "inventory_condition": "out_of_stock"
    }
  }
}
```

### Error cases

- Not found or soft-deleted upholstery -> not found error.

---

## 4) Update upholstery

### Endpoint

- `PATCH /api/v1/upholsteries/{client_id}`

### Body (all fields optional)

```json
{
  "name": "Linen A Premium",
  "code": "LIN-A-P",
  "image_url": "https://...",
  "favorite": true
}
```

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01ABC...",
      "name": "Linen A Premium",
      "code": "LIN-A-P",
      "image_url": "https://...",
      "favorite": true,
      "list_order": 4,
      "current_stored_amount_meters": "8.000",
      "inventory_condition": "available"
    }
  }
}
```

### Behavior notes

- Partial update only; omitted fields remain unchanged.
- `name` and `code` uniqueness are checked inside workspace (excluding current record).

### Error cases

- Not found -> not found error.
- duplicate `name` or `code` -> conflict error.
- provided blank `name` -> validation error.

---

## 5) Delete upholstery (soft delete)

### Endpoint

- `DELETE /api/v1/upholsteries/{client_id}`

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {}
}
```

### Behavior notes

- Soft-deletes upholstery.
- Clears `list_order` to `null` on delete.

### Error cases

- Not found -> not found error.

---

## 6) Toggle single upholstery favorite

### Endpoint

- `PATCH /api/v1/upholsteries/{client_id}/favorite`

### Body

```json
{
  "favorite": true
}
```

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01ABC...",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://...",
      "favorite": true,
      "list_order": 3,
      "current_stored_amount_meters": "5.000",
      "inventory_condition": "low_stock"
    }
  }
}
```

### Error cases

- Not found -> not found error.

---

## 7) Toggle favorite in batch

### Endpoint

- `PATCH /api/v1/upholsteries/favorite`

### Body

```json
{
  "upholstery_ids": ["uph_01...", "uph_02...", "uph_03..."],
  "favorite": false
}
```

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "updated_count": 3
  }
}
```

### Behavior notes

- Updates all matching, non-deleted upholsteries in current workspace.
- `updated_count` can be lower than requested ids if some ids do not exist / are deleted / not in workspace.

### Validation / error cases

- Empty `upholstery_ids` -> validation error.

---

## 8) Update list order

### Endpoint

- `PATCH /api/v1/upholsteries/{client_id}/list-order`

### Body

```json
{
  "list_order": 2
}
```

or clear order:

```json
{
  "list_order": null
}
```

### Success response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01ABC...",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://...",
      "favorite": false,
      "list_order": 2,
      "current_stored_amount_meters": "8.000",
      "inventory_condition": "available"
    }
  }
}
```

### Behavior notes

- If `list_order` is set to a number, backend shifts other non-deleted upholsteries with `list_order >= new_value` by `+1`.
- If `list_order` is `null`, backend clears the target order without shifting others.

### Validation / error cases

- `list_order < 1` -> validation error.
- Not found -> not found error.

## Frontend action required

1. Point upholstery catalog screens to `/api/v1/upholsteries` for list/get/create/update/delete/favorite/list-order.
2. Implement list controls using optional filters: `q`, `in_stock`, `favorite`, plus offset pagination fields from `upholsteries_pagination`.
3. Treat `current_stored_amount_meters` as a string value in API responses (display-ready decimal string).
4. Support both single and batch favorite actions:
   - single card toggle -> `PATCH /{id}/favorite`
   - multi-select bulk toggle -> `PATCH /favorite`
5. For drag/drop or manual ordering, call `PATCH /{id}/list-order` after reorder operations.

## Validation notes

- Backend validation run:
  - Contract confirmed against current router/queries/commands implementation.
- Suggested frontend validation:
  - Verify `in_stock=false` behavior only returns `out_of_stock` rows that have active inventory records.
  - Verify batch favorite `updated_count` handling when some selected ids are stale.
  - Verify null `list_order` entries always render after ordered entries.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_upholsteries_crud_20260527.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholsteries_crud_20260527.md`
- Related debug plan (optional): _none_
