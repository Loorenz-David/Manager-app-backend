# Phase 1 — Worker money redaction

```
plan: phase 1
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Close the existing `total_cost_minor` exposure to WORKER and SELLER identities by
making `serialize_step`'s money emission a declared, fail-closed interface field
(intention §11A.3), across the complete census of §11A.2 **as corrected by the
round-5 amendment: five call expressions, EIGHT endpoints** (two shared builders
serve three endpoints beyond the round-3 table).
**NOT in this phase:** anything item-economics — no new tables, services, or payloads;
no change to what ADMIN/MANAGER see; no change to money emission on the two
ADMIN/MANAGER-only worker-stats endpoints (site 5 and endpoint 8 keep it); no change
to `serialize_item`'s item-money fields (owner projection card 1, 2026-08-12 → R5-2:
that exposure remains until phase 6 removes the columns).

## Read first

1. `master_plan.md` §§3, 5, 6.4–6.5, 9, 10 (workflow, contracts, environment).
2. Intention §11A.1–§11A.3 (exposure predicate, verified census, boundary
   declaration, named mutations M1–M5), §10.4, card 4 + R1-5 (owner decision).
3. Contract bundle per master plan §5 (re-emit before coding); especially
   `46_serialization` + local, `28_roles_permissions`, `15_testing`.

## Dependencies

None (first phase). Independent of all schema work — that is why it runs first: it
closes a live exposure and its review cannot be entangled with new-domain defects.

## Files expected to change

- `app/beyo_manager/domain/tasks/serializers.py` (`serialize_step`, verified at
  `:152` on 2026-08-12 — line numbers below date to 2026-08-11; re-verify by symbol)
- `app/beyo_manager/services/queries/tasks/tasks.py` (call site ~`:702`, `get_task`)
- `app/beyo_manager/services/queries/tasks/list_task_steps.py` (~`:57`)
- `app/beyo_manager/services/queries/working_sections/steps_list_payload.py` (~`:320`)
- `app/beyo_manager/services/queries/working_sections/step_record_payload.py` (~`:208`)
- `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`
  (~`:436` — site 5)
- **Deliberately NOT changing** (projection D1/D2, design (a)): the three round-5
  endpoint query services (`task_step_acknowledgments/list_reassigned_steps.py`,
  `task_step_acknowledgments/list_pending_step_acknowledgments.py`,
  `worker_stats/list_workers_last_interacted_step.py`) — they inherit correct
  behavior from the builders. An edit to any of them is out of perimeter.
- Existing tests that break under the new signature (projection D8; both named,
  handling pinned in Notes):
  `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py:1019`
  and `tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
- tests (new payload/role tests per the criteria table)

## Implementation tasks (ordered)

1. `serialize_step(step, *, include_monetary: bool)` — keyword-only, **no default**
   (§11A.3). When False, `total_cost_minor` is **absent from the dict** (never
   `null`).
2. **One shared pure helper** beside `serialize_step` deriving the flag from the role
   name, written as an **allow-list**: `role_name in {ADMIN, MANAGER} ⇒ True`,
   anything else — including WORKER, SELLER, and an absent/unknown `role_name`
   (`ServiceContext.role_name` defaults to `""`) — ⇒ False (projection D6). The
   deny-list form is forbidden.
3. Derive the flag via that helper **uniformly at every derivation point — no
   hardcoded booleans anywhere, site 5 included** (projection D5): sites 1 and 2 in
   their query services from the request identity; sites 3 and 4 **once inside each
   shared builder** from the `ctx` parameter the builders already receive (design (a),
   projection D2 / intention §11A.2 round-5 correction), so the three round-5
   endpoints inherit redaction (6, 7) and retention (8) with zero changes to their
   query services. If threading a parameter into a builder is ever preferred instead,
   it must be keyword-only with no default — but design (a) is the decided form.
4. Tests per the criteria table below. No other serializer or payload changes.

## Acceptance criteria

All automated (charter rule 1). Role-per-endpoint enumeration over the corrected
eight-endpoint census (§11A.2 incl. round-5 rows; enumerate, never sample — charter
rule 2). "money absent" = `total_cost_minor` key absent (assert key ∉ dict, not
`is None`); "money present" = the key present **and equal to the distinctive non-NULL
value the fixture seeded** — `total_cost_minor` is nullable, so presence alone proves
nothing (projection D4).

