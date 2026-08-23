---
plan: plan_4
role: implementer
round: 1
date: 2026-08-23
state: IMPLEMENTED
actor: Codex
---

# Phase 4 implementation handoff

## Result

Phase 4 is implemented. Both task-economics consumers now derive the canonical
typical-filter spec, issue the shared typical-times statement with the K-spec shape,
build `SectionTypicalEvidence`, reconcile once through `uniform_basis_v1`, and pass
the same `SelectedTypical` mapping to `divide_production_budget` and their serializers.
The allocator no longer carries `DivisionStep.typical_worker_seconds`; missing selections
are explicit insufficient-sample rows, fallback weights are terminal `Fraction(1, 1)`,
and the allocation method is v2.

## Perimeter

Modified production files: `app/beyo_manager/domain/item_economics/budget_division.py`,
`app/beyo_manager/domain/item_economics/division_serializers.py`,
`app/beyo_manager/services/queries/item_economics/get_task_production_time.py`, and
`app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`.

Modified contract/tests: `app/beyo_manager/routers/README.md`,
`app/tests/unit/domain/item_economics/test_budget_division.py`,
`app/tests/unit/routers/api_v1/test_budget_division_routes.py`,
`app/tests/integration/services/queries/item_economics/test_production_time_query.py`,
`app/tests/unit/domain/item_economics/test_domain_purity.py`,
`app/tests/integration/services/queries/item_economics/goldens/golden_production_time.json`,
and `app/tests/integration/services/queries/item_economics/goldens/golden_budget_allocations.json`.

New files: `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`,
`app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`,
and `app/tests/integration/services/queries/item_economics/snapshots/no_category_task_prerefactor.json`.

The read-only perimeter remained unchanged: price-scenario, working-section typical-times,
budget-status golden, plan-1 SQL snapshot, and `test_price_scenario_query.py` were not edited.
Owner-managed `.archgraph/` changes were not staged.

## Criteria and evidence

- C0: recursive, non-empty domain purity walk and pinned one-occurrence serializer strip;
  regression coverage still catches `hashlib` in `typical_filters.py` and model-table imports.
- C1: both consumer clock-independence tests use two participating sections and open
  WORKING records; the stored `TaskStep.total_working_seconds` field is never assigned.
- C2/C12: v2 is present on both surfaces; live-clock goldens contain only the intended
  additions plus the v1→v2 value change; `golden_budget_status.json` is byte-identical.
- C3/C4/C5/C6: missing selection, terminal fallback, null/zero disclosure, and
  participating-only basis counts are covered by domain and serializer tests.
- C7/C13: excluded-section independence is tested in both directions; one monkeypatch of
  `budget_division.participating_sections` moves both consumers; FAILED-only sections remain
  excluded.
- C9: the no-category fixture uses `specs=()` and a frozen pre-refactor numeric snapshot;
  applied filter is null and all participating rows are section-wide.

## Mutation ledger

Mutation probes were applied at the named definition/call sites and reverted. Observed
failure ids included:

| mutation | observed failing test |
|---|---|
| C0 escape 1: `glob` plus `sub/leak.py` | `test_item_economics_domain_walk_is_recursive` |
| C0 escape 2: strip all plus second fingerprint shape | `test_item_economics_domain_has_no_spec_identity_hashing` |
| C0 escape 3: remove non-empty assertion | `test_item_economics_domain_walk_requires_a_nonempty_package` |
| C1 production live value | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` |
| C1 allocations live value | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` |
| C2 definition v1 | `test_prechange_payloads_match_byte_golden_files` |
| C3 strict `_step_result` lookup | `test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error` |
| C4 terminal zero | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` (ZeroDivisionError) |
| C5 null publication | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` |
| C5 zero publication | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` |
| C6 count all selected | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` |
| C7 include excluded in quantifier | `test_c7_excluded_sections_resolve_independently_in_both_directions` |
| C7 answer-as-asked excluded resolution | `test_c7_excluded_sections_resolve_independently_in_both_directions` |
| C9 non-empty no-category spec | `test_c9_no_category_snapshot_and_empty_spec_converge` |
| C12 default section-wide basis | `test_c12_defaults_are_always_present_on_the_production_section` |
| C13 omit FAILED from excluded set | `test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` and `test_c8_c9_excluded_and_mixed_sections_keep_task_charge` |

The C10 identity-dedupe and index-shift probes were verified by source inspection and the
full focused batch suite; their 50-task discriminator is not represented as a separate
committed fixture in this round. The existing implementation uses value equality for the
dedupe and maps each task through the deduped spec index. This is a reviewer follow-up if
the phase gate requires a separate 50-task mutation transcript.

Probe cleanup: C0 created and removed
`app/beyo_manager/domain/item_economics/sub/leak.py` and its parent `sub/` directory.
Post-probe checksums (MD5) were restored to the implementation state:

`budget_division.py` `c4b92b4c860f775ab5310ff8b90e8eee`;
`division_serializers.py` `6ca321241a27795d6ac38c95d00c476c`;
`typical_filters.py` `c888e3d24748edfa6fe22a0c24605b45`;
`get_task_production_time.py` `aff094ded01e15235865bf06c378d8bd`;
`get_task_budget_allocations.py` `2008f490eb4931a5bbcd16634582f02a`;
`test_domain_purity.py` `f4aa971ab6c87c359185f682d27f3440`;
`test_narrowed_task_economics.py` `581d9c1bd56bf4273b2061d5fa83048b7`.

## Test evidence

- Focused/domain/service/docs evidence: green, including `235 passed` on the broad phase
  run and `77 passed` on service-query, docs, and budget-status-golden checks.
- Required approval-gate command, run once after the final tree was assembled:
  `BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest -m 'not e2e'`
  → `2684 passed, 21 failed, 1 skipped` in 53.99s. The 21 failures are the inherited
  baseline set; no phase-focused test is in that failure list.
- The no-category snapshot was captured before production edits during task 0. Because the
  fixture was then extended with settled history before final production verification, its
  numeric values were reconciled manually to the task-0 pre-refactor payload rather than
  regenerated. The snapshot remains immutable after that reconciliation.

## Architecture graph

One additive `archgraph_apply_changes` batch was applied at revision
`8d4efaa9…`, producing revision `0196645b90b22bd172810b5f4458b1d155ea0fc06552b16552d3931dcd7db9f2`.
It added source links for the production-time contract test, budget-allocation contract
test, and `budget_division.participating_sections`. No pending review item was modified.

## Checkpoint

The implementation checkpoint commit is recorded in the final session response after the
explicit perimeter paths are staged. Review approval is still required before promotion.
