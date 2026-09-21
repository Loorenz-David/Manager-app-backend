# Plan 8 — Assignments: batch create with the matcher and override, batch delete, race error, role cells

```
state: NOT_STARTED
phase: 8 of 15
depends_on: 2, 5 (APPROVED)
projection: mandatory (lock order, race row, creation writes)
complex: yes — three lock classes in order, a two-session race row, all-or-nothing batches
```

## 1. Goal

The two batch commands users call from the board: create assignments (MC-13's six phases with the
round-9 refusal `already_processed_by_scanner`, the matcher with the override retry, the race error
contract) and delete assignments (through `remove_assignment`), their routes and eight role cells,
and the request-level event coalescing. **Not in this phase:** the processed webhook (9), task sync
(10), hooks (11), reads (12–13), the Scanner delete webhook (13A).

## 2. Read first

1. `master_plan.md` §6.1, §6.4 (the two structured errors and the closed reason vocabulary), §6.5
   (`create_stock_task_assignments.py`, `delete_stock_task_assignments.py`, `_events.py` coalesce,
   `requests/__init__.py`), §6.6 (routes and the explicit error rendering), §6.7, §9 rules 2–4, 6, 9, 16.
2. Intention §4.2, §4A MC-4 (error contract on the race path), §5 rule 3, §9 (API table, "assignment
   deletion" paragraph), §9A, §9C MC-13 in full **as amended by §14F F9 / P44** (the refusal
   `already_processed_by_scanner`, placed after `item_not_task_primary`), MC-12 (what the matcher
   returns), §4B MC-15 (writer i), MC-17 (creation, delete rows), §9D MC-19 (creation and deletion
   rows; net-change rule), §9E MC-18 (the four cells per operation), §12A closed trigger set, §14C
   C21, C25, C29, U18; §14E E12 and §14F F8 (why the coalescer must also drop an `:updated` for an
   entity that is `:deleted` in the same request — one request can delete several rows in 13A).
3. Plans 2, 4, 5 as shipped and their Review logs (matcher API; `move_assignment` with
   `is_creation`; `remove_assignment`; goal credit on `∅ → awaiting`).
4. Repo: `bm/services/commands/items/batch_create_item_issues.py` (all-or-nothing batch precedent:
   set-difference validation naming missing ids), `bm/routers/api_v1/auth.py:120-130` (`code`
   rendering precedent), `bm/models/tables/tasks/task_item.py` (PRIMARY predicate), plan 3's
   `_locks.py`.

## 3. Dependencies

Phases 2 and 5 APPROVED.

## 4. Files expected to change

New: `bm/services/commands/stock_report/requests/__init__.py` (or extended if phase 3 created it),
`create_stock_task_assignments.py`, `delete_stock_task_assignments.py`;
`app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py`,
`test_delete_stock_task_assignments.py`, `test_create_stock_task_assignments_race.py`.
Edited: `bm/errors/stock_report.py` (two classes), `bm/services/commands/stock_report/_events.py`
(`coalesce_stock_report_events`), `bm/routers/api_v1/stock_report.py` (two routes + explicit
rendering), `app/tests/unit/routers/api_v1/test_stock_report_router.py` (cells + rendering).

## 5. Tasks

1. Requests per master plan §6.5 (`extra="forbid"` on the create request and its entry model; ≥ 1
   entry).
