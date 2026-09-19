---
plan: (pre-plan, project-level — no master plan and no phase plans exist yet)
role: reviewer (mechanism-inventory gate — re-check after the round-7 fold)
round: inventory-recheck
date: 2026-09-19
state: done
verdict: PASS
actor: Claude Opus 5 (1M context), mechanism-inventory re-check session
---

# Mechanism-inventory re-check handoff: `stock_report`

## Opening summary

The gate check passed on all four lines. The header reads `status: RATIFIED`, written by the owner
for round 7 (§18 "Re-ratification — 2026-09-19"). The intention was clean at `a0e14b1`; the only
dirty path was `codex_test.py`, which is foreign. The round-6 handoff exists, and there is no
`master_plan.md` and no phase plan.

The perimeter was seven contracts. **One** (MC-18) passes as written. **Six** needed sentences an
implementer could otherwise have satisfied with two different behaviours, and those sentences are
now in the intention. They are round-7 text tightened in place, marked *(re-check, round 7)*. No
round 0–6 sentence was edited; where round-7 text contradicts round-6 text, the conflict is
ledgered as §14C **C41–C45**. The changelog is §18, "Round 7 re-check".

Two findings are more than wording:
1. **MC-9's time limit did not do what card 11a bought.** The round-7 text said per-statement
   `SET LOCAL` limits keep the request under Scanner's 8 s. They bound each statement, not the
   request (measured). A request of several fast statements can still commit after Scanner gave
   up, which is exactly the phantom-goal case the owner closed. The fix is a request deadline,
   checked immediately before commit. Also, a parameterized `SET LOCAL` is a syntax error on this
   stack (measured), so the limits are applied with `set_config(…, true)`.
2. **D6's set-based INSERT contradicted MC-9's replay instrument.** MC-4's "one multi-row INSERT
   … ON CONFLICT DO NOTHING over every identity" means a replay still *issues* an INSERT, and
   MC-9 counts statements. The D6 statement plan (§8B) discovers identities without a lock and
   inserts only the absent ones. With that, both hold.

**Verdict: `PASS`.** Every perimeter contract is now contract-grade. Nothing changes product
behaviour: the deadline implements card 11a's own words ("abandons any demand call that runs past
about 5 seconds"). So the gate stays RATIFIED and there is no card.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. One piece of information for them is outside this project: Scanner's
existing webhook worker **drops** a delivery when its own 8 s timeout fires, instead of retrying
it (X1 below). It is recorded as a sender note for the closeout handoff.

## 1. Per-contract findings

