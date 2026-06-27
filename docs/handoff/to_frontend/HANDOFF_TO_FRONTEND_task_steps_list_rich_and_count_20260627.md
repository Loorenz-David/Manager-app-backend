# HANDOFF_TO_FRONTEND_task_steps_list_rich_and_count_20260627

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_steps_list_rich_and_count_20260627`
- Created at (UTC): `2026-06-27T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_steps_list_rich_and_count_20260627.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_steps_list_rich_and_count_20260627.md`

## Backend delivery context

- What backend implemented:
  - `GET /api/v1/tasks/{task_id}/steps` now returns the same rich step shape that `GET /api/v1/tasks/{task_id}` returns under `task_steps` — including `latest_state_records` and all aggregate metric fields. The previous compact shape (with live-joined `working_section_name` and `working_section_image`) is gone.
  - `GET /api/v1/tasks/{task_id}/steps/counts` is a new fast endpoint that returns the count of task steps grouped by state for a given task.
  - `GET /api/v1/tasks/{task_id}` itself is **unchanged** — its `task_steps` array already returned this rich shape since the aggregate-metrics plan (`HANDOFF_TO_FRONTEND_task_step_aggregate_metrics_20260621.md`).

- API or contract changes:
  - **Breaking — `GET /tasks/{task_id}/steps`**: `working_section_name` and `working_section_image` are removed. They are replaced by `working_section_name_snapshot` and (for images) no equivalent field exists — the working section image must be fetched separately if needed.
  - **Additive — `GET /tasks/{task_id}/steps`**: 13 new fields added per step item (see field reference below).
  - **New endpoint**: `GET /tasks/{task_id}/steps/counts`.

- Feature flags/toggles (if any): None.

## Frontend action required

1. **Update step list schema**: Remove `working_section_name` and `working_section_image` from the step model. Add the 13 new fields listed in the field reference below.
2. **Rename snapshot fields**: Replace any reads of `working_section_name` with `working_section_name_snapshot`. Replace reads of `assigned_worker_id` display with `assigned_worker_display_name_snapshot` (now available directly on the step).
3. **Handle `latest_state_records` as singular**: The key name is plural but the value is a single `object | null` (the most recent state record). Do not iterate it — read it as an optional object.
4. **Handle aggregate metrics zero-state**: All `total_*_seconds` and `total_*_count` fields default to `0`. `total_cost_minor` defaults to `null`. Display a neutral placeholder (`—`) when all are zero.
5. **Use the new counts endpoint for badges**: Call `GET /tasks/{task_id}/steps/counts` to render per-state step badges without fetching the full step list. All nine states are always present in the response (zero-count states are included as `0`, not omitted).
6. **Split socket event invalidation**: The step-related socket events (`task:step-created`, `task:step-deleted`, `task:step-state-changed`, etc.) previously only invalidated `GET /tasks/{task_id}`. They must now also invalidate `GET /tasks/{task_id}/steps` and `GET /tasks/{task_id}/steps/counts` as appropriate. See the Socket events section below for the full invalidation map per event.
7. **Superseded handoffs**: `HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md` is now stale — the step list shape it documented no longer applies. The `task_steps` section of `HANDOFF_TO_FRONTEND_tasks_items_upholstery_images_contracts_20260523.md` is also superseded by this document for all fields listed here.

## Interface details

---

### Endpoint 1 — Get task detail

`GET /api/v1/tasks/{task_id}`

- Auth: JWT required. Roles: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`.
- No query parameters.
- **This endpoint is unchanged.** It is included here because its `task_steps` shape now has a complete reference and supersedes the 2026-05-23 handoff for that key.

#### Response shape — `task_steps` array item

Each element of the `task_steps` array in the `GET /tasks/{task_id}` response has the shape below. All other top-level keys (`task`, `item`, `item_images`, `item_upholstery`, `requirements`, `unread_message_count`) are unchanged.