2. `create_stock_task_assignments(ctx)`: phase 0 parse; phase 1 duplicates (`item_id`, `task_id`
   repeated → reasons with every index); `maybe_begin`; phase 2 locks — `lock_items`, `lock_tasks`,
   `lock_stock_report_items` over the ids named (existing ones only, each ascending); phase 3 per
   entry in order, first failing reason: `stock_report_item_not_found` (absent / deleted / other
   workspace) · `task_not_found` · `item_not_found` · `item_not_task_primary` (`TaskItem` with
   `task_id`, `item_id`, `role = primary`, `removed_at IS NULL`) · **`already_processed_by_scanner`**
   (a non-deleted assignment with this `(task_id, item_id)` — on **any** row — whose state is
   `resolved` or `resolved_early`; §14F F9) · `task_failed_or_cancelled` ·
   `item_already_assigned` (any non-deleted active assignment for the item) · `item_has_no_category` ·
   `category_mismatch`; any phase 1/3 failure → `StockAssignmentRefused(details=[{index, reason}, …])`
   (nothing written); phase 4 `evaluate_stock_criteria(item, row.properties)` per entry; failures
   without override → `StockAssignmentPropertyMismatch(details=[{index, stock_report_item_id, task_id,
   item_id, failures: [{key, reason}] sorted by key}])`; phase 5 per entry ascending `item_id`: insert
   `StockTaskAssignment(state = ASSIGNMENT_STATE_BY_TASK_STATE[task.state], quantity = max(item.quantity,
   1), property_mismatch_overridden = (failed and overridden), created_by_id = ctx.user_id or None)`,
   flush, `move_assignment(..., target=that state, is_creation=True, trigger="create_assignments",
   actor_user_id=ctx.user_id)`, `set_task_stock_flag(task_id, True)`; collect events; after the block
   `dispatch(coalesce_stock_report_events(events, initial_row_values=<values read at the row lock>))`;
   return `{"stock_task_assignments": [serialize_stock_task_assignment(...)]}` — the **full**
   fourteen-key read shape with nested `item` and `task`, **not** the seven flat columns this task
   previously named (**owner ruling 2026-09-21**: the create response and
   `GET /items/{client_id}/assignments` return one shape, so a frontend can render a newly created
   assignment without a second request). This makes `serialize_stock_task_assignment`,
   `serialize_item_compact` and `serialize_task_compact` (master plan §6.1) **due in this phase**
   rather than in phase 13, and the command must load each assignment's `item` (with images) and
   `task`. The criterion rows that name the old seven-key shape are superseded by this ruling and
   are re-stated during the batch C fold; the reviewer verifies against this text. `IntegrityError` naming either assignment index inside
   phase 5 is mapped to `StockAssignmentRefused` with `item_already_assigned` (backstop).
3. `delete_stock_task_assignments(ctx)`: parse; `maybe_begin`; discover `(stock_report_item_id,
   task_id)` unlocked; lock tasks → rows → assignments (ascending); re-read; any id absent, deleted or
   foreign → `NotFound` naming the ids (nothing written); per assignment ascending `client_id`:
   `remove_assignment(..., trigger="delete_assignments")`; coalesce; dispatch; return
   `{"deleted_client_ids": [...]}`.
4. `coalesce_stock_report_events(events, *, initial_row_values)`: per row keep the **last** `:updated`
   and drop it when its payload equals the row's initial values, or when the row also has `:created`,
   **or when the row also has `:deleted`** (MC-19 "no `:updated` for the deleted row", applied per
   request: a 13A request deleting two rows of one group shifts the second before deleting it); per
   assignment keep the last event of each kind; preserve first-seen order. The `:deleted` clause is
   exercised by plan 13A C5(b); it has no row here because no phase-8 request deletes a row.
5. Router: the two routes; for the two structured errors render
   `JSONResponse({"error": message, "ok": False, "code": error.code, "details": error.details},
   status_code=error.http_status)`; everything else `build_err`.
6. Tests first from the table. From this phase on, assignments in fixtures are created **through the
   command**.

## 6. Criteria

