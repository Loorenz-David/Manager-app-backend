---
batch: C1
plans: [8, 11]
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-09-21
actor: Opus (plan-reviewer)
tree: a9b734f (= tester checkpoint 8c60fb0 + documentation only)
---

# Batch C1 review 1 — plans 8 and 11

## 0. Summary

**90 PASS / 1 FAIL / 2 NOT_VERIFIED** of 93 live criterion rows (plan 8: 65/0/2; plan 11: 25/1/0).

**Verdict: CHANGES_REQUESTED.** Two blocking findings, both `production`, both **measured**, neither
reachable by the tester's campaign because no criterion row asks the question:

1. **B1** — the creation command accepts a **soft-deleted item** and a **soft-deleted task**.
   Intention §5A MC-16's predicate table names `items.is_deleted = false` for the *creation* lookup
   and `tasks.is_deleted = false` for the *creation* task lookup; neither predicate exists in the
   shipped code. This also **falsifies plan 11 C7(b)'s stated outcome**, which was recorded
   `UNFORCEABLE` pending "the reviewer's structural check" — the structural check fails.
2. **B2** — `delete_stock_task_assignments` iterates the *request's* `client_ids`, not the
   discovered assignments, so one repeated id removes the same assignment twice and
   double-subtracts its quantity. Measured: a row holding A(4) and B(4) in queue, `DL([A, A])`,
   ends at `quantity_in_queue = 0` with **zero repair records** — silent, self-heal never fires.

**The tester's work holds up.** I audited all 95 declared mutation cells, 103 runs, both reverse
maps, and all five dispositions that can hide a row that cannot fail. The arithmetic closes
independently (I re-derived the per-criterion sums and the 95-test reverse map by script; every
number matches). Every `EQUIVALENT` and `ARMED-SHARED` claim I re-derived from the code was
correct. **No finding routes against the accuracy of the ledger.** The three `verification`
findings below are about evidence the ledger does not claim to have: two of them are owner rulings
that landed *after* the tester's checkpoint and therefore could not have been implemented.

**Boundary checks consumed by citation, not re-run** (orchestrator, stated in the review prompt):
`git diff 6eaf2d3..8c60fb0 -- app/beyo_manager/` empty; zero criteria-table lines edited by the
tester; L4 on the tester tree 21 failed / 3541 passed / 1 skipped, failure IDs identical to the
published 21-ID baseline by `comm` both ways, `3512 + 29 = 3541`. I re-ran only the one-command
production diff my doctrine names as its first check (empty, confirmed) and
`git diff 8c60fb0..HEAD --stat` (five documentation files, no code). **I took no L4** — I changed
no file that survives this session.

## ⚠ OWNER DECISIONS REQUIRED (2)

**Card 1 — the board lets you assign an item you just deleted**

- **Question** — Author two criterion rows in plan 8 C1: a soft-deleted item and a soft-deleted
  task must each be refused (`item_not_found` / `task_not_found`)?
- **Story** — A worker deletes a broken chair from the item list. The stock-report board in
  another tab still shows it as a candidate, and the next worker taps "assign". Today the
  assignment is created: the row's in-queue count climbs by 4 units of a chair that no longer
  exists, the deleted task's "has stock assignment" flag turns back on, and no hook will ever
  clean it up — deleting the item already ran. The board over-reports its queue until someone
  notices and runs the repair endpoint.
- **Branches** — Author the two rows: the fix ships proven, one round. · Fix without rows: the
  behaviour changes but nothing guards it, and the next refactor can undo it silently.
- **Recommendation** — Author them; the plan already enumerates absent / deleted / foreign for the
  stock-report row and only "absent" for the item and the task, which is the gap that let this
  ship.
- **On silence** — The gate holds: B1 is fixed as a production defect with no criterion row, and
  the row stays owed.
- **Trace** — plan 8 C1(a)–(e); intention §5A MC-16 predicate table; plan 11 C7(b).

**Card 2 — the same assignment named twice in one delete**

- **Question** — Should `POST /assignments/delete` with a repeated `client_id` refuse the batch
  (like creation does for a repeated item), or silently de-duplicate?
- **Story** — A worker multi-selects on a slow board and the same assignment lands in the list
  twice. Today the request succeeds, the assignment is deleted once, but its four units are
  subtracted from the row **twice** — so a row that still has four units queued on another
  assignment reports zero. Nothing warns anyone: the counter never goes negative, so the
  self-repair that exists for exactly this never fires.
