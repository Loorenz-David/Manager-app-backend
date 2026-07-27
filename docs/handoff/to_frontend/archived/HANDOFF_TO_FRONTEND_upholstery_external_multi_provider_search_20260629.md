# HANDOFF_TO_FRONTEND_upholstery_external_multi_provider_search_20260629

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_external_multi_provider_search_20260629`
- Created at (UTC): `2026-06-29T00:00:00Z`
- Owner agent: `codex`
- Source plan: `N/A — composed from current backend state and incremental external-provider implementation work`
- Source summary: `N/A`

## Backend delivery context

- What backend implemented:
  - Shared external upholstery search endpoint: `GET /api/v1/upholsteries/external`
  - Multi-provider fanout through one request using `providers`
  - Persisted upholstery create/list/get contract now includes:
    - `page_link`
    - `supplier_name`
  - External provider enum values:
    - `nevotex`
    - `ohlssons_tyger`
    - `fargotex`
  - Provider-specific compatibility route retained for Nevotex:
    - `GET /api/v1/upholsteries/external/nevotex`
  - Shared external upholstery candidate shape now includes:
    - `origin`
    - `external_url`
    - `page_link`
    - `supplier_name`

- API or contract changes:
  - Frontend no longer needs one endpoint per supplier.
  - The router accepts one or many external providers through the single `providers` query param.
  - Provider searches are executed concurrently across providers on the backend.
  - All providers normalize into one shared response shape so the frontend can render one uniform result list.
  - Database-backed upholstery responses now expose `page_link` and `supplier_name`.
  - `PUT /api/v1/upholsteries` can now create an upholstery together with supplier metadata in one request.

- Feature flags/toggles (if any):
  - None

## Frontend action required

1. Replace any provider-specific search flow with the shared endpoint `GET /api/v1/upholsteries/external`.
2. Send providers through `providers`, not `provider`.
3. Treat `providers` as a comma-separated string:
   - one provider: `providers=nevotex`
   - many providers: `providers=nevotex,ohlssons_tyger,fargotex`
4. Update the client model for external upholstery results to include `external_url`.
5. Update the client model for both external and persisted upholstery results to include:
   - `page_link`
   - `supplier_name`
6. Treat `origin` as required in the frontend external-candidate model.
7. Handle partial supplier coverage gracefully:
   - one provider may return zero matches while another returns results
   - an empty result list is a normal success state
8. Do not rely on frontend-side supplier-specific fields beyond the shared normalized shape and the persisted supplier summary fields documented below.

## Interface details

- Endpoint(s):
  - `GET /api/v1/upholsteries/external`
  - `GET /api/v1/upholsteries/external/nevotex` (compatibility helper, optional for frontend use)

- Auth:
  - **Current backend state for local testing:** auth is temporarily removed from the external search endpoints.
  - **Frontend expectation:** plan for JWT-authenticated usage again when backend restores route protection. Do not build the product feature around public access.

### 1. Shared multi-provider endpoint

- Method: `GET`
- Path: `/api/v1/upholsteries/external`
- Query params:
  - `q: string` required, `min_length=1`, `max_length=200`
  - `limit: integer` optional, default `7`, min `1`, max `20`
  - `providers: string` optional, comma-separated provider enum values

- Supported provider enum values:
  - `nevotex`
  - `ohlssons_tyger`
  - `fargotex`

- Important request rules:
  - `providers` is the only provider selector now.
  - If `providers` is omitted, the backend queries all registered providers.
  - If `providers` is provided, duplicates are ignored.
  - Invalid provider names return `422`.

- Request example: one provider

```http
GET /api/v1/upholsteries/external?q=Afrodite&providers=nevotex&limit=7
```

- Request example: many providers

```http
GET /api/v1/upholsteries/external?q=noma&providers=nevotex,ohlssons_tyger,fargotex&limit=7
```

- Success response shape

```json
{
  "data": {
    "upholsteries": [
      {
        "client_id": null,
        "name": "Noma",
        "code": "55379",
        "image_url": "https://fargotex.pl/wp-content/uploads/2025/03/nowa-noma-1024x1024-500x700.webp",
        "external_url": "https://fargotex.pl/produkt/noma/",
        "page_link": "https://fargotex.pl/produkt/noma/",
        "favorite": null,
        "list_order": null,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "supplier_name": "fargotex",
        "upholstery_category": null,
        "origin": "fargotex"
      },
      {
        "client_id": null,
        "name": "Tyg Afrodite 2 Midnight",
        "code": "1000402",
        "image_url": "https://nevotex.se/Files/Images/produktbilder/1000402.jpg",
        "external_url": "https://nevotex.se/Default.aspx?ID=6301&GroupId=GROUP318&ProductId=1000401&VariantID=VARGRP208_1000402",
        "page_link": "https://nevotex.se/Default.aspx?ID=6301&GroupId=GROUP318&ProductId=1000401&VariantID=VARGRP208_1000402",
        "favorite": null,
        "list_order": null,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "supplier_name": "nevotex",
        "upholstery_category": null,
        "origin": "nevotex"
      }
    ],
    "upholsteries_pagination": {
      "has_more": false,
      "limit": 7,
      "offset": 0
    },
    "providers": [
      "nevotex",
      "ohlssons_tyger",
      "fargotex"
    ]
  },
  "ok": true,
  "warnings": []
}
```

- Empty-result response shape

```json
{
  "data": {
    "upholsteries": [],
    "upholsteries_pagination": {
      "has_more": false,
      "limit": 7,
      "offset": 0
    },
    "providers": [
      "nevotex",
      "ohlssons_tyger",
      "fargotex"
    ]
  },
  "ok": true,
  "warnings": []
}
```

### 2. External upholstery candidate field reference

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `null` | Yes | Always `null` for external search candidates |
| `name` | `string` | No | Provider-normalized display name |
| `code` | `string` | No | Provider-specific stable identifier |
| `image_url` | `string` | No | Absolute image URL |
| `external_url` | `string` | Yes | Supplier product page URL when available |
| `page_link` | `string` | Yes | Frontend-safe alias for supplier product page URL |
| `favorite` | `null` | Yes | Always `null` for external candidates |
| `list_order` | `null` | Yes | Always `null` for external candidates |
| `current_stored_amount_meters` | `number` | No | Currently always `0` for external candidates |
| `inventory_condition` | `string` | No | Currently always `"out_of_stock"` for external candidates |
| `supplier_name` | `string` | Yes | Currently set from `origin` for external candidates |
| `upholstery_category` | `null` | Yes | Currently always `null` for external candidates |
| `origin` | `string` (enum) | No | See origin enum table below |

### 3. Persisted upholstery create/list/get contract

These fields apply to database-backed upholstery endpoints such as:

- `PUT /api/v1/upholsteries`
- `GET /api/v1/upholsteries`
- `GET /api/v1/upholsteries/{client_id}`

#### Create request additions

- New optional request fields on `PUT /api/v1/upholsteries`:
  - `page_link: string | null`
  - `supplier_name: string | null`
  - `supplier_base_url: string | null`
  - `supplier_country: string | null`
  - `supplier_city: string | null`
  - `supplier_street_address: string | null`

- Supplier creation behavior:
  - If `supplier_name` is omitted, no supplier is linked during create.
  - If `supplier_name` is provided, backend creates or reuses a supplier in the same workspace.
  - If supplier detail fields are sent without `supplier_name`, backend rejects the request.

- Example create request

```json
{
  "name": "Afrodite Midnight",
  "code": "1000402",
  "image_url": "https://nevotex.se/Files/Images/produktbilder/1000402.jpg",
  "page_link": "https://nevotex.se/Default.aspx?ID=6301&GroupId=GROUP318&ProductId=1000401&VariantID=VARGRP208_1000402",
  "supplier_name": "nevotex",
  "supplier_base_url": "https://nevotex.se",
  "current_stored_amount_meters": 12
}
```

#### Persisted upholstery response shape

```json
{
  "data": {
    "upholstery": {
      "client_id": "uph_...",
      "name": "Afrodite Midnight",
      "code": "1000402",
      "image_url": "https://nevotex.se/Files/Images/produktbilder/1000402.jpg",
      "page_link": "https://nevotex.se/Default.aspx?ID=6301&GroupId=GROUP318&ProductId=1000401&VariantID=VARGRP208_1000402",
      "favorite": false,
      "list_order": null,
      "inventory_id": "uin_...",
      "current_stored_amount_meters": "12.000",
      "inventory_condition": "available",
      "supplier_name": "nevotex",
      "upholstery_category": null,
      "origin": "database"
    }
  },
  "ok": true,
  "warnings": []
}
```

#### Persisted upholstery field notes

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `page_link` | `string` | Yes | Stored supplier/product page URL on the upholstery row |
| `supplier_name` | `string` | Yes | Resolved from the preferred supplier link, if one exists |
| `origin` | `string` | No | Always `"database"` for persisted upholsteries |

### 4. External provider origin enum

| Value | Meaning |
|---|---|
| `nevotex` | Result came from Nevotex |
| `ohlssons_tyger` | Result came from Ohlssons Tyger |
| `fargotex` | Result came from Fargotex |

### 5. Provider-specific notes

#### `nevotex`

- Search is query-driven against Nevotex search feed.
- `external_url` resolves from the live Nevotex `link` field when present.
- Example product page link shape:
  - `https://nevotex.se/Default.aspx?ID=6301&GroupId=...&ProductId=...`

