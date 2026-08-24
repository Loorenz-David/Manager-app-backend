---
plan: plan_4
role: implementer
round: fix-round-3
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
checkpoint_base: 07cb7bef9237e61b90b228645f31659b5c242926
---

# Plan 4 — fix round 3 implementer handoff

## Result

The two blocking findings and all requested should-fix/note corrections are implemented. The
division contract now has real Layer-2 visibility fixtures, committed absence guards, exact
wire assertions, and a load-bearing `Mapping[str, SelectedTypical]` path. The old `_step_result`
tolerance branch and dead test/service branches are removed. No owner decision is required.

## Completeness table

`shape` means the committed assertion is the criterion's specified shape; no row below is being
claimed from a weaker proxy.

| row | test id | shape |
|---|---|---|
| C0(1) | `test_item_economics_domain_walk_is_recursive` | nested `tmp_path` module is found |
| C0(2) | `test_item_economics_domain_has_no_spec_identity_hashing` | pinned exception remains one occurrence |
| C0(3) | `test_item_economics_domain_walk_requires_a_nonempty_package` | empty walk fails |
| C1(a) | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` | exact per-section allowances on both production calls |
| C1(b) | same | exact per-section allowances on both allocation calls |
| C1(c) | `test_c1c_typicals_and_evidence_helper_do_not_import_live_clock_terms` | non-empty declared roots and expected absence |
| C2(a) | `test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape` | exact v2 on production-time `e3` |
| C2(b) | same | exact v2 on every allocation entry |
| C2(c) | `test_c2c_no_v1_publish_literal_in_production_or_goldens` | declared production/golden roots have no v1 |
| C3(a) | `test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error` | field absent from `DivisionStep` |
| C3(b) | same | missing-selection row shape and allowance |
| C3(c) | `test_c15_c21_c22_task_scope_and_soft_deleted_section_outer_join` | same shape end to end |
| C4(a) | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` | exact even split and no terminal seconds |
| C5(a) | `test_c5a_and_c5c_below_floor_is_visible_with_exact_section_count` | real-session count 3 and insufficient-sample triple |
| C5(b) | `test_c5b_reachable_zero_section_statistic_is_visible_on_both_surfaces` | real-session `(0, "section_wide", 5)` on step and section rows |
| C5(c) | `test_c5a_and_c5c_below_floor_is_visible_with_exact_section_count` | task resolution insufficient count ≥ 1 |
| C6 | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` | exact `{0,2,1}`, count 3, and sum assertion |
| C7(a) | `test_c7_excluded_sections_resolve_independently_in_both_directions` | exact participating task basis and excluded wire basis |
| C7(b) | same | mirrored excluded-section wire basis |
| C8 | `test_c8_no_budget_branch_reconciles_before_the_early_return` | complete no-budget reconciliation |
| C9(a) | `test_c9_no_category_snapshot_and_empty_spec_converge` | immutable numeric snapshot comparison |
| C9(b) | same | `specs=()` observation |
| C9(c) | same | section-wide basis and null filter |
| C10(a) | `test_c10_batch_dedupes_specs_once_and_preserves_category_index` | one statement call / value dedupe |
| C10(b) | same | K=3 and category-less exclusion |
| C10(c) | same | chair count 7 |
| C10(d) | same | category-less section-wide triples |
| C11 | `test_c11_both_consumers_publish_the_same_literal_typical_triples` | exact triples on both consumers |
| C12 | `test_live_clock_goldens.py` byte-golden tests plus C6 assertions | documented defaults and named v1→v2 review diff |
| C13(a) | `test_c13_one_participating_sections_patch_moves_both_consumers` | one patch moves both rendered sets |
| C13(b) | `test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` | excluded wire state and no weight |
| C13(c) | `test_c13c_excluded_state_logic_has_one_shared_production_owner` | non-empty sweep and named shared-predicate exceptions |

## Changes and non-changes

- Added real-session Layer-2 fixtures for below-floor section count 3, and reachable zero
  section-wide values with count 5; both consumers are checked.
- Added C1(c), C2(c), and C13(c) committed guards, each with a non-empty walk assertion.
- C1 uses an accruing open WORKING record, exact allowances `3200` and `1600`, both clock
  calls, both surfaces, and a database re-read proving no persisted totals changed.
- Converted the 23 integer/`None` test mappings to `SelectedTypical`; deleted the old-shape
  `_step_result` branch and the unused `typical=None` helper interface.
- Serializer defaults now read `RECONCILIATION_METHOD` and `COMPARABILITY_PROFILE`; dead
  `task_spec_index is not None` checks and unreachable C10 length assertion were removed.
- Rewrote current stale `§6A` citations to “§6 as amended at the projection fold.” Published
  historical review-log prose was not rewritten.
- C0 escape 2 uses `replace(..., 1)` rather than `count(...) == 1`. This is a deliberate,
  fail-closed divergence: if the pinned line is reworded, replacement becomes a no-op and the
  extra term remains visible to the absence assertion.

Not changed: published handoffs, archived plans, the two golden files, `typical_filters.py`,
price-scenario code, the routers README, the architecture graph, and owner-owned `.archgraph/`
changes. No graph delta is expected because this round adds contract tests and cleanup within
already-mapped nodes; N9 remains an owner decision, not an agent mutation.

## Verification

Focused modified-domain/service/integration command: **51 passed**.

Living-docs guard: `PYTHONPATH=. pytest -n 0 tests/unit/docs -q --tb=short` → **59 passed**.

Closing L4, run once after the authorization line in the plan:

`BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e' --tb=no --show-capture=no -q`

