# HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716`
- Created at (UTC): `2026-07-16T13:45:00Z`
- Owner agent: `claude-opus-4-8`
- Affects: `GET /api/v1/worker-stats/last-interacted-steps` and `GET /api/v1/worker-stats/{user_id}/daily-steps`

## ⚠️ Update 2026-07-18 — batch time is now concurrency-averaged

Time for **batchable** working sections is now split by real concurrency: when a worker runs N steps at once, each moment is divided by N. This changes how `running` ticks:

- **Worker-level total** (`daily_stats/totals + running`) advances at **real time** — i.e. `+1s per real second` per state while that state has any open interval — **not** `open_count × elapsed`. (The batch's per-step shares sum to real time.) So to tick a worker's live total: `+= (open_count > 0 ? 1 : 0) × elapsed` per state.
- `running.working_seconds` / `pause_seconds` / `ended_shift_seconds` are already the **averaged** running seconds at `as_of`; `*_open_count` still tells you how many steps are open (useful for per-step display).
- The **breakdown** endpoint's per-step `active_record` still ticks at `1/k` per step (a batch step accrues its fraction). Summed across the batch, they equal the worker-level real rate.

The field shapes are unchanged; only the numbers (averaged) and the tick rule (real-time, not `open_count×`) changed. Everything else below still holds.

## What changed & why

The daily totals we return (`daily_stats` on the list endpoint, `totals` on the breakdown) are **settled** figures — the analytics pipeline only books an interval's time when that interval **closes**. So while a worker is *currently* working or paused, that in-progress time is **not** in those totals yet. In particular, a worker can have **several** steps sitting in open PAUSE at once (each time they switch tasks, the previous one is auto-paused and stays open), and none of that pause time is counted until they return to it.

To let you show a **live** total without breaking the settled/reconcilable ones, both endpoints now return a **`running`** object: the summed running time of the worker's currently-open intervals. Keep `daily_stats`/`totals` as the source of truth; add `running` on top for a live view.

## The `running` object

```jsonc
"running": {
  "working_seconds": 3600,      // Σ(now − entered_at) over open WORKING intervals, at response time
  "pause_seconds": 17100,       // Σ over open PAUSED intervals (can be several — see below)
  "ended_shift_seconds": 0,     // Σ over open ENDED_SHIFT intervals
  "working_open_count": 1,      // how many intervals are open in each state …
  "pause_open_count": 3,        // … used to TICK the value locally
  "ended_shift_open_count": 0,
  "as_of": "2026-07-16T12:00:00+00:00"   // when the sums were computed (server UTC)
}
```

- Every field is always present. For a **past** `work_date` (or a worker with nothing open) all seconds/counts are `0` — there is no live running on a day that isn't today.
- `pause_open_count` is commonly **> 1**: auto-pause stacks open PAUSE records. That's expected — the sum already includes all of them.
- `COMPLETED` is terminal, not a running interval, so it never contributes to `running` (and there is no "running completed").

## How to read it

**Live total = settled + running:**

```
liveWorkingSeconds = daily_stats.total_working_seconds + running.working_seconds
livePauseSeconds   = daily_stats.total_pause_seconds   + running.pause_seconds
liveEndedShift     = daily_stats.total_ended_shift_seconds + running.ended_shift_seconds
```

(On the **breakdown** endpoint use `totals.working_seconds` / `.pause_seconds` / `.ended_shift_seconds` in place of `daily_stats.*`.)

**To keep it ticking between polls**, advance each metric by `open_count × elapsed`:

```
elapsed = (Date.now() - Date.parse(running.as_of)) / 1000       // seconds
displayWorking = liveWorkingSeconds + running.working_open_count      * elapsed
displayPause   = livePauseSeconds   + running.pause_open_count        * elapsed
displayEnded   = liveEndedShift     + running.ended_shift_open_count  * elapsed
```

The counts are why we send them: with 3 open pauses, pause advances by 3 seconds per real second. Re-fetch periodically to resync (`as_of` refreshes each response).

## No double-counting

`running` and the settled totals are disjoint. The instant an open interval **closes**, the analytics worker books it into the settled totals (`daily_stats`/`totals`) and it drops out of `running` on the next response. Time moves from one bucket to the other — never counted twice, never lost.

## Where each endpoint puts it

- **`/last-interacted-steps`** (roster): `running` is **per worker**, alongside that worker's `daily_stats`.
  ```jsonc
  { "workers": [ { "user": {…}, "daily_stats": {…}, "running": {…}, "insights": [...], "last_interacted_step": {…}, "batch": … } ] }
  ```
- **`/{user_id}/daily-steps`** (drill-down): `running` is **top-level**, alongside `totals`. Each step item also carries its own `active_record` (`{state, entered_at}`) if it's the open interval — `running` is just those summed for you.
  ```jsonc
  { "user": {…}, "work_date": "…", "totals": {…}, "daily_stats": {…}, "running": {…}, "steps": {…} }
  ```

## Notes

- `running` is computed only for `work_date == today` (server UTC); otherwise it's all zeros.
- Attribution and day-bucketing match the settled pipeline (credited user, UTC day of `entered_at`), so `running` is a clean add-on to the settled numbers.
- Both endpoints add one small extra query at most; response times are unaffected in practice.

## Trace links

- Related handoffs:
  - `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
  - `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`
