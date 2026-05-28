# HANDOFF_TO_FRONTEND_route_transition_step_state_contract_20260528

## Metadata

- Handoff ID: HANDOFF_TO_FRONTEND_route_transition_step_state_contract_20260528
- Created at (UTC): 2026-05-28T00:00:00Z
- Owner agent: GitHub Copilot (GPT-5.3-Codex)
- Source plan: N/A
- Source summary: N/A

## Backend delivery context

- What backend implemented:
  - Step state transition endpoint already implemented and active.
  - Transition is atomic and updates step/task state records plus async side effects.
  - Worker working-sections read endpoints implemented and active:
    - GET /api/v1/working-sections/me
    - GET /api/v1/working-sections/{working_section_id}/steps
- API or contract changes:
  - Added worker read contracts for home screen and section step drilldown.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Use this route to transition a task step state from allowed previous states only.
2. Read and handle validation/conflict errors as normal API errors.
3. Refresh task/step UI state after success (new state can imply readiness and task-level state changes).

## Interface details

### Endpoint

- Method: POST
- Path: /api/v1/tasks/{task_id}/steps/{step_id}/transition
- Router handler: route_transition_step_state
- Auth requirement: role must be one of admin, manager, worker.

### Request payload

Body fields:

- new_state: required enum
  - Allowed values: pending, working, paused, ended_shift, blocked, completed, skipped, failed, cancelled
  - Note: command-side transition graph only allows a subset of transitions (see Transition Rules below).
- credited_user_id: optional string
  - Used for analytics payload credit attribution.
  - If omitted, backend uses authenticated user id.
- reason: optional enum
  - Allowed values:
    - waiting_for_upholstery
    - pause_lunch_break
    - pause_coffee_break
    - pause_ended_shift
    - pause_meeting
    - pause_other_task_priority
- description: optional string

Example:

{
  "new_state": "working",
  "credited_user_id": "usr_01ABC...",
  "reason": "pause_meeting",
  "description": "Resuming after sync"
}

### Success response

HTTP 200:

{
  "ok": true,
  "warnings": [],
  "data": {
    "step_id": "stp_...",
    "new_state": "working"
  }
}

### Error response

Shape:

{
  "ok": false,
  "error": "..."
}

Common errors:

- 404: Task step not found.
- 404: Task not found.
- 409: Step is in terminal state ... no further transitions allowed.
- 409: No open state record found for this step.
- 400: Cannot transition step from X to Y.
- 422: Pydantic validation errors for malformed body.

## Additional interface details (newly implemented worker routes)

### Endpoint A

- Method: GET
- Path: /api/v1/working-sections/me
- Router handler: get_worker_working_sections_route
- Auth requirement: role must be one of admin, manager, worker.

### Endpoint A query params

- today_start: optional ISO 8601 timestamp string
  - Example: 2026-05-28T06:00:00Z
  - Used only for terminal-state counting window in response.

### Endpoint A success response

HTTP 200:

{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [
      {
        "client_id": "wsec_...",
        "name": "Upholstery",
        "image": "https://.../section.png",
        "task_steps_counts": {
          "pending": 3,
          "working": 2,
          "paused": 1,
          "ended_shift": 0,
          "blocked": 0,
          "completed": 4,
          "skipped": 0,
          "failed": 1
        }
      }
    ]
  }
}

Count behavior:

- Active states (pending, working, paused, ended_shift, blocked): total counts.
- Terminal states (completed, skipped, failed): only steps whose latest state record entered_at >= today_start.

### Endpoint A error response

Shape:

{
  "ok": false,
  "error": "..."
}

Common errors:

- 422: today_start must be a valid ISO 8601 timestamp.

### Endpoint B

- Method: GET
- Path: /api/v1/working-sections/{working_section_id}/steps
- Router handler: list_working_section_steps_route
- Auth requirement: role must be one of admin, manager, worker.

### Endpoint B path and query params

- working_section_id: required path param string
- q: optional string
  - Always filters by item.article_number ILIKE and item.sku ILIKE.
  - If upholstery_search=true, also filters by item_upholstery.name ILIKE and item_upholstery.code ILIKE.
- upholstery_search: optional boolean, default false
- limit: optional int, default 50, max 200
- offset: optional int, default 0

### Endpoint B success response

HTTP 200:

