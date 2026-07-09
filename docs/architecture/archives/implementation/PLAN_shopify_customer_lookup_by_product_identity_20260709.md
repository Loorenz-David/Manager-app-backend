# PLAN_shopify_customer_lookup_by_product_identity_20260709

## Metadata

- Plan ID: `PLAN_shopify_customer_lookup_by_product_identity_20260709`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T00:00:00Z`
- Last updated at (UTC): `2026-07-09T11:35:56Z`
- Related issue/ticket: Shopify customer lookup by product SKU/barcode (first Shopify commerce-data read capability)
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_customer_lookup_by_product_identity_20260709.md`
- Depends on (implemented and verified): `backend/architecture/57_shopify_integration.md` — the OAuth/webhook integration this plan builds on top of. `ShopifyShopIntegration` (`shop_domain`, `access_token_encrypted`, `granted_scopes`, `status`, `workspace_id`, `is_deleted`, `client_id`), the admin router at `/api/v1/integrations/shopify`, `services/infra/shopify/graphql_client.py` (`execute_shopify_graphql`, `ShopifyGraphQLError`/`ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError`), and `domain/shopify/scopes.py` (`has_all_required_scopes`) are all read directly from the current codebase, not from plan text, and reused as-is — no changes to any of them.

## Goal and intent

- Goal: Add a workspace-scoped, role-gated `POST` route that, given a product `sku` and/or `article_number` (Shopify barcode), searches every active Shopify shop integration in the caller's workspace for a matching order line item and returns normalized, safe customer/address information for each match.
- Business/user intent: Let ADMIN/MANAGER/SELLER users resolve "who does this physical item belong to" from a scanned or typed SKU/barcode, across every Shopify shop the workspace has connected, without exposing any Shopify secret or raw payload.
- Non-goals:
  - No persistence of lookup results (this is a pure read, nothing is written to Postgres).
  - No background/worker/queue involvement — this is a synchronous request-time lookup with bounded query limits (see "Resolved decisions" item 6).
  - No batch lookup of multiple identities in one call, no single-shop-scoped lookup, no order-status/fulfillment-status fields, no pagination beyond the fixed per-shop bounds below.
  - No change to `handle_shopify_process_webhook`, webhook registry, subscription sync, or OAuth flows.
  - No new Postgres migration, table, or enum value.

## Scope

- In scope:
  - `POST /api/v1/integrations/shopify/customers/by-product-identity` on the existing `routers/api_v1/shopify.py` router.
  - `services/queries/shopify/lookup_shopify_customers_by_product_identity.py` — the orchestration query (validates input, fetches active shop integrations, applies SKU-then-barcode preference per shop, aggregates results, handles per-shop failure).
  - `services/infra/shopify/product_identity_client.py` — the low-level Shopify GraphQL adapter (variant-by-barcode lookup, order-by-SKU search).
  - `domain/shopify/customer_lookup.py` — pure functions: exact-match line-item filtering and raw-Shopify-order-node -> `ShopifyCustomerLookupResult` normalization (email/phone/address priority rules).
  - Three new frozen dataclasses in `domain/shopify/results.py`: `ShopifyCustomerLookupCoordinatesResult`, `ShopifyCustomerLookupAddressResult`, `ShopifyCustomerLookupResult`.
  - Adding `SELLER` to the role import in `routers/api_v1/shopify.py` (currently only imports `ADMIN, MANAGER`).
  - Tests across all four new modules plus the extended router test file.
- Out of scope:
  - Any change to `services/commands/shopify/*`, `services/tasks/shopify/*`, `workers/shopify_worker.py`, or the webhook registry.
  - Any change to `ShopifyShopIntegration` or any other table/migration.
  - Caching of lookup results (query result caching per `07_queries.md` is for stable, cacheable data — a live customer/order lookup is neither).
- Assumptions:
  - `read_orders` and `read_products` are already required by existing webhook topics in `SHOPIFY_WEBHOOK_REGISTRY` (`orders/create`+ → `read_orders`; `products/create`+ → `read_products`; `domain/shopify/webhook_registry.py:28,52` etc.), so those two are very likely already part of `SHOPIFY_APP_SCOPES` for every existing installation. **`read_customers` is a third, separate required scope this plan introduces** — nothing in the existing webhook registry or any prior Shopify plan requests it today, because the `customer { ... }` sub-selection this plan's GraphQL query needs (`id`, `displayName`, `defaultEmailAddress.emailAddress`, `defaultPhoneNumber.phoneNumber`, `defaultAddress.*`) is gated behind `read_customers` in Shopify's Admin GraphQL API. **This plan does *not* assume no `SHOPIFY_APP_SCOPES`/Partner Dashboard change is needed** — `read_customers` must be added to `SHOPIFY_APP_SCOPES` for new installs, and every *existing* shop integration will show `missing_required_scope` until it goes through Route 4 (reauthorize) and grants it. A shop that has not (yet) granted all three required scopes is handled per-shop (see "Resolved decisions" item 3), not treated as a global blocker — but this is a real, expected rollout step for already-connected shops, not a hypothetical edge case.
  - Shopify's Admin GraphQL Order connection search (`orders(query: "sku:...")`) supports filtering orders by a line item's SKU — this is Shopify's documented order search syntax (the `sku` field is a supported order-search filter). There is **no equivalent `barcode` filter on the orders connection** — barcode is only a field on `ProductVariant`, searchable via the `productVariants(query: "barcode:...")` connection. This asymmetry is why the barcode path is implemented as "resolve variant(s) by barcode, then search orders by the resolved SKU(s)" rather than a direct one-call order search (see "Resolved decisions" item 1). This must be re-confirmed against the live Shopify Admin API schema for `SHOPIFY_API_VERSION` (`settings.shopify_api_version`, currently `"2026-01"`, `config.py:111`) before merging — if a future API version adds a direct order-barcode filter, prefer it and simplify `fetch_shopify_orders_by_product_identity`, but do not block this plan on that reverification since the variant-resolution fallback is correct regardless.
  - **Order history depth is whatever `read_orders` actually grants for this app's install type, not guaranteed "all orders ever."** Shopify restricts `read_orders` to a rolling recent window (historically 60 days) for many app configurations, with full history requiring an additional, separately-approved `read_all_orders` scope; custom/private-install apps (this integration's current model, per `57_shopify_integration.md`'s "currently single-app/custom install model" section) have historically been exempt from that restriction, but this must be reconfirmed against the actual granted-scopes/app-type behavior for `SHOPIFY_API_VERSION` before relying on it. This plan does not add any handling for "order exists but is outside the accessible window" as a distinct case — it is indistinguishable from "no match" in Shopify's response, so it surfaces to the caller as an ordinary empty result for that shop, not an error. This is called out explicitly (see "Risks and mitigations") as a known, accepted limitation of this first implementation, not a silent gap.

