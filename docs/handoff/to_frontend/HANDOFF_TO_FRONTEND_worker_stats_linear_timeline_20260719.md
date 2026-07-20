# HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719`
- Created at (UTC): `2026-07-19T00:00:00Z`
- Owner agent: `claude-opus-4-8`
- Status: **implemented**
- Related (same router, do not confuse): `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md`, `HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718.md`.

## TL;DR — what is new

**Two new, additive** endpoints on the worker-stats router:

```
GET /api/v1/worker-stats/linear-timeline              # roster: per-worker range TOTALS
GET /api/v1/worker-stats/{user_id}/linear-timeline    # drill-down: the drawable SEGMENTS
```

- The **roster** endpoint reports each worker's **wall-clock ("linear")** time over a date range: how long they actually worked, how much real time passed **between** working (pause, split by reason), and how much was **idle**. Use it for the list/summary view.
- The **drill-down** (`/{user_id}/…`) returns the same totals **plus the ordered list of typed time segments** — the literal shape you paint on an interactive calendar-style timeline, each segment carrying the steps + items behind it. Use it for the single-worker timeline view (see §"Drill-down" below).

Nothing else changes — both are brand-new routes; no existing shape is touched. This mirrors how `/{user_id}/daily-steps` drills into `/totals`.

### Why it exists (read this — it's a different number than `/totals`)

`GET /worker-stats/totals` sums **every** state interval independently. A worker can hold **several items paused at once**, so those pauses **add up**: two items paused over the same 10 minutes = **20 min** of `total_pause_seconds`. That answers *"how long did items sit paused"*.

`/linear-timeline` answers a **different** question: *"over the worker's real day, at each instant what were they doing?"* It collapses overlaps so the same two items paused over the same 10 minutes = **10 min** of wall-clock pause. Use `/totals` for cumulative "time items spent in a state"; use `/linear-timeline` for a real-time-of-day breakdown that partitions the shift.

**Do not expect the two pause numbers to match** — by design `linear pause_seconds ≤ totals total_pause_seconds`.

## Auth & params

- **Auth:** `ADMIN` or `MANAGER` (same as the other worker-stats endpoints).
- **Query params** (all optional):
  - `date_from` — `YYYY-MM-DD`, inclusive start.
  - `date_to` — `YYYY-MM-DD`, inclusive end.
  - `limit` — default `50`, max `200`.
  - `offset` — default `0`.
- Omit both dates → **today → today** (server UTC). Single day → `date_from == date_to`.
- **Validation (`422`):** either date unparseable; `date_to < date_from`; span wider than **366 days**.
- Roster + pagination are the **same** as `/totals` and `/insights` (workers with role `worker`, ordered by `username ASC`).

## Roster endpoint response shape — `GET /worker-stats/linear-timeline`

```jsonc
{
  "workers": [
    {
      "user": {
        "client_id": "usr_…",
        "username": "…",
        "profile_picture": null,
        "last_online": null
      },
      "timeline": {
        "date_from": "2026-07-15",
        "date_to":   "2026-07-15",
        "working_seconds":     7200,   // real time working (parallel work NOT double-counted)
        "pause_seconds":       1800,   // real time not-working with an active pause
        "ended_shift_seconds":    0,   // real time in ended-shift (no work, no active pause)
        "idle_seconds":         600,   // real time attributed to nothing (see below)
        "completed_count":        3,   // steps COMPLETED during recorded shifts in the range (count, not seconds)
        "pause_by_reason": {           // sums EXACTLY to pause_seconds
          "pause_lunch_break": 1800
        }
      }
    }
  ],
  "workers_pagination": { "has_more": false, "limit": 50, "offset": 0, "total": 12 }
}
```

### Field semantics

At every instant the worker is in **exactly one** of four disjoint buckets (they **partition** the active span, so `working + pause + ended_shift + idle ≤ elapsed`):

