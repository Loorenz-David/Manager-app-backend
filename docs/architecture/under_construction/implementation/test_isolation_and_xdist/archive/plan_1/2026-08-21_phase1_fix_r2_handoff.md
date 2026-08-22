---
plan: test_isolation_and_xdist/plans/plan_1.md
role: implementer (fix)
state: IMPLEMENTED
verdict: READY_FOR_REVIEW
date: 2026-08-21
actor: codex
---

# Phase 1 fix r2 handoff

Implemented OD-1 and OD-2, plus the C6 and C8 should-fixes. **OWNER DECISIONS REQUIRED (0).**
`pytest-xdist`, `-n`, and parallel execution remain out of scope.

## Outcome

The template is now schema-only: a fresh database is migrated to `c1d2e3f4a5b6`, checked for
107 public tables and required DDL, and marked disposable. The `pg_dump`/`pg_restore` baseline
path, its local password-prompt fallback, and its development-database coupling are gone. The
nine tests that need reference rows now request narrow, version-controlled fixtures; no live
database data is copied.

The authoritative serial baseline is **22 failed / 2540 passed / 1 deselected / 2 warnings**.
The count is subordinate to the exact ID set below. The dev database remains at
`127.0.0.1:5433/beyo_manager`; after the run its counts are
`workspaces=11253, users=9809, tasks=2445, working_sections=1955`, and the only persistent
`beyo_test_*` database is `beyo_test_template`.

## Owner deliverables refreshed

1. **Current infrastructure:** pytest enters `tests/conftest.py`, creates a fixed-name process
   database from a migrated template, redirects `settings.database_url`, and drops the worker at
   teardown. PostgreSQL is the only isolated external state; Redis keeps its existing test key
   prefix fixture.
2. **Selected design:** fixed-name per-process databases from a persistent schema-only template.
   The template is rebuilt when its marker/schema is invalid or when the legacy
   `baseline_source` marker column identifies an old data-restored template.
3. **Files changed:**
   `app/tests/database_isolation.py`, `app/tests/conftest.py`,
   `app/tests/fixtures/phase1_reference_data.py`,
   `app/tests/integration/infrastructure/test_database_isolation.py`,
   and the four named integration test files under `app/tests/integration/`.
4. **Safety invariant:** destructive targets must match
   `^beyo_test_(template|main|gw\d+)$`, must not be the configured database, must parse as a
   PostgreSQL URL, and must contain the exact `beyo_test_metadata.database_marker`. Identifier
   quoting remains separately constrained by `_quoted_identifier`; malformed, missing,
   configured, unmarked, and injection-shaped targets fail closed.
5. **Lifecycle:**

   ```text
   configured DATABASE_URL
       -> resolve worker (serial: beyo_test_main)
       -> snapshot configured row counts
       -> ensure marked schema-only template via Alembic + DDL assertions
       -> drop-if-exists fixed worker name
       -> CREATE DATABASE worker TEMPLATE beyo_test_template
       -> mark worker and override settings.database_url
       -> run tests
       -> restore settings URL, terminate stragglers, drop worker
   ```

6. **Serial result:** closing L4 stamp below; no xdist was installed or invoked.
7. **Parallel result:** not run by phase 1; phase 2 owns installation and worker-count
   comparison.
8. **Before/after wall time:** prior measured shared development run: 135 s; shipped r1 with
   development-data restore: 169.7 s; coordinator-measured schema-only run before this fix: 109.1
   s. The closing fix-r2 stamp took 124.83 s on this tree; it is the authoritative correctness
   stamp, not a speed comparison because the owner’s concurrent tree and fixture additions are
   part of the measured repository state.
9. **Residue:** final read-only PostgreSQL check found only `beyo_test_template`; no worker
   database remains. The exact C8 probe artifacts `beyo_test_main9` and `beyo_test_gw9999` were
   removed after their probes. Development counts are unchanged from the session-start snapshot.
10. **Authoritative baseline:** exact 22-ID set below, with database and tree identity.
11. **Differences from the previous baseline:** exactly four IDs leave because their assertions
   depended on rows already present in the developer’s database, not on production code. No IDs
   were added. The confirmed order-dependent task-step test remains in the baseline.
12. **Remaining non-parallel-safe test:**
   `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task` passes
   when only the old 26 IDs run but fails in the full schema-only suite, so it depends on state
   created by another test. It is intentionally not fixed here and remains a phase-2 hazard.
13. **Recommended serial invocation:** `PYTHONPATH=. pytest -q` from `backend/app`.
14. **Recommended repeated mutation/full-suite invocation:** use the same serial invocation until
   phase 2 proves a parallel command; keep named mutants targeted to their criterion tests and
   compare any full run to the 22-ID set below.
15. **Remaining risks:** xdist may expose the known order dependency and other non-PostgreSQL
   shared state; the template is persistent and must remain at the migration head; fixture scopes
   were not widened; the three Architecture Graph items remain pending human review.

## Exact authoritative baseline

Tree identity: checkpoint `697b633039b90a465b6511a38232bbd6a7bce37f`, with
`git status --porcelain` empty at the L4 run. A later foreign documentation commit
`ec9cbb3a51789a78da0f8b6c5d4ae054120331ce` changed only `planning/intention.md` and does not
change the tested application perimeter.

