---
plan: 3
role: implement
state: IMPLEMENTED
date: 2026-08-21
actor: Codex
---

# Phase 3 implement r1 handoff

Pre-run declaration recorded before the first evidence run:

- Positional axis: file-level path order under `testpaths = tests`.
- Harness: three temporary DB+Redis probe modules at `connecteam`/prefix,
  `integration`/middle, and `unit`/suffix; collection-neutral when
  `BEYO_TEST_COLLECTION_PROBE` is unset.
- `n = 3`; probe positions are `prefix`, `middle`, and `suffix`.
- Planned evidence budget: `n + 8 = 11` L4 runs.

Pre-run authorization: execute matrix row 0 now as the required unperturbed
repeat/noise-floor run on the harness tree before enabling any probe and before
installing `pytest-xdist`.

Row 0 completed before the explicit `off` control was added. Pre-run
authorization for row 0b: execute the same full suite with
`BEYO_TEST_COLLECTION_PROBE=off`, proving that explicit harness disablement has
the same collection and failure-ID result as the unset noise-floor run.

Pre-run authorization for rows 1–3: execute exactly one full-suite run for
each declared probe position (`prefix`, `middle`, `suffix`) with
`--tb=no`; compare each failing-ID set in both `comm` directions with the
published 21 and admit an ID to the unstable set only after a repeat.

Perturbation result: rows 0, 0b, and 1–3 all retained the published 21-ID
failure set in both directions. The unstable union is empty. Rows 0/0b were
`21/2562/1`; rows 1–3 were `21/2563/1` because one selected probe was active.

Pre-run authorization for matrix row n+1: xdist is now installed from the
pinned development manifest; take the post-install serial comparator before
any worker-count run.

The initial `-n 2` diagnostic exposed four serial-assumption assertions in the
criterion module and one external app-update failure. The criterion assertions
are now worker-scoped; the app-update path was not present when targeted
inspection was attempted and remains reported as a parallel-only observation.
Pre-run authorization for the final row `n+2` re-measurement: rerun `-n 2
--dist loadfile` after this worker-scoping repair because the tree changed.

Row `n+2` final result: `21/2572/0` in 78.35s, matching the serial
comparator's 21 IDs in both directions; `pg_stat_activity` peak 20. The
shipped default remains serial as the conservative choice. Pre-run
authorization for row `n+3`: measure `-n 4 --dist loadfile` under the same
100-connection ceiling before deciding whether a higher count is useful.

Row `n+3` result: `21/2572/0` in 52.20s, matching the serial set in both
directions; `pg_stat_activity` peak 22. Pre-run authorization for row `n+4`:
measure `-n 6 --dist loadfile`; its observed peak must remain within the
documented connection budget.

The remainder of this handoff is completed at phase close.

## Result

Phase 3 is implemented. The shipped invocation remains serial:

```text
PYTHONPATH=. pytest -m 'not e2e' -q
```

The closing serial run on the completed implementation produced `21 failed / 2573 passed / 1
deselected` in 139.96 seconds. Its failure-ID set is exactly the 21-ID set below. A second
closing run at the same serial default is the final C5 scheduling condition; it must retain this
same set. Parallel evidence retained the same 21 IDs at `-n 2` on one run, while the
`app_update_presentations::test_selected_users_only_targeting` ID appeared on the re-measured
`-n 2` run and on both `-n 4` runs and the `-n 6` run. That is reported as a parallel scheduling
instability, not absorbed into the serial baseline.

| run | result | wall time | `pg_stat_activity` peak |
|---|---|---:|---:|
| post-install serial comparator | `21 failed / 2562 passed / 1 deselected`; same 21 IDs | 125.83 s | — |
| `-n 2 --dist loadfile` | `21 failed / 2573 passed`; same 21 IDs on first final row | 71.90 s | 20 (earlier measurement); 21 on re-measurement |
| `-n 4 --dist loadfile` | `22 failed / 2572 passed`; serial 21 plus app-update ID | 52.38 s / 52.08 s | 23 / 23 |
| `-n 6 --dist loadfile` | `22 failed / 2572 passed`; serial 21 plus app-update ID | 48.78 s | 25 |
| closing default, serial | `21 failed / 2573 passed / 1 deselected`; 21 IDs | 139.96 s | — |
| second closing default, serial | `21 failed / 2573 passed / 1 deselected`; same 21 IDs | 141.62 s | — |

The serial failure IDs are:

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

## Selected design and delegations

- Fixed, bounded names: `beyo_test_<slot>_template` persists; `beyo_test_<slot>_<worker>` is
  dropped after the process. Interrupted worker names are absorbed on the next start.
- A per-slot PostgreSQL advisory lock protects the full template ensure/rebuild and worker-copy
  region. The template is accepted by marker, dynamically derived Alembic head, required table
  set, and absence of the legacy baseline column; total public-table count is diagnostic only.
