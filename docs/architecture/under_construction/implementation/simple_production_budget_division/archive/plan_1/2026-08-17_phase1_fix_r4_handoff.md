---
plan: 1
role: fix
round: 4
state: IMPLEMENTED
date: 2026-08-17
actor: Codex
pipeline: simple_production_budget_division
checkpoint: 1290cc0
---

# Phase 1 fix r4 handoff

## Summary

Implemented the single requested S7/C14d test-only correction. `_seed` now
creates a second workspace and a task with no item, evaluation, or steps; the
existing batch call sends that foreign task id as a fourth id and asserts that
its id is absent while retaining `len(...) == 2`. `_cleanup` deletes the
foreign task before the foreign workspace. Checkpoint `1290cc0` is
`CHECKPOINT (not approved): plan1 fix r4 — tenant-boundary row for C14d`.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. No owner decision, graph adjudication, or authorization is requested.

## F1 / S7 outcome

- Changed only `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
  for the fixture handles, four-id batch, absence assertion, and FK-safe
  teardown.
- `first_count == 11` remained unchanged with the foreign id included.
- The C14 test passed after the production filter was restored.

## One-probe delta ledger

Exactly one named mutation was applied at the definition site and reverted:

| # | Mutation/site | Test node | Exact observed red | Reverted |
|---|---|---|---|---|
| 1 | Removed `Task.workspace_id == ctx.workspace_id` from the top-level E2 task visibility query in `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` (current definition site `:65-69`; prompt/reference line `:109-113`) | `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_constant_query_count_for_one_and_three_tasks` | `AssertionError: assert 3 == 2` at `test_budget_allocations_query.py:193` | Yes; the predicate was restored byte-for-byte |

The named mutation now fails because the foreign task is returned. The focused
test after revert passed. The targeted production file is empty in
`git diff 99ade31 -- app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`.
The broader requested command `git diff 99ade31 -- app/beyo_manager` is not
empty because the shared worktree already contains unrelated bootstrap changes
in `app/beyo_manager/services/commands/bootstrap/bootstrap_app.py`; those
changes were not touched or staged by this fix.

## Tests

- Focused C14/E2 integration file:
  `PYTHONPATH=. pytest -q tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
  → **4 passed**.
- Required full suite from `backend/app/`:
  `PYTHONPATH=. pytest -q -m 'not e2e'`
  → **2287 passed, 26 failed, 1 deselected, 2 warnings** in 139.65s.
- Query-count pin: **11 statements** in both the one-task and four-id batch
  calls.
- Failure set: exactly the known 23 inherited baseline IDs plus the 3 foreign
  bootstrap IDs; no phase-specific test failed.

Full failure list:

1. `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`
2. `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`
3. `integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden`
4. `integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
5. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
6. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
7. `integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
8. `integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
9. `integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
10. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates`
11. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first`
12. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events`
13. `integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value`
14. `integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`
15. `integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it`
16. `integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set`
17. `integration/test_audit_log.py::test_write_audit_from_event_inserts_row`
18. `integration/test_audit_log.py::test_detail_defaults_to_empty_dict`
19. `unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`
20. `unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`
21. `unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
22. `unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
23. `unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
24. `unit/test_items_router.py::test_route_list_item_issues_forwards_client_id`
25. `unit/test_items_router.py::test_route_delete_item_issues_forwards_ids`
26. `unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

## Residue and teardown

The fixture's teardown covers these tables, with the foreign task deleted
before the foreign workspace; the configured test transaction rolled back after
the run:

`task_steps`, `item_cost_evaluations`, `task_items`, `item_valuations`,
`tasks` (main workspace and foreign task), `items`,
`production_cost_basis_versions`, `cost_model_versions`,
`production_cost_groups`, `working_sections`, `users`, and `workspaces` (main
and foreign workspace).

No migration, schema change, external-service call, or Architecture Graph
mutation occurred.

## Write perimeter

### Fix-owned files

- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_1.md`
- this handoff

### Mutation-probe files, applied and reverted only

- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`

No production file is part of the fix's own changes. No Architecture Graph
delta was recorded: graph status before implementation was initialized/valid,
revision `ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`,
and tool-delta count is **0 nodes / 0 relationships / 0 source links**.

## STOP items / coordinator notes

- None for the requested fix; the query-count pin did not move.
- Re-review r4 should be delta-scoped to S7/C14d and verify the one-test-file
  perimeter. The production filter remains present.
