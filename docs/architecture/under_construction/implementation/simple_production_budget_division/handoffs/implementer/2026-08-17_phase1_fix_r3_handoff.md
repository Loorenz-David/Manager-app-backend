---
plan: 1
role: fix
round: 3
state: IMPLEMENTED
date: 2026-08-17
actor: Codex
pipeline: simple_production_budget_division
checkpoint: 99ade31
---

# Phase 1 fix r3 handoff

## Summary

Implemented the r3 test/documentation-only correction for S6 and notes N-i,
N-j, and N-l. Checkpoint `99ade31` is
`CHECKPOINT (not approved): plan1 fix r3 — pin C14b fixture property + README order`.

⚠ OWNER DECISIONS REQUIRED (0)

None. No graph adjudication or owner decision is requested.

## F1–F4 outcomes

- **F1/S6:** C14b now pins the evaluated task to `ok` and the evaluation-less
  task to `not_configured_no_cost_group` in both the one-task and three-task
  calls. The fixture's PRIMARY item and valuation remain present, so these
  assertions guard the resolver path rather than the `not_evaluated` short
  circuit.
- **F2/N-i:** moved the E2 budget-allocations README detail section before the
  item-upholsteries path group; endpoint content is unchanged apart from the
  required table separator in F3.
- **F3/N-j:** added the E2 422 response-table separator row and restored the
  budget-status mirror comment stating that WORKER and SELLER use the money-free
  worker service.
- **F4/N-l:** renamed the `no_item_*` fixture family to `unevaluated_*` so the
  fixture communicates that the task lacks an evaluation, not an item.

## Test results

- Focused phase/mirror suite: **140 passed**.
- Required full command from `backend/app/`:
  `PYTHONPATH=. pytest -q -m 'not e2e'`
- Full result: **2287 passed, 26 failed, 1 deselected, 2 warnings** in 138.08s.
- Failure decomposition: **23 inherited baseline IDs + 3 foreign bootstrap IDs**;
  no phase-specific test failed.

The 23 inherited baseline failures are:

1. `integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
2. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
3. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
4. `integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
5. `integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
6. `integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
7. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first`
8. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events`
9. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates`
10. `integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value`
11. `integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`
12. `integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set`
13. `integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it`
14. `integration/test_audit_log.py::test_detail_defaults_to_empty_dict`
15. `integration/test_audit_log.py::test_write_audit_from_event_inserts_row`
16. `unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`
17. `unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`
18. `unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
19. `unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
20. `unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
21. `unit/test_items_router.py::test_route_delete_item_issues_forwards_ids`
22. `unit/test_items_router.py::test_route_list_item_issues_forwards_client_id`
23. `unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

The three foreign failures are:

- `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`
- `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden`
- `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`

## Delta ledger

Exactly one probe was applied, observed red, and reverted:

| # | Mutation/site | Test node and observed red | Reverted |
|---|---|---|---|
| 1 | In `_seed`, remove `unevaluated_task_item` and `unevaluated_valuation` from `db_session.add_all(...)` | `test_budget_allocation_constant_query_count_for_one_and_three_tasks`; `AssertionError: assert 'not_evaluated' == 'not_configured_no_cost_group'` at the exact-status assertion | yes |

The probe was applied after the r3 assertion edits and reverted immediately
after the red result. No other mutation probe was run in this cycle.

## Criterion and write perimeter

### Fix-owned files

- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
- `app/beyo_manager/routers/README.md`
- `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_1.md`
- this handoff

### Mutation-probe files, applied and reverted only

- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`

No production files were changed. No migration, schema change, external service
call, or configured-database residue was introduced.

## Architecture Graph state

No Architecture Graph mutation. Graph status remains initialized and valid at
revision `ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`.
The pre-existing `.archgraph/architecture.yml` and bootstrap-seeding worktree
changes were not touched by this fix cycle.

## STOP / coordinator notes

- Phase tracker is `IMPLEMENTED`; the next gate is re-review r3, delta-scoped to
  S6, N-i, N-j, and the one red probe above.
- The 26 full-suite failures are unchanged from the r2 re-review shape: 23
  inherited baseline failures and 3 foreign bootstrap failures.
- The checkpoint is ready for reviewer consumption.
