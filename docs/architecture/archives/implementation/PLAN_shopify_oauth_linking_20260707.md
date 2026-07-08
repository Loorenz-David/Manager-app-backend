# PLAN_shopify_oauth_linking_20260707

## Metadata

- Plan ID: `PLAN_shopify_oauth_linking_20260707`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T00:00:00Z`
- Last updated at (UTC): `2026-07-08T07:15:16Z`
- Related issue/ticket: `Shopify integration OAuth linking flow`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` — phase 1 is implemented, archived, and has been reviewed against this plan (see "Phase 1 implementation dependencies to verify before approval" below, filled in with confirmed facts). No blockers remain — see "Resolved decisions."

## Goal and intent

- Goal: Draft the Shopify OAuth install/callback linking flow — install URL creation, OAuth state lifecycle, HMAC/query validation, token exchange orchestration, shop integration create/update, scope recording, safe frontend redirect, and a single enqueue/boundary call site for post-link webhook sync.
- Business/user intent: Let an authorized workspace user connect a Shopify shop through a standard OAuth install/callback round trip, with the resulting offline access token stored encrypted and the integration ready for webhook sync in a later phase.
- Non-goals:
  - Webhook subscription GraphQL implementation (master phase 3).
  - Webhook HTTP intake route and webhook processing (master phase 4).
  - Dedicated Shopify worker/task-type implementation (master phase 5).
  - Admin list/detail/disconnect/webhook-sync routes beyond the minimum this flow needs (master phase 6), unless explicitly justified in this plan.
  - Frontend UI implementation.
  - Historical product/order imports.
  - Creation of remaining child implementation plans (phases 3-7 of the master plan).

## Scope

