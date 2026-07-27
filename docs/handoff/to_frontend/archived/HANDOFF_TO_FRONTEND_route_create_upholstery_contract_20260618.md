# HANDOFF_TO_FRONTEND_route_create_upholstery_contract_20260618

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_route_create_upholstery_contract_20260618`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Owner agent: `copilot`
- Source plan: `N/A (targeted contract handoff)`
- Source summary: `N/A (targeted contract handoff)`

## Endpoint summary

Create one upholstery (and its linked inventory row) in a single atomic operation.

- Method: `PUT`
- Path: `/api/v1/upholsteries`
- Router symbol: `route_create_upholstery`
- Auth: `Bearer <JWT>`
- Allowed roles: `ADMIN`, `MANAGER`

## Global response envelope

All API responses from this router use this envelope:

Success:

```json
{
  "ok": true,
  "warnings": [],
  "data": {}
}
```

Error:

```json
{
  "ok": false,
  "error": "..."
}
```

## Request body contract

### Required fields

| Field | Type | Notes |
|---|---|---|
| `name` | `string` | Trimmed by backend. Must not be blank. |

### Optional fields

| Field | Type | Default | Validation / behavior |
|---|---|---|---|
| `client_id` | `string` | auto-generated if omitted | If provided, must be format `uph_<ULID26>` and must be unique. |
| `code` | `string \| null` | `null` | If provided, must be unique within workspace (for non-deleted upholsteries). |
| `image_url` | `string \| null` | `null` | Stored as-is. |
| `favorite` | `boolean` | `false` | Favorite flag at creation time. |
| `current_stored_amount_meters` | `number \| string \| null` | treated as `0` when omitted/null | Must be `>= 0` when provided. |
| `low_stock_threshold_meters` | `number \| string \| null` | `null` | Must be `> 0` when provided. |
| `minimum_to_have` | `integer \| null` | `null` | Must be `>= 0` when provided. |
| `maximum_to_have` | `integer \| null` | `null` | Must be `>= 0` when provided. |
| `projected_inventory_value_minor` | `integer \| null` | `null` | Must be `>= 0` when provided. |
| `currency` | `"swedish_krona" \| "danish_krona" \| "euro" \| null` | `null` | Enum value. |
| `planning_position` | `string \| null` | `null` | Optional free-text planning position. |

Notes for frontend:
- This create endpoint is `PUT` (not `POST`).
- Decimal-like fields can be sent as JSON numbers or strings; backend serializes many decimal fields back as strings.

## Request example

```json
{
  "name": "Linen A",
  "code": "LIN-A",
  "image_url": "https://cdn.example.com/upholstery/linen-a.webp",
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

## Success response

- HTTP: `200 OK`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_01HXYZ...",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://cdn.example.com/upholstery/linen-a.webp",
      "favorite": false,
      "list_order": null,
      "current_stored_amount_meters": "12.500",
      "inventory_condition": "available"
    }
  }
}
```

### Returned upholstery object shape

| Field | Type | Notes |
|---|---|---|
| `client_id` | `string` | Upholstery id (`uph_...`). |
| `name` | `string` | |
| `code` | `string \| null` | |
| `image_url` | `string \| null` | |
| `favorite` | `boolean` | |
| `list_order` | `number \| null` | Usually `null` on fresh create unless set elsewhere. |
| `current_stored_amount_meters` | `string \| null` | Computed available amount, serialized as string. |
| `inventory_condition` | `"available" \| "low_stock" \| "out_of_stock" \| null` | Computed from inventory amounts and threshold. |

## Inventory condition semantics at creation

Initial condition is computed using:
- `stored = current_stored_amount_meters` (or `0` if omitted)
- `in_need = 0`
- `threshold = low_stock_threshold_meters`

Rules:
- `out_of_stock` if `stored - in_need <= 0`
- `low_stock` if threshold is set and `stored - in_need <= threshold`
- `available` otherwise

## Error responses (common)

### 401 Unauthorized

Missing/invalid/expired token.

```json
{
  "detail": "Invalid or expired token."
}
```

### 403 Forbidden

Authenticated but role is not allowed.

```json
{
  "detail": "Insufficient role permissions."
}
```

### 422 Unprocessable Entity

Validation errors from parsed request (first error returned).

Example:

```json
{
  "ok": false,
  "error": "name: Value error, name must not be blank."
}
```

Other 422 examples:
- `low_stock_threshold_meters: Value error, low_stock_threshold_meters must be greater than 0.`
- `current_stored_amount_meters: Value error, current_stored_amount_meters must be >= 0.`
- `minimum_to_have: Value error, Value must be >= 0.`
- `client_id must start with 'uph_'...` (if invalid provided client id)

### 409 Conflict

Uniqueness conflicts.

Examples:

```json
{
  "ok": false,
  "error": "An upholstery with this name already exists in the workspace."
}
```

```json
{
  "ok": false,
  "error": "An upholstery with this code already exists in the workspace."
}
```

```json
{
  "ok": false,
  "error": "Provided client_id is already in use."
}
```

### 500 Internal Server Error

Unexpected backend exception fallback.

```json
{
  "ok": false,
  "error": "An unexpected internal error occurred."
}
```

## Frontend integration checklist

1. Use `PUT /api/v1/upholsteries` with Bearer token.
2. Require non-empty `name` in UI before submit.
3. Treat all stock/threshold/value numeric inputs as non-negative; threshold must be strictly positive if set.
4. Accept both number and string input for decimal fields in client-side DTO typing.
5. Handle response envelope by checking `ok` before reading `data`.
6. Expect `current_stored_amount_meters` in response as a string.
7. Handle 409 conflicts with user-facing duplicate messages (name/code/client_id).
8. Handle 401/403 by auth flow (re-login or permission message).

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/upholsteries.py`
- Service: `backend/app/beyo_manager/services/commands/upholstery/create_upholstery.py`
- Request parser: `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`
- Serializer: `backend/app/beyo_manager/domain/upholstery/serializers.py`
- Response envelope helpers: `backend/app/beyo_manager/routers/http/response.py`
