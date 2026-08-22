---
plan: 2
role: fix
state: IMPLEMENTED
date: 2026-08-21
actor: codex
---

# Phase 2 fix r2 handoff

Resolved B1, S1 and S2 within the fix-cycle perimeter. B1 was a test visibility defect, not
an unclassified production race: the concurrent allocation assertion passed, while the
long-lived `db_session` returned a stale identity-mapped `SkuTemplate` with `last_scalar == 0`
after independent sessions committed `2`. Refreshing the row makes the test observe the
committed value. S1 now uses a fixed, reclaimable `phase2` probe slot and asserts disposable
database membership is unchanged across the entire criterion module. S2 is recorded below as
one evidence row per named mutation.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. B1 stayed inside the permitted SKU-test perimeter; no production-domain decision is
required.

## Implementation and perimeter

Cycle-scoped implementation changes — the only code files changed this session:

- `app/tests/integration/infrastructure/test_database_isolation.py`
  - replaced the random interrupted-template slot with fixed `phase2`;
  - added a module-scoped teardown assertion that `beyo_test_*` membership is identical before
    and after the criterion module, including when a test fails;
- `app/tests/integration/services/commands/sku_templates/test_sku_templates_commands.py`
  - refreshes the SKU row before asserting the result of the two committed allocation sessions.

Documents changed in this cycle:

- this handoff;
- `plans/plan_2.md` frontmatter and Review log.

Checkpoint commits:

- `0f08079` — `CHECKPOINT (not approved): phase 2 fix r2`;
- `8429442` — `CHECKPOINT (not approved): phase 2 fix r2 B1`.

No file under `app/beyo_manager/` changed.

Mutation-probe files, listed separately from the implementation changes above:

- `app/tests/database_isolation.py` — name, endpoint, marker, URL and residue assertions;
- `app/tests/conftest.py` — Redis settings override and collection-order hook;
- `app/tests/integration/infrastructure/test_database_isolation.py` — criterion rows for the
  guard, slots, Redis, residue and collection hook.

Reused prior-round probe files, not touched by this session: the worker-shift borrowing file,
the task-step collision file, and `app/beyo_manager/services/commands/pause_reasons/create_pause_reason.py`.

## B1 characterization and resolution

The reviewer-local reversal at `87a4b7a` measured `139 failed / 2422 passed / 1 deselected`;
the shipped `BEYO_TEST_COLLECTION_ORDER=reverse` hook measured `22 / 2560 / 1`. They do not
reverse identically, so the old 139-run figure was not a valid before-side comparator for the
shipped hook.

On the shipped-hook run, the SKU failure was:

```text
tests/integration/services/commands/sku_templates/test_sku_templates_commands.py:132:
assert 0 == 2
```

The preceding assertion `{first, second} == {1, 2}` passed. The test queried the same ORM
session that had loaded the row before two separate sessions committed the allocations, so the
identity-mapped row was stale. The repair is test-only (`await db_session.refresh(row)`) and
the targeted test passed (`1 passed in 0.55s`).

## Closing evidence

Both final L4 runs were taken after checkpoint `8429442`; the plan authorization explains why
this replacement pair was necessary after the first pair exposed B1. The implementation tree
was clean at the checkpoint; later plan/handoff edits are documentation-only.

| Hypothesis | Scope and command | Result |
|---|---|---|
| Criterion module reclaims every disposable database | L1, `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` | `36 passed in 3.84s`; module membership assertion passed |
| SKU stale-row repair observes committed allocation | L1, `PYTHONPATH=. pytest -q tests/integration/services/commands/sku_templates/test_sku_templates_commands.py::test_concurrent_allocations_return_distinct_scalars` | `1 passed in 0.55s` |
| Default collection order closing stamp | L4, `PYTHONPATH=. pytest -q --tb=line --show-capture=no -m 'not e2e'` | `21 failed / 2561 passed / 1 deselected` in `~128s` |
| Reversed collection order closing stamp | L4, `BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -q --tb=line --show-capture=no -m 'not e2e'` | `21 failed / 2561 passed / 1 deselected` in `129.26s` |

The final failure-ID sets are identical; `comm` is empty in both directions. Enumerated set:

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

