---
plan: batch A — plans/plan_1.md, plans/plan_2.md, plans/plan_3.md (master_plan.md §3A)
role: reviewer (Claude Opus, skill `plan-reviewer`)
round: batch_A-review-1
date: 2026-09-20
tree: 0d5d31d
---

# Batch A review: phases 1, 2, 3 (`stock_report`)

You review **one batch of three phases** implemented in a single Codex session. Your verdict covers
every criterion row of all three phase plans **and** the batch as a whole. You are independent of
the implementer: its handoff is a claim, not evidence, except where §3A lets you consume a stamp.

Paths are relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.
Run tests from `app/`.

## What you are reviewing

- **Tree:** commit `0d5d31d`, which is HEAD and the working tree is clean. The batch perimeter is
  `git diff d0cd5bb..0d5d31d`. 53 files: 2996 lines of new source and tests, plus the migration.
- **Implementer handoff:** `SR/handoffs/implementer/2026-09-19_batch_A_implement_1_handoff.md`.
- **Specification:** `SR/plans/plan_1.md`, `plan_2.md`, `plan_3.md` — 170 criterion rows in 22
  criteria. The plans win over the handoff and over this prompt everywhere except the batch rules,
  which come from master plan §3A.

## Read first

1. The pipeline charter and your `plan-reviewer` doctrine.
2. `SR/master_plan.md`: **§3A** (the batch model — it changes what a review is here), §5 (contracts
   MC-1…MC-20), §6 (naming registry), §9 (standing rules; rule 16: never spell a state list; rule
   17: Scanner-owned shapes), §10 (environment, commands, the 21-ID baseline).
3. `SR/planning/intention.md` — RATIFIED at round 9. §14F (`resolved_early`) touches phases 1 and 3.
4. Each plan in full, then the implementation and the tests.

## What the orchestrator already verified (do not redo; do challenge if you find contradicting evidence)

I ran the full suite myself on this tree:

```
PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile
→ 21 failed, 3241 passed, 2 skipped in 66.03s
```

The 21 failure IDs are **identical in both directions** to the published baseline set (§10; the list
is in `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`
§3). 3241 = 3103 baseline + 138 new. No stock-report test fails, and no previously passing test
broke. **You do not need to run L4 again.** Spend your runs on L1/L2 at the sites you are probing
and on the variations the plans demand.

I also confirmed: the three plan-file diffs are Review-log appends only; `bm/config.py` adds exactly
the three fields plan 1 §4 declares; the migration's `down_revision` is `ce99896e6f49` and it
carries the partial-index predicates, the CHECK constraints and four `DROP TYPE` statements.

## Known gaps in the handoff — these are review tasks, not findings to restate

The handoff is an append-only log. Two parts of it are **stale and wrong**: its frontmatter
(`state: PARTIAL_NOT_READY_FOR_REVIEW`) and its §"Current implementation state", which says the
tests, mutation ledger, routes, locking and L4 were not completed. The same handoff's later stamps
and my own run contradict both. Do not treat the batch as unfinished on their authority; judge the
tree. Four evidence gaps are real and are yours to close:

1. **Scanner conformance for phase 2 is unevidenced (the most important one).** The implementer
   prompt required every hand-walk H-row's criteria to be run through Scanner's own
   `normalizeCriteria`
   (`apps/backend/src/modules/stock/domain/property-criteria.ts` in
   `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify`, read-only, HEAD
   `0d80bf2`, `apps/backend/node_modules/.bin/tsx` present), with each input → output recorded, plus
   one `node -e` each for `String(4.0) === "4"` and the compact `JSON.stringify` separators. **None
   of that appears in the handoff.** Plan 2's fixtures may therefore encode the planner's hand-walk
   literals rather than Scanner's real behavior — exactly the risk rule 17 exists for. Run the
   conformance check yourself (scratch files under `/tmp`, never inside either repository) and
   record each input → output in your handoff. Where Scanner's output differs from the fixture, that
   is a FAIL on the affected C6 rows; where the fixture matches, the row is discharged and you have
   supplied the missing evidence.
2. **No row-level coverage map.** The handoff gives ten criterion *families*, not the required one
   line per criterion row → test id → assertion shape. Build the per-row verdict table yourself;
   that is the review's main artifact.
3. **Mutation ledger arithmetic does not close.** The handoff claims `executed=123` against its own
   scan of "39/37/22 distinct mutation descriptions". My count of the plans' distinct named-mutation
   cells is **35 / 37 / 22 = 94**, and the ledger visibly repeats sites (Plan 1 C3's enum DROP, Plan
   1 C1(h), Plan 1 C6(a), Plan 2 C1(b), Plan 2 C2(a)/(b), Plan 2 C5(a)/(c), Plan 3 C6(f) each appear
   twice). So `executed == declared` is **asserted, not shown**. Determine which declared sites were
   never probed, and for the rows you most doubt, run the mutation yourself rather than trusting the
   ledger line. Rows a plan marks `—` or "cannot isolate" (plan 1 C4(f)) are not failures.
4. **No tree SHAs on the stamps and no graph delta.** The graph was not written (the MCP server was
   in `permissionMode: review`); the prompt's fallback — writing the intended delta into the handoff
   — was not done either. The graph gate is the orchestrator's, so record what the delta should be
   and move on. Missing SHAs are a process note, not a defect in the code.

