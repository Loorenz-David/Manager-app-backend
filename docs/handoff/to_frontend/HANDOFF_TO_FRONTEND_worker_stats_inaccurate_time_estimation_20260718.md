# HANDOFF_TO_FRONTEND_worker_stats_inaccurate_time_estimation_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_inaccurate_time_estimation_20260718`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Last updated at (UTC): `2026-07-19T00:00:00Z`
- Owner agent: `codex`
- Status: **implemented**
- Source plan: `docs/architecture/archives/implementation/PLAN_inaccurate_time_estimation_strategies_20260718.md`

## Changelog

- `2026-07-19` — **Default strategy is now `median`, not `mean`**, on both endpoints.
- `2026-07-19` — `time_quality.<state>` gained `trusted_sample_size` (confidence gate).
- `2026-07-19` — `/{user_id}/daily-steps` now lists **only steps the user worked or
  completed**; steps they merely created are no longer returned. Totals unaffected.
- `2026-07-19` — `sort_by=working|paused` are now **filter** intentions like `completed`,
  not sort-only: steps with nothing in that state are no longer listed. Totals unaffected.
- `2026-07-19` — documented the previously-omitted `daily_stats` and `running` keys on
  `/{user_id}/daily-steps`.

## Contract summary

The backend now exposes three alternatives for time in the existing inclusive-range
worker-stats views:

- `trusted`: persisted time whose step is not flagged inaccurate.
- `wasted`: persisted time from flagged steps; it is diagnostic and must not be added to trusted.
- `trusted + estimated_fill`: the manager-facing usable view. The frontend performs this final sum.

`wasted` and `estimated_fill` are never summed together.

## `/worker-stats/totals`

Existing range shape is unchanged apart from an additive `time_quality` block inside
`daily_stats`:

```jsonc
{
  "daily_stats": {
    "date_from": "2026-07-01",
    "date_to": "2026-07-18",
    "total_working_seconds": 129600,
    "total_pause_seconds": 21600,
    "total_completed_count": 42,
    "time_quality": {
      "strategy": "median",
      "working": {
        "trusted": 120000,
        "wasted": 9600,
        "inaccurate_step_count": 3,
        "estimated_fill": 10800.0,
        "trusted_sample_size": 47
      },
      "paused": {
        "trusted": 18000,
        "wasted": 3600,
        "inaccurate_step_count": 3,
        "estimated_fill": 2400.0,
        "trusted_sample_size": 12
      }
    }
  }
}
```

`time_quality.working` and `.paused` are the components to render. The backend
accepts `time_strategy=mean|median|iqr`; the default is **`median`** (robust to a few
long steps — the `mean` can badly overestimate on skewed data, so it's opt-in for a
cheaper/faster listing). The mean uses the grouped range aggregates only:

`inaccurate_step_count × trusted_state_seconds / (total_completed_count - inaccurate_step_count)`

Median/IQR use a worker × working-section sample from the fixed 28-day lookback ending
at `date_to`; fewer than four trusted per-step samples fall back to that section's stored mean.

> **Confidence gate (important).** Each state block carries **`trusted_sample_size`** — the
> number of trusted steps that actually backed **that state's** `estimated_fill` **under the
> selected strategy** (it lives *inside* `working`/`paused`, and working vs paused can differ):
> - `mean` → **view-range** trusted-completed count (`total_completed_count − inaccurate_step_count`).
> - `median`/`iqr` → the **28-day lookback** sample size that fed the estimate.
>
> Below the minimum (**4**) the estimate is suppressed to `0` (too little data to be meaningful —
> a tiny basis can explode the per-step average). So per state:
> - `trusted_sample_size >= 4` → `estimated_fill` is usable (higher = more confident).
> - `trusted_sample_size < 4` → `estimated_fill` is `0` by design; **render `trusted` + a "not enough data to estimate" hint**, and still show `wasted` so `trusted` isn't read as the whole day. Do **not** treat the `0` as "no wasted time."
>
> Note this is **strategy-aware**: under the default `median`, a worker with **0 trusted steps
> *today*** can still have a strong estimate if they have history (`trusted_sample_size` reflects
> the lookback, not today). Gate on the number, not on today's trusted total. Same field + rule
> on `/{user_id}/daily-steps` inside `daily_stats.time_quality.{working,paused}`.

> **Grain note (not a data bug).** On `/totals`, `mean` is computed at the **worker level**
> (pooled across all sections), while `median`/`iqr` are computed **per working-section and
> summed**. So switching strategy can change the fill by more than just the statistic — the two
> use different grains by design (mean is the free aggregate approximation; median/iqr are the
> precise per-section estimate). Don't treat a mean-vs-median gap as an inconsistency. The
> per-section drill-down on `/{user_id}/daily-steps` reconciles them.

## `/{user_id}/daily-steps`

The existing range parameters remain `date_from` and `date_to`. Add:

- `time_strategy=mean|median|iqr` — selects **only** the top-level `usable` total (default **`median`**, matching `/totals`). It does **not** affect `estimated`/`estimated_fill_by_strategy`, which always return all three real strategies (the sample is loaded on every request) so you can compare them regardless of the selected strategy. Because all three ship on every response, a strategy switch is a **client-side re-render — do not refetch**.
- `only_inaccurate=true` — returns only flagged steps.