- `pytest-xdist==3.6.1` is pinned in `requirements-dev.txt`; no default `-n` was added. The
  existing `requirements.txt` diff (including its xdist/transitive entries and formatting) was
  preserved as an owner change visible at session start and is listed in the perimeter below.
- Legacy reclamation remains an explicit serial-only command because its sweep has global scope.
- Endpoint normalisation was implemented for equivalent loopback spellings and tested against a
  genuinely different host.

## Per-class disposition

| resource class | disposition |
|---|---|
| execution order | isolated, with one parallel scheduling instability separately published |
| module/session mutable state | isolated by worker database and Redis prefix |
| shared filesystem state | isolated; C6's temporary migration is unique and cleaned up |
| fixed ports | not reached; no fixed-port service is started |
| Redis | isolated per process |
| background workers | not reached |
| global caches | declared outside this phase's guarantee |
| environment mutation | isolated and restored by fixtures/monkeypatches |
| timestamps | declared inherited-suite behavior |
| unique constraints | isolated by fresh worker databases; adopt-or-create for global catalog rows |
| processes outside pytest | declared: PostgreSQL and Redis are external services |

## Full write perimeter

Own implementation and documentation changes:

- `app/pytest.ini`
- `app/requirements-dev.txt`
- `app/tests/conftest.py`
- `app/tests/database_isolation.py`
- `app/tests/integration/infrastructure/test_database_isolation.py`
- `app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py`
- `app/tests/connecteam/test_00_phase3_collection_probe.py`
- `app/tests/integration/test_50_phase3_collection_probe.py`
- `app/tests/unit/test_zz_phase3_collection_probe.py`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/plans/plan_3.md`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/planning/intention.md`
- `.archgraph/architecture.yml` (additive graph node and relationship recorded by the graph tool)
- this handoff

The owner-visible pre-existing diff in `app/requirements.txt` was not rewritten; it is included
in the session perimeter for review but was not mechanically altered by the implementation.
The architecture graph received one additive inferred infrastructure node and one contained-by
relationship at revision `6144a01a8ef0619b229b6a7d3ed8afa14b62baaf37570cef902b90fab0f20716`:
`Per-slot template-copy advisory lock` under `Per-process test database isolation`. No existing
node was promoted, rejected, edited, or source-linked.

Mutation-only files, separate from the implementation changes, were
`app/tests/database_isolation.py` and
`app/tests/integration/infrastructure/test_database_isolation.py`; every mutant was reverted.
The C6 test temporarily created
`app/migrations/versions/phase3_c6_temporary_revision.py`, applied it only to a probe database,
and removed it in `finally`; it is absent at close.

Mutation-probe file checksums at close (the mutations were always reverted):

| file | SHA-256 |
|---|---|
| `app/tests/database_isolation.py` | `eac2abd1ee781b02ad5bea7da523e7c66fa9ea60340d06e1905de58a19acd10c` |
| `app/tests/integration/infrastructure/test_database_isolation.py` | `1def631fd136b4b5504368fa1344eecd918ee43c29fc470fb512ef01132f8eed` |

Selected own-change checksums: `app/tests/conftest.py` =
`88c14779d00bc52f28fb4baccc7afb307c9e226b557d97e18d9a4d3ef6e5cbf8`,
`app/pytest.ini` = `fa5e8b9615b148cac5beeb596f46d7e6032956016c4d60552a125b0fe7239de5`,
`app/requirements-dev.txt` =
`973f72aad909917dd89132ae5c6b5dde103f44bd869ef6afc59df3d45ff3f986`, and
`app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py`
= `c0755d3e3e70cc208a9a04e69fbf0236b47d18a4125fa0795a7b69cee157e928`.

## Probe databases and residue

The deliberately named probe databases were `p3absent` (`gw900`, `gw901`), `p3stale` (`gw902`,
`gw903`, `gw904`), `p3current` (`gw905`, `gw906`, `gw907`), `p3c6` (`gw908`), and the held sibling
`beyo_test_main_gw990`. All were dropped by the tests or teardown. The final read-only query of
`pg_database` matching `beyo_test_%` returned exactly:

```text
beyo_test_main_template
```

The configured development database was never a destructive target.

## Mutation evidence

| mutation | reddened rows |
|---|---|
| remove template advisory lock | C2 absent-template and stale-template rows |
| ignore `PYTEST_XDIST_WORKER` | C3 worker observer |
| restore global membership snapshot | C3 teardown membership assertion with `gw990` |
| pin migration head to stale `EXPECTED_HEAD` | C6 temporary-revision rebuild |
| restore literal-only endpoint handling | all four equivalent endpoint-alias rows |

The perturbation harness's three positions plus unset and explicit-off controls all retained the
published 21-ID set; unstable union is empty. Total L4 budget: **11 runs**, with all targeted
criteria and mutation probes recorded as L1/L2 evidence outside that count.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.
