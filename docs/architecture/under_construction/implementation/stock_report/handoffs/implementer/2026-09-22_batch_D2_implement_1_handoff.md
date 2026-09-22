---
batch: D2
phases: [13A, 14]
role: implement
round: 1
state: IMPLEMENTED
date: 2026-09-22
actor: implementer (Opus, slot `d2i`)
tree: fcf2fb8 (app/ clean; later commits touch plans and this handoff only)
---

# Batch D2 — phases 13A and 14 implemented

**Checkpoint SHA: `fcf2fb8`** — the tree the L4 stamp covers, `app/` byte-identical
(`git diff --quiet -- app/` exit 0 after every mutation probe was reverted). Three checkpoint
commits, listed in §8.

**Every criterion row of both plans is satisfied by a test, and every named mutation was executed
at its site and observed red — except one row, C5(g), whose two named mutations are measurably
inert and which is reported as such rather than dressed up.** 42 rows, 41 new tests, 54 mutation
runs, L4 **23 / 3798 / 1** with both failure-ID diffs empty.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The four plan-cell corrections below are the coordinator's to fold, not
the owner's to rule: none changes an outcome, a contract, or a criterion's meaning — each only
records what the cell's own mutation was measured to do. I checked this claim against the two
plans and the ratified intention before writing it.

## 1. What was built

**Phase 13A — `POST /api/v1/location-tracker/webhooks/stock-demand-deleted`.**

| File | What |
|---|---|
| `bm/domain/stock_report/enums.py` | `StockDemandDeletedOutcomeEnum` (`deleted`, `not_found`, `category_not_found`) — **that one name only**. `INLINE_REPAIR_TRIGGERS` deliberately not added: `write_repair_record` takes a free-form trigger string, so it would have no caller (charter rule 4). |
| `…/stock_report/stock_demand_entries.py` | `DemandDeleteEntry` (`DemandEntry` minus `quantity_requested`, same derived `item_category_key`) and `DemandDeleteOutcome`. |
| `…/stock_report/stock_demand_deleted_request.py` (new) | `parse_stock_demand_deleted_body`, with the two MC-8 field checks written **inline** — phase 7 is not touched, card D-3 applied. |
| `…/stock_report/process_stock_demand_deleted.py` (new) | The owning command, exactly task 3's step list. |
| `bm/routers/api_v1/location_tracker_webhooks.py` | The third route, the shape of the other two. |

**One load-bearing pointer per criterion group**, so a reviewer does not have to find them:
the deadline is `process_stock_demand_deleted:process_stock_demand_deleted` first line; the
advisory lock is taken at step 3, **before** discovery; class 3 is `lock_tasks`, class 4 is
`process_stock_demand_deleted:_lock_rows_and_groups` (one statement, groups named by subquery),
class 5 is `lock_stock_task_assignments`; the post-lock re-read is the `row_id not in locked_rows`
guard; the cascade loop runs ascending `client_id`; the deadline check is the last statement inside
the block.

**Phase 14 — the documents.** `docs/domains/stock_report/api.md` (thirteen routes, bodies,
payloads, errors), `docs/domains/stock_report/states.md` (the six-state machine, the soft-delete
predicates, the full cascade strategy), the re-verified frontend handoff (§4 below) and
`app/tests/unit/docs/test_stock_report_docs.py`.

## 2. Task 0 — the coverage map, one line per criterion ROW

Written before the first production edit; the red baseline is in §3.

### Plan 13A — 37 rows in 7 criteria

