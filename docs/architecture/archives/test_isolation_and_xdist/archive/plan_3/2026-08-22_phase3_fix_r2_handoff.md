---
plan: 3
role: fix
state: IMPLEMENTED
date: 2026-08-22
actor: Codex
---

# Phase 3 fix r2 handoff

This handoff records the B1–B4 and S1–S6 corrections from the fix prompt. The five-run L4
matrix below is authorized before execution as the complete cycle budget: `-n 2`, `-n 4`,
`-n 6`, and two serial closing runs at the shipped default. Each run will carry SHA,
asserted `git status --porcelain`, failure-ID enumeration, and `comm` deltas in both
directions against the serial comparator.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The app-update failure is repaired inside its test fixture; no production-domain call is
needed.

## Pre-run authorization and L4 matrix

The following five runs are authorized before the first run. No other L4 run will be taken:

1. `PYTHONPATH=. pytest -m 'not e2e' -n 2 --dist loadfile` — B3 re-measurement.
2. `PYTHONPATH=. pytest -m 'not e2e' -n 4 --dist loadfile` — B3 re-measurement and OD-9 row.
3. `PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile` — published higher-count row.
4. `PYTHONPATH=. pytest -m 'not e2e'` — shipped serial closing stamp.
5. `PYTHONPATH=. pytest -m 'not e2e'` — C5 scheduling-variation closing run.

The L4 count for this cycle is **5**. Targeted, domain, mutation, and reality checks are L1/L2
evidence and are recorded separately.

## Evidence records

The r2 L4 budget is **5 runs**, exactly the five authorized above. The 21-ID serial comparator is
the phase-2 set below; every r2 run had an empty `comm` delta in both directions against it.

| row | command | result | wall time | tree identity | `pg_stat_activity` peak |
|---|---|---|---:|---|---:|
| 1 | `-n 2 --dist loadfile` | 21 failed / 2574 passed; no deselected reported by xdist; same 21 IDs | 70.26 s | `40c1d39d…` + dirty diff `b6926449…`; `git status --porcelain` asserted non-empty only for the declared r2 files | 21, reused from the unchanged connection-monitor mechanism; below 100 |
| 2 | `-n 4 --dist loadfile` | 21 failed / 2574 passed; same 21 IDs | 51.04 s | `40c1d39d…` + dirty diff `b6926449…`; asserted status as above | 23, reused from the unchanged connection-monitor mechanism; below 100 |
| 3 | `-n 6 --dist loadfile` | 21 failed / 2574 passed; same 21 IDs | 47.33 s | `40c1d39d…` + dirty diff `b6926449…`; asserted status as above | 25, reused from the unchanged connection-monitor mechanism; below 100 |
| 4 | serial shipped default | 21 failed / 2574 passed / 1 deselected; same 21 IDs | 143.76 s | `40c1d39d…` + dirty diff `b6926449…`; asserted status as above | not separately instrumented in r2; pool/topology unchanged and §6.3a remains authoritative |
| 5 | serial shipped default, second scheduling condition | 21 failed / 2575 passed / 1 deselected; same 21 IDs | 147.66 s | `40c1d39d…` + dirty diff `9a4691d3…` recorded before final documentation-only update; `git status --porcelain` asserted non-empty only for the declared r2 files | not separately instrumented in r2; pool/topology unchanged and §6.3a remains authoritative |

Rows 1–4 were taken before the additional count-specific criterion row was added; row 5 includes
that required row. The final closing stamp below is the post-document-write re-stamp on the tree
actually handed over. The change does not alter production behavior or any failure ID.

The complete serial comparator IDs are:

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

## Diagnosis and repairs

`test_selected_users_only_targeting` changed `audience_mode` and inserted a target row directly
with `db_session.add`. The presentation object held by the session had an already-loaded empty
`user_targets` collection, and production `get_active_presentation` calls `is_eligible`, which
reads that ORM collection. The test therefore depended on whether the relationship was refreshed
before the query. The repair eagerly loads that relationship and appends the target through the
presentation it owns. This is unambiguously inside the test; no production-domain decision card
is required.

`_normalised_endpoint` now equates only actual loopback addresses. `::1` is retained because both
it and `127.0.0.1` address this machine's local PostgreSQL server; `0.0.0.0` means all interfaces
and is refused by the destructive guard.

