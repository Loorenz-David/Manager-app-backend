# HANDOFF_TO_FRONTEND_typical_filter_properties_20260903

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_typical_filter_properties_20260903`
- Created at (UTC): `2026-09-03T09:10:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation, raised from a live payload where the
  strategy sheet said "Same specification" while showing one criterion.
- This is an **addendum** to `HANDOFF_TO_FRONTEND_typical_filter_category_names_20260902.md`.
  It adds one key inside `applied_filter` and supersedes nothing.

## Backend delivery context

`applied_filter.properties_signature` has always published the hash that the most specific
comparability tier matches on. It is opaque, so a client could say that a full profile matched
but never **which** profile. The only property values a client could name were the ones on the
facet ladder (`properties_facets` — today `upholstery`, then `extension_type`), and those are
owner-declared fallback rungs, not the specification.

That gap is not cosmetic. On `tsk_01KWW5Z82XMXMSH2R9GES21KK4` the item is
`{"wood_type": "Walnut", "upholstery": "Up & Down"}`. In the *cleaning seat* stage the category
cohort is 118 completed jobs, upholstery narrows it to 45, and **wood type narrows it to 10** —
the served `sample_count`. The unnamed criterion was removing more of the population than the
named one.

The filter now carries the snapshot the signature hashes. The signature is unchanged; this is
additive on all three surfaces (production-time, budget-allocations, price-scenario), and the
resolution object's own seven-key shape is unchanged.

## Frontend action required

1. **New key inside `applied_filter`**: `"properties"` — the item's property snapshot as a
   plain object, exactly the dict the signature was computed over.

   ```json
   "applied_filter": {
     "item_category_ids": ["itc_01KVX0G0WHH023EWJ200SCK9DE"],
     "properties_signature": "e5052843…",
     "properties": { "wood_type": "Walnut", "upholstery": "Up & Down" },
     "properties_facets": [{ "upholstery": "Up & Down" }]
   }
   ```

2. **Presence follows `properties_signature`, not the item.** The key appears only when the spec
   carries a signature — without one the properties took no part in the match, and publishing
   them would invite a reader to believe they had. A signature whose snapshot could not be read
   omits the key rather than serving `{}`: an empty object would read as "matched on nothing in
   particular", which is a different claim from "this surface was not told".

3. **Values are arbitrary JSON.** Keys are workspace-defined and values are trusted verbatim —
   `compute_properties_signature` canonicalizes structure only, never casing, units or synonyms.
   Do not assume `string`; render non-strings defensively.

4. **`properties` is a superset of `properties_facets`.** The facets are ladder rungs drawn from
   the same snapshot. Rendering both without distinguishing them will duplicate rows.

## Display guidance

- This exists so a sheet can stop saying "Same specification" beside a list that does not add up
  to one. Name the properties; keep `properties_signature` for keys, diffing and telemetry, and
  never render the hash.
- **Which properties were actually used depends on the basis, not on this key's presence.**
  Every rung starts from the same item predicate (category, type, dimensions, upholstered,
  designer) and then adds signature equality (`item_properties_narrowed`), containment of one
  facet's pairs (`item_facet_narrowed`), or nothing (`item_narrowed`); `section_wide` applies no
  item predicate at all. So on the facet rung the winning facet's keys were used and every other
  property was **not** — which is precisely the fact worth surfacing.
- The properties describe the population the typicals were measured over, which is also the
  population behind the division weights. A surface showing them is describing the budget split,
  not only a displayed number.

## Validation notes

- Backend: full suite 2,963 collected, **23 failures byte-identical to the pre-change baseline**
  (verified by `git stash` and diffing the failing set); none are in item-economics. Every
  item-economics test passes.
- New coverage: `test_applied_filter_names_the_specification_it_matched_on`,
  `test_properties_ride_only_beside_the_signature_that_explains_them`, and
  `test_a_signature_without_a_served_snapshot_omits_the_key`, plus the exact-dict `applied_filter`
  assertion in `test_upholstery_facet_rescues_a_new_wood_profile_on_all_surfaces`.
- **No extra statement on any surface.** The snapshot is read off the primary item each query
  already loads — cheaper than the category names, which cost one statement.
- Suggested frontend validation: parse an `applied_filter` carrying `properties` with a
  non-string value and confirm the sheet renders without crashing.

## Trace links

- Parent: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_typical_filter_category_names_20260902.md`
- Facet ladder: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829.md`
- Narrow typicals: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`
