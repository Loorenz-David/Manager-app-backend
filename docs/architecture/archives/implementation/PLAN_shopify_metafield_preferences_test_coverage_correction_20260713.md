# PLAN_shopify_metafield_preferences_test_coverage_correction_20260713

## Metadata

- Plan ID: `PLAN_shopify_metafield_preferences_test_coverage_correction_20260713`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T10:00:00Z`
- Last updated at (UTC): `2026-07-13T09:46:13Z`
- Related issue/ticket: `n/a`
- Intention plan: none separate — this plan is derived directly from a code review of the completed feature against `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_20260713.md` and `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_metafield_preferences_20260713.md`. That review's findings are restated below as the acceptance criteria for this plan.

## Goal and intent

- Goal: close the test-coverage gap identified in code review of the Shopify metafield-preferences multi-shop feature, and apply one small, narrowly-scoped behavioral correction — without touching the feature's core business logic, which the review found correct on manual trace against every acceptance criterion in the original plan.
- Business/user intent: the original plan's acceptance criterion 15 ("Automated tests cover multi-shop creation, atomic rollback, per-shop category hydration, per-shop search, authorization, and Shopify failure paths") is **not currently met**. Zero integration tests exist for the command, the query, or the model constraints — despite the plan explicitly naming these three files and despite this exact `tests/integration/...` pattern being actively used by sibling Shopify features in this same codebase. The implementation summary attributed this to the local Postgres connection being unavailable; that blocker is now resolved (`alembic upgrade head` has been run successfully, head is `b4c5d6e7f8a9`), so there is no longer a reason these tests can't be written and run to completion.
- Non-goals: do not change the response shape, routes, model, or migration; do not add partial-success semantics; do not perform real-Shopify-store validation (the dev-store `MetafieldOwnerType` introspection check and real cross-shop-GID rejection against live stores both require Shopify credentials this plan does not assume are available — they remain a separate follow-up); do not "fix" the GID-shape regex or refactor `merge_metafield_preference_with_definition`'s null-handling — the review found both acceptable as-is (see Risks).

## Scope

- In scope:
  1. New integration test file: `tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py`.
  2. New integration test file: `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py`.
  3. New integration test file: `tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py`.
  4. Role-rejection test cases for `POST /metafield-preferences` and `GET /metafield-preferences`, added to `tests/unit/services/shopify/test_metafield_preference_routes.py`.
  5. Missing test cases in `tests/unit/services/infra/shopify/test_metafield_definition_client.py`.
  6. One code fix in `services/commands/shopify/create_shopify_metafield_preferences.py`: the existing-active-row branch should only write `sequence_order`/`updated_by_id` when `sequence_order` actually changes, so a byte-for-byte repeat request is a true no-op (matches the original plan's literal wording, which the shipped code diverged from).
  7. Run the full test suite (new + existing) against the now-migrated local Postgres DB; run `alembic current` to confirm head.
- Out of scope: GID regex tightening; `merge_metafield_preference_with_definition` null-handling refactor (both reviewed and judged non-issues — see Risks); real-Shopify dev-store schema introspection; real cross-shop-GID rejection against live Shopify stores; any change to `get_shopify_metafield_preferences.py`'s logic (only its test coverage is in scope — the review found no defect in that file).
- Assumptions:
  - The migration is applied to the local dev Postgres DB (confirmed by the user: `alembic upgrade head` succeeded, `a3d4e5f6a7b8 -> b4c5d6e7f8a9`). Integration tests can run against it directly.
  - `tests/conftest.py`'s `db_session` fixture (`async for session in get_db(): yield session; await session.rollback()`) is the correct session fixture — same one every existing Shopify integration test uses. Commands under test call `maybe_begin(ctx.session)` internally; since `db_session` isn't pre-wrapped in an outer transaction, a command's `maybe_begin` runs in **owner mode** (opens its own `session.begin()`), so a raised exception inside the command triggers an automatic `session.rollback()` *before* the fixture's own teardown rollback ever runs — this is what makes the atomic-rollback test provable: query the table again after the expected exception and assert zero rows.
  - The exact fixture/helper patterns in `tests/integration/services/commands/shopify/test_shopify_admin_commands.py` (`_seed_workspace_and_user`, `_seed_integration`, `_ctx`) and `tests/integration/models/shopify/test_shopify_foundation_constraints.py` (`_shop_integration`, the `pytest.raises(IntegrityError)` + `await db_session.commit()` + `await db_session.rollback()` constraint-test pattern) are the correct templates to copy, not reinvent. `uuid4().hex[:8]`-suffixed `client_id`s are used throughout these existing tests to avoid collisions across repeated runs against a persistent dev DB (rows are not truncated between runs) — new tests must follow the same suffixing convention.
  - Shopify calls are mocked via `monkeypatch.setattr` on the exact import path used *inside the module under test* (e.g. `"beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id"`), not on the infra module's own path — this is the pattern every existing integration test in this codebase uses, and mocking the wrong path silently no-ops the patch.

## Clarifications required

- [ ] Is the no-op idempotency fix (scope item 6) wanted in this pass, or should this correction be test-only? Default: include it — it's a small, single-conditional change, already scoped precisely below, and was an explicit deviation flagged in review. If the answer is "tests only," skip step 8 below and its corresponding test assertion in step 3's test file.

## Acceptance criteria

1. `pytest backend/app/tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py -m integration` passes and proves: the table and all FKs exist; the partial unique index (`workspace_id, shop_integration_id, item_category_id, shopify_metafield_definition_id`, `is_deleted = false`) rejects a second active row with the same four values (`IntegrityError`); two different shops holding the *same* `shopify_metafield_definition_id` string for the same category are both insertable as independent active rows (this is the model-level proof the whole multi-shop design leans on); a soft-deleted row does not block a new active row with the same four values.
2. `pytest backend/app/tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py -m integration` passes and proves, against the real DB: (a) creating preferences across two valid shops in one request; (b) a failure validating the *second* shop's definition leaves **zero** `ShopifyMetafieldPreference` rows for either shop (atomic rollback); (c) repeating an identical multi-shop request twice does not duplicate rows and is idempotent per shop; (d) each Shopify definition-lookup call receives the exact `shop_domain`/`access_token_encrypted` of *its own* selection's integration — never another selection's, proven by asserting on captured call arguments, not just call count; (e) an integration outside the workspace, or inactive, or soft-deleted, is rejected before any Shopify call or DB write; (f) result ordering matches `request.preferences` order, including when shops are interleaved.
3. `pytest backend/app/tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py -m integration` passes and proves: exactly one batched `fetch_shopify_metafield_definitions_by_ids` call per requested shop (never combining definition IDs across shops); correct per-shop `item_categories`/`unavailable_definition_ids` grouping; `sequence_order` preserved within each shop/category group; requested `shop_integration_ids` order preserved in `shops[]` regardless of DB row order; one requested-shop failure (missing/inactive integration) fails the whole request with no partial `shops[]`; the search flow runs independently per shop with its own result set and is unaffected by `only_my_preferences`; a Shopify failure for one shop's search fails the whole request even if other shops already succeeded.
4. `tests/unit/services/shopify/test_metafield_preference_routes.py` includes at least one case per new route asserting a role outside `[ADMIN, MANAGER, SELLER, WORKER]` (e.g. `field`, or whatever this app's actual lowest-privilege non-listed role is) receives the router's standard 403/forbidden response, mirroring the existing role-matrix pattern in `tests/unit/test_shopify_router.py`.
5. `tests/unit/services/infra/shopify/test_metafield_definition_client.py` gains cases for: case-insensitive name matching; stopping exactly at `SEARCH_RESULTS_LIMIT` mid-page; a node with an empty/missing `name` never matching and never raising; a resolved node that isn't a `MetafieldDefinition` (no `ownerType` in the response) being returned as-is by `fetch_shopify_metafield_definition_by_id`/`fetch_shopify_metafield_definitions_by_ids` (filtering is the caller's job, per the existing design — confirm the function does *not* filter, not that it raises); a `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` raised mid-pagination propagating out of `search_shopify_metafield_definitions_by_name` uncaught.
6. If the clarification above resolves to "include the fix": a repeat create request with an unchanged `sequence_order` leaves the existing row's `updated_at`/`updated_by_id` untouched (proven in test 2 above via a direct column-value assertion before/after the repeat call).
7. Full suite (existing 88 unit tests + new tests) passes; `alembic current` reports `b4c5d6e7f8a9`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/15_testing.md` / `backend/architecture/50_testing_strategy.md`: test conventions and fixture isolation strategy for this codebase.
- `backend/architecture/25_soft_delete.md`: what the constraint test (acceptance criterion 1) and the restore-path assertions in the command test (criterion 2) must verify.
- `backend/architecture/24_multi_tenancy.md`: workspace-isolation assertions required in both integration test files.
- `backend/architecture/57_shopify_integration.md`: Shopify-call mocking boundary conventions (mock the infra function import site inside the module under test, per existing precedent).
- `backend/architecture/06_commands.md` + `06_commands_local.md`: `maybe_begin` owner-mode exception-triggers-rollback semantics — this is the exact mechanism acceptance criterion 2(b) tests.

