---
plan: 1
role: implementer
round: 1b
state: IMPLEMENTED
actor: Codex
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Phase 1 r1b implementer handoff

## Summary

Fixed the phase-caused E2 route-mirror failure by adding the all-role route row,
its required `task_ids` query parameter, and the service assertion. Added the
C20 all-excluded unit fixture. C13b was already present in checkpoint `0b85701`
despite the r1 handoff saying it was absent; it was verified and not duplicated.
No production behavior was changed.

⚠ OWNER DECISIONS REQUIRED (0)

## Checkpoint

Checkpoint subject: `CHECKPOINT (not approved): plan1 implement r1b — mirror fix + mutation ledger`

Checkpoint hash: pending until the r1b checkpoint is created; this line is
patched in the metadata follow-up after commit.

## Fix perimeter

Final fix changes in this cycle:

- `app/tests/unit/routers/api_v1/test_item_economics_router.py` — added the E2
  all-role route row; normalized query text for route-pair comparison; asserted
  the E2 service for that row.
- `app/tests/unit/domain/item_economics/test_budget_division.py` — added the
  C20 all-excluded task-figures test.
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
  — tracker row advanced to `IMPLEMENTED (r1b)`.
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_1.md`
  — r1b review-log entry.
- this handoff.

No Architecture Graph mutation was made. The r1 graph revision remains
`ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`.

## Mutation-probe perimeter (applied and reverted, not fix changes)

The following files were temporarily changed at the named mutation sites and
restored before handoff:

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/beyo_manager/services/commands/task_steps/remove_task_step.py`

No mutation probe file remains modified by a probe. The C20 test file is a real
fix-cycle addition, not a probe artifact.

## Verification

Fix-focused command from `backend/app/`:

`PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_budget_division.py tests/unit/routers/api_v1/test_budget_division_routes.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/routers/api_v1/test_item_economics_router.py tests/integration/services/queries/working_sections/test_typical_times_query.py tests/integration/services/queries/item_economics/test_budget_allocations_query.py`

Result: **131 passed**.

Required full command:

`PYTHONPATH=. pytest -q -m 'not e2e'`

Result: **2277 passed, 26 failed, 1 deselected, 2 warnings** in 137.69s.
This is exactly the expected 23 v1 baseline failures plus the 3 foreign
bootstrap failures; no phase-caused failure remains.

Full failure IDs:

- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py` (3 tests)
- `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
- `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py` (2 tests)
- `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
- `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
- `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py` (3 tests)
- `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py` (2 tests)
- `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py` (2 tests)
- `tests/integration/test_audit_log.py` (2 tests)
- `tests/unit/domain/shopify/test_dimension_migration.py` (2 tests)
- `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
- `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
- `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
- `tests/unit/test_items_router.py` (2 tests)
- `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

## Complete named-mutation ledger

Each entry records the mutation, exact pytest node, observed result, and
reversion. `SURVIVED — STOP` means the named test stayed green and the criterion
is not accepted as mutation-proven.

