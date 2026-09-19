# Plan 12 — Priority, dense ordering, history records for user actions, the list endpoint

```
state: NOT_STARTED
phase: 12 of 15
depends_on: 5 (APPROVED)
projection: mandatory (ordering is a silent-failure mechanism; advisory lock)
complex: yes — workspace advisory lock, single-statement shifts, group invariants
```

## 1. Goal

The two user commands that change a row's priority or its position (MC-7's before/after tables,
one history record each, B2 no-ops, MC-17 stamps, MC-19 events) and the list endpoint with §7A's
read order and filter, plus the twelve role cells. **Not in this phase:** row deletion and its gap
closing (13 — this phase ships `close_priority_gap` and uses it for a priority change, and 13
reuses it), assignment reads (13).

## 2. Read first

1. `master_plan.md` §6.1 (`serialize_stock_report_item`), §6.4 (the two 422 identities and the
   filter identity), §6.5 (`_ordering.py`, the two commands, `list_stock_report_items.py`), §6.6, §9
   rules 3–4, 6, 9.
2. Intention §7, §7A MC-7 in full (before/after tables, serialization, race table, read order,
   filter), §6.1 rows 3–4, §6A MC-6 (priority/order records, timing and values), §4.5/MC-17 (priority,
   order rows), §9B/MC-19 (priority change / move row), §9E MC-18 (three operations), §9 response shape
   (`item_category` object), §14B B2, §14C C22, U12.
3. Repo: `bm/services/commands/working_sections/set_user_working_sections_order.py` and
   `_membership_ordering.py` (the `max + 1` precedent; **not** a unique constraint),
   `bm/services/commands/tasks/create_task.py:99` (advisory-lock form), `architecture/07_queries_local.md`
   (the pagination gate this endpoint is exempt from, master plan §5).

## 3. Dependencies

Phase 5 APPROVED (phase 3's repair renumber semantics must match `_ordering.py`'s; both use ascending
`client_id` ties).

## 4. Files expected to change

New: `bm/services/commands/stock_report/_ordering.py`, `set_stock_report_item_priority.py`,
`set_stock_report_item_priority_order.py`; `bm/services/queries/stock_report/list_stock_report_items.py`;
`bm/domain/stock_report/serializers.py` (`serialize_stock_report_item` only);
`app/tests/integration/services/commands/stock_report/test_priority_and_ordering.py`,
`test_ordering_locks.py`; `app/tests/integration/services/queries/stock_report/test_list_stock_report_items.py`.
Edited: `requests/__init__.py` (two request models), `bm/routers/api_v1/stock_report.py` (three
routes), `app/tests/unit/routers/api_v1/test_stock_report_router.py` (twelve cells).

## 5. Tasks

1. `_ordering.py` per master plan §6.5: every shift is **one** column-referencing `UPDATE …
   RETURNING client_id, <six event fields>`; positions are read only after the advisory lock and the
   group `FOR UPDATE`.
