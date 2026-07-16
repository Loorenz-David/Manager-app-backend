# HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716`
- Created at (UTC): `2026-07-16T13:00:00Z`
- Owner agent: `claude-opus-4-8`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_worker_daily_step_breakdown_20260716.md`

## Backend delivery context

- New manager-only drill-down: `GET /api/v1/worker-stats/{user_id}/daily-steps`.
- Companion to `/worker-stats/last-interacted-steps` — that gives each worker's **daily totals**; this shows **which task steps produced them** for one worker on one day.
- Read-only; `ADMIN`/`MANAGER` only.

## Interface details

- Endpoint: `GET /api/v1/worker-stats/{user_id}/daily-steps`
- Auth: `ADMIN` or `MANAGER`.
- Path: `user_id` — the worker to drill into (must be an active member of your workspace).
- Query:
  - `work_date` — optional `YYYY-MM-DD`; default = server UTC today.
  - `limit` (default 50, max 200), `offset` (≥ 0).
  - `sort_by` — one of `contribution` (default), `working`, `paused`, `completed`, `last_activity`.
  - `order` — `desc` (default) or `asc`.

Full serialization of every field (`jsonc` — comments annotate type / nullability; they are not in the wire response):

```jsonc
{
  "user": {                                  // serialize_user_worker_stat
    "client_id": "usr_…",
    "username": "Andrii",
    "profile_picture": "https://… | null",
    "last_online": "2026-07-16T08:00:00+00:00 | null"   // ISO 8601 | null
  },
  "work_date": "2026-07-16",                 // the day these figures cover (UTC)

  "totals": {                                // settled breakdown total, full day
    "working_seconds": 3600,                 // int (seconds)
    "pause_seconds": 600,
    "ended_shift_seconds": 0,
    "completed_count": 1
  },
  "daily_stats": {                           // maintained daily totals (reconciliation)
    "work_date": "2026-07-16",
    "total_working_seconds": 3600,
    "total_pause_seconds": 600,
    "total_ended_shift_seconds": 0,
    "total_completed_count": 1
  },
  "running": {                               // live add-on for open intervals (today only; zeros otherwise)
    "working_seconds": 900, "pause_seconds": 2400, "ended_shift_seconds": 0,
    "working_open_count": 1, "pause_open_count": 2, "ended_shift_open_count": 0,
    "as_of": "2026-07-16T12:00:00+00:00"
  },

  "steps": {
    "items": [
      {
        // ── the step (serialize_step) ──────────────────────────────
        "client_id": "tsp_…",
        "task_id": "tsk_…",
        "state": "working",                  // pending | working | paused | ended_shift | blocked | completed | skipped | failed | cancelled
        "readiness_status": "ready",         // blocked | partial | ready
        "sequence_order": 1,                 // int | null
        "working_section_id": "wsec_…",
        "assigned_worker_id": "usr_… | null",
        "total_dependencies": 0,             // int
        "completed_dependencies": 0,         // int
        "working_section_name_snapshot": "Assembly",
        "assigned_worker_display_name_snapshot": "… | null",
        "created_at": "2026-07-15T09:00:00+00:00 | null",   // ISO | null
        "closed_at": "… | null",
        "ready_by_at": "… | null",
        // step LIFETIME totals (all workers, all time) — NOT this day/worker; use `contribution` instead
        "total_working_seconds": 7200,       "total_pause_seconds": 1200,   "total_ended_shift_seconds": 0,
        "total_working_count": 3,            "total_pause_count": 2,        "total_ended_shift_count": 0,
        "total_issues_count": 0,             "total_issues_resolved_count": 0,
        "total_cost_minor": 1500,            // int | null (minor units / cents)

        // ── task (serialize_task_light) | null ─────────────────────
        "task": {
          "client_id": "tsk_…",
          "task_type": "internal",           // enum
          "priority": "normal",              // enum
          "state": "assigned",               // enum
          "return_source": "… | null",       // enum | null
          "item_location": "… | null",       // enum | null
          "ready_by_at": "… | null",         // ISO | null
          "scheduled_start_at": "… | null",  // ISO | null
          "scheduled_end_at": "… | null",    // ISO | null
          "return_method": "… | null"        // enum | null
        },

        // ── primary item (serialize_item_worker_light) | null ──────
        "item": {
          "client_id": "itm_…",
          "article_number": "ART-123 | null",
          "sku": "SKU-9 | null",
          "state": "…",                      // enum
          "item_category_id": "… | null",
          "quantity": 1,                     // int
          "item_position": "… | null",
          "item_zone": "… | null",
          "upholstery_requirement": [        // [] when none
            {
              "client_id": "iur_…",
              "item_upholstery_id": "iup_…",
              "upholstery_id": "uph_… | null",
              "state": "…",                  // enum
              "source": "…",                 // enum
              "amount_meters": 2.5           // float | null
            }
          ]
        },

        // ── item_images: [] ; the FIRST is rich, the rest are light ─
        "item_images": [
          {                                  // [0] serialize_image (annotations list omitted)
            "client_id": "img_…",
            "image_url": "https://… (presigned GET, 24h TTL)",
            "storage_provider": "…",         // enum
            "source_type": "…",              // enum
            "source_reference": "… | null",
            "width_px": 1024,                // int | null
            "height_px": 768,                // int | null
            "file_size_bytes": 234567,       // int | null
            "created_at": "…Z",              // ISO
            "last_event": {                  // object | null
              "client_id": "…", "event_type": "…", "state": "…",
              "created_at": "…Z", "last_error": "… | null"
            },
            "events": [],                    // always [] on this endpoint
            "image_annotation": {            // first annotation | null
              "client_id": "…", "annotation_type": "…",
              "data": { }, "accuracy": 95, "created_at": "…Z"
            }
          },
          {                                  // [1..] serialize_image_light
            "client_id": "img_…",
            "image_url": "https://…",
            "width_px": 1024, "height_px": 768, "file_size_bytes": 234567
          }
        ],

        // ── per-worker, per-day SETTLED contribution (use this) ────
        "contribution": {
          "working_seconds": 3600,           // int (seconds)
          "pause_seconds": 600,
          "ended_shift_seconds": 0,
          "completed_count": 1
        },

        // ── currently-running interval | null (time-bearing states only) ─
        "active_record": {
          "state": "working",               // working | paused | ended_shift  (never completed)
          "entered_at": "2026-07-16T11:00:00+00:00"   // ISO — start of the running interval
        },
        "last_activity_at": "2026-07-16T11:00:00+00:00",   // ISO — most recent record entered_at
        "last_completed_at": "2026-07-16T10:10:00+00:00"   // ISO | null — completion time, null if not completed today
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

## Reading the payload

- **`contribution`** — this worker's **settled** time/completions on that step **for that day**. This is the field to display per step. It excludes any currently-running interval.
- **Step lifetime totals vs `contribution`** — the item also carries `total_working_seconds`, `total_completed_count`, etc. from the step serializer. Those are the step's **all-time totals across all workers** — *not* today's per-worker figures. For "what this worker did today," use **`contribution`**, not the `total_*` fields.
- **`active_record`** — the currently-open (running) interval for that worker on that step, `{state, entered_at}`, or `null`. Running time is **not** in `contribution`/`totals`. To show it live: `running = now − active_record.entered_at`, and **add it to the metric matching `active_record.state`** (`working` → working, `paused` → pause, `ended_shift` → ended-shift) — display-only. Completed steps have `active_record: null`.
- **`last_activity_at`** / **`last_completed_at`** — timestamps for display ("last worked / completed at"); `last_completed_at` is `null` if not completed that day.
- **`totals`** — the day's settled breakdown total (sum over all steps, before any sort/filter/paging).
- **`daily_stats`** — the maintained daily totals. Normally equal to `totals`; may be **higher** if a step that contributed was later deleted (its time lives on in `daily_stats` but not in the visible breakdown). Show both if you want to expose that gap.
- **`running`** (top-level, alongside `totals`) — the live time of the worker's currently-open intervals summed per state (= the per-step `active_record`s added up for you). Settled `totals` exclude it; show a live total as `totals + running` and tick it locally. Full shape + ticking math in `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`. Zeros for a past `work_date`.

## Sorting & the `completed` filter

- `contribution` (default): the **active** step first (what they're doing now), then biggest worked, then most completed.
- `working` / `paused`: biggest that-metric contribution first (`order` flips).
- `last_activity`: most recently active first (`order=asc` for oldest first).
- **`completed` is a filter + sort**: it returns **only the steps completed that day**, ordered by completion time (`desc` = most recent first). `totals` still reflect the **full day**, so under `sort_by=completed` the listed steps are a subset and won't sum to `totals`.

Page order is stable for identical requests (sort keys are settled values/timestamps, never the live running time), so `limit`/`offset` paging is safe.

## Response variants (what you can get back)

**A. Empty day** — the worker did nothing on `work_date` (or the day hasn't started). Always a valid `200`, never an error:

```json
{ "user": {…}, "work_date": "2026-07-16",
  "totals": { "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0, "completed_count": 0 },
  "daily_stats": { "work_date": "2026-07-16", "total_working_seconds": 0, "total_pause_seconds": 0,
                   "total_ended_shift_seconds": 0, "total_completed_count": 0 },
  "steps": { "items": [], "limit": 50, "offset": 0, "has_more": false } }
```

**B. Currently working** — a step with a running interval. `contribution` is `0` (nothing settled yet); `active_record` carries the start. Under the default `contribution` sort it's first:

```json
{ "client_id": "tsp_b", "state": "working", "…": "…",
  "contribution": { "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0, "completed_count": 0 },
  "active_record": { "state": "working", "entered_at": "2026-07-16T11:00:00+00:00" },
  "last_activity_at": "2026-07-16T11:00:00+00:00", "last_completed_at": null }
```

**C. `?sort_by=completed`** — only completed steps, newest completion first; `totals` still the full day (so `items` sum ≤ `totals`):

```json
{ "totals": { "working_seconds": 3600, "…": "full day" },
  "steps": { "items": [
     { "client_id": "tsp_done", "state": "completed", "…": "…",
       "contribution": { "…": "…", "completed_count": 1 },
       "active_record": null, "last_completed_at": "2026-07-16T10:10:00+00:00" }
  ], "…": "…" } }
```

(A finished step always has `active_record: null` — a completed record is terminal, not a running interval.)

## Error cases

- `401`: missing/invalid auth.
- `403`: caller is not `ADMIN`/`MANAGER`.
- `404`: `{user_id}` is not an active member of your workspace.
- `422`: invalid `work_date`, `sort_by`, or `order`.

## Validation notes

- Backend static validation: compileall + Ruff clean; both routes register.
- Integration tests (real PostgreSQL): settled totals vs open `active_record` and reconciliation; `sort_by=completed` filters to completed while `totals` stay full-day — passing.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_worker_daily_step_breakdown_20260716.md`
- Related: `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