| Contract | Question from the prompt | Finding | What was written |
|---|---|---|---|
| §5A MC-1 | "0 rows = would go negative" sound? | Sound only if the WHERE carries no other predicate. An implementer adding the habitual `is_deleted = false` / `workspace_id` makes 0 rows ambiguous (deleted row read as drift → a "repair" of a dead row) | WHERE is exactly `client_id` + the three guards; liveness/workspace settled at the step-4 lock and the step-5 re-read; a repair statement returning ≠ 1 row is a programming error |
| MC-1 | Write order for every caller, incl. DELETE and creation | **Not stated for DELETE or creation.** DELETE had two owners of the soft-delete: MC-16 says the caller soft-deletes *after* the move, while the repair bullet needs it flushed *before* the Σ. Creation said "inserts with no counted state", with `state`'s nullability unstated | One write order for every path: own columns (state / soft-delete / `updated_*` / credit memory) written and flushed, then the counter statement, then the goal statement. The soft-delete belongs to `move_assignment` (C44). Creation inserts with `state` = target and is told `∅ → B` by its caller (C45) |
| MC-1 | Can the recomputation be wrong under a concurrent writer (MC-11)? | No, but only because of an unstated premise: every writer of an assignment's `state` / `is_deleted` / credit memory holds the row lock. Verified across creation (MC-13 phase 2), the sync (MC-2 step 5), the resolve (MC-10), the delete paths (MC-14, MC-16) and the manual repair | Premise stated, with the READ COMMITTED snapshot argument and the MC-11 instrument as its test |
| MC-1 | Is `stored + delta ≠ recomputed` decidable per column? | **No: `stored_before` had no source.** The ORM instance is stale after any earlier Core UPDATE of the same row in the same transaction (the row-deletion cascade, the grouped processed update), and it makes the rule silently skip records | Read fresh after the 0-row result, never from the ORM. `stored_value` stays "before the operation" (ratified §12A), so an inline record may read `0 → 0`; the warning now carries the delta. Instrument rows (b) DELETE order and (c) fresh `stored_before`, each with a planted defect that the original row (a) cannot see |
| §6A MC-5 | Which lock protects `R` when `R` is not current? | The text said "the record is locked"; no statement locks it. What protects `R` is the row lock: `R` belongs to the assignment's row, and every writer of any goal total of that row holds that lock | Stated. Exact WHERE. Memory cleared in the flushed own-columns write before the Σ. "Exactly one record" shown to follow from the rule |
| MC-5 | Worked sequence still holds? | Yes: the guard never trips in (1)–(6); G1 = 0, G2 = 4 | — |
| §8B MC-9 | `SET LOCAL` inside `maybe_begin`: holds, leaks, what is raised, what status | Holds for the transaction and does not leak (measured). But: (a) a parameterized `SET LOCAL` fails with `ProgrammingError` 42601; (b) **the limits are per statement**, so round-7's "stays under 8 s" is false (C43); (c) a timeout arrives as `sqlalchemy.exc.DBAPIError`, *not* `OperationalError`, with `.orig.sqlstate` 57014 / 55P03, which reaches `run_service` → base `DomainError` → **500**; (d) a statement executed before `maybe_begin` would autobegin, make the webhook's `maybe_begin` subordinate, and commit nothing | Request deadline checked immediately before commit → 503; `set_config(…, true)` as the first statement of one owning transaction; exception class and status stated; liveness limit stated honestly |
| MC-9 | Does the rule-10 instrument prove the default is applied? | **No.** "Inside the webhook's transaction, `SHOW …`" has no seam a test can reach | Three runnable rows: (i) the listener captures the `set_config` first statement carrying the setting's default; (ii) a lock holder → 500 in the window, nothing written, no event; (iii) the clock advanced past the deadline → 503, nothing written. Each has a planted defect |
| MC-9 | Does a timeout leave nothing written? | Yes: the raise propagates through `session.begin()` → rollback, and events are built only after a normal exit | Asserted in rows (ii) and (iii) by row snapshots (the statement listener would count rolled-back statements) |
| MC-9 | Scanner's `DISPATCH_TIMEOUT_MS` | **8 000 ms confirmed**: `outbound-webhook-worker.ts:12`, Scanner `0d80bf2`, clean tree. New: the worker's `isRetryableError` does not recognise its own timeout (X1) | Sender note added |
| §5B MC-14 | Raise inside the transaction, nothing persists? | Yes. `find_or_create_item`'s `maybe_begin` is subordinate under `create_task`; no `begin_nested` wraps the call; the earlier steps (`write_task_note`, `find_or_create_customer`) neither commit nor dispatch | Placement stated: before the first write to `existing` |
| MC-14 | Guard condition | **Defect in the text:** "incoming differs from stored (None-aware)" without the `model_fields_set` term would refuse every task that merely *names* a board item, because the request's default `None` differs from the stored category | `"item_category_id" in model_fields_set` added |
| MC-14 | Other callers; is refusing right for each | Exactly two (below). The second is an item edit by another name, so B6's rule applies | Both named. No third category writer exists (searched) |
| MC-14 | Lock order Items → Tasks | `create_task` holds its workspace advisory key and its own new, uncommitted Task row when the guard locks the Item. Neither can close a cycle: that key has one taker, and no transaction can wait on an invisible row | Argued in the text |
| §9E MC-18 | 28 → 36 cells; new operations are endpoints | 9 operations × 4 roles = 36; `GET /api/v1/stock-report/consistency` and `POST /api/v1/stock-report/repair` are named in §12A | **passes unchanged** |
| §12A repair | Per-kind table total? | Total: 6 kinds (3 counter columns) = the check's 8 probe kinds | — |
| §12A | `priority_order_nullness` vs MC-7 | Consistent (append `max + 1`, then renumber). **Not decidable:** the record's `target_kind` when both repairs touch one row, how null and bool become text (`str(True)` = `"True"` ≠ `bool::text`), and the `trigger` vocabulary | Kind mapping, one record per `(entity, field)` per operation, text rules, closed `trigger` set |
| §12A | Lock order, advisory first | Order consistent with MC-1, but "the tasks whose flag diverges" must be known before the check runs under the locks (circular) | Unlocked pre-pass. Correctness does not depend on task locks (the row locks freeze the flag's input); a missed task costs at most a deadlock abort, never a wrong value |
| §12A | Events per MC-19; authorship per MC-17 | "Rows it changes get `updated_*`" contradicted MC-17's "any counter move stamps nothing", and "rows" was ambiguous | `stock_report_items` rows only (renumbered included); tasks and history never; ledgered C41. `goal_total`/`task_flag` emit nothing |
| §12A | "Clean workspace = zero statements" | The MC-9 listener's table set omitted `stock_report_repair_records`, so a spurious record would go uncounted | Table set includes it |
| §12A | Instrument (e) | Correct in intent, but had no proof it bites, and could be satisfied by calling half of it | One shared helper. Planted probe: a double decrement self-heals, so the check stays `[]` and only the repair-record assertion reddens |
| §12A | Reset phase order | Correct, but "`delete_users`" is not the function name, and the position was loose | First four phases, before `delete_task_events`; the real users-phase name; FK order explained |
| §14D D6 | vs MC-4, MC-6, MC-9 | **Contradiction with MC-9** (C42). D6's listed order (existing first, then insert) also admits a three-transaction deadlock | Statement plan (§8B): set_config → workspace → categories (one) → discovery (unlocked) → INSERT absent only → one sorted `FOR UPDATE` → bulk UPDATE changed only → bulk goal INSERT → deadline. The count criterion counts `SELECT`s too (a write-only count cannot see a per-entry `SELECT` loop), ≤ 8, equal per shape for 3 and 300 entries. Processed grouping = `move_assignment` in grouped form, with the summed delta in the repair rule |

## 2. Evidence (charter rule 17: the dependency-owned shapes)

Reproduced 2026-09-19 at our boundary with the installed SQLAlchemy 2.0.40 / asyncpg 0.30.0,
against a local Postgres (**17.9 Homebrew on `localhost:5432`**; the project's docker compose
runs 18). Only `SELECT`s, no tables touched. Script:
`<scratchpad>/timeout_probe.py` (session scratchpad, outside the repo).

| Hypothesis | Result |
|---|---|
| `text("SET LOCAL statement_timeout = :v")` | `sqlalchemy.exc.ProgrammingError`, SQLSTATE 42601 |
| `SELECT set_config('statement_timeout', :v, true), …` in a transaction | returns `('200ms','200ms')`; `SHOW` inside = 200ms |
| statement timeout fires | `sqlalchemy.exc.DBAPIError`, `.orig` = adapter `Error`, sqlstate 57014 |
| next transaction, same pooled connection (`pool_size=1`) | `SHOW` = `0` / `0` (no leak) |
| lock wait, equal limits | 57014 (statement timer first) |
| lock wait, `lock_timeout` < `statement_timeout` | 55P03 |
| two 250 ms statements, 300 ms limit | committed after 0.51 s (per statement) |

The mapping is confirmed in source: `sqlalchemy/dialects/postgresql/asyncpg.py:_asyncpg_error_translate`
(`PostgresError → Error`; `QueryCanceledError` and `LockNotAvailableError` have no closer entry).

Node: `<scratchpad>/abort_probe.mjs`, Node 22.22.3 (Scanner's Node version not pinned in the repo;
no `.nvmrc` or `engines` found): `fetch` with `AbortSignal.timeout` rejects with
`{name: "TimeoutError", message: "The operation was aborted due to timeout"}`, and
`isRetryableError`'s substring list does not match it.

## 3. Absence claims (charter rule 15)

| Claim | Search | Scope | Result, and proof it can observe |
|---|---|---|---|
| `find_or_create_item` has two callers | `find_or_create_item` | `app/beyo_manager/**/*.py`, excl. `app/tests/**` | `routers/api_v1/items.py:233`, `tasks/create_task.py:259` (plus the definition and request parser); positives observed |
| `create_task` has one caller | `create_task(` and the import | same | `routers/api_v1/tasks.py:343`; other hits are `asyncio.create_task` |
| No third writer of an existing item's category | `item_category_id\s*=[^=]`; `update\(\s*Item\b\|UPDATE items`; `setattr(` in `commands/items` | same | 2 item writes (`update_item.py:74`, `find_or_create_item.py:103`), observed; the rest are other models' constructors or queries. 0 bulk forms. `setattr` loops iterate `_DIRECT_FIELDS`, which exclude the category |
| `hashtext(workspace_id)` advisory key has one taker | `pg_advisory_xact_lock` | same | `create_task.py:99`; `create_case.py:72` uses another key |
| No commit or dispatch before the guard in `create_task` | `commit\|dispatch\|event_bus\|begin_nested\|enqueue` | `tasks/note_writes.py`, `customers/find_or_create_customer.py` | none (only `maybe_begin`) |
| No Stock Report graph nodes | `archgraph_search_nodes("stock report")` | revision `fa1c510e…` (unchanged since round 6) | 0 |

## 4. Findings outside the perimeter (reported, not fixed)

| # | Finding | Evidence | Route |
|---|---|---|---|
| X1 | Scanner's outbound worker treats its own 8 s timeout as **non-retryable** and completes the job: the delivery is dropped, not retried | `outbound-webhook-worker.ts:14-25` (`message.includes("TimeoutError")` against a message that never contains it) + the Node probe | Sender note written into MC-9 for the closeout Scanner handoff (additive, no v2); the Scanner-side sender is a non-goal here, so it goes to whoever builds it |
| X2 | MC-10 locks "the row, then the assignment" **per entry, in request order**. With entries on different rows, that is not MC-1's "ascending within each class", so two processed requests can deadlock (loud: 500, and Scanner retries) | §8B MC-10 step 2 (round-6 text) | planner: sort the processed request's row locks ascending before per-entry decisions (fits the D6 grouping) |
| X3 | MC-8 step 4's `SELECT` and the processed webhook share the autobegin trap stated for demand | §8B | the MC-9 "one owning transaction" sentence is written for demand; the planner applies it to processed too |

## 5. For the implementation-planner (carry into its prompt)

- **D6 (owner requirement):** the demand webhook is set-based, with the statement plan in §8B
  ("D6 statement plan"). One criterion counts **every** statement (unfiltered listener): ≤ 8,
  equal for 3 and 300 entries of each shape. It includes the per-entry-`SELECT`-loop planted
  probe.
- Instrument rows to schedule: MC-1 (a)–(c); MC-9 rule-10 (i)–(iii); §12A (a)–(e) including the
  (e) double-decrement probe. Row (ii) of MC-9 sleeps past the default (~5 s): one test, budget it.
- X2 and X3.

## 6. Architecture graph

Oriented: `archgraph_status` (valid; 211 nodes / 327 edges; 14 pending reviews; revision
`fa1c510e…`) and a search for "stock report" (0 results). **Nothing recorded**, per the prompt.
No discrepancy newly found.

## 7. Write perimeter

From `git status --porcelain` after this session's writes (verified below):
- `docs/architecture/under_construction/implementation/stock_report/planning/intention.md`
  (modified: §5A MC-1 self-heal block; §5B MC-14 addition; §6A MC-5 addition; §8B MC-9 residual
  case rewritten + new "D6 statement plan"; §12A record fields, mechanics, (e), reset; §14C
  C41–C45; §18 re-check entry). Header and Status section **not** touched.
- `docs/architecture/under_construction/implementation/stock_report/handoffs/reviewer/2026-09-19_inventory_mechanism_inventory_recheck_handoff.md` (new, this file).
- `docs/archgraph-anchor-observations.md` (modified: one appended entry, the owner's standing log).
- Foreign, **not** this session's: `…/stock_report/codex_test.py`. It was ` M` at session start
  and is ` D` (deleted) at the end. This session never opened, edited or removed it, so another
  actor changed it mid-session. Verified: `git status --porcelain` at close shows exactly these
  four entries — the three above plus this foreign deletion.
- Tool-recorded state: none (no archgraph writes, no test runs, no writes to any repo database;
  the probes ran read-only `SELECT`s against the local `postgres` database).
- Scratch, outside the repo: `timeout_probe.py`, `abort_probe.mjs` in the session scratchpad.
- Not committed (prompt: "Do not commit").
