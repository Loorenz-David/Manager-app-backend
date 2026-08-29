# HANDOFF_TO_FRONTEND_extension_type_facet_20260829

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_extension_type_facet_20260829`
- Created at (UTC): `2026-08-29T12:45:00Z`
- Owner agent: `Claude`
- This is a value-only **addendum** to `HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829.md`. No schema change of any kind.

## What changed

A second facet was declared in the comparability ladder: **`extension_type`**, sitting after `upholstery` in priority. The ladder per task is now: full properties profile → upholstery facet (items with an `upholstery` property) → extension-type facet (items with an `extension_type` property, e.g. tables with inserts) → category → section-wide. An item only gets the rungs its own properties provide; most items have one facet key or the other, not both.

## Frontend impact — values only

- `typical_resolution.facet` may now also be the string `"extension_type"` (previously only `"upholstery"` or `null`). If you render the facet name, no change is needed unless you hardcoded "upholstery".
- `applied_filter.properties_facets` may contain `{"extension_type": "..."}` entries, and (rarely, for an item carrying both keys) two entries in priority order.
- No new keys, no new basis strings, no profile change — everything else is exactly as the parent handoff describes.

## Validation notes

- Backend suite green outside the pre-existing baseline (2,962 passed). New coverage: ladder-order unit tests (both rungs derive in priority order; rung priority and per-rung fallback in reconciliation), an SQL cohort test for extension tables (2+5 Insert samples pool to 7 while the full profile stays gated), and a two-rung column-shape test.
- Dev-data check: existing well-sampled profiles (e.g. article 0000967) keep resolving on the full profile — the new rung only catches insert tables whose exact build is new (39–51 pooled Insert samples per wood section; wood fix facet median 4,858s vs 3,887s category).

## Trace links

- Parent: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_facet_ladder_20260829.md`
