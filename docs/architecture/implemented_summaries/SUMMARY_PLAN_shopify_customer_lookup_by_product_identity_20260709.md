# SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T11:35:56Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_by_product_identity_20260709.md`
- Related debug plan (optional): `none`

## What was implemented

- Added `POST /api/v1/integrations/shopify/customers/by-product-identity` to the existing Shopify router with `ADMIN`/`MANAGER`/`SELLER` access and the standard `run_service`/`build_ok`/`build_err` flow.
- Added a new Shopify lookup query that validates `sku` and `article_number`, loads active workspace-scoped shop integrations, skips shops missing `read_orders`/`read_products`/`read_customers`, and aggregates per-shop matches plus safe failure metadata.
- Added a new Shopify infra client for product-identity lookup:
  - direct order search by SKU
  - variant lookup by barcode followed by order lookup by resolved SKU
  - exact barcode filtering before order lookup
  - deduped order aggregation across resolved SKUs
- Added pure Shopify domain normalization for:
  - exact line-item matching on SKU or variant barcode
  - customer display-name fallback handling
  - customer/order/address contact fallback handling
  - normalized nested address/coordinates response shaping
- Added new Shopify result dataclasses and focused unit coverage for the domain, infra, query, and router behavior.

## Files changed

- `backend/app/beyo_manager/routers/api_v1/shopify.py`: added the new product-identity customer lookup route and `SELLER` role support for it.
- `backend/app/beyo_manager/domain/shopify/results.py`: added customer lookup result dataclasses.
- `backend/app/beyo_manager/domain/shopify/customer_lookup.py`: added exact-match filtering and normalized customer/address mapping.
- `backend/app/beyo_manager/services/infra/shopify/product_identity_client.py`: added Shopify GraphQL SKU/barcode lookup helpers.
- `backend/app/beyo_manager/services/queries/shopify/lookup_shopify_customers_by_product_identity.py`: added the workspace-scoped lookup orchestration query and request parser.
- `backend/app/tests/unit/domain/shopify/test_customer_lookup.py`: added domain fallback and exact-match tests.
- `backend/app/tests/unit/services/infra/shopify/test_product_identity_client.py`: added infra query-shaping and barcode-resolution tests.
- `backend/app/tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py`: added query behavior tests for scope skips, SKU-first fallback, and all-shops-failed handling.
- `backend/app/tests/unit/test_shopify_router.py`: extended router coverage for the new endpoint and seller access.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt PYTHONPATH=. pytest tests/unit/domain/shopify/test_customer_lookup.py tests/unit/services/infra/shopify/test_product_identity_client.py tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py tests/unit/test_shopify_router.py -q`: passed (`63 passed`).
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt PYTHONPATH=. pytest tests/integration/services/queries/shopify/test_shopify_admin_queries.py -q`: could not run in this sandbox because the local PostgreSQL test connection is blocked (`PermissionError: [Errno 1] Operation not permitted` to `127.0.0.1:5432`).

## Known gaps or deferred items

- Existing connected Shopify shops still need reauthorization to grant `read_customers`; until then they return `missing_required_scope` in `failed_shops`.
- Live DB-backed integration validation was not completed in this session because sandboxed local database access is unavailable.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`
