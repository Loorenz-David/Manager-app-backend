---
plan: 2
role: fix
state: IMPLEMENTED
date: 2026-08-17
actor: Codex/GPT-5
---

# Plan 2 fix r2 handoff

Checkpoint `f904100` (`CHECKPOINT (not approved): plan2 fix r2 — governing step, share_state, guards`). The seven review findings were addressed within the fix perimeter. No owner decision was required.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## What was built

- B1: `_governing_step` partitions non-terminal steps first, then applies `entered_at` DESC, `created_at` DESC, `client_id` ASC. Closed-only groups retain the same precedence.
- S1/D16: section and inherited step `share_state` compare total section `worked_seconds` to the section allowance; `left_seconds` remains allowance minus total worked.
- S2: C1b now seeds sections and steps in reversed insertion order with IDs that disagree with the name order.
- S3: C6a uses a completed step created last, C6b asserts the exact serialized `state_entered_at`, and C6c makes entered/created/client precedence select three different candidates.
- S4: the snapshot is selected from the governing step with first-non-null fallback; E3's step select is ordered by `TaskStep.client_id ASC`.
- S5: the shared-typicals test is renamed and sums allowances at the section unit, with the §12.6 P1 comment.
- S6: `.archgraph/architecture.yml` is declared in this handoff's perimeter.

## Full write perimeter

Fix implementation files:

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py`
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`

Tool-recorded state:

- `.archgraph/architecture.yml`

Pipeline closing artifacts:

- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/implementer/2026-08-17_phase2_fix_r2_handoff.md`

The reviewer/projection handoffs, prompts, intention, and owner-decision edits visible in the working tree predate this fix session and were not modified by it.

## Tests

Targeted fix suite, from `backend/app/`:

```text
PYTHONPATH=. pytest -q -m 'not e2e' \
  tests/unit/domain/item_economics/test_budget_division.py \
  tests/integration/services/queries/item_economics/test_production_time_query.py \
  tests/integration/services/queries/item_economics/test_budget_allocations_query.py
31 passed in 2.24s
```

Full suite, from `backend/app/`:

```text
PYTHONPATH=. pytest -m 'not e2e'
2313 passed, 26 failed, 1 deselected, 2 warnings; 2339 selected in 134.49s
```

The two-pass increase from the r1 total (2311 → 2313) is the two new tests in this fix. Failure-ID diff against the phase-2 start baseline: **0 added, 0 removed**. The current 26 IDs are:

- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`
- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden`
- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`
- `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
- `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
- `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
- `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
- `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
- `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory.py::test_set_current_stored_amount_inventory_noop_emits_no_events`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory.py::test_set_current_stored_amount_inventory_promotes_expected_candidates`
- `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value`
- `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`
- `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set`
- `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it`
- `tests/integration/test_audit_log.py::test_detail_defaults_to_empty_dict`
- `tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row`
- `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`
- `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`
- `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
- `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
- `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
- `tests/unit/test_items_router.py::test_route_delete_item_issues_forwards_ids`
- `tests/unit/test_items_router.py::test_route_list_item_issues_forwards_client_id`
- `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

These are the inherited configured-database/bootstrap/router failures; no phase-2 fix test appears in the list.

## Named mutation ledger

Every mutation was applied at the definition site, run against its named guard, observed red, reverted, and the mutated production file returned to SHA-256 `461c8b6611a8a33d90aaa6c4312f0b0596004d81d72a55d92af2e62d2bf491d9`.

| Finding / criterion | Definition-site mutation | Observed red output | Reverted file |
|---|---|---|---|
| S2 / C1b | Delete the `name` component from `_section_sort_key` in `budget_division.py`. | `AssertionError: assert ['wsec_tie_a_...'] == ['wsec_tie_b_...']`; C1b returned ID order instead of Alpha, Beta. | `app/beyo_manager/domain/item_economics/budget_division.py` |
| B1 / C6a | Delete the liveness partition in `_governing_step`, leaving `candidates = list(steps)`. | `AssertionError: assert 'completed' == 'pending'` at the DB grouped-row assertion. | `app/beyo_manager/domain/item_economics/budget_division.py` |
| S1 / C9 | Replace total `worked` with the non-excluded worked sum in the `share_state` comparison. | `AssertionError: assert 'on_track' == 'over_share'` at the mixed-section assertion. | `app/beyo_manager/domain/item_economics/budget_division.py` |
| S4 / C25b | Replace governing-step snapshot selection with first non-null snapshot in group order. | `AssertionError: assert 'Upholstery' == 'Upholstery installation'`. | `app/beyo_manager/domain/item_economics/budget_division.py` |

## Finding ledger

| Finding | Change | Test that bites |
|---|---|---|
| B1 | Liveness partition plus corrected stable-sort precedence. | C6a DB row; C6c unit precedence row; existing C6 unit control. |
| S1 | `share_state` uses M3.3 total worked seconds. | C9 DB mixed row and the existing zero-distributable unit assertion. |
| S2 | Reversed insertion-order fixture with name/id disagreement. | C1b DB row. |
| S3 | Completed-last DB fixture, exact state-entered timestamp, non-vacuous multi-open unit fixture. | C6a, C6b, C6c. |
| S4 | Governing-step snapshot with null fallback; deterministic E3 query order. | C25b DB row; C25a remains covered by the grouped-row test. |
| S5 | Section-level aggregation and renamed P-PROP test. | `test_budget_allocation_uses_shared_typicals_for_section_proportional_split`. |
| S6 | Declared `.archgraph/architecture.yml` path. | Perimeter audit, not a runtime test. |

## DECISIONS I HAD TO MAKE

- The API serializer emits `state_entered_at` as an ISO string, so C6b asserts the exact ISO representation returned by E3 rather than the ORM `datetime` object.
- The test teardown clears `TaskStep.latest_state_record_id` before deleting its state-record rows because the FK is RESTRICT-protected; this is test-only cleanup and leaves no records behind.
- E3's deterministic order uses `TaskStep.client_id ASC`, the existing stable identity key; no query shape or allowance formula changed.

## Architecture graph

One additive `archgraph_apply_changes` batch recorded three source links on the existing pending `Task production time` projection node: the governing-step allocator, E3's ordered step read, and the C6/C25 integration guard. No new node or relationship was created. No review item was promoted, rejected, edited, deprecated, or removed. Resulting graph revision: `ab867312dafda5e89f5b08050451794d2c681f60344388dba727e336d8a40c7f`.

## Environment / scope notes

- No migrations, schema changes, persisted calculation state, or external-service calls were introduced.
- The configured database was left at head. Mutation probes used fixture transactions and their teardown; no persistent probe rows remain.
- `git diff --check` is clean for the fix changes.
