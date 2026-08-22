---
plan: 2
role: implementer
round: 1
date: 2026-08-21
project: test_isolation_and_xdist
---

# Session prompt — plan 2 implement r1, `test_isolation_and_xdist`

## 1. Role and workspace

You implement phase 2: **order-independence and per-checkout isolation, still serial.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Suite runs from `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`
Branch: `feat/test-isolation-xdist`

**Read first, by absolute path, and follow as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**) and `/Users/davidloorenz/agent-skills/implementation-executor.md`.

**`plans/plan_2.md` is your task list. Where this prompt differs from it, the plan file wins.**

## 2. Gate check — stop and report if any is false

- `plans/plan_1.md` frontmatter reads `state: APPROVED`.
- `plans/plan_2.md` frontmatter reads `state: PROJECTED`, and its §7 carries the projection-r0
  routing table with sixteen rows.
- `planning/intention.md` §4 contains **OD-6** (the repair contract). Task 1 is not
  implementable without it.
- `pytest-xdist` is **not** installed and no `-n` flag appears anywhere in the repository.
- `git status --porcelain` is clean.

## 3. Read order

1. `plans/plan_2.md` — in full. §4 is the work, §5 is what you must prove, §5A is what has
   already cost someone a round.
2. `planning/intention.md` — **OD-6 first** (the repair contract, and the only authority on
   it), then §2.2, §2.3, §5, OD-1, OD-3, OD-5.
3. `plans/plan_1.md` §5A, and its Review log's **fix-r4 consumption entry** — the carry-forwards
   this phase inherits, and the `d8bda2c` stamp you will cite.
4. `handoffs/reviewer/2026-08-21_phase2_projection_r0_handoff.md` §4 — the measurements behind
   most of the plan's amendments, with exact lines. **Its Appendix A is non-authoritative and
   must not be read as guidance.**
5. Source: `app/tests/database_isolation.py`, `app/tests/conftest.py`,
   `app/tests/fixtures/phase1_reference_data.py`,
   `app/beyo_manager/services/infra/redis/keys.py`.

## 4. Settled ground — cite it, do not re-derive it

These are tree-bound and match your tree. Re-running them is over-evidence and a finding
against the round; **contradicting one is a finding worth reporting loudly.**

- **The default-order baseline is `22 failed / 2541 passed / 1 deselected in 107.51 s`** at
  `d8bda2c`, failing-ID set byte-identical to the published 22. `app/` at `d8bda2c` is
  identical to `app/` at HEAD (`5ecfe90` changed documents only), so this stamp covers your
  starting tree. It is C2's default-order before-side.
- **The reversed-order figure `139 / 2422 / 1` (`added = 118, removed = 1`)** was measured at
  `87a4b7a`. It is a **description of the class**, not a stamp on your tree. No tree-matching
  equivalent exists and none is owed.
- **`Role.name` is globally unique** (`role.py:17-21`); `Workspace.name` is not
  (`workspace.py:14`); `PauseReason` is unique on `(workspace_id, slug)`
  (`pause_reason.py:60`). This is why OD-6 splits the classes.
- **OD-6's composition is measured sufficient on the worst file.** Create-your-own
  `Workspace` + adopt-or-create `Role`, applied to the single helper `_seed_workspace_worker`
  (`test_worker_shift_commands.py:78-89`), takes that file from `41 failed / 1 passed` to
  **`42 passed in 4.48 s`** run alone. Ten lines, one helper; the file's other three
  `scalar_one()` sites needed no change. You are applying a measured repair to ten more files.
- **The twelfth file passes alone today** (`1 passed in 0.61 s`) and fails only in company
  (`1 failed, 1 passed`, `UniqueViolationError` on `ix_roles_name`). Its evidence is the paired
  run, never the alone run.
- **Hook order is measured:** session-fixture teardown runs **before** `pytest_sessionfinish`.
  This is why C7(b) lives in `isolated_database`'s teardown and not in a hook.
- **No collection/session hooks exist anywhere under `app/`** — task 6 creates the first one.
- Redis key builders read `settings.redis_key_prefix` **at call time**, so overriding the
  attribute works for the same reason the database override works.

## 5. Not optional — hazards this phase inherits

Each already cost this project or its sibling a round.

- **Assert DDL, never a migration's exit code.** The documented trap makes `alembic upgrade`
  log success, exit 0, and persist nothing.
- **Compute both sides of every fixture before choosing it.** A fixture whose expected value
  is identical under the contract and under the mutation proves nothing. This project has
  recorded **fourteen** instances of that class; three were caught in this plan's own criteria
  last round, on paper.
- **Both refuted hypotheses stay refuted.** Seeding a shared catalog does not fix the order
  class — it moves the error to `AttributeError`. And strict create-your-own collides on
  `Role`. OD-6 is the contract.
- **Three tasks converge on `assert_disposable_database`.** Change its signature once,
  deliberately, and declare the new signature in your handoff.
- **`localhost` vs `127.0.0.1` will stop the suite if you compare hosts naively.** `.env:7`
  says `localhost`; every connection normalises to `127.0.0.1`
  (`database_isolation.py:79,107,296`). Normalise both sides.
