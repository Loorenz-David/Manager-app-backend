# HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718`
- Updated at (UTC): `2026-07-18T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_endpoint_split_20260718.md`

## Backend delivery

The former combined worker-stats request is now split into three independently callable read endpoints. All are restricted to `ADMIN` and `MANAGER`, use the same `limit`/`offset` pagination, sort workers by `username ASC`, and return the same `workers_pagination` envelope.

The frontend should call the three endpoints in parallel and merge worker records by `user.client_id`.

### 1. Last interacted step

```http
GET /api/v1/worker-stats/last-interacted-steps
```

Query parameters:

- `limit` — default `50`, maximum `200`.
- `offset` — default `0`, minimum `0`.
- `work_date` — accepted for the established validation contract; the last-step snapshot itself is point-in-time and does not use date-scoped totals.

Per-worker shape:

```json
{
  "user": {},
  "last_interacted_step": {},
  "batch": null
}
```

`last_interacted_step` is `null` when the worker has no authored step-state records. When present, it contains the existing full step payload without `cases_summary`. `batch` is `null` unless the worker's latest interaction is a batch cohort.

### 2. Worker totals and live running time

```http
GET /api/v1/worker-stats/totals
```

Query parameters:

- `limit` — default `50`, maximum `200`.
- `offset` — default `0`, minimum `0`.
- `work_date` — optional `YYYY-MM-DD`; omitted means the current UTC date.

Per-worker shape:

```json
{
  "user": {},
  "daily_stats": {
    "work_date": "2026-07-18",
    "total_working_seconds": 3600,
    "total_pause_seconds": 600,
    "total_completed_count": 5
  },
  "running": {
    "working_seconds": 600,
    "pause_seconds": 0,
    "ended_shift_seconds": 0,
    "working_open_count": 1,
    "pause_open_count": 0,
    "ended_shift_open_count": 0,
    "as_of": "2026-07-18T14:00:00+00:00"
  }
}
```

`daily_stats` contains settled time only. For today, show live time as `daily_stats + running`. `running` is zero-filled for a past `work_date`. The running seconds are concurrency-averaged for batch work; worker-level live time advances at real time while each batch step receives its averaged share.

### 3. Worker insights

```http
GET /api/v1/worker-stats/insights
```

Query parameters:

- `limit` — default `50`, maximum `200`.
- `offset` — default `0`, minimum `0`.
- `work_date` — optional `YYYY-MM-DD`; omitted means the current UTC date.

Per-worker shape:

```json
{
  "user": {},
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
```

Insights remain daily. They compare the selected `work_date` with the worker's own same-weekday history. An empty list is normal. When the selected date is today, volume-based insights are withheld while ratio-based insights may still appear.

## Shared pagination envelope

```json
{
  "workers_pagination": {
    "has_more": false,
    "limit": 50,
    "offset": 0,
    "total": 2
  }
}
```

## Date semantics

All date filtering uses the UTC calendar day. The planned date-range change is deferred and must be implemented jointly for `/totals` and `/{user_id}/daily-steps` so their totals and drill-down remain reconcilable.

## Errors

- `401`: missing or invalid authentication.
- `403`: caller is not `ADMIN` or `MANAGER`.
- `422`/validation error: invalid `work_date` format (`YYYY-MM-DD`), according to the existing response error mapping.

## Trace links

- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_endpoint_split_20260718.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_endpoint_split_20260718.md`
- Related live-totals handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`