```jsonc
{
  "task_steps": [
    {
      "client_id": "tsp_abc123",
      "task_id": "tsk_xyz789",
      "state": "working",
      "readiness_status": "ready",
      "sequence_order": 1,
      "working_section_id": "wsec_def456",
      "assigned_worker_id": "usr_ghi012",
      "total_dependencies": 2,
      "completed_dependencies": 1,
      "working_section_name_snapshot": "Assembly",
      "assigned_worker_display_name_snapshot": "Jane Worker",
      "created_at": "2026-06-20T10:00:00+00:00",
      "closed_at": null,
      "ready_by_at": "2026-06-27T16:00:00+00:00",
      "total_working_seconds": 3600,
      "total_pause_seconds": 300,
      "total_ended_shift_seconds": 0,
      "total_working_count": 2,
      "total_pause_count": 1,
      "total_ended_shift_count": 0,
      "total_issues_count": 0,
      "total_issues_resolved_count": 0,
      "total_cost_minor": null,
      "latest_state_records": {
        "id": "ssr_jkl345",
        "step_id": "tsp_abc123",
        "state": "working",
        "reason": null,
        "entered_at": "2026-06-20T10:05:00+00:00",
        "exited_at": null,
        "created_at": "2026-06-20T10:05:00+00:00",
        "created_by_id": "usr_ghi012",
        "description": null,
        "accuracy": null,
        "accuracy_measured_by": null,
        "taken_from_average": false
      }
    }
  ]
}
```

---

### Endpoint 2 — List task steps (paginated)

`GET /api/v1/tasks/{task_id}/steps`

- Auth: JWT required. Roles: `ADMIN`, `MANAGER`, `WORKER`.

#### Request shape

Path parameter:

| Param | Type | Description |
|---|---|---|
| `task_id` | `string` | Client ID of the task (prefix `tsk`) |

Query parameters:

| Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | `integer` | `50` | `200` | Max steps per page |
| `offset` | `integer` | `0` | — | Steps to skip |

#### Response shape — success `200`

