---
plan: plan_6
role: implementer
round: 1
date: 2026-08-24
state: APPROVED
---

# Plan 6 closeout handoff

## Summary

Plan 6 is complete. The frontend contract is published at
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`.
No production file, golden, existing test behaviour, or published handoff changed. The docs guard
did not name any living item-economics document, so `README.md`, `api.md`, `events.md`, and
`states.md` remained untouched. Owner decisions required: **0**.

## Task 0 — forward and reverse coverage map

| criterion row | committed test | assertion shape | trace |
|---|---|---|---|
| C2 `typical_basis` | `test_narrow_typicals_handoff_pins_new_field_nullability[typical-basis]` | exact field-specific non-nullability/default sentence | M3 · M6 |
| C2 `sample_count` | `…[sample-count]` | exact field-specific non-nullability/default sentence | M3 · M6 |
| C2 `narrowed_sample_count` | `…[narrowed-sample-count]` | exact field-specific non-nullability/default sentence | M3 · M6 |
| C2 `section_sample_count` | `…[section-sample-count]` | exact field-specific non-nullability/default sentence | M3 · M6 |
| C2 `typical_resolution` | `…[typical-resolution]` | exact field-specific non-nullability/default sentence | M3 · M6 |
| C2 `applied_filter` | `…[applied-filter]` | exact nullable sentence including both producing states | M3 · M6 |
| C3(a) narrowed zero is unreachable | `test_narrow_typicals_handoff_pins_d25_zero_reachability` | exact task-surface unreachability sentence | M6 |
| C3(b) reachable zero is section-wide | same | exact `section_wide` + `0` sentence | M6 |
| C3(c) zero is a statistic | same | exact “never … `insufficient_sample`” sentence | M6 |
| C4(a) old handoff unchanged | manual perimeter diff plus SHA-256 below | no test substituted for repository history | M3 |
| C4(b) named one-instruction supersession | `test_narrow_typicals_handoff_supersedes_the_worker_card_source` | old filename, section, and “exactly one instruction” literals | M3 |
| C4(c1) new source | same | exact budget-allocations step-source sentence | M3 |
| C4(c2) old join removed | same | exact fetch/cache/join deletion sentence | M3 |

Reverse map: the six nullability cases discharge only C2; the D25 test discharges only C3; the
worker-card supersession test discharges only C4. There are no orphan tests and no candidate
criteria. The phase wrote no complement query, so plan 2 C11's conversion trigger did not fire.

## Red baseline and docs guard

The docs suite was green before the guarded write: **59 passed**. With the eight pinned cases
committed before the new handoff existed it produced the intended red baseline: **8 failed / 59
passed**, with no collection or fixture error. The failures were the six
`test_narrow_typicals_handoff_pins_new_field_nullability` parameter ids,
`test_narrow_typicals_handoff_pins_d25_zero_reachability`, and
`test_narrow_typicals_handoff_supersedes_the_worker_card_source`; each named the missing new
handoff. After the document was added, `PYTHONPATH=. pytest tests/unit/docs/` returned **67
passed**. Ruff also passes for the modified test file.

## Criterion evidence and mutation ledger

Declared probes: **2 named definition mutations + 1 planted-defect probe = 3**. Every mutation
was applied, observed, and reverted; the final docs guard then returned 67 passed.

| probe | mutation and scope | observed result | bite and restoration evidence |
|---|---|---|---|
| C1 planted defect | spell the retired inline-refusal identity in the new handoff; docs suite | **1 failed / 66 passed** | the retired-identity guard failed and named the new handoff; mutated diff digest `f04ab56320e78b44cecc8cdb0bed8f42751d123c4fa3c81adf9f099a159b7ee5`; reverted |
| C2 both sides | remove the `applied_filter` nullability sentence, then remove its case from the test definition; docs suite | contract **1 failed / 66 passed** at `[applied-filter]`; definition mutant **66 passed** while the harder statement was absent | contract red / mutant green; mutated diff digest `4b4a4a3a47972988282d7fe190b3877176a40eb9ec4a9180b65e203b1edca162`; both edits reverted |
| C4 both sides | remove the fetch/cache/join deletion sentence, then remove its assertion from the test definition; docs suite | contract **1 failed / 66 passed** in the supersession test; definition mutant **67 passed** with only the new source documented | contract red / mutant green; mutated diff digest `024a9ca23157f03b69fa6a577ad546951b76847b23376a828f30cf4f9c49e810`; both edits reverted |

C2 is pinned by six field-specific literals, including the reachable null states for
`applied_filter`. C3 is pinned by the three-part D25 statement. C4 is pinned by the named document
and section, exactly-one scope, new budget-allocations source, and deletion of the old bootstrap
fetch/cache/join.

## Published-handoff preservation and write perimeter

`git diff -- docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
was empty. Its SHA-256 was measured before and after the guarded writes and stayed
`88e1c795e8fa5f87bb183670f514fa52439238efb9ad3c4631b91f4245838bfb`.
The final guarded-doc hashes are `80766d2f6d047c89349bed99db32425b92d860a52cef58c467dcfb6f555f8634`
for the pinned test and `859fef347c0cac66dde1c74b1b8410a84f5983f4fd9b1abc2fdea7fe31f8ca13`
for the new frontend handoff.

The intended final write perimeter is the new frontend handoff, the modified pinned docs test,
this implementation handoff, `plans/plan_6.md`, and `master_plan.md`. Temporary mutation edits
were limited to the new handoff and pinned test and were reverted. `git diff -- app/beyo_manager
app/tests/golden` is empty. The owner-owned untracked `.archgraph/backfill/` directory was present
at entry and was neither treated as authorization nor modified.

## Architecture graph

Opening status: initialized and valid, **199 nodes / 299 edges**, revision
`3c53f31054e6a41f20cb9a84c00892da86160b8983f864947c5501a87833ce22`, 6 stale nodes,
2 pending reviews, and no diagnostics. These counts are observations, never gates.

A search for `narrow typical work times` returned no literal-name result. A bounded `typical`
search found the existing human-confirmed domain, endpoint, projection, statement, and helper
nodes. Reading `domain-item-economics-typical-filters` confirmed that the graph already records
the shared filter/reconciliation boundary and uniform-basis semantics. This phase changes no code
or architectural meaning, so the architectural delta is **none** and nothing was recorded. No
review, maintenance, re-anchor, or repair action was taken. D29 was not dispatched or executed.

## Judgments

- The docs guard, not preference, decided that no living item-economics doc needed a change.
- The handoff documents the complete nested `typical_resolution` default object; C2's committed
  parameter set remains the six fields enumerated by the plan.
- `is_estimated` carries both truths: no client rule/value-definition change, and legitimate
  movement under `item_narrowed_uniform` when median usability differs.
- The statistics endpoint is described only as deferred. No complement query or route was
  introduced, so C11 did not convert into a behavioural row.

## Closing stamp

After every repository write above is finalized, the one authorized L4 command is
`BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'`.

Closing result: **2716 passed / 21 failed / 1 skipped**. Relative to plan 5's comparator, the
eight added passes are exactly the new docs cases; the 21-ID failing-set delta is **added ∅ /
removed ∅**. Redis was `PONG` immediately before the run.
