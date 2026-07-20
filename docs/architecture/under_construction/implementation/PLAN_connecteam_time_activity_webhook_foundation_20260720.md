# PLAN_connecteam_time_activity_webhook_foundation_20260720

## Metadata

- Plan ID: `PLAN_connecteam_time_activity_webhook_foundation_20260720`
- Status: `approved`
- Owner agent: `codex`
- Created at (UTC): `2026-07-20T00:00:00Z`
- Last updated at (UTC): `2026-07-20T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_connecteam_time_activity_webhook_20260720.md`

## Goal and intent

- Goal: Build the complete Connecteam time-activity webhook foundation — authenticated intake, idempotent deduplication, durable queueing, retry/dead-letter handling, Connecteam-user → `UserWorkProfile` resolution, and event-specific **placeholder** handlers for `clock_in`, `clock_out`, and `auto_clock_out`.
- Business/user intent: Connecteam is the company's time-clock. This phase wires its webhook deliveries safely into the backend so a later phase can attach real clock-in/clock-out domain actions. Nothing in this phase may create, update, or close internal working-time records.
- Non-goals: worker shift/session mutations; timeline or analytics writes; Connecteam REST API calls; automatic user synchronization; any Connecteam event family other than the three time-activity events; frontend pages; a `manual_break` processing path (explicitly ignored).

## Scope

- In scope:
  - New `connecteam` integration boundary (domain DTOs, verifier, intake command, task handler, placeholder handlers, worker, router).
  - `connecteam_user_id` column + index + uniqueness constraint on `user_work_profiles`, with Alembic migration.
  - New `TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY`, queue `queue:connecteam`, dedicated worker process.
  - Redis `SET NX EX` deduplication keyed by deterministic event identity.
  - Typed settings, startup validation, structured lifecycle logging, CLI inspection commands, tests, ngrok validation doc.
- Out of scope: everything listed under intention §3 "Out of scope"; changes to `worker_base.py` retry semantics; a new Connecteam-specific Redis queue framework (see Clarification 1); `user_shift_state_record` / `clock_*_worker_shift` code paths (read-only reference only).
- Assumptions:
  - Single Connecteam company connected today; envelope still carries `company_id` for future scoping.
  - `CONNECTEAM_WEBHOOK_SECRET` already present in the environment.
  - The three event types can each arrive with `activity_type` of `shift` or `manual_break`.

## Clarifications required

- [x] **RESOLVED 2026-07-20 (owner): reuse the ExecutionTask pipeline (hybrid — Redis dedup + ExecutionTask queue/retry/dead-letter).** Original question: Queue substrate: reuse the ExecutionTask pipeline (recommended) or build the Redis-only queue described in intention §10–§17? — This blocks safe implementation because the two directives in the intention conflict. Intention §3 excludes "persisting webhook events in PostgreSQL", and §10–§18 specify a full Redis-native queue (pending/processing lists, sorted-set retry scheduler, dead-letter key, visibility-timeout recovery). But intention §25 mandates: *"Reuse existing infrastructure where it already provides queueing, retries, delayed execution, or worker recovery. Do not introduce a second generic queue framework solely for Connecteam."* The backend's existing — and only — reliable queue is the ExecutionTask system, which is **PostgreSQL-backed**: `services/infra/execution/task_factory.py` writes `ExecutionTask` + `ExecutionPayload` rows; `task_router.py` routes `OPEN` tasks onto Redis lists (`QUEUE_MAP`); `worker_base.py` claims via `FOR UPDATE SKIP LOCKED`, retries with backoff + jitter (`RETRY_SCHEDULED`/`next_retry_at`), recovers stale `IN_PROGRESS` (90 min) and stuck `PENDING` (5 min) tasks, rescues in-flight tasks on SIGTERM, and marks exhausted tasks `FAIL`. The Shopify webhook (contract `57_shopify_integration.md`) already uses exactly this pipeline. **Recommendation (this plan is written against it): hybrid — Redis `SET NX EX` for deduplication (honoring §10) + ExecutionTask pipeline for queue/retry/recovery/dead-letter (honoring §25).** The webhook payload then transits Postgres as execution infrastructure (`execution_payloads.payload`), which technically touches the "no PostgreSQL persistence" exclusion — but no webhook-intake domain table is created, and durability, retry, recovery, and dead-letter come for free instead of being re-implemented. If the owner insists on Redis-only, steps 6–8 below are replaced by a new `infrastructure/redis/connecteam_webhook_queue.py` implementing intention §11/§16/§17 verbatim — a materially larger and convention-breaking build.
- [x] **APPROACH APPROVED 2026-07-20 (owner); findings pending step 1.** Not an owner decision — resolves during implementation via the discovery run; the implementer must append the verified contract to the Review log before enabling verification outside development. Original text: Connecteam signature contract is unverified. — Blocks enabling strict verification. Connecteam documents that the webhook secret is used for signature verification, but the exact header name, digest algorithm, encoding, prefix, and signed content are not published in a form this plan may assume, and intention §7 forbids inventing them. Step 1 performs an empirical discovery run through the existing ngrok tunnel (dev-only logging of header *names*, never values). The verifier ships behind that discovery: implementation cannot be finalized, and the endpoint must not run in any non-development environment, until the contract is recorded in this plan's Review log. If discovery shows Connecteam sends only a static shared secret header (no HMAC), the verifier does a constant-time comparison of that header against the configured secret instead.
- [x] **RESOLVED 2026-07-20 (owner): adapt to what the architecture currently provides — platform backoff (30s/120s/300s ±15%, `max_try=5`); no changes to shared `worker_base.py` for this integration.** Original question: Accept the platform retry schedule instead of intention §16's schedule? — Minor, but it changes an acceptance criterion. `worker_base.py` applies a global backoff of 30s/120s/300s ±15% jitter with per-task `max_try` (we set 5). The intention suggests 10s/30s/2m/10m/30m. Matching the intention exactly would require modifying shared `worker_base.py` for every worker in the system. Recommendation: accept the platform schedule (bounded backoff with jitter is preserved; only the exact intervals differ).

