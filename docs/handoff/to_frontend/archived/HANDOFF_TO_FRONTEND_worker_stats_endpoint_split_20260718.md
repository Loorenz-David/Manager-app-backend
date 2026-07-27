# HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_endpoint_split_20260718.md`
- Status: **implemented**

## TL;DR — what is changing

The former combined roster endpoint `GET /api/v1/worker-stats/last-interacted-steps` returned **three unrelated things** per worker in one payload: the last-interacted step, the daily totals (+ live running), and the insights. It has now been **split into three independent endpoints**, each returning one concern:

| New endpoint | Returns per worker | Time model |
|---|---|---|
| `GET /api/v1/worker-stats/last-interacted-steps` *(slimmed)* | `user`, `last_interacted_step`, `batch` | point-in-time "now" |
| `GET /api/v1/worker-stats/totals` *(new)* | `user`, `daily_stats`, `running` | a day (range later) |
| `GET /api/v1/worker-stats/insights` *(new)* | `user`, `insights` | own baseline window |

> ⚠️ **Breaking change (hard split).** After this ships, `/last-interacted-steps` **no longer returns** `daily_stats`, `running`, or `insights`. There is no compatibility window — the three endpoints land together and the frontend must migrate in the same release. Fetch the three **in parallel** and **zip them by `user.client_id`** to rebuild one worker card.

The drill-down `GET /api/v1/worker-stats/{user_id}/daily-steps` is **unchanged** by this split.

## Why (so the FE models it right)

The three concerns have different refresh cadences and time semantics: the last step is a live snapshot (poll fast), totals are settled aggregates + a live add-on, insights are expensive and change slowly. Splitting lets you poll/cache each independently and — importantly — unblocks the upcoming **date-range** feature on totals (a range is meaningless for "the last step"). Build the three as **separate data sources composed in the view**, not one model.

## Shared contract (all three endpoints)

- **Auth:** `ADMIN` or `MANAGER` only.
- **Query params (identical on all three):**
  - `limit` — default `50`, max `200`.
  - `offset` — default `0`, `≥ 0`.
  - `work_date` — optional `YYYY-MM-DD`; omit for server-UTC today. Unparseable → `422`. **Scopes the data on `/totals` and `/insights` only.** On `/last-interacted-steps` it is accepted (and still `422`s on garbage) but has **no effect** — that endpoint is a point-in-time snapshot and always returns the latest step.
- **Envelope (identical on all three):**
  ```jsonc
  {
    "workers": [ { "user": { … }, /* endpoint-specific fields */ } ],
    "workers_pagination": { "has_more": false, "limit": 50, "offset": 0, "total": 12 }
  }
  ```
- **Worker set + ordering are identical** across the three (same active `worker`-role membership, ordered by `username ASC`, same pagination). So for the same `limit`/`offset`/`work_date`, page *k* of each endpoint contains the same workers in the same order — but still **join by `user.client_id`**, don't assume positional alignment.
- **`user` object** (present on every endpoint, every worker):
  ```jsonc
  "user": {
    "client_id": "usr_…",
    "username": "Andrii",
    "profile_picture": "https://… | null",
    "last_online": "2026-07-18T14:00:00+00:00 | null"   // ISO 8601 | null
  }
  ```
- **Error cases (all three):** `401` missing/invalid auth · `403` not ADMIN/MANAGER · `422` bad `work_date`.

## 1) `GET /api/v1/worker-stats/last-interacted-steps` (slimmed)

Point-in-time snapshot: what each worker is doing now / touched most recently.

```jsonc
{
  "workers": [
    {
      "user": { "client_id": "usr_…", "username": "…", "profile_picture": null, "last_online": null },
      "last_interacted_step": {           // full resume-card payload | null
        "client_id": "tsp_…",
        "state": "working"
        // …same nested step payload as today (unchanged)…
      },
      "batch": {                          // object | null
        "count": 3,
        "step_ids": ["tsp_…", "tsp_…", "tsp_…"],   // sorted
        "shared_entered_at": "2026-07-18T13:00:00+00:00",
        "state": "working"                // majority state of the cohort
      }
    }
  ],
  "workers_pagination": { "has_more": false, "limit": 50, "offset": 0, "total": 12 }
}
```

