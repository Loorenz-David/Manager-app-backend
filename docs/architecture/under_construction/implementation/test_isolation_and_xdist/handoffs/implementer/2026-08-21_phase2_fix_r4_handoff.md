---
plan: 2
role: fix
round: r4
state: IMPLEMENTED
date: 2026-08-21
actor: Codex
---

# Phase 2 fix r4 handoff

## Outcome

Implemented the review-r3 blocking findings and routed notes within the authorized
perimeter. The phase remains serial: no xdist installation, `-n` run, or parallel
measurement was performed.

## Owner decisions required

**0 — none.**

## Changes

- `app/beyo_manager/config.py`: added the parsed `BEYO_TEST_SLOT` setting.
- `app/tests/database_isolation.py`: settings-backed slot resolution, explicit-only legacy
  reclamation, and no-baseline protection for configured-database invariance.
- `app/tests/conftest.py`: unconditional database URL restoration and Redis probe/cleanup
  behavior that tolerates an unavailable Redis instance while asserting no live-prefix residue.
- `app/.env.example`: documented the explicit one-time legacy cleanup command.
- `app/tests/integration/infrastructure/test_database_isolation.py`: covering B1/B2/S2/S3/S4/N2/N7
  assertions, folded into existing criterion items to preserve collection topology.
- `app/tests/integration/services/commands/task_steps/test_add_task_steps_integration.py`:
  removed the duplicate explicit role insert.
- `app/tests/integration/services/queries/users/test_list_users_floor_identification.py`:
  completed workspace-scoped fixture cleanup.
- `plans/plan_2.md`: frontmatter and review log updated.

No production domain behavior changed. No Architecture Graph delta was recorded: the graph
remains valid at revision
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`, with the existing three
inferred items still pending human review.

## Verification

Focused final command:

```text
PYTHONPATH=. .venv/bin/ruff check \
  beyo_manager/config.py tests/database_isolation.py tests/conftest.py \
  tests/integration/infrastructure/test_database_isolation.py \
  tests/integration/services/commands/task_steps/test_add_task_steps_integration.py \
  tests/integration/services/queries/users/test_list_users_floor_identification.py
PYTHONPATH=. .venv/bin/pytest -q \
  tests/integration/infrastructure/test_database_isolation.py \
  tests/integration/services/commands/task_steps/test_add_task_steps_integration.py \
  tests/integration/services/queries/users/test_list_users_floor_identification.py
```

Result: `All checks passed`; `62 passed in 9.56s`.

Collection topology check:

```text
PYTHONPATH=. .venv/bin/pytest -m 'not e2e' --collect-only -q
```

Result: `2582/2583 tests collected (1 deselected)`.

The two authorized L4 closing runs were already consumed before the final criterion-item
topology fold:

- default order: `21 failed, 2569 passed, 1 deselected`;
- `BEYO_TEST_COLLECTION_ORDER=reverse`: `21 failed, 2569 passed, 1 deselected`.

Their failure-ID sets were recorded as identical in the prior review handoff. The differing
foreign IDs observed while the added standalone criterion rows were present were reproduced
by the affected working-sections/items subset without the infrastructure module, identifying
them as pre-existing order seams. The topology fold restored the established collection size;
no third L4 run was authorized by the prompt.

The 21 recorded foreign failures are:

```text
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values
tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events
tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value
tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks
tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it
tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set
tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row
tests/integration/test_audit_log.py::test_detail_defaults_to_empty_dict
tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values
tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values
tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name
tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes
tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields
tests/unit/test_items_router.py::test_route_list_item_issues_forwards_client_id
tests/unit/test_items_router.py::test_route_delete_item_issues_forwards_ids
tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params
```

## Mutation ledger

Each probe was applied singly, run against its named criterion, and reverted before the next
probe. The probe classes were: slot-name derivation, invalid-slot rejection, helper creation
and adopt-or-create behavior, each C4 database URL guard layer, Redis prefix assignment and
deletion, pause-reason ownership, and collection-order validation. Every probe either reddened
its named criterion row(s) or produced the expected collection error. The final checksums of
the files that were mutated temporarily and then restored are:

```text
84f1d7f070d5e903f45302761f1a482bd5831fb23de2894254ff4bea0c483881  app/tests/database_isolation.py
bab5dd586aa0681828b7c23db12924b5c87926070a3d0a51aa3a50b4f6a59d58  app/tests/conftest.py
404ae56f622b271668e5ae22116eacfbec7176a4b995c7bf95a142402bea6c24  app/tests/integration/services/commands/users/test_worker_shift_commands.py
f28703e536600d31504f84e285cdd07d148b69d48e73e68ae8659f4886ee5586  app/tests/integration/services/commands/task_steps/test_add_task_steps_integration.py
befbe046fdbba2e34643d2b72ad1393991f3fa2e0c48933f2821d8ffffc9ec52  app/beyo_manager/services/commands/pause_reasons/create_pause_reason.py
49423816136683daddcc0bc283794e1f6615137019bbf8773ecce7856a2e916c  app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py
```

The checksums above are the post-revert working-tree checksums; the first, second, and task-step
files include their intentional r4 changes, while the worker-helper and pause-reason production
files are byte-identical to the pre-probe tree.

## Residue and handoff

The focused infrastructure module's membership fixture passed, and the final focused run left
no declared disposable database residue. The Redis-dead probe produced warnings and continued
without teardown errors, while the live Redis focused run passed the prefix-residue assertion.

The implementation checkpoint is ready for independent review. No commit was created by this
handoff; the coordinator may checkpoint it with the repository's normal fix-round subject.
