# Plan 13A — Scanner delete webhook: find-and-delete a board row through the existing cascade

```
state: NOT_STARTED
phase: 13A of 15 (after 13, before 14)
depends_on: 13, 9 (APPROVED)   — 9 brings 7 (verifier, parser shape) and 8; 13 brings 12 and the cascade
projection: mandatory, NOT waivable — the owner waived the mechanism-inventory re-check of §14E, so
            the six carried questions are checked here (§7 below); rule 17 shapes (raw-bytes body,
            Postgres lock re-evaluation)
complex: yes — a multi-row cascade under the five-class lock order, deterministic contention rows
```

## 1. Goal

`POST /api/v1/location-tracker/webhooks/stock-demand-deleted`: key-authenticated with demand's
verifier, parsed from raw bytes with demand's entry rules minus `quantityRequested`, each entry's
row found with **the same engine as find-or-create** (category resolution, MC-3 normalization and
signature, MC-4's live-identity predicate) and, when live, removed through **the existing
row-deletion cascade** (`cascade_delete_stock_report_item`, phase 13) with every assignment in any
state, tasks and items untouched, `NULL` authorship, MC-19's row-deletion events, outcomes
`deleted | not_found | category_not_found` echoed per entry in request order, a replay issuing zero
writes, under the demand deadline and `set_config` limits. **Not in this phase:** any new table,
column, migration or reset phase (there is none — intention §14E "adds a third Scanner webhook and
nothing else"); any change to the cascade's order (phase 13 owns it); the frontend/domain docs (14).

## 2. Read first

1. `master_plan.md` §6.1 (`StockDemandDeletedOutcomeEnum`, the `stock_demand_deleted` trigger), §6.3
   (the one timeout setting applies to both stock messages), §6.5 (`stock_demand_entries.py`
   `DemandDeleteEntry`, `_demand_lookup.py`, `stock_demand_deleted_request.py`,
   `process_stock_demand_deleted.py`, `_delete_stock_report_item_cascade.py`, `_locks.py`,
   `_events.py` coalescer), §6.6 (third route), §6.7, §7.2, §9 rules 4–7, 9, 16.
2. Intention **§14E in full** (E1–E13 and "Carried to the planner"), §14C C46, §13 M3 (the round-8
   sentence), §17 "Closed (round 8)"; then the contracts it cites: §8B MC-8 (steps 1–7, the demand
   defect table, category resolution), MC-9 (replay definition and instrument; the deadline and
   `set_config` part, rows (i) and (iii)), §4A MC-3 (normalization; echo as received) and MC-4
   (live-identity predicate), §5A MC-1 (global lock order; second self-heal trigger), MC-16
   (row-deletion cascade order), §7A MC-7 (gap closing; row 10 "the deleted row keeps its own
   values"; serialization by the advisory lock), §4B MC-17 (a Scanner-caused change records no
   one), §9D MC-19 ("Row deletion" row; net-change rule), §9E MC-18 (webhooks carry no role), §12A
   (`inline:stock_demand_deleted` trigger; reset), §14D D5–D6.
3. Scanner v2 handoff `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md` **§4A** (read-only;
   the wire shapes this phase must match exactly), §3.1.1, §3.3, §3.4–§3.5, §5.
4. Plans 6, 7, 9, 13 as shipped and their Review logs: `_demand_lookup.py` (the two lookup
   functions), `verify_location_tracker_webhook`, `parse_stock_demand_body`'s per-field validators,
   `process_items_processed` (the owning-transaction shape, X3), `delete_stock_report_item` (the lock
   sequence for one row — this phase generalizes it to several rows) and the cascade's signature.
5. Plan 6 C5(c) and its task 2 step 6 (the demand side of carried question (1)).
6. Repo: `bm/routers/api_v1/connecteam_webhooks.py` (route shape), `bm/services/commands/tasks/create_task.py:99`
   (advisory-lock statement form), `app/tests/integration/services/commands/item_economics/test_phase7_concurrency.py`
   (second-session shape).

## 3. Dependencies

Phases 13 and 9 APPROVED. Gate: intention header `status: RATIFIED` (round 9, `c231dfb` or later).

## 4. Files expected to change

New: `bm/services/commands/stock_report/stock_demand_deleted_request.py`, `process_stock_demand_deleted.py`;
`app/tests/unit/services/commands/stock_report/test_stock_demand_deleted_request.py`;
`app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py`,
`test_process_stock_demand_deleted_locks.py`.

Edited: `bm/services/commands/stock_report/stock_demand_entries.py` (`DemandDeleteEntry`,
`DemandDeleteOutcome`), `stock_demand_request.py` (only if the per-field validators must be exposed
for reuse — no behaviour change), `bm/routers/api_v1/location_tracker_webhooks.py` (third route),
`app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py` (third route wiring).

**Not changed, and the reviewer's perimeter check asserts it:** nothing under `app/migrations/`,
`bm/models/`, `bm/services/commands/reset/`, `_delete_stock_report_item_cascade.py`,
`_move_assignment.py`, `apply_stock_demand.py`. The enums this phase reads
(`StockDemandDeletedOutcomeEnum`, the `stock_demand_deleted` member of `INLINE_REPAIR_TRIGGERS`)
ship in phase 1 from the master plan registry.

## 5. Tasks (in order)

1. `DemandDeleteEntry` (frozen dataclass: `index`, `item_category_raw`, `item_category_key`,
   `properties_raw`, `properties_normalized`, `properties_signature` — `DemandEntry` without
   `quantity_requested`) and `DemandDeleteOutcome(index, item_category_raw, properties_raw, outcome)`
   in `stock_demand_entries.py`.
2. `parse_stock_demand_deleted_body(raw: bytes) -> list[DemandDeleteEntry]`: UTF-8 decode →
   `json.loads` → top-level list with ≥ 1 entry → per entry the MC-8 demand rules for `itemCategory`
   and `properties` (reuse `parse_stock_demand_body`'s validators; **do not** validate
   `quantityRequested` — it is an unknown key here and ignored like any other, E2/U7) → collect every
   defect → duplicates by `(item_category_key, properties_signature)` → `ValidationError("Malformed
   request: …")` naming every offending index. Raw properties are kept for the echo.
3. `process_stock_demand_deleted(ctx)`, the owning command:
   1. `deadline = time.monotonic() + timeout_ms / 1000` — **first line** (MC-9 part 1; E9).
   2. `workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])` (401 path).
   3. `entries = parse_stock_demand_deleted_body(ctx.incoming_data["raw_body"])` (422 path).
   4. `assert not ctx.session.in_transaction()`; `async with maybe_begin(ctx.session)` in owner mode
      with **nothing executed before it** (X3). Inside, in this order:
      1. `SELECT set_config('statement_timeout', :ms, true), set_config('lock_timeout', :ms, true)`
         — the first statement (MC-9 D5; E9).
      2. `SELECT 1 FROM workspaces WHERE client_id = :ws` → none → `LocationTrackerWebhookAuthError`.
      3. `acquire_stock_report_order_lock(session, workspace_id)` — MC-1 class 1, taken **before
         discovery** (rule Q1/Q2 below: every path that soft-deletes a row holds this lock first, so
         the live set discovered next cannot shrink before the row locks are taken).
      4. `resolve_categories_for_entries(session, workspace_id=…, entries=…)` — one `SELECT`
         (`_demand_lookup.py`, plan 6). No category → outcome `category_not_found` for that entry.
      5. `discover_live_rows_by_identity(session, workspace_id=…, identities=…)` over the entries
         with a category — one unlocked `SELECT` (`is_deleted = false`, same workspace). No live row →
         outcome `not_found`. Otherwise the entry is a **candidate** with its row `client_id`.
         Nothing is ever inserted (E4 "nothing is created").
      6. One unlocked `SELECT client_id, task_id FROM stock_task_assignments WHERE
         stock_report_item_id IN (candidates) AND is_deleted = false` (id discovery only; omitted
         when there is no candidate).
      7. `lock_tasks(session, workspace_id, <distinct task ids>)` — one statement, ascending (class 3).
      8. Lock the candidate rows **and every non-deleted row of their priority groups** in one
         `SELECT … FOR UPDATE ORDER BY client_id` with `populate_existing` (class 4; plan 13's form
         over several rows; groups are `(workspace_id, priority)` for each candidate whose priority
         is non-null). Snapshot the six event fields of every locked row for the coalescer.
      9. `lock_stock_task_assignments(session, workspace_id, <discovered assignment ids>)` — one
         statement, ascending (class 5).
      10. Re-read. A candidate row not returned by step 8 → `RuntimeError` (500): impossible while
          rule Q1 holds (no row-deleting path skips the advisory lock), and a 500 that Scanner retries
          is safer than a silent `not_found` that would hide a lock-order regression.
      11. For each candidate row in **ascending `client_id`**:
          `cascade_delete_stock_report_item(session, row, workspace_id=workspace_id,
          actor_user_id=None, now=ctx.now, trigger="stock_demand_deleted")`, appending its events.
          Each cascade closes its own gap from the positions as they stand **after** the previous
          cascade in this transaction (MC-7; the second deletion in one group sees the first's
          renumbering).
      12. `if time.monotonic() >= deadline: raise StockDemandDeadlineExceeded()` — the last action
          inside the block (E9; 503, nothing committed).
   5. After the block: `await event_bus.dispatch(coalesce_stock_report_events(events,
      initial_row_values=<step-8 snapshot>))` — the coalescer drops an `:updated` for a row that is
      `:deleted` in the same request (plan 8 task 4). Return `{"results": [{"itemCategory": raw,
      "properties": raw, "outcome": <enum value>}, …]}` in request order. `ctx.workspace_id` is
      never read (master plan §9 rule 5).
4. Router: third route in `location_tracker_webhooks.py`, exactly the shape of the other two
   (`Request` → `await request.body()` → `ServiceContext(identity={}, incoming_data={"raw_body",
   "headers"})` → `run_service` → `build_ok`/`build_err`).
5. Tests first from the tables below, then arm. Fixture: **F0** with rows created through the demand
   service (`AD`) and assignments through `CR`; terminal states reached with `PR` (phase 9) or
   `move_assignment` (phase 4). `DD(body_bytes)` = `process_stock_demand_deleted` with a valid key
   and both settings configured for W. "R's identity" = the entry `{"itemCategory": "Dining
   Chairs", "properties": {"wood_group": ["teak"]}}`. "401" / "422" as in plan 7. "zero writes" =
   `count_writes` over the four MC-9 tables **plus `stock_report_repair_records`** `== 0`. Every
   non-drift row ends with `assert_stock_report_clean(session, W)` and asserts the foreign
   workspace's identical shapes are untouched.

## 6. Criteria

Fixture, standing for every row below (this preamble is the fixture of record; §5 task 5 states the same shorthand for the implementer's reading order). **F0** with rows created through the demand service `AD` and assignments through `CR`; terminal states reached with phase 4's `move_assignment` or with `PR` when 9 is already APPROVED — **named per row, never offered as a choice** (L-30). `DD(body_bytes)` = `process_stock_demand_deleted` with a valid key and both settings configured for W. "R's identity" = `{"itemCategory": "Dining Chairs", "properties": {"wood_group": ["teak"]}}`. **Standing groups:** `high` = `A1 R2 C3 D4`, `low` = `X1 Y2`; a row that needs a different shape says so in its own fixture cell. "401"/"422" as in plan 7. "zero writes" = `count_writes` over the four MC-9 tables **plus `stock_report_repair_records`** `== 0`. Every non-drift row ends with `assert_stock_report_clean(session, W)` and asserts the foreign workspace's identical shapes are untouched.

Every outcome in this table is computed from the fixture's **own** values (each assignment's `quantity` and state, G's awaiting total, R's three counters, the standing group positions) plus this row's own deltas, **side effects included** — the per-assignment move, the goal arithmetic, the gap close, the row and history soft-deletes and the events are part of the outcome, not extras. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.

**The seed orders the groups against their ordering key** (L-14): `priority_order` ascending **disagrees** with `client_id` ascending inside `high`, so neither the cascade's own gap close nor the multi-row sequence of C5(b) can pass by renumbering in `client_id` order. Separately, the *cascade loop* is driven in ascending `client_id` (task 3 step 4.11), so a row that asserts the loop's order asserts it against the seeded ids — `client_id` is a ULID with no monotonic counter and is never creation order (master plan §10).

Tenancy and visibility are enumerated in all three cells per entity class — never created (C2(h)), already soft-deleted (C2(g)), foreign (C2(f)) — and C2(f) is a **cross-workspace reference** (L-16): the foreign row carries the same category name and the same properties, so tenancy is the only reason the entry answers `not_found`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | no `x-api-key`, valid body naming R | 401 `Unauthorized.`; R still live; nothing written | fall through to parse | M7, MC-8 step 3, §14E E2 |
| C1(b) | wrong key | 401; nothing written | `process_stock_demand_deleted.py` (def.): delete step 4.2's `verify_location_tracker_webhook` call → the request is parsed and applied and the row is deleted → red. Shares its site with C1(a); both runs recorded (§9 rule 8) — C1(a) bites on the missing-header path, this one on the wrong-key path, and `verify_location_tracker_webhook`'s own behaviour is phase 7's, not re-proved here | M7 |
| C1(c) | wrong key **and** body `b"not json"` | 401, not 422 | parse before verify | MC-8 order (C19) |
| C1(d) | `b"[]"` | 422; nothing written | accept → 200 | MC-8 step 6, §14E E2 ("empty array → 422"), v2 §4A.1 |
| C1(e) | `b'{"itemCategory": "Dining Chairs", "properties": {"wood_group": ["teak"]}}'` — one entry sent **unwrapped**, i.e. a non-empty JSON object where an array is required (the realistic sender mistake; a non-empty object is what makes the `isinstance(payload, list)` term load-bearing, see the mutation) | 422 | `parse_stock_demand_deleted_body` (def.): drop the `isinstance(payload, list)` term from the shape guard → a bare JSON object is iterated as its key list and (with the fixture below) reaches the entry loop → red. C1(d)'s empty-array mutant (`len(payload) == 0`) leaves this row green and vice versa, which is why the fixture is a **non-empty** object (L-12) | MC-8 step 6 |
| C1(f) | entry without `properties` | 422 | default to `{}` | MC-8 defect table |
| C1(g) | `properties: null` | 422 | treat as `{}` | MC-8 (C3) |
| C1(h) | `itemCategory: "  "` | 422 | the shared per-field validator (def., `stock_demand_request.py`): drop `.strip()` from the `itemCategory` non-blank check → `"  "` passes the shape, category resolution then finds nothing and the request answers 200 `category_not_found` instead of 422 → red | MC-8 |
| C1(i) | R's identity **with** `"quantityRequested": 5` in the entry | 200, outcome `deleted` (the key is ignored, not validated) | reject or validate the key | §14E E2 (U7), v2 §4A.1 ("sent anyway, it is ignored") |
| C1(j) | two entries, properties `{"wood_group": ["Teak", "Dark"]}` and `{"wood_group": ["dark", "teak"]}`, same category | 422 naming `entries 0 and 1`; **nothing deleted** (a live row with that identity stays live) | compare raw dicts → 200 | MC-8 step 7, MC-3, §14E E2, v2 §4A.1 |
| C1(k) | entries 0 and 2 malformed, entry 1 = R's identity | 422 naming `entry 0` and `entry 2`; R still live | stop at the first defect / apply entry 1 | MC-8 "names every offending entry", §8 atomic |
| C2(a) | R's identity, category `"Dining Chairs"` (exact) | `deleted`; R `is_deleted` | `process_stock_demand_deleted.py` (def.): report `deleted` for a found candidate without calling `cascade_delete_stock_report_item` → the outcome is right and R is still live → red. Every `not_found`/`category_not_found` row stays green under this mutant, which is what makes this row the positive control of C2 (L-26: the outcome enum is observed carrying its positive value, not only its negatives) | §14E E4, MC-8 category resolution |
| C2(b) | `"dining chairs"` (case variant; only K exists) | `deleted` | drop the case-insensitive fallback → `category_not_found` | MC-8 (U6), §14E E4 |
| C2(c) | W also has a category `"dining chairs"`; entry `"DINING CHAIRS"` | `category_not_found`; R still live | `_demand_lookup.py:resolve_categories_for_entries` (def.): take `case_insensitive[0]` whenever the list is non-empty instead of requiring `len(...) == 1` → the ambiguous `"DINING CHAIRS"` resolves to whichever candidate the SELECT returned first and the row is deleted → red. (There is no `.limit(1)` at this site; the guard is the in-memory length check — L-25, the site named is the site the row depends on) | MC-8 (C14), §14E E7 |
| C2(d) | entries `[unknown "Serving Trolleys" + R's properties, R's identity]` | results `[category_not_found, deleted]` in request order; R deleted | reject the request / stop at the first miss | §14E E7 ("other entries are still applied"), M3 |
| C2(e) | properties `{"wood_group": ["Teak", " TEAK "]}` (normalizes to R's identity) | `deleted` | match on the raw signature → `not_found` | MC-3, §14E E4 ("normalized and signed by MC-3") |
| C2(f) | the identity exists **only** in the foreign workspace (same category name, same properties) | `not_found`; the foreign row untouched | drop the `workspace_id` filter → the foreign row is deleted | MC-4 predicate ("same workspace"), M4, MC-8 workspace guard |
| C2(g) | R already soft-deleted (by a user, plan 13's command) | `not_found` | match deleted rows | §14E E7 ("already deleted — what a replay reads"), MC-16 |
| C2(h) | an identity never created (K + `{"wood_group": ["dark"]}`) | `not_found`; zero `INSERT` on `stock_report_items` during the request; no `:created` event; no live row with that identity afterwards | find-or-**create** (call the demand insert) | §14E E4 ("nothing is created") |
| C3(a) | R in the `high` group as B2 of `A1 B2 C3`, with five assignments on five tasks/items: A1 `awaiting` `q = 2` (credited to G), A2 `resolved` `q = 3` (credited, kept), A3 `in_queue` `q = 1`, A4 `resolved_early` `q = 5` (credited, F4), A5 `failed` `q = 4` — `G == 10` before, counters `(1, 0, 2)`; `DD([R's identity])` | `deleted`; all five assignments `is_deleted`, `deleted_at == ctx.now`, `deleted_by_id IS NULL`, their `updated_*` unchanged; `G == 8` (only A1's credit subtracted) and G soft-deleted with `deleted_by_id IS NULL`; R `is_deleted`, `deleted_at == updated_at == ctx.now`, `deleted_by_id IS NULL`, `updated_by_id IS NULL`, counters `(0, 0, 0)`; all five tasks' `is_stock_assignment` false; every history record of R soft-deleted with NULL author | remove only active assignments (A2/A4/A5 survive) / stamp a fake system user | §14E E5 ("any state"), E6, MC-16 cascade, MC-17 (Scanner records no one), MC-5, M3 round-8 sentence |
| C3(b) | (a), recording before the call for each of the five tasks `state`, `updated_at`, `updated_by_id`, `is_deleted`, the count and states of its steps, and for each item `is_deleted`, `updated_at`, `item_category_id` | every recorded value byte-identical after; no task event dispatched | cancel / soft-delete the task in the cascade; touch a step | §14E E5 ("tasks, task steps and items are never touched"), M3 round-8 sentence, M2 |
| C3(c) | (a)'s group `A1 R2 C3` | `high` = `A1 C2`; R's own (deleted) row keeps `priority high`, `priority_order 2`; `assert_stock_report_clean` | renumber the deleted row / leave the gap | MC-7 row 10, MC-16, §14E E5 ("the row's gap closed") |
| C3(d) | (a) with `capture_dispatch` on the command's import site | exactly: one `stock_report_item:deleted` (R), five `stock_task_assignment:deleted` with the states at deletion, one `stock_report_item:updated` for C (`priority_order 2`); **no** `:updated` for R; every event's `workspace_id == W` | emit `:updated` for R / build `workspace_id` from `ctx` (`""`) | §14E E12, MC-19 "Row deletion", master plan §9 rule 5 |
| C3(e) | after (a), `AD([R's identity, 6])` (the demand service) | a **new** live row: `client_id ≠ R`, `quantity_requested 6`, `priority IS NULL`, `priority_order IS NULL`, counters `(0, 0, 0)`, no assignments, exactly one goal record (`6`, awaiting `0`); events `[stock_report_item:created]` | reuse (un-delete) the old row | §14E E10, MC-4, MC-16 ("a soft-deleted row is outside the predicate") |
| C4(a) | deliver `[R's identity]` twice | second delivery: result `not_found`; **zero writes**; no event | `_demand_lookup.py:discover_live_rows_by_identity` (def.): drop `is_deleted = false` → the replay rediscovers the deleted row, re-runs the cascade, and both the zero-write and the no-event halves fail → red. Same edit as C4(b)'s cell; the two rows assert different things (C4(a) zero writes and no event; C4(b) additionally *still exactly one* repair record), so **both runs are recorded** (§9 rule 8) | §14E E8, MC-9, HC-5, M3 |
| C4(b) | **carried question (4):** A3 `in_queue` `q = 1` on R; raw `quantity_in_queue = 0` (truth 1); deliver `[R's identity]` twice | first: `deleted`; exactly one repair record `{stock_report_item, R, quantity_in_queue, stored "0", recomputed "0", trigger "inline:stock_demand_deleted", created_by_id NULL}` (A3's move would write −1, MC-1 self-heal) and no second-trigger record; second delivery: `not_found`, **zero writes over the five tables**, no event, and **still exactly one** repair record for R | drop `is_deleted = false` from `discover_live_rows_by_identity`'s predicate → the replay rediscovers the deleted row, re-runs the cascade → writes counted, a second record | §14E carried (4), E8, MC-9 instrument, §12A trigger set |
| C5(a) | **carried question (1), tasks-before-rows:** A `in_queue` on R (task T). Session H (`get_db_session()`): `UPDATE tasks SET updated_at = updated_at WHERE client_id = T` (holds T's row lock, as a task command's own `Task.state` UPDATE does — MC-1 class 3), held; main: `DD([R's identity])` started as a task | `DD` has **not** returned after 0.5 s (it is waiting on T at step 7); H then runs `SELECT … FROM stock_report_items WHERE client_id = R FOR UPDATE` and it returns **within 0.5 s** (R is not yet locked by `DD`, because rows come after tasks); H commits; `DD` returns `deleted` with no `DBAPIError`; clean | `process_stock_demand_deleted.py` (def.): lock rows (step 8) **before** tasks (step 7) → `DD` holds R and waits on T while H holds T and waits on R → PostgreSQL detects the cycle after `deadlock_timeout` and one side raises an error → red. **Rule 17, grounded on the installed stack (PostgreSQL 18.6, `deadlock_timeout = 1s`, asyncpg 0.30.0, SQLAlchemy 2.0.40):** asyncpg raises `DeadlockDetectedError` (`sqlstate = "40P01"`); SQLAlchemy's asyncpg dialect maps it through `PostgresError → AsyncAdapt_asyncpg_dbapi.Error` (the **base** class, not `OperationalError`), so the wrapper our code sees is `sqlalchemy.exc.DBAPIError` and the assertion is `exc.orig.sqlstate == "40P01"`. A test written against `OperationalError` would not catch it | §14E carried (1), MC-1 global lock order (3 → 4), MC-11 premise |
| C5(b) | **carried question (2), two rows of one group:** `high` = `A1 R2 C3 D4`, R and C each with one `in_queue` assignment; `DD([R's identity, C's identity])` in that order | results `[deleted, deleted]`; `high` = `A1 D2` (dense); R's deleted row keeps `priority_order 2`, C's deleted row keeps `priority_order 2` (it was shifted `3 → 2` by R's cascade before its own deletion); both assignments deleted; events exactly: `:deleted` R, `:deleted` C, two assignment `:deleted`, **one** `:updated` for D (`priority_order 2`), **no** `:updated` for C (the coalescer's `:deleted` rule, plan 8 task 4) and none for A; `assert_stock_report_clean`. The reviewer verifies structurally that steps 3, 7, 8, 9 are each **one** statement (one advisory lock, one sorted lock per class) — unforceable by a test | close both gaps from the group positions read at step 8 (a stale snapshot: C's cascade then shifts by its old order 3) → D ends at 3, `order_density` divergence → red; or drop the coalescer's `:deleted` clause → a `:updated` for C appears | §14E carried (2), MC-7, MC-19, M6 |
| C5(c) | **carried question (2), across groups with a miss between:** the standing groups of the preamble, `high` = `A1 R2 C3 D4` and `low` = `X1 Y2`; `DD([R (high), <never-created identity>, X (low)])` in that order | results `[deleted, not_found, deleted]` in request order; `high` and `low` both dense (`A1 C2 D3`; `Y1`); clean | sort results by outcome / by `client_id` | §14E E7 ("in request order"), MC-7 |
| C5(d) | **carried question (3):** shape *all `not_found`* (identities never created, one category): 3 entries vs 30 entries; and shape *all `category_not_found`*: 3 vs 30 | total statements recorded during `DD` **equal** for both sizes within each shape, and `≤ 7` (steps 4.1–4.6, several omitted); no write | resolve categories or discover rows with one `SELECT` per entry → the 30-entry count differs | §14E carried (3) — the find step is set-based like demand's; the cascade itself carries **no bound** (rule below), §14D D6 |
| C5(e) | **carried question (5):** after C3(a), `compute_stock_report_divergences(session, W)` and the same for the foreign workspace W′ (seeded with the identical row, group and five assignments, untouched) | `[]` for W (every `task_flag` false, `order_density` dense, no `counter_*`, `goal_total` consistent for the soft-deleted G: stored 8 = Σ over A2 3 + A4 5) and `[]` for W′ with W′'s row still live and its counters unchanged; zero repair records in both | skip `recompute_task_stock_flag` in the per-assignment step (a `task_flag` divergence) / drop the `workspace_id` term in step 5 (W′'s row is deleted) | §14E carried (5), MC-20, M1, M4 |
| C5(f) | **carried question (6):** after C4(b) (a soft-deleted row, its soft-deleted assignments and history, one repair record), `reset_app(ctx for W)`; the foreign workspace holds live shapes | returns; `count(*) … WHERE workspace_id = W` is 0 on all four tables; the workspace row gone; the foreign counts unchanged | move the four reset phases after `delete_tasks` (`reset_app.py`) → FK RESTRICT | §14E carried (6), §12A reset, M1 |
| C5(g) | **two concurrent demand batches with overlapping new identities.** Session H and the main session each call the demand command with the same two *new* identities X and Y, in **opposite** request order (`[X, Y]` and `[Y, X]`), released together by a barrier (the C5(a) two-session pattern) | both return 200, every entry `applied`; exactly **one** live row per identity; `stock_report_item:created` emitted exactly once per identity; **no `DBAPIError` (SQLSTATE `40P01`) on either side**; clean | `apply_stock_demand.py` (definition site), each run separately and **both runs recorded**: (i) drop `sorted(...)` from `absent_identities` so the multi-row INSERT's VALUES follow request order; (ii) drop `.order_by(StockReportItem.client_id)` from the `FOR UPDATE` select. Either makes the two sessions take the two row locks in opposite orders → the cycle is detected after `deadlock_timeout` (1 s on the installed 18.6) and one side raises `sqlalchemy.exc.DBAPIError` with `exc.orig.sqlstate == "40P01"` → red. Measured 2026-09-21: removing **both** sorts leaves all 28 phase-6 tests green — nothing existing contends | MC-4 ("Sorting the VALUES means two concurrent batches with overlapping new identities wait on each other instead of deadlocking"); batch B2 review 1 N5, CF-2, owner card 1. Measured 2026-09-21: removing **both** sorts leaves all 28 phase-6 tests green — nothing existing contends |
| C6(a) | setting unset (default); `record_statements` around `DD` | the **first** recorded statement is the `set_config` call with both parameters `== str(Settings.model_fields["stock_demand_webhook_timeout_ms"].default)` | any statement before it | §14E E9, MC-9 (i), charter rules 10/13 |
| C6(b) | `process_stock_demand_deleted.time.monotonic` patched to `deadline + 1` for the check | raises `StockDemandDeadlineExceeded` (`http_status 503`); R still live, its assignments untouched, no repair record, no event | delete the check → the delete commits → red | §14E E9 (P39), MC-9 (iii), §14D D5 |
| C7(a) | unit router test: `TestClient` POST `/api/v1/location-tracker/webhooks/stock-demand-deleted` with `content=b'[...]'`, header `X-API-KEY: k`, `run_service` faked | the command receives `incoming_data == {"raw_body": b'[...]', "headers": {..."x-api-key": "k"...}}` and `identity == {}`; success renders `{"data": {"results": [...]}, "ok": true, "warnings": []}`; a faked `LocationTrackerWebhookAuthError` renders 401 `{"error": "Unauthorized.", "ok": false}` | — (wiring; calibration) | §14E E2, E7, §8A envelope |
| C7(b) | `DD` with entries `[R's identity sent as {"itemCategory": "dining chairs", "properties": {"wood_group": ["Teak", " TEAK "]}}, <unknown category>, <never-created identity>]` | `results` has three elements, each with exactly the keys `itemCategory`, `properties`, `outcome`; `itemCategory` and `properties` echoed **byte-for-byte as received** (`"dining chairs"`, `["Teak", " TEAK "]`, not the normalized form); outcomes `[deleted, category_not_found, not_found]` | echo the normalized form / the resolved category name | §14E E7 ("echoing as received"), v2 §4A.3, MC-3 |

## 7. §14E carried questions — Q1–Q6 → rule → row

The owner waived the mechanism-inventory re-check of §14E; these are the planner's answers, each a
stated rule and a row that can fail. The round-0 projection checks all six.

| Q | Question (intention §14E) | Stated rule | Row(s) | Status |
|---|---|---|---|---|
| Q1 | Lock order of the cascade against a concurrent demand request naming the same identity and against the processed webhook — any cycle? | **No cycle.** Every Stock Report path acquires lock classes in MC-1's global order and ascending `client_id` within a class: this webhook and the user row delete take **1 advisory → 3 tasks → 4 rows(+groups) → 5 assignments → 6 history**; demand takes **4 rows** (one sorted `FOR UPDATE`) then **6** (goal INSERT), never 1–3 or 5; processed takes **4 → 5 → 6**; the sync takes **3** (its own task UPDATE, flushed) **→ 4 → 5 → 6**. Wait-for edges therefore run only from a lower class to a higher one, or ascending within one class, so no cycle can form. Two consequences are handled explicitly: (i) *delete commits while a demand for the same identity waits at its row lock* — the demand's `FOR UPDATE` re-evaluates `is_deleted = false` on the committed version and drops the row (PostgreSQL manual §13.2.1), so demand asserts its locked set equals its identity set and answers **500** (Scanner retries; the retry creates the fresh row, E10) — plan 6 task 2 step 6, row **plan 6 C5(c)**; (ii) *demand's uncommitted INSERT of the same identity while this webhook discovers* — invisible, read as `not_found`, the new row survives; that order is excluded by the sender rule E3, and Manager adds no defence beyond E9. The advisory lock is taken **before** discovery (task 3 step 4.3) so the discovered live set cannot shrink before step 8: every row-deleting path (this webhook, the user delete) holds it first. **Projection r0, 2026-09-21 — the enumeration above was a sample; every Stock Report path in the shipped tree was read and each ascends:** `create_stock_task_assignments` **2 items → 3 tasks → 4 rows** (`:89-91`); `delete_stock_task_assignments` **3 → 4 → 5** (`:78-80`); `repair_stock_report` **1 → 3 → 4 → 5 → 6** (`:169-206`); `process_items_processed` **4 → 5** (+6 via the goal credit, `:114-118`); `sync_task_stock_assignments` **3 (its own flushed task UPDATE) → 4 → 5** (`:86-92`); `apply_stock_demand` **4 → 6** only (`_demand_lookup` reads are unlocked). No path acquires a lower class after a higher one, and `_locks.py:_lock` sorts within every class, so the wait-for graph is acyclic. The one premise outside this project's files: MC-1's "items before tasks" ordering must hold in foreign task commands too (precedent `cancel_upholstery_requirements.py`), which is MC-1's claim, not this phase's. | **C5(a)** (tasks before rows, deterministic deadlock-shape mutation); **plan 6 C5(c)** (the demand side) | settled — **re-verified against the shipped tree at projection r0** |
| Q2 | Several rows in one request: sorted ascending, one advisory lock; two rows of one priority group → both gaps closed correctly? | One advisory lock per request (step 4.3), one sorted lock statement per class (steps 7–9) covering every candidate row **and every row of every touched group**, then the cascades run **one row at a time in ascending `client_id`**, each closing its own gap from the positions as they stand after the previous cascade in the same transaction. The deleted rows keep the order they held at their own deletion (MC-7 row 10). The coalescer emits no `:updated` for a row that is `:deleted` in the same request (plan 8 task 4). | **C5(b)**, **C5(c)** | settled |
| Q3 | Does the D6 statement bound apply? | **No bound on the cascade, by design.** The effect is per assignment and per row by ratified order (MC-16: `move_assignment(DELETE)` per assignment, a gap close per row) and deletes are rare (E1, v2 §4A). What *is* bounded is the **find step**, which reuses demand's set-based lookup (`_demand_lookup.py`): the same statement count for 3 and for 30 entries of one shape, and no per-entry `SELECT`. **Projection r0 derived the two exact counts from the shipped `_demand_lookup.py` and task 3's own step list** (`record_statements` sees no BEGIN/COMMIT — calibrated against the §9 demand budget, where all-unchanged = 5): shape *all `not_found`* = **exactly 5** (`set_config`, workspace, advisory lock, `resolve_categories_for_entries`, `discover_live_rows_by_identity`; steps 4.6–4.9 all short-circuit on an empty id set, and `_locks.py:_lock` issues no statement for `client_ids == []`); shape *all `category_not_found`* = **exactly 4** (the same minus discovery, which returns `{}` without executing when `identities` is empty). C5(d)'s `≤ 7` is therefore two-to-three statements of slack on a count this projection derived exactly — L-22's own defect. Making the cell exact is an owner card. | **C5(d)** | settled ("no bound", reason stated); **the find-step count is now derived exactly — the cell still says `≤ 7`** |
| Q4 | The replay instrument for a row whose cascade self-healed | The first delivery may write repair records (`inline:stock_demand_deleted`, `created_by_id NULL`) while deleting; the replay reads `not_found` and issues **zero** INSERT/UPDATE/DELETE over the four MC-9 tables **and `stock_report_repair_records`**, dispatches nothing, and leaves the first delivery's record count unchanged. | **C4(b)** | settled |
| Q5 | The MC-20 check after a Scanner deletion | Unchanged definitions: after the webhook the check returns `[]` for the workspace — flags false for every task whose only assignments were on the deleted row, the group dense, no counters left, the soft-deleted goal record consistent with its kept credits — and `[]` for a foreign workspace holding the same shapes, which the webhook never touches. | **C5(e)** (plus `assert_stock_report_clean` at the end of every non-drift row) | settled |
| Q6 | The workspace reset is unaffected (no new table) | This phase adds no table, column, migration or reset phase (§4 perimeter, reviewer-checked); the four phase-1 reset phases hard-delete rows a Scanner deletion left soft-deleted, repair records included. | **C5(f)** | settled |

## 8. Notes

- Sizing: 37 criterion rows in 7 criteria; `complex: yes` (derived by script; see the delta handoff).
- **Owner card 1 fold, 2026-09-21.** The count above is the previously derived count **+1**: exactly one criterion row was added to this plan by that fold, verified as a single `^+| C` line in `git diff` (not re-derived by a new script — the published totals and my regex disagree on row shape, and a typed count is the defect this project keeps finding).
- **Roles:** none — key-authenticated like the other webhooks (E13, MC-18). The user-facing
  `DELETE …/items/{id}` keeps its four cells in plan 13; no role row here.
- **Rule 17 cells.** C5(a)'s expected behaviour under the mutation (a deadlock detected and raised as
  `DBAPIError` with SQLSTATE `40P01` after `deadlock_timeout`, default 1 s) and plan 6 C5(c)'s
  row-drop on re-evaluation are Postgres-owned shapes: the public contract (manual §13.2.1 and
  §13.3.4) settles both; projection confirms on the installed 18.6 and records the version. The
  raw-bytes parsing shapes are plan 7's, already grounded.
- C5(a) and C5(b) are deterministic (held lock + bounded wait; master plan §9 rule 9); no row in
  this phase relies on an unforced interleaving.
- The one sleeping test of the project stays in phase 6 (master plan §9 rule 10); C6 proves the
  limit is *applied* (first statement) and the deadline *checked* (503); the lock-timeout behaviour
  is the same `set_config` statement phase 6 measured.
- Statement counting (C5(d), C4, C6(a)) goes through `record_statements`/`count_writes` only
  (master plan §9 rule 7).
- Nothing is owed to Scanner at closeout: the v2 file already carries §4A (intention §18, round 8 and the v2 entry).
- The processed webhook's per-entry decision (phase 9) and this webhook never touch a task; both
  are MC-17 "Scanner" rows (`NULL` authorship).

**Added by the batch D projection + fold, 2026-09-21 (round 0). Nothing below changes a criterion outcome.**

- **Rule-17 shapes, grounded on the installed stack** (the §8 note above asked for exactly this):
  PostgreSQL **18.6**, `deadlock_timeout = 1s`, `lock_timeout = 0` and `default_transaction_isolation
  = read committed` read from the configured server; asyncpg **0.30.0**, SQLAlchemy **2.0.40**,
  pydantic **2.11.3**. `asyncpg.exceptions.DeadlockDetectedError` carries `sqlstate = "40P01"`; the
  asyncpg dialect's `_asyncpg_error_translate` matches it only at `PostgresError`, so it becomes
  `AsyncAdapt_asyncpg_dbapi.Error` — the **base** DBAPI class, not `OperationalError` — and what our
  code catches is `sqlalchemy.exc.DBAPIError` with `exc.orig.sqlstate == "40P01"`. C5(a) and C5(g)
  say `DBAPIError`, which is right; a test written against `OperationalError` would not catch it.
- **C5(a)'s wait budget.** `DD` sets `lock_timeout = statement_timeout = 5000 ms` as its first
  statement and raises `StockDemandDeadlineExceeded` if `monotonic()` passes the 5 s deadline at
  step 4.12. H's whole hold — the 0.5 s observation, H's own `FOR UPDATE` and H's commit — must
  therefore finish **well inside 5 s**, or the row fails for the wrong reason. Under the mutation
  the deadlock is detected at 1 s, comfortably first (L-19: the condition the bite depends on,
  repeated where the bite is claimed).
- **L-37 — step 4.10's `RuntimeError` is dead by design.** It fires only if a candidate row
  discovered under the advisory lock is missing from the step-8 lock, which rule Q1 makes
  impossible; no criterion arms it and none should. Recorded here so no round burns time trying to
  redden it, and so no reviewer files it as an unguarded branch.
- **L-35 considered, not applicable.** The write loop iterates the **discovered** candidate set
  (task 3 step 4.11), which is the rule; and C1(j)'s duplicate-identity 422 means a repeated
  identity never reaches the loop, so iterating the request list instead would be observationally
  identical here. The distinction stays invisible in this phase.
- **L-26 is already discharged for `count_writes`** (measured non-zero, batch B2 re-review; plan 6
  §7). C4(a)/C4(b)/C2(h) cite it; no round re-buys the observation.
- **`_row_values` is triplicated and unregistered.** Step 4.8's snapshot must match
  `coalesce_stock_report_events`'s comparison exactly — the six event-payload keys with `priority`
  as `priority.value` (or `None`), never the enum member — or a genuinely unchanged row still emits
  `:updated`. The shape exists three times in the tree
  (`create_stock_task_assignments.py:56`, `delete_stock_task_assignments.py:34`,
  `sync_task_stock_assignments.py:36`) and in §6.5 not at all; this phase would be the fourth copy.
  Registering one shared helper is a §6.5 change, i.e. the coordinator's.
- **C5(g)'s home file.** The row exercises the *demand* command's two sorts, not this webhook's;
  §4 gives it no file. `test_process_stock_demand_deleted_locks.py` is the natural home (it owns the
  two-session machinery this row needs), and saying so avoids a fourth new test file appearing in
  the perimeter check.
- **Shared per-field validators.** §4 leaves "expose `stock_demand_request.py`'s validators for
  reuse" conditional ("only if"). That is silent freedom over a phase-7 APPROVED file: extracting
  one shared `_validate_entry_fields` keeps MC-8's defect strings identical for both webhooks,
  duplicating ~12 lines lets them drift. The projection recommends extraction with no behaviour
  change; either way the choice is recorded before the implementer prompt compiles, not taken in
  code.

## 9. Review log

**Owner, 2026-09-21 — criterion row authored (batch B2 card 1, CF-2).** **C5(g)** added: two concurrent demand batches with overlapping new identities must not deadlock (MC-4's sorted VALUES + sorted `FOR UPDATE`). **No test exists yet — owed by this phase's implementation round**, which is where the two-session machinery is built. The reviewer measured that removing **both** sorting rules leaves all 28 phase-6 tests green: this is the longest-undefended of the five rows, correct in shipped code since batch B2 and unguarded until this phase.

(empty — append-only, shared by implementer and reviewer)