- `last_interacted_step` — **unchanged** from today: the same full nested payload as the worker-facing resume-card, **with `cases_summary` omitted** (it's viewer-relative and meaningless for a manager viewing another worker). `null` when the worker has no step records.
- `batch` — `null` for a single-step interaction or a non-batch representative. `state` is the deterministic majority state of the cohort (from that worker's own latest record per step; can differ from the globally-latest state shown inside `last_interacted_step`).
- **Removed here:** `daily_stats`, `running`, `insights` → now on `/totals` and `/insights`.

## 2) `GET /api/v1/worker-stats/totals` (new)

The worker's settled daily totals plus the live running add-on. **This is where the future date-range lives** (see "Coming next").

```jsonc
{
  "workers": [
    {
      "user": { … },
      "daily_stats": {                    // settled-only; always present (zeros if idle)
        "work_date": "2026-07-18",
        "total_working_seconds": 3600,
        "total_pause_seconds": 600,
        "total_completed_count": 5
      },
      "running": {                        // live add-on for currently-open intervals
        "working_seconds": 900, "pause_seconds": 2400, "ended_shift_seconds": 0,
        "working_open_count": 1, "pause_open_count": 3, "ended_shift_open_count": 0,
        "as_of": "2026-07-18T12:00:00+00:00"
      }
    }
  ],
  "workers_pagination": { … }
}
```

**`daily_stats`** (moved verbatim from the old combined endpoint):
- Always present, one per worker, never `null` (all-zero when idle).
- `work_date` echoes the resolved day (`YYYY-MM-DD`, UTC).
- Bucketing: UTC calendar day; completed-count buckets on the completion moment, worked/paused time buckets on when each interval began — the three numbers do **not** reconcile to one timeline.
- **Settled-only** — in-progress intervals are not in here until they close; that's what `running` is for.

**`running`** (moved verbatim):
- Live total = `daily_stats + running`, per state:
  - `liveWorking = daily_stats.total_working_seconds + running.working_seconds`
  - `livePause   = daily_stats.total_pause_seconds   + running.pause_seconds`
- **Tick rule (important — concurrency-averaged):** advance a worker's live total at **real time — `+1s` per real second per state while that state's `*_open_count` > 0**, **not** `open_count × elapsed`:
  ```
  elapsed = (Date.now() - Date.parse(running.as_of)) / 1000
  displayWorking = liveWorking + (running.working_open_count > 0 ? 1 : 0) * elapsed
  displayPause   = livePause   + (running.pause_open_count   > 0 ? 1 : 0) * elapsed
  ```
  (Batch steps split real time, so N open steps still advance the worker total at 1×, not N×.) Re-poll to resync (`as_of` refreshes each response). Full rationale in `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`.
- `running` is meaningful only for **today**; a past `work_date` returns all zeros.
- `pause_open_count` is commonly `> 1` (auto-pause stacks open pauses) — expected; the sum already includes them all. `COMPLETED` is terminal, never in `running`.

## 3) `GET /api/v1/worker-stats/insights` (new)

Ranked, capped (0–3) observations about the worker on `work_date` vs their own recent baseline. **Render copy client-side from `code` + numbers** — the server sends no prose.

```jsonc
{
  "workers": [
    {
      "user": { … },
      "insights": [
        {
          "code": "completion_surge",   // positive/negative event key
          "polarity": "positive",       // "positive" | "negative" → styling
          "metric": "completed_count",
          "target_value": 8.0,          // the day's value
          "baseline_value": 3.0,        // baseline compared against
          "delta": 5.0,
          "delta_pct": 1.667,           // null when baseline is 0
          "sample_size": 4,             // how many past days the baseline used
          "severity": "high"            // "low" | "medium" | "high"
        }
      ]
    }
  ],
  "workers_pagination": { … }
}
```

- `insights` is always present (possibly `[]` — an empty list is normal, especially for new workers with little history).
- Codes (will grow — treat unknown codes as ignorable): `completion_surge`/`completion_dip`, `deep_focus`, `faster_pace`/`slower_pace`, `rising_pauses`, `leaving_steps_mid_shift`, `choppy_work`, `quality_watch`, `on_a_roll`.
- Baseline = same weekday over previous weeks (widens over time). In-progress day: volume-based insights (completions, shift-ends) are withheld until the day is over; ratio-based ones (focus, pauses) can still appear.
- List is pre-sorted strongest-first; use `severity` for emphasis. `sample_size` is worth surfacing ("vs your last 3 Wednesdays").

## Suggested frontend integration

1. On roster load, fire the **three requests in parallel** with the same `limit`/`offset`/`work_date`.
2. Build a `Map<client_id, {step, totals, insights}>` and render one card per worker.
3. Poll cadences can differ: `/last-interacted-steps` and `/totals` frequently (live), `/insights` rarely.
4. Tick the live total locally from `running` per the rule above between `/totals` polls.
5. A worker missing from one response's page (shouldn't happen given identical ordering) → render that section empty, don't block the card.

## Coming next (design for it now, not required yet)

- **Date range** will be added to `/totals` **and** the drill-down `/{user_id}/daily-steps` **together** (the breakdown is the drill-down behind the totals and must cover the same range). `/last-interacted-steps` remains a snapshot and `/insights` retains its own daily baseline window.
- **Trusted / wasted / estimated time** will be added to `/totals` and the breakdown (records with inaccurate timing, patched via a user-chosen strategy). It will be **additive** fields (`time_quality`, `estimated_fill`, …); the shapes above won't break. Separate handoff will follow.

## Trace links

- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_endpoint_split_20260718.md`
- Live-running tick math (still applies to `/totals`): `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`
- Drill-down (unchanged): `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`
- Superseded roster shape (pre-split, for reference only): `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
