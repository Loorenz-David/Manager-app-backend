# PLAN_email_idle_watcher_20260706

## Metadata

- Plan ID: `PLAN_email_idle_watcher_20260706`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T10:00:00Z`
- Last updated at (UTC): `2026-07-06T08:25:48Z`
- Related issue/ticket: `n/a — real-time inbound email push, replacing frontend-triggered polling`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_email_idle_watcher_20260706.md`

## Goal and intent

- Goal: Add a scalable, provider-agnostic IMAP IDLE watcher that maintains a persistent connection per active email connection and reacts to server-pushed "new mail" signals by triggering the existing `EMAIL_INBOX_SYNC` pipeline — so inbound email is ingested in near real-time without the frontend having to call the sync endpoints. Because the watcher runs server-side and always-on (independent of any connected client), the same arrival event also drives a generic routing layer that decides "what should happen" per received email (notify the right users via the existing in-app socket + VAPID push infrastructure today; pluggable for AI/content rules later).
- Business/user intent: Users should be notified of new customer emails immediately — even when the app is closed (via VAPID push, which the arrival routing reaches through the existing notification pipeline) — instead of only discovering mail when a browser tab happens to poll `sync-targeted`/`sync`. The mechanism must work across arbitrary IMAP providers (not just Gmail), matching this system's existing generic SMTP/IMAP connection model.
- Non-goals:
  - Do NOT build a Gmail-API/Pub/Sub push integration — the system connects to generic IMAP/SMTP accounts, so IMAP IDLE (RFC 2177) is the provider-agnostic mechanism. Gmail-specific push is an explicit non-goal.
  - Do NOT reimplement mail fetching/parsing/persistence — the watcher only DETECTS change and triggers the existing `EMAIL_INBOX_SYNC` task, which already fetches, parses, threads, and persists via `process_inbound_messages`.
  - Do NOT remove the existing manual/targeted sync endpoints or the current on-demand sync — they remain as a fallback and for explicit user-triggered refresh. The watcher is additive.
  - Do NOT build the AI/content-rule classifier in this plan — the routing layer must expose a clean extension seam for it, but the first concrete routing rule is deterministic (entity/ownership-based recipient resolution).
  - Do NOT change the VAPID/push sending internals — reuse the existing `CREATE_NOTIFICATIONS` → `SEND_PUSH_NOTIFICATION` pipeline unchanged.

## Scope