### File read intent — pattern vs. relational

- **How to write** the new tests → the contracts above, plus the three named existing test files (they *are* the pattern; do not read any other integration test file as a template when these three already cover session setup, seeding, and Shopify mocking).
- **What exists** (legitimate relational reads before writing):
  - `tests/conftest.py` — `db_session` fixture, confirm no other autouse fixture affects this feature's tests.
  - `tests/integration/services/commands/shopify/test_shopify_admin_commands.py` — `_seed_workspace_and_user`, `_seed_integration`, `_ctx` helpers; the `monkeypatch.setattr("beyo_manager.services.commands.shopify.<module_under_test>.<imported_name>", ...)` mocking pattern.
  - `tests/integration/models/shopify/test_shopify_foundation_constraints.py` — `_shop_integration` helper; the `pytest.raises(IntegrityError)` + `db_session.commit()` + `db_session.rollback()` constraint-test shape.
  - `beyo_manager/services/commands/shopify/create_shopify_metafield_preferences.py`, `beyo_manager/services/queries/shopify/get_shopify_metafield_preferences.py`, `beyo_manager/models/tables/shopify/shopify_metafield_preference.py` — exact current implementation, to assert against, not to modify (except the one scoped fix in step 8 below).
  - `tests/unit/test_shopify_router.py` — the existing role-matrix parametrization shape, to extend rather than duplicate a new pattern.

