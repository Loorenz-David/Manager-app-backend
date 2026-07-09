# SUMMARY_PLAN_shopify_customer_lookup_corrections_20260709

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_customer_lookup_corrections_20260709`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T11:50:47Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_corrections_20260709.md`
- Related debug plan (optional): `none`

## What was implemented

- Fixed the Shopify customer-lookup query so shops with missing or blank `access_token_encrypted` are skipped safely as per-shop failures with `error_code="missing_access_token"` instead of being queried with an empty token.
- Corrected the query's `ExternalServiceError("All Shopify shop lookups failed.")` condition so non-attempted shops skipped for missing scope or missing token do not suppress a legitimate all-attempted-shops-failed external error.
- Added new unit coverage for the missing-access-token path and the mixed missing-token plus external-failure case.
- Restored the Shopify router role-gating test structure to match the original plan: the shared admin-only rejection parametrization no longer contains the customer-lookup route, and a dedicated worker-rejection test now covers that route explicitly.
- Added a DB-backed integration test file for the lookup query's real SQL filtering: workspace isolation, soft-delete exclusion, and `ACTIVE`-status filtering.
- Updated the Shopify frontend handoff doc with the customer-lookup endpoint contract, request/response examples, role access, error cases, and the route-count correction in the no-secret section.
- Updated the linked intention plan to reflect the corrective implementation plan being archived and the overall intention being achieved.

## Files changed

- `backend/app/beyo_manager/services/queries/shopify/lookup_shopify_customers_by_product_identity.py`: added missing-token skip logic and corrected the all-shops-failed classification.
- `backend/app/tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py`: added unit tests for missing token handling and mixed skip/error behavior.
- `backend/app/tests/unit/test_shopify_router.py`: removed the incorrect shared-parametrization exception and added a dedicated worker rejection test for the lookup route.
- `backend/app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py`: added the real-DB workspace/soft-delete/active-status filter test.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md`: documented the new route as Route 12 and updated related metadata/counts/build-order notes.
- `backend/docs/architecture/under_construction/intention/INTENTION_shopify_customer_lookup_by_product_identity_20260709.md`: updated linked-plan status, progress notes, lifecycle status, and timestamp.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt PYTHONPATH=. pytest tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py tests/unit/test_shopify_router.py -q`: passed (`41 passed`).
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt PYTHONPATH=. pytest tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py -q`: could not complete in this sandbox because local PostgreSQL access is blocked (`PermissionError: [Errno 1] Operation not permitted` to `127.0.0.1:5432`).

## Known gaps or deferred items

- The new DB-backed integration test is in place but could not be executed in this sandbox; it still needs CI or a local environment with PostgreSQL access to complete that validation step.
- The low-severity address-tier selection tradeoff noted in the correction plan remains intentionally deferred.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_shopify_customer_lookup_corrections_20260709.md`
