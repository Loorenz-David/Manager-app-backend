# HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - The step state transition service (`POST /api/v1/task-steps/{step_id}/transition`) now enforces a **one-active-step rule per user**: when a user transitions any step to `working`, the backend automatically pauses any other step that user is currently `working` on — before opening the new `working` record.
  - The auto-pause is **atomic**: it happens inside the same database transaction as the requested transition. Both succeed or both roll back together.
  - The conflict check covers **both the performer and the credited worker**: when a manager transitions a step on behalf of a worker (`credited_user_id`), the backend searches for open `working` records belonging to either the manager or the worker. This ensures the rule fires correctly regardless of who originally started the conflicting step.
  - The auto-paused record is created with `reason = PAUSE_OTHER_TASK_PRIORITY`, making it distinguishable from a manual pause in history views and analytics.
  - A full `task:step-state-changed` websocket event is emitted for the auto-paused step alongside the event for the requested step — so all subscribers see both changes.
  - A `PROCESS_STEP_TRANSITION` outbox event is also created for the auto-pause, so it appears as a real transition in analytics and activity history.

- API or contract changes:
  - No new endpoints or changed response shapes.
  - The `POST .../transition` response is unchanged — it still only describes the **requested** transition.
  - The auto-pause produces a separate websocket event; the frontend must listen for it to update the previously-working step.

- Feature flags/toggles: none

## Why this matters for the frontend

Without this rule, a user could appear as `working` on multiple steps simultaneously, which breaks:
- The `user_last_active_step_record` endpoint (designed to return exactly one meaningful record).
- Any UI that prevents a user from starting a second step while already `working`.
- Activity history (ambiguous who is responsible for which step).

The backend now guarantees this invariant. The frontend does **not** need to enforce it — but it **must react** to it via websocket events.

## What happens step by step

Given: User is `working` on **Step A**. User sends a `→ working` transition request for **Step B**.

1. Backend receives the transition request for Step B → working.
2. Backend finds User's open `working` record on Step A.
3. **Auto-pause (atomic, same transaction)**:
   - Closes Step A's open `working` `StepStateRecord` (`exited_at = now`).
   - Creates a new `paused` `StepStateRecord` for Step A with `reason = PAUSE_OTHER_TASK_PRIORITY`.
   - Updates Step A's `state → paused`, `latest_state_record_id`, timestamps.
4. Main transition proceeds: Step B's open record is closed; a new `working` record is opened.
5. Both transitions are committed atomically.
6. **Two websocket events are dispatched**:
   - `task:step-state-changed` for **Step A** (`new_state: "paused"`)
   - `task:step-state-changed` for **Step B** (`new_state: "working"`)
7. Two `PROCESS_STEP_TRANSITION` outbox events are queued (one per transition).

## Frontend action required

1. **Listen for `task:step-state-changed`** on any step, not just the one the user explicitly acted on. When received, refresh or patch that step's state in local state — the auto-paused step will arrive via this event.
2. **Do not assume one event per user action.** A single `→ working` request may produce two `task:step-state-changed` events: one for the newly-working step, one for the auto-paused step.
3. **Do not block the UI on the auto-pause.** The auto-pause is invisible to the user who triggered it — the UX should simply show the previously-working step as `paused` when the event arrives, with no confirmation dialog or error.
4. **Activity history / audit trail**: when displaying state history for a step, a `paused` record with `reason = PAUSE_OTHER_TASK_PRIORITY` means "this step was paused automatically because the user started working on a different step." Consider surfacing this differently from a manual pause (e.g. a distinct label or icon).

## Interface details

### Trigger

- Endpoint: `POST /api/v1/task-steps/{step_id}/transition` (existing)
- The auto-pause fires **only** when `new_state = "working"` AND an open `working` record exists in the workspace for either the performer (`created_by_id`) or the credited worker (`credited_user_id`).
- When both IDs are the same (the common case — a worker acting for themselves), the check is equivalent to a single-user lookup.

### Auto-pause StepStateRecord fields

| Field | Value |
|---|---|
| `state` | `paused` |
| `reason` | `PAUSE_OTHER_TASK_PRIORITY` |
| `description` | `null` |
| `created_by_id` | the user who triggered the `→ working` transition |
| `entered_at` | timestamp of the transition request |
| `exited_at` | `null` (record is open) |

### Websocket event for the auto-paused step

```jsonc
{
  "event": "task:step-state-changed",
  "client_id": "<step_A_uuid>",        // the step that was auto-paused
  "workspace_id": "<uuid>",
  "new_state": "paused"
}
```

This event arrives alongside (not instead of) the event for the requested step.

### `reason` values reference

| Value | Meaning |
|---|---|
| `PAUSE_OTHER_TASK_PRIORITY` | Auto-paused by the backend because the user started working on a different step |
| *(other values)* | Manual pause reasons set by the user |

## Validation notes

- Backend validation run: manual code review; no automated test run.
- Suggested frontend validation:
  - **Happy path (self-performing worker)**: Worker is `working` on Step A → worker transitions Step B to `working` → verify Step A transitions to `paused` in the UI (via websocket event) AND Step B transitions to `working`, without any second user action.
  - **Happy path (manager on behalf of worker)**: Worker started Step A themselves; Manager transitions Step B to `working` with `credited_user_id = Worker` → verify Step A is still auto-paused even though the manager is the performer.
  - **Manager started both steps**: Manager transitioned Step A to `working` for Worker, then transitions Step B to `working` for the same Worker → verify Step A is auto-paused (both steps were created by the manager, so the conflict is found via the performer's ID).
  - **Reason field**: inspect Step A's state history — verify the auto-paused record has `reason = PAUSE_OTHER_TASK_PRIORITY`.
  - **No prior working step**: user with no open `working` record → transition any step to `working` → verify no spurious auto-pause event is emitted.
  - **Atomicity**: simulate a DB failure mid-transition (if possible in staging) — verify neither Step A's auto-pause nor Step B's transition persists.
  - **Concurrent sessions**: user has two browser tabs; Tab 1 transitions Step B to `working` → verify Tab 2 receives the `task:step-state-changed` event for both Step A (paused) and Step B (working).

## Trace links

- Parent plan: `—`
- Parent summary: `—`
- Related handoff (last active step endpoint): [HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md](HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md)
- Related handoff (step list enhancements): [HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md](HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md)