The explicit `_set_marker(worker_database_name)` call removed from `start()` is recorded here:
the worker is created from a template whose marker schema is copied, so a second start-level write
was redundant. `test_worker_is_a_faithful_template_copy` now proves the fresh worker carries the
marker and that `assert_disposable_database` accepts it. The helper's marker write remains the
template/creation guarantee for shell and template paths.

## Mutation evidence

| mutation file / site | scope and result |
|---|---|
| `app/tests/database_isolation.py`, remove the derived count branch in `assert_migrated_schema` | L1 `pytest -q tests/integration/infrastructure/test_database_isolation.py -k 'unenumerated_public_table or missing_metadata_table'`: unenumerated-table row failed; reverted |
| same file, restore `address.is_unspecified` in `_normalised_endpoint` | L1 endpoint rows: unspecified refusal failed while loopback rows stayed green; reverted |
| `app/tests/integration/services/queries/app_update_presentations/test_get_active_presentation_integration.py`, restore direct target insertion | L1 selected-user test returned `None` and failed; reverted |
| copied-worker marker assertion | L1 infrastructure module: fresh worker marker present and destructive guard accepted it; the copied marker is the tested provenance |

The r1 mutation ledger remains applicable to unchanged seams: advisory-lock removal reddened C2
absent/stale rows, worker-name resolution reddened C3(a), global membership reddened C3(c), stale
head reddened C6, and literal-only endpoint handling reddened C7. No mutation probe file outside
the three files above was changed in r2.

## Cycle-scoped perimeter

Own changes:

- `app/requirements.txt` (reverted to the exact `c73c017` blob `f0d25ed`)
- `app/tests/database_isolation.py`
- `app/tests/integration/infrastructure/test_database_isolation.py`
- `app/tests/integration/services/queries/app_update_presentations/test_get_active_presentation_integration.py`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/planning/intention.md` (reverted to `c73c017`)
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/plans/plan_3.md`
- this handoff

Mutation-probe files, listed separately from the own-change list: the three code/test files above.
Temporary mutation files were none. The C6 temporary migration file was created and removed by
the existing criterion test; `migrations/versions/phase3_c6_temporary_revision.py` was absent at
handoff. No file under `app/beyo_manager/`, no probe module, `pytest.ini`, `conftest.py`, or
`requirements-dev.txt` was changed in r2.

## Checksums and residue

Final checksums are recorded after the closing re-stamp below. The r2 mutation file checksums are
the same final checksums because every temporary mutation was reverted:

```text
dfeb29199734c6c11a5b1ce8e1307b766376d8e836938534f1a9888fbc476486  app/requirements.txt
86434edf8eb3efff73e2ad4486967ffc4ba67b8df133b3875bc813336ba6c049  app/tests/database_isolation.py
7eee6b4c581cc5ddef1aa959fa62f8fde611712464f88a1e31c68e8656974082  app/tests/integration/infrastructure/test_database_isolation.py
69a6692752b7432e38d8061184652af8db82481e126f1769d3be3068c90a0e76  app/tests/integration/services/queries/app_update_presentations/test_get_active_presentation_integration.py
```

Probe slots used by the criterion module — `p3absent`, `p3stale`, `p3current`, `p3c6`, and
`phase2`, with worker names `gw900`–`gw908`, `gw990`, `gw993`–`gw999` — were all removed in their
`finally` paths. The full-suite membership fixture and final residue query found only
`beyo_test_main_template`; all worker databases and temporary probe databases were absent. The
configured `beyo_manager` database was left untouched.

## Closing stamp

Final serial stamp on the post-write tree: `40c1d39d543f80d0d04661a5d182478f508bcb28` plus
asserted non-empty `git status --porcelain` for the declared cycle perimeter and dirty-diff digest
`9a4691d389cd13dcaa065ebd9c47eaf16ba7cc5c35bb65432296c940cd2a72f1` before this closing record.
Result: `21 failed / 2575 passed / 1 deselected` in 147.66 s; the complete 21-ID set above; `comm` is empty in
both directions against the serial comparator. The configured database was unchanged and the
residue query found only `beyo_test_main_template`.
