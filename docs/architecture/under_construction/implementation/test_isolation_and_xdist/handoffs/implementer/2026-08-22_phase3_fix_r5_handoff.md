---
plan: 3
role: fix
state: IMPLEMENTED
date: 2026-08-22
actor: Codex
---

# Phase 3 fix r5 handoff

Review r4's B1, S1–S5, N1 and N2 are resolved. The shipped implementation passes the repaired
criterion module; the three authorized full-suite L4 runs retain exactly the phase-2 21-ID
failure set. The application/doc changes were checkpointed concurrently by the owner in
`4b5719d` while this session was measuring; that checkpoint is preserved and is the code tree
handed over here.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## 1. Changes

- `app/tests/integration/infrastructure/test_database_isolation.py`
  - C2 current-template row holds a template connection and tags each probe's maintenance
    sessions. It releases the held connection only when that probe's advisory lock is observed at
    the copy call, so the shipped wide lock passes while M4 and M5 expose PostgreSQL's
    `ObjectInUseError`.
  - C8 skips on any `-n`/`--numprocesses` invocation override; otherwise asserts `--dist loadfile`,
    a positive worker count, and `PYTEST_XDIST_WORKER=gw<n>`.
  - Added `localhost.localdomain` and `ip6-localhost` endpoint rows.
  - Removed C3(a)'s hand-constructed sibling-distinctness assertion.
- `app/.env.example`: legacy reclamation command is explicitly serial with `-n 0`.
- `master_plan.md`: reversed-collection command is serial; §6.4 distinguishes availability-
  tolerant prefix cleanup from the two Redis-dependent logout rows; §8 names the Redis
  precondition and publishes the new counts.
- `plans/plan_3.md`: frontmatter is `IMPLEMENTED`; r5 review-log entry records evidence and the
  L4 count.

Cycle-scoped write perimeter: the four files above plus this handoff. No production code,
requirements manifest, `app/pytest.ini`, `app/tests/conftest.py`, probe harness, migration file,
or `.archgraph/` file was changed by this cycle. The owner checkpoint also changed the live r5
prompt and graph-maintenance prompt outside this cycle; those external-stream changes are not
rewritten here.

## 2. L4 evidence — count is 3

Environment precondition for all runs: Redis reachable at `settings.redis_url`. The authoritative
phase-2 comparator is the 21 IDs listed below. Every run had `comm(phase2, run)=∅` and
`comm(run, phase2)=∅`.

| run | exact command | tree identity | result |
|---|---|---|---|
| 1 | `PYTHONPATH=. pytest -m 'not e2e'` | logical application tree `8501a51` plus application/master/env diff digest `9b1724164bb7867bc3fb2488fae74f2579a8f942a209e71995cd8a4a3b3e3d75` | 21 failed / 2578 passed, 55.95 s; same 21 IDs |
| 2 | `PYTHONPATH=. pytest -m 'not e2e'` | checkpoint `4b5719d`, clean when run | 21 failed / 2578 passed, 55.41 s; same 21 IDs |
| 3 | `PYTHONPATH=. pytest -m 'not e2e' -n 0` | checkpoint `4b5719d`, clean when run | 21 failed / 2577 passed / 1 skipped / 1 deselected, 142.29 s; same 21 IDs |

The 25/100 `pg_stat_activity` peak for the six-worker default is carried from the completed r2
matrix, not re-measured. The final handover tree has checkpoint `4b5719d`; report-only plan and
handoff edits are the only post-run worktree changes.

## 3. Failure-ID set

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

## 4. Targeted and mutation evidence

Targeted repaired criterion: shipped default `53 passed`; `-n 0`: `52 passed / 1 skipped`;
`--numprocesses 0`: `52 passed / 1 skipped`.

| contract / mutation | scope and result | mutation-probe file checksum |
|---|---|---|
| C2 M4, definition-side `_template_operation_lock` body made a bare `yield` | criterion C2 rows (a)/(b)/(c) red with own errors: `UniqueViolationError`, `InvalidCatalogNameError`, `ObjectInUseError` | `app/tests/database_isolation.py` — `e62f471728b0e340402d5b91af58368e6b7f4fbddc088619699272d74b8ed5af` |
| C2 M5, call-site copy moved outside `_template_operation_lock` | C2 row (c) red with `ObjectInUseError`; rows (a)/(b) remain green under this call-site-only mutation | `app/tests/database_isolation.py` — `683acbe481680264361a18a5cb586dec4fe6a31cb4e972881e001191e8c698ad` |
| C8 sub-check 1, addopts worker count removed | red on positive-worker-count assertion | `app/pytest.ini` — `f69cce43676fa23338ded266fa58071307b8c7f4289cc8a2b01630e28ff2da97` |
| C8 repair tolerance, addopts raised to `-n 8` | green, one targeted test passed | `app/pytest.ini` — `d4601b9cf0bdd2070167cff38034be78da9b1b8084c264d2be12e1bc871bf073` |
| C8 sub-check 3, `PYTEST_ADDOPTS='-n 0'` | red on `PYTEST_XDIST_WORKER` assertion; the guard does not short-circuit | `app/tests/integration/infrastructure/test_database_isolation.py` — `433c8c0ee10488414ca1175c416cb3e9c593efffcb1118a87a90bdb600de9caf` |
| C8 comparator spellings `-n 0` and `--numprocesses 0` | both skip C8, each `52 passed / 1 skipped` | no mutation |

All mutation probes were reverted. Final relevant application checksums are criterion file
`433c8c0ee10488414ca1175c416cb3e9c593efffcb1118a87a90bdb600de9caf`,
`app/tests/database_isolation.py` `86434edf8eb3efff73e2ad4486967ffc4ba67b8df133b3875bc813336ba6c049`,
and `app/pytest.ini` `392e7102e99bb3646e402f7652318dc6e55843afedd75189655e406f2b4414b2`.

## 5. Probe resources and disposition

- C2 probe slots `p3absent`, `p3stale`, and `p3current`, including their template and worker
  databases, were removed by each test's `finally` path. The final server inventory contains only
  the persistent `beyo_test_main_template`; no `p3*`, `gw*`, legacy, or fixed-name probe database
  remains.
- The temporary C6 migration file `app/migrations/versions/phase3_c6_temporary_revision.py` is
  absent. No applied migration was rewritten.
- `beyo_manager` remained the configured development database and was not a destructive target;
  the criterion module's configured-database row-count guard passed.
- Redis was reachable at the configured URL. The discarded concurrent comparator attempt shared
  disposable probe slots between two L1 commands; it was not used as evidence. The serial reruns
  are the cited comparator evidence.

## 6. Architecture graph and owner follow-up

No graph mutation was needed or authorized for this fix. Graph status at session start was valid:
194 nodes, 291 edges, 0 diagnostics, 0 pending reviews, revision
`0dd6785a158409121a63063f3326bbcc440136333db42337a8742b71613463bd`. The separate owner-authorized
maintenance session remains responsible for its three settled-record repairs; this cycle did not
touch `.archgraph/`.
