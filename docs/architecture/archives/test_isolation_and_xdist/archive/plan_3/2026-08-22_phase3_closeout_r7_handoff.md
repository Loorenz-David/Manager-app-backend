---
plan: 3
role: fix
state: IMPLEMENTED
date: 2026-08-22
actor: Codex
---

# Phase 3 closeout r7 handoff

The four routed closeout items are implemented. The approved application tree is checkpointed at
`996a77a`; the plan and this handoff are report-only edits after that checkpoint.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## 1. What changed

- Retired the collection perturbation harness: deleted the three probe modules, removed the
  `phase3_collection_probe` marker, and removed only the `BEYO_TEST_COLLECTION_PROBE` branch from
  `pytest_collection_modifyitems`. `BEYO_TEST_COLLECTION_ORDER` is unchanged.
- Fixed C8 to accept both `--dist loadfile` and `--dist=loadfile`; removed the unreachable
  `arg != "--"` clause from the invocation skip predicate.
- Added `PYTHONPATH=.` to `.env.example`'s legacy reclamation command and all four Makefile test
  targets.
- Deleted unreferenced `app/run_pytest_suite.py`.
- Updated master plan §6.1, §6.6 and §8, and appended the closeout review-log entry to plan §7.

## 2. Cycle-scoped write perimeter

Fix/document files changed by this session:

`app/.env.example`, `app/Makefile`, `app/pytest.ini`, `app/tests/conftest.py`,
`app/tests/integration/infrastructure/test_database_isolation.py`,
`app/run_pytest_suite.py` (deleted), the three `app/tests/*phase3_collection_probe.py` modules
(deleted), `master_plan.md`, `plans/plan_3.md`, and this handoff.

No `app/beyo_manager/`, requirements manifest, `app/tests/database_isolation.py`, migration,
`.archgraph/`, tracker row, or unrelated document was changed.

## 3. Collection and repository-wide checks

| hypothesis | command | result |
|---|---|---|
| retiring inert probes does not change selected collection | `PYTHONPATH=. pytest -m 'not e2e' --collect-only -q \| grep -c '::'` before and after retirement | `2599` / `2599` |
| deleted runner is unreferenced | `git grep -n 'run_pytest_suite' -- ':!app/run_pytest_suite.py'` | no runtime/source reference; remaining matches are historical prompt/review prose |

The retired probe variable still appears in two pre-existing no-op assertions in
`test_database_isolation.py` (`test_collection_probe_hook_is_off_by_default` and
`test_collection_probe_hook_accepts_explicit_off`). The prompt fenced that criterion module to F1
only, so those stale assertions were deliberately not changed; the production collection hook,
marker, and all three probe modules are retired.

## 4. Named mutation evidence

The F1 mutation was applied at the named configuration site, `app/pytest.ini`, and reverted before
the checkpoint. Both sides were computed at L1 against the criterion module:

| mutation | command | result |
|---|---|---|
| `addopts` uses `--dist=loadfile` | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` | **53 passed** |
| remove `--dist loadfile` entirely from `addopts` | same command | **4 failed / 1 error / 49 passed**; C8's dist assertion failed, with known load-mode template collateral |

The second result is the required red side; its collateral is why `loadfile` remains load-bearing.
The mutation probe touched `app/pytest.ini` and the criterion module's disposable databases only.

## 5. Mutation-probe files and checksums

Listed separately from the fix perimeter as required. `app/pytest.ini` is both a fix file and the
F1 mutation site; its final checksum is the post-revert shipped configuration.

| probe file | final SHA-256 | mutation |
|---|---|---|
| `app/pytest.ini` | `632f1873194be0404e80d4efc557292efc70ee8e1582fb41553e799dde153c53` | `--dist=loadfile`; `--dist loadfile` removed |
| `app/tests/integration/infrastructure/test_database_isolation.py` | `34c47569fafc4d16b611056faa3af635b458776efbd9dfe62f9290b564728300` | criterion executed; no source mutation |

All mutations were reverted. The configured database `beyo_manager` was never a destructive target.

## 6. Probe databases and operator-surface evidence

The F1 criterion run exercised the disposable slot families `p3absent`, `p3stale`, `p3current`,
`p3c6`, and `phase2`, plus the process-local `main` worker databases and the declared sibling
probes `gw900`–`gw999`. Their template and worker databases were reclaimed by fixture cleanup.
Final inventory is `beyo_manager`, `beyo_test_main_template`, `housing_parser_plan1_20260807`,
and `postgres` plus the PostgreSQL template databases: no `p3*` or `gw*` probe residue remains,
and no temporary migration remains. `beyo_manager` was left at head.

`make test-unit` executed `PYTHONPATH=. pytest tests/unit -m unit`, proving the corrected Makefile
prefix reaches imports. It produced 918 passed and 7 pre-existing failures in unrelated unit
areas; this is not a new phase-baseline failure-ID claim.

## 7. L4 closing evidence — count is 2

Both runs below are on checkpoint `996a77a`, with the final app tree clean; report-only plan and
handoff edits do not change the application tree under test. Redis was reachable at
`settings.redis_url`. The carried `pg_stat_activity` peak is 25/100, not re-measured.

| run | exact command | result | failure-ID delta |
|---|---|---|---|
| shipped default | `PYTHONPATH=. pytest -m 'not e2e'` | 21 failed / 2578 passed | `comm(phase2, run)=∅`; `comm(run, phase2)=∅` |
| serial comparator | `PYTHONPATH=. pytest -m 'not e2e' -n 0` | 21 failed / 2577 passed / 1 skipped / 1 deselected | `comm(phase2, run)=∅`; `comm(run, phase2)=∅` |

Enumerated failing-ID set, unchanged from phase 2:

```text
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values
tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first
tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events
tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value
tests/integration/services/commands/working_sections/test_worker_working_sections_excludes_counts_for_deleted_parent_tasks
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

## 8. Corrections quoted by the prompt

All four quoted corrections were implemented. No divergence requires explanation under charter
rule 14.

## 9. Architecture graph

No graph delta was made. The prompt explicitly fences `.archgraph/`; status at entry was valid with
194 nodes, 291 edges, 0 pending reviews, and 0 diagnostics.