- **Branches** — Refuse: consistent with creation's duplicate check, the caller learns its bug. ·
  De-duplicate: the request succeeds and the count stays truthful, the caller's bug stays hidden.
- **Recommendation** — De-duplicate **and** keep the response listing each id once: deleting is
  idempotent by nature and a refusal would make an honest retry fail, whereas creation's duplicate
  check exists because two entries genuinely compete.
- **On silence** — The gate holds: B2 stays open, no outcome is written, no row is authored.
- **Trace** — plan 8 §5 task 3, C6(d)–(h); master plan §6.5 `delete_stock_task_assignments`.

---

## 1. Gate check

| Check | Result |
|---|---|
| Intention `planning/intention.md` status header | `RATIFIED` (round 9, 2026-09-19) — **pass** |
| Master plan §4A batch C1 | `TESTED`; A, B1, B2 `APPROVED` — **pass** |
| Tree | `a9b734f`, `git status --porcelain` empty at entry and at exit |
| `git diff 6eaf2d3..8c60fb0 -- app/beyo_manager/` | empty (re-run, one command, doctrine's first check) |
| `git diff 8c60fb0..HEAD` | 5 files, all documentation (master plan, plans 8/11/13, this round's prompt) |

## 2. Findings

Every finding carries one route. `production` → implementer · `verification` → tester ·
`plan` → coordinator/owner.

### B1 — blocking · route: **production** · the creation path ignores soft deletion of the Item and the Task

**What is wrong.** `create_stock_task_assignments._phase3_reason` checks
`row is None or row.is_deleted` for the stock-report row, but only `item is None` and
`task is None` for the Item and the Task. `_locks.py:_lock` (which backs `lock_items` and
`lock_tasks`) filters on `workspace_id` and `client_id` only — deliberately, because §9 rule 4
requires the caller to re-read `is_deleted` after the lock and decide on that. The caller does
that for the row and not for the other two classes.

**Violated authority.** Intention **§5A MC-16**, the predicate table:

| Item lookup (processed, **creation**, guard) | `items.is_deleted = false` |
| Task lookup (**creation**) | `tasks.is_deleted = false` |

and **plan 11 C7(b)**, whose outcome is "no active assignment on a deleted item (creation refused
`item_not_found`, or created then removed)".

**Measured** (reviewer probe, temporary test file, removed — see §5):

```
PROBE deleted-item: CREATED -> in_queue     # after delete_item(I), CR([I on R]) succeeds
PROBE deleted-item: row quantity_in_queue -> 4
PROBE deleted-task: CREATED -> in_queue     # after delete_task(T), CR([I on R]) succeeds
PROBE deleted-task: row quantity_in_queue -> 4
PROBE deleted-task: task.is_stock_assignment -> True
```

Neither `delete_item` nor `delete_task` retires the `TaskItem` link, so `_lookup_primary_pairs`
still returns the pair and phase 3 passes clean. The assignment that results is **unreachable by
every removal hook in plan 11** — its item and its task are already deleted — so the row's counter
is wrong until someone runs `POST /stock-report/repair`.

Why plan 11 C7(b) fails as a row, not merely as an unnamed gap: the Item `FOR UPDATE` that
`delete_item` now takes does exactly what MC-14/U16 asks — it serialises the two sessions. In the
serialisation where `delete_item` commits first, the waiting `CR` then reads a soft-deleted item
through `lock_items` and creates anyway. The lock is present and correctly ordered
(`test_removal_locks.py` observes that); the row's *outcome* still does not hold. This is the
distance between a statement-order proxy and an outcome — see note N2.

**Suggested correction** (inside plan 8's own perimeter; do **not** change `_locks.py`, whose
no-deletion-filter shape is what §9 rule 4 requires):

```python
    task = locked_tasks.get(entry.task_id)
    if task is None or task.is_deleted:
        return "task_not_found"
    item = locked_items.get(entry.item_id)
    if item is None or item.is_deleted:
        return "item_not_found"
```

i.e. the same shape the row check already uses one line above. Both reasons are already in MC-13's
closed vocabulary, so the error contract does not change.

**Rows to prove it** — see owner card 1. Until they exist the fix is unguarded; see S6.

### B2 — blocking · route: **production** · a repeated `client_id` in one delete double-subtracts the counter

**What is wrong.** `delete_stock_task_assignments` discovers assignments into
`discovered_by_id`, computes `missing` from the *set* of request ids, and then removes with
`for client_id in sorted(ids)` — iterating the raw request list. `ids` may contain duplicates:
`DeleteStockTaskAssignmentsRequest.client_ids` is a plain `list[str]` with `min_length=1` and no
uniqueness constraint, and the router's `_DeleteStockTaskAssignmentsBody` adds none. Each repeat
calls `remove_assignment` again on the same, already-soft-deleted instance; `move_assignment`'s
DELETE branch has no `if assignment.is_deleted: return []` short-circuit, so
`_delta_vector(from_state=IN_QUEUE, DELETE, q)` subtracts `q` a second time.

**Violated authority.** Plan 8 **§5 task 3**: "per **assignment** ascending `client_id`:
`remove_assignment(...)`" — the loop is per request id, not per assignment. MC-19's net-change rule
and M1 (counters equal the sum over non-deleted assignments) are broken as a consequence.

**Measured** (reviewer probe, removed — see §5). Row R holds A (`in_queue`, q=4) and B
(`in_queue`, q=4); `quantity_in_queue == 8`. Then `DL([A, A])`:

```
PROBE response: {'deleted_client_ids': ['sta_…5H', 'sta_…5H']}
PROBE counters after DL([A, A]) (B still active, q=4): (0, 0, 0)
PROBE repair records: []
```

The truthful value is `(4, 0, 0)`. The self-heal does not fire because the counter never goes
negative — 8 → 4 → 0 — so no repair record is written and nothing in production notices. (With
only A on the row the second subtraction *would* go negative and self-heal, leaving a spurious
repair record; the two-assignment shape is the silent one.)

**Suggested correction.** Iterate the discovered set, and answer with each id once:

```python
        for client_id in sorted(locked_assignments):
            events.extend(await remove_assignment(ctx.session, locked_assignments[client_id], …))
    …
    return {"deleted_client_ids": sorted(locked_assignments)}
```

That also matches the shape `delete_task`, `delete_item` and `remove_item_from_task` already use
(`for client_id in sorted(locked_assignments)`), which is why the defect is confined to this one
command. Whether a duplicate should instead be *refused* is owner card 2.

### S1 — should-fix · route: **production** · unknown fields are silently dropped at the HTTP boundary

**What is wrong.** `bm/routers/api_v1/stock_report.py` validates with its own body models
(`_CreateStockTaskAssignmentsBody`, `_StockTaskAssignmentEntryBody`,
`_DeleteStockTaskAssignmentsBody`), none of which sets `extra="forbid"`. Pydantic's default is
`extra='ignore'`, so an unknown field is **removed by `body.model_dump()`** before the command's
`extra="forbid"` model ever sees it. Over HTTP the request succeeds with 200.

**Violated authority.** Intention **§9C MC-13**: "Unknown fields → 422 (a local API, so strict)."

**Measured** (pure model check, no DB, no file changed):

```
create body extra cfg = None
dumped -> {'entries': [{'stock_report_item_id': 'a', 'task_id': 'b', 'item_id': 'c',
                        'override_property_mismatch': False}]}     # 'unexpected' and 'typo' gone
```

**Why this is production and not verification.** Plan 8 C3(e) is proven at the `CR()` command
boundary, which is the plan's own fixture shorthand — the row is satisfied and I marked it PASS.
The contract it serves is not. Both the implementer's §8 item 3 and the tester's candidate
criterion 5 describe this as "FastAPI's own validation error"; it is not an error at all (note N5).

**Suggested correction.** `model_config = ConfigDict(extra="forbid")` on the three router body
models, or drop them in favour of the registered request classes. `min_length=1` on the router's
`entries`/`client_ids` is not needed — the command model still enforces it.

### S2 — should-fix · route: **verification** · plan 8 C5(a)'s ratified clause is asserted by no test

C5(a)'s outcome cell now carries, by owner card 1 of the tester round (ruled 2026-09-21, after the
tester's checkpoint): "**and the losing call wrote nothing — `count_writes(statements,
{"stock_task_assignments"}) == 0` over it**". `test_c5a_concurrent_create_on_the_same_item_leaves_
exactly_one_active` imports neither `record_statements` nor `count_writes`. The tester measured
(M56) that without this clause the row is green with the Item lock removed, so the row is
currently exactly as unarmable as the card said. **Row marked NOT_VERIFIED.**

**Correction.** Wrap the losing call in `record_statements` and assert
`count_writes(statements, {"stock_task_assignments"}) == 0`, then re-run M56 (remove the Item lock
in phase 2) and record the red. C1(j)/C1(k) already show the shape.

### S3 — should-fix · route: **verification** · plan 8 C3(a)'s folded fixture is implemented by no test

C3(a)'s fixture cell was folded (after the tester's checkpoint) to
`{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"],"zone":["a1"]}`, precisely so that
JSONB's (length, bytes) storage order differs from alphabetical and the "failures sorted by key"
sub-check can fail. `test_property_mismatch_without_override_raises_409_with_sorted_failures`
still uses the three-key criteria. The sub-check remains unarmable in the tree, which is the
defect the fold was written to close. **Row marked NOT_VERIFIED.**

I confirmed the mechanism by reading rather than re-measuring: `evaluate_stock_criteria` iterates
`criteria.items()` (JSONB order) and returns `sorted(failures, key=key)`; with `zone` (4 bytes)
present JSONB yields `zone, quantity, upholstery, wood_group` while the assertion expects
alphabetical, so M25 would redden. **Correction:** adopt the folded fixture and re-run M25.
Note the outcome cell must be corrected first — see S4.

### S4 — should-fix · route: **plan** · C3(a)'s outcome cell contradicts its own folded fixture

The folded fixture has **four** criteria keys; the outcome cell still lists **three** failures
(`quantity`, `upholstery`, `wood_group`). With item `properties {}` and `quantity 1`, the item
property bag is `{"quantity": "1"}`, so `zone` resolves to `None` and
`evaluate_stock_criteria` appends `CriterionFailure("zone", MISSING_ON_ITEM)`. The correct
`failures` list is
`[{quantity, value_not_accepted}, {upholstery, missing_on_item}, {wood_group, missing_on_item}, {zone, missing_on_item}]`.

Plan 8 §6's own preamble: "An outcome that disagrees with its own fixture is a plan defect: report
it, never reconcile it in the test." Reported. This is an **outcome** cell, so per §9A's authority
split it is the owner's to amend, not the coordinator's — but it is arithmetic, not judgment, and
it blocks S3.

### S5 — should-fix · route: **verification** · the `assert_stock_report_clean` obligation is met by 14 of 79 tests

Plan 8 §6: "Every success row ends with `assert_stock_report_clean`." Plan 11 §6: "Every row ends
with `assert_stock_report_clean` unless drift is planted." Master plan §9 rule 2 states the same
obligation project-wide, with its reason: "A scenario that passes only because it self-healed is a
failure."

Measured across the seven batch-C1 integration files: 79 test functions, **14** call
`assert_stock_report_clean`. The rows the two plans' own preambles oblige and that miss it:

- plan 8 success rows — C3(b), C3(c), C4(g), C4(h), C4(k), C1(r), C1(s), C6(c), C6(h), C7(a)
  (`test_override_on_a_mismatching_entry_creates_with_flag_true`,
  `test_override_on_a_matching_entry_is_ignored`, `test_c4g_quantity_is_copied_from_the_item`,
  `test_quantity_floors_at_one`, `test_two_entries_ascending_item_id_response_order_and_summed_counters`,
  `test_c1r_…`, `test_c1s_…`, `test_deleting_resolved_assignment_leaves_counters_untouched`,
  `test_two_assignments_on_one_row_coalesce_to_one_updated_event`,
  `test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated`);
- plan 11 non-drift rows — C1(b), C1(c), C2(b), C2(c), C3(b), C4(a), C4(b), C4(c), C4(d), C4(e),
  C4(f), C4(i), C5(a), C5(b), C5(c), C5(d), C5(e) (only C1(a), C2(a), C3(a) and C4(g) comply).

The sharpest instance is plan 11 **C3(b)**: its counters clause asserts `(0, 0, 0)`, which is also
what a double-subtract-then-self-heal produces. Only the repair-record half of
`assert_stock_report_clean` distinguishes them. B2 is the same shape in a command this instrument
was never pointed at, which is the argument for the rule.

This is a plan-declared obligation, not coverage I am inventing: it traces to both §6 preambles
and §9 rule 2.

### S6 — should-fix · route: **plan** · plan 8 C1 samples where MC-16 enumerates

C1(a)/(b)/(c) enumerate **absent / soft-deleted / foreign** for the stock-report row. C1(d) and
C1(e) give the Task and the Item **absent only** — no deleted case, no foreign case — although
MC-16's predicate table names an `is_deleted = false` predicate for the creation lookup of both.
Charter rule 2 ("enumerate, never sample") applied to the three visibility predicates of three
entity classes gives nine cells; the plan has five. This gap is exactly what let B1 ship with a
green ledger and `executed == declared`. (Foreign items and tasks are in fact refused — `_lock`
filters `workspace_id` — so only the two deleted cells are live defects.) See owner card 1.

## 3. Notes

- **N1 · production · the phase-5 `except IntegrityError` is a blanket catch.** It wraps the whole
  write loop (insert, `move_assignment`, goal credit, `set_task_stock_flag`) and answers every
  integrity failure with `item_already_assigned` at a single index. Today the only reachable
  violation is the intended one (`uix_stock_task_assignments_item_active`), and I could not
  construct a path to the task-active index (`add_item_to_task` permits one active PRIMARY per
  task) or to the `quantity >= 1` CHECK (`max(item.quantity, 1)`). Recording it because the next
  constraint added to this table will be mislabelled rather than surfaced. Backlog.
- **N2 · plan · a statement-order test is not an outcome, and C7(b) shows the cost.**
  `test_removal_locks.py`'s two tests assert the *generated query text* of the `FOR UPDATE`
  statements. Charter rule 2 (owner rule, 2026-09-19) lists "generated query text" among the
  things that may **not** be a criterion. They are legitimate engineering aids and I do **not**
  ask for their removal (that rule cuts both ways). But the tester's **candidate criterion 3**
  proposes folding `test_delete_task_locks_rows_then_assignments_after_the_existing_task_lock`
  into a lettered row — the coordinator should refuse that, or reshape it as an outcome. And
  plan 11 C7(b)'s disposition cites the `delete_item` twin as evidence that "the lock statement
  itself is observed": the lock *is* observed, is correctly ordered, and the row's outcome is
  still false (B1). That is the whole argument for the rule.
- **N3 · verification · the plan 11 mutation ledger skips id `N06`.** Ids run N01–N05, N05b,
  N07–N26. Every total closes (26 declared, 26 executed, 25 distinct edits because N04 is shared),
  so nothing is missing — but a gap in an id sequence is the first thing an auditor chases. A
  one-line "N06 merged into N04" in table 1 would have saved it.
- **N4 · plan · plan 8 C6(h)'s response clause does not decide an order.** The cell writes
  `{"deleted_client_ids": [A, B]}` in the request's order; the code returns `sorted(ids)`; the test
  asserts a `set`. Any of the three is defensible and the cell picks none. Decide it at the fold
  (it is a frontend-visible shape, §9 rule 15).
- **N5 · verification · a wrong claim about the HTTP surface propagated unchallenged.** The
  implementer's §8 item 3 says an unrecognized top-level field over HTTP "gets FastAPI's own
  validation error"; the tester's candidate criterion 5 repeats it. Measured: it is silently
  dropped and the request succeeds (S1). Both handoffs' prose should be corrected when S1's fix
  lands, so the frontend contract (phase 14) is not written from it.
- **N6 · production · one unlocked read survives in `remove_item_from_task`.** `task_item.role` is
  read before `lock_tasks(...)` and never re-read under the lock (§9 rule 4 asks for the re-read).
  Benign today: the discovery query *is* issued after the lock, and no command in the tree changes
  a `TaskItem.role` in place. Recording it so the next writer of `role` knows.
- **N7 · verification · two tests that cannot fail, by owner ruling.** Plan 11 C4(b) and C5(b) are
  `known-unarmed` (owner card E) and the tester added a test for each anyway. I am **not** routing
  this as over-evidence: each traces to a live criterion row and each cost one short test. Noting
  it only so the next round does not "discover" them as inert.

## 4. What I verified correct, specifically

So the next re-review can spend its budget elsewhere.

**Production, read against the authorities:**
- MC-13's phase-3 order is implemented exactly as the intention lists it, including the round-9
  insertion of `already_processed_by_scanner` between `item_not_task_primary` and
  `task_failed_or_cancelled` (`_phase3_reason`, nine arms, in order).
- MC-1's lock order holds in all five new/edited call sites: create (items → tasks → rows),
  delete (tasks → rows → assignments, no Item tier), `delete_task` (items via the existing
  upholstery pass → task → rows → assignments), `delete_item` (item → tasks → rows → assignments),
  `remove_item_from_task` (task → rows → assignments). Every class is acquired by one
  `SELECT … WHERE client_id IN (…) ORDER BY client_id … FOR UPDATE`.
- **Plan 8 C5(b)'s structural check (the question the prompt asked me).** One statement with
  `ORDER BY client_id … FOR UPDATE` **does** discharge the lock-order promise for a batch:
  PostgreSQL's `LockRows` node sits above the `Sort`/ordered scan and locks each row as it is
  pulled, so acquisition order is the sort order, not the request order. `create_stock_task_assignments`
  passes an unordered `set` to `lock_items` exactly once, so no caller-supplied order can reach
  acquisition at all. That is also *why* the row is `UNFORCEABLE`: deleting `.order_by(...)` leaves
  both sessions receiving the same physical order, so no crossing pair exists to deadlock. Arming
  it would need a multi-site restructure (lock per entry in request order), not a mutant. The
  tester's `UNFORCEABLE` is honest and the row's production requirement is met by construction.
- **Plan 11 C7(a)'s structural check.** `remove_item_from_task` takes
  `lock_tasks(..., {request.task_id})` before its discovery block and before the `TaskItem` write;
  `create_stock_task_assignments` reads `_lookup_primary_pairs` only after its own task lock. Both
  serialisations give the row's outcome: unlink-first ⇒ the waiting `CR` sees `removed_at` set and
  refuses `item_not_task_primary`; create-first ⇒ the assignment exists and the hook removes it.
  **PASS.** (The same check applied to C7(b) is what produced B1.)
- The `IntegrityError → item_already_assigned` backstop, which plan 8 §7 leaves to me, **is**
  positively observed: M56 removed the Item lock, both sessions reached the INSERT, and the
  backstop produced the same 422 with the same reason. Its happy path is not merely argued.
- Post-commit serialization is safe: `create_stock_task_assignments` serializes `locked_items` /
  `locked_tasks` instances *after* the owner-mode commit. I checked
  `models/database.py:44` — the session factory sets `expire_on_commit=False`, so no lazy refresh
  (and no `MissingGreenlet`) can fire on the production path that the tests, running in
  subordinate mode, never exercise.
- `coalesce_stock_report_events` implements MC-19 as registered: last-`:updated` per row, dropped
  on equals-initial, on `:created` **and** on `:deleted`; last-of-each-kind per assignment;
  first-seen order preserved by `first_index`.
- The two structured errors carry MC-13's envelope (`code`, `details`, 422/409) and the router
  renders them explicitly through `_STRUCTURED_ASSIGNMENT_ERRORS`, everything else via `build_err`.
- `serialize_stock_task_assignment` returns exactly the fourteen keys of §6.1 with nested
  `serialize_item_compact` (images included) and `serialize_task_compact`, per §9B ruling 2.
- Tenancy: foreign rows, items, tasks and assignments are all excluded — `_lock` carries
  `workspace_id` on every class, and the delete command's discovery filters it directly.

**The tester's ledger, audited:**
- Arithmetic re-derived independently and matching: plan 8 declared 69 cells (C1 21 · C2 3 · C3 6 ·
  C4 14 · C5 2 · C6 10 · C7 3 · C8 10) against 68 distinct M-ids, C6(c)/C6(i)-ii sharing M49; plan
  11 declared 26 against 25 distinct N-ids, C2(a)/C2(c) sharing N04; 95 total; 103 runs with the 8
  re-sitings. Dispositions sum to 67 and 26.
- The reverse map's per-file test counts are correct, counted by script: create 40 (37 functions,
  two parametrized into 3 and 2), race 2, delete 11, task_side 4, item_side 8, guard 13, locks 2,
  ser 4, router 10, demand 1 = **95**. Three candidate criteria and three rule-18 pins declared;
  **zero silent orphans**.