| Field | Meaning |
|---|---|
| `working_seconds` | Any item being worked. **Wins over everything** — if the worker is working item A while item B sits paused, that instant is *working*, not pause. Parallel/batch work is collapsed to wall-clock (no double counting). |
| `pause_seconds` | Not working **and** at least one **active** pause is open. This is your "time between working". |
| `ended_shift_seconds` | Not working, no active pause, an ended-shift interval open. |
| `idle_seconds` | None of the above — non-working time attributed to nothing: researching the next item, un-booked gaps, or a pause the worker walked away from after they already resumed (see capping). |
| `completed_count` | Number of steps the worker **completed during their recorded shifts** in the range. A **count**, not a duration — it's not part of the time partition. It counts `COMPLETED` step records (credited to the worker) **only when the completion falls inside a recorded `UserShiftStateRecord` interval**, so it stays consistent with the shift-based time buckets: a day the worker never clocked in contributes **0** completions here (even if step data exists). This differs from `/totals`' `total_completed_count`, which is range-based off the aggregate table. |
| `pause_by_reason` | `pause_seconds` split by reason. **Reconciles exactly** with `pause_seconds`. Keys are the reason enum values (below); pauses with no reason bucket under `"unspecified"`. Omitted reasons are simply `0`; the object only contains reasons that occurred. |

### `pause_by_reason` keys

The possible keys (any subset, only those that occurred in the range):

- `pause_lunch_break`
- `pause_coffee_break`
- `pause_meeting`
- `pause_case_created`
- `pause_other_task_priority`
- `pause_ended_shift`
- `waiting_for_upholstery`
- `unspecified` — the pause carried no reason.

> Treat this list as open — new reason values can be added server-side. Render unknown keys generically rather than hard-failing.

## Two behaviors that will surprise you (please read)

### 1) Overlapping pauses with different reasons

When two pauses overlap and neither is under work, each **instant** is credited to the pause that **started earliest** among those still open there (deterministic tiebreak). It's decided per-instant, not once for the whole overlap:

```
lunch:   [09:00 ─────────── 09:30]
meeting:        [09:10 ─────────── 09:40]
→ pause_by_reason: { "pause_lunch_break": 1800, "pause_meeting": 600 }
  (lunch owns 09:00–09:30 incl. the overlap; meeting owns 09:30–09:40 after lunch ends)
```

### 2) Stale pauses are capped at the next resume → the rest becomes `idle`

A paused record stays open in the DB until explicitly resumed. To stop a walked-away pause from swallowing every later gap under its old reason, each pause is **capped at the moment the worker next starts working anything**. Past that cap it is *stale* and stops counting as pause; that non-working time falls into `idle_seconds`.

```
Pause A for lunch at 09:00 (never resumed on A).
Worker returns and works item B  09:30–09:50, then stops (nothing until you pull at 10:00).

→ working_seconds       = 1200   (09:30–09:50)
  pause_seconds         = 1800   (09:00–09:30, lunch)   ← capped at the 09:30 resume
  idle_seconds          =  600   (09:50–10:00)          ← the gray area, NOT lunch
  pause_by_reason       = { "pause_lunch_break": 1800 }
```

Consequences to design for:

- A **genuine re-pause after resuming** is a fresh interval and **still counts** (e.g. lunch → work → coffee → coffee counts).
- A brief work blip during a pause **consumes** the pause; if the worker doesn't re-pause, the remainder becomes `idle`. This is intended (nudges explicit pausing).
- A pause **left open with no clock-out** and pulled later shows a large `idle_seconds` tail out to "now" after the last work. That's honest signal (forgotten pause / clock-out), not a bug.

## Drill-down endpoint — `GET /worker-stats/{user_id}/linear-timeline`

The **interactive timeline** source. Same auth and the **same** `date_from`/`date_to` params (no `limit`/`offset` — see granularity below). Returns the worker, the range totals (identical `timeline` shape as above, so it reconciles with the roster row), and the ordered **segments**: the partition of the window into contiguous, single-state blocks you draw and click.

