# HANDOFF_TO_FRONTEND_batch_step_transition_20260623

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_batch_step_transition_20260623`
- Created at (UTC): `2026-06-23T12:10:00Z`
- Owner agent: `claude-opus-4-8`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_step_transition_20260623.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_step_transition_20260623.md`

## Backend delivery context

- What backend implemented:
  - A new workspace-scoped endpoint to transition **1..N batch-capable** task steps to a single target state in one atomic call.
  - The existing single-step transition endpoint is unchanged.
- API or contract changes:
  - New: `POST /api/v1/tasks/steps/transition-batch`.
  - Existing `POST /api/v1/tasks/{task_id}/steps/{step_id}/transition` is untouched (still the path for individual / non-batch steps).
- Feature flags/toggles (if any):
  - None. Only steps whose working section has `allows_batch_working = true` are accepted by the batch endpoint.

## Frontend action required

1. For the batch buttons on batch-capable sections (`pending→working`, `working→paused`, `paused→working`, `working→completed`), call the new `POST /api/v1/tasks/steps/transition-batch` with the whole active batch group.
2. Handle the **atomic all-or-nothing** behavior: if any step can't transition, the call fails and **nothing** changes — surface the per-step error message and refetch.
3. Keep using the single endpoint for individual (non-batch) steps; the batch endpoint rejects non-batch steps.
4. Expect a **single** `task:step-state-changed` realtime event carrying all changed steps (do not expect one event per step).

## Interface details

- Common success envelope: `{ ok: true, data: <payload>, warnings: [] }`
- Common error envelope: `{ ok: false, error: <message> }`
- Auth roles: `admin`, `manager`, `worker`

### Request — `POST /api/v1/tasks/steps/transition-batch`

```json
{
  "items": [
    { "task_id": "tsk_01", "step_id": "tsp_07", "mark_closing_record_inaccurate": true },
    { "task_id": "tsk_01", "step_id": "tsp_05" },
    { "task_id": "tsk_02", "step_id": "tsp_03" }
  ],
  "new_state": "completed",
  "reason": null,
  "description": null
}
```

- `items`: 1..100 entries; each is a `{ task_id, step_id, mark_closing_record_inaccurate? }` object. Steps may span **different tasks**. Duplicate `step_id`s are rejected.
- `mark_closing_record_inaccurate` (optional, **per-item**, default `false`): when `true`, the step's closing record is flagged as having an inaccurate recorded time (and, when `new_state` is `completed`, the newly opened completed record too). Set it only on the specific steps whose recorded time was wrong. Most relevant on the `working → completed` flow.
- `new_state`: one of `working`, `paused`, `ended_shift`, `completed`, `failed`, `cancelled` (the four button flows use `working`, `paused`, `completed`). One state applies to all items; each step's *current* state must legally allow that transition.
- `reason`, `description`: optional, shared across the batch.
- Not supported in v1: per-item `credited_user_id` and per-item `new_state` (the batch credits the calling user; one state per request).

### Success response

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "step_id": "tsp_07",
        "new_state": "working",
        "last_state_record": {
          "state": "working",
          "entered_at": "2026-06-23T12:00:00+00:00",
          "exited_at": null,
          "last_action_by": null,
          "first_started_at": "2026-06-23T11:00:00+00:00"
        }
      }
    ]
  },
  "warnings": []
}
```

- `data.items` has one entry per requested step, each with its new state and freshly opened `last_state_record`.

### Allowed transitions (per step's current state)

- `pending → working`
- `working → paused | ended_shift | completed | failed | cancelled`
- `paused → working | ended_shift | failed | cancelled`
- `ended_shift → working | failed | cancelled`

### Error cases (atomic — whole batch rejected, nothing mutated)

- `400`-style validation error (`{ ok: false, error: "Batch transition rejected — <step_id>: <reason>; ..." }`) when any item:
  - is not found, or its `step_id` does not belong to the provided `task_id`,
  - is not batch-capable (`allows_batch_working = false`),
  - is in a terminal state, or the requested `new_state` is not a legal transition from its current state,
  - has no open state record.
- Request validation errors: empty `items`, more than 100 `items`, or duplicate `step_id`s.

### Realtime + notifications (coalesced)

- One `task:step-state-changed` `BatchWorkspaceEvent` is broadcast to the workspace with an `items` array of `{ client_id, new_state }` for every changed step (and any auto-paused step, though auto-pause does not occur for batch steps).
- One `task:state-changed` event per *distinct* task whose state changed as a side effect (e.g. a task becoming `working` on first start, or `ready` once all its steps are terminal).
- Notifications are **coalesced**: step watchers receive a single "N steps changed" notification instead of one per step; task-state notifications fire once per changed task. (Copy differs from the single-step per-step notification by design.)

## Validation notes

- Backend validation run:
  - `python -m compileall beyo_manager`: clean.
  - `pytest tests/integration/services/commands/task_steps tests/unit/services/commands/task_steps`: 25 passed (includes the four batch transitions, cross-task batch, atomic rejection, non-batch rejection, single coalesced event, task→ready, and the request validator).
- Suggested frontend validation:
  - Batch-start several steps in a batch section → all become `working`, one socket event with all items.
  - Batch with one already-completed step → request fails, no step changes, error names the offending step.
  - Confirm individual (non-batch) flows still use the single endpoint.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_batch_step_transition_20260623.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_step_transition_20260623.md`
- Related: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_working_section_20260623.md` (the `active_batch_steps` resume-card field that feeds this endpoint's `items`).
- Related debug plan (optional): `—`
```
