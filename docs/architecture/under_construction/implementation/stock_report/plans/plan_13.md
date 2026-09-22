# Plan 13 — Row deletion cascade, second self-heal trigger, assignment reads and compact serializers

```
state: NOT_STARTED
phase: 13 of 15
depends_on: 12, 8 (APPROVED)
projection: mandatory (cascade order, instrument (c), lock order)
complex: yes — five-class lock order in one transaction, second self-heal trigger
```

## 1. Goal

`DELETE /api/v1/stock-report/items/{client_id}`: the MC-16 cascade (assignments out through
`remove_assignment`, gap closed, row and history soft-deleted, counters repaired to 0 if drifted),
and `GET …/items/{client_id}/assignments` with the two compact serializers and batch-loaded
images, plus eight role cells. **Not in this phase:** documents (14).

## 2. Read first

1. `master_plan.md` §6.1 (serializers), §6.5 (`delete_stock_report_item.py`,
   `list_stock_task_assignments.py`), §6.6, §6.7, §9 rules 3–4, 7.
2. Intention §9 (delete row; GET assignments), §5A MC-16 ("row-deletion cascade order"), MC-1
   "second trigger — row deletion" and instrument **(c)** (fresh `stored_before`), §12A
   (`inline:delete_stock_report_item`), MC-5 row "R soft-deleted, −= q due", MC-17 (user deletes a
   row: `deleted_*` and `updated_*`; assignment deleted; records `deleted_*`), MC-19 (row deletion
   row), MC-18 (two operations), §9B response shapes (`serialize_item_compact`,
   `serialize_task_compact` field lists), §14C C27, C39, P36.
3. Plan 12's `_ordering.py` (`close_priority_gap`), plan 4's `remove_assignment`.
4. Repo: `bm/services/queries/tasks/tasks.py:425-450` (image batch-load pattern with
   `serialize_image_light`), `bm/domain/images/serializers.py:49`, `bm/models/tables/tasks/task.py`
   (the compact fields exist: `task_type`, `priority`, `state`, `title`, `return_source`,
   `ready_by_at`, `return_method`, `created_at`, `updated_at`, `closed_at`, `completed_at`),
   `bm/models/tables/items/item.py` (`article_number`, `sku`, `quantity`, `item_category_snapshot`,
   `item_major_category_snapshot`).

## 3. Dependencies

Phases 12 and 8 APPROVED.

## 4. Files expected to change

New: `bm/services/commands/stock_report/_delete_stock_report_item_cascade.py`, `delete_stock_report_item.py`;
`bm/services/queries/stock_report/list_stock_task_assignments.py`;
`app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py`;
`app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py`.
Edited: `bm/routers/api_v1/stock_report.py` (two routes),
`app/tests/unit/routers/api_v1/test_stock_report_router.py`.

**Corrected by owner card 5, 2026-09-21.** Two entries were dropped from this list because they are
stale, and the reviewer's perimeter check treats a change to either as a finding:
`bm/domain/stock_report/serializers.py` — the three compact serializers **already ship in phase 8**
(owner ruling §9B.2), so this phase adds none; `requests/__init__.py` — `DELETE` takes **no body**
(owner ruling §9B.1 removed `DeleteStockReportItemRequest` entirely), so this phase adds no request
model. The router injects `{client_id}` into `incoming_data` per phase 8A's shipped precedent.

## 5. Tasks

1. `delete_stock_report_item(ctx)`: parse; `maybe_begin`; `acquire_stock_report_order_lock`;
   discover the row's non-deleted assignments and their `task_id`s (unlocked); `lock_tasks`
   ascending; lock the row **and** its priority group in one statement ordered by `client_id`;
   `lock_stock_task_assignments` ascending; re-read; row absent/deleted/foreign → `NotFound("Stock
   report item not found.")`; then call **`cascade_delete_stock_report_item(session, row, *,
   workspace_id, actor_user_id=ctx.user_id, now=ctx.now, trigger="delete_stock_report_item")`**
   (new subordinate module `_delete_stock_report_item_cascade.py`, master plan §6.5 — the command
   is its one caller in this phase; **phase 13A's Scanner delete webhook is its second caller**, with
   `actor_user_id=None` and `trigger="stock_demand_deleted"`, so the cascade must take every stamp
   value from its arguments and never from `ctx`). The cascade, in order:

   **(i) The assignment loop.** For each assignment ascending `client_id`:
   `remove_assignment(..., actor_user_id=actor_user_id, now=now, trigger=trigger)`. Nothing else
   happens inside this loop.

   **(ii) After the loop ends** — once, not per assignment: one fresh `SELECT` of the three
   counters; for each column ≠ 0, one `UPDATE` setting that column to 0 (its recomputed value, since
   no non-deleted assignment remains) with one repair record (`stock_report_item`, R, field,
   `stored_before`, `"0"`, `inline:<trigger>`, NULL author) and a warning. This is MC-1's second
   trigger and MC-16 puts it after every assignment has been moved out; C2(a) and C2(b) both read it
   that way. (Owner card 5, 2026-09-21: the loop boundary was ambiguous in the previous wording.)

   **(iii) Then**: close the gap in the row's group (when priority non-null) — `removed_order` comes
   from a **fresh `SELECT` of the row's `priority_order`**, never from the ORM instance loaded at the
   lock, which is stale after any earlier Core shift in the same transaction (§9 rule 3; see §7 and
   phase 13A C5(b), the only row anywhere that can observe this); soft-delete the row (`is_deleted`,
   `deleted_at = now`, `deleted_by_id = actor_user_id`, **and** `updated_at = now`, `updated_by_id =
   actor_user_id` — **the cascade's own arguments, never `ctx`**: the command passes
   `now=ctx.now, actor_user_id=ctx.user_id`, and phase 13A passes `actor_user_id=None`, so a cascade
   that reads `ctx` cannot serve its second caller. Owner card 5, 2026-09-21); soft-delete its
   history records (`deleted_*` only, from the same two arguments); the cascade returns the events: `stock_report_item:deleted`
   for the row, `stock_task_assignment:deleted` per assignment, `:updated` per shifted neighbour,
   **no** `:updated` for the row. The command coalesces, dispatches after the block, and returns
   `{"client_id": R}`. With `actor_user_id=None` the cascade stamps NULL everywhere (MC-17) — not
   exercised by a criterion in this phase; the row and every stamp assertion here use `U`.