```jsonc
{
  "steps_pagination": {
    "items": [
      {
        "client_id": "tsp_abc123",
        "task_id": "tsk_xyz789",
        "state": "working",
        "readiness_status": "ready",
        "sequence_order": 1,
        "working_section_id": "wsec_def456",
        "assigned_worker_id": "usr_ghi012",
        "total_dependencies": 2,
        "completed_dependencies": 1,
        "working_section_name_snapshot": "Assembly",
        "assigned_worker_display_name_snapshot": "Jane Worker",
        "created_at": "2026-06-20T10:00:00+00:00",
        "closed_at": null,
        "ready_by_at": "2026-06-27T16:00:00+00:00",
        "total_working_seconds": 3600,
        "total_pause_seconds": 300,
        "total_ended_shift_seconds": 0,
        "total_working_count": 2,
        "total_pause_count": 1,
        "total_ended_shift_count": 0,
        "total_issues_count": 0,
        "total_issues_resolved_count": 0,
        "total_cost_minor": null,
        "latest_state_records": {
          "id": "ssr_jkl345",
          "step_id": "tsp_abc123",
          "state": "working",
          "reason": null,
          "entered_at": "2026-06-20T10:05:00+00:00",
          "exited_at": null,
          "created_at": "2026-06-20T10:05:00+00:00",
          "created_by_id": "usr_ghi012",
          "description": null,
          "accuracy": null,
          "accuracy_measured_by": null,
          "taken_from_average": false
        }
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Step field reference

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `string` | No | Step ID (prefix `tsp`) |
| `task_id` | `string` | No | Parent task ID (prefix `tsk`) |
| `state` | `string` (enum) | No | See state enum table below |
| `readiness_status` | `string` (enum) | No | `ready` · `partial` · `blocked` |
| `sequence_order` | `integer` | Yes | Display order within the task; `null` if unset |
| `working_section_id` | `string` | No | Working section ID (prefix `wsec`) |
| `assigned_worker_id` | `string` | Yes | User ID of assigned worker; `null` if unassigned |
| `total_dependencies` | `integer` | No | Total prerequisite steps |
| `completed_dependencies` | `integer` | No | Completed prerequisite steps |
| `working_section_name_snapshot` | `string` | Yes | Snapshotted name of the working section at step creation; `null` if not set |
| `assigned_worker_display_name_snapshot` | `string` | Yes | Snapshotted display name of the assigned worker; `null` if unassigned |
| `created_at` | `string` (ISO 8601) | No | Step creation timestamp |
| `closed_at` | `string` (ISO 8601) | Yes | When step reached a terminal state; `null` if active |
| `ready_by_at` | `string` (ISO 8601) | Yes | Step-level due date; `null` if not set |
| `total_working_seconds` | `integer` | No | Cumulative seconds in `working` state; `0` until analytics worker is live |
| `total_pause_seconds` | `integer` | No | Cumulative seconds in `paused` state |
| `total_ended_shift_seconds` | `integer` | No | Cumulative seconds in `ended_shift` state |
| `total_working_count` | `integer` | No | Number of `working` state entries |
| `total_pause_count` | `integer` | No | Number of `paused` state entries |
| `total_ended_shift_count` | `integer` | No | Number of `ended_shift` state entries |
| `total_issues_count` | `integer` | No | Issues linked to this step at completion |
| `total_issues_resolved_count` | `integer` | No | Resolved issues at completion |
| `total_cost_minor` | `integer` | Yes | Labour cost in minor currency units (e.g. cents); `null` when no salary profile is configured |
| `latest_state_records` | `object` | Yes | The most recent state record; `null` if no state transition has been recorded yet. **Value is a single object, not a list.** |

#### `latest_state_records` object field reference

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `string` | No | State record ID |
| `step_id` | `string` | No | Parent step ID |
| `state` | `string` (enum) | No | The state the step entered in this record |
| `reason` | `string` (enum) | Yes | Why this state was entered; `null` if not provided |
| `entered_at` | `string` (ISO 8601) | Yes | When this state was entered |
| `exited_at` | `string` (ISO 8601) | Yes | When this state was exited; `null` if still current |
| `created_at` | `string` (ISO 8601) | Yes | Record creation timestamp |
| `created_by_id` | `string` | Yes | User ID who created the record |
| `description` | `string` | Yes | Free-text description |
| `accuracy` | `number` | Yes | Accuracy value (model-dependent) |
| `accuracy_measured_by` | `string` (enum) | Yes | `user` · `ai` · `null` |
| `taken_from_average` | `boolean` | No | Whether timing was inferred from averages |

#### Step state enum

| Value | Meaning |
|---|---|
| `pending` | Not yet started |
| `working` | Actively being worked on |
| `paused` | Temporarily paused |
| `ended_shift` | Worker ended their shift mid-step |
| `blocked` | Waiting on an external dependency |
| `completed` | Successfully finished |
| `skipped` | Intentionally skipped |
| `failed` | Ended with failure |
| `cancelled` | Cancelled before completion |

#### Breaking changes vs previous handoff (`HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md`)

| Old field | Status | Replacement |
|---|---|---|
| `working_section_name` | **Removed** | Use `working_section_name_snapshot` |
| `working_section_image` | **Removed** | No equivalent on this endpoint; fetch via `GET /api/v1/images?entity_type=working_section&entity_client_id=...` if needed |

#### Pagination fields

| Field | Type | Description |
|---|---|---|
| `limit` | `integer` | The limit that was applied |
| `offset` | `integer` | The offset that was applied |
| `has_more` | `boolean` | `true` if more steps exist beyond this page |

#### Error cases

| HTTP status | When |
|---|---|
| `401 Unauthorized` | Missing or invalid JWT |
| `403 Forbidden` | Authenticated role not in `ADMIN`, `MANAGER`, `WORKER` |
| `404 Not Found` | `task_id` does not exist or belongs to a different workspace |

---

### Endpoint 3 — Count task steps by state

`GET /api/v1/tasks/{task_id}/steps/counts`

- Auth: JWT required. Roles: `ADMIN`, `MANAGER`, `WORKER`.
- No query parameters.

#### Request shape

Path parameter:

| Param | Type | Description |
|---|---|---|
| `task_id` | `string` | Client ID of the task (prefix `tsk`) |

#### Response shape — success `200`

All nine state keys are always present. States with no matching steps have count `0`.

```json
{
  "counts_by_state": {
    "pending": 3,
    "working": 1,
    "paused": 0,
    "ended_shift": 0,
    "blocked": 0,
    "completed": 5,
    "skipped": 0,
    "failed": 0,
    "cancelled": 0
  }
}
```

#### Field reference

| Field | Type | Description |
|---|---|---|
| `counts_by_state` | `object` | Map of step state value → count of non-deleted steps in that state for the given task |

All nine `TaskStepStateEnum` values are guaranteed to be present as keys. Values are non-negative integers.

#### Error cases

| HTTP status | When |
|---|---|
| `401 Unauthorized` | Missing or invalid JWT |
| `403 Forbidden` | Authenticated role not in `ADMIN`, `MANAGER`, `WORKER` |
| `404 Not Found` | `task_id` does not exist or belongs to a different workspace |

---

## Socket events

The frontend previously invalidated the full `GET /tasks/{task_id}` query in response to step socket events. With the introduction of `GET /tasks/{task_id}/steps` and `GET /tasks/{task_id}/steps/counts` as independent queries, event-driven cache invalidation must be split across all three queries.

All events are broadcast to the **workspace room** (all connected users in the workspace receive them).

---

### Event → query invalidation map

| Socket event | `GET /tasks/{task_id}` | `GET /tasks/{task_id}/steps` | `GET /tasks/{task_id}/steps/counts` |
|---|---|---|---|
| `task:step-created` | Invalidate (task state may have changed) | Invalidate (new step in list) | Invalidate (count increased) |
| `task:step-deleted` | Invalidate (task state may have reverted) | Invalidate (step removed from list) | Invalidate (count decreased) |
| `task:step-state-changed` | Invalidate (task state may have changed) | Invalidate (step state changed in list) | Invalidate (state distribution changed) |
| `task:step-readiness-changed` | — | Invalidate (readiness field changed on affected steps) | — |
| `task:step-updated` | — | Invalidate (field change, e.g. `ready_by_at`) | — |
| `task:step-assigned` | — | Invalidate (`assigned_worker_id` changed) | — |
| `task:state-changed` | Invalidate | — | — |
| `task:updated` | Invalidate | — | — |

> All events carry a `task_id`-scoped or `workspace_id`-scoped key. Always filter by the relevant `task_id` before invalidating.

---

### Event payloads

#### `task:step-created`
```jsonc
{
  "event_name": "task:step-created",
  "workspace_id": "wrk_xxx",
  "items": [
    { "client_id": "tsp_abc", "working_section_id": "wsec_def" }
  ]
}
```
Emitted after one or more steps are added to a task.

#### `task:step-deleted`
```jsonc
{
  "event_name": "task:step-deleted",
  "workspace_id": "wrk_xxx",
  "items": [
    { "client_id": "tsp_abc", "working_section_id": "wsec_def" }
  ]
}
```
Emitted after one or more steps are soft-deleted.

#### `task:step-state-changed`
```jsonc
{
  "event_name": "task:step-state-changed",
  "workspace_id": "wrk_xxx",
  "items": [
    { "client_id": "tsp_abc", "new_state": "completed" },
    { "client_id": "tsp_xyz", "new_state": "paused" }
  ]
}
```
Emitted on every state transition. Can include a second item when an auto-pause was applied to a sibling step (batch-working section constraint).

#### `task:step-readiness-changed`
```jsonc
// WorkspaceEvent shape (single step per event)
{
  "event_name": "task:step-readiness-changed",
  "client_id": "tsp_abc",
  "workspace_id": "wrk_xxx",
  "extra": { "new_readiness": "ready" }
}
```
Emitted for each step whose `readiness_status` changed as a side-effect of a dependency being resolved or removed. One event per affected step.

> **Note**: This event also arrives as a `BatchWorkspaceEvent` (array `items`) when emitted from the delete-step path. Both shapes should be handled: check for `items` array first, fall back to `client_id` + `extra`.

#### `task:step-updated`
```jsonc
{
  "event_name": "task:step-updated",
  "workspace_id": "wrk_xxx",
  "items": [
    { "client_id": "tsp_abc" }
  ]
}
```
Emitted when step fields are patched in bulk (currently only `ready_by_at`). Refetch the step list to get updated values.

#### `task:step-assigned`
```jsonc
{
  "event_name": "task:step-assigned",
  "client_id": "tsp_abc",
  "workspace_id": "wrk_xxx",
  "extra": { "user_id": "usr_worker" }
}
```
Emitted when a worker is assigned to a step. Invalidate the step list for the affected task.

#### `task:state-changed`
```jsonc
{
  "event_name": "task:state-changed",
  "client_id": "tsk_xyz",
  "workspace_id": "wrk_xxx",
  "extra": { "new_state": "completed" }
}
```
Emitted when a step operation causes the parent task to change state (e.g. last step completed → task resolved). Invalidate `GET /tasks/{task_id}`.

#### `task:updated`
```jsonc
{
  "event_name": "task:updated",
  "client_id": "tsk_xyz",
  "workspace_id": "wrk_xxx",
  "extra": {}
}
```
Structural change on the task (e.g. first step added → task moved from `pending` to `assigned`). Invalidate `GET /tasks/{task_id}`.

---

### Recommended query invalidation strategy

```
on workspace event received:
  switch event_name:

    case "task:step-created":
    case "task:step-deleted":
      invalidate GET /tasks/{task_id}          // task state may have changed
      invalidate GET /tasks/{task_id}/steps     // list membership changed
      invalidate GET /tasks/{task_id}/steps/counts  // counts changed

    case "task:step-state-changed":
      invalidate GET /tasks/{task_id}          // task state may have changed
      invalidate GET /tasks/{task_id}/steps     // step.state changed in list
      invalidate GET /tasks/{task_id}/steps/counts  // state distribution changed

    case "task:step-readiness-changed":
    case "task:step-updated":
    case "task:step-assigned":
      invalidate GET /tasks/{task_id}/steps     // step fields changed

    case "task:state-changed":
    case "task:updated":
      invalidate GET /tasks/{task_id}           // task-level fields changed
