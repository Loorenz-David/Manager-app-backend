# PLAN_shopify_webhook_intake_execution_20260708

## Metadata

- Plan ID: `PLAN_shopify_webhook_intake_execution_20260708`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T20:00:00Z`
- Last updated at (UTC): `2026-07-08T09:08:39Z`
- Related issue/ticket: `Shopify integration webhook intake and execution enqueue boundary`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` — phase 1 foundation (`ShopifyWebhookIntake`, `ShopifyShopIntegration`, `ShopifyIntegrationEvent` models, `domain/shopify/webhook_registry.py`) is used directly by this plan.
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md` — phase 2 OAuth linking (`routers/api_v1/shopify.py`, `services/infra/shopify/hmac_verifier.py`) establishes the router/HMAC pattern this plan follows for a second, distinct HMAC scheme.
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md` — phase 3 webhook subscription sync (`domain/shopify/webhook_registry.py` usage, `SHOPIFY_WEBHOOK_CALLBACK_PATH`) fixes the exact callback URL this plan's route must serve (see "Phase 3 implementation dependencies verified").
- No blockers remain — see "Resolved decisions."

## Goal and intent

- Goal: Draft the Shopify inbound webhook intake route — HMAC verification on the raw request body, topic/header validation against the phase-1 registry, shop integration resolution, durable intake persistence with dedupe, and a single event-only "enqueue-pending" boundary — that responds to Shopify quickly and defers all real processing to a later phase.
- Business/user intent: Let Shopify actually deliver webhooks to this backend once a shop's subscriptions are synced (phase 3), durably record every supported delivery exactly once, and leave a clear, safe boundary for phase 5 to connect to real background processing — without building any execution-layer code in this phase.
- Non-goals:
  - Actual webhook business processing (parsing/acting on order or product payloads).
  - Product/order import or update behavior.
  - Dedicated Shopify worker implementation (master phase 5).
  - Redis queue mapping (master phase 5).
  - Execution-layer task payloads/types (master phase 5) — see "Phase 4 design decision: Option A" below.
  - Real queue enqueue calls of any kind — no task type exists yet to enqueue.
  - Admin routes (master phase 6).
  - Frontend UI.
  - Historical product/order imports.
  - Disconnect flow (uses phase 3's `remove_shopify_webhooks_for_shop`, but the route/command that triggers it is master phase 6's concern).
  - Creation of remaining child implementation plans (phases 5-7 of the master plan).

## Phase 4 design decision: Option A (event-only enqueue boundary until phase 5)

Phase 4 is named "webhook intake and execution enqueue" in the master plan, but master phase 5 owns the dedicated Shopify worker, task types, payloads, and queue routing. Two approaches were considered:

- **Option A — event-only enqueue boundary until phase 5** (chosen): this phase verifies the webhook, persists intake/dedupe, records a single outcome event noting the webhook is durably recorded and pending processing, and returns `200` quickly. It creates no execution task types and makes no Redis enqueue call. Phase 5 later connects this boundary to a real `SHOPIFY_PROCESS_WEBHOOK` enqueue.
- **Option B — minimal execution task type only**: this phase would additionally create the minimum task type/payload/enqueue path for `SHOPIFY_PROCESS_WEBHOOK`, while phase 5 still owns the worker/handlers. This moves partial execution-layer ownership into phase 4 and would need its own master-plan deviation sign-off.

