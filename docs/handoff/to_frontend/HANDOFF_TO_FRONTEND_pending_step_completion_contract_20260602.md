# HANDOFF_TO_FRONTEND_pending_step_completion_contract_20260602

## Metadata

- Handoff ID: HANDOFF_TO_FRONTEND_pending_step_completion_contract_20260602
- Created at (UTC): 2026-06-02T08:10:47Z
- Owner agent: copilot
- Source plan: backend/docs/architecture/archives/implementation/PLAN_pending_step_completion_20260602.md
- Source summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pending_step_completion_20260602.md

## Backend delivery context

- What backend implemented:
  - Step transition to completed is no longer applied immediately.
  - Backend now creates a delayed scheduler intent with an undo window.
  - A background worker finalizes the completion after the delay if not canceled.
  - A new cancel endpoint was added for the pending completion intent.
- API or contract changes:
  - Response shape for POST transition when new_state=completed changed to a pending intent payload.
  - New DELETE endpoint for canceling pending completion.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Handle dual success shapes on POST transition:
   - For new_state=completed: pending completion response.
   - For other states: existing immediate transition response.
2. Show undo UI based on expires_at when completed is requested.
3. Call DELETE pending-completion during undo window.
4. If cancel returns conflict, treat undo as expired and refresh task/step state.
5. Keep websocket listeners active for task:step-state-changed and task:state-changed to reflect worker-finalized completion.

## Interface details

### 1) Request completion (scheduled, not immediate)

- Method: POST
- Path: /api/v1/tasks/{task_id}/steps/{step_id}/transition
- Auth roles: admin, manager, worker

Request body example:

{
  "new_state": "completed",
  "credited_user_id": "usr_01ABC...",
  "reason": "pause_meeting",
  "description": "Done"
}

Success response shape for new_state=completed:

{
  "ok": true,
  "warnings": [],
  "data": {
    "pending_completion_id": "dsch_01...",
    "expires_at": "2026-06-02T08:11:12.123456+00:00"
  }
}

Important behavior:

- Step state remains working during the pending window.
- This is an intent acknowledgment, not a completed write.
- Effective finalization timing is scheduler-driven (configured poll interval), so do not assume exact wall-clock 5.0s completion.

Existing success response shape remains unchanged for non-completed transitions:

{
  "ok": true,
  "warnings": [],
  "data": {
    "step_id": "stp_...",
    "new_state": "working",
    "last_state_record": {
      "client_id": "ssr_...",
      "state": "working",
      "reason": null,
      "description": null,
      "entered_at": "2026-06-02T08:10:00+00:00",
      "exited_at": null,
      "created_by_id": "usr_..."
    }
  }
}

### 2) Cancel pending completion

- Method: DELETE
- Path: /api/v1/tasks/{task_id}/steps/{step_id}/pending-completion
- Auth roles: admin, manager, worker

Success response shape:

{
  "ok": true,
  "warnings": [],
  "data": {
    "cancelled": true
  }
}

Conflict response shape (undo expired or no active pending intent):

{
  "ok": false,
  "error": "No active pending completion found for this step. The undo window may have expired."
}

### 3) Scheduled finalization events (worker)

When pending completion is not canceled and finalization runs, frontend should expect realtime updates:

- task:step-state-changed
  - client_id: step id
  - extra.new_state: completed
- task:step-readiness-changed
  - emitted for dependent steps whose readiness changed
  - extra.new_readiness: new readiness value
- task:state-changed
  - emitted when task state changes as a side effect
  - extra.new_state: task state value

Notes:

- Analytics transition task is enqueued by worker finalization, not by the initial POST request for completed.
- Transition timing uses completion_requested_at in worker payload for entered/exited timestamps.

## Error cases

- POST transition with new_state=completed:
  - 404: task step not found
  - 404: task not found
  - 409: step terminal state
  - 409: A pending completion already exists for this step.
  - 400/422: request validation errors
- DELETE pending-completion:
  - 404: task step not found
  - 409: no active pending completion (already fired, canceled, or never created)

## Validation notes

- Backend validation run:
  - frontend/apps/managers-app/ManagerBeyo-app-managers: npm run typecheck passed
  - frontend/apps/workers-app/ManagerBeyo-app-workers: npm run typecheck passed
- Suggested frontend validation:
  - Request completed and verify pending response shape and undo UI.
  - Cancel within window and verify step remains working.
  - Let window expire and verify realtime transition to completed.
  - Try cancel after expiry and handle conflict response.

## Trace links

- Parent plan: backend/docs/architecture/archives/implementation/PLAN_pending_step_completion_20260602.md
- Parent summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pending_step_completion_20260602.md
- Related archive record: backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pending_step_completion_20260602.md