- Every `EQUIVALENT` I re-derived from the code is genuinely equivalent: C7(b) (a phase-3 raise
  precedes every dispatch statement and `events` is empty there, so no placement can fail the row);
  C4(k) (`:244` and `:309` sort twice); C6(c)/C6(i) (the `deltas` guard and the coalescer's
  equals-initial drop); C6(e) (the post-lock re-read catches the discovery filter); plan 11 C2(b)
  (the discovery query is keyed on `(task_id, item_id)`, so the role check alone is inert);
  C5(a)-i (the rollback hides write order).
- Both `ARMED-SHARED` rows reach the **second** row's own assertion, as §9 rule 8 demands: M09
  reddens C3(d)'s own `details` equality (dropping `CANCELLED` lets the retry through phase 3 and
  the `pytest.raises` fails), and N04 reddens C2(c) on its `CR` half (a surviving A makes the new
  create hit the task-active index), not on C2(a)'s clause — the assertion order was moved for
  exactly this and the move is correct.
- The C3(a) JSONB measurement is sound and I extended it rather than repeating it (see S3/S4).
- The plan-11 C3(a) identity-map repair is real: `populate_existing` is present and a
  Core-statement task deletion would now be seen.
- Plan 11 C5(a) genuinely runs `create_task` on a second `get_db_session()`, which is production's
  topology, and the three counts it asserts are all written before `find_or_create_item` is reached.

