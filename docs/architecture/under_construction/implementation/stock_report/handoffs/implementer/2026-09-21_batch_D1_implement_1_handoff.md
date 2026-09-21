---
batch: D1
plan: [12, 13]
role: implement
round: 1
state: IMPLEMENTED
date: 2026-09-21
actor: Opus implementer (orchestrated subagent, slot `d1`)
---

# Batch D1 implementation handoff — phases 12 and 13

Both phases are implemented, both checkpoints are committed, and the one L4 reconciles
exactly against the 23-ID baseline in both directions. **One owner card** — a
contradiction between the RATIFIED intention and the shipped four-key `item_category`.

This project runs a tester (master plan §3B), so this round carries **no row-level
coverage map, no named mutation and no mutation ledger**. Not one mutation was run.
What follows is the tester contract.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — the ratified intention still describes the board row's category as three keys

**Question.** May the intention's response-shape sentence be amended to the four-key
`item_category` (adding `image_url`) that the code and the published frontend contract
already carry — yes, or should the code drop the key instead?

**Story.** You asked on 2026-09-21 for the category's picture to reach the stock-report
board, and the API document that went to the frontend the same day promises
`image_url` on every row, `null` when a category has no picture. The board code now
sends it. But the intention — the document everything else is derived from — still
says the category is three fields. Nobody is blocked today. Six months from now
someone re-derives the board from the intention, drops a key the app renders, and the
pictures quietly disappear from a screen that has shown them all year.

**Branches.**
- *Amend the intention (add a lettered note):* the three documents agree again; five
  minutes of your time; nothing in the code or the frontend changes.
- *Drop the key from the code:* the frontend promise made today is broken and must be
  withdrawn, and the row you personally added is reverted.
- *Leave it:* the shipped behaviour is right, and the root document stays wrong.

**Recommendation.** Amend the intention — the four-key shape is the one you instructed,
the one already promised to the frontend, and the only one that renders.

**On silence.** Nothing changes: the code keeps the four keys, the frontend contract
stands, and the intention stays inconsistent until you rule. The gate holds on the
amendment, not on the batch.

**Trace.** Intention §9 "Response shapes"; plan 12 C4(e) and its Review-log note;
`HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` §6.1.

---

## 1. Checkpoints (both on a clean tree)

| Phase | SHA | Subject |
|---|---|---|
| 12 | **`568a1cb`** | `CHECKPOINT (not approved): stock_report phase 12 — priority, dense ordering, history records, the list endpoint` |
| 13 | **`b6cbbb9`** | `CHECKPOINT (not approved): stock_report phase 13 — row deletion cascade, second self-heal trigger, assignment reads` |

Both committed with **explicit paths**; `git add -A` was never used, and nothing was
pushed. Starting point was `6aed93f` (the orchestrator's own docs-only commit on top of
`fa301fd`; `git diff fa301fd 6aed93f -- app/` is empty, so the code baseline is
unchanged).

## 2. The one L4 stamp

**Tree:** `b6cbbb9`, `git status --porcelain` empty at the moment of the run.
**Command:** `cd app && BEYO_TEST_SLOT=d1 PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q`
**Result:** **23 failed / 3739 passed / 1 skipped**, 75 s.

**Failure-ID diff against `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`
(23 IDs), both directions:**

```
=== in mine, not in the baseline ===
(empty)
=== in the baseline, not in mine ===
(empty)
```

23 = 23, zero unexplained in either direction. The two slot-sensitive
`test_database_isolation.py` IDs are present, as §10's ruling requires under a
non-`main` slot.

**Pass-count arithmetic, reconciled from 3679:**

| Source | New cases |
|---|---|
| `test_stock_report_priority_and_ordering.py` | 15 |
| `test_stock_report_ordering_locks.py` | 1 |
| `test_list_stock_report_items.py` | 6 |
| `test_delete_stock_report_item.py` | 6 |
| `test_list_stock_task_assignments.py` | 5 |
| `test_stock_report_router.py` (26 → 53 collected) | 27 |
| **Total** | **60** |

`3679 + 60 = 3739`. Exact.

