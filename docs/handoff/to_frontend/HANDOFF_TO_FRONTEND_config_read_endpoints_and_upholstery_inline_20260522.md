# HANDOFF_TO_FRONTEND_config_read_endpoints_and_upholstery_inline_20260522

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_config_read_endpoints_and_upholstery_inline_20260522`
- Created at (UTC): `2026-05-22T15:55:00Z`
- Owner agent: `copilot`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_config_list_get_endpoints_20260522.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_config_list_get_endpoints_20260522.md`

Additional source plan and summary:
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_inline_20260522.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_inline_20260522.md`

## Backend delivery context

- What backend implemented:
  - New read endpoints for frontend option loading:
    - Item categories (list + get)
    - Issue types (list + get)
    - Issue category configs (list + get)
    - Upholsteries (list + get)
  - Upholstery payload now inlines inventory context:
    - `current_stored_amount_meters` (string or null)
    - `inventory_condition` (string enum value or null)
- API or contract changes:
  - Added endpoint surfaces under `/api/v1/item-categories`, `/api/v1/issue-types`, `/api/v1/issue-category-configs`, and `/api/v1/upholsteries`.
  - All success responses use the standard envelope:
    - `{"ok": true, "data": <payload>, "warnings": []}`
  - All domain errors use:
    - `{"ok": false, "error": "<message>"}`
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Wire form option fetchers to these new list endpoints with `limit`, `offset`, optional `q`, and (for issue-category-configs) optional `item_category_id`.
2. Use the new upholstery inline fields directly in option cards/rows:
   - `current_stored_amount_meters`
   - `inventory_condition`
3. Use `*_pagination.has_more` + `offset` for pagination/infinite scroll.
4. Handle nulls safely for optional fields (`image_url`, upholstery inventory fields).
5. Handle 404 route/get cases and standard auth failures.
6. Use the working sections list endpoint to render section-member assignments from `members` without additional member fetch calls.

## Interface details

### 1) Item Categories

- Endpoint(s):
  - `GET /api/v1/item-categories?limit=<1..200>&offset=<0+>&q=<optional>`
  - `GET /api/v1/item-categories/{client_id}`
- Request shape:
  - Query params:
    - `limit: int` default `50`, max `200`
    - `offset: int` default `0`
    - `q: string | null`
- Response shape (list):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "item_categories": [
      {
        "client_id": "itc_xxx",
        "name": "Wood Chair",
        "major_category": "wood",
        "created_at": "2026-05-22T10:00:00+00:00",
        "created_by_id": "usr_xxx",
        "image_url": "https://..." 
      }
    ],
    "item_categories_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

- Response shape (get):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "item_category": {
      "client_id": "itc_xxx",
      "name": "Wood Chair",
      "major_category": "wood",
      "created_at": "2026-05-22T10:00:00+00:00",
      "created_by_id": "usr_xxx",
      "image_url": "https://..."
    }
  }
}
```

### 2) Issue Types

- Endpoint(s):
  - `GET /api/v1/issue-types?limit=<1..200>&offset=<0+>&q=<optional>`
  - `GET /api/v1/issue-types/{client_id}`
- Request shape:
  - Query params:
    - `limit: int` default `50`, max `200`
    - `offset: int` default `0`
    - `q: string | null`
- Response shape (list):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "issue_types": [
      {
        "client_id": "ist_xxx",
        "name": "Scratch",
        "source": "internal_inspection",
        "created_at": "2026-05-22T10:00:00+00:00",
        "created_by_id": "usr_xxx"
      }
    ],
    "issue_types_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

- Response shape (get):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "issue_type": {
      "client_id": "ist_xxx",
      "name": "Scratch",
      "source": "internal_inspection",
      "created_at": "2026-05-22T10:00:00+00:00",
      "created_by_id": "usr_xxx"
    }
  }
}
```

### 3) Issue Category Configs

- Endpoint(s):
  - `GET /api/v1/issue-category-configs?limit=<1..200>&offset=<0+>&q=<optional>&item_category_id=<optional>`
  - `GET /api/v1/issue-category-configs/{client_id}`
- Request shape:
  - Query params:
    - `limit: int` default `50`, max `200`
    - `offset: int` default `0`
    - `q: string | null` (matches `issue_type_name`)
    - `item_category_id: string | null`
- Notes:
  - List route applies active-window filtering (`effective_from`/`effective_to`) server-side.
- Response shape (list):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "issue_category_configs": [
      {
        "client_id": "icc_xxx",
        "item_category_id": "itc_xxx",
        "issue_type_id": "ist_xxx",
        "base_time_seconds": 600,
        "issue_type_name": "Scratch"
      }
    ],
    "issue_category_configs_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

- Response shape (get):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "issue_category_config": {
      "client_id": "icc_xxx",
      "item_category_id": "itc_xxx",
      "issue_type_id": "ist_xxx",
      "base_time_seconds": 600,
      "issue_type_name": "Scratch"
    }
  }
}
```

