# HANDOFF_TO_FRONTEND_pin_notification_batch_20260620

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pin_notification_batch_20260620`
- Created at (UTC): `2026-06-20T13:04:27Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_pin_notification_batch_20260620.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_batch_20260620.md`

## Backend delivery context

- What backend implemented: Batch create/upsert, delete, edit, and list endpoints for notification pins.
- API or contract changes: `POST /pins` and `DELETE /pins` now accept JSON arrays. `PATCH /pins` and `GET /pins` are new.
- Feature flags/toggles (if any): _none_

## Frontend action required

1. Replace any single-item pin/unpin calls with the batch list endpoints.
2. Generate and inject `client_id` values client-side using the `npin_` prefix before calling `POST /pins`.
3. Store `major_entity_type` + `major_client_entity_id` on each pin creation request to enable efficient batch delete and list queries later.
4. Use `PATCH /pins` to update conditions or `fire_once` on existing pins by their `client_id`.
5. Use `GET /pins?major_client_entity_ids=<id>` to hydrate pin state when opening a task view.

## Interface details

### POST `/api/v1/notifications/pins`

Auth: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`

Request body:

```json
[
  {
    "client_id": "npin_<client_generated_id>",
    "entity_type": "task_step",
    "entity_client_id": "tsp_...",
    "major_entity_type": "task",
    "major_client_entity_id": "tsk_...",
    "conditions": [{"type": "state", "op": "in", "value": ["completed"]}],
    "fire_once": false
  }
]
```

Constraints:
- `client_id` is required, must start with `npin_`, and must be at most 64 characters.
- `major_entity_type` and `major_client_entity_id` must both be provided or both omitted.
- Duplicate `(entity_type, entity_client_id)` pairs in one request are rejected.
- Re-pinning an existing `(user_id, entity_type, entity_client_id)` overwrites `conditions`, `fire_once`, and major entity fields while preserving the existing pin `client_id`.

Response shape:

```json
{
  "ok": true,
  "data": {
    "pins": [{"client_id": "npin_..."}]
  },
  "warnings": []
}
```

Error cases:
- Unknown `entity_type`.
- Invalid `conditions` type, op, or state value.
- Missing or invalid `client_id`.
- One major entity field provided without the other.
- Duplicate pin target in a single batch.

### DELETE `/api/v1/notifications/pins`

Auth: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`

Request body:

```json
[
  {"client_id": "npin_..."},
  {"major_entity_type": "task", "major_client_entity_id": "tsk_..."}
]
```

Constraints:
- Each item must target either by `client_id` or by `major_entity_type` + `major_client_entity_id`.
- Deletes are scoped to the authenticated user.
- Missing pins are ignored.

Response shape:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

Error cases:
- Both targeting modes provided in one item.
- Neither targeting mode provided.
- Only one major entity field provided.

### PATCH `/api/v1/notifications/pins`

Auth: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`

Request body:

```json
[
  {
    "client_id": "npin_...",
    "conditions": [{"type": "state", "op": "eq", "value": "completed"}],
    "fire_once": true
  }
]
```

Constraints:
- `client_id` is required and must start with `npin_`.
- Missing or non-owned pins are skipped.
- Conditions are validated against the existing pin's `entity_type`.

Response shape:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

Error cases:
- Invalid `client_id` prefix.
- Invalid condition for the stored pin entity type.

### GET `/api/v1/notifications/pins`

Auth: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`

Query params:
- `entity_client_ids`: comma-separated entity IDs.
- `major_client_entity_ids`: comma-separated controlling entity IDs.

Exactly one of `entity_client_ids` or `major_client_entity_ids` is required.

Response shape:

```json
{
  "ok": true,
  "data": {
    "pins": [
      {
        "client_id": "npin_...",
        "entity_type": "task_step",
        "entity_client_id": "tsp_...",
        "major_entity_type": "task",
        "major_client_entity_id": "tsk_...",
        "conditions": null,
        "fire_once": false,
        "pinned_at": "2026-06-20T13:04:27+00:00",
        "user": {
          "client_id": "usr_...",
          "username": "Example",
          "profile_picture": null
        }
      }
    ]
  },
  "warnings": []
}
```

Error cases:
- Both query params provided.
- Neither query param provided.

## Reference: Entity types and state enums

### Entity types (`entity_type` / `major_entity_type`)

All values are from `EntityType(StrEnum)` in `domain/presence/enums.py`:

| `entity_type` value | Supports state condition | `major_entity_type` for cleanup |
|---------------------|-------------------------|----------------------------------|
| `task`              | yes                     | `task` (self)                    |
| `task_step`         | yes                     | `task`                           |
| `item_upholstery`   | yes                     | `task`                           |
| `case`              | no                      | `task`                           |
| `case_list`         | no                      | -                                |
| `conversation`      | no                      | -                                |
| `conversation_list` | no                      | -                                |

The only supported value for `major_entity_type` in the current task-driven design is `"task"`. The `major_client_entity_id` is the `client_id` of the controlling task.

### State enum values per entity type

These are the only legal values for a `state` condition on each entity type.

**`task`**

| Value | Meaning |
|-------|---------|
| `pending` | Task created, not yet assigned |
| `assigned` | Task assigned to a worker |
| `working` | Task actively in progress |
| `stalled` | Task blocked or on hold |
| `ready` | Task ready for next action |
| `resolved` | Task successfully completed |
| `failed` | Task ended in failure |
| `cancelled` | Task cancelled |

**`task_step`**

| Value | Meaning |
|-------|---------|
| `pending` | Step not yet started |
| `working` | Step actively in progress |
| `paused` | Step paused mid-execution |
| `ended_shift` | Worker ended their shift mid-step |
| `blocked` | Step blocked by a dependency |
| `completed` | Step successfully completed |
| `skipped` | Step skipped intentionally |
| `failed` | Step ended in failure |
| `cancelled` | Step cancelled |

**`item_upholstery`**

| Value | Meaning |
|-------|---------|
| `missing_quantity` | Required quantity not yet available |
| `available` | Stock confirmed available |
| `needs_ordering` | Must be ordered externally |
| `ordered` | Purchase order placed |
| `in_use` | Currently being consumed in the task |
| `completed` | Requirement fulfilled |
| `failed` | Requirement could not be fulfilled |

### Condition schema reference

```json
{
  "type": "state",
  "op": "eq" | "in" | "not_in",
  "value": "<string>" | ["<string>", "..."]
}
```

A pin with no conditions (`null` or `[]`) fires on every event for that entity. Multiple conditions in the array are evaluated with AND semantics.

## Validation notes

- Backend validation run: see `SUMMARY_PLAN_pin_notification_batch_20260620`.
- Suggested frontend validation: Open a task view, batch-create pins for task, steps, and item upholstery records, reload via `GET /pins?major_client_entity_ids=<task_id>`, edit one pin with `PATCH`, then batch-delete by major entity.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_pin_notification_batch_20260620.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_batch_20260620.md`
- Related debug plan (optional): _none_
