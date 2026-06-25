# HANDOFF_TO_FRONTEND_upholstery_nevotex_and_inline_category_20260625

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_nevotex_and_inline_category_20260625`
- Created at (UTC): `2026-06-25T10:05:53Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_nevotex_upholstery_search_20260625.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_nevotex_upholstery_search_20260625.md`

## Backend delivery context

- What backend implemented:
  - New Nevotex search endpoint: `GET /api/v1/upholsteries/external/nevotex`
  - Extended upholstery create endpoint: `PUT /api/v1/upholsteries`
  - New `origin` field on upholstery cards:
    - Nevotex search results return `origin: "nevotex"`
    - Database-backed upholstery responses return `origin: "database"`
- API or contract changes:
  - Frontend can now search external Nevotex products through the backend instead of calling Nevotex directly from the browser.
  - Frontend can now create a new upholstery category inline while creating a new upholstery by sending `create_category`.
- Feature flags/toggles (if any):
  - None

## Frontend action required

1. Add a frontend schema/type for Nevotex search results that matches the exact upholstery card shape returned by the backend.
2. Treat `origin` as required in the client model for upholstery cards:
   - `"nevotex"` for external candidates
   - `"database"` for stored upholsteries
3. Build the Nevotex search flow against `GET /api/v1/upholsteries/external/nevotex` using `q` and optional `limit`.
4. Build the create-upholstery form so it can send exactly one of:
   - `upholstery_category_id`
   - `create_category`
5. Do not send both `upholstery_category_id` and `create_category` in the same create request.
6. Treat meter values in responses as strings, not numbers.

## Interface details

- Endpoint(s):
  - `GET /api/v1/upholsteries/external/nevotex`
  - `PUT /api/v1/upholsteries`
- Auth:
  - `GET /external/nevotex`: `ADMIN`, `MANAGER`, `WORKER`
  - `PUT /api/v1/upholsteries`: `ADMIN`, `MANAGER`

### 1. Nevotex search

- Method: `GET`
- Path: `/api/v1/upholsteries/external/nevotex`
- Query params:
  - `q: string` required, `min_length=1`, `max_length=200`
  - `limit: integer` optional, default `7`, min `1`, max `20`

- Request example:

```http
GET /api/v1/upholsteries/external/nevotex?q=Tyg%20Afrodite&limit=7
Authorization: Bearer <token>
```

- Success response shape:

```json
{
  "data": {
    "upholsteries": [
      {
        "client_id": null,
        "name": "Tyg Afrodite 2 Midnight",
        "code": "1000402",
        "image_url": "https://nevotex.se/Files/Images/produktbilder/1000402.jpg",
        "favorite": null,
        "list_order": null,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "upholstery_category": null,
        "origin": "nevotex"
      }
    ],
    "upholsteries_pagination": {
      "has_more": false,
      "limit": 7,
      "offset": 0
    }
  },
  "ok": true,
  "warnings": []
}
```

- Empty-result response shape:

```json
{
  "data": {
    "upholsteries": [],
    "upholsteries_pagination": {
      "has_more": false,
      "limit": 7,
      "offset": 0
    }
  },
  "ok": true,
  "warnings": []
}
```

- Important frontend notes:
  - `client_id` is always `null` for Nevotex search results.
  - `favorite` is always `null`.
  - `list_order` is always `null`.
  - `current_stored_amount_meters` is currently `0` as a number for Nevotex candidates.
  - `inventory_condition` is always `"out_of_stock"` for Nevotex candidates.
  - `upholstery_category` is always `null` for Nevotex candidates in this phase.
  - `has_more` is always `false` in the current implementation.

### 2. Create upholstery

- Method: `PUT`
- Path: `/api/v1/upholsteries`
- Body fields:
  - `client_id: string | null`
  - `name: string` required
  - `code: string | null`
  - `image_url: string | null`
  - `favorite: boolean` optional, default `false`
  - `current_stored_amount_meters: number|string|null`
  - `low_stock_threshold_meters: number|string|null`
  - `minimum_to_have: integer | null`
  - `maximum_to_have: integer | null`
  - `projected_inventory_value_minor: integer | null`
  - `currency: "swedish_krona" | "danish_krona" | "euro" | null`
  - `planning_position: string | null`
  - `upholstery_category_id: string | null`
  - `create_category: object | null`

- Inline category object:
  - `client_id: string | null`
  - `name: string` required
  - `image_url: string | null`
  - `favorite: boolean` optional, default `false`

- Mutual exclusion rule:
  - Send `upholstery_category_id` or `create_category`, never both.

- Example A: create upholstery linked to an existing category

```json
{
  "name": "Blue Velvet",
  "code": "BLU-1",
  "image_url": "https://cdn.example.com/blue-velvet.jpg",
  "current_stored_amount_meters": 2.5,
  "low_stock_threshold_meters": 1.0,
  "upholstery_category_id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
}
```

- Example B: create upholstery and create a new category inline

```json
{
  "name": "Green Linen",
  "code": "GRN-2",
  "current_stored_amount_meters": 4.0,
  "create_category": {
    "name": "Mobeltyger",
    "image_url": null,
    "favorite": false
  }
}
```

- Example C: create upholstery with no category

```json
{
  "name": "Plain Fabric",
  "code": "PLN-3"
}
```

- Success response shape:

```json
{
  "data": {
    "upholstery": {
      "client_id": "uph_01ARZ3NDEKTSV4RRFFQ69G5FAA",
      "name": "Green Linen",
      "code": "GRN-2",
      "image_url": null,
      "favorite": false,
      "list_order": null,
      "current_stored_amount_meters": "4.000",
      "inventory_condition": "available",
      "upholstery_category": {
        "id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "name": "Mobeltyger",
        "image_url": null
      },
      "origin": "database"
    }
  },
  "ok": true,
  "warnings": []
}
```

- Important frontend notes:
  - `current_stored_amount_meters` in the create response is a string.
  - `origin` in the create response is always `"database"`.
  - If `create_category` is used, the response already includes the created category under `upholstery.upholstery_category`.
  - No separate frontend category-create call is needed when using `create_category`.

- Error cases:
  - `422`:
    - missing `q` on Nevotex search
    - empty `q`
    - invalid `limit`
    - blank `name`
    - blank `create_category.name`
    - both `upholstery_category_id` and `create_category` sent together
  - `404`:
    - `upholstery_category_id` points to a non-existent or deleted category
  - `409`:
    - upholstery `client_id` already exists
    - upholstery `name` already exists in workspace
    - upholstery `code` already exists in workspace
    - inline category `client_id` already exists
    - inline category `name` already exists in workspace
  - `502`:
    - Nevotex timeout
    - Nevotex request failure
    - Nevotex non-200 response
    - Nevotex invalid top-level response shape

- Error response shape:

```json
{
  "error": "create_category and upholstery_category_id are mutually exclusive. Provide one or the other, not both.",
  "ok": false
}
```

## Validation notes

- Backend validation run:
  - `./.venv/bin/python -m pytest tests/unit/services/infra/nevotex/test_client.py tests/unit/services/infra/nevotex/test_normalizer.py`
  - `./.venv/bin/python -m pytest tests/unit/test_upholstery_request_models.py tests/unit/services/commands/upholstery/test_create_upholstery.py tests/unit/test_upholstery_serializers.py`
- Suggested frontend validation:
  - Enforce client-side mutual exclusion between `upholstery_category_id` and `create_category`
  - Treat all response meter fields as strings in stored/database upholsteries
  - Treat Nevotex candidates as selectable external records with no `client_id`
  - Handle empty Nevotex search results as a normal success state, not an error state

## Trace links

- Parent plan:
  - `backend/docs/architecture/archives/implementation/PLAN_nevotex_upholstery_search_20260625.md`
  - `backend/docs/architecture/archives/implementation/PLAN_create_upholstery_inline_category_20260625.md`
- Parent summary:
  - `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_nevotex_upholstery_search_20260625.md`
  - `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_inline_category_20260625.md`
- Related debug plan (optional):
  - `backend/docs/architecture/archives/implementation/PLAN_nevotex_search_corrections_20260625.md`