## 5. Mutation-probe declaration

**Production files touched: none.** I applied no mutation to any file under `app/beyo_manager/`.
The two blocking findings were produced by *adding* temporary test files, not by mutating code.

**Temporary files created and removed:**

```
app/tests/integration/services/commands/stock_report/test_zz_reviewer_probe_dupdelete.py         (created, run, deleted)
app/tests/integration/services/commands/stock_report/test_zz_reviewer_probe_deleted_entities.py  (created, run, deleted)
```

Their compiled artefacts under `__pycache__/` were removed with them. After cleanup,
`git status --porcelain` is empty and `git diff --quiet` succeeds — **the working tree is
byte-identical to `a9b734f`**.

**Database side effects: none persisted.** Both probes ran on the `db_session` fixture, which
rolls back at teardown; each probe failed its own assertion (that was the point), and the failure
path is the rollback path. No probe committed, and no probe used
`purge_stock_report_workspace`-requiring commits.

**Other commands run** (read-only): `git status`, `git diff`, `git show`, a Pydantic model check in
a throwaway `python3 -c` (no file written), and the two probe runs above at L1 scope
(`pytest <file>`, `-n 0` for the second read of stdout). **No L4** — my tree changes nothing that
survives, so an L4 of my own would be over-evidence (charter test-evidence section); the
orchestrator's tree-bound stamp is cited in §0.

