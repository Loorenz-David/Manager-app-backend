# PLAN_shopify_metafield_preferences_serialization_layer_correction_20260713

## Metadata

- Plan ID: `PLAN_shopify_metafield_preferences_serialization_layer_correction_20260713`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T14:00:00Z`
- Last updated at (UTC): `2026-07-13T09:50:23Z`
- Related issue/ticket: `n/a`
- Intention plan: none separate — this plan is derived directly from an architectural finding raised against `routers/api_v1/shopify.py`. **Independent of, and must not be merged into, `PLAN_shopify_metafield_preferences_test_coverage_correction_20260713.md`** — that plan is already being executed by Codex; this is a separate, sequenced-after correction so the two pieces of work don't collide mid-flight.

## Goal and intent

- Goal: relocate serialization for the two metafield-preference routes from the router layer to the service layer, matching this codebase's actual prevailing convention.
- Business/user intent: `routers/api_v1/shopify.py`'s two metafield-preference routes (`POST /metafield-preferences`, `GET /metafield-preferences`) call `serialize_shopify_metafield_preference`/`serialize_shopify_metafield_preferences_response` themselves — the only place in the entire router that does this. Every other query in this codebase serializes internally and returns an already-serialized dict, confirmed by direct inspection of:
  - `services/queries/shopify/get_shopify_shop_integration.py` and `list_shopify_shop_integrations.py` — both import `serialize_shopify_shop_integration` and return `{"shops": [asdict(serialize_shopify_shop_integration(item)) for item in page], ...}`-shaped dicts directly.
  - `services/queries/tasks/tasks.py` — imports `serialize_task`, `serialize_item`, `serialize_image`, `serialize_step`, etc. and returns dicts built with them; `routers/api_v1/tasks.py` never imports a single serializer — every route is a bare `return build_ok(outcome.data)`.

  `46_serialization.md`'s documented "routers pick the serializer view" rule is stale relative to how this codebase actually works today — it was mistakenly followed as if current when the metafield-preferences feature was built. This plan brings those two routes into line with the actual convention.
- Non-goals: do not change the response *shape* (field names/nesting) for either route — only *where* serialization happens, which is invisible to the frontend and requires no update to `HANDOFF_TO_FRONTEND_shopify_metafield_preferences_20260713.md`; do not touch any other route in `routers/api_v1/shopify.py` (only the two metafield-preference routes are out of line with the rest of it); do not touch the test-coverage/idempotency work tracked in `PLAN_shopify_metafield_preferences_test_coverage_correction_20260713.md` — treat that plan's files as being actively edited elsewhere and avoid assumptions about their exact current state beyond what's needed to sequence around them (see "Sequencing" below).

## Scope

- In scope:
  1. Move `serialize_shopify_metafield_preference` into `services/commands/shopify/create_shopify_metafield_preferences.py` — the command returns `list[dict]` instead of `list[ShopifyMetafieldPreferenceResult]`.
  2. Move `serialize_shopify_metafield_preferences_response` into `services/queries/shopify/get_shopify_metafield_preferences.py` — the query returns the fully-serialized `{"shops": [...]}` dict instead of a dict containing nested dataclass instances.
  3. Strip both serializer imports and calls out of `routers/api_v1/shopify.py` — both routes become bare `return build_ok(outcome.data)`.
  4. Update `tests/unit/services/shopify/test_metafield_preference_routes.py`'s existing POST-route test, which currently mocks a `ShopifyMetafieldPreferenceResult` dataclass as the service's return value — after this fix, that's the wrong mock shape.
  5. Run the full existing unit suite to confirm the JSON response body is unchanged.
- Out of scope: any of the new integration tests, the no-op idempotency fix, or any other item tracked in the test-coverage correction plan; any change to `merge_metafield_preference_with_definition` (unaffected — it still returns a dataclass; the new serializer call wraps it at the call site).

### Sequencing — read before starting

`PLAN_shopify_metafield_preferences_test_coverage_correction_20260713.md` is being executed concurrently (or may already be complete) by another Codex run against the same files this plan touches (`create_shopify_metafield_preferences.py`, `get_shopify_metafield_preferences.py`, `tests/unit/services/shopify/test_metafield_preference_routes.py`). Before starting:

1. Check the current state of that plan (its `Current state` field, and whether `tests/integration/.../test_create_shopify_metafield_preferences.py` / `test_get_shopify_metafield_preferences.py` already exist) to know whether it has landed yet.
2. **If the test-coverage plan's integration tests already exist and assert against the pre-fix (dataclass-attribute) return shape** — e.g. `result[i].shop_integration_id` instead of `result[i]["shop_integration_id"]` — this plan's step 1/2 will break those tests. Update them to dict-key access as part of this plan's step 6 (added specifically to cover this case) rather than leaving them red.
3. **If the test-coverage plan has not yet touched these files** — proceed normally; there's nothing to reconcile.
4. Either way, do not revert or fight any test-coverage-plan changes already present in these files — layer this fix on top of whatever state they're actually in, re-reading each file fresh immediately before editing rather than assuming the shape described in this plan's snippets below is still exactly current.

## Clarifications required

- None — this is a mechanical relocation with a byte-for-byte-identical output contract (acceptance criterion 1 below), not a design decision.

## Acceptance criteria

1. The JSON response body for both routes is byte-for-byte unchanged from before this fix, for equivalent inputs — verified by the updated router test asserting the full response body, not just status code.
2. Neither route in `routers/api_v1/shopify.py` imports or calls a `serialize_*` function; both are `return build_ok(outcome.data)` (success path).
3. `create_shopify_metafield_preferences` returns `list[dict]`; `get_shopify_metafield_preferences` returns the fully-serialized `{"shops": [...]}` dict. Neither function's return value contains a `ShopifyMetafieldPreferenceResult`/`ShopifyMetafieldDefinitionResult` instance anywhere by the time it reaches the router.
4. `merge_metafield_preference_with_definition` is unchanged — still returns a dataclass; the new `serialize_shopify_metafield_preference(...)` call wraps it at the command's call site only.
5. Any test in this codebase that asserts against the pre-fix return shape of either service function (dataclass attribute access) is updated to dict-key access, whether it lives in this plan's own scope or was added by the concurrently-executing test-coverage plan (see Sequencing).
6. Full existing test suite passes with no regressions.

## Contracts and skills

### Contracts loaded

- `backend/architecture/46_serialization.md`: canonical contract, but its "routers pick the serializer view" rule is stale for this codebase — load it only for the parts that still hold (services return typed/serialized data, serializers are plain functions, no dynamic dispatch), not for who calls the serializer.
- `backend/architecture/09_routers.md`: standard route-handler skeleton (`run_service` → check `outcome.success` → `build_ok`/`build_err`) — the post-fix routes must still match this shape exactly, just without a serializer call in between.

### Finding that overrides the canonical contract text

Confirmed by direct inspection, not inference — see Goal and intent above for the exact files. This plan follows the confirmed actual convention (serialize in the service, plain `build_ok(outcome.data)` in the router), not the stale contract text.

### File read intent — pattern vs. relational

- **How to write** this relocation → `services/queries/shopify/get_shopify_shop_integration.py` (nearest same-domain precedent — read its exact `asdict(serialize_...)` call shape before writing the equivalent here) and `services/queries/tasks/tasks.py` (confirms the pattern is codebase-wide, not Shopify-specific).
- **What exists** (read fresh immediately before editing, per Sequencing above, not from memory of an earlier version):
  - `services/commands/shopify/create_shopify_metafield_preferences.py`
  - `services/queries/shopify/get_shopify_metafield_preferences.py`
  - `domain/shopify/serializers.py` (`serialize_shopify_metafield_preference`, `serialize_shopify_metafield_preferences_response` — read, don't modify)
  - `routers/api_v1/shopify.py`
  - `tests/unit/services/shopify/test_metafield_preference_routes.py`

### Skill selection

- Primary skill: none — mechanical layering fix following an established in-repo pattern.

## Implementation plan

1. Re-read the five files listed above fresh (per Sequencing) to confirm their current exact state before editing anything.

2. In `services/commands/shopify/create_shopify_metafield_preferences.py`:
   - Add `from beyo_manager.domain.shopify.serializers import serialize_shopify_metafield_preference`.
   - Change the function's return type annotation from `-> list[ShopifyMetafieldPreferenceResult]` to `-> list[dict]`.
   - Wrap the final list-comprehension's `merge_metafield_preference_with_definition(...)` call in `serialize_shopify_metafield_preference(...)`.
   - Check whether `ShopifyMetafieldPreferenceResult` is still referenced elsewhere in the file (e.g. an internal type hint); only drop its import if genuinely unused afterward.

3. In `services/queries/shopify/get_shopify_metafield_preferences.py`:
   - Add `from beyo_manager.domain.shopify.serializers import serialize_shopify_metafield_preferences_response`.
   - Change the final `return {"shops": shops}` to `return serialize_shopify_metafield_preferences_response({"shops": shops})`.

4. In `routers/api_v1/shopify.py`:
   - Delete the `from beyo_manager.domain.shopify.serializers import (serialize_shopify_metafield_preference, serialize_shopify_metafield_preferences_response)` import block — confirm first (per Sequencing) that nothing else in the file still needs it.
   - Change `return build_ok([serialize_shopify_metafield_preference(result) for result in outcome.data])` to `return build_ok(outcome.data)`.
   - Change `return build_ok(serialize_shopify_metafield_preferences_response(outcome.data))` to `return build_ok(outcome.data)`.

5. In `tests/unit/services/shopify/test_metafield_preference_routes.py`:
   - Update the POST-route test's mocked `run_service` return value: replace the `ShopifyMetafieldPreferenceResult` dataclass instance with a plain dict literal matching `serialize_shopify_metafield_preference`'s exact output shape (all 15 fields: `client_id`, `item_category_id`, `shop_integration_id`, `shopify_metafield_definition_id`, `name`, `namespace`, `key`, `description`, `type`, `validations`, `sequence_order`, `is_enabled`, `created_at`, `updated_at`, `created_by`).
   - Remove the `ShopifyMetafieldPreferenceResult` import from this test file if it becomes unused.
   - Add a direct full-body assertion (`assert response.json()["data"] == <the mock list>`) to both the POST and GET tests in this file, to concretely prove pass-through rather than only checking a single field (acceptance criterion 1).
   - Rename the POST test if its current name implies the router serializes (e.g. `..._serializes_list` → `..._forwards_body_and_returns_list`).

6. **Reconciliation step, only if needed** (per Sequencing item 2): if the test-coverage-correction plan's integration tests already exist and assert dataclass-attribute access (`result[i].shop_integration_id`, `result["shops"][0].something`) against either service function's return value, update those specific assertions to dict-key access. Do not touch any other part of those test files — this is a narrow shape-compatibility fix, not a re-review of that plan's test coverage.

7. Run `PYTHONPATH=. pytest backend/app/tests/unit -q` and, if the DB is reachable and the test-coverage plan's integration tests already exist, `PYTHONPATH=. pytest backend/app/tests -m integration -q` — confirm no regressions anywhere, not just in the files this plan directly touches.

8. `ruff check` on every changed file.

## Risks and mitigations

- Risk: this plan's edits land while the test-coverage-correction plan is mid-execution in the same files, causing a merge conflict or an edit clobbering the other plan's in-progress work.
  Mitigation: the Sequencing section above requires checking the other plan's state first and re-reading every touched file fresh immediately before editing, not assuming a specific starting state.
- Risk: the response-shape byte-for-byte guarantee is asserted only informally ("looks the same") rather than concretely.
  Mitigation: acceptance criterion 1 requires an explicit full-body equality assertion in the updated router test, not just a spot-check on one field.
- Risk: dropping the `domain.shopify.serializers` import from the router turns out to be wrong because some other part of the file was quietly relying on it (e.g. a shared alias).
  Mitigation: step 4 explicitly requires confirming nothing else needs it before deleting, not deleting on the assumption from this plan's earlier grep (which found only the two metafield-preference call sites, but that was checked before the concurrent plan's edits — re-verify).

## Validation plan

- `PYTHONPATH=. pytest backend/app/tests/unit/services/shopify/test_metafield_preference_routes.py -q` — the primary proof of correctness for this plan.
- `PYTHONPATH=. pytest backend/app/tests/unit -q` — full unit suite, no regressions.
- `PYTHONPATH=. pytest backend/app/tests -m integration -q` — if the DB is reachable and the sibling plan's integration tests exist, confirm those still pass against the new return shapes.
- `ruff check` on every changed file.

## Review log

- `2026-07-13` `claude`: Plan drafted as a standalone correction, split out of an earlier draft that had been merged into `PLAN_shopify_metafield_preferences_test_coverage_correction_20260713.md` by mistake while that plan was already being executed by Codex. This plan supersedes that merged content; the test-coverage plan has been reverted to its original, pre-merge state.
- `2026-07-13` `codex`: Relocated serialization into the command/query services, removed serializer calls from the two routes, updated full-body route assertions, and reconciled integration tests to serialized dictionary access. Focused tests and lint passed; full unit validation reported 389 passed and 12 unrelated existing failures.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
