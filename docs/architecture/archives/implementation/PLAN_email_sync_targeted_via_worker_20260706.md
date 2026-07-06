# PLAN_email_sync_targeted_via_worker_20260706

## Metadata

- Plan ID: `PLAN_email_sync_targeted_via_worker_20260706`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T06:00:00Z`
- Last updated at (UTC): `2026-07-06T05:55:34Z`
- Related issue/ticket: `n/a — follow-up to PLAN_offload_blocking_imap_smtp_20260706 (Tier 2)`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_email_sync_targeted_via_worker_20260706.md`

## Goal and intent

- Goal: Move the targeted email-thread sync off the HTTP request path. `POST /api/v1/email-threads/sync-targeted` should enqueue a background execution task and return immediately; the general worker performs the IMAP sync and pushes a real-time socket event to the user who requested it.
- Business/user intent: Triggering a sync must never hold an HTTP request open for the IMAP round-trip (~seconds to 20s timeout). The requesting user's frontend gets an immediate OK, then reacts to a socket event when the sync completes and refreshes the affected threads.
- Non-goals:
  - Do NOT create a new dedicated email worker/queue yet — reuse the existing general worker (`queue:tasks`). A dedicated worker is a later step if `queue:tasks` gets overwhelmed.
  - Do NOT change thread-matching, MIME parsing, or the inbound message-processing logic.
  - Do NOT build a polling/status REST endpoint — delivery is via the socket layer only.
  - Do NOT change the full-inbox sync path (`EMAIL_INBOX_SYNC`) — it already runs on the worker; only mirror its pattern.

## Scope

- In scope:
  - New `TaskType` for targeted sync + `QUEUE_MAP` + `HANDLER_TIMEOUT_SECONDS` entries.
  - New execution payload dataclass mirroring `SyncThreadsBatchTargetedRequest` fields + `requested_by_user_id`.
  - Convert the `sync_email_threads_batch_targeted` command into a thin enqueue (mirror `sync_email_connection`), extracting the actual sync logic into a shared function.
  - New worker handler that runs the extracted sync logic and emits a socket event to the requesting user.
  - Register handler in `workers/tasks_worker.py` `HANDLER_MAP`.
  - Cross-process socket delivery bridge (see Clarifications — the single real architectural decision).