### Skill selection

- Primary skill: none — this is a test-writing and one-line-fix task following established in-repo patterns, not a new design surface.

## Implementation plan

1. **Model constraint test** — `tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py`:
   - Copy `test_shopify_foundation_constraints.py`'s `_seed_workspace_and_user` shape (or import/reuse it if the existing file exports it cleanly — check first; duplicate only if it isn't importable without pulling in unrelated fixtures).
   - Add a local `_metafield_preference(*, suffix, workspace_id, shop_integration_id, item_category_id, definition_id, sequence_order=0, is_deleted=False)` helper building a bare `ShopifyMetafieldPreference` (no need to seed a real `ItemCategory`/`ShopifyShopIntegration` row for the FK if the constraint test's `db_session.commit()` is expected to fail on the *unique index*, not the FK — but Postgres checks FKs too, so seed a minimal real `ItemCategory` and two `ShopifyShopIntegration` rows first, same as `_seed_integration`).
   - Test 1: two rows, same `(workspace_id, shop_integration_id, item_category_id, shopify_metafield_definition_id)`, both `is_deleted=False` → `db_session.add_all(...)`; `await db_session.commit()` raises `IntegrityError`; `await db_session.rollback()` after.
   - Test 2: two rows with the *same* `shopify_metafield_definition_id` string but *different* `shop_integration_id` (two seeded integrations) → both insert and commit successfully. This is the direct proof for review finding "confirms two shops can hold the same definition GID as independent active rows."
   - Test 3: one active row plus one soft-deleted row (`is_deleted=True, deleted_at=<now>`) sharing all four values → both insert and commit successfully (the partial index predicate `is_deleted = false` means the soft-deleted row doesn't count).
   - Test 4 (light): confirm the FK constraints reject a `workspace_id`/`item_category_id`/`shop_integration_id` that doesn't exist (`IntegrityError`) — one case is enough, don't enumerate all three FKs separately unless it's near-zero extra cost.

2. **Command atomicity/idempotency test** — `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py`:
   - Seed one workspace, one user, two `ShopifyShopIntegration` rows (`status=ACTIVE`), one `ItemCategory` — mirror `_seed_workspace_and_user`/`_seed_integration` exactly; add a local `_seed_item_category` helper (check if `test_shopify_admin_commands.py` or a nearby items-domain integration test already has one to reuse before writing a new one).
   - Mock `fetch_shopify_metafield_definition_by_id` at `"beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id"` with a fake keyed by `shop_domain` (a dict `{shop_domain: definition_dict_or_exception}`), so different shops can be given different (or failing) responses in the same test.
   - Test "two valid shops, one request": two selections, one per shop; call `create_shopify_metafield_preferences(ctx)`; assert two rows exist in the DB (query directly), assert result list length 2, assert `result[i].shop_integration_id` matches `request.preferences[i]` order.
   - Test "several definitions, same shop": two selections with the same `shop_integration_id`, different `shopify_metafield_definition_id`; assert both rows created for that one shop.
   - Test "rollback on second-shop failure": shop A's mock returns a valid `PRODUCT` definition, shop B's mock returns `None` (or an `ownerType` mismatch) — call the command inside `pytest.raises(NotFound)`; after the exception, query `ShopifyMetafieldPreference` directly on `db_session` and assert **zero rows** exist for *either* shop's selection (not just shop B's) — this is the proof that shop A's already-`session.add()`-ed-but-not-yet-flushed row was rolled back too, per the "validate everything before writing anything" design (in the current implementation, this test will actually always find zero rows regardless, since all `session.add()` calls happen only after all Shopify validation succeeds — but write the assertion anyway, since it's the acceptance criterion, and it also protects against a future refactor that moves the write earlier).
   - Test "credential isolation": assert the captured call arguments to the mock show shop A's selection called with shop A's `shop_domain`/`access_token_encrypted` and shop B's selection called with shop B's — not each other's.
   - Test "foreign/inactive integration rejected": one selection referencing an integration from a *different* workspace (seed a second workspace + integration) → `NotFound`, and separately, an integration with `status != ACTIVE` → `ValidationError`; assert no rows written in either case.
   - Test "idempotent per shop": call the command twice with identical input → second call updates, doesn't duplicate; call once more changing only shop A's `sequence_order` → assert shop B's row (`updated_at`/`updated_by_id`/`sequence_order`) is untouched by the second call.
   - If step 8 (the no-op fix) is in scope: add an assertion that a byte-for-byte repeat (same `sequence_order`) leaves `updated_at` unchanged (capture the value before, assert equality after) — this will fail against the *current* shipped code and pass only after step 8's fix, so write this test alongside the fix, not before it, to avoid a red commit boundary.