```

The `task_id` to invalidate is derived from the event:
- `BatchWorkspaceEvent` (`items` array): the frontend must already know which task is open, or use the step `client_id` to look up the owning task from local cache.
- `WorkspaceEvent` (`client_id`): for `task:state-changed` / `task:updated`, `client_id` is the task ID directly.

---

## Validation notes

- Backend validation run: static compilation verified; no automated test suite run.
- Suggested frontend validation:
  - **Step list**: Verify `steps_pagination.items[*].working_section_name_snapshot` is a string or null. Verify `steps_pagination.items[*].working_section_image` does not appear.
  - **Step list**: Verify `latest_state_records` is either `null` or an object with `id`, `state`, `entered_at` keys — not an array.
  - **Step list**: Verify `total_cost_minor` renders without crash when `null`.
  - **Counts**: Call with a task that has no `working` steps — verify `"working": 0` appears in the response (not absent).
  - **Counts**: Call with a non-existent `task_id` — verify `404` response.
  - Regression: `GET /tasks/{task_id}` `task_steps` shape unchanged.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_task_steps_list_rich_and_count_20260627.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_steps_list_rich_and_count_20260627.md`
- Correction plan: `backend/docs/architecture/under_construction/implementation/PLAN_task_steps_corrections_and_handoff_20260627.md`
- Supersedes (step list shape): `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md`
- Supersedes (get_task task_steps section): `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_tasks_items_upholstery_images_contracts_20260523.md` (section 1, `task_steps` key only)
- Related: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_step_aggregate_metrics_20260621.md`