2. `list_stock_task_assignments(ctx)`: the row by `client_id` in the workspace, non-deleted (else
   `NotFound`); its non-deleted assignments in all states ordered by `created_at, client_id`; items,
   tasks batch-loaded by id; images batch-loaded once for all items (the `tasks.py` pattern);
   `{"stock_task_assignments": [serialize_stock_task_assignment(...)]}`.
3. **Serializers — this phase adds none** (owner card 5, 2026-09-21). All three ship in **phase 8**
   by owner ruling §9B.2 and are live in `bm/domain/stock_report/serializers.py` today; re-adding or
   re-defining them is a review finding. They are listed here only as the shapes task 2 consumes:
   `serialize_item_compact(item, *, images)` → `client_id`, `article_number`, `sku`,
   `quantity`, `item_category_snapshot`, `item_major_category_snapshot`, `item_images` (list of
   `serialize_image_light`) — **seven keys**; `serialize_task_compact(task)` → **twelve keys**,
   `client_id` plus the eleven fields §2 lists (owner card 2, 2026-09-21: the previous "eleven"
   disagreed with the shipped function and with §9B's own enumeration);
   `serialize_stock_task_assignment(a, *, item, task, images)` → `client_id`, `state`,
   `stock_report_item_id`, `task_id`, `item_id`, `quantity`, `property_mismatch_overridden`,
   `credited_history_record_id`, `created_at`, `created_by_id`, `updated_at`, `updated_by_id`, `item`,
   `task` — **fourteen keys**.
4. Router: two routes.
5. Tests first from the table.

## 6. Criteria

Fixture: **F0** with several assignments created through `CR` on different tasks/items; R in the
`high` group as B2 of `A1 B2 C3`. `DR(R)` = the delete command as manager U. Rows end with
`assert_stock_report_clean` unless drift is planted.

Every outcome in this table is computed from the fixture's **own** values (R's four counters, G's awaiting total, each assignment's `quantity` and state, and the `high` group `A1 B2 C3`) plus this row's own deltas, **side effects included** — the per-assignment move, the goal arithmetic, the counter repair, the gap close and the events are part of the outcome, not extras. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.

**How the fixture is built — the choice is named, not offered** (L-30). Assignments are created through `CR`; terminal states are reached with phase 4's `move_assignment` and **never with `PR`**, because this phase depends on 12 and 8 and must stay armed whatever order the batches run in. `priority`/`priority_order` are written by raw SQL in the seed. **The seed orders the group against its ordering key** (L-14): in `high`, `priority_order` ascending **disagrees** with `client_id` ascending (A holds order 1 with the group's largest `client_id`), so a gap close that renumbers by `client_id` instead of by `priority_order` cannot pass. `client_id` is a ULID with no monotonic counter (master plan §10): assignment order inside the cascade is asserted against the seeded ids, never against creation order.

