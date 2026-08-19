---
plan: 1
role: implement
state: IMPLEMENTED
round: 1b
date: 2026-08-19
actor: Codex
pipeline: inline_valuation_versioning
---

# Implementer handoff — phase 1, round 1b

Implemented inline valuation versioning on task creation, retired the live refusal
identity, rewrote the operational frontend handoff, and checkpointed the verified phase.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Checkpoint

- Commit: `6f825790c0e47e35e7f3fa638d2a68790382ebef`
- Subject: `CHECKPOINT (not approved): inline valuation versioning`
- Final production-file SHA-256:
  `10c5f350bf6d8e624a0bf9f2612510785c77435c1c3f8f69b2acee33f1772986`

## What was built

- `create_task` now loads an existing current valuation, inherits either omitted amount,
  compares both effective amounts plus request currency, and calls the existing
  `write_item_valuation_chain_in_session` only when that triple differs.
- An identical effective triple skips the writer and valuation audit entirely. The current
  row keeps its id, creator, open-chain state, and null `superseded_by_id`.
- New-item and existing-unvalued-item first writes still use the same shared writer.
- `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` was removed from live application/test/handoff
  surfaces. Repository-root verification over `app/` and `docs/handoff/` returned no hit.
- Operational handoff §9.1 now describes re-pricing, D17 inheritance, different-value
  versioning/credit, identical-value no-op, unvalued first write, and the deliberate
  wholesale-replace divergence of `PUT /items/{id}/valuation`. Frontend validation step 4
  now checks both different and identical prices. The remaining generic validation phrase
  was mechanically changed from `inline-pricing refusal` to `inline-pricing versioning`
  because C10 forbids asserting the retired behavior anywhere in the live document.

## Full write perimeter (generated from Git)

Checkpoint paths from `git show --format= --name-only 6f82579`:

1. `app/beyo_manager/services/commands/tasks/create_task.py`
2. `app/tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`
3. `app/tests/unit/docs/test_item_economics_handoff_accuracy.py`
4. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
5. `docs/architecture/under_construction/implementation/inline_valuation_versioning/master_plan.md`
6. `docs/architecture/under_construction/implementation/inline_valuation_versioning/plans/plan_1.md`

Post-checkpoint queue artifact from `git status --short`:

7. `docs/architecture/under_construction/implementation/inline_valuation_versioning/handoffs/implementer/2026-08-19_phase1_implement_r1b_handoff.md`

The HC-1 implementation/document perimeter is paths 1–4. Paths 5–7 are mandated pipeline
state/review/handoff records. No other workspace file changed.

Tool-recorded state: none. Architecture Graph previewed one description-only maintenance
edit, but the client approval channel rejected it; no graph record or graph mutation was
written.

## Test arithmetic and results

- Before: 2,340 selected = 2,314 passed + 26 failed; 1 deselected.
- Removed: 2 selected cases — the priced-item rejection integration test and the retired
  identity's generated parameter case in the literal registry.
- Added: 8 tests — C1–C5 and C8 integration tests, plus the live-surface C9 and handoff
  contract C10 unit tests.
- Renamed without count change: existing first-valuation coverage to C6 and existing
  inline-birth parameter rows to C7.
- After: 2,346 selected = 2,320 passed + 26 failed; 1 deselected.
- Focused final suite: 78 passed.
- Changed-file Ruff lint: passed.
- Full-suite failure-ID diff: added `[]`; removed `[]`.

The exact inherited failure set before and after was:

