---
plan: batch A (1, 2, 3)
role: review
round: batch_A-rereview-1
state: CHANGES_REQUESTED
date: 2026-09-20
actor: Claude Opus 5 (plan-reviewer)
tree: 983d774
---

# Batch A re-review 1 — after fix round 1

**Tree identity.** Session HEAD is `056287e`; `git status --porcelain` empty at entry and at close.
`git diff --name-status 983d774..056287e -- app/` is **empty** — the orchestrator's docs commit
touches no source or test — so the L4 stamp on `983d774` (**21 failed / 3265 passed / 2 skipped**,
failure IDs identical to the 21-ID baseline in both directions) is tree-valid for this review and is
**consumed by citation, not re-run** (charter test-evidence section; the prompt also instructs it).

**Perimeter (verified, not reconstructed).** `git diff --name-status 0d5d31d..983d774 -- app/` is 17
paths: 8 production, 9 test, of which exactly two are deletions
(`tests/unit/domain/stock_report/test_settings.py`, `tests/unit/domain/stock_report/__init__.py`).
All inside the batch A perimeter. **No escape.** The three plan files received Review-log entries
only; no criteria table, task list or §4 list was edited (verified by diffing those sections).

**Review history.** Review 1 (`0d5d31d`) returned CHANGES_REQUESTED at 125 PASS / 30 FAIL /
15 NOT_VERIFIED of 170, 2 blocking + 14 should-fix. One grouped fix round ran. This re-review is
delta-scoped to the 45 failed/unverified rows, the six production corrections, the registry
restoration, the declared mutation gap, and the rows whose foundation moved.

---

## 1. Verdict

**CHANGES_REQUESTED** — 1 blocking, 2 should-fix, 7 notes.

This is a narrow verdict on a strong round. **43 of the 45 re-verdicted rows now pass, and every one
of the six production corrections is confirmed in behaviour, not just in diff.** The mutation gap
the fix handoff declared honestly is now closed for the whole re-verdict set: I ran **54 distinct
mutations** and every row I passed is armed. Two rows still fail, and one of them is a *new*
regression this round introduced.

| Phase | Rows | PASS | FAIL | NOT_VERIFIED |
|---|---|---|---|---|
| 1 | 53 | 53 | 0 | 0 |
| 2 | 75 | 75 | 0 | 0 |
| 3 | 42 | 40 | 2 | 0 |
| **Total** | **170** | **168** | **2** | **0** |

**Delta against review 1:** PASS 125 → **168** (+43) · FAIL 30 → **2** (−28) · NOT_VERIFIED
15 → **0** (−15).