#### `ohlssons_tyger`

- Search is query-driven, but the provider fetches HTML and parses product detail pages server-side.
- `external_url` is the product detail page URL.
- Example product page link shape:
  - `https://www.ohlssonstyger.se/sv/artikel/<product-slug>`

#### `fargotex`

- Search is category-crawl based, not remote search-endpoint based.
- Backend crawls the upholstery category archive and filters matches locally by `q`.
- `external_url` is the product page URL.
- Example product page link shape:
  - `https://fargotex.pl/produkt/<product-slug>/`

### 6. Pagination and provider behavior notes

- `upholsteries_pagination.has_more` is currently always `false`.
- `limit` limits the returned result count after provider work completes.
- Provider work is concurrent across providers.
- Result ordering is flattened in provider order:
  - if `providers=nevotex,fargotex`, Nevotex results appear before Fargotex results
- The `providers` array in the response echoes the resolved provider selection used by the backend.

### 7. Error cases

| HTTP status | When |
|---|---|
| `422` | Missing `q` |
| `422` | Empty `q` |
| `422` | Invalid `limit` |
| `422` | Invalid provider enum value inside `providers` |
| `422` | Supplier detail fields provided without `supplier_name` on `PUT /api/v1/upholsteries` |
| `200` | Zero matches from all providers |

