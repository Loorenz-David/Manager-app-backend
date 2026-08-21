---
plan: 1
role: implementer
round: 1
date: 2026-08-21
project: test_isolation_and_xdist
---

# Session prompt — plan 1 implement (round 1), `test_isolation_and_xdist`

## 1. Role and workspace

You implement **phase 1 only**: per-worker PostgreSQL database isolation, proven **serially**.
`plans/plan_1.md` is your task list and acceptance criteria. Where this prompt and the plan
differ, **the plan file wins**.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (suite: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/test_isolation_and_xdist/`

**Read these two files first and follow them as doctrine** (absolute paths):
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — including **"Test-evidence scope
   and reuse"**, which governs §5 below.
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## 2. ⛔ The one scope fence that matters

**Do not install `pytest-xdist`. Do not add `-n`. Do not run anything in parallel.**

That is phase 2, and the owner made the ordering a hard constraint: *"Do not simply install
pytest-xdist, add `-n auto`, and declare the work complete."* Isolation is proven serially
first, because a parallel run on unproven isolation produces nondeterministic failures that
poison the very measurements parallelism is being bought for.

Your code should be **written so a worker id selects the database** (so phase 2 is a
configuration change, not a rewrite), but this phase runs single-process only, where the
worker id resolves to `main`.

## 3. Read order

1. `planning/intention.md` — **§1 is the owner's intention verbatim; §2 is a measured
   inspection that has already discharged the intention's "inspect first" step.** Do not
   re-derive §2's facts; they were verified at source and by execution today. Do challenge them
   if the tree disagrees — that is a finding.
2. `plans/plan_1.md` in full — §5 criteria C1–C8, §5A the inherited traps, §6 notes.
3. Source: `app/tests/conftest.py`, `app/beyo_manager/models/database.py`,
   `app/beyo_manager/config.py`, `app/migrations/env.py`, `app/pytest.ini`.

## 4. What is already established — cite it, do not re-derive it

- **The seam is `settings.database_url`.** `init_db()` reads it at call time, and
  `tests/conftest.py:initialize_database` is **autouse with function scope**, so it is re-read
  for *every test*. Overriding it once per process redirects the whole suite with no per-test
  patching. That is where the isolation belongs.
- **Provisioning is cheap — measured today**: `alembic upgrade head` onto an empty database
  (118 revisions) ≈ **1.0 s**; `CREATE DATABASE … TEMPLATE …` ≈ **0.11 s**; `DROP DATABASE`
  ≈ **0.11 s**; a template copy carries all **107** tables. Against a 135 s suite, four worker
  databases cost under half a second. **The owner's worry that recreating schemas would eat the
  gain is empirically false at this scale** — you do not need to trade cleanliness for speed.
- **Residue is exactly "rows committed by tests that commit"** — `db_session` rolls back *after*
  the test, which is a no-op once a test has committed. A fresh per-run database makes the whole
  class harmless. **Do not repair individual tests.**
- **Head is `c1d2e3f4a5b6`, 107 tables.** The dev database is `…@localhost:5433/beyo_manager`.
  `app/.env.testing` points somewhere else entirely (`…@127.0.0.1:5432/app_test`) and is stale
  at `67cfba8fcb2d` with 96 tables — **do not adopt it as the test database**; it is evidence of
  how this drifts, not a target.
- **The dev server holds exactly three databases**: `beyo_manager`,
  `housing_parser_plan1_20260807`, `postgres`. Anything outside a strict test-name pattern is
  someone's real data.
- **Current baseline: `26 failed / 2515 passed / 1 deselected`**, failure-ID set = the 26
  enumerated in `live_clock_for_working_time_economics/master_plan.md` §6, on a clean tree.

## 5. Testing — scope per hypothesis

The charter's test-evidence section governs; `plans/plan_1.md` assigns scopes.

- C1–C5, C8 are **L1/L2** questions ("does this named row redden under this named mutation").
  Run them at that scope; the inner loop should cost seconds.
- **C7 is L4 by construction** — it is baseline re-enumeration over the whole suite, an explicit
  L4 trigger. Run the full suite serially and `comm`-diff the failing-ID set in **both
  directions** against the enumerated 26.
- **One authoritative L4 stamp at the close of this cycle**, tree identity recorded.
- Every evidence record: hypothesis · scope · exact command · tree identity (SHA + clean
  `git status --porcelain`; if dirty, add a `git diff` digest) · result · ID delta both
  directions. Where a plan divides labour between two rows, **state which row did *not* bite**.
- Run **every named mutation** the plan names, at its named site, before submitting; revert each
  and verify the revert.

## 6. Hazards — each already cost someone a round

1. **Never accept a migration's exit code as evidence — assert the DDL.** This repo has a
   documented trap where `alembic upgrade` logs success, exits 0, and persists nothing. During
   inspection it exited 0 in ~1 s, which is exactly what the trap looks like; only counting 107
   tables told them apart. C3's named mutation exists to keep that alive.
2. **Build the guard before anything can drop a database** (task 1). C2 must exist and pass
   first. A safety invariant written after the destructive code is a safety invariant that has
   never been tested against the code it guards.
3. **Fail closed, never guess.** A malformed or missing `DATABASE_URL` aborts the run. It never
   falls back to a default, and never "helpfully" picks a database.
4. **`count_queries` in `conftest.py` is dead and broken** — a session-scoped fixture capturing
   an engine that `close_db()` disposes after every test. Two tests carry local replacements and
   say so. You will be editing that file: **report it as a finding; do not delete it silently.**
5. **Do not widen `initialize_database`'s fixture scope as an optimisation.** It looks like free
   speed (~2515 engine create/dispose cycles) but fixture scope *is* isolation semantics here.
   Measure, report, leave it to phase 2 or a decision card.
6. **Do not touch production domain code.** If isolation appears to require it, stop and raise a
   decision card rather than improvising.

## 7. Closing protocol

1. The cycle's one L4 stamp: full suite serially + linters, tree identity and both-direction ID
   delta recorded.
2. Every named mutation run at its site, recorded as a full evidence record, reverted, revert
   verified.
3. **Handoff** at `handoffs/implementer/2026-08-21_phase1_implement_r1_handoff.md` with the
   charter row schema, declaring your **full write perimeter** (documents, code, tool-recorded
   state) and every file a mutation probe touched, listed separately.

   The owner asked for specific deliverables; phase 1 owes these of the fifteen:
   **(1)** infrastructure discovered — confirm or correct intention §2; **(2)** the isolation
   design as built and why; **(3)** exact files changed; **(4)** the database safety invariant,
   stated precisely; **(5)** the database lifecycle **as a diagram**; **(6)** the serial-suite
   result; **(9)** residue measurements before/after; **(11)** any difference from the previous
   failure-ID set, **each one explained**; **(15)** remaining risks. Deliverables 7, 8, 10,
   12–14 belong to phase 2 — say so rather than guessing at them.

   Any question only the owner can settle goes in an `⚠ OWNER DECISIONS REQUIRED` section as a
   decision card; one line if there are none.
4. Review log entry in `plans/plan_1.md`; tracker row is not used in this project (no master
   plan) — the Review log is the record.
5. Checkpoint commit, subject prefixed `CHECKPOINT (not approved):`.

**A closing note on why this phase is worth its care.** Every measurement this organisation
makes — every mutation bite, every approval baseline, every "the suite is green" — is taken
through the instrument you are building. If isolation is subtly wrong, nothing downstream is
trustworthy and nothing will announce it. That is why the guard comes first and why the
failure-ID set must be *explained* rather than updated.
