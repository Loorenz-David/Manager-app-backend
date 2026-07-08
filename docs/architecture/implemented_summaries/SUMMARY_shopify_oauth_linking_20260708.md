# SUMMARY_shopify_oauth_linking_20260708

## Metadata

- Summary ID: `SUMMARY_shopify_oauth_linking_20260708`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T07:15:16Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md`
- Related debug plan (optional): `none`

## What was implemented

- Added the Phase 2 Shopify OAuth linking backend flow:
  - `POST /api/v1/integrations/shopify/install-url`
  - `GET /api/v1/integrations/shopify/oauth/callback`
- Added OAuth state creation, validation, and one-time consumption using the existing `ShopifyOAuthState` model.
- Added Shopify OAuth callback HMAC verification and a single Shopify OAuth token-exchange infra boundary.
- Added encrypted offline token persistence using the existing `FIELD_ENCRYPTION_KEY` / `field_encryption` helpers.
- Added Shopify shop link/relink upsert logic, requested/granted scope recording, and scope-status calculation using the existing Shopify scope helpers.
- Added a safe frontend redirect builder that only emits `success`, `shop_domain`, and `error_code`.
- Added the required `enqueue_shopify_webhook_sync_after_install` no-op boundary that records a `WEBHOOK_SYNC` integration event and does not enqueue real worker/task/webhook work.
- Added focused unit, router, infra, and integration tests for the approved OAuth-linking scope.

## Files changed

- `backend/app/beyo_manager/config.py`: added `shopify_oauth_redirect_url`.
- `backend/app/beyo_manager/services/infra/shopify/`: added OAuth HMAC verification and token-exchange infra modules.
- `backend/app/beyo_manager/services/commands/shopify/`: added install-url, callback, linking, webhook-sync boundary, and internal helper modules.
- `backend/app/beyo_manager/routers/api_v1/shopify.py`: added the Shopify OAuth routes.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: registered the Shopify router under `/api/v1/integrations/shopify`.
- `backend/app/tests/unit/services/infra/shopify/`: added focused infra tests.
- `backend/app/tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py`: added focused command/integration coverage.
- `backend/app/tests/unit/test_shopify_router.py`: added route and permission coverage.
- `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`: added the minimal lifecycle progress note for the completed Phase 2 child plan.

## Contract adherence

- `backend/architecture/06_commands.md` + `06_commands_local.md`: kept write orchestration in Shopify commands and used `maybe_begin` where callback/linking composition required nested-safe transaction handling.
- `backend/architecture/09_routers.md`: kept the Shopify router thin; it only builds `ServiceContext`, calls `run_service`, and returns JSON/redirect responses.
- `backend/architecture/18_security.md`: validated OAuth input at the command boundary, enforced HMAC verification before trusting callback values, used one-time OAuth state validation, and avoided open redirects and secret leakage.
- `backend/architecture/19_integrations.md`: centralized Shopify OAuth token exchange inside `services/infra/shopify/oauth_client.py`.
- `backend/architecture/24_multi_tenancy.md`: callback identity is recovered only from the stored `shopify_oauth_states` row, and link/upsert logic keeps workspace ownership intact while preserving the existing global active-shop uniqueness rule.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. .venv/bin/python -m pytest tests/unit/domain/shopify -q`: passed (`16 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. .venv/bin/python -m pytest tests/unit/services/infra/shopify/test_hmac_verifier.py tests/unit/services/infra/shopify/test_oauth_client.py tests/unit/test_shopify_router.py tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py tests/unit/domain/shopify tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: passed (`39 passed`).
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. .venv/bin/python -m py_compile beyo_manager/services/infra/shopify/hmac_verifier.py beyo_manager/services/infra/shopify/oauth_client.py beyo_manager/services/commands/shopify/_callback_errors.py beyo_manager/services/commands/shopify/_redirect.py beyo_manager/services/commands/shopify/_events.py beyo_manager/services/commands/shopify/_linking.py beyo_manager/services/commands/shopify/_webhook_sync.py beyo_manager/services/commands/shopify/create_shopify_install_url.py beyo_manager/services/commands/shopify/link_or_update_shopify_shop.py beyo_manager/services/commands/shopify/enqueue_shopify_webhook_sync_after_install.py beyo_manager/services/commands/shopify/handle_shopify_oauth_callback.py beyo_manager/routers/api_v1/shopify.py tests/unit/services/infra/shopify/test_hmac_verifier.py tests/unit/services/infra/shopify/test_oauth_client.py tests/unit/test_shopify_router.py tests/integration/services/commands/shopify/test_shopify_oauth_linking_integration.py`: passed.

## Known gaps or deferred items

- No migration was required in Phase 2; the only new setting is config-only.
- Real webhook subscription sync, webhook intake processing, Shopify worker/task wiring, admin list/detail/disconnect routes, and historical imports remain intentionally deferred to later approved child plans.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md`
