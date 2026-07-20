# INTENTION — Connecteam Time Activity Webhook Foundation (2026-07-20)

> Provided by the product owner on 2026-07-20. Source of truth for
> `PLAN_connecteam_time_activity_webhook_foundation_20260720.md`.
> Where this intention conflicts with the backend's existing architecture,
> the conflict is surfaced in the plan's "Clarifications required" section.

## 1. Objective

Implement the backend foundation required to receive, authenticate, queue, retry, and resolve Connecteam time-clock webhook events.

The webhook is already configured in Connecteam with these event types:

- `clock_in`
- `clock_out`
- `auto_clock_out`

The webhook currently points to an ngrok HTTPS tunnel forwarding requests to the local FastAPI backend on port 8000.

The shared webhook secret has already been stored in the backend environment as `CONNECTEAM_WEBHOOK_SECRET=...`.

This phase must establish the complete webhook infrastructure, but it must **not** yet create, update, or close any internal working-time records. The actual domain actions for clock-in and clock-out will be added in a later phase.

Connecteam documents these three events as supported time-activity webhook events. A time activity can represent a `shift` or a `manual_break`, so this implementation must explicitly distinguish the activity type rather than treating every received event as a worker shift.

## 2. Intended architecture

Lightweight Redis-backed asynchronous flow:

```
Connecteam
    → POST webhook endpoint
    → read raw request body
    → validate webhook authenticity
    → minimal payload validation
    → deterministic event identity
    → deduplicate through Redis
    → enqueue event
    → return successful HTTP response quickly
    → background worker consumes event
    → resolve Connecteam user ID to UserWorkProfile
    → dispatch to event-specific placeholder handler
    → mark completed or schedule a retry
```

The webhook route must remain thin: no worker resolution, retry orchestration, or future clock-event business logic inside the route.

## 3. Scope

In scope: webhook settings; public FastAPI endpoint; raw-body handling; secret/signature validation; flexible payload parsing; Redis-backed queue, deduplication, retry scheduling; dead-letter handling after retry exhaustion; Connecteam worker resolution through `UserWorkProfile`; adding the Connecteam user identifier to `user_work_profiles`; event dispatcher plus placeholder handlers for `clock_in`, `clock_out`, `auto_clock_out`; structured logging and diagnostics; unit and integration tests; local ngrok validation instructions.

Out of scope: creating internal worker clock-in records; updating internal work sessions; closing worker sessions; modifying worker timeline or analytics tables; synchronizing all Connecteam users automatically; calling Connecteam's REST API; supporting Connecteam admin-edit, manual-break, time-off, scheduler, form, task, or user events; frontend management pages; persisting webhook events in PostgreSQL during this phase.

## 4. External identifier on UserWorkProfile

Update `backend/app/beyo_manager/models/tables/users/user_work_profile.py` with a nullable `connecteam_user_id: Mapped[str | None]` — `String(64)`, nullable, with lookup index `ix_user_work_profiles_connecteam_user_id` and a uniqueness constraint scoped to the narrowest safe Connecteam identity scope (inspect the existing workspace/integration ownership model to choose; if multiple Connecteam companies may share the database, do not treat the raw ID as globally unique).

The migration must add the nullable column, index, and constraint; stay backward-compatible with existing rows; include a clean downgrade; and never populate IDs automatically. The webhook resolver must use the explicit Connecteam ID mapping only — no matching by username, email, or phone.

## 5. Configuration

Typed backend settings for (names may be aligned to existing conventions):

```
CONNECTEAM_WEBHOOK_SECRET=
CONNECTEAM_WEBHOOK_ENABLED=true
CONNECTEAM_WEBHOOK_QUEUE_KEY=connecteam:webhooks:queue
CONNECTEAM_WEBHOOK_PROCESSING_KEY=connecteam:webhooks:processing
CONNECTEAM_WEBHOOK_RETRY_KEY=connecteam:webhooks:retries
CONNECTEAM_WEBHOOK_DEAD_LETTER_KEY=connecteam:webhooks:dead-letter
CONNECTEAM_WEBHOOK_DEDUP_PREFIX=connecteam:webhooks:dedup
CONNECTEAM_WEBHOOK_MAX_ATTEMPTS=5
CONNECTEAM_WEBHOOK_DEDUP_TTL_SECONDS=604800
CONNECTEAM_WEBHOOK_PROCESSING_TIMEOUT_SECONDS=120
```

Requirements: startup fails clearly when webhook enabled but secret missing; the secret is never logged; raw signature values not logged at normal levels; disabling the integration produces a controlled response, not silent acceptance.

## 6. Public webhook endpoint

