# PLAN_shopify_webhook_registry_sync_20260707

## Metadata

- Plan ID: `PLAN_shopify_webhook_registry_sync_20260707`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T14:00:00Z`
- Last updated at (UTC): `2026-07-08T07:49:42Z`
- Related issue/ticket: `Shopify integration webhook registry and subscription sync`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` — phase 1 is implemented, archived, and its foundation (`domain/shopify/webhook_registry.py`, `ShopifyWebhookSubscription` model, config fields) is used directly by this plan.
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md` — phase 2 is implemented, reviewed, and archived (see "Phase 2 implementation dependencies to verify before approval" below, filled in with confirmed facts). No blockers remain — see "Resolved decisions."

## Goal and intent

- Goal: Draft the Shopify webhook subscription sync subsystem — a GraphQL infra client boundary, commands that reconcile desired (phase-1 registry) vs. installed (remote Shopify) webhook subscriptions for one shop at a time, idempotent install/remove, local `shopify_webhook_subscriptions` status tracking, and safe error/logging handling.
- Business/user intent: Once a shop is linked (phase 2), give the backend a safe, callable, idempotent way to bring that shop's remote Shopify webhook subscriptions in line with the central registry — without yet wiring it to run automatically inline during OAuth or through a background worker (both are later phases).
- Non-goals:
  - Inbound webhook HTTP route / intake (master phase 4).
  - Webhook HMAC intake verification (master phase 4).
  - Webhook processing (master phase 4).
  - `SHOPIFY_PROCESS_WEBHOOK` task type or any Shopify execution task type/payload (master phase 5).
  - Dedicated Shopify worker or Redis queue mapping (master phase 5).
  - Execution-layer task handlers (master phase 5).
  - Admin routes (master phase 6).
  - Frontend UI.
  - Historical product/order imports.
  - Creation of remaining child implementation plans (phases 4-7 of the master plan).
  - Connecting the OAuth callback to real inline or enqueued webhook sync — `enqueue_shopify_webhook_sync_after_install` (phase 2) stays an event-only no-op in this phase; see "Resolved decisions" (master-plan deviation approved).
  - Automatically deleting an existing remote webhook subscription solely because the shop's granted scopes no longer cover its required scopes — see "Resolved decisions."

## Scope

- In scope:
  - Central Shopify webhook registry usage from phase 1 (`domain/shopify/webhook_registry.py`: `SHOPIFY_WEBHOOK_REGISTRY`, `get_webhook_definition`, `SHOPIFY_WEBHOOK_CALLBACK_PATH`).
  - A Shopify webhook subscription GraphQL client boundary under `services/infra/shopify/`.
  - Query existing remote webhook subscriptions from Shopify for one shop.
  - Create missing remote webhook subscriptions for one shop.
  - Remove disabled/undesired remote webhook subscriptions where safe (see Acceptance criteria for the exact safety conditions) — a topic no longer scope-covered is **not** one of those conditions; see "Resolved decisions."
  - Mark a local `ShopifyWebhookSubscription` row `FAILED` with `last_error_code="missing_required_scope"` when its topic's required scopes are no longer covered by the shop's granted scopes, without deleting the corresponding remote subscription.
  - Update local `shopify_webhook_subscriptions` rows to reflect the outcome of every create/remove/no-op decision.
  - `sync_shopify_webhook_subscriptions_for_shop`: idempotent reconciliation for one shop (desired-vs-installed, creates missing, removes undesired, leaves matching subscriptions untouched).
  - `remove_shopify_webhooks_for_shop`: idempotent bulk removal for one shop (for later use by disconnect flows in phase 6 — this phase only builds the command, not the route that calls it).
  - Status transitions for `shopify_webhook_subscriptions` (`PENDING` -> `ACTIVE`/`FAILED`, `-> REMOVED`) using the phase-1 `ShopifyWebhookSubscriptionStatusEnum`.
  - Safe structured logging (gated by `settings.shopify_integration_debug_logs` where appropriate) that never includes the access token or raw Shopify request/response bodies containing secrets.
  - Shopify GraphQL request error normalization into a Shopify-specific `ExternalServiceError` subclass.
  - Retryable vs. non-retryable error classification (timeouts/5xx/rate-limit -> retryable; auth/validation/user errors -> non-retryable).
  - Tests with mocked Shopify GraphQL responses (no real network calls).
- Out of scope:
  - Inbound webhook HTTP route.
  - Webhook intake route.
  - Webhook HMAC intake verification.
  - Webhook processing.
  - `SHOPIFY_PROCESS_WEBHOOK` task type.
  - Dedicated Shopify worker.
  - Redis queue mapping.
  - Execution-layer task handlers.
  - Admin routes.
  - Frontend UI.
  - Historical product/order imports.
  - Remaining child plans (phases 4-7).
- Assumptions:
  - Phase 1's `ShopifyWebhookSubscription` model, `ShopifyWebhookSubscriptionStatusEnum`, and `domain/shopify/webhook_registry.py` are used exactly as implemented (see "Phase 1 implementation dependencies" carried over from phase 2's review — already verified, not re-verified here).
  - Phase 2's `ShopifyShopIntegration` row (with `access_token_encrypted`, `granted_scopes`, `status`) exists and is populated by `handle_shopify_oauth_callback`/`link_or_update_shopify_shop` (confirmed implemented) — but this phase does not assume phase 2 calls these new commands; they are called manually/by tests/by a later phase in this plan's scope.
  - Shopify's Admin API GraphQL exposes `webhookSubscriptions` (query), `webhookSubscriptionCreate` (mutation), and `webhookSubscriptionDelete` (mutation) for the API version this backend targets (`settings.shopify_api_version`); exact field-level GraphQL query/mutation shapes are an implementation-time detail against current Shopify docs, not a plan-blocking clarification.
  - A shop's remote `webhookSubscriptions` query is inherently scoped to the app/token used to call it — Shopify does not return another app's subscriptions for the same shop. Removal logic still only acts on subscriptions this backend can positively identify as belonging to its own registry (see Acceptance criteria) as defense in depth, not because Shopify might return foreign subscriptions.

## Phase 2 implementation dependencies to verify before approval

Phase 2 was reviewed against the archived plan, its implemented summary, and the actual code in the repository on `2026-07-08`. Every item below is now a **confirmed fact**, not an assumption.

- [x] **Actual Shopify OAuth router path** — confirmed: `app/beyo_manager/routers/api_v1/shopify.py` defines `router = APIRouter()` with `POST /install-url` and `GET /oauth/callback`. `app/beyo_manager/routers/api_v1/__init__.py` imports `shopify` and calls `app.include_router(shopify.router, prefix="/api/v1/integrations/shopify", tags=["shopify"])`. Full paths: `POST /api/v1/integrations/shopify/install-url`, `GET /api/v1/integrations/shopify/oauth/callback`. Matches this plan's original assumption exactly. This phase must not add a second router file for the same prefix — any future admin/sync route in this phase's scope (there is none) would belong in this same file or a sibling, per `21_naming_conventions.md`.
- [x] **Actual command names and paths** — confirmed under `services/commands/shopify/`: `create_shopify_install_url.py`, `handle_shopify_oauth_callback.py`, `link_or_update_shopify_shop.py`, `enqueue_shopify_webhook_sync_after_install.py`. Phase 2 also introduced four internal (underscore-prefixed, not part of the public command surface) helper modules in the same package: `_callback_errors.py` (`ShopifyOAuthCallbackError`), `_events.py` (`create_shopify_integration_event`), `_linking.py` (`link_or_update_shopify_shop_record`), `_redirect.py` (`build_shopify_oauth_redirect_url`, `validate_redirect_after_success_key`), `_webhook_sync.py` (`record_webhook_sync_pending`). This phase's new files (`sync_shopify_webhook_subscriptions_for_shop.py`, `remove_shopify_webhooks_for_shop.py`) must not collide with any of these nine names, and should reuse `_events.create_shopify_integration_event` directly for their own event recording rather than duplicating it (see Implementation plan step 6).
- [x] **Actual infra Shopify OAuth module paths** — confirmed: `services/infra/shopify/oauth_client.py` (`build_shopify_install_url`, `exchange_oauth_code_for_offline_token`, `ShopifyOAuthTokenExchangeResult`) and `services/infra/shopify/hmac_verifier.py` (`is_valid_shopify_oauth_callback_hmac`). No collision with this phase's planned `graphql_client.py`/`webhook_subscription_client.py`. Both existing modules raise `beyo_manager.errors.external_service.ExternalServiceError` on failure, confirming the exact base class this phase's Shopify-specific error subclass(es) must extend.
- [x] **Actual token crypto usage** — confirmed: `_linking.link_or_update_shopify_shop_record` sets `access_token_encrypted=encrypt_field(access_token)` (imported from `beyo_manager.services.infra.crypto.field_encryption`), with no extra wrapping. Verified round-trip directly in `tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py`: `decrypt_field(integration.access_token_encrypted or "") == "offline-access-token"`. This phase's `graphql_client` can safely call `field_encryption.decrypt_field(integration.access_token_encrypted)` with no shape correction needed.
- [x] **Actual event-recording command behavior** — confirmed: `_events.create_shopify_integration_event(session, *, workspace_id, shop_integration_id, event_type, severity, message, metadata_json, created_by_id)` constructs `ShopifyIntegrationEvent(metadata_json=..., ...)` exactly as planned (never `metadata=`). Phase 2 records `INSTALL`/`REAUTHORIZE` from `_linking.py` and `WEBHOOK_SYNC` from `_webhook_sync.py` — outcome-level only, matching the established pattern. This phase's sync/remove commands should call `_events.create_shopify_integration_event` directly (it is already a shared, reusable helper) rather than writing a second event-construction function.
- [x] **Actual `enqueue_shopify_webhook_sync_after_install` function path and signature** — confirmed: `services/commands/shopify/enqueue_shopify_webhook_sync_after_install.py`, `async def enqueue_shopify_webhook_sync_after_install(ctx: ServiceContext) -> dict`, validated via a small pydantic request model (`workspace_id`, `user_id`, `shop_integration_id`, `shop_domain`), loads the `ShopifyShopIntegration` by id (raises `ValidationError` if not found), then calls `_webhook_sync.record_webhook_sync_pending(...)`, which calls only `_events.create_shopify_integration_event(event_type=WEBHOOK_SYNC, ...)`. Confirmed pure event-recording no-op — no GraphQL/HTTP call, no queue/task reference anywhere in this file or its dependency chain. **Important nuance found during review**: `handle_shopify_oauth_callback` does **not** call this standalone command function — it calls the shared helper `_webhook_sync.record_webhook_sync_pending(...)` directly (avoiding a nested command-calling-command hop), so there are effectively two call sites that must both stay inert: `enqueue_shopify_webhook_sync_after_install.py` itself, and `handle_shopify_oauth_callback.py`'s direct call into `_webhook_sync.py`. This phase's "no real sync reference" check (Acceptance criteria item 11 / Implementation plan step 8 / test step) must cover both, not just the standalone command file.
- [x] **Actual config field names** — confirmed unchanged: `shopify_webhook_base_url`, `shopify_api_version` (default `"2026-01"`) remain exactly as phase 1 defined them in `app/beyo_manager/config.py`. Phase 2's new field is exactly `shopify_oauth_redirect_url: str | None = Field(default=None, alias="SHOPIFY_OAUTH_REDIRECT_URL")`, added under the same `# Shopify` comment block, not present in `_require_critical_settings`. No Shopify-specific encryption key was added, and no `refresh_token_encrypted` field exists anywhere in the codebase (grepped, zero matches).
- [x] **Actual `settings.shopify_oauth_redirect_url` behavior** — confirmed consumed only by `_redirect.build_shopify_oauth_redirect_url`, which appends only `success`/`shop_domain`/`error_code` query parameters and raises `ValidationError` if unset or not an absolute http(s) URL. Not directly used by this phase (no redirect logic here), but confirms the config-usage pattern already established is safe to follow if this phase ever needed a new setting (it does not).
- [x] **Actual route registration path** — confirmed in `routers/api_v1/__init__.py`: `shopify` is imported alongside the other `api_v1` modules and `app.include_router(shopify.router, prefix="/api/v1/integrations/shopify", tags=["shopify"])` is called immediately after `auth.router` and before `users.router`.
- [x] **Actual test results from phase 2** — confirmed from the implemented summary and reviewed directly: `pytest tests/unit/domain/shopify tests/unit/services/infra/shopify/test_hmac_verifier.py tests/unit/services/infra/shopify/test_oauth_client.py tests/unit/test_shopify_router.py tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: `39 passed`. Reviewed test content directly: HMAC accept/reject, token-exchange success/timeout, install-url role gating (`ADMIN`/`MANAGER` -> 200; `WORKER`/`SELLER` -> 403 with zero command invocations), callback redirect safety (redirect query contains only `success`/`shop_domain`, never state/hmac/token), OAuth state expiry/replay/consumption rejection, encryption round-trip, cross-workspace active-like conflict rejection, and a no-secret-in-logs negative assertion. One test gap found (non-blocking, does not affect this phase's design): the standalone `enqueue_shopify_webhook_sync_after_install(ctx)` command has no direct unit test of its own (only exercised indirectly via the OAuth callback's separate call path into the shared helper).
- [x] **Implemented summary path** — `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_oauth_linking_20260708.md` (confirmed exists and reviewed).
- [x] **Archived phase 2 plan path** — `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md` (confirmed exists, `Status: archived`, reviewed as the authoritative record).
- [x] **Other deviations found during phase-2 review, carried into this plan**: the token-exchange-failure error path in `handle_shopify_oauth_callback` hardcodes `redirect_key="default"` instead of reusing the loaded state row's own key — harmless today (only one valid key exists) and irrelevant to this phase, noted for completeness only. No deviation found that changes this phase's design beyond the two-call-site nuance above.

## Resolved decisions

These clarifications are resolved for this child plan by explicit product/policy decision and must not be re-opened during implementation.

1. **Auto-remove on revoked scope — resolved as no auto-delete.** `sync_shopify_webhook_subscriptions_for_shop` must **not** automatically remove an existing remote webhook subscription only because its required scopes are no longer covered by the shop's granted scopes. Specifically:
   - If a desired webhook definition requires scopes the shop no longer has, the command does **not** create that subscription (unchanged from Acceptance criteria item 4).
   - If a matching remote subscription already exists but the required scopes are no longer granted, the command does **not** delete it.
   - The local `ShopifyWebhookSubscription` row for that topic is set to `FAILED` (the existing `ShopifyWebhookSubscriptionStatusEnum` has no `OUTDATED` member, so `FAILED` is reused deliberately rather than adding a migration/enum member for this decision) with `last_error_code="missing_required_scope"` and a safe, non-secret `last_error_message`.
   - A `ShopifyIntegrationEvent` is recorded with `event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC` and a `metadata_json` payload identifying the affected topic(s) and `"reason": "missing_required_scope"` — no token, no raw Shopify payload.
   - A structured debug log line may be emitted, gated by `settings.shopify_integration_debug_logs`, containing only safe fields (shop domain, topic, missing scope names) — never the access token or raw Shopify request/response bodies.
   - **Reason**: a scope mismatch usually means the shop needs reauthorization, not that the webhook subscription is unwanted. Silently deleting a potentially recoverable subscription during a routine sync would be surprising and could cause silent data loss (missed orders/products) once the shop is reauthorized, since nothing would have flagged that the subscription was ever removed. Remote deletion is reserved for the three conditions in Acceptance criteria item 6: topic absent from the registry, topic disabled in the registry, or an explicit `remove_shopify_webhooks_for_shop` call (e.g. a future disconnect flow).
2. **Master-plan deviation — approved.** The master plan's phase 3 description lists `16_background_jobs.md` as a required contract and `domain/execution/payloads/` as an expected file area, anticipating phase 3 might define the future `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP`/`SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP` task payload shapes even before the worker exists. This plan deliberately does **not** select `16_background_jobs.md` and does **not** touch `domain/execution/payloads/` — task types, payload dataclasses, queue mapping, the dedicated worker, Redis queue wiring, and execution-layer handlers are entirely master phase 5's ownership per the master plan's own phase-5 description ("Owns: Shopify task types, payload dataclasses..."), and defining them here would create two owners for the same concern. This phase owns only the directly callable webhook registry/subscription sync subsystem: the Shopify GraphQL webhook subscription client, `sync_shopify_webhook_subscriptions_for_shop`, `remove_shopify_webhooks_for_shop`, desired-vs-installed reconciliation, local `shopify_webhook_subscriptions` status updates, outcome-level `ShopifyIntegrationEvent` recording, and mocked tests for sync/remove behavior — all directly callable functions that phase 5 wires into task handlers later. This deviation is confirmed acceptable and closes the only other remaining blocker. This plan is approved.

## Acceptance criteria

1. `services/infra/shopify/graphql_client.py` centralizes Shopify GraphQL request execution: builds the endpoint from the shop's normalized `shop_domain` and `settings.shopify_api_version`, decrypts `access_token_encrypted` via `field_encryption.decrypt_field` only at the point of the HTTP call (never persisted or logged in decrypted form), sets the request timeout explicitly, and is the only module in this phase that constructs a Shopify GraphQL HTTP request.
2. Shopify GraphQL/HTTP failures are normalized into a Shopify-specific `ExternalServiceError` subclass with an explicit retryable/non-retryable classification — timeouts, connection errors, and 5xx/rate-limit responses are retryable; 4xx auth failures and GraphQL `userErrors` are non-retryable. No raw `httpx` exception or raw GraphQL error body crosses this boundary uncaught.
3. `sync_shopify_webhook_subscriptions_for_shop(shop_integration_id)` is idempotent: calling it twice in a row with no external state change results in no duplicate create/delete calls and no duplicate local rows on the second call.
4. The desired-for-creation set for a sync run is `SHOPIFY_WEBHOOK_REGISTRY` filtered to `enabled=True` definitions whose `required_scopes` are fully covered by the shop's `granted_scopes` (via phase-1's `has_all_required_scopes`); topics whose required scopes are not granted are skipped and not created.
5. For each desired topic missing remotely, the command creates the remote subscription (using `SHOPIFY_WEBHOOK_CALLBACK_PATH` combined with `settings.shopify_webhook_base_url` as the callback URL) and upserts a local `ShopifyWebhookSubscription` row to `ACTIVE` on success or `FAILED` (with `last_error_code`/`last_error_message` set) on failure — a failed create does not stop the rest of the sync run for other topics.
6. A remote subscription is removed only when all of the following hold: (a) its callback URL matches this backend's own `SHOPIFY_WEBHOOK_CALLBACK_PATH`/`shopify_webhook_base_url` combination, (b) its topic is either absent from `SHOPIFY_WEBHOOK_REGISTRY` or disabled (`enabled=False`) in the registry — a topic that is merely no longer scope-covered is explicitly **not** a removal condition (see "Resolved decisions") — and (c) the local row (if any) is not already `REMOVED`. Removing an already-absent remote subscription is treated as success (idempotent), not an error.
7. Subscriptions whose remote state already matches the desired state are left untouched by create/remove calls; `last_verified_at` may be updated to record that the sync run confirmed them.
8. When a remote subscription already exists for a topic whose required scopes are no longer covered by the shop's granted scopes, the command leaves the remote subscription in place, sets the local row's status to `FAILED` with `last_error_code="missing_required_scope"`, and does not treat this as a create/remove action for idempotency purposes — re-running sync with no other state change produces the same `FAILED`/`missing_required_scope` outcome, not a repeated action.
9. `remove_shopify_webhooks_for_shop(shop_integration_id)` idempotently removes all of this backend's own remote subscriptions for the shop — including ones a sync run left `FAILED` due to `missing_required_scope` — and marks all local rows `REMOVED`; calling it when no subscriptions remain succeeds as a no-op.
10. Every sync/remove run records a single outcome-level `ShopifyIntegrationEvent` (`event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC`) summarizing what changed, using `metadata_json` for structured detail (including any `missing_required_scope` topics) — never the raw access token or raw GraphQL request/response bodies.
11. No command or infra module in this phase calls `sync_shopify_webhook_subscriptions_for_shop` or `remove_shopify_webhooks_for_shop` from inside `enqueue_shopify_webhook_sync_after_install` or anywhere in the phase-2 OAuth callback path — that boundary remains a pure event-recording no-op in this phase (see "Resolved decisions").
12. This phase adds no inbound webhook route, no execution task types/payloads, no worker code, no admin routes, and no frontend code.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: Commands own writes/orchestration; infra owns the Shopify GraphQL adapter; domain (`webhook_registry.py`) stays the pure source of desired state.
- `architecture/05_errors.md`: Shopify GraphQL failures raise a specific `ExternalServiceError` subclass, never a bare `DomainError` or built-in exception.
- `architecture/06_commands.md`: Write-operation structure for `sync_shopify_webhook_subscriptions_for_shop` and `remove_shopify_webhooks_for_shop`.
- `architecture/08_domain.md`: Reuse (not reimplement) phase-1's pure `webhook_registry.py` and `scopes.py` helpers for desired-set and scope-coverage computation.
- `architecture/17_logging.md`: Structured logs for sync/remove operations, gated by `settings.shopify_integration_debug_logs` where appropriate, no secrets or raw payloads.
- `architecture/18_security.md`: Access token is decrypted only at the point of use inside the infra client and never logged or returned from any command.
- `architecture/19_integrations.md`: Adapter pattern for the Shopify GraphQL client, explicit timeouts, error normalization, mapper pattern for GraphQL responses, integration-test isolation via mocked clients (no real network calls).
- `architecture/21_naming_conventions.md`: Command/file/module naming for this phase.
- `architecture/24_multi_tenancy.md`: Sync/remove operate on one `shop_integration_id` at a time and never cross workspace boundaries; the shop integration row's `workspace_id` is used for event recording.
- `architecture/40_identity.md`: Reuses phase-1's `shpwhs` prefix for any new local rows; no new prefixes needed.
- `architecture/42_event.md`: Outcome-level `ShopifyIntegrationEvent` recording for sync/remove runs, following the phase-1/phase-2 established pattern.
- `architecture/15_testing.md`: Test tier placement for infra client tests (mocked HTTP) and command tests (mocked infra client), matching `19_integrations.md`'s integration-test-isolation rule.

### Local extensions loaded

- `architecture/40_identity_local.md`: No new prefixes needed in this phase; reuses phase-1's `shpwhs`.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `19_integrations.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape -> `06_commands.md`
- Reading another infra adapter to understand retry/timeout wiring -> `19_integrations.md`

