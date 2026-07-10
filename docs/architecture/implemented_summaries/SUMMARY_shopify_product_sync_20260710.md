# SUMMARY_shopify_product_sync_20260710

## Metadata

- Summary ID: `SUMMARY_shopify_product_sync_20260710`
- Status: `summarized`
- Owner agent: `Codex` (main implementation), `Claude` (closeout, fixes, validation)
- Created at (UTC): `2026-07-10T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_product_sync_20260709.md`
- Related debug plan (optional): `none`

## What was implemented

- A batched, workspace-scoped, background-processed "create or update Shopify products" capability: `POST /api/v1/integrations/shopify/products/process` validates a batch of items, resolves target Shopify shop(s) (defaulting to every `active` shop in the workspace when omitted), persists one `ShopifyProductSyncItem` tracking row per (item, shop) pair, writes one `ShopifyIntegrationEvent(event_type=PRODUCT_SYNC)` per distinct shop touched, enqueues exactly one `SHOPIFY_PROCESS_PRODUCTS` task, and returns immediately — no synchronous Shopify GraphQL call ever happens in the request path.
- A new `queue:shopify` worker task (`handle_shopify_process_products`) that loads all rows for a batch, and for each one: looks up an existing Shopify product by SKU (falling back to barcode) via `find_product_variant_by_identity`, creates (`productCreate` + `productVariantsBulkUpdate`) or updates (`productUpdate` + `productVariantsBulkUpdate`) the product accordingly, sets metafields via `metafieldsSet`, and records the row's terminal status — one row's failure never stops the rest of the batch.
- New GraphQL infra (`services/infra/shopify/product_sync_client.py`) using the corrected mutation shapes: `productCreate(product: ProductCreateInput!)` / `productUpdate(product: ProductUpdateInput!)` (not the deprecated `ProductInput`/`input:` shape), `productVariantsBulkUpdate` with `sku` nested under `inventoryItem.sku` (never top-level) and weight under `inventoryItem.measurement.weight`, and `metafieldsSet` with explicit `ownerId`/`namespace`/`key`/`type`/`value` per entry.
- A domain identity-matching module (`product_sync_identity.py`) that treats two-or-more exact SKU/barcode matches across *distinct* Shopify products as an explicit `ambiguous_product_match` failure rather than silently picking one, and a payload normalizer (`product_sync_payloads.py`) that applies the phase-1 defaults (`status` defaults to `draft`, metafields fixed to `namespace="custom"`/`type="single_line_text_field"`).
- One new socket event, `shopify.products.synced`, emitted once per completed batch to the requesting workspace's room (via a new `emit_to_workspace_room` helper) with `succeeded`/`failed` lists keyed by the caller's own `frontend_client_id` + `shop_integration_id`.
- Three additive Alembic migrations (new `shopify_product_sync_items` table + two enum `ADD VALUE` migrations), chained cleanly off the pre-existing single head.
- 44 new unit tests + 15 new integration tests across the domain/infra/command/task/router layers, plus extensions to five pre-existing Shopify test files (execution contracts, worker registration, router role-gating, model constraints, worker handler integration).
- The Route 13 + `shopify.products.synced` section of the Shopify frontend handoff doc.

## Files changed