### 4) Upholsteries (with inline inventory fields)

- Endpoint(s):
  - `GET /api/v1/upholsteries?limit=<1..200>&offset=<0+>&q=<optional>`
  - `GET /api/v1/upholsteries/{client_id}`
- Request shape:
  - Query params:
    - `limit: int` default `50`, max `200`
    - `offset: int` default `0`
    - `q: string | null` (matches by `name` or `code`)
- Response shape (list):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholsteries": [
      {
        "client_id": "uph_xxx",
        "name": "Linen A",
        "code": "LIN-A",
        "image_url": "https://...",
        "current_stored_amount_meters": "12.500",
        "inventory_condition": "available"
      }
    ],
    "upholsteries_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

- Response shape (get):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "upholstery": {
      "client_id": "uph_xxx",
      "name": "Linen A",
      "code": "LIN-A",
      "image_url": "https://...",
      "current_stored_amount_meters": "12.500",
      "inventory_condition": "available"
    }
  }
}
```

- Nullability rules:
  - If no inventory row exists: both are `null`.
  - If inventory exists but `current_stored_amount_meters` is DB NULL: field is `null`.

### 5) Working Sections (with members)

- Endpoint(s):
  - `GET /api/v1/working-sections?limit=<1..200>&offset=<0+>`
  - `GET /api/v1/working-sections/{working_section_id}`
- Request shape:
  - Query params:
    - `limit: int` default `50`, max `200`
    - `offset: int` default `0`
- Response shape (list):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [
      {
        "client_id": "wse_xxx",
        "name": "Assembly",
        "image": "https://...",
        "dependencies": [
          { "client_id": "wse_dep_1", "name": "Pre-check" }
        ],
        "item_categories": [
          { "client_id": "itc_xxx", "name": "Wood", "major_category": "wood" }
        ],
        "supported_issue_types": [
          { "client_id": "ist_xxx", "name": "Scratch" }
        ],
        "members": [
          {
            "client_id": "usr_xxx",
            "username": "alex",
            "profile_picture": "https://..."
          }
        ]
      }
    ],
    "working_sections_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

- Response shape (get):

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_section": {
      "client_id": "wse_xxx",
      "name": "Assembly",
      "image": "https://...",
      "dependencies": [
        { "client_id": "wse_dep_1", "name": "Pre-check" }
      ],
      "item_categories": [
        { "client_id": "itc_xxx", "name": "Wood", "major_category": "wood" }
      ],
      "supported_issue_types": [
        { "client_id": "ist_xxx", "name": "Scratch" }
      ],
      "members": [
        {
          "client_id": "usr_xxx",
          "username": "alex",
          "profile_picture": "https://..."
        }
      ]
    }
  }
}
```

- Notes:
  - `members` is always present and is an array (possibly empty).
  - Member objects are lightweight by design: `client_id`, `username`, `profile_picture`.

### Error cases (all endpoints)

- Unauthorized/expired JWT:

```json
{
  "ok": false,
  "error": "..."
}
```

- Forbidden role:

```json
{
  "ok": false,
  "error": "..."
}
```

- Not found for `{client_id}` get routes (HTTP 404):

```json
{
  "ok": false,
  "error": "Item category not found."
}
```

Possible messages by endpoint:
- Item category: `Item category not found.`
- Issue type: `Issue type not found.`
- Issue category config: `Issue category config not found.`
- Upholstery: `Upholstery not found.`
- Working section: `Working section not found.`

## Validation notes

- Backend validation run:
  - Import smoke passed for new query + serializer modules.
  - Alembic migration for config endpoints plan applied successfully (`alembic upgrade head`).
  - Upholstery inline inventory update import smoke passed.
- Suggested frontend validation:
  - Verify each list endpoint renders and paginates with `has_more/offset`.
  - Verify each get endpoint detail panel handles 404 gracefully.
  - Verify upholstery UI handles null inventory fields and non-null string meter values.

## Trace links

- Parent plan:
  - `backend/docs/architecture/archives/implementation/PLAN_config_list_get_endpoints_20260522.md`
  - `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_inline_20260522.md`
- Parent summary:
  - `backend/docs/architecture/implemented_summaries/SUMMARY_config_list_get_endpoints_20260522.md`
  - `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_inline_20260522.md`
- Related debug plan (optional):
  - None.
