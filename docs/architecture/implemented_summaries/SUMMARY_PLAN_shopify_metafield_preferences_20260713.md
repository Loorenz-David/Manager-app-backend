# SUMMARY_PLAN_shopify_metafield_preferences_20260713

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_metafield_preferences_20260713`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T09:05:27Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_20260713.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_shopify_metafield_preferences_20260713.md`

## What was implemented

- Added `shopify_metafield_preferences` with workspace, item category, Shopify integration, definition ID, sequence, enabled, audit, soft-delete, lookup indexes, and a shop-scoped partial unique index.
- Added the Alembic revision `b4c5d6e7f8a9_create_shopify_metafield_preferences.py`.
- Added pure metafield preference normalization/merge helpers and result dataclasses/serializers, including the grouped `shops[]` response.
- Added a single-shop Shopify GraphQL client for definition lookup, batched lookup, and paginated product-definition name search. Multi-shop credential/domain orchestration remains in the command/query services.
- Added atomic batch creation with per-selection shop validation, workspace/active-integration checks, idempotent restore/re-enable/sequence updates, and request-order-preserving results.
- Added the multi-shop category query and independent per-shop search flow, with per-shop result limits, stale-definition reporting, requested-shop ordering, and all-or-nothing Shopify failures.
- Added `POST /api/v1/integrations/shopify/metafield-preferences` and `GET /api/v1/integrations/shopify/metafield-preferences` for all existing Shopify roles.
- Updated the frontend handoff and intention-plan lifecycle linkage.

## Files added or updated

- `app/beyo_manager/models/tables/shopify/shopify_metafield_preference.py`
- `app/beyo_manager/models/__init__.py`
- `app/migrations/versions/b4c5d6e7f8a9_create_shopify_metafield_preferences.py`
- `app/beyo_manager/domain/shopify/metafield_preferences.py`
- `app/beyo_manager/domain/shopify/results.py`
- `app/beyo_manager/domain/shopify/serializers.py`
- `app/beyo_manager/services/infra/shopify/metafield_definition_client.py`
- `app/beyo_manager/services/commands/shopify/requests/create_shopify_metafield_preferences_request.py`
- `app/beyo_manager/services/commands/shopify/create_shopify_metafield_preferences.py`
- `app/beyo_manager/services/queries/shopify/get_shopify_metafield_preferences.py`
- `app/beyo_manager/routers/api_v1/shopify.py`
- Focused unit tests under `app/tests/unit/` for normalization, request validation, Shopify GraphQL shape/pagination, and routes.

## Validation evidence

- `PYTHONPATH=. pytest tests/unit/domain/shopify tests/unit/services/infra/shopify tests/unit/services/shopify/test_metafield_preference_routes.py tests/unit/services/commands/shopify/test_create_shopify_metafield_preferences_request.py -q`: passed, 88 tests.
- `ruff check` on all changed Python files: passed.
- `PYTHONPATH=. python3 -m compileall -q beyo_manager migrations tests`: passed.
- `PYTHONPATH=. alembic heads`: passed; new head is `b4c5d6e7f8a9`.
- `alembic current`, `alembic upgrade head`, and database-backed integration tests were not run to completion because the local PostgreSQL connection was unavailable/blocked in this environment.

## Defaults and follow-ups

- The plan's defaults were retained: no `ShopifyIntegrationEvent` is emitted for preference saves, and combined category/search results remain independent sections per shop.
- A live development-store schema check for `MetafieldOwnerType.PRODUCT`, real cross-shop GID behavior, and applying/rolling back the migration remain follow-up validation items requiring database/Shopify credentials.

## Post-implementation migration correction

The first upgrade attempt exposed a PostgreSQL identifier-length error: the generated creator lookup index name was 64 characters, exceeding PostgreSQL's 63-character limit. The model and migration now use `ix_shopify_metafield_preferences_ws_shop_category_creator` (57 characters). The failed upgrade rolled back transactionally; `alembic current` remains `a3d4e5f6a7b8`, so the migration can be retried safely.

## Lifecycle transition

- State: `summarized`
- Next state: `archived`
- Archive target: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_20260713.md`