```jsonc
{
  "user": { "client_id": "usr_…", "username": "…", "profile_picture": null, "last_online": null },

  "timeline": {                       // range totals — same shape/rules as the roster endpoint
    "date_from": "2026-07-15", "date_to": "2026-07-15",
    "working_seconds": 1200, "pause_seconds": 1800,
    "ended_shift_seconds": 0, "idle_seconds": 600,
    "completed_count": 1,
    "pause_by_reason": { "pause_lunch_break": 1800 }
  },

  "segments": [                        // ORDERED, contiguous, non-overlapping; draw these
    {
      "start": "2026-07-15T09:00:00+00:00",
      "end":   "2026-07-15T09:30:00+00:00",
      "seconds": 1800,
      "state": "paused",              // "working" | "paused" | "ended_shift" | "idle"
      "reason": "pause_lunch_break",  // only for paused; else null
      "is_open": false,               // true = currently running (reaches "now")
      "steps": [                      // ONE entry per contributing state record (empty for idle)
        {
          "record_id": "ssr_…",
          "step_id": "tsp_…",
          "task_id": "tsk_…",
          "working_section_id": "wsec_…",
          "working_section_name": "Upholstery",
          "item": {                   // the task's PRIMARY item; null if none
            "client_id": "itm_…",
            "article_number": "ART-1",
            "sku": "SKU-1"
          },
          "state": "paused",          // THIS record's own state (== the block's state)
          "reason": "pause_lunch_break", // THIS record's own reason (may differ from the block owner)
          "entered_at": "2026-07-15T09:00:00+00:00", // the record's TRUE span…
          "exited_at":  "2026-07-15T09:30:00+00:00", // …may extend beyond the block/window; null if open
          "is_open": false,
          "ended_by": "working"       // what the step did NEXT: "completed" | "paused" |
                                      // "working" | "ended_shift" | … | "still_open" | "unknown"
        }
      ]
    },
    { "start": "…09:30", "end": "…09:50", "seconds": 1200, "state": "working",
      "reason": null, "is_open": false, "steps": [ { …ART-2… } ] },
    { "start": "…09:50", "end": "…10:00", "seconds": 600, "state": "idle",
      "reason": null, "is_open": false, "steps": [] }
  ],

  "segments_truncated": false          // true only if a pathological window exceeded the 5000-segment cap
}
```

### How to render / interact

- **Draw** each segment as a block on the time axis using `start`/`end` (absolute UTC ISO); color by `state`; label paused blocks by `reason`. `seconds` is the block width for convenience.
- **Segments are a partition** — contiguous, non-overlapping, ordered. Within a day they sum to that day's totals; across the range they sum to `timeline`. No gaps except at the very start/end of the worker's activity.
- **Click** a block → show `steps[]`. **Each entry is one underlying `StepStateRecord`** (not one step), so it carries that record's own `state`, `reason`, `entered_at`, `exited_at`, `is_open` **plus** the step/item labels (`article_number`, `sku`, `working_section_name`). This is how you place an individual state record inside the block:
  - A `working` block with **batch** work lists **all** the *working* records active in it — you can draw each step's own sub-span using its `entered_at`/`exited_at`. Note it lists the records **in the block's state only**: if some steps were *paused* concurrently while others were worked, those paused steps are **not** in this working block's `steps[]` (working wins, so the block is `working`, and a paused step only surfaces where its pause is the effective state). `steps[]` is "the batch in *this* state during this block," not "everything the worker had open." To show every step's state at the same instant (a multi-lane Gantt), you'd need raw per-step records — not exposed here; ask if you need it.
  - **`ended_by`** tells you what the step did **after** this record — the state it transitioned into: `"completed"`, `"paused"`, `"working"`, `"ended_shift"` (or `"skipped"`/`"failed"`/`"cancelled"`/`"blocked"`), or `"still_open"` if the record hasn't ended yet, `"unknown"` if no later transition is recorded. This is how you show "✓ completed A at 17:00" — a `working` record with `ended_by: "completed"` whose `exited_at` is the completion time. (`completed` is a transition, not a block, so it never gets its own segment.)
  - A `paused` block lists **every** item paused during it; the *block* is labelled by the owner reason, but each record keeps its **own** `reason` (e.g. one item on lunch, another on a meeting).
  - `idle` blocks have `steps: []`.
  - ⚠️ A record's `entered_at`/`exited_at` are its **true** span and can extend **beyond** the block (or the queried window) — e.g. a working record that started before this day. **Clip to the block/your visible range when drawing.** (No item images here — fetch those separately if a detail panel needs them.)