## 6. Per-row disposition — 93 rows

### Plan 8 — 65 PASS / 0 FAIL / 2 NOT_VERIFIED

| Rows | Disposition | Note |
|---|---|---|
| C1(a)–C1(u) (21) | **PASS** | phase-3 order and every reason verified against MC-13; C1(j)/C1(k)'s `count_writes` clauses present and reddening alone, as owner card A intended |
| C2(a)–C2(c) (3) | **PASS** | phase-1 duplicates name every index; C2(c) proves collection into phase 3's error |
| C3(a) | **NOT_VERIFIED** | S3 — the folded four-key fixture is implemented by no test, so "failures sorted by key" is still unarmable. Its 409/`code`/`details`/nothing-written clauses PASS |
| C3(b)–C3(f) (5) | **PASS** | C3(e) passes at the command boundary, which is the plan's shorthand; the HTTP-surface gap is S1, a separate production finding |
| C4(a)–C4(l) (12) | **PASS** | C4(l) clause 1 only; clause 2 relocated to plan 13 C6(a) by owner card 2 and correctly removed from this cell |
| C4(m) | **PASS** | both authorship halves, one mutation each (rule 12) |
| C5(a) | **NOT_VERIFIED** | S2 — the ratified `count_writes == 0` clause is asserted by no test |
| C5(b) | **PASS** | `UNFORCEABLE`; **reviewer's structural check performed and passed** — §4 |
| C6(a)–C6(i) (9) | **PASS** | C6(g)'s `failed`-sibling fixture is built as owner card B ruled |
| C7(a)–C7(c) (3) | **PASS** | C7(b) `EQUIVALENT`, accepted: structurally true, no placement of the dispatch can fail it |
| C8(a)–C8(j) (10) | **PASS** | four role mutants per route, one per sub-row, each run separately; both renderings armed |

