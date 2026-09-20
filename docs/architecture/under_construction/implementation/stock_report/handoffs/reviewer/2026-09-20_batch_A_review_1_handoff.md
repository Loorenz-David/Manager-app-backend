---
plan: batch A (1, 2, 3)
role: review
round: batch_A-review-1
state: CHANGES_REQUESTED
date: 2026-09-20
actor: Claude Opus 5 (plan-reviewer)
tree: 0d5d31d
---

# Batch A review 1 — phases 1, 2, 3

**Tree identity.** Session HEAD is `eef2977`, `git status --porcelain` empty. `git diff 0d5d31d..eef2977`
touches only `docs/archgraph-anchor-observations.md`, `SR/master_plan.md` and the reviewer prompt —
**no source or test file differs from `0d5d31d`**, so the orchestrator's L4 stamp on `0d5d31d`
(21 failed / 3241 passed / 2 skipped, failure IDs identical to the 21-ID baseline both ways) is
tree-valid for this review and is **consumed by citation, not re-run** (charter test-evidence section).

## 1. Verdict and counts

**CHANGES_REQUESTED.** 2 blocking, 14 should-fix, 9 notes.

Verdict vocabulary, stated so the table is decidable:
- **PASS** — every clause of the row's *Exact outcome* is asserted by a test that can fail (directly,
  or by an equivalent fixture that arms the row's named mutation).
