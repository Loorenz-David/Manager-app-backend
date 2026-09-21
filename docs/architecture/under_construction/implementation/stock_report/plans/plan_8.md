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

New: `bm/domain/stock_report/serializers.py` (`serialize_stock_task_assignment`, `serialize_item_compact`, `serialize_task_compact` — master plan §6.1; **due in this phase** by the owner ruling of 2026-09-21, §9B ruling 2), `app/tests/unit/domain/stock_report/test_serializers.py`;
`bm/services/commands/stock_report/requests/__init__.py` (or extended if phase 3 created it),
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

Every outcome in this table is computed from **F0**'s own values (I `quantity 4`, R `quantity_requested 10`, goal G awaiting 0) plus this row's own deltas, side effects included. Where a row names a second task or item, it is a copy of F0's unless stated. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.

Tenancy rows (C1(c), C6(f)) use a **cross-workspace reference**: the foreign entity is otherwise a valid target of this request (same category, same criteria, same PRIMARY link), so tenancy is the only reason the call refuses.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `stock_report_item_id` absent | refused(`stock_report_item_not_found` @ 0) | delete the phase-3 `stock_report_item_not_found` existence check (`create_stock_task_assignments.py`, definition site) | MC-13 phase 3 |
| C1(b) | R soft-deleted | same reason | drop `is_deleted` filter | MC-13, MC-16 |
| C1(c) | R belongs to the foreign workspace | same reason | drop `workspace_id` filter | MC-13, M4 |
| C1(d) | `task_id` absent | `task_not_found` | delete the phase-3 task-existence check (`create_stock_task_assignments.py`) → the absent `task_id` falls through to `item_not_task_primary` | MC-13 |
| C1(e) | `item_id` absent | `item_not_found` | delete the phase-3 item-existence check (`create_stock_task_assignments.py`) → the absent `item_id` falls through to `item_not_task_primary` | MC-13 |
| C1(f) | I linked to T as RELATED (a second item is PRIMARY) | `item_not_task_primary` | accept any role | MC-13 (owner: PRIMARY only) |
| C1(g) | I's PRIMARY link has `removed_at` set | `item_not_task_primary` | drop `removed_at IS NULL` | MC-13 |
| C1(h) | T `failed` | `task_failed_or_cancelled` | drop `failed` from the refused task-state set of the phase-3 `task_failed_or_cancelled` check (`create_stock_task_assignments.py`) → phase 5 reaches `move_assignment(is_creation=True, target=failed)` and raises `IllegalAssignmentMove` (500), not a refusal | MC-13, §5 r3 |
| C1(i) | T `cancelled` | `task_failed_or_cancelled` | allow cancelled | MC-13 |
| C1(j) | I already active on another row R2 | `item_already_assigned`; **and `count_writes(statements, {"stock_task_assignments"}) == 0` over the call** (`record_statements`) — same reason as C1(k): the index is keyed on the item, not the row, so without this clause the row cannot fail (owner card A, 2026-09-21) | narrow the phase-3 pre-check to the same row only (`create_stock_task_assignments.py`) → phase 5 attempts the INSERT, `uix_stock_task_assignments_item_active` raises and the backstop answers the same 422 `item_already_assigned` — **only the `count_writes == 0` clause reddens** | MC-13, MC-4 |
| C1(k) | I already active on R | `item_already_assigned`; **and `count_writes(statements, {"stock_task_assignments"}) == 0` over the call** (`record_statements`) — the pre-check refuses *before* attempting the write, which is the only observable that separates it from the `IntegrityError` backstop (owner card A, 2026-09-21; master plan §9 rule 7, fifth ratified use) | delete the phase-3 `item_already_assigned` pre-check (`create_stock_task_assignments.py`) → phase 5 attempts the INSERT, `uix_stock_task_assignments_item_active` raises, the backstop still answers 422 `item_already_assigned` — so the *reason* clause stays green and **only the `count_writes == 0` clause reddens.** That is the point of the clause | MC-13 |
| C1(l) | I `item_category_id NULL` | `item_has_no_category` | delete the phase-3 `item_has_no_category` check (`create_stock_task_assignments.py`) → the NULL-category item falls through to `category_mismatch` | MC-13, §9A rule 2 |
| C1(m) | I in K2, R in K | `category_mismatch` | drop the row-category ↔ item-category comparison in phase 3 (`create_stock_task_assignments.py`) → the K2 item passes the matcher (F0's properties still derive `wood_group = Teak`) and is created on the K row | MC-13, M8 |
| C1(n) | I in K2 **and** properties mismatching | 422 `category_mismatch` (not 409) | evaluate the matcher first | MC-13 precedence (U18) |
| C1(o) | entries `[valid, task_not_found]` | refused(`task_not_found` @ 1); `details` has one element; nothing written for entry 0 | apply the valid entry | MC-13 all-or-nothing |
| C1(p) | A on (T, I) created by `CR` (T `pending` → `in_queue`), then `move_assignment(in_queue → awaiting)` and `move_assignment(awaiting → resolved)` — the intermediate move is required, `awaiting → resolved` is the only Scanner exit (MC-1); `CR([I on R])` again | refused(`already_processed_by_scanner` @ 0); nothing written | drop the check → a second assignment is born and waits forever | §14F F9 / P44, MC-13 phase 3 |
| C1(q) | A on (T, I) `resolved_early` (`move_assignment(in_queue → resolved_early)`); `CR([I on R2])` (another row, same pair) | `already_processed_by_scanner` | check only the same row | §14F F9 ("on any row") |
| C1(r) | A on (T, I) `resolved`; a **new** task T2 with PRIMARY I (a second `TaskItem`, T's link `removed_at` set); `CR([I on R], task T2)` | created (`in_queue`) | **both halves, or it is inert** (measured): drop `StockTaskAssignment.task_id.in_(task_ids)` from `_lookup_processed_pairs` **and** key the membership test on `item_id` (definition site). The membership change alone does not redden | §14F F9 ("a new task for the same item … is not affected") |
| C1(s) | A on (T, I) `resolved` **and soft-deleted** (a user unassigned it); `CR([I on R])` | created | count deleted assignments → refused | §14F F9 ("non-deleted") |
| C1(t) | A on (T, I) `resolved` **and** I linked to T as RELATED (raw `TaskItem.role` change after the fixture) | `item_not_task_primary` (comes first) | swap the two checks | MC-13 order (adjacent pair `item_not_task_primary` → `already_processed_by_scanner`) |
| C1(u) | A on (T, I) `resolved` **and** T `failed` (raw) | `already_processed_by_scanner` (comes before `task_failed_or_cancelled`) | swap the two checks | MC-13 order (adjacent pair `already_processed_by_scanner` → `task_failed_or_cancelled`), §14F F9 |
| C2(a) | same `item_id` in entries 0 and 2 (two tasks) | refused: `duplicate_item_in_batch` for indices 0 **and** 2 | list only the later index | MC-13 phase 1 |
| C2(b) | same `task_id` in entries 0 and 1 | `duplicate_task_in_batch` @ 0 and 1 | drop the repeated-`task_id` detection from phase 1, keeping only `item_id` (`create_stock_task_assignments.py`) → both entries reach phase 3 and the answer becomes `item_not_task_primary` @ 1 | MC-13 phase 1 |
| C2(c) | (a) plus entry 3 with an absent task | one 422 whose `details` holds all three `{index, reason}` | raise on phase 1 before collecting phase 3 | MC-13 "collected into phase 3's error" |
| C3(a) | R criteria = H8's rule **plus a short, late-alphabet key** — `{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"],"zone":["a1"]}` — because criteria are stored as JSONB and **Postgres orders JSONB keys by length then bytes**, which for the original three keys happens to coincide with alphabetical, so the "sorted failures" sub-check could not fail (measured by the tester, 2026-09-21; L-14). I `properties {}` `q = 1`, no override | raises `StockAssignmentPropertyMismatch` (`409`, `code stock_assignment_property_mismatch`), `details == [{index: 0, stock_report_item_id: R, task_id: T, item_id: I, failures: [{quantity, value_not_accepted}, {upholstery, missing_on_item}, {wood_group, missing_on_item}]}]`; nothing written | unsorted failures; missing `details` | MC-13 phase 4, MC-12 (H8), M8 |
| C3(b) | (a) resent with `override_property_mismatch: true` | created; `property_mismatch_overridden == true`; state `in_queue`; counters `(1, 0, 0)` | store `false` | MC-13, §9A rule 3, P23 |
| C3(c) | matching entry with `override_property_mismatch: true` | created with `property_mismatch_overridden == false` | store the flag as sent | MC-13 "flag on a matching entry is ignored" |
| C3(d) | after a 409, T is cancelled; retry with override | 422 `task_failed_or_cancelled` (re-evaluated from scratch) | **Sited on real code by the tester, 2026-09-21** (the cell was a class-2 deliberate blank; a site now exists): drop `CANCELLED` from `_TASK_FAILED_OR_CANCELLED_STATES` (`create_stock_task_assignments.py`, definition site) — the same mutation as C1(i), measured to fire on C3(d)'s own `details` assertion | MC-13 retry contract |
| C3(e) | request with an unknown top-level or entry field | `ValidationError` 422 | `extra="ignore"` | MC-13 "unknown fields → 422" |
| C3(f) | `{"entries": []}` | 422 | remove the `min_length=1` constraint on `entries` in `CreateStockTaskAssignmentsRequest` (`requests/__init__.py`, definition site) → `{"entries": []}` no longer raises | MC-13 |
| C4(a) | T `pending` | A `in_queue`; counters `(4, 0, 0)` | set the `TaskStateEnum.PENDING` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` (`bm/domain/stock_report/state_map.py:5`, definition site) to `AWAITING` — **out-of-perimeter, plan 1; see §7** | MC-13 phase 5, §5 r3 |
| C4(b) | T `assigned` | `in_queue`; `(4, 0, 0)` | set the `TaskStateEnum.ASSIGNED` cell of the same map (`state_map.py:6`) to `IN_PROGRESS` — **out-of-perimeter, plan 1; see §7** | §5 |
| C4(c) | T `working` | `in_progress`; `(0, 4, 0)` — moved by the operation, not written by hand | set the `TaskStateEnum.WORKING` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` (`state_map.py:7`, definition site) to `IN_QUEUE` — it kills both of the row's clauses. The §9 rule 3 "write counters directly" shape is **equivalent at this row's boundary** (measured, tester M33a) — **out-of-perimeter, plan 1; see §7** | §5 r3, HC-3 |
| C4(d) | T `stalled` (set by raw SQL) | `in_progress` | set the `TaskStateEnum.STALLED` cell of the same map (`state_map.py:8`) to `IN_QUEUE` — **out-of-perimeter, plan 1; see §7** | §5 (C5) |
| C4(e) | T `ready` | `awaiting`; `(0, 0, 4)`; `G == 4`; `mem == G` | set the `TaskStateEnum.READY` cell of the same map (`state_map.py:9`) to `IN_QUEUE` → kills state, `(0,0,4)` and the `G == 4` credit at once — **out-of-perimeter, plan 1; see §7** | §5, MC-5 |
| C4(f) | T `resolved` | `awaiting`; `G == 4` (a resolved task may be assigned) | refuse resolved | MC-13 last bullet |
| C4(g) | I `quantity 8` | A `quantity 8`; `(8, 0, 0)` | replace `max(item.quantity, 1)` with the literal `1` at the phase-5 insert (`create_stock_task_assignments.py`) → A `quantity 1`, counters `(1,0,0)`. Distinct from C4(h)'s "drop `max(…,1)`": this one keeps a value, that one removes the floor | HC-2a |
| C4(h) | I `quantity` raw-set to `0` | A `quantity 1` | drop `max(…, 1)` → CHECK violation | MC-13 (C21) |
| C4(i) | any creation | `tasks.is_stock_assignment == true` for T | skip the flag | MC-15 (i) |
| C4(j) | any creation | A `created_by_id == U`, `updated_by_id IS NULL`, `updated_at IS NULL` | stamp `updated_*` on creation | MC-17 (U12) |
| C4(k) | two entries on R — a second task T2 with a second item I2 (a copy of I: `quantity 4`, same properties, PRIMARY on T2), **supplied in the request ordered descending by `item_id`**, computed at runtime from the two created ids and never from creation order (ULIDs minted in one millisecond have random relative order — master plan §10) | both created; `(8, 0, 0)`; response lists both in ascending `item_id` | drop **both** ascending-`item_id` sorts — the phase-5 write loop (`create_stock_task_assignments.py:244`) and the response build (`:309`). **Either alone is an equivalent mutant** (measured, tester) | MC-13 phase 5 order |
| C4(l) | response shape | each element is `serialize_stock_task_assignment`'s shape — the fourteen keys of master plan §6.1, with nested `item` (`serialize_item_compact`, images included) and `task` (`serialize_task_compact`). **The cross-check against `GET /items/{client_id}/assignments` moved to plan 13 C6(a) (owner card 2, 2026-09-21): that endpoint is phase 13's, so nothing in this batch can compare the two shapes** | drop the nested `item` load and return the flat columns → the key set shrinks | §9, master plan §9B ruling 2, §6.1 (owner card D, 2026-09-21) |
| C4(m) | **Inherited from phase 7 (the demand path), not this phase's own surface — see §7.** `AD([(category, properties, q)])` creating a new row, then a second `AD` changing that row's `quantity_requested` | after the create: `created_by_id IS NULL`, `updated_by_id IS NULL`, `updated_at IS NULL`. After the quantity change: `updated_by_id` and `updated_at` **still NULL** (unchanged), `quantity_requested` = the new value | `apply_stock_demand.py` (definition site), two sites, each run separately: (i) add `"created_by_id": <any non-NULL user id>` to the step-5 INSERT `values` dict → the create half reddens; (ii) extend the step-7 raw `UPDATE stock_report_items AS r SET quantity_requested = v.q` with `, updated_at = now(), updated_by_id = :actor` → the change half reddens | MC-17 rows "Demand creates a row" and "Demand changes `quantity_requested`"; batch B2 review 1 N4, CF-1, owner card 1 |
| C5(a) | two sessions, each `CR([I on R])` and `CR([I on R2])` with different tasks (same item, two rows), barrier-released after parse | exactly one active assignment on I; the losing call raises `StockAssignmentRefused` with `item_already_assigned`; the winner's counters correct on its row; the loser's row untouched; **and the losing call wrote nothing — `count_writes(statements, {"stock_task_assignments"}) == 0` over it** (`record_statements`), which is the only clause that distinguishes the Item lock from the unique index (owner card 1, 2026-09-21; §9 rule 7). Measured this round: with the lock removed the reason clause stayed green | drop the Item lock (phase 2) → both pass the pre-check, both reach the INSERT, one hits the unique index and the backstop still answers `item_already_assigned` — **so only the `count_writes == 0` clause reddens.** Measured by the tester, 2026-09-21 | MC-4 error contract, M4 |
| C5(b) | **Authored by the owner, card C, 2026-09-21 (lesson L-29).** Two sessions, each `CR` of **two** entries naming the same two items in **opposite request order** — session 1 `[I1 on R1, I2 on R2]`, session 2 `[I2 on R2', I1 on R1']` with distinct tasks — barrier-released after parse, every wait bounded by `asyncio.wait_for` (§9 rule 9) | both calls complete and **neither raises a deadlock**; each item ends with exactly one active assignment; both rows' counters correct | **Corrected 2026-09-21 after implementation (orchestrator; the cell as authored named a site that was never written — L-31).** There is no `sorted(...)` in `create_stock_task_assignments.py`: it passes an unordered `set` to phase 3's approved `lock_items`, and deterministic ascending acquisition comes from **one** statement in `_locks.py:_lock` — `.order_by(model.client_id)` beside `.with_for_update()`. Mutate **there**: delete `.order_by(model.client_id)` (`_locks.py:33`, definition site) → each session locks in the order Postgres returns rows, and the crossing pair can deadlock. Note `sorted(client_ids)` at `:31` is **not** load-bearing for lock order — it only shapes the `IN` list — so mutating it is an expected `EQUIVALENT`; record it as such if run. **Out-of-perimeter, plan 3; see §7.** Authorized fallback (owner card C) stands unchanged: if the deadlock does not reproduce deterministically, record `UNFORCEABLE` with the measured reason and the reviewer performs the structural check | MC-4 deadlock avoidance; §9 rules 4 and 9; §9A L-29; batch B1 re-review S2 |
| C6(a) | A `in_queue` `q = 4` via `CR`; `DL([A])` | counters `(0, 0, 0)`; A `is_deleted true`, `deleted_by_id == U`, `deleted_at == ctx.now`; flag false; events `[stock_task_assignment:deleted {state: in_queue}, stock_report_item:updated]` | delete the `recompute_task_stock_flag(session, workspace_id, assignment.task_id)` **call** in `_remove_assignment.py:21` (call site) → the flag stays `true`; reaches the "flag false" sub-check only — **out-of-perimeter, plan 4; see §7** | §9 "assignment deletion", MC-14 |
| C6(b) | A `awaiting` credited to G (`G == 4`); `DL([A])` | `G == 0`; `mem IS NULL` | delete the `await _uncredit(session, assignment, trigger, now)` call in `apply_goal_effect`'s `from_state == AWAITING` branch (`_goal_credit.py:129`, call site) → `G` stays 4 and the credit memory stays set — **out-of-perimeter, plan 5; see §7** | MC-5 row 5 |
| C6(c) | A resolved (via phase-4 `move_assignment` in the fixture) ; `DL([A])` | no counter change; no `:updated`; `deleted` event; flag false | remove the `if any(value != 0 for value in deltas.values()):` guard around the `stock_report_item:updated` append (`_move_assignment.py:260-261`, definition site) **and** the `event.extra == initial` drop in `coalesce_stock_report_events` (`_events.py`, definition site). **Either alone is equivalent** (measured, tester) — **out-of-perimeter, plan 4; see §7** | MC-19, MC-15 |
| C6(d) | `DL([A, "sta_absent"])` | `NotFound` naming the absent id; A **not** deleted | delete the found ones | §9 "all-or-nothing" (MC-13 batch rule applied to delete), M1 |
| C6(e) | `DL([A_deleted])` (already soft-deleted) | `NotFound`; nothing written | drop the `is_deleted.is_(False)` predicate from the discovery filter **and** the post-lock re-read's `if assignment.is_deleted` branch (`delete_stock_task_assignments.py`). **Dropping only the discovery filter is equivalent — the re-read catches it** (measured, tester) | MC-16 |
| C6(f) | `DL([A_foreign])` (foreign workspace) | `NotFound` | drop `workspace_id` filter | M4 |
| C6(g) | T has A (`in_queue`, via `CR`) and B — the only reachable second assignment: a **`failed`** one on the same item, built as `CR([I on R2])` → `move_assignment(→ failed)` **before** A is created, so neither active index nor §14F F9 applies; `DL([A])` | flag stays true | drop the "any non-deleted assignment of this task" term from `recompute_task_stock_flag`'s predicate (`consistency.py:expected_task_flag`) → the flag goes false — **out-of-perimeter, plan 3; see §7** | MC-15 (P21), §14F F9 (owner card B, 2026-09-21) |
| C6(h) | `DL([A, B])` two assignments on R | response `{"deleted_client_ids": [A, B]}`; one `:updated` for R (coalesced) | dispatch the delete events without `coalesce_stock_report_events` (`delete_stock_task_assignments.py`, call site) → two `:updated` for R. Same mutant *shape* as C7(a), different call site — both runs recorded (L-28) | §6.5, MC-19 |
| C6(i) | A `resolved_early` (via `move_assignment(in_queue → resolved_early)`, credited to G, `G == 4`); `DL([A])` | no counter change; no `:updated`; `deleted {state: resolved_early}` event; flag false; `G == 4`, `mem == G` kept | subtract `q` on delete / emit `:updated` — the same two-site edit as C6(c): the `deltas` guard (`_move_assignment.py:260-261`) **and** `coalesce_stock_report_events`'s `event.extra == initial` drop. Either alone is equivalent (measured, tester); this cell's own bite is the `resolved_early` credit staying at `G == 4` | §14F F1–F2, F4, MC-19 ("deleting a terminal assignment moves no counter") |
| C7(a) | `CR` with two entries on R | dispatched list has exactly two `:created` and **one** `:updated` for R with the final counters | skip coalescing → two `:updated` | MC-19 net-change |
| C7(b) | `CR` that fails at phase 3 | `capture_dispatch` list empty | dispatch inside the block | MC-19 "nothing on a rolled-back request" |
| C7(c) | A `in_queue` via `CR`; raw `quantity_in_queue = 0`; `DL([A])` | one repair record with `trigger == "inline:delete_assignments"` | wrong trigger string | §12A trigger set |
| C8(a)–C8(d) | `POST /api/v1/stock-report/assignments` as admin / manager / worker / seller | reached / reached / reached / 403 | `require_roles([...])` on `POST /api/v1/stock-report/assignments` (`bm/routers/api_v1/stock_report.py`, route decorator) — four mutants, one per sub-row, each run separately: drop `ADMIN` → (a) reddens · drop `MANAGER` → (b) · drop `WORKER` → (c) · add `SELLER` → (d) | MC-18 |
| C8(e)–C8(h) | `POST /api/v1/stock-report/assignments/delete` as admin / manager / worker / seller | reached / reached / reached / 403 | `require_roles([...])` on `POST /api/v1/stock-report/assignments/delete` — the same four mutants, one per sub-row | MC-18 |
| C8(i) | router unit test: a faked `StockAssignmentRefused(details=[...])` | status 422, body `{"error", "ok": false, "code": "stock_assignment_refused", "details": [...]}` | render through `build_err` (drops `code`) | MC-13 envelope (C25) |
| C8(j) | a faked `StockAssignmentPropertyMismatch` | status 409 with `code stock_assignment_property_mismatch` and `details` | remove `StockAssignmentPropertyMismatch` from the router's explicit-rendering branch (`stock_report.py`, call site) → `build_err` renders `{"error", "ok"}` only, dropping `code` and `details` (status stays 409) | MC-13 envelope |

## 7. Notes

- **L-20, 2026-09-21 (lands first).** Relocating a row's test to a narrower surface is a criterion change and is the owner's alone. C4(m)'s relocation to the demand test file is owner-authorized (batch B2 card 1, 2026-09-21) and is the only one in this phase; no implementer or tester may make another.
- **Perimeter extension for mutation probing (2026-09-21 fold).** Named mutations in §6 land in files belonging to APPROVED phases: `bm/domain/stock_report/state_map.py` (plan 1 — C4(a), C4(b), C4(d), C4(e)), `_remove_assignment.py` (plan 4 — C6(a)), `_move_assignment.py` (plan 4 — C6(c)), `_goal_credit.py` (plan 5 — C6(b)), `consistency.py` (plan 3 — C6(g)), `_locks.py` (plan 3 — C5(b), added 2026-09-21 when the row's real arming site was found), `criteria_matcher.py` (plan 2 — the matcher rows; **added 2026-09-21 after the tester probed it without a declaration covering it**, the same omission that cost batch B2 a round), and `apply_stock_demand.py` (plan 7 — C4(m), already declared). Applying and reverting a probe in these files is **authorized for this phase's tester**; leaving any change is not. Collateral reds, measured by reading: each `state_map.py` cell mutant reddens exactly one parametrized case of plan 1's `test_state_map.py::test_task_state_map_is_exact`, and every F0-based test of plans 4–11 when the mutated cell is `PENDING`; plan 1 C6(a) and C6(j) stay **green** under all four (the key set and the value *set* are unchanged). That is expected, not a regression. **A named mutation is never declined for living in another phase's file** (batch B2 lost a round to exactly that).
- **Owner cards ruled 2026-09-21 (batch C1 projection).** Card A: C1(j) and C1(k) gained a `count_writes == 0` clause — without it the partial unique index plus the `IntegrityError` backstop reproduce the same 422 and the same reason, so both rows could not fail (master plan §9 rule 7, fifth ratified use). Card B: C6(g)'s fixture was unbuildable — "another item" is impossible because a task holds one active PRIMARY item, and the same-item form is refused by §14F F9; the second assignment is now a **`failed`** one built before A. Card C: C5(b) authored, the caller's lock order. Card D: C4(l) re-stated to the fourteen-key shape.

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

**Implementer, 2026-09-21 (batch C1, Sonnet).** Built: `serializers.py` (three functions,
due-in-this-phase per §9B ruling 2); the two structured errors in `errors/stock_report.py`;
`requests/__init__.py` (`StockTaskAssignmentEntry`, `CreateStockTaskAssignmentsRequest`,
`DeleteStockTaskAssignmentsRequest` — `SetStockReportItemPriority(Order)Request` deliberately
**not** added: they belong to phase 12 and charter rule 4 forbids a name with no caller yet);
`create_stock_task_assignments.py` and `delete_stock_task_assignments.py`;
`coalesce_stock_report_events` in `_events.py`; the two routes plus structured-error rendering in
`stock_report.py`. C4(m)'s test landed in `test_apply_stock_demand.py` per §7's perimeter
extension — no production change there, both authorship clauses were already true.

**Judgment calls:**
- Phase-1 duplicate check order: item_id checked before task_id when an entry could name either
  (not specified by the plan; no criterion exercises both at once).
- Phase-4 matcher: collects **every** post-phase-3 entry's mismatch into one
  `StockAssignmentPropertyMismatch` (the plan's C3(a) sentence is singular but the batch is
  all-or-nothing elsewhere; no criterion row tests two simultaneous mismatches).
- `delete_stock_task_assignments`'s response order and the "re-read after lock" pass over
  `locked_assignments` (a race-defence beyond what any C6 row forces) follow §9 rule 4's standing
  instruction, not a named criterion.
- Router body models (`_CreateStockTaskAssignmentsBody`, `_DeleteStockTaskAssignmentsBody`) are
  fully-typed FastAPI models, matching this codebase's established convention (e.g.
  `item_upholsteries.py:_CreateBody`) rather than a raw-dict passthrough — master plan §6.5/§6.6
  registers only the command-level request classes, not a router-level shape, so this is filled
  in as a judgment call. Consequence: an actual HTTP client sending an unrecognized top-level
  field gets FastAPI's own validation error, not `StockAssignmentRefused`/`ValidationError` — C3(e)
  ("unknown field → `ValidationError` 422") is proven at the `CR()`/command boundary only, per the
  plan's own fixture shorthand, which bypasses the router. Flagging this because a future reviewer
  or the frontend may expect uniform error envelopes across the whole surface; no criterion in this
  phase asks for it.

**C5(b) — the caller's lock order (owner card C / L-29).** The named mutation site ("remove the
`sorted(...)` from the Item-lock acquisition in `create_stock_task_assignments.py`, definition
site") does not exist in the file I wrote: my command passes an unordered Python `set` of
`item_ids` straight to phase-3's approved `lock_items` helper (`_locks.py`), whose single
`SELECT … ORDER BY client_id … FOR UPDATE` already guarantees deterministic ascending lock
acquisition in one atomic statement, regardless of the order ids arrive in. `_locks.py` is out of
this phase's perimeter (phase 3, APPROVED) and I have not touched it. I believe C5(b)'s production
requirement — "acquire the locks in sorted order, deterministically" — is met by construction via
that one call, with nothing left for this phase to add. I did not build a two-session test for
C5(b) (unlike C5(a), which I did build — see the implementer handoff): there is no
phase-8-authored logic path for such a test to exercise red→green against, and forcing the
opposite-order interleaving is exactly the kind of adversarial proof this project's tester owns.
Flagging this now so the tester sites its arming attempt against `_locks.py`'s single-statement
lock, not a `sorted()` call in my file that was never written — an L-25 site-mismatch caught before
arming time rather than during it.

**C4(l)'s second clause** ("`set(element) == set(GET /items/{client_id}/assignments`'s element)")
is not exercised: that endpoint is phase 13, not yet built in this batch. My tests assert the
fourteen-key shape directly instead.

**Tester (verification engineer), 2026-09-21 (batch C1, Opus).** All 67 criterion rows have a
disposition. 29 tests added, 0 removed, 1 renamed; no production change (`git diff
6eaf2d3..HEAD -- app/beyo_manager/` empty). Full ledger:
`handoffs/tester/2026-09-21_batch_C1_test_1_handoff.md`.

*Judgment calls and re-sitings (each shows both runs in ledger table 1):*
- **C4(k)** — the named mutation (drop the phase-5 write-loop sort) is an **equivalent mutant**:
  the response is sorted a *second* time at `create_stock_task_assignments.py:309`
  (`sorted(created, key=item_id)`), so either sort alone keeps the row's observable ascending.
  Armed by removing **both** sorts. Backfill proposed.
- **C4(c)** — the cell's "write counters directly" names no file/site (rule 11). The §9 rule 3
  ORM-write shape was run (`_apply_counter_delta`, value sourced from the identity-mapped
  instance) and is **equivalent at this row's boundary** — a single create reads the same value
  it would have computed. Re-sited to the `state_map.py` WORKING cell, which is what makes both
  of the row's clauses true. Backfill proposed.
- **C1(r)** — the cell's mutant applied to the *membership test* alone is inert: the
  `_lookup_processed_pairs` query already filters `task_id.in_(task_ids)`. "Key the check on
  `item_id` alone" only exists as query-plus-test; both runs recorded.
- **C6(c) / C6(i)** — "no `:updated` for a terminal delete" is guarded **twice**: the
  `deltas` guard in `_move_assignment.py:260` *and* `coalesce_stock_report_events`' drop of a
  payload equal to the row's initial values. Either alone is equivalent; armed by removing both.
- **C6(e)** — the named mutant (drop `is_deleted.is_(False)` from discovery) is caught by the
  implementer's post-lock re-read, so it is equivalent; armed by removing the discovery filter
  **and** the re-read.
- **C7(b)** — "dispatch inside the block" is equivalent by construction: a phase-3 refusal raises
  before any dispatch statement and `events` is empty at that point, so no placement of the
  dispatch call can make the row fail. Recorded `EQUIVALENT`, row noted as structurally true.
- **C3(a)** — the "sorted failures" sub-check cannot fail **with this row's own fixture**: the
  criteria live in a JSONB column and Postgres stores keys by (length, bytewise), which for
  `quantity` / `upholstery` / `wood_group` is already alphabetical (measured:
  `'{"wood_group":1,"quantity":2,"upholstery":3}'::jsonb` -> `quantity, upholstery, wood_group`).
  The "missing `details`" sub-check is armed. Fixture fold proposed (L-14).
- **C5(b)** — built as the owner's card C describes (two sessions, two items, opposite request
  order, one barrier). The named mutation (delete `.order_by(model.client_id)` from
  `_locks.py:_lock`) leaves the test green: with the `IN` list still `sorted(client_ids)` both
  sessions receive rows in the same physical order, so the deadlock does not reproduce.
  **`UNFORCEABLE`** per the owner's authorized fallback; the structural check is named in the
  handoff. The test is kept: it is the row's outcome (both calls complete, one active assignment
  per item, both rows' counters correct) and it holds.
- **C3(e)** — the implementer's fixture sent `{"entries": [], "unexpected": True}`, which refuses
  for **C3(f)'s** reason as well, so `extra="ignore"` left it green. Fixture strengthened to a
  valid entry plus an unknown field, and the entry-level clause added.
- **C3(d)** — sited on real code after all: the retry's `task_failed_or_cancelled` comes from the
  same cancelled-state check C1(i) names, and C1(i)'s mutation reddens C3(d)'s own assertion.
  `ARMED-SHARED`; backfill proposed.

*Blocked:* **C5(a)** `BLOCKED-PLAN` and **C4(l)** (second clause) `BLOCKED-PLAN` — see the
handoff's owner cards 1 and 2. No `BLOCKED-PRODUCTION` row: production behaved correctly under
every probe.
