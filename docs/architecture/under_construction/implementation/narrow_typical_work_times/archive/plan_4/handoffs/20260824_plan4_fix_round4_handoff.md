---
plan: plan_4
role: fix
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Fix round 4 handoff

## Summary

Closed the three requested test/fixture findings and four notes. No production file
was changed. The focused perimeter is green: 37 passed across the three edited test
files. The required full-suite approval-gate stamp is recorded in this handoff after
the final tree run.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Changes

- S1/C13(c): documented imports are checked mechanically by rejecting a local
  def _step_state_is_excluded; the set/frozenset scan checks the measured
  string-literal shape for two or more of SKIPPED, CANCELLED, and FAILED.
- S2: the unit selected() fixture derives insufficient_sample/zero for None
  and uses TYPICAL_MIN_SAMPLE_SIZE for section-wide values.
- S3: removed the void evidence-helper source check, renamed C1(c), and made its
  root assertion test path existence.
- N1: C2(c) now asserts a non-empty file set separately for each root.
- N2: the recursive-walk fixture now has both a nested module and a top-level module,
  so the glob mutant reaches assert nested in modules.
- N7: corrected the two over-indented converted dictionary entries.
- N4: the ledger below gives every retained mutation its file and
  definition-vs-call-site location.

Rule-14 divergence declared for C13(c): the shipped sweep uses the two mechanically
sweepable terms EXCLUDED_STEP_STATES and _step_state_is_excluded, and its root is
app/beyo_manager/. The three enum names are intentionally not swept as structural
terms because they occur legitimately across the production tree; the measured
different-name claim is the absence of a string-literal set/frozenset containing two
or more of those names. This follows the amended plan rather than the original
five-term repository-root wording.

## Evidence

Focused command, clean final test tree:

    BEYO_TEST_SLOT=main PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_narrowed_task_economics.py tests/unit/domain/item_economics/test_budget_division.py tests/unit/domain/item_economics/test_domain_purity.py

Result: 37 passed. git diff --check is clean; git status --porcelain -- app/
contains only the three intended test files before checkpointing. No production
file is changed.

## Mutation ledger — 25 observed rows

Each row was run on the named mutant and reverted immediately. The contract side is
the clean focused run above; the mutant side is the observed failing ID/assertion.