**Lint.** `ruff check` over every file this round touched: **clean**. Repo-wide
`ruff check .` reports **140 errors across 84 files** — and **zero of the 20 `app/`
files this round touched appear in that set** (verified by intersecting the two file
lists), so all 140 are pre-existing. One of them sits inside phase 12's L2 surface and
was deliberately left alone: `tests/integration/services/commands/stock_report/
test_apply_stock_demand_timing.py:15` `F401 sqlalchemy.text imported but unused`
(APPROVED phase 6; `git diff HEAD` on that file is empty).

No mutation probe was applied, so **the list of files a mutation probe touched is
empty** — "no production changes beyond the perimeter" is falsifiable against the two
checkpoint commits alone.

## 3. The production write perimeter

Every file created or edited by this session. Nothing outside the two plans' §4 lists
except the authorised `_row_values` replacement below.

**New — phase 12**
- `app/beyo_manager/services/commands/stock_report/_row_values.py`
- `app/beyo_manager/services/commands/stock_report/_ordering.py`
- `app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority.py`
- `app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority_order.py`
- `app/beyo_manager/services/queries/stock_report/list_stock_report_items.py`

**New — phase 13**
- `app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py`
- `app/beyo_manager/services/commands/stock_report/delete_stock_report_item.py`
- `app/beyo_manager/services/queries/stock_report/list_stock_task_assignments.py`

**Edited**
- `app/beyo_manager/domain/stock_report/serializers.py` — `serialize_stock_report_item`
  added; the three shipped serializers untouched (plan 13 adds none, owner card 5).
- `app/beyo_manager/services/commands/stock_report/requests/__init__.py` — the two
  models and their two parse wrappers.
- `app/beyo_manager/routers/api_v1/stock_report.py` — five routes, two body models,
  `_run` gained a `query_params` argument.

**New tests**
- `app/tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py`
- `app/tests/integration/services/commands/stock_report/test_stock_report_ordering_locks.py`
- `app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py`
- `app/tests/integration/services/queries/stock_report/test_list_stock_report_items.py`
- `app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py`

**Edited tests**
- `app/tests/unit/routers/api_v1/test_stock_report_router.py` — appended only; no
  existing case was changed.

**Documents**
- `plans/plan_12.md` §8 Review log · `plans/plan_13.md` §8 Review log · this handoff.
  **No tracker row was written** — master plan §4 reserves phase rows (`PENDING →
  IMPLEMENTED → VERIFIED`) and §4A's batch row to the orchestrator, which overrides the
  executor doctrine's closing step 2. Please set them.

**Tool-recorded state**
- `.archgraph/architecture.yml` — see §8 below.

### The authorised touch: `_row_values` (master plan §6.5, ledger D-6)

`bm/services/commands/stock_report/_row_values.py` created with `row_values(row) -> dict`,
and **exactly the three** registry-named copies replaced by an import:

- `create_stock_task_assignments.py:56` · `sync_task_stock_assignments.py:36` ·
  `delete_stock_task_assignments.py:34`

The replacement is byte-for-byte equivalent: the block was removed programmatically
after asserting it appeared exactly once per file, and every `_row_values(` call site
was renamed to `row_values(`. `priority` is still emitted as `.value`, never the enum
member. **No test file of those three modules was edited**, and all three suites are
green — that is the inertness proof the gate checklist asks for.

`repair_stock_report.py:325-331` was **not** touched. Note for the coordinator, not a
change: it still builds the same six keys inline inside an event `extra=`, with a
truthiness test rather than `is not None`, so `priority_order = 0` would be emitted as
`None` there. It belongs to APPROVED phase 3 and folding it in is out of perimeter.

## 4. Tests I wrote → the row each aimed at (claims, not evidence)

### Phase 12 — `test_stock_report_priority_and_ordering.py`

