# HANDOFF_TO_FRONTEND_live_working_time_clock_20260822

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822`
- Created at (UTC): `2026-08-22`
- Status: go-live and closeout
- Scope: live worked-time values for production time, budget status, and budget allocations
- This document is a new dated handoff. No published handoff was edited.

## 1. Go-live: retire the interim verdict-suppression flag

The live-working-time pipeline is now approved and this dated handoff is the promised
go-live signal. Retire the frontend's interim verdict-suppression flag now; do not
continue suppressing or marking `share_state` provisional while a step is working.

Render the server-served `worked_seconds`, `left_seconds`, and `share_state` together.
The backend computes the live open-work share and the verdict from the same basis, so
the client must render `share_state` as received and must not derive or override it.
This is the retirement promised by §4 of
`HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`; the pipeline's
closeout obligation is recorded in intention §5.4.

## 2. New dated handoff; the earlier corrections that survive

This document supersedes only the settled-only answer in §1 of the 2026-08-19 handoff.
That handoff was not edited in place, and neither was the 2026-08-18 production-time
handoff.

The 2026-08-19 handoff's §2 correction survives: the client must not manufacture a
verdict from a locally advanced time value. Its §3 ratio warning also survives:
typicals, fallback weights, excluded work, and the declared allocation method mean an
item-level ratio is not a contract. The 2026-08-15 operational handoff's live-versus-
frozen percentage distinction is corrected below by this new document; that published
handoff is not edited.

## 3. Correction to the 2026-08-18 “Live time” section

The old instruction to add `now − state_entered_at` to the served `worked_seconds`
value in the client is superseded. The server now serves settled work plus the
concurrency-averaged share of an open working interval on the production-time,
budget-status, and budget-allocations surfaces.

Client smoothing from time of receipt remains legitimate: it may add elapsed time on
top of the last served value between polls. It must not recompute the verdict, replace
the served value, or keep a previously displayed value after the server has disowned
time. This corrects the 2026-08-18 handoff's *Live time* section and follows intention
§5.4 and §6A C.

## 4. Answers to the four open questions

### 4.1 Is the live calculation feasible, and what does it cost?

Yes. The backend extends an existing read-path pattern that supplies one request-time
`now`, then computes the open-work contribution once and shares that basis across the
present-tense consumers. The covered surfaces do not need a client clock or a second
calculation path.

The cost is one batched probe for open records, followed by one SQL statement and two
in-memory sweeps for each distinct credited user with open work. The number of sweeps
is bounded by the smaller of the open records among the batch's non-deleted steps and
the number of distinct credited users in the workspace. The overnight-close condition
keeps the normal window under roughly 48 hours; that is a cost condition, not a
correctness dependency. See intention §§2.3A and 3.4A.

### 4.2 Do all worked-time fields move together?

Yes. On production-time, the section and budget worked-time fields, remaining time,
and present-tense verdict use the same live basis. The manager and worker faces of
budget-status use the same evaluated computation, and the batched allocation cards use
the same per-step figures. Non-worked-derived fields remain unchanged, and frozen
result blocks remain frozen. See intention §§4.1 and 4.1A.

### 4.3 What still consumes settled time?

The complete audit has eight consumer rows. Durable item-cost results, daily analytics,
settlement-time step cost and rollups, the typical-times aggregate, worker clock-out
analytics, and the task/step serializer remain settled consumers. The production-time
final block is partly live only in its present-time fields; its frozen values remain
frozen. The eighth row is an inert metrics helper with no callers. The live calculation
does not rewrite the settled step column, and no client should treat a live response as
payroll or archival data. See intention §2.5A and HC-1A.

### 4.4 Is the result deterministic?

Yes, when the request's `now` and database state are fixed. The covered surfaces take
one injected request time, including the date and typical-time cutoffs, and two
executions produce byte-identical payloads. The determinism contract is the named T1
test; the clock type, injection boundary, and covered call graph are defined in
intention §1A HC-3A and §9 T1.

## 5. When `worked_seconds` decreases: three modes and the client rule

There are exactly three client-visible decrease modes:

1. **Rounding sense.** A decrease of at most 1 second is the rounding bound. Smoothing
   may absorb it; a visible snap is not required.
2. **Disowning.** Marking any record of a step inaccurate, or removing the step, can
   remove the step's live contribution. Record deletion is not a shipped client event
   and is not a cause to handle. A drop larger than 1 second is authoritative: snap
   down immediately to the served value, reset the smoothing baseline, and accrue from
   the new time of receipt. Never clamp to the previous maximum, and do not animate the
   descent: render the drop in one step rather than easing the value down over time —
   the time is gone at once, not gradually.
3. **Settlement window.** Closing a working record can briefly make the served value
   dip before the asynchronous settlement recomputation returns it to the settled
   value. If it drops and returns within seconds, render both served values as given;
   do not hide the dip or infer which internal event caused it.

For every mode, smoothing may add elapsed time after receipt, but it must snap down to
the served value rather than clamp. Render `share_state` as received. There is no
`as_of` field by design, so the client does not distinguish a settlement-window dip
from another served decrease. See intention §§3.3, 3.3A, 5.4, and 6A C.

## 6. Architecture dependency and the frozen percentage correction

The four present-time projections now depend on the open interval records through the
same live-worked-time boundary: task budget status, its worker/seller face, task budget
allocations, and task production time. The task price-scenario projection composes
task budget status and therefore has the dependency transitively; it does not publish a
live worked-time field and must not be described as reading live seconds directly.

This is a read dependency only. No live value is persisted, no endpoint or response key
is added for this change, and the settled record and analytics boundaries remain intact.

For the published operational status table, the live percentage is still `null` when
the **current** allowance is zero or negative. The frozen `final.percent_consumed` and
worker-facing frozen `result.percent_consumed` use the frozen result's own reconstructed
allowance and are `null` only when that **frozen** allowance is zero or negative. A
current infeasible status does not blank a valid frozen percentage. This is the OD-10
correction from intention §5.3A, delivered here without editing the 2026-08-15 handoff.

## 7. Published approval baseline for the successor pipeline

The following is the approval reference point for `narrow_typical_work_times` D23. The
count is context; the failing-ID set is the durable comparator.

- **Runner:** from `app/`, `PYTHONPATH=. pytest -m 'not e2e'`, with six xdist workers
  and `--dist loadfile` supplied by `app/pytest.ini`'s `addopts`.
- **Required service:** Redis reachable at `settings.redis_url`.
- **Database:** each pytest process creates its own database from the migrated
  `beyo_test_main_template` and drops it at session end; this is not a development-
  database measurement.
- **Tree identity:** commit `dc76db8` — subject `CHECKPOINT (not approved): gate stamp
  + two rows that cannot fail, deleted` — with `git status --porcelain` empty at
  measurement time. Check out that commit to reproduce the measurement. As of
  2026-08-22 the backend's `app/` tree is identical to it (`git diff dc76db8 HEAD --
  app/` is empty), so a measurement taken on today's tree is comparable without
  checking anything out.
- **Result:** 21 failed / 2576 passed, collection 2597, measured in 50.61 seconds.
- **Relation to the previous baseline:** this 21-ID set is a strict subset of the
  previously published 26-ID set: five IDs were removed and zero were added. The
  subset relation was checked by document arithmetic; the five removed IDs are named
  in the provenance appendix below.

The complete 21-ID failing set is:

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

The five IDs removed from the former 26-ID baseline were:

```text
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model
tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden
tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference
tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task
tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged
```

## Provenance appendix

Semantic authority:

- `planning/intention.md:§1A HC-3A`
- `planning/intention.md:§2.3A`
- `planning/intention.md:§2.5A`
- `planning/intention.md:§3.4A`
- `planning/intention.md:§4.1A`
- `planning/intention.md:§5.3A`
- `planning/intention.md:§5.4`
- `planning/intention.md:§6A C`
- `planning/intention.md:§8`
- `planning/intention.md:§9 T1`

Implementation anchors:

- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py:load_live_worked_seconds`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py:_build_evaluated_status`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py:get_task_budget_status_worker`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py:get_task_budget_allocations`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py:get_task_production_time`
- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py:get_task_price_scenario`
- `app/beyo_manager/models/tables/tasks/step_state_record.py:StepStateRecord`

Baseline evidence:

- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md:§8`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md:§3`
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md:§4`
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md:Live time`
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md:status table`