### Plan 11 — 25 PASS / 1 FAIL / 0 NOT_VERIFIED (C4(h) withdrawn, not counted)

| Rows | Disposition | Note |
|---|---|---|
| C1(a)–C1(c) (3) | **PASS** | the `failed`-then-active construction of C1(c) is the only reachable two-assignment shape and is built correctly |
| C2(a)–C2(c) (3) | **PASS** | C2(b) re-sited to the `item_id` term (the role check alone is inert — confirmed by reading); C2(c) `ARMED-SHARED`, reaching its own bite |
| C3(a)–C3(b) (2) | **PASS** | C3(a)'s fresh read is what makes the row able to fail |
| C4(a)–C4(g), C4(i) (8) | **PASS** | C4(b) `EQUIVALENT` by owner card E, not reopened; C4(d)/C4(e) cover both None directions |
| C5(a)–C5(e) (5) | **PASS** | C5(a)'s rollback clause proven on a second fresh session; C5(b) `EQUIVALENT` by owner card E |
| C6(a)–C6(c) (3) | **PASS** | all three trigger strings distinguished |
| C7(a) | **PASS** | `UNFORCEABLE`; **reviewer's structural check performed and passed** — §4 |
| C7(b) | **FAIL** | the structural check **fails**: in the ordering the new Item lock produces, `CR` creates an active assignment on the deleted item. See **B1** |

