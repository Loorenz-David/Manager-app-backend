# HANDOFF_TO_FRONTEND_item_properties_complexity_20260829

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_properties_complexity_20260829`
- Created at (UTC): `2026-08-29T09:20:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation (item-properties complexity tier), recorded in architecture graph changes `.archgraph/changes/2026-08-29T09-12-53-938Z--48535f.yml` and `.archgraph/changes/2026-08-29T09-13-20-013Z--00abe2.yml`
- This is an **addendum** to the published typical/production-time contracts. It does not replace `HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`, `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`, `HANDOFF_TO_FRONTEND_price_scenario_20260819.md`, or `HANDOFF_TO_FRONTEND_quantity_normalized_typicals_20260829.md`; everything in those documents stays true.

## Backend delivery context

- Items now carry an externally-owned **properties snapshot** (wood type, upholstery placement, etc.) with a derived `properties_signature`. The snapshot describes the item's innate complexity; ingestion from the external app ships separately, so **all signatures are NULL in production until then and every payload is byte-identical to today**.
- The typical-time comparability ladder gained a most-specific tier. Per task, sections now resolve top-down:
  1. `item_properties_narrowed` — history whose PRIMARY item shares **both** the current item's category **and** its properties signature (only attempted when the current item has a signature),
  2. `item_narrowed` — same category (unchanged),
  3. `section_wide` — unchanged fallback,
  with the same minimum sample size (5), the same 90-day window, and the same all-or-nothing `uniform_basis_v1` reconciliation at each tier.
- The division method (`static_proportional_section_v2`), quantity projection fields, budget-signals rows, and `GET /api/v1/working-sections/typical-times` are all unchanged. No new endpoint, flag, event, or socket.

## Frontend action required

**No new fields** — this change is entirely new *values* inside existing fields. Action is limited to widening enums/unions:

1. Accept `"item_properties_narrowed"` wherever `typical_basis` is parsed (production-time `sections[].typical.typical_basis`, budget-allocations `steps[].typical_basis`).
2. Accept `"item_properties_narrowed_uniform"` for `typical_resolution.task_typical_basis`.
3. Accept `"primary_item_category_properties_v1"` for `typical_resolution.comparability_profile` (it appears exactly when the current item has a signature, even if the tier fell back).
4. `typical_resolution.sections_by_basis` now always contains the additional key `"item_properties_narrowed"` (integer, `0` when the tier never fired). Strict object parsers must add it.
5. `typical_resolution.applied_filter` may now include `"properties_signature": string` beside `item_category_ids`. It is an opaque hash — display it only for debugging, never parse it.

If any of these are closed enums or exact-key schemas on your side, the payloads will fail validation once items start carrying signatures (and `sections_by_basis` fails immediately — the key is present today).

## Semantics worth knowing for display

- When a step shows basis `item_properties_narrowed`, its `typical_worker_seconds`, `typical_unit_worker_seconds`, `projected_typical_worker_seconds`, and `sample_count` all describe the **same-category-and-same-properties** population — a more comparable, usually tighter history. No display change is required; the existing basis badge/labeling just gains one more (more specific) level.
- Quantity projection semantics are unchanged and compose with this tier: the projected value is the *selected basis's* per-unit median × quantity, whatever the basis.
- Division allowances follow the selected raw typicals exactly as they already followed category narrowing; there is no new invariant to display.
- Properties have **no versioning by design**: a snapshot update in the source app rewrites the item's canonical properties and regroups its history on the next read. Two reads across such an update may legitimately differ.

## Validation notes

- Backend: full suite 2858 passed with only the pre-existing baseline failures (verified against clean HEAD). New coverage includes a SQL-level cohort test (two signatures inside one category: properties median 300 vs pooled category median 1000, gates counted per tier), a below-gate test, an 8-row resolution-ladder grid, three-tier reconciliation tests, and a cross-surface test (signed item reads 600/`item_properties_narrowed` on all three surfaces; clearing the signature falls back to 650/`item_narrowed`). The no-spec SQL byte-identity snapshot (HC-4) held without re-baseline; live-clock goldens changed only by the additive `sections_by_basis` key.
- Suggested frontend validation: parse all three responses with the widened unions; verify a payload carrying `sections_by_basis.item_properties_narrowed` passes strict parsing; nothing else should change until property ingestion ships.

## Trace links

- Parent quantity contract (unchanged, composes): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_quantity_normalized_typicals_20260829.md`
- Parent typical contract (unchanged): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`
- Parent allocation contract (unchanged): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`
- Architecture graph change records: `.archgraph/changes/2026-08-29T09-12-53-938Z--48535f.yml`, `.archgraph/changes/2026-08-29T09-13-20-013Z--00abe2.yml`
