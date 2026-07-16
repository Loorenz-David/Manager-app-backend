# HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715`
- Created at (UTC): `2026-07-15T14:12:38Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_last_interacted_steps_20260715.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_daily_metrics_20260715.md`

## Backend delivery context

- Added `GET /api/v1/worker-stats/last-interacted-steps`.
- The route is read-only and restricted to `ADMIN` and `MANAGER`.
- It returns every active `worker`-role membership in the caller's workspace, including workers with no authored step records.

> **Delivery status — two waves.** Wave 1 (`last_interacted_step` + `batch` + pagination) and Wave 2 (per-worker `daily_stats` object + the `work_date` query param) are **live**. The full response shape below is the guaranteed contract.

## Frontend action required

1. Fetch the endpoint for the manager worker roster using `limit` and `offset`.
2. Render the nested `last_interacted_step` with the existing resume-card/step-card renderer.
3. Render a batch as one representative card with `+N in batch`; drill into members through existing per-step endpoints when needed.
4. Render each worker's `daily_stats`: worked time (`total_working_seconds`), paused time (`total_pause_seconds`), and steps completed today (`total_completed_count`). Format seconds → h/m on the client. `daily_stats` is always present (zeros when the worker has no activity for the day).
5. (Optional) Pass `work_date=YYYY-MM-DD` to view a specific day; omit it for "today".

## Interface details

- Endpoint: `GET /api/v1/worker-stats/last-interacted-steps`
- Auth: `ADMIN` or `MANAGER`.
- Request query:
  - `limit` — defaults to `50`, capped at `200`.
  - `offset` — defaults to `0`, must be non-negative.
  - `work_date` — optional, `YYYY-MM-DD`. Selects which day's `daily_stats` to return. Omit for the current day (server UTC date). An unparseable value returns a `422` validation error.

```json
{
  "workers": [
    {
      "user": {
        "client_id": "usr_…",
        "username": "…",
        "profile_picture": "…",
        "last_online": "2026-07-15T14:00:00+00:00"
      },
      "last_interacted_step": null,
      "batch": null,
      "daily_stats": {
        "work_date": "2026-07-15",
        "total_working_seconds": 0,
        "total_pause_seconds": 0,
        "total_completed_count": 0
      }
    },
    {
      "user": {
        "client_id": "usr_…",
        "username": "…",
        "profile_picture": null,
        "last_online": null
      },
      "last_interacted_step": {
        "client_id": "tsp_…",
        "state": "working"
      },
      "batch": {
        "count": 3,
        "step_ids": ["tsp_…", "tsp_…", "tsp_…"],
        "shared_entered_at": "2026-07-15T13:00:00+00:00",
        "state": "working"
      },
      "daily_stats": {
        "work_date": "2026-07-15",
        "total_working_seconds": 3600,
        "total_pause_seconds": 600,
        "total_completed_count": 5
      },
      "insights": [
        {
          "code": "completion_surge",
          "polarity": "positive",
          "metric": "completed_count",
          "target_value": 8.0,
          "baseline_value": 3.0,
          "delta": 5.0,
          "delta_pct": 1.667,
          "sample_size": 4,
          "severity": "high"
        }
      ]
    }
  ],
  "workers_pagination": {
    "has_more": false,
    "limit": 50,
    "offset": 0,
    "total": 2
  }
}
```

When present, `last_interacted_step` contains the same full nested payload shape as the existing worker-facing resume-card endpoint, **with one exception**: the `cases_summary` field is **omitted** here. That count is viewer-relative (unread for the requesting user), which is meaningless for a manager viewing another worker's step, so it is intentionally left out of this endpoint. Do not rely on `cases_summary` being present in this response.

`batch` is `null` for a single-step interaction or a non-batch-capable representative. Its `step_ids` are sorted, and its `state` is the deterministic majority state of the cohort as carried by the surfaced representative step (derived from that worker's own latest record on each step; it can differ from the step's globally-latest state shown inside `last_interacted_step` if another user acted on the step more recently).

### `daily_stats`

- Always present — one object per worker, never `null`. A worker with no activity for the day returns all-zero counters with `work_date` still echoed.
- `work_date` — the day these figures cover (`YYYY-MM-DD`); echoes the resolved `work_date` (the request param, or the server's UTC date when omitted).
- `total_working_seconds` / `total_pause_seconds` — integer seconds spent working / paused that day.
- `total_completed_count` — number of task steps this worker **completed** that day.
- Day semantics: stats are bucketed on the **UTC** calendar day; there is no per-user local timezone. Completed-count is bucketed on the **completion** moment; worked/paused time is bucketed on when each interval began — so a step worked just before midnight and completed just after will book its time on one day and its completion on the next. Don't expect the three numbers to reconcile to a single timeline.
- **`daily_stats` is settled-only** — currently-open (in-progress) intervals are not counted here until they close. Each worker also carries a **`running`** object with the live time of open intervals; show a live total as `daily_stats + running`. See `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md` for the shape and the ticking math.

### `insights`

A ranked, capped list (0–3) of noteworthy observations about the worker on `work_date`, comparing that day to the worker's **own** recent baseline. **Render copy client-side from `code` + the numeric fields** — the server sends no prose (so it localizes). An empty list is normal and common (a normal day).

Each insight:

| Field | Meaning |
|---|---|
| `code` | What to say. Current set: `completion_surge` / `completion_dip`, `deep_focus`, `faster_pace` / `slower_pace`, `rising_pauses`, `leaving_steps_mid_shift`, `choppy_work`, `quality_watch`, `on_a_roll`. Treat unknown codes as ignorable (the set will grow). |
| `polarity` | `"positive"` (recognize) or `"negative"` (attention) — drives styling. |
| `metric` | Underlying metric key (`completed_count`, `focus_ratio`, `avg_pause_seconds`, …). |
| `target_value` / `baseline_value` | The day's value and the baseline it's compared against. |
| `delta` / `delta_pct` | Signed difference; `delta_pct` is `null` when the baseline is 0. |
| `sample_size` | How many past days the baseline is built from — surface it for honesty ("vs your last 3 Wednesdays"). |
| `severity` | `"low" \| "medium" \| "high"` — use for ordering/emphasis; the list is already sorted strongest-first. |

Behavioral notes:
- **Baseline** = the same weekday over the previous weeks (widens over time); insights are suppressed until there's enough history (so new workers show none — that's expected, not an error).
- **In-progress day**: when `work_date` is today, volume-based insights (completions, shift-ends) are withheld because the day isn't over; ratio-based ones (focus, pauses) can still appear.
- `on_a_roll` is a streak — its `target_value` is the streak length in days, `baseline_value` the bar it cleared.

## Error cases

- `401`: missing or invalid authentication.
- `403`: caller is not `ADMIN` or `MANAGER`.
- `422`: `work_date` is present but not a valid `YYYY-MM-DD` date. *(Wave 2)*

## Validation notes

- Backend static validation passed: compileall, Ruff, and route registration/import checks.
- Combined analytics, daily-metrics, and existing extracted-payload regression suite passed (`9 passed`) against migrated local PostgreSQL.
- Alembic migration applied successfully to development and test databases.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_last_interacted_steps_20260715.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_daily_metrics_20260715.md`
- Related implementation plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_daily_metrics_20260715.md`
- Related debug plan: `—`