| Test | Row(s) it aims at |
|---|---|
| `test_move_up_shifts_only_the_block_it_enters` | C1(a); also touches C3(b), C5(b), C6(a) |
| `test_move_down_shifts_only_the_block_it_leaves` | C1(b) |
| `test_move_to_the_held_position_writes_nothing` | C1(c); also touches C3(c), C6(b) |
| `test_target_outside_the_group_is_refused[0]` | C1(d) |
| `test_target_outside_the_group_is_refused[5]` | C1(e) |
| `test_last_position_of_the_group_is_a_noop_not_a_refusal` | C1(f) |
| `test_row_without_a_priority_cannot_be_ordered` | C1(g) |
| `test_non_integer_target_is_a_validation_error` | C1(n), at command scope |
| `test_priority_change_closes_the_source_gap_and_appends` | C1(h); also touches C3(a), C5(a) |
| `test_priority_cleared_nulls_the_order_too` | C1(i) |
| `test_null_row_given_a_priority_is_appended_last` | C1(j) |
| `test_setting_the_priority_a_row_already_has_writes_nothing[B-high]` | C1(k); also C3(c) |
| `…[N-None]` | C1(l) |
| `test_unknown_priority_token_is_a_validation_error` | C1(m), at command scope |
| `test_priority_lookup_refuses_foreign_deleted_and_absent_rows` | C1(o), all three cells |

### Phase 12 — `test_stock_report_ordering_locks.py`

| Test | Row |
|---|---|
| `test_the_move_waits_for_the_workspace_ordering_lock` | C2(c) |

### Phase 12 — `test_list_stock_report_items.py`

| Test | Row(s) |
|---|---|
| `test_read_order_is_high_medium_low_then_priority_order` | C4(a) |
| `test_no_filter_lists_only_null_priority_rows_by_created_at` | C4(b) and C4(d) |
| `test_unknown_priority_token_is_refused` | C4(c) |
| `test_row_shape_carries_the_four_key_category_including_a_null_image` | C4(e), both fixture rows |
| `test_soft_deleted_and_foreign_rows_are_not_listed` | C4(f) |
| `test_a_row_whose_category_was_soft_deleted_still_serializes_its_name` | C4(g) |

### Phase 13 — `test_delete_stock_report_item.py`

| Test | Row(s) |
|---|---|
| `test_cascade_removes_every_assignment_and_soft_deletes_the_row` | C1(a); also touches C3(a) |
| `test_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order` | C1(b); also C3(a)'s event list |
| `test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded` | C2(a) |
| `test_instrument_c_reads_stored_before_fresh_after_the_guarded_statement` | C2(b) |
| `test_delete_refuses_deleted_absent_and_foreign_rows` | C1(d), all three cells |
| `test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` | **a narrower probe of C1(c)'s premise, NOT C1(c)** — see §6 |

### Phase 13 — `test_list_stock_task_assignments.py`

| Test | Row(s) |
|---|---|
| `test_every_non_deleted_state_is_listed_in_created_at_client_id_order` | C4(a) |
| `test_the_element_is_the_fourteen_key_shape_with_its_two_nested_objects` | C4(b), the list side only |
| `test_the_create_and_list_surfaces_return_the_same_key_set` | C6(a) |
| `test_the_row_lookup_refuses_deleted_absent_and_foreign_rows` | C4(d), all three cells |
| `test_a_row_with_no_assignments_answers_an_empty_list` | **no row** — candidate, see §6 |

### Router (`test_stock_report_router.py`, 27 new cases)

| Test | Row(s) |
|---|---|
| `test_ordering_routes_reach_service_for_permitted_roles` (3 roles × 2 routes) | C7(a),(b),(d) and C7(e),(f),(h) |
| `test_ordering_routes_reject_worker` (2) | C7(c), C7(g) |
| `test_list_items_route_reaches_service_for_every_role` (4) | C7(i)–(l) |
| `test_ordering_routes_refuse_malformed_bodies` (3) | C1(m), C1(n) at the HTTP boundary |
| `test_delete_item_route_reaches_service_for_admin_and_manager` (2) | C5(a), C5(b) |
| `test_delete_item_route_rejects_worker_and_seller` (2) | C5(c), C5(d) |
| `test_list_assignments_route_reaches_service_for_every_role` (4) | C5(e)–(h) |
| `test_ordering_routes_refuse_unknown_fields` (2) | **no row** — candidate, see §6 |
| `test_list_items_route_passes_no_priority_when_the_param_is_absent` (1) | **no row** — candidate |
| `test_priority_route_accepts_an_explicit_null` (1) | **no row** — candidate |