Tenancy and visibility rows (C1(d), C4(d)) enumerate all three cells per entity class — absent, soft-deleted, foreign (L-34) — and the foreign row is a **cross-workspace reference** (L-16): otherwise a valid target of the same request, so tenancy is the only reason it refuses.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | R with A1 `awaiting` (`q = 2`, credited to G), A2 `resolved` (`q = 3`, entered `awaiting` first so credited, then `move_assignment(awaiting → resolved)`), A3 `in_queue` (`q = 1`), A4 `resolved_early` (`q = 5`, `move_assignment(in_queue → resolved_early)`, credited per §14F F4) — `G == 10` before, **every terminal state driven with phase 4's `move_assignment` in the fixture, never with `PR`** (the choice is named, L-30: this phase depends on 12 and 8, not on 9, and the row must stay armed in either batch order); `DR(R)` | all four soft-deleted (`deleted_by_id == U`); `G == 8` (only A1's credit is subtracted, before G's own soft-delete; A2's and A4's `mem` kept); counters `(0, 0, 0)`; all four tasks' flags false; every history record of R soft-deleted (`deleted_at == ctx.now`, `deleted_by_id == U`); R `is_deleted`, `deleted_*` **and** `updated_*` == (U, ctx.now) | two mutants at `_delete_stock_report_item_cascade.py` (def.), **both runs recorded**: (i) soft-delete the row before the assignment loop → the loop's own guard hits a deleted row and the counters/goal arithmetic diverge → red; (ii) call `_uncredit` for A4 as well as A1 (treat `resolved_early → DELETE` as a credit removal) → `G == 3` instead of 8 → red (§14F F4) | MC-16 cascade, MC-5, §14F F4 ("never removed, except by the cascade's history soft-delete"), MC-17 (U12), M1 |
| C1(b) | high = A1 R2 C3; `DR(R)` | high = A1 C2; R keeps `priority high`, `priority_order 2` on its own (deleted) row | `_delete_stock_report_item_cascade.py` (def.): renumber the deleted row along with its group (include it in the shift's WHERE) → R's own row reads `priority_order 1` → red | MC-7 row 10, MC-16 |
| C1(c) | after (a), a demand delivery with R's identity | a **new** live row with empty history | `_demand_lookup.py:discover_live_rows_by_identity` (def.): drop `is_deleted = false` → the demand finds the soft-deleted R, updates it instead of inserting, and the "new row with empty history" assertion fails on both halves → red | MC-16, §4.1 |
| C1(d) | `DR(R_deleted)`; `DR("sri_absent")`; `DR(R_foreign)` | `NotFound` each; nothing written | three mutants at `delete_stock_report_item.py`'s post-lock re-read (def.), **all three runs recorded** (L-34's three visibility cells): (i) drop `is_deleted = false` → the deleted row is cascaded a second time; (ii) drop `workspace_id` → the foreign row is deleted; (iii) return `{"client_id": …}` instead of raising when the lock returns nothing → the absent id answers 200 | §9, M4 |
| C2(a) | A `in_queue` `q = 1`; raw `quantity_in_queue = 4`; `DR(R)` | A's move leaves 3 (no repair at the move: `3 ≥ 0`); second trigger: `quantity_in_queue` set to 0 with one record `{stock_report_item, R, quantity_in_queue, stored "3", recomputed "0", inline:delete_stock_report_item}`; deletion proceeds | `_delete_stock_report_item_cascade.py` (def.): restore the round-6 wording — raise instead of repairing when a counter is non-zero after the loop → the deletion is blocked and no repair record is written → red; **added at the D1 fix round (N-4)**: `_delete_stock_report_item_cascade.py` (def.) writes `target_kind=HISTORY_RECORD` instead of `STOCK_REPORT_ITEM` → red on that assertion alone (1 failed / 5 passed), pinning the §6.5 `counter_* → stock_report_item` mapping that nothing else in the batch pins | MC-1 second trigger, P36, C39 |
| C2(b) | instrument (c): A1 `q = 2`, A2 `q = 3`, both `in_queue`, `A1.client_id < A2.client_id`; raw `quantity_in_queue = 3` (truth 5); `DR(R)` | A1's move → 1 (no repair); A2's move would write −2 → repaired to 0 with **one** record `stored "1"`, `recomputed "0"`, `inline:delete_stock_report_item`; no second-trigger record (already 0); deletion completes | `_delete_stock_report_item_cascade.py` (def.): read `stored_before` from the row's ORM instance (3, loaded at the lock) instead of a fresh `SELECT` after the guarded statement returned zero rows → `3 − 3 = 0 = recomputed` → no record is written → red (MC-1 instrument (c); §9 rule 3) | MC-1 instrument (c) |
| C3(a) | C1(a)'s fixture with `capture_dispatch` | dispatched: one `stock_report_item:deleted` (R), three `stock_task_assignment:deleted` (states at deletion), one `:updated` for C (shifted 3 → 2); **no** `:updated` for R | `_delete_stock_report_item_cascade.py` (def.): append a `stock_report_item:updated` for R after the counter repair instead of relying on the coalescer's `:deleted` rule, and drop the `:deleted` clause from `coalesce_stock_report_events` → an `:updated` for R appears → red. Both edits are needed for the bite, and that is the point (L-36: the pair is load-bearing, each alone is an equivalent mutant); the pair is run and recorded as one mutant | MC-19 row deletion |
| C4(a) | R with A1 active, A2 `resolved`, A3 soft-deleted, A4 `resolved_early`; `GET` | lists A1, A2 and A4 (all states, non-deleted) ordered by `created_at, client_id`, A4's `state == "resolved_early"`; A3 absent | **three** mutants at `list_stock_task_assignments.py` (def.), **all three runs recorded**: (i) filter to `ACTIVE_ASSIGNMENT_STATES` → A2 and A4 vanish; (ii) filter to a hand-typed `state IN ('in_queue','in_progress','awaiting','resolved','failed')` → only A4 vanishes, which is the §9 rule 16 defect this row exists to catch; (iii) **added at the D1 fix round** — drop the `created_at` term from the `ORDER BY`, leaving `client_id` alone → red. **The `client_id` tiebreaker itself is an EQUIVALENT mutant at this boundary, measured not assumed** (owner card D-11): dropping it leaves the output identical because the query reaches the rows through `ix_stock_task_assignments_stock_report_item_id` and feeds a **stable** sort in insertion order, which equals `client_id` order here. Forcing a red would require manipulating physical row storage, which would prove knowledge of Postgres rather than the contract | §9 "non-deleted, all states", §14F F10 (the traceability surface), rule 16 |
| C4(b) | any listed assignment | keys exactly the fourteen of task 3; `item` keys exactly `client_id, article_number, sku, quantity, item_category_snapshot, item_major_category_snapshot, item_images`; `task` keys exactly the **twelve** of §9B — `client_id` plus the eleven fields §2 lists; `item_images` elements are `serialize_image_light` shapes | three mutants, **all runs recorded across the suite** (§9 rule 8 — these serializers ship in phase 8, so each mutant reddens phase 8 rows as well and the observed-red set is recorded whole): (i) `serialize_stock_task_assignment` (def.) drops `credited_history_record_id`; (ii) `serialize_item_compact` (def.) adds `"item_category_id"`; (iii) `serialize_task_compact` (def.) drops `completed_at` | §9B response shapes |
| C4(d) | `GET` for a deleted row / absent id / foreign row | `NotFound` each | three mutants at `list_stock_task_assignments.py`'s row lookup (def.), **all three runs recorded** (L-34): drop `is_deleted = false`; drop `workspace_id`; return `{"stock_task_assignments": []}` instead of raising when the row is absent | M4 |
| C5(a)–C5(d) | `DELETE …/items/{id}` as admin / manager / worker / seller | reached / reached / 403 / 403 | `bm/routers/api_v1/stock_report.py`, the `require_roles([...])` list of the `DELETE …/items/{client_id}` route (def.) — **both directions run and recorded** (L-13/L-24): (i) remove ADMIN, then MANAGER → the matching "reached" cell answers 403; (ii) add WORKER, then SELLER → the matching 403 cell reaches the service | MC-18 |
| C5(e)–C5(h) | `GET …/items/{id}/assignments` as admin / manager / worker / seller | reached ×4 | `bm/routers/api_v1/stock_report.py`, the `require_roles([...])` list of the `GET …/items/{client_id}/assignments` route (def.): remove the role under test → that cell answers 403 → red. Four runs, one per role, each recorded; every cell here is "reached", so there is no opposite direction | MC-18 |
| C6(a) | **Moved here from plan 8 C4(l) by the owner, card 2, 2026-09-21** — it can only be true where both shapes exist. Create an assignment with `CR([I on R])`, keep the create response element, then `GET /api/v1/stock-report/items/{R}/assignments` and take the same assignment's element | `set(create_element) == set(list_element)` — the two surfaces return the **same key set**, so a board can render a freshly created assignment and a reloaded one identically | `list_stock_task_assignments.py` (def.): build the element inline instead of calling `serialize_stock_task_assignment`, then drop one key → the two key sets diverge → red. Run **once per surface pair** and record both: the create surface's own key rows (phase 8) stay green under this mutant, which is what proves the row is about the *agreement*, not about either shape alone | master plan §9B ruling 2, §6.1; plan 8 C4(l); batch C1 tester card 2 |

