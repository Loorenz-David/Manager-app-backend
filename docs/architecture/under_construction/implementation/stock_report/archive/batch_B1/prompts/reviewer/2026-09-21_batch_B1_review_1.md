---
plan: batch B1 — plans/plan_4.md, plans/plan_5.md (master_plan.md §3A)
role: reviewer (Claude Opus, skill `plan-reviewer`)
round: batch_B1-review-1
date: 2026-09-21
tree: 1351b5f
---

# Batch B1 review: phases 4 and 5 (`stock_report`)

You review **one batch of two phases** — 84 criterion rows — implemented in a single session. Your
verdict covers every criterion row of both phase plans and the batch as a whole.

**Two things are different about this review, and they matter.**

1. **The implementer was a Sonnet agent, not Codex.** The owner is asleep and authorized an
   unattended overnight run. Its handoff is unusually good and its headline numbers check out (I
   verified them myself, below) — but this pipeline has a measured finding that Sonnet approved a
   phase carrying an inert safety switch and a silent `DROP DATABASE`, and affirmed coverage that
   did not exist by trusting a ledger. **Trust its claims exactly as far as you can re-measure
   them.** Where you can run the mutation yourself, run it.
2. **Both plans were amended hours before implementation.** 22 fixture and mutation cells were
   folded because they specified guards that could not fail. Each plan carries a **Fold note** at
   the top of §6 marking the change. Part of your job is judging whether the fold did what it
   claimed — see §"The fold" below.

Paths are relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.
Run tests from `app/`.

## What you are reviewing

- **Tree:** `1351b5f`, HEAD is `b89d568` (docs only — no source or test file differs).
- **Perimeter:** `git diff aa849cc..1351b5f -- app/` — 10 files, +2426/−4. Four new production
  files (`_move_assignment.py` 268, `_goal_credit.py` 132, `_events.py` 41, `_remove_assignment.py`
  22), three new test files (`test_move_assignment.py` 991, `test_goal_credit.py` 744,
  `test_remove_assignment.py` 220), three authorized edits to phase 3 code.
- **Implementer handoff:** `SR/handoffs/implementer/2026-09-21_batch_B1_implement_1_handoff.md`.
- **Projection:** `SR/handoffs/projectionist/2026-09-21_batch_B_projection_handoff.md` — §1.2's
  hazards H1–H13 and §1.3's shipped signatures are the ground truth the implementer worked from.
- **Specification:** `SR/plans/plan_4.md` (62 rows, 7 criteria), `SR/plans/plan_5.md` (22 rows, 3
  criteria). The plans win over the handoff; the intention wins over the plans.

## Read first

1. The pipeline charter and your `plan-reviewer` doctrine.
2. `SR/master_plan.md` §5, §6.1, §6.5 (**amended twice on 2026-09-20 and again by this batch**),
   §6.7, §6.8, §9, §10.
3. `SR/planning/intention.md` §5A MC-1, §6A MC-5/MC-6, §4B MC-15, MC-16, MC-17, §9D MC-19, §12A,
   §14C, §14F.
4. Both plans in full, including their Fold notes and Review logs.
5. The implementation and the tests.

## What I verified (consume by citation, do not re-run)

- **L4 on `1351b5f`**, my own run: **21 failed / 3349 passed / 2 skipped in 65.65s**, failure IDs
  identical to the 21-ID baseline **in both directions**. 3349 = 3264 (post-batch-A) + 85 new
  tests, exactly as the handoff claims. **Do not run L4.**
- **The perimeter** is as listed above, with no escape and no master-plan edit.
- **The three authorized edits** are minimal and correct by reading: `write_repair_record` gains a
  keyword-only `delta=None` passed into the existing warning slot; `set_task_stock_flag` gains
  `workspace_id` with `Task.workspace_id == workspace_id` in the `WHERE`; `repair_stock_report.py`'s
  direct call site threads `ctx.workspace_id`.

