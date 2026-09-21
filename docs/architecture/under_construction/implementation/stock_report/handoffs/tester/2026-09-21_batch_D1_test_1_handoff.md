---
batch: D1
plan: [12, 13]
role: test
round: 1
state: BLOCKED
date: 2026-09-21
actor: Opus tester (orchestrated subagent, slot `dt`)
---

# Batch D1 verification handoff — plans 12 and 13

**64 criterion rows in scope · 78 declared named mutations, 78 executed · 56 rows ARMED ·
2 UNFORCEABLE (the plan's own class-3 rows) · 3 EQUIVALENT · 1 BLOCKED-PRODUCTION ·
2 BLOCKED-PLAN** (56 + 2 + 3 + 1 + 2 = 64). The production diff against the implementer's
checkpoint is **empty**.

The batch does **not** pass to review as it stands: one row is `BLOCKED-PRODUCTION` (§3B returns
a handoff carrying one to the implementer first) and three are `BLOCKED-PLAN`. Everything else is
armed and the evidence is in the three tables below.

---

## ⚠ OWNER DECISIONS REQUIRED (5)

### Card 1 — changing a row's priority while work is out breaks the board's own health check

**Question.** May the consistency check's "goal total" rule be narrowed to goal records only
(a one-line change inside an already-approved part of the board), yes or no?

**Story.** A seller drags a row up the board while two chairs for it are already out with a
worker. From that moment the board's self-check reports a problem that does not exist, for that
row, forever. Worse, if anyone presses the repair button, the repair quietly rewrites the history
entry the drag created — the note that says how much work was outstanding when the priority
changed — to zero. Every priority change on a row with work in progress adds one more permanent
false alarm, and the checker is the thing you rely on to tell you the board is trustworthy.

**Branches.**
- *Narrow the rule to goal records:* the false alarm disappears, history entries stop being
  rewritten, one small change inside approved code plus a re-check of that phase.
- *Leave it:* the health check reports permanent phantom problems and the repair button destroys
  history the moment anyone uses it.
- *Stop recording how much was outstanding:* the health check goes quiet, but the history entry
  loses the number the intention says it must carry.

**Recommendation.** Narrow the rule to goal records — the board code is right, the checker is
reading a field that means two different things.

**On silence.** The gate holds: batch D1 does not reach review, the failing test stays red and
named, and nothing is changed in the approved phase.

**Trace.** Plan 12 C3(d), §9 rule 2; intention §6.1/§6.2/MC-6, §14C consistency table `goal_total`;
`consistency.py:compute_stock_report_divergences`, `repair_stock_report.py` `goal_total` branch.

### Card 2 — the safety instrument for the counter repair cannot actually fail

**Question.** Should the counter-repair instrument be re-stated around a defect it can observe,
or accepted as unguarded — and should the same question be put to phase 13A before D2 starts?

**Story.** One row in this batch exists purely as a tripwire: it is supposed to go red if someone
ever makes the counter repair read a stale copy of a number instead of re-reading it. I planted
exactly that defect, at both the place the plan names and the place the code actually lives, and
the tripwire stayed green both times — the database layer keeps the copy up to date by itself, so
the stale-copy mistake cannot happen here at all. A tripwire that cannot trip reads as coverage
and is worth less than none. The next batch's own tripwire for the deletion cascade rests on the
same assumption.

**Branches.**
- *Re-state it around an observable defect:* the tripwire earns its place; costs one criterion
  rewrite, which only you may author.
- *Accept it unguarded and record why:* honest, cheap, and the next reviewer stops looking for it.
- *Leave it as written:* the batch ships a row that reads as proof and is not.

**Recommendation.** Accept it unguarded and record why, then re-check 13A's equivalent row before
D2 — the production code is correct; only the proof is empty.

**On silence.** The gate holds; the row stays `BLOCKED-PLAN` and is not counted as covered.

**Trace.** Plan 13 C2(b), §7; §9 rule 3; intention MC-1 instrument (c); plan 13A C5(b).

### Card 3 — a criterion counts three deletions where its own fixture makes four

**Question.** Should the deletion-event row be corrected to four assignment-deleted events, yes
or by another number you name?

**Story.** The row that pins what the system announces when a board row is deleted says "three
assignments deleted". Its own setup, after a change made two rounds ago, creates four. Nothing is
broken in the product — the code announces four and the tests agree — but the written rule and the
thing it describes disagree, and the next person to re-derive the announcement from the rule will
build a four-event system against a three-event specification.

**Branches.**
- *Correct it to four:* the rule matches the setup again; five minutes; no code changes.
- *Change the setup back to three assignments:* undoes a deliberate round-9 addition.
- *Leave it:* the batch closes with a criterion that contradicts itself.

**Recommendation.** Correct it to four — the fourth assignment was added on purpose and the code
already handles it.

**On silence.** The gate holds: the row stays `BLOCKED-PLAN` and I authored no test against a
number I am not allowed to choose.

**Trace.** Plan 13 C3(a) vs C1(a)'s fixture; plan 13 §7 (rounds 8–9 note).

### Card 4 — "empty history" is not achievable for a re-created board row

**Question.** Does "a new live row with empty history" mean "inherits none of the deleted row's
history", yes or no?

**Story.** When a deleted board row's identity comes back from the scanner, a brand-new row is
created. The rule says that row should have an empty history. In practice the very delivery that
creates it also writes its first entry — the goal it was created with — so the history is never
literally empty, only free of anything belonging to the old row. The test I wrote asserts the
second reading and says so out loud rather than quietly adjusting the rule.

**Branches.**
- *Yes, it means "inherits nothing":* the wording is tightened, the test stands as written.
- *No, it means literally empty:* the rule can only be met by a delivery that asks for zero units,
  which is not how the scanner behaves.

**Recommendation.** Yes — "inherits nothing from the deleted row" is the only reading the product
can satisfy.

**On silence.** The gate holds on the wording; the row is armed and its test is green.

**Trace.** Plan 13 C1(c); intention §6.1 / MC-6 ("a goal record is written iff new > stored").

### Card 5 — nothing checks that the cascade empties a row before deleting it

**Question.** Do you want a criterion that proves the deletion cascade never marks a row deleted
before its assignments are moved out, yes or no?

**Story.** The deletion order is a written rule: empty the row first, delete it last. I planted
the forbidden order — mark the row deleted first — and every test stayed green, because nothing
downstream ever looks at the row's deleted flag while the cascade runs. So the rule is real, the
code follows it, and no evidence anywhere would notice if a future change stopped following it.

**Branches.**
- *Yes, add a criterion:* one new row you author; it would need an observable the code does not
  currently produce, so it may also need a small production seam.
- *No, record it as knowingly unguarded:* costs nothing now; a future reordering goes unnoticed.

**Recommendation.** No for this batch, recorded as knowingly unguarded — the seam does not exist
today and inventing one at the end of a sixteen-phase project is the expensive option.

**On silence.** The gate holds on the criterion; the mutation is recorded as an equivalent mutant
and the row is not claimed as proven by it.

**Trace.** Plan 13 C1(a) mutant (i); intention §5A MC-16 cascade order; plan 13 §7 final bullet.

---

## 1. Gate check (all green)

| Check | Result |
|---|---|
| Intention status | `RATIFIED` (round 9, 2026-09-19; round 10 additive, owner-ruled) |
| Tracker | phase 12 `IMPLEMENTED` (`568a1cb`), phase 13 `IMPLEMENTED` (`b6cbbb9`), batch D1 `TEST_PROMPT_READY` |
| `git status --porcelain` at start | clean |
| HEAD contains both checkpoints | yes; HEAD at dispatch `1a22263` |
| Docs-only since `b6cbbb9` | `git diff --name-only b6cbbb9 HEAD -- app/` → **0 files** (re-checked myself) |
| Implementer L4 stamp | 23 failed / 3739 passed / 1 skipped at `b6cbbb9`, ID diff empty both ways |

## 2. Counts, derived by command, never typed

**Criterion rows** — `python3 SR/count_criteria.py`: **plan 12 = 45 rows in 7 criteria**,
**plan 13 = 19 rows in 6 criteria**. 64 rows in scope. Agrees with the prompt.

**Declared named mutations** — derived by script from the §6 tables
(`scratchpad/declared.py`; counting rules printed with the output: a class-3 cell = 0; a
shorthand role group = one run per row, since each row is reddened by exactly one edit — three
"remove the role under test" for three reached cells plus one "add ROLE" for the 403 cell; an
explicit count word wins; else the `(i)/(ii)/(iii)` enumeration; else 1):

```
plan 12:  C1=18 + C2=1 + C3=5 + C4=11 + C5=2 + C6=2 + C7=12 = 51
plan 13:  C1=7  + C2=2 + C3=1 + C4=8  + C5=8 + C6=1        = 27
DECLARED TOTAL = 78        EXECUTED = 78        78 == 78
```

**My derivation disagrees with the prompt's upper bound of ~91, and per the prompt mine wins.**
The whole difference is the twelve role-cell rows whose cells say "both directions run and
recorded": the prompt counted two runs for each of those rows (+9 in plan 12, +4 in plan 13);
each row is reddened by exactly one edit, and running the opposite direction against a row it
cannot reach would be a second mutant of the same sign. Every reached cell's removal and every
403 cell's addition **was** run — the *set* is identical, only the arithmetic differs.

## 3. Ledger table 1 — mutations (run once, referenced many times)

Every run: landed inside the named symbol (asserted programmatically before the run), whole test
file (never `-k`), `git checkout` + `git diff --quiet` exit 0 after. Full transcript:
`scratchpad/ledger.log`. "Extra reds" lists reds outside the row's own test.

| M-id | Site (`file:symbol`, def / call-site) | Plan-named? (row) | Landed | Command (scope) | Observed red: test id → assertion | Reverted |
|---|---|---|---|---|---|---|
| M-01 | `_ordering.py:shift_within_group` (def.) — band `[t, p]` | 12 C1(a) | yes | L1 `test_stock_report_priority_and_ordering.py` | **not on C1(a)'s assertion**: state assertion passes; red at `test_move_up_shifts_only_the_block_it_enters` → C6(a)'s payload list (`[('high',4),…]`) | 0 |
| M-02 | `_ordering.py:shift_within_group` (def.) — band `[p, t]` | 12 C1(b) | yes | L1 ordering file | **green** (only the declared witness failed) | 0 |
| M-03 | `set_stock_report_item_priority_order.py` (def.) — delete the `t == p` short-circuit | 12 C1(c) | yes | L1 ordering file | `test_move_to_the_held_position_writes_nothing` → `_records(...) == []`. Extra red: C1(f)'s test | 0 |
| M-04 | same (def.) — guard `0 <= t <= n` | 12 C1(d) | yes | L1 ordering file | `test_target_outside_the_group_is_refused[0]` → DID NOT RAISE `ValidationError` | 0 |
| M-05 | same (def.) — guard `1 <= t <= n+1` | 12 C1(e) | yes | L1 ordering file | `…is_refused[5]` → DID NOT RAISE | 0 |
| M-06 | same (def.) — guard `1 <= t <= n−1` | 12 C1(f) | yes | L1 ordering file | `test_last_position_of_the_group_is_a_noop_not_a_refusal` → `STOCK_REPORT_TARGET_OUT_OF_RANGE: 4 is outside 1..4`. C1(d)/(e) stayed green, as the cell claims | 0 |
| M-07 | same (def.) — drop the `priority IS NULL` guard | 12 C1(g) | yes | L1 ordering file | `test_row_without_a_priority_cannot_be_ordered` → `TypeError` in `_ordering.py:109` instead of `ValidationError` | 0 |
| M-08 | `set_stock_report_item_priority.py` (def.) — append with the **source** priority | 12 C1(h)(i) | yes | L1 ordering file | `test_priority_change_closes_the_source_gap_and_appends` → `state[B] == ('low', 4) != ('low', 3)`. The D1 gate's replacement text, confirmed | 0 |
| M-09 | `_ordering.py:close_priority_gap` (def.) — never shift | 12 C1(h)(ii) | yes | L1 ordering + delete files | same test → `state[C] == ('high', 3) != ('high', 2)`. Cross-file red (§9 rule 8): plan 13 C1(b)'s test → `orders[C] 3 != 2` | 0 |
| M-10 | `set_stock_report_item_priority.py` (def.) — keep `priority_order` when the target is null | 12 C1(i) | yes | L1 ordering file | `test_priority_cleared_nulls_the_order_too` → `(None, 2) != (None, None)` | 0 |
| M-11 | `_ordering.py:append_to_priority_group` (def.) — `max` not `max+1` | 12 C1(j) | yes | L1 ordering file | `test_null_row_given_a_priority_is_appended_last` → `('high',4) != ('high',5)` | 0 |
| M-12 | `set_stock_report_item_priority.py` (def.) — delete `X == Y` | 12 C1(k) | yes | L1 ordering file | `…writes_nothing[B-high]` → state map changed. Extra red: `[N-None]` | 0 |
| M-13 | same (def.) — `if Y is not None and X == Y` | 12 C1(l) | yes | L1 ordering file | `…writes_nothing[N-None]` → `_records(...) == []`; `[B-high]` stays green (the other branch) | 0 |
| M-14 | `requests/__init__.py:SetStockReportItemPriorityRequest` (def.) — `str \| None` | 12 C1(m) | yes | L1 ordering file | `test_unknown_priority_token_is_a_validation_error` → asyncpg `invalid input value for enum … "urgent"` instead of `ValidationError`. Extra red: `[B-high]` | 0 |
| M-15 | `requests/__init__.py:SetStockReportItemPriorityOrderRequest` (def.) — plain `int` | 12 C1(n) | yes | L1 ordering file | `test_non_integer_target_is_a_validation_error` → DID NOT RAISE (lax coercion, rule 17 confirmed) | 0 |
| M-16a | `set_stock_report_item_priority.py:_find_row` (def.) — drop `workspace_id` | 12 C1(o)(i), first siting | yes | L1 ordering file | **green** — the post-lock re-read carries the same term | 0 |
| M-16 | …`_find_row` **and** `_lock_row_and_groups` (def.) — drop `workspace_id` | 12 C1(o)(i), re-sited | yes | L1 ordering file | `test_priority_lookup_refuses_foreign_deleted_and_absent_rows` red — the command **wrote the foreign workspace's row**, proven by the FK RESTRICT on `stock_report_items.updated_by_id` when W's users were purged | 0 |
| M-17a | `…:_find_row` (def.) — drop `is_deleted` | 12 C1(o)(ii), first siting | yes | L1 ordering file | **green** (same second sufficient cause) | 0 |
| M-17 | `_find_row` + `_lock_row_and_groups` + the `row.is_deleted` check (def.) | 12 C1(o)(ii), re-sited | yes | L1 ordering file | same test → DID NOT RAISE `NotFound` (soft-deleted cell) | 0 |
| M-18 | `_find_row` + the post-lock raise (def.) — return instead of raising | 12 C1(o)(iii) | yes | L1 ordering file | same test → DID NOT RAISE `NotFound` (absent cell) | 0 |
| M-19 | `set_stock_report_item_priority_order.py` (def.) — remove `acquire_stock_report_order_lock` | 12 C2(c) | yes | L1 `test_stock_report_ordering_locks.py` | `test_the_move_waits_for_the_workspace_ordering_lock` → DID NOT RAISE `TimeoutError`: the move completed while H held the lock | 0 |
| M-20 | `set_stock_report_item_priority.py` (def.) — insert the record twice | 12 C3(a)(i) | yes | L1 ordering file | `test_priority_change_closes_the_source_gap_and_appends` → `len(records) 2 != 1` | 0 |
| M-21 | same (def.) — `priority_order=None` in the record | 12 C3(a)(ii) | yes | L1 ordering file | same test → `record.priority_order None != 3` | 0 |
| M-22 | `_ordering.py:shift_within_group` (def.) — one `priority_order_change` per shifted row | 12 C3(b) | yes | L1 ordering file | `test_move_up_shifts_only_the_block_it_enters` → the records list (A and B appear) | 0 |
| M-23 | `set_stock_report_item_priority.py` **and** `…_order.py` (def.) — record before both short-circuits | 12 C3(c) | yes (both) | L1 ordering file | four no-op cells red on **their record-count assertions**: C1(c)'s test, C1(f)'s, `[B-high]`, `[N-None]` | 0 |
| M-24 | `set_stock_report_item_priority.py` (def.) — record built before the append/counter read | 12 C3(d) | yes | L1 ordering file | `test_the_priority_record_snapshots_the_live_awaiting_counter` → `records[0].priority_order None != 3` (C3(d)'s own clause), i.e. the test's failure point moves ahead of its already-red clean check. Extra red: C3(a)'s test | 0 |
| M-25 | `list_stock_report_items.py:_PRIORITY_RANK` (def.) — ranks in the column's text order | 12 C4(a) | yes | L1 `test_list_stock_report_items.py` | `test_read_order_is_high_medium_low_then_priority_order` → the id list | 0 |
| M-26 | `list_stock_report_items.py` (def.) — drop `priority IS NULL` | 12 C4(b)(i) | yes | L1 list file | `test_no_filter_lists_only_null_priority_rows_by_created_at` → `priced not in listed` | 0 |
| M-27 | same (def.) — null listing ordered by `client_id` only | 12 C4(b)(ii) | yes | L1 list file | same test → `listed == [N1, N2]` (the ordering clause) | 0 |
| M-28 | `…:_parse_priority_filter` (def.) — drop the membership check | 12 C4(c) | yes | L1 list file | `test_unknown_priority_token_is_refused` → asyncpg enum error, not `ValidationError` | 0 |
| M-29 | same (def.) — `priority=` treated as an unknown token | 12 C4(d) | yes | L1 list file | `test_no_filter_…` → the **empty-parameter** call raises 422; C4(b)'s two clauses stayed green | 0 |
| M-30 | `serializers.py:serialize_stock_report_item` (def.) — add `item_type` | 12 C4(e)(i) | yes | L1 list + ordering files | `test_row_shape_carries_the_four_key_category_including_a_null_image` → the row key-set map | 0 |
| M-31 | same (def.) — drop `properties_signature` | 12 C4(e)(ii) | yes | L1 list + ordering files | same test → the row key-set map | 0 |
| M-32 | same (def.) — drop `image_url` | 12 C4(e)(iii) | yes | L1 list file (full traceback) | same test → **both rows separately**: `{'Coffee Tables': …} != {'Coffee Tables': …, 'image_url', …}` **and** `{'Dining Chairs': …} != {'Dining Chairs': …, 'image_url', …}` | 0 |
| M-33 | `list_stock_report_items.py` (def.) — drop `is_deleted` | 12 C4(f)(i) | yes | L1 list file | `test_soft_deleted_and_foreign_rows_are_not_listed` → `listed == [live]` | 0 |
| M-34 | same (def.) — drop `workspace_id` | 12 C4(f)(ii) | yes | L1 list file | same test → the `priority=high` call returns the foreign row instead of `[]` | 0 |
| M-35 | same (def.) — category load filtered by `is_deleted` | 12 C4(g) | yes | L1 list file | `test_a_row_whose_category_was_soft_deleted_still_serializes_its_name` → `KeyError` on the category id | 0 |
| M-36 | `set_stock_report_item_priority.py` (def.) — stamp the shifted rows too | 12 C5(a) | yes | L1 ordering file | `test_priority_change_closes_the_source_gap_and_appends` → `other.updated_at is None, label` with **label `C`** | 0 |
| M-37 | `_ordering.py:shift_within_group` (def.) — stamp the rows the shift moved | 12 C5(b) | yes | L1 ordering + delete files | `test_move_up_shifts_only_the_block_it_enters` → A's `updated_at is None`. No extra red in the delete file | 0 |
| M-38 | `set_stock_report_item_priority_order.py` (def.) — one `:updated` per group row | 12 C6(a) | yes | L1 ordering file | **green** — see `EQUIVALENT` below | 0 |
| M-39a | same (def.) — dispatch before `t == p`, values from `row_values` | 12 C6(b), first siting | yes | L1 ordering file | red, but by `AttributeError` inside `_events.py` (the builder wants the enum member, `row_values` gives `.value`) — not the row's assertion; re-sited | 0 |
| M-39 | same (def.) — dispatch before `t == p`, enum-member values | 12 C6(b), re-sited | yes | L1 ordering file | `test_move_to_the_held_position_writes_nothing` → `captured == []` (the dispatch-list assertion) | 0 |
| M-40…M-43 | `routers/api_v1/stock_report.py:route_list_stock_report_items` `require_roles` (def.) — remove ADMIN / MANAGER / WORKER / SELLER | 12 C7(i)…C7(l) | yes ×4 | L1 `test_stock_report_router.py` ×4 | `test_list_items_route_reaches_service_for_every_role[admin]` / `[manager]` / `[worker]` / `[seller]`, one cell each | 0 ×4 |
| M-44…M-46 | `…:route_set_stock_report_item_priority` `require_roles` (def.) — remove ADMIN / MANAGER / SELLER | 12 C7(a), C7(b), C7(d) | yes ×3 | L1 router ×3 | `test_ordering_routes_reach_service_for_permitted_roles[…/priority-body0-admin]` / `-manager]` / `-seller]` | 0 ×3 |
| M-47 | same (def.) — **add WORKER** (opposite direction) | 12 C7(c) | yes | L1 router | `test_ordering_routes_reject_worker[…/priority-body0]` | 0 |
| M-48…M-50 | `…:route_set_stock_report_item_priority_order` `require_roles` (def.) — remove ADMIN / MANAGER / SELLER | 12 C7(e), C7(f), C7(h) | yes ×3 | L1 router ×3 | `…[…/priority-order-body1-admin]` / `-manager]` / `-seller]` | 0 ×3 |
| M-51 | same (def.) — **add WORKER** | 12 C7(g) | yes | L1 router | `test_ordering_routes_reject_worker[…/priority-order-body1]` | 0 |
| M-52, M-53 | `…:route_delete_stock_report_item` `require_roles` (def.) — remove ADMIN / MANAGER | 13 C5(a), C5(b) | yes ×2 | L1 router ×2 | `test_delete_item_route_reaches_service_for_admin_and_manager[admin]` / `[manager]` | 0 ×2 |
| M-54, M-55 | same (def.) — **add WORKER / add SELLER** | 13 C5(c), C5(d) | yes ×2 | L1 router ×2 | `test_delete_item_route_rejects_worker_and_seller[worker]` / `[seller]` | 0 ×2 |
| M-56…M-59 | `…:route_list_stock_task_assignments` `require_roles` (def.) — remove ADMIN / MANAGER / WORKER / SELLER | 13 C5(e)…C5(h) | yes ×4 | L1 router ×4 | `test_list_assignments_route_reaches_service_for_every_role[…]`, one cell each | 0 ×4 |
| M-60 | `_delete_stock_report_item_cascade.py` (def.) — soft-delete the row before the loop | 13 C1(a)(i) | yes | L1 `test_delete_stock_report_item.py` | **green** — see `EQUIVALENT` below | 0 |
| M-61 | `_goal_credit.py:apply_goal_effect` (def.) — **foreign site**, uncredit `resolved_early → DELETE` | 13 C1(a)(ii) | yes | L1 delete file | `test_cascade_removes_every_assignment_and_soft_deletes_the_row` → `G 3 != 8` | 0 |
| M-62 | `_delete_stock_report_item_cascade.py` (def.) — `removed_order − 1` (the deleted row inside the band) | 13 C1(b) | yes | L1 delete + ordering files | `test_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order` → `orders[R] 1 != 2` | 0 |
| M-63 | `_demand_lookup.py:discover_live_rows_by_identity` (def.) — drop `is_deleted` | 13 C1(c) | yes | L1 delete file | `test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` red: the delivery finds the soft-deleted row and then `apply_stock_demand` raises *"stock demand identity vanished under lock"* (the locked read still filters), so no new row is ever produced | 0 |
| M-64 | `delete_stock_report_item.py:_lock_row_and_group` + the `row.is_deleted` check (def.) — drop `is_deleted` | 13 C1(d)(i) | yes | L1 delete file | `test_delete_refuses_deleted_absent_and_foreign_rows` → DID NOT RAISE (deleted cell) | 0 |
| M-65 | `…:_lock_row_and_group` (def.) — drop `workspace_id` | 13 C1(d)(ii) | yes | L1 delete file | same test → DID NOT RAISE (foreign cell) | 0 |
| M-66 | `…:delete_stock_report_item` post-lock raise (def.) — return `{"client_id": …}` | 13 C1(d)(iii) | yes | L1 delete file | same test → DID NOT RAISE (all three cells) | 0 |
| M-67 | `_delete_stock_report_item_cascade.py` (def.) — raise instead of repairing | 13 C2(a) | yes | L1 delete file | `test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded` → `RuntimeError: … has a non-zero quantity_in_queue` | 0 |
| M-68 | `_delete_stock_report_item_cascade.py` (def., **the named site**) — `stored_before` from the ORM instance | 13 C2(b) | yes | L1 delete file | **green** | 0 |
| M-69 | `_move_assignment.py:_apply_counter_delta` (def., **the real site**) — `stored_before` from the ORM instance | 13 C2(b), re-sited | yes | L1 delete file | **green** — see `BLOCKED-PLAN` below | 0 |
| M-70 | `_delete_stock_report_item_cascade.py` **pair** `_events.py:coalesce_stock_report_events` (def.) | 13 C3(a) | yes (both) | L1 delete file | `test_cascade_…` → `'stock_report_item:updated' not in names`; `test_the_group_closes_…` → the exact ordered event list | 0 |
| M-71 | `list_stock_task_assignments.py` (def.) — filter to `ACTIVE_ASSIGNMENT_STATES` | 13 C4(a)(i) | yes | L1 `test_list_stock_task_assignments.py` | `test_every_non_deleted_state_is_listed_…` → `set(ids)` loses A2 and A4 | 0 |
| M-72 | same (def.) — hand-typed five-state list | 13 C4(a)(ii) | yes | L1 assignments file | same test → only A4 vanishes: the §9 rule 16 defect the row exists for | 0 |
| M-73 | `serializers.py:serialize_stock_task_assignment` (def.) — drop `credited_history_record_id` | 13 C4(b)(i) | yes | L2 radius ×3 files | **cross-suite red set:** `test_list_stock_task_assignments.py::…fourteen_key_shape…`, phase 8's `test_stock_report_serializers.py::…fourteen_keys…`, phase 8's `test_create_stock_task_assignments.py::…full_read_shape` | 0 |
| M-74 | `serializers.py:serialize_item_compact` (def.) — add `item_category_id` | 13 C4(b)(ii) | yes | L2 radius | red set: the list test + phase 8's `…item_compact_returns_exact_key_set_and_images`; the create test stays green | 0 |
| M-75 | `serializers.py:serialize_task_compact` (def.) — drop `completed_at` | 13 C4(b)(iii) | yes | L2 radius | red set: the list test + phase 8's `…task_compact_returns_exact_key_set_and_enum_values`; the create test stays green | 0 |
| M-76 | `list_stock_task_assignments.py` row lookup (def.) — drop `is_deleted` | 13 C4(d)(i) | yes | L1 assignments file | `test_the_row_lookup_refuses_deleted_absent_and_foreign_rows` → DID NOT RAISE | 0 |
| M-77 | same (def.) — drop `workspace_id` | 13 C4(d)(ii) | yes | L1 assignments file | same test → DID NOT RAISE | 0 |
| M-78 | same (def.) — return `[]` instead of raising | 13 C4(d)(iii) | yes | L1 assignments file | same test → DID NOT RAISE | 0 |
| M-79 | `list_stock_task_assignments.py` (def.) — element built inline, one key dropped | 13 C6(a) | yes | L2 radius ×3 files | `test_the_create_and_list_surfaces_return_the_same_key_set` → the key-set comparison, **and phase 8's two files stay green** — the half the cell exists for | 0 |

**Runs that are not part of the declared set** (listed separately so the arithmetic stays clean):

| id | Purpose | Result | Reverted |
|---|---|---|---|
| P-1 | Proposed replacement for 12 C1(a): `low=to_order + 1` | red at `test_move_up_shifts_only_the_block_it_enters` → C1(a)'s **state** assertion | 0 |
| P-2 | Proposed replacement for 12 C1(b): `high=to_order − 1` | red at `test_move_down_shifts_only_the_block_it_leaves` → C1(b)'s state assertion | 0 |
| P-3 | Proposed replacement for 12 C6(a): neighbours sorted by `client_id` | red at `test_move_up_…` → C6(a)'s event-list assertion | 0 |
| D-1 | Diagnostic probe in `_apply_counter_delta`: print the ORM value vs a fresh `SELECT` at the moment `stored_before` is read | `PROBE ORM_in_queue=1 FRESH_in_queue=1 expired=False identity_map_has=True` — the identity-mapped instance is **already synchronised** | 0 |

## 4. Ledger table 2 — rows (the forward coverage map)

Test ids are abbreviated to the function name; files: **O** = `test_stock_report_priority_and_ordering.py`,
**L** = `test_stock_report_ordering_locks.py`, **I** = `test_list_stock_report_items.py`,
**D** = `test_delete_stock_report_item.py`, **A** = `test_list_stock_task_assignments.py`,
**R** = `test_stock_report_router.py`.

### Plan 12 — 45 rows

| Row | Observable (boundary → exact outcome) | Test id | Source | What it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | `SO(C,1)` → high `A2 B3 C1 D4` | O `test_move_up_shifts_only_the_block_it_enters` | existing | — | M-01 (equivalent), P-1 (proposal) | **EQUIVALENT** — the mover's own `UPDATE` overwrites whatever the band did to it, so widening the band to `[t, p]` leaves the disk state identical; the row's own assertion never fires |
| C1(b) | `SO(A,3)` → high `B1 C2 A3 D4` | O `test_move_down_shifts_only_the_block_it_leaves` | existing | — | M-02 (equivalent), P-2 | **EQUIVALENT** — same mechanism, and this test captures no events, so the mutant is invisible everywhere |
| C1(c) | `SO(B,2)` → unchanged, no record, no event, no stamp, `count_writes == 0` | O `test_move_to_the_held_position_writes_nothing` | **strengthened** | the fifth clause (`count_writes` on the four tables) was not asserted at all | M-03 | ARMED |
| C1(d) | `SO(A,0)` → 422 `STOCK_REPORT_TARGET_OUT_OF_RANGE:`, state unchanged | O `…is_refused[0]` | existing | — | M-04 | ARMED |
| C1(e) | `SO(A,5)` → same 422 | O `…is_refused[5]` | existing | — | M-05 | ARMED |
| C1(f) | `SO(D,4)` → no-op | O `test_last_position_of_the_group_is_a_noop_not_a_refusal` | existing | — | M-06 | ARMED |
| C1(g) | `SO(N,1)` → 422 `STOCK_REPORT_ROW_HAS_NO_PRIORITY:` | O `test_row_without_a_priority_cannot_be_ordered` | existing | — | M-07 | ARMED |
| C1(h) | `SP(B,low)` → high `A1 C2 D3`, low `X1 Y2 B3` | O `test_priority_change_closes_the_source_gap_and_appends` | existing | — | M-08, M-09 | ARMED (both runs recorded) |
| C1(i) | `SP(B,null)` → high `A1 C2 D3`, B `(null,null)` | O `test_priority_cleared_nulls_the_order_too` | existing | — | M-10 | ARMED |
| C1(j) | `SP(N,high)` → high `A1 B2 C3 D4 N5` | O `test_null_row_given_a_priority_is_appended_last` | existing | — | M-11 | ARMED |
| C1(k) | `SP(B,high)` → unchanged, no record, no event, zero writes | O `…writes_nothing[B-high]` | **strengthened** | the zero-writes clause | M-12 | ARMED |
| C1(l) | `SP(N,null)` → unchanged, no record, no event | O `…writes_nothing[N-None]` | **strengthened** | the zero-writes clause | M-13 | ARMED |
| C1(m) | `SP(B,"urgent")` → 422 | O `test_unknown_priority_token_is_a_validation_error` | existing | — | M-14 | ARMED |
| C1(n) | `SO(B,"2")` → 422 | O `test_non_integer_target_is_a_validation_error` | existing | — | M-15 | ARMED |
| C1(o) | foreign / soft-deleted / absent → `NotFound` each; the foreign group byte-identical | O `test_priority_lookup_refuses_foreign_deleted_and_absent_rows` | existing | — | M-16a+M-16, M-17a+M-17, M-18 | ARMED (all three; re-sited, both sitings recorded) |
| C2(a) | two barrier-released moves → high dense `1..4` and one of the two sequential compositions | — | — | — | — | **UNFORCEABLE** — the plan's class-3 ruling. Reviewer's structural check: *after either serialisation the `high` group is exactly `1..4` with no gap and no duplicate and the state equals one of the two sequential compositions*. No test exists and none was added |
| C2(b) | `SO(A,3)` vs `SP(N,high)` → high dense `1..5`, N last | — | — | — | — | **UNFORCEABLE** — same ruling; structural check as the cell states |
| C2(c) | a held advisory lock blocks the move for 0.5 s, then it completes with high `A2 B3 C1 D4` | L `test_the_move_waits_for_the_workspace_ordering_lock` | existing | — | M-19 | ARMED — two real sessions, order forced by lock acquisition, every wait bounded; with the lock removed the move completes, i.e. the test genuinely forces the contention |
| C3(a) | `SP(B,low)` → exactly one `priority_change` with all eight fields | O `test_priority_change_closes_the_source_gap_and_appends` | existing | — | M-20, M-21 | ARMED (both runs) |
| C3(b) | `SO(C,1)` → one `priority_order_change` for C, none for A or B | O `test_move_up_shifts_only_the_block_it_enters` | existing | — | M-22 | ARMED |
| C3(c) | the three no-ops → zero new records | O ×4 no-op tests | existing | — | M-23 | ARMED (the run is recorded against **this** row's record-count assertion in all four) |
| C3(d) | `SP(B,low)` with B's `quantity_awaiting = 4` → record `quantity_awaiting == 4`, `priority_order == 3` | O `test_the_priority_record_snapshots_the_live_awaiting_counter` | **new** | the only row that gives the mover a non-zero live counter, so the record's counter clause is discriminating at all; §9 rule 2 then forces the clean check that fails | M-24 | **BLOCKED-PRODUCTION** — see §6 and owner card 1 |
| C4(a) | `priority=high,medium,low` → `[A,B,C,D,M,X,Y]`, no pagination key | I `test_read_order_is_high_medium_low_then_priority_order` | existing | — | M-25 | ARMED |
| C4(b) | no `priority` → `[N1,N2]` only, by `created_at, client_id` | I `test_no_filter_lists_only_null_priority_rows_by_created_at` | **strengthened (fixture)** | the back-dated row is now chosen from the sorted real ids, so `created_at` asc is **guaranteed** to disagree with `client_id` asc; before, the two agreed on roughly a third of runs and mutant (ii) was inert on those | M-26, M-27 | ARMED (both runs) |
| C4(c) | `priority=urgent` → 422 `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER:` | I `test_unknown_priority_token_is_refused` | existing | — | M-28 | ARMED |
| C4(d) | `priority=` → nulls only | I `test_no_filter_…` (the empty-parameter block) | existing | — | M-29 | ARMED — C4(b)'s mutants leave this clause green and M-29 leaves C4(b)'s green, measured both ways |
| C4(e) | the fourteen row keys, `item_category` exactly four keys incl. `image_url` present-and-`None` | I `test_row_shape_carries_the_four_key_category_including_a_null_image` | **strengthened** | both fixture rows' key sets are now compared in one mapping assertion, so the `image_url` mutant shows **both** reddenings in one run instead of aborting on whichever row sorts first | M-30, M-31, M-32 | ARMED (all three runs) |
| C4(f) | a soft-deleted row and a foreign row are not listed | I `test_soft_deleted_and_foreign_rows_are_not_listed` | existing | — | M-33, M-34 | ARMED (both runs) |
| C4(g) | a row whose category is soft-deleted still lists with the category's name | I `test_a_row_whose_category_was_soft_deleted_still_serializes_its_name` | existing | — | M-35 | ARMED |
| C5(a) | `SP(B,low)` → B stamped `(S, ctx.now)`; A, C, D, X, Y unchanged | O `test_priority_change_closes_the_source_gap_and_appends` | **strengthened** | only C was asserted; A, D, X, Y and the mover's `updated_at` were not | M-36 | ARMED |
| C5(b) | `SO(C,1)` → C stamped; A, B not | O `test_move_up_shifts_only_the_block_it_enters` | **strengthened** | B (the second shifted row) was not asserted | M-37 | ARMED |
| C6(a) | `SO(C,1)` → exactly three `:updated` (C, A, B) with post-move payloads; none for D | O `test_move_up_shifts_only_the_block_it_enters` | **strengthened** | the payload clause was asserted for the mover only; all three are now asserted | M-38 (equivalent), P-3 | **EQUIVALENT** — `coalesce_stock_report_events` drops an `:updated` whose payload equals the row's initial values, so a spurious event for D never reaches the dispatch list; the named mutant is absorbed by a second sufficient cause in production |
| C6(b) | the `t == p` no-op dispatches nothing | O `test_move_to_the_held_position_writes_nothing` | existing | — | M-39a + M-39 | ARMED (re-sited; both runs recorded) |
| C7(a)–C7(d) | `PATCH …/priority` as admin / manager / worker / seller → reached / reached / 403 / reached | R `test_ordering_routes_reach_service_for_permitted_roles[…]` ×3, `test_ordering_routes_reject_worker[…priority…]` | existing | — | M-44, M-45, M-47, M-46 | ARMED ×4 (both directions run) |
| C7(e)–C7(h) | `PATCH …/priority-order`, same four cells | R same two functions, the `priority-order` parameters | existing | — | M-48, M-49, M-51, M-50 | ARMED ×4 |
| C7(i)–C7(l) | `GET …/items` reached ×4 | R `test_list_items_route_reaches_service_for_every_role[…]` ×4 | existing | — | M-40…M-43 | ARMED ×4 |

### Plan 13 — 19 rows

| Row | Observable (boundary → exact outcome) | Test id | Source | What it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | `DR(R)` over four assignments → all soft-deleted by U, `G == 8`, counters `(0,0,0)`, four task flags false, every history record soft-deleted, R's `deleted_*` **and** `updated_*` = (U, ctx.now) | D `test_cascade_removes_every_assignment_and_soft_deletes_the_row` | existing | — | M-60 (equivalent), M-61 | **partly ARMED** — mutant (ii) bites; mutant (i) is `EQUIVALENT` (owner card 5). Recorded as ARMED on the credit/stamp clauses, with MC-16's ordering clause unguarded |
| C1(b) | high `A1 R2 C3`, `DR(R)` → high `A1 C2`, R keeps `high 2` on its deleted row | D `test_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order` | existing | — | M-62 | ARMED |
| C1(c) | after (a), a demand delivery with R's identity → a **new** live row, no inherited history | D `test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` | **new (replaces a narrower probe of the same id)** | the old test asserted only that `discover_live_rows_by_identity` returns `{}` — the premise, not the row; this one runs a real delivery at the surface the cell names (§9 rule 17) | M-63 | ARMED — with owner card 4 on the literal "empty history" |
| C1(d) | deleted / absent / foreign → `NotFound` each, nothing written | D `test_delete_refuses_deleted_absent_and_foreign_rows` | existing | — | M-64, M-65, M-66 | ARMED (all three cells; each mutant bites its own visibility cell) |
| C2(a) | drifted `quantity_in_queue` → repaired to 0 after the loop with one record, deletion proceeds | D `test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded` | existing | — | M-67 | ARMED |
| C2(b) | instrument (c): one inline repair record with `stored "1"`, no second-trigger record | D `test_instrument_c_reads_stored_before_fresh_after_the_guarded_statement` | existing | — | M-68 (named site), M-69 (real site) | **BLOCKED-PLAN** — green at both sites; the instrument cannot fail. See §6 and owner card 2 |
| C3(a) | the dispatched list: one `:deleted` for R, one per assignment, one `:updated` for C, none for R | D `test_the_group_closes_…` (the exact list) + D `test_cascade_…` (the counts and the absence) | existing | — | M-70 | **BLOCKED-PLAN** — the cell's "three `stock_task_assignment:deleted`" contradicts its own four-assignment fixture, and no single test combines that fixture with the priority group. Owner card 3. The mutant was run and reddens both tests |
| C4(a) | all non-deleted states listed by `created_at, client_id`; A4 `resolved_early`; A3 absent | A `test_every_non_deleted_state_is_listed_in_created_at_client_id_order` | existing | — | M-71, M-72 | ARMED (both runs) |
| C4(b) | the fourteen element keys, seven item keys, twelve task keys, `item_images` of `serialize_image_light` shape | A `test_the_element_is_the_fourteen_key_shape_with_its_two_nested_objects` | **strengthened (fixture)** | a real linked image, so the `item_images` element-type clause is exercised instead of satisfied by `[]` | M-73, M-74, M-75 | ARMED (all three; cross-suite red sets recorded) |
| C4(d) | deleted / absent / foreign → `NotFound` each, never `[]` | A `test_the_row_lookup_refuses_deleted_absent_and_foreign_rows` | existing | — | M-76, M-77, M-78 | ARMED (all three) |
| C5(a)–C5(d) | `DELETE …/items/{id}` as admin / manager / worker / seller → reached / reached / 403 / 403 | R `test_delete_item_route_reaches_service_for_admin_and_manager[…]` ×2, `…rejects_worker_and_seller[…]` ×2 | existing | — | M-52…M-55 | ARMED ×4 (both directions) |
| C5(e)–C5(h) | `GET …/assignments` reached ×4 | R `test_list_assignments_route_reaches_service_for_every_role[…]` ×4 | existing | — | M-56…M-59 | ARMED ×4 |
| C6(a) | the create response element and the list element carry the same key set | A `test_the_create_and_list_surfaces_return_the_same_key_set` | existing | — | M-79 | ARMED — and phase 8's own key rows stay green under the mutant, which is the clause that makes the row about the *agreement* |

### Disposition arithmetic

```
plan 12:  ARMED 39  +  UNFORCEABLE 2  +  EQUIVALENT 3  +  BLOCKED-PRODUCTION 1              = 45 rows
plan 13:  ARMED 17  +  EQUIVALENT 0*  +  BLOCKED-PLAN 2                                     = 19 rows
          (* plan 13 C1(a) carries one equivalent mutant but is counted ARMED on its other clauses)
total  :  56 ARMED + 2 UNFORCEABLE + 3 EQUIVALENT + 1 BLOCKED-PRODUCTION + 2 BLOCKED-PLAN   = 64 rows
```

64 = 45 + 19, the script's own totals.

## 5. Ledger table 3 — removed or consolidated tests

| Test id | Why redundant | Survivor | Survivor reddened under M-id |
|---|---|---|---|
| — | — | — | — |

**Nothing was deleted.** `test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row`
was **rewritten in place** (same id, same file) from a lookup-level probe to plan 13 C1(c)'s own
surface, so no id disappears and no pass count moves for a deletion. The five tests the
implementer declared as candidate criteria were left untouched, per the prompt.

### The reverse map (test → row), derived by `--collect-only`

The five integration files in scope collect **34 test ids** (32 functions; two are parametrized
into two ids each). Table 2 references **33** of them. The one not referenced is
`test_a_row_with_no_assignments_answers_an_empty_list`, which the implementer declared a
**candidate criterion** and the prompt told me to keep and not credit. No orphan.

`test_stock_report_router.py` gained **27** ids in this batch: 20 are the C7 and C5 role cells
(12 + 8, one id per cell), 3 are `test_ordering_routes_refuse_malformed_bodies[…]` — HTTP-scope
coverage of C1(m)/C1(n), whose cells site their mutation in `requests/__init__.py` and are armed
at command scope, so these three are not credited against a row either — and 4 are the declared
candidate criteria. 20 + 3 + 4 = 27.

**Pass-count delta = new − removed = 1 − 0 = 1**, and the one new test is the
`BLOCKED-PRODUCTION` witness, which fails — so the pass count stays at the implementer's **3739**
and the failure count rises by exactly one. Reconciled against the run below.

## 6. The four hard-evidence items, each answered

### 6.1 The requirement no row in scope can test — the cascade's fresh `removed_order`

**Read, not run, as instructed.** `cascade_delete_stock_report_item` takes `removed_order` from a
fresh `SELECT` of `(priority, priority_order)`, not from the ORM instance:

`app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py:146-163`

```python
    position = (
        (
            await session.execute(
                select(
                    StockReportItem.priority, StockReportItem.priority_order
                ).where(StockReportItem.client_id == row.client_id)
            )
        )
        .mappings()
        .one()
    )
    if position["priority"] is not None:
        shifted = await close_priority_gap(
            session,
            workspace_id=workspace_id,
            priority=position["priority"],
            removed_order=position["priority_order"],
        )
```

The requirement is satisfied as written: `row.priority_order` is never used for the gap close.

**A caveat for D2 that I did not expect to find, measured on this tree.** §9 rule 3's premise —
"an ORM instance is stale after any Core UPDATE of the same row in the same transaction" — does
**not** hold for this codebase's counter and shift statements. They are ORM-enabled
`update(StockReportItem)` statements executed through `session.execute`, so SQLAlchemy 2.0
synchronises the identity-mapped instance (`synchronize_session="auto"` → `fetch`, because the
statements carry `RETURNING`). Probe D-1 in table 1 shows the ORM attribute and a fresh `SELECT`
answering the same value at exactly the point the repair reads it. The practical consequence:
**13A C5(b), the only armed evidence anywhere for this requirement, is likely to be inert for the
same reason C2(b) is** — `close_priority_gap`'s UPDATE matches the neighbour rows and therefore
refreshes their instances, so a second cascade call in the same transaction would read a current
`priority_order` from the ORM as well. Worth settling before D2 is dispatched (owner card 2).

### 6.2 The cascade must never reach for `ctx`

**Clean.** Parsed the module's AST: zero `ctx`-like `Name` or `Attribute` nodes, and its import
list contains no context type —

```
ctx-like identifiers: []
imports: ['__future__', 'beyo_manager.domain.stock_report.enums',
 'beyo_manager.models.tables.stock_report.stock_report_history_record',
 'beyo_manager.models.tables.stock_report.stock_report_item',
 'beyo_manager.models.tables.stock_report.stock_task_assignment',
 'beyo_manager.services.commands.stock_report._events',
 'beyo_manager.services.commands.stock_report._ordering',
 'beyo_manager.services.commands.stock_report._remove_assignment',
 'beyo_manager.services.commands.stock_report._repair_records',
 'beyo_manager.services.infra.events.domain_event', 'sqlalchemy']
```

The only occurrences of the string `ctx` in the file are in its docstring. Phase 13A's
`actor_user_id=None, trigger="stock_demand_deleted"` call is structurally available; nothing in
this batch exercises it, by design.

### 6.3 The owner's row — plan 12 C4(e), `item_category.image_url`

`ItemCategory.image_url` is `Mapped[str | None]`, `String(1024)`, nullable
(`item_category.py:23`); the serializer emits it unconditionally
(`serializers.py:serialize_stock_report_item`, the `item_category` block, four keys).

The test carries both fixture rows — a category with an image and one with `NULL` — and I changed
its two key-set assertions into mapping comparisons keyed by category name, because a `for row in
rows` loop aborts on whichever row the read order returns first and can therefore show only one
reddening. **Mutant (iii), run on this tree, reddens both rows and reports them separately:**

```
E   AssertionError: assert {'Coffee Tabl...ory', 'name'}} == {'Coffee Tabl...ory', 'name'}}
E     Differing items:
E     {'Coffee Tables': {'client_id', 'major_category', 'name'}} != {'Coffee Tables': {'client_id', 'image_url', 'major_category', 'name'}}
E     {'Dining Chairs': {'client_id', 'major_category', 'name'}} != {'Dining Chairs': {'client_id', 'image_url', 'major_category', 'name'}}
1 failed, 5 passed
```

The `None` row is asserted twice over: its key set above, and `assert "image_url" in …` plus
`… is None` on the Coffee Tables row. The orchestrator's two hand-run observations were **not**
consumed: editing this file for C4(b)'s fixture expired them (L-23), so all three C4(e) mutants
were re-run at the new surface. Mutants (i) and (ii) were mine to run in any case.

### 6.4 The `_row_values` consolidation is provably inert

- The implementer's diff (`git diff --name-only 6aed93f b6cbbb9 -- app/`) touches the three
  donor **production** modules (`create_stock_task_assignments.py`, `sync_task_stock_assignments.py`,
  `delete_stock_task_assignments.py`) and **no donor test file**. The full list is 14 production
  files and 6 test files, all of them this batch's own.
- All three donors' suites are green inside my L2 run (**1 failed, 696 passed** — the one failure
  is the declared witness), with no edit to any of them.
- The registry trap is honoured: `_row_values.py:25` emits
  `"priority": row.priority.value if row.priority is not None else None`, never the enum member,
  which is what `coalesce_stock_report_events` compares against.

## 7. The two notes the prompt asked me to answer

**The cascade's two fresh `SELECT`s filter on `client_id` only — I agree it is safe today, and I
would still add the term.** Safe: the caller has already resolved and locked the row by
`workspace_id`, and `client_id` is a prefixed ULID, so no other workspace can own that id. My
reservation is not about today's reachability — it is that `cascade_delete_stock_report_item`
**takes `workspace_id` as an argument and already uses it** for `close_priority_gap` and for the
repair records, while four statements in the same function (the counters `SELECT`, the `position`
`SELECT`, the row soft-delete `UPDATE`, the history soft-delete `UPDATE`) do not. A reader cannot
tell which omissions are deliberate, and this is the exact shape batch B1 repaired in
`set_task_stock_flag`. Not changed, not a card — a one-line note for the coordinator.

**C4(a) of plan 12 is a row with a demonstrated ability to fail.** Recorded as asked: the
implementer's first `case({...}, value=…)` form made every `priority=` request a 500, and this
row's test is what caught it before review. Its mutation (M-25) reddens it a second time on a
different defect.

## 8. What I could have hidden and am reporting

1. **I spent one avoidable full-suite run.** My first L4 was taken correctly but I piped its
   output through `tail -4` and lost the failing-ID list, and pytest's `lastfailed` cache was
   polluted by the mutation campaign. I re-ran the suite to capture the IDs. The two runs are on a
   byte-identical `app/` tree (diff digest `2f1ff5889344cdb7` both times) and returned identical
   totals; only the second is cited. ~75 seconds, and it is the exact anti-pattern the charter's
   over-evidence rule names.
2. **Three declared mutants turned out inert, and one of them was only visible because of an
   assertion I had added minutes earlier.** C1(a)'s mutant reddens the payload clause I added to
   C6(a); had I not strengthened that assertion, I would have recorded C1(a) as ARMED on a red
   that has nothing to do with C1(a). I nearly did.
3. **My first attempt at C6(b)'s mutant crashed instead of biting** (it passed `row_values`'
   string `priority` into a builder that wants the enum member) and I recorded a red that was not
   the row's assertion before noticing. Both runs are in table 1.
4. **My first C1(o) and C2(b) sitings were the ones the cells name, and both were inert.** I could
   have reported the re-sited runs only and shown three clean bites.
5. **I changed a fixture in the implementer's list test.** C4(b)'s pair of null rows agreed on
   `created_at` and `client_id` order about a third of the time, so the cell's second mutant was
   inert on those runs — a flaky *arming*, invisible in a green suite. The plan's fixture cell
   already demands the disagreement; I implemented it, I did not invent it.
6. **C3(d)'s witness test is red on the tree I am handing over, on purpose.** I could have
   dropped the `assert_stock_report_clean` line and shipped a green suite with a row that passes
   and a product that reports phantom drift forever.
7. **Two clauses I did not close.** Plan 12 C2(a)/C2(b) have no test at all (the plan's class-3
   ruling, and the prompt told me not to try) — so the "density under a real race" half of MC-7 is
   unproven by anything in this batch, exactly as the plan says. And plan 13 C3(a)'s "one
   `:updated` for C **alongside** four assignment deletions" composition is proven by two tests
   with different fixtures, never by one.

## 9. Candidate criteria (not mine to fold)

Carried forward unchanged from the implementer, none credited against any row in scope and none
deleted: `test_ordering_routes_refuse_unknown_fields` (×2),
`test_list_items_route_passes_no_priority_when_the_param_is_absent`,
`test_priority_route_accepts_an_explicit_null`, `test_a_row_with_no_assignments_answers_an_empty_list`.

I add none of my own.

## 10. Proposed plan-cell backfills (mutation cells only — the coordinator folds them)

| Cell | Current text | Proposed replacement | Verified |
|---|---|---|---|
| 12 C1(a) | `shift_within_group`: shift `[t, p]` instead of `[t, p−1]` | `shift_within_group` (def.): shift `[t+1, p−1]` instead of `[t, p−1]` (raise the band's **lower** bound) → A is never moved, so C lands on an occupied 1 and `order_density` diverges | **P-1, red on C1(a)'s own state assertion** |
| 12 C1(b) | `shift_within_group`: shift `[p, t]` instead of `[p+1, t]` | `shift_within_group` (def.): shift `[p+1, t−1]` (lower the band's **upper** bound) → C is never moved and A lands on an occupied 3 | **P-2, red on C1(b)'s own state assertion** |
| 12 C6(a) | one `:updated` per group row instead of per shifted row | `set_stock_report_item_priority_order.py` (def.): order the neighbour events by `client_id` instead of by their new `priority_order` → the fixture pins the two orderings against each other, so the list comes back `(C, B, A)` | **P-3, red on C6(a)'s own event-list assertion** |

Rationale for all three: the mover's own `UPDATE … RETURNING` overwrites its `priority_order`
after the shift, and `coalesce_stock_report_events` drops an unchanged `:updated` — two production
mechanisms that absorb the currently-named mutants. Same class as L-37 and as the C1(h)(i) cell
the D1 gate already replaced.

Plan 13 C1(a) mutant (i) has **no** proposed replacement: no observable in this phase distinguishes
the cascade's ordering. Owner card 5.

## 11. The one L4 stamp

**Hypothesis:** the tree I hand over does not move the enumerated baseline except by the rows I
declare. **Scope:** L4 (the cycle-closing stamp).
**Tree identity:** `HEAD = 1a22263`, working tree carrying only my declared perimeter,
`git diff -- app/` digest `2f1ff5889344cdb7` (`shasum -a 256`, first 16).
**Command:** `cd app && BEYO_TEST_SLOT=dt PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q`
**Result:** **24 failed / 3739 passed / 1 skipped**, 75 s.

**Failure-ID diff against `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`
(23 IDs, comments stripped), both directions:**

```
=== in mine, not in the baseline ===
tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py::test_the_priority_record_snapshots_the_live_awaiting_counter

=== in the baseline, not in mine ===
(empty)
```

The one new ID is the declared `BLOCKED-PRODUCTION` witness for plan 12 C3(d) (§6 and owner card
1). All 23 baseline IDs are present, including the two slot-sensitive
`test_database_isolation.py` ids §10's ruling requires under a non-`main` slot.

**Arithmetic, reconciled from 3679:** `3679 + 60 (the implementer's) = 3739` passes, unchanged by
this session because the one test I added fails; failures `23 + 1 = 24`; skipped `1`.

**Other evidence taken this session** (all at hypothesis scope, none an L4):
78 declared-mutation L1/L2 runs, 4 non-declared runs (P-1…P-3, D-1), 2 re-siting runs, 1
detail-capture run of C4(e)(iii), and **one L2** covering both phases' radius —
`tests/integration/services/commands/stock_report`, `tests/integration/services/queries/stock_report`,
`tests/unit/domain/stock_report`, `tests/unit/routers/api_v1` → **1 failed, 696 passed**, the
failure being the declared witness. *Authorization line, written before the run:* the two phases'
production modules have an identical import radius, so one L2 answers both and a second run of the
same command would be redundant reproduction.

## 12. Perimeter and the empty production diff

**Files I changed** (four test files + two plan Review logs + this handoff):

```
app/tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py
app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py
app/tests/integration/services/queries/stock_report/test_list_stock_report_items.py
app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py
docs/.../implementation/stock_report/plans/plan_12.md          (§8 Review log, verification half)
docs/.../implementation/stock_report/plans/plan_13.md          (§8 Review log, verification half)
docs/.../implementation/stock_report/handoffs/tester/2026-09-21_batch_D1_test_1_handoff.md
```

No tracker row and no criterion cell was written. No archgraph change.

**Files a mutation probe touched and reverted** (listed separately; every one verified
byte-identical with `git diff --quiet` immediately after its run):

```
app/beyo_manager/services/commands/stock_report/_ordering.py
app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority.py
app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority_order.py
app/beyo_manager/services/commands/stock_report/requests/__init__.py
app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py
app/beyo_manager/services/commands/stock_report/delete_stock_report_item.py
app/beyo_manager/services/commands/stock_report/_events.py              (APPROVED phase 8 — C3(a)'s pair)
app/beyo_manager/services/commands/stock_report/_goal_credit.py         (APPROVED phase 5 — C1(a)(ii)'s real site)
app/beyo_manager/services/commands/stock_report/_move_assignment.py     (APPROVED phase 4 — C2(b)'s real site)
app/beyo_manager/services/commands/stock_report/_demand_lookup.py       (APPROVED — C1(c))
app/beyo_manager/services/queries/stock_report/list_stock_report_items.py
app/beyo_manager/services/queries/stock_report/list_stock_task_assignments.py
app/beyo_manager/domain/stock_report/serializers.py
app/beyo_manager/routers/api_v1/stock_report.py
```

**The empty-production-diff command and its output:**

```
$ git diff --name-only b6cbbb9 -- app/beyo_manager/
$ git diff --name-only b6cbbb9 -- app/beyo_manager/ | wc -l
0
```

## 13. What variation I did NOT spend — where the reviewer's budget buys something new

- **No second mutant shape of the same sign anywhere.** Every declared cell was run exactly once
  per named mutant (plus the recorded re-sitings). Different mutant shapes at the same site are
  untouched budget.
- **No `TZ`, locale or clock variation.** Every test uses the fixed `NOW`.
- **No concurrency beyond C2(c).** One serialization order is forced (H holds the advisory lock);
  the lock-ordering matrix, `lock_tasks`/`lock_stock_task_assignments` acquisition order, and any
  two-writer race on the delete path are unexercised.
- **No `actor_user_id=None` path** through the cascade (13A's, by plan).
- **No statement-count evidence** beyond C1(c)/C1(k)/C1(l)'s zero-write clause; the batch bound of
  §9 rule 7 is untouched by this batch.
- **No HTTP-layer evidence for the two commands' 422s** beyond the router's own body models —
  C1(m)/C1(n) are proven at the command, which is where their cells site the mutation.
- **No image-ordering evidence**: C4(b)'s new fixture carries one image, so
  `ImageLink.display_order` and the batch-load's `sorted(item_ids)` bound are unprobed.
- **Plan 12 C2(a)/C2(b)** carry no test at all and the density-under-a-real-race half of MC-7 is
  unproven — the plan says so and the prompt forbids reopening it, but it is where an independent
  structural check has the most to find.
