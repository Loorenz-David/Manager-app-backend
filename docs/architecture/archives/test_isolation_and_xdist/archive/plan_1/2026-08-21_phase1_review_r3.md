---
plan: 1
role: reviewer
round: 3
date: 2026-08-21
project: test_isolation_and_xdist
---

# Session prompt — plan 1 review r3, `test_isolation_and_xdist`

## 1. Role and mode

First and only independent review of phase 1: per-worker PostgreSQL isolation, proven serially.
You did not write this and must not assume it is correct — or wrong. Findings and a verdict;
you never fix.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(suite from `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`)

**Read first, by absolute path, as doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**) and `/Users/davidloorenz/agent-skills/plan-reviewer.md`.

## 2. Why this phase deserves a careful reader

**This is the instrument every other measurement passes through.** Every mutation bite, every
approval baseline, every "the suite is green" in this organisation is now mediated by the code
under review, and it publishes a **new authoritative failure-ID set** that
`live_clock_for_working_time_economics` phase 4 and `narrow_typical_work_times` D23 will build
on. If isolation is subtly wrong, nothing downstream is trustworthy and nothing will announce it.

## 3. Gate check — stop and report if false

- Branch `feat/test-isolation-xdist`; HEAD's `app/` tree identical to checkpoint **`697b633`**
  (`git diff 697b633 HEAD -- app/` empty — later commits are documentation only).
- `plans/plan_1.md` carries three Review-log entries (implement r1, the coordinator's r1
  consumption, fix r2's, plus the coordinator's r2 consumption).
- `pytest-xdist` is **not** installed and no `-n` appears anywhere. That is phase 2.

## 4. Settled ground — do NOT re-spend the round here

Verified independently by the coordinator; **contradicting one is a finding worth reporting
loudly**, re-deriving them is waste:

- **Perimeter**: exactly eight files in `697b633`, all under `app/tests/`, no production code.
- **Baseline**: coordinator run at the current tree gave **22 failed / 2539 passed / 1
  deselected in 108.72 s**, and the failing-ID set is **byte-identical** to the handoff's
  published 22 (`comm` empty both directions). Against the old 26: **removed = four, added = ∅**.
  Cite this; do not re-run the full suite unless your tree differs.
- **The four removed** are dev-data artifacts, named and reasoned in the handoff, and were
  identified independently by the coordinator before the fix round ran.
- **Residue**: after a full run the server holds only `beyo_test_template`; dev counts are
  `11253/9809/2445/1955`, unchanged; the two rows the C6 mutation committed into the dev database
  are gone, verified by direct query.
- **F3 is closed**: C6 now snapshots before/after instead of hardcoding the owner's row counts.
- **The fixtures are narrow**: 142 lines, four fixtures (one per test group), explicit
  `phase1-*` rows, no broad dataset and no live-data copy.

**One known defect, already found — do not spend the round rediscovering it.** The handoff
publishes the baseline as `22 failed / **2540** passed`, twice. Collection is 2561 selected, so
`22 + 2540 = 2562` cannot be right; the correct figure is **2539**. Confirm the correction lands
wherever the baseline is finally published; it is not yours to fix.

## 5. Probes — spend the round here

- **P1 — can any of the nine tests now pass for the wrong reason?** This is the highest-value
  question in the round. Nine tests that used to lean on a developer's database now lean on
  authored fixtures. For each, ask whether the fixture supplies **exactly what the test's own
  assertion needs** or something broader that would keep the test green if the behaviour it
  guards regressed. A fixture that over-supplies is the same defect as the dev-data coupling,
  one layer down and harder to see. Name any row where the fixture, not the production code, is
  the reason the assertion holds.
- **P2 — C3's evidence shape.** Its named mutation (stamp without migrating) produced a **setup
  abort** — `expected 107 public tables, got 1` — rather than a red test row, so its ID delta
  reads `∅ / ∅`. Argue whether that is the correct outcome (the guard refuses to build a bad
  template before any test can report a false green) or a criterion whose stated mutation cannot
  actually turn its own row red. Both readings are defensible; pick one with evidence.
- **P3 — the safety invariant, attacked rather than read.** Four conditions guard every `DROP`:
  name pattern, not-the-configured-database, marker present, URL parses. Try to defeat them.
  Consider a database that matches the pattern *and* carries a marker but is not this project's;
  a `DATABASE_URL` pointing at a **different host** whose database name collides; case and
  Unicode variations on the name; and what happens if the marker table exists but is empty.
  The guard is the one thing here whose failure is unrecoverable.
- **P4 — teardown on the paths nobody runs.** Normal completion is proven. What happens on
  **test failure**, on **KeyboardInterrupt mid-run**, and if the maintenance connection itself
  fails? The intention requires an interrupted run to be reabsorbed, not accumulated — C8 proves
  the fixed-name reabsorption, but confirm the drop path is reached (or safely skipped) when the
  session ends abnormally.
- **P5 — what isolation does NOT cover.** PostgreSQL is isolated; the intention warns explicitly
  against inferring the suite is parallel-safe from that. Redis keys share a prefix fixture; the
  suite may touch the filesystem, fixed ports, background tasks or module-level caches. Report
  what remains shared, because phase 2 will run these concurrently. Scope any repository-wide
  absence claim as **L4** and record your search terms beside it.
- **P6 — the order-dependent test.**
  `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task` passes
  when only the old 26 IDs run and fails in a full suite on a clean schema, so it depends on
  state another test creates. It stays in the baseline deliberately. Confirm that diagnosis, and
  say whether any *other* member of the 22 shows the same signature — xdist will reorder tests
  for the first time in this repository's history, and this class is what will break.

## 6. Evidence policy

- Cite the coordinator's tree-bound baseline rather than reproducing it; re-run the full suite
  only if your tree differs from `697b633`'s `app/` or you change code.
- Spend your budget on **variation** — conditions, sites and mutant shapes no ledger has tried
  (P3 and P4 are explicitly that).
- Every evidence record: hypothesis · scope · command · tree identity · result · ID delta both
  directions. Probe declarations must list every file touched, every database created, and
  confirm removal — this round's predecessors created and cleaned real databases and real dev
  rows, and that standard holds for you.
- **Foreign streams are live**: the owner works in parallel on other domains. Files outside
  `app/tests/` and this project's folder are not yours — do not commit, revert or stash them.

## 7. Closing protocol

Mutation-probe declaration (files, databases, rows — created and removed, verified); a
carry-forward dispositions table if you approve with open notes; technical findings appended to
`plans/plan_1.md`'s Review log; and a handoff at
`handoffs/reviewer/2026-08-21_phase1_review_r3_handoff.md` (frontmatter `plan`, `role: review`,
`verdict`, `date`, `actor`) with verdict, findings by severity, lessons, and any owner item as a
**decision card** (one line if none).

Your final message carries the layer-2 human briefing: 2–4 sentences of plain state-of-the-build,
then a faithful narrative per blocking/should-fix finding. The owner's stake here is concrete —
they are about to run parallel work trees against this, and a wrong isolation boundary means
silent, nondeterministic test failures that look like flakiness.

If the work holds, **approve plainly**. Do not invent findings for completeness.