## Clarifications required

None. Every open design question below is resolved in "Resolved decisions," with the single reverification note above (Shopify schema capability, not a design ambiguity) flagged for implementation time.

## Resolved decisions

1. **Barcode path resolves via variant lookup first, never a direct order-barcode search.** `fetch_shopify_orders_by_product_identity` (infra layer): for `identity_type="barcode"`, first calls `productVariants(query: "barcode:<value>")`, keeps only variants whose `barcode` field exactly equals the input (defends against Shopify's fuzzy/tokenized search), collects the distinct `sku` values from those variants, then calls the same order-by-SKU search for each resolved SKU and merges/dedupes the returned orders by `id`. For `identity_type="sku"`, it calls the order-by-SKU search directly. This matches the intention's explicit instruction not to assume barcode is directly searchable on orders.
2. **Two layers of exact-match enforcement, not one.** (a) Infra layer: after `productVariants(query: "barcode:...")`, only variants whose `barcode` field is a case-sensitive exact match to the input are kept, before their SKUs are used to search orders — this narrows which SKU(s) get searched and avoids wasting an order search on a fuzzy-matched variant. (b) Domain layer (`filter_shopify_order_line_item_exact_matches` in `domain/shopify/customer_lookup.py`): after orders come back from either path, only orders containing a line item whose `sku` (sku path) or whose `variant.barcode` (barcode path — re-checked against the *original* `article_number`, not the intermediate SKU) exactly matches are kept. Both checks are needed: (a) prevents wasted order-search calls on the wrong variant; (b) is the actual correctness guarantee against Shopify's order-search index doing partial/tokenized matching, and also guards the edge case where an order search by SKU returns an order whose *other* line items share that SKU but whose matched line item's variant barcode differs from what the caller asked for.
3. **Missing required scopes is a per-shop skip, not a request-level error.** Before querying a shop, the query checks `has_all_required_scopes(("read_orders", "read_products", "read_customers"), integration.granted_scopes or ())`. If false, that shop is skipped and recorded in `failed_shops` with `error_code="missing_required_scope"` — no GraphQL call is attempted (avoids a guaranteed 401/403 round trip, and avoids querying `customer { ... }` fields the shop hasn't authorized). This shop's absence does not count toward the "all shops failed" external-error condition in decision 5, because it is a configuration gap (the shop needs Route 4 reauthorization), not a transient external-service failure.
4. **Response envelope: `{"customer_matches": [...], "failed_shops": [...]}`**, following the Shopify domain's established `asdict(serialize_or_normalize(...))`-per-item list pattern (`list_shopify_shop_integrations.py`'s `"shops": [...]`, `get_shopify_scope_status.py`'s `"scope_statuses": [...]`) rather than returning a bare list at the router's top level — the intention text explicitly allows adjusting the exact shape to match existing patterns. `failed_shops` entries are minimal and safe: `{"shop_integration_id": str, "shop_domain": str, "error_code": str}` — no error message, no raw Shopify response, no token. This is deliberately visible (not log-only) because a caller retrying a scan benefits from knowing *some* shop(s) didn't return a result due to a config/API issue, distinct from "no product found anywhere."
5. **All-shops-failed condition raises `ExternalServiceError`, everything else degrades gracefully.** Let `attempted` = shops with sufficient scope (decision 3). If `attempted` is non-empty, zero `customer_matches` were produced, and every `attempted` shop's `error_code` in `failed_shops` came from a caught `ShopifyGraphQLError` (i.e., `len(failed_shops-from-graphql-errors) == len(attempted)`), raise `ExternalServiceError("All Shopify shop lookups failed.")` (`errors/external_service.py`, `http_status=502`, already imported via `beyo_manager.errors`). If `attempted` is empty (every shop skipped for missing scope, or there are zero active shop integrations at all), or if at least one shop succeeded (even with an empty match list) or at least one match was found, the query returns success — `customer_matches` may be `[]`, matching the intention's explicit "no match anywhere is not an error" requirement. A `ShopifyGraphQLError` from one shop's call is caught in the per-shop loop (see step 3 of the query in "Implementation plan"), never allowed to propagate and abort the loop for other shops.
6. **Fixed, small query limits — no pagination.** `_ORDERS_FIRST = 10` (orders inspected per SKU search), `_LINE_ITEMS_FIRST = 20` (line items inspected per order), `_VARIANTS_FIRST = 5` (variants inspected per barcode search) — module-level constants in `services/infra/shopify/product_identity_client.py`. This is a point lookup for one physical item, not a bulk export; ordering the order search `sortKey: CREATED_AT, reverse: true` means the 10 most recent orders containing that SKU are inspected first, which is the overwhelmingly common case for "which customer has this item" (the most recent sale). If a future need arises for "all orders ever containing this SKU," that is a distinct, explicitly-paginated capability, not this one — documented as an explicit scope boundary, not a silent limitation.
7. **Query string values are escaped before being interpolated into Shopify's search syntax.** A private `_quote_shopify_search_term(value: str) -> str` helper in `product_identity_client.py` wraps the value in double quotes and escapes internal backslashes/double-quotes (`value.replace("\\", "\\\\").replace('"', '\\"')`), producing e.g. `sku:"ABC-123"` / `barcode:"012345678905"`. This is defensive against a SKU/barcode containing a quote character breaking Shopify's search-query parsing or (worst case) altering the intended filter — not a SQL-injection-equivalent risk against Shopify's own systems, but correctness/robustness hygiene for arbitrary user-supplied search terms.
8. **Router request model accepts raw optional strings; business validation (trim, at least one required) lives in the query's own request parser**, mirroring `06_commands.md`'s `parse_<x>_request` pattern (already used by every existing Shopify command, e.g. `create_shopify_install_url.py`'s `CreateShopifyInstallUrlRequest`/`parse_create_shopify_install_url_request`) even though this is a query, not a command — no existing Shopify query needed this level of cross-field validation before, so this plan is the first to apply the command-style parser pattern inside a query file. A Pydantic `model_validator(mode="after")` enforces "at least one of `sku`/`article_number` after trimming," converting to `beyo_manager.errors.ValidationError` (`http_status=422`) exactly like every existing Shopify command's parser does for `PydanticValidationError`.
9. **No `ctx.add_warning`/`ctx.warnings` mechanism exists in this codebase's actual `ServiceContext`** (`services/context.py:1-56` — a plain `@dataclass` with `identity`/`incoming_data`/`session`/`query_params` and no warnings list, unlike the aspirational `04_context.md` canonical text). Confirmed via direct read and a repo-wide grep for `add_warning`/`ctx.warnings` (zero hits). This plan does not attempt to introduce that mechanism — the "zero active integrations" case (decision 5) is communicated purely through the response shape (`customer_matches: []`, `failed_shops: []`), not a warning.
10. **No new enum class for `identity_type`/`match_type`.** These are typed as `Literal["sku", "barcode"]` (from `typing`) threaded through the infra/domain/query functions, since the two literal values already are the exact `match_type` API field values and a two-member `StrEnum` would add a layer with no behavior beyond what `Literal` already gives at the type-checking level. This is a deliberate scope call, not an oversight — every other Shopify enum in `domain/shopify/enums.py` models genuine multi-state lifecycle/status data, which this is not.
11. **`display_name` is the linked Shopify Customer account's display name, with an address-name fallback chain — not the order's shipping/billing recipient name as a *separate* concept.** `customer.displayName` is Shopify's own computed "first + last name" for the `Customer` record (what shows in the Shopify admin customer list); it can differ from who the package is actually addressed to (e.g. gifting), but it is the most stable "who is this customer" identity when a `Customer` record exists. The ambiguity this decision closes: an order with no linked `Customer` (guest/POS checkout, `order.customer` is `null`) would otherwise leave `display_name` permanently `None` even though the shipping address almost always has a real name on it. To close that gap, `display_name` uses the *same* priority order as the `address` field — `customer.displayName` → `shippingAddress.{firstName,lastName}` (joined with a space, trimmed) → `billingAddress.{firstName,lastName}` → `customer.defaultAddress.{firstName,lastName}` → `None`. This requires `firstName`/`lastName` added to all three address selections in `SEARCH_ORDERS_BY_SKU_QUERY` (already reflected in "Implementation plan" step 3's query text). Every caller of this API must treat `display_name` as "best-known name for this match," not as a guaranteed Shopify-account identity — this is documented so the frontend does not conflate it with a verified customer identity field.
12. **`primary_email`/`primary_phone_number` are sourced from `Customer.defaultEmailAddress.emailAddress`/`Customer.defaultPhoneNumber.phoneNumber`, not the older bare `Customer.email`/`Customer.phone` fields, and this is exactly why `read_customers` (decision 3) is required at all.** Current Shopify Admin GraphQL API models a customer's contact info as `defaultEmailAddress: CustomerEmailAddress` / `defaultPhoneNumber: CustomerPhoneNumber` sub-objects (each wrapping the actual string plus verification/marketing-consent metadata this plan does not need and does not select) rather than flat `email`/`phone` scalars on `Customer`. `SEARCH_ORDERS_BY_SKU_QUERY`'s `customer { ... }` selection (Implementation plan step 3) selects `defaultEmailAddress { emailAddress }` / `defaultPhoneNumber { phoneNumber }`, and `normalize_shopify_customer_lookup_result` reads `customer.defaultEmailAddress.emailAddress` / `customer.defaultPhoneNumber.phoneNumber` (guarding for either sub-object being `null` — a customer can have no phone on file, and rarely no email). `Order.email`/`Order.phone` (the order-level, not customer-level, contact fields) remain flat scalars and are read as before — only the `Customer`-level fields changed shape. This plan does not add `customer.email`/`customer.phone` as a defensive legacy fallback; if a future API version deprecates `defaultEmailAddress`/`defaultPhoneNumber` first, that is a follow-up plan, not a speculative fallback added now.
13. **Address `district` maps from `province`/`provinceCode` only — never `company`.** The original draft's `company` fallback was a mapping error: Shopify's `MailingAddress.company` is the customer's company/organization name, not a district or region, and using it as a `district` fallback would silently produce nonsense data (e.g. a business name shown where a neighborhood/district was expected) for any B2B order. Corrected priority: `district` = first non-blank of `province`, `provinceCode`, else `None`. `company` is not selected in `SEARCH_ORDERS_BY_SKU_QUERY`'s address sub-selections at all (removed from `shippingAddress`/`billingAddress`/`defaultAddress` in "Implementation plan" step 3) — there is no `company_name` field on `ShopifyCustomerLookupAddressResult` in this plan; a future plan can add one deliberately if the frontend needs it, rather than smuggling it in under a misleading `district` key.

## Acceptance criteria

1. `POST /api/v1/integrations/shopify/customers/by-product-identity` is registered on the existing `shopify.py` router at the existing `/api/v1/integrations/shopify` prefix, gated by `Depends(require_roles([ADMIN, MANAGER, SELLER]))`; a `WORKER` JWT is rejected (`403`) before any query logic runs.
2. Request body `{"article_number": "...", "sku": "..."}` (both optional): omitting both, or supplying only whitespace in both, resolves to a `422 ValidationError` before any Shopify call or database query.
3. When `sku` is supplied and a shop's SKU search finds an exact-match line item, that shop's result uses `match_type="sku"`, `matched_value=<sku>` — `article_number`, if also supplied, is never used for that shop.
4. When `sku` is supplied but a shop's SKU search finds no exact match, and `article_number` is also supplied, that shop falls back to the barcode path and (if found) reports `match_type="barcode"`, `matched_value=<article_number>`.
5. When only `article_number` is supplied, every shop uses the barcode path directly.
6. The lookup only ever queries `ShopifyShopIntegration` rows where `workspace_id == ctx.workspace_id`, `is_deleted.is_(False)`, `status == ShopifyIntegrationStatusEnum.ACTIVE` — no cross-workspace data ever appears in a result.
7. A shop lacking `read_orders`+`read_products`+`read_customers` in `granted_scopes` is skipped with no GraphQL call, appearing in `failed_shops` as `{"error_code": "missing_required_scope", ...}`.
8. A `ShopifyGraphQLError` raised for one shop is caught, recorded in `failed_shops` with that error's `error_code`, and does not prevent other shops' results from being returned.
9. If every shop with sufficient scope raises a `ShopifyGraphQLError` and zero matches were found anywhere, the route returns a `502 ExternalServiceError`.
10. No match anywhere (zero active integrations, or all integrations queried cleanly with no exact-match line item) returns `200` with `{"customer_matches": [], "failed_shops": [...]}` (`failed_shops` empty unless a shop was actually skipped/failed) — never an error.
11. Every `ShopifyCustomerLookupResult` in the response includes exactly the fields in the intention's "Expected Router Response" shape (`shop_integration_id`, `shop_domain`, `match_type`, `matched_value`, `order_id`, `order_name`, `customer_id`, `display_name`, `primary_phone_number`, `primary_email`, `address.{street_address,post_code,coordinates.{latitude,longitude},city,district}`) and never a raw Shopify field name, raw payload, or `access_token_encrypted`.
12. Email/phone/display-name/address resolution follows the documented priority order exactly, verified by domain-layer unit tests with fixtures that force each fallback tier:
    - `primary_email`: `customer.defaultEmailAddress.emailAddress` → `order.email` → `None`.
    - `primary_phone_number`: `customer.defaultPhoneNumber.phoneNumber` → `order.phone` → `shippingAddress.phone` → `billingAddress.phone` → `customer.defaultAddress.phone` → `None`.
    - `display_name`: `customer.displayName` → `shippingAddress.{firstName,lastName}` → `billingAddress.{firstName,lastName}` → `customer.defaultAddress.{firstName,lastName}` → `None`.
    - `address`: `shippingAddress` → `billingAddress` → `customer.defaultAddress` → an all-`None` address object; within the chosen tier, `street_address` = `address1` → `address2` → `None`, `post_code` = `zip` → `None`, `city` = `city` → `None`, `district` = `province` → `provinceCode` → `None` (never `company`), `coordinates` = `latitude`/`longitude` → `None`/`None`.
13. Missing Shopify coordinates on the resolved address serialize as `null`/`None`, never `0` or an omitted key.
14. `display_name` is never silently blank on an order that has a shipping or billing name but no linked `Customer` record (guest/POS checkout) — the address-name fallback tiers in criterion 12 cover this case explicitly.
15. `address.district` never contains a Shopify `company`/organization value — only `province`, `provinceCode`, or `null`.

## Contracts and skills

### Contracts loaded

- `architecture/57_shopify_integration.md`: The authoritative Shopify integration document — file structure, "Adding a new admin route (query or command)" section (query/infra/domain split, role-gate-by-risk-level rule), security rules (no secrets in `metadata_json`/responses, workspace scoping). This plan follows its "Query" bullet exactly: read-only, `ctx.incoming_data`, returns a `dict`, always filters by `ctx.workspace_id`.
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: Query signature (`async def fn(ctx: ServiceContext) -> dict`), workspace-scope-first `where()` ordering. The offset-pagination section of `07_queries_local.md` does **not** apply — this is a bounded point lookup, not a list query, so no `limit`/`offset`/`has_more` envelope is added (explicitly not a contract violation: pagination applies to *list queries*, and this query's internal Shopify-side limits are a different concern, documented in "Resolved decisions" item 6).
- `architecture/06_commands.md`: The `parse_<x>_request`/`BaseModel`/`field_validator`/`model_validator` request-parsing pattern this plan reuses inside a query file (decision 8) — "One parse entry point," "Domain error conversion in the parser only," "No `validate_fields` classmethod" rules all apply verbatim.
- `architecture/09_routers.md`: Router does exactly: parse body -> build `ServiceContext` -> `run_service` -> `build_ok`/`build_err`. No business logic, no ORM calls in the router.
- `architecture/05_errors.md`: `ValidationError` (422) for the "at least one of sku/article_number" violation; `ExternalServiceError` (502, already defined in `errors/external_service.py`) for the all-shops-failed case; no new error subclass is introduced.
- `architecture/19_integrations.md`: Graceful-degradation table precedent ("External data API -> Return empty result, surface error to frontend, allow manual entry") directly informs decision 5's partial-failure design; "Integration test isolation" rule (`monkeypatch` the provider client, never hit real external APIs) governs this plan's integration tests.
- `architecture/24_multi_tenancy.md`: `workspace_id` filter is the first `where()` condition on the `ShopifyShopIntegration` query, exactly as every other Shopify query already does.
- `architecture/46_serialization.md`: `domain/shopify/results.py` gets three new frozen dataclasses; the query builds them via the new domain normalization function and calls `asdict()` per item before returning — same shape as every existing Shopify query's `asdict(serialize_x(row))` pattern, adapted for a raw-dict source instead of an ORM row.
- `architecture/28_roles_permissions.md`: Confirms flat `role_name`/`require_roles([...])` is the actual enforced gate in this codebase (re-confirmed by reading `routers/utils/roles.py` and `routers/api_v1/shopify.py` directly) — this plan adds `SELLER` to the existing gate list for this one route only, not to any other existing Shopify route.
- `architecture/15_testing.md`: Test-tier placement — domain functions need zero mocking; infra unit tests mock `execute_shopify_graphql`; the query's integration test mocks the infra function (not `httpx`) and uses a real Postgres-backed `ShopifyShopIntegration` row, per this repo's existing `test_shopify_admin_queries.py` fixture style.

### Local extensions loaded

- `architecture/07_queries_local.md`: Loaded to explicitly confirm its offset-pagination section is out of scope for this plan (see above) — not because it changes this query's shape.
- `architecture/46_serialization_local.md`: Confirmed empty stub — canonical pattern followed directly, matching every prior Shopify plan.

### File read intent — pattern vs. relational

- **How to write** → contracts listed above (`06_commands.md`, `07_queries.md`, `09_routers.md`, `46_serialization.md`, `19_integrations.md`).
- **What exists** → reading is legitimate for the files below (existing behavior, field names, module connections this plan's new code must match or call into).

Permitted for this plan (all already read once during drafting; re-read only to confirm nothing changed before implementation):
- `app/beyo_manager/routers/api_v1/shopify.py` — exact existing route/role-gate/`ServiceContext`-construction shape; exact place to add the new route and the `SELLER` import.
- `app/beyo_manager/services/queries/shopify/list_shopify_shop_integrations.py`, `get_shopify_scope_status.py` — exact existing query-file shape (`asdict(serialize_x(row))` list pattern, `select().where(workspace_id, is_deleted)` ordering) this plan's new query matches.
- `app/beyo_manager/services/infra/shopify/graphql_client.py`, `webhook_subscription_client.py`, `shop_client.py` — exact `execute_shopify_graphql` call signature, `raise_for_graphql_user_errors` usage, and the existing GraphQL-query-as-triple-quoted-string-constant-plus-async-function file shape this plan's new infra module matches.
- `app/beyo_manager/domain/shopify/results.py`, `serializers.py`, `scopes.py`, `enums.py` — exact existing dataclass/serializer conventions, `has_all_required_scopes` signature, and `ShopifyIntegrationStatusEnum.ACTIVE` value this plan reuses.
- `app/beyo_manager/models/tables/shopify/shopify_shop_integration.py` — exact column names (`workspace_id`, `shop_domain`, `access_token_encrypted`, `granted_scopes`, `status`, `is_deleted`, `client_id`) for the new query's `select()`.
- `app/beyo_manager/errors/base.py`, `validation.py`, `external_service.py`, `__init__.py` — exact `DomainError`/`ValidationError`/`ExternalServiceError` constructor signatures and `http_status` attributes (not the canonical `code`-attribute shape described in `05_errors.md` — this codebase's actual errors use `http_status`, confirmed by direct read).
- `app/beyo_manager/services/context.py`, `services/run_service.py`, `services/outcome.py` — exact actual `ServiceContext`/`run_service`/`StatusOutcome` shape (no `.warnings`, `identity` is a plain dict via `.get(...)`, not the canonical raising-property shape in `04_context.md`) — confirmed by direct read, per decision 9.
- `app/beyo_manager/routers/utils/roles.py` — confirmed `ADMIN`, `MANAGER`, `SELLER`, `WORKER` constants.
- `app/tests/unit/test_shopify_router.py`, `app/tests/integration/services/queries/shopify/test_shopify_admin_queries.py`, `app/tests/unit/services/infra/shopify/test_webhook_subscription_client.py` — exact existing test fixture/mocking shape this plan's new tests match.

### Skill selection

- Primary skill: `none` — this is a document-only, no-Python-tooling planning session (`backend_contract_goal_mapping_guide.md`'s "Document-only protocol").
- Router trigger terms: `none` beyond the goal bundle itself.
- Excluded alternatives: none — no other skill in this repo's skill set applies to drafting an implementation plan document.

### Contracts intentionally not selected for this plan

- `03_models.md`, `30_migrations.md`: No new table, column, or migration.
- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`: No task type, queue, or worker code — this is a synchronous, inline Shopify call (an accepted exception per `57_shopify_integration.md`'s rule, which only mandates the worker path for *writes*/subscription management, not a bounded read call gated by explicit limits; see "Resolved decisions" item 6 for why the bound is safe to keep inline).
- `13_sockets.md`, `56_realtime_layer.md`: No realtime/event surface.
- `34_file_storage.md`, `20_api_versioning.md`, `35_gdpr_erasure.md`, `36_audit_log.md`, `37_scheduled_jobs.md`: Not relevant.
- `25_soft_delete.md`: `ShopifyShopIntegration.is_deleted` is already filtered exactly like every other Shopify query — no new soft-delete semantics introduced.
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: No deployment/observability change — reuses the existing web process, no new worker to deploy.

## Implementation plan

1. **`domain/shopify/results.py`** — add three frozen dataclasses (placed after the existing `ShopifyShopIntegrationResult`/history dataclasses):
   ```python
   @dataclass(frozen=True)
   class ShopifyCustomerLookupCoordinatesResult:
       latitude: float | None
       longitude: float | None

   @dataclass(frozen=True)
   class ShopifyCustomerLookupAddressResult:
       street_address: str | None
       post_code: str | None
       coordinates: ShopifyCustomerLookupCoordinatesResult
       city: str | None
       district: str | None

   @dataclass(frozen=True)
   class ShopifyCustomerLookupResult:
       shop_integration_id: str
       shop_domain: str
       match_type: str
       matched_value: str
       order_id: str | None
       order_name: str | None
       customer_id: str | None
       display_name: str | None
       primary_phone_number: str | None
       primary_email: str | None
       address: ShopifyCustomerLookupAddressResult
   ```
   `asdict()` on `ShopifyCustomerLookupResult` deep-converts the nested dataclasses automatically — no manual nested-`asdict` calls needed in the query.

2. **`domain/shopify/customer_lookup.py`** (new file) — pure functions, zero I/O:
   - `filter_shopify_order_line_item_exact_matches(order_nodes: list[dict], *, identity_type: Literal["sku", "barcode"], identity_value: str) -> list[dict]` — for each raw order node (as shaped by the infra layer's GraphQL query, see step 3), walks `order["lineItems"]["edges"]`; keeps the order if any line item's `sku` (sku path, trimmed exact match) or `variant["barcode"]` (barcode path, trimmed exact match against the original `identity_value`) matches exactly.
   - `normalize_shopify_customer_lookup_result(order_node: dict, *, shop_integration_id: str, shop_domain: str, match_type: Literal["sku", "barcode"], matched_value: str) -> ShopifyCustomerLookupResult` — maps one raw order node into the result dataclass:
     - `order_id`/`order_name` from `order_node["id"]`/`order_node["name"]`.
     - `customer_id` from `order_node["customer"]["id"]` (customer may be `None` for guest/POS checkouts with no linked `Customer` record — guard with `or {}`; `customer_id` is simply `None` in that case, no fallback — there is no address-level equivalent of a customer id).
     - `display_name`: **this is Shopify's own account display name, not necessarily the shipping recipient's name** — first non-blank of `customer.displayName` (Shopify's computed "first + last name" for the linked `Customer` account, shown in the Shopify admin customer list), then a name built from `shippingAddress.firstName`+`shippingAddress.lastName`, then `billingAddress.firstName`+`billingAddress.lastName`, then `customer.defaultAddress.firstName`+`.lastName` — same source priority order as `address` below, since a guest/POS order with no linked customer still normally has a shipping name. Join `firstName`/`lastName` with a single space, trimmed; a tier with only one of the two names present uses just that one; a tier with neither is skipped. `None` only if every tier is empty.
     - `primary_email`: first non-blank of `customer.defaultEmailAddress.emailAddress` (guard `customer.get("defaultEmailAddress") or {}` — the sub-object itself may be `null`), `order.email`.
     - `primary_phone_number`: first non-blank of `customer.defaultPhoneNumber.phoneNumber` (guard `customer.get("defaultPhoneNumber") or {}`), `order.phone`, `shippingAddress.phone`, `billingAddress.phone`, `customer.defaultAddress.phone`.
     - `address`: built from the first non-empty of `shippingAddress`, `billingAddress`, `customer.defaultAddress` (in that priority order) — `street_address` from `address1` (fallback `address2`), `post_code` from `zip`, `city` from `city`, `district` from first non-blank of `province`, `provinceCode` (never `company` — see "Resolved decisions" item 13), `coordinates` from `latitude`/`longitude` (both `None` if Shopify didn't supply them — never defaulted to `0`).
   - Both functions take plain `dict` input (the shape returned by the infra layer) and have no SQLAlchemy/HTTP/Redis import — matches `08_domain.md`'s purity rule exactly (normalization/classification of an already-fetched value, same category as `normalize_shop_domain` elsewhere in this same domain package).

3. **`services/infra/shopify/product_identity_client.py`** (new file) — the low-level Shopify GraphQL adapter, matching `webhook_subscription_client.py`'s file shape (query/mutation strings as module constants, plain async functions, `execute_shopify_graphql` for transport):
   ```python
   FIND_VARIANTS_BY_BARCODE_QUERY = """
   query FindVariantsByBarcode($searchQuery: String!, $first: Int!) {
     productVariants(first: $first, query: $searchQuery) {
       edges { node { id sku barcode } }
     }
   }
   """

   SEARCH_ORDERS_BY_SKU_QUERY = """
   query SearchOrdersBySku($searchQuery: String!, $ordersFirst: Int!, $lineItemsFirst: Int!) {
     orders(first: $ordersFirst, query: $searchQuery, sortKey: CREATED_AT, reverse: true) {
       edges {
         node {
           id
           name
           email
           phone
           customer {
             id
             displayName
             defaultEmailAddress { emailAddress }
             defaultPhoneNumber { phoneNumber }
             defaultAddress { firstName lastName address1 address2 city province provinceCode zip phone latitude longitude }
           }
           shippingAddress { firstName lastName address1 address2 city province provinceCode zip phone latitude longitude }
           billingAddress  { firstName lastName address1 address2 city province provinceCode zip phone latitude longitude }
           lineItems(first: $lineItemsFirst) {
             edges { node { sku variant { id sku barcode } } }
           }
         }
       }
     }
   }
   """
   ```
   - `_ORDERS_FIRST = 10`, `_LINE_ITEMS_FIRST = 20`, `_VARIANTS_FIRST = 5` module constants (decision 6).
   - `_quote_shopify_search_term(value: str) -> str` — escaping helper (decision 7).
   - `_search_orders_by_sku(*, shop_domain, access_token_encrypted, sku) -> list[dict]` — calls `execute_shopify_graphql` with `SEARCH_ORDERS_BY_SKU_QUERY`, `operation_name="search_orders_by_sku"`, returns the list of `edges[].node` dicts (empty list if none).
   - `_find_variants_by_barcode(*, shop_domain, access_token_encrypted, barcode) -> list[dict]` — same shape for `FIND_VARIANTS_BY_BARCODE_QUERY`, `operation_name="find_variants_by_barcode"`.
   - `fetch_shopify_orders_by_product_identity(*, shop_domain: str, access_token_encrypted: str, identity_type: Literal["sku", "barcode"], identity_value: str) -> list[dict]` — the single public entry point matching the intention's low-level-service input contract (minus `shop_integration_id`, which the caller already has and does not need round-tripped): for `"sku"`, delegates directly to `_search_orders_by_sku`; for `"barcode"`, calls `_find_variants_by_barcode`, filters to variants whose `barcode` exactly equals `identity_value`, collects distinct non-blank `sku` values, calls `_search_orders_by_sku` once per distinct SKU, and merges/dedupes the resulting order nodes by `id`. Returns `[]` early if no exact-matching variant/SKU is found — no order search is attempted.
   - No `ShopifyGraphQLError` handling inside this file — errors propagate to the caller (the query layer), matching every other infra function in this package (`shop_client.py`, `webhook_subscription_client.py` do not catch `ShopifyGraphQLError` either).

4. **`services/queries/shopify/lookup_shopify_customers_by_product_identity.py`** (new file):
   - `ShopifyProductIdentityLookupRequest(BaseModel)`: `article_number: str | None = None`, `sku: str | None = None`; a `field_validator(mode="before")` on both fields trims and converts blank strings to `None`; a `model_validator(mode="after")` raises `ValueError` if both end up `None` (converted to `ValidationError` in `parse_shopify_product_identity_lookup_request`, per decision 8 / `06_commands.md`'s pattern).
   - `_REQUIRED_SCOPES: tuple[str, ...] = ("read_orders", "read_products", "read_customers")` module constant.
   - `async def lookup_shopify_customers_by_product_identity(ctx: ServiceContext) -> dict`:
     1. `request = parse_shopify_product_identity_lookup_request(ctx.incoming_data)`.
     2. Fetch active integrations: `select(ShopifyShopIntegration).where(ShopifyShopIntegration.workspace_id == ctx.workspace_id, ShopifyShopIntegration.is_deleted.is_(False), ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE)`.
     3. For each integration: if `not has_all_required_scopes(_REQUIRED_SCOPES, integration.granted_scopes or ())`, append `{"shop_integration_id": integration.client_id, "shop_domain": integration.shop_domain, "error_code": "missing_required_scope"}` to `failed_shops` and continue (do not count toward `attempted`).
     4. Otherwise (an "attempted" shop — append `integration.client_id` to a running `attempted_shop_ids: list[str]` so step 6 can check every attempted shop was accounted for), call a private `_lookup_customer_matches_for_shop(integration, request)` helper that: if `request.sku` is set, tries `identity_type="sku"` first (`fetch_shopify_orders_by_product_identity` → `filter_shopify_order_line_item_exact_matches` → `normalize_shopify_customer_lookup_result` per match); then, only if that sku attempt produced zero matches (or `request.sku` was never set at all), and only if `request.article_number` is set, tries `identity_type="barcode"`, `identity_value=request.article_number`. (If neither condition for a barcode attempt holds — e.g. `sku` was set, found nothing, and `article_number` was never supplied — the shop simply contributes zero matches, no error.) The whole per-shop attempt (both the sku call and any barcode fallback call) is wrapped in one `try/except ShopifyGraphQLError as exc` (imported from `beyo_manager.errors.external_service`, since it is not re-exported from `beyo_manager.errors`'s `__all__`), appending `{"shop_integration_id": integration.client_id, "shop_domain": integration.shop_domain, "error_code": exc.error_code}` to `failed_shops` and yielding no matches for that shop on failure (decision 5's per-shop isolation).
     5. Aggregate every shop's matches into one flat list; `customer_matches = [asdict(m) for m in all_matches]`.
     6. Apply decision 5's all-failed check: `graphql_failed_ids = {f["shop_integration_id"] for f in failed_shops if f["error_code"] != "missing_required_scope"}`; if `attempted_shop_ids` is non-empty, `customer_matches` is empty, and `set(attempted_shop_ids) == graphql_failed_ids`, raise `ExternalServiceError("All Shopify shop lookups failed.")`.
     7. Return `{"customer_matches": customer_matches, "failed_shops": failed_shops}`.

5. **`routers/api_v1/shopify.py`**:
   - Change the role import line (`from beyo_manager.routers.utils.roles import ADMIN, MANAGER`) to `from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER`.
   - Add `ShopifyProductIdentityCustomerLookupBody(BaseModel)`: `article_number: str | None = None`, `sku: str | None = None` (structural only — no validators; business validation is the query's job per decision 8).
   - Add, after the existing `/scopes` route and before `/oauth/callback` (keeping the unauthenticated OAuth callback last, matching the file's existing ordering):
     ```python
     @router.post("/customers/by-product-identity")
     async def lookup_shopify_customers_by_product_identity_route(
         body: ShopifyProductIdentityCustomerLookupBody,
         claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
         session: AsyncSession = Depends(get_db),
     ):
         outcome = await run_service(
             lookup_shopify_customers_by_product_identity,
             ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
         )
         if not outcome.success:
             return build_err(outcome.error)
         return build_ok(outcome.data)
     ```
   - Import the new query function alongside the other `services.queries.shopify` imports.
   - This route's static path (`/customers/by-product-identity`) does not share a prefix segment with any existing `/shops/{shop_integration_id}` wildcard route, so `09_routers.md`'s route-declaration-order rule is not in play here — no reordering of existing routes is needed.

6. **Tests**:
   - `app/tests/unit/domain/shopify/test_customer_lookup.py` (new): `filter_shopify_order_line_item_exact_matches` — matches on exact sku, rejects a fuzzy/partial sku match, matches on exact `variant.barcode`, rejects a barcode belonging to a different line item in the same order. `normalize_shopify_customer_lookup_result` — fixtures use the corrected GraphQL shape, e.g. `customer = {"id": ..., "displayName": ..., "defaultEmailAddress": {"emailAddress": "..."}, "defaultPhoneNumber": {"phoneNumber": "..."}, "defaultAddress": {...}}`, **not** the old flat `customer = {"email": "...", "phone": "..."}` shape — one test per fallback tier for email (`customer.defaultEmailAddress.emailAddress` present -> `defaultEmailAddress` is `null`/missing, falls back to `order.email` -> both blank -> `None`), phone (`customer.defaultPhoneNumber.phoneNumber` -> `order.phone` -> `shippingAddress.phone` -> `billingAddress.phone` -> `customer.defaultAddress.phone` -> all blank -> `None`), display_name (`customer.displayName` present -> no linked customer but `shippingAddress` has a name -> shipping blank but `billingAddress` has a name -> both address name fields blank but `customer.defaultAddress` has a name -> every tier blank -> `None`; also a partial-name case, `firstName` only or `lastName` only, joins to just that one name with no stray space), and address (shipping present -> billing fallback -> customer default address fallback -> all absent produces an all-`None` `ShopifyCustomerLookupAddressResult` with `coordinates=(None, None)`, never a `KeyError`; a dedicated `district` test asserts a `company` value on the address fixture is never read into `district`, since `company` is not even part of this plan's normalized shape). Zero mocking, per `15_testing.md`'s domain-function tier.
   - `app/tests/unit/services/infra/shopify/test_product_identity_client.py` (new), mirroring `test_webhook_subscription_client.py`'s `monkeypatch.setattr(".../product_identity_client.execute_shopify_graphql", _fake_execute)` shape: sku path calls `SEARCH_ORDERS_BY_SKU_QUERY` once and returns mapped order nodes; barcode path calls `FIND_VARIANTS_BY_BARCODE_QUERY` then `SEARCH_ORDERS_BY_SKU_QUERY` once per distinct exact-matching variant SKU, deduping by order `id`; a barcode with zero exact-matching variants returns `[]` and never calls the order search; `_quote_shopify_search_term` escapes an embedded `"` and `\`.
   - `app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py` (new), seeding real `ShopifyShopIntegration` rows (mirroring `test_shopify_admin_queries.py`'s `_seed_integration` helper) and monkeypatching `fetch_shopify_orders_by_product_identity` on the query module (never `httpx`/`execute_shopify_graphql` directly, per `19_integrations.md`'s integration-test-isolation rule):
     - Request with only `sku` finds a match.
     - Request with only `article_number` finds a match via the barcode path.
     - Both provided, sku finds a match (barcode path never invoked for that shop — assert the fake function's barcode-path call count is zero).
     - Both provided, sku finds nothing, barcode finds a match (assert both paths were invoked for that shop, in that order).
     - Neither provided raises `ValidationError` before any DB query or Shopify call.
     - Two active shops both return distinct matches -> both appear in `customer_matches`, each with correct `shop_integration_id`/`shop_domain`.
     - One shop's fake function raises `ShopifyGraphQLNonRetryableError` while another shop succeeds -> the failing shop appears in `failed_shops`, the succeeding shop's match is still present, response is still `200`.
     - Every active shop's fake function raises `ShopifyGraphQLError` and zero matches exist -> `ExternalServiceError` is raised.
     - Zero active shop integrations for the workspace -> `{"customer_matches": [], "failed_shops": []}`, no error.
     - A shop with `granted_scopes` missing `read_products` is skipped (`missing_required_scope` in `failed_shops`, fake function never called for that shop) and does not count toward the all-failed condition.
     - A shop with `granted_scopes` missing `read_customers` (but present `read_orders`/`read_products`) is skipped the same way — `missing_required_scope` in `failed_shops`, fake function never called for that shop, does not count toward the all-failed condition. This is a distinct test from the `read_products` case above, not a parametrized variant folded into it, since `read_customers` is the scope this plan newly introduces and is the one most likely to be missing on already-connected shops.
     - A shop belonging to a different workspace, or a soft-deleted/non-`ACTIVE`-status shop, is never queried (workspace isolation + status filter).
   - `app/tests/unit/test_shopify_router.py` (extended): add three new rows (one per `role_name` — `admin`, `manager`, `seller`) to the existing `test_new_shopify_shared_role_routes_call_service_with_expected_context`-style parametrized cases, each asserting `200` and the correct `ctx.incoming_data` for `POST /customers/by-product-identity`. **Do not add this new route to the existing `test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic` parametrization** — that test's route list is for routes where `seller` is rejected, which does not include this one; leave that list exactly as-is. Instead add one new, separate test asserting a `worker` JWT gets `403` with zero `run_service` calls on this route specifically. Also assert the response body never contains `access_token_encrypted` or `granted_scopes`-shaped raw text, matching the existing test's secret-leak assertions.

## Risks and mitigations

- Risk: Shopify's order search `sku:` filter behaves as a fuzzy/tokenized text match (documented Shopify search behavior for several other fields), returning orders whose line items merely *contain* the searched substring rather than matching it exactly.
  Mitigation: Decision 2's domain-layer `filter_shopify_order_line_item_exact_matches` re-checks every candidate order's line items for a true exact match before any order is normalized or returned — the GraphQL search is treated purely as a candidate-narrowing step, never as the source of truth for "is this an exact match."
- Risk: A SKU is shared across multiple products/variants (common in real Shopify catalogs for bundles or resized variants), so the barcode-resolved SKU search could return orders unrelated to the specific barcode scanned.
  Mitigation: Decision 2(b) explicitly re-validates the *original* `article_number` against each candidate line item's `variant.barcode` (not the intermediate resolved SKU) before accepting a match — a shared-SKU false positive is filtered out at this step.
- Risk: This plan's inline (non-worker) Shopify GraphQL call appears to conflict with `57_shopify_integration.md`'s "Never call Shopify's API inline from an HTTP request handler" rule.
  Mitigation: That rule's stated scope and rationale (see the same document's "Worker & queue wiring" and "Rules" sections) is about *mutating* Shopify state (webhook subscription create/remove) and about not blocking the request cycle on retryable, potentially-slow write operations — the one existing inline exception already in the codebase is the OAuth token exchange, justified by "the merchant's browser is synchronously waiting." This plan's calls are read-only, explicitly bounded (decision 6: max 10 orders + 5 variants per shop, no unbounded loop), and the entire feature's value proposition is a synchronous answer to a scan-time question — making it async/worker-based would require a poll/webhook-callback UX this feature does not need. This tradeoff is called out explicitly here rather than silently deviating from the contract; if a future review disagrees, the fix is to move `lookup_shopify_customers_by_product_identity`'s Shopify calls behind a new task type and have the frontend poll, which would be a materially larger, separate plan.
- Risk: A workspace with many active Shopify shops makes this endpoint slow (one sequential round trip per shop, each potentially two sequential Shopify calls on the barcode fallback path).
  Mitigation: Explicitly accepted for this first implementation, matching the intention's own "For now, this implementation can be synchronous if the expected query is lightweight" allowance — per-shop calls could be parallelized with `asyncio.gather` in a later iteration if real-world shop counts per workspace make this a problem; not attempted here to keep the first implementation's error-aggregation logic (decision 5) simple and easy to reason about sequentially.
- Risk: A future contributor adds a field to `SEARCH_ORDERS_BY_SKU_QUERY`'s response that happens to be Shopify-secret-shaped (e.g., a raw payment or token field) and it flows straight into `ShopifyCustomerLookupResult`.
  Mitigation: `normalize_shopify_customer_lookup_result` only ever reads the specific named keys documented in "Implementation plan" step 2 — there is no `**raw_node` passthrough or generic dict merge anywhere in the normalization function, so an unexpected new GraphQL field simply has no path into the response without an explicit code change to the normalizer (which the unit tests in step 6 would need to be updated to cover).
- Risk: A real order containing the scanned SKU/barcode exists in Shopify but falls outside whatever historical window `read_orders` actually grants for this app's install type (see "Scope" assumptions) — the caller sees an ordinary empty/no-match result and has no way to distinguish "never sold" from "sold too long ago to be visible to this scope."
  Mitigation: Accepted for this first implementation, consistent with the intention's explicit "no match anywhere is not an error" requirement — Shopify itself gives no signal to distinguish these two cases via this query shape, so there is nothing this plan's code could check for. If this proves to matter in practice, the fix is requesting `read_all_orders` (a separate Shopify approval/scope change, not a code change) and adding it to `_REQUIRED_SCOPES` and `SHOPIFY_APP_SCOPES` — out of scope here.

## Validation plan

- `pytest app/tests/unit/domain/shopify/test_customer_lookup.py`: exact-match filtering and every email/phone/address fallback tier pass.
- `pytest app/tests/unit/services/infra/shopify/test_product_identity_client.py`: sku path, barcode path (including zero-exact-match short-circuit and multi-SKU dedupe), and search-term escaping pass.
- `pytest app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py`: full orchestration matrix from "Implementation plan" step 6 passes against a real Postgres-backed `ShopifyShopIntegration`, with the infra call monkeypatched (no real Shopify HTTP call).
- `pytest app/tests/unit/test_shopify_router.py`: role-gating (`ADMIN`/`MANAGER`/`SELLER` allowed, `WORKER` rejected) and no-secret-leak assertions pass for the new route.
- Manual/documented check: confirm against the live Shopify Admin GraphQL schema for `SHOPIFY_API_VERSION` (`2026-01`) that `orders(query: String)` supports a `sku:` filter, that `Customer.defaultEmailAddress.emailAddress`/`Customer.defaultPhoneNumber.phoneNumber` are the current (non-deprecated) customer contact fields, and that `ProductVariant.barcode`/`Order.shippingAddress`/`Order.billingAddress`/`Customer.defaultAddress` expose `latitude`/`longitude` as documented — flagged in "Scope" as an assumption to reconfirm before merging, not a blocking unknown for this plan's design.
- Manual/documented check: add `read_customers` to `SHOPIFY_APP_SCOPES` in every environment config (local/staging/production) before this route is exercised against a real shop, and confirm at least one existing connected shop's Route 4 reauthorize flow successfully upgrades `granted_scopes` to include it — this is a real deployment step this plan introduces, not merely a code change.
- Manual/documented check: confirm this app's actual granted-scopes/install-type behavior for `read_orders`'s historical order-access window (60-day rolling window vs. full history) for at least one real connected shop, per "Scope" assumptions and the corresponding entry in "Risks and mitigations" — informs whether `read_all_orders` needs to be requested in a follow-up plan, does not block this plan's merge.

## Review log

- `2026-07-09` `Codex`: Drafted this implementation plan after reading the existing Shopify integration end-to-end (`57_shopify_integration.md`, `routers/api_v1/shopify.py`, `services/queries/shopify/*`, `services/infra/shopify/*`, `domain/shopify/*`, `models/tables/shopify/shopify_shop_integration.py`, `errors/*`, `services/context.py`, `services/run_service.py`) directly, and confirmed this codebase's actual `ServiceContext`/error-class shape diverges from the canonical `04_context.md`/`05_errors.md` text in ways that matter for this plan (no `ctx.warnings`, `http_status` not `code`). Chose the variant-resolve-then-order-search strategy for the barcode path per the intention's explicit instruction not to assume direct barcode searchability on orders. No blockers found.
- `2026-07-09` `David` (review correction): Corrected three Shopify Admin GraphQL API accuracy issues against current Shopify documentation: (1) added `read_customers` as a third required scope (decision 3, Scope assumptions, acceptance criterion 7, `_REQUIRED_SCOPES`) — the `customer { ... }` field selection this plan needs is gated behind it, and it was missing from the original draft entirely; (2) replaced `customer.email`/`customer.phone` with `customer.defaultEmailAddress.emailAddress`/`customer.defaultPhoneNumber.phoneNumber` (decision 12) — current Shopify Admin API models customer contact info as sub-objects, not flat scalars, on the `Customer` type; (3) removed `company` from the `district` fallback chain (decision 13) — `MailingAddress.company` is an organization name, not a district/region, and mapping it in was a semantic error in the original draft. Updated every affected section (Scope, Resolved decisions, Acceptance criteria, Implementation plan's GraphQL query and normalization spec, Tests, Validation plan) consistently. The barcode-via-variant-resolution strategy (decision 1) was reviewed and confirmed correct as originally designed — no change.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
