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
`app/tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py`,
`test_stock_report_ordering_locks.py`; `app/tests/integration/services/queries/stock_report/test_list_stock_report_items.py`.
(**Renamed at the batch D fold, §9 rule 19** — the planned `test_priority_and_ordering.py` and
`test_ordering_locks.py` are bare names in a tree whose test packages carry no `__init__.py`; both
are unique today, and both are exactly the shape that collided in batch C1.)
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
   major_category, **image_url**}`, `properties` (stored, normalized), `properties_signature`, the four quantities,
   `priority`, `priority_order`, `created_at`, `updated_at` (ISO UTC), `created_by_id`, `updated_by_id`.
6. Router: three routes; role lists per master plan §6.6.
7. Tests first from the table.

## 6. Criteria

Fixture: **F0**'s workspace with rows inserted via the demand service or ORM: group `high` = A1 B2 C3
D4 (four rows, orders 1–4), group `low` = X1 Y2, and N (priority null), exactly as MC-7's table; the
foreign workspace holds the same shapes. `SP(row, p)` / `SO(row, t)` = the two commands as seller
**S** (a permitted role). "state" = the `(priority, priority_order)` of every row in W. Every row
ends with `assert_stock_report_clean`.

Every outcome in this table is computed from the fixture's **own** values (`high` = A1 B2 C3 D4, `low` = X1 Y2, N null/null, and F0's `quantity_requested`/live counters) plus this row's own deltas, **side effects included** — the gap close, the append, the stamp, the history record and the events are part of the outcome, not extras. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.

**How the fixture is built — the choice is named, not offered** (L-30). Rows are created through the demand service `AD` (the only creator of rows); `priority` and `priority_order` are then written by raw SQL in the seed, never by the commands under test. **The seed orders the groups against their ordering key** (L-14): in `high`, `priority_order` ascending must **disagree** with `client_id` ascending — the row at order 1 carries the group's largest `client_id` and the row at order 4 its smallest. `client_id` is a ULID with no monotonic counter (master plan §10), so creation order is not `client_id` order either; every row whose outcome names an order asserts it against the seeded `priority_order` (or, for the null listing, `created_at`), never against insertion order. Without this the phase's whole point — ordering — is proven by a fixture in which three different orderings agree.

Tenancy rows (C1(o), C4(f)) use a **cross-workspace reference** (L-16): the foreign row is otherwise a valid target of the same request — same category name, same properties, same `high` group with the same orders — so tenancy is the only reason the call refuses or omits it.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `SO(C, 1)` | high = A2 B3 C1 D4 | `_ordering.py:shift_within_group` (def.): shift `[t, p]` instead of `[t, p−1]` → C lands at 1 with A still at 1 → `order_density` diverges → red | MC-7 row 1, M6 |
| C1(b) | `SO(A, 3)` | high = B1 C2 A3 D4 | `_ordering.py:shift_within_group` (def.): shift `[p, t]` instead of `[p+1, t]` → A is shifted with the block it is leaving → red | MC-7 row 2 |
| C1(c) | `SO(B, 2)` | unchanged; no record; no event; no stamp; `count_writes` on the four tables `== 0` | `set_stock_report_item_priority_order.py` (def.): delete the `t == p` short-circuit → the `−1`/`+1` pair still runs and the mover is re-written, so `count_writes` on the four tables is non-zero and one `priority_order_change` record appears → red | MC-7 row 3, B2 |
| C1(d) | `SO(A, 0)` | `ValidationError` 422 starting `STOCK_REPORT_TARGET_OUT_OF_RANGE:`; state unchanged | `set_stock_report_item_priority_order.py` (def.): widen the range guard to `0 <= t <= n` → `SO(A, 0)` is accepted → red | MC-7 row 4 |
| C1(e) | `SO(A, 5)` (n = 4) | same 422 | `set_stock_report_item_priority_order.py` (def.): widen the range guard to `1 <= t <= n + 1` → `SO(A, 5)` is accepted → red. Adjacent pair with C1(d); both runs recorded (§9 rule 8) | MC-7 row 4 (adjacent pair with (b)/(f)) |
| C1(f) | `SO(D, 4)` | no-op (t == p == n) | `set_stock_report_item_priority_order.py` (def.): narrow the range guard to `1 <= t <= n − 1` → `SO(D, 4)` answers 422 instead of the no-op → red. C1(d)/C1(e) stay green under this mutant, which is what makes the upper boundary its own sub-check (L-12) | MC-7 |
| C1(g) | `SO(N, 1)` | 422 `STOCK_REPORT_ROW_HAS_NO_PRIORITY:` | `set_stock_report_item_priority_order.py` (def.): drop the `priority IS NULL → ValidationError` guard → `n` is computed over the null rows and the move proceeds → red | MC-7 row 5 |
| C1(h) | `SP(B, low)` | high = A1 C2 D3; low = X1 Y2 B3 | two mutants at `_ordering.py` (def.), **both runs recorded**: (i) `append_to_priority_group` computes `max` over a set that still includes the mover → B lands at 3 in `low` with Y already at 2 → wrong order; (ii) skip `close_priority_gap` for the source group → `high` stays `A1 C3 D4` → `order_density` diverges | MC-7 row 6 |
| C1(i) | `SP(B, null)` | high = A1 C2 D3; B = (null, null) | `set_stock_report_item_priority.py` (def.): omit `priority_order = NULL` from the mover's UPDATE when the target priority is null → B keeps order 3 with a null priority → `priority_order_nullness` diverges → red | MC-7 row 7, §7 "null ⇔ null" |
| C1(j) | `SP(N, high)` | high = A1 B2 C3 D4 N5 | `_ordering.py:append_to_priority_group` (def.): return `max` instead of `max + 1` → N lands at 4 beside D → `order_density` diverges → red | MC-7 row 8 |
| C1(k) | `SP(B, high)` | unchanged; no record; no event; zero writes | `set_stock_report_item_priority.py` (def.): delete the `X == Y` short-circuit → the source gap closes and B re-appends at `high 3`, one `priority_change` record is written and `count_writes` is non-zero → red | MC-7 row 9, B2 |
| C1(l) | `SP(N, null)` | unchanged; no record; no event | `set_stock_report_item_priority.py` (def.): write the short-circuit as `if Y is not None and X == Y` → the `null → null` case falls through, NULL/NULL is re-written, `updated_*` is stamped and a record is inserted → red. Same site as C1(k), a **different branch of it**; both runs recorded (§9 rule 8) | MC-7 row 9 |
| C1(m) | `SP(B, "urgent")` | 422 (`ValidationError`) | `requests/__init__.py` (def.): widen `SetStockReportItemPriorityRequest.priority` to `str \| None` → `"urgent"` reaches the command and nothing raises → red. **Rule 17, measured on the installed pydantic 2.11.3:** a `StockReportPriorityEnum \| None` field rejects `"urgent"` by value, accepts `"high"` and `null`, and 422s an omitted key (the field carries no default); the parse function converts pydantic's error into `bm.errors.validation.ValidationError`, which is the only class that yields 422 here | MC-7 "anything else → 422" |
| C1(n) | `SO(B, "2")` (non-integer) | 422 | `requests/__init__.py` (def.): declare `priority_order` as a plain `int` instead of `StrictInt` → **measured on the installed pydantic 2.11.3, lax mode coerces `"2"` to `2`**, the call returns a 200 no-op and the row reddens. The row is decidable only if that field is strict; this cell is where that contract is pinned (rule 17) | MC-7 |
| C1(o) | three calls as U of W — `SP(row of the foreign workspace, low)`, `SP(a soft-deleted row of W, low)`, `SP("sri_absent", low)`. The foreign row is a **cross-workspace reference** (preamble): same category, same properties, same `high` group with the same orders, so tenancy is the only reason it refuses | `NotFound` each; no state anywhere changes; the foreign workspace's group is byte-identical | three mutants at `set_stock_report_item_priority.py`'s row lookup (def.), **all three runs recorded** (L-34's three visibility cells): (i) drop the `workspace_id` term → the foreign row is found and moved; (ii) drop `is_deleted = false` → the soft-deleted row is moved and `priority_order_nullness` diverges; (iii) return the serialized row instead of raising when the lookup finds nothing → the absent id answers 200 | M4 |
| C2(a) | two sessions: `SO(C, 1)` and `SO(D, 2)` barrier-released | high group is dense `1..4`; the end state equals one of the two sequential compositions (**inherent disjunction — unforced interleaving; recorded, see (c)**) | **class 3 — no mutant can force this row**, because the interleaving is unforced (§9 rule 9). Treat it as an invariant check, never as the serialization proof. Structural property the reviewer derives (L-32), stated as a post-condition and not as a statement to look at: *after either serialisation the `high` group is exactly `1..4` with no gap and no duplicate, and the on-disk state equals one of the two sequential compositions.* The serialization itself is proven deterministically by **C2(c)**; C2(c) does **not** cover this row's density-under-a-real-race half, and nothing in this phase does | MC-7 race row 1 |
| C2(b) | `SO(A, 3)` vs `SP(N, high)` barrier-released | high dense `1..5`, N last | **class 3 — unforced interleaving**, same treatment as C2(a). Structural property (L-32): *after either serialisation `high` is exactly `1..5`, N holds order 5, and the state equals one of the two sequential compositions.* Deterministic serialization evidence: **C2(c)** | MC-7 race row 2 |
| C2(c) | session H opens a transaction and takes `pg_advisory_xact_lock(hashtext('stock_report_order:' \|\| W))`; then `SO(C, 1)` is started | the move does **not** complete within 0.5 s; after H commits it completes with high = A2 B3 C1 D4 | remove `acquire_stock_report_order_lock` → completes while H holds → red | MC-7 serialization (deterministic form) |
| C3(a) | `SP(B, low)` | exactly one new history record: `{type: priority_change, stock_report_item_id: B, priority: low, priority_order: 3, quantity_requested: B's, quantity_awaiting: B's live counter, created_by_id: S, created_at: ctx.now}` | two mutants at `set_stock_report_item_priority.py` (def.), **both runs recorded**: (i) insert the `priority_change` record twice (once before and once after the append) → two records → red; (ii) omit `priority_order` from the record's values → the record's order reads NULL → red | MC-6, §6.1, M5 |
| C3(b) | `SO(C, 1)` | one `priority_order_change` for C (`priority_order 1`); none for A or B | `_ordering.py:shift_within_group` (def.): emit one `priority_order_change` record per row returned by the shift statement → records appear for A and B → red | MC-6, M5 |
| C3(c) | C1(c), C1(k), C1(l) | zero new records | `set_stock_report_item_priority.py` / `set_stock_report_item_priority_order.py` (def.): insert the history record **before** the `X == Y` / `t == p` short-circuit → one record per no-op appears → red. Shares the short-circuit site with C1(c)/C1(k)/C1(l)/C6(b); the run against **this** row's record-count assertion is recorded separately (§9 rule 8) | MC-6 no-op |
| C3(d) | `SP(B, low)` with B's `quantity_awaiting = 4` (an awaiting assignment) | the record's `quantity_awaiting == 4` and `priority_order == 3` (after all mutations) | `set_stock_report_item_priority.py` (def.): insert the record before the append and before the counter read → `priority_order` reads NULL and `quantity_awaiting` reads the pre-move value → red | MC-6 timing |
| C4(a) | `GET` with `priority=high,medium,low` on high A1 B2 C3 D4, medium M1, low X1 Y2 | order `[A, B, C, D, M, X, Y]` | `list_stock_report_items.py` (def.): order by the `priority` column's text instead of the `CASE` expression → `high, low, medium` → red | §7A read order, M6 |
| C4(b) | `GET` with no `priority`, and two null-priority rows N1 and N2 seeded by **two separate `AD` calls** so their `created_at` differ, with the pair chosen so that `created_at` ascending **disagrees** with `client_id` ascending (preamble) | `[N1, N2]` only (nulls by `created_at, client_id`) | two mutants at `list_stock_report_items.py` (def.), **both runs recorded** (L-12, one per sub-check): (i) drop the `priority IS NULL` predicate when the parameter is omitted → every row is returned → red; (ii) order the null listing by `client_id` only → N1/N2 come back reversed, because the preamble pins the pair so that `created_at` ascending disagrees with `client_id` ascending | §7A, owner answer |
| C4(c) | `priority=urgent` | 422 `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER:` | `list_stock_report_items.py` (def.): drop the token-membership check and filter on whatever was sent → `priority=urgent` returns an empty list with 200 → red | §7A |
| C4(d) | `priority=` (empty) | nulls only | `list_stock_report_items.py` (def.): strip empty tokens before the branch, so `priority=` is treated as the unknown-token case → 422 instead of the null listing → red. C4(b)'s mutants leave this row green and vice versa (L-12) | §7A |
| C4(e) | any row in the payload | keys exactly: `client_id`, `item_category {client_id, name, major_category}`, `properties`, `properties_signature`, `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`, `priority`, `priority_order`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id`; no `item_type`; no pagination key | two mutants at `serialize_stock_report_item` (def.), **both runs recorded** (L-13, one per direction): (i) add `"item_type": row.item_category_id` → an extra key → red; (ii) drop `properties_signature` → a missing key → red | §9 response shape (P18), master plan §5 |
| C4(f) | a soft-deleted row and a foreign-workspace row exist | neither is listed | two mutants at `list_stock_report_items.py` (def.), **both runs recorded**: (i) drop `is_deleted = false` → the soft-deleted row is listed; (ii) drop `workspace_id` → the foreign row is listed. One predicate per sub-check; either alone leaves the other half green | MC-16, M4 |
| C4(g) | R's category K soft-deleted by raw SQL | R still listed with `item_category.name == "Dining Chairs"` | `list_stock_report_items.py` (def.): load categories with an inner join carrying `ItemCategory.is_deleted == False` instead of the batch load by id → R vanishes from the payload → red | MC-16 "serializes the deleted category's name" |
| C5(a) | `SP(B, low)` | B `updated_by_id == S`, `updated_at == ctx.now`; A, C, D, X, Y `updated_*` unchanged | `set_stock_report_item_priority.py` (def.): add `updated_by_id = :actor, updated_at = :now` to the SET list of the shift statements as well as the mover's → A, C, D are stamped → red | MC-17, §4.5 |
| C5(b) | `SO(C, 1)` | C stamped; A, B not | `_ordering.py:shift_within_group` (def.): add `updated_by_id = :actor, updated_at = :now` to the shift statement's SET list → A and B are stamped → red. C5(a)'s mutant sits at the priority command's stamp site, this one at the shift statement; **both runs recorded** (§9 rule 8 — the cells are not the same edit) | MC-17 |
| C6(a) | `SO(C, 1)` with `capture_dispatch` | exactly three `stock_report_item:updated` (C, A, B) with payload `priority`/`priority_order` after the move; none for D | `set_stock_report_item_priority_order.py` (def.): build one `:updated` event per row of the group instead of per row returned by the shift statements → a fourth event for D appears → red | MC-19 "one per shifted neighbour" |
| C6(b) | C1(c) | no event | `set_stock_report_item_priority_order.py` (def.): build the `:updated` event **before** the `t == p` short-circuit → one event is dispatched for a no-op → red. Shared short-circuit site with C1(c)/C3(c); this run is recorded against the dispatch-list assertion (§9 rule 8) | MC-19 no-op |
| C7(a)–C7(d) | `PATCH …/priority` as admin / manager / worker / seller | reached / reached / 403 / reached | `bm/routers/api_v1/stock_report.py`, the `require_roles([...])` list of the `PATCH …/priority` route (def.) — **both directions run and recorded** (L-13/L-24): (i) remove the role under test → its "reached" cell answers 403; (ii) add `WORKER` to the list → the 403 cell reaches the service | MC-18 |
| C7(e)–C7(h) | `PATCH …/priority-order` as admin / manager / worker / seller | reached / reached / 403 / reached | `bm/routers/api_v1/stock_report.py`, the `require_roles([...])` list of the `PATCH …/priority-order` route (def.) — both directions, as C7(a)–(d), run and recorded separately: this is a **second route**, not the same edit (§9 rule 8) | MC-18 |
| C7(i)–C7(l) | `GET …/items` as admin / manager / worker / seller | reached ×4 | `bm/routers/api_v1/stock_report.py`, the `require_roles([...])` list of the `GET …/items` route (def.): remove the role under test → that cell answers 403 → red. Four runs, one per role, each recorded — every cell here is "reached", so there is no opposite direction to run | MC-18 |