## 5. One load-bearing pointer per criterion — where the behaviour is made true

Paths are relative to `app/beyo_manager/`.

**Where the advisory lock is taken, and where the group `FOR UPDATE` is taken** (all
three commands take the advisory lock as the **first statement inside `maybe_begin`**):

| Command | Advisory lock | Group `FOR UPDATE` (one statement, `ORDER BY client_id`) |
|---|---|---|
| priority | `services/commands/stock_report/set_stock_report_item_priority.py:set_stock_report_item_priority` (`acquire_stock_report_order_lock`) | `…:_lock_row_and_groups` — `or_(client_id == R, priority.in_([source, target]))` |
| priority-order | `services/commands/stock_report/set_stock_report_item_priority_order.py:set_stock_report_item_priority_order` | `…:_lock_row_and_group` — `or_(client_id == R, priority == p)` |
| delete | `services/commands/stock_report/delete_stock_report_item.py:delete_stock_report_item` | `…:_lock_row_and_group`, between `lock_tasks` and `lock_stock_task_assignments` |

**Where each shift statement's `RETURNING` is consumed into events.** All three shifts
are `services/commands/stock_report/_ordering.py:_shift`, which returns the six event
fields plus `client_id`; the consumers are:
- `set_stock_report_item_priority.py:set_stock_report_item_priority` — the `events.extend(...)`
  over `sorted(shifted, key=lambda r: r["priority_order"])`, after the mover's own event;
- `set_stock_report_item_priority_order.py:set_stock_report_item_priority_order` — same shape;
- `_delete_stock_report_item_cascade.py:cascade_delete_stock_report_item` — the
  `events.extend(...)` immediately after `close_priority_gap`.
The mover's own `:updated` comes from its own `UPDATE … RETURNING` (`_MOVER_RETURNING`
in each command), never from the ORM instance.

**The two fresh `SELECT`s in the cascade**, both in
`_delete_stock_report_item_cascade.py:cascade_delete_stock_report_item`:
1. **counter `stored_before`** — the `stored_counters` `SELECT` of the three counters,
   taken **once after the assignment loop ends**, and used as `stored_value` on each
   repair record. (The *inline* repair inside a single move is the approved
   `_move_assignment.py:_apply_counter_delta`, which already reads fresh after its
   guarded statement returned zero rows — that is what C2(b) actually exercises.)
2. **gap-close `removed_order`** — the `position` `SELECT` of
   `(priority, priority_order)`, taken immediately before `close_priority_gap`. **It is
   a fresh `SELECT`, not `row.priority_order` as loaded at the lock.** Nothing in
   phase 13 can observe it (§6).

**Where the short-circuits sit relative to the record insert and the event build:**
- `X == Y` — `set_stock_report_item_priority.py`, the `if source_priority == target_priority:`
  block, which `return`s **before** `close_priority_gap`, before the mover `UPDATE`,
  before `session.add(StockReportHistoryRecord(...))` and before any event is built. The
  only statements it runs are the locks and the response re-read.
- `t == p` — `set_stock_report_item_priority_order.py`, the `if target == position:`
  block, in the same position relative to the shift, the mover `UPDATE`, the record and
  the events. It sits **after** the null-priority and range guards, so `SO(D, 4)` is a
  no-op and not a 422.

**Where `stock_report_item:deleted` is built** — see §7, its own heading.

**Other pointers the tester will want:**
- the four-key `item_category` — `domain/stock_report/serializers.py:serialize_stock_report_item`;
- the read order — `services/queries/stock_report/list_stock_report_items.py:_PRIORITY_RANK`
  and the two `order_by` branches in `list_stock_report_items`;
