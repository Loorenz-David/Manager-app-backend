---
plan: batch A — plans/plan_1.md, plans/plan_2.md, plans/plan_3.md (master_plan.md §3A)
role: implementer (Codex)
round: batch_A-implement-1
date: 2026-09-19
skill: implementation-executor (`/Users/davidloorenz/agent-skills/implementation-executor.md`, via the pipeline charter)
model: gpt-5.6-terra, reasoning effort medium (phase 3 is complex)
---

# Batch A implementation: phases 1 → 2 → 3 (`stock_report`)

You implement **three phases in one session**, in the order 1 → 2 → 3, and write **one batch
handoff**. Crossing a phase boundary does not return control to anyone and triggers no review: you
finish a phase, run its local evidence, optionally commit a checkpoint, and continue. The three
phase plans are the specification. This prompt only frames the session. Where it differs from a
plan file, the plan file wins, **except** for the batch rules below, which come from the master
plan's §3A and are the owner's.

Paths are relative to the repo root `backend/` (`git rev-parse --show-toplevel`). `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.

## Gate check (stop and report `BLOCKED` if any line fails)

1. `SR/planning/intention.md` header begins `status: RATIFIED` (round 9).
2. `SR/master_plan.md` §4A shows batch A `IMPLEMENTATION_PROMPT_READY` (or `IMPLEMENTING`) and no
   predecessor batch (A has none).
3. `git status --porcelain` is empty at start. If it is not, list what you see in your handoff
   and stop, unless every entry is outside `app/` and outside `SR/plans/`. In that case, record
   them as foreign and continue.
4. `cd app && .venv/bin/python -c "from alembic.script import ScriptDirectory; from alembic.config import Config; print(ScriptDirectory.from_config(Config('alembic.ini')).get_heads())"`
   prints exactly `['ce99896e6f49']`.

**How to read the plans' dependency lines inside this batch** (master plan §3A): plan 2's and plan
3's `depends_on: 1 (APPROVED)` is satisfied when **you** have implemented phase 1 earlier in this
session, with its L1 tests green and its named mutations run. Your doctrine's "predecessors
APPROVED" check reads §4A, not per-phase rows. The plans' `projection: mandatory` lines were
satisfied by the orchestrator's batch projection. Its notes are below, and they are part of your
task.

## Read, in this order

1. The pipeline charter and your `implementation-executor` doctrine.
2. `SR/master_plan.md`: **§3A (the batch model, which governs this session)**, §5, §6 (naming
   registry; everything you create is named there), §8, §9 (standing rules; rule 16: never spell a
   state list), and §10 (commands, L1–L4, the baseline, known hazards).
3. For each phase in turn, its plan file in full: its Read-first list, then its tasks and criteria.
   Read a phase's Read-first sources when you reach that phase, not all at the start.

## Batch projection notes (the orchestrator's, from reading plans 1–3; treat as tasks)

1. **Migration safety (plan 1 task 3).** `alembic revision --autogenerate` compares against the
   dev database from `app/.env`. That is a read-only use and is allowed. **Never run `alembic
   upgrade` or `downgrade` against the dev database `beyo_manager`.** The test template rebuilds
   itself at the new head (`tests/database_isolation.py`). If you want to exercise `downgrade()`,
   do it on a scratch database you create and drop yourself, and say so. Autogenerate is known to
   drop `postgresql_where` predicates and CHECK constraints: open the revision and compare it to
   master plan §6.2 line by line. Plan 1 C2(a) is the parity check.
2. **`tasks.is_stock_assignment` needs `server_default`** (master plan §10 hazard (a), plan 1
   C2(h)). Without it every raw-SQL task insert in the suite breaks, and the L4 diff will show it.
3. **Rule-17 facts for plan 2 (Scanner-owned shapes).** Scanner's source is read-only at
   `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify`. Its HEAD is the cited
   commit `0d80bf2`. An untracked docs folder there is not yours, so ignore it.
   - The hand-walk's criteria literals (C6, inventory handoff §3) were **not** read from Scanner's
     database (planner note N7). Before you transcribe C6, run every H-row's criteria through
     Scanner's own `normalizeCriteria` (`apps/backend/src/modules/stock/domain/property-criteria.ts`).
     `apps/backend/node_modules/.bin/tsx` exists, so use a scratch script under `/tmp`, never inside
     either repository. Record each input → output in the handoff. If an output differs from the
     hand-walk's literal, use Scanner's output as the fixture (that is what Manager will store). If
     the verdict then differs from the hand-walk's verdict, **do not change the expected verdict**:
     mark that row not discharged, explain it in the handoff, and continue with the rest.
   - Confirm `String(4.0) === "4"` and the compact `JSON.stringify` separators with one `node -e`
     each (C1(e), C1(h), C1(i)), and record the output.
   - C2(e)'s duplicate-key tie-break is a Manager-only rule (Scanner trims keys at ingestion), so
     there is nothing in Scanner to mirror. Implement it as the plan states.
4. **Plan 3 C2(a) was re-stated by an owner ruling (2026-09-19).** It asserts the data is
   unchanged, meaning every row of the four tables and `stock_report_repair_records` in W is equal
   before and after the check. It does not count writes. `record_statements` / `count_writes` are
   still required, because C5(a) uses them (§12A (d): zero statements when nothing diverges).
5. **Plan 3 C6(a) hazard:** do the nullness step before the density renumber, and write repair
   records from a before/after diff per `(row, field)`, never per step. The repair's task-lock
   pre-pass and the "≠ 1 row is a programming error" rule are not criterion rows. Implement them as
   §12A says, and name where they are in the handoff so the reviewer can check them structurally.
6. **Cross-phase within the batch:** phase 3 extends the test kit phase 1 creates
   (`app/tests/helpers/stock_report.py`, adding `assert_stock_report_clean`). Re-run phase 1's
   kit-using tests after the phase 3 edit. Every kit function must have a caller in its phase
   (charter rule 4).
7. **Test-database rule (measured 2026-09-19):** within a run, about 819 rows from 23 other test
   files stay behind in each worker database. Every test creates its own workspace through the
   kit, scopes every assertion to it, and asserts no global total. A test whose code commits
   purges its workspace in `finally`. Plan 1 C3(a) (`reset_app`) and plan 3 C1(k) keep a foreign
   workspace on purpose, so purge both.
8. **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19). Tests assert the input →
   outcome each row states: a return value, persisted state, an event, or an HTTP answer. Where a
   plan row itself names a statement-level instrument (plan 3 C5(a)), implement it as written. Do
   not add such assertions anywhere else.

## Evidence budget (charter L1–L4; master plan §10 commands, run from `app/`)

- **As each test file lands:** L1, the whole file (never `-k`).
- **Per phase, before moving on:** that phase's L1 files green, and **every named mutation in its
  criteria table run and reverted**, at the scope the row needs. Report `executed == declared` per
  phase, with the per-criterion summands, the site of each mutation, and the observed failing test
  id and assertion. Rows the plan marks `—` or "cannot isolate" (plan 1 C4(f)) are recorded as
  such, not run.
- **Do not** run L3 or L4 at the phase-1 or phase-2 boundary. The next phase extends the same code.
- **Batch end, once:**
  - **L2**: every test folder the batch created, plus
    `tests/integration/services/commands/reset`.
  - **One L4**: `PYTHONPATH=. pytest -m 'not e2e'`. Diff its failure-ID set **in both
    directions** against the 21-ID baseline (§10; the list is in
    `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3).
    Expected: exactly those 21 fail, nothing else; passed = 3103 + your new tests.
  - If an unexpected ID appears, capture the set, re-run that file at L1 once, and explain. The
    known load-dependent drifter is
    `test_c3_real_concurrent_open_insert_translates_the_loser[model]`.
  - Record the tree SHA each stamp ran on.

