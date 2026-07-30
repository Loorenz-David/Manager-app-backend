# HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729`
- Created at (UTC): `2026-07-29T12:00:00Z`
- Owner agent: `claude-fable-5`
- Source plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (phases 1–6)
- Source summary: pending (backend under construction)

> **STATUS: BUILD-AHEAD CONTRACT.** The backend for this surface is being implemented in parallel
> (phases 1–6 of the master plan). This document is the **authoritative API contract**: the backend
> implements to match it; the frontend builds against it now. Endpoint liveness is tracked here:
>
> | Backend phase | Endpoints | Live? |
> |---|---|---|
> | 5 | Floor sign-in / logout (§2) | ❌ not yet |
> | 4 | `GET /current`, `POST /clock-in`, `POST /clock-out` (§4, §5) | ❌ not yet |
> | 3 | Declared states (§6) | ✅ live (reviewed & approved) |
> | 6 | Roster `clock_in_code` exposure, `clock_in_code` management (§3) | ❌ not yet |
> | 7 | Populated clock-out `analytics` (§5.1) | ❌ not yet — `analytics` is `null` until then |
> | — | Pause reasons listing (§7) | ✅ live today (filter param may be added in phase 4) |
>
> Mock these shapes until the phase flips to ✅. Any contract change will be edited **here first**.

## 1. What this app is

A new always-on **shop-floor application** ("floor app") running on a shared device (wall tablet /
terminal). It signs in **once** with an admin or manager account under the new `floor` app scope and
receives a **non-expiring token** — the device stays authenticated forever until explicitly logged
out. Workers then use the device to clock in/out and to **declare states** (lunch, cleaning,
meeting, …) via a personal **clock-in code** or their **working email**, with a visual
"is this you?" confirmation step.

Key model facts the UI should reflect:

- A worker's day is a timeline of states: `started_shift` → (`idle` | `working` | `in_pause`)* → `ended_shift`.
- `working`/`in_pause` are driven automatically by task-step activity; **declared states** are the worker's own explanation of off-task time and render as `in_pause` with a catalog reason.
- Declaring **auto-pauses** the worker's active working steps under the declared reason. Starting/resuming a task step **auto-closes** an open declaration. Clock-out force-closes everything.
- Both this app **and Connecteam** write the same shift machinery during the transition period — a worker may already be clocked in when the device looks them up. Always render from server state, never assume.

## 2. Auth (floor scope)

### `POST /api/v1/auth/sign-in`

Request:
```json
{ "email": "manager@shop.com", "password": "…", "app_scope": "floor" }
```
(`username` may be used instead of `email`.)

Response `200`:
```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "access_token": "<JWT — NO EXPIRY>",
    "user": { "user_id": "usr_…", "username": "…", "workspace_id": "ws_…", "role_name": "manager", "app_scope": "floor", "time_zone": "Asia/Jerusalem", "…": "…" },
    "workspace_id": "ws_…"
  }
}
```

- Allowed roles for `app_scope="floor"`: **admin, manager**. Anything else → `403` `"Invalid credentials."` (message is intentionally opaque).
- **No refresh token / no cookie** is issued for this scope. Store `access_token` in secure device storage; send as `Authorization: Bearer <token>` on every call. Never put it in URLs or logs.
- The token never expires. Revocation = `POST /api/v1/auth/logout` (with the token) — permanent, takes effect within ≤60s server-side. A `401` on any call means the device was revoked → return to sign-in screen.
- Sign-in is rate-limited (10/min per IP).

## 3. Worker identification (kiosk step 1) — client-side matching

There is **no identify endpoint**. The device keeps the workspace's worker roster cached (TanStack
Query) and matches the typed code/email **locally**:

### `GET /api/v1/users?role=worker&compact=true&limit=200`

