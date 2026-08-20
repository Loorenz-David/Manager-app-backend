---
plan: 2
role: implementer
round: 6
state: IMPLEMENTED
date: 2026-08-21
actor: Codex
---

# Phase 2 fix r6 handoff

Fix r6 is implemented and remains test-only. B1 is now guarded by one two-section
fixture with five qualifying typicals per section and one open working record. S2 uses
the preferred re-anchor: C6 now runs on that same positive-allowance fixture.

⚠ OWNER DECISIONS REQUIRED (0)

None.

## B1 proof

The fixture's settled typical weights are 3600 seconds for the first section and 1800
seconds for the second. The clean E-P and E-A results are exact section allowances of
`(3040, 1520)` from 4560 distributable seconds. The named mutation in
`get_task_production_time.py:get_task_production_time`, inserted between the typicals
loop and the division, adds each section's live-minus-settled delta to
`typicals_by_section`. It changes the weights to `(4200, 1800)` and the expected result
to `(3192, 1368)`. The new test fails under that mutation for both surfaces.

## S2 proof

The re-anchored C6 test uses the same two-section fixture and has a positive allowance.
The named settled-substitution mutation (`live_seconds[step.client_id]` replaced by
`step.total_working_seconds`) reddens exactly the prior four-ID set: C2/C3/C7 payload
reconciliation, C2 positive allowance share state, C6 settlement recompute, and C9
settlement-window visibility. No prior ID was removed.

## Verification ledger

All whole-suite rows below were run at tree `HEAD b099423`, with the temporary mutation
removed after each probe. The clean row is the intended r6 tree; mutation rows are
temporary proof probes.

| Contract / tree | Result | Added failure IDs | Removed failure IDs |
|---|---:|---|---|
| Clean intended tree `b099423` | 26 failed / 2479 passed / 1 deselected / 2 warnings | none; the published §6 baseline set is unchanged | none |
| B1 live-typicals mutation at `b099423` | 47 failed / 2458 passed / 1 deselected / 2 warnings | 21 IDs, listed below | none |
| S2 settled-substitution mutation at `b099423` | 30 failed / 2475 passed / 1 deselected / 2 warnings | 4 IDs, listed below | none |

B1 added IDs:

1. `tests/integration/services/queries/item_economics/test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`
2. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`
3. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c2_positive_allowance_moves_share_state_under_live_basis`
4. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_b1_live_work_does_not_change_typical_section_weights`
5. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`
6. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c4_frozen_open_record_payloads_are_byte_identical`
7. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c6_allowances_are_byte_identical_after_settlement_recompute`
8. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c6_created_at_is_carried_into_the_production_division_row`
9. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c6_latest_state_record_is_carried_into_the_production_division_row`
10. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c9_settlement_window_drop_is_visible_until_recompute`
11. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks`
12. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c1a_c2_section_order_is_total_and_nulls_last`
13. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c1b_reversed_insertion_order_keeps_name_tie_break`
14. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c4_c6a_c6b_c25a_c25b_grouped_row_preserves_state_and_snapshot`
15. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c8_c9_excluded_and_mixed_sections_keep_task_charge`
16. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape`
17. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c13_negative_open_residual_is_not_clamped`
18. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c14_c16_flat_time_only_degradation_and_tenant_boundary`
19. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c17_frozen_final_uses_live_percent_without_money`
20. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c15_c21_c22_task_scope_and_soft_deleted_section_outer_join`
21. `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c23_leftover_section_tie_uses_section_id_for_both_surfaces`

S2 added IDs:

1. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`
2. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c2_positive_allowance_moves_share_state_under_live_basis`
3. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c6_allowances_are_byte_identical_after_settlement_recompute`
4. `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c9_settlement_window_drop_is_visible_until_recompute`

## Perimeter and records

The intended code change is limited to
`app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`.
The B1 live-typicals and S2 settled-substitution edits to
`app/beyo_manager/services/queries/item_economics/get_task_production_time.py` were
temporary mutation probes and were reverted. No golden files were moved or changed.

Pipeline records written by this closing protocol are the phase 2 tracker row in
`master_plan.md`, this r6 review-log entry in `plans/plan_2.md`, and this handoff. No
Architecture Graph state was written; the graph was only checked for orientation.

Focused verification: 18 phase tests passed and Ruff passed. The full suite retains the
published baseline exception: 26 failed, 2479 passed, 1 deselected, and 2 warnings.
