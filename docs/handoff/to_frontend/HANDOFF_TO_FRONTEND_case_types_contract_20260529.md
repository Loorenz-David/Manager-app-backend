# Handoff to Frontend: Case Types API Contract (2026-05-29)

## Summary
The backend now exposes dedicated endpoints to create, list, and get case types.

Base path:
- `/api/v1/case-types`

## Endpoints

### 1) Create case type
- Method: `POST`
- Path: `/api/v1/case-types`
- Roles: `admin`, `manager`

Request body:
```json
{
  "client_id": "cty_custom_optional",
  "name": "Repair",
  "image_url": "https://cdn.example.com/case-types/repair.webp",
  "description": "Repair requests",
  "entity_type": "item"
}
```

Notes:
- `client_id` is optional. If omitted, backend generates one.
- `entity_type` must be one of allowed enum values in `CaseLinkEntityTypeEnum`.
- `(name, entity_type)` combination is unique.

Success response shape:
```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case_type": {
      "client_id": "cty_xxx",
      "name": "Repair",
      "image_url": "https://cdn.example.com/case-types/repair.webp",
      "description": "Repair requests",
      "entity_type": "item"
    }
  }
}
```

### 2) List case types
- Method: `GET`
- Path: `/api/v1/case-types`
- Roles: `admin`, `manager`, `worker`

Query params:
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)
- `q` (string, optional): applied to `name` and `description`
- `entity_type` (string, optional): comma-separated enum values, ex: `item,task`

Success response shape:
```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case_types": [
      {
        "client_id": "cty_xxx",
        "name": "Repair",
        "image_url": "https://cdn.example.com/case-types/repair.webp",
        "description": "Repair requests",
        "entity_type": "item"
      }
    ],
    "case_types_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

### 3) Get case type by client_id
- Method: `GET`
- Path: `/api/v1/case-types/{client_id}`
- Roles: `admin`, `manager`, `worker`

Success response shape:
```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case_type": {
      "client_id": "cty_xxx",
      "name": "Repair",
      "image_url": "https://cdn.example.com/case-types/repair.webp",
      "description": "Repair requests",
      "entity_type": "item"
    }
  }
}
```

## Error handling
Error envelope follows standard contract:
```json
{
  "ok": false,
  "error": "message"
}
```

Common cases:
- `400` validation error:
  - invalid `entity_type`
  - malformed request fields
- `404` not found:
  - requested case type does not exist
- `409` conflict:
  - duplicate `(name, entity_type)`
  - provided `client_id` already exists
