---
plan: plan_5
role: implement
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Plan 5 implementation handoff

## Summary

Phase 5 is implemented. Price-scenario typicals now use the injected request clock, the
`TaskBudgetStatus.typical_filter_spec`, the shared item-aware reconciliation, and the
participating-section boundary. The price terminal is `Fraction(0, 1)`. The published block now
includes the participating counts and serialized `typical_resolution`; the obsolete private median
bridge in `budget_division.py` is gone. Existing call sites and fakes were widened while keeping
their prior criterion attribution.

⚠ OWNER DECISIONS REQUIRED (1)

The settled graph node's stale description was previewed for replacement but the client's safety
gate refused the persistent maintenance edit because this turn did not explicitly authorize that
exact mutation. The owner may authorize that exact graph edit in a later turn. No workaround,
promotion, rejection, or anchor repair was attempted.

## Baseline and fixture ledger

Pre-implementation baseline, run from `backend/app/`:

`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py tests/integration/services/queries/item_economics/test_price_scenario_query.py -n 0 -p no:randomly`

The new file was absent at baseline; collection was 67 and the result was **60 failed / 7
passed**. Failures were primarily the expected three-argument `_typical_block` seam and the old
fake status shapes.

The new divergent fixture was verified at source before assertions were written: narrowed values
`500, 550, 600, 650, 700` have median `600`; the non-category task over the same twelve-row
history has section-wide median `375`. The fixture also carries an excluded section with a skipped
step so the participating-set mutation is observable.

## Task-0 coverage map

The new phase tests are all attributed to a criterion. The widened old tests retain their existing
phase-3/phase-4 attribution; they were not re-attributed to phase 5.

| criterion row | test coverage | assertion strength |
|---|---|---|
| C1(a) | `test_c1a_typical_block_passes_the_request_clock_to_the_statement` | exact kwarg and delegated statement |
| C1(b) | `test_c1b_same_frozen_context_produces_byte_identical_typicals` | exact repeated injected `now`, boundary inclusion, byte-identical payload |
| C1(c) | `test_c1c_working_section_typicals_keep_the_default_statement_clock` | exact source-level absence of `now=` on the deliberate D24 surface |
| C2(a) | parametrized `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals` | exact empty-set `true`, zero total and zero count |
| C2(b) | parametrized `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals` | exact one missing selected value and count |
| C2(c) | parametrized `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals` | exact one selected zero and count |
| C2(d) | `test_c2d_section_wide_uniform_does_not_make_is_estimated_true` | exact false flag and zero missing count |
| C3 | `test_c3_counts_only_participating_selected_typicals` | exact `3` participating and `2` without sample, with one excluded |
| C4(a) | parametrized `test_c4_price_terminal_and_median_are_duration_values` | exact zero terminal and estimated flag |
| C4(b) | parametrized `test_c4_price_terminal_and_median_are_duration_values` | exact `600 + 900 + 750 = 2250` |
| C5(a–c) | `test_c5_three_surfaces_use_the_same_published_literal` | exact `(600, item_narrowed, 5)` on production-time and allocations, plus price total `600` |
| C6(a–c) | `test_c6_price_and_production_resolution_have_the_exact_six_key_shape` | exact six-key set and literal basis/filter/count values on both surfaces |
| C7(a) | `test_c7_typical_block_delegates_statistics_and_has_no_private_terms` | exact one spy call plus source-term absence |
| C7(b) | `test_c7_item_economics_fork_sweep_finds_only_the_shared_median` | exact allowlisted hit set |
| C7(c) | `test_c7_item_economics_fork_sweep_finds_only_the_shared_median` with planted private median probe | observed red from an extra `_median` fork; probe reverted |
| C7(d) | `test_narrowed_task_economics` ownership guard with planted enum-state copy | observed red from an extra local excluded-state predicate; probe reverted |
| C8(a) | `test_c8_narrowing_changes_the_published_number_and_basis` and divergent-fixture half of `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | exact narrowed `600` and `item_narrowed_uniform` |
| C8(b) | section-wide half of `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | exact plain-task `375`, same history and section |

## Write perimeter and probes

Production writes: `get_task_price_scenario.py`, `serializers.py`, `budget_division.py`.
Test writes: `test_price_scenario_query.py`, additive `_narrowing_fixture.py`, the one expected
count change in `test_narrowed_task_economics.py`, and new `test_narrowed_price_scenario.py`.
No other `app/` file is part of the implementation perimeter.

Authorized probe files were restored and have no diff. Their final md5 values are:

- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` — `48833e4438348f2d01bcf2d00f64bb20`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` — `aff094ded01e15235865bf06c378d8bd`

## Mutation ledger

All rows below were executed, produced the stated red, and were reverted.

| row | hypothesis / site | observed red |
|---|---|---|
| C1(i) | drop `now=ctx.now` at price statement | C1(a) missing kwarg; strengthened C1(b) also changes boundary calls |
| C1(ii) | add `now=ctx.now` to working-sections statement | C1(c) source assertion |
| C2(i) | remove empty-set disjunct | C2(a) `true` → `false` |
| C2(ii) | base `is_estimated` on narrowed evidence | C2(d) `false` → `true` |
| C2(iii) | change selected `<= 0` to `< 0` | C2(c) zero section no longer counted |
| C3(i) | use `len(selection.selected)` | C3 `3` → `4` |
| C3(ii) | count narrowed-thin sections | C3 `2` → `3` |
| C4(i) | price terminal `Fraction(1, 1)` | C4(a) total `0` → `3` |
| C4(ii) | force shared fallback terminal | C4(b) `2250` → `1500` |
| C5(i) | use all task sections as participating | C5 price total `600` → `750` |
| C5(ii) | pass no reconciliation spec | C5 narrowed literal `600` → `375` |
| C6 | omit `comparability_profile` in price serializer | C6 price shape six keys → five |
| C7 | private usable / median ladder in `_typical_block` | C7 spy records zero shared fallback calls |
| C8 | force `specs=()` at statement call | C8 narrowed fixture fails before narrowed result, with no `spec_index` |
| C7(c) probe | planted private `_median` in an out-of-allowlist item-economics file | C7 sweep finds the extra file |
| C7(d) probe | planted enum set and local excluded-state predicate | phase-4 ownership guard finds the extra file |

## Verification

- `84 passed` — phase-5 tests plus the modified legacy query and ownership tests.
- `367 passed` — `tests/unit/domain/item_economics` plus
  `tests/integration/services/queries/item_economics`.
- Focused Ruff: all checks passed.
- Required full stamp: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` → **2708 passed / 21
  failed / 1 skipped / 2 warnings**. The 21 failure IDs match the published baseline set.

## Architecture graph

The existing `projection-item-economics-task-price-scenario` node was inspected and reused. One
source-link batch recorded `_typical_block`, `serialize_task_price_scenario`, and the divergent
fixture test at revision
`501a3ce5180a161eb07ae05ba178f8f2506f12e97839dacff5bedf1ac3fed1b6`.

Final graph status: valid; 198 nodes, 298 edges, six stale nodes, zero diagnostics, zero pending
reviews. The stale settled description still mentions the removed median substitution because its
edit requires explicit owner authorization through the configured maintenance approval channel.

## State

`IMPLEMENTED`. No candidate criteria were added. One owner decision remains for the optional
settled-node description maintenance edit described above.