**Chosen: Option A.** Reasons: it keeps this phase narrow and safe; it avoids introducing execution payloads/task types before the dedicated Shopify worker plan exists (mirroring phase 3's already-approved deviation of leaving all execution-layer concerns to phase 5); it still fully verifies and tests Shopify's fast-response contract and durable intake/dedupe, which is the actual hard problem in this phase; and it lets phase 5 own the complete execution-layer integration coherently in one place instead of split across two plans. Consequences, stated explicitly per the requested format:

- No execution task types are created in this phase.
- No Redis queue enqueue occurs in this phase.
- This phase records a single enqueue-pending/event-only outcome (`ShopifyIntegrationEvent`, `event_type=WEBHOOK_RECEIVED`) after intake persistence, not a real enqueue call.
- Master phase 5 will connect this boundary to a real `SHOPIFY_PROCESS_WEBHOOK` enqueue — most likely by having phase 5's worker/task wiring poll or subscribe to `shopify_webhook_intakes` rows with `status=RECEIVED`, or by phase 5 adding a call from this phase's command into a new enqueue helper once task types exist. This plan does not decide phase 5's exact wiring mechanism — that is phase 5's design question, flagged here only so phase 5's plan does not have to rediscover it.

## Scope

- In scope:
  - One generic Shopify webhook HTTP route: `POST /api/v1/shopify/webhooks` (see "Phase 3 implementation dependencies verified" for why this exact, non-`/integrations/`-prefixed path is fixed, not a choice).
  - Raw request body extraction (bytes, not re-serialized JSON) for HMAC verification.
  - A new Shopify webhook HMAC verification function using the raw body and `X-Shopify-Hmac-Sha256`, distinct from phase 2's existing OAuth-callback HMAC verifier (see "Phase 3 implementation dependencies verified" for why the two cannot be the same function).
  - Shopify topic/header validation (`X-Shopify-Topic`, `X-Shopify-Shop-Domain`, `X-Shopify-Webhook-Id`).
  - Supported-topic validation through the phase-1 webhook registry (`get_webhook_definition`).
  - Shop integration resolution by normalized Shopify shop domain (`X-Shopify-Shop-Domain` header, normalized via `domain/shopify/shop_domains.normalize_shop_domain`).
  - Webhook intake persistence into `shopify_webhook_intakes` (phase-1 model, unused until now).
  - Dedupe by a durable key (`shop_integration_id:topic:webhook_id`, matching `shopify_webhook_intakes.dedupe_key`'s unique constraint).
  - Duplicate delivery (same `dedupe_key`) returns `200` without creating a second intake row and without a second event.
  - Unsupported-topic behavior after HMAC verification: HMAC is always checked first; an unsupported topic is recorded as an intake row with `status=IGNORED` (the phase-1 enum member exists specifically for this) and `200` is returned — Shopify must never be told to retry a topic it will never become supported.
  - Missing/blank `X-Shopify-Webhook-Id` behavior: treated as an invalid delivery, returns `400`, no intake row, no event (see "Resolved decisions" item 9).
  - Known-but-inactive shop integration behavior: `disabled`/`uninstalled` integrations still get a persisted, `IGNORED`/non-retryable intake row plus a `WARNING` event with `reason="inactive_shop_integration"` (see "Resolved decisions" item 7) — never skipped, never `RECEIVED`.
  - `ShopifyIntegrationEvent` recording for the received/enqueue-pending outcome (one event per unique webhook, not per delivery attempt — see "Resolved decisions" item 3), the unsupported-topic/ignored outcome, and the inactive-shop-integration/ignored outcome.
  - A single command, `enqueue_or_record_shopify_webhook`, that owns validated/parsed webhook input, shop integration resolution, intake persistence, dedupe, the ignored behaviors above, and the event-only boundary — this is the single call site the route invokes (see "Resolved decisions" item 8 — no split into separate intake/boundary commands in this phase).
  - Fast Shopify response behavior: verify, resolve, persist, return — no Shopify API calls, no GraphQL calls, no synchronous processing in the request path.
  - No raw payload logging (the raw body is persisted to `shopify_webhook_intakes.raw_payload` as JSONB, never written to a log line).
  - Tests: valid webhook (creates intake, returns 200), invalid HMAC (rejected before any other trust, 400, no DB writes), missing/blank webhook id (400, no DB writes), unsupported topic (ignored intake + 200), unknown shop domain (200, no DB writes), known-but-inactive shop integration (ignored/non-retryable intake + WARNING event + 200), duplicate delivery (dedupe, no second intake/event, 200), and enqueue-boundary behavior (event recorded, no real enqueue/task-type reference anywhere).
- Out of scope:
  - Actual webhook business processing.
  - Product/order import/update behavior.
  - Dedicated Shopify worker implementation.
  - Redis queue mapping.
  - Execution-layer task payloads/types (deferred entirely to master phase 5, per the Option A decision above).
  - Real queue enqueue calls.
  - Admin routes.
  - Frontend UI.
  - Historical product/order imports.
  - Disconnect flow route.
  - Remaining child implementation plans (phases 5-7).
- Assumptions:
  - Shopify signs webhook deliveries with HMAC-SHA256 over the raw request body, base64-encoded, in the `X-Shopify-Hmac-Sha256` header — a different scheme from the OAuth callback's query-string HMAC (phase 2), which is hex-encoded over sorted `key=value` pairs. Both are legitimate, well-documented Shopify mechanisms for different endpoints; they are not interchangeable.
  - Shopify includes `X-Shopify-Topic`, `X-Shopify-Shop-Domain`, and `X-Shopify-Webhook-Id` headers on every webhook delivery; `X-Shopify-Webhook-Id` is stable across Shopify's own retries of the same delivery (this is the basis for the dedupe key, matching the intention plan's "shop integration + topic + Shopify webhook ID").
  - FastAPI's `Request.body()` gives the exact raw bytes Shopify sent, before any framework re-serialization — required for HMAC verification to match Shopify's signature.

## Phase 3 implementation dependencies verified

Phase 3 was reviewed against the archived plan, its implemented summary, and the actual code in the repository on `2026-07-08`. Every item below is a **confirmed fact**, not an assumption.

- [x] **Actual Shopify router path and mount path** — `app/beyo_manager/routers/api_v1/shopify.py` defines `router = APIRouter()` with `POST /install-url` and `GET /oauth/callback`, mounted in `routers/api_v1/__init__.py` via `app.include_router(shopify.router, prefix="/api/v1/integrations/shopify", tags=["shopify"])`. **This phase's webhook route must not be added to this same router/prefix** — see the callback-path finding below.
- [x] **Actual HMAC verifier module and function name** — `app/beyo_manager/services/infra/shopify/hmac_verifier.py`, `is_valid_shopify_oauth_callback_hmac(raw_query_string: str) -> bool`. This function verifies the **OAuth callback query string** (hex HMAC-SHA256 over sorted `key=value` pairs, keyed by `settings.shopify_client_secret`). It cannot be reused for webhook intake HMAC verification, which Shopify signs differently (base64 HMAC-SHA256 over the raw JSON body). This phase adds a new function in the same module (see Implementation plan step 2) rather than overloading the existing one.
- [x] **Actual `ShopifyWebhookIntake` model class/path/fields** — `app/beyo_manager/models/tables/shopify/shopify_webhook_intake.py`, class `ShopifyWebhookIntake`, `CLIENT_ID_PREFIX = "shpwhi"`, table `shopify_webhook_intakes`. Fields: `client_id`, `workspace_id` (FK `workspaces.client_id`, NOT NULL), `shop_integration_id` (FK `shopify_shop_integrations.client_id`, NOT NULL, `ondelete="RESTRICT"`), `shop_domain` (String(255)), `topic` (String(128)), `webhook_id` (String(255), nullable), `dedupe_key` (String(255), unique constraint `uq_shopify_webhook_intakes_dedupe_key`), `raw_payload` (JSONB, nullable), `status` (`ShopifyWebhookIntakeStatusEnum`: `RECEIVED`/`PROCESSING`/`PROCESSED`/`FAILED`/`IGNORED`, default `RECEIVED`), `attempts` (Integer, default 0), `retryable` (Boolean, default True), `received_at` (DateTime tz-aware, indexed), `processing_started_at`/`processed_at` (nullable), `last_error` (Text, nullable), `created_at`/`updated_at`. **Critical constraint**: `shop_integration_id` is `NOT NULL` — an intake row cannot be created without a matching `ShopifyShopIntegration.client_id` (see "Resolved decisions" item 2 for the consequence).
- [x] **Actual `ShopifyShopIntegration` model class/path/fields** — `app/beyo_manager/models/tables/shopify/shopify_shop_integration.py`, class `ShopifyShopIntegration`, `CLIENT_ID_PREFIX = "shpint"`, table `shopify_shop_integrations`. Relevant fields for this phase: `client_id`, `workspace_id`, `shop_domain` (String(255), not unique alone — uniqueness is enforced only among active-like rows via the phase-1 partial unique index), `status` (`ShopifyIntegrationStatusEnum`), `is_deleted` (Boolean). Lookup by `shop_domain` can return zero, one, or (across workspaces, if all are inactive) more than one row — this phase must pick a single, well-defined resolution rule (see "Resolved decisions" item 1).
- [x] **Actual `ShopifyIntegrationEvent` model class/path/fields** — `app/beyo_manager/models/tables/shopify/shopify_integration_event.py`, class `ShopifyIntegrationEvent`, `CLIENT_ID_PREFIX = "shpevt"`, table `shopify_integration_events`. Fields: `client_id`, `workspace_id`, `shop_integration_id` (FK, NOT NULL — same constraint as intake), `event_type` (`ShopifyIntegrationEventTypeEnum`: `INSTALL`, `REAUTHORIZE`, `WEBHOOK_SYNC`, `WEBHOOK_RECEIVED`, `WEBHOOK_PROCESSED`, `HEALTH_CHECK`, `ERROR` — `WEBHOOK_RECEIVED` is the exact member this phase needs, already present since phase 1; no enum extension required), `severity` (`ShopifyIntegrationEventSeverityEnum`: `INFO`/`WARNING`/`ERROR`), `message` (Text), `metadata_json` (JSONB, mapped via the `metadata_json` Python attribute — the column is named `metadata` but `metadata` is reserved by SQLAlchemy's declarative `Base`, so the constructor kwarg is `metadata_json=`, never `metadata=`), `created_by_id` (nullable FK), `created_at`.
- [x] **Actual webhook registry API** — `app/beyo_manager/domain/shopify/webhook_registry.py`: `SHOPIFY_WEBHOOK_REGISTRY: tuple[ShopifyWebhookDefinition, ...]` (8 topics: `app/uninstalled`, `orders/create`, `orders/updated`, `orders/paid`, `orders/cancelled`, `products/create`, `products/update`, `products/delete`), `SHOPIFY_WEBHOOK_CALLBACK_PATH = "/api/v1/shopify/webhooks"` (an **absolute path constant**, not relative to any router prefix), `get_webhook_definition(topic: str) -> ShopifyWebhookDefinition | None` (returns `None`, not an exception, for an unsupported topic — this phase's "unsupported topic" branch is exactly this `None` case).
- [x] **Actual webhook subscription sync command names/paths** — `services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py` and `remove_shopify_webhooks_for_shop.py`, confirmed implemented, archived, and tested (`14 passed` unit, `7 passed` integration per the phase-3 summary). Not called by this phase, but their behavior fixes a load-bearing fact below.
- [x] **Actual GraphQL/webhook subscription infra module names/paths** — `services/infra/shopify/graphql_client.py` (`execute_shopify_graphql`, `build_shopify_admin_graphql_endpoint`, `raise_for_graphql_user_errors`) and `services/infra/shopify/webhook_subscription_client.py` (`list_remote_webhook_subscriptions`, `create_remote_webhook_subscription`, `delete_remote_webhook_subscription`, `RemoteWebhookSubscription`). Not called by this phase (no GraphQL calls in the intake path), listed for completeness and to avoid name collisions in `services/infra/shopify/`.
- [x] **Actual event helper names/paths** — `services/commands/shopify/_events.py`: `create_shopify_integration_event(session, *, workspace_id, shop_integration_id, event_type, severity, message, metadata_json, created_by_id)`. This phase's `enqueue_or_record_shopify_webhook` command must call this existing helper directly for its outcome event, not write a new one, continuing the pattern from phases 2 and 3.
- [x] **Finding: the webhook callback URL is already fixed, not a phase-4 design choice.** Phase 3's `sync_shopify_webhook_subscriptions_for_shop` builds the callback URL it registers with Shopify as `f"{settings.shopify_webhook_base_url.rstrip('/')}{SHOPIFY_WEBHOOK_CALLBACK_PATH}"`, and phase 3's own integration tests assert this resolves to exactly `.../api/v1/shopify/webhooks` (e.g. `https://backend.example.com/api/v1/shopify/webhooks`). Because phase 3 is already implemented, archived, and its tests already hardcode this path, **this phase's webhook route must be reachable at exactly `POST /api/v1/shopify/webhooks`** — not nested under the OAuth router's `/api/v1/integrations/shopify` prefix (that would produce `/api/v1/integrations/shopify/api/v1/shopify/webhooks` if the two paths were naively combined, or a wrong path entirely if only a suffix were mounted there). This closes the path-mismatch question flagged as unresolved since the phase 1 and phase 2 reviews — the master/intention plan's example prefix (`/api/v1/integrations/shopify/webhooks`) is superseded by what phase 1 and phase 3 actually built and already tested against.
- [x] **Actual test results from phase 3** — per the implemented summary: new phase-3 unit tests `14 passed`, new integration tests `7 passed`, combined Shopify phase 1-3 regression suite `60 passed`. Reviewed test content directly (`test_graphql_client.py`, `test_webhook_subscription_client.py`, `test_webhook_sync_boundary.py`, `test_shopify_webhook_subscription_sync_integration.py`): retryable/non-retryable classification, no-token-in-logs, no-auto-delete-on-missing-scope (including the case where an existing remote subscription is left untouched), backend-owned-callback-URL removal gating (including a "foreign callback URL" subscription correctly ignored), idempotent sync and idempotent remove, and a direct source-inspection test confirming the phase-2 event-only boundary (`enqueue_shopify_webhook_sync_after_install.py`, `_webhook_sync.py`, `handle_shopify_oauth_callback.py`) contains no reference to the phase-3 sync/remove commands.
- [x] **Actual phase 3 summary path** — `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_webhook_registry_sync_20260708.md` (confirmed exists and reviewed).
- [x] **Actual archived phase 3 plan path** — `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md` (confirmed exists, `Status: archived`, reviewed as the authoritative record).
- [x] **Other deviations found during phase-3 review, carried into this plan**: `execute_shopify_graphql` decrypts the access token *inside* the infra client from an `access_token_encrypted` parameter, rather than the caller decrypting and passing plaintext — a stronger boundary than originally planned (the plaintext token never exists in command-layer code at all). This phase should follow the same pattern for consistency, though it decrypts nothing itself (no Shopify API calls). `remove_shopify_webhooks_for_shop.py` imports a "private" `_SYNCABLE_INTEGRATION_STATUSES` constant directly from `sync_shopify_webhook_subscriptions_for_shop.py` rather than a shared helper module — a minor style inconsistency, not something this phase needs to fix or replicate.

## Resolved decisions

These design questions are resolved for this child plan; only the items in "Phase 4 clarifications required before approval" remain open.

1. **Shop integration resolution rule.** Resolve `X-Shopify-Shop-Domain` (normalized) to a `ShopifyShopIntegration` row using: `is_deleted = false`, ordered by `created_at DESC`, take the first match regardless of `status` (active-like or not). Rationale: webhooks can legitimately arrive for a shop whose integration is `needs_reauth`/`scopes_outdated`/`error` (still a real, addressable integration), and rejecting those would silently drop data the moment reauthorization would have fixed things. A `disabled`/`uninstalled` integration is treated the same way for resolution purposes (a valid FK target exists) — whether to still *accept* delivery for such a shop is answered by clarification item 1 below, not by resolution logic.
2. **Unrecognized shop domain (no matching row at all).** Because `shopify_webhook_intakes.shop_integration_id` and `shopify_integration_events.shop_integration_id` are both `NOT NULL` foreign keys (confirmed above), a webhook for a `shop_domain` with **zero** matching `ShopifyShopIntegration` rows (deleted or otherwise) cannot be durably persisted in the current schema at all. This phase does not add a migration to make the FK nullable. Instead: verify HMAC first (always), then attempt shop resolution; on no match, return `200` immediately (Shopify's own guidance is to always acknowledge webhooks for shops it doesn't recognize to stop retries) and emit only a structured, debug-gated log line (`settings.shopify_integration_debug_logs`) — no DB row is written for this case. This is a hard schema constraint, not a preference, so it is recorded as resolved rather than left open.
3. **One event per unique webhook, not per delivery/retry.** `ShopifyIntegrationEvent` rows are recorded on first receipt of a `dedupe_key` only (`WEBHOOK_RECEIVED`, for both the supported-and-persisted case and the unsupported-topic/ignored case, distinguished by `severity` and `metadata_json`). A duplicate delivery of an already-seen `dedupe_key` writes no new event row — only a debug-gated log line. Rationale: the intention plan explicitly marks the deduplicated-event record as optional ("optionally record a webhook_deduplicated event"), and Shopify's retry behavior can otherwise flood the events table with noise for a single logical webhook.
4. **Dedupe key format.** `dedupe_key = f"{shop_integration_id}:{topic}:{webhook_id}"`, matching the intention plan's "shop integration + topic + Shopify webhook ID" and relying on the existing `uq_shopify_webhook_intakes_dedupe_key` unique constraint (phase 1) as the authoritative dedupe guard — the command performs a pre-check `SELECT` for a fast/clean duplicate response, but treats a unique-constraint `IntegrityError` on insert (a race between two near-simultaneous deliveries) as the same "already exists, return 200" outcome, not a failure.
5. **Webhook HMAC secret.** Use `settings.shopify_webhook_secret` if configured (the phase-1 field reserved for exactly this, unused until now); otherwise fall back to `settings.shopify_client_secret` (Shopify's default behavior for apps that do not configure a distinct webhook signing secret). This mirrors how Shopify itself behaves and requires no new config field.
6. **New HMAC function location.** Add the new webhook HMAC function to the existing `services/infra/shopify/hmac_verifier.py` (its natural home), named distinctly from the OAuth one — e.g. `is_valid_shopify_webhook_hmac(raw_body: bytes, provided_hmac_header: str) -> bool` — rather than a new module, since both are HMAC verification for the same integration and the existing module has no reason not to hold both.
7. **Known-but-inactive shop integration — resolved as persist-and-ignore.** If the resolved `ShopifyShopIntegration.status` is `disabled` or `uninstalled`, the command still creates a `ShopifyWebhookIntake` row (does not skip persistence), but with `status=IGNORED` (not `RECEIVED`) and `retryable=False`. The raw payload is stored in `raw_payload` using the same JSONB convention as any other intake row. A `ShopifyIntegrationEvent` is recorded with `event_type=WEBHOOK_RECEIVED`, `severity=WARNING`, and `metadata_json` including `reason="inactive_shop_integration"`, `shop_domain`, `topic`, `webhook_id`, and `integration_status`. The route returns `200`. No enqueue-pending semantics apply to this row — it is durably recorded but explicitly marked so that phase 5 never treats it as work to process. **Reason**: preserves operational visibility (why is Shopify still sending webhooks for a disconnected shop?) while guaranteeing phase 5 cannot accidentally process webhooks for an explicitly disabled/uninstalled integration.
8. **Command shape — resolved as one command.** `enqueue_or_record_shopify_webhook` is the single command for this phase, owning: validated/parsed webhook input, shop integration resolution, intake persistence, dedupe behavior, the inactive-shop "ignored" behavior (item 7), and the event-only enqueue-pending boundary. No split into separate intake/boundary commands in this phase. **Reason**: the real execution enqueue does not exist until phase 5; splitting now would be premature abstraction around a boundary that doesn't do anything real yet. Phase 5 can refactor or add a second seam when `SHOPIFY_PROCESS_WEBHOOK` task types and queue wiring exist and there is a concrete reason to split.
9. **Missing `X-Shopify-Webhook-Id` — resolved as invalid delivery (400).** HMAC is verified first, always. If `X-Shopify-Webhook-Id` is missing or blank, the command treats this as an invalid webhook delivery: it returns `400`, creates no `ShopifyWebhookIntake` row, and records no `ShopifyIntegrationEvent`. Safe debug/warning-level metadata (shop domain, topic, the fact that the id was missing) may be logged; the raw payload is never logged. **Reason**: the durable dedupe key depends on `shop_integration_id:topic:webhook_id` (item 4) — without a webhook id, the backend cannot safely dedupe Shopify's retries per the approved schema and intention plan, so accepting such a delivery would risk either silent data loss (if treated as a one-off, non-deduped write) or duplicate processing (if retried deliveries can't be recognized as the same event).

## Phase 4 clarifications required before approval

None. All three blockers are resolved — see "Resolved decisions" items 7-9.

## Acceptance criteria

1. `POST /api/v1/shopify/webhooks` is registered as a new, unauthenticated-by-JWT route (no `require_roles`/`get_jwt_claims` dependency), matching the phase-2 OAuth-callback precedent for Shopify-initiated, non-session HTTP calls.
2. The route extracts the raw request body via `await request.body()` (bytes) before any JSON parsing, and passes those exact bytes to HMAC verification — never a re-serialized/re-encoded version of the body.
3. HMAC verification (`is_valid_shopify_webhook_hmac`, using `X-Shopify-Hmac-Sha256` and the resolved webhook secret per "Resolved decisions" item 5) happens before any other header or body value is trusted; an invalid signature is rejected without touching the database.
4. Immediately after HMAC verification, if `X-Shopify-Webhook-Id` is missing or blank, the command returns `400`, creates no `ShopifyWebhookIntake` row, and records no `ShopifyIntegrationEvent` (per "Resolved decisions" item 9) — this check happens before topic or shop-domain resolution.
5. After the webhook-id check, `X-Shopify-Shop-Domain` is normalized via `normalize_shop_domain` and resolved to a `ShopifyShopIntegration` row per "Resolved decisions" item 1; when no row exists at all, the route returns `200` with no DB write, per "Resolved decisions" item 2.
6. When the resolved integration's `status` is `disabled` or `uninstalled`, the command creates a `ShopifyWebhookIntake` row with `status=IGNORED` and `retryable=False` (not skipped, not `RECEIVED`, and independent of whether the topic itself is supported), stores the raw payload normally, and records a `WARNING`-severity `WEBHOOK_RECEIVED` event with `metadata_json["reason"] = "inactive_shop_integration"` plus `shop_domain`/`topic`/`webhook_id`/`integration_status`, per "Resolved decisions" item 7 — this check takes precedence over the topic-support check below.
7. For an active-like shop, the command validates `X-Shopify-Topic` against `get_webhook_definition(topic)`; an unsupported topic still returns `200` but creates an intake row with `status=IGNORED` rather than `RECEIVED`, and records a `WARNING`-severity `WEBHOOK_RECEIVED` event with `metadata_json["reason"] = "unsupported_topic"` (per "Resolved decisions" item 3) — never a retry-inviting non-2xx response.
8. A supported-topic, active-like-shop delivery creates exactly one `ShopifyWebhookIntake` row with `status=RECEIVED`, the raw JSON body in `raw_payload` (JSONB), and `dedupe_key` per "Resolved decisions" item 4.
9. A second delivery with the same `dedupe_key` (whether via pre-check `SELECT` or a caught unique-constraint `IntegrityError`) creates no second intake row, records no second event, and still returns `200`.
10. Exactly one `ShopifyIntegrationEvent` (`event_type=WEBHOOK_RECEIVED`) is recorded per unique `dedupe_key` that reaches persistence (i.e. excluding the missing-webhook-id case, which records none at all) — not per delivery attempt — using `metadata_json` for topic/status/reason detail, via the existing `_events.create_shopify_integration_event` helper.
11. No log statement anywhere in this phase's code contains the raw webhook payload body or the webhook HMAC secret; only safe metadata (shop domain, topic, webhook id, outcome) is logged, gated by `settings.shopify_integration_debug_logs` where appropriate per `17_logging.md`.
12. The route makes no Shopify API call, no GraphQL call, and no Redis/queue call in the request path; the full request/response cycle is verify -> resolve -> persist -> return, with no execution task type or payload created anywhere in this phase.
13. `enqueue_or_record_shopify_webhook` — one single command, per "Resolved decisions" item 8 — is the only call site that writes to `shopify_webhook_intakes` or records the `WEBHOOK_RECEIVED` event for this route; the router itself contains no business logic beyond raw-body/header extraction and response-code shaping (`400` for invalid HMAC or missing webhook id, `200` for every other outcome).
14. This phase adds no execution task types/payloads, no worker code, no Redis queue mapping, no admin routes, and no frontend code.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: Router stays I/O only (raw body extraction, response shaping); all logic lives in the command; domain (`webhook_registry.py`) stays the pure source of supported topics.
- `architecture/05_errors.md`: Domain-safe error subclasses for invalid HMAC, unsupported topic (not actually an error — a 200/ignored outcome), and validation failures (missing headers).
- `architecture/06_commands.md`: Write-operation structure for `enqueue_or_record_shopify_webhook`.
- `architecture/08_domain.md`: Reuse (not reimplement) phase-1's `webhook_registry.get_webhook_definition` and `shop_domains.normalize_shop_domain`.
- `architecture/09_routers.md`: Router boundaries; the webhook route must stay a thin, unauthenticated-by-JWT route that extracts the raw body, calls one command, and returns a fast, always-2xx-for-recognized-shops response.
- `architecture/17_logging.md`: Module logger usage, required context fields (shop domain, topic, webhook id, outcome), forbidden raw payload/secret logging.
- `architecture/18_security.md`: New HMAC verification scheme for webhook intake (distinct from OAuth callback HMAC), raw-body integrity, IDOR prevention (shop resolution never trusts a caller-supplied `shop_integration_id`, only the HMAC-verified `X-Shopify-Shop-Domain`).
- `architecture/19_integrations.md`: "Webhook receipt contract" pattern (verify -> parse -> return 200 immediately -> defer real work) — this phase implements verify/parse/persist/return-200 and explicitly stops short of "defer real work" (that's phase 5, via the event-only boundary).
- `architecture/21_naming_conventions.md`: Route, command, and file naming for this phase.
- `architecture/24_multi_tenancy.md`: Intake rows are workspace-scoped via the resolved shop integration's `workspace_id`; no cross-workspace leakage is possible since resolution is by Shopify-verified shop domain only.
- `architecture/40_identity.md`: Reuses phase-1's `shpwhi`/`shpevt` prefixes; no new prefixes needed.
- `architecture/42_event.md`: Outcome-level `ShopifyIntegrationEvent` recording for received/ignored outcomes, following the phase-1/2/3 established pattern (one event per meaningful outcome, not per low-level step).
- `architecture/15_testing.md`: Test tier placement for HMAC unit tests (mocked/synthetic bodies) and route/command integration tests (real DB, no real Shopify calls).

### Local extensions loaded

- `architecture/40_identity_local.md`: No new prefixes needed in this phase; reuses phase-1's `shpwhi`/`shpevt`.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `09_routers.md`, `19_integrations.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape -> `06_commands.md`
- Reading another router to understand handler wiring -> `09_routers.md`

Permitted for this child:
- `app/beyo_manager/routers/api_v1/shopify.py`, `routers/api_v1/__init__.py` — to confirm the existing router/mount pattern this phase's new route must sit alongside without colliding.
- `app/beyo_manager/services/infra/shopify/hmac_verifier.py` — to add the new webhook-HMAC function next to the existing OAuth one, matching its style (pure function, no side effects, no logging of secrets).
- `app/beyo_manager/models/tables/shopify/shopify_webhook_intake.py`, `shopify_shop_integration.py`, `shopify_integration_event.py` — for exact column names/types this phase reads and writes (already confirmed above; re-read only to double-check nothing changed).
- `app/beyo_manager/domain/shopify/webhook_registry.py`, `shop_domains.py` — for exact `get_webhook_definition`/`normalize_shop_domain` signatures.
- `app/beyo_manager/services/commands/shopify/_events.py` — the existing event-recording helper this phase's command must call.
- `app/beyo_manager/config.py` — to confirm `shopify_webhook_secret`/`shopify_client_secret`/`shopify_integration_debug_logs` are unchanged.
- `app/beyo_manager/routers/api_v1/bootstrap.py` — read only as a relational example of an existing unauthenticated-by-JWT route with custom verification, not copied verbatim.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`: Not selected — Option A keeps all execution-layer/queue/worker concerns in master phase 5, continuing phase 3's approved deviation.
- `28_roles_permissions.md`: No JWT-authenticated route in this phase.
- `07_queries.md`, `07_queries_local.md`: No list/detail query surface; the one lookup (shop integration by domain) is internal to the command.
- `03_models.md`, `30_migrations.md`: No new tables or schema changes — this phase only writes to existing phase-1 columns (`shopify_webhook_intakes`, `shopify_integration_events`).
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: Deployment child (master phase 7), not this phase.
- `13_sockets.md`, `56_realtime_layer.md`, `34_file_storage.md`: Not relevant to webhook intake.

## Implementation plan

1. All three previously open clarifications are resolved (see "Resolved decisions" items 7-9) — no open blockers remain.

2. Add a new function to `services/infra/shopify/hmac_verifier.py`: `is_valid_shopify_webhook_hmac(raw_body: bytes, provided_hmac_header: str) -> bool` — computes base64 HMAC-SHA256 over `raw_body` using the resolved secret (`settings.shopify_webhook_secret` or `settings.shopify_client_secret`, per "Resolved decisions" item 5), compares with `hmac.compare_digest` against the base64-decoded or base64-compared header value (implementation-time detail: match Shopify's documented base64 comparison exactly). Never logs the secret, the body, or the computed digest.

3. Add `services/commands/shopify/enqueue_or_record_shopify_webhook.py` — one command, per "Resolved decisions" item 8:
   - Accepts the raw body bytes, parsed headers (`X-Shopify-Hmac-Sha256`, `X-Shopify-Topic`, `X-Shopify-Shop-Domain`, `X-Shopify-Webhook-Id`), and the parsed JSON payload (for `raw_payload` storage only — never trusted for identity/routing decisions).
   - Verifies HMAC first; raises a validation error on failure (mapped by the router to `400` — an invalid signature is one of only two cases where Shopify should see a rejection, unlike unsupported topics or unknown/inactive shops).
   - Immediately after HMAC, checks `X-Shopify-Webhook-Id` is present and non-blank; if not, raises a validation error (mapped by the router to `400`), creating no intake row and no event, per "Resolved decisions" item 9 — this check happens before topic or shop lookup so no partial work is done for an undeduplicable delivery.
   - Normalizes the shop domain and resolves the `ShopifyShopIntegration` row per "Resolved decisions" item 1; returns a "no-op, no DB write" result if no row exists (per item 2), which the router turns into `200`.
   - If the resolved integration's `status` is `disabled` or `uninstalled`, proceeds to create the intake row (does not early-return) but forces `status=IGNORED`, `retryable=False`, and a `WARNING` event with `metadata_json["reason"] = "inactive_shop_integration"` plus `integration_status`, per "Resolved decisions" item 7 — this check happens right after shop resolution and takes precedence over the topic-support check below (an inactive shop is ignored regardless of whether its topic is supported).
   - For an active-like shop, looks up `get_webhook_definition(topic)`; an unsupported topic is also an `IGNORED` outcome, but with `metadata_json["reason"] = "unsupported_topic"` instead. Either way, builds the `dedupe_key` (`shop_integration_id:topic:webhook_id`); pre-checks for an existing intake with that key (and handles a race via caught `IntegrityError` on insert as the same outcome).
   - On first receipt: creates the `ShopifyWebhookIntake` row (`status=RECEIVED` for a supported topic on an active-like shop; `status=IGNORED` for an inactive shop or an unsupported topic, per the two ignored-outcome branches above), and records exactly one `ShopifyIntegrationEvent` (`WEBHOOK_RECEIVED`, severity `INFO` for `RECEIVED`, `WARNING` for either `IGNORED` case) via `_events.create_shopify_integration_event`.
   - On duplicate: makes no DB write beyond the dedupe check itself; optionally emits a debug-gated log line.
   - Never logs `raw_payload` or any header value that could contain sensitive Shopify request data beyond topic/shop-domain/webhook-id (all of which are safe, non-secret routing metadata).

4. Add the router `routers/api_v1/shopify_webhooks.py` (a new file, not added to the existing `shopify.py` OAuth router, since the two are mounted at different, non-nested prefixes):
   - `POST /webhooks`, mounted with no extra prefix segment beyond `/api/v1/shopify` so the full path is exactly `POST /api/v1/shopify/webhooks`, matching the fixed callback URL from "Phase 3 implementation dependencies verified."
   - Extracts `await request.body()` and the four Shopify headers, calls `enqueue_or_record_shopify_webhook` via `run_service`, and returns `400` for an invalid HMAC signature or a missing/blank webhook id, `200` for every other outcome (unsupported topic, unknown shop, inactive shop, duplicate, and normal success).
   - Register in `routers/api_v1/__init__.py` as a new `app.include_router(shopify_webhooks.router, prefix="/api/v1/shopify", tags=["shopify-webhooks"])` entry, alongside (not replacing) the existing `shopify.router` registration.

5. Tests:
   - HMAC unit tests: valid/invalid signature over a synthetic raw body, using a monkeypatched `shopify_webhook_secret`; confirm the function never logs the secret or body.
   - Route/command integration tests: valid webhook creates an intake row (`RECEIVED`) and one `INFO` event and returns 200; invalid HMAC returns `400` and creates no DB rows; missing/blank `X-Shopify-Webhook-Id` returns `400` and creates no DB rows or events; unsupported topic returns 200 and creates an `IGNORED` intake row plus a `WARNING` event; unknown shop domain returns 200 and creates no DB rows; a known shop integration with `status=disabled` or `status=uninstalled` returns 200 and creates an `IGNORED`/`retryable=False` intake row plus a `WARNING` event with `metadata_json["reason"] == "inactive_shop_integration"`; duplicate delivery (same headers/body replayed) creates no second intake row or event and returns 200; a test/assertion confirms no execution task type, payload class, or Redis/queue call exists anywhere in this phase's source (mirroring phase 3's source-inspection pattern for its own boundary).
   - Logging: no captured log line contains the raw request body or the webhook secret (negative assertion), matching phases 2 and 3's established logging-test pattern.

## Risks and mitigations

- Risk: The new webhook HMAC function is confused with or accidentally merged into the existing OAuth-callback HMAC function, since both live in the same file and both are "Shopify HMAC verification."
  Mitigation: Distinct function names, distinct signatures (`raw_body: bytes` + header vs. `raw_query_string: str`), and a unit test suite that never calls one where the other is expected.
- Risk: The webhook route is mounted at the wrong path (e.g. nested under `/api/v1/integrations/shopify`), silently breaking every webhook delivery once a real shop has subscriptions synced from phase 3.
  Mitigation: "Phase 3 implementation dependencies verified" pins the exact required path (`/api/v1/shopify/webhooks`) as a confirmed fact from phase 3's own already-tested callback URL construction, not a phase-4 choice; Implementation plan step 4 states the exact router prefix required.
- Risk: A shop with zero matching `ShopifyShopIntegration` rows causes an unhandled `IntegrityError` when the command tries to write an intake row with a null/invalid FK.
  Mitigation: "Resolved decisions" item 2 makes this an explicit branch (return 200, write nothing) rather than an attempted-and-failed write.
- Risk: Retry storms from Shopify (e.g. during a backend outage) flood `shopify_integration_events` with one row per delivery attempt.
  Mitigation: "Resolved decisions" item 3 records at most one event per unique `dedupe_key`; duplicate deliveries are DB-cheap dedupe checks only.
- Risk: This phase quietly grows into Option B (a minimal task type/enqueue path) because "it's right there" once intake persistence works.
  Mitigation: Acceptance criteria items 12 and 14 explicitly forbid any execution task type/payload/queue code in this phase; the test suite includes a source-inspection check mirroring phase 3's own boundary test.
- Risk: The raw request body is accidentally re-parsed/re-serialized before HMAC verification (e.g. FastAPI auto-parses JSON first), producing a byte-for-byte mismatch against Shopify's signature and rejecting all legitimate webhooks.
  Mitigation: Implementation plan step 4 explicitly calls out extracting `await request.body()` first, before any `.json()` parsing, mirroring phase 2's `raw_query_string` handling for the OAuth callback.
- Risk: A future phase 5 processes an `IGNORED` intake row for a disabled/uninstalled shop as if it were real work, because the row still contains a full `raw_payload`.
  Mitigation: "Resolved decisions" item 7 requires `status=IGNORED`, `retryable=False`, and `metadata_json["reason"] = "inactive_shop_integration"` on the event — both the intake `status` and the event `reason` give phase 5 an unambiguous, machine-checkable signal to skip these rows rather than requiring phase 5 to re-derive "should I process this" from the shop integration's current state at processing time.
- Risk: Rejecting deliveries with a missing `X-Shopify-Webhook-Id` with `400` causes Shopify to retry indefinitely if this ever happens in practice (e.g. a future Shopify API change), effectively DoS-ing that webhook topic.
  Mitigation: Per current Shopify documentation this header is always present; "Resolved decisions" item 9 treats absence as sufficiently rare to warrant surfacing loudly (via the `400` and a warning-level log) rather than silently working around it with a weaker dedupe key — if this assumption ever proves wrong in production, the `400` responses and warning logs are the signal that would surface it quickly, not a silent failure mode.

## Validation plan

- Phase 3 verification checklist (this plan's own dependency section) — already complete as of this draft.
- `pytest tests/unit/services/infra/shopify/test_hmac_verifier.py` (extended): new webhook-HMAC tests pass alongside the existing OAuth-callback HMAC tests.
- `pytest tests/integration/services/commands/shopify/` (new intake test file): valid/invalid-HMAC/missing-webhook-id/unsupported-topic/unknown-shop/inactive-shop/duplicate-delivery cases all pass.
- Negative logging test: no captured log line contains the raw payload or the webhook secret during a full mocked intake run.
- Static/source-inspection check: no execution task type, payload dataclass, or Redis/queue reference exists anywhere in this phase's new files.

## Review log

- `2026-07-08` `Codex`: Drafted fourth child implementation plan (Shopify webhook intake and execution enqueue) as a companion to phase 3, which is implemented, reviewed, and archived. Chose Option A (event-only enqueue boundary until phase 5) per the recommended design. Left in `under_construction` pending three open clarifications (accept-vs-ignore for inactive shop integrations on intake; single-vs-split command shape; missing-webhook-id handling).
- `2026-07-08` `User decision`: Resolved all three remaining blockers. (1) Known-but-inactive shop integrations (`disabled`/`uninstalled`) are persisted, not skipped — intake row `status=IGNORED`, `retryable=False`, plus a `WARNING` event with `reason="inactive_shop_integration"` — so phase 5 never treats these as processable work while operational visibility is preserved. (2) `enqueue_or_record_shopify_webhook` stays a single command owning input validation, resolution, persistence, dedupe, both ignored-outcome branches, and the event-only boundary — no split into intake/boundary commands in this phase, since the real enqueue boundary doesn't exist until phase 5. (3) A missing/blank `X-Shopify-Webhook-Id` is treated as an invalid delivery — `400`, no intake row, no event — because the durable dedupe key depends on it. Applied all three decisions to Resolved decisions (items 7-9), Scope, Acceptance criteria (renumbered, now 14 items), Implementation plan steps 1/3/4/5, and the risk list. Confirmed Option A is unchanged (no task types, no Redis enqueue, no worker, no execution payloads) and all out-of-scope exclusions remain intact. No blockers remain — plan moved from `under_construction` to `approved`.
- `2026-07-08` `Codex`: Implemented the approved Phase 4 scope exactly as planned. Added `POST /api/v1/shopify/webhooks`, a distinct raw-body Shopify webhook HMAC verifier, the single `enqueue_or_record_shopify_webhook` command, durable intake persistence with dedupe, ignored handling for unsupported topics and inactive integrations, and the event-only `WEBHOOK_RECEIVED` boundary with no execution-layer wiring. Added focused unit and integration coverage for valid webhook, invalid HMAC, HMAC-first validation order, missing webhook ID, unsupported topic, unknown shop, inactive integration states, duplicate delivery, exact route path, no JWT/role protection, and the no-execution-runtime boundary. Validation completed with focused suites plus the impacted Shopify regression bundle (`76 passed`). Plan archived and summary written at `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_webhook_intake_execution_20260708.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `Codex`