Spend your budget on whether the 84 rows are armed, not on re-deriving these.

## Per-row verdict

Give **every** row of both plans `PASS | FAIL | NOT_VERIFIED` with its test id, and state whether
the assertion has the shape the row specifies. A row whose test cannot fail is not a PASS. The
recurring defect in this pipeline, across three batch A reviews, is the row that passes for the
wrong reason — a fixture too uniform to discriminate, an assertion weaker than the row, a
paraphrase of the criterion instead of its literal outcome.

## The five things most likely to be wrong

**1. The two self-reported findings.** The implementer surfaced both rather than smoothing them
over, which is a good sign — but they are exactly where a weak row would hide.

- *Phase 4 C3.* It reports that C3's 22 "allow it" rows reduce to **4 guard branches** in code, and
  that C3(m)/(s)/(u)/(v) are each protected by **two** independent guards, so no single-guard
  removal reddens them — only a combined removal does, which it says it ran separately. **Verify
  this claim directly.** If four rows can only be reddened by removing two guards at once, decide
  whether each row is genuinely armed or whether the four collapse into fewer real checks. This is
  lesson L-12's shape (one mutation for a row protecting several sub-checks) seen from the other
  side.
- *Phase 5 C2(c).* Its named mutation came back **inert at the literal site the fold gave it**
  (inside `_uncredit`, which the implementation never calls for that scenario); the implementer
  re-sited it to the path that runs and reports it then reddened. I wrote that cell, so judge it
  without deference: was the re-siting legitimate, or does the inertia mean the row is testing
  something other than what it says?

**2. H9 — the enum serialization is implemented but unexercised.** `RETURNING
StockReportItem.priority` yields a `StockReportPriorityEnum` member, and `event_bus.dispatch` never
serializes, so a non-JSON-serializable payload would **pass every test in this batch and fail in
production**. The implementer emitted `priority.value`, verified it with a scratch test, then
deleted the test because no criterion pins it — correctly, per its instructions. **No shipped
fixture in phases 4 or 5 sets a non-null `priority`.** Decide: is a row needed now, or does phase
12 (priority triage) legitimately inherit it? Say which, and why.

**3. The task-flag fixture rule (fold F4-1/F5-1).** This is the amendment that unblocked ~50 rows,
and it works by seeding `tasks.is_stock_assignment = true` via raw SQL wherever a scenario ends
with a live assignment. Check that the seeding is (a) present where the rule says, (b) absent where
the rule says it must be absent (rows ending soft-deleted: plan 4 C1(g), C1(k), C1(p), C1(q),
C1(r), C1(u), C5(c), C7(c); plan 5 C1(i), C1(l), C1(q), C2(c), C3(a) step 6), and (c) **not doing
the row's work for it** — a fixture that seeds the flag to the value the outcome asserts makes the
flag mutation inert (`set_task_stock_flag` no-ops via `is_distinct_from`). Plan 4 C6(a) and C6(c)
were folded specifically for this; confirm the fold actually armed them.

**4. The guarded counter statement and the inline self-heal** (MC-1). The write order — own columns
and flush, then the guarded UPDATE, then on zero rows the `stored_before` read, recompute, absolute
UPDATE, one repair record per diverging column, one warning carrying the delta. Check the delta
actually reaches the warning (that is what the B2 amendment exists for), that the `WHERE` carries
no predicate beyond the guard, and that events are built from `RETURNING` and not from the ORM
instance (plan 4 C4(c) depends on the instance staying stale — confirm nothing refreshes it).

**5. Lock order and the H6 premise.** `remove_assignment` writes `tasks` after the row and
assignment locks, inverting MC-1's order; the resolution was that its contract is *the caller
already holds the task lock*, and phase 4's tests must model that by taking the task `FOR UPDATE`
first. Confirm the tests do. Plan 5's `apply_goal_effect` must take **no lock on `R`** — the
protection is the moving assignment's row lock (intention §6A MC-5's round-7 re-check). Confirm it
does not add one, and that the tests hold row + assignment `FOR UPDATE` before calling.