## Acceptance criteria

1. `POST /api/v1/connecteam/webhooks/time-activity` accepts valid `clock_in`, `clock_out`, and `auto_clock_out` deliveries and returns success quickly, without performing worker resolution inline.
2. Missing/invalid webhook authentication is rejected with 401 before payload parsing or enqueueing; malformed JSON returns 400; recognized envelopes missing required identity fields return 422; `CONNECTEAM_WEBHOOK_ENABLED=false` returns a controlled 503-style error, never silent acceptance.
3. A redelivered event (same `event_key`) is acknowledged with success and creates no second ExecutionTask (verified by test).
4. An accepted event survives worker downtime: the ExecutionTask row persists and is processed when the worker returns.
5. A handler failure is retried up to 5 attempts with the platform backoff; after exhaustion the task reaches `FAIL` state (dead-letter) and is listable/requeueable via the CLI.
6. Stale/abandoned processing recovery works via the existing task-router stale/stuck sweeps (no new mechanism required — verified by relational read, asserted in tests only for FAIL/requeue).
7. `user_work_profiles.connecteam_user_id` exists (nullable `String(64)`), indexed, unique per `(workspace_id, connecteam_user_id)`; existing rows remain valid; downgrade is clean; multiple NULLs coexist.
8. The resolver maps a Connecteam user ID to exactly one `UserWorkProfile`; unknown IDs produce an explicit `worker_not_mapped` outcome (no retry loop); ambiguous mappings produce a non-retryable integration error; no email/name/phone fallback exists.
9. `activity_type == "manual_break"` deliveries are acknowledged at intake but never reach worker resolution or handlers (`ignored_activity_type`); unknown event types never invoke handlers.
10. Each supported event type reaches its dedicated placeholder handler, which logs and performs zero work-session writes — asserted by tests that no `user_shift_state_record` (or any worker-state) rows change.
11. Secret and signature values never appear in logs; lifecycle events from intention §19 are emitted via `log_event`.
12. Test suite covers verifier, router statuses, normalization/policy, deduplication, task lifecycle (retry → FAIL → requeue), resolver, dispatcher, and migration behavior.

## Contracts and skills

### Contracts loaded

Selected contracts (core, always included):
- `backend/architecture/01_architecture.md`: layering and boundaries for the new integration.
- `backend/architecture/04_context.md`: `ServiceContext` shape for the intake command.
- `backend/architecture/05_errors.md`: `DomainError` subclasses with `http_status` for 400/401/422/503 mapping.
- `backend/architecture/06_commands.md`: command structure for `enqueue_connecteam_time_activity_webhook`.
- `backend/architecture/07_queries.md`: resolver query structure.
- `backend/architecture/09_routers.md`: thin-router wiring (`run_service`, `build_ok`/`build_err`).
- `backend/architecture/21_naming_conventions.md`: file/function/constraint naming.
- `backend/architecture/40_identity.md`: `client_id`/IdentityMixin usage.
- `backend/architecture/41_user.md`: `UserWorkProfile` ownership rules for the new column.
- `backend/architecture/42_event.md`: event vocabulary (relevant to integration lifecycle events).
- `backend/architecture/48_presence.md`: core-mandated; confirms what this phase must NOT touch (worker state).

