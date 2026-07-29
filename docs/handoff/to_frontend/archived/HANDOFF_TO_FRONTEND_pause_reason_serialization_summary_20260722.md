# HANDOFF_TO_FRONTEND_pause_reason_serialization_summary_20260722

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pause_reason_serialization_summary_20260722`
- Created at (UTC): `2026-07-22T21:40:00Z`
- Owner agent: `claude`
- Status: **implemented**
- Source plan: `PLAN_custom_pause_reasons_20260722`

## TL;DR

Quick index of every endpoint whose contract changed because of the pause-reasons migration. Use
this to figure out what your app actually touches before diving into the detailed docs linked at
the bottom — each row has enough info to know if it affects you.

## Endpoints that must change in the frontend

| Endpoint | What changed |
|---|---|
| `POST /api/v1/tasks/{task_id}/steps/{step_id}/transition` | Request: send `pause_reason_id` (a `pause_reasons` client id), not `reason` (enum string). Response: `last_state_record.pause_reason_id` → `last_state_record.pause_reason` (nested object). New validation: 404 if invalid id, 400 if the chosen reason requires a description and none was sent. |
| `POST /api/v1/tasks/steps/transition-batch` | Same request/response change as above. |
| `GET /api/v1/tasks/{task_id}` | `steps[].latest_state_records.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/tasks/{task_id}/steps` | `steps_pagination.items[].latest_state_records.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/working-sections/{working_section_id}/steps` | each item's `last_state_record.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/working-sections/steps/user-last-active` | `last_state_record.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/worker-stats/last-interacted-steps` | each item's `last_state_record.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/task-step-acknowledgments/pending` | each item's `last_state_record.pause_reason_id` → `.pause_reason` (nested object). |
| `GET /api/v1/worker-stats/{user_id}/linear-timeline` | `timeline.pause_by_reason` keys and `segments[].reason` are now opaque `pause_reason_id`s (were enum strings) — resolve via the new sibling `pause_reasons` lookup map in the same response. Separately, `segments[].steps[].reason` was renamed to `.pause_reason` and is a full nested object (different pattern from the line above — see gotcha below). |
| `GET /api/v1/worker-stats/linear-timeline` (roster) | Same `pause_by_reason` key + lookup-map change as above. No `steps[]` here, so no nested-object concern. |

The nested `pause_reason` object shape (used everywhere above except the lookup maps) is:
```json
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
```
It's `null` when the record has no reason. The lookup-map shape (analytics only) is trimmed:
`{ "par_01...": { "name": ..., "image_url": ..., "pause_type": ... } }`.

## ⚠️ The one gotcha

`GET /api/v1/worker-stats/{user_id}/linear-timeline` uses **both patterns in the same response**:
segment-level `reason` stays a flat id (resolve via the lookup map), but each step inside
`segments[].steps[]` is the new nested object. Don't assume the whole response follows one rule.

## New endpoints (not a breaking change — opt-in)

`PUT` / `GET` / `PATCH` / `DELETE /api/v1/pause-reasons` — full CRUD for managing pause reasons
themselves (the picker's data source). See the CRUD handoff for the request/response shapes and
role requirements.

## Detailed docs, if you need them

- `HANDOFF_TO_FRONTEND_pause_reasons_crud_20260722.md` — the CRUD endpoints and object shape.
- `HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` — transition request/
  response details, validation errors, and the paused-vs-ended_shift picker-sheet guidance.
- `HANDOFF_TO_FRONTEND_pause_reason_nested_in_step_state_records_20260722.md` — full detail on the
  nested-object change across the 7 read endpoints above.
- `HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_20260722.md` — full detail on the two
  linear-timeline endpoints, including the `"unspecified"` sentinel key.
