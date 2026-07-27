# HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Owner agent: `claude-opus-4-8`
- Status: **implemented**
- Supersedes (for these two endpoints only): the `work_date`/`daily_stats` shapes in `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md` and `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`.

## TL;DR — what is changing

Two worker-stats endpoints now take an **inclusive date range** instead of a single `work_date`:

- `GET /api/v1/worker-stats/totals`
- `GET /api/v1/worker-stats/{user_id}/daily-steps`

> ⚠️ **Breaking (hard change).** The `work_date` param is **removed** from these two endpoints and replaced by `date_from` / `date_to`. The `daily_stats` object and the breakdown's top-level date field also change shape (see below). Migrate both call sites together.

**Unchanged:** `GET /worker-stats/last-interacted-steps` (snapshot, no date) and `GET /worker-stats/insights` (still single `work_date`, its own baseline window) are **not** affected by this change.

## The new range params (both endpoints)

- `date_from` — optional `YYYY-MM-DD`, inclusive start.
- `date_to` — optional `YYYY-MM-DD`, inclusive end.
- Omit both → **today → today** (single-day, server UTC), so the default behaves like the old no-param call.
- To ask for a single day, set `date_from == date_to`.
- Validation (`422`): either date unparseable; `date_to < date_from`; or a span wider than **366 days**.

## 1) `GET /worker-stats/totals`

`daily_stats` is now a **range summary** (summed across the range), not a single day:

```jsonc
{
  "workers": [
    {
      "user": { "client_id": "usr_…", "username": "…", "profile_picture": null, "last_online": null },
      "daily_stats": {
        "date_from": "2026-07-01",         // ⬅ was "work_date"
        "date_to":   "2026-07-18",
        "total_working_seconds": 129600,   // Σ over the range
        "total_pause_seconds":   21600,
        "total_completed_count": 42
      },
      "running": {
        "working_seconds": 900, "pause_seconds": 2400, "ended_shift_seconds": 0,
        "working_open_count": 1, "pause_open_count": 3, "ended_shift_open_count": 0,
        "as_of": "2026-07-18T12:00:00+00:00"
      }
    }
  ],
  "workers_pagination": { "has_more": false, "limit": 50, "offset": 0, "total": 12 }
}
```

- `daily_stats` — **settled** totals summed over `[date_from, date_to]`. Field set is the same as before (`total_working_seconds`, `total_pause_seconds`, `total_completed_count`) — only `work_date` → `date_from`/`date_to`.
- `running` — **unchanged shape and meaning**: the live time of currently-open intervals. It is only ever non-zero for **today**, so it is populated as a slice **when the range includes today** and is all-zeros otherwise (e.g. a purely historical range). Live total = `daily_stats.total_working_seconds + running.working_seconds`, ticked per the concurrency-averaged rule (`+1s/sec while `working_open_count` > 0`) documented in `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`.

## 2) `GET /worker-stats/{user_id}/daily-steps`

The drill-down now aggregates the per-step breakdown over the **same range** (so it reconciles with `/totals` for the same `date_from`/`date_to`).

```jsonc
{
  "user": { … },
  "date_from": "2026-07-01",              // ⬅ replaces "work_date"
  "date_to":   "2026-07-18",
  "totals": { "working_seconds": …, "pause_seconds": …, "ended_shift_seconds": …, "completed_count": … },
  "daily_stats": {                         // maintained-table totals, summed over the range
    "date_from": "2026-07-01",
    "date_to":   "2026-07-18",
    "total_working_seconds": …, "total_pause_seconds": …,
    "total_ended_shift_seconds": …, "total_completed_count": …
  },
  "running": { … },                        // same shape; today-slice if range includes today, else zeros
  "steps": { "items": [ … ], "limit": 50, "offset": 0, "has_more": false }
}
```

What changes semantically over a range (everything else in the breakdown is as before):

- **`totals`** and each step's **`contribution`** — aggregate the worker's concurrency-averaged time over **all days in the range**, not one day.
- **`completed_count`** (totals + per-step) — completions that landed **anywhere in the range**.
- **`last_activity_at` / `last_completed_at`** — the latest such moment **within the range**.
- **`?sort_by=completed`** — still "only steps completed", now meaning completed **within the range**, ordered by completion time.
- **`active_record`** (per step) and **`running`** — "currently open", so meaningful only when the range includes today; a purely historical range yields `active_record: null` / zero running.
- Sorting, paging (`limit`/`offset`, `has_more`), and all other fields are unchanged. Note a wide range can list many more steps — page accordingly.

## Frontend action

1. Replace `work_date=YYYY-MM-DD` with `date_from`/`date_to` on **both** endpoints (send neither for "today").
2. Read range totals from `daily_stats.date_from`/`date_to` + the summed `total_*` (the `work_date` key is gone on these two).
3. Keep the live-total behavior only when the range includes today (backend already zeroes `running` otherwise).
4. When drilling from a range totals view into `/{user_id}/daily-steps`, pass the **same** `date_from`/`date_to` so the numbers reconcile.

## Not in this change (heads-up)

Trusted/wasted/estimated time (records with inaccurate timing, patched by a chosen strategy) is a **separate** upcoming change — it will add fields to `/totals` and the breakdown and **won't** alter the range params established here. When it lands, the median/IQR estimation sample uses a fixed rolling lookback **decoupled from this view range**.

## Trace links

- Source plan: date-range step of the worker-stats sequence (split → **range** → inaccurate-time).
- Split contract: `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md`.
- Running tick math: `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`.
