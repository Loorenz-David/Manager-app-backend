# HANDOFF_TO_FRONTEND_task_counts_endpoint_20260627

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_counts_endpoint_20260627`
- Created at (UTC): `2026-06-27T00:00:00Z`
- Owner agent: `codex`
- Source plan: —
- Source summary: —

## Backend delivery context

- What backend implemented:
  - A lightweight read-only endpoint that returns task counts for a given set of filters.
  - Counts are intentionally cheap: the service runs `COUNT` queries only — no row hydration, no serialization overhead.
  - The response has two parts: a `total` (all requested filters applied together) and a `granularity` object that breaks down the count per individual value for each filter dimension that was included in the request.
- API or contract changes:
  - New endpoint: `GET /api/v1/tasks/counts`
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use `GET /api/v1/tasks/counts` to populate badge counts, filter pills, or summary cards without triggering a full task list fetch.
2. Pass only the filter dimensions whose per-value breakdown is actually needed — unneeded dimensions add round-trip `COUNT` queries on the backend.
3. Granularity keys are only present in the response when the corresponding query param was supplied. Check for key presence before reading.
4. Counts in `granularity` are not additive to `total`. Each per-value count is calculated with all other active filters still applied.

## Interface details

### Response envelope (all success cases)

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

### Error envelope (all failure cases)

```json
{
  "ok": false,
  "error": "Human-readable message"
}
```

---

### GET /api/v1/tasks/counts

- Auth and role access: `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Method: `GET`
- Path: `/api/v1/tasks/counts`

#### Query parameters

All parameters are optional. Each accepts a comma-separated string of one or more values from the allowed set. Unrecognized values are passed to the database as-is and will return `0` for that key.

| Param | Type | Allowed values |
|---|---|---|
| `task_states` | CSV string | `pending`, `assigned`, `working`, `stalled`, `ready`, `resolved`, `failed`, `cancelled` |
| `task_step_states` | CSV string | `pending`, `working`, `paused`, `ended_shift`, `blocked`, `completed`, `skipped`, `failed`, `cancelled` |
| `step_readiness_statuses` | CSV string | `blocked`, `partial`, `ready`, `waiting_for_upholstery` |
| `priorities` | CSV string | `low`, `normal`, `high`, `urgent` |
| `task_types` | CSV string | `return`, `pre_order`, `internal` |
| `return_sources` | CSV string | `after_purchase`, `before_purchase`, `store_return` |

#### Filtering semantics

- Filters across different dimensions are combined with **AND** (a task must match all supplied dimensions simultaneously).
- Values within the same dimension are combined with **OR** (a task matching any of the listed values qualifies for that dimension).
- `task_step_states` and `step_readiness_statuses` match tasks that have **at least one non-deleted step** satisfying the condition.
- Only non-deleted tasks (`is_deleted = false`) are counted.
- `granularity` per-value counts apply all other active filters, isolating only that one value within its own dimension.

---

#### Response: no params supplied

When called with no query params, `total` is the count of all non-deleted tasks in the workspace and `granularity` is an empty object.

```json
{
  "ok": true,
  "data": {
    "total": 318,
    "granularity": {}
  },
  "warnings": []
}
```

---

#### Response: single dimension

Request: `GET /api/v1/tasks/counts?task_states=pending,working,stalled`

```json
{
  "ok": true,
  "data": {
    "total": 87,
    "granularity": {
      "task_states": {
        "pending": 34,
        "working": 41,
        "stalled": 12
      }
    }
  },
  "warnings": []
}
```

- `total` — tasks that are in `pending` OR `working` OR `stalled`.
- `granularity.task_states.pending` — tasks that are specifically in `pending` (no other dimension filters apply here since none were passed).

---

#### Response: multiple dimensions

Request: `GET /api/v1/tasks/counts?task_states=pending,working&priorities=urgent,high`

```json
{
  "ok": true,
  "data": {
    "total": 42,
    "granularity": {
      "task_states": {
        "pending": 15,
        "working": 27
      },
      "priorities": {
        "urgent": 8,
        "high": 34
      }
    }
  },
  "warnings": []
}
```

- `total` — tasks that are (`pending` OR `working`) AND (`urgent` OR `high`).
- `granularity.task_states.pending` — tasks that are `pending` AND (`urgent` OR `high`). The priority filter is kept.
- `granularity.priorities.urgent` — tasks that are (`pending` OR `working`) AND `urgent`. The state filter is kept.
- Individual granularity values are **not** expected to sum to `total`.

---

#### Response: step-level filters

Request: `GET /api/v1/tasks/counts?task_step_states=blocked,working&step_readiness_statuses=ready,partial`

```json
{
  "ok": true,
  "data": {
    "total": 23,
    "granularity": {
      "task_step_states": {
        "blocked": 9,
        "working": 19
      },
      "step_readiness_statuses": {
        "ready": 11,
        "partial": 14
      }
    }
  },
  "warnings": []
}
```

- A task is counted under `task_step_states.blocked` if it has at least one non-deleted step in state `blocked` (while also satisfying the `step_readiness_statuses` filter).
- A task can appear under multiple step-state values if it has steps in different states simultaneously.

---

#### Response: all dimensions combined

Request:
```
GET /api/v1/tasks/counts
  ?task_states=pending,working
  &task_step_states=blocked
  &step_readiness_statuses=partial,ready
  &priorities=urgent
  &task_types=return,repair
  &return_sources=after_purchase,store_return
```

```json
{
  "ok": true,
  "data": {
    "total": 5,
    "granularity": {
      "task_states": {
        "pending": 2,
        "working": 3
      },
      "task_step_states": {
        "blocked": 5
      },
      "step_readiness_statuses": {
        "partial": 4,
        "ready": 1
      },
      "priorities": {
        "urgent": 5
      },
      "task_types": {
        "return": 3,
        "repair": 2
      },
      "return_sources": {
        "after_purchase": 4,
        "store_return": 1
      }
    }
  },
  "warnings": []
}
```

---

#### Response: a value that matches zero tasks

Values passed in the query params that match no tasks will appear in `granularity` with a count of `0`. They are never omitted.

```json
{
  "ok": true,
  "data": {
    "total": 3,
    "granularity": {
      "priorities": {
        "urgent": 3,
        "low": 0
      }
    }
  },
  "warnings": []
}
```

---

### Error cases

| Scenario | HTTP status | `error` message |
|---|---|---|
| Unauthenticated request | `401` | `"Unauthorized"` |
| Caller role not in `ADMIN`, `MANAGER`, `WORKER`, `SELLER` | `403` | `"Forbidden"` |
| `workspace_id` not resolvable from token | `400` | Varies |

No `404` is possible — counts return `0` for empty result sets.

## Validation notes

- Backend validation run: query params are parsed server-side; no schema validation on individual values — unrecognized enum strings return `0` counts rather than erroring.
- Suggested frontend validation: constrain UI controls to the allowed enum sets listed in the table above so users cannot construct requests with unknown values.

## Trace links

- Parent plan: —
- Parent summary: —
- Related debug plan (optional): —
