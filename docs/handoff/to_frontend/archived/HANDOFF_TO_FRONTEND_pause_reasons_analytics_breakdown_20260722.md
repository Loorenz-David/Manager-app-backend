# HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_20260722

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_20260722`
- Created at (UTC): `2026-07-22T14:00:00Z`
- Owner agent: `codex`
- Status: **implemented**
- Source plan: `PLAN_custom_pause_reasons_20260722`

## TL;DR

Worker linear timeline breakdowns now use opaque `pause_reason_id` client IDs as the keys in
`timeline.pause_by_reason` and segment `reason` fields. The response includes a sibling lookup map
so the frontend can render names and images without one request per bucket.

## Changed response shape

`GET /api/v1/worker-stats/{user_id}/linear-timeline` keeps its existing `user`, `timeline`, and
`segments` fields and adds:

```json
{
  "pause_reasons": {
    "par_01...": {
      "name": "Lunch break",
      "image_url": null,
      "pause_type": "personal"
    }
  }
}
```

Use `timeline.pause_by_reason` keys and each segment/detail `reason` value to index this map. A
missing map entry usually means the referenced reason was deleted; render a fallback using the ID
rather than failing the timeline — **except** for the reserved key below, which is expected to
have no map entry.

### The `"unspecified"` key

A **paused** segment's `reason` is never `null` — when the underlying `StepStateRecord` has no
`pause_reason_id`, the sweep substitutes the literal string `"unspecified"` as both the segment
`reason` and the `pause_by_reason` bucket key. This key will **never** appear in the `pause_reasons`
lookup map (it isn't a real `pause_reasons` row), so treat it as its own case rather than a
deleted/missing reason — e.g. render it as "No reason specified" instead of falling back to a
raw-ID placeholder. `reason: null` only occurs on non-paused segments (`working`/`idle`/
`ended_shift`), which don't participate in `pause_by_reason` at all.

## Compatibility notes

- `pause_by_reason` values remain integer seconds.
- Fetch the CRUD list for richer fields when needed; this lookup intentionally contains only
  `name`, `image_url`, and `pause_type`.

## Correction (2026-07-22): the roster endpoint has the same lookup map now

This handoff originally said the roster endpoint, `GET /api/v1/worker-stats/linear-timeline`
(`list_workers_linear_timeline.py`), was out of scope because its pause buckets come from
`UserShiftStateRecord` rather than `StepStateRecord`. That undersold a real effect of the
cutover: `UserShiftStateRecord.reason` is populated by copying over the already-chosen
`pause_reason_id` (from `reconcile_worker_shift_state.py`, `_reconstruct_shift_middle.py`, and the
`backfill_worker_shift_state_records.py` script), so the roster endpoint's `pause_by_reason` keys
silently changed from readable strings (e.g. `"pause_lunch_break"`) to the same opaque
`pause_reason_id` client IDs — with no lookup map, until now.

The roster response now also returns a top-level `pause_reasons` map, aggregated across every
worker on the page, in the same shape as the breakdown endpoint's:

```json
{
  "workers": [ { "user": { ... }, "timeline": { ..., "pause_by_reason": { "par_01...": 1800 } } } ],
  "workers_pagination": { ... },
  "pause_reasons": {
    "par_01...": { "name": "Lunch break", "image_url": null, "pause_type": "personal" }
  }
}
```

A bucket key can be one of three things — resolve in this order:
1. **Present in `pause_reasons`** → a real, still-existing pause reason; render its `name`.
2. **The literal string `"unspecified"`** → no reason was recorded (see the section above);
   render "No reason specified", never look it up in the map.
3. **Absent from `pause_reasons` and not `"unspecified"`** → either a deleted pause reason, or
   (roster endpoint only) free text from a manually-recorded whole-shift pause
   (`POST /api/v1/worker-shifts/pause`, unrelated to the `pause_reasons` table) — render the raw
   key as a fallback label in both cases.

## Correction (2026-07-22, later same day): `segments[].steps[]` no longer uses this lookup map

On `GET /api/v1/worker-stats/{user_id}/linear-timeline` only: each step detail inside
`segments[].steps[]` used to carry a flat `reason` id meant to be resolved against the
`pause_reasons` map above, same as everything else on this page. It's since been changed to embed
the full pause reason object directly, under a renamed field:

```diff
-{ "step_id": "tsp_...", "state": "paused", "reason": "par_01...", "description": null, ... }
+{ "step_id": "tsp_...", "state": "paused", "pause_reason": { "client_id": "par_01...", "name": "Lunch break", "image_url": null, "pause_type": "personal", "description": null, "requires_description": false, "is_system_managed": false, "slug": "pause_lunch_break", "created_at": "...", "created_by_id": null, "updated_at": null, "updated_by_id": null }, "description": null, ... }
```

Everything else on this page is unchanged: `segments[].reason` (segment/block level, one level up
from `steps[]`), `timeline.pause_by_reason` keys, and the `pause_reasons` map itself are all still
the original flat-id-plus-lookup-map contract described above — only the per-step `reason` field
was replaced with `pause_reason`. Full detail (including why, and the shared serializer used
elsewhere) is in
`HANDOFF_TO_FRONTEND_pause_reason_nested_in_step_state_records_20260722.md`.
