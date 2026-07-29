# HANDOFF_TO_FRONTEND_pause_reason_nested_in_step_state_records_20260722

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pause_reason_nested_in_step_state_records_20260722`
- Created at (UTC): `2026-07-22T19:00:00Z`
- Owner agent: `claude`
- Status: **implemented**
- Source plan: `PLAN_custom_pause_reasons_20260722`

## TL;DR

Every endpoint that embeds a step-state-record object now returns a full nested `pause_reason`
object instead of the opaque `pause_reason_id` string. You no longer need to cross-reference
`GET /api/v1/pause-reasons` (or the analytics lookup maps) to render a name/image for these
endpoints specifically — the record carries its own reason inline. `pause_reason_id` is gone from
these response shapes; it's not a rename you can `pause_reason_id → pause_reason.client_id` blindly
without checking each endpoint (see below).

## What changed

`domain/tasks/serializers.py`'s two step-state-record serializers now nest the pause reason object
(via the same shape as `serialize_pause_reason`, documented in the CRUD handoff) instead of the raw
FK id:

```diff
 {
   "state": "paused",
-  "pause_reason_id": "par_01...",
+  "pause_reason": {
+    "client_id": "par_01...",
+    "name": "Lunch break",
+    "image_url": null,
+    "pause_type": "personal",
+    "description": null,
+    "requires_description": false,
+    "is_system_managed": false,
+    "slug": "pause_lunch_break",
+    "created_at": "2026-07-22T11:00:00+00:00",
+    "created_by_id": null,
+    "updated_at": null,
+    "updated_by_id": null
+  },
   ...
 }
```

`"pause_reason"` is `null` when the record has no reason (unpaused states, or a pause with no
reason selected) — same as `pause_reason_id` being `null` before.

## Affected endpoints

| Endpoint | Response field | Serializer |
|---|---|---|
| `GET /api/v1/tasks/{task_id}` | each item in `steps[].latest_state_records` | `serialize_step_latest_state_record` |
| `GET /api/v1/tasks/{task_id}/steps` | each item in `steps_pagination.items[].latest_state_records` | `serialize_step_latest_state_record` |
| `GET /api/v1/working-sections/{working_section_id}/steps` | each item's `last_state_record` | `serialize_step_state_record_light` |
| `GET /api/v1/working-sections/steps/user-last-active` | `last_state_record` | `serialize_step_state_record_light` (via shared `build_step_record_payload`) |
| `GET /api/v1/worker-stats/last-interacted-steps` | each item's `last_state_record` | `serialize_step_state_record_light` (via shared `build_step_record_payload`) |
| `GET /api/v1/task-step-acknowledgments/pending` | each item's `last_state_record` | `serialize_step_state_record_light` (via shared `build_step_record_payload`) |
| `GET /api/v1/worker-stats/{user_id}/linear-timeline` | each item in `segments[].steps[]` | `record_detail()` (bespoke, see below) |

The two shapes differ in surrounding fields (`serialize_step_latest_state_record` includes
`id`/`step_id`/`created_at`/`created_by_id`/`accuracy`/`accuracy_measured_by`/`taken_from_average`;
`serialize_step_state_record_light` is the trimmed variant with `last_action_by`/
`first_started_at`) — only the `pause_reason` field itself is new in both.

## Also corrects the transition-endpoint handoff

`HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` (written earlier the same
day) documented `last_state_record.pause_reason_id` as a flat string for
`POST /api/v1/tasks/{task_id}/steps/{step_id}/transition` and
`POST /api/v1/tasks/steps/transition-batch`. That's now stale — those two endpoints return
`last_state_record` via the same `serialize_step_state_record_light` function covered here, so they
get the same nested `pause_reason` object. That doc has been updated in place; this handoff exists
for the read endpoints that doc didn't cover.

## Not affected

- `GET /api/v1/pause-reasons` and friends (the CRUD endpoints) — unchanged, already returned this
  exact object shape as `pause_reason` (singular) or inside `pause_reasons` (list).

### `GET /api/v1/worker-stats/{user_id}/linear-timeline` — mixed: steps[] now nested, segment-level stays flat

**Correction (2026-07-22, later same day):** this section originally said this endpoint's
`segments[].steps[]` detail objects were untouched. That's since been corrected too —
`record_detail()` (a separate, bespoke serializer in `services/queries/worker_stats/`, not
`serialize_step_state_record_light`/`serialize_step_latest_state_record`, but updated to match) now
also nests the full `pause_reason` object per step, **renaming the field from `reason` to
`pause_reason`** in `steps[]` specifically:

```diff
 {
   "segments": [
     {
       "reason": "par_01...",
       "steps": [
-        { "step_id": "tsp_...", "state": "paused", "reason": "par_01...", "description": null, ... }
+        { "step_id": "tsp_...", "state": "paused", "pause_reason": { "client_id": "par_01...", "name": "Lunch break", ... }, "description": null, ... }
       ]
     }
   ],
   "pause_reasons": {
     "par_01...": { "name": "Lunch break", "image_url": null, "pause_type": "personal" }
   }
 }
```

**What did NOT change** — still a flat `pause_reason_id`-shaped string, still resolved via the
sibling top-level `pause_reasons` lookup map, exactly as documented in
`HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_20260722.md`:
- The **segment-level** `reason` field (`segments[].reason`, one level up from `steps[]` — describes
  the whole block, can also be the `"unspecified"` sentinel).
- `timeline.pause_by_reason` bucket keys.
- The top-level `pause_reasons` lookup map itself — still present, still needed for the two items
  above, even though `steps[]` no longer needs it.

So within one `segments[]` entry you'll see both styles side by side: `reason` (flat id/sentinel,
segment-level) and `steps[].pause_reason` (nested object, per-step). Don't conflate them.

The roster endpoint, `GET /api/v1/worker-stats/linear-timeline`, does not embed per-step detail
objects at all (no `steps[]`) — its `pause_by_reason` bucket keys + lookup map are unaffected by
anything in this doc.
