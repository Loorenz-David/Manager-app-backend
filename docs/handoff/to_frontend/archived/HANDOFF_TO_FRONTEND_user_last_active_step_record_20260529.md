# HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - New standalone endpoint that returns **one** `StepStateRecord` representing the most relevant active interaction the authenticated user has across all steps in the workspace.
  - The selection follows a **4-tier priority rule** that considers both the record's state and whether it is still live (`exited_at IS NULL`) or historical (`exited_at` set): open `working` → open `paused`/`ended_shift` → closed `working` → closed `paused`/`ended_shift`. This ensures a user who transitioned from `working` to `paused` is shown as `paused` (live), not `working` (now historical), while still surfacing closed records as a fallback for the cross-user completion case (see below).
  - Filtered on the **record's own state** — not the step's current state. This is intentional: a user may have paused a step that was later completed by a colleague. The user's `paused` record is still meaningful (it tells the frontend the user was last active on that step) and must not be hidden just because the step moved to a terminal state.
  - Intended to be called on first page load to determine whether the user has an in-progress step to resume, and to drive frontend validation rules around active work (e.g. prevent starting a new step if the user is already `working`).
  - **The backend now enforces the one-active-step rule**: when a user transitions any step to `working`, the server automatically pauses any other step the user is currently `working` on before opening the new record. The frontend does not need to enforce this — it is guaranteed by the backend. See [HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md](HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md) for full details of that behaviour.

- API or contract changes:
  - New endpoint — no changes to existing endpoints.

- Feature flags/toggles: none

## Why this priority rule?

A user can have multiple records across different steps in non-terminal states. For example:

- Step A: user set `paused` yesterday
- Step B: user set `paused` this morning
- Step C: user set `working` one hour ago

Without a priority rule, returning "most recent" would give Step C's `working` record — which happens to be correct here, but only by coincidence of timing. If Step C had been paused *before* Step B, "most recent" would return Step B's `paused` record even though the user is actively `working` on Step C.

The priority rule makes this deterministic, across four tiers ordered by liveness first, then state:

1. **Open `working`** — the user is actively working right now. The backend enforces that only one open `working` record can exist per user at a time. See [HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md](HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md).
2. **Open `paused` / `ended_shift`** — the user's current paused state. Returned when no open `working` record exists.
3. **Closed `working`** — a historical `working` record where the step was since completed by another user. The user's own record was never explicitly closed by them, but it was closed as a side-effect of the other user's terminal transition.
4. **Closed `paused` / `ended_shift`** — a historical paused record similarly closed by another user's terminal transition. This is the cross-user fallback case: if User B completes a step User A had paused, User A still sees the paused record as a last resort when no live record exists.

## Frontend action required

1. Call `GET /api/v1/working-sections/steps/user-last-active` on first page load.
2. If `user_last_active_step_record.state === "working"` — the user is mid-task. Lock starting any other step; highlight or surface the active step using `step_id`.
3. If `state` is `paused` or `ended_shift` — the user has a step to resume. Show a "resume" prompt or indicator using `step_id`.
4. If `null` — the user has no active interaction. Allow full step-start interactions.

## Interface details

- Endpoint: `GET /api/v1/working-sections/steps/user-last-active`
- Roles allowed: `ADMIN`, `MANAGER`, `WORKER`
- No path or query parameters.

### Response shape

The response uses the **same shape as each item in `list_working_section_steps`**, so the frontend can render it identically to a step card without any adaptation.

```jsonc
{
  "user_last_active_step_record": null  // null when the user has no working / paused / ended_shift record
}
```

```jsonc
{
  "user_last_active_step_record": {
    // — Core step fields (from serialize_step) —
    "id": "<uuid>",
    "state": "working",               // current step state (not necessarily the record's state)
    "name": "...",
    // ... all other TaskStep fields serialized by serialize_step

    // — Timestamps & actors —
    "updated_at": "2026-05-29T10:00:00",
    "created_by": { /* serialize_user_working_section_member */ },
    "updated_by": { /* serialize_user_working_section_member */ },

    // — Latest state record —
    "last_state_record": {
      "state": "working",
      "entered_at": "2026-05-29T09:00:00",
      "exited_at": null,
      "last_action_by": { /* serialize_user_working_section_member */ },
      "first_started_at": "2026-05-28T14:00:00"   // earliest entered_at across all records for this step
    },

    // — Task —
    "task": { /* serialize_task_light */ },

    // — Item (primary task item) —
    "item": { /* serialize_item_worker_light — null fields when no primary item */ },

    // — Item images —
    "item_images": [
      { /* serialize_image (rich, first image) */ },
      { /* serialize_image_light (subsequent images) */ }
    ],

    // — Cases —
    "cases_summary": {
      "total_unread": 0
    }
  }
}
```

### Selection logic (single query, no second round-trip)

```
ORDER BY
  CASE
    WHEN state = 'working' AND exited_at IS NULL THEN 0   -- currently working
    WHEN exited_at IS NULL                        THEN 1   -- currently paused / ended_shift
    WHEN state = 'working'                        THEN 2   -- was working (historical)
    ELSE                                               3   -- was paused / ended_shift (historical)
  END ASC,
  created_at DESC
LIMIT 1
```

- Live records (`exited_at IS NULL`) always beat historical ones of the same state.
- Within the same tier, newest record wins.
- Result: one row, selected in a single DB round-trip.

### Selection priority

| Tier | Condition | Meaning |
|---|---|---|
| 0 | `state = working` AND `exited_at IS NULL` | User is actively working right now |
| 1 | `exited_at IS NULL` (any active state) | User's current paused / ended-shift state |
| 2 | `state = working`, `exited_at` set | Was working; step since moved on (historical) |
| 3 | `exited_at` set (any active state) | Was paused / ended-shift; closed by another user's terminal transition |

### Excluded states

| State | Reason excluded |
|---|---|
| `pending` | Step not yet started by anyone — no user action to surface |
| `blocked` | System/dependency state, not a direct user action |
| `completed` | Terminal |
| `skipped` | Terminal |
| `failed` | Terminal |
| `cancelled` | Terminal |

### Error cases

| Status | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Role not permitted |

## Validation notes

- Backend validation run: manual code review; no automated test run.
- Suggested frontend validation:
  - **Null case**: user with no step records → verify `null` returns and no "resume" UI is shown.
  - **Open working wins over older paused**: user has an open `paused` record on Step A (created this morning) and an open `working` record on Step B (created last week) → verify Step B's `working` record is returned.
  - **Open paused wins over closed working**: user was `working` on Step A, then transitioned to `paused` → verify the endpoint now returns the open `paused` record for Step A, not the now-historical closed `working` record.
  - **Paused fallback**: user has only `paused` and `ended_shift` records, all open → verify the most recently created one is returned.
  - **Cross-user terminal resilience**: User A pauses Step X; User B completes Step X (closing User A's paused record as a side-effect) → call endpoint as User A → verify User A's historical `paused` record for Step X is still returned as a fallback when User A has no other live records.
  - **`step_id` navigation**: verify `step_id` resolves correctly in the working section step list.

## Trace links

- Parent plan: `—`
- Parent summary: `—`
- Related handoff (step list enhancements): [HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md](HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529.md)
- Related handoff (auto-pause rule): [HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md](HANDOFF_TO_FRONTEND_auto_pause_on_working_transition_20260529.md)
