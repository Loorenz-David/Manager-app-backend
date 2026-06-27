# HANDOFF_TO_FRONTEND_task_date_fields_20260625

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_date_fields_20260625`
- Created at (UTC): `2026-06-25T21:03:01Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_date_fields_20260625.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_task_date_fields_20260625.md`

## Backend delivery context

- What backend implemented: Added two focused task date update endpoints so the frontend can update `ready_by_at` separately from the schedule window.
- API or contract changes: New `PATCH /api/v1/tasks/{task_id}/ready-by-at` and `PATCH /api/v1/tasks/{task_id}/schedule` endpoints. Both return `client_id` only and emit normal `task:updated` realtime events.
- Feature flags/toggles (if any): None.

## Frontend action required

1. Use `PATCH /ready-by-at` when the user edits only the "ready by" date, instead of sending the broad task update payload.
2. Use `PATCH /schedule` when the user edits scheduled start and end together, including schedule clear flows.
3. Restrict these controls to frontend experiences where the acting user is `ADMIN` or `MANAGER`.
4. Handle terminal-task edit rejection cleanly: resolved, failed, and cancelled tasks should show a validation error and revert local optimistic state.

## Interface details

- Endpoint(s):
  - `PATCH /api/v1/tasks/{task_id}/ready-by-at`
  - `PATCH /api/v1/tasks/{task_id}/schedule`
- Request shape:
  - Ready-by: `{"ready_by_at": "2026-06-30T12:00:00Z"}` or `{"ready_by_at": null}`
  - Schedule: `{"scheduled_start_at": "2026-06-30T09:00:00Z", "scheduled_end_at": "2026-06-30T11:00:00Z"}`
  - Schedule clear: `{"scheduled_start_at": null, "scheduled_end_at": null}`
- Response shape:
  - `{"ok": true, "data": {"client_id": "tsk_..."}}`
- Error cases:
  - `403` for roles outside `ADMIN` and `MANAGER`
  - `404` when the task does not exist in the active workspace
  - `422` when trying to edit a terminal task
  - `422` for schedule payloads where both fields are non-null and `scheduled_end_at < scheduled_start_at`

## Validation notes

- Backend validation run: Unit tests for request parsing and router wiring passed; command integration tests are in place but could not be executed in this sandbox because local Postgres access is blocked.
- Suggested frontend validation:
  - Prevent obviously invalid schedule ranges before submit.
  - Allow explicit `null` sends for clearing `ready_by_at` or the whole schedule.
  - Treat the schedule editor as one atomic form because start and end are validated together on the backend.
  - Refresh or reconcile task detail state after a successful response if the screen also depends on realtime `task:updated` payloads elsewhere.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_task_date_fields_20260625.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_task_date_fields_20260625.md`
- Related debug plan (optional): none