- the filter parse and the 422 — `…:_parse_priority_filter`;
- `StrictInt` / enum-without-default — `services/commands/stock_report/requests/__init__.py`,
  `SetStockReportItemPriorityOrderRequest` and `SetStockReportItemPriorityRequest`; the
  pydantic→domain conversion is `parse_set_stock_report_item_priority_request` /
  `parse_set_stock_report_item_priority_order_request` in the same file;
- the MC-17 stamp on the mover only — the `.values(... updated_by_id=..., updated_at=...)`
  of each command's `_MOVER_RETURNING` `UPDATE`; `_ordering.py:_shift` sets **only**
  `priority_order`;
- rule 16 — `list_stock_task_assignments.py` applies **no** state predicate at all, so
  neither `ACTIVE_ASSIGNMENT_STATES` nor a spelled list appears; C4(a)'s second mutant
  (a hand-typed five-state list) is therefore a real edit at a real site.

## 6. Rows I know I did not exercise, and the seams behind them

**Plan 12**
- **C2(a), C2(b)** — not attempted. The plan declares them class 3 (unforced
  interleaving, no mutant can force them); the prompt says not to try. Nothing in this
  round runs two ordering operations from a barrier.
- **C3(d)** — not exercised. No test here gives B an `awaiting` assignment, so the
  record's `quantity_awaiting == 4` clause is unproven. The production code reads that
  value from the mover statement's `RETURNING`, so the seam exists; the fixture does not.
- **C4(b)'s second half is exercised differently from the cell's wording.** The cell
  seeds two null rows by two separate `AD` calls "with the pair chosen so that
  `created_at` ascending disagrees with `client_id` ascending". I could not *choose* a
  ULID pair, so I **back-dated the first row's `created_at` by raw SQL** and asserted it
  comes back first even though it does not sort first by `client_id`. That is the same
  discrimination by a different construction; the tester should decide whether it
  satisfies the cell as written.
- **C1(m)/C1(n) are exercised twice** (command scope and HTTP scope) but the cells name
  `requests/__init__.py` as the mutation site — the command-scope tests are the ones
  that site bites.

**Plan 13**
- **C1(c) — not exercised.** My
  `test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` asserts only
  that `discover_live_rows_by_identity` returns `{}` after the deletion. The row demands
  a **demand delivery** producing a new live row with empty history. Proving it at the
  lookup instead of at the delivery is a **relocation to a narrower surface**, which §9
  rule 17 reserves to the owner — so I am **not** claiming the row, and I am declaring
  the probe for what it is. The tester should build C1(c) at `apply_stock_demand`; note
  that `apply_stock_demand` refuses a session with an open transaction, so that test has
  to be a committing test with a `purge` in `finally` (the shape `test_apply_stock_demand.py`
  already uses).
- **The cascade's `actor_user_id=None` path — not exercised**, by design (plan §7: it
  belongs to 13A C3). The production code takes every stamp from its arguments and the
  module imports no context type, so the path is reachable; nothing here proves it.
- **C4(b)'s cross-suite observed-red set** and **C6(a)'s "phase 8's own key rows stay
  green under the mutant" half** — not run; both are the tester's.
- **C3(a)'s exact dispatched list** is asserted in full only in
  `test_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order`; the four-
  assignment test asserts counts and the absence of `:updated`, not an ordered list.

### A seam the tester should know about, and one it does not have

**The gap close's fresh `removed_order` has no *criterion* in this phase but it does
have a seam.** `cascade_delete_stock_report_item` is a public subordinate function, so a
test could call it **twice in one transaction** on two rows of the same group and watch
the second call renumber from a stale position. I did **not** write that test:
plan 13 authorises no such row, and authoring one here is a criterion change (§9 rule
17). Flagging it because the prompt is right that this is the requirement most likely to
pass D1 and fail D2 — if the orchestrator wants it armed inside D1, it is buildable
today and needs an owner-authored row.

**A seam that does not exist:** nothing in phase 13 distinguishes the counter repair's
`stored_before` freshness *at the second trigger* from an ORM read, because by the time
the loop ends the ORM instance and the database agree unless an earlier statement drifted
them. C2(b)'s planted defect lands on the **inline** repair inside `_move_assignment`,
not on the post-loop one. The post-loop `stored_before` is therefore unarmed in this
phase too.

