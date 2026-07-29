# HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722`
- Created at (UTC): `2026-07-22T15:40:00Z`
- Owner agent: `claude`
- Status: **implemented**
- Source plan: `PLAN_custom_pause_reasons_20260722`

## TL;DR

The step-transition endpoints no longer accept `reason: <StepEventReasonEnum slug>`. They now
accept `pause_reason_id: <pause_reasons client_id>`. This field rename shipped as part of the
pause-reasons cutover but was never written up for the frontend until now — the CRUD handoff only
covers `/api/v1/pause-reasons` itself, not its callers.

## Endpoints affected

- `POST /api/v1/tasks/{task_id}/steps/{step_id}/transition`
- `POST /api/v1/tasks/steps/transition-batch`

Both take the field identically.

## Request body change

```diff
 {
   "new_state": "paused",
   "credited_user_id": null,
-  "reason": "pause_lunch_break",
+  "pause_reason_id": "par_01...",
   "description": null,
   "mark_closing_record_inaccurate": false
 }
```

- `pause_reason_id` is a `pause_reasons.client_id`, not a slug or enum value. Fetch valid IDs from
  `GET /api/v1/pause-reasons` (see the CRUD handoff).
- Still **optional/nullable** — omit it or send `null` for an unspecified pause, same as the old
  `reason` field's behavior. Not required even when `new_state` is `"paused"`.
- The batch endpoint (`transition-batch`) applies one `pause_reason_id`/`description` pair to the
  whole batch, same as before — it was not made per-item.

## Server-side validation (new — the old `reason` enum had none of this)

If `pause_reason_id` is provided:

1. It must resolve to a real, non-deleted `pause_reasons` row **in the caller's workspace** —
   otherwise the request fails with `404 Pause reason not found.`
2. If that reason has `requires_description: true`, the request must also include a non-blank
   `description` string — otherwise it fails with
   `400 A description is required for the selected pause reason.`

This is the mechanism for reasons flagged `requires_description` (e.g. "Supplier call") to force a
typed explanation from the worker at the moment they select that reason, rather than after the
fact.

## Response shape change

**Correction (2026-07-22, later same day):** this section originally said `last_state_record.reason`
became a flat `pause_reason_id` string. That's now superseded — it's a full nested `pause_reason`
object instead, matching every other endpoint that embeds a step-state record (see
`HANDOFF_TO_FRONTEND_pause_reason_nested_in_step_state_records_20260722.md`, which covers this
serializer change across all affected endpoints, not just these two):

```diff
 {
   "step_id": "tsp_...",
   "new_state": "paused",
   "last_state_record": {
     "state": "paused",
-    "reason": "pause_lunch_break",
+    "pause_reason": {
+      "client_id": "par_01...",
+      "name": "Lunch break",
+      "image_url": null,
+      "pause_type": "personal",
+      "description": null,
+      "requires_description": false,
+      "is_system_managed": false,
+      "slug": "pause_lunch_break",
+      "created_at": "2026-07-22T11:00:00+00:00",
+      "created_by_id": null,
+      "updated_at": null,
+      "updated_by_id": null
+    },
     "description": null,
     "entered_at": "...",
     "exited_at": null,
     "last_action_by": { ... },
     "first_started_at": "..."
   },
   "was_final_step": false
 }
```

`pause_reason` is `null` when the record has no reason. No client-side lookup against
`GET /api/v1/pause-reasons` is needed to render a name/image here — the record already embeds it.

## Clarification (2026-07-22): deciding `paused` vs `ended_shift` in the reasons sheet

Question raised: now that reasons are data-driven, how should the picker sheet decide whether to
send `new_state: "paused"` or `new_state: "ended_shift"`? Today it hardcodes
`slug === "pause_ended_shift"` → `new_state: "ended_shift"`.

**Decision: keep that pattern — key off `slug === "pause_ended_shift"` in the sheet; every other
reason → `"paused"`. No backend change needed.**

Why this is safe:
- `WORKING`/`PAUSED → ENDED_SHIFT` is already a plain legal target for
  `POST .../transition`/`transition-batch`, for any `pause_reason_id` (or none) — the backend does
  not tie `new_state` to a specific reason. The step transition itself works identically to any
  other `new_state` value regardless of which reason accompanies it.
- `pause_ended_shift` is the one `is_system_managed: true` reason with a stable `slug` (protected
  from deletion/rename), so keying off it in the client is safe long-term.

Known, accepted limitation (not fixed by this decision, not a blocker): transitioning a step to
`ended_shift` this way does **not** update the worker's own shift-level record
(`UserShiftStateRecord`) — that only happens through the actual clock-out flow, which closes every
open step for that worker atomically. Driving `ended_shift` from a single task's reasons sheet can
leave a step reading "ended shift" while the worker's own shift history still shows them clocked
in. This mismatch predates the pause-reasons migration (the old enum-based sheet had the same
behavior) and is being knowingly deferred rather than fixed here — flagged for awareness, not
action.

## Not affected

- `_TaskStepInputBody.reason` / working-section reassignment `reason` fields elsewhere in the
  tasks router are a different, pre-existing concept (opaque free-text reassignment note) — not
  renamed, not related to `pause_reasons`.
- The manual whole-shift pause endpoint, `POST /api/v1/worker-shifts/pause`, still takes free-text
  `reason` and is unrelated to this table.
