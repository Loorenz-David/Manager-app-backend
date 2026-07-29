# HANDOFF_TO_FRONTEND_pause_reasons_crud_20260722

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pause_reasons_crud_20260722`
- Created at (UTC): `2026-07-22T11:30:00Z`
- Owner agent: `codex`
- Status: **implemented**
- Source plan: `PLAN_custom_pause_reasons_20260722`

## TL;DR

Pause reasons are now workspace data. Use the CRUD endpoints below instead of a hardcoded
`StepEventReasonEnum` list. The two automatic reasons have `is_system_managed: true` and cannot be
deleted; their `slug` values are `pause_ended_shift` and `pause_other_task_priority`.

## Auth

- Reads: `ADMIN`, `MANAGER`, or `WORKER`.
- Writes: `ADMIN` or `MANAGER`.
- All responses use the standard envelope: `{ "data": ..., "warnings": [] }`.

## Endpoints

### `GET /api/v1/pause-reasons?limit=50&offset=0&pause_type=personal`

Returns non-deleted reasons ordered by `created_at` ascending. `pause_type` is optional and accepts
`personal` or `blocker`.

```json
{
  "pause_reasons": [
    {
      "client_id": "par_01...",
      "name": "Lunch break",
      "image_url": null,
      "pause_type": "personal",
      "description": null,
      "requires_description": false,
      "is_system_managed": false,
      "slug": "pause_lunch_break",
      "created_at": "2026-07-22T11:00:00+00:00",
      "created_by_id": null,
      "updated_at": null,
      "updated_by_id": null
    }
  ],
  "pause_reasons_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

### `GET /api/v1/pause-reasons/{client_id}`

Returns `{ "pause_reason": { ... } }` using the same object shape. Deleted or cross-workspace IDs
return `404`.

### `PUT /api/v1/pause-reasons`

Creates a user-managed reason. `slug` and `is_system_managed` are not accepted.

```json
{
  "name": "Supplier call",
  "image_url": "https://cdn.example/supplier-call.png",
  "pause_type": "blocker",
  "description": "Waiting for supplier confirmation",
  "requires_description": true
}
```

Returns `{ "pause_reason": { ... } }`. Names must be unique among non-deleted rows in the workspace.

### `PATCH /api/v1/pause-reasons/{client_id}`

Partial update. Any supplied field, including an explicit `null` for `image_url` or `description`, is
applied. `slug` and `is_system_managed` are not accepted. Returns the updated object.

### `DELETE /api/v1/pause-reasons/{client_id}`

Soft-deletes a user-managed reason and returns `{}`. System-managed reasons return `409 Conflict`.

## Realtime events

The existing generic workspace event pipeline emits these events after the database transaction:

| Event | Payload data |
|---|---|
| `pause_reason:created` | `{ "client_id": "par_..." }` |
| `pause_reason:updated` | `{ "client_id": "par_..." }` |
| `pause_reason:deleted` | `{ "client_id": "par_..." }` |

Treat the event as a cache invalidation signal and refetch the affected reason or list. No new socket
handler is required.

## Bootstrap defaults

After the Phase A schema is deployed, the secret-gated `POST /api/v1/bootstrap` creates all seven
legacy-equivalent rows idempotently. It returns their slug keys under `pause_reasons_seeded`. The
two system-managed defaults are protected from deletion.
