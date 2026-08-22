---
plan: 3
role: implementer
round: 1
date: 2026-08-21
project: test_isolation_and_xdist
---

# Session prompt — plan 3 implement r1, `test_isolation_and_xdist`

## 1. Role and workspace

You implement phase 3: **parallelism, and a baseline worth trusting.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Suite from `backend/app/`. Branch `feat/test-isolation-xdist`.

**Read first, by absolute path, as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**) and `/Users/davidloorenz/agent-skills/implementation-executor.md`.

**`plans/plan_3.md` is your task list. Where this prompt differs from it, the plan file wins.**

## 2. Gate check — stop and report if any is false

- `plans/plan_2.md` frontmatter reads `state: APPROVED` **and** carries a `gate_stamp:` line.
- `plans/plan_3.md` reads **`state: PROMPT_READY`** — the state a plan carries once its prompt is
  authored and awaiting a session (charter: `PROJECTED → PROMPT_READY → IMPLEMENTING`). Its §7
  carries the projection-r0 routing table. *(Corrected 2026-08-21: this line said `PROJECTED`,
  the state plan_3 held while this prompt was being written; flipping it to `PROMPT_READY` at
  dispatch invalidated the coordinator's own gate check, and an implement session correctly
  stopped on it. The gate protects "the projection is folded and this prompt is live", which
  holds.)*
- **Flip it to `IMPLEMENTING` when you start**, and to `IMPLEMENTED` at close (§9.4).
- `planning/intention.md` §4 contains **OD-8** and **OD-9**. Task 1 and task 5 are not executable
  without them.
- `pytest-xdist` is **not** installed and no `-n` appears in any pytest configuration. Installing
  it is task 2 — **after** task 1 has an answer.
- Architecture graph: 0 pending, 0 stale, 0 diagnostics.
- `git status --porcelain` clean.

## 3. Read order

1. `plans/plan_3.md` in full. §4 is the work in order, §5 is what you must prove, §5A is what has
   already cost someone a round, §6 is your budget, **§7's routing table tells you which
   amendments came from where** — read it, because several tasks were rewritten after the
   projection and the reasons matter.
2. `../master_plan.md` — **§6 is the environment authority.** Do not restate it in your handoff;
   cite it. §5's eight standing rules bind this session. §6.3a is new and constrains task 5.
3. `planning/intention.md` — §1 verbatim (the **correctness gate** list and the
   **mutation-testing consequence**), **OD-8** and **OD-9**, then OD-1/OD-3/OD-6.
4. `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md` — F1 (the three template paths),
   F2 (what `-n 2` will redden first), F3 (the table-count arithmetic). Its measurements are why
   the plan reads as it does.
5. `archive/plan_2/2026-08-21_phase2_review_r3_handoff.md` — S5, N3, N4.

## 4. Settled ground — cite it, do not re-derive it

Tree-bound and matching yours. Re-running any of it is over-evidence and a finding against the
round; **contradicting any of it is a finding worth reporting loudly.**

- **The serial baseline is `21 failed / 2561 passed / 1 deselected`** at `11b4d02`, clean —
  default and reversed, failing-ID sets `comm`-empty in both directions, enumerated in
  `archive/plan_2/2026-08-21_phase2_fix_r4_handoff.md`. This is task 1's comparator. `app/` at
  HEAD is identical to `11b4d02`; later commits are documentation only.
- **Two third-party plugins are registered today** — `pytest-asyncio-0.25.3` and `anyio-4.13.0`.
- **Connection budget** (master plan §6.3a): `max_connections = 100`, ~16 backends already in use,
  `DB_POOL_SIZE=20` + `DB_MAX_OVERFLOW=20` = a per-process ceiling of 40. **Three workers at full
  pool exhaust the server; `-n auto` is 14 workers.** Real usage sits well below the ceiling —
  which is why task 5 measures rather than assumes.
- **The schema-constant arithmetic**: `ScriptDirectory.from_config(...).get_heads()` →
  `['c1d2e3f4a5b6']`, exactly `EXPECTED_HEAD`. `len(Base.metadata.tables)` = **104**; the migrated
  template = **107**; the development database = **109**. The 107 is
  `104 + alembic_version + ended_shift_collapse_journal + item_valuation_migration_journal`, the
  last two kept out of ORM metadata by the convention documented at `migrations/env.py:20-31`.
- **All three template-contention paths reproduce serially**, in-process, with concurrent
  `DatabaseIsolation(...).start()` under `asyncio.gather`. C2 does not need `-n 4`.

## 5. Not optional — hazards this phase inherits

- **Master plan §5's eight standing rules bind this session.** Two will be tested directly:
  **rule 7** (a single-occurrence failing-ID difference triggers re-measurement, never
  attribution) governs task 1's own output as well as the matrix; **rule 8** — your closing stamp
  is defined by **the tree you hand over**. If you change anything after stamping, that stamp is
  void and re-taking it is **not** over-budget. Two previous rounds lost their stamp to the
  opposite reading.
- **The first `-n 2` run will redden the isolation criterion module**, at four sites that assert
  server-global database membership. **This is our assumption breaking, not the suite.** Task 8
  pre-authorises the worker-scoping repair. Treat it as a signal you were told to expect, not an
  obstacle and not a discovery.
- **Assert DDL, never a migration's exit code.** The documented Alembic trap exits 0 and persists
  nothing.
- **Do not let measurement convenience drive test design.** Phase 2 folded new criterion rows into
  existing tests to keep collection size constant; coverage survived but attribution did not — a
  URL-driver regression now reddens through a test named for unmarked databases. If adding rows
  perturbs the baseline, that is task 1's subject, not a reason to avoid adding rows.
- **A published handoff is never edited.** Corrections to earlier rounds' numbers go in *your*
  handoff.