The existing roster endpoint. **For floor-scope sessions only**, each item additionally carries the
identification fields:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "users": [
      {
        "client_id": "usr_…",
        "username": "Mykola",
        "profile_picture": "https://…",
        "role": { "…": "…" },
        "clock_in_code": "4821",
        "email": "mykola@shop.com"
      }
    ]
  }
}
```

- `clock_in_code` is `null` until a manager assigns one (4–16 chars, unique per workspace). Email matching always works as the fallback.
- Regular manager/worker app sessions do **not** receive `clock_in_code`/`email` here — the fields exist only under a floor token.
- Suggested TanStack setup: `refetchInterval` of 1–5 min + refetch on window focus; the roster changes rarely.
- Matching rules: trim input; match code exactly; match email case-insensitively.

**The cache decides *who*, never *what state*.** After the worker confirms their identity
(photo + name), fetch `GET /current?user_id=…` (§4) fresh before rendering Clock in / Clock out /
Declare — the worker may have clocked in via Connecteam or another device since the last poll.

Unmatched input → handle entirely client-side ("No worker matches this code or email" — one message
for both cases; don't reveal which codes exist).

Notes: the code **identifies** — it does not authenticate. The human confirmation step and the
device's manager-authorized floor token are the trust anchors; every action endpoint re-validates
server-side regardless of what the device matched.

## 4. Current state

### `GET /api/v1/worker-shifts/current?user_id=usr_…`

Roles: admin/manager **must** pass `user_id`; a worker token (regular worker app) omits it (self).

Response `200` (`data`):
```json
{
  "user_id": "usr_…",
  "clocked_in": true,
  "shift_started_at": "2026-07-29T06:58:00Z",
  "state": "in_pause",
  "state_entered_at": "2026-07-29T09:12:00Z",
  "pause_reason": { "id": "par_…", "name": "Lunch break", "image_url": "https://…" },
  "declared_state": {
    "id": "uds_…",
    "pause_reason": { "id": "par_…", "name": "Lunch break", "image_url": "https://…" },
    "description": null,
    "entered_at": "2026-07-29T09:12:00Z"
  }
}
```

- `state` ∈ `idle | working | in_pause` while clocked in.
- Not clocked in → `{ "user_id": …, "clocked_in": false, "shift_started_at": null, "state": null, "state_entered_at": null, "pause_reason": null, "declared_state": null }`.
- `pause_reason` is set when `state == "in_pause"`; `declared_state` is non-null only when the pause is a worker declaration (vs a task-step blocker pause, where `declared_state` is `null` but `pause_reason` still describes the step's pause reason).
- Legacy edge: very old pauses may carry free text instead of a catalog reason → `pause_reason: null` plus additive `reason_text: "<raw>"`.
- All timestamps UTC ISO-8601; localize client-side using the workspace `time_zone` from sign-in. **Wire format note (applies to every timestamp in this document):** the backend serializes the UTC offset as `+00:00` (e.g. `2026-07-29T09:12:00+00:00`), not `Z`. The examples here use `Z` for brevity — treat the two as equivalent; parse with any ISO-8601 parser, don't string-match the suffix.

## 5. Clock actions (kiosk step 2)

All three: roles admin/manager **must** pass `user_id` (the confirmed worker); a worker token omits it. Errors: `404` unknown/non-worker target, `403` role/target violations.

### `POST /api/v1/worker-shifts/clock-in`
```json
{ "user_id": "usr_…" }
```
→ `200` `data`: `{ "action": "clock_in", "user_id": "usr_…" }`
- Already clocked in → `409` `"Worker is already clocked in."`

### `POST /api/v1/worker-shifts/clock-out`
```json
{ "user_id": "usr_…" }
```
→ `200` `data`:
```json
{ "action": "clock_out", "user_id": "usr_…", "transitioned_steps": 2, "analytics": null }
```
- Not clocked in → `409` `"Worker is not clocked in."`
- `transitioned_steps` = working task-steps the clock-out force-closed (worth surfacing: "2 active tasks were stopped").
- `analytics` = the worker's **day summary** (§5.1) — `null` until backend phase 7 lands, and `null` thereafter whenever the summary could not be computed (degraded mode). **Always handle `null`** by rendering the plain success screen without the stats panel.

### 5.1 The `analytics` object (clock-out day summary)

Everything is scoped to the clock-out's UTC date and reflects the **final, rebuilt** timeline (the
backend reconstructs the whole shift at clock-out — these numbers are authoritative, not the live
provisional ones).

```json
{
  "date": "2026-07-29",
  "timeline": {
    "date_from": "2026-07-29",
    "date_to": "2026-07-29",
    "working_seconds": 21600,
    "pause_seconds": 3600,
    "ended_shift_seconds": 0,
    "idle_seconds": 1800,
    "completed_count": 7,
    "pause_by_reason": { "par_…": 2700, "par_…2": 900 }
  },
  "segments": [
    {
      "start": "2026-07-29T06:58:00Z",
      "end": "2026-07-29T06:58:00Z",
      "state": "started_shift",
      "reason": null,
      "is_open": false,
      "manually_recorded": false,
      "seconds": 0,
      "steps": []
    },
    {
      "start": "2026-07-29T09:12:00Z",
      "end": "2026-07-29T09:42:00Z",
      "state": "paused",
      "reason": "par_…",
      "is_open": false,
      "manually_recorded": true,
      "seconds": 1800,
      "steps": []
    }
  ],
  "segments_truncated": false,
  "pause_reasons": {
    "par_…": { "name": "Lunch break", "image_url": "https://…", "pause_type": "personal" }
  },
  "insights": [
    {
      "code": "…", "polarity": "positive", "metric": "working_seconds",
      "target_value": 21600, "baseline_value": 19800, "delta": 1800,
      "delta_pct": 9.1, "sample_size": 12, "severity": "info"
    }
  ]
}
```

- `timeline` — the day resume for tiles/donuts: the four buckets partition the shift; `pause_by_reason` sums exactly to `pause_seconds`; keys resolve via `pause_reasons`.
- `segments` — the drawable timeline, ordered; `state` ∈ `started_shift | working | paused | idle | ended_shift` (markers have `seconds: 0`); worker-declared segments have `manually_recorded: true`; `steps` lists the task-step details behind working/paused blocks (same shape as the manager timeline endpoint — see the related handoff). `segments_truncated` is a safety cap flag (render what you got).
- `insights` — trend cards comparing the day against the worker's recent baseline. May be `[]` (not enough history). **Freshness caveat:** insights read aggregate day-stats that are updated asynchronously — seconds after clock-out they may not yet include the very last steps of the day. `timeline`/`segments` have no such lag. Treat insights as indicative, not as the payroll number.
- These are the same shapes as the manager endpoints (`GET /worker-stats/{user_id}/linear-timeline`, `GET /worker-stats/insights`) — components built for one render the other.
- Unknown extra keys may appear inside `analytics` later — ignore them (additive contract).

### `POST /api/v1/worker-shifts/clock` *(legacy toggle — prefer the explicit routes)*
```json
{ "user_id": "usr_…" }
```
→ `200` `data`: `{ "action": "clock_in" | "clock_out", "user_id": "…", "transitioned_steps": n }` (gains `"analytics": null` on the clock-out branch once phase 6 lands).

## 6. Declared states

### `POST /api/v1/worker-shifts/declared-states`

Roles: admin/manager pass `user_id`; worker token omits it.

```json
{ "user_id": "usr_…", "pause_reason_id": "par_…", "description": "Cleaning section B" }
```

→ `200` `data`:
```json
{
  "declared_state": {
    "id": "uds_…",
    "pause_reason": { "id": "par_…", "name": "Cleaning", "image_url": "https://…" },
    "description": "Cleaning section B",
    "entered_at": "2026-07-29T10:00:00Z"
  },
  "shift_state": "in_pause",
  "paused_steps": 1
}
```

Rules the UI must reflect:
- Worker must be clocked in → else `409` `"Worker must be clocked in to declare a state."` (offer clock-in first).
- Only **PERSONAL**-type catalog reasons are declarable (see §7); a BLOCKER reason → validation error.
- If the chosen reason has `requires_description: true`, `description` is mandatory → else validation error.
- `paused_steps` = active working steps that were auto-paused under this reason (surface it: "1 task was paused").
- Switching declarations does not re-label already-paused task steps; `paused_steps` counts only newly-paused WORKING steps.
- Declaring while another declaration is open **switches** (old one closes automatically) — no need to close first.
- Unknown/foreign/deleted reason → `404`.

### `POST /api/v1/worker-shifts/declared-states/close`

```json
{ "user_id": "usr_…" }
```
→ `200` `data`: `{ "shift_state": "idle", "closed_declared_state_id": "uds_…" }`
- No open declaration → `409` `"No declared state is open."`
- Note: closing does **not** resume auto-paused task steps (the worker resumes tasks from the worker app). `shift_state` in the response tells you where they landed (`idle`, or `in_pause` if a step-blocker pause is still open).
- A declaration also closes **automatically** when the worker starts/resumes any task step, and at clock-out. After any await, re-render from `GET /current` rather than cached state.

## 7. Pause reasons catalog (declare picker)

### `GET /api/v1/pause-reasons?pause_type=personal`

Roles: any authenticated session. Returns the workspace's manager-editable catalog. Filter to `personal` for the declare picker (`blocker` reasons are task-step blockers, not declarable).

Item shape (`data` is a list):
```json
{
  "client_id": "par_…",
  "name": "Lunch break",
  "image_url": "https://…",
  "pause_type": "personal",
  "description": "…",
  "requires_description": false
}
```
(Additional admin fields may be present; ignore unknown keys. The `pause_type` query param arrives with phase 4 — until then filter client-side.)

## 8. Response envelope & error handling (all endpoints)

- Success: `{ "ok": true, "data": …, "warnings": [] }`
- Error: `{ "ok": false, "error": "<human-readable message>" }` with the HTTP status carrying the semantics: `401` invalid/revoked token (→ sign-in screen), `403` role/scope violation, `404` not found (incl. anti-enumeration identify misses), `409` state conflict (already clocked in, not clocked in, no open declaration, duplicate clock code), `422` validation.
- Kiosk UX rule: `409`s are **normal flow** (e.g., double-tap, stale screen) — render them as friendly state refreshes (re-fetch `GET /current`), not as failures.

## 9. Suggested kiosk flows

**Clock in/out:**
type code/email → local match against the cached roster (§3) → confirm identity (photo + name) → `GET /current?user_id=…` (fresh) → if `clocked_in == false` → `clock-in`; else offer `clock-out` (+ declared-state button) → success screen (show `transitioned_steps` / future `analytics`) → auto-return to idle screen.

**Declare:**
match → confirm → `GET /current` (must be clocked in — else offer clock-in) → fetch reasons (`pause_type=personal`) → pick reason (+ description if required) → `declared-states` → show confirmation with `paused_steps`. Closing: match → confirm → `declared-states/close`.

## Validation notes

- Backend validation status: **the liveness table at the top of this document is the single
  source of truth** — no phase is live until its row shows ✅. Per-phase validation evidence lives
  in the phase plans' Review logs and implemented summaries, not here.
- Suggested frontend validation: build against a mock server generated from §2–§8; when a phase flips ✅, run the same flows against a real backend before removing the mock.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Parent summary: pending
- Related handoff: `HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719.md` (manager timeline views — unchanged by this feature set, gains declared segments as `in_pause` + `manually_recorded: true` automatically)