## 7. Where `stock_report_item:deleted` is built

**`app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py:build_stock_report_item_deleted_event`**

Chosen, and it was **not a free choice**: plan 13 §4 does not list `_events.py`, which
belongs to APPROVED phase 8, so adding a builder there would be a perimeter violation.
The inline precedent is `apply_stock_demand.py`, which builds `stock_report_item:created`
the same way. It is a named module-level function, not an inline dict, precisely so plan
14's accuracy guard has a `file:symbol` to find.

**Two consequences for the coordinator** (neither is mine to act on):
1. §6.5 must register this name in the same act (§9 rule 18).
2. **Plan 14 C1(b)'s guard currently roots in `_events.py` alone and would not see it.**

It constructs `WorkspaceEvent(...)` directly with `extra={}`, exactly as both `_events.py`
builders do (`build_workspace_event` wants an object carrying `.client_id`, and this is a
bare id).

## 8. `PATCH …/priority-order` tenancy — which lookup both routes use

Both routes use the **same lookup shape, duplicated per command module** (C1(o) names
`set_stock_report_item_priority.py`'s lookup as its mutation site, so the terms have to
be in that file):

- `set_stock_report_item_priority.py:_find_row`
- `set_stock_report_item_priority_order.py:_find_row`

Both are `SELECT … WHERE workspace_id = ctx.workspace_id AND client_id = :id AND
is_deleted = false`, raising `NotFound("Stock report item not found.")` otherwise, and
both are followed by the same post-lock re-read (`row is None or row.is_deleted →
NotFound`). **The behaviour is therefore identical on the two routes.** No test and no
criterion row for the priority-order route was authored — that cell is the owner's.

## 9. Judgment calls, deviations, and what I found wrong in the plans

The full list with rationale is in each plan's §8 Review log. The ones that matter here:

1. **`shift_within_group(from_order, to_order)` means the mover's `p` and `t`**, not the
   band; the band and the sign are derived inside. §6.5 registers no direction argument.
2. **Both parse wrappers live in `requests/__init__.py`**, beside their models and the
   shipped `_raise_validation_error`, not in the two command modules. §6.5 names the
   functions but registers the models in `requests/__init__.py`, which is also §4's
   "Edited" entry and C1(m)/C1(n)'s mutation site. The registered names are unchanged.
3. **Event order is deterministic**: mover first, then neighbours ordered by their **new**
   `priority_order`. A shift's `RETURNING` order is not guaranteed by Postgres, and
   C6(a)'s cell lists `(C, A, B)`.
4. **A production defect found by a test and fixed in the same round.**
   `list_stock_report_items`' read-order `CASE` was first written as
   `case({...}, value=StockReportItem.priority)`. The mapping form binds each key as a
   bare parameter and asyncpg rejects it — *invalid input for query argument $2:
   `<StockReportPriorityEnum.HIGH: 'high'>` (expected str)* — so **every** `priority=`
   request would have been a 500. Rewritten as explicit `when` pairs comparing the column.
   C4(a)'s test is what caught it.
5. **Plan 12 C1(h) mutant (i) looks inert at the site.** The cell says computing `max`
   over a set that still includes the mover makes B land at `low 3` "with Y already at 2
   → wrong order" — but `low X1 Y2 B3` **is** the row's stated outcome. The mover is never
   a member of its destination group when the append runs (`X == Y` is short-circuited),
   and even counting its stale `high` order 2 gives `max(1,2,2)+1 = 3`, the same answer.
   Mutant (ii) of the same cell does bite. Reported, not acted on.
6. **Intention §9 "Response shapes" still says three keys** — owner card 1.
7. **Rule 17 contradiction check: no contradiction.** Measured on the installed pydantic
   2.11.3 before writing the commands: `StockReportPriorityEnum | None` with no default
   rejects `"urgent"` by value, accepts `"high"` and `null`, and 422s an omitted key;
   `StrictInt` refuses the string `"2"` instead of coercing it.

### Things I could have hidden and am reporting