Fixture: **F0** (R with goal G, task T `pending`, item I `q = 4`, PRIMARY). `CR(entries)` =
`create_stock_task_assignments(make_ctx(role worker U, incoming_data={"entries": entries}))`; `DL(ids)`
= the delete command. "refused(reason @ i)" = raises `StockAssignmentRefused` (`http_status 422`,
`code stock_assignment_refused`) whose `details` contains `{index: i, reason}`; nothing written; no
dispatch. Every success row ends with `assert_stock_report_clean`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `stock_report_item_id` absent | refused(`stock_report_item_not_found` @ 0) | — | MC-13 phase 3 |
| C1(b) | R soft-deleted | same reason | drop `is_deleted` filter | MC-13, MC-16 |
| C1(c) | R belongs to the foreign workspace | same reason | drop `workspace_id` filter | MC-13, M4 |
| C1(d) | `task_id` absent | `task_not_found` | — | MC-13 |
| C1(e) | `item_id` absent | `item_not_found` | — | MC-13 |
| C1(f) | I linked to T as RELATED (a second item is PRIMARY) | `item_not_task_primary` | accept any role | MC-13 (owner: PRIMARY only) |
| C1(g) | I's PRIMARY link has `removed_at` set | `item_not_task_primary` | drop `removed_at IS NULL` | MC-13 |
| C1(h) | T `failed` | `task_failed_or_cancelled` | — | MC-13, §5 r3 |
| C1(i) | T `cancelled` | `task_failed_or_cancelled` | allow cancelled | MC-13 |
| C1(j) | I already active on another row R2 | `item_already_assigned` | check only the same row | MC-13, MC-4 |
| C1(k) | I already active on R | `item_already_assigned` | — | MC-13 |
| C1(l) | I `item_category_id NULL` | `item_has_no_category` | — | MC-13, §9A rule 2 |
| C1(m) | I in K2, R in K | `category_mismatch` | — | MC-13, M8 |
| C1(n) | I in K2 **and** properties mismatching | 422 `category_mismatch` (not 409) | evaluate the matcher first | MC-13 precedence (U18) |
| C1(o) | entries `[valid, task_not_found]` | refused(`task_not_found` @ 1); `details` has one element; nothing written for entry 0 | apply the valid entry | MC-13 all-or-nothing |
| C1(p) | A on (T, I) driven to `resolved` in the fixture (`move_assignment(awaiting → resolved)`, as C6(c) does); `CR([I on R])` again | refused(`already_processed_by_scanner` @ 0); nothing written | drop the check → a second assignment is born and waits forever | §14F F9 / P44, MC-13 phase 3 |
| C1(q) | A on (T, I) `resolved_early` (`move_assignment(in_queue → resolved_early)`); `CR([I on R2])` (another row, same pair) | `already_processed_by_scanner` | check only the same row | §14F F9 ("on any row") |
| C1(r) | A on (T, I) `resolved`; a **new** task T2 with PRIMARY I (a second `TaskItem`, T's link `removed_at` set); `CR([I on R], task T2)` | created (`in_queue`) | key the check on `item_id` alone → refused | §14F F9 ("a new task for the same item … is not affected") |
| C1(s) | A on (T, I) `resolved` **and soft-deleted** (a user unassigned it); `CR([I on R])` | created | count deleted assignments → refused | §14F F9 ("non-deleted") |
| C1(t) | A on (T, I) `resolved` **and** I linked to T as RELATED (raw `TaskItem.role` change after the fixture) | `item_not_task_primary` (comes first) | swap the two checks | MC-13 order (adjacent pair `item_not_task_primary` → `already_processed_by_scanner`) |
| C1(u) | A on (T, I) `resolved` **and** T `failed` (raw) | `already_processed_by_scanner` (comes before `task_failed_or_cancelled`) | swap the two checks | MC-13 order (adjacent pair `already_processed_by_scanner` → `task_failed_or_cancelled`), §14F F9 |
| C2(a) | same `item_id` in entries 0 and 2 (two tasks) | refused: `duplicate_item_in_batch` for indices 0 **and** 2 | list only the later index | MC-13 phase 1 |
| C2(b) | same `task_id` in entries 0 and 1 | `duplicate_task_in_batch` @ 0 and 1 | — | MC-13 phase 1 |
| C2(c) | (a) plus entry 3 with an absent task | one 422 whose `details` holds all three `{index, reason}` | raise on phase 1 before collecting phase 3 | MC-13 "collected into phase 3's error" |
| C3(a) | R criteria = H8's rule (`{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"]}`), I `properties {}` `q = 1`, no override | raises `StockAssignmentPropertyMismatch` (`409`, `code stock_assignment_property_mismatch`), `details == [{index: 0, stock_report_item_id: R, task_id: T, item_id: I, failures: [{quantity, value_not_accepted}, {upholstery, missing_on_item}, {wood_group, missing_on_item}]}]`; nothing written | unsorted failures; missing `details` | MC-13 phase 4, MC-12 (H8), M8 |
| C3(b) | (a) resent with `override_property_mismatch: true` | created; `property_mismatch_overridden == true`; state `in_queue`; counters `(1, 0, 0)` | store `false` | MC-13, §9A rule 3, P23 |
| C3(c) | matching entry with `override_property_mismatch: true` | created with `property_mismatch_overridden == false` | store the flag as sent | MC-13 "flag on a matching entry is ignored" |
| C3(d) | after a 409, T is cancelled; retry with override | 422 `task_failed_or_cancelled` (re-evaluated from scratch) | — | MC-13 retry contract |
| C3(e) | request with an unknown top-level or entry field | `ValidationError` 422 | `extra="ignore"` | MC-13 "unknown fields → 422" |
| C3(f) | `{"entries": []}` | 422 | — | MC-13 |
| C4(a) | T `pending` | A `in_queue`; counters `(4, 0, 0)` | — | MC-13 phase 5, §5 r3 |
| C4(b) | T `assigned` | `in_queue`; `(4, 0, 0)` | — | §5 |
| C4(c) | T `working` | `in_progress`; `(0, 4, 0)` — moved by the operation, not written by hand | write counters directly | §5 r3, HC-3 |
| C4(d) | T `stalled` (set by raw SQL) | `in_progress` | — | §5 (C5) |
| C4(e) | T `ready` | `awaiting`; `(0, 0, 4)`; `G == 4`; `mem == G` | — | §5, MC-5 |
| C4(f) | T `resolved` | `awaiting`; `G == 4` (a resolved task may be assigned) | refuse resolved | MC-13 last bullet |
| C4(g) | I `quantity 8` | A `quantity 8`; `(8, 0, 0)` | — | HC-2a |
| C4(h) | I `quantity` raw-set to `0` | A `quantity 1` | drop `max(…, 1)` → CHECK violation | MC-13 (C21) |
| C4(i) | any creation | `tasks.is_stock_assignment == true` for T | skip the flag | MC-15 (i) |
| C4(j) | any creation | A `created_by_id == U`, `updated_by_id IS NULL`, `updated_at IS NULL` | stamp `updated_*` on creation | MC-17 (U12) |
| C4(k) | two entries on R (two tasks/items) | both created; `(8, 0, 0)`; response lists both in ascending `item_id` | — | MC-13 phase 5 order |
| C4(l) | response shape | each element has exactly the seven keys of task 2 | — | §9 |
| C4(m) | **Inherited from phase 7 (the demand path), not this phase's own surface — see §7.** `AD([(category, properties, q)])` creating a new row, then a second `AD` changing that row's `quantity_requested` | after the create: `created_by_id IS NULL`, `updated_by_id IS NULL`, `updated_at IS NULL`. After the quantity change: `updated_by_id` and `updated_at` **still NULL** (unchanged), `quantity_requested` = the new value | `apply_stock_demand.py` (definition site), two sites, each run separately: (i) add `"created_by_id": <any non-NULL user id>` to the step-5 INSERT `values` dict → the create half reddens; (ii) extend the step-7 raw `UPDATE stock_report_items AS r SET quantity_requested = v.q` with `, updated_at = now(), updated_by_id = :actor` → the change half reddens | MC-17 rows "Demand creates a row" and "Demand changes `quantity_requested`"; batch B2 review 1 N4, CF-1, owner card 1 |
| C5(a) | two sessions, each `CR([I on R])` and `CR([I on R2])` with different tasks (same item, two rows), barrier-released after parse | exactly one active assignment on I; the losing call raises `StockAssignmentRefused` with `item_already_assigned`; the winner's counters correct on its row; the loser's row untouched | drop the Item lock (phase 2) → both pass the pre-check → one hits the unique index (500 or the backstop) | MC-4 error contract, M4 |
| C6(a) | A `in_queue` `q = 4` via `CR`; `DL([A])` | counters `(0, 0, 0)`; A `is_deleted true`, `deleted_by_id == U`, `deleted_at == ctx.now`; flag false; events `[stock_task_assignment:deleted {state: in_queue}, stock_report_item:updated]` | — | §9 "assignment deletion", MC-14 |
| C6(b) | A `awaiting` credited to G (`G == 4`); `DL([A])` | `G == 0`; `mem IS NULL` | — | MC-5 row 5 |
| C6(c) | A resolved (via phase-4 `move_assignment` in the fixture) ; `DL([A])` | no counter change; no `:updated`; `deleted` event; flag false | — | MC-19, MC-15 |
| C6(d) | `DL([A, "sta_absent"])` | `NotFound` naming the absent id; A **not** deleted | delete the found ones | §9 "all-or-nothing" (MC-13 batch rule applied to delete), M1 |
| C6(e) | `DL([A_deleted])` (already soft-deleted) | `NotFound`; nothing written | — | MC-16 |
| C6(f) | `DL([A_foreign])` (foreign workspace) | `NotFound` | drop `workspace_id` filter | M4 |
| C6(g) | T has A (active) and B (resolved, another item legal); `DL([A])` | flag stays true | — | MC-15 (P21) |
| C6(h) | `DL([A, B])` two assignments on R | response `{"deleted_client_ids": [A, B]}`; one `:updated` for R (coalesced) | — | §6.5, MC-19 |
| C6(i) | A `resolved_early` (via `move_assignment(in_queue → resolved_early)`, credited to G, `G == 4`); `DL([A])` | no counter change; no `:updated`; `deleted {state: resolved_early}` event; flag false; `G == 4`, `mem == G` kept | subtract `q` on delete / emit `:updated` | §14F F1–F2, F4, MC-19 ("deleting a terminal assignment moves no counter") |
| C7(a) | `CR` with two entries on R | dispatched list has exactly two `:created` and **one** `:updated` for R with the final counters | skip coalescing → two `:updated` | MC-19 net-change |
| C7(b) | `CR` that fails at phase 3 | `capture_dispatch` list empty | dispatch inside the block | MC-19 "nothing on a rolled-back request" |
| C7(c) | A `in_queue` via `CR`; raw `quantity_in_queue = 0`; `DL([A])` | one repair record with `trigger == "inline:delete_assignments"` | wrong trigger string | §12A trigger set |
| C8(a)–C8(d) | `POST /api/v1/stock-report/assignments` as admin / manager / worker / seller | reached / reached / reached / 403 | — | MC-18 |
| C8(e)–C8(h) | `POST /api/v1/stock-report/assignments/delete` as admin / manager / worker / seller | reached / reached / reached / 403 | — | MC-18 |
| C8(i) | router unit test: a faked `StockAssignmentRefused(details=[...])` | status 422, body `{"error", "ok": false, "code": "stock_assignment_refused", "details": [...]}` | render through `build_err` (drops `code`) | MC-13 envelope (C25) |
| C8(j) | a faked `StockAssignmentPropertyMismatch` | status 409 with `code stock_assignment_property_mismatch` and `details` | — | MC-13 envelope |

## 7. Notes

- Sizing: 66 criterion rows in 8 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- **Owner card 1 fold, 2026-09-21.** The count above is the previously derived count **+1**: exactly one criterion row was added to this plan by that fold, verified as a single `^+| C` line in `git diff` (not re-derived by a new script — the published totals and my regex disagree on row shape, and a typed count is the defect this project keeps finding).
- **C4(m) is inherited debt, not this phase's own surface.** Its fixture and both named mutations live in `apply_stock_demand.py` (phase 7's perimeter), because the MC-17 demand-authorship cells were shipped correctly in batch B2 and asserted by nothing (review 1 N4 / CF-1), and phases 6–7 are already VERIFIED — adding the row there would reopen a closed gate. The batch-B2 reviewer routed it here as the next round with capacity. **This phase's perimeter is therefore extended by one file, `apply_stock_demand.py`, for this row only**; the test belongs in the demand test file, not in this phase's own.
- Round 9 (2026-09-19): C1(p)–(u) added for `already_processed_by_scanner` (its two adjacent pairs
  in MC-13's order are each a row); C6(i) added for deleting a `resolved_early` assignment. The
  reason vocabulary of `StockAssignmentRefused` is closed and registered in master plan §6.4. In a
  phase-8 fixture `resolved` / `resolved_early` are reached with phase 4's `move_assignment`
  directly; the webhook that performs them in production is phase 9.
- C5(a): the barrier releases after each session parsed and before phase 2; the loser's failure is
  the **pre-check** reason after waiting on the Item lock (MC-4), so the unique index is never hit
  on the happy path. The `IntegrityError → item_already_assigned` backstop has no deterministic row;
  the reviewer checks it structurally.
- C8 rows use the router unit-test shape; calibration: no ledger rows.
- From this phase on, every fixture's assignments come from `CR`; earlier phases' ORM-inserted
  fixtures stay as they are (they test the operation directly).

## 8. Review log

**Owner, 2026-09-21 — criterion row authored (batch B2 card 1, CF-1).** **C4(m)** added: the demand path must leave `created_by_id` and `updated_*` NULL when it creates a row, and `updated_*` unchanged when it changes `quantity_requested` (MC-17). **No test exists yet — this row is owed by this phase's implementation round.** See §7 for the one-file perimeter extension it carries: the code under test is phase 7's, which is VERIFIED, so the row could not be placed in plan 6 or 7 without reopening a closed gate.

(empty)