- **Every probe database is declared and verified absent at close**; the configured development
  database is never a target (charter rule 7).
- **The intention forbids by name**: weakened assertions, retries, and `xfail`/`skip` applied to
  tests that parallelism exposes. If parallelism reveals a real race, report it; repair it only
  when the repair is clear and inside the test perimeter, and **raise an owner decision rather
  than improvising** if it needs a production-domain call.

## 6. Explicit delegations — yours to decide, on purpose

Granted in writing so the freedom is deliberate. Decide each once and state it with its reason.

1. **Task 1 — the positional axis** you probe (file-level, governed by path sort order under
   `testpaths = tests`, or within-file) and how you control position. Also **the harness's
   location**. Bounds: it must be **collection-neutral unless explicitly enabled** (the
   `BEYO_TEST_COLLECTION_ORDER` pattern is the precedent), and its enable mechanism must produce an
   **identical collection list in every worker** — xdist aborts when workers disagree, so nothing
   may key off process or worker identity.
2. **Task 1 — `n` and the probe positions.** Declared in the handoff **before the first run**;
   C1's union is only decidable if the probe set is fixed in advance.
3. **Task 2 — which manifest** gets `pytest-xdist`. Both `requirements.txt` and
   `requirements-dev.txt` pin `pytest==8.3.5` / `pytest-asyncio==0.25.3` today. Name the file, pin
   as its neighbours are pinned, say why that file.
4. **Task 3 — the contention strategy**: serialise, retry with backoff, or per-worker templates.
   Bound: whichever you choose, the protected region is **the whole of `_ensure_template` plus the
   copy**, not the `CREATE DATABASE` statement.
5. **Task 9 — legacy reclamation under workers**: exclude the sweep from non-controller workers,
   or document the command as serial-only in master plan §6.1. State which.
6. **N3 / C7** — implement the endpoint-normalisation criterion, or declare N3 documentation-only
   for this phase with a reason. If you declare it, **delete C7** rather than leaving a criterion
   unmet.

## 7. Evidence budget

**`n + 8` L4 runs**, the enumerated matrix in plan_3 §6 — rows 0 and 0b (noise floor and
harness-only control), the `n` probe runs, post-install serial, `-n 2`, `-n 4`, a higher count if
§6.3a's budget allows, the closing stamp at the chosen default, and a second run at that default
as C5's second condition.

**Declare `n` before the first run, and state the total as a number once `n` is fixed.** Anything
beyond the matrix needs the charter's authorization line, written before the run.

Probe runs happen on a dirty tree (the harness), so each evidence record carries **SHA plus a
`git diff` digest**, not SHA alone.

Everything else is L1/L2, including every named mutation at its own site.

## 8. Scope fences

- **Nothing under `app/beyo_manager/`.** The `config.py` carve-out is spent (OD-7). If you need it
  again, raise a decision card.
- **No production domain change**, no `pytest.ini` default `-n` — **OD-9 fixes the shipped default
  as serial** unless the parallel failing-ID set matches the serial comparator exactly. Report the
  whole matrix either way.
- **Task 1 finishes before `pytest-xdist` is installed.** OD-8 gives you the branch: a non-empty
  unstable set is enumerated, published as a separately-named list, excluded from the
  authoritative set, and **the phase continues**. You never repair that class here.
- **`migrations/versions/` is outside §3's perimeter.** C6's temporary revision is created and
  removed inside the test, applied only to a disposable database, and declared in your write
  perimeter. Never rewrite an applied migration.
- The three archgraph items are `human_confirmed` as of revision `f5bf3a7`. If this phase changes
  the isolation contract, record the delta **additively**; never promote, reject or edit.

## 9. Closing protocol

Per `implementation-executor.md`, with this project's specifics:

1. **The closing L4 stamp at the chosen default, on the tree you hand over**, with tree identity,
   the **enumerated** failing-ID set, and the delta in both directions against the post-install
   serial comparator.
2. **One evidence record per named mutation**, at the site the criterion names, stating which
   criterion rows reddened. Not probe *classes* — three rounds have reported classes and the
   information a reviewer needs is which row bit. A sub-check whose disabling reddens nothing is
   **a finding to report**, not a gap to fill silently.
3. **Document writes are yours except the tracker row**: master plan **§8** replaces its phase-3
   baseline row, **§6.3a** gains the measured `pg_stat_activity` peak, and **§6.1** gains task 9's
   disposition if you chose serial-only. The master plan §3 tracker row is the coordinator's.
4. `plans/plan_3.md` frontmatter → `state: IMPLEMENTED` with date, actor, counts. **This project's
   state lives in plan frontmatter**; there is no separate tracker file.
5. **Review-log entry** in `plans/plan_3.md` §7: what you built, every judgment call with its
   reason (including the six delegations above), deviations with justification, and the
   **per-class disposition table** task 4 owes — *reached / not reached / isolated / declared* for
   all eleven resource classes.
6. **The intention's named deliverables**: the before/after table (wall time, databases used,
   residue, failure count, failing-ID set, worker count) and the database lifecycle **as a
   diagram**.
7. **Handoff** at `handoffs/implementer/2026-08-21_phase3_implement_r1_handoff.md`, frontmatter
   `plan: 3` / `role: implement` / `state` / `date` / `actor`. Body: what was built, counts, the
   judgment calls, your **full write perimeter** (documents, code, tool-recorded state), **every
   file a mutation probe touched listed separately from your own changes** with checksums, every
   probe database and its verified disposition, and **your total L4 count as a number**.
8. Anything only the owner can settle goes in the handoff as a **decision card** in the charter's
   `⚠ OWNER DECISIONS REQUIRED (n)` section. If nothing needs the owner, one line saying so.

The handoff file, not your chat message, is what the coordinator consumes.
