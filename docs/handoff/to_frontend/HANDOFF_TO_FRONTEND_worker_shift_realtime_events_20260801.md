# HANDOFF_TO_FRONTEND_worker_shift_realtime_events_20260801

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_shift_realtime_events_20260801`
- Created at (UTC): `2026-08-01T00:00:00Z`
- Owner agent: `claude-opus-5`
- Domain doc: `backend/docs/domains/worker_shifts/api.md` (§ Realtime events) — the authoritative contract

> **STATUS: implemented on the backend, not yet deployed.** Nothing here is breaking: these are new
> events on rooms your sockets already join. Ignoring them leaves today's behaviour exactly as it is.

## 1. What this is

Worker shift state changed silently until now. A worker clocked in at a shared floor terminal, a
manager declared a break on someone's behalf, the overnight safeguard closed a forgotten shift, the
external clock integration fired — and no client was told. Every screen showing shift state was
correct only as far back as its last fetch.

Three events now cover it.

## 2. The events

Your socket already joins both rooms at connect: `user:{your user_id}` and
`workspace:{your workspace_id}`. No subscribe call, no new handshake.

### `worker-shift:state-changed` — room `user:{target_user_id}`

Payload is **exactly** the `GET /api/v1/worker-shifts/current` body for that worker:

```json
{
  "user_id": "usr_…",
  "clocked_in": true,
  "shift_started_at": "2026-08-01T07:02:11.482Z",
  "state": "in_pause",
  "state_entered_at": "2026-08-01T11:15:00.000Z",
  "pause_reason": { "id": "par_…", "name": "Lunch", "…": "…" },
  "declared_state": { "…": "…" }
}
```

Write it straight into your `/current` cache — no refetch needed. Clock-out is not a special shape;
it arrives as the same body with `clocked_in: false` and `state: null`, identical to reading
`/current` for a worker who is out.

You only ever receive this for **yourself**. A manager watching a worker does not get that worker's
full state — see below.

### `worker-shift:roster-changed` — room `workspace:{workspace_id}`

```json
{ "user_id": "usr_…", "clocked_in": true, "state": "in_pause", "state_entered_at": "…" }
```

**This is a signal to refetch, not data to render as the whole truth.** It deliberately carries no
pause reason and no declared state: every worker's device is in the workspace room too, and a
declaration's `description` is free text a worker typed about themselves ("doctor appointment").
Managers refetch the `/worker-stats/` endpoint backing the view; those already gate the detail
behind `ADMIN`/`MANAGER`.

You may use `state` and `clocked_in` directly for cheap things — an online dot, a roster sort, an
optimistic badge — without refetching.

### `task:step-state-changed` — room `workspace:{workspace_id}`

The event you already handle, same list shape:

```json
[{ "client_id": "tst_…", "new_state": "paused" }]
```

Now also emitted when the **backend** pauses a step without the worker asking: clock-out force-pausing
what they were still working, declaring a state auto-pausing their steps, and raising a case on a
task pausing that task's working steps. No new handling required if you already invalidate on this
event — the point is that it now fires in cases where your cache used to go stale silently.

## 3. When they fire

| Trigger | Events |
|---|---|
| `POST /worker-shifts/clock-in`, `/clock-out`, `/clock` | shift + roster; step event when clock-out force-paused steps |
| `POST /worker-shifts/declared-states` and `/close` | shift + roster; step event when declaring auto-paused steps |
| A step transition moving the worker between `WORKING` / `IN_PAUSE` / `IDLE` | shift + roster, **once per actual state change** — pausing five steps of a batch is one event, not five |
| The external clock integration | shift + roster; step event on clock-out |
| The overnight safeguard | shift + roster per closed shift |
| Raising a case on a task | step event only |

All fire **after** the write commits, so an event never describes a state the database rolled back.

## 4. Frontend action required

1. **Floor / worker app** — subscribe to `worker-shift:state-changed` and write the payload into the
   `/worker-shifts/current` cache. This is the one that matters most: a worker whose manager just
   declared a break for them, or whose shift the overnight job closed, currently has no way to find
   out.
2. **Manager app** — subscribe to `worker-shift:roster-changed` and invalidate the `/worker-stats/`
   query for that `user_id`. Debounce if your roster is large; a busy floor produces a few events per
   worker per hour, not per second.
3. **Both** — confirm `task:step-state-changed` invalidates step caches even when the change was not
   initiated locally. If your handler filters to steps you believe you own, it will drop these.
4. Do **not** treat the absence of an event as authoritative. The backend logs and swallows broadcast
   failures rather than failing a committed clock-out, so a Redis outage costs you the event, not the
   write. Keep whatever refetch-on-focus you have today.

## 5. Ordering and races

The step event and the shift event are emitted separately and are not ordered relative to each other.
If you render "paused — lunch" from two caches, expect a frame where one has landed and the other has
not. Both converge within the same round trip.

Related: the case-created conflict in
`HANDOFF_TO_FRONTEND_remove_case_created_pause_20260801.md` is **not** fixed by this. The workers app
still fires its own `PAUSED → PAUSED` transition after creating a case, and the socket event cannot be
relied on to arrive before it. Self-healing makes the next render right; it does not make the racing
write legal. That client-side removal is still required.

## 6. Validation notes

- Backend validation run: `pytest tests/integration tests/unit tests/connecteam` — all new tests pass;
  the pre-existing failures in unrelated suites (working sections, upholstery, shopify, audit log) are
  unchanged from `main`.
- Coverage: room split and payload shapes per command, the declaration-description exclusion from the
  workspace payload, the once-per-actual-change gate on step transitions, the case-created step event,
  and that a dead socket transport does not fail the command.
- Suggested frontend validation: clock a worker in from a manager session on a second device and
  confirm the worker's own device updates without a refetch; declare a state with a description and
  confirm the description is absent from what a *different* worker's device receives.

## 7. Trace links

- Domain contract: `backend/docs/domains/worker_shifts/api.md` § Realtime events
- Domain overview: `backend/docs/domains/worker_shifts/README.md`
- Emitter: `backend/app/beyo_manager/services/infra/events/worker_shift_realtime.py`
