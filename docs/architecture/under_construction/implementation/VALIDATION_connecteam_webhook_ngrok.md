# Connecteam webhook ngrok validation

1. Start the API on port 8000 and expose it with ngrok HTTPS.
2. Set the Connecteam webhook URL to `/api/v1/connecteam/webhooks/time-activity` on the current tunnel.
3. Start `task-router` and `tasks-worker` from the Procfile (Connecteam events are processed by the shared `tasks-worker` on `queue:tasks`).
4. Set a test `UserWorkProfile.connecteam_user_id` explicitly before checking resolution.
5. Human-only validation: ask the owner to clock the mapped worker in and out once in Connecteam.
   Do not simulate this step. If deferred, record it as pending; it does not block the phase-2
   lifecycle transition.
6. Confirm `connecteam_webhook_enqueued`, worker resolution, and the applied handler logs
   (`connecteam_clock_in_applied` / `connecteam_clock_out_applied`).
7. After the Connecteam clock-in, confirm an open `IDLE` shift record with
   `manually_recorded=false`, `changed_by_id` equal to the mapped worker, and the event's
   `occurred_at` timestamp.
8. Start a working step, then clock out in Connecteam. Confirm the shift is closed, the
   working step is `ENDED_SHIFT` with `PAUSE_ENDED_SHIFT`, and the clock-out timestamp comes
   from the event.
9. Trigger or requeue the same completed delivery and confirm the terminal ConflictError path
   produces `connecteam_clock_event_noop` with the correct `noop_reason` and no new records.
10. Trigger `auto_clock_out` and confirm it uses the same close semantics with
    `auto_clock_out=true`; an already-closed shift is the expected `no_open_shift` no-op.

The tunnel URL belongs only in the Connecteam console; never commit it to application code.

The initial inspector run established the static `X-Webhook-Secret` header name and
non-empty request bodies, but the target returned 502. Capture one successful
delivery before enabling this endpoint outside development and replace the
provisional fixture values with a safely redacted real payload shape.

Phase-2 automated validation completed on 2026-07-20: the Connecteam suite passed, including
DB-backed toggle parity and `WORKING`-step closure coverage. The human-only ngrok delivery
remains pending until the owner clocks a mapped worker in and out in Connecteam.
