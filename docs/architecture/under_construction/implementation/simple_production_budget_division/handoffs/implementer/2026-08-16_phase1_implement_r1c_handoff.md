---
plan: 1
role: implementer
round: 1c
state: IMPLEMENTED
actor: Codex
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Phase 1 r1c implementer handoff

## Summary

This was a test-only ledger-closure round. The new fixtures prove the M1 group,
window, statistic, rounding, predicate, and minimum-sample contracts, plus M2's
live allocation universe and E2's exact 50-ID boundary. W2 and W3 found no M1
production defect: the existing query aggregates by `(working_section_id, task_id)`,
admits a group by `MAX(closed_at)`, uses `percentile_cont`, and rounds its double
result with PostgreSQL's half-even behavior.

C13b-door2 and C20 are equivalence STOPs, not surviving coverage gaps. No
production behavior or Architecture Graph state changed.

⚠ OWNER DECISIONS REQUIRED (0)

## Checkpoint

Checkpoint subject: `CHECKPOINT (not approved): plan1 implement r1c — mutation ledger closed`

Checkpoint hash: pending commit below; this handoff will receive the final hash in
the immediate metadata follow-up commit.

## Write perimeter

Final r1c implementation changes:

- `app/tests/integration/services/queries/working_sections/test_typical_times_query.py`
  — W1–W5 M1 fixtures, all transaction teardown-owned.
- `app/tests/unit/domain/item_economics/test_budget_division.py` — W6 and W8 M2
  live-universe/charged-partition fixtures.
