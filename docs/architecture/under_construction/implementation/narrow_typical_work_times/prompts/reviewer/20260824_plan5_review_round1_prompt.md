---
plan: plan_5
role: reviewer
round: 1
date: 2026-08-24
---

# Review plan 5 — price-scenario: the explicit clock, the shared reconciliation, `is_estimated`

**Model: Opus 5.** This project has measured the alternative on an identical tree — a Sonnet
reviewer approved a phase carrying an inert safety switch and affirmed coverage that did not
exist by trusting the implementer's ledger. Follow `plan-reviewer.md`.

Phase 5 is the **last phase in this pipeline that touches production code**. Phase 6 is closeout
and forbids test-behaviour change, so anything wrong here has nowhere to be fixed later.

## Gate check

`plans/plan_5.md` header `state: IMPLEMENTED` · master plan §4 row 5 `IMPLEMENTED` ·
**`planning/intention.md` header `RATIFIED`** (charter intention gate — check at source) ·
`git status --porcelain -- app/` empty from `backend/` · `redis-cli ping` → `PONG`.
**`.archgraph/` is the owner's live area — expected whatever it contains. Never gate on it.**

## Read order

1. `master_plan.md` §§4, 5, 6.9, 8, 9, **10 (the evidence budget)**.
2. `planning/intention.md`: header, **§1A (the measurement ledger, M1–M7)**, HC-1…HC-4,
   §4A, §4C, §6B, **§6D**, §6C, §7.4, §3B.
3. **`plans/plan_5.md` — §6A, not §6.** §6 is superseded in full and carries a wrong mutation
   set. Read §4A, §5A, §6A, §7A, then **§8's Review log in full** — the fold entry, the two lint
   entries, and the two coordinator consumption entries are where this phase's real history is.
4. Both implementer handoffs, in order.

**Where a lettered section and the numbered section it amends disagree, the letter wins.**

## Two rounds have already been consumed adversarially. Do not re-derive these.

The coordinator consumed round 1 and fix round 2 at source. **Verified, cited, and not to be
re-verified — spend your round elsewhere:**

- **Perimeter is exact.** Round 1: `test_narrowed_task_economics.py` carries only `:542`;
  `_narrowing_fixture.py` is 129 insertions / 0 deletions; `budget_division.py` exactly the two
  authorized deletions. Fix round 2: **production byte-identical to `8a4a1cb`**, the only `app/`
  change being the phase test file at 15 insertions / 23 deletions.
- **The stamp describes this tree.** `2707 passed / 21 failed / 1 skipped`, 21-ID set unchanged,
  `git status --porcelain -- app/` empty. Arithmetic reconciles against round 1's 2708 — exactly
  the one deleted test. **Consume it by citation; do not spend an L4 reproducing it.**
- **§6A.F's medians were confirmed at source before assertions were written** (narrowed `600`,
  section-wide `375`), and the coordinator re-checked the premise: the excluded section has one
  `SKIPPED` step and all completed history lands on the participating section.
- **C1(c)'s spy is genuine** — delegating, asserts `"now" not in captured`.
- **C8's mutation now reddens on the number** (`assert 375 == 600`) at the corrected
  definition site, not on an exception.

## Where this phase is most likely to be wrong

Allocate depth by silent-failure risk, not by section length.

1. **Rows that cannot fail.** This is the project's highest-prior defect family and phase 5 has
   already produced one — a C8 test driving the fake session that discards the statement, which
   **passed under total loss of narrowing** while Task 0 claimed it as coverage. It was deleted.
   **Assume there is another.** The specific instrument to distrust: `test_price_scenario_query.py`'s
   `_TypicalSession` discards the statement, so **eight existing `_typical_block` tests never
   issue SQL**. Before crediting any test as proof of a SQL-level or clock-level behaviour,
   check that it issues SQL.