Added from guide (goal bundle: **Worker-driven backend** + triggers):
- `backend/architecture/16_background_jobs.md`: trigger "worker/retry/dead letter" — ExecutionTask conventions.
- `backend/architecture/12_infra_redis.md`: trigger "worker/retry" — Redis client + `make_key` conventions for the dedup key.
- `backend/architecture/51_worker_runtime.md`: trigger "worker" — worker process registration and shutdown.
- `backend/architecture/49_observability_runtime.md`: trigger "structured logs" — `log_event` usage.
- `backend/architecture/17_logging.md`: trigger "structured logs" — redaction rules for secrets.
- `backend/architecture/31_health_observability.md`: trigger "observability" — operational diagnostics.
- `backend/architecture/54_ci_cd_runtime.md`: bundle member — CI expectations for new worker/migration.
- `backend/architecture/03_models.md`: model change on `user_work_profiles`.
- `backend/architecture/30_migrations.md`: Alembic migration + enum-value migration conventions.
- `backend/architecture/15_testing.md`: test layout under `backend/tests/`.
- `backend/architecture/18_security.md`: unauthenticated public endpoint hardening.
- `backend/architecture/19_integrations.md`: adapter pattern — provider code isolated under `services/infra/connecteam/`.
- `backend/architecture/57_shopify_integration.md`: the documented precedent integration; explicitly instructs new integrations to read it rather than re-derive the pattern.

Excluded contracts:
- `13_sockets.md` / `56_realtime_layer.md`: no realtime surface this phase.
- `52_replayability.md` / `53_operational_cli.md` beyond minimal CLI: requeue is provided by flipping FAIL→OPEN; full replay framework out of scope.
- `11_infra_events.md`: no domain-event emission this phase (placeholder handlers are no-ops).
- `34_file_storage.md`, `55_query_filters_local.md`, `24_multi_tenancy.md` (workspace scoping is handled via the `UserWorkProfile.workspace_id` column already mandated by 41): not needed now.

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` transaction utility + session call safety — used in the intake command.
- `backend/architecture/07_queries_local.md`: offset pagination override — applies to CLI listing query.
- `backend/architecture/40_identity_local.md`: app-specific identity deltas for `client_id` handling.
- `backend/architecture/41_user_local.md`: app-specific user/work-profile field rules.
- `backend/architecture/42_event_local.md`: app-specific event deltas.
- `backend/architecture/48_presence_local.md`: app-specific presence deltas (read to confirm non-interference).

Applied precedence: canonical first, local second; local wins for this app.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists; these were performed while authoring this plan and may be repeated):
- `services/infra/execution/task_factory.py`, `task_router.py`, `worker_base.py` — exact enqueue/claim/retry/recovery semantics being reused.
- `routers/api_v1/shopify_webhooks.py`, `services/commands/shopify/enqueue_or_record_shopify_webhook.py`, `services/infra/shopify/hmac_verifier.py`, `workers/shopify_worker.py` — the precedent integration's actual wiring.
- `models/tables/users/user_work_profile.py` — exact current columns/constraints.
- `routers/api_v1/__init__.py` — registration order and prefixes.
- `config.py` — settings field style, `_resolve_env_file`, required-settings check.
- `services/infra/redis/keys.py` (`make_key`), `services/infra/redis/client.py`.
- `domain/execution/enums.py` — TaskType members; `migrations/versions/e1b2c3d4f5a6_add_email_sync_targeted_task_type.py` — how a TaskType enum value is migrated.
- `migrations/versions/` head check (current head: `b4074f2e26c4`).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/planning_contract_selection/SKILL.md` (used to assemble the contract set above); no domain skill covers external integrations.
- Router trigger terms: `webhook, integration, worker, retry, dead letter, migration`
- Excluded alternatives: `backend/skills/domains/*` — all seven domain skills (case, content, events, identity, image, notifications, presence) target other domains; none owns integrations.

## Implementation plan

