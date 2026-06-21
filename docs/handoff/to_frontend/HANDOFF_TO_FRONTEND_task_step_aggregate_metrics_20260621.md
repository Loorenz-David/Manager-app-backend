# HANDOFF_TO_FRONTEND_task_step_aggregate_metrics_20260621

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_step_aggregate_metrics_20260621`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_task_step_aggregate_metrics_20260621.md`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - Added 9 aggregate metric fields to `serialize_step`, the shared serializer used by both `get_user_last_active_step_record` and `list_working_section_steps`.
  - The new fields are additive — no existing key was removed or renamed.
  - The fields are populated by the analytics worker (`PROCESS_STEP_TRANSITION` handler). **Until the worker plan is implemented, all time/count fields will be `0` and `total_cost_minor` will be `null` for all steps.** The serializer change ships first; the worker backfill follows as a separate plan.

- API or contract changes:
  - Both endpoints now return 9 additional keys on every step object. No request shape changes.

- Feature flags/toggles: none

## Frontend action required

1. Consume the new aggregate metric fields when displaying step detail cards — working time, pause time, and issue counts are now available directly on the step object without a separate request.
2. Handle `total_cost_minor` as nullable (`null` when no salary profile is configured for the assigned worker).
3. Note that values will be `0` / `null` for all existing steps until the analytics worker that populates these columns is deployed. Plan for a zero-state display (e.g. "—" instead of "0s").

## Interface details

Both endpoints expose the same step object shape. The 9 new keys are present on every step item in both responses.

---

### Endpoint 1 — User's last active step

- `GET /api/v1/working-sections/steps/user-last-active`
- Roles: `ADMIN`, `MANAGER`, `WORKER`
- No request parameters.

#### Response shape

```jsonc
{
  "user_last_active_step_record": {
    // — existing fields (unchanged) —
    "client_id": "tsp_...",
    "task_id": "tsk_...",
    "state": "working",
    "readiness_status": "ready",
    "sequence_order": null,
    "working_section_id": "ws_...",
    "assigned_worker_id": "usr_...",
    "total_dependencies": 0,
    "completed_dependencies": 0,
    "working_section_name_snapshot": "Upholstery",
    "assigned_worker_display_name_snapshot": "jane.doe",
    "created_at": "2026-05-01T08:00:00+00:00",
    "closed_at": null,

    // — NEW aggregate metric fields —
    "total_working_seconds": 3600,      // sum of all WORKING intervals in seconds; 0 until worker is live
    "total_pause_seconds": 300,         // sum of all PAUSED intervals in seconds; 0 until worker is live
    "total_ended_shift_seconds": 0,     // sum of all ENDED_SHIFT intervals in seconds; 0 until worker is live
    "total_working_count": 2,           // number of times step entered WORKING state
    "total_pause_count": 1,             // number of times step entered PAUSED state
    "total_ended_shift_count": 0,       // number of times step entered ENDED_SHIFT state
    "total_issues_count": 3,            // total issues linked to this step at completion time
    "total_issues_resolved_count": 3,   // resolved issues at completion time
    "total_cost_minor": 4500,           // labour cost in minor currency units (cents); null if no salary profile

    // — per-service extra fields (unchanged) —
    "updated_at": "2026-06-20T10:00:00+00:00",
    "created_by": { "client_id": "...", "username": "...", "profile_picture": null },
    "updated_by": { "client_id": "...", "username": "...", "profile_picture": null },
    "last_state_record": {
      "state": "working",
      "entered_at": "2026-06-21T08:00:00+00:00",
      "exited_at": null,
      "last_action_by": { "client_id": "...", "username": "...", "profile_picture": null },
      "first_started_at": "2026-05-01T07:30:00+00:00"
    },
    "task": { "client_id": "...", "task_type": "...", "priority": "...", "state": "...", "return_source": null, "item_location": null, "ready_by_at": null, "return_method": null },
    "item": { /* serialize_item_worker_light shape */ },
    "item_images": [],
    "cases_summary": { "total_unread": 0 }
  }
}
```

When no active step is found for the user:
```json
{ "user_last_active_step_record": null }
```

---

### Endpoint 2 — Working section step list

- `GET /api/v1/working-sections/{working_section_id}/steps`
- Roles: `ADMIN`, `MANAGER`, `WORKER`

#### Request parameters (unchanged)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | `string \| null` | `null` | Free-text search on item `article_number` / `sku` |
| `upholstery_search` | `boolean` | `false` | Extend `q` to also match upholstery `name` / `code` |
| `item_major_category` | `string \| null` | `null` | Comma-separated major category snapshots to filter by |
| `record_step_state` | `string \| null` | `null` | Comma-separated step state values to filter by (e.g. `working,paused`) |
| `limit` | `integer` | `50` | Max `200` |
| `offset` | `integer` | `0` | Pagination offset |

