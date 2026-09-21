# Plan 11 — Removal hooks (task, item, PRIMARY unlink) and the category guard on both item writers

```
state: NOT_STARTED
phase: 11 of 15
depends_on: 8 (APPROVED)
projection: mandatory (five existing commands, two new locks, a refusal inside task creation)
complex: yes — multi-site edits in existing commands with lock-order arguments
```

## 1. Goal

The pairing can end from the task or item side: deleting a task, unlinking its PRIMARY item, or
deleting the item removes every non-deleted assignment of the pair through `remove_assignment`;
and an item on the board cannot change category through `update_item` **or** through
`find_or_create_item` (reached from `create_task` and the items route). **Not in this phase:**
row deletion (13), sync (10 — its hooks are separate call sites).

## 2. Read first

1. `master_plan.md` §6.5 (`_category_guard.py`), §9 rules 4, 6.
2. Intention §5 rule 6, §5B MC-14 in full (the hook table, "the find-or-create guard, made exact",
   callers, lock order), §14B B4, B6, §14D D3, §14C C23, C30, C31, C33, U11, U16; MC-1 lock order
   (items → tasks → rows → assignments); §12A trigger set.
3. Re-check handoff §1 rows for MC-14 and §3 (the two callers of `find_or_create_item`, one caller of
   `create_task`, no third category writer).
4. The five commands (line numbers verified 2026-09-19): `bm/services/commands/tasks/delete_task.py`
   (existing task `FOR UPDATE` at `:71-77`, `task.is_deleted = True` at `:92` — the hook goes between);
   `tasks/remove_item_from_task.py` (loads no Task today; hook after the `TaskItem` lookup `:23-32`,
   new Task `FOR UPDATE` first); `items/delete_item.py` (item loaded without lock `:26-35`; add `FOR
   UPDATE`, hook before `item.is_deleted = True` `:37`); `items/update_item.py:_update_item_in_session`
   (category write at `:73-74`; guard before it, after locking the item); `items/find_or_create_item.py`
   existing branch (`:94-118`; guard before the first write to `existing` at `:98`);
   `tasks/create_task.py:250-262` (the call with `model_dump(exclude_unset=True)`);
   `routers/api_v1/items.py:225-237` (the second caller); `items/cancel_upholstery_requirements.py:lock_and_filter_items_without_active_tasks`
   (the Items → Tasks precedent `delete_task` already uses).

## 3. Dependencies

Phase 8 APPROVED (assignments through `CR`; `remove_assignment` from 4).

## 4. Files expected to change

New: `bm/services/commands/stock_report/_category_guard.py`;
`app/tests/integration/services/commands/stock_report/test_task_side_removals.py`,
`test_item_side_removals.py`, `test_category_guard.py`, `test_removal_locks.py`.
Edited: `delete_task.py`, `remove_item_from_task.py`, `delete_item.py`, `update_item.py`,
`find_or_create_item.py` (each: one hook or guard call plus, where MC-14 says **new**, one lock).

## 5. Tasks

1. `assert_item_category_change_allowed(session, *, workspace_id, item_id, current_category_id,
   incoming_category_id)`: no-op when `incoming == current` (None-aware); otherwise query a non-deleted
   assignment for the item with `state IN ACTIVE_ASSIGNMENT_STATES` (the frozenset, master plan §9
   rule 16); found → `ConflictError("Unassign this item from the
   stock report before changing its category.")`. The caller holds the Item lock and has re-read the
   stored category (`populate_existing`) before calling.
2. `delete_task`: after the task `FOR UPDATE` (existing) and before `task.is_deleted = True`: discover
   the task's non-deleted assignments (any state) → lock their rows ascending → lock the assignments
   ascending → `remove_assignment(..., trigger="delete_task")` each → append events to the command's
   list. Lock order Items → Task (existing) → rows → assignments holds.
3. `remove_item_from_task`: before the `TaskItem` write, lock the Task (`FOR UPDATE`, new); when
   `task_item.role == PRIMARY`, remove every non-deleted assignment with that `(task_id, item_id)` via
   `remove_assignment(..., trigger="remove_item_from_task")`; RELATED → nothing; events appended to
   its dispatch list.
4. `delete_item`: load the Item `FOR UPDATE` (new); remove every non-deleted assignment of the item
   (`trigger="delete_item"`), locking tasks → rows → assignments ascending; the item's tasks are
   untouched; events appended.
5. `update_item._update_item_in_session`: when `"item_category_id" in request.model_fields_set` and
   the value differs from the stored one (None-aware): lock the Item `FOR UPDATE` with
   `populate_existing`, re-compare, call the guard; then proceed as today.
