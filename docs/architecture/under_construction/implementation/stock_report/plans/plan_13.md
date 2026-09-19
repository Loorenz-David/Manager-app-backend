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
Edited: `bm/domain/stock_report/serializers.py` (three serializers added), `requests/__init__.py`,
`bm/routers/api_v1/stock_report.py` (two routes), `app/tests/unit/routers/api_v1/test_stock_report_router.py`.

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
   value from its arguments and never from `ctx`). The cascade, in order: for each assignment
   ascending `client_id`:
   `remove_assignment(..., trigger=trigger)`; then, per counter column, a fresh
   `SELECT` of the three counters — any ≠ 0 → one `UPDATE` setting it to 0 (its recomputed value, no
   assignments remain) with one repair record (`stock_report_item`, R, field, `stored_before`, `"0"`,
   `inline:delete_stock_report_item`, NULL author) and a warning; close the gap in the row's group
   (when priority non-null); soft-delete the row (`is_deleted`, `deleted_at = ctx.now`, `deleted_by_id
   = ctx.user_id`, **and** `updated_at = ctx.now`, `updated_by_id = ctx.user_id`); soft-delete its
   history records (`deleted_*` only); the cascade returns the events: `stock_report_item:deleted`
   for the row, `stock_task_assignment:deleted` per assignment, `:updated` per shifted neighbour,
   **no** `:updated` for the row. The command coalesces, dispatches after the block, and returns
   `{"client_id": R}`. With `actor_user_id=None` the cascade stamps NULL everywhere (MC-17) — not
   exercised by a criterion in this phase; the row and every stamp assertion here use `U`.
2. `list_stock_task_assignments(ctx)`: the row by `client_id` in the workspace, non-deleted (else
   `NotFound`); its non-deleted assignments in all states ordered by `created_at, client_id`; items,
   tasks batch-loaded by id; images batch-loaded once for all items (the `tasks.py` pattern);
   `{"stock_task_assignments": [serialize_stock_task_assignment(...)]}`.
3. Serializers: `serialize_item_compact(item, *, images)` → `client_id`, `article_number`, `sku`,
   `quantity`, `item_category_snapshot`, `item_major_category_snapshot`, `item_images` (list of
   `serialize_image_light`); `serialize_task_compact(task)` → the eleven fields of §9B;
   `serialize_stock_task_assignment(a, *, item, task, images)` → `client_id`, `state`,
   `stock_report_item_id`, `task_id`, `item_id`, `quantity`, `property_mismatch_overridden`,
   `credited_history_record_id`, `created_at`, `created_by_id`, `updated_at`, `updated_by_id`, `item`,
   `task`.
4. Router: two routes.
5. Tests first from the table.

## 6. Criteria

Fixture: **F0** with several assignments created through `CR` on different tasks/items; R in the
`high` group as B2 of `A1 B2 C3`. `DR(R)` = the delete command as manager U. Rows end with
`assert_stock_report_clean` unless drift is planted.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | R with A1 `awaiting` (`q = 2`, credited to G), A2 `resolved` (`q = 3`, entered `awaiting` first so credited, then `move_assignment(awaiting → resolved)`), A3 `in_queue` (`q = 1`), A4 `resolved_early` (`q = 5`, `move_assignment(in_queue → resolved_early)`, credited per §14F F4) — `G == 10` before, every terminal one driven with phase 4's operation in the fixture (or `PR` once phase 9 is APPROVED); `DR(R)` | all four soft-deleted (`deleted_by_id == U`); `G == 8` (only A1's credit is subtracted, before G's own soft-delete; A2's and A4's `mem` kept); counters `(0, 0, 0)`; all four tasks' flags false; every history record of R soft-deleted (`deleted_at == ctx.now`, `deleted_by_id == U`); R `is_deleted`, `deleted_*` **and** `updated_*` == (U, ctx.now) | soft-delete the row before the assignments (the row's guard then hits a deleted row); subtract A4's credit → `G == 3` | MC-16 cascade, MC-5, §14F F4 ("never removed, except by the cascade's history soft-delete"), MC-17 (U12), M1 |
| C1(b) | high = A1 R2 C3; `DR(R)` | high = A1 C2; R keeps `priority high`, `priority_order 2` on its own (deleted) row | renumber the deleted row | MC-7 row 10, MC-16 |
| C1(c) | after (a), a demand delivery with R's identity | a **new** live row with empty history | — | MC-16, §4.1 |
| C1(d) | `DR(R_deleted)`; `DR("sri_absent")`; `DR(R_foreign)` | `NotFound` each; nothing written | — | §9, M4 |
| C2(a) | A `in_queue` `q = 1`; raw `quantity_in_queue = 4`; `DR(R)` | A's move leaves 3 (no repair at the move: `3 ≥ 0`); second trigger: `quantity_in_queue` set to 0 with one record `{stock_report_item, R, quantity_in_queue, stored "3", recomputed "0", inline:delete_stock_report_item}`; deletion proceeds | block the deletion on a non-zero counter (the round-6 wording) | MC-1 second trigger, P36, C39 |
| C2(b) | instrument (c): A1 `q = 2`, A2 `q = 3`, both `in_queue`, `A1.client_id < A2.client_id`; raw `quantity_in_queue = 3` (truth 5); `DR(R)` | A1's move → 1 (no repair); A2's move would write −2 → repaired to 0 with **one** record `stored "1"`, `recomputed "0"`, `inline:delete_stock_report_item`; no second-trigger record (already 0); deletion completes | read `stored_before` from the row's ORM instance (3, loaded at the lock) → `3 − 3 = 0 = recomputed` → no record | MC-1 instrument (c) |
| C3(a) | C1(a)'s fixture with `capture_dispatch` | dispatched: one `stock_report_item:deleted` (R), three `stock_task_assignment:deleted` (states at deletion), one `:updated` for C (shifted 3 → 2); **no** `:updated` for R | emit `:updated` for R | MC-19 row deletion |
| C4(a) | R with A1 active, A2 `resolved`, A3 soft-deleted, A4 `resolved_early`; `GET` | lists A1, A2 and A4 (all states, non-deleted) ordered by `created_at, client_id`, A4's `state == "resolved_early"`; A3 absent | filter to active only; filter to `state IN (active + resolved)` (a hand-typed list) → A4 vanishes | §9 "non-deleted, all states", §14F F10 (the traceability surface), rule 16 |
| C4(b) | any listed assignment | keys exactly the fourteen of task 3; `item` keys exactly `client_id, article_number, sku, quantity, item_category_snapshot, item_major_category_snapshot, item_images`; `task` keys exactly the eleven of §9B; `item_images` elements are `serialize_image_light` shapes | — | §9B response shapes |
| C4(d) | `GET` for a deleted row / absent id / foreign row | `NotFound` each | — | M4 |
| C5(a)–C5(d) | `DELETE …/items/{id}` as admin / manager / worker / seller | reached / reached / 403 / 403 | — | MC-18 |
| C5(e)–C5(h) | `GET …/items/{id}/assignments` as admin / manager / worker / seller | reached ×4 | — | MC-18 |

## 7. Notes

- Sizing: 18 criterion rows in 5 criteria; `complex: yes`. (Counts re-derived by script after the
  round-8/9 fold; see the delta handoff.)
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

## 8. Review log

(empty)
