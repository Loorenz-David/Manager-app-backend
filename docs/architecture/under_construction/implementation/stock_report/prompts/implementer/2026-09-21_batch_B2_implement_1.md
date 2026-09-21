---
plan: batch B2 — plans/plan_6.md, plans/plan_7.md (master_plan.md §3A)
role: implementer
round: batch_B2-implement-1
date: 2026-09-21
base: a2f4fc2
---

# Batch B2 implementation: phases 6 → 7 (`stock_report`)

You implement **two phases in one session**, in the order 6 → 7, and write **one batch handoff**.
Crossing the phase boundary returns control to no one: finish phase 6, run its evidence, commit a
checkpoint, continue to phase 7.

Plans 6 and 7 are the specification. This prompt frames the session and carries the orchestrator's
projection. **Where this prompt and a plan disagree, this prompt wins** — it was written after a
full projection of the shipped code and a re-measurement of every dependency claim, and the plans
were not. Where a plan and the intention disagree, the intention wins.

Batch A (phases 1–3) and batch B1 (phases 4–5) are **APPROVED**. You are building on both.

Paths are relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.
Run tests from `app/`.

## Gate check (stop and report `BLOCKED` if any line fails)

1. `SR/planning/intention.md` begins `status: RATIFIED`.
2. `SR/master_plan.md` §4A shows batch B2 `IMPLEMENTATION_PROMPT_READY`, B1 and A `APPROVED`.
3. `git status --porcelain` is empty.
4. `a2f4fc2` is an ancestor of HEAD.

**Dependency rule.** Plan 7 depends on phase 6, which **you** implement earlier in this session;
that is satisfied when phase 6's tests are green and its mutations have run. Do not wait.

## Read, in this order

1. Your `implementation-executor` doctrine and the pipeline charter.
2. `SR/master_plan.md` §5, §6.1, §6.5 (**amended three times since the plans were written**), §6.8,
   §9 (rule 16: never hand-type a state list), §10.
3. `SR/planning/intention.md` §4A MC-3, §8B MC-8/MC-9, §9D, §12A, §14C.
4. `SR/plans/plan_6.md` in full, then implement it. Then `SR/plans/plan_7.md`.

**Both plans were amended today** — 21 fixture and mutation cells were corrected because they
specified guards that could not fail, or predicted consequences the row cannot observe. Plan 6
carries a **Fold note** at the top of §6. Read it.

## 1. Five blockers — resolved. These override the plans.

**B5 (the one that would stop you dead) — every row in both plans is a committing test.**
`apply_stock_demand` asserts `not session.in_transaction()`, and the phase-1 kit's first `flush()`
autobegins on `db_session`. So the shape of **every** row is:

```
seed → await db_session.commit() → AD(...) → assertions
     → finally: await purge_stock_report_workspace(db_session, W); await db_session.commit()
```

Without this, every row raises `RuntimeError` before its first assertion. There is no rollback
safety net, so §9 rule 1 and charter rule 11½ bind on every row: scope to your own workspace,
assert no global totals, purge in `finally`.

**B3 — plan 6 C7(a) is unmeasurable with the shipped statement listener.** `record_statements`
yields statement **text only** and discards parameters; the compiled statement carries `$1`, not
the value. **Add `record_statement_calls(session)` to `app/tests/helpers/statement_listener.py`** —
an `asynccontextmanager` yielding `list[tuple[str, Any]]` of `(statement, parameters)` from the
same `before_cursor_execute` hook. **Leave `record_statements` and `count_writes` byte-identical**;
batch A has a live caller (`test_repair_stock_report.py`) that must not regress.
`app/tests/helpers/statement_listener.py` is therefore **added to phase 6's perimeter**.

**B4 — `StockDemandOutcomeEnum` was never shipped.** Master plan §6.1 claims all its enums shipped
in phase 1; measured, six names are missing and `enums.py` defines five enums plus two frozensets.
You need `StockDemandOutcomeEnum` for `DemandOutcome.outcome`. **`bm/domain/stock_report/enums.py`
is added to phase 6's perimeter, for that one enum only.** Do not add the other five missing names
— they belong to phases 9 and 13A, and charter rule 4 forbids shipping a constant with no caller.
Report this; I correct §6.1, not you.

**B6 — plan 7 C7(a)'s prescribed monkeypatch made its own outcome unreachable.** Already fixed in
the plan by the fold. Patch the **module reference** (`monkeypatch.setattr(apply_stock_demand,
"time", SimpleNamespace(monotonic=...))`), never `apply_stock_demand.time.monotonic`, which mutates
the shared `time` module including the asyncio event-loop clock.

**O1 — plan 6 C7(a)'s outcome says "its two parameters".** Measured: the statement plan 6 task 2
step 1 prescribes uses one bind name twice, which compiles to a single `$1` with **one** parameter.
An outcome cell is an acceptance criterion and I may not amend it, so: **bind two distinct
parameters** — `set_config('statement_timeout', :statement_timeout_ms, true),
set_config('lock_timeout', :lock_timeout_ms, true)`, both bound to `str(timeout_ms)`. The compiled
statement then carries `$1` and `$2` with `parameters == ('5000', '5000')`, the outcome is
satisfied word for word, and the row gains real content — it now pins that **both** limits are set.
Declare the choice in plan 6's Review log (charter rule 14).