**Harness (projection D3):** every (endpoint × identity) row is a
**query-service-level integration test** — hand-built
`ServiceContext(identity={"role_name": ...})`, the query service called directly, a
real `TaskStep` ORM instance seeded via `flush()` on the rolled-back `db_session`
fixture (never committed; rule 11½ satisfied structurally). The repo's router-test
idiom (stubbed `run_service`) is **forbidden for these rows** — under it, mutations
M2–M5 never bite. Route *admission* (which roles reach each endpoint) is a documented
fact evidenced by the `require_roles` citations in §11A.2's tables, not by HTTP
tests. The "Endpoint" column below therefore names the surface whose query service
the row exercises.

| Row | Endpoint | Identity | Expected |
|---|---|---|---|
| 1 | `GET /tasks/{id}` | ADMIN | money present |
| 2 | `GET /tasks/{id}` | MANAGER | money present |
| 3 | `GET /tasks/{id}` | WORKER | money absent |
| 4 | `GET /tasks/{id}` | SELLER | money absent |
| 5 | `GET /tasks/{id}/steps` | ADMIN | money present |
| 6 | `GET /tasks/{id}/steps` | MANAGER | money present |
| 7 | `GET /tasks/{id}/steps` | WORKER | money absent |
| 8 | `GET /tasks/{id}/steps` | SELLER | money absent |
| 9 | `GET /working-sections/{id}/steps` | ADMIN | money present |
| 10 | `GET /working-sections/{id}/steps` | MANAGER | money present |
| 11 | `GET /working-sections/{id}/steps` | WORKER | money absent |
| 12 | `GET /working-sections/steps/user-last-active` | ADMIN | money present |
| 13 | `GET /working-sections/steps/user-last-active` | MANAGER | money present |
| 14 | `GET /working-sections/steps/user-last-active` | WORKER | money absent |
| 15 | `GET /worker-stats/{user_id}/daily-steps` | MANAGER | money **present** (the anti-blanket-redaction row) |
| 15b | `GET /worker-stats/{user_id}/daily-steps` | ADMIN | money present |
| 16 | direct call `serialize_step(step)` with no keyword | — | raises `TypeError` |
| 17 | `GET /task-step-acknowledgments/reassigned-steps` | ADMIN | money present |
| 18 | `GET /task-step-acknowledgments/reassigned-steps` | MANAGER | money present |
| 19 | `GET /task-step-acknowledgments/reassigned-steps` | WORKER | money absent |
| 20 | `GET /task-step-acknowledgments/pending` | ADMIN | money present |
| 21 | `GET /task-step-acknowledgments/pending` | MANAGER | money present |
| 22 | `GET /task-step-acknowledgments/pending` | WORKER | money absent |
| 23 | `GET /worker-stats/last-interacted-steps` | ADMIN | money present (anti-blanket row) |
| 24 | `GET /worker-stats/last-interacted-steps` | MANAGER | money present (anti-blanket row) |
| 25 | direct call to the derivation helper (or any row-8-style query) with identity whose `role_name` is absent/unknown (`""`) | — | money absent (the allow-list row, projection D6) |

Rows 17–24 are the round-5 census endpoints (intention §11A.2 correction). Each
redacted row's fixture gives the step a non-NULL `total_cost_minor`, so absence can
only come from redaction; each present row asserts equality against its seeded value
(sole-predicate companion, rule 2 + D4).

**Named mutations (intention §11A.3 table as extended by the §11A.2 round-5
correction — file + definition-vs-call-site; each must turn the listed rows red):**

- M1: default `include_monetary=True` in `domain/tasks/serializers.py::serialize_step`
  (definition) → row 16. (Row 16's test calls the function directly — a routed test
  cannot catch this.)
- M2: hardcode `include_monetary=True` at the `get_task` call site → rows 3, 4.
- M3: same at the `list_task_steps` call site → rows 7, 8.
- M4: hardcode `True` at `build_steps_list_payload`'s flag derivation (the builder,
  design (a)) → rows 11 **and 19**.
- M5: hardcode `True` at `build_step_record_payload`'s flag derivation → rows 14
  **and 22**.