The repaired task-step ID and SKU ID are absent. The 21 remaining IDs are the pre-existing
foreign failure stream carried by the published baseline; they are unchanged by this phase.

## S2 mutation ledger

Mutation probes were applied one at a time, run at the smallest scope that tested the named
hypothesis, and reverted. The targeted probes used checkpoint `0f08079` with a one-file dirty
mutation; the tree returned byte-for-byte before the next probe. Results below name the
reddened criterion rows.

| Named mutation and site | Scope and command | Reddened rows / result |
|---|---|---|
| Remove slot from `resolve_worker_database_name` return | L1, `...::test_worker_name_resolution` | all 4 `test_worker_name_resolution[...]` rows; `4 failed` |
| Replace slot rejection with `slot.lower().strip()` in `resolve_test_slot` | L1, `...::test_slot_resolution_rejects_invalid_values` | `[Alpha]`; `1 failed / 4 passed` |
| Disable database-name pattern branch in `assert_disposable_database` | L1, full criterion module | six invalid-name rows: injection, Unicode digit, trailing newline, uppercase, underscore and 13-character slot; `6 failed / 30 passed` |
| Disable configured-database tuple comparison | L1, `...::test_destructive_guard_rejects_every_unsafe_case` | configured database equality row; `1 failed / 11 passed` |
| Disable endpoint-confinement comparison | L1, same named guard test | different-host and different-port rows; `2 failed / 10 passed` |
| Disable marker/public-table refusal branch | L1, `...::test_unmarked_empty_database_is_allowed_but_populated_one_is_not` | populated markerless row; `1 failed` |
| Disable URL parsing entirely (`_parse_database_url` returns `make_url` directly) | L1, `...::test_destructive_guard_rejects_every_unsafe_case` | missing-URL and malformed-URL rows became uncaught SQLAlchemy `ArgumentError`s; `2 errors / 10 passed` |
| Make the configured-database residue assertion a no-op in `assert_configured_database_unchanged` | L1, `...::test_teardown_residue_proxy_detects_a_declared_probe_database_mutation` | residue proxy row; `1 failed` |
| Remove `settings.redis_key_prefix = prefix` in `isolated_redis_prefix` | L1, `...::test_default_redis_key_uses_the_process_prefix` | default Redis prefix row; `1 failed` |
| Reverse collection items when the env var is unset | L1, `...::test_collection_order_hook_is_off_by_default` | default-off hook row; `1 failed` |

The marker mutation is also C5's named mutation: making the absent-marker branch unconditional
lets the populated markerless database be dropped, and the same populated-row criterion
reddens. The URL parsing probe first tried disabling only the initial missing-value guard; that
shape stayed green because later validation still rejected the inputs. Disabling the complete
URL parser produced the two errors above, so the malformed and missing URL rows are load-bearing.

Reused prior-round evidence for the two C1 mutations and C7(a), not re-run on this unchanged
fix perimeter:

- restoring the unfiltered workspace lookup at `_seed_workspace_worker` produced `41 failed /
  1 passed`, the expected `AttributeError` row;
- restoring unconditional `Role(...)` creation in the task-step file produced `1 failed /
  1 passed`, the expected unique-index collision row;
- setting the production pause-reason creation flag true produced `1 failed / 4 passed` in
  the retirement criterion. The probe was reverted and no production file is in this cycle's
  diff.

## Probe databases and disposition

- Removed, after verifying 107 public tables and a valid marker: `beyo_test_shell_gw995`,
  `beyo_test_shell_template`.
- Fixed-slot criterion probes used `beyo_test_phase2_*` and were reclaimed by the test's
  `finally` blocks and module teardown assertion.
- Post-run server membership: `beyo_test_main_template` only among `beyo_test_*`; no worker
  probe or legacy shell database remains.
- The configured development database was not a disposal target; the configured row-count
  assertion passed.

## Architecture Graph

Final status: initialized and valid, 192 nodes / 289 edges, no diagnostics, revision
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`, three pending inferred
items. No additive graph delta was recorded: the changes remain within the existing
test-isolation boundary, and the graph is in review mode rather than graph-write mode.