| # | criterion | mutation site (file · definition/call site) | observed mutant red |
|---:|---|---|---|
| 1 | C0 | app/tests/unit/domain/item_economics/test_domain_purity.py:_domain_modules definition: rglob → glob | test_item_economics_domain_walk_is_recursive, nested in modules |
| 2 | C0 | app/beyo_manager/domain/item_economics/serializers.py definition/module: add a second fingerprint use | test_item_economics_domain_has_no_spec_identity_hashing, fingerprint assertion |
| 3 | C0 | app/tests/unit/domain/item_economics/test_domain_purity.py:_domain_modules definition: remove non-empty assertion | test_item_economics_domain_walk_requires_a_nonempty_package, pytest.raises |
| 4 | C0 | app/beyo_manager/domain/item_economics/typical_filters.py definition/module: add hashlib import | test_item_economics_domain_has_no_spec_identity_hashing |
| 5 | C0 | app/beyo_manager/domain/item_economics/typical_filters.py definition/module: add model-table import | test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports |
| 6 | C1(a) | app/beyo_manager/services/queries/item_economics/get_task_production_time.py call site: replace one selected typical with live_seconds | test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves, allowance contract |
| 7 | C1(b) | app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py call site: replace one selected typical with live_seconds | same C1 test, allocation allowance contract |
| 8 | C2 | app/beyo_manager/domain/item_economics/budget_division.py definition: ALLOCATION_METHOD v2 → v1 | test_c2c_no_v1_publish_literal_in_production_or_goldens; byte-golden assertion |
| 9 | C3 | app/beyo_manager/domain/item_economics/budget_division.py:_step_result definition: .get → [] | test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error, KeyError |
| 10 | C4 | app/beyo_manager/domain/item_economics/budget_division.py:divide_production_budget definition: terminal Fraction(1, 1) → Fraction(0, 1) | test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal, ZeroDivisionError |
| 11 | C5(i) | app/beyo_manager/domain/item_economics/budget_division.py:_step_result definition: publish fallback 1 for a selected None | test_c5a_and_c5c_below_floor_is_visible_with_exact_section_count |
| 12 | C5(ii) | app/beyo_manager/domain/item_economics/division_serializers.py:serialize_budget_step definition: zero → null/insufficient | test_c5b_reachable_zero_section_statistic_is_visible_on_both_surfaces |
| 13 | C6 | app/beyo_manager/domain/item_economics/division_serializers.py:serialize_typical_resolution definition: iterate selected rather than participating ids | test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections, {1,2,1} |
| 14 | C7(a) | app/beyo_manager/domain/item_economics/typical_filters.py:reconcile_task_typicals definition: quantifier includes excluded ids | test_c7_excluded_sections_resolve_independently_in_both_directions, task basis |
| 15 | C7(b) | same definition: excluded rows use task section-wide basis | same C7 test, mirrored excluded basis |
| 16 | C8 | app/beyo_manager/services/queries/item_economics/get_task_production_time.py call site: guard reconciliation by budget status | test_c8_no_budget_branch_reconciles_before_the_early_return, missing/incorrect basis |
| 17 | C9(a) | app/beyo_manager/domain/item_economics/typical_filters.py:derive_spec_from_primary_item definition: category-less item returns non-empty spec | test_c9_no_category_snapshot_and_empty_spec_converge, applied_filter |
| 18 | C9(b) | app/beyo_manager/domain/item_economics/typical_filters.py:reconcile_task_typicals definition: category-less section evidence treated as narrowed | same C9 test, numeric snapshot mismatch |
| 19 | C10(a) | app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py definition loop: dedupe by object identity | test_c10_batch_dedupes_specs_once_and_preserves_category_index, captured spec sequence |
| 20 | C10(b) | app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py lookup call site: spec_index + 1 modulo K | same C10 test, chair sample count [9] != [7] |
| 21 | C10(d) anti-regression | same lookup call site: (section_id, 0) → (section_id, None) | same C10 test, category-less basis |
| 22 | C11 | app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py evidence construction call site: section-wide value replaces narrowed value | test_c11_both_consumers_publish_the_same_literal_typical_triples |
| 23 | C12 | app/beyo_manager/domain/item_economics/division_serializers.py:serialize_budget_step definition: default basis section-wide | test_c12_defaults_are_always_present_on_the_production_section |
| 24 | C13(b) | app/beyo_manager/domain/item_economics/budget_division.py definition: remove FAILED from EXCLUDED_STEP_STATES | test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct, excluded step KeyError |
| 25 | S1/C13(c) new | app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py definition/call site: remove shared import and add faithful local def + call, preserving two occurrences | test_c13c_excluded_state_logic_has_one_shared_production_owner, local-def assertion |

An initial C10(ii) probe at the task-index assignment definition was green and
was discarded as the wrong site. The required probe was then applied at the
typical_rows.get call site and reddened with the discriminating [9] != [7]
assertion. All mutation probes, including temporary production files, were
reverted; none remain in the final diff.

## Full-suite approval-gate stamp

Command (verbatim, run once on the closing tree):

    BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'

Result and programmatic comparison against the published 21-ID block are recorded
here after the run:

    21 failed, 2692 passed, 1 skipped, 2 warnings in 56.27s
    published=21 actual=21
    actual_minus_published=∅
    published_minus_actual=∅
    ID_DIFF=empty

## Full write perimeter

Intended fix files:

- app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py
- app/tests/unit/domain/item_economics/test_budget_division.py
- app/tests/unit/domain/item_economics/test_domain_purity.py
- docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_4.md
- docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md
- this handoff

Mutation-only files, applied and reverted:

- app/beyo_manager/domain/item_economics/budget_division.py
- app/beyo_manager/domain/item_economics/division_serializers.py
- app/beyo_manager/domain/item_economics/serializers.py
- app/beyo_manager/domain/item_economics/typical_filters.py
- app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py
- app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py
- app/beyo_manager/services/queries/item_economics/get_task_production_time.py
- app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py

No architecture-graph delta was recorded or expected. The graph was read-only
oriented at session start; owner .archgraph/ changes are outside this session.