#### Response shape

```jsonc
{
  "steps_pagination": {
    "items": [
      {
        // — existing fields (unchanged) —
        "client_id": "tsp_...",
        "task_id": "tsk_...",
        "state": "working",
        "readiness_status": "ready",
        "sequence_order": null,
        "working_section_id": "ws_...",
        "assigned_worker_id": "usr_...",
        "total_dependencies": 1,
        "completed_dependencies": 0,
        "working_section_name_snapshot": "Upholstery",
        "assigned_worker_display_name_snapshot": "jane.doe",
        "created_at": "2026-05-01T08:00:00+00:00",
        "closed_at": null,

        // — NEW aggregate metric fields —
        "total_working_seconds": 3600,
        "total_pause_seconds": 300,
        "total_ended_shift_seconds": 0,
        "total_working_count": 2,
        "total_pause_count": 1,
        "total_ended_shift_count": 0,
        "total_issues_count": 0,
        "total_issues_resolved_count": 0,
        "total_cost_minor": null,

        // — per-service extra fields (unchanged) —
        "updated_at": "2026-06-20T10:00:00+00:00",
        "created_by": { "client_id": "...", "username": "...", "profile_picture": null },
        "updated_by": null,
        "last_state_record": {
          "state": "working",
          "entered_at": "2026-06-21T08:00:00+00:00",
          "exited_at": null,
          "last_action_by": { "client_id": "...", "username": "...", "profile_picture": null },
          "first_started_at": "2026-05-01T07:30:00+00:00"
        },
        "task": { "client_id": "...", "task_type": "...", "priority": "...", "state": "...", "return_source": null, "item_location": null, "ready_by_at": null, "return_method": null },
        "item": { /* serialize_item_worker_light shape */ },
        "item_images": [],
        "cases_summary": { "total_unread": 0 },
        "dependency_working_sections": [
          {
            "working_section": { "client_id": "ws_...", "name": "Sewing", "image": null, "order_list": 1 },
            "prerequisite_step_state": "completed"
          }
        ]
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

## New field reference

The following 9 fields are now present on every step object returned by both endpoints. All are sourced from the `task_steps` table columns inherited from the aggregate metric mixins.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `total_working_seconds` | `integer` | No | Cumulative seconds the step spent in `WORKING` state across all intervals |
| `total_pause_seconds` | `integer` | No | Cumulative seconds the step spent in `PAUSED` state |
| `total_ended_shift_seconds` | `integer` | No | Cumulative seconds the step spent in `ENDED_SHIFT` state |
| `total_working_count` | `integer` | No | Number of `WORKING` state intervals recorded |
| `total_pause_count` | `integer` | No | Number of `PAUSE` state intervals recorded |
| `total_ended_shift_count` | `integer` | No | Number of `ENDED_SHIFT` state intervals recorded |
| `total_issues_count` | `integer` | No | Number of issues linked to this step at the time of completion |
| `total_issues_resolved_count` | `integer` | No | Number of those issues that were resolved |
| `total_cost_minor` | `integer \| null` | Yes | Cumulative labour cost in minor currency units (e.g. cents); `null` when no hourly rate is configured for the credited worker |

**Zero-state note:** All non-nullable integer fields default to `0`. `total_cost_minor` defaults to `null`. These values reflect the state on the `task_steps` row; they are updated asynchronously by the analytics worker after each state transition. Steps that pre-date the worker going live will retain `0` / `null` until they receive a new transition.

## Error cases

| Status | Endpoint | Condition |
|---|---|---|
| `404` | `list_working_section_steps` | `working_section_id` not found or not in workspace |
| `200` with `null` body key | `get_user_last_active_step_record` | No active step found for the current user |

## Validation notes

- Backend validation run: serializer change applied and reviewed; no automated test run against the new keys.
- Suggested frontend validation:
  - Verify all 9 new keys are present on a step object from both endpoints.
  - Verify `total_cost_minor: null` renders without crashing (missing salary profile case).
  - Display `0` values gracefully — steps that have never transitioned will have all-zero counters.
  - Confirm no regression on existing fields (`state`, `last_state_record`, `dependency_working_sections`, etc.).

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_task_step_aggregate_metrics_20260621.md`
- Parent summary: `—`
- Related handoff: [HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md](HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md)
- Related handoff: [HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md](HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md)
