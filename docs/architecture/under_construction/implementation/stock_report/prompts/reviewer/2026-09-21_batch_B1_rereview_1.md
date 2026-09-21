---
plan: batch B1 — plans/plan_4.md, plans/plan_5.md
role: reviewer (Claude Opus, skill `plan-reviewer`) — re-review after fix round 1
round: batch_B1-rereview-1
date: 2026-09-21
tree: 60d6a12
scope: light and delta-scoped (§3A). Four findings, one scenario, one new gap.
---

# Batch B1 re-review 1 — after fix round 1

Review 1 (`SR/handoffs/reviewer/2026-09-21_batch_B1_review_1_handoff.md`, tree `1351b5f`) returned
**CHANGES_REQUESTED at 83/84 with zero blocking findings and no production defect**. One fix round
ran. **This re-review decides whether batch B1 is APPROVED.**

If you wrote review 1, you have no memory of it — read it. Its verdict table is the baseline this
is a delta against.

Keep this narrow. The fix round shipped **zero production-code change**, 83 rows were already armed
and measured, and the risk now is spending budget re-deriving settled ground. §10 of review 1 lists
what it already verified correct; do not revisit it.

Paths relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. Run tests from `app/`.

## The delta

`git diff 1351b5f..60d6a12` is **tests and plan documentation only**:

| File | Change |
|---|---|
| `test_move_assignment.py` | +105/−5 — S1's repair leg, S3's priority payload, the lock fixture |
| `test_goal_credit.py` | +43 — card 2's scenario |
| `test_remove_assignment.py` | +34 — the lock fixture |
| `plans/plan_4.md`, `plans/plan_5.md` | Review-log entries, candidate criteria |

`git diff 1351b5f..60d6a12 -- app/beyo_manager/` is **empty**. I verified this myself.

## What I verified (consume by citation)

- **Zero production-code diff** since the reviewed tree, as above.
- **L4 on `60d6a12`, my own run: 22 failed / 3349 passed / 2 skipped.** The 22nd is
  `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`.
  **It is provably independent of this batch:** I ran that file alone, with no stock-report test in
  the session, and it still fails; its line 554 computes `datetime.now(timezone.utc)` and subtracts
  three hours, so between 00:00 and ~03:00 UTC the clock-in falls on the previous UTC day. My run
  was at 00:31 UTC. **Do not investigate it, and do not run L4** — I will re-take a clean 21-ID
  stamp after 03:00 UTC before the approval gate. Treat the batch's L4 obligation as mine, not
  yours.
- The two orchestrator-ruled cards were carried out: card 1's priority guard and card 2's goal
  scenario both landed as tests plus **candidate criteria in the Review logs**, not as authored
  table rows — which is what I instructed, because authoring a criterion row is the owner's call.

## What to decide

**1. S1 — does plan 4 C5(b) now assert all four clauses?** Including the `repair_stock_report` leg
and the whole divergence list rather than a filtered one.

**2. S2 — the lock modelling. This is the one that matters.** A shared helper was added to both
phase-4 test files, taking task → row → assignment `FOR UPDATE` before each call. Judge whether it
genuinely models the caller contract that makes `remove_assignment`'s inverted write order safe, or
whether it is decoration that runs and proves nothing. Phases 8–13 will copy this shape, so if it
is wrong it is wrong eleven more times. Check in particular that the helper is used in **every**
scenario the finding named, including plan 5's `apply_goal_effect` rows (row then assignment, and
**no** lock on `R`).

**3. S3 / card 1 — the priority payload guard.** Fixture sets `priority = HIGH` **and**
`priority_order = 1` (both, or the nullness check fails the row for an unrelated reason); the
payload asserts the string `"high"`; the mutation emitting the enum member reddens it. Confirm all
three, and that the row's clean assertion still holds for the right reason.

**4. Card 2 — the goal self-heal scenario.** A move that *does* subtract, against a total that
drifted upward, asserting no repair record and one `goal_total` divergence. Confirm it closes N1
and that it does not disturb C2(c)'s existing clauses.

**5. S4 — the ledger, and the new gap.** The fix round re-derived both counts mechanically and the
honest result is that **the arithmetic does not close: `executed 33 != declared 34`.** The single
unrun mutation is plan 4 **C5(c)**, deliberately not attempted because closing it means
restructuring the write order rather than swapping a value, which the prompt told the implementer
to avoid in a caution-first round. It is declared as note **N12**.

While re-deriving, the round also found that **C5(a) and C5(b) were counted in the original prose
sum but had no run recorded anywhere** — two more gaps than review 1 detected. Both were closed
this round and behaved as predicted.

**Your calls here:**
- Is `executed 33 / declared 34` with one named, reasoned gap acceptable for APPROVED, or does
  C5(c) block? Say which and why. An honestly declared gap is not automatically a failure, and an
  undeclared one is not automatically forgivable — decide on the substance.
- Verify the re-derivation itself. The failure family this pipeline keeps paying for is a count
  that is typed rather than computed; check that the new mapping (plan cell → table row) actually
  holds, and spot-check at least two of the four mutations re-run this round.
- Confirm the C3 collapse statement ("22 declared cells → 4 guard mutations + 1 combined proof")
  matches what the table shows.

## Widening — only this

The fix round touched no production code, so §3A's shared-foundation clause is not triggered. The
one thing to check beyond the delta: the lock fixture is used in **every** scenario in two test
files, so confirm it did not perturb a row that review 1 passed — particularly any row asserting
stamps, event lists or `count_writes`, where an extra `SELECT … FOR UPDATE` could change what an
instrument observes. Name any row you pull in.

Do not re-verdict the other rows. Review 1 measured them.

## Rules

- **Outcomes, not internals.** A finding that only asks for an implementation-coupled assertion is
  a backlog note, never CHANGES_REQUESTED.
- Do not modify source or tests; revert every probe and prove it byte-identical.
- **Owner asleep, authorized unattended run.** If you raise a card, give a recommendation and say
  whether the RATIFIED intention settles it. I rule what the intention determines and proceed
  provisionally on your recommendation where it does not.
- **If you approve, say so without hedging.** If something still fails, be explicit about whether
  it genuinely blocks — this is the second round, and a third needs to be worth its cost.

## Do not touch

The intention; the Scanner repository; the plans except one appended Review-log entry each; the
master plan (§6.5 already carries this batch's three amendments — report anything further, do not
edit); other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`. No commits, no
graph write, no L4.

## Handoff

`SR/handoffs/reviewer/2026-09-21_batch_B1_rereview_1_handoff.md`. Frontmatter: `plan: batch B1 (4,
5)`, `role: review`, `round: batch_B1-rereview-1`, `state: APPROVED | CHANGES_REQUESTED`, `date`,
`actor`, `tree: 60d6a12`. Sections:

1. **Verdict** and row totals of 84, with the delta against review 1's 83/1/0.
2. **S1, S2, S3, card 2, S4** — CONFIRMED / PARTIAL / NOT_DONE each, with evidence.
3. **Your ruling on the C5(c) gap** — blocking or carry-forward, with reasoning.
4. **The ledger re-derivation audit**, including the two mutations you spot-checked.
5. **Any row pulled in under the widening**, and whether the lock fixture perturbed it.
6. **Findings**, blocking first; **backlog notes** separate.
7. **What you ran**, and the mutation-probe declaration.
8. `⚠ OWNER DECISIONS REQUIRED (n)` with recommendations, or `(0)`.

First line of your final message: `HANDOFF: … | STATE: … | OWNER_CARDS: n`, then a short summary
and the most important thing I should know.