3. **Query multi-shop test** — `tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py`:
   - Seed two workspaces-worth of fixtures as needed: one workspace, two active `ShopifyShopIntegration`s, two `ItemCategory` rows, and `ShopifyMetafieldPreference` rows distributed across both shops and both categories (some shared `shopify_metafield_definition_id` strings across shops, to prove independence).
   - Mock `fetch_shopify_metafield_definitions_by_ids` at `"beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.fetch_shopify_metafield_definitions_by_ids"` keyed by `shop_domain`, recording call arguments (definition IDs requested) per call.
   - Test "one batched call per shop, never combined": two shops, each with 2 preference rows; assert the mock was called exactly twice, and each call's `definition_ids` argument contains only that shop's own rows' definition IDs.
   - Test "grouping and ordering": request `shop_integration_ids` in one order, assert `result["shops"]` preserves that exact order regardless of DB insertion order (insert rows for shop B before shop A in the seed step, request `shop_integration_ids=[A, B]`, assert `shops[0]["shop_integration_id"] == A`).
   - Test "sequence_order preserved per shop/category group": seed rows with out-of-insertion-order `sequence_order` values, assert `metafield_preferences` within each group come back sorted by `sequence_order`.
   - Test "unavailable_definition_ids scoped per shop": mock returns `None` for one shop's definition, a valid node for another shop's *same-string* definition ID; assert the `None` case lands in the correct shop's `unavailable_definition_ids` and does *not* affect the other shop's `item_categories`.
   - Test "invalid integration fails whole request": one of two requested `shop_integration_ids` doesn't belong to the workspace → `NotFound`, assert no partial response is returned (the function raises before returning anything, so this is naturally satisfied — assert via `pytest.raises`).
   - Test "search independent per shop": mock `search_shopify_metafield_definitions_by_name` (same import-site-mocking convention) to return different result sets per shop; assert `search_results` differs correctly per shop entry and `only_my_preferences=True` has no effect on it.
   - Test "search failure fails whole request": one shop's search mock raises `ShopifyGraphQLRetryableError`; assert the whole call raises and no partial `shops[]` is returned.