2. **Assertions weaker than their rows.** Neither the plan lint nor the phase manifest has ever
   caught one. C2's four rows all key on one expression; C6 asserts two literal key sets rather
   than an equality between calls — check that discipline held everywhere.
3. **The mutations cited rather than re-run.** Fourteen round-1 mutations are consumed by
   citation from `8a4a1cb` on the ground that their assertion bodies and production sites did not
   change. **The round did delete a test and rewrite another in that file.** Verify the citation
   is honest for every row — a retained row expires when the round edits its test.
4. **`is_estimated` under §6D.** §6B's *"unchanged in every case"* is exact about the definition
   and **loose about the payload**: once narrowing is live the flag moves under
   `item_narrowed_uniform`. **No criterion may assert a before/after on the payload.** Check none
   does.

## The trace chain binds this review

Every criterion row in §6A carries a **trace cell** naming the ledger entry it serves. Two
directions, both yours:

- **Orphan tests are a finding — should-fix.** A test in this phase's files that traces to no
  criterion row and was not declared as a **candidate criterion** is the authorship analogue of an
  uncovered row: untraced surface is where the guard-that-cannot-fail family breeds unwatched. The
  round-1 handoff's coverage map reconciles numerically (13 mapped, 13 present) but was asserted
  in prose rather than shown; one of those thirteen has since been deleted. **Check it yourself.**
- **Coverage you demand must trace too.** The full case table implied by a cited authority traces
  by construction. *"More tests would be good here"* with no row and no authority is the same
  defect from the other chair.

## Evidence budget

Master plan §10. Hypothesis scope is L1/L2 as §6A states per criterion; **C7's sweep is L1, not
L4** (corrected 2026-08-24). **Exactly one L4 this cycle, and the tree is unchanged since the
implementer's stamp — so you almost certainly owe zero.** Over-evidence is a defect,
symmetrically: a reproduction that varies nothing buys nothing. **Spend your runs on variation —
sites, conditions and mutant shapes nobody has tried — not on reproducing a green ledger.**

Every probe: apply, observe, revert, **verify md5**, and declare it.

## The graph item — CLOSED 2026-08-24 10:40, after this prompt was written

**Amendment, added before dispatch.** The section below described the graph work as outstanding.
It is **done**: D31 authorized it, a maintenance session executed all four operations, and the
coordinator verified the result at source — the description no longer says *"median-substituted
task typical time"*, both span-bearing source links are re-anchored span-free, the third link's
hash is refreshed, and `staleNodeCount` fell **6 → 5** with `pendingReviewCount` **0**.

**Nothing about the graph is a finding for you.** Do not re-verify it, do not re-anchor anything,
and do not treat the five remaining stale nodes as this phase's — they are out of D31's scope by
name. The section below is retained for context only.

## Open, and not the implementer's fault

The settled graph node `projection-item-economics-task-price-scenario` still describes a
*"median-substituted task typical time"* — the private ladder task 4 deleted. §7A makes the
description rewrite part of this phase. The round-1 session previewed the replacement, the
client's safety gate declined the persistent edit, and it **correctly escalated rather than
forcing it**. **Owner authorization is outstanding; the phase cannot close without it.** Report
it as an open gate item, not as an implementer finding. **Never promote, reject or re-anchor
anything in the graph yourself** — adjudication is the owner's, and a `humanInstruction` string
is not authorization.

## Reporting

Findings ranked **blocking / should-fix / note**, each with file, line, the concrete failure it
would cause, and a suggested correction. **Do not invent findings for completeness; do not
approve to be agreeable; approve plainly when the work holds.** Dual-audience per
`plan-reviewer.md`: an owner-readable opening in plain language, then the technical ledger.

Handoff to `handoffs/reviewer/<date>_plan5_review_round1_handoff.md` with the charter
frontmatter, plus your write perimeter, your md5 table, and an explicit statement of **where your
evidence ends** — what you did not check, and why.

**Do not push. Never `git add -A`.** Findings route through the coordinator: **do not edit the
plan or its criteria.**