Permitted for this child:
- `app/beyo_manager/domain/shopify/webhook_registry.py`, `scopes.py`, `enums.py` — required to confirm actual registry/helper/enum names per phase-1 (already verified in phase 2's review; re-read only to double-check nothing changed).
- `app/beyo_manager/models/tables/shopify/shopify_webhook_subscription.py`, `shopify_shop_integration.py` — for exact column names/types this phase reads and writes.
- `app/beyo_manager/services/commands/shopify/` and `app/beyo_manager/services/infra/shopify/` — phase 2's file/function names are confirmed per "Phase 2 implementation dependencies to verify before approval"; re-read only `_events.py`/`_webhook_sync.py` at implementation time to call/extend them precisely.
- `app/beyo_manager/services/infra/crypto/field_encryption.py` — existing decryption boundary this phase calls for the first time.
- `app/beyo_manager/services/infra/location_tracker/client.py`, `services/infra/upholstery_providers/` — read only as relational examples of this codebase's existing external-adapter timeout/error-normalization style, not copied verbatim.
- `app/beyo_manager/errors/external_service.py`, `errors/base.py` — for the exact base class this phase's Shopify-specific error subclass(es) extend.
- `app/beyo_manager/config.py` — to confirm `shopify_webhook_base_url`/`shopify_api_version` are unchanged after phase 2.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`: Deliberately not selected — see "Resolved decisions" (master-plan deviation approved). Task types, payloads, and queue routing belong entirely to master phase 5.
- `09_routers.md`: No HTTP routes in this phase.
- `07_queries.md`, `07_queries_local.md`: No list/detail query surface; remote-state lookups go through the infra client, not the DB query layer.
- `03_models.md`, `30_migrations.md`: No new tables or schema changes — this phase only reads/writes existing phase-1 columns.
- `28_roles_permissions.md`: No routes/permissions in this phase; role gating is master phase 6's concern for the admin sync route.
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: Deployment child (master phase 7), not this phase.
- `13_sockets.md`, `56_realtime_layer.md`, `34_file_storage.md`: Not relevant to webhook subscription sync.

## Implementation plan

1. Phase 2 verification is complete (see "Phase 2 implementation dependencies to verify before approval" — all items confirmed against the archived plan, implemented summary, and actual code).

2. All clarifications are resolved (see "Resolved decisions") — no open blockers remain.

3. Add `services/infra/shopify/graphql_client.py`:
   - A thin, generic GraphQL request executor: `execute(shop_domain: str, access_token: str, query: str, variables: dict) -> dict`, using `httpx.AsyncClient` with an explicit timeout, `settings.shopify_api_version` in the endpoint URL, and the shop's decrypted access token in the `X-Shopify-Access-Token` header.
   - Never accepts a pre-decrypted token from a caller that isn't the webhook subscription client below — decryption happens immediately before this call, not earlier and not cached.
   - Raises the Shopify-specific `ExternalServiceError` subclass (see step 4) on timeout, transport error, non-2xx HTTP status, or top-level GraphQL `errors`.

4. Add Shopify-specific error classes (new file, e.g. `app/beyo_manager/errors/external_service.py` addition or a small `errors/` extension) following `05_errors.md`'s "add new subclasses when a new semantic category is needed" rule:
   - `ShopifyGraphQLError(ExternalServiceError)` base.
   - A `retryable: bool` distinguishing marker (either via two subclasses, e.g. `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError`, or a constructor flag) — timeouts/connection errors/5xx/rate-limit responses are retryable; 4xx auth errors and GraphQL `userErrors` are non-retryable.

5. Add `services/infra/shopify/webhook_subscription_client.py`, built on `graphql_client.execute`:
   - `list_remote_webhook_subscriptions(shop_domain, access_token) -> list[RemoteWebhookSubscription]` (a small mapper dataclass with `id`, `topic`, `callback_url`, per `19_integrations.md`'s mapper pattern — never returns raw Shopify JSON to callers).
   - `create_remote_webhook_subscription(shop_domain, access_token, topic, callback_url, format) -> RemoteWebhookSubscription`.
   - `delete_remote_webhook_subscription(shop_domain, access_token, remote_subscription_id) -> None` (treats "not found" as success).

6. Add `services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py`:
   - Loads the `ShopifyShopIntegration` row; raises a domain error if it has no `access_token_encrypted` or is not in an active-like status.
   - Decrypts the token via `field_encryption.decrypt_field` immediately before calling the infra client; the plaintext token never leaves this command's local scope and is never included in any log statement, exception message, or returned dict.
   - Computes two sets from `SHOPIFY_WEBHOOK_REGISTRY`: (a) the **creation-eligible** set — `enabled=True` definitions whose `required_scopes` are fully covered by `has_all_required_scopes(definition.required_scopes, integration.granted_scopes)`; (b) the **removal-eligible** set of registry topics that are absent or `enabled=False` — scope coverage plays no part in removal eligibility (see "Resolved decisions").
   - Fetches the remote subscription list, diffs against the two sets above and against local `ShopifyWebhookSubscription` rows:
     - Missing remotely + creation-eligible -> create, upsert local row `ACTIVE`/`FAILED` per Acceptance criteria item 5.
     - Present remotely + registry-absent-or-disabled (and callback URL matches this backend, and local row isn't already `REMOVED`) -> remove, upsert local row `REMOVED`.
     - Present remotely + registry-enabled but **not** scope-covered -> leave the remote subscription untouched; upsert the local row to `FAILED` with `last_error_code="missing_required_scope"` and a safe `last_error_message` (no token/raw payload); do not call the delete mutation for this topic.
     - Present remotely + registry-enabled + scope-covered -> leave untouched, optionally bump `last_verified_at`.
   - Per-topic failures (create/delete call errors, not the missing-scope case above) are caught and recorded (`FAILED` + error fields) without aborting the rest of the run.
   - Records one summary `ShopifyIntegrationEvent` at the end via the existing `services/commands/shopify/_events.create_shopify_integration_event` helper (do not write a second event-construction function), with `metadata_json` listing any `missing_required_scope` topics alongside created/removed/failed topics.
   - Emits a structured debug log line (gated by `settings.shopify_integration_debug_logs`) for each `missing_required_scope` topic, containing only shop domain, topic, and the missing scope names — never the token or raw Shopify payload.
   - Returns a plain result (created/removed/skipped/failed topic lists) — no new `domain/shopify/results.py`/serializer file (that remains deferred to master phase 6, consistent with phase 1's decision).

7. Add `services/commands/shopify/remove_shopify_webhooks_for_shop.py`:
   - Loads the shop integration, decrypts the token, lists remote subscriptions matching this backend's callback URL, removes each (idempotently), marks all matching local rows `REMOVED`, records one summary event via `_events.create_shopify_integration_event`.

8. Do not modify `services/commands/shopify/enqueue_shopify_webhook_sync_after_install.py` **or** `services/commands/shopify/_webhook_sync.py`/`handle_shopify_oauth_callback.py` (phase 2) to call either new command. Both are confirmed call sites into the same event-only boundary (`handle_shopify_oauth_callback` calls `_webhook_sync.record_webhook_sync_pending` directly rather than the standalone command — see "Phase 2 implementation dependencies to verify before approval"), and both must remain inert in this phase. Phase 5 is responsible for wiring a real enqueue path to these commands.

9. Tests (all against mocked `webhook_subscription_client`/`graphql_client`, per `19_integrations.md`'s integration-test-isolation rule — no real Shopify network calls):
   - `graphql_client`: timeout, connection error, non-2xx status, and GraphQL `errors` each normalize to the correct retryable/non-retryable `ShopifyGraphQLError` subclass; token is read from the encrypted column and decrypted exactly once per call, never logged.
   - `webhook_subscription_client`: list/create/delete map raw GraphQL responses to `RemoteWebhookSubscription`/`None` correctly; delete-of-missing is treated as success.
   - `sync_shopify_webhook_subscriptions_for_shop`: empty remote state creates all desired topics; fully-matching remote state makes zero create/delete calls (idempotency); a topic missing required scope with no existing remote subscription is skipped (not created); a topic missing required scope with an **existing** remote subscription is left in place (no delete call) and the local row becomes `FAILED`/`missing_required_scope`; re-running sync in that state produces the same outcome with still no delete call (idempotency for the missing-scope case); an undesired (registry-absent-or-disabled) remote subscription is removed; a create failure for one topic does not prevent other topics from being processed; running twice in a row is a no-op the second time.
   - `remove_shopify_webhooks_for_shop`: removes all tracked subscriptions; running again when none remain is a no-op.
   - Logging: no test asserts on log content containing the access token or raw GraphQL response bodies (negative assertion).
   - Explicit non-goal check: a test/assertion confirms neither `enqueue_shopify_webhook_sync_after_install.py` nor `_webhook_sync.py`/`handle_shopify_oauth_callback.py` (phase 2) references `sync_shopify_webhook_subscriptions_for_shop` or `remove_shopify_webhooks_for_shop` — both confirmed call sites into the event-only boundary must be checked, not just the standalone command file (see "Phase 2 implementation dependencies to verify before approval").

## Risks and mitigations

- Risk: This plan was originally drafted against an approved-but-unimplemented phase-2 design; phase 2 is now implemented and verified, but the two-call-site nuance (standalone command vs. the callback's direct helper call) could be missed if only the standalone file is checked.
  Mitigation: "Phase 2 implementation dependencies to verify before approval" documents both call sites explicitly; Implementation plan step 8 and the test in step 9 check both.
- Risk: The GraphQL infra client accidentally logs the decrypted access token or a raw request/response body containing it.
  Mitigation: Decrypt only immediately before the HTTP call inside `graphql_client.execute`; structured log statements reference only shop domain, topic, and status — never headers or bodies; enforced by a negative logging test.
- Risk: Removal logic deletes a remote webhook subscription that isn't actually this backend's own, or deletes on a transient/incorrect diff, or deletes because a scope was revoked.
  Mitigation: Removal requires a positive callback-URL match to this backend's own registered path plus one of the two explicit "undesired" conditions in Acceptance criteria item 6 (absent from or disabled in the registry) — scope coverage is explicitly excluded from removal eligibility per "Resolved decisions"; "not found remotely" is always treated as already-satisfied, never as a reason to act elsewhere.
- Risk: A scope revocation silently deletes a working, potentially-recoverable webhook subscription with no human in the loop.
  Mitigation: Resolved as no-auto-delete-on-missing-scope — the subscription is left in place, the local row is marked `FAILED`/`missing_required_scope`, and an event is recorded so the condition is visible and actionable via reauthorization, not silently lost.
- Risk: A partial failure during sync (one topic's create/delete fails) aborts the whole run and leaves other topics unreconciled.
  Mitigation: Per-topic try/except inside the sync command; failures are recorded on the local row and in the summary event, not raised, so the rest of the run completes.
- Risk: This phase quietly starts building execution-layer payload/task-type code because the master plan's phase-3 description mentions it.
  Mitigation: Explicit "Resolved decisions" entry (master-plan deviation approved) and a corresponding "contracts intentionally not selected" entry keep `domain/execution/payloads/` and `16_background_jobs.md` out of this phase's file list.
- Risk: `enqueue_shopify_webhook_sync_after_install` gets wired to real sync logic "since the commands now exist," accidentally making OAuth callback block on a Shopify GraphQL round trip.
  Mitigation: Implementation plan step 8 and Acceptance criteria item 11 explicitly forbid this in-phase; a test asserts both confirmed call sites contain no such reference.

## Validation plan

- Phase 2 verification checklist (this plan's own dependency section) passes before implementation starts.
- `pytest tests/unit/services/infra/shopify/`: GraphQL client and webhook subscription client tests pass with mocked HTTP.
- `pytest tests/unit/services/commands/shopify/`: sync/remove command tests pass with mocked infra client, including the idempotency and partial-failure cases.
- Negative logging test: no captured log line contains a token-shaped value or a raw GraphQL response body during a full mocked sync run.
- Static check: neither `enqueue_shopify_webhook_sync_after_install.py` nor `_webhook_sync.py`/`handle_shopify_oauth_callback.py` references `sync_shopify_webhook_subscriptions_for_shop` or `remove_shopify_webhooks_for_shop`.

## Review log

- `2026-07-08` `Codex`: Drafted third child implementation plan (Shopify webhook registry and subscription sync) as a companion to phase 2, which is approved but not yet implemented. Left in `under_construction` pending phase-2 verification and open clarifications (auto-remove-on-revoked-scope behavior, master-plan deviation on execution-payload ownership).
- `2026-07-08` `User/GPT review, Stage 1`: Reviewed the archived phase-2 plan, its implemented summary, and the actual code (`routers/api_v1/shopify.py`, `routers/api_v1/__init__.py`, `config.py`, `services/infra/shopify/`, `services/commands/shopify/` including the internal `_callback_errors.py`/`_events.py`/`_linking.py`/`_redirect.py`/`_webhook_sync.py` helpers, and all phase-2 tests). Verdict: **approved with minor follow-up** — no critical issues; HMAC-before-trust ordering, one-time state consumption with row locking, identity recovery solely from the stored state row, role gating (`ADMIN`/`MANAGER` only, verified 403 for `WORKER`/`SELLER` with zero command invocations), encryption reuse (verified round-trip via `decrypt_field`), safe redirect (verified query contains only `success`/`shop_domain`), `metadata_json` usage, and scope boundaries (no GraphQL/webhook-subscription/worker/queue/admin/serializer code) all confirmed correct and matching the approved phase-2 plan. Non-blocking notes: the standalone `enqueue_shopify_webhook_sync_after_install` command has no direct unit test (only exercised indirectly); a hardcoded `redirect_key="default"` fallback in one error path is harmless today; one line of defensive dead code (`"oauth_state" in locals()`) is cosmetic only. Discovered and documented an important structural nuance: the OAuth callback calls the shared `_webhook_sync.record_webhook_sync_pending` helper directly rather than the standalone `enqueue_shopify_webhook_sync_after_install` command, so this phase's "stays inert" checks must cover both call sites.
- `2026-07-08` `User/GPT review, Stage 2`: Replaced all assumed phase-2 names in "Phase 2 implementation dependencies to verify before approval" with confirmed facts, including the two-call-site nuance. Updated Implementation plan steps 6, 7, and 8, the test list, the risk list, and the "permitted file reads" list to reference the actual `_events.create_shopify_integration_event`/`_webhook_sync.py` helpers instead of assumed names, and to check both event-only call sites rather than only the standalone command file. The two Phase-3-native clarifications (auto-remove-on-revoked-scope behavior; master-plan deviation sign-off on execution-payload ownership) are unrelated to phase-2 verification and remain open — this plan stays `under_construction`.
- `2026-07-08` `User decision`: Resolved both remaining blockers. (1) Auto-remove-on-revoked-scope decided as **no auto-delete**: a topic that is registry-enabled and scope-covered creation-wise but whose existing remote subscription is no longer scope-covered is left in place, with the local row marked `FAILED`/`missing_required_scope`, an outcome-level event recorded, and a debug-gated safe log line — reusing the existing `ShopifyWebhookSubscriptionStatusEnum` (no new enum member, no migration) per the instruction to prefer `FAILED` since `OUTDATED` does not exist. Removal eligibility is narrowed to exactly two conditions: topic absent from the registry, or topic disabled in the registry — explicit `remove_shopify_webhooks_for_shop` calls remain the only other removal path. (2) The master-plan deviation (excluding `16_background_jobs.md`, `domain/execution/payloads/`, task types, queue mapping, worker, Redis wiring, and execution-layer handlers from this phase, all reserved for master phase 5) is **approved**. Applied both decisions to Non-goals, Scope, Resolved decisions, Acceptance criteria (added item 8, renumbered subsequent items, narrowed item 6), Implementation plan step 6, the test list, and the risk list. No blockers remain — plan moved from `under_construction` to `approved`.
- `2026-07-08` `Codex implementation`: Implemented the approved Phase 3 scope only: Shopify GraphQL request normalization, webhook subscription infra list/create/delete operations, one-shop sync/remove commands, desired-vs-installed reconciliation against `SHOPIFY_WEBHOOK_REGISTRY`, local `ShopifyWebhookSubscription` status upserts, missing-scope failure handling without remote deletion, outcome-level `ShopifyIntegrationEvent` recording, and focused unit/integration coverage. Validated with `py_compile`, new Phase 3 unit tests (`14 passed`), new Phase 3 integration tests (`7 passed`), and the impacted combined Shopify Phase 1-3 regression suite (`60 passed`).

## Lifecycle transition

- Current state: `archived`
- Next state: `parent plan / later Shopify child`
- Transition owner: `Codex`