- `backend/app/beyo_manager/domain/shopify/enums.py`: added `ShopifyProductSyncOperationEnum`, `ShopifyProductSyncItemStatusEnum`, `PRODUCT_SYNC` on `ShopifyIntegrationEventTypeEnum`.
- `backend/app/beyo_manager/domain/shopify/product_sync_identity.py` (new): exact-match/ambiguous-match domain logic.
- `backend/app/beyo_manager/domain/shopify/product_sync_payloads.py` (new): frontend-item → Shopify-ready payload normalizer.
- `backend/app/beyo_manager/domain/execution/enums.py`: added `TaskType.SHOPIFY_PROCESS_PRODUCTS`.
- `backend/app/beyo_manager/domain/execution/payloads/shopify.py`: added `ShopifyProcessProductsPayload` (IDs-only: `workspace_id`, `requested_by_user_id`, `sync_item_client_ids`).
- `backend/app/beyo_manager/errors/external_service.py`: added `ShopifyProductLookupAmbiguousError`.
- `backend/app/beyo_manager/models/tables/shopify/shopify_product_sync_item.py` (new): the per-(item, shop) tracking table.
- `backend/app/beyo_manager/models/__init__.py`: registered the new table import.
- `backend/app/beyo_manager/services/infra/shopify/product_sync_client.py` (new): GraphQL lookup/create/update/metafields functions.
- `backend/app/beyo_manager/services/commands/shopify/requests/process_shopify_products_request.py` (new): request schema + validation (identity required, weight-unit validation, 1-200 item cap).
- `backend/app/beyo_manager/services/commands/shopify/_product_sync_normalizer.py` (new): resolves target shops and builds normalized payloads.
- `backend/app/beyo_manager/services/commands/shopify/process_shopify_products.py` (new): the router-triggered command.
- `backend/app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py` (new): per-(item, shop) lookup → create-or-update → metafields orchestration.
- `backend/app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py` (new): the worker task handler.
- `backend/app/beyo_manager/services/infra/execution/task_router.py`: added `SHOPIFY_PROCESS_PRODUCTS` to `QUEUE_MAP` (→ `queue:shopify`).
- `backend/app/beyo_manager/services/infra/execution/worker_base.py`: added a 900s `HANDLER_TIMEOUT_SECONDS` entry for `shopify_process_products`.
- `backend/app/beyo_manager/sockets/worker_emitter.py`: added `emit_to_workspace_room`.
- `backend/app/beyo_manager/workers/shopify_worker.py`: registered the new handler in `HANDLER_MAP`.
- `backend/app/beyo_manager/routers/api_v1/shopify.py`: added `POST /products/process` and its request body models.
- `backend/app/migrations/versions/e1b2c3d4e5f6_create_shopify_product_sync_items_table.py`, `f2c3d4e5f6a7_add_shopify_process_products_task_type.py`, `a3d4e5f6a7b8_add_product_sync_to_shopify_integration_event_type.py` (new): chained additive migrations, `d4f8a1b2c3e4 -> e1b2c3d4e5f6 -> f2c3d4e5f6a7 -> a3d4e5f6a7b8`.
- `backend/app/tests/unit/domain/shopify/test_product_sync_identity.py`, `test_product_sync_payloads.py` (new).
- `backend/app/tests/unit/services/infra/shopify/test_product_sync_client.py` (new).
- `backend/app/tests/unit/services/commands/shopify/test_process_shopify_products.py` (new).
- `backend/app/tests/unit/services/tasks/shopify/test_handle_shopify_process_products.py` (new).
- `backend/app/tests/integration/services/commands/shopify/test_process_shopify_products_integration.py` (new).
- `backend/app/tests/integration/services/tasks/shopify/test_shopify_worker_handlers_integration.py`: extended with a new DB-backed status-transition test; fixed a stale-ORM-object assertion (see "Known gaps or deferred items" — actually a fixed bug, see below).
- `backend/app/tests/integration/models/shopify/test_shopify_foundation_constraints.py`: extended with FK/enum/default-status constraint coverage for the new table.
- `backend/app/tests/unit/domain/execution/test_shopify_execution_contracts.py`, `tests/unit/workers/test_shopify_worker.py`: extended for the new task type/payload/handler registration.
- `backend/app/tests/unit/test_shopify_router.py`: extended for the new route's role gating; one entry corrected (see below).
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md`: added Route 13 + the `shopify.products.synced` event contract, updated route count and build-order list.
- `backend/docs/architecture/under_construction/intention/INTENTION_shopify_product_sync_20260709.md`: linked plan status updated (see below).

## Bugs found and fixed during closeout

1. **Misplaced router role-test entry** (`tests/unit/test_shopify_router.py`): `/products/process` (gated `ADMIN` **or** `MANAGER`) had been added to the parametrize list for `test_new_shopify_admin_only_routes_allow_admin_and_reject_manager_before_service_logic` — a list reserved for genuinely admin-only routes. Removed it from there and added an explicit `admin`-role row to `test_new_shopify_shared_role_routes_call_service_with_expected_context` (which already had a `manager`-role row), so both allowed roles are now explicitly exercised in the correct test bucket. The worker/seller-rejection list already correctly included the route and was left unchanged.
2. **Stale-ORM-object assertion in a worker integration test** (`test_shopify_worker_handlers_integration.py::test_handle_shopify_process_products_transitions_rows_to_succeeded_and_failed`): the test's `_fake_create_shopify_product` helper called `await db_session.get(ShopifyProductSyncItem, success_row.client_id)` to assert the row had been transitioned to `PROCESSING` by the handler's own (separate) session — but this app's session factory sets `expire_on_commit=False` (`models/database.py:47`), so `Session.get()` returned the cached, never-invalidated `success_row` object straight from the identity map without querying the database at all, always showing the pre-handler `PENDING` value. Fixed by replacing it with an explicit `await db_session.refresh(success_row)`. This is a reusable lesson for any future test in this codebase that asserts on a row mutated by a second session while holding a reference from a first session — `session.get()` alone is not sufficient with `expire_on_commit=False`.
3. **Missing frontend handoff doc section**: `HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` had no entry for the new route or its socket event. Added Route 13 with full request/response/error documentation and a `shopify.products.synced` event contract section, per `57_shopify_integration.md`'s explicit "keep this doc from drifting" rule.

## Follow-up code review and fixes (2026-07-10, same day)

An 8-angle code review (`/code-review high`) was run against the full diff after the closeout above and found 10 issues, all fixed in a follow-up pass:

- **Validation gap discovered first**: 5 of the 8 new unit test files never had a `@pytest.mark.unit` decorator, so every earlier `pytest -m unit` run in this session (including "44 unit tests" above) silently excluded them without error. Running the excluded files directly surfaced a real, currently-shipping bug (see next item) that the earlier "153 passed, 0 failed" validation evidence had never actually exercised. Added the missing markers to all 5 files (`test_product_sync_identity.py`, `test_product_sync_payloads.py`, `test_process_shopify_products.py`, `test_shopify_worker.py`, `test_shopify_execution_contracts.py`) so they now run under `-m unit` as intended.
- **`domain/shopify/product_sync_payloads.py`**: an empty `inventoryItem: {}` was never dropped from the normalized payload for items identified only by barcode (no sku/weight) — `_drop_none` only strips `None` values, and a redundant reconstruction turned an already-correct `None` back into `{}`. Fixed by returning `_drop_none(variant)` directly instead of rebuilding the dict; this also removed the redundant reconstruction entirely.
- **`services/tasks/shopify/_product_sync_orchestrator.py`**: `set_shopify_product_metafields` ran before `shopify_product_id`/`shopify_variant_id` were persisted on the row, so a metafields-only failure discarded the ID of a product Shopify had just successfully created — risking a duplicate on any future retry. Fixed by persisting the IDs immediately after create/update succeeds, before the metafields call.
- **Same file**: once a sku match was found, the item's own barcode was never checked against it, so a barcode belonging to a *different* existing product could silently be written onto the matched one (Shopify does not enforce barcode uniqueness). Fixed by verifying the barcode resolves to the same product when both identities are present, raising a new `conflicting_identity_match` error otherwise.
- **`services/commands/shopify/_product_sync_normalizer.py`**: `target_shop_integration_ids` was never deduplicated, so a duplicate id in the request created two tracking rows (and risked two Shopify products) for one logical (item, shop) pair. Fixed with an order-preserving `dict.fromkeys(...)` dedupe.
- **`services/tasks/shopify/handle_shopify_process_products.py`**: the outer `except Exception` re-committed on the same session without calling `rollback()` first — if the orchestrator's own commit failed for a reason outside its narrow `except` clause, the recovery commit would itself raise, uncaught, crashing the entire batch mid-loop and skipping the final socket notification. Fixed by adding `await session.rollback()` before the recovery commit. Also added `logging` (missing entirely from this file) — `logger.warning` for expected failure branches, `logger.exception` for the unexpected-error catch-all — and added a `status == ACTIVE` / `is_deleted == False` filter to the shop-integration query, matching the same check already done at enqueue time, so a shop disabled between enqueue and worker pickup is treated as missing rather than synced against with a possibly stale token.
- **`services/infra/shopify/product_sync_client.py`**: `_quote_shopify_search_term` and `_clean_str` were duplicated verbatim from the pre-existing `product_identity_client.py`. Promoted `quote_shopify_search_term` to a shared public function in `graphql_client.py` (the module both files already import from) and updated both call sites; left the tiny `_clean_str` per-file duplication as-is, matching this codebase's existing convention for that helper.
- **`tests/unit/domain/execution/test_shopify_execution_contracts.py`**: the new migration-assertion test copied a pre-existing broken pattern (`Path("app/migrations/versions/...")`, which only resolves when pytest is invoked from the repo root, not from `app/` — this project's own working directory). Fixed both the new and the pre-existing test to resolve the path relative to `__file__` instead.
- Added new/extended tests covering every behavioral fix above: a new `tests/unit/services/tasks/shopify/test_product_sync_orchestrator.py` (metafields-failure-keeps-ids, conflicting-identity-match, and the same-product-agrees-so-update-proceeds case), a new dedupe integration test in `test_process_shopify_products_integration.py`, a new disabled-shop-integration integration test in `test_shopify_worker_handlers_integration.py`, and a new rollback-before-recommit unit test in `test_handle_shopify_process_products.py`.

Full findings were reported via the code-review skill's structured output (not reproduced here); the above is the complete fix list. No structural/architectural changes — router, command, worker delegation, DB tracking table, and socket-event strategy are all unchanged from the original closeout.

## Contract adherence

- `architecture/57_shopify_integration.md`: followed exactly — new task type added via the documented 7-step process (`TaskType` → payload → `QUEUE_MAP` → handler → `HANDLER_MAP` → `create_instant_task` caller → additive migration); new admin route follows the existing query/command split and `run_service`/`build_ok`/`build_err` pattern; every state-mutating operation writes a `ShopifyIntegrationEvent`; no inline Shopify GraphQL call from any HTTP request handler.
- `architecture/16_background_jobs.md`: `ShopifyProcessProductsPayload` carries IDs only (`sync_item_client_ids`), never denormalized item data — the handler re-loads everything from Postgres.
- `architecture/30_migrations.md`: all three migrations are additive (`CREATE TABLE`, `ALTER TYPE ... ADD VALUE IF NOT EXISTS` x2), chained linearly, no destructive operation.
- `architecture/09_routers.md` / `06_commands.md`: router does no business logic (validate body → `run_service` → `build_ok`/`build_err`); command owns its own `ctx.session.begin()` transaction and parses its own request.
- `architecture/03_models.md`: new table uses `IdentityMixin`, indexed FKs, indexed `workspace_id`+`status` composite, `SAEnum(..., create_type=True)`.
- Real `python-socketio` implementation (not the stale `13_sockets.md` sample) followed for `emit_to_workspace_room`.

## Validation evidence

- `python3 -m py_compile` on all 32 new/changed Python modules: passed.
- `python -m alembic heads` (before): single head confirmed. `alembic upgrade head`: applied all three new migrations cleanly against the local dev Postgres (`docker` container on `localhost:5433`); new head `a3d4e5f6a7b8`. Verified via `psql \d shopify_product_sync_items` and a `pg_enum` query that the live schema (columns, types, defaults, indexes, FKs, and the `shopify_process_products` task-type enum value) matches the ORM model and migration exactly.
- **Superseded by the follow-up review pass above** — the numbers below are from *after* the missing `@pytest.mark.unit` markers were added, i.e. the first validation pass that actually exercised every new test file:
- `pytest -m unit` (new-capability files only): **114 passed** (up from a mis-measured 44 before the marker fix).
- `pytest -m integration` (new-capability files only, against the migrated local dev DB): **60 passed**.
- `pytest` with no marker filter across the entire `tests/{unit,integration}/.../shopify/` tree (new + all pre-existing Shopify suites): **207 passed, 0 failed** — no regressions in any pre-existing Shopify coverage.
- `pytest -m unit` across the **entire** repo test suite: 297 passed, 6 failed (same 6 as before the marker fix — the +19 delta is entirely newly-collected Shopify tests, no new failures). All 6 failures are in files/modules this work never touched (`test_sign_in_user.py`, `test_process_step_transition.py`, `test_case_type_serializers.py`, `test_items_router.py`, `test_upholstery_inventories_router.py`) and are confirmed pre-existing on the base commit (`git status`/`git diff` show zero uncommitted changes anywhere in those modules) — unrelated to this plan, left untouched, not investigated further.

## Known gaps or deferred items

- **Live Shopify GraphQL schema/dev-shop verification was not performed.** No live Shopify shop or API credentials were available in this session. The mutation names and top-level argument shapes (`ProductCreateInput`/`ProductUpdateInput` via `product:`, `ProductVariantsBulkInput` with `inventoryItem.sku`/`inventoryItem.measurement.weight`, `MetafieldsSetInput`'s five fields) are implemented per the corrected, documentation-verified design and covered by unit tests asserting the exact request shape sent to `execute_shopify_graphql` — but no request has actually been sent to a real Shopify Admin API endpoint. This is the one explicit, carried-forward gap from the plan's "Clarifications required" item 2. Recommended before this capability is used against a production or staging Shopify store: run the introspection query noted in the plan, or a one-item smoke test end-to-end against a development store.
- Product image/media upload, multi-variant products, and Shopify's structured `TaxonomyCategory` remain explicitly out of scope, per the plan's own non-goals — not gaps, deliberate deferrals.
- Row-level idempotency across a *whole-task* retry (e.g. after a worker crash mid-batch) is not implemented — a retried task re-processes every row in the batch, including already-`SUCCEEDED` ones. This was a known, accepted risk in the original plan (see its "Risks and mitigations"), not something introduced during implementation.
- 6 pre-existing, unrelated test failures elsewhere in the repo (see "Validation evidence") were observed but not investigated or fixed — out of scope for this plan.

## Handoff notes

- To frontend: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` (Route 13 + `shopify.products.synced` section added in this session).

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_shopify_product_sync_20260710.md`