Design constants used throughout:
- Task type: `TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY = "connecteam_process_time_activity"`
- Queue: `queue:connecteam` (added to `QUEUE_MAP` in `task_router.py`)
- Dedup key: `make_key("connecteam", "webhooks", "dedup", event_key)` → `beyo_manager:connecteam:webhooks:dedup:{event_key}`
- Event key: `connecteam:{request_id}` when present; else `connecteam:sha256(company_id|event_type|activity_type|connecteam_user_id|time_clock_id|time_activity_id|event_timestamp|sha256(raw_body))`
- Route: `POST /api/v1/connecteam/webhooks/time-activity`, registered with prefix `/api/v1/connecteam`, tag `connecteam-webhooks` (mirrors Shopify's `/api/v1/shopify` webhook prefix; admin routes, when they exist later, go under `/api/v1/integrations/connecteam`).

Steps:

1. **Signature-contract discovery (gate for step 4).** Add a temporary, `settings.connecteam_integration_debug_logs`-gated branch in the new router (step 8) that logs incoming header **names** only (`sorted(request.headers.keys())`) plus body length — never values. Run one real `clock_in` through the existing ngrok tunnel. Record in the Review log: header name(s), whether the value is an HMAC (and of what: raw body vs timestamp+body), digest/encoding, any prefix, any timestamp header. Save the redacted payload as `backend/tests/connecteam/fixtures/time_activity_clock_in.json` (redact names/phones; keep structure). Repeat for `clock_out`; capture a `manual_break` variant if obtainable.

2. **Settings** — modify `backend/app/beyo_manager/config.py`. Add, following existing alias style:
   - `connecteam_webhook_secret: str | None = Field(default=None, alias="CONNECTEAM_WEBHOOK_SECRET")`
   - `connecteam_webhook_enabled: bool = Field(default=True, alias="CONNECTEAM_WEBHOOK_ENABLED")`
   - `connecteam_webhook_dedup_ttl_seconds: int = Field(default=604800, alias="CONNECTEAM_WEBHOOK_DEDUP_TTL_SECONDS")`
   - `connecteam_integration_debug_logs: bool = Field(default=False, alias="CONNECTEAM_INTEGRATION_DEBUG_LOGS")`
   Extend the existing required-settings validation: when `connecteam_webhook_enabled` is true and `connecteam_webhook_secret` is empty → raise at startup with a clear message. The intention's queue/processing/retry/dead-letter key and max-attempt/processing-timeout settings are **intentionally dropped**: queue/retry/recovery is owned by the ExecutionTask pipeline (`max_try=5` is passed at task creation; processing timeout is `worker_base.HANDLER_TIMEOUT_SECONDS` default 300s; stale recovery is task-router policy).

3. **Domain layer** — new package `backend/app/beyo_manager/domain/connecteam/` (mirrors `domain/shopify/`):
   - `__init__.py`
   - `enums.py`: `ConnecteamEventTypeEnum` (`CLOCK_IN`, `CLOCK_OUT`, `AUTO_CLOCK_OUT`), `ConnecteamActivityTypeEnum` (`SHIFT`, `MANUAL_BREAK`, `UNKNOWN`), `ConnecteamIntakeOutcomeEnum` (`accepted`, `duplicate`, `ignored_activity_type`, `unsupported_event_type`), `ConnecteamProcessingOutcomeEnum` (`processed`, `worker_not_mapped`, `ambiguous_mapping`, `ignored_activity_type`).
   - `webhook_payloads.py`: tolerant provider DTOs (`ConfigDict(extra="allow")`) for the outer envelope and the time-activity body, shaped from the step-1 fixture — capture `request_id`, `company`/`company_id`, `event_type`, `activity_type`, `event_timestamp`, `user_id`, `time_clock_id`, `time_activity_id`, nested `data`/`time_activity`. Field nesting is finalized against the real fixture, not guessed.
   - `time_activity_event.py`: frozen dataclass `ConnecteamTimeActivityEvent` — the internal normalized envelope (`event_key, provider="connecteam", event_type, activity_type, request_id, company_id, connecteam_user_id, time_clock_id, time_activity_id, occurred_at, received_at, payload`) plus `event_key` builder (primary: `request_id`; fallback: deterministic hash as specified above — never `user_id + event_type` alone). Provider field names do not leak past `webhook_payloads.py` + the normalizer.
   - `normalize_time_activity_event.py`: provider DTO → `ConnecteamTimeActivityEvent`; raises typed errors for missing required identity fields (→ 422).

4. **Verifier (adapter)** — new `backend/app/beyo_manager/services/infra/connecteam/webhook_verifier.py` (+ `__init__.py`), mirroring `services/infra/shopify/hmac_verifier.py`: `verify_connecteam_webhook(raw_body: bytes, headers: Mapping[str, str]) -> None`, raising `ConnecteamWebhookAuthError` (see step 5). Implementation per the **verified** step-1 contract; in all cases `hmac.compare_digest` on values derived from raw body bytes (or constant-time compare of a static secret header if that is what discovery shows). Secret read from `settings.connecteam_webhook_secret`; missing secret raises config error; no secret/signature values in logs at any level — debug logging may state only *that* verification failed and which header was absent.

5. **Errors** — in the intake command module (Shopify precedent keeps webhook errors local to the command; follow `05_errors.md` + `errors/base.DomainError`): `ConnecteamWebhookAuthError(DomainError, http_status=401)`, `InvalidConnecteamWebhookRequest(DomainError, http_status=400)`, `UnsupportedConnecteamWebhookPayload(DomainError, http_status=422)`, `ConnecteamWebhookUnavailable(DomainError, http_status=503)` (integration disabled, or Redis+Postgres both unable to accept durably). Note: use `ValidationError` from `errors.validation` where field validation applies (not "ValidationFailed").

6. **Task type + routing** — modify `backend/app/beyo_manager/domain/execution/enums.py` (add `CONNECTEAM_PROCESS_TIME_ACTIVITY`) and `services/infra/execution/task_router.py` (`QUEUE_MAP[TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY] = "queue:connecteam"`). No `HANDLER_TIMEOUT_SECONDS` entry needed (default 300s is ample for a no-op phase).

7. **Intake command** — new `backend/app/beyo_manager/services/commands/connecteam/enqueue_connecteam_time_activity_webhook.py` (+ `__init__.py`), shaped on `enqueue_or_record_shopify_webhook`:
   1. Parse incoming `{raw_body, headers}` request model.
   2. If `not settings.connecteam_webhook_enabled` → raise `ConnecteamWebhookUnavailable` (controlled response; never silent accept).
   3. `verify_connecteam_webhook(...)` → 401 on failure (before any JSON parsing).
   4. `json.loads` raw body → `InvalidConnecteamWebhookRequest` (400) on malformed JSON; validate provider DTO; normalize → `ConnecteamTimeActivityEvent`; missing identity fields → 422.
   5. Policy filter: unsupported `event_type` → outcome `unsupported_event_type`, log `connecteam_webhook_rejected`, return success-shaped result **without enqueueing** (Connecteam should not retry these); `activity_type == manual_break` → outcome `ignored_activity_type`, acknowledged, not enqueued.
   6. Dedup: `SET NX EX 900` on the dedup key (provisional TTL). Key exists → outcome `duplicate`, log `connecteam_webhook_duplicate`, return success (idempotent acknowledgement — never an error).
   7. Enqueue: inside `maybe_begin(ctx.session)`, `create_instant_task(session, TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY, payload=asdict(event), max_try=5)`.
   8. After commit: `EXPIRE` dedup key to `settings.connecteam_webhook_dedup_ttl_seconds`; log `connecteam_webhook_enqueued`. On task-creation failure: best-effort `DEL` dedup key, re-raise. The provisional-TTL pattern bounds the worst-case lost-event window (crash between SETNX and DEL) to 15 minutes, within which Connecteam's own 3 retries would be deduped — documented as an accepted risk below.
   9. Redis-failure policy: if the dedup `SET` itself errors (Redis down), **still enqueue** (Postgres is the durability substrate) and log a warning that dedup is degraded — duplicates are tolerable because handlers are idempotent no-ops; 503 is returned only when the event cannot be durably accepted at all (Postgres write fails).
   Result dataclass: `ConnecteamWebhookAcceptance(event_key, outcome)` with outcome from `ConnecteamIntakeOutcomeEnum`.

8. **Router** — new `backend/app/beyo_manager/routers/api_v1/connecteam_webhooks.py`: thin, mirrors `shopify_webhooks.py` — `raw_body = await request.body()`, pass `raw_body` + `dict(request.headers)` into `run_service(enqueue_connecteam_time_activity_webhook, ServiceContext(identity={}, incoming_data=..., session=session))`, `build_ok`/`build_err`. Register in `routers/api_v1/__init__.py`: `app.include_router(connecteam_webhooks.router, prefix="/api/v1/connecteam", tags=["connecteam-webhooks"])`. No JWT dependency (public, signature-authenticated), matching the Shopify webhook route.

9. **Resolver query** — new `backend/app/beyo_manager/services/queries/users/resolve_connecteam_worker.py`: `resolve_connecteam_worker(session, *, connecteam_user_id: str, company_id: str | None) -> ResolvedConnecteamWorker | None`. Normalizes the external ID to `str`; selects `UserWorkProfile` where `connecteam_user_id == value`; 0 rows → `None` (explicit unmapped); >1 rows (possible across workspaces) → raise `AmbiguousConnecteamMappingError` (non-retryable). Returns frozen dataclass `ResolvedConnecteamWorker(work_profile_id, user_id, workspace_id)`. No fallback matching of any kind. `company_id` is accepted and logged now, reserved for future scoping.

10. **Task handler + dispatcher + placeholder handlers** — new package `backend/app/beyo_manager/services/tasks/connecteam/`:
    - `handle_connecteam_process_time_activity.py`: worker entrypoint `(raw_payload: dict, task_client_id: str)`. Deserializes `ConnecteamTimeActivityEvent`; defense-in-depth re-check of `activity_type` (manual_break → log + return normally); resolves via step 9; dispatch via module-level map `{ConnecteamEventTypeEnum.CLOCK_IN: handle_clock_in, ...}` (no conditional block; unknown types log `connecteam_webhook_rejected` and return).
    - **Retry classification is expressed through the existing worker contract:** non-retryable outcomes (`worker_not_mapped`, `ambiguous_mapping`, `ignored_activity_type`, unknown type) **return normally** after logging — the task completes and does not retry (an unmapped worker is not transient; requeue-after-mapping is served by the CLI in step 13). Retryable failures (DB/Redis/dependency errors) **raise** — `worker_base` schedules the retry and, after `max_try=5`, marks `FAIL` (dead-letter).
    - `handlers/handle_clock_in.py`, `handlers/handle_clock_out.py`, `handlers/handle_auto_clock_out.py`: each `async def execute(*, worker: ResolvedConnecteamWorker, event: ConnecteamTimeActivityEvent) -> ConnecteamHandlerResult` — logs `connecteam_event_noop_handled` with the full structured field set, returns a no-op result, performs **zero** writes. These signatures are the stable phase-2 extension points.

11. **Worker process** — new `backend/app/beyo_manager/workers/connecteam_worker.py`, byte-for-byte pattern of `shopify_worker.py`: `configure_logging()`, `init_db()`, `run_worker("queue:connecteam", {TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY: handle_connecteam_process_time_activity})`. Add Procfile entry `connecteam-worker: python beyo_manager/workers/connecteam_worker.py`. Bounded concurrency, clean shutdown, no-tight-loop, and abandoned-processing recovery are inherited from `worker_base` + `task_router` (relational reads confirm: blpop timeout 2s, SIGTERM rescue, stale sweeps).

12. **Model + migration** — modify `models/tables/users/user_work_profile.py`: add `connecteam_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)`; add to `__table_args__`: `Index("ix_user_work_profiles_connecteam_user_id", "connecteam_user_id")` and `UniqueConstraint("workspace_id", "connecteam_user_id", name="uq_user_work_profiles_workspace_connecteam_user")`. Scope rationale: `UserWorkProfile` is already workspace-scoped (`workspace_id` FK, existing `(user_id, workspace_id)` unique); `(workspace_id, connecteam_user_id)` is the narrowest constraint the current ownership model supports without inventing an integration-config table; Postgres treats NULLs as distinct, so unmapped profiles are unaffected; cross-workspace ambiguity is handled at the resolver (step 9). Two Alembic migrations chained from current head `b4074f2e26c4` (verify head again with `alembic heads` before generating):
    - (a) add `connecteam_process_time_activity` to the task-type enum, following `e1b2c3d4f5a6_add_email_sync_targeted_task_type.py`'s pattern (enum-value additions are irreversible in PG — document downgrade as no-op comment, matching that precedent).
    - (b) add column + index + unique constraint; downgrade drops constraint, index, column in that order. No data population.

13. **CLI inspection** — extend `backend/app/beyo_manager/cli/main.py` with three subcommands operating on `ExecutionTask` rows where `task_type == CONNECTEAM_PROCESS_TIME_ACTIVITY`: `connecteam-dead-letter-list` (state `FAIL`, offset pagination, prints task id, `last_error` truncated, created_at, event_key from payload — never full payload without an explicit `--raw` flag), `connecteam-dead-letter-requeue <task_client_id>` (FAIL → OPEN, reset `try_count=0`, task-router picks it up; this is also the "requeue after a mapping is added" path for unmapped events that were dead-lettered manually), `connecteam-dead-letter-purge <task_client_id>` (explicit deliberate delete/mark, with confirmation flag).

14. **Logging** — all lifecycle points use `core/logging/config.log_event` with intention-§19 event names (`connecteam_webhook_received`, `_rejected`, `_duplicate`, `_enqueued`, `connecteam_worker_resolved`, `connecteam_worker_not_mapped`, `connecteam_event_noop_handled`, `connecteam_webhook_completed`; `_retry_scheduled`/`_dead_lettered`/`_claimed` are emitted by the shared worker/router logs and therefore not duplicated) and fields (`provider, event_key, request_id, event_type, activity_type, connecteam_user_id, time_clock_id, time_activity_id, workspace_id, internal_user_id, attempt, processing_status, duration_ms` as applicable). Raw payload logging only behind `connecteam_integration_debug_logs`. Remove/disable the step-1 header-name discovery logging once the contract is confirmed.

15. **Tests** — new `backend/tests/connecteam/` (pytest, following `backend/tests/tasks/` fixtures/conventions):
    - `test_webhook_verifier.py`: valid accepted; invalid rejected; missing header rejected; one-byte body change invalidates; comparison via `hmac.compare_digest` (assert usage); unrelated headers cannot bypass.
    - `test_webhook_router.py`: valid → 200 + task created; malformed JSON → 400; bad/missing auth → 401 and nothing enqueued; duplicate delivery → 200 + single task; disabled integration → controlled 503; Postgres-unavailable intake → 503; unsupported event type and manual_break → acknowledged, no task.
    - `test_payload_normalization.py`: all three fixture events normalize; additive unknown fields tolerated; missing `user_id`/`event_type` → 422 path; manual_break classified.
    - `test_deduplication.py`: same request_id enqueues once; concurrent duplicates (two coroutines) enqueue once; fallback key deterministic across calls; two legitimate sequential clock_in/clock_out events produce distinct keys; TTL set on key; Redis-down dedup degrades to accept-with-warning.
    - `test_task_lifecycle.py`: handler exception → `RETRY_SCHEDULED` with `next_retry_at`; exhausted `max_try=5` → `FAIL`; CLI requeue FAIL → OPEN; (claim/ack/stale recovery are shared `worker_base` behavior — cover only the connecteam-specific max_try wiring).
    - `test_resolver.py`: exact ID resolves expected profile; unknown → `None`/`worker_not_mapped` outcome and task completes without retry; duplicate mapping across workspaces → ambiguous error, non-retryable; same-workspace duplicate prevented by constraint; no fallback resolution.
    - `test_dispatcher.py`: each event type reaches its handler (spy); unknown type reaches none; handlers write no rows (assert `user_shift_state_record` count unchanged); no-op completes task.
    - `test_migration.py`: upgraded schema stores/retrieves the ID; multiple NULLs valid; `(workspace_id, connecteam_user_id)` uniqueness enforced; existing rows valid.

16. **ngrok validation doc** — new `backend/docs/architecture/under_construction/implementation/VALIDATION_connecteam_webhook_ngrok.md` with the intention-§23 manual flow adapted to this design: start API (8000) → ngrok → confirm Connecteam webhook URL → start `task-router` + `connecteam-worker` (Procfile names) → clock in/out/auto-clock-out → verify `connecteam_webhook_enqueued`, `connecteam_worker_resolved` (after setting a test profile's `connecteam_user_id` manually in the DB), `connecteam_event_noop_handled` logs → verify zero `user_shift_state_record` changes (`SELECT count(*)` before/after). Note that the ngrok URL lives only in the Connecteam console, never in code.

## Risks and mitigations

- Risk: The recommended queue substrate contradicts the intention's "no PostgreSQL persistence" exclusion.
  Mitigation: Surfaced as blocking Clarification 1 with an explicit alternative path; no webhook-specific table is created either way; the payload lives only in the execution infrastructure rows that every async job in this backend already uses.
- Risk: Connecteam's real signature scheme differs from any assumption (or is absent).
  Mitigation: Step 1 discovery gate; verifier is a single isolated adapter; endpoint stays dev-only until the contract is recorded in the Review log; static-secret fallback path defined.
- Risk: Crash between dedup `SETNX` and task commit loses an event for the dedup TTL window.
  Mitigation: Provisional 900s TTL (extended to 7 days only after successful commit) + best-effort `DEL` on failure; Connecteam retries within that window are the only affected deliveries; phase-1 handlers are no-ops so the blast radius is zero.
- Risk: Real payload shape diverges from the DTOs (e.g., `activity_type` nested differently), silently misclassifying manual_break as shift.
  Mitigation: DTOs finalized against real captured fixtures (step 1), not documentation guesses; unknown `activity_type` maps to `UNKNOWN` which is **not** dispatched; defense-in-depth re-check in the task handler.
- Risk: Global unique lookup on `connecteam_user_id` across workspaces becomes ambiguous if a second workspace maps the same Connecteam company.
  Mitigation: Resolver raises a non-retryable ambiguity error (never guesses); `company_id` is already carried in the envelope so future scoping is additive, not a rewrite.
- Risk: Adding a TaskType enum value without its migration breaks task creation at runtime.
  Mitigation: Step 12(a) follows the existing enum-migration precedent; validation plan runs `alembic upgrade head` before tests.
- Risk: Secret/signature leakage via debug logging during discovery.
  Mitigation: Discovery logs header names only; explicit acceptance criterion 11; discovery branch removed in step 14.

## Validation plan

- `cd backend/app && .venv/bin/alembic heads`: exactly one head (`b4074f2e26c4` before work; the new step-12(b) revision after).
- `.venv/bin/alembic upgrade head` then `downgrade -1` then `upgrade head`: column/index/constraint apply and revert cleanly; existing `user_work_profiles` rows untouched.
- `.venv/bin/python -m pytest ../tests/connecteam -q`: all step-15 suites pass.
- `.venv/bin/ruff check beyo_manager`: no new violations.
- App startup with `CONNECTEAM_WEBHOOK_ENABLED=true` and unset secret: fails with the explicit configuration error.
- `curl -X POST localhost:8000/api/v1/connecteam/webhooks/time-activity -d '{}'` without signature: 401, no task row created.
- Manual ngrok flow per `VALIDATION_connecteam_webhook_ngrok.md`: all three placeholder handlers observed in logs; `SELECT count(*) FROM user_shift_state_records` unchanged.
- `grep -rn "CONNECTEAM_WEBHOOK_SECRET\|signature" backend/app/beyo_manager --include='*.py' | grep -i log`: no code path logs the secret or signature values.

## Review log

- `2026-07-20` `claude (plan author)`: Initial draft. Substrate decision (Clarification 1), signature contract (Clarification 2), and retry-schedule deviation (Clarification 3) await owner sign-off. Signature-contract discovery findings to be appended here by the implementer after step 1.
- `2026-07-20` `owner (David)`: Clarification 1 resolved — reuse the existing ExecutionTask webhook pipeline (Shopify precedent); confirmed Connecteam must not disrupt Shopify webhooks (satisfied: all shared-file changes are additive; separate queue `queue:connecteam` and dedicated worker).
- `2026-07-20` `owner (David)`: Clarification 3 resolved — no changes to existing architecture for this integration; retries adapt to what the platform currently provides (`worker_base` backoff, `max_try=5`).
- `2026-07-20` `owner (David)`: Clarification 2 resolved — the discovery approach is the accepted resolution: check the logs from real ngrok deliveries to understand and analyze the payload/signature shape; no assumed header or algorithm.
- `2026-07-20` `claude (plan author)`: All owner decisions recorded; status moved to `approved`. Pending during implementation: step-1 signature-contract discovery findings must be appended here before the endpoint runs outside development.
- `2026-07-20` `claude (plan author)`: **Signature-contract discovery COMPLETE** (real deliveries observed via ngrok inspector, source IP 20.82.69.91, User-Agent `connecteam`). Verified contract: **static shared secret, no HMAC** — header `X-Webhook-Secret` carries the literal webhook secret (64-char hex); value confirmed equal to `CONNECTEAM_WEBHOOK_SECRET` in the environment. No signature/timestamp headers present (only `Baggage` with request_id/user_id/company_data/actor_id/platform, and `Traceparent`). Verification = constant-time comparison of the header against the configured secret — codex's `webhook_verifier.py` already implements exactly this; no change needed. Observed payload (flat envelope): `requestId` (uuid str), `company` (str), `activityType` ("shift"), `eventType` ("clock_in"/"clock_out"), `eventTimestamp` (int epoch) **plus provider typo duplicate `evnetTimestamp`**, `userId` (int), `timeClockId` (int), `timeActivity` (nested dict with `userId`, `timeClock.id`, `createdAt`, `jobId`, `shiftAttachments`, `isAutoClockOut`), `webhookVersion` (int 1) — tolerant parsing justified. End-to-end verified live: real clock_in delivery → verified → normalized (`event_key connecteam:{requestId}`) → ExecutionTask enqueued (`max_try=5`) → Connecteam redelivery deduplicated → 200.
- `2026-07-20` `claude (reviewer)`: **Defect found and fixed** during live validation: all Connecteam `log_event(...)` calls passed `event_type=` as a kwarg, colliding with `log_event`'s first positional parameter of the same name → `TypeError` after COMMIT → 500 to Connecteam (and would have failed every worker-side task through all 5 retries, and turned unsupported-event acknowledgements into 500s causing Connecteam retries). Fixed by renaming the kwarg to `connecteam_event_type` in `enqueue_connecteam_time_activity_webhook.py` (3 sites), `handle_connecteam_process_time_activity.py`, and all three placeholder handlers; shared `core/logging/config.py` untouched per owner rule. Verified: accept → `accepted`, redelivery → `duplicate`, both through `run_service`. Codex to add a regression test for the enqueued/completed/noop log paths.
- `2026-07-20` `codex`: Discovery through the existing ngrok inspector observed eight POST deliveries carrying the header name `X-Webhook-Secret`; all observed values were identical (comparison performed without printing values), and `Content-Length` was non-zero (623 or 810 bytes). The deliveries were answered `502` by the tunnel target, so they do not provide a trustworthy parsed event fixture. No HMAC digest, encoding, prefix, or timestamp contract was observed; the current evidence supports only a static shared-secret header comparison. The verifier remains isolated behind this adapter and must stay development-only until a successful real delivery is captured and the redacted payload nesting is confirmed.
- `2026-07-20` `codex`: Implemented the transport/task-pipeline foundation provisionally (settings, adapter verifier, tolerant normalizer, dedup/intake command, resolver, no-op handlers, worker, router, migrations, CLI, fixture/test scaffolding). Scope remains in `debugging`; no implementation-complete/archive transition is claimed until a successful real delivery supplies the payload nesting and confirms the provisional fixture.

- `2026-07-20` `owner (David)`: **Worker consolidation decision** — no dedicated Connecteam worker process; delegate processing to an already-running worker. Applied by claude: `TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY` now routes to `queue:tasks` and `handle_connecteam_process_time_activity` is registered in the shared `tasks_worker` `HANDLER_MAP` (alongside `AUTO_CLOCK_OUT_OPEN_SHIFTS`); `workers/connecteam_worker.py` and its Procfile entry deleted; `queue:connecteam` no longer exists; ngrok validation doc updated. This supersedes plan step 11 and aligns with intention §13 ("prefer the existing worker framework unless isolation provides a concrete operational advantage"). Codex: target `tasks_worker` in queue-lifecycle tests, and do not reintroduce a dedicated worker.

## Lifecycle transition

- Current state: `approved`
- Next state: `debugging` (implementation by codex; endpoint stays development-only until the verified signature contract is recorded in the Review log)
- Transition owner: `codex`
