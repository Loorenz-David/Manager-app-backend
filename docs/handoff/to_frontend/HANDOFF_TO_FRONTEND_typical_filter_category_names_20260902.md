# HANDOFF_TO_FRONTEND_typical_filter_category_names_20260902

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_typical_filter_category_names_20260902`
- Created at (UTC): `2026-09-02T17:40:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation (typical strategy disclosure), requested so the two surfaces that show a typical can also tell the reader which population produced it.
- This is an **addendum** to `HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md` and its
  facet-ladder addendum. It adds one key inside `applied_filter` and supersedes nothing.

## Backend delivery context

`typical_resolution.applied_filter` has always published `item_category_ids`, and those ids are
opaque: no response on any of the three surfaces carried the category's name, so a client could
say *how many* categories the typicals were narrowed to but never *which*. Any UI that wants to
tell a user what a typical was measured against had to either fetch the category list separately
or show a raw id.

The filter now names them. The ids stay exactly as they were — this is additive on all three
surfaces (production-time, budget-allocations, price-scenario), and the resolution object's own
seven-key shape is unchanged.

## Frontend action required

1. **New key inside `applied_filter`**: `"item_categories"` — an ordered array of
   `{"client_id": string, "name": string | null}`, in the same order as `item_category_ids`.

   ```json
   "applied_filter": {
     "item_category_ids": ["itc_chair_a1b2c3"],
     "item_categories": [{"client_id": "itc_chair_a1b2c3", "name": "Chair"}]
   }
   ```

2. **Presence follows `item_category_ids` exactly.** The key is present whenever the filter
   narrows on category and absent whenever it does not — the same rule every other axis inside
   `applied_filter` already follows. `applied_filter` itself is still `null` when the primary item
   has no category or there is no primary item.

3. **`name` is nullable, `client_id` is not.** A category that has since been deleted keeps its
   entry with `name: null` rather than dropping out, so the array length always equals
   `item_category_ids` length and a missing name never costs the surface its provenance. Render
   the id-only case as an unnamed category, not as a missing filter.

4. Everything else inside `applied_filter` is unchanged: `major_categories`, `width_cm`,
   `height_cm`, `depth_cm`, `can_have_upholstery`, `designers`, `properties_signature` and
   `properties_facets` keep their existing shapes and their omit-when-inactive rule.

## Display guidance

- This exists so a strategy disclosure can say *"Based on Chair, same upholstery"* instead of
  *"Based on itc_chair_a1b2c3"*. Prefer `item_categories[].name` for anything a user reads and
  keep `item_category_ids` for keys, diffing and telemetry.
- `properties_signature` remains an opaque hash. Use it as a *presence* signal ("matched on the
  full specification"); never render the value.
- The names describe the population the typicals were measured over — which is also the population
  behind the division weights. A surface that shows the strategy is telling the user something
  about their budget split, not only about a displayed number.

## Validation notes

- Backend: full suite 2,963 passed. The 23 failures are the pre-existing baseline — the failing
  test set is **byte-identical** to the same suite run on a clean tree (`git stash`, diffed), and
  none are in item-economics. Every item-economics test passes.
- New coverage: a serializer test asserting the names ride beside the ids on production-time, and
  the existing exact-dict `applied_filter` assertions extended on every surface. The
  no-names-supplied path is pinned by
  `test_c6_price_and_production_resolution_have_the_exact_seven_key_shape`, which now asserts the
  `name: null` entry rather than an absent key.
- One extra statement per request when the filter narrows on category, batched to one statement
  per page on budget-allocations. No statement at all when it does not.
- Suggested frontend validation: parse an `applied_filter` carrying `item_categories` with a
  `null` name and confirm the strategy copy degrades to the unnamed form without crashing.

## Trace links

- Parent: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`
- Facet ladder addendum: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829.md`
- Quantity projection: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_quantity_normalized_typicals_20260829.md`