| Row | Test that discharges it | Is the assertion the row's shape? |
|---|---|---|
| C1(a) | `test_c1a_a_missing_api_key_is_401_and_writes_nothing` | yes — 401, the exact message, R still live, `count_writes == 0` |
| C1(b) | `test_c1b_a_wrong_api_key_is_401_and_writes_nothing` | yes |
| C1(c) | `test_c1c_a_wrong_key_with_an_unparseable_body_is_401_not_422` | yes — the raised class is asserted, so a 422 fails it |
| C1(d) | `test_c1d_an_empty_array_is_refused` (unit) | **stronger** — asserts *which* 422 (the array-shape message) |
| C1(e) | `test_c1e_one_entry_sent_unwrapped_is_refused_as_a_shape_defect` (unit) | **stronger, and it has to be** — see finding F-1 |
| C1(f) | `test_c1f_an_entry_without_properties_is_refused` (unit) | yes |
| C1(g) | `test_c1g_properties_null_is_refused` (unit) | yes |
| C1(h) | `test_c1h_a_blank_item_category_is_refused` (unit) | yes |
| C1(i) | `test_c1i_an_unknown_quantity_requested_key_is_ignored` (integration, the cell's literal `5`) + `test_c1i_quantity_requested_is_ignored_and_the_entry_shape_is_the_registered_one` (unit, `"seven"`) | the integration half matches the cell and **cannot fail** under the cell's own mutation; the unit half is what arms it — finding F-2 |
| C1(j) | `test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing` | yes — names `entries 0 and 1` and asserts the live row survives |
| C1(k) | `test_c1k_every_offending_entry_is_named_and_the_good_one_is_not_applied` | yes — both indices named, R live |
| C2(a) | `test_c2a_an_exact_identity_is_deleted` | yes (the positive control) |
| C2(b) | `test_c2b_a_case_variant_category_resolves_and_deletes` | yes |
| C2(c) | `test_c2c_an_ambiguous_case_insensitive_match_resolves_to_nothing` | yes |
| C2(d) | `test_c2d_an_unknown_category_does_not_stop_the_other_entries` | yes — both outcomes in request order |
| C2(e) | `test_c2e_properties_are_matched_on_the_normalized_signature` | yes |
| C2(f) | `test_c2f_an_identity_that_exists_only_in_a_foreign_workspace_is_not_found` | yes — as a genuine cross-workspace reference; see judgment call 3 |
| C2(g) | `test_c2g_an_already_deleted_row_is_not_found` | yes |
| C2(h) | `test_c2h_an_identity_that_was_never_created_creates_nothing` + `test_c2h_emits_no_created_event` | yes — zero INSERT, no live row afterwards, and nothing dispatched |
| C3(a) | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited` | yes — six assignments, one per state; goal 10 → 8; counters (1,3,2) → (0,0,0); NULL authorship; six task flags cleared |
| C3(b) | `test_c3b_tasks_task_steps_and_items_are_never_touched` | **partly** — the task and item halves are exact; the fixture's tasks have no steps, so the step clause is asserted as "still zero" (finding F-5) |
| C3(c) | `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order` | yes |
| C3(d) | `test_c3d_the_coalesced_event_list_is_exactly_these_events` | yes — multiset with per-name counts, the six assignment events as a `{client_id: state}` mapping, `workspace_id` on every event |
| C3(e) | `test_c3e_a_later_demand_for_the_same_identity_creates_a_fresh_row` | yes |
| C4(a) | `test_c4a_a_replay_is_not_found_and_writes_nothing` | yes — zero writes over the five tables, nothing dispatched |
| C4(b) | `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record` | yes — the record's seven fields, then zero writes and **still exactly one** |
| C5(a) | `test_c5a_the_webhook_waits_on_the_task_before_it_takes_the_row` | yes — the 0.5 s non-return, the holder's own `FOR UPDATE` inside 0.5 s, the deleted outcome |
| C5(b) | `test_c5b_two_rows_of_one_group_each_close_their_own_gap` | yes — both deleted rows' retained orders, the dense group, the event multiset, and the four one-statement-per-class counts |
| C5(c) | `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order` | yes |
| C5(d) | `test_c5d_the_find_step_is_set_based_for_all_not_found[3]`/`[30]` and `…_all_category_not_found[3]`/`[30]` | yes — exactly 5 and exactly 4, identical at 3 and at 30 |
| C5(e) | `test_c5e_the_consistency_check_stays_empty_in_both_workspaces` | yes |
| C5(f) | `test_c5f_the_workspace_reset_still_clears_everything` | yes |
| C5(g) | `test_c5g_two_demand_batches_with_overlapping_new_identities_do_not_deadlock` | **the positive half only** — the sorts are not armed by it, measured; finding F-4 |
| C6(a) | `test_c6a_the_first_statement_sets_both_limits_from_the_default` | yes — first recorded statement, both parameters from the field's default |
| C6(b) | `test_c6b_the_deadline_is_checked_before_the_commit` | yes — 503, and nothing committed |
| C7(a) | `test_c7a_stock_demand_deleted_route_forwards_raw_bytes_and_headers` + `…_renders_build_err_for_a_faked_auth_error` | yes |
| C7(b) | `test_c7b_every_result_echoes_the_entry_byte_for_byte` | yes — exact key set per element and byte-for-byte echo |

### Plan 14 — 5 rows in 2 criteria

| Row | Test | Shape |
|---|---|---|
| C1(a) | `test_c1a_api_md_carries_every_route_with_its_roles` + `test_c1a_api_md_documents_no_route_the_app_does_not_serve` | yes, both directions |
| C1(b) | `test_c1b_every_event_name_the_code_builds_is_in_the_handoff` + `test_c1b_the_handoff_names_no_event_no_site_builds` | yes, both directions |
| C1(c) | `test_c1c_every_error_class_and_identity_appears[api.md]`/`[handoff]` | yes, per document |
| C1(d) | `test_c1d_every_assignment_state_appears[states.md]`/`[handoff]` | yes, per surface |
| C2(a) | `test_c2a_the_handoff_nullability_matches_the_shipped_serializer[×4]` + `test_c2a_at_least_one_field_of_each_kind_exists_to_discriminate` | yes — equality per field, plus the condition cell, plus the check that the comparison can disagree |

**The map runs both ways.** Every test in the five files traces to a row above; there are **no
orphan tests** and no candidate criteria are proposed.

## 3. The red baseline, captured before the first production edit

Command (slot `d2i`, the four new/extended test files):
`3 errors, 2 failed, 5 passed` — the three new test files failed to **collect**
(`stock_demand_deleted_request` and `process_stock_demand_deleted` did not exist, and
`StockDemandDeletedOutcomeEnum` was unshipped), and the two new router tests failed 404 because the
third route did not exist. The 5 passed are the pre-existing plan-7 and plan-9 router tests. This
was taken at `bb704f5`, before any production file was touched.

## 4. Task 3 — the frontend handoff re-verification, and the §6.1 `properties` defect

**Answer: the defect is real, the code is right, the document was wrong, and the re-issue path
applied.** `normalize_stock_criteria` lower-cases, trims, de-duplicates and **sorts** each
criterion's values and turns a single string into a one-element list; `apply_stock_demand` stores
`properties_normalized`; `serialize_stock_report_item` returns `row.properties` unchanged. So the
stored, normalized form the endpoint returns is `{"wood_group": ["teak"]}` and the superseded §6.1
example's `{"wood_group": "teak"}` could never be emitted. (The membership test at
`criteria_matcher.py` — `token in accepted` — happens to be true for a bare string too, which is
why nothing had caught it.)

Three further things moved: the delete webhook is built and its response shape was undocumented;
no route is SPECIFIED any more; nullability is now per field.

**What I did, exactly.** A **new** dated file
`handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` with a `supersedes:` key
naming `…_api_v2_20260921.md`, a §0 table of what is current and what is historical, and a §0.1
listing the four changes. The superseded file was moved with `git mv` to `archived/` — **unedited**;
`git show` of the rename confirms zero content change. `…_match_preview_v2_20260921.md` was **not**
superseded and **not** moved, and the new document points at it for that endpoint's semantics. The
published file was never opened for writing.

The six SPECIFIED routes were read field by field against the shipped code before re-issue: roles,
bodies, strictness, the two no-ops, the 404-not-empty-list rule, the refusal identities. All six
matched what the frontend was promised; only the four things above moved.

## 5. Findings against the plans (routed to the coordinator; none changes an outcome)

- **F-1 — 13A C1(e)'s named mutation cannot move the row's stated outcome.** Dropping
  `isinstance(payload, list)` makes a bare JSON object iterate as its key list; every key is a
  `str`, so the entry loop produces per-entry defects and the answer is **422 either way**. The
  test therefore asserts *which* 422 (the array-shape message), and the mutant reddens it. The
  cell's parenthetical ("reaches the entry loop → red") is right about the path and wrong about
  the outcome.
- **F-2 — 13A C1(i)'s fixture cannot fail under its own mutation.** With `"quantityRequested": 5`
  a mutant that validates the key accepts it. Measured: under M8 the integration row stayed green
  while 28 other tests reddened. The unit half now sends `"seven"`; re-run M8-r reddens it. The
  cell's literal is worth amending to a value the demand rule would refuse.
- **F-3 — 13A C5(e)'s second named mutant is inert.** "Drop the `workspace_id` term in step 5
  (W′'s row is deleted)" presumes the foreign workspace holds the *same identity tuple*, which a
  naturally seeded foreign workspace does not — its category id differs. Measured: M17 reddens
  C2(f) alone and leaves C5(e) green. C5(e) is armed by its first mutant.
- **F-4 — 13A C5(g) does not arm the two sorts. Measured four times, twice at each size.** Both
  named mutations stay green at two identities and at forty. The reason is structural, not fixture
  size: each batch's absent identities go in as **one** multi-row `INSERT … ON CONFLICT DO
  NOTHING`, a backend runs that statement to completion unless it blocks, and the second session's
  statement compilation costs more than the first session's whole insert — so the first holds every
  new row before the second touches one, and the second then blocks on a single row while holding
  none. No cycle can form in either sort order. The row's **positive** half is real and asserted
  (both batches complete, one live row per identity, created exactly once, no `DBAPIError`); the
  sorts need §9 rule 9's structural check, which the test's docstring now names and which is
  satisfied at `apply_stock_demand.py` (`sorted(...)` on `absent_identities`, `.order_by(client_id)`
  on the locking `SELECT`). **The cell should say so.** This is the one row I could have quietly
  claimed as armed; the ledger shows the green.
- **F-5 — 13A C3(b)'s step clause is unexercised, not unmet.** The fixture's six tasks carry no
  task steps, so "the count and states of its steps" is asserted as "still zero". The task half is
  armed (M22 soft-deletes the tasks inside the cascade and reddens the row alone).
- **F-6 — reference only.** 13A §6 says the seeding procedure uses "phase 11's
  `set_stock_report_item_priority_order`". That command is phase **12**'s.
- **F-7 — plan 14's C2(a) says "the three serializers".** There are four
  (`serialize_stock_report_item`, `serialize_stock_task_assignment`, `serialize_item_compact`,
  `serialize_task_compact`). The guard covers all four — a superset, not a narrowing.

## 6. Named-mutation ledger — `executed == declared`

**Arithmetic, per criterion, countable against the table below and derived from the cells, not
typed.** A cell that says "both runs recorded", "two mutants" or "three mutants" declares that
many; a cell whose text offers two phrasings separated by `/` with no such instruction is counted
as **one** required mutant (I ran both sides anyway wherever it was cheap, and those runs are in
the table).

* **13A = 42.** C1 11 (one per row; (a) and (b) share a site and are two recorded runs) · C2 8 ·
  C3 7 (a 2, b 1, c 1, d 2, e 1) · C4 2 (one edit, two recorded runs) · C5 10 (a 1, b 3, c 1, d 1,
  e 2, f 1, g 2) · C6 2 · C7 2.
* **14 = 8.** C1(a) 1 · C1(b) 3 · C1(c) 1 · C1(d) 2 · C2(a) 1.
* **Declared 50. Executed 54.** Every declared mutation ran; the surplus is named, not hidden:
  **M8-r** (M8 re-run against the corrected C1(i) fixture), **M11** and **M24** and **M44b** (the
  second phrasing of a `/` cell, run because it was one line), **M49b** and **M53** (the second
  document / the second half of a row that asserts two things — charter rule 12), **M39-b** and
  **M40-b** (the 40-identity re-measurement behind finding F-4), and **M31b** (a self-chosen
  reordering probe, declared below). Nothing in either plan is unrun.

| # | rows | site | observed red (failing ids) | reverted |
|---|---|---|---|---|
| M1 | C1(a), C1(b) | `process_stock_demand_deleted.py` (def.) — the `verify_location_tracker_webhook` call deleted | `test_c1a_a_missing_api_key_is_401_and_writes_nothing`, `test_c1b_a_wrong_api_key_is_401_and_writes_nothing`, `test_c1c_a_wrong_key_with_an_unparseable_body_is_401_not_422` (3 failed, 30 passed) | `git diff --quiet` exit 0 |
| M2 | C1(c) | `process_stock_demand_deleted.py` (def.) — parse moved before verify | `test_c1c_a_wrong_key_with_an_unparseable_body_is_401_not_422` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M3 | C1(d) | `stock_demand_deleted_request.py` (def.) — `len(payload) == 0` dropped | `test_c1d_an_empty_array_is_refused` (1 failed, 5 passed) | `git diff --quiet` exit 0 |
| M4 | C1(e) | `stock_demand_deleted_request.py` (def.) — `isinstance(payload, list)` dropped | `test_c1e_one_entry_sent_unwrapped_is_refused_as_a_shape_defect` (1 failed, 5 passed) | `git diff --quiet` exit 0 |
| M5 | C1(f) | `stock_demand_deleted_request.py` (def.) — `properties` defaults to `{}` | `test_c1f_an_entry_without_properties_is_refused` (1 failed, 5 passed) | `git diff --quiet` exit 0 |
| M6 | C1(g) | `stock_demand_deleted_request.py` (def.) — `null` properties coerced to `{}` | `test_c1f_an_entry_without_properties_is_refused`, `test_c1g_properties_null_is_refused` (2 failed, 4 passed) | `git diff --quiet` exit 0 |
| M7 | C1(h) | `stock_demand_deleted_request.py` (def.) — `.strip()` dropped from the itemCategory check | `test_c1h_a_blank_item_category_is_refused` (1 failed, 5 passed) | `git diff --quiet` exit 0 |
| M8 | C1(i) | `stock_demand_deleted_request.py` (def.) — `quantityRequested` validated as an int | `test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing`, `test_c2a_an_exact_identity_is_deleted`, `test_c2b_a_case_variant_category_resolves_and_deletes`, `test_c2c_an_ambiguous_case_insensitive_match_resolves_to_nothing`, `test_c2d_an_unknown_category_does_not_stop_the_other_entries`, `test_c2e_properties_are_matched_on_the_normalized_signature`, `test_c2f_an_identity_that_exists_only_in_a_foreign_workspace_is_not_found`, `test_c2g_an_already_deleted_row_is_not_found`, `test_c2h_an_identity_that_was_never_created_creates_nothing`, `test_c2h_emits_no_created_event`, `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3b_tasks_task_steps_and_items_are_never_touched`, `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c3e_a_later_demand_for_the_same_identity_creates_a_fresh_row`, `test_c4a_a_replay_is_not_found_and_writes_nothing`, `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[3]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[3]`, `test_c5e_the_consistency_check_stays_empty_in_both_workspaces`, `test_c5f_the_workspace_reset_still_clears_everything`, `test_c6a_the_first_statement_sets_both_limits_from_the_default`, `test_c6b_the_deadline_is_checked_before_the_commit`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (28 failed, 11 passed) | `git diff --quiet` exit 0 |
| M8-r | C1(i) | `stock_demand_deleted_request.py` (def.) — `quantityRequested` validated as an int, **re-run against the corrected fixture** | `test_c1i_quantity_requested_is_ignored_and_the_entry_shape_is_the_registered_one` plus the 28 integration ids M8 already reddened (29 failed, 10 passed) | production restored, `git diff --quiet -- app/` exit 0 (the tree-wide check saw the plan files this session was editing) |
| M9 | C1(j) | `stock_demand_deleted_request.py` (def.) — duplicate key built from the raw dict | `test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M10 | C1(k) | `stock_demand_deleted_request.py` (def.) — `continue` → `break` (stop at the first defect) | `test_c1k_every_offending_entry_is_named_and_the_good_one_is_not_applied` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M11 | C1(k) | `stock_demand_deleted_request.py` (def.) — defects ignored when any entry parsed (apply entry 1) | `test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing`, `test_c1k_every_offending_entry_is_named_and_the_good_one_is_not_applied` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M12 | C2(a) | `process_stock_demand_deleted.py` (call site) — the cascade loop iterates nothing | `test_c1i_an_unknown_quantity_requested_key_is_ignored`, `test_c2a_an_exact_identity_is_deleted`, `test_c2b_a_case_variant_category_resolves_and_deletes`, `test_c2d_an_unknown_category_does_not_stop_the_other_entries`, `test_c2e_properties_are_matched_on_the_normalized_signature`, `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c3e_a_later_demand_for_the_same_identity_creates_a_fresh_row`, `test_c4a_a_replay_is_not_found_and_writes_nothing`, `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c5e_the_consistency_check_stays_empty_in_both_workspaces` (14 failed, 19 passed) | `git diff --quiet` exit 0 |
| M13 | C2(b) | `_demand_lookup.py:resolve_categories_for_entries` (def.) — the case-insensitive fallback removed | `test_c2b_a_case_variant_category_resolves_and_deletes`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M14 | C2(c) | `_demand_lookup.py:resolve_categories_for_entries` (def.) — `len(...) == 1` → non-empty | `test_c2c_an_ambiguous_case_insensitive_match_resolves_to_nothing` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M15 | C2(d) | `process_stock_demand_deleted.py` (def.) — `continue` → `break` at the first unresolved category | `test_c2d_an_unknown_category_does_not_stop_the_other_entries`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[3]`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (4 failed, 29 passed) | `git diff --quiet` exit 0 |
| M16 | C2(e) | `stock_demand_deleted_request.py` (def.) — signature computed from the raw dict, unnormalized | `test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing`, `test_c2e_properties_are_matched_on_the_normalized_signature`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (3 failed, 30 passed) | `git diff --quiet` exit 0 |
| M17 | C2(f), C5(e)-second-mutant | `_demand_lookup.py:discover_live_rows_by_identity` (def.) — the `workspace_id` filter dropped | `test_c2f_an_identity_that_exists_only_in_a_foreign_workspace_is_not_found` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M18 | C2(g), C3(e), C4(a), C4(b) | `_demand_lookup.py:discover_live_rows_by_identity` (def.) — `is_deleted = false` dropped | `test_c2g_an_already_deleted_row_is_not_found`, `test_c3e_a_later_demand_for_the_same_identity_creates_a_fresh_row`, `test_c4a_a_replay_is_not_found_and_writes_nothing`, `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record` (4 failed, 29 passed) | `git diff --quiet` exit 0 |
| M19 | C2(h) | `process_stock_demand_deleted.py` (def.) — a row is INSERTed on the not-found branch (find-or-create) | `test_c2f_an_identity_that_exists_only_in_a_foreign_workspace_is_not_found`, `test_c2g_an_already_deleted_row_is_not_found`, `test_c2h_an_identity_that_was_never_created_creates_nothing`, `test_c2h_emits_no_created_event`, `test_c4a_a_replay_is_not_found_and_writes_nothing`, `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c5d_the_find_step_is_set_based_for_all_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[3]`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (10 failed, 23 passed) | `git diff --quiet` exit 0 |
| M20 | C3(a) | `_delete_stock_report_item_cascade.py` (def.) — only active assignments removed | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3d_the_coalesced_event_list_is_exactly_these_events` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M21 | C3(a) | `process_stock_demand_deleted.py` (call site) — `actor_user_id` stamped with a real user | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M22 | C3(b) | `_delete_stock_report_item_cascade.py` (def.) — the tasks soft-deleted inside the cascade | `test_c3b_tasks_task_steps_and_items_are_never_touched` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M23 | C3(c) | `_delete_stock_report_item_cascade.py` (def.) — the gap close skipped (leave the gap) | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3b_tasks_task_steps_and_items_are_never_touched`, `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c5e_the_consistency_check_stays_empty_in_both_workspaces` (7 failed, 26 passed) | `git diff --quiet` exit 0 |
| M24 | C3(c) | `_delete_stock_report_item_cascade.py` (call site) — `removed_order - 1` (renumber the deleted row) | `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M25 | C3(d), C5(b) | `_events.py:coalesce_stock_report_events` (def., the `:updated` skip condition) — `or client_id in row_deleted` dropped | `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M26 | C3(d) | `process_stock_demand_deleted.py` (call site) — `workspace_id=ctx.workspace_id` (`""`) | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3b_tasks_task_steps_and_items_are_never_touched`, `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c5e_the_consistency_check_stays_empty_in_both_workspaces`, `test_c5f_the_workspace_reset_still_clears_everything` (9 failed, 24 passed) | `git diff --quiet` exit 0 |
| M31 | C5(b) | `process_stock_demand_deleted.py` (def.) — the cascade runs for the first candidate only | `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M31b | C5(b) | `process_stock_demand_deleted.py` (def.) — the cascade loop runs in **descending** `client_id` | `test_c5b_two_rows_of_one_group_each_close_their_own_gap` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M33 | C5(b) | `process_stock_demand_deleted.py` (def.) — the class-4 and class-5 locks moved inside the loop | `test_c5b_two_rows_of_one_group_each_close_their_own_gap` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M34 | C5(c) | `process_stock_demand_deleted.py` (def.) — results sorted by outcome instead of request order | `test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M35 | C5(d) | `process_stock_demand_deleted.py` (call site) — category resolution called once per entry | `test_c5d_the_find_step_is_set_based_for_all_category_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[3]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[3]` (4 failed, 29 passed) | `git diff --quiet` exit 0 |
| M36 | C5(e) | `_remove_assignment.py` (def.) — `recompute_task_stock_flag` skipped | `test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited`, `test_c3b_tasks_task_steps_and_items_are_never_touched`, `test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`, `test_c3d_the_coalesced_event_list_is_exactly_these_events`, `test_c5b_two_rows_of_one_group_each_close_their_own_gap`, `test_c5e_the_consistency_check_stays_empty_in_both_workspaces` (6 failed, 27 passed) | `git diff --quiet` exit 0 |
| M38 | C5(f) | `reset_app.py` (def.) — the four stock-report phases moved after `delete_tasks` | `test_c5f_the_workspace_reset_still_clears_everything` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M41 | C6(a) | `process_stock_demand_deleted.py` (def.) — a `SELECT 1` issued before `set_config` | `test_c5d_the_find_step_is_set_based_for_all_category_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_category_not_found[3]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[30]`, `test_c5d_the_find_step_is_set_based_for_all_not_found[3]`, `test_c6a_the_first_statement_sets_both_limits_from_the_default` (5 failed, 28 passed) | `git diff --quiet` exit 0 |
| M42 | C6(b) | `process_stock_demand_deleted.py` (def.) — the deadline check disabled | `test_c6b_the_deadline_is_checked_before_the_commit` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M43 | C7(a) | `location_tracker_webhooks.py` (def., third route) — `dict(request.headers)` dropped | `test_c7a_stock_demand_deleted_route_forwards_raw_bytes_and_headers` (1 failed, 6 passed) | `git diff --quiet` exit 0 |
| M44a | C7(b) | `process_stock_demand_deleted.py` (def.) — `properties` echoed normalized | `test_c7b_every_result_echoes_the_entry_byte_for_byte` (1 failed, 32 passed) | `git diff --quiet` exit 0 |
| M44b | C7(b) | `process_stock_demand_deleted.py` (def.) — `itemCategory` echoed as the normalized key | `test_c1i_an_unknown_quantity_requested_key_is_ignored`, `test_c7b_every_result_echoes_the_entry_byte_for_byte` (2 failed, 31 passed) | `git diff --quiet` exit 0 |
| M45 | 14 C1(a) | `api.md` — one route row deleted | `test_c1a_api_md_carries_every_route_with_its_roles` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M46 | 14 C1(b) | the handoff — `stock_task_assignment:state-changed` renamed away | `test_c1b_every_event_name_the_code_builds_is_in_the_handoff`, `test_c1b_the_handoff_names_no_event_no_site_builds` (2 failed, 11 passed) | `git diff --quiet` exit 0 |
| M47 | 14 C1(b) | `_events.py` (def.) — a site renamed so the code builds `stock_report_item:refreshed` | `test_c1b_every_event_name_the_code_builds_is_in_the_handoff` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M48 | 14 C1(b) | the handoff — `stock_report_item:archived` added to the event table, no site builds it | `test_c1b_the_handoff_names_no_event_no_site_builds` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M49a | 14 C1(c) | `api.md` — `StockDemandDeadlineExceeded` renamed away | `test_c1c_every_error_class_and_identity_appears[api.md]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M49b | 14 C1(c) | the handoff — `STOCK_REPORT_TARGET_OUT_OF_RANGE` renamed away | `test_c1c_every_error_class_and_identity_appears[handoff]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M50 | 14 C1(d) | `states.md` — `resolved_early` renamed away | `test_c1d_every_assignment_state_appears[states.md]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M51 | 14 C1(d) | the handoff — `resolved_early` renamed away | `test_c1d_every_assignment_state_appears[handoff]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M52 | 14 C2(a) | the handoff — `priority`'s nullability claim flipped to `no` | `test_c2a_the_handoff_nullability_matches_the_shipped_serializer[serialize_stock_report_item]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M53 | 14 C2(a) | the handoff — `credited_history_record_id`'s "Null when" cell emptied | `test_c2a_the_handoff_nullability_matches_the_shipped_serializer[serialize_stock_task_assignment]` (1 failed, 12 passed) | `git diff --quiet` exit 0 |
| M30 | C5(a) | `process_stock_demand_deleted.py` (def.) — rows (class 4) locked before tasks (class 3) | `test_c5a_the_webhook_waits_on_the_task_before_it_takes_the_row` (1 failed, 1 passed) | `git diff --quiet` exit 0 |
| M39 | C5(g) | `apply_stock_demand.py` (def.) — `sorted(...)` dropped from `absent_identities` | **none — see the finding** (2 passed) | `git diff --quiet` exit 0 |
| M40 | C5(g) | `apply_stock_demand.py` (def.) — `.order_by(client_id)` dropped from the locking `SELECT` | **none — see the finding** (2 passed) | `git diff --quiet` exit 0 |
| M39-b | C5(g) | `apply_stock_demand.py` (def.) — `sorted(...)` dropped from `absent_identities` | **none — see the finding** (2 passed; **40 identities**, run twice) | production restored; the tree-wide check saw my own in-flight fixture edit, since reverted |
| M40-b | C5(g) | `apply_stock_demand.py` (def.) — `.order_by(client_id)` dropped from the locking `SELECT` | **none — see the finding** (2 passed; **40 identities**, run twice) | production restored; the tree-wide check saw my own in-flight fixture edit, since reverted |

**Two rows of the table need their `reverted` cell read carefully, and I would rather say it than
have it found.** The harness's revert check is `git diff --quiet` over the **whole** tree. On
**M8-r** and on the two **N=40** re-runs (M39-b, M40-b) the tree also carried work of my own that
was in flight — the plan Review logs in one case, the widened fixture in the other — so the
check reported dirty although the mutated production file had been byte-restored. The
authoritative proof is the one taken after every probe: **`git diff --quiet -- app/` exit 0**, i.e.
`app/` is byte-identical to `fcf2fb8`, and `git diff --name-only -- app/` prints nothing.

**Self-chosen probe, declared.** **M31b** is not in any plan cell. C5(b)'s replacement mutant
(i-r) as written ("cascade the first candidate only") reddens the row, but it reddens it by leaving
the second row alive — it does not isolate *"each cascade closes its own gap against the positions
the previous one left"*. Running the loop in **descending** `client_id` does: both rows are deleted,
both gaps close, and only the retained order of C comes out wrong. It reddens `test_c5b` alone.
Offered as a sharper replacement for cell (i-r); the cell's own mutant was run and is recorded.

**`_events.py` — the declared probe exception, and it is clean.** Two mutations were planted there
(M25, the coalescer's `:deleted` clause, serving 13A C3(d) and C5(b); and M47, a renamed
`event_name=` site serving plan 14 C1(b)). Both were reverted in the same act and
**`git diff --quiet -- app/beyo_manager/services/commands/stock_report/_events.py` exits 0**; the
file's content is identical to `fcf2fb8`.

## 7. Perimeter declaration

**Files this session changed and left changed (code):**

| File | New / edited |
|---|---|
| `app/beyo_manager/domain/stock_report/enums.py` | edited — `StockDemandDeletedOutcomeEnum` only |
| `app/beyo_manager/services/commands/stock_report/stock_demand_entries.py` | edited — `DemandDeleteEntry`, `DemandDeleteOutcome` |
| `app/beyo_manager/services/commands/stock_report/stock_demand_deleted_request.py` | **new** |
| `app/beyo_manager/services/commands/stock_report/process_stock_demand_deleted.py` | **new** |
| `app/beyo_manager/routers/api_v1/location_tracker_webhooks.py` | edited — the third route |
| `app/tests/unit/services/commands/stock_report/test_stock_demand_deleted_request.py` | **new** |
| `app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py` | **new** |
| `app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted_locks.py` | **new** (C5(g)'s declared home) |
| `app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py` | edited — two tests appended |
| `app/tests/unit/docs/test_stock_report_docs.py` | **new** |

**Documents:** `docs/domains/stock_report/api.md` (new), `docs/domains/stock_report/states.md`
(new), `…/handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` (new),
`…/handoffs/to_frontend/archived/HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` (**moved**,
content unchanged), `plans/plan_13A.md` §9 and `plans/plan_14.md` Review log (append-only), and
this file.

**Tool-recorded state:** one batched `archgraph_apply_changes` — **3 nodes, 7 edges**, revision
`595a4813…` → `554701ca…`. Nodes `endpoint-stock-demand-deleted-webhook`,
`command-process-stock-demand-deleted`, `test-stock-report-contract-docs-guard`; edges the route →
command call, the command → cascade / locks calls, three `writes_to` table edges, and the guard →
board-endpoints `verifies` edge. Nothing promoted, rejected or edited. No symbol was deleted or
moved, so there is no symbol-level drift to report.

**Files a mutation probe touched and reverted (listed separately, per the executor protocol):**
`process_stock_demand_deleted.py`, `stock_demand_deleted_request.py`, `_demand_lookup.py`,
`_delete_stock_report_item_cascade.py`, **`_events.py`** (the plan's declared exception),
`_remove_assignment.py`, `apply_stock_demand.py`, `reset_app.py`,
`routers/api_v1/location_tracker_webhooks.py`, `docs/domains/stock_report/api.md`,
`docs/domains/stock_report/states.md`, and the new frontend handoff. Every one restored; proof
above.

**Not changed, and the perimeter check can assert it:** nothing under `app/migrations/`,
`bm/models/`, `bm/services/commands/reset/` (probe only), `_delete_stock_report_item_cascade.py`
(probe only), `_move_assignment.py`, `apply_stock_demand.py` (probe only), and
**`stock_demand_request.py` — not touched at all, by any probe.**

**The master plan tracker was NOT written by this session.** §3A reserves §4 and §4A rows to the
orchestrator ("Only the orchestrator writes tracker rows, from the handoffs it consumes"), and the
prompt's stop conditions do not list the tracker. Phases 13A and 14 are ready to move
`PENDING → IMPLEMENTED`, and batch D2's §4A row needs creating.

## 8. Evidence records

**L4 — the one authoritative stamp of this cycle.** Hypothesis: the batch broke nothing in the
suite. Scope L4 (mandatory cycle close). Command:
`BEYO_TEST_SLOT=d2i PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q` from `app/`. Tree `fcf2fb8`,
`git status --porcelain` empty at the time of the run.
**Result: 23 failed / 3798 passed / 1 skipped in 74 s.**

- observed-not-in-baseline: **∅**
- baseline-not-observed: **∅**

against the 23 checked-in ids at `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`
(the published 21 plus the two slot-sensitive `test_database_isolation` ids). Pass delta
**3742 → 3798 = +56**, which reconciles exactly: 33 integration + 6 unit parse + 2 locks +
2 router + 13 docs = 56 added, 0 removed.

**L1/L2 during implementation:** each new file whole, never `-k`; `pytest tests/unit/docs/`
50 → 63 before and after task 4 (§9 rule 11).

**Lint:** `ruff check beyo_manager tests` reports **131 findings on this tree and 131 on the tree
with every change stashed** — identical, all pre-existing. A targeted run over only this batch's
ten files is clean.

## 9. Judgment calls

1. **Step 4.8 names the priority groups by subquery** rather than reading the candidates'
   priorities first. `discover_live_rows_by_identity` returns ids only; an extra unlocked `SELECT`
   would have added a sixth statement to C5(d)'s *all `not_found`* shape. The group predicate now
   lives inside the class-4 statement, which is also what makes C5(b)'s one-statement-per-class
   clause true for any number of candidates.
2. **The group seeding runs through the shipped phase-12 commands** — `set_stock_report_item_priority`
   to put each row in the group, then `set_stock_report_item_priority_order` to place it — and the
   fixture asserts the arrangement disagrees with ascending `client_id` before the act under test.
   Plan 13's sibling used raw SQL; §6's procedure asked for the commands.
3. **C2(f)'s foreign row carries W's own `item_category_id`.** With its own category the identity
   tuple differs and *no* tenancy mutation could ever be observed — the entry would answer
   `not_found` for the wrong reason. Seeded as a genuine cross-workspace reference (L-16); M17
   reddens this row and nothing else. The row owns its own teardown, because the shared purge
   cannot delete W's categories while a W′ row references one.
4. **Goal records are read by `type`** (`quantity_requested_change`): the phase-12 seeding leaves
   `priority_change` and `priority_order_change` records on the same row.
5. **C6(b)'s clock** is a two-value iterator on `process_stock_demand_deleted.time`, so the deadline
   is computed from the first value and the check sees the second — the module-level `time` import
   exists for exactly this, as `apply_stock_demand`'s does.

## 10. What the coordinator must fold upstream

1. The five plan-cell corrections F-1 … F-5 (13A) and F-6, F-7 (references).
2. The tracker rows (§7 above).
3. **Nothing is owed to Scanner** — the v2 Scanner file already carries §4A and was not touched.
4. The frontend is owed the new handoff's §0.1: the one shape that changed under them is
   `properties`, list-valued, not a bare string.