| Criterion | Mutation at named site | Test node | Observed output | Revert |
|---|---|---|---|---|
| C1 | Replace Fraction floors/remainder correction with independent `round(float(share))`. | `test_budget_division.py::test_largest_remainder_preserves_distributable_sum` | `E assert 60 == 61` | restored |
| C2 | Delete `charged_seconds` from `budget_seconds - charged_seconds`. | `...::test_excluded_consumption_is_charged_before_division_and_clamped` | `E assert 3600 == 1200` | restored |
| C3 | Remove `max(0, ...)` clamp. | same C2 node | `E assert -40 == 0` | restored |
| C4 | Use equal `Fraction(1, 1)` weights unconditionally. | `...::test_typicals_proportionally_weight_and_missing_typicals_split_equally` | `E assert 2700 == 3600` | restored |
| C5a | Reverse the client-id tie key. | `...::test_tie_order_is_nulls_last_then_client_id` | `E assert 1 == 2` | restored |
| C5b | Drop NULLS-LAST normalization from `_sort_key`. | same C5 node | `TypeError: '<' not supported between instances of 'int' and 'NoneType'` | restored |
| C6 | Freeze allocation to `state == PENDING`. | `...::test_live_step_set_redivides_and_removed_steps_are_not_in_universe` | **SURVIVED: `1 passed in 0.03s` — STOP** | restored |
| C7a | Replace fallback median with arithmetic mean. | `...::test_fallback_median_interpolates_even_values` | `E assert 1500 == 800` | restored |
| C7b | Replace even-count interpolation with lower-middle selection. | same C7 node | `E assert 667 == 811` | restored |
| C8 | Remove the `allowed_worker_minutes is None` no-budget guard. | `...::test_no_budget_and_zero_typicals` | `decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]` | restored |
| C19 | Replace Decimal half-even quantization with integer truncation. | `...::test_half_even_budget_seconds_quantization` | `E assert 11700 == 11701` | restored |
| C9 | Replace `percentile_cont` with `avg`. | `test_typical_times_query.py::test_typical_query_uses_group_median_and_returns_empty_sections` | `E assert 3160 == 1200` | restored |
| C9b | Remove `task_id` from the `(working_section_id, task_id)` GROUP BY. | same C9 node | database query failure; teardown surfaced `E sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.Error: ... InFailedSQLTransactionError` | restored |
| C9c | Move group-window admission to per-step `closed_at` filtering. | `...::test_typical_query_applies_group_window_and_repeatable_filter` | **SURVIVED: `1 passed in 0.20s` — STOP** | restored |
| C9d-statistic | Replace `percentile_cont` with `percentile_disc`. | C9 node | **SURVIVED: `1 passed in 0.19s` — STOP** | restored |
| C9d-rounding | Replace `round(percentile)` with a direct integer cast. | C9 node | **SURVIVED: `1 passed in 0.19s` — STOP** | restored |
| C9e | Remove the latest-close window predicate. | `...::test_typical_query_applies_group_window_and_repeatable_filter` | `E assert 5 == 0` | restored |
| C10a | Remove the `state == COMPLETED` predicate. | C9 node | **SURVIVED: `1 passed in 0.19s` — STOP** | restored |
| C10b | Remove the `recorded_time_marked_wrong IS FALSE` predicate. | C9 node | **SURVIVED: `1 passed in 0.19s` — STOP** | restored |
| C11 | Change `sample_count >= 5` to `sample_count > 5`. | C9 node | `E assert None == 1200` | restored |
| C12 | Change section `outerjoin` to inner `join`. | C9 node | `KeyError: 'wsec_empty_...'` | restored |
| C13a | Remove the E2 `TaskStep.is_deleted IS FALSE` loader predicate. | `test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` | `E assert 2400 == 1200` | restored |
| C13b-state | Make `remove_task_step` write `PENDING` instead of `SKIPPED`. | `...::test_remove_service_maps_a_removed_step_to_deleted_skipped` | `E AssertionError: assert PENDING is SKIPPED` | restored |
| C13b-delete | Make `remove_task_step` write `is_deleted = False`. | same C13b node | `E assert False is True` | restored |
| C13b | Baseline service-invoking mapping test already exists and passes without a new r1b file change. | same C13b node | green in the 131-test fix suite | verified |
| C13b-door2 | Add deletion exclusion to the pure charged/excluded partition. | `...::test_excluded_consumption_is_charged_before_division_and_clamped` | **SURVIVED: `1 passed in 0.03s` — STOP** | restored |
| C14 | Add one evaluation SELECT inside the per-task output loop. | `test_budget_allocations_query.py::test_budget_allocation_constant_query_count_for_one_and_three_tasks` | `E assert 12 == 13` | restored |
| C16 | Change the 50-id cap from `>` to `>=`. | `test_budget_division_routes.py::test_budget_allocations_at_fifty_calls_the_service` | **SURVIVED: `1 passed in 0.67s` — STOP** | restored |
| C20 | Remove the empty allocated-set guard. | `test_budget_division.py::test_all_excluded_steps_return_task_figures_without_division` | **SURVIVED: `1 passed in 0.02s` — STOP** | restored |
| C21 | Admit zero typicals with `>= 0` in the positive-weight ladder. | `...::test_no_budget_and_zero_typicals` | `ZeroDivisionError: Fraction(1, 0)` | restored |

There are no named mutations for C15, C17, or C18. The surviving rows above are
STOP items for review; no production change was made to make a weak fixture bite.

## Criterion-to-test map

| Criterion | Exact test node(s) |
|---|---|
| C1 | `tests/unit/domain/item_economics/test_budget_division.py::test_largest_remainder_preserves_distributable_sum` |
| C2 | `...::test_excluded_consumption_is_charged_before_division_and_clamped` |
| C3 | same C2 node |
| C4 | `...::test_typicals_proportionally_weight_and_missing_typicals_split_equally` |
| C5a | `...::test_tie_order_is_nulls_last_then_client_id` (first case) |
| C5b | same C5 node (second case) |
| C6 | `...::test_live_step_set_redivides_and_removed_steps_are_not_in_universe` |
| C7 | `...::test_fallback_median_interpolates_even_values` |
| C8 | `...::test_no_budget_and_zero_typicals` |
| C9 | `tests/integration/services/queries/working_sections/test_typical_times_query.py::test_typical_query_uses_group_median_and_returns_empty_sections` |
| C9b | NOT COVERED — STOP item |
| C9c | NOT COVERED — STOP item |
| C9d | NOT COVERED — STOP item |
| C9e | `...::test_typical_query_applies_group_window_and_repeatable_filter` |
| C10 | NOT COVERED — STOP item |
| C11 | NOT COVERED — STOP item |
| C12 | both typical-times integration test nodes |
| C13 | `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
| C13b | `...::test_remove_service_maps_a_removed_step_to_deleted_skipped` |
| C14 | `...::test_budget_allocation_constant_query_count_for_one_and_three_tasks` |
| C15 | `tests/unit/routers/api_v1/test_budget_division_routes.py::test_both_surfaces_admit_every_role_and_use_the_standard_envelope` |
| C16 | `...::test_budget_allocations_rejects_more_than_fifty_ids_with_registered_identity`; `...::test_budget_allocations_at_fifty_calls_the_service` |
| C17 | `...::test_time_payload_serializers_have_exact_money_free_key_sets` |
| C18 | required full-suite command and failure-set comparison above |
| C19 | `tests/unit/domain/item_economics/test_budget_division.py::test_half_even_budget_seconds_quantization` |
| C20 | `...::test_all_excluded_steps_return_task_figures_without_division` |
| C21 | `...::test_no_budget_and_zero_typicals` |

## STOP items

The named mutation ledger identifies surviving mutations for C6, C9c, C9d
statistic, C9d rounding, C10a, C10b, C13b door 2, C16, and C20, plus uncovered
criterion rows C9b, C9c, C9d, C10, and C11. These are test-coverage findings,
not production defects. The round is marked IMPLEMENTED because the r1b prompt
requires reporting these non-red mutations rather than silently redesigning
the phase; review must decide whether another test-only fix cycle is required.