## 7. Notes

- Sizing: 45 criterion rows in 7 criteria; `complex: yes`.
- C2(a)/(b) carry an inherent disjunction because the interleaving is unforced; C2(c) is the
  deterministic proof that the advisory lock is taken. The reviewer treats (a)/(b) as invariant
  checks, not as the serialization proof.
- Dense-order and nullness invariants after every C1 row are covered by `assert_stock_report_clean`
  (the `order_density` and `priority_order_nullness` kinds).
- The list endpoint is exempt from the `07_queries_local` pagination gate by ratified owner answer
  (master plan §5); do not add `_pagination`.

**Added by the batch D projection + fold, 2026-09-21 (round 0). Nothing below changes a criterion outcome.**

- **L-26 is already discharged for `count_writes`.** The instrument behind C1(c) was measured
  capable of returning non-zero on 2026-09-21 (batch B2 re-review: three writes observed under an
  apply-then-reject probe in `receive_stock_demand_webhook.py`; plan 6 §7). No round in this phase
  buys that observation again.
- **C2(a)/C2(b) are class-3 rows** (§9 rule 9 + L-32): the interleaving is unforced, so each cell
  now states the **post-condition the reviewer derives**, not a statement to look at. C2(c) is the
  deterministic serialization proof and is the only row in this phase that proves the advisory lock
  is taken; it does **not** cover the density-under-a-real-race half of (a)/(b), and nothing does.
