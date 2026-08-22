---
plan: 3
role: fix
state: IMPLEMENTED
date: 2026-08-22
actor: Codex
---

# Phase 3 fix r3 handoff

Task 10 is implemented: bare pytest now reaches six xdist workers with `--dist loadfile`.
C8 proves the configuration is the cause of that reachability, not a command-line `-n 6`
override. The serial comparator is explicit `-n 0` and is excluded from C8 only when that
override is present.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. OD-10 already settled the six-worker default.

## Cycle-scoped write perimeter

Intended/final files changed in this fix cycle:

- `app/pytest.ini`
- `app/tests/integration/infrastructure/test_database_isolation.py`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/plans/plan_3.md`
- this handoff

No file under `app/beyo_manager/`, no requirements manifest, and no other phase artifact was
changed. No architecture item was promoted, rejected, edited, deprecated or removed; the two
pending graph items remain pending and the three settled items remain `human_confirmed`.

Architecture Graph delta: one inferred `configuration` node and one `configured_by` relationship
were added in a single batch at revision `2c3f0c58a6c45a66834f2377fb3bb7f8586b171e50c59d20e1348b17cebb0e61`.
The pre-write graph was valid at revision `6144a01a…`, with 193 nodes, 290 edges, and two pending
reviews; the delta leaves 194 nodes, 291 edges, and two pending reviews.

## C8 design and mutation evidence

C8 first checks for the deliberate `-n 0` comparator override and skips in that mode. Otherwise
it requires the contiguous configured tokens `-n`, `6`, `--dist`, `loadfile` in pytest's loaded
`addopts`, then requires `PYTEST_XDIST_WORKER` to match `gw<n>`. This makes the row about the
shipped configuration: passing `-n 6` cannot repair the named mutation when `-n 6` is absent from
`pytest.ini`.

| condition | command | result |
|---|---|---|
| shipped default | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` | 51 passed; C8 ran on a `gw<n>` worker |
| named mutation: remove `-n 6` from `app/pytest.ini` | same command, with no `-n` argument | C8 failed as required; 1 failed / 50 passed |
| serial comparator control | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py -n 0` | 50 passed / 1 skipped; C8 skipped only for the explicit comparator override |

Mutation-probe files, listed separately from the fix's own changes, with final restored-file
checksums:

| file | SHA-256 |
|---|---|
| `app/pytest.ini` | `392e7102e99bb3646e402f7652318dc6e55843afedd75189655e406f2b4414b2` |
| `app/tests/integration/infrastructure/test_database_isolation.py` | `5b78a16a63f8731c6409f752ac679fc2c14c555cee32e1943b6fc87c3f125bc9` |

The mutation touched no database schema or production code. The module's disposable worker
databases were reclaimed by the existing fixture; the verified persistent residue is only
`beyo_test_main_template`. The configured `beyo_manager` database was not a target and remained
unchanged.

## L4 evidence budget and baselines

The r3 L4 count is **3**, exactly: (1) the shipped-default closing stamp, (2) a second shipped-
default run varying scheduling, and (3) the explicit `-n 0` serial comparator. No additional L4
run is authorized in this cycle. The tree for all three is the fix-r3 checkpoint, with asserted
clean `git status --porcelain`; the checkpoint SHA is the commit handed to the coordinator.

The shipped default result is **21 failed / 2575 passed**. The serial comparator result is
**21 failed / 2575 passed / 1 skipped / 1 deselected**. The failure-ID set is the phase-2 21-ID
set below; `comm` is empty in both directions for each of the three runs. The six-worker
`pg_stat_activity` peak is **25 of max_connections 100**, carried from r2 because the monitor was
not re-wired for this fix cycle.

The complete comparator failure-ID set is:

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

Resource-class dispositions remain those recorded in the r2 handoff: execution order is
isolated by `loadfile`; module/session state, Redis, filesystem mutation, environment mutation,
unique constraints and worker databases are isolated; fixed ports and background workers are not
reached; global caches, timestamps and processes outside pytest remain declared boundaries.

## Coordinator fold

The master plan now names the shipped parallel command and the explicit serial comparator, §6.3a
records the 25/100 peak and the standing measurement rule, and §8 publishes both baselines on the
fix-r3 tree. The plan review log records the C8 comparator exception and why it cannot be satisfied
by a hand-passed worker count.