- Example validation error

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["query", "q"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

- Example invalid provider error

```json
{
  "error": "Invalid external upholstery provider 'ohlssons_tyge'. Allowed values: nevotex, ohlssons_tyger, fargotex",
  "ok": false
}
```

- Example create validation error

```json
{
  "error": "supplier_name is required when supplier details are provided.",
  "ok": false
}
```

## Validation notes

- Backend validation run:
  - `./.venv/bin/python -m pytest tests/unit/services/queries/upholstery/test_list_external_upholsteries.py tests/unit/test_upholsteries_router.py -q`
  - `./.venv/bin/python -m pytest tests/unit/services/infra/nevotex/test_normalizer.py tests/unit/services/infra/ohlssons_tyger/test_ohlssons_tyger_normalizer.py tests/unit/services/infra/upholstery_providers/test_ohlssons_tyger.py -q`
  - `./.venv/bin/python -m pytest tests/unit/services/infra/fargotex/test_fargotex_parser.py tests/unit/services/infra/fargotex/test_fargotex_normalizer.py tests/unit/services/infra/upholstery_providers/test_fargotex.py -q`
  - `./.venv/bin/python -m pytest tests/unit/services/commands/upholstery/test_create_upholstery.py -q`

- Suggested frontend validation:
  - Model `providers` as one CSV query param, not repeated `provider` params.
  - Treat `origin` as required.
  - Treat `external_url` as optional in the UI model.
  - Handle empty results as a normal success state.
  - Avoid assuming all providers return the same number of matches.
  - Display supplier-specific badges or grouping from `origin`, not from URL inspection.

## Trace links

- Related prior handoff: [HANDOFF_TO_FRONTEND_upholstery_nevotex_and_inline_category_20260625.md](/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_nevotex_and_inline_category_20260625.md)
