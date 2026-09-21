# Plan 6 — Demand service, set-based (D6): find-or-create, goal records, replay, deadline, statement bound

```
state: NOT_STARTED
phase: 6 of 15
depends_on: 3 (APPROVED)   — does NOT need 4 or 5
projection: mandatory, NOT waivable (rule 17: SQLAlchemy/asyncpg timeout shapes, ON CONFLICT semantics)
complex: yes — set-based statements, two-session rows, the 5 s budget
```

## 1. Goal

`apply_stock_demand`: the D6 statement plan inside one owner-mode transaction — `set_config`,
workspace check, one category `SELECT`, unlocked identity discovery, one `INSERT … ON CONFLICT DO
NOTHING` of the absent identities only, one sorted `FOR UPDATE`, one bulk `UPDATE` of changed rows,
one bulk goal-record `INSERT`, the deadline check — with the MC-6 goal rules, MC-9's zero-statement
replay, MC-4's concurrency invariant, the rule-10 time-limit instruments and MC-19's demand events.
**Not in this phase:** the HTTP route, key auth, body decoding and shape validation, duplicate
detection (phase 7 — this phase receives already-parsed `DemandEntry` objects).

## 2. Read first

1. `master_plan.md` §6.1, §6.3, §6.4 (`LocationTrackerWebhookAuthError`, `StockDemandDeadlineExceeded`),
   §6.5 (`stock_demand_entries.py`, `apply_stock_demand.py`), §6.7, §9 rules 1, 5–7, 9, 10.
2. Intention §8, §8.1, §8B MC-8 (steps 4, 8, 9; category resolution), MC-9 in full (replay
   definition, instrument, arrival order, the residual case: deadline + `set_config`, one owning
   transaction, exception class, instrument rows (i)–(iii)), the **D6 statement plan** (steps 1–9 and
   the three "holds" bullets), §4A MC-4 (find-or-create, the concurrency invariant), §6A MC-6
   (comparison base, examples, timing, authorship), §9D MC-19 (demand rows), MC-17 (demand rows),
   §14D D4–D6, §14C C14, C42, C43.
3. Re-check handoff §1 (MC-9 rows) and **§2** (the measured shapes: `set_config(…, true)` form,
   `DBAPIError` with `.orig.sqlstate` `57014`/`55P03`, no leak, per-statement semantics).
4. Repo: `bm/services/commands/utils/transaction.py` (`maybe_begin` owner/subordinate — the
   autobegin trap), `bm/models/database.py:58-70` (`get_db_session` for the second session),
   `app/tests/integration/services/commands/item_economics/test_phase7_concurrency.py` (two-session
   shape), `bm/services/queries/items/lookup/purchase_api.py:123-136` (the `.limit(1)` precedent that
   is **not** copied).

## 3. Dependencies

Phase 3 APPROVED (clean helper, listener, tables, normalization from phase 1).

## 4. Files expected to change

New: `bm/services/commands/stock_report/stock_demand_entries.py`, `_demand_lookup.py` (steps 3–4
below, factored so the Scanner delete webhook of phase 13A reuses the same category resolution and
identity discovery — intention §14E E4 "the same engine as find-or-create"), `apply_stock_demand.py`;
`bm/errors/stock_report.py` (both webhook error classes; phase 7 adds nothing new here);
`app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py`,
`test_apply_stock_demand_timing.py` (holds the one sleeping test).

## 5. Tasks

1. `stock_demand_entries.py`: `DemandEntry` (frozen dataclass, fields in master plan §6.5;
   `item_category_key = item_category_raw.strip().lower()`), `DemandOutcome(index, item_category_raw,
   properties_raw, outcome)`, `StockDemandResult(outcomes, events)`.