- **Never `except Exception` around the guard.** That is how the original B2 swallowed its own
  refusal. Task 4 catches `asyncpg.exceptions.UndefinedTableError` and nothing wider.
- **The eleven files currently pass.** You are repairing green tests, so a careless repair
  reads as success in default order and is caught only by the reversal.
- **A published handoff is never edited.** Corrections to numbers published in earlier rounds
  go in *your* handoff. Fix r4 rewrote r2's measurement and destroyed the provenance of a real
  error; the coordinator restored the file.
- **Probe databases are declared and verified absent at close**, and the configured
  development database is never a target (charter rule 7).

## 6. Explicit delegations — yours to decide, on purpose

Granted in writing so the freedom is deliberate rather than silent. Decide each once, state it
in the handoff with its reason.

1. **Task 1's shape:** (a) shared row factories in `app/tests/fixtures/` reused by all eleven
   files, or (b) per-file helper repair. The class is uniform, so either is comparable work.
   Bounds: **one strategy for all eleven** (a mixed repair makes C2's result unattributable);
   **no factory creates a globally-unique catalog row inside a test that commits**; factories
   create rows per test on demand and never seed a shared catalog (OD-1 stands); the twelfth
   file is repaired under task 1b, not this task.
2. **The slot environment variable's name.** Lowercase; declare it in the handoff and document
   it where an operator running a second worktree will find it.
3. **Whether the one-time legacy-name disposition (task 2) is permanent or removable later.**
   State which and why.
4. **Whether `isolated_redis_prefix` becomes autouse** or reaches the shipped default some
   other way. Charter rule 10 requires that it reach it; how is yours.

## 7. Evidence budget

**This session's L4 budget is exactly 3 runs.**

1. **One diagnostic reversal, pre-authorised** — take it mid-cycle when you judge the repair
   close to complete. No authorisation line is needed; this line is the authorisation.
2. **The closing pair, both on the tree you hand over:** default order — this is the mandatory
   closing stamp — and the task-6 reversal.

Any run beyond these three requires the charter's authorization line, written before it.

Everything else runs at L1/L2: twelve file-scoped runs for C1, the criterion module for
C3–C8, and every named mutation at its own site's hypothesis scope.

## 8. Scope fences

- **No `pytest-xdist`, no `-n`, no parallel run, no worker-count matrix, no new authoritative
  baseline under a changed runner.** That is plan 3 (OD-5). This phase is judged entirely
  serially.
- **Nothing under `app/beyo_manager/`.** Phase 1 held this line across four rounds and the
  projection confirmed no task here requires crossing it — including task 5, which reads the
  production key builders without modifying them. The one exception is a **mutation probe** at
  `create_pause_reason.py:36` for C7(a), which is applied, observed and reverted, and declared
  separately from your changes.
- **No fixture-scope optimisation.** Plan 1 C7's fence stands: `initialize_database` being
  autouse and function-scoped *is* isolation semantics, and widening it looks like free speed.
- **`CREATE DATABASE … TEMPLATE` failing while another session holds the source open** is
  recorded against plan 3. Do not solve it here.
- The three `ai_inferred` architecture-graph items from plan 1 are **owner-adjudicated and
  deliberately unconfirmed**. Do not promote them. Record any new delta additively.

## 9. Closing protocol

Follow `implementation-executor.md` §Closing protocol, with these project specifics:

1. **The closing L4 stamp**, taken on the tree you hand over, with tree identity and the
   failure-ID delta in both directions against the published 22. The predicted set is **21** —
   the 22 minus `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`,
   which task 1b repairs. Any other difference is **a finding to explain, not a number to
   update**.
1½. **Run every named mutation the plan states, at the site it names**, and record each as a
   full evidence record. Note that C4 requires **one mutation per sub-check** — a single
   `return True` reddens every row regardless of which check bit, so it cannot detect the
   failure mode C4 exists to catch. A sub-check whose disabling reddens nothing has no row
   that tests it, and that is a finding to report.
2. **This project has no master-plan tracker.** State lives in the plan's frontmatter: set
   `plans/plan_2.md` `state: IMPLEMENTED` with date, actor and a one-line note carrying test
   counts. Touch nothing else in the frontmatter.
3. **Review log entry** in `plans/plan_2.md` §7: what you built, every judgment call with its
   reason (including the four delegations of §6), deviations with justification, and
   observations a reviewer needs.
4. **Handoff file** at
   `handoffs/implementer/2026-08-21_phase2_implement_r1_handoff.md`, frontmatter
   `plan: 2` / `role: implement` / `state` / `date` / `actor`. Body: what was built, test
   counts, judgment calls, the **new `assert_disposable_database` signature**, your **full
   write perimeter** (documents, code, tool-recorded state), and **every file a mutation probe
   touched, listed separately from your own changes** — this is what makes "no production
   changes" falsifiable. Every probe database created, and its verified disposition.
5. Anything only the owner can settle goes in the handoff as a **decision card** in the
   charter's `⚠ OWNER DECISIONS REQUIRED (n)` section — never as a buried paragraph. If
   nothing needs the owner, one line saying so.

The handoff file, not your chat message, is what the coordinator consumes.
