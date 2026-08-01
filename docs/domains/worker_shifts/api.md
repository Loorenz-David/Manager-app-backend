# Worker Shifts API

Base paths: `/api/v1/worker-shifts/` and `/api/v1/worker-stats/`
Auth: all endpoints require `Authorization: Bearer <access_token>`.

Every response is wrapped: `{ "ok": true, "data": {...} }` on success,
`{ "ok": false, "error": "..." }` on failure.

---

## Who may act on whose shift

Every endpoint under `/worker-shifts/` accepts an optional `user_id` and resolves the target the same
way:

| Caller role | `user_id` omitted | `user_id` names another worker |
|---|---|---|
| `worker` | Acts on self | `403` — workers may only manage their own shift |
| `manager` / `admin` | `403` — must select a worker | Acts on that worker |

A manager or admin therefore cannot clock themselves in through these endpoints. The target must
also be a worker in the caller's workspace.

`403` messages: `"Workers may only manage their own shift."` /
`"Managers and admins must select a worker."`

---

## `GET /api/v1/worker-shifts/current`

Live shift state for the UI. Query param `user_id` optional, resolved per the table above.

Returns the worker's current state, when it started, and — when paused — what for. A pause is
described by a reason object whether the worker chose it from the catalog or the system paused them
itself; the object's shape is the same either way, and its `id` is a catalog id in the first case
and a transition reason in the second. Older records carrying plain text instead of either surface
it as `reason_text`.

Use this whenever you need to know what a worker is doing **now**. It is the authoritative live
read; never infer current state from a cached list.

---

## `POST /api/v1/worker-shifts/clock-in`

```json
{ "user_id": "usr_…" }
```

→ `200`

```json
{ "action": "clock_in", "user_id": "usr_…" }
```

- Already clocked in → `409` `"Worker is already clocked in."`

Clock-in responses carry **no** `analytics` key.

---

## `POST /api/v1/worker-shifts/clock-out`

```json
{ "user_id": "usr_…" }
```

→ `200`

```json
{
  "action": "clock_out",
  "user_id": "usr_…",
  "transitioned_steps": 2,
  "analytics": { }
}
```

- Not clocked in → `409` `"Worker is not clocked in."`
- `transitioned_steps` — task steps this clock-out paused because the worker was still working
  them. Steps the worker had already paused are not counted and not touched.
- `analytics` — the worker's day summary, or **`null`**.

**The clock-out time is decided by the server.** Any `clock_out_at` in the request body is ignored.

**`analytics` is always nullable.** It is composed *after* the shift is closed, outside the write
transaction, so that a failure computing statistics can never fail or roll back a clock-out. When
composition fails, the shift is still closed, the response is still `200`, and `analytics` is `null`
in full — never partially populated. Callers must always handle `null`.

Clock sources other than HTTP (the external integration, the overnight safeguard) close shifts
through the same core but never compute analytics.

### The `analytics` object

Scoped to the clock-out date, read from the **rebuilt** timeline — these are the authoritative
numbers, not the live provisional ones.

| Key | Contents |
|---|---|
| `date` | The clock-out date |
| `timeline` | `working_seconds`, `pause_seconds`, `idle_seconds`, and `pause_by_reason` |
| `pause_reasons` | Lookup map resolving every key in `pause_by_reason` to a name, image and type |
| `completed_items` | One entry per item the worker completed that day |
| `completed_items_truncated` | Whether a defensive cap was hit |
| `week` | Monday–Sunday containing the date: per-day buckets plus totals |
| `rate` | Units per hour today against a recent-history baseline |

Two things that bite:

- `pause_by_reason` is keyed by pause-reason id **plus** the literal key `"unspecified"`, used when
  paused time cannot be attributed to a catalog reason. Do not assume every key is an id. Every key
  is guaranteed to resolve in `pause_reasons`; the `"unspecified"` entry carries a null type.
- `completed_items[].total_seconds` is **working time only** — pause and overnight time excluded, and
  task-level rather than this worker's share. An item blocked for three days reads as its hours of
  actual work.

---

## `POST /api/v1/worker-shifts/clock`

Toggle. Clocks in if out, out if in. Body and target resolution as above.

The response is whichever of the two shapes applies, including `analytics` on the clock-out branch
and no such key on the clock-in branch. Prefer the explicit endpoints when the intent is known;
this exists for a single-button UI.

---

## `POST /api/v1/worker-shifts/declared-states`

Declare what the worker is doing while off-task.

```json
{ "user_id": "usr_…", "pause_reason_id": "par_…", "description": "…" }
```

- `pause_reason_id` is **required** and must be a declarable reason in the workspace.
- `description` is required when the chosen reason demands one.
- Requires an open shift → `409` otherwise. Declaring never clocks anyone in.
- Declaring while a declaration is already open is a **switch**: the open one closes and the new one
  opens in the same transaction.
- Declaring **auto-pauses the worker's open working steps**, so the step record and the shift
  timeline agree.

---

## `POST /api/v1/worker-shifts/declared-states/close`

```json
{ "user_id": "usr_…" }
```

Closes the open declaration. Starting or resuming a task step also closes it automatically, so
explicit closing is for "I have stopped doing this and am not starting a task yet".

---

## Shared-device (floor) behaviour

A shared shop-floor terminal signs in once with the `floor` app scope and acts on behalf of workers
all day. Two things behave differently under that scope:

- **`GET /api/v1/users`** includes each worker's `clock_in_code` and their working sections. Regular
  manager and worker sessions never receive codes.
- The roster page limit is raised for floor sessions, so a large workspace is reachable in one
  request rather than by paging.

The device matches a typed code or email against its cached roster to decide **who**, then reads
`GET /worker-shifts/current` fresh to decide **what state** — the cache decides identity, never
state.

---

## `/api/v1/worker-stats/` — manager reporting

| Endpoint | Returns |
|---|---|
| `GET /last-interacted-steps` | Each worker's most recent step interaction |
| `GET /totals` | Aggregate working/pause/idle totals across workers |
| `GET /linear-timeline` | Per-worker day timelines, with a pause-reason lookup map |
| `GET /insights` | Derived observations over a period |
| `GET /{user_id}/daily-steps` | One worker's step-level day breakdown |
| `GET /{user_id}/linear-timeline` | One worker's timeline with per-segment drill-down |

These read the **derived** timeline. For a closed day that means the rebuilt, authoritative version;
for a day in progress it means the live provisional one, which may be revised at clock-out.

The clock-out summary and `GET /linear-timeline` share the same underlying day computation, so the
number a worker sees at clock-out and the number their manager sees cannot drift.