2. `set_stock_report_item_priority(ctx)`: parse (`priority ∈ {high, medium, low, null}`; anything
   else 422); `maybe_begin`; `acquire_stock_report_order_lock`; lock the target row plus every
   non-deleted row of the source and destination groups in one statement ordered by `client_id`;
   re-read; `X == Y` → return the serialized row with no write, no record, no stamp, no event (B2);
   else close the source gap (`close_priority_gap`, when X non-null), set the row's priority and
   order (`append_to_priority_group` when Y non-null, else NULL); stamp `updated_by_id = ctx.user_id`,
   `updated_at = ctx.now` on the moved row only; insert one `priority_change` record after all row
   mutations (`quantity_requested`, live `quantity_awaiting`, new `priority`, new `priority_order`,
   `created_by_id = ctx.user_id`, `created_at = ctx.now`); events: `:updated` for the moved row and
   for every shifted neighbour (from the shift statements' `RETURNING`), coalesced; dispatch after
   the block; return `{"stock_report_item": serialize_stock_report_item(...)}`.
3. `set_stock_report_item_priority_order(ctx)`: parse (integer target); same locking; the row's
   priority null → `ValidationError("STOCK_REPORT_ROW_HAS_NO_PRIORITY: …")`; `n` = group size read
   under the locks; `t ∉ 1..n` → `ValidationError("STOCK_REPORT_TARGET_OUT_OF_RANGE: …")`; `t == p` →
   no-op; `t < p` → `+1` on `[t, p−1]`; `t > p` → `−1` on `[p+1, t]`; mover → `t`; stamp the mover;
   one `priority_order_change` record for the mover; events for mover + shifted rows.
4. `list_stock_report_items(ctx)`: `priority` query param comma list; omitted or empty →
   `priority IS NULL` ordered by `created_at, client_id`; tokens each in `{high, medium, low}` else
   `ValidationError("STOCK_REPORT_UNKNOWN_PRIORITY_FILTER: …")`; otherwise `CASE priority WHEN 'high'
   THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, priority_order ASC`; non-deleted rows of the
   workspace; categories batch-loaded in one query (deleted categories included by id, so a deleted
   category still serializes its name); `{"stock_report_items": [...]}` — no pagination key.
5. `serialize_stock_report_item(row, *, category)`: `client_id`, `item_category {client_id, name,
   major_category}`, `properties` (stored, normalized), `properties_signature`, the four quantities,
   `priority`, `priority_order`, `created_at`, `updated_at` (ISO UTC), `created_by_id`, `updated_by_id`.
6. Router: three routes; role lists per master plan §6.6.
7. Tests first from the table.

## 6. Criteria

Fixture: **F0**'s workspace with rows inserted via the demand service or ORM: group `high` = A1 B2 C3
D4 (four rows, orders 1–4), group `low` = X1 Y2, and N (priority null), exactly as MC-7's table; the
foreign workspace holds the same shapes. `SP(row, p)` / `SO(row, t)` = the two commands as seller
**S** (a permitted role). "state" = the `(priority, priority_order)` of every row in W. Every row
ends with `assert_stock_report_clean`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `SO(C, 1)` | high = A2 B3 C1 D4 | shift `[t, p]` instead of `[t, p−1]` | MC-7 row 1, M6 |
| C1(b) | `SO(A, 3)` | high = B1 C2 A3 D4 | shift `[p, t]` | MC-7 row 2 |
| C1(c) | `SO(B, 2)` | unchanged; no record; no event; no stamp; `count_writes` on the four tables `== 0` | write anyway | MC-7 row 3, B2 |
| C1(d) | `SO(A, 0)` | `ValidationError` 422 starting `STOCK_REPORT_TARGET_OUT_OF_RANGE:`; state unchanged | accept 0 | MC-7 row 4 |
| C1(e) | `SO(A, 5)` (n = 4) | same 422 | accept `n + 1` | MC-7 row 4 (adjacent pair with (b)/(f)) |
| C1(f) | `SO(D, 4)` | no-op (t == p == n) | — | MC-7 |
| C1(g) | `SO(N, 1)` | 422 `STOCK_REPORT_ROW_HAS_NO_PRIORITY:` | order a null-priority row | MC-7 row 5 |
| C1(h) | `SP(B, low)` | high = A1 C2 D3; low = X1 Y2 B3 | compute `max` including the mover / forget to close the gap | MC-7 row 6 |
| C1(i) | `SP(B, null)` | high = A1 C2 D3; B = (null, null) | leave the order | MC-7 row 7, §7 "null ⇔ null" |
| C1(j) | `SP(N, high)` | high = A1 B2 C3 D4 N5 | append at `n` | MC-7 row 8 |
| C1(k) | `SP(B, high)` | unchanged; no record; no event; zero writes | — | MC-7 row 9, B2 |
| C1(l) | `SP(N, null)` | unchanged; no record; no event | — | MC-7 row 9 |
| C1(m) | `SP(B, "urgent")` | 422 (`ValidationError`) | — | MC-7 "anything else → 422" |
| C1(n) | `SO(B, "2")` (non-integer) | 422 | — | MC-7 |
| C1(o) | `SP(row of the foreign workspace, low)` as U of W | `NotFound`; foreign state unchanged | — | M4 |
| C2(a) | two sessions: `SO(C, 1)` and `SO(D, 2)` barrier-released | high group is dense `1..4`; the end state equals one of the two sequential compositions (**inherent disjunction — unforced interleaving; recorded, see (c)**) | — | MC-7 race row 1 |
| C2(b) | `SO(A, 3)` vs `SP(N, high)` barrier-released | high dense `1..5`, N last | — | MC-7 race row 2 |
| C2(c) | session H opens a transaction and takes `pg_advisory_xact_lock(hashtext('stock_report_order:' \|\| W))`; then `SO(C, 1)` is started | the move does **not** complete within 0.5 s; after H commits it completes with high = A2 B3 C1 D4 | remove `acquire_stock_report_order_lock` → completes while H holds → red | MC-7 serialization (deterministic form) |
| C3(a) | `SP(B, low)` | exactly one new history record: `{type: priority_change, stock_report_item_id: B, priority: low, priority_order: 3, quantity_requested: B's, quantity_awaiting: B's live counter, created_by_id: S, created_at: ctx.now}` | write two records / omit the order | MC-6, §6.1, M5 |
| C3(b) | `SO(C, 1)` | one `priority_order_change` for C (`priority_order 1`); none for A or B | record for neighbours | MC-6, M5 |
| C3(c) | C1(c), C1(k), C1(l) | zero new records | — | MC-6 no-op |
| C3(d) | `SP(B, low)` with B's `quantity_awaiting = 4` (an awaiting assignment) | the record's `quantity_awaiting == 4` and `priority_order == 3` (after all mutations) | insert the record before the append | MC-6 timing |
| C4(a) | `GET` with `priority=high,medium,low` on high A1 B2 C3 D4, medium M1, low X1 Y2 | order `[A, B, C, D, M, X, Y]` | order by `priority` text → `high, low, medium` | §7A read order, M6 |
| C4(b) | `GET` with no `priority` and rows N1 (created first), N2 | `[N1, N2]` only (nulls by `created_at, client_id`) | return all rows | §7A, owner answer |
| C4(c) | `priority=urgent` | 422 `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER:` | ignore unknown tokens | §7A |
| C4(d) | `priority=` (empty) | nulls only | — | §7A |
| C4(e) | any row in the payload | keys exactly: `client_id`, `item_category {client_id, name, major_category}`, `properties`, `properties_signature`, `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`, `priority`, `priority_order`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id`; no `item_type`; no pagination key | — | §9 response shape (P18), master plan §5 |
| C4(f) | a soft-deleted row and a foreign-workspace row exist | neither is listed | drop a filter | MC-16, M4 |
| C4(g) | R's category K soft-deleted by raw SQL | R still listed with `item_category.name == "Dining Chairs"` | inner-join on `is_deleted = false` → R vanishes | MC-16 "serializes the deleted category's name" |
| C5(a) | `SP(B, low)` | B `updated_by_id == S`, `updated_at == ctx.now`; A, C, D, X, Y `updated_*` unchanged | stamp shifted neighbours | MC-17, §4.5 |
| C5(b) | `SO(C, 1)` | C stamped; A, B not | — | MC-17 |
| C6(a) | `SO(C, 1)` with `capture_dispatch` | exactly three `stock_report_item:updated` (C, A, B) with payload `priority`/`priority_order` after the move; none for D | emit for every row of the group | MC-19 "one per shifted neighbour" |
| C6(b) | C1(c) | no event | — | MC-19 no-op |
| C7(a)–C7(d) | `PATCH …/priority` as admin / manager / worker / seller | reached / reached / 403 / reached | — | MC-18 |
| C7(e)–C7(h) | `PATCH …/priority-order` as admin / manager / worker / seller | reached / reached / 403 / reached | — | MC-18 |
| C7(i)–C7(l) | `GET …/items` as admin / manager / worker / seller | reached ×4 | — | MC-18 |

## 7. Notes

- Sizing: 45 criterion rows in 7 criteria; `complex: yes`.
- C2(a)/(b) carry an inherent disjunction because the interleaving is unforced; C2(c) is the
  deterministic proof that the advisory lock is taken. The reviewer treats (a)/(b) as invariant
  checks, not as the serialization proof.
- Dense-order and nullness invariants after every C1 row are covered by `assert_stock_report_clean`
  (the `order_density` and `priority_order_nullness` kinds).
- The list endpoint is exempt from the `07_queries_local` pagination gate by ratified owner answer
  (master plan §5); do not add `_pagination`.

## 8. Review log

(empty)