The two survivors are plan 3 **C1(k)** (workspace isolation, blocking — see F-R1) and plan 3
**C3(d)** (the task repair record's `true → false` values, should-fix — F-R2).

---

## 2. ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — should the consistency check still filter task assignments by workspace?

**Question.** Does `expected_task_flag` keep the registry's `(session, task_id)` shape, which drops
the workspace filter — or does §6.5 change back to `(session, workspace_id, task_id)`?

**Story.** Two workshops share the installation. A job in workshop B is written against a stock row
that belongs to workshop A — a mix-up any future booking screen could make in one line of code.
Today's check asks "does any assignment anywhere mention this job?", so workshop A's board lights up
a job it does not own, and pressing *Repair* stamps that job as A's stock work. The old code asked
"does any assignment **in this workshop**…?" and would simply have ignored it. Nothing does this
today; the next phase is the one that starts writing those assignments.

**Branches.** Restore the workspace filter — the check can never read another workshop's rows, at the
cost of one extra argument in the registry. · Keep the registry's shape — one less argument, and the
boundary depends on no future code ever writing a cross-workshop row.

**Recommendation.** Restore the filter and amend §6.5, because a tenancy boundary that holds only
while every other file stays correct is the kind that fails silently and late.

**On silence.** The gate holds: batch A stays CHANGES_REQUESTED and no second fix round starts.

**Trace.** master plan §6.5 (`consistency.py` row); plan 3 C1(k); finding F-R1.

---

## 3. Re-verdict table (45 rows)

Verdict vocabulary is review 1's, unchanged. "mutation" = the row's own named mutation, run by me at
the scope stated, unless marked cited.

### Plan 1 — 13 rows (13 PASS)

| Row | Verdict | Test id | Mutation run → what reddened |
|---|---|---|---|
| C1(c) | PASS | `test_terminal_assignment_does_not_block_new_active_assignment` | **DB-level**: `DROP INDEX uix_stock_task_assignments_item_active` → the duplicate flushes; the row's `pytest.raises` bites. Fixture now isolates: same `item_id`, **different** `task_id`, so only the item index is violated (the two unique indexes are on `(workspace_id, item_id)` and `(workspace_id, task_id)` — `stock_report_item_id` is in neither, so the disjunction of review 1 is gone) |
| C1(d) | PASS | `test_terminal_states_do_not_block_new_active_assignment[RESOLVED]` | **DB-level**: recreate both partial indexes without `state IN (…)` → the second flush now raises. Bites |
| C1(e) | PASS | `…[FAILED]` | same mutation, same flip |
| C1(f) | PASS | `test_soft_deleted_active_assignment_does_not_block_new_active_assignment` | **DB-level**: recreate without `is_deleted = false` → now blocked. Bites |
| C1(g) | PASS | `test_active_assignments_on_same_task_and_different_items_hit_task_index` | **DB-level**: `DROP INDEX …_task_active` → flushes. Isolated: same `task_id`, different `item_id` |
| C1(h) | PASS | `test_same_identity_is_reusable_across_workspaces` | **DB-level**: recreate the identity index without `workspace_id` → **no flip. EQUIVALENT MUTANT** — `item_category_id` is FK-bound to one workspace, so `(item_category_id, properties_signature)` already separates workspaces. Recorded as equivalent (doctrine rule 2); no test is demanded for it. Lesson L-10 |
| C1(j) | PASS | `test_terminal_states_do_not_block_new_active_assignment[RESOLVED_EARLY]` | **DB-level**: add `resolved_early` to both predicates' state list → now blocked. Bites. C1(i) and C1(j) share this one fixture and one mutation reddens both |
| C2(a) | PASS | `test_stock_report_migration_matches_runtime_metadata` | Instrument rebuilt as the row writes it: real `compare_metadata(MigrationContext, Base.metadata)` over `run_sync` on the migrated worker DB, filtered to the five owned tables. **The row's named mutation ("remove one CHECK from the model") is INERT — 33 passed**: Alembic does not diff CHECK constraints. Calibrated with "remove an index from the model" → **RED**. The guard is real and its reach is columns/types/indexes; the CHECKs are covered at DB level by C2(b)–(g). Lesson L-11 |
| C3(a) | PASS | `test_reset_removes_stock_report_graph_before_task_deletion_and_keeps_other_workspace` | Move the four stock phases after `delete_tasks` → RED. Also probed the row's new clause: comment out `delete_workspace` → RED. All four clauses now asserted (own counts 0, foreign counts 1, workspace row gone, `["workspace:reset"]` only), `capture_dispatch` used, `finally` purge present (residual in N-R4) |
| C5(a) | PASS | `test_normalization_preserves_keys_and_is_idempotent` | lower-case keys → RED ×3. Both clauses now asserted (keys preserved **and** signature differs) |
| C5(b) | PASS | `test_normalization_preserves_string_property_key_spelling` | strip keys → RED ×2 |
| C5(c) | PASS | `test_normalization_is_idempotent_for_all_golden_vectors` | `str` wraps twice → RED ×6, **but not on this test** — wrapping twice is still idempotent, so the row's named mutation cannot reach its own guard. Idempotence over 15 payloads (was 1); every normalization branch represented. Enumeration is 7 payloads short of "every raw payload of C4 and C5" → note N-R2, deliberately not blocking |
| C5(d) | PASS | `test_signature_uses_normalized_golden_vectors[0..5]` | Six hand-written golden vectors (was 1). "drop `sorted()`" → **RED on 4 of 7 `PYTHONHASHSEED` values (2, 7, 11, 42), green on 0, 1, 3** — the intermediate is a `set`, so a two-element fixture's iteration order sometimes coincides with sorted order. The assertion itself is exact and is the strongest form available; recorded as a condition-varied measurement, not a defect |

### Plan 2 — 11 rows (11 PASS)

| Row | Verdict | Test id | Mutation run → what reddened |
|---|---|---|---|
| C2(c) | PASS | `test_build_item_property_bag_drops_blank_values` | plan declares no mutation. `{"   ": "x"}` → `{"quantity": "1"}` asserted exactly |
| C2(h) | PASS | `test_build_item_property_bag_scanner_table[properties13]` | "trust stored" run properly (drop `wood_group` from `EXCLUDED_ITEM_PROPERTY_KEYS` **and** skip re-derivation when present) → RED on this row. The bag now carries Scanner's `"Light"` |
| C3(d) | PASS | `test_matcher_accepts_any_of_multiple_criterion_values_and_rejects_a_miss` | **Review 1's probe P1 shape re-run** (`any(token in accepted …)` → `all(value in tokens …)`) → **RED on exactly this test**. The survivor of review 1 now bites. I also ran the other "require all" direction (`all(token in accepted …)`) → RED on `test_wildcard_and_token_matching_table` and `[H9]`. Fixture deviates from the row (`wood_group` list, not `{"quantity": ["4","8"]}`) — same code path, undeclared: note N-R5 |
| C4(a) | PASS | `[H1]` + `test_scanner_tables_and_drawer_ascii_rules` | plan declares no mutation. Bag value `"Dark"` for Walnut is not asserted directly; it is now **entailed** by two asserted facts — `WOOD_GROUPS` equals its literal (C7(a), mutated red twice) and `wood_group_of_token` returns the declared name verbatim (asserted for `"Teak"` and `"Light"` at bag level, lower-case mutant RED) |
| C4(b) | PASS | `[H3-teak]`, `[H3-light]`, `[H7]` | last-token instead of first → RED ×3 |
| C4(d) | PASS | `[H10]` + bag rows | case-sensitive member lookup → RED ×17 incl. `[properties9]`, `[properties13]`, `[H10]` |
| C5(d) | PASS | `test_wildcard_and_token_matching_table` | wildcard passes on a derived key with no group → RED |
| C5(e) | PASS | same | plan declares no mutation. `{"drawers_range": ["3-5"]}` with no `drawers_qty` → `MISSING_ON_ITEM`, asserted exactly |
| C5(n) | PASS | same (final assert) | plan declares no mutation. `evaluate_stock_criteria(item(None), {}) == []` asserted. Reachability established by the green run; note N-R6 on the sequential-assert shape |
| C6(j) | PASS | `test_scanner_hand_walk_golden_cases[H9-oval]` | H9's first item (`{"wood_type": "Oak", "shape": "Oval"}`) now ships beside the `Oval/Rectangular` variant. Reddened by the C4(d) and C3(d) mutants |
| C7(a) | PASS | `test_scanner_tables_and_drawer_ascii_rules` | "any edit": removed `"Elm"` from Light → RED ×3; removed `"Cherry"` from Teak → RED. The whole literal is now asserted, not just the Dark list |

### Plan 3 — 21 rows (19 PASS, 2 FAIL)

| Row | Verdict | Test id | Mutation run → what reddened |
|---|---|---|---|
| C1(a) | PASS | `test_counter_and_signature_divergences_are_reported` | drop the counter kind → RED ×10. Full-list equality with **both** exact divergence dicts (was a kind-set) |
| C1(d) | PASS | `test_task_flag_divergence_is_reported_when_assignment_is_missing` | drop the task_flag kind → RED ×7. Exact dict, full-list equality |
| C1(e) | PASS | `test_counter_and_signature_divergences_are_reported` | the row's discriminating mutation (**"scan only tasks with the flag set"**) → RED ×4. stored `"false"` / expected `"true"` now asserted |
| C1(f) | PASS | `test_order_density_reports_only_the_row_that_needs_renumbering` | drop the density kind → RED ×3. Exact dict **and** the "rows 1 and 2 not reported" clause, via equality on the filtered list |
| C1(g) | PASS | `test_null_priority_order_appends_after_the_group_maximum` | drop the nullness kind → RED ×4. Dense `[1, 2]` fixture restored **and** the sparse `[1, 7]` neighbour added |
| C1(h) | PASS | `test_null_priority_order_is_reported_when_priority_is_missing` | same mutation, RED. Exact dict, full-list equality |
| C1(i) | PASS | `test_goal_signature_and_density_divergences_are_reported` | drop the goal kind → RED ×2. Exact dict |
| C1(j) | PASS | same | drop the signature kind → RED ×3. Exact dict incl. `stored` |
| **C1(k)** | **FAIL** | `test_consistency_does_not_report_foreign_workspace_drift` | **Measured: 4 of the 5 workspace filters survive the row's own named mutation.** See F-R1 |
| C2(a) | PASS | `test_consistency_service_returns_workspace_timestamp_and_divergences` | make the check write (`UPDATE tasks SET updated_at`) → RED ×3. Rebuilt on the owner's restatement: every row of the four MC-9 tables plus `stock_report_repair_records` in W, `SELECT *` before and after, compared for equality |
| C3(a) | PASS | `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` | skip the counter repair → RED ×6. The record's full 8-tuple is now asserted as a set equality (target_kind, target_client_id, field, stored, recomputed, trigger, created_by_id, created_at) |
| C3(b) | PASS | `test_manual_repair_fixes_each_active_counter_and_records_exact_fields[IN_PROGRESS]` | same mutation, RED. Exact record + check `[]` |
| C3(c) | PASS | `…[AWAITING]` | same mutation, RED |
| **C3(d)** | **FAIL** | `test_manual_repair_clears_false_positive_task_flag` | **Measured**: hard-coding the task record's `recomputed_value` to `"true"` leaves the whole file green (17 passed). See F-R2. The `target_kind: task` half *is* armed (mislabelling it → RED) |
| C3(f) | PASS | `test_repair_records_one_net_change_per_priority_order_field` | "renumber by client_id instead of current order" → **RED** on this test and on `test_repair_applies_nullness_before_priority_density`, reproduced 11 of 12 runs at two scopes. `target_kind: group` is now asserted. Row uses C6(a)'s fixture, not its own (note N-R7) |
| C3(g) | PASS | same | same mutation. `("stock_report_item", missing, None, "3")` — SQL NULL, not `"None"` (C6(f)) |
| C3(h) | PASS | `test_manual_repair_clears_priority_nullness_and_records_one_item_change` | drop the nullness kind → RED. **F-B1's probe P10 scenario, now green**: order set NULL, exactly one `stock_report_item` record stored `"1"` / recomputed NULL, `repaired` exact, post-repair check `[]` and no raise |
| C6(a) | PASS | `test_repair_records_one_net_change_per_priority_order_field` | force the appended row's `target_kind` to `group` → RED. Both target kinds now asserted (`group` for the row that moved 3 → 2, `stock_report_item` for the appended one), one record per `(row, field)` |
| C6(d) | PASS | `test_density_repair_stamps_only_the_renumbered_row` | drop the density kind → RED. The renumbered row's `updated_at`/`updated_by_id` **and** the unchanged row's `(None, None)` both asserted |
| C6(e) | PASS | `test_repair_dispatches_only_changed_stock_report_rows` | "emit for goal/task repairs" (adding their client_ids to `changed_row_ids`) → **no flip, EQUIVALENT**: the dispatch query is `select(StockReportItem)`, so a task or history id can never produce an event — the "nothing for G or T" clause is structural. The other half **is** armed: dropping `priority_order` from the event `extra` → RED. Fixture carries all three drifts the row names |
| C7(a) | PASS | `test_assert_stock_report_clean_rejects_a_stray_repair_record` | "split the helper so the record half can be skipped" → RED. The helper's own charter-rule-15 probe now exists |

### Rows pulled in under §3A's widening clause (all re-confirmed PASS)

Named, with why. None changed verdict.

- **`criteria_normalization.py` moved (F-B2's filter):** plan 1 **C4(c), C4(d), C4(e), C4(f), C4(g)** —
  every list/blank branch the filter could have broken. The blank-passthrough row C4(g)
  (`{"k": ["", "  "]}` → unchanged) is the one at risk and is still exact; removing the filter reddens
  `test_normalization_value_table[raw5]` and `test_signature_uses_normalized_golden_vectors[raw1]`,
  not C4(g). Plan 1 **C5(e)–(h)** re-confirmed by the `sort-not-understood` mutant (RED ×3).
- **`scanner_property_tables.py` moved (F-S1's casing):** plan 2 **C4(c), C5(b), C5(c), C6(a)–(q)** —
  every row that reads a derived `wood_group`. All green; the matcher tokenizes to lower case on both
  sides, so the casing change is invisible at match level, which is why no hand-walk row moved.
- **`consistency.py` moved (five signatures + F-S2):** plan 3 **C1(b), C1(c), C1(l), C2(b), C2(c)** —
  reddened by my counter-kind, goal-kind and task-flag-kind mutants, so all still armed.
- **`repair_stock_report.py` / `_task_flag.py` / `_repair_records.py` moved (F-S7, F-S8, F-B1):**
  plan 3 **C3(e), C3(i), C4(a), C5(a), C6(b), C6(c), C6(f), C7(b)**. `C5(a)`'s `count_writes == 0`
  survives the registry change and reddens under the C2(a) write mutant. `C6(b)` (no task stamps)
  reddens under the `require_update` probe. `write_repair_record`'s new `now` is asserted positively:
  three tests compare `record.created_at == ctx.now`.
- **`_locks.py` moved (F-S6):** plan 3 `test_stock_report_row_lock_is_workspace_scoped` (plan 3 §7's
  structural check) still discriminates — `_lock` is unchanged and the new helper reuses it.
- **`reset_app.py` moved (N-4 + F-S10):** plan 1 **C3(a)** only; the change is the docstring plus the
  test. Phase order unchanged and re-mutated (RED).

---

## 4. Mutation sweep

**Does `executed == declared` now hold? For the re-verdict set, yes — and only for that set.**
Every row I graded PASS above had its named mutation applied and observed, except where the table
records the mutation as **equivalent** (3 sites: P1 C1(h), P3 C6(e), and the P2 C2(h) first attempt)
or **inert by dependency limitation** (1 site: P1 C2(a)'s CHECK mutation, which Alembic cannot see).
For those I ran a calibrating mutation instead and recorded it.

For the full 94-site inventory (35 / 37 / 22): **no, and it should not.** The remaining sites belong
to the 125 rows review 1 passed whose foundation did not move — out of scope by §"Out of scope" and
re-running them would be the over-evidence violation the charter names. I state this plainly rather
than implying a closed ledger.

### Per declared site — run here

| # | Site (file · definition) | Rows served | Result |
|---|---|---|---|
| 1 | `criteria_normalization.py::normalize_stock_criteria` — lower-case keys | P1 C5(a) | RED ×3 |
| 2 | same — strip keys | P1 C5(b) | RED ×2 |
| 3 | same — `str` wraps twice | P1 C5(c) | RED ×6, **not** on C5(c)'s own guard |
| 4 | same — drop `sorted()` | P1 C4(e), C5(d) | RED on 4/7 hash seeds |
| 5 | same — remove the blank filter | P1 C4 candidate row, F-B2 | RED ×2 |
| 6 | same — sort not-understood lists | P1 C5(g) *(also cited: fix handoff §5)* | RED ×3 |
| 7 | DB · `uix_stock_task_assignments_item_active` — drop | P1 C1(c) | FLIP |
| 8 | DB · `uix_stock_task_assignments_task_active` — drop | P1 C1(g) | FLIP |
| 9 | DB · both predicates — drop `state IN (…)` | P1 C1(d), C1(e) | FLIP ×2 |
| 10 | DB · both predicates — drop `is_deleted = false` | P1 C1(f) | FLIP |
| 11 | DB · both predicates — add `resolved_early` | P1 C1(i), C1(j) | FLIP |
| 12 | DB · `uix_stock_report_items_identity_active` — drop `workspace_id` | P1 C1(h) | **no flip — EQUIVALENT** |
| 13 | `stock_report_item.py` — remove a CHECK | P1 C2(a) | **green — INERT** (Alembic does not diff CHECKs) |
| 14 | `stock_report_item.py` — remove an index *(calibration for 13)* | P1 C2(a) | RED ×2 |
| 15 | `reset_app.py` — stock phases after `delete_tasks` | P1 C3(a) | RED |
| 16 | `reset_app.py` — skip `delete_workspace` *(the row's new clause)* | P1 C3(a) | RED |
| 17 | `criteria_matcher.py` — `all(value in tokens …)` **(probe P1 shape)** | P2 C3(d) | RED on its own test |
| 18 | `criteria_matcher.py` — `all(token in accepted …)` | P2 C3(d) | RED ×2 |
| 19 | `criteria_matcher.py` + `scanner_property_tables.py` — trust the stored group | P2 C2(h) | RED on `[properties13]` |
| 20 | `criteria_matcher.py` — skip re-derivation only | P2 C2(h) | **no flip — EQUIVALENT** (the key is excluded first) |
| 21 | `scanner_property_tables.py::EXCLUDED_ITEM_PROPERTY_KEYS` — drop `wood_group` | P2 C2(h) | RED |
| 22 | `criteria_matcher.py` — last token, not first | P2 C4(b) | RED ×3 |
| 23 | `scanner_property_tables.py::wood_group_of_token` — case-sensitive | P2 C4(d) | RED ×17 |
| 24 | `criteria_matcher.py` — wildcard passes on a null derived key | P2 C5(d) | RED ×2 |
| 25 | `scanner_property_tables.py::wood_group_of_token` — `group.lower()` | F-S1, P2 C2(h)/C4(a)/(b)/(d) | RED ×2 |
| 26 | `WOOD_GROUPS` — drop `"Elm"` from Light | P2 C7(a) | RED ×3 |
| 27 | `WOOD_GROUPS` — drop `"Cherry"` from Teak | P2 C7(a) | RED |
| 28 | `consistency.py` — drop the counter kinds | P3 C1(a), C1(b), C1(c) | RED ×10 |
| 29 | `consistency.py` — drop the signature kind | P3 C1(j) | RED ×3 |
| 30 | `consistency.py` — drop the nullness kind | P3 C1(g), C1(h) | RED ×4 |
| 31 | `consistency.py` — drop the order_density kind | P3 C1(f) | RED ×3 |
| 32 | `consistency.py` — drop the goal_total kind | P3 C1(i) | RED ×2 |
| 33 | `consistency.py` — drop the task_flag kind | P3 C1(d), C1(e) | RED ×7 |
| 34 | `consistency.py` — scan only flagged tasks | P3 C1(e) | RED ×4 |
| 35 | `consistency.py` — `len(assigned)+1` for the nullness expected | F-S2, P3 C1(g) | RED — **only** on the sparse neighbour |
| 36 | `consistency.py` — drop the ws filter, `stock_report_items` select | P3 C1(k) | RED |
| 37 | `consistency.py` — drop the ws filter, `stock_report_history_records` select | P3 C1(k) | **GREEN — unguarded** |
| 38 | `consistency.py` — drop the ws filter, `tasks` select | P3 C1(k) | **GREEN — unguarded** |
| 39 | `consistency.py` — drop the ws filter, `_recompute_row_counters_for_workspace` | P3 C1(k) | **GREEN — unguarded** |
| 40 | `consistency.py` — drop the ws filter, `_recompute_goal_totals_for_workspace` | P3 C1(k) | **GREEN — unguarded** |
| 41 | `consistency.py` — the check writes a row | P3 C2(a) | RED ×3 |
| 42 | `repair_stock_report.py` — skip the counter repair | P3 C3(a), C3(b), C3(c) | RED ×6 |
| 43 | `repair_stock_report.py::_TARGETS` — mislabel the task record's kind | P3 C3(a), C3(d) | RED |
| 44 | `repair_stock_report.py` — hard-code the task record's `recomputed_value` | P3 C3(d) | **GREEN — unguarded** |
| 45 | `repair_stock_report.py` — renumber by `client_id` | P3 C3(f), C6(a) | RED (11/12 runs) |
| 46 | `repair_stock_report.py` — appended row gets `target_kind: group` | P3 C6(a) | RED |
| 47 | `repair_stock_report.py` — add task/history ids to `changed_row_ids` | P3 C6(e) | **no flip — EQUIVALENT** |
| 48 | `repair_stock_report.py` — drop `priority_order` from the event payload | P3 C6(e) | RED |
| 49 | `tests/helpers/stock_report.py::assert_stock_report_clean` — drop the record half | P3 C7(a) | RED |
| 50 | `repair_stock_report.py:275` — counter UPDATE matches no row | F-S7 | `RuntimeError: counter repair affected an unexpected number of rows` |
| 51 | `repair_stock_report.py:256` — goal-total UPDATE matches no row | F-S7 | `RuntimeError: goal-total repair affected an unexpected number of rows` |
| 52 | `repair_stock_report.py:74` — nullness UPDATE matches no row | F-S7 | guard fires, RED |
| 53 | `repair_stock_report.py:130` — density UPDATE matches no row | F-S7 | guard fires, RED ×3 |
| 54 | `_task_flag.py:14` — write the flag's stored value with `require_update=True` | F-S7 | `RuntimeError: task flag update affected an unexpected number of rows` |
| 55 | `repair_stock_report.py` — remove `lock_stock_report_history_records` | F-S6 | **GREEN — not observable** by a single-session test (concurrency guard); confirmed structurally instead |

### Cited from the fix handoff §5 (same tree, consumed not re-run)

P1 C5(g), P1 C7(a), P2 C3(d), P2 C7(a)/F-S1, P3 C3(h)/F-B1, P3 C7(a), F-B2, F-S2 — 8 sites. I
independently re-ran six of these eight at a different site or mutant shape (rows 4, 5, 6, 17, 25,
27, 35 above), which is variation rather than reproduction; the two I did not re-run are P1 C7(a)
and P3 C7(a), and P3 C7(a) I replaced with the stronger helper-splitting mutant (row 49).

### Not run, and why

- The declared sites for the **125 rows review 1 passed whose foundation did not move** — out of
  scope, and re-running them is the charter's named over-evidence defect.
- **P2 C6(a)–(q)'s own mutation column** is "(the C1–C5 mutations)" — it declares no site of its own;
  it is discharged by rows 17–27, which reddened nine distinct hand-walk cases.
- **Plan 1 C4(f)** is marked "cannot isolate" by the plan itself; C4(g) is its discriminating
  neighbour and was mutated (row 5).

---

## 5. Correction-by-correction

| # | Status | Evidence |
|---|---|---|
| **F-B1** repair crashes on `priority` NULL + order set | **CONFIRMED** | `_repair_priority_orders:59-99` handles `expected is None` **before** the density renumber (`:101-161`) — ordering verified by reading *and* by `test_repair_applies_nullness_before_priority_density` asserting `(1, 2, 3)`. One `stock_report_item` record, old order as `stored_value`, NULL as `recomputed_value`. Review 1's probe P10 scenario is now `test_manual_repair_clears_priority_nullness_and_records_one_item_change`: green, and it asserts the post-repair check is `[]`, i.e. **no raise**. The `rows` query no longer filters `priority IS NOT NULL` and re-groups on `priority is not None` instead |
| **F-B2** blank list elements | **CONFIRMED** | `criteria_normalization.py:17-19` filters. `{'k': ['Teak','  ','Dark']}` → `['dark','teak']` asserted as `test_normalization_value_table[raw5]` and as golden vector `[raw1]`. **`CRITERIA_NORMALIZATION_VERSION == 1`** (`:3`) — the owner's ruling held; no bump. Removing the filter reddens both |
| **F-S1** wood-group casing | **CONFIRMED** | `wood_group_of_token:47` returns `group`. The bag now carries Scanner's declared `"Teak"` (`[properties9]`) and `"Light"` (`[properties13]`); `"Dark"` is entailed by C7(a)'s full-table assertion plus the same return statement. Re-lower-casing reddens two rows |
| **F-S2** nullness `expected` | **CONFIRMED** | `consistency.py:173` is `max(assigned_orders, default=0) + 1`. Review 1's probe P5 shape is now a shipped test: `[1, 7]` group + a null-order row reports **8**. Plan 3 C1(g) has the dense `[1, 2]` fixture **and** the sparse neighbour, and the `len+1` mutant reddens **only the sparse one** — which is precisely the discrimination the fix prompt required |
| **F-S6** history-record lock | **CONFIRMED (structural), with a residual** | `lock_stock_report_history_records` exists (`_locks.py:52`), is taken at `repair_stock_report.py:206` — **after** `lock_tasks` (:173), `lock_stock_report_items` (:182) and `lock_stock_task_assignments` (:194) — and goes through the shared `_lock`, so it is `SELECT … FOR UPDATE ORDER BY client_id` ascending with `populate_existing`. **Residual:** the lock set is taken from the **pre-lock** divergence read (`:170`), while the goal-total UPDATE at `:248` iterates the **post-lock** read (`:217`). A `goal_total` divergence that only appears in the second read — a newly-inserted assignment, or a concurrent write to the record — is updated unlocked. Same shape as the `lock_tasks` call, whose comment acknowledges it. Note N-R1; not blocking, and the correction as quoted in the fix prompt was implemented literally |
| **F-S7** `rowcount == 1` guards | **CONFIRMED** | All four repair-path statements guard (`:74`, `:130`, `:256`, `:275`), and `set_task_stock_flag` takes `require_update=True` on the repair path only (`:241-246`) while keeping the idempotent 0 elsewhere. **All five demonstrated to fire**, each with its exact `RuntimeError` — sweep rows 50–54 |
| **F-S8** §6.5 registry | **PARTIAL** | Names and shapes restored; `Divergence` TypedDict defined and used as the return type; `write_repair_record` takes `now` and sets `created_at=now` — asserted positively by three tests comparing `record.created_at == ctx.now`; the workspace-wide variants are private and separately named as the prompt allowed. **But, per the prompt's "check the call sites, not the `def` lines":** `recompute_row_counters`, `recompute_goal_total` and `recompute_task_stock_flag` have **zero callers anywhere — production or test** (`grep -rn` over `app/`). They are provisioned for phases 4/5/11 and are unexercised (note N-R3). And `expected_task_flag` implements the registry by **dropping its workspace filter** — finding F-R1 |
| **F-S9** plan 1 C5 clauses | **CONFIRMED** | Two-different-signature clauses asserted for both spellings; idempotence over 15 payloads; six golden vectors, hand-written (no snapshot trap). Enumeration shortfall in N-R2 |
| **F-S10** reset test hygiene | **PARTIAL** | `finally` purge via `purge_stock_report_workspace` added, workspace-row-gone asserted, kit's `capture_dispatch` used. **Residual:** only the *foreign* workspace is purged. The own workspace's two kit users (`usr_sm_reset-own`, `usr_sw_reset-own`) are committed and never deleted — `reset_app` leaves users global by design and the ctx passes `delete_orphan_bootstrap_users: False`. ~13 rows/run → **2 rows/run**. Note N-R4 |
| **F-S11** repair-record `target_kind` | **PARTIAL** | `group`, `stock_report_item`, `task` and `history_record` are all now asserted, and mislabelling any of them reddens. **Except C3(d)** — finding F-R2 |
| **F-S12** plan 3 C2(a) instrument | **CONFIRMED** | Owner's restatement implemented: `SELECT * … WHERE workspace_id = … ORDER BY client_id` over the five tables before and after, compared for equality. `count_writes`/`record_statements` correctly retained for C5(a) |
| **F-S13** four short enumerations | **CONFIRMED** | H9's first item added; the whole `WOOD_GROUPS` literal asserted; `quantity_in_progress`/`quantity_awaiting` repair tests added; the density-renumbered row's stamp asserted; `assert_stock_report_clean` shown to raise on a stray record. All five mutated red |
| **F-S14** orphan tests | **PARTIAL** | Eight of the nine handled correctly — `test_settings.py` (2) deleted, `test_schema_contract.py` (4) / `test_repair_record_values.py` (1) / `test_stock_report_helper.py` (1) / `test_stock_report_row_lock_is_workspace_scoped` (1) routed as candidate criteria in the plans' Review logs. **But the round added a new, unrouted orphan** — finding F-R3 |
| **N-4** reset docstring | **CONFIRMED** | The four stock phases are listed first and the list renumbered. The list skips 23 and 27 — a pre-existing off-by-one, carried forward, not introduced. Note N-R8 |
| **N-5** stray `__init__.py` | **CONFIRMED** | Deleted. `find app/tests -name __init__.py` is now **empty**, matching the repo convention |

### The two deletions — story confirmed

`tests/helpers/test_settings.py` exists and contains **no tests at all** — a single helper,
`assert_deterministic_environment`, in a file pytest collects because of its `test_*` name. With
`tests/unit/domain/stock_report/__init__.py` removed, both files resolved to the module name
`test_settings`, which is the duplicate-module collection error the handoff reports. Deleting the
orphan resolved it. I verified the rest of the story:

- **Nothing else was shadowed.** `find app/tests -name "test_*.py" | xargs -n1 basename | sort | uniq -d`
  is **empty** — no basename collides anywhere under `app/tests` today.
- **No surviving test lost coverage.** The deleted tests asserted `Settings` defaults and env aliases
  for the three stock-report settings; plan 1 §6 states in so many words that settings carry no
  criterion until phase 6, "whose instrument (i) reads the default from the class". Routed forward in
  the dispositions table.
- **Collection is correct** — the batch's 155 tests collect and pass (§8).
- The collection error was **not** silently present before: it was created by removing the
  `__init__.py` and removed again in the same round. What *is* worth recording is the latent hazard
  that caused it — note N-R9.

---

## 6. `lock_stock_report_history_records` — for master plan §6.5

Exact signature as shipped (`_locks.py:52-53`), in the form §6.5's `_locks.py` row uses:

```
lock_stock_report_history_records(session, workspace_id, client_ids) -> dict[str, StockReportHistoryRecord]
```

Like its four siblings it delegates to `_lock`, i.e. `SELECT … WHERE workspace_id = :ws AND
client_id IN (sorted(client_ids)) ORDER BY client_id FOR UPDATE` with `populate_existing`, and
returns `{}` unchanged when `client_ids` is empty. Add it to the `_locks.py` row after
`lock_stock_task_assignments`, which is where §12A's lock order places it.

---

## 7. Findings

### Blocking

**F-R1 — the consistency check lost its workspace filter on task assignments, and the row that
guards workspace isolation is measurably inert for four of five kinds.**

Two halves of one defect.

*The production half.* `expected_task_flag` was `(session, workspace_id, task_id)` with
`StockTaskAssignment.workspace_id == workspace_id` in its `WHERE`. This round implemented master plan
§6.5's registered `expected_task_flag(session, task_id) -> bool` and **deleted that predicate**
(`consistency.py:101-110`). The query now answers "does *any* assignment in the installation name
this task?". `StockTaskAssignment` carries independent FKs to `workspaces.client_id` and
`tasks.client_id` with no composite constraint tying them together, so a row whose `workspace_id` is
F and whose `task_id` belongs to W is structurally permitted. When one exists, the check reports a
`task_flag` divergence for W's task and `repair_stock_report` writes `is_stock_assignment = true` on
it — and `set_task_stock_flag`'s UPDATE is itself keyed on `Task.client_id` alone, with no workspace
predicate, so the write lands. Nothing writes such a row today; **phase 4 is the phase that starts
writing assignments.**

*The coverage half.* Plan 3 C1(k) exists for exactly this: "clean F0 plus every C1(a)–(j) drift
planted in the **foreign** workspace → check for W returns `[]`", with the named mutation "drop the
`workspace_id` filter from any kind → foreign rows leak in". `test_consistency_does_not_report_foreign_workspace_drift`
is **unchanged by this round** and still plants one foreign row carrying two kinds. I applied the
row's named mutation to each of the five workspace filters in turn (sweep rows 36–40):

| Filter | Kinds it protects | Mutation result |
|---|---|---|
| `stock_report_items` select | counter ×3, signature, nullness, order_density | **RED** |
| `stock_report_history_records` select | goal_total | **GREEN** |
| `tasks` select | task_flag | **GREEN** |
| `_recompute_row_counters_for_workspace` | counter ×3 | **GREEN** |
| `_recompute_goal_totals_for_workspace` | goal_total | **GREEN** |

So the guard that would have caught the production half cannot observe it, and four more tenancy
filters can be deleted today with a green suite.

Authority: master plan §9 rule 1 (workspace scoping); plan 3 C1(k); charter rule 15 ("measuring an
absence proves the absence; it does not prove the instrument could ever observe the presence").
**Correction:** (a) owner ruling on card 1, then either restore the predicate and amend §6.5 or
record the decision to drop it; (b) implement C1(k) as written — one foreign-planted drift per kind
— so the remaining four filters are armed.

Note in fairness to the implementer: §6.5 line 400 really does register the no-workspace signature,
and the fix prompt §2 ordered the registry to be implemented. What was missed is the same section's
last bullet — "if you conclude a registered signature is genuinely wrong, implement it **and raise an
owner card**". No card was raised. The defect is the registry's; the omission is the round's.

### Should-fix

**F-R2 — the task repair record's `true → false` values are asserted nowhere.**
Plan 3 C3(d) requires, for a flag wrongly set true, one record
`{target_kind: task, target_client_id: T, field: is_stock_assignment, stored_value: "true",
recomputed_value: "false", trigger: manual}` plus a clean post-repair check.
`test_manual_repair_clears_false_positive_task_flag` (`test_repair_stock_report.py:117-131`) asserts
the `repaired` kinds and the flag's new value, and **nothing about the record or the check**. The
opposite direction is asserted exactly by C3(e)'s test, which is what makes the gap invisible.
Measured: hard-coding `recomputed_value` to `"true"` for the `task_flag` kind leaves the whole file
green (17 passed), while the same test file catches a mislabelled `target_kind`. The cost is a wrong
audit record for the commonest task-flag repair — contained, no stock data corrupted. Authority: plan
3 C3(d); review 1 F-S11, which named this row and was only half-applied.
**Correction:** assert the record 6-tuple and `compute_stock_report_divergences(...) == []` in
`test_manual_repair_clears_false_positive_task_flag`, the way C3(a) now does.

**F-R3 — the round that removed nine orphan tests added one: a duplicate of plan 1 C2(a).**
`test_consistency_check.py:119-134` (`test_consistency_matches_migrated_worker_schema`) is new in
this delta and is **byte-for-byte the same check** as
`test_stock_report_schema.py:264-279` (`test_stock_report_migration_matches_runtime_metadata`) — same
`MigrationContext`, same `compare_metadata`, same five-table filter, same assertion. Plan 1 C2(a) is
the row; plan 3 has no such row, and plan 3's Review log routes the lock-scoping test and the
`requests/__init__.py` choice but **not this one**. Both reddened together under my index
calibration, confirming they are redundant. Authority: charter rule 16 / trace chain link 4; the fix
prompt §4's own instruction to route or delete. **Correction:** delete the plan 3 copy (plan 1 owns
the row), or route it in plan 3's Review log with the ledger entry it serves.

---

## 8. Backlog notes (not findings; nothing here blocks)

- **N-R1** — the goal-total lock set is computed from the **pre-lock** divergence read while the
  UPDATE iterates the post-lock read, so a `goal_total` divergence that first appears after the item
  and assignment locks are taken is updated unlocked. Same shape as `lock_tasks`, whose inline comment
  acknowledges it. Destination: phase 5, with the inline goal credit that F-S6 was written for.
- **N-R2** — plan 1 C5(c) says "every raw payload of C4 and C5";
  `test_normalization_is_idempotent_for_all_golden_vectors` lists 15. Missing: `{"k": "TEAK"}` (C4(m)),
  `{"k": [1, 2]}` and `{"k": [2, 1]}` (C5(g)), `{"a": {"x": 1, "y": 2}}` (C5(h)),
  `{" wood_type": ["x"]}` and `{"wood_type": ["x"]}` (C5(b)), `{"Wood_Type": "Teak", " wood_type": "Oak"}`.
  Every *branch* of `normalize_stock_criteria` is represented by a payload that is present, so
  completing the list catches nothing new — recorded rather than blocked, deliberately.
- **N-R3** — `recompute_row_counters`, `recompute_goal_total` and `recompute_task_stock_flag` have no
  caller anywhere in `app/`, production or test. Charter rule 4 (no dead scaffolding) is technically
  unmet; the prompt explicitly provisioned them for phases 4/5/11 and no criterion row traces to
  §6.5 (review 1's lesson L-8), so demanding a test here would be inventing a row. Destination: the
  phase that first calls each — and L-8's proposal of one registry criterion per phase.
- **N-R4** — `test_stock_report_reset.py` still leaks its **own** workspace's two kit users
  (`usr_sm_reset-own`, `usr_sw_reset-own`) into the worker DB: `reset_app` keeps users global and the
  ctx passes `delete_orphan_bootstrap_users: False`, and only the foreign workspace is purged in
  `finally`. Down from ~13 rows/run to 2. The worker DB is provisioned fresh per pytest process
  (`conftest.py:20-35`), so this is a within-run leak only. Destination: fix round or phase 13A's
  isolation pass.
- **N-R5** — plan 2 C3(d)'s fixture is `criteria {"quantity": ["4","8"]}` with `quantity 8`; the
  shipped test uses `{"wood_group": ["dark","teak"]}` on a Teak item. Same code path
  (`criteria_matcher.py:101`), same outcome, mutation bites — but the deviation was not declared
  (charter rule 14).
- **N-R6** — plan 2 C5(d), C5(e) and C5(n) are three sequential `assert` statements appended to
  `test_wildcard_and_token_matching_table`. Charter rule 12's short-circuit shape: an earlier
  assertion failing means the later rows never execute. Reachability is established today by the
  green run; splitting them into parametrize rows would make each row independently addressable.
- **N-R7** — plan 3 C3(f) is discharged by C6(a)'s fixture (`[1, 3, NULL]`), not its own
  (`[1, 2, 3]` with the third raw-set to 5). Every clause of C3(f) is asserted, with different
  literals. Related: in **every** priority-order fixture in the suite, rows are created in ascending
  `priority_order` order, and client_ids are ULIDs — so client_id order and priority_order order
  always agree. I built the discriminating fixture (rows created in reverse order) as a probe and
  confirmed production is correct and the mutant is **not** equivalent. Worth one permanent fixture
  whose creation order and ordering disagree.
- **N-R8** — `reset_app`'s renumbered docstring list skips 23 and 27. Pre-existing off-by-one,
  shifted by the insertion, not introduced.
- **N-R9** — `app/tests/helpers/test_settings.py` contains **no tests**; it is a helper module whose
  `test_*` name makes pytest collect it, and it is what the deleted file collided with. Any future
  `test_settings.py` anywhere under `tests/` will re-create the collection error. Renaming it to
  `settings_helpers.py` removes the hazard permanently. Outside batch A's perimeter.

Review 1's notes N-1, N-2, N-3, N-6, N-8, N-9 remain open and out of scope, as the prompt directs.
N-7 was absorbed by F-S8 and is **closed** — `write_repair_record` takes `now`.

---

## 9. Carry-forward dispositions

| Item | Destination |
|---|---|
| N-R1 unlocked post-read goal-total row | phase 5 (inline goal credit) |
| N-R2 C5(c) payload enumeration | fix round 2, if one runs; else phase 13A |
| N-R3 three uncalled registry helpers | phases 4 / 5 / 11, at first call |
| N-R4 two leaked kit users | fix round 2 or phase 13A |
| N-R5 / N-R7 fixture deviations | coordinator fold into plans 2 and 3 |
| N-R6 sequential asserts | plan 2, at the next fold |
| N-R8 / N-R9 | housekeeping backlog |
| Deleted `Settings` coverage (3 settings) | **phase 6**, whose criterion (i) reads the defaults from the class |
| Graph delta (unchanged from review 1) | the orchestrator's approval gate |

---

## 10. Lessons for the plans (coordinator folds upstream)

- **L-10** — plan 1 C1(h)'s named mutation ("drop `workspace_id` from the identity index") is an
  **equivalent mutant**: `item_category_id` is FK-bound to a single workspace, so the identity index's
  `workspace_id` column is redundant. The row's *outcome* is real and worth keeping; its mutation
  column should say so rather than name a defect that cannot exist.
- **L-11** — plan 1 C2(a)'s named mutation ("remove one CHECK from the model") is **inert**: Alembic's
  `compare_metadata` does not diff CHECK constraints. Measured, with "remove an index" as the
  calibrating control. Charter rule 17's territory — the mutation a plan names against a *dependency's*
  comparison engine has to be grounded in what that engine actually compares.
- **L-12** — plan 3 C1(k) names one mutation ("drop the `workspace_id` filter from **any** kind") for
  a row that protects **five** distinct filters. Charter rule 12's other half: one mutation per
  sub-check. A single foreign-drift fixture can never discharge it; the row needs one planted drift
  per kind, like §12A's own C1 probe set.
- **L-13** — plan 3 C3(d) and C3(e) are the two directions of one repair. C3(e)'s test discharges the
  record contract and makes C3(d)'s missing half invisible. When two rows are inverse directions of
  one write, each needs its own record assertion, or the pair needs one parametrized row.
- **L-14** — every priority-order fixture in plans 3 creates rows in ascending `priority_order` order.
  With ULID client_ids that makes the two candidate sort keys identical, so C3(f)'s "renumber by
  client_id" mutation is only observable through the *nullness* row. Rule 2's companion: at least one
  fixture must create rows in an order that disagrees with their ordering.
- **L-15** — `sorted()` over a `set` cannot be mutation-tested deterministically: dropping `sorted`
  reddens the golden vectors on 4 of 7 `PYTHONHASHSEED` values. Plans that name "drop `sorted`" as a
  mutation should say that the fixture needs ≥3 elements, or accept the assertion as the guard.

---

## 11. What I ran

| # | Hypothesis | Scope | Command | Result |
|---|---|---|---|---|
| — | tree identity | — | `git status --porcelain`; `git diff --name-status 983d774..056287e -- app/` | clean; **empty** → the orchestrator's L4 stamp is tree-valid, **not re-run** |
| — | perimeter | — | `git diff --name-status 0d5d31d..983d774` | 17 app paths, 2 deletions, no escape |
| — | plan-file perimeter | — | diff of plans 1–3 | Review-log additions only |
| — | registry call sites | — | `grep -rn --include="*.py"` over `app/` for the six registered names | F-S8 / N-R3 |
| — | orphan inventory | L2 | `pytest … --collect-only -q` over the batch | F-R3 |
| — | basename collisions | — | `find app/tests -name "test_*.py" \| xargs basename \| sort \| uniq -d` | empty |
| — | test-package convention | — | `find app/tests -name "__init__.py"` | empty (N-5 confirmed) |
| 1–55 | the mutation sweep (§4) | L1 / L2 | per-site, each applied → run → reverted with a checksum assert | §4 |
| — | condition variation | L1 | the `drop sorted()` mutant under `PYTHONHASHSEED` ∈ {0,1,2,3,7,11,42} | RED 4/7 |
| — | anomaly re-measurement | L1 + L2 | the C3(f) mutant re-run 12× at two scopes after one anomalous green | RED 11/12; see the declaration |
| — | C3(f) discriminating fixture | L1 | reviewer probe, clean tree then mutated | green → RED; mutant is **not** equivalent |
| — | closing cleanliness | L2 | `pytest tests/unit/domain/stock_report tests/integration/models/stock_report tests/integration/services/queries/stock_report tests/integration/services/commands/stock_report tests/integration/services/commands/reset tests/integration/helpers/test_stock_report_helper.py -q` | **155 passed in 4.15s** — matches the fix handoff's L2 exactly, after every probe was reverted |
| — | lint | — | `ruff check` over the batch's source + kit | All checks passed |

**No L4 was run.** My tree's `app/` is byte-identical to the stamped `983d774`, and no hypothesis in
this re-review was repository-wide (charter test-evidence section; the prompt also forbids it).

---

## 12. Mutation-probe declaration

**Files mutated and restored.** Twelve files were backed up to `/tmp/sr-rereview/*.orig` before any
probe and checksummed. Every probe applied exactly one edit set, ran, and reverted inside a `finally`
that asserts the SHA-256 matches the pre-probe value; `__pycache__` under `app/beyo_manager` was
cleared before each run so no stale bytecode could mask a mutation, and each run asserted the mutated
text was present on disk before invoking pytest.

`diff BEFORE.sha256 AFTER.sha256` over all 19 batch-A source/kit files is **empty** — every file is
byte-identical. Unchanged hashes of the files actually mutated:

```
5be822d6b3c90fd4b993866a066ca6061a40e833502116a1ef98e66bcabd3791  criteria_normalization.py
f0c4a51ac03dc6da9e001d254f110c3dee5410ff308a663f6dfb85176cc1dccd  criteria_matcher.py
663cfb0f74a5161d2b295de15d4ca4b3b70c6759934ad11092d18def221c7b72  scanner_property_tables.py
6cddd4de8a52eab03b46d8c8b337551646490f45af1fa18fe5de127fd9ce4767  consistency.py
e9b2ae0d59b3f984be7be98006db86a7bf5244c9de48bca8a04738b0f21b4a04  repair_stock_report.py
50123b24573ac462db5488d40ddb6b46b91cd1251f9d3c157971a616ce9000ca  reset_app.py
98d7db0e00cd0c23f422bd7395c4f6df2ae125408cd95cc3a881a3da1066a53b  stock_report_item.py
b4adcea6ad85aaa7b09d82470bd20cfae9cb70cadb79f0a86f328fb3d80a9185  tests/helpers/stock_report.py
```

**Files created and removed.** Two probe files, copied to `/tmp/sr-rereview/` and **deleted** from the
tree: `app/tests/integration/models/stock_report/test_zz_rereview_probe.py` (the six DB-level index
mutations) and `app/tests/integration/services/commands/stock_report/test_zz_rereview_probe2.py` (the
C3(f) discriminating fixture). `git status --porcelain` is **empty** at close; HEAD is `056287e`.

**Database/state side effects: none.** Every probe ran inside the `db_session` fixture, which rolls
back (`tests/conftest.py:107-110`). The six schema mutations were `DROP INDEX` / `CREATE UNIQUE INDEX`
issued **inside that transaction** — Postgres DDL is transactional, so they rolled back with
everything else, and the worker database is dropped at session end regardless
(`database_isolation.py:254-258`). The configured development database was never connected to.
No graph write was made.

**One anomalous reading, disclosed.** My first run of the C3(f) mutant at L2 scope reported
`34 passed`. I could not reproduce it: 12 subsequent runs at two scopes, with a hardened harness that
clears bytecode and asserts the mutation is on disk, all reddened (11 of 12 — the third reddening
test, `test_density_repair_stamps_only_the_renumbered_row`, is intermittent under the mutant). The
ledger records **RED** and C3(f) is graded PASS on the reproduced result. Flagging it because a
single green reading is exactly how a row-that-cannot-fail gets waved through, and the discipline has
to cut both ways.

---

## 13. What the next round must do

1. Owner rules on card 1 (`expected_task_flag`'s registry signature).
2. F-R1: implement the ruling, and arm plan 3 C1(k) with one foreign-planted drift per kind.
3. F-R2: assert the record 6-tuple and the clean post-repair check in
   `test_manual_repair_clears_false_positive_task_flag`.
4. F-R3: delete or route `test_consistency_matches_migrated_worker_schema`.
5. Orchestrator: add `lock_stock_report_history_records` to master plan §6.5 (§6 above), and fold
   lessons L-10…L-15.

Nothing else in batch A is outstanding. The other 168 rows are armed and measured.