## 7. Notes

- Sizing: **19 criterion rows in 6 criteria**; `complex: yes`. (Re-derived by the committed
  script `SR/count_criteria.py` at the D1 gate, 2026-09-21 — never typed. The previous "18 in 5"
  was stale from the round-8/9 fold: **owner card 2 later moved C6(a) in from plan 8**, which
  added both a nineteenth row and a sixth criterion, and the sizing line was never re-run. Plan
  12's "45 rows in 7 criteria" is correct as written.)
- C4(c) (equal statement count for 1 vs 5 assignments) was removed (owner ruling 2026-09-19: outcomes, not internals): it asserted query count,
  not an outcome. Batch-loading stays the implementation rule of task 2, unguarded by a test.
- Rounds 8–9 (2026-09-19): C1(a)'s fixture gained a `resolved_early` assignment (its credit is kept
  through the cascade, §14F F4) and no longer depends on `PR` (this phase depends on 12 and 8; the
  terminal states are reached with phase 4's operation); C4(a) lists the new state (§14F F10). The
  cascade's second caller is phase 13A (§14E E5); its `actor_user_id=None` path is exercised there
  (13A C3), not here.
- C2(b) is the instrument the re-check added specifically for the cascade; its planted defect is
  the ORM read of `stored_before`, so the implementation must take `stored_before` from a fresh
  `SELECT` after the guarded statement returned zero rows.
- The cascade never soft-deletes the row before its assignments (MC-16); the order in task 1 is
  the contract's order.

**Added by the batch D projection + fold, 2026-09-21 (round 0). Nothing below changes a criterion outcome.**

- **The three compact serializers already ship — APPLIED, owner card 5, 2026-09-21.** Owner ruling
  §9B.2 moved `serialize_stock_task_assignment`, `serialize_item_compact` and
  `serialize_task_compact` into **phase 8**; they are live in
  `bm/domain/stock_report/serializers.py` today. Task 3 now says so and §4 no longer lists the
  file. Only `serialize_stock_report_item` is still owed, and that one belongs to phase 12.
- **`serialize_task_compact` returns twelve keys, not eleven — APPLIED, owner card 2,
  2026-09-21.** `client_id` plus the eleven fields §2 lists. Task 3 and C4(b) now read "twelve …
  `client_id` plus the eleven fields", which reconciles both readings that produced the error.
- **The gap close must read a *fresh* `priority_order` — APPLIED to task 1, owner card 5,
  2026-09-21.** Phase 13A calls this same cascade once per row inside one transaction (13A C5(b)),
  so by the second call the ORM instance loaded at the lock is stale after the first cascade's Core
  shift (§9 rule 3). `close_priority_gap`'s `removed_order` therefore comes from a fresh `SELECT`
  taken inside the cascade, never from `row.priority_order` as loaded. **No row in this phase can
  observe that** — this phase deletes one row at a time. Its only armed evidence anywhere is 13A
  **C5(b)**, and 13A's §4 perimeter forbids editing this module, so the requirement has to be true
  when this phase ships. This is why batch D is split with **D1 (12 + 13) APPROVED before D2 (13A +
  14) starts**.
- **C4(b) overlaps phase 8's own key rows** (the three serializers are shipped and pinned there).
  It is kept because it pins the *list* endpoint's element, and C6(a) proves the two surfaces
  agree; its mutants redden phase 8 tests too, so the observed-red set is recorded across the
  suite (§9 rule 8).
- **`DELETE` takes no body** (§9B ruling 1, §6.5): `DeleteStockReportItemRequest` is removed and
  there is nothing for this phase to add to `requests/__init__.py`. §4's "Edited:
  `requests/__init__.py`" is stale unless the router's path-param injection needs a model, which
  8A's precedent shows it does not.
- **Where `stock_report_item:deleted` is built** is undetermined: §6.5's `_events.py` registers
  only the `:updated` and assignment builders, and `stock_report_item:created` is built inline in
  `apply_stock_demand.py`. Whichever this phase picks, it must be registered in §6.5 in the same
  act (§6 preamble; §9 rule 18) — and plan 14's C1(b) currently roots its guard in `_events.py`
  alone, which would not see it.

## 8. Review log

### Implementation, batch D1 round 1 (2026-09-21, Opus implementer, slot `d1`)

**What was built.** `_delete_stock_report_item_cascade.py`, `delete_stock_report_item.py`,
`list_stock_task_assignments.py`, and the two routes. **No serializer and no request
model were added** (owner card 5): the three compact serializers ship in phase 8 and
`DELETE` takes no body. Tests: `test_delete_stock_report_item.py` (6),
`test_list_stock_task_assignments.py` (5), and 3 cases appended to
`test_stock_report_router.py`. This project runs a tester, so this round wrote no
row-by-row transcription, ran no named mutation and carries no mutation ledger
(master plan §3B).

**The two fresh `SELECT`s, named, because one of them has no armed evidence in this
phase.**

- The **counter repair's `stored_before`** at the second self-heal trigger:
  `_delete_stock_report_item_cascade.py:cascade_delete_stock_report_item`, the
  `stored_counters` `SELECT` taken **after** the assignment loop ends, once, never
  per assignment. (The *inline* repair inside a move is the approved
  `_move_assignment.py:_apply_counter_delta`, which already reads fresh after its
  guarded statement returned zero rows — that is what C2(b) exercises.)
- The **gap close's `removed_order`**: the `position` `SELECT` of
  `(priority, priority_order)` in the same function, immediately before
  `close_priority_gap`. It is a fresh `SELECT`, **not** `row.priority_order` as
  loaded at the lock. **Nothing in this phase can observe it** — this phase deletes
  one row at a time; its only armed evidence anywhere is phase 13A C5(b), and 13A's
  perimeter forbids editing this module.

**The cascade reads no `ctx`.** `_delete_stock_report_item_cascade.py` does not
import `ServiceContext` and takes `workspace_id`, `actor_user_id`, `now` and
`trigger` from its arguments only, so phase 13A's `actor_user_id=None,
trigger="stock_demand_deleted"` call works unchanged. That path is **not exercised
by any criterion here** (plan §7), and no test in this round covers it.

**Judgment calls.**

1. **`stock_report_item:deleted` is built in
   `_delete_stock_report_item_cascade.py:build_stock_report_item_deleted_event`** —
   inline in this phase's own module, not in `_events.py`. Plan 13 §4 does not list
   `_events.py`, which belongs to APPROVED phase 8, so adding a builder there would
   be a perimeter violation; the inline precedent is `apply_stock_demand.py`'s
   `stock_report_item:created`. It is a named module-level function precisely so
   plan 14's accuracy guard has a `file:symbol` to find. **It must be registered in
   §6.5 by the coordinator in the same act (§9 rule 18), and plan 14 C1(b)'s guard,
   which currently roots in `_events.py` alone, would not see it.**
2. **No `:updated` for the deleted row is produced by suppression, not by
   omission.** The per-assignment moves legitimately return `stock_report_item:updated`
   for R; the cascade keeps them and relies on `coalesce_stock_report_events`' rule
   that a row carrying a `:deleted` in the request gets no `:updated`. That is the
   shipped phase-8 rule and the one C3(a)'s paired mutant targets.
3. **The cascade re-queries the row's non-deleted assignments itself** (ascending
   `client_id`) rather than taking a list argument: its registered signature takes
   only `row`, and the caller has already locked exactly those rows, so the query
   reads locked rows.
4. **The row soft-delete is a Core `UPDATE`, not an ORM attribute write.** The ORM
   instance is stale after the loop's Core statements (§9 rule 3); a Core statement
   removes the whole staleness class rather than relying on SQLAlchemy emitting only
   the dirty columns.
5. **The command's post-lock re-read is `_lock_row_and_group` plus the
   `row is None` check**, in `delete_stock_report_item.py` — that is where
   `workspace_id`, `is_deleted = false` and the raise live, which is the site C1(d)
   names.
6. **`list_stock_task_assignments` returns early on an empty assignment list**, so a
   row with no assignments costs one lookup and one list query and no image query.

**Fixture note the tester should keep (it was a real flake).** C2(b)'s two
assignments must carry `q = 2` on the **smaller** `client_id` and `q = 3` on the
larger, or the row asserts a different `stored_before` on roughly half its runs —
the cascade's loop is ascending `client_id` and a ULID has no monotonic counter
(master plan §10). The test binds the quantities to the **sorted real ids** after
creation for exactly this reason. My first draft did not, and it would have been an
intermittent red nobody could reproduce on demand.

**Observations.**

- C1(a)'s fixture cannot reuse F0's own item/task for the `q = 2` assignment: `CR`
  sets `quantity = max(item.quantity, 1)` at creation and the counter moves with it,
  so editing the quantity afterwards plants counter drift and the cascade then writes
  a (correct) repair record the row does not expect. Each of the four assignments
  gets its own (item, task) pair seeded at the intended quantity. A second pair also
  needs its own `task_scalar_id` — `uq_tasks_workspace_scalar_id`.
- No row in this phase exercises the `actor_user_id=None` path, C4(b)'s cross-suite
  observed-red set, or C6(a)'s "phase 8 rows stay green" half; those are the tester's.

---

## Review log — verification, batch D1 round 1 (2026-09-21, Opus tester, slot `dt`)

Ledger: `handoffs/tester/2026-09-21_batch_D1_test_1_handoff.md`. Declared named mutations for
this plan, derived by script from the §6 table: **C1=7 + C2=2 + C3=1 + C4=8 + C5=8 + C6=1 = 27**,
all 27 executed.

**C1(c) was built at the surface the cell names.** The implementer's
`test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` asserted only that
`discover_live_rows_by_identity` returns `{}`; it is replaced in place by a test that runs a real
demand delivery after `DR(R)` and asserts a new live row with its own fresh history. The old
probe is not a separate deletion: the same test id now carries the row's own surface.

**Foreign sites, reported not moved (L-25).** Two cells name
`_delete_stock_report_item_cascade.py` for behaviour that lives elsewhere: C1(a) mutant (ii)
(`resolved_early → DELETE` credit removal) is decided in `_goal_credit.py:apply_goal_effect`, and
C2(b)'s inline repair is `_move_assignment.py:_apply_counter_delta`. Both were run at the real
site; C1(a)(ii) bites, C2(b) does not (below).

**Two equivalent mutants, one of them blocking.**
- **C1(a) mutant (i)** — soft-deleting the row before the assignment loop changes nothing
  observable: no code on the cascade path reads the row's `is_deleted`, and the cascade's own
  later `UPDATE` re-applies the same values. MC-16's ordering clause is therefore unguarded by
  any row in this phase. `EQUIVALENT`.
- **C2(b) cannot fail** — the planted defect ("read `stored_before` from the row's ORM instance")
  was run at the named site **and** at the real site, and the test stays green at both. Measured
  cause, by probe on this tree: the counter statement is an **ORM-enabled** `update(StockReportItem)`
  executed through `session.execute`, so SQLAlchemy synchronises the identity-mapped instance
  (`synchronize_session="auto"` → `fetch` with `RETURNING`). At the moment `_apply_counter_delta`
  reads `stored_before`, the ORM instance and a fresh `SELECT` both answer **1**. The instrument
  MC-1 (c) exists to protect cannot observe the defect it names. `BLOCKED-PLAN`, owner card 2 —
  and the same mechanism puts **13A C5(b)**'s `removed_order` evidence in doubt before D2 starts.

**C3(a) is `BLOCKED-PLAN` on its own arithmetic** (owner card 3): the cell says "three
`stock_task_assignment:deleted`" over C1(a)'s fixture, which carries **four** assignments since
the round-8/9 fold added `resolved_early`. Its paired mutant was run and reddens both delete
tests; no test was authored against the corrected count.

**C4(b) and C6(a) cross-suite red sets are recorded.** The radius was established by grep (the
three compact serializers have exactly two production consumers and three asserting test files);
C4(b)'s mutants redden phase 8's `test_stock_report_serializers.py` (all three) and
`test_create_stock_task_assignments.py` (mutant (i) only), while **C6(a)'s mutant leaves both
phase-8 files green**, which is the half the cell exists for.

---

## Review log — independent review, batch D1 round 1 (2026-09-21, Opus reviewer, slot `dr`)

Handoff: `handoffs/reviewer/2026-09-21_batch_D1_review_1_handoff.md`. Tree `06ad124`; the tester's
27 plan-13 mutation rows are consumed by citation (matching tree), and the reviewer's budget went
to the variation its §13 declared unspent. Verdict **CHANGES_REQUESTED** (batch-level).

**Plan 13: 19 rows — 16 PASS / 1 FAIL / 2 NOT_VERIFIED.**
FAIL: **C4(a)** (S-1, route `verification`). NOT_VERIFIED: **C2(b)** (`BLOCKED-PLAN`, card D-6 —
the instrument cannot fail at either site) and **C3(a)** (`BLOCKED-PLAN`, card D-7.1 — three
declared events against a four-assignment fixture).

### S-1 · route `verification` · C4(a)'s ordering clause cannot fail

The row names the key *"ordered by `created_at, client_id`"*; its fixture creates four assignments
in one loop with nothing pinning the two orderings apart, and the test derives its expectation
from a second query using the same two keys. Measured on this tree:

- **RP-1** production ordered by `client_id` **alone** → **green** (repeated 5×, so not a flake);
- **RP-1b** production ordered by `created_at` **alone** → **green**;
- **RP-2** both terms reversed → red.

Three different order keys satisfy the fixture. This is the exact twin of the defect the tester
repaired the same evening in plan 12 C4(b), whose test now back-dates the null row with the
**larger** `client_id`, chosen from the sorted real ids, and asserts `N1 > N2` (master plan §10).
**Correction (tester's lane, no criterion change):** back-date one assignment the same way and
re-run RP-1 as the arming proof. The row's state-filter half (M-71, M-72) is genuinely armed.

### S-2 · route `plan` · §9 rule 18 — `build_stock_report_item_deleted_event` is pinned by no row

The builder was registered in master plan §6.5 at the D1 gate (`extra {}`, §6.7). **RP-10** changes
`extra={}` to a non-empty dict and the whole delete file stays green (6 passed);
`grep -rn "stock_report_item:deleted" app/tests` returns two lines, both asserting only the name
and the row id, so nothing anywhere reads `extra`. The nearest row, C3(a), is itself
`BLOCKED-PLAN`. A criterion row is the owner's to author — **owner card R-1** — and RP-10 is its
ready-made arming mutant.

### Reviewer probes that confirmed arming (all reverted, `git diff --quiet` exit 0)

- **RP-6** cascade, history soft-delete `UPDATE` deleted → **red** at C1(a):333 and at C1(c):633.
- **RP-7** cascade, `updated_at`/`updated_by_id` dropped from the row soft-delete → **red** at
  C1(a):319. Both clauses carry no named mutation; both bite.
- **RP-8** `serialize_item_compact`'s `item_images` elements replaced by `{client_id}` → **red** at
  C4(b):295 — the tester's real-image fixture strengthening is load-bearing.

### N-2 · a seventh absorbed-additive mutant (RP-9)

Emitting every shifted neighbour's `:updated` **twice** in the cascade is invisible —
`coalesce_stock_report_events` de-duplicates — so C3(a)'s "one `:updated` for C" clause is held by
production's coalescer, not by the cascade. Recorded as an **equivalent mutant**; never a test
demand. With C1(h)(i), 12 C1(a)/C1(b)/C6(a), 13 C1(a)(i) and 13 C2(b) that is seven inert mutants
in one batch, **every one additive**. Fold into the D2 projection as a rule: in a module that
de-duplicates or overwrites, name a subtraction or a re-order, never an addition.

### N-4 · route `verification` · C2(a) does not assert `target_kind`

The cell names the repair record as `{stock_report_item, R, field, stored, recomputed,
inline:…}`; the test asserts every field except `target_kind`. One line.

### Confirmations

C1(c) **is** exercised at the surface the cell names — the tester's in-place rewrite runs a real
`apply_stock_demand` delivery after `DR(R)`; the review prompt's "NOT EXERCISED" is stale (only the
"empty history" wording is open, card D-7.2). The cascade's two fresh `SELECT`s and its
`ctx`-free argument list are consumed from the gate's own reading. Perimeter clean: no serializer
and no request model was added, exactly as owner card 5 requires.

---

## Review log — verification fix round 1 (2026-09-22, Opus tester, slot `dt2`)

Handoff: `handoffs/tester/2026-09-22_batch_D1_fix_verification_1_handoff.md`. Scope: the two
findings routed `verification` — **S-1** (C4(a)) and **N-4** (C2(a)). No production file changed
(`git diff b6cbbb9..HEAD -- app/beyo_manager app/migrations app/scripts` → 0 files); no criterion
cell edited; no criterion row authored.

**C4(a) — the fixture now orders the data against its key, and the row's two expectations are
constructed, not re-derived.** `test_every_non_deleted_state_is_listed_in_created_at_client_id_order`
binds `LO < MID < HI` by sorting the three listed ids at runtime (master plan §10), then writes
`created_at` against that sort: `HI` gets the earlier value, `LO` and `MID` share the later one.
The expectation is now the explicit list `[HI, LO, MID]`; the second `ORDER BY` that mirrored
production's own clause is gone.

- **RP-1** (`list_stock_task_assignments.py` def., drop `created_at`, order by `client_id` alone)
  → **RED**, `assert ids == [HI, LO, MID]`, index 0 differs. It was **green** on the pre-fix
  fixture (reviewer, 5 runs). This is the arming proof the correction asked for.
- **RP-2** (both terms `.desc()`) → **RED** at the same assertion, re-run at the new surface (L-23).
- **RP-1b** (drop `client_id`, keep `created_at`) → **green, and measured EQUIVALENT at this
  boundary, not a weak fixture.** Probe on the real fixture: the plan is
  `Sort(created_at) ← Index Scan using ix_stock_task_assignments_stock_report_item_id`; the
  `created_at` back-dating is a HOT update, so the index entries still address the original
  tuples and the scan feeds the sort in **insertion** order (measured `scan=[LO, MID, HI]` while
  `ctid=[HI, MID, LO]`), the sort is stable, and insertion order equals `client_id` order because
  `CR` mints its ULIDs milliseconds apart. The tie therefore already emerges in `client_id`
  ascending order **without** the term, so removing it yields byte-identical output. The
  `client_id` term is a determinism guarantee whose removal this query plan absorbs; no fixture
  built from `CR` at this boundary can observe it. See the handoff's own section — this is the
  one correction quoted in the fix prompt that is not implemented as quoted (§9 rule 14).

**C2(a) — `target_kind` is now asserted** in
`test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded`
(`record.target_kind == StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM`). Armed by **RP-11**
(`_delete_stock_report_item_cascade.py` def., `STOCK_REPORT_ITEM` → `HISTORY_RECORD`) → **RED**,
and red on **that assertion alone**: 1 failed / 5 passed, no other test in the file moves, which
is the measurement behind N-4's "nothing else in the batch pins this mapping".

**The two rows' existing plan-named mutations re-run at the new surface** (L-23 — I edited both
test functions, so the previous round's reds do not carry): **M-71** (filter to
`ACTIVE_ASSIGNMENT_STATES`) → red at C4(a)'s `set(ids)`, A2 and A4 missing; **M-72** (hand-typed
five-state list) → red at the same assertion, A4 alone missing — the §9 rule 16 defect the row
exists for; **M-67** (cascade raises instead of repairing) → red at C2(a),
`RuntimeError: … has a non-zero quantity_in_queue`. All three reverted, `git diff --quiet` exit 0.

**Closing stamp** (this tree, clean but for the two test files): **24 failed / 3739 passed /
1 skipped**. Failure-ID diff against the checked-in 23-ID baseline: `+1` =
`test_the_priority_record_snapshots_the_live_awaiting_counter` (the declared card D-5 witness),
`−0`. Pass count unchanged — no test added, none removed.

**Proposed cell backfills** (the coordinator folds; the tester does not): C4(a) gains the ordering
mutant **RP-1** (drop `created_at` from the `order_by`) beside its two state-filter mutants, and
C2(a) gains **RP-11**. Both are measured red on this tree.

### Re-review 1 (batch D1, round 2) — 2026-09-22, Opus reviewer, slot `dr2`, tree `74c7a6e`

**Verdicts for this plan's in-scope rows: `C4(a)` PASS** (was FAIL, S-1) **and `C2(a)` PASS**
(N-4 closed). Delta-scoped; plan 13's other 17 rows are carried from round 1 and were not
re-opened. Full record: `handoffs/reviewer/2026-09-22_batch_D1_rereview_1_handoff.md`.

**C4(a) — three mutant shapes at the one site, on a green suite.**
- **RP-1** (drop `created_at`, leave `client_id`) → **RED**, 1 failed / 4 passed,
  `test_list_stock_task_assignments.py:265 assert ids == [HI, LO, MID]`, "At index 0 diff".
  S-1's shipping risk — "a change that dropped the date entirely would ship unnoticed" — is closed.
- **RP-1b** (drop `client_id`, keep `created_at`) → **GREEN**, 5 passed. The tester's measurement
  is confirmed independently.
- **RP-1b-var** (*new shape, nobody named it*: keep `client_id`, reverse it to `.desc()`) →
  **RED**, 1 failed / 4 passed, same assertion, **"At index 1 diff"** — the tied `LO`/`MID` pair.

The state-filter half (M-71, M-72) is consumed by citation: the production fix does not reach that
site. All probes reverted, `shasum -c` OK, `git diff --quiet` exit 0.

**Finding R2-1 · should-fix · route `plan`.** The C4(a) cell as folded at `cbecd2b` reads *"**The
`client_id` tiebreaker itself is an EQUIVALENT mutant at this boundary, measured not assumed**
(owner card D-11): dropping it leaves the output identical…"*. The first clause does not follow
from the second and is **false**: RP-1b-var reddens the row. What is equivalent is the **deletion**
of the term, not the term — when present it decides the tie (reverse it, the output reverses);
when absent, today's plan happens to supply the same order for free. So C4(a) is armed on the
`created_at` term **and** on the tiebreaker's *direction*, and unarmed only against the clause's
*removal*. **Suggested cell wording:** *"deleting the `client_id` term is unobservable under
today's query plan (RP-1b, green — conditions recorded); **reversing** it is observable and is the
tiebreaker's arming proof (RP-1b-var, red at the tied pair, 2026-09-22)."*
**Owner card D-11 is NOT re-opened** — the accept ruling stands and is better supported than when
it was taken; only the sentence recording it is wrong, and the card's own note already asks for
"the measurement **and its conditions**".

**C2(a) — N-4 closed.** **RP-11** (`_delete_stock_report_item_cascade.py`, def.:
`target_kind=STOCK_REPORT_ITEM` → `HISTORY_RECORD`) → **RED**, 1 failed / 5 passed, at
`test_delete_stock_report_item.py:427`, the new assertion, **nothing else in the file moves**.
Re-run rather than cited because the tester's tree carried the un-fixed `consistency.py` and this
file reaches that module through `assert_stock_report_clean`. M-67 consumed by citation (it aborts
the cascade before the consistency assertion is ever evaluated, so the tree change cannot affect
it).

**Probe inside this plan's test file, declared.** One `assert_stock_report_clean` line was added to
`test_delete_stock_report_item.py::test_cascade_removes_every_assignment_and_soft_deletes_the_row`
to measure whether a **soft-deleted goal record** still reconciles clean after MC-16's cascade — it
does (6 passed: goal at 8, A1's credit subtracted, A2's/A4's kept, every history record
soft-deleted, check empty). Reverted from a scratch copy rather than with git, because the file is
legitimately part of the fix perimeter; `shasum -c` OK and `grep -c "PROBE P7"` → 0.

**Nothing else in plan 13 changed.** No production file, test file or criterion cell of this phase
was touched by this round; no tracker row written (§4: orchestrator-only).