- In scope:
  - `POST /api/v1/integrations/shopify/install-url`
  - `GET /api/v1/integrations/shopify/oauth/callback`
  - OAuth state creation (`shopify_oauth_states` row: expiring, one-time, workspace/user-bound).
  - OAuth state validation and one-time consumption (state match, not expired, not already consumed).
  - Shopify OAuth query/HMAC validation on the callback request.
  - Shopify token exchange infra boundary (a single `services/infra/shopify/` module that calls Shopify's OAuth token endpoint; no other module makes this call).
  - Encrypted storage of the offline access token using the existing field encryption system (`app/beyo_manager/services/infra/crypto/field_encryption.py`, `settings.field_encryption_key`) — no new encryption key.
  - Create/update `shopify_shop_integrations` row (link or re-link a shop to a workspace).
  - Granted/requested scope recording and scope status update using the phase-1 `domain/shopify/scopes.py` helpers.
  - Safe frontend redirect after OAuth callback (status/shop_domain/error_code only; no tokens, no raw Shopify errors, allowlisted redirect target only).
  - A single enqueue/boundary call site for webhook installation/sync after successful link: `enqueue_shopify_webhook_sync_after_install` (see "Resolved decisions" — implemented as a no-op/event-recording boundary in this phase because the real Shopify sync command and dedicated worker/task types do not exist until master phases 3 and 5).
  - Tests: install URL, callback (success and failure paths), OAuth state expiry/consumption, shop linking/relinking, encryption boundary, safe redirect, no-secret logging.
- Out of scope:
  - Webhook subscription GraphQL implementation.
  - Webhook HTTP intake route.
  - Webhook processing.
  - Dedicated Shopify worker implementation.
  - Admin list/detail/disconnect routes, unless a minimal read is strictly required to support this flow (none identified so far — see Implementation plan step 8).
  - Frontend UI.
  - Historical product/order imports.
  - Remaining child plans (phases 3-7).
- Assumptions:
  - Phase 1 (`PLAN_shopify_foundation_schema_config_20260707.md`) is implemented, migrated, and archived. This plan's file/module/class/function references now reflect the **actual verified phase-1 code** (see "Phase 1 implementation dependencies to verify before approval"), not assumptions.
  - Shopify Admin API OAuth uses the standard `code` + `hmac` + `state` + `shop` query-string callback shape and the standard `client_id`/`client_secret`/`code` token exchange POST. Shopify's offline token-exchange response includes a `scope` field with the comma-separated granted scopes — no follow-up API call is needed to learn granted scopes (see Resolved decisions).
  - Offline access tokens only; no refresh token exchange or storage.
  - `install-url` is an authenticated, workspace-scoped route (JWT required). `oauth/callback` is unauthenticated by ManagerBeyo JWT (Shopify redirects the merchant's browser here) but is authenticated by Shopify's HMAC signature on the callback query string.
  - Router response bodies for this phase are plain dicts returned from commands via `outcome.data` and wrapped by `build_ok`/`build_err` (matching `routers/api_v1/auth.py` and `routers/api_v1/email_connections.py`), not a `domain/shopify/serializers.py` module — that module is explicitly deferred to master phase 6.

## Phase 1 implementation dependencies to verify before approval

Phase 1 was reviewed against the archived plan, its implemented summary, and the actual code in the repository on `2026-07-08`. Every item below is now a **confirmed fact**, not an assumption. Deviations from the original phase-1 plan wording are called out explicitly.

- [x] **Shopify model class names** — confirmed in `app/beyo_manager/models/tables/shopify/`: `ShopifyShopIntegration`, `ShopifyOAuthState` (capital "OAuth", not "Oauth" as this plan originally assumed), `ShopifyWebhookSubscription`, `ShopifyWebhookIntake`, `ShopifyIntegrationEvent`.
- [x] **Shopify model file paths** — `shopify_shop_integration.py`, `shopify_oauth_state.py`, `shopify_webhook_subscription.py`, `shopify_webhook_intake.py`, `shopify_integration_event.py`, all under `app/beyo_manager/models/tables/shopify/`. Matches this plan's original assumption exactly.
- [x] **Actual enum class and member names** — `app/beyo_manager/domain/shopify/enums.py`:
  - `ShopifyIntegrationStatusEnum`: `PENDING_INSTALL`, `ACTIVE`, `NEEDS_REAUTH`, `SCOPES_OUTDATED`, `WEBHOOKS_OUTDATED`, `DISABLED`, `UNINSTALLED`, `ERROR` (values are the matching lowercase strings). Matches the approved active-like/inactive split exactly.
  - `ShopifyOAuthStateStatusEnum` (new, not in the original field list but additive and useful): `PENDING`, `CONSUMED`, `EXPIRED` — the `shopify_oauth_states.status` column uses this; use it instead of inferring state from `consumed_at`/`expires_at` alone.
  - `ShopifyWebhookSubscriptionStatusEnum`: `PENDING`, `ACTIVE`, `FAILED`, `DISABLED`, `REMOVED`.
  - `ShopifyWebhookIntakeStatusEnum`: `RECEIVED`, `PROCESSING`, `PROCESSED`, `FAILED`, `IGNORED`.
  - `ShopifyIntegrationEventTypeEnum`: `INSTALL`, `REAUTHORIZE`, `WEBHOOK_SYNC`, `WEBHOOK_RECEIVED`, `WEBHOOK_PROCESSED`, `HEALTH_CHECK`, `ERROR`. **Deviation from the intention plan**: the intention plan listed a much more granular event-type list (`oauth_install_started`, `oauth_callback_received`, `oauth_state_validated`, `access_token_exchanged`, `shop_linked`, `shop_reauthorized`, `shop_unlinked`, etc.); phase 1 implemented a coarser set. This plan does **not** require extending the enum (see Resolved decisions) — granular step detail belongs in structured logs, and `shopify_integration_events` records only outcome-level milestones using the existing members (`INSTALL` for a new link, `REAUTHORIZE` for a re-link/re-auth, `WEBHOOK_SYNC` for the sync-pending boundary event, `ERROR` for failures).
  - `ShopifyIntegrationEventSeverityEnum`: `INFO`, `WARNING`, `ERROR`.
  - `ShopifyWebhookPayloadFormatEnum`: `JSON` only.
- [x] **Actual domain helper function names** — confirmed:
  - `app/beyo_manager/domain/shopify/shop_domains.py`: `normalize_shop_domain(raw_shop_domain: str) -> str` (raises `beyo_manager.errors.validation.ValidationError` on invalid input), `is_valid_shop_domain(raw_shop_domain: str) -> bool`.
  - `app/beyo_manager/domain/shopify/scopes.py`: `normalize_scope(scope: str) -> str`, `normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]`, `parse_scope_config(scope_config: str) -> tuple[str, ...]`, `compare_requested_and_granted_scopes(requested_scopes, granted_scopes) -> ShopifyScopeComparison` (dataclass with `.requested`, `.granted`, `.missing`, `.extra`, `.is_outdated`), `has_all_required_scopes(requested_scopes, granted_scopes) -> bool`.
- [x] **Actual webhook registry public API** — `app/beyo_manager/domain/shopify/webhook_registry.py`: `SHOPIFY_WEBHOOK_CALLBACK_PATH = "/api/v1/shopify/webhooks"`, `SHOPIFY_WEBHOOK_REGISTRY: tuple[ShopifyWebhookDefinition, ...]`, `get_webhook_definition(topic: str) -> ShopifyWebhookDefinition | None` (returns `None`, not an exception, for an unknown topic). Each `ShopifyWebhookDefinition` has `.topic`, `.callback_path`, `.required_scopes`, `.payload_format`, `.enabled`. **Deviation to note**: `SHOPIFY_WEBHOOK_CALLBACK_PATH` is `/api/v1/shopify/webhooks`, not `/api/v1/integrations/shopify/webhooks` as the intention/master plan examples suggested. This plan's own router prefix (step 6 below) is therefore aligned to `/api/v1/integrations/shopify` for the OAuth routes while flagging this mismatch for phase 3/4 to reconcile before the real webhook route is built — phase 2 does not fix it, since it owns no webhook route.
- [x] **Actual config field names** — confirmed in `app/beyo_manager/config.py` (lines 105-113, under a `# Shopify` comment): `shopify_client_id`, `shopify_client_secret`, `shopify_app_scopes`, `shopify_redirect_uri`, `shopify_api_version` (default `"2026-01"`), `shopify_webhook_base_url`, `shopify_integration_debug_logs`, `shopify_webhook_secret`. Matches this plan's original assumption exactly. None of these are in `_require_critical_settings`.
- [x] **Actual model import paths** — `app/beyo_manager/models/__init__.py` lines 134-139, under a `# --- Shopify foundation ---` comment, register all five modules (e.g. `from beyo_manager.models.tables.shopify import shopify_shop_integration  # noqa: F401`). `app/beyo_manager/models/tables/client_id_prefix_map.md` lines 38-42 confirm the exact prefix reservations (see below).
- [x] **Actual client_id prefix entries** — confirmed in `client_id_prefix_map.md`: `ShopifyIntegrationEvent -> shpevt`, `ShopifyOAuthState -> shpoau`, `ShopifyShopIntegration -> shpint`, `ShopifyWebhookIntake -> shpwhi`, `ShopifyWebhookSubscription -> shpwhs`. Matches this plan's original assumption exactly.
- [x] **Actual migration revision/head** — `677ed7131bb2_create_shopify_integration_foundation.py` (`down_revision = 'b2c4d6e8f0a1'`), applied and confirmed at head via `alembic current`. Both partial unique indexes (`uix_shopify_shop_integrations_shop_domain_active` and `uix_shopify_shop_integrations_workspace_shop_domain_active`) exist with `postgresql_where` restricted to the approved active-like status set and `is_deleted = false`, and are exercised by integration tests. **Design note (non-blocking)**: because the global `shop_domain` index alone already forbids any two active-like rows sharing a `shop_domain` regardless of workspace, the `workspace_id + shop_domain` composite index can never trigger independently of the global one — it is harmless defensive redundancy, not a gap, and this plan should not expect a test that exercises it in isolation.
- [x] **Actual test results from phase 1** — `pytest tests/unit/domain/shopify -q`: `16 passed`. `pytest tests/unit/domain/shopify tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: `22 passed`. Constraint tests cover: global active-like shop-domain uniqueness, `error` status still blocking a new link, inactive/soft-deleted rows not blocking a new link, duplicate OAuth state, duplicate subscription topic, duplicate webhook intake dedupe key.
- [x] **Implemented summary path** — `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_foundation_schema_config_20260708.md` (confirmed exists and reviewed).
- [x] **Archived phase 1 plan path** — `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` (confirmed exists, `Status: archived`, reviewed as the authoritative record).
- [x] **Other deviations found during review, carried into this plan**: the planned `shopify_webhook_subscriptions.format` column was implemented as `payload_format` (avoids shadowing the Python builtin `format`) — any later phase referencing "format" must use `payload_format`. The planned `shopify_integration_events.metadata` column is mapped through the Python attribute `metadata_json` (SQLAlchemy reserves `metadata` on declarative models) — construct `ShopifyIntegrationEvent(metadata_json=...)`, not `metadata=...`. Neither deviation affects this plan's scope beyond naming.

## Resolved decisions

These clarifications are resolved for this child plan following the Stage-1 phase-1 review and must not be re-opened during implementation.

1. **Post-link webhook sync boundary.** Resolved as option (a) from the two choices considered: `handle_shopify_oauth_callback` calls a single named command boundary, `enqueue_shopify_webhook_sync_after_install(shop_integration_id)`, defined in `services/commands/shopify/`. In this phase — since the real webhook subscription sync command (master phase 3) and the dedicated Shopify task types/worker/queue (master phase 5) do not exist yet — this command's implementation is a documented no-op that only records a `shopify_integration_events` row with `event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC`, `severity=INFO`, and a `message` stating that webhook sync is pending and will be picked up once phase 3/5 exist. It makes no Shopify API call and invents no queue/task type. **Why this option over blocking OAuth on phase 3/5**: OAuth linking is independently useful (a linked shop with no webhooks yet is still a valid, visible state — `webhooks_outdated`-style follow-up is expected), blocking phase 2 entirely on unbuilt phase 3/5 infrastructure would stall the whole integration for no safety benefit, and a single named call site means phase 3/5 replaces exactly one function body later instead of touching the OAuth callback again. This is logged per the master plan's drift-prevention rules as a **Master-plan deviation requested**: master plan phase 2 describes this as "enqueue of webhook sync after successful link" — this plan implements the named boundary call site now and defers the actual enqueue/execution to phase 5, which the master plan should reflect if/when it is next updated.
2. **Frontend redirect allowlist config.** Resolved: add one new config field, `shopify_oauth_redirect_url: str | None = Field(default=None, alias="SHOPIFY_OAUTH_REDIRECT_URL")`, to the existing `Settings` class (not added to `_require_critical_settings`), representing the single frontend "Shopify integration result" page the intention plan describes. `handle_shopify_oauth_callback` redirects here with `success`, `shop_domain`, and `error_code` (if any) appended as query parameters — never a request-supplied URL. The existing `shopify_oauth_states.redirect_after_success` column (already present from phase 1, currently unused) is treated as a bounded, validated key for a future multi-destination allowlist (per the intention plan's "optional redirect_after_success key or enum, not arbitrary URL"); this phase validates it against a single allowed value (`"default"`, mapping to `settings.shopify_oauth_redirect_url`) and rejects anything else — it does not implement a multi-entry allowlist yet, since only one destination is needed for phase 2's scope.
3. **Scope comparison inputs at callback time.** Resolved: Shopify's offline access-token exchange response includes a `scope` field containing the comma-separated granted scopes. `handle_shopify_oauth_callback` parses it with `parse_scope_config`/`normalize_scopes` and passes the result directly to `compare_requested_and_granted_scopes` alongside the `requested_scopes` recorded on the OAuth state row — no follow-up Shopify API call is needed to learn granted scopes.
4. **Role/permission names for linking.** Resolved by explicit product/policy decision:
   - `POST /api/v1/integrations/shopify/install-url` is allowed for `ADMIN` and `MANAGER` only (`require_roles(ADMIN, MANAGER)`).
   - `WORKER` is not allowed to call `install-url`.
   - `SELLER` is not allowed to call `install-url` in this phase (the intention plan's "manager may view linked shops" is a read/list concern for master phase 6, not a write permission for this phase).
   - `GET /api/v1/integrations/shopify/oauth/callback` does not require ManagerBeyo JWT authentication, because Shopify redirects the merchant's browser directly to this route with no ManagerBeyo session context available. It is secured instead by (a) Shopify OAuth HMAC signature validation over the raw callback query string, and (b) one-time `shopify_oauth_states` validation (matching, non-expired, not-yet-consumed `state`).
   - The callback must recover `workspace_id` and `user_id` from the stored `shopify_oauth_states` row located by the validated `state` value — never from callback query parameters, headers, or any other caller-supplied input. The `install-url` command is the only place that writes `workspace_id`/`user_id` onto the state row, under an authenticated JWT identity; the callback only ever reads them back.
   - This closes the only remaining blocker. This plan is approved.

## Acceptance criteria

1. `POST /install-url` accepts a shop domain input, normalizes it via the phase-1 `shop_domains` helper, rejects invalid domains, creates a `shopify_oauth_states` row (expiring, one-time, bound to `workspace_id` and `user_id`), and returns an authorization URL built from `settings.shopify_client_id`, `settings.shopify_app_scopes`, `settings.shopify_redirect_uri`, and the created `state`.
2. `GET /oauth/callback` validates the Shopify HMAC over the raw callback query string before trusting any other query parameter.
3. The callback validates the `state` parameter against a matching, non-expired, not-yet-consumed `shopify_oauth_states` row, and consumes it (sets `consumed_at`) exactly once — a replayed callback with the same `state` is rejected.
4. On successful validation, the callback exchanges the authorization code for an offline access token through a single infra boundary module, encrypts the token with the existing field encryption system before persisting it, and never logs the raw token.
5. The callback creates a new `shopify_shop_integrations` row or updates the existing one for that normalized `shop_domain` + `workspace_id`, respecting the phase-1 partial unique constraints (an active-like integration for that shop domain must not already exist in a different workspace).
6. `granted_scopes` and `requested_scopes` are recorded, and scope status (e.g. `scopes_outdated` / `needs_reauth`) is set using the phase-1 scope comparison helpers — not ad hoc string comparison in the command.
7. The callback redirects the browser to `settings.shopify_oauth_redirect_url` with only safe status fields (`success`, `shop_domain`, `error_code` if applicable) appended as query parameters — no access token, no raw Shopify error, no OAuth code, no internal state value, and never a request-supplied redirect target.
8. Exactly one call site exists for the post-link webhook-sync boundary (`enqueue_shopify_webhook_sync_after_install`); no command in this phase calls a Shopify webhook subscription API directly, and no queue/task type is invented.
9. All Shopify OAuth flow logging is gated by `settings.shopify_integration_debug_logs` where appropriate and never includes token, client secret, raw OAuth code, or raw HMAC values.
10. This phase adds no webhook HTTP intake route, no webhook subscription GraphQL calls, no worker/task-type code, and no frontend code.
11. `shopify_oauth_states.redirect_after_success`, if supplied on `install-url`, is validated against a single allowed value (`"default"`); any other value is rejected as a validation error rather than trusted as a URL.
12. `POST /install-url` is reachable only by `ADMIN` and `MANAGER`; a `WORKER` or `SELLER` JWT is rejected with a permission error before any command logic runs.
13. `handle_shopify_oauth_callback` obtains `workspace_id` and `user_id` exclusively by reading them off the `shopify_oauth_states` row matched by `state`; no code path in the callback reads workspace/user identity from query parameters, headers, or any other request-supplied input.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: Routers stay I/O only; OAuth business logic lives in commands; token exchange lives in infra.
- `architecture/04_context.md`: `ServiceContext` identity/session boundaries for the install-url command (authenticated) and the callback command (unauthenticated by JWT, but still session-scoped).
- `architecture/05_errors.md`: Safe domain errors for invalid shop domain, invalid/expired/consumed OAuth state, invalid HMAC, token exchange failure, shop already linked elsewhere.
- `architecture/06_commands.md`: Write-operation structure for `create_shopify_install_url`, `handle_shopify_oauth_callback`, `link_or_update_shopify_shop`, `enqueue_shopify_webhook_sync_after_install`.
- `architecture/06_commands_local.md`: `maybe_begin` usage if the callback command becomes composable across sub-steps (state consumption + shop upsert + event recording).
- `architecture/09_routers.md`: Router boundaries; `oauth/callback` must stay a thin, unauthenticated-by-JWT route that only calls one command and issues a redirect response.
- `architecture/08_domain.md`: Reuse (not reimplement) phase-1 `domain/shopify/` pure helpers; no new business rules embedded in commands that belong in domain.
- `architecture/10_auth.md`: JWT dependency usage for `install-url`; explicit justification for why `oauth/callback` is exempt from JWT auth and relies on Shopify HMAC instead.
- `architecture/17_logging.md`: Module logger usage, required context fields (workspace_id, shop domain, operation, status), forbidden secrets.
- `architecture/18_security.md`: HMAC verification, one-time expiring state, redirect allowlisting, IDOR prevention (state must be bound to the requesting workspace/user).
- `architecture/19_integrations.md`: External adapter pattern for the Shopify OAuth/token-exchange infra client; timeout handling; error normalization via `ExternalServiceError`.
- `architecture/21_naming_conventions.md`: Route, command, query, env var, and file naming for this phase.
- `architecture/24_multi_tenancy.md`: `install-url` and the resulting integration are workspace-scoped; state is bound to `workspace_id`.
- `architecture/25_soft_delete.md`: Re-linking behavior must respect `is_deleted`/status semantics from phase 1 rather than hard-deleting/recreating rows.
- `architecture/28_roles_permissions.md`: `install-url` is restricted to `ADMIN`/`MANAGER` (resolved — see Resolved decisions item 4).
- `architecture/40_identity.md`: `client_id` identity usage for the OAuth state and shop integration rows created/updated in this phase.
- `architecture/42_event.md`: Recording OAuth/link lifecycle events into `shopify_integration_events`.
- `architecture/46_serialization.md`: Confirms this phase returns plain command-outcome dicts, not a deferred `domain/shopify/serializers.py`.
- `architecture/15_testing.md`: Test tier placement for command tests (mocked Shopify infra), route tests, and redirect-safety tests.

### Local extensions loaded

- `architecture/40_identity_local.md`: No new prefixes needed in this phase; reuses phase-1 `shpint`/`shpoau` prefixes.
- `architecture/46_serialization_local.md`: No Shopify-specific local delta.
- `architecture/07_queries_local.md`: Not loaded — this phase adds no list/detail queries beyond what a command needs internally to look up an existing integration by shop domain.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape -> `06_commands.md`
- Reading another router to understand handler wiring -> `09_routers.md`
- Reading another serializer to understand output shape -> `46_serialization.md`

Permitted for this child:
- `app/beyo_manager/domain/shopify/` (all phase-1 files) — required to confirm actual names per "Phase 1 implementation dependencies to verify before approval."
- `app/beyo_manager/models/tables/shopify/` and `app/beyo_manager/models/__init__.py` — required to confirm actual model/class/prefix names.
- `app/beyo_manager/config.py` — for existing settings structure and to place new OAuth-specific fields correctly.
- `app/beyo_manager/services/infra/crypto/field_encryption.py` — existing encryption boundary this phase must call.
- `app/beyo_manager/services/infra/email_providers/` — read only as a relational example of an existing `services/infra/<domain>/` external-client module layout, not copied verbatim.
- `app/beyo_manager/routers/api_v1/auth.py`, `routers/api_v1/email_connections.py`, `routers/api_v1/bootstrap.py` — read only to confirm existing response-wrapping (`build_ok`/`build_err`), unauthenticated-route, and rate-limit patterns already in use.
- `app/beyo_manager/routers/utils/roles.py`, `routers/utils/jwt_dep.py`, `routers/utils/rate_limit.py` — for exact role constants and auth/rate-limit dependency names.
- `app/beyo_manager/services/context.py`, `services/run_service.py` — for `ServiceContext`/`run_service` exact shape.
- `app/beyo_manager/errors/external_service.py`, `errors/base.py` — for exact error base classes to raise from the infra token-exchange boundary.
- No migration file reads are needed for this phase — the redirect config addition is config-only and adds no schema.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `07_queries.md`, `07_queries_local.md`: No list/detail query surface is added in this phase.
- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`: Real task types/queue/worker belong to master phase 5; this phase only defines the boundary call site (see Resolved decisions item 1).
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: Deployment child (master phase 7), not this phase.
- `13_sockets.md`, `56_realtime_layer.md`: No realtime behavior in the OAuth flow.
- `34_file_storage.md`: Not relevant to OAuth linking.
- `30_migrations.md`: Not needed — the new `shopify_oauth_redirect_url` field is config-only (no schema change), and `redirect_after_success` validation is a domain-level check against the existing phase-1 column.

## Implementation plan

1. Phase 1 verification is complete (see "Phase 1 implementation dependencies to verify before approval" — all items confirmed against the archived plan, implemented summary, and actual code as of `2026-07-08`).

2. All clarifications are resolved (see "Resolved decisions") — no open blockers remain.

3. Add one OAuth-specific config field to the existing `Settings` class in `app/beyo_manager/config.py`, under the existing `# Shopify` comment block (do not create a second comment block):
   - `shopify_oauth_redirect_url: str | None = Field(default=None, alias="SHOPIFY_OAUTH_REDIRECT_URL")`.
   - Do not duplicate or rename any phase-1 field.
   - Do not add this to `_require_critical_settings`.

4. Add `services/infra/shopify/` boundary module(s):
   - A single module (e.g. `oauth_client.py`) responsible for building the Shopify authorization URL (using `settings.shopify_client_id`, `settings.shopify_app_scopes`, `settings.shopify_redirect_uri`) and performing the token-exchange HTTP call, parsing the response's `access_token` and `scope` fields.
   - A single module (e.g. `hmac_verifier.py` or a shared function) responsible for verifying the Shopify OAuth callback HMAC using `settings.shopify_client_secret`.
   - Normalize infra failures into `ExternalServiceError` (`app/beyo_manager/errors/external_service.py`) — no raw `httpx`/`requests` exceptions leak past this boundary.
   - No GraphQL client work here (that belongs to later phases); this is OAuth/token-exchange only.

5. Add `services/commands/shopify/` modules:
   - `create_shopify_install_url.py`: normalizes the shop domain via `normalize_shop_domain` (`domain/shopify/shop_domains.py`), validates `redirect_after_success` is `"default"` if supplied (reject otherwise), creates a `ShopifyOAuthState` row (status `ShopifyOAuthStateStatusEnum.PENDING`), returns the authorization URL + state metadata.
   - `handle_shopify_oauth_callback.py`: verifies HMAC, loads and validates the `ShopifyOAuthState` row (`status == PENDING`, `expires_at` in the future), marks it `ShopifyOAuthStateStatusEnum.CONSUMED` with `consumed_at` set, calls the infra token-exchange boundary, calls `link_or_update_shopify_shop`, calls `enqueue_shopify_webhook_sync_after_install`, returns the safe redirect target/status built from `settings.shopify_oauth_redirect_url`. **Identity recovery**: `workspace_id` and `user_id` passed to `link_or_update_shopify_shop` and to event recording come exclusively from the loaded `ShopifyOAuthState` row's `workspace_id`/`user_id` columns (written by the authenticated `install-url` call). The callback command must not accept or trust a `workspace_id`/`user_id` from its own inputs (no such query params exist on the callback route, and none should be added).
   - `link_or_update_shopify_shop.py`: creates or updates the `ShopifyShopIntegration` row (encrypts the token via `field_encryption.encrypt_field`, records `granted_scopes`/`requested_scopes` as JSONB lists via `normalize_scopes`, computes scope status via `compare_requested_and_granted_scopes`, sets `status` to `ShopifyIntegrationStatusEnum.ACTIVE` or `NEEDS_REAUTH`/`SCOPES_OUTDATED` based on `ShopifyScopeComparison.is_outdated`), respecting the phase-1 partial unique constraints and raising a domain error if the shop is already active-like in a different workspace.
   - `enqueue_shopify_webhook_sync_after_install.py`: the resolved no-op/event-recording boundary — records a `ShopifyIntegrationEvent(event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC, severity=ShopifyIntegrationEventSeverityEnum.INFO, message="Webhook sync pending; will be processed once webhook subscription sync (phase 3) and the dedicated worker (phase 5) exist.", metadata_json=...)`. This is the single function phase 3/5 replaces later.
   - Record `ShopifyIntegrationEvent` rows at outcome-level milestones only (new link -> `INSTALL`; re-link/re-auth -> `REAUTHORIZE`; failures -> `ERROR`), using `metadata_json`, not `metadata`, as the constructor kwarg. Record granular step detail (state validated, token exchanged, etc.) via structured logs gated by `settings.shopify_integration_debug_logs`, not as separate event rows — the event-type enum is intentionally coarse (see "Phase 1 implementation dependencies to verify before approval").

6. Add the router `routers/api_v1/shopify.py` (confirm this single-file naming is still appropriate at implementation time against `21_naming_conventions.md`; later phases may split by concern):
   - `POST /install-url`: JWT-authenticated, `require_roles(ADMIN, MANAGER)` (resolved policy — `WORKER` and `SELLER` are rejected), calls `create_shopify_install_url` via `run_service`, returns `build_ok(outcome.data)`.
   - `GET /oauth/callback`: unauthenticated by JWT (no `require_roles`/`get_jwt_claims` dependency at all — Shopify's redirect carries no ManagerBeyo session), calls `handle_shopify_oauth_callback` via `run_service`, and issues an HTTP redirect (not a JSON body) to `settings.shopify_oauth_redirect_url` with only safe status fields appended as query params. Security for this route is HMAC + one-time OAuth state validation inside the command, not router-level auth (see Resolved decisions item 4).
   - Register the router in `routers/api_v1/__init__.py` under `/api/v1/integrations/shopify`. Note the resulting webhook path this implies (`/api/v1/integrations/shopify/webhooks`) does not match the phase-1 `SHOPIFY_WEBHOOK_CALLBACK_PATH` constant (`/api/v1/shopify/webhooks`) — this phase does not own the webhook route and does not fix the constant, but phase 3/4 must reconcile the two before the real webhook route is built.

7. Confirm whether any read is strictly required to support this flow (e.g. checking for an existing active-like integration before creating OAuth state, to fail fast with a clear error instead of failing later at the unique-constraint level). If needed, add the minimal such lookup inside the relevant command rather than a standalone query module, unless `07_queries.md` conventions require otherwise — decide and document at implementation time, not by adding admin list/detail routes.

8. Tests:
   - `create_shopify_install_url`: valid/invalid shop domain, state row created with correct expiry/binding.
   - `handle_shopify_oauth_callback`: valid flow end-to-end (mocked Shopify infra); invalid HMAC rejected; expired state rejected; already-consumed state rejected (replay); state bound to a different workspace/user rejected.
   - `link_or_update_shopify_shop`: creates new row; updates existing row for same shop+workspace; rejects linking a shop domain that is active-like in a different workspace.
   - Encryption boundary: stored `access_token_encrypted` is not plaintext; round-trips correctly through `field_encryption`.
   - Redirect safety: redirect URL never contains token/code/state/raw error; only allowlisted target host(s) are used.
   - Logging: no test asserts on log content containing secrets (negative assertion) for the full callback flow.
   - Role gating: `install-url` succeeds for `ADMIN` and `MANAGER`; rejected with a permission error for `WORKER` and `SELLER`.
   - Identity recovery: `handle_shopify_oauth_callback` derives `workspace_id`/`user_id` only from the matched `ShopifyOAuthState` row; a test asserts the command signature/flow accepts no workspace/user identity from the callback's own inputs.

## Risks and mitigations

- Risk: The coarse `ShopifyIntegrationEventTypeEnum` (no distinct `oauth_state_validated`/`access_token_exchanged`-style members) makes it harder to reconstruct a precise OAuth timeline from the events table alone.
  Mitigation: Pair outcome-level event rows (`INSTALL`/`REAUTHORIZE`/`ERROR`) with structured, debug-gated logs for the intermediate steps, per Implementation plan step 5; revisit enum granularity only if real operational debugging proves it insufficient.
- Risk: The post-link webhook-sync boundary is implemented as a silent no-op and the gap is forgotten, so shops never get webhooks installed once phases 3/5 land.
  Mitigation: `enqueue_shopify_webhook_sync_after_install` always records a `WEBHOOK_SYNC` event row, making the pending state visible in the audit trail and testable, not a bare `pass`.
- Risk: `oauth/callback` becomes a place where business logic accumulates because it is public and "special."
  Mitigation: Keep the router to HMAC/redirect glue only; all logic lives in `handle_shopify_oauth_callback` and the commands/infra it calls.
- Risk: Redirect target becomes an open redirect if the allowlist config is misconfigured or missing.
  Mitigation: Redirect target must come from backend config/allowlist only, never from a request-supplied URL.
- Risk: Token or HMAC values leak into logs or error messages during debugging.
  Mitigation: Structured logging contract (`17_logging.md`) plus explicit negative logging tests.
- Risk: Two overlapping OAuth attempts for the same shop domain race and both succeed, violating the phase-1 partial unique constraint only at the DB layer with a confusing error.
  Mitigation: `link_or_update_shopify_shop` should perform a pre-check read plus rely on the DB constraint as the authoritative guard, and translate a constraint violation into a clear domain error.

## Validation plan

- Phase 1 verification checklist (this plan's own dependency section) passes before implementation starts.
- `pytest tests/unit/services/commands/shopify/`: command tests pass with mocked Shopify infra.
- `pytest tests/unit/services/infra/shopify/` (if infra unit tests are added): HMAC verification and token-exchange error normalization pass.
- Route-level test hitting `POST /install-url` and `GET /oauth/callback` against a test client with a mocked Shopify infra boundary.
- Manual/documented check: confirm no secret appears in captured logs during a full mocked OAuth flow test run.

## Review log

- `2026-07-08` `Codex`: Drafted second child implementation plan (Shopify OAuth linking) as a companion to phase 1, which is still under implementation. Left in `under_construction` pending phase-1 verification and open clarifications.
- `2026-07-08` `User/GPT review, Stage 1`: Reviewed the archived phase-1 plan, its implemented summary, and the actual code (`domain/shopify/`, `models/tables/shopify/`, `config.py`, `models/__init__.py`, `client_id_prefix_map.md`, migration `677ed7131bb2`, and both test suites). Verdict: **approved with minor follow-up** — no critical issues; contract adherence, scope boundaries, active-like/inactive status handling, JSONB storage types, and prefix reservations all match the approved phase-1 plan. Non-blocking notes carried into this plan: `ShopifyIntegrationEventTypeEnum` is coarser than the intention plan's example list; `ShopifyWebhookSubscriptionStatusEnum` has no `outdated` member (a phase-3 concern); `SHOPIFY_WEBHOOK_CALLBACK_PATH` (`/api/v1/shopify/webhooks`) does not match the intention/master plan's suggested `/api/v1/integrations/shopify/webhooks` prefix (a phase-3/4 concern); `format` was implemented as `payload_format` and `metadata` as `metadata_json` for reserved-word reasons.
- `2026-07-08` `User/GPT review, Stage 2`: Replaced all assumed phase-1 names in "Phase 1 implementation dependencies to verify before approval" with confirmed facts. Resolved three of four open clarifications (post-link webhook-sync boundary as a named no-op/event-recording command; frontend redirect allowlist as a single new `shopify_oauth_redirect_url` config field plus a validated `redirect_after_success` key; scope data confirmed available directly from the Shopify token-exchange response). Updated Implementation plan steps 3, 5, and 6 to reference actual class/enum/function names instead of assumptions. Left the exact role/permission names for `install-url` open as the sole remaining blocker — this is a policy decision, not an implementation fact, and is not resolved unilaterally. Plan remains `under_construction`.
- `2026-07-08` `User decision`: Confirmed the role/permission policy for `install-url` (`ADMIN`/`MANAGER` allowed; `WORKER` and `SELLER` rejected) and the `oauth/callback` security model (no ManagerBeyo JWT — HMAC + one-time OAuth state validation instead, with `workspace_id`/`user_id` recovered solely from the stored `shopify_oauth_states` row, never from callback query parameters). Applied to Resolved decisions, Acceptance criteria, Contracts, Implementation plan steps 5-6, and the test list. No blockers remain — plan moved from `under_construction` to `approved`.
- `2026-07-08` `Codex implementation`: Implemented the approved Phase 2 scope only: install URL route/command, OAuth callback route/command, OAuth state lifecycle, callback HMAC validation, token-exchange infra boundary, encrypted offline token persistence, Shopify shop link/relink upsert, scope recording/status update, safe frontend redirect builder, and the `enqueue_shopify_webhook_sync_after_install` no-op event-recording boundary. Validated with focused Shopify infra/router/integration tests plus the existing Phase 1 Shopify suites (`39 passed`) and `py_compile` for all new Shopify Phase 2 modules.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `Codex`