- Out of scope:
  - Router signature/URL of `sync-targeted` stays the same; only its response semantics change (now returns "enqueued" instead of sync results).
  - The `asyncio.to_thread` adapter offload from `PLAN_offload_blocking_imap_smtp_20260706` — that plan ships independently and remains correct (it also protects the worker's own event loop). This plan assumes it is applied or will be.
- Assumptions:
  - The existing execution pipeline (task_factory → task_router LISTEN/NOTIFY → Redis queue → worker_base claim/retry/timeout) is the intended mechanism; we only add a task type + handler, exactly as `EMAIL_INBOX_SYNC` and `SEND_COORDINATION_EMAIL_BATCH` already do.
  - Redis is available to the worker process (it already uses `get_redis_client` for `blpop`).

## Clarifications required

- [ ] **Cross-process socket delivery mechanism.** `sockets/__init__.py` constructs `socketio.AsyncServer(async_mode="asgi")` with **no `client_manager`**, so socket connections live only in the web process's in-memory `ConnectionManager`. The worker is a *separate process* (`workers/tasks_worker.py` → its own `asyncio.run`). Calling `manager.send_to_user(...)` from the worker will emit into a void — the target socket is not in that process. This must be bridged before socket delivery works. Options:
  - **Option A (recommended):** Give the web `AsyncServer` a `client_manager=socketio.AsyncRedisManager(settings.redis_url)`, and in the worker emit through a write-only `socketio.AsyncRedisManager(settings.redis_url, write_only=True)`. This is python-socketio's canonical multi-process fan-out; reuses existing Redis; minimal custom code. `manager.send_to_user`'s room convention (`user:{user_id}`) is preserved.
  - **Option B:** Custom Redis pub/sub bridge — worker `PUBLISH`es an event to a channel; the web process runs a subscriber task that calls `manager.send_to_user`. More code, but fully decoupled from socket.io internals and reuses the existing `ConnectionManager` directly.
  - Decision needed before implementation; default to Option A unless there is a reason to avoid the Redis-manager dependency.
- [ ] **Socket event name + payload shape** the frontend will listen for (e.g. `email.threads.synced` with `{ connection_client_id, thread_ids_with_new_messages, synced_thread_count, sync_success }`). Confirm the contract with the frontend so it knows which threads to refetch.
- [ ] **Dedup / in-flight coalescing:** should a second `sync-targeted` for the same connection while one is already OPEN/IN_PROGRESS be coalesced/skipped, or always enqueue a new task? Current infra does not dedupe. Recommend: allow duplicates for now (simplest); revisit if load warrants.

## Acceptance criteria

1. `POST /api/v1/email-threads/sync-targeted` returns immediately (no IMAP call on the request path) with an "enqueued" acknowledgement, after creating exactly one `ExecutionTask` of the new targeted-sync type inside the request transaction.
2. The general worker (`queue:tasks`) picks up the task, runs the same targeted-sync logic that previously ran inline (load threads → gather outbound rfc ids → `provider.search_by_header_ids` → `process_inbound_messages` → audit), producing the same DB effects as today.
3. On completion, the worker emits a socket event addressed to `user:{requested_by_user_id}`, and that event is delivered to the requesting user's browser even though the worker is a separate process (cross-process bridge working).
4. A concurrent pure-DB request during the sync is unaffected (already true once work is off the request path).
5. Failure/retry semantics come for free from `worker_base` (retry with backoff, timeout, SIGTERM rescue); a failed sync does not 500 the original request (it already returned OK).

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/.../execution/*.md` (task types, task_factory, worker registration): reason — confirm the canonical way to add a task type + handler and the queue mapping rules.
- `backend/docs/architecture/.../09_routers.md`: reason — confirm the enqueue-and-return response convention for command routers.
- `backend/docs/architecture/.../sockets/*.md` (if present): reason — confirm event naming conventions and room usage.

### Local extensions loaded

- None expected.

### File read intent — pattern vs. relational

Relational reads (understanding what exists) already performed and permitted:
- `services/commands/emails/sync_email_connection.py` — the reference enqueue pattern (full-inbox sync) to mirror.
- `services/tasks/email_inbox_sync_handler.py` — the reference worker handler shape.
- `services/infra/execution/task_factory.py` (`create_instant_task`), `task_router.py` (`QUEUE_MAP`), `worker_base.py` (`HANDLER_TIMEOUT_SECONDS`), `workers/tasks_worker.py` (`HANDLER_MAP`) — the registration surface.
- `sockets/__init__.py`, `sockets/manager.py` — emit API (`send_to_user`) and the missing client-manager.
- `services/commands/emails/requests/sync_thread_targeted_request.py` — exact fields to carry in the payload.
- `services/commands/emails/sync_email_threads_batch_targeted.py` — the sync logic to extract.

Do NOT pattern-read other commands/handlers to learn structure — the two references above are sufficient.

### Skill selection

- Primary skill: n/a (follows established execution-task + handler pattern).
- Router trigger terms: `execution task, background worker, socket emit, AsyncRedisManager, enqueue`.
- Excluded alternatives: dedicated-worker/new-queue skill — excluded per owner decision (reuse general worker first).

## Implementation plan

1. **Add task type.** In `domain/execution/enums.py` add `TaskType.EMAIL_SYNC_TARGETED` (name TBD). Map it in `task_router.QUEUE_MAP` → `"queue:tasks"` and add a `HANDLER_TIMEOUT_SECONDS["email_sync_targeted"]` (e.g. 300s) in `worker_base.py`.
2. **Add payload dataclass.** New `domain/execution/payloads/sync_email_threads_targeted.py` (frozen dataclass) carrying: `workspace_id`, `connection_client_id`, `thread_client_ids`, `entity_type`, `entity_client_ids`, `major_entity_type`, `major_entity_client_id`, `max_threads`, `requested_by_user_id`, `role_name`. (Mirror `SyncThreadsBatchTargetedRequest` + requester identity so access checks can be re-evaluated in the handler.)
3. **Extract the sync core.** Pull the body of `sync_email_threads_batch_targeted` (thread loading, rfc-id gathering, `provider.search_by_header_ids`, `process_inbound_messages`, audit, result dict) into a reusable async function that takes a `session` + resolved params — callable from the worker handler. Keep it session-agnostic about who opens the transaction.
4. **Convert the command to a thin enqueue.** `sync_email_threads_batch_targeted` becomes: validate request → resolve/authorize connection (keep the access guard on the request path so unauthorized callers still get an immediate error) → `create_instant_task(session, EMAIL_SYNC_TARGETED, payload, max_try=3)` → `write_audit("email.threads.sync_enqueued")` → return `{ "enqueued": true, ... }`. Mirror `sync_email_connection` exactly.
5. **Write the worker handler.** New `services/tasks/emails/handle_sync_email_threads_targeted.py`: open `get_db_session()` + `session.begin()`, reconstruct params from payload, re-resolve/authorize the connection, call the extracted sync core, then emit the socket event to the requester.
6. **Register the handler.** Add to `HANDLER_MAP` in `workers/tasks_worker.py`.
7. **Cross-process socket delivery** (per Clarification decision). Option A: add `client_manager=socketio.AsyncRedisManager(settings.redis_url)` in `sockets/__init__.py`; in the worker, build a write-only `AsyncRedisManager` and emit to room `user:{requested_by_user_id}` with the agreed event name/payload (or thread through a small worker-side emit helper that reuses `ConnectionManager.user_room`).
8. **Emit the completion event** from the handler with `{ connection_client_id, synced_thread_count, thread_ids_with_new_messages, sync_success, sync_error }` (final shape per Clarification).

## Risks and mitigations

- Risk: **Worker emits but nothing reaches the browser** because the socket manager is single-process (the core gap above).
  Mitigation: Implement the cross-process bridge (Clarification/step 7) and verify end-to-end with a real connected client before considering the feature done. This is the highest-risk item.
- Risk: Access control regression — moving work to the worker could drop the authorization the request path enforced.
  Mitigation: Keep the connection access guard on the request path (step 4) AND re-resolve/authorize in the handler using `requested_by_user_id`/`role_name` from the payload (step 5).
- Risk: Silent failures — since the request already returned OK, a failed sync is invisible to the user.
  Mitigation: Rely on `worker_base` retry/backoff + `last_error`; on terminal failure, emit a socket event with `sync_success=false` so the frontend can surface it. Audit both enqueue and completion.
- Risk: Payload carries stale data (threads deleted between enqueue and run).
  Mitigation: The handler re-queries threads by id at run time (does not trust enqueue-time snapshots), same as the current command loads them fresh.
- Risk: Blocking IMAP call blocks the worker's event loop during the run.
  Mitigation: Covered by `PLAN_offload_blocking_imap_smtp_20260706` (`asyncio.to_thread` in the adapter). Ensure that plan is applied; note the dependency.

## Validation plan

- Static: `ruff check` on all touched files + project type check — expected clean.
- Enqueue behavior: call `POST /api/v1/email-threads/sync-targeted`; assert response is immediate (< DB time, no IMAP latency) and one `ExecutionTask` row of the new type is created OPEN with the correct payload.
- Worker behavior: with the worker running, assert the task transitions OPEN→PENDING→IN_PROGRESS→COMPLETED and the same rows are written as the old inline path (compare `email_messages` created for a known thread with new inbound mail).
- Socket delivery (the critical check): connect a socket client as the requesting user, trigger the sync, assert the completion event arrives in the browser/client — proving the cross-process bridge works. Repeat with the web server and worker as genuinely separate processes (not a single dev process) to catch the single-process illusion.
- Concurrency: fire `sync-targeted` + `GET /api/v1/tasks/customer-coordination/threads` in parallel; assert the GET returns immediately.
- Failure path: point the connection at an unreachable IMAP host; assert retries/backoff occur and a `sync_success=false` event is eventually emitted, with no impact on the original (already-returned) request.

## Review log

- `2026-07-06` `claude`: Drafted from execution/worker + socket infra read. Confirmed enqueue pattern already exists (`sync_email_connection` → `EMAIL_INBOX_SYNC`); the only genuine new problem is cross-process socket delivery (no `client_manager` on `AsyncServer`). Owner decisions baked in: reuse general worker; immediate OK + socket event to requester.
- `2026-07-06` `codex`: Implemented the worker-backed targeted sync with `TaskType.EMAIL_SYNC_TARGETED`, a Redis-backed cross-process Socket.IO bridge, and the `email.threads.synced` user event emitted from the worker after sync completion.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
