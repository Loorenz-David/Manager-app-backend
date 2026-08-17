---
plan: 1
role: fix
round: 2
state: IMPLEMENTED
date: 2026-08-17
actor: Codex
pipeline: simple_production_budget_division
checkpoint: 7f09637
---

# Phase 1 fix r2 handoff

## Summary

Closed review-r1 findings S1–S5 and notes N-a–N-g. The only production refactor
extracts the shared `typical_times_statement(...)` M1 grouped-median builder into
the E1 query module; E2 now calls that builder. The checkpoint is
`7f09637` (`CHECKPOINT (not approved): plan1 fix r2 — close review r1 coverage holes`).

⚠ OWNER DECISIONS REQUIRED (0)

None. The phase remains at the re-review gate; no graph adjudication or owner
decision is requested.

## F1–F6 outcomes

- **F1/S1:** shared M1 builder exported and used by E1/E2; the E2 integration
  fixture has two sections with exactly five qualifying groups per section,
  typicals 3600 and 1800, and asserts the 2:1 allowance split.
- **F2/S2:** the evaluation-less task now has a PRIMARY item and valuation; the
  one-task and three-task calls include it, so `resolve_economics_selection` is
  executed. The local query-count fixture pins 11 statements and equality.
- **F3/S3:** E2 step payload has an exact key-set assertion and nested step money
  scan; `division_serializers.py` itself was not changed.
- **F4/S4:** the E1 route test asserts service identity, protecting declaration
  order above `/{working_section_id}`.
- **F5/S5:** the C13 test compares E2 `actual_worker_seconds` with
  `get_task_budget_status` on the same fixture.
- **F6/notes:** README detail sections now include Request Body/Responses and are
  path-ordered; the mirror comment is accurate; dead `_binding` was removed; the
  excluded-state set is hoisted; the new route import is ordered; C3 share state
  and both C5b integers are pinned.

## Test results

- Focused phase/mirror suite: **140 passed**.
- Required full command from `backend/app/`:
  `PYTHONPATH=. pytest -q -m 'not e2e'`
- Full result: **2287 passed, 26 failed, 1 deselected, 2 warnings**.
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

The three foreign failures are the three tests in
`integration/services/commands/bootstrap/test_seed_item_economics_configuration.py`:
`test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`,
`test_person_owned_configuration_and_section_membership_are_not_overridden`, and
`test_human_successors_permanently_freeze_bootstrap_basis_and_model`.

## Delta-scoped observed-red ledger

Exactly five probes were applied at the named site, run, observed red, and
reverted. Probe-only files are listed separately from the fix perimeter below.

| # | Mutation/site | Test node and observed red | Reverted |
|---|---|---|---|
| 1 | `get_task_budget_allocations.py::_load_typicals`: `return {}` | `test_budget_allocation_uses_shared_typicals_for_two_section_proportional_split`; expected 3600 became `None` | yes |
| 2 | Immediately before `resolve_economics_selection`: per-task workspace-wide `ProductionCostGroup` SELECT | `test_budget_allocation_constant_query_count_for_one_and_three_tasks`; query count became 12 instead of 11 | yes |
| 3 | `division_serializers.py::serialize_budget_step`: add `consumed_cost_minor` | `test_time_payload_serializers_have_exact_money_free_key_sets`; exact key-set assertion failed | yes |
| 4 | `working_sections.py`: move E1 declaration below `/{working_section_id}` | `test_both_surfaces_admit_every_role_and_use_the_standard_envelope`; captured command was `get_working_section` | yes |
| 5 | `typical_times_statement`: remove `(working_section_id, task_id)` GROUP BY | `test_typical_query_aggregates_same_task_section_steps_before_sampling`; PostgreSQL grouping error | yes |

## Lettered criterion → test map

| Row | Test node |
|---|---|
| C13a | `test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
| C13b | `test_budget_allocations_query.py::test_remove_service_maps_a_removed_step_to_deleted_skipped` |
| C13c | `test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
| C14a/b/c | `test_budget_allocations_query.py::test_budget_allocation_constant_query_count_for_one_and_three_tasks` — equality, resolver fixture property, and unknown/degraded rows |
| C15a/b/c | `test_budget_division_routes.py::test_both_surfaces_admit_every_role_and_use_the_standard_envelope` — E1 admission/identity and E2 admission |
| C17a/b/c | `test_budget_division_routes.py::test_time_payload_serializers_have_exact_money_free_key_sets` — E1, E2 task, and E2 step exact sets/nested scan |

## Write perimeter

### Fix-owned files

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/routers/README.md`
- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/unit/routers/api_v1/test_budget_division_routes.py`
- `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_1.md`
- this handoff

### Mutation-probe files, applied-and-reverted only

- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/routers/api_v1/working_sections.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`

### Tool-recorded state

No Architecture Graph mutation. Graph status before/after remains initialized and
valid at revision `ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`;
the pre-existing `.archgraph/architecture.yml` and bootstrap-seeding worktree
changes were not touched by this fix cycle.

## STOP / coordinator notes

- Re-review r2 is the next gate and should verify only this fix perimeter plus the
  five observed-red records; settled M1/M2 behavior remains as recorded in the r1
  review's Verified correct section.
- The full suite's three bootstrap failures are foreign in-flight work, not caused
  by this fix. The 23 inherited baseline failures remain unchanged.
- No migration, schema change, external service call, or configured-database
  residue was introduced.