> **Which steps are listed (changed 2026-07-19).** `steps.items` contains only steps this
> user **worked or completed** in the range — i.e. steps with a `working` / `paused` /
> `ended_shift` / `completed` record credited to them.
>
> Previously a step was listed if *any* record touched it, including the `pending` record
> written when the step is created. Since creation records carry `created_by_id` but
> deliberately leave `credited_user_id` NULL, the credit fallback read "created by" as
> "worked by": creating one task listed every sibling step with zero time — including steps
> assigned to **other** workers. On real data one worker-day went from 21 listed steps to 11,
> and all 10 removed had 0 seconds and 0 completions.
>
> **No total moved**, then or now: `totals`/`usable`/`wasted`/`estimated` have always been
> derived from time-bearing records only. If you were filtering out zero-time cards on the
> client as a workaround, you can drop that — but keep any handling for genuinely flagged
> steps, which legitimately report `contribution: 0` (their time is in `wasted`).

> **`sort_by` is a filter, not just an order (changed 2026-07-19).** All three intentions now
> scope the list to steps that actually contribute to that metric — each tab answers "where did
> *this* total come from", so a zero-contribution step would just render as a `0h 0m` card.
>
> | `sort_by` | lists |
> |---|---|
> | `working` | settled working time > 0, **or** currently working, **or** `is_time_inaccurate` |
> | `paused` | settled pause time > 0, **or** currently paused |
> | `completed` | completed in the range (unchanged) |
> | `contribution`, `last_activity` | unfiltered — "everything touched" views |
>
> Two deliberate inclusions, both of which would otherwise vanish:
> - **Live-but-zero**: a step paused *right now* with no settled pause time yet still appears
>   under `paused` (it is accruing — `active_record` drives the ticking timer).
> - **Flagged under `working`**: flagged steps carry `contribution: 0` by definition, with
>   their time in `wasted` / `estimated_fill_by_strategy`. They stay listed under `working`
>   precisely because they are what the estimation UI exists to show. They do **not** appear
>   under `paused` unless they hold real pause time.
>
> Totals are untouched — this only narrows `steps.items`. Expect visibly shorter lists: one
> real worker-day went from 9 listed steps under `paused` to 3.

The response keeps `totals` as trusted-only and adds:

```jsonc
{
  "date_from": "2026-07-17",
  "date_to": "2026-07-17",
  // Trusted-only: a flagged step contributes 0 seconds here (but keeps its completed_count).
  "totals": { "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0, "completed_count": 1 },
  // usable = totals + estimated[time_strategy]. With the default `median`: 0 + 1500.
  "usable": { "working_seconds": 1500, "pause_seconds": 240, "ended_shift_seconds": 0, "completed_count": 1 },
  // Diagnostic only — never add to totals or usable.
  "wasted": { "working_seconds": 3600, "pause_seconds": 600, "ended_shift_seconds": 0, "completed_count": 0 },
  // Always all three, regardless of `time_strategy`.
  "estimated": {
    "mean": { "working_seconds": 1800, "pause_seconds": 300, "ended_shift_seconds": 0, "completed_count": 0 },
    "median": { "working_seconds": 1500, "pause_seconds": 240, "ended_shift_seconds": 0, "completed_count": 0 },
    "iqr": { "working_seconds": 1620, "pause_seconds": 260, "ended_shift_seconds": 0, "completed_count": 0 }
  },
  "inaccurate_step_count": 1,
  "time_strategy": "median",
  // Same range-summed block as /totals, plus ended-shift. Carries `time_quality`
  // (incl. `trusted_sample_size`) for the SELECTED strategy — see the confidence gate above.
  "daily_stats": { "date_from": "…", "date_to": "…", "total_working_seconds": 0, "total_pause_seconds": 0,
                   "total_ended_shift_seconds": 0, "total_completed_count": 1, "time_quality": { /* … */ } },
  // Live open-interval seconds, all zeros unless the range includes today.
  "running": { "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0,
               "working_open_count": 0, "pause_open_count": 0, "ended_shift_open_count": 0, "as_of": "…" },
  "steps": {
    "items": [
      {
        "is_time_inaccurate": true,
        "contribution": { "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0, "completed_count": 1 },
        "wasted": { "working_seconds": 3600, "pause_seconds": 600, "ended_shift_seconds": 0, "completed_count": 0 },
        "estimated_fill_by_strategy": {
          "working": { "mean": 1800.0, "median": 1500.0, "iqr": 1620.0 },
          "paused": { "mean": 300.0, "median": 240.0, "iqr": 260.0 },
          "ended_shift": { "mean": 0.0, "median": 0.0, "iqr": 0.0 }
        },
        "inaccurate_records": [
          { "record_id": "ssr_…", "state": "working", "entered_at": "…", "exited_at": "…", "wasted_seconds": 3600.0 }
        ]
      }
    ]
  }
}
```

The frontend should render `usable` for the selected strategy and use `wasted` only
for diagnostics. `estimated` and `estimated_fill_by_strategy` are available for
side-by-side strategy comparison.

Per step, `contribution` is trusted-only and `estimated_fill_by_strategy[state][strategy]`
is its replacement — so a flagged step's displayed time is
`contribution + estimated_fill_by_strategy[state][strategy]`. `inaccurate_records` lists the
individual flagged intervals behind that step's `wasted`, for a drill-in diagnostic.

## Trace links

- Source plan: `docs/architecture/archives/implementation/PLAN_inaccurate_time_estimation_strategies_20260718.md`
- Prior range contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718.md`
- Prior endpoint split: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md`
- Step-scoping fix (2026-07-19): `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`
  (`_WORK_STATES` filter + the `_credited` docstring explaining the attribution trap);
  regression test `test_breakdown_excludes_steps_only_created_by_the_user`.