- **Rule 17, the request models (measured on the installed pydantic 2.11.3).** A plain `int` field
  coerces the string `"2"` to `2` in lax mode, so C1(n)'s 422 exists only if `priority_order` is
  declared `StrictInt` (or the model is strict). `StockReportPriorityEnum | None` rejects
  `"urgent"` by value and accepts `"high"`/`null`; an omitted key is itself a 422 because the field
  carries no default. Only `bm.errors.validation.ValidationError` reaches a 422 — a pydantic error
  escaping the command becomes a 500 — so both request models need a `parse_*_request` wrapper of
  the shipped `requests/__init__.py` shape.
- **Where `client_id` comes from** (projection ledger D-2, unresolved in the plan): §9B ruling 1
  says the router injects the path param and the request model drops the field, but names no key.
  The one shipped precedent is phase 8A's route — `incoming_data={**body.model_dump(), "client_id":
  client_id}`, with `client_id: str` **kept on the service-side request model** while the router's
  body model omits it and carries `extra="forbid"`. Following it is a coordinator/owner call
  because §6.5's registered model shape does not carry the field.

## 8. Review log

(empty)


---

## Review log — owner addition, 2026-09-21: `item_category.image_url`

**The owner asked for the item category's `image_url` to surface on stock-report instances — a
promise already made to the frontend.** Added to `serialize_stock_report_item`'s `item_category`
block above, so the nested shape is now **four** keys: `client_id`, `name`, `major_category`,
`image_url`.

**It lands here rather than as a post-batch patch, and that is the whole point.** The owner
expected to bolt this on after batch D closed, which would have meant editing an APPROVED phase —
an owner decision plus a re-gate. It does not: `serialize_stock_report_item` is **phase 12's own
new function**, unwritten today, and it already receives the resolved `category` object as a
keyword argument. So there is no join to add, no query to change, and no approved code to reopen —
it is one key in a dict this phase is writing from scratch, and it gets a criterion row and a test
like everything else in the phase.

`ItemCategory.image_url` is `Mapped[str | None]`, `String(1024)`, nullable
(`models/tables/items/item_category.py:23`), so the key is `str | None` and **the serializer must
emit it as `None`, never omit it** — an absent key and a null key are different things to a
frontend renderer, and the row below pins the key's presence, not just its value.

**This row is armable and must be armed:** a mutation dropping `image_url` from the returned dict
reddens it. Do not let it ship as a key nobody asserts.

**Whose authority.** The owner instructed this directly. It is recorded here rather than applied
silently, and the criterion text below is the orchestrator's transcription of that instruction —
correct it if it overreaches.