- In scope:
  1. A new long-running worker process (Procfile entry + `workers/email_idle_watcher.py` entrypoint) following the established `init_db()` + `asyncio.run(run_*())` pattern used by `task_router_process.py`, `recurring_scheduler_runner.py`, etc.
  2. A supervisor in `services/infra/email_idle/` that: periodically reconciles the set of active email connections it should watch; maintains one persistent IMAP IDLE session per owned connection; renews IDLE within the protocol's ~29-minute window; reconnects with capped backoff on transient drop; distinguishes auth failures from transient failures (see Implementation step 4); debounces/coalesces new-mail signals per connection; and, on a (coalesced) new-mail signal, enqueues the existing `EMAIL_INBOX_SYNC` task via `create_instant_task` using its exact existing payload contract.
  3. Horizontal scalability via deterministic sharding using a **stable, cross-process hash** of `connection.client_id` (NOT Python's built-in `hash()`), modulo `shard_count`, matched against `shard_index` — configured through settings so the process count can grow with connection volume. See Implementation step 3.
  4. A generic "email arrival routing" seam invoked after new inbound messages are persisted, driven strictly by the set of **newly-inserted inbound `EmailMessage` rows from the current sync** (never by timestamp/recency/count inference). Its first concrete implementation resolves recipient users (connection owner + existing entity-linked resolvers) and enqueues `CREATE_NOTIFICATIONS` — reusing the existing socket + VAPID fan-out. The seam must be extensible (registry/resolver pattern, mirroring the existing `domain/<entity>/notification_targets.py` convention) so AI/content rules can be added later without touching the watcher or the sync handler.
  5. A minimal, additive extension of `ProcessResult` (in `message_processor.py`) to surface the newly-created inbound message records/IDs, so the routing hook receives exact identities rather than inferring them. This is the ONLY permitted change to inbound-processing code.
  6. Sleep-mode awareness and graceful SIGTERM drain, consistent with the existing runners (`ActivityTracker`, `_shutdown_event` patterns).
  7. Settings additions (enable flag, shard count/index, reconcile cadence, IDLE renewal window, debounce/backoff intervals) with fail-fast startup validation, and a Procfile/deployment entry.
- Out of scope:
  - AI content classification (Non-goals) — seam only.
  - Any change to `process_inbound_messages`'s matching/dedup/persistence logic, MIME parsing, or thread matching — the ONLY permitted change there is the additive `ProcessResult` extension (in-scope item 5).
  - A new `EMAIL_INBOX_SYNC` task type, handler, or payload shape — the watcher reuses the existing one verbatim.
  - Direct socket/VAPID emission from the sync handler — the handler only enqueues `CREATE_NOTIFICATIONS`; the existing pipeline owns delivery.
  - Gmail API / Pub/Sub (Non-goals).
  - A new DB table for watcher state or notification-dedup state — the working set is derived from `EmailConnection` and notification idempotency is bounded by the DB insertion result (see Implementation step 7); no new schema is added.
- Assumptions:
  - The active working set is derivable from `EmailConnection WHERE status = 'active' AND deleted_at IS NULL` (status enum: `active`/`disabled`/`auth_failed`/`error`), so no new "should-watch" flag is required.
  - Triggering `EMAIL_INBOX_SYNC` (not fetching inside the watcher) is correct: IDLE only signals "the mailbox changed," not content — the existing sync task is the single, already-tested path that turns "changed" into persisted messages. This keeps the watcher thin and reuses all retry/backoff/observability of the worker runtime.
  - The existing `EMAIL_INBOX_SYNC` handler (`email_inbox_sync_handler.py`) currently persists messages but does NOT fan out any notification — confirmed by reading it — so the arrival-routing hook is genuinely new work, not a duplicate of existing behavior.
  - Reusing `CREATE_NOTIFICATIONS` yields both the in-app socket event (`notification:new`) and the VAPID push (`SEND_PUSH_NOTIFICATION`) with no new push code — confirmed by reading `handle_create_notifications`.
  - `process_inbound_messages` currently returns `ProcessResult(saved_count: int, skipped_count: int, new_thread_ids: set[str])` — confirmed by reading `message_processor.py`. It does **not** currently surface the identities of the newly-inserted `EmailMessage` rows, only counts. Notification routing therefore requires a minimal, additive extension of `ProcessResult` to also return the newly-created inbound message records/IDs (see Implementation steps 6 and 8). This is the only change permitted to the existing inbound-processing code — no change to its matching/dedup/persistence logic.
  - The watcher reuses the **exact** existing `EMAIL_INBOX_SYNC` enqueue contract — the payload shape produced by `sync_email_connection.py` via `create_instant_task` (`{connection_client_id, workspace_id, requested_by_user_id}`, confirmed by reading it). No new task type, handler, or payload schema is introduced by the watcher.

## Clarifications required

None outstanding — all four resolved by the owner on 2026-07-06 (see Decisions log below).

### Decisions log

- **IMAP IDLE client library → `aioimaplib` (async-native).** The whole runner fleet is asyncio (`init_db()` + `asyncio.run(run_*())`), so async-native IDLE keeps each idle mailbox connection a cheap coroutine on one event loop — no thread offload. Rejected `imapclient` + `asyncio.to_thread` because each idle wait would consume a threadpool slot, capping per-process connection count and reintroducing the threadpool-pressure concern from `PLAN_offload_blocking_imap_smtp_20260706`. The stdlib `imaplib` used by `ImapReader` has no clean IDLE API and is not a candidate for the watcher.
- **Scale target → fewer than 15 active connections; single process, `shard_count=1`.** At this scale a single watcher process on one event loop handles all connections comfortably. Build the deterministic sharding *interface* using a **stable cross-process hash** (see Implementation step 3 — NOT Python's built-in `hash()`, which is per-process randomized) so Acceptance Criterion 5 is satisfiable and future scale-out is a config change, but run `shard_count=1` — sharding is a latent capability, not an operational concern at current volume.
- **Arrival-routing execution locus → inline in the `EMAIL_INBOX_SYNC` handler.** Run recipient resolution + `CREATE_NOTIFICATIONS` enqueue inline right after `process_inbound_messages`, reusing the sync task's transaction — simpler, no task-per-message. Keep the routing logic isolated in `domain/emails/notification_targets.py` so promoting it to a dedicated `EMAIL_ARRIVAL_DISPATCH` task later (e.g. once AI classification lands and wants independent retry) is a small, contained change.
- **IDLE-unsupported fallback → skip + log, lean on existing sync.** Connections whose IMAP server does not advertise IDLE are skipped by the watcher and continue to rely on the existing manual/scheduled sync. Do NOT build a per-connection polling loop inside the watcher — that would re-create the polling this effort replaces.

## Acceptance criteria

1. With the watcher process running and an active email connection whose IMAP server supports IDLE, a new message arriving in the mailbox causes an `EMAIL_INBOX_SYNC` task (using the existing payload contract, no new task type) to be enqueued within seconds (no frontend action, no fixed polling delay), and the message is persisted by the existing sync pipeline.
2. The watcher maintains the IDLE session across the protocol renewal window (re-issuing IDLE at least every ~29 minutes) and automatically reconnects with capped backoff after a dropped connection, without operator intervention.
3. **Auth vs. transient failure is distinguished:** only an explicit authentication/login failure sets `EmailConnection.status = auth_failed` and stops watching that connection; network timeouts, connection resets, IDLE drops, socket closes, and temporary IMAP/protocol errors keep the connection `active` and trigger capped-backoff reconnect. `last_error` is updated for observability on failures, and cleared/refreshed after a successful reconnect+login per existing `EmailConnection` conventions. A failing connection never tight-loops or hammers the provider; other connections keep being watched.
4. The watcher reconciles its working set on a cadence: connections newly set to `active` begin being watched, and connections `disabled`/deleted/`auth_failed` are dropped, without restarting the process.
5. Running multiple watcher processes with the same `shard_count` but distinct `shard_index` values partitions the connections with **no overlap** (each connection watched by exactly one process) and **no gaps** (every active connection watched by some process), using a **stable deterministic hash** (e.g. `int.from_bytes(hashlib.sha256(client_id.encode()).digest()[:8]) % shard_count`) that yields identical assignments across processes, restarts, and deployments — verifiable by running two processes and confirming the partition.
6. **Signal coalescing:** a burst of IDLE new-mail signals for one connection does not enqueue a storm of `EMAIL_INBOX_SYNC` tasks — signals are debounced per `connection_client_id`, an equivalent already-pending/running sync is not re-enqueued (where the execution-task model supports checking), and coalesced/skipped signals are logged.
7. **Arrival routing is driven by exact new-message identities:** after a sync, only inbound `EmailMessage` rows *newly inserted by that sync operation* are passed to routing (via the extended `ProcessResult`). Messages re-observed during a re-sync are never routed. New-message detection is never inferred from timestamps, thread recency, latest-message, or message counts.
8. **Notification idempotency:** re-syncing the same mailbox or thread never creates duplicate notifications — a notification is created only as a consequence of a new inbound `EmailMessage` DB row inserted in the current sync transaction. No new notification-state table is introduced; the insertion result is the idempotency boundary.
9. **Transaction + delivery-ownership boundaries:** the newly-inserted message rows and the enqueued `CREATE_NOTIFICATIONS` task rows commit atomically in the sync handler's transaction. The sync handler does NOT emit socket events or VAPID pushes directly — it only enqueues `CREATE_NOTIFICATIONS`; the existing notification pipeline remains solely responsible for socket fan-out and VAPID delivery.
10. **First-version target resolution is conservative:** the connection owner is always a target; entity-linked users are added ONLY by reusing existing `resolve_<entity>_notification_targets` resolvers where they already exist. No new task/case/customer assignment logic is invented inside the email watcher/routing implementation. The resolver lives in `domain/emails/notification_targets.py` as the extension seam for future content/AI rules.
11. Enqueuing `CREATE_NOTIFICATIONS` results in both an in-app `notification:new` socket event and a VAPID push (via the existing `SEND_PUSH_NOTIFICATION` path) — with no duplicate push code introduced.
12. The routing layer is structured so a new recipient source or content-based rule can be added by editing the single `domain/emails/notification_targets.py` resolver, without changes to the watcher or the sync handler.
13. **Settings fail fast:** invalid watcher settings (`shard_count < 1`, `shard_index` outside `[0, shard_count)`, `renew_seconds` not safely below the ~29-minute IDLE window, non-positive/unbounded reconcile/debounce/backoff intervals) cause the watcher to fail on startup rather than silently run with unsafe behavior.
14. For an IMAP server that does not advertise/support IDLE, the watcher skips watching that connection and logs it; it does NOT start a per-connection polling loop. Those connections continue to rely on the existing manual/scheduled sync.
15. The watcher respects sleep mode and drains gracefully on SIGTERM (closing IDLE connections cleanly), consistent with the other runners.
16. The watcher is registered as a Procfile process and is independently deployable/scalable, matching the existing process-per-responsibility deployment model.

## Contracts and skills

> Read order per `task_system/backend_contract_goal_mapping_guide.md`: canonical first, then `*_local.md` companion if present; local overrides baseline for this app only.

### Contracts loaded

Core contracts (always):
- `../architecture/01_architecture.md`: overall layering and where a new infra runner belongs.
- `../architecture/04_context.md`: `ServiceContext` shape for any command/handler work.
- `../architecture/05_errors.md`: error-raising conventions in the routing/handler code.
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: `maybe_begin` transaction utility, session-call safety, subordinate-command event rule — for the arrival-routing enqueue and any command touchpoints.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: read patterns for loading the connection working set and recipient resolution.
- `../architecture/09_routers.md`: only if a management/health endpoint is added (likely not — watcher is process-only).
- `../architecture/21_naming_conventions.md`, `../architecture/40_identity.md`, `../architecture/41_user.md`, `../architecture/42_event.md`, `../architecture/48_presence.md`: naming, identity/user resolution for recipients, event emission, and presence-based exclusion (the notification pipeline already excludes users currently viewing an entity).

Added from guide — Worker-driven backend bundle (trigger: new long-running worker process, "worker", "stale task", "retry"):
- `../architecture/16_background_jobs.md`: the execution-task model, `create_instant_task`, task-type registration, and retry/backoff the watcher relies on by delegating to `EMAIL_INBOX_SYNC`.
- `../architecture/12_infra_redis.md`: Redis usage conventions (queues, and any coordination the shard model needs).
- `../architecture/51_worker_runtime.md`: the long-running runner lifecycle, SIGTERM handling, and handler-timeout conventions the watcher must follow.
- `../architecture/49_observability_runtime.md`: structured logging/correlation for a new always-on process.
- `../architecture/54_ci_cd_runtime.md`: registering a new process type in the deployment pipeline.

Added — realtime/notification reuse:
- `../architecture/13_sockets.md`: socket event conventions (the `notification:new` fan-out the routing triggers).
- `../architecture/11_infra_events.md`: event build/dispatch used by the notification pipeline.
- `../architecture/08_domain.md`: where the recipient-resolution domain logic (`domain/emails/notification_targets.py`) belongs, mirroring existing `notification_targets.py` modules.

Added — deployment/config:
- `../architecture/33_deployment.md`: adding the Procfile process and scaling model.
- `../architecture/30_migrations.md`: not needed for this plan — no new schema (working set derived from `EmailConnection`); listed only for completeness in case implementation surfaces an unforeseen column need.

### Local extensions loaded

- `06_commands_local.md`, `07_queries_local.md`: load both per the guide (local adds `maybe_begin`, session-call safety, offset pagination). Report deltas in the pre-code output block.

### File read intent — pattern vs. relational

Pattern reads (HOW to write) → the contracts above; do not substitute implementation files for these.

Relational reads (WHAT exists) already performed and sufficient:
- `workers/task_router_process.py`, `workers/tasks_worker.py`, `workers/recurring_scheduler_runner.py`, `services/infra/schedulers/recurring_scheduler_runner.py`, `services/infra/execution/task_router.py`, `services/infra/execution/worker_base.py` — the long-running-process + reconcile-loop + SIGTERM/sleep patterns to mirror.
- `Procfile`, `docker-compose.yml` — the process-per-responsibility launch model.
- `models/tables/emails/email_connection.py`, `domain/emails/enums.py` (`EmailConnectionStatusEnum`) — the working-set query source and status values to set on failure.
- `services/tasks/email_inbox_sync_handler.py`, `services/commands/emails/sync_email_connection.py`, `services/infra/execution/task_factory.py` — the exact `EMAIL_INBOX_SYNC` trigger to reuse and confirmation it currently emits no notification.
- `services/tasks/notifications/create_notifications.py`, `domain/cases/notification_targets.py`, `services/infra/push/vapid.py` — the recipient-resolution + `CREATE_NOTIFICATIONS` + VAPID pipeline to reuse for arrival routing.
- `services/infra/email_providers/smtp_imap/imap_reader.py` — current `imaplib` connection/auth logic to reference when building the IDLE connection (decrypting creds, security modes).

### Skill selection

- Primary skill: n/a beyond the contract set (new infra runner + task reuse + domain resolver).
- Router trigger terms: `worker, background job, retry, stale task, sockets, notification, deployment process`.
- Excluded alternatives: replay/reprocess contracts (`52`, `53`) — not needed; the watcher triggers idempotent syncs and holds no replayable state of its own.

> **Before writing any code**, read the existing `EMAIL_INBOX_SYNC` factory/handler input contract (`sync_email_connection.py` → `create_instant_task`, and `email_inbox_sync_handler.py`) and reuse that payload shape *exactly*. Do not create a parallel sync pathway, a new task type, a new handler, or a new payload schema. The watcher's only job is: detect change → enqueue the existing `EMAIL_INBOX_SYNC` with its existing contract.

1. **Settings + Procfile (with fail-fast validation).** Add settings: `email_idle_enabled` (bool), `email_idle_shard_count` (int, default 1), `email_idle_shard_index` (int, default 0), `email_idle_reconcile_seconds`, `email_idle_renew_seconds`, `email_idle_debounce_seconds`, `email_idle_backoff_max_seconds`. Validate on watcher startup and **fail fast** (raise, do not silently run) if: `shard_count < 1`; `shard_index` not in `[0, shard_count)`; `renew_seconds` not safely below the ~29-minute IDLE window (e.g. `> 1680`); or any of reconcile/debounce/backoff intervals is non-positive or unbounded. Add Procfile entry `email-idle-watcher: python beyo_manager/workers/email_idle_watcher.py`.
2. **Entrypoint.** `workers/email_idle_watcher.py` mirroring `task_router_process.py`: `await init_db()` then `await run_email_idle_watcher()`.
3. **Supervisor + stable sharding.** `services/infra/email_idle/supervisor.py` with `run_email_idle_watcher()`:
   - Provide `owns_connection(client_id) -> bool` using a **stable, deterministic, cross-process hash** — e.g. `int.from_bytes(hashlib.sha256(client_id.encode("utf-8")).digest()[:8], "big") % shard_count == shard_index`. **Do NOT use Python's built-in `hash()`** — it is per-process randomized (PYTHONHASHSEED) and would assign the same connection to different shards across processes/deployments.
   - Reconcile loop: every `reconcile_seconds`, load active connections (`status='active' AND deleted_at IS NULL`), filter via `owns_connection`, start watch tasks for newly-owned connections, cancel tasks for connections no longer active/owned.
   - Sleep-mode aware and SIGTERM-draining, reusing the `ActivityTracker` + `_shutdown_event` patterns.
4. **Per-connection watcher.** `services/infra/email_idle/connection_watcher.py`:
   - Open an authenticated IMAP IDLE session, entering IDLE on the configured inbox folder.
   - **On a new-mail signal:** debounce per `connection_client_id` over `debounce_seconds`; before enqueuing, skip if an equivalent `EMAIL_INBOX_SYNC` for the same connection is already pending/running *where the execution-task model supports checking this cheaply*; otherwise enqueue the existing `EMAIL_INBOX_SYNC` via `create_instant_task` with its exact payload. Log when a signal is coalesced or skipped because a sync is already queued/running. (Goal: prevent obvious duplicate storms, not perfect global locking — the sync is idempotent by provider UID anyway.)
   - **Renew IDLE** within `renew_seconds` (< 29-min window).
   - **Failure handling — distinguish auth from transient:**
     - Explicit authentication/login failure → set `EmailConnection.status = auth_failed`, update `last_error`, and stop watching this connection until the next reconcile. Do not reconnect-loop.
     - Transient failure (network timeout, connection reset, temporary IMAP/server error, IDLE drop, socket close, protocol interruption) → keep the connection `active`, update `last_error` for observability, and reconnect with **capped exponential backoff**. After a successful reconnect+login, clear/refresh the stale `last_error` per existing `EmailConnection` conventions. Never hammer the provider after repeated failures.
   - **IDLE-unsupported:** if the server does not advertise IDLE capability, skip watching this connection and log it — do NOT start a per-connection polling loop; it falls back to the existing manual/scheduled sync.
5. **Library integration mirroring `ImapReader`.** Implement the IDLE session with `aioimaplib` (decided; add to `requirements.txt`), isolated behind a small interface in `services/infra/email_idle/` (mirrors how `adapter.py` isolates the provider). The connection code MUST mirror the existing `ImapReader` behavior for every provider-specific detail — credential decryption, `imap_host`, `imap_port`, `imap_username`, `imap_password` (decrypted), `imap_security` mode, SSL/TLS vs STARTTLS selection, selected inbox/`inbox_folder`, and timeout behavior. **Do NOT hardcode SSL assumptions** — the watcher must support the same generic IMAP providers the current sync reader supports, driven by the `EmailConnection` fields.
6. **Extend `ProcessResult` (minimal, additive).** In `message_processor.py`, extend `ProcessResult` to also carry the newly-created inbound `EmailMessage` records (or their `client_id`s, captured after `session.flush()` so identities are assigned). Do not change any matching/dedup/persistence logic — only add the return data. This is what lets routing act on exact new-message identities.
7. **Arrival-routing seam.** `domain/emails/notification_targets.py`: `resolve_email_notification_targets(session, thread, connection) -> set[str]`:
   - ALWAYS include `connection.owner_user_id`.
   - Add entity-linked users ONLY by reusing an existing `resolve_<entity>_notification_targets` resolver when `thread.entity_type` maps to a domain that already has one (e.g. task/case). Do NOT invent new task/case/customer assignment logic here.
   - Use the concurrent-source pattern from `domain/cases/notification_targets.py`; keep it a single module so future content/AI rules are added here without touching the watcher or sync handler.
8. **Wire routing into arrival (inline, decided) — exact-identity + transaction rules.** In `email_inbox_sync_handler.py`, after `process_inbound_messages` returns, iterate ONLY the newly-inserted inbound message records from the extended `ProcessResult`. For each, resolve targets and enqueue `CREATE_NOTIFICATIONS` (title/body from the message subject/preview, `entity_type`/`entity_client_id` from the thread) **within the same transaction**, so the new message rows and the `CREATE_NOTIFICATIONS` task rows commit atomically. Exclude currently-viewing users via the existing `exclude_viewing` mechanism. The handler MUST NOT emit socket events or VAPID pushes directly — only enqueue `CREATE_NOTIFICATIONS`; the existing pipeline owns delivery. Never route messages inferred by timestamp/recency/count — only the exact new-insertion set.
9. **Observability.** Structured logs for watch start/stop, reconcile deltas, IDLE renew, reconnect/backoff (with attempt count), auth-failure vs transient-failure classification, signal coalesce/skip, and enqueue-on-arrival, per `49_observability_runtime.md`.

## Risks and mitigations

- Risk: **Sharding with Python's built-in `hash()` splits or duplicates the working set** because `hash()` of a str is randomized per process (PYTHONHASHSEED), so different watcher processes would disagree on which shard owns a connection — causing both gaps (unwatched connections) and overlaps (double-watched).
  Mitigation: Use a stable content hash (`hashlib.sha256`/CRC32 of `client_id`), never `hash()` (Implementation step 3, Acceptance Criterion 5). This is a hard blocker called out explicitly for Codex.
- Risk: One persistent connection per mailbox does not scale on a single process/event loop as connection count grows.
  Mitigation: At the confirmed scale (< 15 connections) a single process is ample; the stable-hash sharding interface is built (dormant at `shard_count=1`) so scale-out is a config change. `aioimaplib` keeps each idle wait a cheap coroutine rather than a thread.
- Risk: IDLE signal storms (many rapid `EXISTS` notifications) could enqueue redundant `EMAIL_INBOX_SYNC` tasks.
  Mitigation: Debounce per connection + skip-if-already-pending/running before enqueuing (Implementation step 4); the sync itself is idempotent (dedupes by provider UID), so an occasional extra enqueue is harmless. Aim is storm prevention, not perfect global locking.
- Risk: Treating a transient network/IDLE drop as an auth failure would wrongly disable a healthy connection (and vice-versa — treating an auth failure as transient would hammer the provider and risk account lockout).
  Mitigation: Explicit auth-vs-transient classification (Implementation step 4, Acceptance Criterion 3): only real login failures set `auth_failed` and stop; transient failures keep `active` and reconnect with capped exponential backoff; never tight-loop.
- Risk: **Duplicate notifications** if routing acts on messages re-observed during a re-sync, or if new-message detection is inferred from timestamps/recency/counts.
  Mitigation: Route ONLY the exact inbound rows newly inserted by the current sync, surfaced via the extended `ProcessResult` (Implementation steps 6-8). The DB insertion result is the idempotency boundary; re-syncs re-observing existing messages produce zero notifications. No new dedup-state table.
- Risk: The sync handler taking on direct socket/VAPID delivery would fork notification responsibility away from the existing pipeline.
  Mitigation: The handler only enqueues `CREATE_NOTIFICATIONS` within the sync transaction (atomic with the message inserts); the existing pipeline remains the sole owner of socket fan-out and push delivery (Acceptance Criterion 9).
- Risk: A watcher process crash silently stops real-time ingestion for its shard.
  Mitigation: Process supervised/restarted by the platform (same as other Procfile processes); the existing manual/scheduled sync remains as the safety net so mail is never permanently missed, only delayed. Structured heartbeat logging per `49` is sufficient at current scale; no dedicated health table/endpoint added.
- Risk: Hardcoding SSL/TLS assumptions in the new IDLE connection would break non-SSL/STARTTLS or other generic IMAP providers the current reader supports.
  Mitigation: Mirror `ImapReader`'s connection semantics driven by `EmailConnection` fields (`imap_security`, host/port, decrypted creds, folder, timeouts) — Implementation step 5; provider-agnostic behavior covered by Acceptance Criteria 1 and 14 and the provider-agnostic connection validation step.

## Validation plan

- Static: `ruff check` + type check on all new/changed files.
- Settings fail-fast: start the watcher with each invalid setting (`shard_count=0`, `shard_index>=shard_count`, `renew_seconds` above the safe window, non-positive interval) and confirm it raises on startup rather than running.
- IDLE trigger (core): against a test IMAP account (or a local IMAP server such as Dovecot/GreenMail), start the watcher, deliver a message, and assert an `EMAIL_INBOX_SYNC` task is enqueued within seconds (with the existing payload shape) and the message is persisted — with the web server NOT involved and no frontend polling.
- Coalescing: deliver a burst of messages / trigger rapid EXISTS signals and confirm sync enqueues are debounced (not one-per-signal), and that a coalesce/skip is logged.
- Renewal/reconnect: hold the connection idle past the renewal window and confirm IDLE is re-issued; kill the connection mid-idle and confirm reconnect-with-backoff resumes watching **without** flipping `status` to `auth_failed`.
- Auth vs transient: force a login failure and confirm `status=auth_failed` + watch stops for that connection only; force a transient drop and confirm the connection stays `active`, backs off, reconnects, and refreshes `last_error`.
- Reconcile: flip a connection `active`→`disabled` and back; confirm the watcher drops then resumes it without a restart.
- Stable-hash sharding: run two watchers with `shard_count=2`, indexes 0/1; assert every active connection is watched by exactly one, none by both — and that the assignment is identical across process restarts (proving `hash()` is not used).
- Arrival routing (exact-identity + idempotency): deliver a message to a connection whose thread links to a task with an assignee; assert a `CREATE_NOTIFICATIONS` task is enqueued for the correct users (owner + assignee) and that both the `notification:new` socket event and a `SEND_PUSH_NOTIFICATION` (VAPID) task result. Then **re-run the sync on the same mailbox** and assert ZERO new notifications (idempotency boundary = new DB insertion only).
- Transaction atomicity: simulate a failure between message insert and `CREATE_NOTIFICATIONS` enqueue and confirm neither is committed (no orphaned message without its notification task, no notification for an uncommitted message).
- Delivery ownership: confirm `email_inbox_sync_handler.py` contains no direct socket/VAPID call — only the `CREATE_NOTIFICATIONS` enqueue.
- Graceful shutdown: SIGTERM the watcher and confirm IDLE connections close cleanly and in-flight enqueues are not lost.
- Provider-agnostic connection: confirm the IDLE session honors `imap_security` (SSL vs STARTTLS vs none) from `EmailConnection` rather than assuming SSL — test against at least two security modes if the test environment allows.
- Fallback: point a connection at an IMAP server without IDLE capability; confirm the watcher skips+logs it and the existing sync path still works for it.

## Handoff notes (frontend coordination)

- The existing manual/targeted sync endpoints (`/sync-targeted`, `/{thread_id}/sync`, connection sync) remain available as a fallback and as explicit user-triggered refresh actions — they are NOT removed by this work.
- After watcher deployment, real-time inbound updates should arrive through the **existing notification/socket/push pipeline** once new inbound messages are persisted (via `CREATE_NOTIFICATIONS` → `notification:new` socket event + VAPID push). The frontend does not need to call sync to learn about new mail in the normal case.
- The frontend should still refresh inbox/thread/unread-count data on relevant socket/push events and on normal screen re-entry — the socket/push signal is a best-effort real-time nudge, and the DB remains the source of truth (consistent with the earlier "socket = hint, DB = truth" principle used across the email work).

## Review log

- `2026-07-06` `claude`: Drafted from a read of the existing runner/deployment model (Procfile process-per-responsibility, `init_db()`+`run_*()` entrypoints), the `EMAIL_INBOX_SYNC` pipeline (which the watcher will trigger rather than duplicate), and the established notification-routing pattern (`domain/<entity>/notification_targets.py` + `CREATE_NOTIFICATIONS` → socket + VAPID). Contracts selected per `backend_contract_goal_mapping_guide.md` core + worker-driven bundle + realtime/notification reuse. Four clarifications flagged (IDLE library, scale/sharding, routing locus, IDLE-unsupported fallback), each with a recommended default.
- `2026-07-06` `david`: Settled all four clarifications — `aioimaplib` for IDLE, single process at `shard_count=1` (expected < 15 connections; sharding interface built but dormant), arrival routing inline in the sync handler, and skip+log fallback for non-IDLE servers.
- `2026-07-06` `david`: Requested 12 pre-implementation corrections. Applied by `claude`: (1) reuse existing `EMAIL_INBOX_SYNC` contract exactly — no new task/handler/payload; (2) explicit per-connection debounce + skip-if-pending coalescing with logging; (3) **stable cross-process hash for sharding — never Python `hash()`** (blocker); (4) fail-fast settings validation; (5) IDLE connection must mirror `ImapReader`'s provider-specific semantics, no hardcoded SSL; (6) explicit auth-vs-transient failure handling; (7) **route only exact newly-inserted inbound message rows via a minimal additive `ProcessResult` extension — no timestamp/recency/count inference** (blocker); (8) notification idempotency bounded by DB insertion, no new state table; (9) atomic commit of message rows + `CREATE_NOTIFICATIONS`, no direct socket/VAPID from the sync handler; (10) conservative first-version targets (owner always + existing entity resolvers only); (11) keep IDLE-unsupported skip+log; (12) frontend-coordination handoff note added. Both named blockers are now hard requirements in Scope, Implementation, Acceptance Criteria, and Validation. Plan is ready for Codex implementation.
- `2026-07-06T08:25:48Z` `codex`: Implemented the email IDLE watcher runtime, added inline exact-new-message notification routing to `EMAIL_INBOX_SYNC`, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_email_idle_watcher_20260706.md`, created `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_email_idle_watcher_20260706.md`, and archived this plan. The linked intention-plan file referenced in metadata was not present in the repo, so there was no intention document to update.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