6. `find_or_create_item` existing branch: same condition and guard before the first write to
   `existing`; the `ConflictError` propagates through `create_task`'s owner-mode `maybe_begin`, so the
   whole creation rolls back.
7. Tests first from the table.

## 6. Criteria

Fixture: **F0** with A created through `CR`. Commands are called with `make_ctx` (manager U).
Every row ends with `assert_stock_report_clean` unless drift is planted.

Every outcome is computed from **F0**'s own values (I `quantity 4`, R `quantity_requested 10`, goal G awaiting 0) plus this row's own deltas, side effects included; a second item or task named by a row is a copy of F0's unless stated. **`PR` is not available in batch C1** (phase 9 is batch C2): a terminal assignment is reached with `move_assignment` directly. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | A `awaiting` (`G == 4`); `delete_task(T)` | T soft-deleted; A soft-deleted (`deleted_by_id == U`); counters `(0, 0, 0)`; `G == 0`; flag false; dispatched list contains `stock_task_assignment:deleted` + `stock_report_item:updated` beside the task's own events | remove the hook | MC-14 row 1, §5 r6, M2 |
| C1(b) | A `resolved`; `delete_task(T)` | A soft-deleted; counters unchanged; no `:updated`; flag false | remove only active assignments | MC-14 (U11, C23) |
| C1(c) | T holds two non-deleted assignments — the only reachable shape: `CR([I on R])` → A `in_queue`; `move_assignment(A, failed)` (terminal, and **not** one of the two states §14F F9 refuses); `CR([I on R2])` → B `in_queue`; `delete_task(T)` | both A and B soft-deleted; R2's counters `(0,0,0)`; R's unchanged; flag false | remove only the first found | MC-14 "every non-deleted assignment of the task", §14F F9 (owner card B, 2026-09-21) |
| C2(a) | `remove_item_from_task(T, I)` with A `in_queue` | `TaskItem.removed_at` set; A soft-deleted; counters `(0, 0, 0)`; flag false; stock events in the dispatched list | remove the hook | MC-14 row 2 |
| C2(b) | T has PRIMARY I (A active) and a RELATED item J; `remove_item_from_task(T, J)` | A untouched; counters unchanged; no stock event | act on any role | MC-14 "removing a RELATED item does nothing" |
| C2(c) | swap: `remove_item_from_task(T, I)` then `add_item_to_task(T, J as PRIMARY)`, where **J is a copy of I** (same category K, same properties, so `CR([J on R])` clears MC-13's category and matcher checks) | no non-deleted assignment exists for T; `CR([J on R])` then succeeds | remove the PRIMARY-unlink removal hook from `remove_item_from_task.py` (call site, before the `TaskItem` write) → A survives the swap, so no-non-deleted-assignment fails and `CR([J on R])` hits `uix_stock_task_assignments_task_active` and is refused by the `IntegrityError` backstop. Same code edit as C2(a): both runs recorded, and this cell's bite is the `CR` half (L-28) | MC-14 "a swap is removal then add" |
| C3(a) | `delete_item(I)` with A `in_progress` | I soft-deleted; A soft-deleted; counters `(0, 0, 0)`; T **not** deleted and its state unchanged; flag false | also delete the task | MC-14 row 3, P31, §14B B4 |
| C3(b) | A `failed`; `delete_item(I)` | A soft-deleted; counters unchanged | restrict the `delete_item` hook's assignment query to `ACTIVE_ASSIGNMENT_STATES` (`delete_item.py`, call site) → the `failed` assignment is left non-deleted. Twin of C1(b) on the item side; both runs recorded (L-28) | MC-14 (U11) |
| C4(a) | A active; `update_item(I, item_category_id = K2)` | raises `ConflictError` (`409`) with message exactly `Unassign this item from the stock report before changing its category.`; I's category, snapshot and `updated_at` unchanged | drop the guard | MC-14 row 4, §14B B6, M8 |
| C4(b) | A active; `update_item(I, item_category_id = K)` (same) | allowed; no error | compare raw request to stored without None-awareness → no change either; the bite is (d)/(e). **Known-unarmed on its own terms** — the same double guard as C5(b); see owner card E, 2026-09-21 | MC-14 "setting the same value is not a change" |
| C4(c) | A active; `update_item(I, designer = "x")` (category not in `model_fields_set`) | allowed | guard on the request's default `None` → refuses | MC-14 `model_fields_set` term |
| C4(d) | I `item_category_id NULL`, A cannot exist (creation requires a category) — use: A created, then raw `UPDATE items SET item_category_id = NULL`; `update_item(I, item_category_id = K)` | 409 | treat `None → X` as no change | MC-14 (None-aware) |
| C4(e) | A active; `update_item(I, item_category_id = None)` | 409 | treat `X → None` as no change | MC-14 (None-aware) |
| C4(f) | A `resolved` only; change category | allowed; category changed | block on terminal | MC-14 "terminal does not block" |
| C4(g) | A soft-deleted only; change category | allowed | block on deleted | MC-14 |
| ~~C4(h)~~ | **WITHDRAWN — owner card F, 2026-09-21.** The row cannot be built: `_update_item_in_session` has exactly two callers, and the second (`complete_task_post_handling.py:120-129`) constructs `UpdateItemRequest(client_id=…, item_zone=…)` — `item_category_id` is never in `model_fields_set` and nothing in that command can put it there, so the named mutation is unobservable. MC-14's "covers both" is a claim about **where the guard sits**, not that the second caller can change a category; that placement is enforced by there being one implementation point (`_category_guard.py`) and is covered by C5(a)/C5(e). Forcing it by calling the private helper from a test would assert at a private boundary, which charter rule 2 forbids. | — | — | — |
| C4(i) | A `resolved_early` only, reached with `move_assignment(in_queue → resolved_early)` — **`PR` (phase 9) is not available: the owner split batch C into C1 = 8 → 11 and C2 = 9 → 10, so 11 runs before 9 (master plan §3B)**; change category | allowed; category changed | write the guard's query as `state NOT IN (resolved, failed)` (a hand-typed terminal list) → 409 | MC-14 "terminal does not block", §14F F1, master plan §9 rule 16 |
| C5(a) | A active on I (`article_number SR-x`); `create_task` for `SR-x` with `item_category_id = K2` | 409 with the same message; no task row, no task note, no customer row, no change to I (counts in W before == after) | guard after the first write / raise outside the transaction | MC-14 row 5, §14D D3, C30 |
| C5(b) | same with `item_category_id = K` | task created; I unchanged | — **deliberate blank (§3B class 3, owner card E, 2026-09-21).** No single-site mutant: "setting the same value is not a change" is guarded twice — the caller's own `differs` term (§5 tasks 5–6) and the guard's `incoming == current` short-circuit (§5 task 1). Dropping either alone is an **equivalent mutant**, because the other still short-circuits. The owner declined the one-decision-point restructure: it would take a row lock on every ordinary item save to arm one test. Row is **known-unarmed**, not unexamined | MC-14 |
| C5(c) | same with the category omitted from the item payload | task created; I's category unchanged (`exclude_unset`) | drop the `model_fields_set` term → refuses | MC-14 "made exact" |
| C5(d) | I with **no assignment at all** (the choice that keeps this row armed — with a terminal assignment a weaker "widen the lookup to any non-deleted assignment" mutant would also kill it, and that finer mutant is already carried by C4(f)/C4(g) on the `update_item` caller); `create_task` with `K2` | task created; I now in K2 (today's behaviour) | delete the active-assignment lookup in `assert_item_category_change_allowed` (`_category_guard.py`, definition site) and refuse whenever the incoming category differs → 409 instead of a created task | MC-14 "behaves as today" |
| C5(e) | `find_or_create_item` via `POST /api/v1/items/find-or-create` semantics (call the command with the route's ctx) with a different category while A active | 409 | delete the `assert_item_category_change_allowed(...)` call from `find_or_create_item.py`'s existing branch (call site, before `:98`) → no refusal on either caller. Same code edit as C5(a): both runs recorded, and this cell's bite is the items-route ctx (L-28) | MC-14 second caller |
| C6(a) | A `in_queue`; raw `quantity_in_queue = 0`; `delete_task(T)` | one repair record `trigger == "inline:delete_task"` | pass `trigger="manual"` instead of `trigger="delete_task"` at `delete_task.py`'s `remove_assignment` call (call site) → the repair record's trigger reads `inline:manual` | §12A trigger set |
| C6(b) | same drift; `remove_item_from_task(T, I)` | `inline:remove_item_from_task` | the same substitution at `remove_item_from_task.py`'s `remove_assignment` call (call site) → `inline:manual` ≠ `inline:remove_item_from_task` | §12A |
| C6(c) | same drift; `delete_item(I)` | `inline:delete_item` | the same substitution at `delete_item.py`'s `remove_assignment` call (call site) → `inline:manual` ≠ `inline:delete_item` | §12A |
| C7(a) | two sessions: `remove_item_from_task(T, I)` and `CR([I on R])` for a not-yet-assigned I, barrier-released | afterwards: no active assignment exists for an item that is not T's PRIMARY (either the creation was refused `item_not_task_primary` after waiting, or it was created and then removed) | drop the new Task lock — **interleaving not forced**; reviewer verifies the lock statement | MC-14 (U16, C33) |
| C7(b) | `delete_item(I)` vs `CR([I on R])`, barrier-released | no active assignment on a deleted item (creation refused `item_not_found`, or created then removed) | drop the new Item lock — same caveat | MC-14 (U16) |

## 7. Notes

- Sizing: 27 criterion rows in 7 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- Round 9 (2026-09-19): C4(i) added — the category guard reads the active frozenset, so the sixth
  terminal state does not block a category change. This phase depends on 8; `PR` (phase 9) is
  **The coordinator did reorder: batch C1 is 8 → 11 and phase 9 is batch C2, so `PR` does not
  exist when this phase runs. C1(c) and C4(i) therefore reach their terminal states through
  `move_assignment` directly** (master plan §3B).
- **Foreign fixture-side dependencies (2026-09-21 fold, L-25).** Two rows depend on files no plan
  names: C2(c) on `tasks/add_item_to_task.py` (its one-active-PRIMARY-per-task check, `:47-57`,
  is what makes the swap and C1(c)'s construction behave as the row assumes) and the withdrawn
  C4(h) on `task_post_handling/complete_task_post_handling.py:120-129`. Both are registered in
  master plan §6.1b.
- **Owner cards ruled 2026-09-21 (batch C1 projection).** Card B: C1(c)'s fixture was unbuildable
  — it re-assigned an item Scanner had already reported, which §14F F9 refuses on any row and
  plan 8 C1(p)/C1(q) implement; the second assignment is now reached through a **`failed`** one.
  Card E: C4(b) and C5(b) are **known-unarmed** — the no-op is guarded twice, so no single-site
  mutant exists, and the owner declined the one-decision-point restructure because it would take
  a row lock on every ordinary item save. Card F: C4(h) **withdrawn** — its fixture cannot be
  built.
- C1(c) records its own construction difficulty deliberately: the only way a task holds two
  non-deleted assignments is a terminal one plus an active one for the same item on two rows. The
  implementer builds exactly that.
- C4(d) shows the item with a NULL category **after** assignment (raw SQL) because creation refuses
  a category-less item (`item_has_no_category`); the row tests the guard's None-awareness, not a
  reachable user path.
- C7 rows are declared unable to force their interleaving (master plan §9 rule 9).
- The 409 message is the ratified sentence, verbatim, no leading identity token (master plan §5).

## 8. Review log

**Implementer, 2026-09-21 (batch C1, Sonnet).** Built `_category_guard.py`
(`assert_item_category_change_allowed`) and its five call sites: `delete_task.py` (hook
between the existing task lock and `task.is_deleted = True`), `remove_item_from_task.py`
(new Task lock, PRIMARY-only removal), `delete_item.py` (new Item lock, first statement
in the transaction), `update_item.py` and `find_or_create_item.py`'s existing-item
branch (both: lock+re-read+guard *before* any other field write to the item — see the
ordering note below).

**Judgment call — guard placement relative to `_DIRECT_FIELDS`.** In both `update_item.py`
and `find_or_create_item.py`, the category guard's `with_for_update().execution_options(
populate_existing=True)` re-select refreshes **every** mapped column on the item from the
database, discarding any not-yet-flushed in-memory attribute changes. The plan's task text
places the guard "before the first write to `existing`", which I read as before the
`_DIRECT_FIELDS` loop too, not only before the category assignment line — placing it after
that loop (as a literal reading of "before item.item_category_id = ..." might suggest) would
silently drop the request's other field changes whenever a category change is also requested
in the same call. I moved the guard block to run first in both functions. No criterion row
in this phase exercises "category change plus another field in one request", so this is
undeclared by any row; flagging it since a mutation that reintroduces the ordering bug would
not be caught by any of my tests or (as far as I can tell) any named cell in this plan.

**C5(a)'s "whole creation rolls back" claim is not independently testable at this file's
scope.** My `test_category_guard.py` proves the guard fires with the exact message and
leaves the item's own category unchanged, but cannot observe "no task row exists" from
inside the same test session: `db_session` has been in one continuously-autobegun
transaction since the fixture's first flush, so `create_task`'s own `maybe_begin` never
reaches owner mode in-test and never gets a chance to roll back — the flushed-but-uncommitted
Task row is visible to a same-session read regardless of whether production's real,
fresh-per-request session would have discarded it. The full-rollback guarantee is argued
analytically in intention §5B ("no `begin_nested` wraps the call, no earlier step commits")
and I did not reproduce it with an isolated two-session test given this batch's scope; naming
it here rather than asserting something my own fixture cannot actually discriminate.

**C7(a)/(b) are not built** — plan §7 already declares them unable to force their
interleaving; the reviewer's structural check is the intended instrument (master plan §9
rule 9). `test_removal_locks.py` instead verifies each hook's own **statement order**
(MC-1: items → tasks → rows → assignments) via `record_statements`, which is a different,
buildable claim.

**Environment finding, fixed in this round (not a criterion, a collision):** the new unit
test `app/tests/unit/domain/stock_report/test_serializers.py` (phase 8) collided at the
full-suite L4 with the pre-existing `app/tests/unit/domain/shopify/test_serializers.py` —
this test tree has no `__init__.py` files, so pytest's rootdir import mode uses the bare
filename as the module name and the second file collected errors out instead of running.
Renamed to `test_stock_report_serializers.py`. Caught only at the batch's one L4 run,
never at L1/L2 scope (both files import and run cleanly alone) — worth a standing rule if
this project adds more `test_serializers.py`-shaped files elsewhere.

**Rows not exercised by this round's tests** (named per the tester contract, see the batch
handoff for the full per-criterion map): C4(b), C4(d), C4(e) (built: C4(a), C4(c), C4(f),
C4(g), C4(i)); C5(b) (declared known-unarmed by the plan itself); the two C7 rows (declared
unforceable); C6(a)-(c) (the trigger-string rows) — not built in this round.

**Tester (verification engineer), 2026-09-21 (batch C1, Opus).** All 26 live criterion rows
(C4(h) withdrawn) have a disposition. 7 tests added, 0 removed; no production change. Full
ledger: `handoffs/tester/2026-09-21_batch_C1_test_1_handoff.md`.

*Judgment calls and re-sitings:*
- **C2(b)** — "act on any role" is an **equivalent mutant**: the hook's discovery query is keyed
  on `(task_id, item_id)`, so unlinking a RELATED item finds no assignment whatever the role
  check says. Re-sited to the `item_id` term of that query; both runs recorded. The row also
  gained its "no stock event" clause, which was unasserted.
- **C2(c)** — the test asserted C2(a)'s clause (`A.is_deleted is True`) *before* the `CR`, so the
  shared mutation short-circuited there and never reached this row's own bite (charter rule 12).
  The removal assertion now sits after the `CR`, which is where the cell says the bite is (L-28).
- **C3(a)** — the test read the Task back with `db_session.get(...)`, which returns the
  identity-mapped instance; a defect deleting the task with a Core statement left it saying
  `False` and the row could not fail. The read is now `populate_existing`. With that, the
  "also delete the task" mutant reddens.
- **C5(a)** — the implementer correctly reported that "the whole creation rolls back" is not
  observable inside `db_session` (one continuously-autobegun transaction, so `create_task`'s
  `maybe_begin` never reaches owner mode). The test now runs `create_task` on a **second, fresh
  session** from `get_db_session()` — production's own topology — and asserts the task, task-note
  and customer counts in W are unchanged. `create_task` writes the Task row (`:~150`), its note
  (`:203`) and resolves the customer (`:177`) *before* `find_or_create_item` (`:259`), so the
  clause is load-bearing. Armed by a mutant that commits before the refusal escapes; the cell's
  other half, "guard after the first write", is **equivalent** (the rollback hides write order).
- **C4(b)** and **C5(b)** — tests added; both recorded `EQUIVALENT`, the named C4(b) mutant
  measured green exactly as owner card E predicts. Not reopened.
- **C7(a)/(b)** — both named mutations executed and recorded. `UNFORCEABLE` as the plan declares.
  "Drop the new Item lock" does redden `test_removal_locks.py`'s MC-1 statement-order test, so
  the reviewer's structural check for C7(b) has an automated instrument; C7(a)'s
  (`remove_item_from_task`'s Task lock) has none and stays a reading check.
- **C1(a)/(b)/(c), C2(a)** gained the clauses their outcome cells name and their tests did not
  assert (task flag, the dispatched stock events, R's counters).

*Blocked:* none. No `BLOCKED-PRODUCTION` row.