- **FAIL** — a clause is contradicted by the implementation, **or** the assertion that discharges the
  row is materially weaker than the row (a paraphrase, a kind-only check, a disjunction, a fixture
  that cannot discriminate the row's predicate).
- **NOT_VERIFIED** — no test in the tree addresses the row.

| Phase | Rows | PASS | FAIL | NOT_VERIFIED |
|---|---|---|---|---|
| 1 | 53 | 40 | 8 | 5 |
| 2 | 75 | 64 | 7 | 4 |
| 3 | 42 | 21 | 15 | 6 |
| **Total** | **170** | **125** | **30** | **15** |

**Read this before the tables.** Of the 30 FAILs, **26 are "the test is weaker than the row", not
"the production code is wrong"**. I verified the underlying behaviour myself for every such row I
could reach (probe log, §8) and it holds. Four FAILs are real production divergences (F-S1 wood-group
case ×4 rows) and one is the blocking repair defect (F-B1). The dominant defect family in this batch
is the pipeline's own recurring one: **a row discharged by an assertion that cannot observe what the
row names.**

## 2. ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — does fixing the criteria-normalization bug bump the version constant?

**Question.** When the blank-element bug in `normalize_stock_criteria` is fixed, does
`CRITERIA_NORMALIZATION_VERSION` go to 2, or stay at 1?

**Story.** Scanner sends you a rule for "Down or Up & Down" upholstery. Today, if that list carried a
stray empty entry, Manager would file it under a different fingerprint than the rule Scanner thinks
it sent — so the same rule could end up on two separate board rows, each with its own counters. The
fix makes Manager agree with Scanner again. Nothing has shipped yet, so there is no live board to
re-file; but the number stamped on the fingerprint rule is how a future you will know which rows were
made by which recipe.

**Branches.** Stay at 1 — simplest, and truthful because no row was ever created by the broken
recipe. · Go to 2 — records that the recipe changed, at the cost of a constant nobody can point at
real data for.

**Recommendation.** Stay at 1, because the contract's version rule exists to force a re-signing
migration for *existing* rows and there are none; the golden vectors are updated instead.

**On silence.** The gate holds: the fix round implements the correction and leaves the constant at 1,
flagged in its handoff for your confirmation before batch A is approved.

**Trace.** intention §4A MC-3 ("Version"); plan 1 C5(d); finding F-B2.

## 3. Scanner conformance record (prompt gap 1)

Scanner repository `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify`,
read-only, **HEAD `a565674`, not `0d80bf2` as the prompt states**. I verified the drift is immaterial:
`git diff 0d80bf2..a565674 -- modules/stock/domain/property-criteria.ts modules/stock/domain/best-match.ts shared/item-properties/`
is **empty** — every file plan 2 cites is byte-identical between the two commits, so
`SCANNER_SOURCE_COMMIT = "0d80bf2"` remains an accurate provenance stamp and no fixture is affected.

Run with the real dependency: `apps/backend/node_modules/.bin/tsx /tmp/sr-review/conf.ts`.

### 3.1 `normalizeCriteria` — every hand-walk rule's criteria, input → output

| H-row | Input (the report line as the hand-walk writes it) | Scanner output | Fixture in `test_criteria_matcher.py` | Verdict |
|---|---|---|---|---|
| H1 | `{"wood_group":"Dark"}` | `{"wood_group":["dark"]}` | `{"wood_group": ["dark"]}` | match |
| H2 | `{"wood_group":"Light"}` | `{"wood_group":["light"]}` | `{"wood_group": ["light"]}` | match |
| H3 | `{"wood_group":"Teak"}` / `"Light"` | `{"wood_group":["teak"]}` / `["light"]` | same | match |
| H4, H4′ | `{"quantity":"4","upholstery":"Down","wood_group":"Teak"}` | `{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"]}` | same | match |
| H5 | `{"quantity":"4","upholstery":"Up & Down","wood_group":"Light"}` | `{"quantity":["4"],"upholstery":["up & down"],"wood_group":["light"]}` | same | match |
| H6 | `{"quantity":"8","upholstery":"Up & Down","wood_group":"Teak"}` | `{"quantity":["8"],"upholstery":["up & down"],"wood_group":["teak"]}` | same | match |
| H7, H8 | H4's rule | as H4 | same | match |
| H9 | `{"shape":"Oval","wood_group":"Light"}` | `{"shape":["oval"],"wood_group":["light"]}` | same | match |
| H10 | `{"shape":"Round","wood_group":"Dark"}` | `{"shape":["round"],"wood_group":["dark"]}` | same | match |
| H11 | `{"wood_type":null}` | `{"wood_type":null}` | `{"wood_type": None}` | match |
| H13, H14 | `{"drawers_range":"3-5"}` | `{"drawers_range":["3-5"]}` | same | match |
| H15 | `{"wood_group":[]}` | **throws** `ValidationError: Stock criteria values cannot be empty` | `{"wood_group": []}` | match — consistent with the plan's own note that only a non-Scanner payload can hold this |
| (variation) | `{"wood_group":["Dark","Teak"]}` | `{"wood_group":["dark","teak"]}` | *no fixture anywhere* | see F-S3 |

**Every C6 criteria literal is Scanner-conformant. Rule 17 is discharged for the criteria side.**

### 3.2 `deriveItemProperties` — the item side (this is where the divergence is)

| Item properties | Scanner output | Manager `build_item_property_bag` | Plan 2 row | Verdict |
|---|---|---|---|---|
| `{"wood_type":"Walnut"}` | `wood_group: "Dark"` | `"dark"` | C4(a) says `"Dark"` | **DIVERGES** |
| `{"wood_type":"Teak, Oak"}` | `wood_group: "Teak"` | `"teak"` | C4(b) says `"Teak"` | **DIVERGES** |
| `{"wood_type":"Oak"}` | `wood_group: "Light"` | `"light"` | — | DIVERGES |
| `{"wood_type":"santos rosewood"}` | `wood_group: "Dark"` | `"dark"` | C4(d) says `"Dark"` | **DIVERGES** |
| `{"wood_type":"Other"}` | key not added | key absent | C4(c) | match |
| `{"wood_group":"Dark","wood_type":"Oak"}` | `wood_group: "Light"` | `"light"` | C2(h) says `"Light"` | **DIVERGES** |
| `{"drawers_range":"6+","drawers_qty":"2"}` | `drawers_range: "1-2"` | `"1-2"` | C2(i) | match |

Mechanism: Scanner's `groupByMember.set(normalizeMember(member), group)`
(`shared/item-properties/wood-groups.ts:54-70`) stores the group name **as declared**; Manager's
`wood_group_of_token` returns `group.lower()`
(`bm/domain/stock_report/scanner_property_tables.py:47`). The inventory hand-walk states the
expected shape literally: H1 — "→ bag `wood_group:"Dark"`". See F-S1.

### 3.3 The two `node -e` checks

```
String(4.0) === "4"            → true          (plan 2 C1(e); Manager: str(4.0).removesuffix(".0"))
String(4.5)                    → "4.5"         (C1(f))
String(true)                   → "true"        (C1(b))
JSON.stringify(["a","b"])      → ["a","b"]     no space after the comma (C1(h))
JSON.stringify({"é":1})        → {"é":1}       not escaped (C1(i))
```
All five Manager expectations are grounded. Also confirmed from
`shared/item-properties/purchase-api.integration.ts:47-66` (`toPropertyValue`): `null`/`undefined` →
dropped, `string` trimmed with `""` → null, `number`/`boolean` → `String(v)`, everything else
`JSON.stringify`. Manager's `_property_value` mirrors this exactly.

## 4. Per-phase verdict tables

### Plan 1 — 53 rows (PASS 40 / FAIL 8 / NOT_VERIFIED 5)

| Row | Verdict | Test id | Note |
|---|---|---|---|
| C1(a) | PASS | `test_active_row_identity_is_unique_but_soft_deleted_identity_is_reusable` | IntegrityError matched on the index name |
| C1(b) | PASS | same | |
| C1(c) | FAIL | `test_terminal_assignment_does_not_block_new_active_assignment` | Row needs **different tasks** to isolate the item index; the test uses the same task AND item and matches `uix_stock_task_assignments_(item\|task)_active` — the disjunction charter rule 2 forbids. Behaviour correct (probe P3) |
| C1(d) | NOT_VERIFIED | — | no `resolved` fixture. Behaviour correct (probe P4) |
| C1(e) | NOT_VERIFIED | — | no `failed` fixture. Behaviour correct (probe P4) |
| C1(f) | NOT_VERIFIED | — | no soft-deleted-active fixture. Behaviour correct (probe P7) |
| C1(g) | FAIL | as C1(c) | task index never isolated. Behaviour correct (probe P6) |
| C1(h) | NOT_VERIFIED | — | no cross-workspace identity test. Behaviour correct (probe P9) |
| C1(i) | PASS | `test_terminal_assignment_does_not_block_new_active_assignment` | |
| C1(j) | NOT_VERIFIED | — | same-task/different-item variant absent. Behaviour correct (probe P8) |
| C2(a) | FAIL | `test_stock_report_migration_declares_all_owned_counter_checks` | The row names `alembic.autogenerate.compare_metadata` against the migrated worker DB; what shipped is a **source-text grep of the revision file**, which cannot see a model↔DB divergence at all. Parity itself verified (probe P2: 0 relevant diffs) |
| C2(b)–(e) | PASS ×4 | `test_stock_report_counter_checks_are_enforced[...]` | exact constraint names |
| C2(f) | PASS | `test_assignment_quantity_must_be_positive` | |
| C2(g) | PASS | `test_history_awaiting_quantity_must_be_non_negative` | |
| C2(h) | PASS | `test_task_stock_assignment_flag_has_a_database_default` | raw INSERT omitting the column |
| C3(a) | FAIL | `test_reset_removes_stock_report_graph_before_task_deletion_and_keeps_other_workspace` | order, foreign counts and the single `workspace:reset` event ✓; **"the workspace row is gone" is not asserted**, and the test commits without a `finally` purge (F-S10) |
| C4(a)–(l) | PASS ×12 | `test_normalization_value_table[...]` | (j)/(k) type clauses discharged by C5(e)/(f), since `{"k":1.0} == {"k":1}` in Python |
| C4(m) | PASS | `test_normalization_value_table[raw1]`, `[raw12]` | literal input `"TEAK"` absent, but the row's named mutation (drop `.lower()`) reddens on `"  Teak "` and `"Straße"` |
| C4(n) | PASS | `test_normalization_value_table[raw12]` | `straße`, not `strasse` |
| C5(a) | FAIL | `test_normalization_preserves_keys_and_is_idempotent` | key preservation ✓; **"signature differs from `{"wood_type":["x"]}` alone" is never asserted** |
| C5(b) | FAIL | `test_normalization_preserves_string_property_key_spelling` | asserts normalize output, **not two different signatures** |
| C5(c) | FAIL | `test_normalization_preserves_keys_and_is_idempotent` | idempotence over **one** payload; the row says every raw payload of C4 and C5 |
| C5(d) | FAIL | `test_signature_uses_normalized_golden_vector` | **one** golden vector; the row says six |
| C5(e)–(h) | PASS ×4 | `test_signature_separates_ununderstood_values_but_sorts_object_keys` | |
| C6(a) | PASS | `test_task_state_map_is_total` | |
| C6(b)–(i) | PASS ×8 | `test_task_state_map_is_exact[...]` | one parametrize row per pair |
| C6(j) | PASS | `test_task_state_map_excludes_scanner_only_terminal_states` | |
| C7(a) | PASS | `test_assignment_state_partition_includes_resolved_early_as_terminal` | union + empty intersection |
| C7(b) | PASS | same | |

### Plan 2 — 75 rows (PASS 64 / FAIL 7 / NOT_VERIFIED 4)

| Row | Verdict | Test id | Note |
|---|---|---|---|
| C1(a)–(i) | PASS ×9 | `test_build_item_property_bag_scanner_table[...]` | every coercion vector grounded in §3.3 |
| C2(a) | PASS | same (`" wood_type "` row) | |
| C2(b) | PASS | same | |
| C2(c) | NOT_VERIFIED | — | no all-blank **key** fixture (`{"   ": "x"}`); only the blank-value case ships |
| C2(d) | PASS | `test_build_item_property_bag_drops_blank_values` | |
| C2(e) | PASS | `test_build_item_property_bag_scanner_table` (`{" a","a"}`) | sorted-key later-wins |
| C2(f) | PASS | same (`qty_extensions`) | |
| C2(g) | PASS | same (`{"quantity":"9"}`) | |
| C2(h) | **FAIL** | same | row says `wood_group = "Light"`; implementation and test both say `"light"` — F-S1 |
| C2(i) | PASS | same | |
| C3(a) | PASS | `test_build_item_property_bag_scanner_table[None]` | |
| C3(b) | PASS | `test_scanner_hand_walk_golden_cases[H16]` | |
| C3(c) | PASS | `[H7]` | |
| C3(d) | **FAIL** | — | **no test anywhere uses a criteria list with more than one accepted value.** The row's named mutation ("require all") survives L1 and L2 — proved, probe P1 |
| C4(a) | **FAIL** | — | bag value never asserted for Walnut, and the value produced is `"dark"` not `"Dark"` — F-S1 |
| C4(b) | **FAIL** | `[H3-teak]` / `[H3-light]` | first-token rule ✓ but the row's stated bag value `"Teak"` is not produced — F-S1 |
| C4(c) | PASS | `test_known_source_without_derived_group_reports_no_group`, `[H12]` | |
| C4(d) | **FAIL** | `[H10]` | member case-folding ✓; stated bag value `"Dark"` not produced — F-S1 |
| C4(e) | PASS | `test_build_item_property_bag_scanner_table` (exact-dict rows without `wood_type`) | |
| C4(f)–(p) | PASS ×11 | `test_drawer_range_derivation_table[...]` | 1/2/3/5/6/0/"4.0"/"abc"/int 4/`٤`/`" 6 "` |
| C5(a) | PASS | `test_empty_list_is_not_a_wildcard` | |
| C5(b) | PASS | `test_matcher_reports_all_sorted_failures`, `[H8]` | |
| C5(c) | PASS | `test_known_source_without_derived_group_reports_no_group` | |
| C5(d) | NOT_VERIFIED | — | no fixture for a **wildcard** (`None`) on a derived key whose source derives to nothing; the row's point is that the wildcard fails too |
| C5(e) | NOT_VERIFIED | — | no `drawers_range` criterion without a `drawers_qty` on the item |
| C5(f) | PASS | `[H14-zero]` | |
| C5(g) | PASS | `test_matcher_reports_all_sorted_failures` (upholstery), `[H4prime]` | plain-key-absent rule armed |
| C5(h) | PASS | `test_wildcard_and_token_matching_table` (`", /"`) | |
| C5(i) | PASS | same, `[H11-present]` | |
| C5(j) | PASS | same (`up & down`) | |
| C5(k) | PASS | same | |
| C5(l) | PASS | same (`Oval/Rectangular`) | |
| C5(m) | PASS | `test_matcher_reports_all_sorted_failures`, `[H8]` | three failures, sorted, no short-circuit |
| C5(n) | NOT_VERIFIED | — | no `evaluate_stock_criteria(item(None), {})` case |
| C5(o) | PASS | `test_scanner_hand_walk_golden_cases` (final assert) | checked over all 21 hand-walk fixtures |
| C6(a)–(i) | PASS ×9 | `test_scanner_hand_walk_golden_cases[H1..H8]` | H3 both rules ✓, H4′ ✓ |
| C6(j) | **FAIL** | `[H9]` | the hand-walk names **two items** (`"shape":"Oval"` and the `"Oval/Rectangular"` variant); only the variant ships |
| C6(k)–(q) | PASS ×7 | `[H10]`…`[H16]` | H11 both ✓, H14 all three ✓ |
| C7(a) | **FAIL** | `test_scanner_tables_and_drawer_ascii_rules` | asserts only `WOOD_GROUPS["Dark"]`; the row says the whole literal (Teak and Light lists unguarded) |
| C7(b) | PASS | same | |
| C7(c)–(e) | PASS ×3 | `test_scanner_table_validators_reject_ambiguous_definitions` | incl. the `maximum < minimum` branch |

### Plan 3 — 42 rows (PASS 21 / FAIL 15 / NOT_VERIFIED 6)

Note on the bar: intention §12A states the charter-rule-15 probe set explicitly — "one planted
drift per `kind` … **each must produce exactly one divergence of that kind, with the exact stored and
expected values**. That makes eight probe rows." A C1 row discharged by a kind-set assertion does not
meet it.

| Row | Verdict | Test id | Note |
|---|---|---|---|
| C1(a) | FAIL | `test_counter_and_signature_divergences_are_reported` | asserts only `{kinds} == {counter_in_queue, task_flag}` — no exact stored/expected dict for `counter_in_queue` anywhere |
| C1(b) | PASS | `test_active_counter_divergence_kinds_are_reported[IN_PROGRESS]` | exact dict |
| C1(c) | PASS | `[AWAITING]` | exact dict |
| C1(d) | NOT_VERIFIED | — | no check-level test for a flagged task with no assignment (only the repair path covers it) |
| C1(e) | FAIL | `test_counter_and_signature_divergences_are_reported` | `task_flag` appears as a kind only; stored `"false"` / expected `"true"` never asserted |
| C1(f) | FAIL | `test_goal_signature_and_density_divergences_are_reported` | single-row group; the row's discriminating clause "rows 1 and 2 not reported" is untested |
| C1(g) | FAIL | `test_null_priority_order_appends_after_the_group_maximum` | fixture changed from the row's dense `[1, 2]` to a sparse `[1, 3]`, and the asserted `expected` (3) **contradicts** §12A / §6.5 `max(group) + 1` (= 4). Probe P5 confirms the implementation reports 3 for a `[1, 7]` group where the contract says 8 — F-S2 |
| C1(h) | NOT_VERIFIED | — | no check-level test for priority NULL with an order set |
| C1(i) | FAIL | `test_goal_signature_and_density_divergences_are_reported` | only `expected == 4`; client_id/field/stored unasserted |
| C1(j) | FAIL | same | only `expected`; `stored` (the stale signature) unasserted |
| C1(k) | FAIL | `test_consistency_does_not_report_foreign_workspace_drift` | one foreign drift (counter + signature); the row says **every** C1(a)–(j) drift planted foreign. `task_flag`, `goal_total`, `order_density`, nullness workspace filters are unguarded |
| C1(l) | PASS | `test_resolved_early_is_terminal_but_still_counts_toward_goal_total` | full-list equality discriminates both halves |
| C2(a) | FAIL | `test_consistency_service_returns_workspace_timestamp_and_divergences` | uses `count_writes`; the owner restated this row (master plan §7.4 item 5) to assert the **data is unchanged before and after** over the four MC-9 tables plus repair records |
| C2(b) | PASS | `test_goal_signature_and_density_divergences_are_reported` | five kinds in sorted order |
| C2(c) | PASS | `test_consistency_service_returns_workspace_timestamp_and_divergences` | |
| C3(a) | FAIL | `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` | kinds set + the **task** record asserted; the counter record's `target_kind`/`field`/`stored_value`/`recomputed_value`/`trigger`/`created_by_id` are not |
| C3(b) | NOT_VERIFIED | — | no repair test for `quantity_in_progress` |
| C3(c) | NOT_VERIFIED | — | no repair test for `quantity_awaiting` |
| C3(d) | FAIL | `test_manual_repair_clears_false_positive_task_flag` | flag cleared ✓; the record dict is not asserted |
| C3(e) | PASS | `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` | `("false","true")` |
| C3(f) | FAIL | `test_repair_records_one_net_change_per_priority_order_field` | different fixture, and `target_kind: group` is asserted **nowhere in the suite** |
| C3(g) | FAIL | same | stored NULL / recomputed `"3"` ✓; `target_kind: stock_report_item` unasserted |
| C3(h) | **FAIL (blocking)** | — | `repair_stock_report` raises `RuntimeError` instead of setting the order NULL — F-B1, probe P10 |
| C3(i) | PASS | `test_manual_repair_fixes_goal_total_and_writes_history_record` | target_kind, field, stored, recomputed |
| C4(a) | PASS | `test_manual_repair_leaves_signature_divergence_unrepaired` | full response dict, signature unchanged, zero records |
| C5(a) | PASS | `test_clean_manual_repair_makes_no_stock_writes_or_events` | writes 0, events [] |
| C6(a) | FAIL | `test_repair_applies_nullness_before_priority_density` + records test | final orders and net records ✓; the row's `target_kind` clause (`group` for the moved row, `stock_report_item` for the appended one) is unasserted |
| C6(b) | PASS | `test_task_flag_repair_does_not_change_task_stamps` | |
| C6(c) | PASS | `test_counter_repair_stamps_only_the_changed_stock_report_row` | changed and unchanged rows both asserted |
| C6(d) | NOT_VERIFIED | — | the density-renumbered row's stamp is never asserted |
| C6(e) | FAIL | `test_repair_dispatches_only_changed_stock_report_rows` | fixture omits the goal drift the row names, so "nothing for G" is untested |
| C6(f) | PASS | `test_repair_records_one_net_change_per_priority_order_field` | SQL NULL, not `"None"` |
| C7(a) | NOT_VERIFIED | — | **the helper is never shown to raise on a stray repair record** — the charter-rule-15 probe for `assert_stock_report_clean` itself |
| C7(b) | PASS | `test_clean_seed_has_no_stock_report_divergences` | |
| C8(a)–(h) | PASS ×8 | `test_stock_report_routes_reject_non_manager_roles`, `..._reach_service_for_permitted_roles` | 403 + service not called, 200 + service reached. The literal message `Insufficient role permissions.` is not asserted; graded PASS because it is emitted by shared `require_roles` machinery with its own coverage and the discriminating content is exact (note N-8) |

## 5. Mutation audit (prompt gap 3)

**Declared sites.** My count of distinct named-mutation cells is **35 / 37 / 22 = 94**, matching the
orchestrator's and contradicting the handoff's "39/37/22". The handoff's `executed=123` counts
repeated ledger lines (Plan 1 C1(h), C2(b), C3, C6(a); Plan 2 C1(b), C2(a)/(b), C5(a)/(c)/(d);
Plan 3 C6(b)/(c)/(f) each appear two or more times), so **`executed == declared` is asserted, not
shown**. I did not reconcile all 94 line by line; I audited the sites the row table flagged as doubtful
and re-ran the ones whose survival would change a verdict.

**Declared sites I found never probed:**

| Site | Status |
|---|---|
| Plan 2 C3(d) "require all" | **Never probed, and the mutant survives** — probe P1. This is the only unrun mutation that turned out to be a real coverage hole |
| Plan 3 C7(a) "split the helper into two functions" | Never probed; the row has no test either |
| Plan 1 C5(g) "sort not-understood lists" | Never probed. Re-derived: it would redden `test_signature_separates_ununderstood_values_but_sorts_object_keys` — armed |
| Plan 1 C7(a) "add a member to the enum only" | Never probed. Re-derived: reddens the partition test — armed |

**Declared sites probed against the wrong instrument.** Plan 1 C1(a),(b),(c),(f),(g),(h),(i)/(j) and
C2(a),(b),(c),(e),(h) are recorded in the ledger as reddening `test_schema_contract.py` — a test that
reads `Base.metadata` and greps the migration source. The rows name **database** outcomes
(IntegrityError on a flush, a raw INSERT defaulting). A mutation that removes an index from the ORM
`__table_args__` reddens a metadata assertion without ever proving the database rejects the duplicate.
The DB-level instrument exists for C1(a),(b),(i) and C2(b)–(h) only.

**Mutations I ran myself (variation, not reproduction):**

| # | Site (file · definition) | Scope | Result |
|---|---|---|---|
| P1 | `criteria_matcher.py::evaluate_stock_criteria` — `any(token in accepted …)` → `all(value in tokens …)` | L1 `test_criteria_matcher.py`, then L2 `tests/unit/domain/stock_report` | **SURVIVED**: 56 passed, then 96 passed. Plan 2 C3(d)'s mutation does not bite |

## 6. Batch-level findings

Grouped by cause. One fix prompt.

### Blocking

**F-B1 — the manual repair crashes on the divergence it is contracted to fix (priority NULL, order set).**
`repair_stock_report.py:38-54` selects only rows with `priority IS NOT NULL`, and the main loop
`continue`s on both ordering kinds (`:171-172`). A row with `priority = NULL` and `priority_order = 1`
is therefore repaired by nobody; the post-repair re-check (`:215-224`) still sees it and raises.
Observed verbatim (probe P10):
```
RuntimeError: stock-report repair left divergences: [{'kind': 'priority_order_nullness',
 'client_id': 'sri_…', 'field': 'priority_order', 'stored': 1, 'expected': None}]
```
The whole transaction rolls back, so a workspace containing one such row can never be repaired at
all — every other divergence in it is abandoned too. Authority: intention §12A MC-20 repair table
("`priority` null → `priority_order` set null"); plan 3 C1(h), C3(h).
**Correction:** handle the `expected is None` case (set `priority_order = NULL`, write one
`stock_report_item` record with `stored_value` = the old order and `recomputed_value` NULL) before
`_repair_priority_orders`, and add the C3(h) row's test.

**F-B2 — `normalize_stock_criteria` does not drop blank elements from an understood list, so the row
signature diverges from the contract.**
MC-3's value table: a list of strings with at least one non-blank is stored as
`sorted({e.strip().lower() for e in v if e.strip().lower() != ""})` — the blank elements are
**filtered**. `criteria_normalization.py:17` is `sorted(set(v.strip().lower() for v in value))`, with
no filter. Measured:
```
{'k': ['Teak', '  ', 'Dark']} -> {'k': ['', 'dark', 'teak']}      MC-3 says {'k': ['dark', 'teak']}
{'k': ['Down', '']}           -> {'k': ['', 'down']}
```
The extra `""` changes `properties_signature`, so the same rule lands on a different
`stock_report_item` identity, and the matcher then carries a `""` token that no item value can
satisfy. Scanner's own `normalizeCriteria` filters blanks (`.filter(Boolean)`), so the exposure is
limited to a non-Scanner payload — but MC-3 is explicit that Manager accepts what Scanner throws on
and stores it by this table. Authority: intention §4A MC-3 value table, row 4.
**Correction:** add the `if e.strip()` filter; extend the plan 1 C4 table with the missing row
(lesson L-1); see owner card 1 on the version constant.

### Should-fix

**F-S1 — the derived `wood_group` is lower-cased, diverging from Scanner and from four plan rows.**
`scanner_property_tables.py:47` returns `group.lower()`. Scanner returns the declared group name
(`"Dark"`, `"Teak"`, `"Light"`) — grounded in §3.2 above and in the hand-walk's H1 cell
("bag `wood_group:"Dark"`"). Plan 2 C2(h), C4(a), C4(b), C4(d) all state the capitalized value; the
test at `test_criteria_matcher.py:76,88` asserts the lower-cased one, so the divergence is cemented.
No user-visible wrong answer today, because both sides of the comparison are tokenized to lower case
— but `build_item_property_bag` is a §6.1 public name and the next consumer that compares a bag value
to a Scanner-supplied value will disagree. Authority: master plan §9 rule 14, charter rule 17, plan 2
C2(h)/C4(a)/(b)/(d). **Correction:** return `group` unchanged; update the four assertions to the
plan's literals.

**F-S2 — the check's `expected` for a null priority order is `len(assigned) + 1`, not `max(group) + 1`.**
`consistency.py:121-126`. Intention §12A ("appended at the end of its group (`max + 1`)") and master
plan §6.5 ("`expected` = `max(group) + 1`") both say max. The two agree only on a dense group, and
plan 3 C1(g)'s fixture was changed from the row's dense `[1, 2]` to a sparse `[1, 3]` — where they
still agree by coincidence — so the test named
`test_null_priority_order_appends_after_the_group_maximum` asserts a value that is *not* after the
group maximum. Probe P5 on a `[1, 7]` group: reported `expected` 3, contract 8. The repaired value is
correct (density renumbering makes it so); it is the **reported** number the admin sees that is wrong.
**Correction:** use `max(assigned_orders, default=0) + 1`; restore C1(g)'s dense fixture and add the
sparse case as the discriminating neighbour.

**F-S3 — no test anywhere exercises a criterion with more than one accepted value.**
Every criteria list in the suite has exactly one element, so the any-of semantics at the heart of
`matchesCriteria` is unguarded: the "require all" mutant survives both L1 and L2 (probe P1). Plan 2
C3(d) is the row that exists for this. Scanner does send multi-value criteria
(`{"wood_group":["dark","teak"]}` normalizes fine — §3.1). **Correction:** implement C3(d) as written
plus the symmetric miss, and run the named mutation.

**F-S4 — the two partial unique indexes are never isolated, and five index rows have no test.**
`test_stock_report_schema.py:84-87` matches `uix_stock_task_assignments_(item|task)_active` on a
fixture that violates both — the disjunction charter rule 2 names ("an assertion accepting a
disjunction of outcomes hides mislabeling"). Plan 1 C1(c) requires different tasks, C1(g) different
items. C1(d), (e), (f), (h), (j) have no test at all. I verified all seven behaviours myself
(probes P3, P4, P6–P9) and they are correct — this is purely missing coverage on the phase's
silent-failure mechanism. **Correction:** one row per C1 letter, each asserting one index name.

**F-S5 — plan 1 C2(a)'s migration-parity instrument was not built.**
What shipped (`test_schema_contract.py:98-113`) greps the revision file for constraint names. The row
names `alembic.autogenerate.compare_metadata` against the migrated worker DB via `run_sync`, filtered
to the five tables. The revision was hand-edited (the implementer removed three unrelated autogenerate
operations), which is exactly the case the row exists for. I ran the real comparison myself (probe P2):
**0 diffs on the five tables** — the schema is correct today, but nothing in the suite will notice if
it stops being. **Correction:** build the row as written.

**F-S6 — the goal-total repair writes `stock_report_history_records` without locking it.**
§12A's repair lock order is "advisory → tasks → rows → assignments → **history records** — each class
ascending". `repair_stock_report.py:182-189` issues an absolute `UPDATE … SET quantity_awaiting = …`
on a history row that was never locked, and `_locks.py` has no history-lock helper (master plan §6.5
omits one — lesson L-4). Two manual repairs are serialized by the advisory lock, but phase 5's inline
goal credit will not take it, so a manual repair can overwrite a concurrent credit with a stale
absolute value. **Correction:** add `lock_stock_report_history_records` to `_locks.py` and §6.5, and
lock the diverging records after the assignments.

**F-S7 — no "≠ 1 row is a programming error" guard on three of the four repair statements.**
Plan 3 §7 asks the reviewer to verify this structurally. Result: `set_task_stock_flag`
(`_task_flag.py:14-15`) checks `rowcount not in (0, 1)` — and accepts 0, which on the repair path
means the repair silently did nothing. The counter UPDATE (`repair_stock_report.py:191-201`), the
goal-total UPDATE (`:183-189`) and the priority-order UPDATE (`:71-79`) have **no rowcount check at
all**. Authority: intention §12A mechanics. **Correction:** assert `rowcount == 1` on all four repair
statements (the flag's idempotent 0 case is only legitimate outside the repair path).

**F-S8 — undeclared deviations from the §6.5 naming registry.** None was recorded as a judgment call,
and every one of them is a signature later phases are planned against:

| Registered (§6.5) | Shipped | Consumer at risk |
|---|---|---|
| `recompute_row_counters(session, stock_report_item_id) -> dict[str,int]` | `(session, workspace_id) -> dict[str, dict]` | phase 4's inline self-heal is per row |
| `recompute_goal_total(session, history_record_id) -> int` | `(session, workspace_id) -> dict[str,int]` | phase 5 |
| `expected_task_flag(session, task_id) -> bool` | `(session, workspace_id, task_id)` | phase 11 |
| `recompute_task_stock_flag(session, task_id) -> bool` | `(session, workspace_id, task_id) -> None` | `_remove_assignment` (phase 4) |
| `write_repair_record(…, stored_value, recomputed_value, …, now)` | `(…, stored, recomputed, …, delta=None)`, **no `now`** | every inline caller; `created_at` now defaults to wall-clock, contrary to §12A "`created_at` — the operation's `now`" |
| `Divergence` TypedDict | never defined | typing only |

**Correction:** either implement the registered signatures or amend §6.5 in the same round and say so
(master plan §6's own rule).

**F-S9 — plan 1 C5's signature clauses are unasserted.** C5(a) and C5(b) each state that two spellings
of a key produce **two different signatures**; the tests assert only the normalized dicts. C5(c) runs
idempotence over one payload instead of every C4/C5 payload. C5(d) ships one golden vector where the
row says six. The golden vectors are, per MC-3, "what redden" if the identity function ever changes —
one vector is a thin guard for the function F-B2 just turned out to be wrong in.

**F-S10 — the reset test commits and never purges.**
`test_stock_report_reset.py:89` commits two seeded workspaces; `reset_app` commits again. The foreign
workspace, its users, category, item, task, task_item and four stock rows are left in the worker
database. Charter rule 11½ and master plan §9 rule 1 both require a `finally` purge via
`purge_stock_report_workspace`, which this batch shipped and which no committing test calls. The same
row also fails to assert "the workspace row is gone" (C3(a)) and hand-rolls its dispatch capture
instead of the kit's `capture_dispatch`, which plan 1 task 7 names as C3(a)'s caller.

**F-S11 — repair-record `target_kind` is asserted nowhere.** C3(f), C3(g) and C6(a) each state the
`target_kind` the record must carry (`group` for a renumbered row, `stock_report_item` for an appended
one); `_repair_priority_orders:83-87` computes it from `stored is None` and no test observes it.
C3(a) and C3(d) likewise assert no record fields for the counter and task repairs.

**F-S12 — plan 3 C2(a) uses the instrument the owner replaced.** The shipped test counts write
statements; the owner's 2026-09-19 ruling (master plan §7.4 item 5) restated the row to compare every
row of the four MC-9 tables and `stock_report_repair_records` in W before and after. Recorded honestly:
MC-20 itself blesses the statement listener, so the *substance* is proven — but the row is the
specification and it was not followed.

**F-S13 — four coverage rows short of their own enumeration.** Plan 2 C6(j) ships one of H9's two
items; C7(a) asserts only the `Dark` list of `WOOD_GROUPS`; plan 3 C3(b)/(c) have no repair test for
`quantity_in_progress`/`quantity_awaiting`; plan 3 C6(d) never asserts the density-renumbered row's
stamp; plan 3 C7(a) never shows `assert_stock_report_clean` failing on a stray repair record — which is
that helper's own charter-rule-15 probe, and the helper is the instrument every later phase ends its
scenarios with.

**F-S14 — nine orphan tests (charter rule 16).** Tracing to no criterion row and not declared as
candidate criteria in any Review log:

| File | Tests | Comment |
|---|---|---|
| `tests/unit/domain/stock_report/test_schema_contract.py` | 4 | `Base.metadata` introspection and migration source-text greps; implementation-coupled (charter rule 2). Also the instrument the C1/C2 mutations were probed against (§5) |
| `tests/unit/domain/stock_report/test_repair_record_values.py` | 1 | asserts the **private** `_text` helper directly |
| `tests/unit/domain/stock_report/test_settings.py` | 2 | plan 1 says in so many words "Settings (task 5) carry no criterion" |
| `tests/integration/helpers/test_stock_report_helper.py` | 1 | the only caller of `purge_stock_report_workspace`, so it does discharge charter rule 4 — route it, don't delete it |
| `test_repair_stock_report.py::test_stock_report_row_lock_is_workspace_scoped` | 1 | plan 3 §7 makes lock scoping a structural check, not a row |

**Correction:** declare each as a candidate criterion in the owning plan's Review log (the trace-chain
link-3 path) or delete it. I am **not** asking for any new implementation-coupled test; where the
existing ones are implementation-coupled that is a separate backlog note (N-1).

## 7. Backlog notes (kept separate from findings)

- **N-1** — `test_schema_contract.py` and `test_stock_report_partial_unique_indexes_have_workspace_and_active_predicates`
  assert ORM metadata and a literal predicate string (`predicate == "is_deleted = false AND state IN (…)"`).
  Implementation-coupled (charter rule 2) and a charter-rule-13 literal. Backlog: replace with the
  DB-level rows F-S4 asks for, then delete. **Not** a CHANGES_REQUESTED item.
- **N-2** — `compute_stock_report_divergences` calls `expected_task_flag` once per task (`consistency.py:186-187`):
  N+1 on a workspace-wide read. Destination: phase 12 (the list endpoint's performance pass).
- **N-3** — the task-flag scan includes soft-deleted tasks, so a deleted task with a stale flag is
  reported and repaired. Harmless, but undecided by §12A. Destination: phase 11.
- **N-4** — `reset_app`'s docstring still lists 35 steps starting at `task_events`; the four stock
  phases now run first and are not listed. Plan 1 task 4 asked for it. Destination: the fix round.
- **N-5** — `tests/unit/domain/stock_report/__init__.py` is the only `__init__.py` under `tests/` in
  this repository. Collection is unaffected either way; it breaks convention. Destination: fix round.
- **N-6** — `StockReportHistoryRecord.quantity_requested` / `quantity_awaiting` gained
  `default=0, server_default="0"`, which §6.2 does not declare. Benign; record it in §6.2 or drop it.
- **N-7** — `write_repair_record` takes no `now`, so `created_at` is wall-clock rather than the
  operation's `now` (§12A). Folded into F-S8's correction.
- **N-8** — C8(c),(d),(g),(h)'s literal 403 message `Insufficient role permissions.` is not asserted.
  Graded PASS (shared `require_roles` machinery); add the message if a later router phase asserts it.
- **N-9** — plan 2 §2 cites `repositories/location-stock.repository.ts:43-68`; the file is at
  `modules/stock/repositories/location-stock.repository.ts`. Stale citation, fix at the next fold.

## 8. Perimeter ruling on the five deviations

1. **`test_stock_report_reset.py` (plan 1 §4 names `test_reset_stock_report_phases.py`) — ACCEPTED**,
   with a charter rule 14 note: the rename is harmless but was not declared. Either name, recorded.
2. **`tests/integration/helpers/test_stock_report_helper.py` — ACCEPTED, with F-S14.** It is the only
   caller of `purge_stock_report_workspace`, so charter rule 4 is satisfied by it; it is an orphan
   under rule 16 and must be routed as a candidate criterion, not deleted.
3. **`tests/integration/infrastructure/test_database_isolation.py` — ACCEPTED, NO FINDING.** The guard
   still discriminates. `expected_public_tables()` returns `set(Base.metadata.tables) |
   NON_METADATA_PUBLIC_TABLES` (`tests/database_isolation.py:51-53`) — it is the *input* the test
   feeds in, not the function under test; `assert_migrated_schema` is what is being exercised, and the
   test still adds `{"unexpected_public_table"}` and still requires the RuntimeError. The hard-coded
   `109` was a duplicate of a derived number and exactly the time-bomb shape charter rule 13 forbids;
   deriving it is the correct repair, not a hollowing-out.
4. **Missing `__init__.py` in the new test packages — NO FINDING.** No test package in this repository
   has one; collection is unaffected (all 139 batch-A tests collect and run). The inconsistency is the
   one that *was* added (N-5). Plan 1 §4's list is wrong here; fold it (lesson L-6).
5. **No `bm/services/commands/stock_report/requests/__init__.py` — ACCEPTED.** Plan 3 §4 makes it the
   implementer's choice. The choice was not recorded; record it in the fix round's handoff.

## 9. What I ran

| # | Hypothesis | Scope | Command | Result |
|---|---|---|---|---|
| — | tree identity | — | `git status --porcelain`; `git diff --stat 0d5d31d..eef2977` | clean; docs only → orchestrator's L4 stamp is tree-valid, **not re-run** |
| — | Scanner drift | — | `git -C Item-Scanner-Shopify diff 0d80bf2..a565674 -- <the cited files>` | empty |
| S1 | Scanner conformance (gap 1) | external | `apps/backend/node_modules/.bin/tsx /tmp/sr-review/conf.ts` | §3.1–3.2 |
| S2 | JS coercion (gap 1) | external | `node -e '…String(4.0)…JSON.stringify…'` | §3.3 |
| — | suite health at my tree | L1 | `PYTHONPATH=. pytest tests/unit/domain/stock_report -q` | 96 passed |
| P1 | plan 2 C3(d) mutation | L1 then L2 | `pytest tests/unit/domain/stock_report/test_criteria_matcher.py -q`, then the package | **SURVIVED** (56 passed, 96 passed) |
| P2 | plan 1 C2(a) parity | L1 probe | `compare_metadata(MigrationContext, Base.metadata)` via `run_sync` on the worker DB | 0 diffs on the five tables |
| P3 | plan 1 C1(c) | L1 probe | two active assignments, same item, different tasks | `uix_stock_task_assignments_item_active` — correct |
| P4 | plan 1 C1(d)/(e) | L1 probe | `resolved` then `in_queue`; `failed` then `in_queue` | both flush — correct |
| P5 | §12A nullness `expected` | L1 probe | group `[1, 7]` + a null-order row | reported 3, contract says 8 — **F-S2** |
| P6 | plan 1 C1(g) | L1 probe | two active assignments, same task, different items | `uix_stock_task_assignments_task_active` — correct |
| P7 | plan 1 C1(f) | L1 probe | soft-deleted `in_queue` then `in_queue` | flushes — correct |
| P8 | plan 1 C1(j) | L1 probe | `resolved_early` on T then `in_queue` on T | flushes — correct |
| P9 | plan 1 C1(h) | L1 probe | same `(category, signature)` in two workspaces | both flush — correct |
| P10 | plan 3 C3(h) | L1 probe | priority NULL + order 1 → `repair_stock_report` | **RuntimeError** — F-B1 |
| — | MC-3 blank element | L1 | `python -c` on `normalize_stock_criteria` | `['', 'dark', 'teak']` vs MC-3's `['dark', 'teak']` — F-B2 |
| — | lint | — | `ruff check` over the batch's source + kit | All checks passed |

**No L4 was run** (charter over-evidence rule): my tree's source is byte-identical to the stamped
`0d5d31d`, and no hypothesis in this review was repository-wide.

## 10. Mutation-probe declaration

**Files mutated and reverted.** `app/beyo_manager/domain/stock_report/criteria_matcher.py` —
sha256 `f0c4a51ac03dc6da9e001d254f110c3dee5410ff308a663f6dfb85176cc1dccd` before the probe and
**identical** after restoring from `/tmp/sr-review/criteria_matcher.orig.py`.

**Files created and removed.** `app/tests/integration/services/commands/stock_report/test_zz_reviewer_probe.py`
(probes P2–P10), written twice and deleted. `git status --porcelain` is **empty** at the close of the
session; all scratch artefacts live under `/tmp/sr-review/`.

**Database/state side effects: none.** Every probe ran inside the `db_session` fixture, which rolls
back (`tests/conftest.py:107-110`); nothing was committed. The dev database `beyo_manager` was never
connected to, migrated or downgraded. No graph write was made (the graph delta remains the
orchestrator's gate; the intended delta is unchanged from the implementer handoff's §"Graph": one
`capability-stock-report` node plus one node per §6 module registered in this batch, with
`calls`/`writes`/`reads` edges — `command-repair-stock-report` → `query-consistency`,
`command-repair-stock-report` → `model-stock-report-item`/`-history-record`/`-repair-record`/`-task`,
`query-consistency` → the four models, `domain-criteria-matcher` → `domain-scanner-property-tables`).

## 11. Lessons for the plans (coordinator folds upstream)

- **L-1** — plan 1 C4's value table has no row for a list mixing blank and non-blank elements: the one
  MC-3 row the implementation got wrong. Charter rule 2 ("enumerate, never sample") applies to the
  value table, not only to ordered rules.
- **L-2** — plan 2 C6 says "seventeen rows lettered (a)–(q)" while its own prose enumerates 22 cases
  (H3 both, H9 both, H11 both, H14 three). Manifest property 3: the count and the enumeration must be
  derived from one another. H9's second item was the case that fell through.
- **L-3** — plan 3 task 5 says "**zero statements** on the five tables when nothing diverges" while
  C5(a) says `count_writes(...) == 0` and §12A says lock `SELECT`s are not counted. The task text is
  wrong and would make a correct implementation look like a violation.
- **L-4** — §6.5's `_locks.py` registry has no history-record lock helper although §12A's repair lock
  order requires one (F-S6). A contract the plan cites but does not provision.
- **L-5** — plan 1 C1(c)/(g) name the right fixtures but nothing in the row forbids a regex
  disjunction over the two index names. Quote rule 2's "expected outputs too" clause in rows whose
  outcome is an error identity.
- **L-6** — plan 1 §4 lists `__init__.py` files for test packages that this repository does not use
  anywhere. Manifest property 2 (every reference resolves) should run the other way too: a plan should
  not require a file the repo's convention forbids.
- **L-7** — plan 3 C1(g)'s fixture (group `[1, 2]`) is dense, so it cannot tell `max+1` from
  `len+1`. Rule 2's companion — the fixture must make its own predicate the only reason the outcome
  holds — and the implementer then moved it to `[1, 3]`, which is still degenerate.
- **L-8** — the §6.5 registry is checked at review but no criterion row traces to it, so signature
  drift ships silently and is only caught two batches later (F-S8). Consider one criterion per phase
  that pins the phase's registered public signatures, or a plan-lint check.
- **L-9** — plan 2 C4(a)/(b)/(d) and C2(h) state the right literals but no row states the *rule*
  ("the bag's `wood_group` is Scanner's group name verbatim"), which is why a lower-casing
  implementation looked plausible and the test was written to it. Rule-17 rows should carry the rule
  next to the literal.