## Git

- You may make a checkpoint commit at the end of each phase: `CHECKPOINT (not approved): stock_report
  phase <n> — <one line>`. Make a final one at the batch end if anything is uncommitted.
  Each commit contains **only your perimeter's paths**: `git add <paths>`, then
  `git commit -m "…" -- <paths>`. Never use `add -A`, `add .` or `commit -a`. Never push, amend,
  rebase or reset. List every SHA in the handoff.
- **A checkpoint is not an approval.** Do not write any tracker row (§4, §4A): the orchestrator
  does that from your handoff.

## Architecture graph

Orient at start (`archgraph_status`, `archgraph_search_nodes("stock report")`). At the batch end,
record **one** batched `apply_changes` for the whole batch, per master plan §8. If the archgraph
tools are unavailable in your session, write the intended delta as a section of the handoff and
say so. That is not a blocker.

## Do not touch

The intention; the Scanner handoffs; any other plan's file (except appending to the **Review log**
of plans 1, 2 and 3, one entry each); master plan tracker rows; other roles' prompts or handoffs;
`docs/archgraph-anchor-observations.md`; the Scanner repository (read-only). No file outside the
three plans' "Files expected to change" lists, the kit, and the migration. If you need one, say why
in the handoff.

## Handoff

Write it to `SR/handoffs/implementer/2026-09-19_batch_A_implement_1_handoff.md`. The frontmatter is
`plan: batch A (1, 2, 3)`, `role: implement`, `round: batch_A-implement-1`, `state`, `date`,
`actor`. Structure:

1. **Gate check record** (the four lines, with their outputs).
2. **Phase 1**, then **Phase 2**, then **Phase 3**, each with:
   - the Task 0 coverage map: one line per criterion row → test id → whether the assertion has the
     shape the row specifies;
   - test files and L1 results;
   - the named-mutation ledger (`executed == declared`, with summands);
   - judgment calls and deviations with reasons;
   - for phase 1: the migration's hand edits;
   - for phase 2: the Scanner normalization and `node` outputs from projection note 3.
3. **Batch level:**
   - cross-phase integration evidence (the kit after phase 3, the reset test after the new tables);
   - contract compliance against master plan §5;
   - the L2 and L4 stamps with SHAs and the two-way baseline diff;
   - the commits;
   - the graph delta (or its text);
   - blockers and limitations.
4. **Write perimeter:** every path you created or changed, checked against `git status --porcelain`
   and `git diff --stat` since the batch start commit. List separately every file a mutation probe
   touched (applied and reverted, confirmed byte-identical) and any scratch files outside the repo.
5. `⚠ OWNER DECISIONS REQUIRED (n)` in the charter's card format, or `(0)`.

Your final message's first line is the `HANDOFF: … | STATE: … | OWNER_CARDS: n` line, followed by
the owner layer.
