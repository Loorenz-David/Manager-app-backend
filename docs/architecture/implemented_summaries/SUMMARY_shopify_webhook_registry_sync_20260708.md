# SUMMARY_shopify_webhook_registry_sync_20260708

## Metadata

- Summary ID: `SUMMARY_shopify_webhook_registry_sync_20260708`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T07:49:42Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md`
- Related debug plan (optional): `none`

## What was implemented

- Added a Shopify Admin GraphQL boundary under `services/infra/shopify/` that builds versioned GraphQL endpoints from normalized shop domains, decrypts Shopify access tokens only at outbound call time, enforces explicit timeouts, logs safe request metadata, and normalizes retryable vs. non-retryable Shopify failures.
- Added a Shopify webhook subscription infra client for listing, creating, and deleting remote Shopify webhook subscriptions without leaking raw GraphQL payloads into command code.
- Added the Phase 3 reconciliation commands:
  - `sync_shopify_webhook_subscriptions_for_shop`
  - `remove_shopify_webhooks_for_shop`
- Implemented desired-vs-installed reconciliation against `domain/shopify/webhook_registry.py`, including:
  - create missing subscriptions for enabled, scope-covered topics
  - mark missing-scope topics as local `FAILED` with `last_error_code="missing_required_scope"`
  - preserve existing remote subscriptions when scopes are missing
  - remove only safe backend-owned subscriptions for registry-absent topics
  - idempotent local `shopify_webhook_subscriptions` updates and outcome-level `ShopifyIntegrationEvent` recording
- Added focused unit and integration tests for GraphQL error classification, webhook subscription client mapping, Phase 2 event-only boundary protection, and Phase 3 sync/remove behavior.

## Files changed

- `backend/app/beyo_manager/errors/external_service.py`: added Shopify GraphQL error subclasses with retryability classification.
- `backend/app/beyo_manager/services/infra/shopify/graphql_client.py`: added the Shopify Admin GraphQL request boundary.
- `backend/app/beyo_manager/services/infra/shopify/webhook_subscription_client.py`: added list/create/delete Shopify webhook subscription operations.
- `backend/app/beyo_manager/services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py`: added one-shop webhook reconciliation.
- `backend/app/beyo_manager/services/commands/shopify/remove_shopify_webhooks_for_shop.py`: added one-shop backend-owned webhook removal.
- `backend/app/tests/unit/services/infra/shopify/test_graphql_client.py`: added GraphQL boundary tests.
- `backend/app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py`: added webhook subscription client tests.
- `backend/app/tests/unit/services/commands/shopify/test_webhook_sync_boundary.py`: added the Phase 2 event-only boundary guard.
- `backend/app/tests/integration/services/commands/shopify/test_shopify_webhook_subscription_sync_integration.py`: added Phase 3 sync/remove integration coverage.
- `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`: added the minimal lifecycle progress note for the completed Phase 3 child plan.

## Contract adherence

- `backend/architecture/19_integrations.md`: centralized Shopify GraphQL and webhook subscription calls inside `services/infra/shopify/` with explicit timeout and mapping boundaries.
- `backend/architecture/06_commands.md`: kept reconciliation and removal logic inside narrow command modules with local request parsing and DB ownership.
- `backend/architecture/17_logging.md`: logged only safe metadata (`shop_domain`, `operation`, `latency`, topic names, missing scopes when debug-gated) and excluded tokens and raw provider bodies.
- `backend/architecture/05_errors.md`: normalized Shopify provider failures into explicit domain-safe `ExternalServiceError` subclasses instead of leaking `httpx` exceptions.
- `backend/architecture/15_testing.md`: added focused unit and integration coverage aligned to the new infra and command surfaces, while rerunning the existing impacted Shopify suites.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m py_compile app/beyo_manager/errors/external_service.py app/beyo_manager/services/infra/shopify/graphql_client.py app/beyo_manager/services/infra/shopify/webhook_subscription_client.py app/beyo_manager/services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py app/beyo_manager/services/commands/shopify/remove_shopify_webhooks_for_shop.py app/tests/unit/services/infra/shopify/test_graphql_client.py app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py app/tests/unit/services/commands/shopify/test_webhook_sync_boundary.py app/tests/integration/services/commands/shopify/test_shopify_webhook_subscription_sync_integration.py`: passed.
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/unit/services/infra/shopify/test_graphql_client.py app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py app/tests/unit/services/commands/shopify/test_webhook_sync_boundary.py -q`: passed (`14 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/integration/services/commands/shopify/test_shopify_webhook_subscription_sync_integration.py -q`: passed (`7 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/unit/domain/shopify app/tests/unit/services/infra/shopify/test_hmac_verifier.py app/tests/unit/services/infra/shopify/test_oauth_client.py app/tests/unit/services/infra/shopify/test_graphql_client.py app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py app/tests/unit/services/commands/shopify/test_webhook_sync_boundary.py app/tests/unit/test_shopify_router.py app/tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py app/tests/integration/services/commands/shopify/test_shopify_webhook_subscription_sync_integration.py app/tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: passed (`60 passed`).

## Known gaps or deferred items

- No migration was required in Phase 3.
- Webhook HTTP intake, HMAC intake verification, webhook processing, Shopify execution task types, queue/worker wiring, admin routes, and frontend UI remain intentionally deferred to later approved Shopify child plans.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md`
