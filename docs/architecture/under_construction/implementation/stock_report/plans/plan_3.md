# Plan 3 — Consistency check, manual repair, repair records, task-flag writer, two endpoints

```
state: NOT_STARTED
phase: 3 of 15
depends_on: 1 (APPROVED)
projection: mandatory (recomputation SQL and the repair are silent-failure mechanisms)
complex: yes — advisory lock, group renumbering, six-kind recomputation over five tables
```

## 1. Goal

The one definition of "correct" (the recomputations), the read-only check that reports every
divergence kind, the manual whole-workspace repair that uses the same recomputations, the
repair-record writer, the MC-15 flag writer, and the two ADMIN/MANAGER endpoints with their eight
role cells. This is the instrument every later phase ends its scenarios with. **Not in this
phase:** `move_assignment` and inline self-heal (phase 4), goal credit (phase 5), any other
endpoint.

## 2. Read first

1. `master_plan.md` §5, §6.1 (enums), §6.4, §6.5 (`_repair_records.py`, `_task_flag.py`, `_locks.py`,
   `repair_stock_report.py`, queries table incl. the divergence conventions), §6.6 (two routes),
   §6.8 (kit, listener, `assert_stock_report_clean`), §9 rules 1–4, 7.
2. Intention §12A in full (MC-20, repair, record fields, mechanics, instruments (a)–(e)), §4B MC-15,
   §4B MC-17 (the manual-repair stamp row and §14C C41), §9E MC-18 (the two new operations' cells),
   §9D MC-19 (repair events), §7A MC-7 (group and 1..n definitions only), §6A MC-5 recomputation
   sentence, §14D D1–D2, §14C C18, C39, C41.
3. Charter rule 15 (guards ship with proof they can fail) — every C1 row is such a probe.
4. Repo (relational): `bm/services/commands/cases/message_writes.py:60-75` (column-referencing
   Core UPDATE), `bm/models/tables/tasks/task.py:87-92` (`updated_at` `onupdate`),
   `bm/routers/api_v1/item_economics.py` (router shape with `require_roles`),
   `app/tests/unit/routers/api_v1/test_item_economics_router.py:60-115` (role-cell test shape),
   `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py:465-490`
   (statement listener), `bm/services/commands/tasks/create_task.py:99` (advisory-lock statement form).

## 3. Dependencies

Phase 1 APPROVED. Phase 2 is **not** required.

## 4. Files expected to change

New: `bm/services/queries/stock_report/__init__.py`, `consistency.py`, `get_stock_report_consistency.py`;
`bm/services/commands/stock_report/__init__.py`, `_repair_records.py`, `_task_flag.py`, `_locks.py`,
`repair_stock_report.py`, `requests/__init__.py` (empty module for now, or omitted until phase 8 —
implementer's choice, recorded); `bm/routers/api_v1/stock_report.py`;
`app/tests/helpers/statement_listener.py`;
`app/tests/integration/services/queries/stock_report/__init__.py`, `test_consistency_check.py`;
`app/tests/integration/services/commands/stock_report/__init__.py`, `test_repair_stock_report.py`;
`app/tests/unit/routers/api_v1/test_stock_report_router.py`.

Edited: `bm/routers/api_v1/__init__.py` (mount), `app/tests/helpers/stock_report.py`
(`assert_stock_report_clean`).

## 5. Tasks

1. `consistency.py`: `recompute_row_counters` (Σ `quantity` of non-deleted assignments by state, one
   grouped `SELECT` over the three members of `ACTIVE_ASSIGNMENT_STATES` — never a spelled list,
   master plan §9 rule 16; the three terminal states, `resolved_early` included, count nowhere),
   `recompute_goal_total` (Σ `quantity` over **all** assignments with
   `credited_history_record_id = R`, deleted included, **any state**), `expected_task_flag` (`EXISTS` non-deleted
   assignment), and `compute_stock_report_divergences` covering the eight kinds of MC-20 with the
   `field`/`stored`/`expected` conventions of master plan §6.5; output sorted by `(kind, client_id,
   field)`; workspace filter first on every statement; read-only.
2. `_repair_records.py`: `write_repair_record` + `logger.warning` per record with row, field,
   stored, recomputed, delta (when the caller supplies one), trigger. Values as text: ints in
   decimal, bools `"true"`/`"false"`, null as SQL NULL.
3. `_task_flag.py`: `set_task_stock_flag` as the exact MC-15 Core statement (`UPDATE tasks SET
   is_stock_assignment = :v, updated_at = tasks.updated_at WHERE client_id = :id AND
   is_stock_assignment IS DISTINCT FROM :v`); `recompute_task_stock_flag` = `expected_task_flag` then
   `set_task_stock_flag`.
4. `_locks.py` per master plan §6.5 (advisory key `stock_report_order:<ws>`; one `FOR UPDATE ORDER BY
   client_id` statement per class with `populate_existing`).
5. `repair_stock_report.py` per §12A mechanics: one `maybe_begin`; advisory lock; unlocked pre-pass of
   the `task_flag` check → lock those tasks ascending; lock every non-deleted row; lock assignments;
   run the check under the locks; repair per kind (counters, goal totals via Core UPDATE; task flag via
   `set_task_stock_flag`; nullness: null priority → order null, priority with null order → append at
   `max+1`; then density renumber `1..n` keeping relative order, ties by `client_id`); one repair
   record per `(target_client_id, field)` per run with the kind mapping of §12A; stamp
   `updated_at/updated_by_id` on every changed `stock_report_items` row; re-run the check; response
   `{"repaired": [...], "not_repaired": [signature kinds]}`; events `stock_report_item:updated` per row
   whose six event fields net-changed, dispatched after the block; **zero statements** on the five
   tables when nothing diverges.
6. `get_stock_report_consistency.py` (ctx → dict with `checked_at = ctx.now.isoformat()`).
7. Router file with the two routes; mount.
8. Test kit additions: `assert_stock_report_clean` (one helper, both assertions), `record_statements`,
   `count_writes`. Callers: every row below.
9. Tests first from the table, then arm.

## 6. Criteria

Fixtures start from **F0** (master plan §6.8) with rows and assignments inserted as ORM instances
and flushed; drift is planted by raw SQL **after** a clean setup. "one divergence" means the check
returns exactly one element for W. `MR` = `repair_stock_report(make_ctx(...))` as user U.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | A `in_queue` q=4; `UPDATE … SET quantity_in_queue = quantity_in_queue + 1` | one divergence `{kind: counter_in_queue, client_id: R, field: quantity_in_queue, stored: 5, expected: 4}` | remove the kind from `compute_stock_report_divergences` | MC-20, M1 |
| C1(b) | A `in_progress` q=4; `+1` on `quantity_in_progress` | one `counter_in_progress` divergence, stored 5 expected 4 | same, that kind | MC-20 |
| C1(c) | A `awaiting` q=4; `+1` on `quantity_awaiting` | one `counter_awaiting`, stored 5 expected 4 | same | MC-20 |
| C1(d) | T has no assignment; raw `UPDATE tasks SET is_stock_assignment = true` | one `task_flag` divergence `{client_id: T, field: is_stock_assignment, stored: "true", expected: "false"}` | remove the kind | MC-20, MC-15 |
| C1(e) | A exists on T; raw flag set `false` | one `task_flag`, stored `"false"` expected `"true"` | scan only tasks with the flag set → misses (e) | MC-20 ("every task that has either") |
| C1(f) | three `high` rows with orders 1, 2, 3; raw set the third to 5 | one `order_density` divergence `{client_id: row3, field: priority_order, stored: 5, expected: 3}`; rows 1 and 2 not reported | remove the kind | MC-20, M6 |
| C1(g) | row with `priority = high`, raw `priority_order = NULL`, group otherwise `[1, 2]` | one `priority_order_nullness` `{client_id: row, field: priority_order, stored: NULL, expected: 3}` | remove the kind | MC-20, M6 |
| C1(h) | row with `priority = NULL`, raw `priority_order = 1` | one `priority_order_nullness`, stored 1 expected NULL | same | MC-20 |
| C1(i) | A `awaiting` credited to G with q=4, G.quantity_awaiting 4; raw `+1` on G | one `goal_total` `{client_id: G, field: quantity_awaiting, stored: 5, expected: 4}` | remove the kind | MC-20, MC-5 |
| C1(j) | raw `UPDATE stock_report_items SET properties = '{"wood_group": ["Teak"]}'` (unnormalised, signature now stale) | one `signature` divergence `{client_id: R, field: properties_signature, stored: <old>, expected: compute_stock_criteria_signature(new props)}` | remove the kind | MC-20, MC-3 |
| C1(k) | clean F0 plus every C1(a)–(j) drift planted in the **foreign** workspace | check for W returns `[]` | drop the `workspace_id` filter from any kind → foreign rows leak in | MC-20, §9 rule 1 |
| C1(l) | A `resolved_early` q=4 (ORM-inserted, `credited_history_record_id = G`, `G.quantity_awaiting = 4`), counters `(0, 0, 0)`; no drift | check returns `[]` — no `counter_*` kind counts a terminal state, and `goal_total` Σ includes the `resolved_early` credit | count `state NOT IN (resolved, failed)` into a counter (a hand-typed terminal list) → a `counter_*` divergence appears; or exclude `resolved_early` from the goal Σ → `goal_total` stored 4 expected 0 | §14F F10–F11 (terminal, never counted; goal Σ includes it), MC-20, rule 16 |
| C2(a) | clean F0 | `[]`; every row of the four MC-9 tables and `stock_report_repair_records` in W, read before and after the call, is equal (same rows, same values) | write anything during the check (e.g. a repair record, a touched `updated_at`) | MC-20 read-only |
| C2(b) | drifts (a) and (i) planted together plus (f) | divergences sorted by `(kind, client_id, field)`: `counter_in_queue`, `goal_total`, `order_density` in that order | drop the sort | MC-20 output |
| C2(c) | `get_stock_report_consistency(ctx)` | `{"workspace_id": W, "checked_at": ctx.now ISO string, "divergences": [...]}` | — (envelope; calibration) | MC-20 |
| C3(a) | drift C1(a) → MR | check `[]`; exactly one repair record `{target_kind: stock_report_item, target_client_id: R, field: quantity_in_queue, stored_value: "5", recomputed_value: "4", trigger: "manual", created_by_id: U}`; response `repaired` has that divergence | skip the counter repair | §12A (a), M1 |
| C3(b) | drift C1(b) → MR | as (a) for `quantity_in_progress` | same | §12A (a) |
| C3(c) | drift C1(c) → MR | as (a) for `quantity_awaiting` | same | §12A (a) |
| C3(d) | drift C1(d) → MR | check `[]`; one record `{target_kind: task, target_client_id: T, field: is_stock_assignment, stored_value: "true", recomputed_value: "false", trigger: manual}` | write via ORM attribute (see C6(e)) | §12A (a), MC-15 |
| C3(e) | drift C1(e) → MR | one record stored `"false"` recomputed `"true"` | — | §12A (a) |
| C3(f) | drift C1(f) → MR | orders become 1, 2, 3; one record `{target_kind: group, target_client_id: row3, field: priority_order, stored_value: "5", recomputed_value: "3"}`; rows 1–2 get no record | renumber by `client_id` instead of current order → different row moves | §12A (a), M6 |
| C3(g) | drift C1(g) → MR | row appended at 3; one record `{target_kind: stock_report_item, field: priority_order, stored_value: NULL, recomputed_value: "3"}` | — | §12A (a) |
| C3(h) | drift C1(h) → MR | order set NULL; one record stored `"1"` recomputed NULL | — | §12A (a) |
| C3(i) | drift C1(i) → MR | G back to 4; one record `{target_kind: history_record, target_client_id: G, field: quantity_awaiting, stored_value: "5", recomputed_value: "4"}` | — | §12A (a), MC-5 |
| C4(a) | drift C1(j) → MR | `not_repaired == [that divergence]`, `repaired == []`; no record; `properties_signature` unchanged; check still reports it | "repair" it by re-signing → red | §12A (b), MC-4 |
| C5(a) | clean F0 → MR | `{"repaired": [], "not_repaired": []}`; `count_writes(..., five tables) == 0`; zero repair records; zero events dispatched | write a record for an equal value | §12A (d) |
| C6(a) | row with `priority = high`, order NULL (nullness) **and** the group `[1, 3]` (density gap) → MR | that row ends at order 3; **one** record for it: `target_kind: stock_report_item`, stored NULL, recomputed `"3"`; the row that moved 3 → 2 gets `target_kind: group` | write two records for the same `(row, field)` | §12A "one record per (target, field)" |
| C6(b) | task-flag drift C1(d) → MR | `tasks.updated_at` and `updated_by_id` byte-identical before and after | write the flag as an ORM attribute (`_task_flag.py`) → `onupdate` fires | MC-15 (U3) |
| C6(c) | counter drift C1(a) → MR | R's `updated_at == ctx.now`, `updated_by_id == U`; an unchanged row in W keeps its prior `updated_*` | stamp every row | §12A stamps, MC-17 (C41) |
| C6(d) | density drift C1(f) → MR | the renumbered row (3 → 2) is stamped; unchanged rows are not | — | §12A stamps |
| C6(e) | drifts C1(a) + C1(i) + C1(d) → MR, `capture_dispatch` on `repair_stock_report`'s import site | exactly one `stock_report_item:updated` (for R, payload = the six fields after repair); nothing for G or T | emit for goal/task repairs | §12A events, MC-19 |
| C6(f) | `null` text rule | C3(g)'s record has `stored_value IS NULL` (SQL NULL), not `"None"`/`"null"` | `str(None)` | §12A values-as-text |
| C7(a) | consistent W with one `manual` repair record present | `assert_stock_report_clean(session, W)` raises `AssertionError` | split the helper into two functions → the record half can be skipped | §12A (e) |
| C7(b) | consistent W, zero records | helper passes | — | §12A (e) |
| C8(a)–C8(d) | `GET /api/v1/stock-report/consistency` as admin / manager / worker / seller | 200 (service reached) / 200 / 403 `Insufficient role permissions.` with the service not called / 403 | wrong role list in `require_roles` | MC-18, M9 |
| C8(e)–C8(h) | `POST /api/v1/stock-report/repair` as admin / manager / worker / seller | reached / reached / 403 / 403 | same | MC-18, M9 |

## 7. Notes

- Sizing: 42 criterion rows in 8 criteria; `complex: yes` — advisory lock,
  renumbering, recomputation SQL over five tables. (Counts re-derived by script after the round-9
  fold; see the delta handoff.)
- Round 9 (2026-09-19): C1(l) added — the check must neither count `resolved_early` in a counter
  nor drop its goal credit (§14F F10–F11). Task 1 names the frozensets the recomputations read.
- C8 rows use the `TestClient` + `dependency_overrides[get_jwt_claims]` + faked `run_service` shape
  (precedent cited in §2); MVP calibration: no mutation ledger rows for C8 and C2(c).
- The repair's task-lock pre-pass and the "repair statement returning ≠ 1 row is a programming
  error" rule are **not** criterion rows (unobservable without a defect racing the repair); the
  reviewer verifies both structurally and records it in the Review log.
- Every C3 row ends with `assert_stock_report_clean` **except** that a `manual` record is expected
  there — so C3 rows assert the check `[]` and the exact record set directly, not through the helper.
  From phase 4 on, scenarios that plant no drift use the helper.
- Hazard: the density renumber and the nullness append interact (C6(a)); do the nullness step first
  (§12A) and write records from a before/after diff per `(row, field)`, not per step.

## 8. Review log

(empty)

### Implementer note — Batch A session (2026-09-20)

Consistency, manual repair, repair records, task-flag writing, locks/recomputation, and both
endpoints are implemented and covered by the green focused perimeter (`139 passed`; scoped Ruff and
`git diff --check` clean). Raw-SQL identity-map drift and full signature `not_repaired` records are
explicitly tested. The complete named-mutation ledger and pre-edit full-suite baseline are captured
in the Batch-A handoff; this phase remains pending reviewer-owned graph/checkpoint gates.
