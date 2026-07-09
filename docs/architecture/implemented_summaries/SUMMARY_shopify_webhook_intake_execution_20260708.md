# SUMMARY_shopify_webhook_intake_execution_20260708

## Metadata

- Summary ID: `SUMMARY_shopify_webhook_intake_execution_20260708`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T09:08:39Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_intake_execution_20260708.md`
- Related debug plan (optional): `none`

## What was implemented

- Added the Phase 4 Shopify webhook intake boundary:
  - `POST /api/v1/shopify/webhooks`
  - raw-body HMAC verification for Shopify webhooks
  - durable intake persistence into `shopify_webhook_intakes`
  - durable dedupe by `shop_integration_id:topic:webhook_id`
  - event-only enqueue-pending boundary via `ShopifyIntegrationEvent(event_type=WEBHOOK_RECEIVED)`
- Added supported-path behavior for active integrations (`RECEIVED`, `retryable=True`) without introducing any real queue, task type, worker, or execution handler.
- Added ignored-path behavior for unsupported topics and inactive integrations (`IGNORED`, `retryable=False`) with safe reason metadata.
- Added duplicate-delivery handling that returns success without creating a second intake row or event.
- Added focused unit and integration coverage for webhook HMAC, route reachability/auth boundary, intake outcomes, dedupe behavior, and the explicit Phase 4 no-execution-layer boundary.

## Files changed

- `backend/app/beyo_manager/services/infra/shopify/hmac_verifier.py`: added webhook HMAC verification alongside the existing OAuth callback verifier.
- `backend/app/beyo_manager/services/commands/shopify/enqueue_or_record_shopify_webhook.py`: added the single Phase 4 intake/dedupe/event-only command.
- `backend/app/beyo_manager/routers/api_v1/shopify_webhooks.py`: added the unauthenticated-by-JWT Shopify webhook route.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: registered the new webhook router under `/api/v1/shopify`.
- `backend/app/tests/unit/services/infra/shopify/test_hmac_verifier.py`: added webhook HMAC unit coverage.
- `backend/app/tests/unit/test_shopify_webhooks_router.py`: added exact-path and no-JWT/role route coverage.
- `backend/app/tests/unit/services/commands/shopify/test_webhook_intake_boundary.py`: added the no-execution-runtime source-inspection guard.
- `backend/app/tests/integration/services/commands/shopify/test_shopify_webhook_intake_integration.py`: added focused Phase 4 intake integration coverage.
- `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`: added the minimal lifecycle progress note for the completed Phase 4 child plan.

## Contract adherence

- `backend/architecture/09_routers.md`: kept the webhook route thin; it extracts raw bytes and headers, calls `run_service`, and returns fast HTTP responses.
- `backend/architecture/06_commands.md`: kept shop resolution, intake persistence, dedupe, and event recording inside one narrow Shopify command.
- `backend/architecture/18_security.md`: verified Shopify webhook HMAC on the raw body, rejected invalid signatures before DB work, and avoided logging payloads, secrets, or signatures.
- `backend/architecture/19_integrations.md`: preserved the event-only intake boundary with no Shopify API or GraphQL calls from the webhook path.
- `backend/architecture/17_logging.md`: limited logging to safe metadata only and excluded raw payloads, access tokens, client secrets, and HMAC values.

## Validation evidence

- `PYTHONPATH=app python3 -m py_compile app/beyo_manager/services/infra/shopify/hmac_verifier.py app/beyo_manager/services/commands/shopify/enqueue_or_record_shopify_webhook.py app/beyo_manager/routers/api_v1/shopify_webhooks.py app/tests/unit/services/infra/shopify/test_hmac_verifier.py app/tests/unit/test_shopify_webhooks_router.py app/tests/unit/services/commands/shopify/test_webhook_intake_boundary.py app/tests/integration/services/commands/shopify/test_shopify_webhook_intake_integration.py`: passed.
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/unit/services/infra/shopify/test_hmac_verifier.py app/tests/unit/test_shopify_webhooks_router.py app/tests/unit/services/commands/shopify/test_webhook_intake_boundary.py -q`: passed (`8 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/integration/services/commands/shopify/test_shopify_webhook_intake_integration.py -q`: passed (`10 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/app_test REDIS_URL=redis://127.0.0.1:6379/1 PYTHONPATH=app python3 -m pytest app/tests/unit/domain/shopify app/tests/unit/services/infra/shopify/test_hmac_verifier.py app/tests/unit/services/infra/shopify/test_oauth_client.py app/tests/unit/services/infra/shopify/test_graphql_client.py app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py app/tests/unit/services/commands/shopify/test_webhook_sync_boundary.py app/tests/unit/services/commands/shopify/test_webhook_intake_boundary.py app/tests/unit/test_shopify_router.py app/tests/unit/test_shopify_webhooks_router.py app/tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py app/tests/integration/services/commands/shopify/test_shopify_webhook_subscription_sync_integration.py app/tests/integration/services/commands/shopify/test_shopify_webhook_intake_integration.py app/tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: passed (`76 passed`).

## Known gaps or deferred items

- No migration was required in Phase 4.
- Real queue enqueue, execution task types, worker wiring, execution handlers, admin routes, disconnect flow, and historical import behavior remain intentionally deferred to later approved Shopify child plans.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_intake_execution_20260708.md`