- **My C2(b) test was ULID-order flaky in its first draft** and would have failed on
  roughly half its runs. The cascade's loop is ascending `client_id`; I created the two
  assignments with quantities 2 and 3 in *creation* order and asserted `stored_before ==
  "1"`, which only holds when the `q = 2` assignment sorts first. It now binds the
  quantities to the **sorted real ids** after creation. This is master plan §10 biting
  exactly where §10 says it bites, inside a test written by someone who had just read §10.
- **My first C1(a) fixture planted counter drift by accident** — it edited an
  assignment's quantity *after* `CR` had already moved the counter by the old value, so
  the cascade correctly wrote a repair record the row did not expect. The fixture now
  seeds each assignment's own item at the intended quantity.
- **`test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row` does not
  discharge C1(c)** and I have said so above rather than letting the name imply it.
- **Four router tests trace to no criterion row** (`test_ordering_routes_refuse_unknown_fields`
  ×2, `test_list_items_route_passes_no_priority_when_the_param_is_absent`,
  `test_priority_route_accepts_an_explicit_null`) and one query test does
  (`test_a_row_with_no_assignments_answers_an_empty_list`). They are declared here as
  **candidate criteria** for the coordinator to fold or refuse: the first guards the
  batch-C1 S1 defect (a router body model without `extra="forbid"` silently drops an
  unknown field before the strict service model sees it); the second and third pin the
  two transports C4(b) and C1(i) depend on but do not themselves assert; the fifth pins
  that an assignment-less row answers `[]` rather than 404, which is the boundary C4(d)'s
  refusals are defined against. **If the coordinator refuses any of them, they should be
  deleted rather than shipped silently.**
- **The `_seller` / `_ctx` helper in the phase-12 test file bypasses `make_ctx` for the
  per-call context.** `make_ctx` is still the source of the identity dict, but
  `session.rollback()` expires the seed's ORM instances and a later read from a sync
  helper attempts IO outside the greenlet context. I hit that as a `MissingGreenlet` and
  worked around it rather than changing the kit.

## 10. Architecture-graph delta

One batched `apply_changes` against revision
`d6e9aee772c591e309c676516179e9b389a8bc5d10755b97a896d9d89ed723ad` (dry run first, then
applied; new revision `595a481323d34c0d203bb3af36a1d306c694ac1f1b445cc7dba7acf65036cae5`).
**9 nodes + 16 relationships, 0 skipped, 0 diagnostics.** All `ai_inferred` and pending
review; nothing was promoted, rejected or edited.

Nodes: `domain-stock-report-dense-ordering`, `command-set-stock-report-item-priority`,
`command-set-stock-report-item-priority-order`, `domain-stock-report-item-deletion-cascade`,
`command-delete-stock-report-item`, `endpoint-stock-report-board-writes`,
`query-list-stock-report-items`, `query-list-stock-task-assignments`,
`domain-stock-report-row-values-snapshot`. Granularity is mechanisms and boundaries, not
files; every evidence anchor is a **symbol**, never a line span.

**Symbol-level drift check (doctrine step 4).** This round deleted three private
`_row_values` functions. `grep -r "_row_values" .archgraph/` on the pre-round graph
(`git show HEAD:.archgraph/architecture.yml`) returns **0** occurrences, so no existing
anchor cited any of them. The three occurrences present now are all mine and all point at
the new module. **No drift to report.**

`.archgraph/architecture.yml` is the only file changed after the L4 stamp; **zero files
under `app/` changed after it**, so the stamp covers the code being handed over.

## 11. For the coordinator

- Tracker rows (§4 phase rows for 12 and 13, §4A batch row) are yours — I wrote none.
- Register `stock_report_item:deleted`'s build site in §6.5 (§7 above).
- Register `_row_values.py` as shipped and the three copies as replaced (§6.5 D-6 says
  "in the same act" — done in code, not in the registry text).
- Owner card 1 above; the priority-order tenancy proposal in §8 is yours to carry.
- Plan 12 C1(h) mutant (i) appears inert (§9 item 5) — it is a mutation cell, so it is
  foldable, but it is the owner's row shape that would change if the fix is to the outcome.