4. **Router role-rejection tests** — extend `tests/unit/services/shopify/test_metafield_preference_routes.py`:
   - Add one case per route using this app's `_build_test_client` helper (already imported from `tests.unit.test_shopify_router`) with a role not in `[ADMIN, MANAGER, SELLER, WORKER]` — check `routers/utils/roles.py` and `require_roles`'s rejection behavior/status code first (read, don't guess) so the assertion matches the real response shape, mirroring exactly how `test_shopify_router.py`'s existing role-matrix cases assert rejection for other routes.

5. **Infra client test additions** — extend `tests/unit/services/infra/shopify/test_metafield_definition_client.py` with the five cases listed in acceptance criterion 5, following the file's existing `monkeypatch.setattr(".../execute_shopify_graphql", _fake_execute)` pattern.

6. Run `PYTHONPATH=. pytest backend/app/tests -m integration -q` and the existing full unit suite; fix any real failures surfaced (expected: none in the unit suite, since no production code changes except step 8).

7. Run `alembic current` and confirm it reports `b4c5d6e7f8a9`.

8. **Code fix** (only if the clarification above resolves to "include it") — in `create_shopify_metafield_preferences.py`, change:
   ```python
   else:
       existing.sequence_order = selection.sequence_order
       existing.updated_by_id = ctx.user_id
       if existing.is_deleted:
           existing.is_deleted = False
           existing.deleted_at = None
           existing.deleted_by_id = None
       existing.is_enabled = True
   ```
   to only touch `sequence_order`/`updated_by_id` when something actually changed:
   ```python
   else:
       changed = existing.is_deleted or not existing.is_enabled or existing.sequence_order != selection.sequence_order
       if existing.is_deleted:
           existing.is_deleted = False
           existing.deleted_at = None
           existing.deleted_by_id = None
       existing.is_enabled = True
       if changed:
           existing.sequence_order = selection.sequence_order
           existing.updated_by_id = ctx.user_id
   ```
   Keep this a single, narrowly-scoped conditional — do not restructure the surrounding loop or touch the create/restore branches, which are already correct.

## Risks and mitigations

- Risk: seeding two `ShopifyShopIntegration` rows per test (rather than the single-shop pattern every existing Shopify integration test uses) could silently violate the global-unique-shop-domain partial index (`uix_shopify_shop_integrations_shop_domain_active`) if both integrations reuse the same `shop_domain`.
  Mitigation: always call `unique_shop_domain(prefix)` (already defined in `test_shopify_admin_commands.py`) with a distinct prefix per integration in every new test, exactly as existing multi-integration tests already do.
- Risk: mocking the wrong import path (the infra module's own path instead of the call-site's imported name inside the command/query module) makes `monkeypatch.setattr` silently no-op, and the test would then attempt a real HTTP call to Shopify and fail with a confusing network error rather than a clear assertion failure.
  Mitigation: explicitly documented above (Assumptions, step 2/3) — mock at `beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.<name>` / `beyo_manager.services.queries.shopify.get_shopify_metafield_preferences.<name>`, matching the exact `from ... import <name>` lines already present in those two files (both import `fetch_shopify_metafield_definition*`/`search_shopify_metafield_definitions_by_name` by name at module scope, confirmed by direct file read during this planning pass).
- Risk: the no-op idempotency fix (step 8) is deferred as "optional" and gets silently skipped without anyone deciding either way.
  Mitigation: listed as an explicit open clarification with a stated default (include it) rather than a footnote — if left unanswered, proceed with the default per this session's established practice of not blocking on low-stakes clarifications with a safe fallback.
- Risk: the local dev Postgres DB accumulates rows across repeated test runs (no truncation between runs, per existing convention) — a bug in a new test's uniqueness suffixing could cause flaky cross-run collisions.
  Mitigation: always derive test IDs from a fresh `uuid4().hex[:8]` per test function, exactly as every existing integration test in this codebase already does — never hardcode a `client_id` or `shop_domain` literal in a new test.

## Validation plan

- `PYTHONPATH=. pytest backend/app/tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py -m integration -q`
- `PYTHONPATH=. pytest backend/app/tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py -m integration -q`
- `PYTHONPATH=. pytest backend/app/tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py -m integration -q`
- `PYTHONPATH=. pytest backend/app/tests/unit/services/shopify/test_metafield_preference_routes.py backend/app/tests/unit/services/infra/shopify/test_metafield_definition_client.py -q`
- `PYTHONPATH=. pytest backend/app/tests -q` (full suite, confirm no regressions from step 8's fix)
- `PYTHONPATH=. alembic current` — confirm head `b4c5d6e7f8a9`.
- `ruff check` on every new/changed file.

## Review log

- `2026-07-13` `claude`: Plan drafted directly from code-review findings against the completed multi-shop implementation (see `PLAN_shopify_metafield_preferences_20260713.md` and its summary). Migration confirmed applied by the user (`alembic upgrade head` succeeded, head `b4c5d6e7f8a9`), removing the blocker the implementation summary cited for skipping integration tests.
- `2026-07-13` `codex`: Implemented service-layer serialization, expanded integration/unit coverage, and applied the scoped idempotency no-op fix. Targeted validation passed; full-suite validation reported 489 passed and 23 unrelated existing failures. Alembic confirmed `b4c5d6e7f8a9 (head)`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