## 7. Lessons for the plans

- **L-32 (new). A criterion row whose evidence is "the reviewer's structural check" must name the
  property to be checked, not the statement to be looked at.** Plan 11 C7(b) said "drop the new
  Item lock — reviewer verifies the lock statement". The lock statement is present, correctly
  ordered, and observed by an automated test — and the row's outcome is still false, because the
  outcome depends on what the *other* session does after the lock is released, which no statement
  inspection can see. Where a row is declared unforceable, the cell should state the
  post-condition the reviewer must derive ("after either serialisation, no active assignment names
  a deleted item"), not the line to read.
- **L-33 (new). An owner ruling that lands after the tester's checkpoint creates an unmet clause,
  not a satisfied one.** Two rulings (C5(a)'s `count_writes` clause, C3(a)'s fixture) were folded
  into plan 8 between `8c60fb0` and `a9b734f`. Both were folded correctly; neither can be true in
  a tree the tester had already handed over. The batch state machine has no step between
  `TESTED` and `REVIEWING` that re-arms rows, so the coordinator should either fold before the
  tester runs or record the folded cells as owed in the same act. (Both are recorded here as
  NOT_VERIFIED, which is the cheapest correct outcome, but a tracker note would have been cheaper
  still.)
- **L-34 (new). Visibility predicates are a three-cell enumeration per entity class, and the plan
  must carry all three.** Absent / soft-deleted / foreign. Plan 8 carries three for the row, one
  for the task and one for the item; MC-16's predicate table names the missing ones explicitly.
  Applies forward to plans 9, 10, 12, 13 and 13A, each of which looks up items, tasks or rows.
  Folds under L-16's family (a tenancy row needs a cross-workspace reference) as its deletion twin.
- **L-35 (new). A batch command's write loop iterates its discovered set, never its request
  list.** The distinction is invisible until the request repeats an id. Four commands in this
  batch iterate `sorted(locked_assignments)`; one iterates `sorted(request.client_ids)`, and that
  one is the defect. Worth a §9 standing rule if plan 12/13's batch surfaces repeat the shape.
- **Residual on L-25** (name the arming site and verify it is the site the row depends on): this
  round produced its cleanest instance. C5(b)'s cell was corrected pre-implementation to
  `_locks.py:_lock`'s `.order_by(...)`, which **is** the load-bearing site — and it still cannot
  arm the row, because the property is not observable from either session. Naming the right site
  is necessary and not sufficient; L-31's "verify the site executes under the row's own fixture"
  needs a second half: "and that the fixture can observe its absence".

## 8. Carry-forward dispositions

| Item | Destination | Why |
|---|---|---|
| N1 (blanket `except IntegrityError`) | backlog note, revisit at plan 13 (the cascade adds writes to this table) | no reachable mislabelling today |
| N2 (statement-order tests are not criteria) | coordinator, at the batch C1 fold — **refuse or reshape tester candidate criterion 3** | charter rule 2 forbids the row shape |
| N3 (`N06` gap) | tester, next round's ledger | cosmetic; totals close |
| N4 (C6(h) response order undecided) | coordinator fold; frontend-visible, §9 rule 15 | affects the phase-14 contract |
| N5 (wrong HTTP claim in two handoffs) | coordinator, when S1's fix lands | the phase-14 contract is written from these |
| N6 (unlocked `task_item.role` read) | backlog; revisit if any command writes `TaskItem.role` | benign today |
| N7 (two by-ruling inert tests) | none — recorded so they are not rediscovered | owner already ruled |
| Tester candidate criteria 1, 2, 4 | coordinator fold (4 is the implementer's own, and I agree it is covered by nothing) | unchanged from the tester's routing |
| Tester candidate criterion 5 | folds into **S1**; it is a production defect, not a candidate row | measured this round |
| Tester backfill table (§9), 13 rows | coordinator fold; all 13 verified accurate against the code | — |
