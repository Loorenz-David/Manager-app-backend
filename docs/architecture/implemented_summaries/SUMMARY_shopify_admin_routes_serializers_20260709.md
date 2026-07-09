# SUMMARY_shopify_admin_routes_serializers_20260709

## Metadata

- Summary ID: `SUMMARY_shopify_admin_routes_serializers_20260709`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T10:08:50Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_admin_routes_serializers_20260709.md`
- Related debug plan (optional): `none`

## What was implemented

- Added the Phase 6 Shopify admin surface on the existing router:
  - `GET /api/v1/integrations/shopify/shops`
  - `GET /api/v1/integrations/shopify/shops/{shop_integration_id}`
  - `POST /api/v1/integrations/shopify/shops/{shop_integration_id}/reauthorize-url`
  - `DELETE /api/v1/integrations/shopify/shops/{shop_integration_id}`
  - `POST /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/sync`
  - `POST /api/v1/integrations/shopify/webhooks/sync`
  - `GET /api/v1/integrations/shopify/scopes`
- Added the canonical Shopify serialization layer:
  - frozen result dataclasses in `domain/shopify/results.py`
  - pure serializer functions in `domain/shopify/serializers.py`
  - secret-free response shaping for integration, webhook-subscription, and scope-status views
- Added workspace-scoped Shopify query services:
  - list integrations with offset pagination
  - get one integration with webhook subscription summary
  - get scope status for one shop or all shops in the workspace
- Added Shopify commands for admin actions:
  - reauthorize URL generation that reuses the existing install URL command with the stored shop domain
  - soft disconnect that disables the integration, clears the token, records a `DISCONNECT` event, and enqueues webhook removal
  - manual webhook sync for one shop
  - manual webhook sync for all eligible shops in the workspace
- Added the additive Postgres enum migration for `ShopifyIntegrationEventTypeEnum.DISCONNECT`.
- Extended the Shopify router tests and added focused serializer/query/command coverage for the Phase 6 behavior.

## Files changed

- `backend/app/beyo_manager/domain/shopify/enums.py`: added `ShopifyIntegrationEventTypeEnum.DISCONNECT`.
- `backend/app/migrations/versions/ab12cd34ef56_add_disconnect_to_shopify_integration_event_type.py`: additive enum migration.
- `backend/app/beyo_manager/domain/shopify/results.py`: new frozen result dataclasses.
- `backend/app/beyo_manager/domain/shopify/serializers.py`: new serializer functions.
- `backend/app/beyo_manager/services/queries/shopify/__init__.py`: new query package initializer.
- `backend/app/beyo_manager/services/queries/shopify/list_shopify_shop_integrations.py`: list query.
- `backend/app/beyo_manager/services/queries/shopify/get_shopify_shop_integration.py`: detail query.
- `backend/app/beyo_manager/services/queries/shopify/get_shopify_scope_status.py`: scope-status query.
- `backend/app/beyo_manager/services/commands/shopify/create_shopify_reauthorize_url.py`: reauthorization command.
- `backend/app/beyo_manager/services/commands/shopify/disconnect_shopify_shop.py`: disconnect command.
- `backend/app/beyo_manager/services/commands/shopify/enqueue_shopify_webhook_sync_for_shop.py`: manual shop sync command.
- `backend/app/beyo_manager/services/commands/shopify/enqueue_shopify_webhook_sync_for_workspace.py`: manual workspace sync command.
- `backend/app/beyo_manager/routers/api_v1/shopify.py`: added the six approved admin routes.
- `backend/app/tests/unit/domain/shopify/test_serializers.py`: serializer secret-safety and derived-status tests.
- `backend/app/tests/unit/test_shopify_router.py`: expanded router role-gating coverage.
- `backend/app/tests/integration/services/queries/shopify/test_shopify_admin_queries.py`: new query integration coverage.
- `backend/app/tests/integration/services/commands/shopify/test_shopify_admin_commands.py`: new command integration coverage.

## Validation evidence

- `PYTHONPATH=. .venv/bin/py_compile ...`: passed for all changed Shopify implementation files and tests.
- `PYTHONPATH=. .venv/bin/pytest tests/unit/domain/shopify/test_serializers.py -q`: passed (`3 passed`).
- `PYTHONPATH=. .venv/bin/pytest tests/unit/test_shopify_router.py -q`: passed (`29 passed`).
- `PYTHONPATH=. .venv/bin/pytest tests/integration/services/queries/shopify/test_shopify_admin_queries.py -q`: could not complete because the local PostgreSQL connection on port `5433` was unavailable (`Connect call failed ('::1', 5433)` / `('127.0.0.1', 5433)`).

## Known gaps or deferred items

- DB-backed Shopify integration validation and `alembic upgrade head` remain blocked by the unavailable local PostgreSQL/Redis service in this session. The code paths and tests are in place, but the live database pass could not be completed here.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_admin_routes_serializers_20260709.md`