## 2. Measured facts — do not re-derive, do not assume

The projection re-measured every dependency claim in plans 6 and 7 against the installed stack:
**PostgreSQL 18.6**, SQLAlchemy 2.0.40, asyncpg 0.30.0, Starlette 0.46.2, FastAPI 0.115.12,
CPython 3.13.2. **Record these versions in plans 6 and 7's Review logs** (plan 7 note 2 requires
it). Confirmed:

- Parameterized `set_config(..., true)` works and does not leak to the next transaction on the same
  pooled connection. `set_config` **returns `'5s'`, not `'5000'`** — assert on the bound parameter,
  never on the result or `SHOW`.
- Equal statement and lock limits on a lock wait → SQLSTATE **57014**, surfaced as
  `sqlalchemy.exc.DBAPIError` with `.orig` an adapter `Error`.
- `INSERT … ON CONFLICT (ws, cat, sig) WHERE is_deleted = false DO NOTHING RETURNING client_id`
  infers the **partial** index and returns only newly inserted rows.
- A waiting `SELECT … FOR UPDATE` re-evaluates its `WHERE` on the committed version and **drops** a
  row the locker soft-deleted.
- `dict(request.headers)` keys are lower-cased under `TestClient`.
- `hmac.compare_digest(str, str)` with non-ASCII raises `TypeError`.
- `json.loads(b"\xff\xfe")` raises **`JSONDecodeError`**, not `UnicodeDecodeError` — so a parser
  that skips the explicit decode still passes C2(a). Implement MC-8 step 5 as written
  (`raw.decode("utf-8")` in its own `try`) and catch **both**.
- `json.loads` keeps the last duplicate key; `json.loads("5.0")` → `float`; `type(True) is int` is
  False.

## 3. Hazards

**H14 — committing tests.** B5 above.

**H15 — `record_statements` listens on the *engine*, not the session.** Every statement of every
session on that engine lands in the list. Open the window **after** the seed commit, close it
before the purge, and in the two-session rows keep the holder session's writes outside it.

**H16 — the statement budget is exact, not slack.** All-new = 8, all-changed = 7, all-unchanged =
5. Any stray `SELECT` — a `session.get`, an autoflush, a lazy-load — breaks C6. Build the demand
path with Core statements only and no ORM loads.

**H17 — step 6 must re-discover client_ids by *identity*, never reuse the ids generated for step
5's VALUES.** `ON CONFLICT DO NOTHING` returns nothing for a conflicting row, so the locally
generated ULID for that identity is not the row's id. Locking by identity is also what keeps two
concurrent requests on one lock order.

**H19 — patch the module reference, never the shared `time` module.** B6 above.

**H21 — `uq_item_categories_workspace_name` is a plain UNIQUE on `(workspace_id, name)`**,
case-sensitive, **not** partial on `is_deleted`. So "Dining Chairs" and "dining chairs" can coexist
in one workspace, and a soft-deleted category still holds its name.

**H22 — two routers share the `/api/v1/location-tracker` prefix.** The existing
`location_tracker.router` exposes `/items/location` only; nothing collides with
`/webhooks/stock-demand`. Add the new mount, do not move the old one.
`bm/services/infra/location_tracker/` **already exists** — add only `webhook_verifier.py`.

**H23 — `bm/errors/stock_report.py` does not exist**; phase 6 creates it. Bases: `DomainError`
(`http_status = 500`), `ValidationError`, `ConflictError`.

**H24 — the envelope is exact.** `build_ok(data)` → `{"data": …, "ok": true, "warnings": []}`;
`build_err(error)` → `{"error": error.message, "ok": false}` with `status_code =
error.http_status`. `run_service` turns a `DomainError` into `StatusOutcome(success=False,
error=exc)` and anything else into a generic 500.

**H25 — C7(b) is the only sleeping test and it commits.** ~8 s, its own file
(`test_apply_stock_demand_timing.py`), excluded from L1 loops **by file, never by `-k`**. The
holder must hold for `default + 3000 ms` so the statement timer fires first.

**H13 — never run `alembic upgrade`/`downgrade` against the dev database, and add no revision.**
Phases 6 and 7 need no schema change; verified.

**Lock and transaction shape.** `apply_stock_demand` is **owner mode**: one `maybe_begin`, refuses a
pre-open transaction, locks `stock_report_items` only, one sorted `FOR UPDATE ORDER BY client_id`,
**no advisory lock** (demand is not an ordering operation). `receive_stock_demand_webhook` opens
nothing — the command owns the transaction — and computes the deadline on its **first line**, so
the budget covers verify and parse too.

## 4. Routed debt landing here