E.g. `POST /api/v1/integrations/connecteam/webhooks/time-activity` (final location follows the backend's integration-router structure). The route must: read raw body before JSON deserialization; extract the signature header; validate against the secret; reject missing/invalid auth; parse with a tolerant schema; confirm supported event type and intended activity type; build deterministic event identity; enqueue through a service; return quickly.

Responses: 200/202 accepted or duplicate (idempotent success); 400 malformed JSON / structurally unusable; 401/403 auth failure; 422 recognized envelope with unsupported/invalid required fields; 503 Redis unavailable and event cannot be durably accepted. Connecteam requires HTTPS and retries deliveries up to three times, so intake must be idempotent.

## 7. Signature verification

First determine the exact Connecteam authentication contract: header name, encoding, digest algorithm, what the signature covers (raw body vs timestamp+body), any `sha256=` prefix, any replay-prevention timestamp. **Do not invent a header name or verification algorithm.** Verify against raw body bytes with constant-time comparison (`hmac.compare_digest`). Isolate behind a provider-specific verifier (e.g. `ConnecteamWebhookVerifier.verify(raw_body, headers)`) raising a provider auth exception mapped to 401/403. Development-only discovery logging may record incoming header *names*, never secrets or signature values; remove once the contract is confirmed.

## 8. Flexible webhook schemas

Provider DTOs separate from domain models; tolerant parsing (`ConfigDict(extra="allow")`) because Connecteam schemas may gain fields. Capture at least: request_id, company, event_type, activity_type, event_timestamp, user_id, time_clock_id, time_activity_id, data/time_activity, raw payload. Exact nesting must come from real payloads received through ngrok. Normalize into an internal queue envelope:

```json
{
  "event_key": "...", "provider": "connecteam", "event_type": "clock_in",
  "activity_type": "shift", "request_id": "...", "company_id": "...",
  "connecteam_user_id": "...", "time_clock_id": "...", "time_activity_id": "...",
  "occurred_at": "...", "received_at": "...", "attempt": 0, "payload": {}
}
```

Provider field names must not leak beyond the Connecteam adapter.

## 9. Supported-event policy

Accept only `clock_in`, `clock_out`, `auto_clock_out`. `activity_type == "shift"` is eligible for resolution and placeholder dispatch; `manual_break` is deliberately ignored/explicit unsupported state; unknown event types never invoke business handlers; unknown additive fields never break deserialization. Service results distinguish: accepted, duplicate, ignored_activity_type, unsupported_event_type, worker_not_mapped, processed, retry_scheduled, dead_lettered.

## 10. Event identity and deduplication

Prefer Connecteam's unique `requestId` (`connecteam:{request_id}`). Fallback: deterministic hash over company, event_type, activity_type, connecteam_user_id, time_clock_id, time_activity_id, event_timestamp, canonical payload hash. Never just `user_id + event_type`. Dedup via atomic Redis `SET NX EX` (`connecteam:webhooks:dedup:{event_key}`, TTL ≥ 7 days). Duplicates return success. The dedup marker must not be able to permanently lose an event if created before the queue write; define recovery behavior if Redis fails between operations.

## 11. Redis queue design

Use the backend's existing Redis client and worker conventions. **Inspect the current worker architecture before selecting the primitive.** Preferred: Redis Streams with consumer groups if supported; a reliable list pattern (pending/processing lists, atomic move, visibility timeout); or the project's existing task-router/event-bus mechanism if it already provides equivalent reliability. No pub/sub. Must support enqueue, claim, acknowledge, retry-later, recovery of abandoned processing, dead-letter. Document the chosen structures and atomicity guarantees.

## 12. Webhook intake service

A service (e.g. `accept_time_activity_webhook`) that builds the event key, atomically checks dedup, enqueues the normalized event, returns an intake result (`accepted` | `duplicate`), and performs no domain actions. The router depends on this service, never on Redis directly.

## 13. Background consumer

Dedicated consumer or integration with the existing worker process per current conventions. Lifecycle: claim → deserialize → resolve worker → dispatch placeholder → acknowledge. Must process idempotently, use bounded concurrency, recover events abandoned in processing, emit structured logs, avoid blocking the API process, shut down cleanly, avoid tight loops when Redis is down. Prefer the existing worker framework unless isolation provides a concrete operational advantage.

## 14. Worker resolver

`resolve_connecteam_worker` — input: workspace/company scope + connecteam_user_id; output: UserWorkProfile, internal user_id, workspace_id, or explicit unmapped result. Normalize the external ID to string; query only via the explicit `connecteam_user_id` field; respect workspace/integration scope; never guess by email/name/phone/username; treat ambiguous mappings as integration errors. Unmapped workers must not retry forever: log warning, preserve the event for inspection, dead-letter or mark unresolved, never invoke a clock handler. Design must allow requeueing unresolved events after a mapping is added later.

## 15. Event dispatcher

Map `clock_in → HandleConnecteamClockIn`, `clock_out → HandleConnecteamClockOut`, `auto_clock_out → HandleConnecteamAutoClockOut`. Placeholders this phase: receive resolved worker + normalized event, log successful resolution, return no-op result, perform no work-session mutations, define stable interfaces for later. No large conditional block inside the route.

## 16. Retry policy

Internal processing retries are independent from Connecteam's delivery retries. Non-retryable: invalid signature, malformed payload, unsupported event/activity type, missing required identity fields, ambiguous mapping, worker not mapped (unless delayed mapping retries are explicitly chosen). Retryable: temporary Postgres/Redis failure after acceptance, connection timeout, dependency unavailability, recoverable worker crash. Suggested schedule: 10s, 30s, 2m, 10m, 30m with jitter. Envelope carries attempt, first_received_at, last_attempt_at, next_attempt_at, last_error_code — no tracebacks in queue payloads. After max attempts: dead-letter with original normalized event, safe error metadata, ERROR log.

## 17. Retry scheduler and processing recovery

Lightweight Redis retry scheduler (e.g. sorted set scored by next-attempt timestamp): read due members, atomically claim, return to pending, preserve attempt counter. Also recover events abandoned in processing beyond the processing timeout. Two workers must not requeue the same due event.

## 18. Dead-letter inspection

Even without a PostgreSQL webhook table: dead-letter key, CLI/script to list entries, requeue one event, purge deliberately; safe structured logs with event key and reason. No secrets or full sensitive payloads in routine logs. A future phase may add durable PostgreSQL intake records.

## 19. Logging and observability

Structured logs with provider, event_key, request_id, event_type, activity_type, connecteam_user_id, time_clock_id, time_activity_id, workspace_id, internal_user_id, attempt, processing_status, duration_ms. Lifecycle events: connecteam_webhook_received / rejected / duplicate / enqueued / claimed, connecteam_worker_resolved / not_mapped, connecteam_event_noop_handled, connecteam_webhook_retry_scheduled / dead_lettered / completed. Never log the secret, signature values, authorization headers, or full payloads at INFO. Raw payload logging only behind an explicit debug setting.

## 20. Suggested package structure

Align with the repository's actual architecture; responsibility boundaries resembling: router `integrations/connecteam_webhooks.py`; schemas `integrations/connecteam_webhooks.py`; services `integrations/connecteam/` (verify, normalize, accept, resolve, dispatch, handlers/); infrastructure `redis/connecteam_webhook_queue.py`; worker `connecteam_webhook_worker.py`; model change in `user_work_profile.py`. Provider-specific code stays inside the Connecteam integration boundary.

## 21. Database migration

Alembic migration for the UserWorkProfile change. Inspect the current Alembic head first. Upgrade: add nullable column, index, safe uniqueness constraint. Downgrade: remove constraint, index, column. Existing rows remain valid with NULL. No automatic ID population.

## 22. Tests

Signature verifier (valid/invalid/missing signature, raw-body sensitivity, constant-time comparison, unknown headers don't bypass). Router (valid → success, malformed JSON → 400, bad auth → 401/403, duplicate → success, Redis intake failure → 503, unsupported events don't enter the queue). Payloads (all three events normalize; manual_break ignored; additive fields tolerated; missing identity fields rejected). Deduplication (same requestId queues once, concurrent duplicates queue once, fallback key deterministic, legitimate repeat clock events don't collide, TTL applied). Queue (enqueue/claim/acknowledge; failure → retry; due retry → pending; max attempts → dead-letter; abandoned processing recovered; no double-claim). Worker resolution (exact ID resolves; unknown → worker_not_mapped; ambiguous rejected; workspace scope respected; no fallback matching). Dispatcher (each event reaches its handler; unknown events don't; placeholders write nothing; no-op acknowledged). Migration (existing rows valid; ID stored/retrieved; uniqueness enforced; multiple NULLs valid).

## 23. Local validation with ngrok

Start FastAPI on 8000 → start ngrok → confirm Connecteam webhook targets current ngrok URL → start the worker → clock in → confirm accept + queue → confirm mapping resolution → confirm clock-in placeholder → clock out → confirm clock-out placeholder → trigger/wait for auto-clock-out → confirm its placeholder → confirm no internal work-session rows changed. Retain a safely redacted example payload as a test fixture from the first discovery run. Keep the endpoint URL outside application code.

## 24. Acceptance criteria

1. Connecteam can POST all three events to the endpoint. 2. Invalid auth rejected before parsing/queueing. 3. Valid events acknowledged quickly. 4. Duplicates create no duplicate work. 5. Accepted events survive temporary consumer downtime. 6. Retryable failures retried with bounded backoff. 7. Exhausted failures dead-lettered. 8. Abandoned processing recoverable. 9. UserWorkProfile supports an explicit Connecteam user ID. 10. Resolver maps the ID to exactly one work profile. 11. Manual-break events never trigger shift handlers. 12. Three placeholder handlers invoked correctly. 13. No internal clock/worker-state/timeline records modified. 14. Tests cover auth, intake, dedup, queue lifecycle, retries, mapping, dispatch. 15. Implementation follows existing DI, Redis, worker, exception, logging, and service conventions.

## 25. Instructions for the implementation-plan author

Before proposing files, inspect: router registration; integration modules; Redis client abstraction; task-router and worker conventions; retry/delayed-scheduler implementations; structured logging; settings system; service/query patterns; UserWorkProfile repositories; current Alembic head; existing test fixtures. **Reuse existing infrastructure where it already provides queueing, retries, delayed execution, or worker recovery. Do not introduce a second generic queue framework solely for Connecteam.** The plan must document: verified signature contract; chosen Redis primitives; atomic dedup/enqueue behavior; acknowledgement semantics; retry classification and timing; dead-letter/requeue workflow; identity scope; every new and modified file; test coverage; local ngrok verification procedure.
