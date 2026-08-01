# HANDOFF_TO_FRONTEND_worker_originated_socket_events_20260801

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_worker_originated_socket_events_20260801`
- Created at (UTC): `2026-08-01T00:00:00Z`
- Owner agent: `claude-opus-5`
- Contract: `backend/architecture/11_infra_events.md`
- Related: `HANDOFF_TO_FRONTEND_worker_shift_realtime_events_20260801.md`

> **STATUS: implemented on the backend, not yet deployed.** No contract changes. Event names and
> payloads are unchanged. What changes is that some events **start arriving** that never did.

## 1. What this is

Socket events raised from background jobs were never delivered. The backend has two kinds of code
that change data — request handlers, and background workers running as separate processes — and the
event system only worked in the first. A worker dispatched its events into an empty handler list and
returned successfully, so nothing was sent, nothing errored, and nothing was logged.

This has been true since the first commit (2026-05-15). It is now fixed for every process.

## 2. What you will start receiving

### `notification:new` → room `user:{user_id}`

```json
{ "client_id": "ntf_…" }
```

The one that matters. In-app notifications are created by a background worker, so this event has
**never** fired. The notification row was written and the OS push was sent — only the live socket
update was missing, which is why it reads as "the bell is slow" rather than as a broken feature.

If your client already has a handler for this event, it is about to be exercised for the first time.
Worth a look before deploy: make sure it invalidates the notification list and unread count rather
than assuming a full object in the payload — the payload is just the `client_id`, as documented.

### `email_batch:delivery_completed` → room `user:{requesting_user_id}`

```json
{
  "client_id": "…", "request_kind": "…", "connection_client_id": "…",
  "attempted_count": 3, "sent_count": 3, "failed_count": 0, "message_ids": ["…"]
}
```

Fires when a queued email batch finishes, to whoever requested it. Also never delivered before.

### `task:step-state-changed` from deferred completions

Only if the completion undo window is ever re-enabled — it is currently commented out, so this path
does not run today. Listed so it is not a surprise later.

## 3. What does not change

- No event was renamed, and no payload shape changed.
- Every event you already receive keeps arriving exactly as it does now, by the same route and with
  the same latency. Request-driven events are still delivered directly by the API process without a
  Redis round trip.
- Rooms are unchanged: your socket still joins `user:{user_id}` and `workspace:{workspace_id}` at
  connect, with no new subscribe call.

## 4. Frontend action required

1. Verify your `notification:new` handler does something sensible — this is the one that goes from
   never firing to firing.
2. Nothing else is required. If you ignore this handoff entirely, the app behaves as it does today
   plus a live notification badge.

## 5. Validation notes

- Backend validation run: full `pytest tests/unit tests/integration tests/connecteam`. 15 new tests
  covering registration in a fresh interpreter, transport selection per process, the full
  bus → handler → transport chain from a worker, and that an empty handler list now logs a warning.
  Remaining failures are the pre-existing ones on `main`, unchanged.
- Suggested frontend validation: with the app open and idle, have someone trigger a notification for
  you (assign a step, raise a case). The badge should move without any navigation or refresh.

## 6. Trace links

- Contract: `backend/architecture/11_infra_events.md` — "Handler registration" and "Delivery is
  process-dependent"
- Registration: `backend/app/beyo_manager/services/infra/events/bootstrap.py`
- Transport selection: `backend/app/beyo_manager/services/infra/events/realtime_push.py`