- `app/tests/unit/routers/api_v1/test_budget_division_routes.py` — W9 changes the
  50-ID test to invoke the actual query command through an empty async session.
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
  — tracker advanced to IMPLEMENTED (r1c).
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_1.md`
  — r1c review-log entry.
- this handoff.

No production file changed. No Architecture Graph mutation was made; the r1 graph
revision remains `ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`.

## W1–W10 outcomes

| Work item | Outcome |
|---|---|
| W1 / C9b | Five task-section groups with `{4200,1000,2000,5000,6000}` return count 5 / median 4200. Per-step grouping returns count 6 (and then 2800), red. |
| W2 / C9c | A 100-day first pass plus yesterday's rework returns the full 4200 sample. Per-step time filtering returns 2000, red. **Production complied.** |
| W3 / C9d | Six-group rows return 1002 for middles 1000/1003 and 1000 for 1000/1001. `percentile_disc` returns 1000; numeric/half-away returns 1001, red. **Production complied.** |
| W4 / C10 | Removing either completed-state or accurate-time predicate moves the pinned group and turns the fixture red. |
| W5 / C11 | Four groups return `null` / count 4; after a fifth, 4200 / count 5. `>=` to `>` returns `null`, red. |
| W6 / C6 | Working, paused, and completed live steps receive allocations; pending-only mutation gives the pending step all 60 seconds, red. |
| W7 / C10a–b | Re-ran independently after W4; both predicates red at their named site. |
| W8 / C13b-door2 | Fixture pins deleted+skipped invisible and live skipped charged. Adding a deletion check to `excluded` stays green because `excluded` is constructed from `live_steps`; formal equivalence STOP below. |
| W9 / C16 | The old fake service bypassed the cap. The revised test invokes the command with exactly 50 IDs; `>` to `>=` returns 422, red. |
| W10 / C20 | Guard-elision is output-equivalent for all-excluded inputs; formal equivalence STOP below. |

## Closed named-mutation ledger

All temporary mutations were applied at their named production sites and reverted.
Rows not revisited in r1c retain their r1b observed-red evidence; no row remains
`NOT COVERED` or `SURVIVED` without an explicit equivalence STOP.

| Criterion | Mutation / test node | Result |
|---|---|---|
| C1 | float independent rounding / `test_largest_remainder_preserves_distributable_sum` | red: `60 != 61` (r1b) |
| C2–C3 | remove charged subtraction or clamp / `test_excluded_consumption_is_charged_before_division_and_clamped` | red (r1b) |
| C4 | force equal weights / `test_typicals_proportionally_weight_and_missing_typicals_split_equally` | red: `2700 != 3600` (r1b) |
| C5a–b | reverse tie key or remove null normalization / `test_tie_order_is_nulls_last_then_client_id` | red (r1b) |
| C6 | allocate only pending / `test_live_partition_includes_working_paused_and_completed_steps` | red: `{'pending': 60}` vs four 15s |
| C7a–b | average or lower-middle fallback / `test_fallback_median_interpolates_even_values` | red (r1b) |
| C8 | remove no-budget guard / `test_no_budget_and_zero_typicals` | red (r1b) |
| C9 | use `avg` / `test_typical_query_uses_group_median_and_returns_empty_sections` | red (r1b) |
| C9b | group by step identity / `test_typical_query_aggregates_same_task_section_steps_before_sampling` | red: count `6 != 5` |
| C9c | filter contributors by per-step `closed_at` / `test_typical_query_admits_old_first_pass_when_recent_rework_closes_group` | red: `2000 != 4200` |
| C9d-statistic | `percentile_disc` / `...[continuous-interpolation]` | red: `1000 != 1002` |
| C9d-rounding | cast percentile to `NUMERIC` before round / `...[half-even-rounding]` | red: `1001 != 1000` |
| C9e | remove latest-close qualification / `test_typical_query_applies_group_window_and_repeatable_filter` | red (r1b) |
| C10a | remove completed predicate / `test_typical_query_excludes_non_completed_and_marked_wrong_steps_independently` | red |
| C10b | remove marked-wrong predicate / same C10 node | red |
| C11 | `>= 5` to `> 5` / `test_typical_query_requires_five_qualifying_groups` | red: fifth typical `null` |
| C12 | outer join to inner join / M1 empty-section test | red (r1b) |
| C13a | include deleted loader rows / `test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` | red (r1b) |
| C13b-state/delete | change remove-service mapping / `test_remove_service_maps_a_removed_step_to_deleted_skipped` | red (r1b) |
| C13b-door2 | add deletion check inside `excluded` / `test_deleted_skipped_step_is_outside_budget_universe_but_live_skipped_is_charged` | equivalence STOP |
| C14 | per-task evaluation query / `test_budget_allocation_constant_query_count_for_one_and_three_tasks` | red (r1b) |
| C16 | cap `>` to `>=` / `test_budget_allocations_at_fifty_calls_the_service` | red: status `422 != 200` |
| C19 | truncate budget quantization / `test_half_even_budget_seconds_quantization` | red (r1b) |
| C20 | remove empty-allocated guard / `test_all_excluded_steps_return_task_figures_without_division` | equivalence STOP |
| C21 | accept zero typicals as positive / `test_no_budget_and_zero_typicals` | red (r1b) |

There are no named mutations for C15, C17, or C18.

## Equivalence STOPs

- **C13b-door2:** `live_steps` filters `is_deleted` before the excluded partition.
  Therefore adding an `is_deleted` exclusion inside the `excluded` comprehension is
  logically redundant: a deleted skipped row cannot reach it, while a live skipped
  row remains charged. The W8 fixture verifies both observables. Any mutation that
  actually changes this behavior would need to move deletion filtering upstream,
  which is C13a rather than this door-2 wording.
- **C20:** when `allocated` is empty, `excluded == live_steps`. Without the guard,
  weight collection, raw shares, floors, remainder distribution, and allocation-row
  loop are each empty; the final `rows.extend(excluded)` and task figures are the
  same. The guard is a readable fast path, not behavior necessary to avoid a
  zero-weight division. Re-negotiate the named mutation if a distinct behavior is
  required; do not add dead-fixture coverage.

## Criterion-to-test map

| Criterion | Exact test node(s) |
|---|---|
| C1 | `test_budget_division.py::test_largest_remainder_preserves_distributable_sum` |
| C2–C3 | `...::test_excluded_consumption_is_charged_before_division_and_clamped` |
| C4 | `...::test_typicals_proportionally_weight_and_missing_typicals_split_equally` |
| C5a–b | `...::test_tie_order_is_nulls_last_then_client_id` |
| C6 | `...::test_live_partition_includes_working_paused_and_completed_steps` |
| C7 | `...::test_fallback_median_interpolates_even_values` |
| C8 | `...::test_no_budget_and_zero_typicals` |
| C9 | `test_typical_times_query.py::test_typical_query_uses_group_median_and_returns_empty_sections` |
| C9b | `...::test_typical_query_aggregates_same_task_section_steps_before_sampling` |
| C9c | `...::test_typical_query_admits_old_first_pass_when_recent_rework_closes_group` |
| C9d | `...::test_typical_query_uses_continuous_median_and_half_even_rounding[continuous-interpolation]`; `...[half-even-rounding]` |
| C9e | `...::test_typical_query_applies_group_window_and_repeatable_filter` |
| C10 | `...::test_typical_query_excludes_non_completed_and_marked_wrong_steps_independently` |
| C11 | `...::test_typical_query_requires_five_qualifying_groups` |
| C12 | both baseline M1 integration nodes |
| C13 | `test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
| C13b | `...::test_remove_service_maps_a_removed_step_to_deleted_skipped`; `test_budget_division.py::test_deleted_skipped_step_is_outside_budget_universe_but_live_skipped_is_charged` |
| C14 | `test_budget_allocations_query.py::test_budget_allocation_constant_query_count_for_one_and_three_tasks` |
| C15 | `test_budget_division_routes.py::test_both_surfaces_admit_every_role_and_use_the_standard_envelope` |
| C16 | `...::test_budget_allocations_rejects_more_than_fifty_ids_with_registered_identity`; `...::test_budget_allocations_at_fifty_calls_the_service` |
| C17 | `...::test_time_payload_serializers_have_exact_money_free_key_sets` |
| C18 | full suite command below |
| C19 | `test_budget_division.py::test_half_even_budget_seconds_quantization` |
| C20 | `...::test_all_excluded_steps_return_task_figures_without_division` (equivalence STOP) |
| C21 | `...::test_no_budget_and_zero_typicals` |

## Verification

Focused r1c command from `backend/app/`:

`PYTHONPATH=. pytest -q tests/integration/services/queries/working_sections/test_typical_times_query.py tests/unit/domain/item_economics/test_budget_division.py tests/unit/routers/api_v1/test_budget_division_routes.py`

Result: **30 passed**.

Required full command:

`PYTHONPATH=. pytest -q -m 'not e2e'`

Result: **2286 passed, 26 failed, 1 deselected, 2 warnings** in 137.27s.

Failure IDs (exactly the established 23 v1 baseline IDs plus three foreign
bootstrap-seeding tests):

- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py` (3)
- `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
- `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py` (2)
- `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
- `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
- `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py` (3)
- `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py` (2)
- `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py` (2)
- `tests/integration/test_audit_log.py` (2)
- `tests/unit/domain/shopify/test_dimension_migration.py` (2)
- `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
- `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
- `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
- `tests/unit/test_items_router.py` (2)
- `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`