Database identity: PostgreSQL at `127.0.0.1:5433`, configured database `beyo_manager`.

Failure IDs:

```text
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values
tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing
tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task
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

Previous baseline IDs removed, with the reason each now passes on schema-only isolation:

- `test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model` — the developer database already contained the bootstrap rows that the clean-schema test expects not to exist.
- `test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden` — the same developer-owned configuration/section contents made the clean-state predicate false.
- `test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference` — a developer database preference row already occupied the create path.
- `test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged` — the developer database’s existing task state prevented the clean-schema invalid-order setup from reaching its old failure.

Failure-ID delta at L4: **added = ∅; removed = the four IDs above**. No other difference was
observed.

## Evidence ledger

Every row records hypothesis, scope, command, tree identity, result, and both ID deltas. Targeted
rows use the checkpoint code tree where noted; the L4 row uses the clean checkpoint exactly.

| Hypothesis | Scope / command | Tree identity | Result and ID delta |
|---|---|---|---|
| Nine named tests need only explicit reference rows | L1/L2: `PYTHONPATH=. pytest -q --tb=short` with the nine named IDs | dirty pre-checkpoint diff; code later checkpointed as `697b633` | `9 passed`; contract delta `added ∅ / removed ∅`. The fixture rows, not a live snapshot, supplied each predicate. |
| C1-C8 contract after the fix | L1/L2: `PYTHONPATH=. pytest -q --tb=short tests/integration/infrastructure/test_database_isolation.py` | checkpoint code tree | `15 passed`; `added ∅ / removed ∅`. |
| C3 rejects stamp-without-DDL | L1: same C3 test after replacing `alembic upgrade head` with `alembic stamp head` and rebuilding the disposable template | mutation tree; source restored | setup stopped at `expected 107 public tables, got 1`; clean contract test ID was not collected under the mutant (`added ∅ / removed ∅`), and the DDL assertion—not the exit code—was the observed guard. |
| C6 catches a dev-URL override | L2: `PYTHONPATH=. pytest -q --tb=short tests/integration/services/commands/users/test_reconcile_worker_shift_state.py::test_concurrent_reconciles_create_one_open_shift_record tests/integration/infrastructure/test_database_isolation.py::test_dev_database_counts_are_untouched` | mutation tree; source and exact committed probe rows restored/removed | `1 passed, 1 failed`; C6 was added to the failure set, `added={test_dev_database_counts_are_untouched} / removed=∅`; observed counts grew by one in each named table. |
| C8 rejects unique worker creation | L1: `PYTHONPATH=. pytest -q --tb=short tests/integration/infrastructure/test_database_isolation.py::test_fixed_name_reabsorbs_an_interrupted_worker` with creation changed to `worker_name + "9"` | mutation tree; source restored and `beyo_test_gw9999` removed | clean assertion red: expected `beyo_test_gw999`, observed `beyo_test_gw9999`; `added={test_fixed_name_reabsorbs_an_interrupted_worker} / removed=∅`. The earlier wrong-site setup-error probe did not bite; the corrected site did. |
| Serial authoritative baseline | L4: `PYTHONPATH=. pytest -q --tb=no` | clean checkpoint `697b633`, status empty; DB `127.0.0.1:5433/beyo_manager` | `22 failed, 2540 passed, 1 deselected, 2 warnings in 124.83s`; `added=∅ / removed={the four IDs listed above}` against the prior 26. |
| Static quality | L1: `ruff check` on all eight changed Python files; `python3 -m compileall -q` on the same files; `git diff --check` | checkpoint code tree | all passed; `added ∅ / removed ∅`. |
| Residue and dev preservation | L1 environment check: read-only database membership and four row counts after the L4 run, following exact probe cleanup | post-L4 DB state | `beyo_test_*={beyo_test_template}` and counts `11253/9809/2445/1955`; `added ∅ / removed ∅` for the database-membership contract. |

## Architecture Graph and write perimeter

The graph was checked before and after implementation: initialized/valid, 192 nodes, 289 edges,
no diagnostics, revision
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`, three pending reviews, and
zero stale nodes. No graph mutation was made in this cycle: the existing isolation and contract
items are already pending human review, and agents are not authorized to edit or promote them.

Full write perimeter for this cycle:

- code/tests: the eight files in the checkpoint commit `697b633`;
- documents: this handoff and the append-only `plans/plan_1.md` review-log entry;
- tool-recorded state: no Architecture Graph delta.

Mutation-probe files, listed separately: `app/tests/database_isolation.py` and
`app/tests/conftest.py`. Probe artifacts, all removed: `beyo_test_main9`,
`beyo_test_gw9999`, and the exact committed rows created by the C6 mutation in workspace
`ws_01M0HX8YBXK0WWHWNVQCAKGN0F` and user `usr_01M0HX8YBVZYZT2RYT126QQRNC`.

## Checkpoint

`CHECKPOINT (not approved): fix schema-only test isolation` — `697b633`.

Phase 2 remains gated on review approval and owns xdist installation, serial/`-n 2`/`-n 4`
comparison, and the next topology-specific baseline.
