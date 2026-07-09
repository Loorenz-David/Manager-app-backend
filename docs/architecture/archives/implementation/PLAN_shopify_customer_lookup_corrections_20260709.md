# PLAN_shopify_customer_lookup_corrections_20260709

## Metadata

- Plan ID: `PLAN_shopify_customer_lookup_corrections_20260709`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T00:00:00Z`
- Last updated at (UTC): `2026-07-09T11:50:47Z`
- Related issue/ticket: Post-implementation review findings for `PLAN_shopify_customer_lookup_by_product_identity_20260709` (archived) — corrective follow-up, not a new capability.
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_customer_lookup_by_product_identity_20260709.md`
- Parent plan (implemented and archived): `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_by_product_identity_20260709.md` — this plan corrects gaps found in a post-implementation review of that plan's delivered code, documented in that plan's own review log dated `2026-07-09` (`David` review correction entry) and in the conversation that produced this plan. It does not redo or reopen any of that plan's already-correct design decisions (barcode-via-variant-resolution strategy, `read_customers` scope addition, `defaultEmailAddress`/`defaultPhoneNumber` field usage, `district` mapping — all confirmed correct on review).
- Related summary (source of the review): `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`

## Goal and intent

- Goal: Close four gaps a post-implementation review found in the already-shipped Shopify customer-lookup-by-product-identity capability: (1) no automated test exists that verifies workspace isolation / soft-delete exclusion / active-status filtering on the new query — the only "integration-shaped" test that was written is actually a unit test whose fake DB session ignores the real SQL filter entirely; (2) a null-token edge case can silently break the per-shop failure-isolation guarantee; (3) a router test was patched in a way that contradicts the original plan's explicit instruction and now reads as self-contradictory; (4) the frontend handoff document was never updated with the new route, violating `57_shopify_integration.md`'s explicit "don't let it drift" rule.
- Business/user intent: The underlying feature (scan a SKU/barcode, find the customer) already works and is deployed — this plan is entirely about closing verification and documentation gaps around it, not changing its behavior for end users. The one behavior change (item 2, the token-fallback fix) is a defensive correction, not a new feature.
- Non-goals:
  - No change to the GraphQL query strategy, scope list, normalization/fallback priority rules, or response shape established by the parent plan — all of that was reviewed and confirmed correct.
  - No new route, no new query/command, no new domain capability.
  - No change to `SHOPIFY_APP_SCOPES` deployment configuration itself (that remains an operational step outside this repo, per the parent plan's "Validation plan").

## Scope

- In scope:
  - Add `app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py` — a real-Postgres-backed integration test verifying workspace isolation, soft-delete exclusion, and `ACTIVE`-status filtering for `lookup_shopify_customers_by_product_identity`, mirroring this exact repo's own established pattern in `test_shopify_admin_queries.py`.
  - Fix `services/queries/shopify/lookup_shopify_customers_by_product_identity.py`: treat a missing/blank `access_token_encrypted` on an attempted shop as an immediate per-shop failure (`failed_shops` entry), not a silent `""` passed into Shopify's GraphQL client.
  - Fix `app/tests/unit/test_shopify_router.py`: remove the new route from `test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic`'s parametrization (and its now-unnecessary special-case branch), and add one small, separate, correctly-named test asserting `worker` is rejected on `POST /customers/by-product-identity` specifically.
  - Update `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` with the new route's contract (request/response shape, roles, error cases), per `57_shopify_integration.md`'s explicit requirement.
- Out of scope:
  - Any change to `domain/shopify/customer_lookup.py`'s normalization/fallback logic (reviewed, correct).
  - Any change to `services/infra/shopify/product_identity_client.py`'s GraphQL query text or barcode/SKU resolution strategy (reviewed, correct).
  - The address-tier-selection edge case noted in review (an address with only `phone`/`latitude`/`longitude` and no street fields could be skipped in favor of a lower-priority tier) — this is a documented, accepted low-severity tradeoff, not fixed here; revisit only if it causes a real observed issue.
  - Re-litigating the `read_orders` 60-day-order-window or `read_all_orders` question — already documented as an accepted, deferred limitation in the parent plan.
- Assumptions:
  - The integration test suite's `db_session` fixture (`app/tests/conftest.py`) and this domain's own seed helpers (`_seed_workspace_and_user`, `_seed_integration` in `test_shopify_admin_queries.py`) are usable as-is and require no changes — confirmed by direct read.
  - CI has real Postgres access even though this local/sandboxed session does not (the original implementation's inability to run a DB-backed test in-sandbox is why the gap exists at all) — the new integration test is expected to run in CI, not necessarily in this sandbox.

## Clarifications required

None. All four items are concrete, independently fixable, and were fully specified during the review that produced this plan.

## Resolved decisions

1. **The integration test is additive, not a replacement for the existing fake-session unit test.** `app/tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py` already correctly covers the query's *business logic* (SKU-first/barcode-fallback ordering, missing-scope skip, per-shop `ShopifyGraphQLError` isolation, all-shops-failed condition) with a fast fake session — that coverage is good and is kept unchanged. What's missing is coverage of the *SQL filter itself* (`workspace_id`, `is_deleted`, `status`), which a fake session that ignores its query argument structurally cannot verify. The new integration test's job is narrower and specific: prove that a shop in another workspace, a soft-deleted shop, and a non-`ACTIVE`-status shop are each excluded by the real query — it does not need to re-verify SKU/barcode business logic (that's the unit test's job), so it can use a minimal `fetch_shopify_orders_by_product_identity` monkeypatch that returns a fixed, trivial match for whichever shop(s) actually get queried, and assert on *which shops* produced a result, not on match content.
2. **Missing/blank `access_token_encrypted` is treated exactly like a missing required scope: a per-shop skip recorded in `failed_shops`, not a call attempt.** Before calling `_lookup_customer_matches_for_shop` for an attempted (sufficient-scope) shop, check `integration.access_token_encrypted` for blankness the same way scope-sufficiency is checked. If blank, append `{"shop_integration_id": ..., "shop_domain": ..., "error_code": "missing_access_token"}` to `failed_shops` and do not call the infra layer at all — no `or ""` fallback, no attempt to decrypt an empty string. This shop's id must still be excluded from `attempted_shop_ids` (same treatment as a missing-scope shop, for the same reason: this is a data/config gap, not a transient external-service failure, so it must not count toward the "all shops failed externally" condition). This mirrors decision 3 from the parent plan exactly, just for a different precondition.
3. **The router test fix restores the parent plan's original, explicit instruction rather than inventing a new pattern.** The parent plan said, in its own words: *"Do not add this new route to the existing `test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic` parametrization... instead add one new, separate test."* The shipped code violated that instruction. This plan simply carries out the original instruction: remove the new route's tuple from that test's parametrize list, remove the `if path == ".../customers/by-product-identity" and role_name == "seller": ... return` branch from the test body (restoring it to a plain, unconditional `assert response.status_code == 403` for every parametrized case, as it was before this route existed), and add a new, small, correctly-named test function for the `worker`-on-this-route-gets-403 case. `seller`-is-allowed coverage already exists correctly in `test_new_shopify_shared_role_routes_call_service_with_expected_context`'s parametrization (row asserting `200` for `role_name="seller"`) — nothing needs to be added there.
4. **The handoff doc gets a new "Route 12" entry, appended after the existing "Route 11," not a renumbering of Routes 10-11.** The existing doc numbers routes 1-9 as JWT-protected admin/query routes (in the router file's declaration order), 10 as the OAuth callback, and 11 as the inbound webhook-delivery route (both Shopify-facing, not frontend-called). The new customer-lookup route is JWT-protected and admin-facing like routes 1-9 — in the router file, it physically sits after Route 9 (`/scopes`) and before Route 10 (`/oauth/callback`) — but renumbering 10→11 and 11→12 would silently invalidate any existing reference to "Route 10"/"Route 11" elsewhere (this doc's own "No-secret guarantee" section counts "9 admin/OAuth-callback routes," and the "Suggested frontend build order" section numbers steps against specific routes). Appending as "Route 12" with an explicit one-line note of its actual router-file position is a smaller, safer diff than renumbering, and matches how this doc already handles routes that were added after the initial numbering pass (Route 11 itself was appended after Route 10 for the same reason, per its own file history). The "No-secret guarantee" section's route count must be updated from 9 to 10 (Route 12 is JWT-protected/admin-facing like routes 1-9, so it belongs in that count; routes 10-11 are the two Shopify-facing exceptions already carved out separately in that sentence).

## Acceptance criteria

1. `app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py` exists and, run against a real database, proves: a shop in a different workspace is never queried or returned; a soft-deleted (`is_deleted=True`) shop in the caller's own workspace is never queried or returned; a shop with a non-`ACTIVE` status (e.g. `DISABLED`, `NEEDS_REAUTH`) in the caller's own workspace is never queried or returned; a shop that is `ACTIVE`, not deleted, and in the caller's workspace **is** queried and its match appears in `customer_matches`.
2. A shop with `access_token_encrypted` equal to `None` or an empty/whitespace-only string is never passed into `fetch_shopify_orders_by_product_identity` — it is skipped exactly like a missing-scope shop, appears in `failed_shops` with `error_code="missing_access_token"`, and does not count toward the "all attempted shops failed externally" `ExternalServiceError` condition.
3. `test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic`'s parametrize list no longer includes `POST /customers/by-product-identity`, and its body no longer contains the `if path == ... and role_name == "seller"` special case — every remaining parametrized case in that test asserts a plain, unconditional `403`.
4. A new, separate unit test asserts: a `worker` JWT on `POST /customers/by-product-identity` gets `403` and zero `run_service` calls.
5. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` documents the new route as "Route 12," including: exact path/method, roles (`admin`, `manager`, `seller` — noting this is the *first* route `seller` can call), request body shape (`article_number`/`sku`, at least one required), a realistic success response example (`customer_matches`/`failed_shops`), and an error table covering `422` (validation), `502` (all shops failed), and `401/403`.
6. The handoff doc's "No-secret guarantee" section's route count is updated from "9" to "10," and the new route's no-secret guarantee (never returns `access_token_encrypted`, never a raw Shopify payload) is implicitly covered by that same sentence — no separate carve-out needed since the existing sentence already states the guarantee for the whole route count.
7. All pre-existing tests in the four touched files continue to pass unchanged in behavior (the router test fix is a like-for-like restructuring, not a coverage reduction — total assertions covering `worker`/`seller` role gating on this route must be equal or greater after the fix, just correctly organized).

## Contracts and skills

### Contracts loaded

- `architecture/15_testing.md`: Integration-test tier definition ("real DB, real app context, no external APIs") and the explicit rule that a list/lookup query's workspace-scoping must be integration-tested — this plan's central requirement. Also governs the "patch on a module, not globally" mocking rule reused for the new test's `fetch_shopify_orders_by_product_identity` monkeypatch.
- `architecture/24_multi_tenancy.md`: The exact guarantee being tested — every multi-tenant query's `workspace_id` filter must be verified, not just written.
- `architecture/25_soft_delete.md`: The soft-delete exclusion guarantee (`is_deleted.is_(False)`) being verified by the same new test.
- `architecture/57_shopify_integration.md`: The explicit "update the frontend handoff doc, don't let it drift" rule this plan's item 4 satisfies; also the query/infra/domain split precedent this plan's code fix (item 2) must continue to respect (the fix stays entirely inside the query's orchestration loop — no infra or domain change).
- `architecture/05_errors.md`: `failed_shops` entries stay in the same minimal, safe shape (`shop_integration_id`, `shop_domain`, `error_code`) already established — the new `"missing_access_token"` error_code follows the same convention as `"missing_required_scope"`, no new error class introduced.
- `architecture/19_integrations.md`: "Integration test isolation... use monkeypatch to replace the provider client, never hit real external APIs" — the new integration test monkeypatches `fetch_shopify_orders_by_product_identity`, exactly as the existing unit test and the parent plan's design intended, just now against a real `db_session` instead of a fake one.

### Local extensions loaded

- None beyond what the parent plan already loaded — this is a narrow corrective plan touching test/doc surfaces, not architecture-shaping code.

### File read intent — pattern vs. relational

- **How to write** → `15_testing.md` for the integration test's shape.
- **What exists** → reading is legitimate for every file this plan touches or must match.

Permitted for this plan (already read once during drafting; re-read only to confirm nothing changed before implementation):
- `app/beyo_manager/services/queries/shopify/lookup_shopify_customers_by_product_identity.py` — exact current code, to apply the minimal token-check fix in place.
- `app/tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py` — exact existing fake-session/fixture shape, confirmed *not* to be touched by this plan (kept as-is).
- `app/tests/integration/services/queries/shopify/test_shopify_admin_queries.py` — exact `_seed_workspace_and_user`/`_seed_integration`/`unique_shop_domain`/`_ctx` helper shapes and `@pytest.mark.integration` + `db_session` fixture usage this plan's new test must copy exactly (not reinvent a new seeding pattern).
- `app/tests/conftest.py` — confirmed `db_session` fixture behavior (function-scoped, rolls back after each test via `get_db()` + `await session.rollback()`).
- `app/tests/unit/test_shopify_router.py` — exact current parametrize lists and the special-case branch to remove.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` — exact existing Route 9/10/11 formatting, the "No-secret guarantee" paragraph, and the "Suggested frontend build order" list this plan's Route 12 entry and edits must match in style.
- `app/beyo_manager/domain/shopify/enums.py` — confirmed `ShopifyIntegrationStatusEnum` member names (`ACTIVE`, `DISABLED`, `NEEDS_REAUTH`, etc.) for the new test's non-active-status fixture.

### Skill selection

- Primary skill: `none` — document-only planning session, no Python tooling executed.
- Excluded alternatives: none.

### Contracts intentionally not selected for this plan

- `06_commands.md`, `07_queries.md`, `09_routers.md`, `46_serialization.md`: No command/query/router/serializer *shape* changes — this plan only adds a guard clause inside an existing query function and adds tests/docs.
- `03_models.md`, `30_migrations.md`: No schema change.
- Everything else the parent plan excluded remains excluded here for the same reasons.

## Implementation plan

1. **Fix `services/queries/shopify/lookup_shopify_customers_by_product_identity.py`** — in the main loop, after the existing scope check and before appending to `attempted_shop_ids`, add a token-blankness check:
   ```python
   for integration in integrations:
       if not has_all_required_scopes(_REQUIRED_SCOPES, integration.granted_scopes or ()):
           failed_shops.append({
               "shop_integration_id": integration.client_id,
               "shop_domain": integration.shop_domain,
               "error_code": "missing_required_scope",
           })
           continue

       if not (integration.access_token_encrypted or "").strip():
           failed_shops.append({
               "shop_integration_id": integration.client_id,
               "shop_domain": integration.shop_domain,
               "error_code": "missing_access_token",
           })
           continue

       attempted_shop_ids.append(integration.client_id)
       try:
           all_matches.extend(await _lookup_customer_matches_for_shop(integration=integration, request=request))
       except ShopifyGraphQLError as exc:
           ...
   ```
   Then remove the `access_token_encrypted or ""` fallback from `_lookup_customer_matches_for_identity` (it becomes unreachable/unnecessary once the caller guarantees a non-blank token) and pass `integration.access_token_encrypted` directly — if it can be blank at that point, that is now a bug in the guard above, not something to paper over with a fallback at the call site.

2. **Add `app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py`**:
   - Reuse `unique_shop_domain`, `_seed_workspace_and_user`, `_seed_integration`, and a local `_ctx`-equivalent helper matching `test_shopify_admin_queries.py`'s exact shape (import them or duplicate the small helpers locally — match this test file's existing convention of whether Shopify test modules import shared helpers or redefine them locally before deciding; if no shared test-utility module exists for these helpers, duplicate them locally exactly as `test_shopify_admin_queries.py` does, since that file itself defines them locally rather than importing from a shared fixture module).
   - `test_lookup_shopify_customers_by_product_identity_is_workspace_scoped_and_excludes_soft_deleted_and_inactive_shops(db_session)`:
     - Seed `workspace`/`other_workspace`/`user`.
     - Seed four `ShopifyShopIntegration` rows in `workspace`: one `ACTIVE` (the "eligible" shop), one `ACTIVE` but `is_deleted=True` (must set this directly on the seeded instance after `_seed_integration` returns, then `await db_session.flush()`), one `DISABLED` (non-active status), and one in `other_workspace` that is `ACTIVE`.
     - Monkeypatch `fetch_shopify_orders_by_product_identity` on the query module to return one trivial matching order node (reuse a minimal fixture shaped like the existing unit test's, or the domain test's `_order_node()`-equivalent) for **any** shop it's called with, and additionally assert (via a `calls: list[str]` capture inside the fake, keyed by `shop_domain`) that it was invoked **exactly once**, and only for the eligible `ACTIVE` shop's `shop_domain` — this is the critical assertion that proves the SQL filter, not just the response shape, actually excluded the other three rows.
     - Call `lookup_shopify_customers_by_product_identity` with `sku="SKU-TEST"` and assert: `len(result["customer_matches"]) == 1`, `result["customer_matches"][0]["shop_integration_id"] == eligible.client_id`, `result["failed_shops"] == []`.
   - This one test satisfies acceptance criterion 1's four sub-assertions; a second, small test is optional but not required — do not attempt to re-test SKU/barcode fallback ordering or scope/token-skip logic here, that is the existing unit test's job (decision 1).

3. **Fix `app/tests/unit/test_shopify_router.py`**:
   - Remove `("post", "/api/v1/integrations/shopify/customers/by-product-identity", {"json": {"sku": "SKU-123"}})` from `test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic`'s `path`/`kwargs` parametrize list.
   - Remove the `if path == "/api/v1/integrations/shopify/customers/by-product-identity" and role_name == "seller": ... return` block from that test's body, restoring it to an unconditional `assert response.status_code == 403; assert captured["calls"] == 0`.
   - Add a new, separate test (near the other role-gating tests for this route, or immediately after the shared-role-routes test) asserting `worker` gets `403` with zero `run_service` calls on `POST /customers/by-product-identity` specifically — same `_build_test_client` pattern already used throughout this file.

4. **Update `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md`**:
   - Insert a new section after "## Route 11 — Inbound Shopify webhook delivery..." and before "## No-secret guarantee":
     ```markdown
     ---

     ## Route 12 — Customer lookup by product SKU/barcode

     `POST /api/v1/integrations/shopify/customers/by-product-identity`

     Given a product's SKU and/or barcode (`article_number`), searches every active Shopify shop integration in the caller's workspace for a matching order line item and returns normalized customer/address information for each match. This is the first Shopify route `seller` (not just `admin`/`manager`) can call.

     **Note on position:** in `routers/api_v1/shopify.py` this route is declared right after Route 9 (`/scopes`) and before Route 10 (`/oauth/callback`) — it is numbered 12 here only to avoid renumbering the already-documented Routes 10-11.

     - **Auth:** JWT required. Roles: `admin`, `manager`, `seller`. Workspace-scoped (only searches shops connected to the caller's workspace).

     **Request body:**
     ```json
     { "sku": "ABC-123", "article_number": "0123456789012" }
     ```
     Both fields are optional strings, but at least one (after trimming) is required. SKU is preferred: if `sku` is provided, it's tried first for each shop; `article_number` (Shopify barcode) is only used as a fallback for a shop where the SKU search found nothing, or directly if `sku` was omitted.

     **Success response `data`:**
     ```json
     {
       "customer_matches": [
         {
           "shop_integration_id": "shpint_...",
           "shop_domain": "my-shop.myshopify.com",
           "match_type": "sku",
           "matched_value": "ABC-123",
           "order_id": "gid://shopify/Order/...",
           "order_name": "#1001",
           "customer_id": "gid://shopify/Customer/...",
           "display_name": "Jane Doe",
           "primary_phone_number": "+1234567890",
           "primary_email": "jane@example.com",
           "address": {
             "street_address": "123 Main St",
             "post_code": "12345",
             "coordinates": { "latitude": 59.1, "longitude": 18.2 },
             "city": "Stockholm",
             "district": "Stockholm County"
           }
         }
       ],
       "failed_shops": [
         { "shop_integration_id": "shpint_...", "shop_domain": "other-shop.myshopify.com", "error_code": "missing_required_scope" }
       ]
     }
     ```
     `customer_matches` may be an empty array — this is not an error, it means no shop found a matching line item. `failed_shops` lists shops that were skipped or failed (missing scope, missing token, or a Shopify API error) — their absence from `customer_matches` does not necessarily mean "no match," it may mean "couldn't check." `display_name` is the linked Shopify customer's account name (or, for guest/POS orders with no linked customer, a name derived from the shipping/billing address) — treat it as "best-known name for this match," not a verified identity field. `address`/`coordinates` fields are `null` when Shopify didn't supply them, never `0` or omitted.

     **Errors:**
     | Status | Cause |
     |---|---|
     | 422 `{"error": "sku: At least one of sku or article_number is required.", "ok": false}` | Both `sku` and `article_number` omitted or blank |
     | 502 `{"error": "All Shopify shop lookups failed.", "ok": false}` | Every shop with sufficient scope/token raised a Shopify API error and zero matches were found anywhere |
     | 401/403 | Auth |

     No match anywhere (zero eligible shops, or every shop queried cleanly with nothing found) is a normal `200` with `customer_matches: []`, not an error.
     ```
   - Update the "No-secret guarantee" section's leading count from "the 9 admin/OAuth-callback routes above" to "the 10 admin/OAuth-callback routes above."
   - Add one line to "Suggested frontend build order": e.g. `7. Optional: a scan/lookup UI (barcode scanner or manual SKU entry) → Route 12, for staff resolving a physical item to its customer.`
   - Update the Metadata block's "Source plans" list to append `PLAN_shopify_customer_lookup_by_product_identity_20260709.md` (and, once this plan is archived, this plan too) if the doc's convention is to track every contributing plan — confirm against the existing list's pattern before editing (it currently lists 8 phase plans; follow that same style).

5. **Update the intention plan's linked-plans table** (`INTENTION_shopify_customer_lookup_by_product_identity_20260709.md`): add a row for this corrective plan and a progress note dated `2026-07-09` summarizing that a post-implementation review found and this plan fixes four gaps (test coverage, a defensive fix, a test-quality issue, and doc drift).

## Risks and mitigations

- Risk: The new integration test's `is_deleted=True` mutation on a `_seed_integration`-returned instance doesn't take effect if `_seed_integration` itself sets `is_deleted` via a server-side default that isn't refreshed before the query runs.
  Mitigation: Set `integration.is_deleted = True` on the Python instance and `await db_session.flush()` before the test's `lookup_shopify_customers_by_product_identity` call — this exact pattern (mutate an already-flushed ORM instance, flush again) is already proven to work in this same test module's other tests (e.g. `test_get_shopify_shop_integration_is_workspace_scoped_and_returns_subscription_summary`'s use of a second, differently-scoped integration).
- Risk: Fixing the router test (item 3) accidentally drops real coverage if the removed parametrize row was the *only* place asserting `worker`/`seller` behavior for this specific route.
  Mitigation: Acceptance criterion 4 explicitly requires a replacement test for the `worker`-rejected case; the `seller`-allowed case is already covered elsewhere (`test_new_shopify_shared_role_routes_call_service_with_expected_context`'s existing `seller` row) and untouched by this fix — acceptance criterion 7 requires confirming net coverage is not reduced.
- Risk: Renumbering avoidance in the handoff doc (decision 4) could itself be seen as inconsistent since Route 12 sits physically before Routes 10-11 in the actual router file.
  Mitigation: The new Route 12 entry's "Note on position" line makes this explicit and searchable — a future reader who greps the router file and finds the customer-lookup route between `/scopes` and `/oauth/callback` will not be confused by the doc's route number, because the doc itself explains the discrepancy inline.

## Validation plan

- `pytest app/tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py`: existing business-logic tests still pass unchanged after the token-check fix (none of them exercise a blank-token shop today, so none should need updating — but re-run to confirm no regression).
- `pytest app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py`: new test passes against a real database (CI, not necessarily this sandbox).
- `pytest app/tests/unit/test_shopify_router.py`: full file passes after the parametrize-list fix and the new dedicated `worker`-rejection test.
- Manual/documented check: read the updated handoff doc section once more against the actual router code (`routers/api_v1/shopify.py`) and the actual response shape (`domain/shopify/results.py`'s `ShopifyCustomerLookupResult`/`ShopifyCustomerLookupAddressResult`/`ShopifyCustomerLookupCoordinatesResult`) to confirm the JSON example has no invented or stale field names.

## Review log

- `2026-07-09` `David`: Drafted this corrective plan immediately after a post-implementation review of the parent plan's delivered code found four gaps (missing DB-backed workspace-isolation test, a null-token edge case, a router-test instruction violation, and undocumented frontend handoff drift). No new design decisions were needed — every fix was fully specified during the review itself.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