- M6: flip the derivation helper from allow-list to deny-list
  (`not in {worker, seller}`) → row 25.

Rows 15/15b bite on blanket `False` at site 5's derivation; rows 23/24 bite on
blanket `False` at `build_step_record_payload`'s derivation (the retention side of
M5's builder).

## Notes

- Site 4 is the worker's live step card (`LastActiveStepCard.tsx`) — the most
  frequently fetched worker payload; a frontend smoke after deploy is a coordinator
  note, not a criterion.
- SELLER exclusion is the ratified round-3 unilateral resolution 2 (R4-3) — not
  revisitable here.
- **Owner decision (projection card 1 → R5-2, 2026-08-12):** the item-money exposure
  (`item_value_minor`/`item_cost_minor`/`item_currency` via `serialize_item` on
  worker-reachable task payloads) stays until phase 6 removes the columns. Phase 1
  touches `serialize_item` in no way; "money absent" means exactly the
  `total_cost_minor` key, nothing broader.
- **Existing-test handling (projection D8):**
  `test_ended_shift_bucket_collapse.py:1019` calls `serialize_step(step)`
  positionally — minimum edit only: add the keyword, change no assertion (it is a
  characterization test of an earlier project's published-names criterion).
  `test_list_working_section_steps_payload_characterization.py` asserts set-equality
  of `_STEP_KEYS` under a `"role_name": "worker"` context and **will fail on the
  redaction**: re-parametrize it by role (worker → `total_cost_minor` absent,
  manager → present with value) rather than deleting the key from the set, and record
  the key-set change in this Review log so the reviewer reads it as authorized.
- **Contract note (projection D7, recorded in master plan §5):** `46_serialization`'s
  router-owned-serialization rule diverges from the entire existing task/
  working-section query layer; phase 1 **keeps serialization at the query layer**,
  matching the code it modifies. Re-emitting the contract bundle must not be read as
  license to relocate serialization — that would blow the perimeter. The local
  contract file records the divergence in phase 9's drift batch.
- Archgraph: orient on `table-task-step`; expected delta ≈ zero new nodes (this is
  evidence-level change to existing payload behavior) — record the zero-delta
  statement explicitly at close.
- Criteria amendment 2026-08-12 (coordinator fold, rule 2): row 15b added — site 5's
  route admits ADMIN and MANAGER (`routers/api_v1/worker_stats.py:133`, verified);
  the table previously sampled MANAGER only. Row numbering preserved (M1 cites row 16).

## Review log

(append-only; implementer and reviewer entries land here)

### Implementer r1 — 2026-08-12 — Codex

- Baseline before implementation: `PYTHONPATH=. pytest -m 'not e2e'` collected 1602 tests, selected 1601; 1092 passed, 473 failed, 38 errors, 1 deselected. The failures/errors were caused primarily by sandbox-denied connections to the local PostgreSQL/Redis services, with unrelated unit failures also present.
- Implementation verification with the already-running containers: 57 phase-focused tests passed. Final full non-e2e run: 1624 collected, 1623 selected; 1601 passed, 22 failed, 1 deselected. The 22 failures are outside this phase (bootstrap/item-position/task-step/task-date/upholstery/working-section commands, audit log, Shopify dimension migration, auth, worker-stats unit seam, case serializer, item router, and upholstery-inventory router tests); all phase-focused tests passed.
- Implemented `serialize_step(step, *, include_monetary: bool)` with absent-key redaction, one allow-list helper for ADMIN/MANAGER, and helper-derived flags at all five serializer call sites. Shared builders cover the three round-5 acknowledgment/last-interacted endpoints without edits to those query services. `serialize_item` and item money fields were untouched.
- Authorized judgment calls: helper lives beside `serialize_step`; test fixture reuse imports the existing working-section step seed and flushes only the rolled-back `db_session`; characterization tests were role-parameterized rather than deleting the published key; the existing ended-shift characterization call received only the required keyword.
- Key-set change record: working-section and reassigned-step worker payloads now omit `total_cost_minor`; manager/admin rows assert the seeded value `4321`. The site-5 and endpoint-8 manager/admin retention rows assert the same value.
- Mutation probes: M1, M2, M3, M4, M5, M6, site-5 blanket-False, and shared-builder blanket-False all turned their named tests red and were reverted. Probe files: `app/beyo_manager/domain/tasks/serializers.py`, `app/beyo_manager/services/queries/tasks/tasks.py`, `app/beyo_manager/services/queries/tasks/list_task_steps.py`, `app/beyo_manager/services/queries/working_sections/steps_list_payload.py`, `app/beyo_manager/services/queries/working_sections/step_record_payload.py`, and `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`.
- Architecture Graph closeout: status remained valid at 116 nodes / 157 edges, revision `b0702c3c…`, zero stale nodes. The batched closeout apply recorded an exact duplicate of `table-task-step`, so `applied=[]`; architectural delta is explicitly zero.
- **S2 correction — 2026-08-12 — fix r2:** The verified healthy-container baseline is `545e504` → **1578 passed / 23 failed / 1 deselected** and checkpoint `4416570` → **1600 passed / 23 failed / 1 deselected**; the failure sets are byte-identical. The complete 23-item pre-existing failure set, confirmed again at the fix-r2 working HEAD, is:
  1. `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
  2. `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
  3. `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
  4. `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
  5. `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
  6. `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
  7. `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates`
  8. `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first`
  9. `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events`
  10. `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value`
  11. `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`
  12. `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it`
  13. `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set`
  14. `tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row`
  15. `tests/integration/test_audit_log.py::test_detail_defaults_to_empty_dict`
  16. `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`
  17. `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`
  18. `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
  19. `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
  20. `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
  21. `tests/unit/test_items_router.py::test_route_delete_item_issues_forwards_ids`
  22. `tests/unit/test_items_router.py::test_route_list_item_issues_forwards_client_id`
  23. `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

### Reviewer r1 — 2026-08-12 — Claude (plan-reviewer)

**Verdict: CHANGES_REQUESTED.** No behavioral defect found: the leak is closed on all
eight endpoints, fail-closed, and every named mutation bites. Two should-fix items
(both about what the tests and the record *prove*, not about what the code does),
six notes. Findings routed below with the exact correction clause per item.

**S1 — five acceptance-criteria rows have no asserting test (charter rules 1 + 2).**
Rows **9, 12, 17, 20, 23** — ADMIN, money present, on `/working-sections/{id}/steps`,
`/working-sections/steps/user-last-active`,
`/task-step-acknowledgments/reassigned-steps`, `/task-step-acknowledgments/pending`
and `/worker-stats/last-interacted-steps` — are unexercised. ADMIN appears in only
three places in the whole phase: `test_worker_money_redaction.py:23` and `:46`
(rows 1, 5) and `test_get_worker_daily_step_breakdown.py:169` (row 15b). The four
role-parametrized payload tests carry `["worker", "manager"]` only
(`test_list_working_section_steps_payload_characterization.py:228`,
`test_get_user_last_active_step_record_integration.py:154`,
`test_reassigned_steps_integration.py:262` for both the reassigned and the pending
assertion), and `test_worker_stats_endpoint_split_integration.py:31` (`_ctx`)
hardcodes `role_name="manager"` with no override, so row 23 cannot be reached.
Verified coverage is **19 of the 24 (endpoint × admitted role) cells, 21 of 26 rows**.
The plan enumerated all 24 deliberately after the round-5 correction; the
implementation samples them. *Correction:* add `"admin"` to the three parametrize
lists named above (and an ADMIN pass for the pending assertion at `:276`), and give
`test_worker_stats_endpoint_split_integration.py::_ctx` a `role_name` parameter so
`test_last_interacted_steps_keep_money_for_manager` (`:256`) also runs under ADMIN;
each added row asserts `== 4321`, not key presence. *Alternative, coordinator's call
only:* if the ADMIN rows are judged redundant because a single shared helper serves
ADMIN and MANAGER identically, amend the plan's criteria table to say so — five
enumerated criteria must not stay silently unmet.

**S2 — the recorded suite baseline is wrong, and master plan §10 makes later phases
inherit it.** The implementer r1 entry above records "1601 passed, 22 failed" at the
checkpoint and a pre-change baseline of 1092/473/38 taken in a sandbox with
PostgreSQL/Redis denied. Re-run with healthy containers (probe P-R1): the pre-change
commit `545e504` gives **1578 passed / 23 failed / 1 deselected** and the checkpoint
`4416570` gives **1600 passed / 23 failed / 1 deselected** — and the two failure
**sets are byte-identical**, so phase 1 introduced zero regressions and added 22
passing tests. The count is **23, not 22**, and the category list omits
`tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`.
*Correction:* replace the baseline numbers in the implementer entry (or add a
correction line) with the verified pair above and the 23-item list below, so
phase 2 does not compare against a number that was never measured.

**Verified pre-existing failure set (identical at `545e504` and `4416570`,
2026-08-12, healthy containers) — the inheritable baseline for phases 2–9:**

1. `integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
2. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
3. `integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
4. `integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference` ← **absent from the implementer's category list**
5. `integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
6. `integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
7–9. `integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::{test_set_current_stored_amount_inventory_demotes_low_priority_available_first, …_noop_emits_no_events, …_promotes_expected_candidates}`
10–11. `integration/services/commands/working_sections/test_batch_working_section_integration.py::{test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value, test_worker_working_sections_excludes_counts_for_deleted_parent_tasks}`
12–13. `integration/services/commands/working_sections/test_working_section_ordering_integration.py::{test_reorder_rejects_payload_not_matching_active_set, test_reorder_rewrites_sort_order_and_worker_view_follows_it}`
14–15. `integration/test_audit_log.py::{test_detail_defaults_to_empty_dict, test_write_audit_from_event_inserts_row}`
16–17. `unit/domain/shopify/test_dimension_migration.py::{test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values, test_legacy_seat_height_without_height_maps_without_zero_values}`
18. `unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
19. `unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
20. `unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
21–22. `unit/test_items_router.py::{test_route_delete_item_issues_forwards_ids, test_route_list_item_issues_forwards_client_id}`
23. `unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

Counts: `545e504` → 1578 passed / 23 failed / 1 deselected (1602 collected);
`4416570` → 1600 passed / 23 failed / 1 deselected (1624 collected). Command:
`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`.

**N1 — live frontend contract doc now misstates the worker payload.**
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
documents a **worker-app** page (`app_scope="worker"`, roles admin/manager/worker) and
publishes `total_cost_minor` as an always-present nullable int (`:393`, sample
`:166`). After this phase a WORKER receives no such key on that endpoint. Not a code
defect — the redaction is owner-ordered — but a published contract that is now false.
*Correction:* route to phase 9's docs/drift batch; coordinator note for the frontend
team, alongside the existing `LastActiveStepCard.tsx` smoke note.

**N2 — the money-audience boundary is stated nowhere in the architecture graph.** The
implementer's explicit zero delta is **confirmed correct** (see below), but the
ADMIN/MANAGER-only step-money audience is now a real architectural policy that no node
carries. *Correction:* carry forward to phase 9 as a candidate node/description, not a
phase-1 fix.

**N3 — cross-module id reconstruction in the new test.**
`tests/integration/services/queries/tasks/test_worker_money_redaction.py:32` and `:48`
rebuild the seeded task's `client_id` as
`f"tsk_{workspace.client_id.removeprefix('ws_')}"` because the imported `_seed_step`
returns no task. It is correct today and fails loudly (not silently) if that helper's
id scheme changes. *Correction:* optional — have `_seed_step` return the task, or
query it. No criterion depends on it.

**N4 — gratuitous whitespace churn in two pre-existing test files.** A stray blank
line added inside an unrelated test at
`test_get_worker_daily_step_breakdown.py:136-137`, and at
`test_reassigned_steps_integration.py:250` a blank line removed plus the new test
separated by one blank line instead of two. In perimeter, zero behavioral effect.
*Correction:* optional tidy on the next touch.

**N5 — tracker actor stamp overwritten.** The `4416570` tracker row read
`IMPLEMENTED | Codex`; the coordinator's consumption commit `d457d84` rewrote the
actor to `coordinator`, so the row no longer records who implemented the phase (and
this review's own gate check, which expects "actor Codex", mismatched). *Correction:*
process note for the coordinator — keep the producing actor and add consumption detail
to the Note column instead.

**N6 — rows 19 and 22 share one test function.** Both round-5 worker rows are asserted
inside
`test_reassigned_steps_integration.py::test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker`.
M4 and M5 each redden it (verified), and row 19 has a second independent witness in
the pre-existing pagination characterization, so detection is intact; a single failure
report just does not say which endpoint regressed. *Correction:* optional split.

**Verified correct (so re-review can skip it).**
- Census re-derived from the tree independently of every recorded census: exactly five
  `serialize_step` call expressions, no sixth; `build_steps_list_payload` has 2 callers
  and `build_step_record_payload` has 3; **eight** endpoints; all eight `require_roles`
  sets read directly from the routers and matching the plan's rows. No caller passes a
  synthetic `ctx` — every one is the request identity.
- Fail-closed construction: keyword-only, no default (`serializers.py:161`); the
  allow-list helper (`:153-158`) returns False for WORKER, SELLER, `""` and unknown;
  `ServiceContext.role_name` defaults to `""` (`services/context.py:40-41`). No
  hardcoded boolean at any of the five sites — site 5 included, per D5.
- Absent-key (not `null`) redaction at `serializers.py:187-188`.
- **No production consumer reads the key** — the only other `total_cost_minor`
  references in `beyo_manager/` are the ORM column and the analytics writers, so
  redaction cannot raise a `KeyError` downstream.
- **The redaction survives to the wire**: none of the four routers declares a
  `response_model`, and `build_ok` (`routers/http/response.py:11`) wraps the dict
  verbatim in a `JSONResponse` — no schema coercion re-adds the key. This is the one
  gap the query-service harness pin cannot see, so it was checked structurally.
- Mutation battery re-run independently in a disposable worktree at `4416570`:
  **M1–M6 plus both blanket-`False` probes all bite (8/8)**. M4 reddens row 11 **and**
  row 19 (two independent tests), M5 reddens row 14 **and** row 22 — the round-5
  pairing holds. All six probe files sha256-identical after revert.
- Sole-predicate companion: every redacted-row fixture seeds `total_cost_minor=4321`
  (five seed helpers + the unit stub), every present row asserts `== 4321`, every
  absent row asserts `key ∉ dict`. No row can pass vacuously — each indexes a payload
  that must exist first.
- Characterization authority (P-R4): `_STEP_KEYS` still contains `total_cost_minor`
  (`:48`) — the published key set was role-conditioned, not edited; the ended-shift
  test shows exactly the one-token keyword addition with no assertion change; the
  key-set change is recorded in the implementer entry.
- Scope fences: `serialize_item` untouched (item money stays until phase 6 per R5-2);
  the three round-5 query services untouched; serialization stays in the query layer
  per master plan contract-gap 2; ADMIN/MANAGER money retained on both worker-stats
  endpoints.
- Perimeter: `git diff 545e504..4416570` is exactly the 14 declared code/test files
  plus this plan and the master plan — nothing outside. The Review log edit was
  append-only and the master-plan edit touched only the phase-1 row.
- Archgraph zero delta **confirmed**: status unchanged (116/157, revision
  `b0702c3c…`, 0 stale, 244 pending), no node exists for `serialize_step` or for seven
  of the eight endpoints, `endpoint-worker-daily-step-breakdown`'s description says
  nothing about money or per-role visibility, and `table-task-step` describes
  `total_cost_minor` as a column (unchanged by this phase). Nothing in the graph became
  false. No discrepancy to file.

**Reviewer mutation-probe declaration.** Every probe ran in a throwaway `git worktree`
at `4416570` (`probe_head`), never in the working tree; a second worktree at `545e504`
served the P-R1 baseline. Files mutated and reverted there:
`domain/tasks/serializers.py`, `services/queries/tasks/tasks.py`,
`services/queries/tasks/list_task_steps.py`,
`services/queries/working_sections/steps_list_payload.py`,
`services/queries/working_sections/step_record_payload.py`,
`services/queries/worker_stats/get_worker_daily_step_breakdown.py` — each sha256
byte-identical after revert, worktree `git status` clean, both worktrees removed and
pruned. The primary tree was never modified (clean at `d457d84` before and after). DB
side effects: none committed — the suite's `db_session` fixture rolls back; the
configured database is left as found, at head.

### Fixer r2 — 2026-08-12 — Codex

- **S1 resolved:** added ADMIN to the existing role enumeration for the working-section list payload and last-active-step tests; parameterized the reassigned/pending payload test over MANAGER and ADMIN; and made the worker-stats `_ctx` accept `role_name`, running the last-interacted retention test for both MANAGER and ADMIN. Every added retained-money assertion is equality with the seeded `4321` value.
- **S2 resolved:** added the correction above without rewriting the historical implementer r1 record. The full 23-item failure list was reproduced at this working HEAD with healthy PostgreSQL/Redis; it matches the verified baseline set. The full run changed from the r1 checkpoint's `1600 passed / 23 failed / 1 deselected` to `1605 passed / 23 failed / 1 deselected` (`1629` collected), with no new failures.
- Focused verification: **39 passed** across the four changed integration modules.
- Optional notes N3, N4, and N6 were not taken: none is required by S1/S2, and keeping the cycle limited preserves the finding-scoped perimeter.
- No production code changed. Architecture Graph status remained valid at 116 nodes / 157 edges, zero stale nodes, revision `b0702c3c…`; no architectural delta was recorded.

### Reviewer r2 — 2026-08-12 — Claude (plan-reviewer, delta-scoped re-review)

**Verdict: APPROVED.** S1 and S2 are both resolved and independently verified. No new
findings; one cosmetic note carried forward. Settled ground from r1 was not re-derived,
per the charter's re-review protocol.

**Perimeter — PASS.** `git show ed99e7e` contains exactly the six allowed files: the
four test modules, this plan (Review log) and the master-plan tracker row. Nothing
outside. **No production code changed** — `git diff 4416570..ed99e7e --
app/beyo_manager/` is empty, so the redaction machinery approved on the merits in r1 is
byte-identical, and the r1 "Verified correct" list stands unchanged. Commits `3e40646`,
`65a20f0`, `bb7de26` after the checkpoint are coordinator docs only.

**S1 — RESOLVED.** All five previously untested rows now collect as live parameters and
assert equality with the seeded value: row 9 →
`test_list_working_section_steps_payload_key_sets_are_stable[admin-False]` and
`[admin-True]`; row 12 → `test_last_active_step_payload_applies_role_money_boundary[admin-True]`;
rows 17 and 20 →
`test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker[admin]`
(both assertions in that param); row 23 →
`test_last_interacted_steps_keep_money_for_manager[admin]`. Criteria coverage is now
**24 of 24 (endpoint × admitted role) cells, 26 of 26 rows**.

**R2-P1 — PASS. The WORKER rows survived the reshaping.** The two reshaped tests
parametrize only the *retained-money* context; the worker contexts take the `"worker"`
default, so rows 19 and 22 still execute — and now run **twice each**, once per
parameter. Verified by collection (14 ids across the five criteria tests) and by
mutation (below), not by reading alone.

**R2-P3 — PASS, probes run independently (fix r2 ran none).** In a disposable worktree
at `ed99e7e`, per-parameter granularity, control run 15/15 green first:

| Probe | Result |
|---|---|
| blanket `False` at site-5 derivation | RED — daily-breakdown test (rows 15 + 15b) |
| blanket `False` at `build_step_record_payload` derivation | RED — `last_interacted[admin]` **and** `last_interacted[manager]` (rows 23 + 24) independently; also `last_active[admin-True]`/`[manager-True]` (rows 12/13); worker row correctly green |
| M4 hardcode `True` at `build_steps_list_payload` | RED — `key_sets_are_stable[worker-False]`/`[worker-True]` (row 11) and the reassigned test under both params plus the pre-existing pagination characterization (row 19); admin/manager rows correctly green |
| M5 hardcode `True` at `build_step_record_payload` | RED — `last_active[worker-False]` (row 14) and the reassigned test under both params (row 22); retention rows correctly green |

**Additional probe (not requested — the sharpest test of whether S1's fix earns its
place): ADMIN dropped from the allow-list.** Exactly **nine** ADMIN-bearing ids went
red — one per endpoint plus the unit helper row — with **zero** ADMIN ids left green and
**zero** collateral reddening of any MANAGER or WORKER row. This is the defect the five
new rows exist to catch: before fix r2 it would have been caught on only three of the
eight endpoints, and an admin-visible money regression on the working-section list, the
live step card, both acknowledgment screens and the last-interacted roster would have
shipped green. The fix has real detection value, not just row-count conformance. It also
settles a doubt about the daily-breakdown test's sequential `for role_name in
("manager", "admin")` loop: the admin iteration does execute and does bite, so row 15b
is genuinely live (r1 note N6's shared-test caveat is cosmetic, not a coverage hole).

**S2 / R2-P2 — RESOLVED and exact.** The correction is **append-only** — the plan-file
diff for `ed99e7e` contains no deletions at all, and the historical implementer r1
numbers are preserved beside it (placement inside the implementer entry is exactly what
the r1 correction clause authorized). It carries the verified pair (`545e504` →
1578/23/1; `4416570` → 1600/23/1) verbatim, and its 23-item list was **set-compared
programmatically** against the r1 reviewer's verified set: identical in both directions,
no additions, no omissions.

**Arithmetic — PASS, exact.** Collection 1624 → **1629** = +5, matching the added
parameters precisely (characterization role 2→3 × group 2 = +2; last-active 2→3 = +1;
reassigned 1→2 = +1; last-interacted 1→2 = +1). Nothing else was added or removed.

**Full suite — PASS.** `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`:
**1605 passed / 23 failed / 1 deselected** (1629 collected), 55 s, containers healthy.
Zero connection noise (no `ConnectionRefused` / `OperationalError` / redis
`ConnectionError` lines), so this run is admissible evidence. The failure set is
**byte-identical** to the recorded 23-item baseline — the fix introduced no regression
and resolved none of the pre-existing failures.

**Archgraph — zero delta, confirmed.** Read-only `archgraph_status`: 116 nodes /
157 edges, revision `b0702c3c…`, 0 stale, 244 pending, unchanged. Trivially correct
here — the fix touched only test files, so no architecture could have moved. No
discrepancy filed.

**N7 — note (new, cosmetic, carry-forward).** Two test names now under-describe what
they assert: `test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker`
and `test_last_interacted_steps_keep_money_for_manager` both cover ADMIN, and the local
variables still read `manager_reassigned` / `manager_pending`. This matters mildly
because opacity about which roles were covered is what produced S1 in the first place —
a reader scanning names would conclude ADMIN is untested. *Correction:* rename to
`…_for_money_audience_roles_and_redact_worker` / `…_keep_money_for_money_audience_roles`
on the next touch of these files. Not a blocker and not worth its own cycle.

**Carry-forward dispositions (open notes at approval).**

| Note | Origin | Destination |
|---|---|---|
| N1 — live frontend handoff doc publishes `total_cost_minor` for the worker reassigned-steps page | review r1 | phase 9 docs/drift batch; coordinator note to the frontend team |
| N2 — money-audience boundary stated nowhere in the architecture graph | review r1 | phase 9 (candidate node/description) |
| N3, N4, N6 — id reconstruction, whitespace churn, rows 19/22 sharing one test | review r1, declined in fix r2 | closed as declined; N6 additionally settled by the ADMIN-drop probe |
| N5 — tracker Actor column overwritten | review r1 | absorbed: fix r2 preserved the reviewer stamp and appended its own |
| N7 — two test names under-describe their role coverage | review r2 | next touch of the two files; no dedicated cycle |
| Lessons P-G/P-H | review r1, folded by coordinator | master plan §9 |

**Reviewer mutation-probe declaration (round 2).** All probes ran in a throwaway
`git worktree` at `ed99e7e` (`probe_r2`); the primary working tree was **never
modified** — clean at `bb7de26` before and after. Files mutated and reverted inside the
probe worktree, each sha256 byte-identical afterwards:
`domain/tasks/serializers.py` (ADMIN-drop probe),
`services/queries/working_sections/steps_list_payload.py` (M4),
`services/queries/working_sections/step_record_payload.py` (M5 + blanket-False),
`services/queries/worker_stats/get_worker_daily_step_breakdown.py` (site-5
blanket-False). Worktree `git status` clean before removal; worktree removed and
`git worktree prune` run. DB side effects: none committed — `db_session` rolls back; the
configured database is left as found, at head. No migrations run. Archgraph: read-only,
nothing written.
