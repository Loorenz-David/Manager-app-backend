# HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_list_task_steps_by_task_20260620.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_list_task_steps_by_task_20260620.md`

## Backend delivery context

- What backend implemented: New read-only endpoint that returns all task steps belonging to a specific task, each enriched with the name and image of its working section.
- API or contract changes: New `GET` route added to the tasks router at `/{task_id}/steps`. No existing routes modified.
- Feature flags/toggles (if any): None.

## Frontend action required

1. Call `GET /tasks/{task_id}/steps` (with optional `limit` / `offset` query params) wherever the UI needs to display the step list for a task.
2. Handle the `404` error case — show a suitable empty or error state when the task no longer exists.
3. Use `steps_pagination.has_more` to decide whether to show a "load more" / pagination control.

## Interface details

- Endpoint: `GET /tasks/{task_id}/steps`
- Auth: JWT required. Allowed roles: `ADMIN`, `MANAGER`, `WORKER`.

### Request shape

Path parameter:
| Param | Type | Description |
|---|---|---|
| `task_id` | `string` | Client ID of the task (prefix `tsk`) |

Query parameters:
| Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | `integer` | `50` | `200` | Max steps per page |
| `offset` | `integer` | `0` | — | Number of steps to skip |

### Response shape — success `200`

```json
{
  "steps_pagination": {
    "items": [
      {
        "client_id": "tsp_abc123",
        "task_id": "tsk_xyz789",
        "state": "pending",
        "readiness_status": "ready",
        "sequence_order": 1,
        "working_section_id": "wsec_def456",
        "assigned_worker_id": "usr_ghi012",
        "total_dependencies": 2,
        "completed_dependencies": 1,
        "working_section_name": "Assembly",
        "working_section_image": "https://cdn.example.com/assembly.png",
        "created_at": "2026-06-18T10:00:00+00:00",
        "closed_at": null
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Field reference

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `string` | No | Step ID (prefix `tsp`) |
| `task_id` | `string` | No | Parent task ID (prefix `tsk`) |
| `state` | `string` (enum) | No | `pending` · `working` · `paused` · `ended_shift` · `blocked` · `completed` · `skipped` · `failed` · `cancelled` |
| `readiness_status` | `string` (enum) | No | `ready` · `partial` · `blocked` |
| `sequence_order` | `integer` | Yes | Display order within the task; `null` if unset |
| `working_section_id` | `string` | No | ID of the working section this step belongs to (prefix `wsec`) |
| `assigned_worker_id` | `string` | Yes | User ID of the assigned worker; `null` if unassigned |
| `total_dependencies` | `integer` | No | How many prerequisite steps this step has |
| `completed_dependencies` | `integer` | No | How many of those prerequisites are done |
| `working_section_name` | `string` | Yes | Display name of the working section; `null` only on data integrity issue |
| `working_section_image` | `string` (URL) | Yes | Image URL for the working section; `null` if none set |
| `created_at` | `string` (ISO 8601) | No | When the step was created |
| `closed_at` | `string` (ISO 8601) | Yes | When the step reached a terminal state; `null` if still active |

#### Pagination fields

| Field | Type | Description |
|---|---|---|
| `limit` | `integer` | The limit that was applied |
| `offset` | `integer` | The offset that was applied |
| `has_more` | `boolean` | `true` if there are more steps beyond this page |

### Error cases

| HTTP status | When |
|---|---|
| `401 Unauthorized` | Missing or invalid JWT |
| `403 Forbidden` | Authenticated user does not have `ADMIN`, `MANAGER`, or `WORKER` role |
| `404 Not Found` | `task_id` does not exist or belongs to a different workspace |

## Validation notes

- Backend validation run: endpoint should be manually exercised against a task with known steps, with `limit=1` to confirm `has_more: true`, and again with an invalid `task_id` to confirm `404`.
- Suggested frontend validation:
  - Guard rendering on `steps_pagination.items` being an array (never `undefined`).
  - Treat `working_section_name: null` and `working_section_image: null` gracefully — render a fallback icon/label.
  - `readiness_status === "blocked"` should surface a visual indicator (step cannot start).
  - `completed_dependencies < total_dependencies` means dependencies are still pending — surface this in the UI alongside `readiness_status`.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_list_task_steps_by_task_20260620.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_list_task_steps_by_task_20260620.md`
- Related debug plan (optional): `—`