```text
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden
tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events
tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing
tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference
tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task
tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged
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

## Named mutation probes

All three probes touched only
`app/beyo_manager/services/commands/tasks/create_task.py`. Each was applied at the
production definition site, run, reverted with `apply_patch`, and returned to pre-probe
SHA-256 `63f5a81fafed0a248c75e7428c8b4086aa95ae16f0c1feca072766efc57c3447`.
The file's final SHA differs only because Ruff subsequently identified and the
implementation removed the refusal guard's now-unused earlier boolean initialization.

| Criterion | Definition-site mutation | Observed red output |
|---|---|---|
| C2 | Replace the effective-triple inequality decision with `should_write_valuation = True` | `test_c2_identical_inline_values_are_a_zero_write_noop`: `assert after_count == 1` → `E assert 2 == 1`; `1 failed in 0.95s` |
| C3 | Pass `request.item.expected_sale_price_minor` straight through instead of inheriting the current value | `test_c3_partial_inline_request_inherits_omitted_current_value`: `E assert None == 1200`; `1 failed in 0.90s` |
| C5 | Remove request/current currency from the effective-triple comparison | `test_c5_currency_only_change_creates_a_new_version`: `assert len(valuations) == 2` → `E assert 1 == 2`; `1 failed in 0.89s` |

## C1–C10 coverage and mutation bite map

| Criterion | Test coverage | Mutation it bites on |
|---|---|---|
| C1 | `test_c1_different_inline_values_version_chain_and_credit_task_creator` | A writer call omitted or task creator not passed leaves row count/chain/link/creator assertions red |
| C2 | `test_c2_identical_inline_values_are_a_zero_write_noop` | Equality decision deleted → exact row count becomes 2; also asserts same id/creator, open row, no successor, no valuation audit |
| C3 | `test_c3_partial_inline_request_inherits_omitted_current_value` | Omitted expected price passed through → persisted value is `None`, not `1200` |
| C4 | `test_c4_partial_effectively_identical_request_is_a_zero_write_noop` | Inheritance or equality semantics broken → the independent partial-identical fixture writes a second row or loses the inherited value |
| C5 | `test_c5_currency_only_change_creates_a_new_version` | Amount-only comparison → exact row count remains 1 instead of 2 |
| C6 | `test_c6_never_valued_existing_item_accepts_first_inline_price` | First-write path omitted → no valuation row/value |
| C7 | `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses` (six exact parameter rows) | New-item write or existing auto-commit routing changed → exact valuation/status assertions fail |
| C8 | `test_c8_no_inline_price_leaves_existing_valuation_untouched` | Trigger broadened → exact row count/id/open-chain/no-audit assertions fail |
| C9 | `test_retired_inline_refusal_identity_is_absent_from_live_sources`, the literal registry parameter set, and `test_no_document_names_an_unregistered_error_identity[operational]` | Identity retained anywhere under live package/tests/handoff sources → path-bearing assertion fails |
| C10 | `test_operational_handoff_documents_inline_repricing_contract` | Missing re-price/inherit/version/no-op/first-write/endpoint-divergence or validation wording → exact required-literal assertion fails |

## Deleted-assertion mapping

The removed rejection test pinned four things:

| Removed behavior/assertion | New coverage or deliberate retirement |
|---|---|
| A matched, currently valued item plus inline price raised the exact refusal identity | Deliberately retired. C1/C3/C5 now cover successful differing-value version writes; C2/C4 cover successful identical-value no-ops |
| The rejection rolled back task, task-item, and matched-item mutation | The rejection path no longer exists. C1 proves the task succeeds and versions; C2/C4 prove the task succeeds without a valuation write |
| The existing valuation remained a single open row after rejection | C2/C4/C8 cover the surviving one-row/no-supersession guarantee for no-op/no-trigger cases |
| A differing inline price could not grow the chain | Replaced by C1, which asserts the old row is superseded and linked to the new task-creator-credited version |

## Architecture Graph

- Inspected/reused: `command-task-create`, its `writes_to` relationships to
  `table-item-valuation`, `table-task`, and `table-task-item`, and its `reads_from`
  relationship to `table-item`.
- Impact budget/result: maximum depth 2; actual depth 1; 3 direct impacted nodes; 0
  transitive/possible; 0 new nodes of a maximum 15; context cost 0.
- Additive delta: zero. The existing command/table concepts and canonical edges remain the
  right architecture; this phase changes the command's behavior rather than creating an
  independently named boundary.
- Maintenance: previewed a description-only edit for the human-confirmed
  `node:command-task-create` (operation-set hash
  `c300d29abee87fb67ba5c08a6305793119aae50740a39b760eae8c7355ee92db`, no cascade).
  The client approval channel rejected application because this request did not explicitly
  authorize that exact settled-node mutation. No workaround or retry was attempted; no
  graph write occurred.
- Unresolved: the settled command description still says an existing priced item is
  refused, and one relationship evidence summary still names the refusal predicate. These
  require separately authorized graph maintenance.
- Permission/outcome: graph valid, revision
  `ab867312dafda5e89f5b08050451794d2c681f60344388dba727e336d8a40c7f`, mode `review`,
  maintenance available; authoritative writes applied: 0.

## DECISIONS I HAD TO MAKE

None. D-AUTH, D17, D18, M1, the four-file perimeter, and the live-document rewrite were
fully resolved. The C10 validation-overview wording change was a mechanical consequence of
the criterion, not a new semantic choice. Architecture Graph maintenance was governed by
the graph approval policy and was not improvised after rejection.