## The fold — judge it

I amended 22 cells in plans 4 and 5 before implementation, under authority limited to **"Named
mutation (site)" and "Fixture / input" cells only**. No outcome cell was touched. Every amended
cell is visible in `git show a306298`.

Judge whether each fold did what it claimed: did it arm a guard that was inert, or did it shape the
fixture to the implementation? **If I over-reached — if any fold changed what a row effectively
asserts rather than how it is armed — say so plainly.** I am the orchestrator, not an authority on
these plans, and the owner authorized the fold on my recommendation while asleep. A fold that
weakened a row is a finding against me, and I would rather have it now than in batch C.

## Batch level

- **Contract compliance** against master plan §5 and the intention's MC-1, MC-5, MC-15, MC-16,
  MC-17, MC-19, §12A, §14F.
- **Cross-phase integration:** phase 5's `apply_goal_effect` is wired into phase 4's
  `_move_assignment.py` at the step-4 insertion point. Confirm the placement matches MC-1's write
  order (after the counter statement, before the events) and that phase 4's rows still hold with it
  present.
- **N-R3 discharge:** `recompute_row_counters`, `recompute_task_stock_flag` and
  `recompute_goal_total` each got their first caller in this batch. Confirm each is genuinely
  reached by a shipped test, not just referenced.
- **Workspace isolation** (§9 rule 1): every test scoped to its own workspace, no global totals, a
  `finally` purge on anything that commits. Measured 2026-09-19: ~819 rows already leak per run.
- **Perimeter escape**, orphan tests (charter rule 16), and whether any test is
  implementation-coupled rather than outcome-asserting.

## Rules

- **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19). A finding that only asks for
  an implementation-coupled assertion is a **backlog note**, never CHANGES_REQUESTED.
- Do not redesign; do not weaken a row to make it pass; do not invent rows the plans lack.
- The 21 baseline failures are not yours.
- Findings route into **one** grouped fix prompt, so group them by cause and rank blocking first.
- **The owner is asleep.** If you raise an owner card, state plainly whether the RATIFIED intention
  or a contract settles it — I am authorized to rule what the intention determines and to proceed
  provisionally on your recommendation where it does not, flagging it for the morning. Give me a
  recommendation on every card, and say which of the two kinds it is.

## Do not touch

The intention; the Scanner repository; the plan files except one appended **Review log** entry
each; the master plan (§6.5 needs three amendments from this batch — report them, do not edit);
other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`. Do not modify source or
tests: you review, you do not fix. Revert every mutation probe and prove it byte-identical. No
commits, no graph write.

## Handoff

`SR/handoffs/reviewer/2026-09-21_batch_B1_review_1_handoff.md`. Frontmatter: `plan: batch B1 (4,
5)`, `role: review`, `round: batch_B1-review-1`, `state: APPROVED | CHANGES_REQUESTED`, `date`,
`actor`, `tree: 1351b5f`. Structure:

1. **Verdict** and counts: rows PASS / FAIL / NOT_VERIFIED per phase and in total (of 84).
2. **Per-phase verdict tables**, one line per criterion row.
3. **Mutation audit**: declared sites vs probed sites, which you re-ran yourself and what you
   observed. State whether `executed == declared` actually holds.
4. **The five risk areas** above, each with your finding or a confirmation.
5. **Your judgment on the fold**, including any over-reach.
6. **Batch-level findings**, grouped by cause, blocking first.
7. **Backlog notes**, separate.
8. **The three §6.5 amendments** as final signatures, for me to write into the master plan.
9. **What you ran**, and the **mutation-probe declaration**.
10. `⚠ OWNER DECISIONS REQUIRED (n)` in the charter's card format, each with a recommendation and
    whether the intention settles it, or `(0)`.

Your final message's first line is `HANDOFF: … | STATE: … | OWNER_CARDS: n`, then a short summary
and the single most important thing I should know.