{
  "ok": true,
  "warnings": [],
  "data": {
    "steps_pagination": {
      "items": [
        {
          "client_id": "tsp_...",
          "task_id": "tsk_...",
          "state": "working",
          "readiness_status": "ready",
          "sequence_order": 1,
          "working_section_id": "wsec_...",
          "assigned_worker_id": "usr_...",
          "total_dependencies": 0,
          "completed_dependencies": 0,
          "working_section_name_snapshot": "Upholstery",
          "assigned_worker_display_name_snapshot": "Sophia",
          "created_at": "2026-05-28T09:15:00+00:00",
          "closed_at": null,
          "updated_at": "2026-05-28T10:30:00+00:00",
          "created_by": {
            "client_id": "usr_...",
            "username": "sophia_morris",
            "profile_picture": null
          },
          "updated_by": {
            "client_id": "usr_...",
            "username": "manager_john",
            "profile_picture": null
          },
          "last_state_record": {
            "state": "working",
            "entered_at": "2026-05-28T09:15:00+00:00",
            "exited_at": null
          },
          "task": {
            "client_id": "tsk_...",
            "task_type": "return",
            "priority": "normal",
            "state": "working",
            "return_source": "after_purchase",
            "item_location": "store",
            "ready_by_at": null,
            "return_method": "pickup"
          },
          "item": {
            "client_id": "itm_...",
            "article_number": "ART-001",
            "sku": "SKU-001",
            "state": "pending",
            "item_category_id": "icat_...",
            "quantity": 1,
            "item_position": null,
            "upholstery_requirement": [
              {
                "client_id": "iur_...",
                "item_upholstery_id": "iup_...",
                "state": "available",
                "source": "internal",
                "amount_meters": 2.5
              }
            ]
          },
          "item_images": [
            {
              "client_id": "img_...",
              "image_url": "https://...",
              "storage_provider": "s3",
              "source_type": "upload",
              "source_reference": null,
              "width_px": 1200,
              "height_px": 900,
              "file_size_bytes": 123456,
              "created_at": "2026-05-28T09:00:00+00:00",
              "last_event": null,
              "events": [],
              "image_annotation": null
            }
          ]
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}

item_images serialization behavior:

- First image in display order is serialized with full image shape.
- Remaining images are serialized with light image shape.
- Light image shape fields: client_id, image_url, width_px, height_px, file_size_bytes.

item and upholstery_requirement empty-state behavior:

- If item exists but has no upholstery requirements, item.upholstery_requirement returns an empty array [].
- If the step has no resolvable primary item, item returns null and item_images returns [].

### Endpoint B error response

Shape:

{
  "ok": false,
  "error": "..."
}

Common errors:

- 404: Working section not found.

## Transition rules (important for FE UX)

Current state to allowed next states:

- pending -> working
- working -> paused, ended_shift, completed, failed, cancelled
- paused -> working, ended_shift, failed, cancelled
- ended_shift -> working, failed, cancelled
- completed -> none
- skipped -> none
- failed -> none
- cancelled -> none
- blocked -> none

Terminal step states:

- completed
- skipped
- failed
- cancelled

Any transition attempt from terminal state is rejected.

## Internal side effects (service logic)

When transition succeeds, backend performs all of the following in one atomic transaction:

1. Resolve step by workspace + task_id + step_id, and ensure step is not deleted.
2. Validate transition graph and terminal restrictions.
3. Resolve task by workspace + task id.
4. Close current open step state record (set exited_at).
5. Create new step state record with entered_at now and optional reason/description.
6. Update step:
   - state = new_state
   - latest_state_record_id -> new record
   - updated_at, updated_by_id
   - closed_at when new_state is terminal
7. Task state side effects:
   - If step moves to working and task is assigned, task becomes working.
   - If step moves to completed:
     - increments completed_dependencies on dependent steps
     - recalculates dependent step readiness
     - if all non-deleted steps are terminal and task is not terminal, task becomes ready
8. Enqueue async processing task (execution system):
   - task_type: process_step_transition
   - payload includes closing/new state, actor, credited user, section snapshots, timing
9. Notification side effect:
   - finds pinned users for this task_step
   - excludes acting user
   - enqueues create_notifications task with notification_type task_step_state_changed

After commit, backend dispatches websocket/event-bus events:

- task:step-state-changed (always)
- task:step-readiness-changed (for each dependent step whose readiness changed)
- task:state-changed (if task state changed)

## Frontend implications

- Do not assume only the target step changes. A successful transition can also change:
  - dependent step readiness statuses
  - parent task state
  - notification badges/feeds (async)
- For best UX consistency after success:
  - refresh task detail payload
  - refresh task flow records if shown
  - optionally re-fetch list if task state filters are active

## Trace links

- Router endpoint: backend/app/beyo_manager/routers/api_v1/tasks.py
- Command: backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py
- Request parser: backend/app/beyo_manager/services/commands/task_steps/requests/__init__.py
- Response wrapper: backend/app/beyo_manager/routers/http/response.py