- **`is_open: true`** marks the block currently in progress (only when the range includes today). Render it as live/striped and let it grow to "now".
- **Segment merging:** consecutive instants of the same `state` (and same `reason` for pauses) are merged into one block, so you get clean calendar events rather than a sliver per state-record. A block is split at **UTC-midnight** boundaries so each belongs to a single day.

### Granularity — you own the window

There is **no server-side paging** on segments. **You choose the window** via `date_from`/`date_to` and paginate by moving it — e.g. request a 3-day window for a calendar view and step it forward/back; widen it to zoom out and **compress visually on the client**. The `timeline` totals always cover the exact window you asked for. Guardrails: the shared **366-day** range cap still applies (`422`), and a hard **5000-segment** ceiling sets `segments_truncated: true` (narrow the window if you ever see it — normal windows never hit it).

> **Timezone note:** all timestamps and the midnight day-splits are **UTC**, consistent with the rest of worker-stats (`work_date` is UTC). If your calendar renders in local time, bucket the segments into day-columns yourself using the absolute `start`/`end`; adjacent same-state blocks can be visually joined.

## Relationship to the other worker-stats endpoints

- **`/totals`** — cumulative per-state sums (overlaps add up) + live `running`. Different number; keep using it for "time items spent in state" and live tickers.
- **`/{user_id}/daily-steps`** — per-step, contribution-oriented drill-down of `/totals`.
- **`/linear-timeline`** (roster) — this feature; wall-clock partition of the shift, totals only. No `running`/live-tick field: it's a settled-range view (it does include still-open intervals clamped to "now" when the range includes today, but there is no separate live add-on to tick).
- **`/{user_id}/linear-timeline`** (drill-down) — the same totals **plus** the drawable segments; the source for the interactive timeline. `is_open` marks the live block.

## Frontend action