## Perimeter deviations to rule on

- `app/tests/integration/services/commands/reset/test_stock_report_reset.py` — plan 1 §4 names this
  file `test_reset_stock_report_phases.py`. Renamed without a recorded judgment call.
- `app/tests/integration/helpers/test_stock_report_helper.py` — in no plan's expected-files list and
  not justified in the handoff.
- `app/tests/integration/infrastructure/test_database_isolation.py` — an **existing guard test was
  edited**: the hard-coded `expected 109 public tables` became a count derived from
  `expected_public_tables()`. Decide whether the unenumerated-table guard still discriminates, or
  whether deriving the expected count from the function under test hollows it out.
- The new test packages have no `__init__.py`, which plan 1 §4 lists. Check collection is
  unaffected before calling it a finding.
- No `bm/services/commands/stock_report/requests/__init__.py` — plan 3 §4 makes that the
  implementer's choice, so it is fine, but the choice was not recorded.

## Review dimensions (§3A)

Per phase, a verdict for **every** criterion row: `P<n> C<k>(<x>) PASS | FAIL | NOT_VERIFIED`, each
with the test id that discharges it and whether the assertion has the shape the row specifies. A row
whose test cannot fail is not a PASS — the recurring defect in this pipeline is the row that passes
for the wrong reason (uniform fixtures, an assertion weaker than the row, a paraphrase of the
criterion instead of its literal outcome).

Then the batch as a whole:

- **Contract compliance** against master plan §5 (MC-1…MC-20), and §14F's `resolved_early` as a
  terminal state that still counts toward the goal total.
- **Cross-phase integration:** phase 3 extended phase 1's kit (`app/tests/helpers/stock_report.py`,
  `assert_stock_report_clean`); confirm phase 1's kit-using tests still hold, and that every kit
  function has a caller (charter rule 4).
- **Locks and transactions** in `_locks.py` and `repair_stock_report.py`: workspace scoping, lock
  order, the task-lock pre-pass, the "≠ 1 row is a programming error" rule (§12A — structural, not
  criterion rows).
- **Repair ordering:** nullness before priority density; repair records written from a before/after
  diff per `(row, field)`, never per step.
- **Workspace isolation.** Measured 2026-09-19: ~819 rows from 23 other test files persist in a
  worker database within a run. Every new test must scope its assertions to its own workspace and
  assert no global total, and any test that commits must purge in `finally`. Plan 1 C3(a)
  (`reset_app`) and plan 3 C1(k) keep a foreign workspace on purpose.
- **Event semantics** and the `changed_row_ids` dispatch guard.
- **Perimeter escape:** anything outside the three plans' expected-file lists, the kit and the
  migration.
- **Migration:** compare the revision to §6.2 line by line — autogenerate drops `postgresql_where`
  predicates and CHECKs, and the dev database `beyo_manager` must never have been upgraded or
  downgraded.

## Rules that constrain your findings

- **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19). A test asserts input →
  outcome at a public boundary: a return value, persisted state, an event, an HTTP answer. A finding
  that only asks for an implementation-coupled assertion is a **backlog note**, never
  CHANGES_REQUESTED. The one place a statement-level instrument is legitimate is plan 3 C5(a), which
  the row itself names; plan 3 C2(a) was re-stated by owner ruling to assert the data is unchanged
  (every row of the four MC-9 tables and `stock_report_repair_records` in W equal before and after),
  not to count writes.
- Do not redesign. If the implementation satisfies the row by another route, that is a PASS.
- Do not weaken a row to make it pass, and do not invent rows the plans do not contain.
- The 21 baseline failures are not yours to fix or to report.

## Do not touch

The intention; the Scanner repository (read-only); the Scanner handoffs; the plan files except one
appended **Review log** entry each; master plan tracker rows (§4, §4A — the orchestrator writes
them); other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`. Do not modify
source or tests: you review, you do not fix. You may create scratch files under `/tmp`. Make no
commits.

## Handoff

Write it to `SR/handoffs/reviewer/2026-09-20_batch_A_review_1_handoff.md`. Frontmatter: `plan: batch
A (1, 2, 3)`, `role: review`, `round: batch_A-review-1`, `state: APPROVED | CHANGES_REQUESTED`,
`date`, `actor`, `tree: 0d5d31d`. Structure:

1. **Verdict** and the counts: rows PASS / FAIL / NOT_VERIFIED per phase and in total (of 170).
2. **Per-phase verdict tables** (one line per criterion row).
3. **Scanner conformance record** (gap 1): every input → output, and the two `node` outputs.
4. **Mutation audit** (gap 3): declared sites vs probed sites, which you re-ran yourself and what
   you observed.
5. **Batch-level findings** under the dimensions above, each with a severity, the evidence, and the
   phase and row it belongs to. Group them by cause — I turn them into **one** fix prompt.
6. **Backlog notes** (charter rule 2) kept separate from findings.
7. **Perimeter ruling** on the five deviations listed above.
8. **What you ran**, with commands and results.
9. `⚠ OWNER DECISIONS REQUIRED (n)` in the charter's card format, or `(0)`.

Your final message's first line is the `HANDOFF: … | STATE: … | OWNER_CARDS: n` line, followed by
the owner layer.
