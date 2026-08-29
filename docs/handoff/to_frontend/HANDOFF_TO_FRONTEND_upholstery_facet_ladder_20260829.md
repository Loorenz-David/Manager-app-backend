# HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829`
- Created at (UTC): `2026-08-29T12:20:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation (upholstery facet ladder), recorded in architecture graph changes `.archgraph/changes/2026-08-29T12-12-55-110Z--3027ff.yml` and `.archgraph/changes/2026-08-29T12-13-25-900Z--49505f.yml`
- This is an **addendum** to `HANDOFF_TO_FRONTEND_item_properties_complexity_20260829.md`. It supersedes exactly one value from that document (the comparability profile string — see below); everything else in the parent and in the earlier typical/quantity handoffs stays true.

## Backend delivery context

The comparability ladder gained owner-declared **facet rungs** between the full properties profile and the category tier. Per task, sections now resolve top-down:

1. `item_properties_narrowed` — same category AND same full properties profile,
2. `item_facet_narrowed` — same category AND matching **facet** (a declared subset of properties; currently exactly one facet is declared: `upholstery`). Example: a Mahogany "Up & Down" chair with no mahogany history borrows the history of ALL "Up & Down" chairs in its category,
3. `item_narrowed` — same category,
4. `section_wide` — unchanged fallback.

Same minimum sample size (5), same 90-day window, same all-or-nothing per-task rule at every rung. Division method, quantity projection, budget-signals, and the typical-times endpoint are unchanged.

## Frontend action required

1. **New enum values** (widen unions):
   - `typical_basis` (production-time `sections[].typical`, allocations `steps[]`): add `"item_facet_narrowed"`.
   - `typical_resolution.task_typical_basis`: add `"item_facet_narrowed_uniform"`.
2. **Changed value — supersedes the parent handoff**: `typical_resolution.comparability_profile` is now `"primary_item_category_properties_v2"` whenever the item has a properties snapshot (the parent document said `..._v1`; that string no longer occurs but keep accepting both).
3. **New key (always present)**: `typical_resolution.facet` — string | null. The facet name (`"upholstery"`) when `task_typical_basis` is `"item_facet_narrowed_uniform"`, otherwise `null`. Strict object parsers must add it.
4. **New key in `sections_by_basis` (always present)**: `"item_facet_narrowed"` — integer, `0` when the rung never fired.
5. **`applied_filter` may include** `"properties_facets"`: an ordered array of small objects, e.g. `[{"upholstery": "Up & Down"}]` — the facet key/value pairs of the current item, in ladder priority order. Present only when the item has the facet's keys.

## Display guidance

- A step on basis `item_facet_narrowed` is estimated from *"chairs with the same upholstery"* rather than *"identical chairs"* or *"any chair"*. If the UI labels the basis, a good label chain is: exact build → same `<facet>` (from `typical_resolution.facet`) → same type → all work.
- All the usual fields (`typical_worker_seconds`, `typical_unit_worker_seconds`, `projected_typical_worker_seconds`, `sample_count`) describe the facet population when that basis is selected — nothing else to compute.
- Real-data effect to expect immediately: tasks whose exact build is new but whose upholstery type is common (e.g. mahogany "Up & Down" chairs) flip from category numbers to facet numbers — measured on dev data, upholstery installation moved from 3,706s to 6,338s (+71%) and upholstery removal from 1,446s to 3,176s (+120%) for such a task.

## Validation notes

- Backend: full suite green outside the pre-existing baseline (2,958 passed). New coverage: facet derivation and skip-if-absent unit tests, an 8-case resolution-ladder grid extension, facet-uniform reconciliation (including the facet name disclosure and both fallback directions), SQL-level cohort tests (facet pools across signatures by containment: 2+5 Up & Down samples pool to 7 while the full profile stays below gate; mixed faceted/facet-less batches pad missing rungs with empty columns), and a cross-surface test (facet basis 600s on production-time, allocations, and the price block; stripping the snapshot falls back to the 650s category tier). Goldens changed only by the two additive keys; the no-spec SQL identity snapshot (HC-4) held again.
- Suggested frontend validation: parse all three responses with the widened unions and the two new always-present keys; verify a `facet: "upholstery"` payload renders whatever basis labeling you use without crashing.

## Trace links

- Parent (superseded in one value): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_properties_complexity_20260829.md`
- Ingestion addendum (unchanged): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_properties_ingestion_20260829.md`
- Architecture graph change records: `.archgraph/changes/2026-08-29T12-12-55-110Z--3027ff.yml`, `.archgraph/changes/2026-08-29T12-13-25-900Z--49505f.yml`