1. **Roster/summary:** call `GET /worker-stats/linear-timeline?date_from&date_to&limit&offset` for the "worked vs. pause-between-work vs. idle" totals per worker. Render the four `*_seconds` as a partition (stacked bar); show `pause_by_reason` as the pause breakdown; and `completed_count` as a standalone "steps completed" metric (it's a count, not part of the bar).
2. **Interactive timeline:** call `GET /worker-stats/{user_id}/linear-timeline?date_from&date_to` for the worker's segments; draw each `segment` as a block (`start`/`end`, color by `state`, label pauses by `reason`), and on click show `steps[]` — one entry per underlying state record with its own `state`/`reason`/`entered_at`/`exited_at` and the step/item labels (article_number/sku/section). Own the window: request the days you display and move it to paginate/zoom; there is no `limit`/`offset` here.
3. **Do not** try to reconcile `pause_seconds` here with `total_pause_seconds` from `/totals` — they measure different things (wall-clock vs. cumulative).
4. Handle `pause_by_reason` keys defensively (unknown/`unspecified` allowed); trust that its values sum to `pause_seconds`, and that the drill-down's `segments` sum back to `timeline`.
5. Reuse the existing `date_from`/`date_to` handling from `/totals` (roster endpoint also shares its `limit`/`offset` roster pagination).

## Error cases

- `422` — invalid/inverted date range or span > 366 days (see Validation).
- `401/403` — missing/insufficient role (needs ADMIN or MANAGER).

## Validation notes

- Backend validation run: unit tests `tests/unit/domain/analytics/test_linear_timeline.py` (28) — overlap collapse, working-wins, per-reason attribution + tiebreak, cap-at-resume → idle, idle gaps, re-pause, partition invariant, window/now clamping, segment partition/merge, step-id union, hard-break split, `is_open`, segments-reconcile-with-totals, **plus** per-record true times, per-record reasons on concurrent pauses, idle-has-no-records, and open-record flag. Integration `test_list_workers_linear_timeline.py` (5, roster: incl. `completed_count` scoped to recorded shifts) and `test_get_worker_linear_timeline_breakdown.py` (4, drill-down: ordered segments with item article/sku/section + per-record times, `ended_by` outcomes incl. `completed`/`paused`/`still_open`, `NotFound` for unknown worker, empty worker). All green; ruff clean.
- Suggested frontend validation: pull a real worker's range that includes a lunch + a resume; confirm the idle tail lands in `idle_seconds` (not pause), `sum(pause_by_reason.values()) === pause_seconds`, and the drill-down `segments` sum back to `timeline`. Click a `working` block and confirm the batch steps render, each with its own `entered_at`/`exited_at`; click a `paused` block with two items paused and confirm each record shows its own `reason`; and confirm a completed step's working record shows `ended_by: "completed"`.

## Trace links

- Roster endpoint: `backend/app/beyo_manager/routers/api_v1/worker_stats.py` → `GET /linear-timeline` (service `list_workers_linear_timeline.py`).
- Drill-down endpoint: same router → `GET /{user_id}/linear-timeline` (service `get_worker_linear_timeline_breakdown.py`; a lean 3-query load for step → primary item article/sku, no images).
- Pure sweep (rules + capping + segments): `backend/app/beyo_manager/domain/analytics/linear_timeline.py` (`compute_linear_timeline`, `compute_linear_segments`).
- Serializers: `backend/app/beyo_manager/domain/analytics/serializers.py` → `serialize_linear_timeline`, `serialize_linear_segment`.
- Sibling contracts: `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md`, `HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718.md`, `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`.

## Addendum — recorded shift state (`2026-07-20`)

The two endpoint paths and every previously delivered response key remain unchanged.
Their time buckets now come from recorded `UserShiftStateRecord` intervals rather than
being inferred from overlapping step records:

- Off-shift time is excluded. `idle_seconds` is only an explicit, recorded on-shift
  `idle` interval; pre-clock-in and post-clock-out gaps no longer appear as idle.
- `pause_seconds` and `pause_by_reason` come directly from recorded shift pauses.
  Manual free-text reasons are valid object keys in addition to the enum-like keys
  listed above; the key set was already declared open.
- Open duration segments are still clamped to `now`, and `is_open: true` keeps its
  existing live meaning.
- `completed_count` is now **scoped to recorded shifts**: it counts `COMPLETED` step
  records only when the completion falls inside one of the worker's recorded
  `UserShiftStateRecord` intervals (shift bounds inclusive, so a completion at the
  `ended_shift` instant still counts). This keeps it consistent with the shift-based
  time buckets — a day with no recorded shift contributes 0. Same key and shape (an
  integer); only the semantics tightened. Each segment's `steps[]` detail is unchanged.

The drill-down has two additive extensions only:

1. It can return zero-duration `started_shift` and `ended_shift` marker segments.
   Both have `start == end`, `seconds: 0`, `reason: null`, `is_open: false`, and
   `steps: []`. Treat them as clock-in/clock-out ticks rather than duration blocks.
2. Every segment includes `manually_recorded: boolean`. It is `true` for a worker's
   explicit shift pause and `false` for derived, backfilled, idle, working, and marker
   records.

The existing public pause segment value remains `"paused"` (the persistence enum is
`in_pause`). Existing duration states and all nested step-detail fields are unchanged.
The earlier sweep/capping examples above describe the historical reconstruction input;
after this addendum, the live read semantics are the recorded on-shift intervals stated
here.