**The deleted `Settings` coverage.** Batch A's fix round deleted `test_settings.py` (an orphan that
caused a basename collision), taking the only coverage of the three new settings with it. Plan 6
C7(a) reads the timeout default from the class and restores part of it; plan 7 C1(a)–(c) cover the
two `str | None` settings. **Confirm the restoration in your handoff.** Do **not** rename
`app/tests/helpers/test_settings.py` — it is a test-named helper module outside your perimeter.

## 5. Mutation discipline

**Standing rule:** every named mutation is applied at the **definition site** of the function named
in the plan's task section unless the cell says otherwise. Record file and site in the ledger.

- Run **every** named mutation, revert each, and report `executed == declared` **derived
  mechanically from the plan cells and your own run table — never typed.** Publish the mapping:
  which plan cell → which table row. If a number disagrees with the table, the table wins. Batch
  B1 lost a round to exactly this.
- Cells marked `—` are not run; several now say which row carries the real bite.
- Some cells are **enumerated** (i)/(ii) — run each and record which reddened which sub-check.
- Some name an **equivalent mutant** and say which row carries the bite. Record as equivalent; do
  not run.
- **A mutation that reddens nothing is a finding, not a nuisance.** Report it. Do not adjust the
  test to make it bite, and do not skip it silently. If you decline a probe on caution grounds,
  say so explicitly — that is a legitimate outcome, and the reviewer will close it.

## 6. Evidence

- **L1 per test file as it lands**, whole file, never `-k`. Exclude `test_apply_stock_demand_timing.py`
  from L1 loops by file (H25).
- **Per phase, before moving on:** that phase's L1 files green and every named mutation run.
- **Do not** run L4 at the phase-6 boundary.
- **Batch end, once:** L2 over the batch's folders, and **one L4**
  (`PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`) diffed **both ways** against the 21-ID
  baseline (§10; list in
  `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3).
  The current stamp is **21 failed / 3349 passed / 2 skipped**.
  **Known drifter:** `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`
  fails between 00:00 and ~03:00 UTC because it computes `datetime.now(timezone.utc)` minus three
  hours. It is outside this perimeter and proven independent. If it appears, record it as the known
  drifter with the UTC time of your run; it is not yours to fix.
- **Record the tree SHA each stamp ran on.**
- **Outcomes, not internals** (charter rule 2): assert input → outcome at a public boundary. Where a
  row itself names a statement-level instrument, implement it as written; add such assertions
  nowhere else.

## 7. Git

Commit a checkpoint at the end of each phase: `CHECKPOINT (not approved): stock_report phase <n> —
<one line>`, perimeter paths only (`git add <paths>`, then `git commit -m "…" -- <paths>`). Never
`add -A`, `add .` or `commit -a`. Never push, amend, rebase or reset. No tracker row.

## 8. Do not touch

The intention; the master plan (report signature and §6.1 corrections to me); the Scanner
repository or its handoffs; plans other than 6 and 7, and those only by appending one **Review
log** entry each; other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`; batch
A's and B1's shipped code except the two perimeter additions §1 B3 and B4 authorize; the 21
baseline failures; `app/tests/helpers/test_settings.py`. No graph write. No Alembic revision.

## 9. If you get stuck

Unattended run, owner asleep, orchestrator active. Never weaken a criterion, a helper or an
assertion to get past something; never delete a failing test; never invent a criterion row. A
partial batch with an honest, precise blocker report is a good outcome — a complete-looking batch
with a quietly weakened instrument is the worst one. If a plan row turns out to be unachievable,
implement the contract, leave the row failing, and say exactly why.

## 10. Handoff

`SR/handoffs/implementer/2026-09-21_batch_B2_implement_1_handoff.md`. Frontmatter: `plan: batch B2
(6, 7)`, `role: implement`, `round: batch_B2-implement-1`, `state`, `date`, `actor`, `tree`.
Sections:

1. Gate check record.
2. **Phase 6**, then **Phase 7**, each with: the Task 0 coverage map (one line per criterion row →
   test id → whether the assertion has the row's shape); test files and L1 results; the
   named-mutation ledger **with its derivation** (plan cell → table row), sites, and the red test
   id per mutation; judgment calls and deviations.
3. **The perimeter additions** (B3's `record_statement_calls`, B4's enum) and the **O1 decision**,
   each with its final signature or statement text, for master plan §6.1/§6.5.
4. **The measured dependency versions**, confirmed into both Review logs.
5. **Settings-coverage restoration** confirmation.
6. **Batch level:** cross-phase integration, contract compliance against §5, L2 and L4 stamps with
   tree SHAs and the two-way baseline diff (noting the known drifter and your run's UTC time),
   commits, blockers.
7. **Write perimeter**, checked against `git status --porcelain` and `git diff --stat a2f4fc2..`,
   listing every file a probe touched (applied, reverted, byte-identical).
8. `⚠ OWNER DECISIONS REQUIRED (n)` or `(0)`.

First line of your final message: `HANDOFF: … | STATE: … | OWNER_CARDS: n`, then a short summary
and the most important thing I should know.
