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

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | A `awaiting` (`G == 4`); `delete_task(T)` | T soft-deleted; A soft-deleted (`deleted_by_id == U`); counters `(0, 0, 0)`; `G == 0`; flag false; dispatched list contains `stock_task_assignment:deleted` + `stock_report_item:updated` beside the task's own events | remove the hook | MC-14 row 1, §5 r6, M2 |
| C1(b) | A `resolved`; `delete_task(T)` | A soft-deleted; counters unchanged; no `:updated`; flag false | remove only active assignments | MC-14 (U11, C23) |
| C1(c) | T with A active on R and B resolved on R2 (a second item is impossible — one active per task; use A active + a resolved earlier assignment of the same item on R2 that a new active replaced? **not constructible**: a task has one PRIMARY item; use A `awaiting` then `PR` resolves it, then `CR` refused… ) — **row withdrawn at planning**: one active per task and one PRIMARY per task make "two assignments on one task in different states" reachable only as terminal + active for the same item on two rows: build A resolved on R (via `PR`) then `CR` on R2 for the same item → B active; `delete_task(T)` | both A and B soft-deleted; R2's counters `(0,0,0)`; R's unchanged; flag false | remove only the first found | MC-14 "every non-deleted assignment of the task" |
| C2(a) | `remove_item_from_task(T, I)` with A `in_queue` | `TaskItem.removed_at` set; A soft-deleted; counters `(0, 0, 0)`; flag false; stock events in the dispatched list | remove the hook | MC-14 row 2 |
| C2(b) | T has PRIMARY I (A active) and a RELATED item J; `remove_item_from_task(T, J)` | A untouched; counters unchanged; no stock event | act on any role | MC-14 "removing a RELATED item does nothing" |
| C2(c) | swap: `remove_item_from_task(T, I)` then `add_item_to_task(T, J as PRIMARY)` | no non-deleted assignment exists for T; `CR([J on R])` then succeeds | — | MC-14 "a swap is removal then add" |
| C3(a) | `delete_item(I)` with A `in_progress` | I soft-deleted; A soft-deleted; counters `(0, 0, 0)`; T **not** deleted and its state unchanged; flag false | also delete the task | MC-14 row 3, P31, §14B B4 |
| C3(b) | A `failed`; `delete_item(I)` | A soft-deleted; counters unchanged | — | MC-14 (U11) |
| C4(a) | A active; `update_item(I, item_category_id = K2)` | raises `ConflictError` (`409`) with message exactly `Unassign this item from the stock report before changing its category.`; I's category, snapshot and `updated_at` unchanged | drop the guard | MC-14 row 4, §14B B6, M8 |
| C4(b) | A active; `update_item(I, item_category_id = K)` (same) | allowed; no error | compare raw request to stored without None-awareness → no change either; the bite is (d)/(e) | MC-14 "setting the same value is not a change" |
| C4(c) | A active; `update_item(I, designer = "x")` (category not in `model_fields_set`) | allowed | guard on the request's default `None` → refuses | MC-14 `model_fields_set` term |
| C4(d) | I `item_category_id NULL`, A cannot exist (creation requires a category) — use: A created, then raw `UPDATE items SET item_category_id = NULL`; `update_item(I, item_category_id = K)` | 409 | treat `None → X` as no change | MC-14 (None-aware) |
| C4(e) | A active; `update_item(I, item_category_id = None)` | 409 | treat `X → None` as no change | MC-14 (None-aware) |
| C4(f) | A `resolved` only; change category | allowed; category changed | block on terminal | MC-14 "terminal does not block" |
| C4(g) | A soft-deleted only; change category | allowed | block on deleted | MC-14 |
| C4(h) | `complete_task_post_handling` path that calls `_update_item_in_session` with a category change while A active | 409; nothing written by that command | guard only in `update_item` (the public function) | MC-14 "covers both" |
| C4(i) | A `resolved_early` only (via `PR` while T `pending`); change category | allowed; category changed | write the guard's query as `state NOT IN (resolved, failed)` (a hand-typed terminal list) → 409 | MC-14 "terminal does not block", §14F F1, master plan §9 rule 16 |
| C5(a) | A active on I (`article_number SR-x`); `create_task` for `SR-x` with `item_category_id = K2` | 409 with the same message; no task row, no task note, no customer row, no change to I (counts in W before == after) | guard after the first write / raise outside the transaction | MC-14 row 5, §14D D3, C30 |
| C5(b) | same with `item_category_id = K` | task created; I unchanged | — | MC-14 |
| C5(c) | same with the category omitted from the item payload | task created; I's category unchanged (`exclude_unset`) | drop the `model_fields_set` term → refuses | MC-14 "made exact" |
| C5(d) | I with no active assignment; `create_task` with `K2` | task created; I now in K2 (today's behaviour) | — | MC-14 "behaves as today" |
| C5(e) | `find_or_create_item` via `POST /api/v1/items/find-or-create` semantics (call the command with the route's ctx) with a different category while A active | 409 | — | MC-14 second caller |
| C6(a) | A `in_queue`; raw `quantity_in_queue = 0`; `delete_task(T)` | one repair record `trigger == "inline:delete_task"` | — | §12A trigger set |
| C6(b) | same drift; `remove_item_from_task(T, I)` | `inline:remove_item_from_task` | — | §12A |
| C6(c) | same drift; `delete_item(I)` | `inline:delete_item` | — | §12A |
| C7(a) | two sessions: `remove_item_from_task(T, I)` and `CR([I on R])` for a not-yet-assigned I, barrier-released | afterwards: no active assignment exists for an item that is not T's PRIMARY (either the creation was refused `item_not_task_primary` after waiting, or it was created and then removed) | drop the new Task lock — **interleaving not forced**; reviewer verifies the lock statement | MC-14 (U16, C33) |
| C7(b) | `delete_item(I)` vs `CR([I on R])`, barrier-released | no active assignment on a deleted item (creation refused `item_not_found`, or created then removed) | drop the new Item lock — same caveat | MC-14 (U16) |

## 7. Notes

- Sizing: 27 criterion rows in 7 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- Round 9 (2026-09-19): C4(i) added — the category guard reads the active frozenset, so the sixth
  terminal state does not block a category change. This phase depends on 8; `PR` (phase 9) is
  APPROVED before 11 in the default order — if the coordinator reorders, C4(i)'s fixture may reach
  `resolved_early` through `move_assignment(in_queue → resolved_early)` instead.
- C1(c) records its own construction difficulty deliberately: the only way a task holds two
  non-deleted assignments is a terminal one plus an active one for the same item on two rows. The
  implementer builds exactly that.
- C4(d) shows the item with a NULL category **after** assignment (raw SQL) because creation refuses
  a category-less item (`item_has_no_category`); the row tests the guard's None-awareness, not a
  reachable user path.
- C7 rows are declared unable to force their interleaving (master plan §9 rule 9).
- The 409 message is the ratified sentence, verbatim, no leading identity token (master plan §5).

## 8. Review log

(empty)