2. `apply_stock_demand(session, *, workspace_id, entries, now, deadline, timeout_ms)`:
   `async with maybe_begin(session)` — the session must have **no** open transaction on entry (assert
   `not session.in_transaction()` and raise `RuntimeError` otherwise: the autobegin trap of MC-9).
   Inside, in this order and with nothing before it:
   1. `SELECT set_config('statement_timeout', :ms, true), set_config('lock_timeout', :ms, true)`
      with `:ms = str(timeout_ms)`.
   2. `SELECT 1 FROM workspaces WHERE client_id = :ws` → none → `LocationTrackerWebhookAuthError`.
   3. One `SELECT` of non-deleted categories of the workspace whose `lower(name)` is in the set of
      `item_category_key`; resolve in memory: exact `strip(name)` match first, else a unique
      case-insensitive match, else `category_not_found` (ambiguity logged). Lives in
      `_demand_lookup.py` as `resolve_categories_for_entries(session, *, workspace_id, entries) ->
      dict[str, str | None]` (category key → category `client_id`, or `None`), master plan §6.5.
   4. One unlocked `SELECT client_id, item_category_id, properties_signature FROM stock_report_items
      WHERE workspace_id = :ws AND is_deleted = false AND (item_category_id, properties_signature) IN
      (…)` over the resolved entries. Lives in `_demand_lookup.py` as
      `discover_live_rows_by_identity(session, *, workspace_id, identities) -> dict[tuple[str, str], str]`
      (identity → row `client_id`). Both functions take a list of any entry type exposing
      `item_category_key` and `properties_signature` (`DemandEntry` here; `DemandDeleteEntry` in 13A).
   5. If any identity is absent: one multi-row `INSERT … ON CONFLICT (workspace_id, item_category_id,
      properties_signature) WHERE is_deleted = false DO NOTHING RETURNING client_id, item_category_id,
      properties_signature` with VALUES sorted by `(item_category_id, properties_signature)`,
      `quantity_requested 0`, `properties` = the normalized dict, `properties_signature`, `created_by
      NULL`. Returned = created by this request. Omitted when none absent.
   6. One `SELECT … FOR UPDATE ORDER BY client_id` over every identity (existing + new), with
      `populate_existing` and the predicate `is_deleted = false`; its values are the comparison base
      (0 for rows returned by step 5). **Then assert that every identity of the request was locked.**
      A row discovered at step 4 can be soft-deleted by a concurrent transaction (a user's row delete,
      phase 13; the Scanner delete webhook, phase 13A) before this statement takes its lock; under
      READ COMMITTED a `FOR UPDATE` that waited re-evaluates its `WHERE` on the committed version and
      **drops** a row that no longer satisfies `is_deleted = false` (PostgreSQL manual §13.2.1, "Read
      Committed Isolation Level"; installed server 18.6). If the locked set is smaller than the
      identity set, raise `RuntimeError("stock demand identity vanished under lock")` — the block
      rolls back, `run_service` answers **500**, Scanner retries (v2 §3.4: 5xx → retry), and the
      retry creates the fresh row (intention §14E E10). No silent skip and no `applied` for a row
      that was not written.
   7. If any `new ≠ base`: one `UPDATE stock_report_items AS r SET quantity_requested = v.q FROM
      (VALUES …) AS v(id, q) WHERE r.client_id = v.id RETURNING <six event fields>`. Omitted when none.
   8. If any `new > base`: one multi-row `INSERT INTO stock_report_history_records` (type
      `quantity_requested_change`, `quantity_requested = new`, `quantity_awaiting 0`, `priority`,
      `priority_order` from step 6's values, `created_at = now`, `created_by NULL`). Omitted when none.
   9. `if time.monotonic() >= deadline: raise StockDemandDeadlineExceeded()` — the last statement
      inside the block. `time.monotonic` is looked up through the module attribute `time` so a test
      can patch `apply_stock_demand.time.monotonic`.
   After the block: build events — `stock_report_item:created` for step-5 rows (no `:updated` for
   them), `:updated` for step-7 rows from `RETURNING`, nothing for unchanged or skipped — and return
   `StockDemandResult`. The function does not catch `DBAPIError`.
3. Tests first from the table. The two-session rows use `get_db_session()` for the second session.

## 6. Criteria

Fixture: **F0**'s workspace W with categories K ("Dining Chairs") and K2 ("Coffee Tables"); entries are
built with `DemandEntry` from raw dicts via `normalize_stock_criteria`/`compute_stock_criteria_signature`.
**Every row in this plan is a committing test:** `apply_stock_demand` opens its own owner-mode
transaction and refuses a session that is already in one, while the phase-1 kit autobegins on its
first `flush()`. So each row runs `seed → await db_session.commit() → AD(...) → assertions →
finally: await purge_stock_report_workspace(db_session, W); await db_session.commit()` (§9 rule 1,
charter rule 11½). `AD(entries)` = `apply_stock_demand(session, workspace_id=W, entries, now=t0,
deadline=+60 s, timeout_ms=<default>)`. "no write" = `count_writes` over the four MC-9 tables
`== 0`; the `record_statements` window opens **after** the seed commit and closes **before** the
purge, because the listener attaches to the engine and would otherwise record both. Every
non-timing row ends with `assert_stock_report_clean`.

> **Fold note (orchestrator, 2026-09-21, batch B projection F6-1 — lesson L-17).** The commit/purge
> sentences are a fixture-cell amendment; no outcome cell changed. Without them **every** row in
> this plan raises `RuntimeError` before its first assertion: `apply_stock_demand` asserts
> `not session.in_transaction()` and the kit's first `flush()` autobegins.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | one new entry (K, `{"wood_group": ["teak"]}`, 5) | one live row: `quantity_requested 5`, `properties == {"wood_group": ["teak"]}`, signature = `compute_stock_criteria_signature`, `created_by NULL`, counters 0, priority/order NULL; outcome `applied`; events `[stock_report_item:created]` only | emit `:updated` too | MC-4, MC-6, MC-19 |
| C1(b) | row exists at 5; entry with 7 | same row, `quantity_requested 7`; events `[:updated {quantity_requested: 7, …}]`; no new row | enumerated, `apply_stock_demand.py` (definition site): (i) **drop the `ON CONFLICT … DO NOTHING` from step 5 and treat every entry as absent** (skip step 4's discovery result) → the INSERT violates `uix_stock_report_items_identity_active` → `IntegrityError` → red; (ii) **build a `stock_report_item:created` event for every identity in the request instead of only for step 5's `RETURNING` rows** → a spurious `:created` appears and the event assertion reddens. ("insert a second row" is **not implementable**: step 5's `ON CONFLICT` silently drops the conflicting VALUES row — measured on PostgreSQL 18.6 — so a mutant treating the identity as absent still inserts nothing.) | MC-4, HC-1 |
| C1(c) | row at 5; entry with 5 | no write; no event; outcome `applied` | issue the `UPDATE` anyway | MC-9 equality short-circuit |
| C1(d) | row at 5 **soft-deleted by direct column write** (`is_deleted = true`, `deleted_at` set; the row and its goal record stay in the table — the partial identity index excludes it, which is what lets the new row be inserted); entry with 3 | a **new** live row at 3 with no history except its own goal record; the deleted row untouched | match deleted rows | MC-4, MC-16 |
| C1(e) | two entries: one new, one existing changed | both `applied`; one `:created` + one `:updated` | — | D6 |
| C1(f) | `workspace_id` names no `workspaces` row | raises `LocationTrackerWebhookAuthError` (`http_status 401`); nothing written | delete the step-2 workspace `SELECT` and its raise, `apply_stock_demand.py` (definition site) → the call returns normally with every entry `category_not_found` (step 3 finds no categories, so no row is inserted and the FK is never exercised) → `pytest.raises(LocationTrackerWebhookAuthError)` reddens. *Corrected at the fold: the previous cell predicted an FK failure and a 500, which cannot occur on this path.* | MC-8 step 4 |
| C2(a) | entry `itemCategory = "Dining Chairs"` | resolves to K | — | MC-8 category resolution |
| C2(b) | `"dining chairs"`, only K exists | resolves to K | drop the case-insensitive fallback → `category_not_found` | MC-8 (U6) |
| C2(c) | W also has a category `"dining chairs"` (case variant of K); entry `"DINING CHAIRS"` | outcome `category_not_found`; nothing written for it | pick the first (`.limit(1)`) | MC-8 (U6, C14) |
| C2(d) | same two categories; entry `"Dining Chairs"` | resolves to K (exact wins) | case-insensitive first → ambiguous | MC-8 |
| C2(e) | entries `[unknown "Serving Trolleys", K new]` | outcomes `[category_not_found, applied]`; one row created; the skipped entry writes nothing | reject the request | §8.1 (P11 struck), M3 |
| C2(f) | `"  Sofas "` with category `Sofas` | resolves | drop the `.strip()` from `item_category_key = item_category_raw.strip().lower()` in `stock_demand_entries.py` (`DemandEntry` construction, definition site) → the key is `"  sofas "`, `lower(name) IN (…)` matches nothing → outcome `category_not_found` → red | MC-8 |
| C2(g) | K soft-deleted; entry K | `category_not_found` | drop `is_deleted` filter | MC-16 |
| C3(a) | new entry with 5 | one goal record `{type: quantity_requested_change, quantity_requested: 5, quantity_awaiting: 0, priority: NULL, priority_order: NULL, created_by_id: NULL, created_at: t0}` | enumerated, `apply_stock_demand.py` step 8 (definition site): (i) **snapshot `quantity_requested` from the row's pre-update stored value instead of the new value** → the record reads 0 instead of 5 → red; (ii) **let `created_at` fall to the column default instead of the operation's `now`** → `created_at != t0` → red. ("snapshot `quantity_awaiting` from the row" is an **equivalent mutant on this row** — a new row's counter is already 0, which is the value the outcome asserts — and is carried by C3(g).) | MC-6 |
| C3(b) | then 5 again | no record; no write | — | MC-6 (`5→5`) |
| C3(c) | then 3 | no record; row at 3 | write on any change | MC-6 (`5→3`) |
| C3(d) | then 4 | a record (4 > stored 3) | compare against the historical max (5) → none | MC-6 (`3→4`, literal reading) |
| C3(e) | then 0 | no record; row at 0 | — | MC-6 |
| C3(f) | new entry with 0 | row created at 0; **no** record | write a `0` goal | MC-6 (`0→0` new row) |
| C3(g) | the row exists with `priority = high`, `priority_order = 2` (set by raw SQL) **and a live `awaiting` assignment of `q = 3` on the kit's (I, T)**, so the row's `quantity_awaiting` is legitimately **3** and the workspace is still clean (seed `tasks.is_stock_assignment = true` for T, per MC-20's task-flag rule); entry raises the quantity. Without the non-zero live counter the "copy the counter" mutation writes the same `0` the outcome asserts and cannot fail | the goal record snapshots `priority high`, `priority_order 2` and the row's live `quantity_awaiting` is **not** used — record's `quantity_awaiting` is 0 | copy the counter (`quantity_awaiting` snapshotted from the row instead of 0), `apply_stock_demand.py` step 8 (definition site) → with the live `awaiting` assignment this row now seeds, the record reads 3 instead of 0 → red | MC-6 snapshot rules |
| C4(a) | batch of 3 (one new, one changed, one unchanged) delivered twice | second `AD`: `count_writes` over the four tables `== 0`; zero events; outcomes all `applied` | remove the `new ≠ base` filter (step 7) → 1 UPDATE | MC-9, HC-5, M3 |
| C4(b) | replay of an all-new batch | second delivery issues **no** INSERT on `stock_report_items` (step 5 omitted) | always issue the INSERT (MC-4's old wording) → counted | MC-9 (C42) |
| C5(a) | two sessions, each `AD([same new identity, 5])`, released by an `asyncio.Barrier` after both are built; the second session is opened as `async for s in get_db_session(): …` (it is an async generator, not a context manager) and is closed and purged in a `finally` (§9 rule 9) | exactly one live row; both results `applied`; exactly one `stock_report_item:created` across the two results; `quantity_requested 5` | replace `ON CONFLICT DO NOTHING` with a plain INSERT → one raises IntegrityError | MC-4 invariant, M4 |
| C5(b) | two sessions, batches of two new identities in opposite order, barrier-released; the second session is opened as `async for s in get_db_session(): …` (an async generator, not a context manager), closed and purged in a `finally` (§9 rule 9) | both complete (no `DBAPIError` deadlock); two live rows | unsorted VALUES + per-identity INSERTs — **interleaving not forced**: reviewer checks the `ORDER BY`/sorted VALUES structurally | MC-4 "sorting the VALUES" |
| C5(c) | row R live at 5. Session H (`get_db_session()`): `SELECT … FOR UPDATE` on R, then `UPDATE stock_report_items SET is_deleted = true, deleted_at = now() WHERE client_id = R`, **held uncommitted**; main session starts `AD([R's identity, 7])` as a task — the `record_statements` window opens **after** H's UPDATE has been issued, because the listener attaches to the engine and would otherwise count H's statements against this row's `count_writes == 0` | the task has **not** returned after 0.5 s (step 6 is waiting on H); H commits; the task raises `RuntimeError`; `count_writes` over the four tables during `AD` `== 0`; no live row with R's identity exists; a second `AD([R's identity, 7])` then creates a **fresh** live row (new `client_id`, `quantity_requested 7`, one goal record) — deterministic (held lock + bounded wait, master plan §9 rule 9) | drop the locked-set assertion → the first `AD` returns `applied` (or raises `KeyError`) with nothing written → the `RuntimeError` assertion reddens | task 2 step 6 rule; §14E carried question (1) (concurrent demand vs a row deletion), §14E E10, MC-4, M3 |
| C6(a) | shape *all new*: 3 entries vs 300 entries (distinct properties, one category) | total statements recorded during `AD` equal for both sizes and `≤ 8` | resolve categories or discover rows per entry → counts differ | D6, §14D D6 |
| C6(b) | shape *all changed* (rows pre-exist at other values) | equal, `≤ 8` | per-row `UPDATE` | D6 |
| C6(c) | shape *all unchanged* | equal, `≤ 8` (expected 5: steps 1, 2, 3, 4, 6) | per-entry equality `SELECT` | D6, MC-9 |
| C6(d) | shape *entry 0 unknown category, rest new* | equal, `≤ 8` | — | D6 |
| C7(a) | setting unset (default); a **parameter-capturing** listener around `AD` — add `record_statement_calls(session)` to `app/tests/helpers/statement_listener.py`, an `asynccontextmanager` yielding `list[tuple[str, Any]]` of `(statement, parameters)` from the same `before_cursor_execute` hook, leaving `record_statements` and `count_writes` untouched so batch A's one caller stays green | the **first** recorded statement is the `set_config` call and its two parameters both equal `str(Settings.model_fields["stock_demand_webhook_timeout_ms"].default)` | any statement before it → red. **Assert on the bound parameters, never on the statement text, the result, or `SHOW`**: SQLAlchemy compiles the bind to `$1`/`$2` and `set_config` *returns* `'5s'`, not `'5000'` | MC-9 (i), charter rule 10/13 |
| C7(b) | **the one sleeping test.** Second session holds `SELECT … FOR UPDATE` on an existing row R for `default + 3000 ms`; `AD([R's identity, new value])` in the main session | raises `sqlalchemy.exc.DBAPIError` with `.orig.sqlstate == "57014"`; elapsed `≥ default − 250 ms` and the holder has not yet released; afterwards R's row and history are byte-identical to before; no event | remove the `set_config` statement → the call waits until the holder releases and then **succeeds** (deadline 60 s) → status/timing assertion red | MC-9 (ii) |
| C7(c) | `monkeypatch.setattr(apply_stock_demand, "time", SimpleNamespace(monotonic=lambda: deadline + 1))` — replace the **module reference in `apply_stock_demand`'s namespace**, never the attribute on the shared `time` module, which would also freeze the asyncio event-loop clock (patched only for the check — see note) | raises `StockDemandDeadlineExceeded` (`http_status 503`); nothing written; no event | delete the check → commits → red | MC-9 (iii), §14D D5 |
| C8(a) | new row | events `[:created]` and **no** `:updated` for it | — (C1(a) mutation) | MC-19 (C35) |
| C8(b) | changed row | `:updated` payload equals the six `RETURNING` values | payload from the ORM instance loaded at step 6 (stale after step 7) | MC-19 |
| C8(c) | unchanged + skipped entries | no events | — | MC-19 |
| C8(d) | any event | `event.workspace_id == W` (the argument), never `""` | read `ctx.workspace_id` (there is no ctx here — the planted defect is hard-coding `""`) | MC-8 guard, §2.5 |

## 7. Notes

- Sizing: 36 criterion rows in 8 criteria; `complex: yes`. (Counts re-derived by script after the
  round-8/9 fold; see the delta handoff.)
- Round 8 (2026-09-19): `_demand_lookup.py` factored out of task 2 (steps 3–4) so phase 13A's delete
  webhook finds rows with the identical statements (§14E E4); step 6 gained the locked-set
  assertion and C5(c) its row — the discover-then-lock gap against a concurrent soft-delete was
  unplanned in the round-7 set and applies to the user delete of phase 13 as much as to 13A. The
  shape in C5(c)'s fixture (a `FOR UPDATE` that waited drops a row whose committed version fails
  the `WHERE`) is Postgres-owned (rule 17): the public contract (manual §13.2.1) settles it;
  projection confirms on 18.6 and records the version.
- C7(b) is the project's **only** test that sleeps past the default (master plan §9 rule 10); budget
  ~8 s wall time; it lives in its own file so it can be excluded from L1 loops by file, never by `-k`.
- C7(c): the deadline is taken by the caller (phase 7's command, at handler entry). Here the test
  passes `deadline` explicitly and patches `monotonic` so the check sees it exceeded while the
  statements ran normally.
- Rule 17 fixture cells: C7(b)'s exception shape is the re-check handoff §2 measurement
  (`DBAPIError`, adapter `Error`, sqlstate `57014`); the `set_config(…, true)` form is measured there
  too. Projection re-checks both against the installed 2.0.40/0.30.0.
- C5(b) is declared unable to force its interleaving; the structural check is the reviewer's.
- Statement counting in C6 counts **every** statement, `SELECT` included, and only the statements
  issued between the call's entry and return.

## 8. Review log

**2026-09-21, batch B2 implement 1 (Sonnet).** Implemented `stock_demand_entries.py`,
`_demand_lookup.py`, `apply_stock_demand.py`, `bm/errors/stock_report.py` (new file,
`LocationTrackerWebhookAuthError` + `StockDemandDeadlineExceeded` only — the two
structured assignment errors belong to phase 8). Tests:
`test_apply_stock_demand.py` (28 rows/tests) and `test_apply_stock_demand_timing.py`
(3 rows/tests, C7 — the sleeping test lives here per H25). All 31 green.

**Perimeter additions (blockers B3/B4), final signatures:**
- `app/tests/helpers/statement_listener.py`: added
  `record_statement_calls(session)`, an `asynccontextmanager` yielding
  `list[tuple[str, Any]]` of `(statement, parameters)` from the same
  `before_cursor_execute` hook as `record_statements`. `record_statements` and
  `count_writes` are byte-identical to before.
- `bm/domain/stock_report/enums.py`: added `StockDemandOutcomeEnum` only
  (`APPLIED = "applied"`, `CATEGORY_NOT_FOUND = "category_not_found"`). The other
  five names master plan §6.1 claims (round-8/9 items) are still missing and belong
  to phases 9/13A — not added here (charter rule 4).

**O1 decision (outcome cell, plan 6 C7(a)):** implemented as the fold prescribes —
two distinct bind names, `:statement_timeout_ms` and `:lock_timeout_ms`, both bound
to `str(timeout_ms)`. The compiled statement carries `$1`/`$2`; C7(a) asserts
`tuple(first_params) == (expected, expected)`.

**Measured dependency versions** (re-confirmed against the installed stack, not
re-derived): PostgreSQL 18.6, SQLAlchemy 2.0.40, asyncpg 0.30.0, Starlette 0.46.2,
FastAPI 0.115.12, CPython 3.13.2.

**Judgment calls:**
1. Step 6's lock (task 2 step 6) locks by **identity**
   (`tuple_(item_category_id, properties_signature).in_(...)`), never by the
   client_ids steps 4/5 happened to see (H17) — a concurrent insert can win an
   identity between step 4's discovery and this lock, and step 5's own
   `ON CONFLICT DO NOTHING` then returns nothing for it, so the locally generated
   client_id is not the row's id. This is not spelled out as a separate task step,
   but H17 requires it and C5(a)'s two-session invariant depends on it.
- `apply_stock_demand.py`'s step-7 UPDATE is one `UPDATE ... FROM (VALUES (CAST(:id_i
  AS varchar), CAST(:q_i AS integer)), ...) AS v(id, q)` statement. **Measured**:
  SQLAlchemy's `text()` bind-parameter scanner does not recognize `:name::type`
  (Postgres's own cast syntax) as a parameter followed by a cast — it treats the
  whole `:name::type` token as unparseable and leaves it as literal text, which
  asyncpg then rejects with a syntax error. `CAST(:name AS type)` avoids the
  adjacency and compiles correctly. Recorded here since master plan §9 rule 14 asks
  Postgres/SQLAlchemy shapes to be cited, not invented, and this one is not in the
  re-check handoff.
- The step-7 UPDATE's `RETURNING` columns are bound to their real column types via
  `text(...).columns(...)`, reusing `StockReportItem.__table__.c.priority.type` for
  `priority` — this is what makes the raw-SQL `RETURNING` produce a real
  `StockReportPriorityEnum` member (not a string) for
  `_events.py:build_stock_report_item_updated_event`, which the existing (batch B1)
  code assumes.
- `resolve_categories_for_entries` resolves per **entry**, using the first entry
  seen for a given `item_category_key` as the "raw" string compared for the exact
  match. Two entries sharing one key but differing only in casing (already
  duplicate-rejected as a single-identity in phase 7 when their properties also
  match) is not exercised by any plan-6 row; documented as a smallest-reasonable
  reading of the master plan's `dict[str, str | None]` signature, not a new
  contract.
- C3(g)'s fixture: the plan names the row's own `priority_order = 2` while asserting
  the workspace stays clean. A single row at `priority_order = 2` is not dense
  (`order_density` expects `1`), so the test adds a companion row at
  `priority_order = 1` in the same "high" group — the smallest addition that makes
  the plan's literal numbers a consistent fixture rather than a self-contradicting
  one.

**Mutation ledger — derivation (plan cell → table row).** 30 named-mutation cells
counted from §6 (excludes `—` cells, the C8(a) reuse of C1(a)'s mutation, the
C3(a)-iii equivalent mutant carried by C3(g), and C5(b)'s declared-unrunnable
interleaving). `executed == declared == 30`. Two cells (C1(c), C4(a)) name the
identical code change (the equality guard before `to_update`/`to_credit`) and are
recorded as one physical mutation run against both tests. Two mutations were
**re-sited** after an initial false green (see notes): C2(d) and C3(f) needed a
different code change than first tried; C6(a) needed to loop per **entry**, not per
distinct key, since the fixture's 3-vs-300 batches share one category.

| Row | Site | Command (file run) | Result |
|---|---|---|---|
| C1(a) | `apply_stock_demand.py`, event-filter (def.) | `test_apply_stock_demand.py::test_c1a_...` | red: event count 2, spurious `:updated` |
| C1(b)(i) | `apply_stock_demand.py`, step 5 absent-set + ON CONFLICT (def.) | `test_apply_stock_demand.py::test_c1b_...` | red: `IntegrityError` on the INSERT |
| C1(b)(ii) | `apply_stock_demand.py`, `created_client_ids` after lock (def.) | `test_apply_stock_demand.py::test_c1b_...` | red: spurious `:created`, event-shape assertion fails |
| C1(c) / C4(a) | `apply_stock_demand.py`, step-7 equality guard (def.) | `test_apply_stock_demand.py::test_c1c_...`, `test_c4a_...` (also incidentally `test_c6c_...`) | red on all three: `count_writes != 0` |
| C1(d) | `_demand_lookup.py::discover_live_rows_by_identity`, `is_deleted` filter (def.) | `test_apply_stock_demand.py::test_c1d_...` | red: matched the soft-deleted row, no new row created |
| C1(f) | `apply_stock_demand.py`, step-2 workspace check (def.) | `test_apply_stock_demand.py::test_c1f_...` | red: no exception raised |
| C2(b) | `_demand_lookup.py::resolve_categories_for_entries`, case-insensitive fallback (def.) | `test_apply_stock_demand.py::test_c2b_...` | red: `category_not_found` instead of resolved |
| C2(c) | same, ambiguous case-insensitive branch (def.) | `test_apply_stock_demand.py::test_c2c_...` | red: resolved (picked one) instead of `category_not_found` |
| C2(d) | same, check order (def.) — re-sited: reordering alone was inert (case-insensitive returns the same ambiguous 2 either way and still falls through); the real mutation stops at the ambiguous case-insensitive result | `test_apply_stock_demand.py::test_c2d_...` | red (2nd attempt): resolved to `None` instead of K |
| C2(e) | `apply_stock_demand.py`, category-not-found branch (def.) | `test_apply_stock_demand.py::test_c2e_...` | red: `RuntimeError` propagates, whole request fails |
| C2(f) | `stock_demand_entries.py::DemandEntry.__post_init__` (def.) | `test_apply_stock_demand.py::test_c2f_...` | red: `category_not_found` instead of resolved |
| C2(g) | `_demand_lookup.py::resolve_categories_for_entries`, `is_deleted` filter (def.) | `test_apply_stock_demand.py::test_c2g_...` | red: resolved the soft-deleted category |
| C3(a)(i) | `apply_stock_demand.py`, history `quantity_requested` value (def.) | `test_apply_stock_demand.py::test_c3_sequence_...` | red: record shows 0 (stale) instead of 5 |
| C3(a)(ii) | same, history `created_at` (def.) | `test_apply_stock_demand.py::test_c3_sequence_...` | red: `created_at != NOW` |
| C3(c) | `apply_stock_demand.py`, credit guard (def.) | `test_apply_stock_demand.py::test_c3_sequence_...` | red: a record appears on `5→3` |
| C3(d) | same, comparison base (def.) — extra query against `StockReportHistoryRecord` max | `test_apply_stock_demand.py::test_c3_sequence_...` | red: no record on `3→4` |
| C3(f) | `apply_stock_demand.py`, step 5 (def.) — re-sited: the `>`/`>=` swap at the credit guard is inert for this row (a new row at 0 never enters `to_update`, since `0 != 0` is false regardless); the real mutation unconditionally credits every created row | `test_apply_stock_demand.py::test_c3f_...` | red (2nd attempt): a goal record appears for the 0-quantity new row |
| C3(g) | `apply_stock_demand.py`, history `quantity_awaiting` value (def.) | `test_apply_stock_demand.py::test_c3g_...` | red: record shows 3 (the live counter) instead of 0 |
| C4(b) | `apply_stock_demand.py`, step 5 omission guard (def.) | `test_apply_stock_demand.py::test_c4b_...` | red: `count_writes({"stock_report_items"}) != 0` on replay |
| C5(a) | `apply_stock_demand.py`, step 5 ON CONFLICT (def.) | `test_apply_stock_demand.py::test_c5a_...` | red: `IntegrityError` under the concurrent race |
| C5(b) | — | not run (plan: interleaving cannot be forced; reviewer performs the structural check on the sorted VALUES / `ORDER BY`) | declined by design |
| C5(c) | `apply_stock_demand.py`, locked-set assertion (def.) | `test_apply_stock_demand.py::test_c5c_...` | red: no `RuntimeError`, `pytest.raises` fails |
| C6(a) | `_demand_lookup.py::resolve_categories_for_entries` (def.) — re-sited: looping per distinct **key** was a false green (both batch sizes share one category key); looping per **entry** reddens | `test_apply_stock_demand.py::test_c6a_...` | red (2nd attempt): statement counts diverge (also reddened C6b/c/d as a bonus, each re-run at its own site below) |
| C6(b) | `apply_stock_demand.py`, step 7 (def.) | `test_apply_stock_demand.py::test_c6b_...` | red: per-row UPDATE count scales with batch size |
| C6(c) | `apply_stock_demand.py`, step 7 loop (def.) | `test_apply_stock_demand.py::test_c6c_...` | red: statement count is 305 instead of 5 for the 300-entry batch |
| C6(d) | — | not run (cell is `—`) | declared not run |
| C7(a) | `apply_stock_demand.py`, top of the owner-mode block (def.) | `test_apply_stock_demand_timing.py::test_c7a_...` | red: first statement is `SELECT 1`, not `set_config` |
| C7(b) | `apply_stock_demand.py`, step 1 (def.) | `test_apply_stock_demand_timing.py::test_c7b_...` | red (~8.6s): call succeeds after the holder releases instead of raising `DBAPIError` |
| C7(c) | `apply_stock_demand.py`, step 9 (def.) | `test_apply_stock_demand_timing.py::test_c7c_...` | red: no `StockDemandDeadlineExceeded` raised |
| C8(a) | — | discharged by the C1(a) run above (plan cell says "(C1(a) mutation)") | reused |
| C8(b) | `apply_stock_demand.py`, event-payload construction (def.) | `test_apply_stock_demand.py::test_c8b_...` | red: payload shows the stale step-6 values, not `RETURNING` |
| C8(c) | — | not run (cell is `—`) | declared not run |
| C8(d) | `apply_stock_demand.py`, `:created` event construction (def.) | `test_apply_stock_demand.py::test_c8d_...` | red: `workspace_id == ""` |

All mutations reverted; `git status --porcelain` on the two production files matches
their post-implementation content (verified below in the batch handoff).