Result: **21 failed, 2692 passed, 1 skipped, 2 warnings in 60.64s**. The actual failed IDs
were sorted and compared programmatically with the published 21-ID set in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md`:

`actual − published: ∅`

`published − actual: ∅`

## Mutation ledger — 26 observed rows

Rows 1–22 are standing observed evidence retained from the correction2 handoff. Rows 23–24 are
the current C5 fixture mutations; the correction2 anti-regression is row 22. C8 and C11 are
transcribed from the review's observed runs and were not rerun, as directed.

| # | mutation | observed red test / assertion |
|---:|---|---|
| 1 | C0 recursive walk → `glob` | `test_item_economics_domain_walk_is_recursive` |
| 2 | C0 remove fingerprint pin | `test_item_economics_domain_has_no_spec_identity_hashing` |
| 3 | C0 remove non-empty guard | `test_item_economics_domain_walk_requires_a_nonempty_package` |
| 4 | C1 production live value fixed | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` |
| 5 | C1 allocation live value fixed | same C1 test |
| 6 | C2 definition v2 → v1 | `test_prechange_payloads_match_byte_golden_files` |
| 7 | C3 strict missing-selection lookup | `test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error` |
| 8 | C4 terminal zero | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` (`ZeroDivisionError`) |
| 9 | C5 no-typical result → null | same C4 test |
| 10 | C5 no-typical result → zero | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` |
| 11 | C6 count all selected rows | same C6 test |
| 12 | C7 include excluded ids | `test_c7_excluded_sections_resolve_independently_in_both_directions` |
| 13 | C7 use task basis for excluded rows | same C7 test |
| 14 | C9 non-empty categoryless spec | `test_c9_no_category_snapshot_and_empty_spec_converge` |
| 15 | C12 default section-wide | `test_c12_defaults_are_always_present_on_the_production_section` |
| 16 | C13 omit FAILED | `test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct`; `test_c8_c9_excluded_and_mixed_sections_keep_task_charge` |
| 17 | C0 add hashlib import | `test_item_economics_domain_has_no_spec_identity_hashing` |
| 18 | C0 add SQLAlchemy model import | `test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports` |
| 19 | C9 classify all narrowed | `test_c9_no_category_snapshot_and_empty_spec_converge` |
| 20 | C10 dedupe by identity | `test_c10_batch_dedupes_specs_once_and_preserves_category_index` at exact tuple assertion |
| 21 | C10 shift post-dedupe indices | same C10 exact tuple assertion |
| 22 | C10(d) `(section_id, 0)` → `(section_id, None)` | same C10 category-less fallback assertion |
| 23 | C0 recursive walk → `glob`, with nested fixture | `test_item_economics_domain_walk_is_recursive`: nested module absent |
| 24 | C2 v2 → v1 | `test_prechange_payloads_match_byte_golden_files` and `test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape`: both exact v2 surfaces |
| 25 | C5(i) selected value → `1` | `test_c5a_and_c5c_below_floor_is_visible_with_exact_section_count`: allocation exact triple `(None, "insufficient_sample", 3)` |
| 26 | C5(ii) selected value/basis → `(None, "insufficient_sample")` | `test_c5b_reachable_zero_section_statistic_is_visible_on_both_surfaces`: allocation exact `(0, "section_wide", 5)` |

For C5(i), the fixture has no usable typical, so the prescribed fallback flip is exactly `1`.
For C5(ii), the production-side exact assertion is evaluated first and the allocation-side
assertion is the observed red after it passes; both surfaces are in the committed test.

## Write perimeter

Production:

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`

Fixtures/tests:

- `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
- `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/unit/domain/item_economics/test_domain_purity.py`

Documentation/tracking:

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_4.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

No other path was written. Temporary mutation files, including the C0 nested probe, were removed
before this handoff.

## Owner decisions required

None.

## Architecture graph

No graph delta required. Status was read before implementation and the graph remains owner-owned;
no promotion, rejection, edit, deprecation, or removal was attempted.
