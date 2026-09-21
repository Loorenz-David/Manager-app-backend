---
plan: batch B2 — plans/plan_6.md, plans/plan_7.md (master_plan.md §3A)
role: reviewer (Claude Opus, skill `plan-reviewer`)
round: batch_B2-review-1
date: 2026-09-21
tree: ff39a96
---

# Batch B2 review: phases 6 and 7 (`stock_report`)

You review **one batch of two phases** — 88 criterion rows — implemented in a single session. This
is the last batch of batch B; batches A and B1 are APPROVED.

Three things are different about this review.

1. **The implementer was a Sonnet agent** on an authorized unattended overnight run. Its two
   predecessors in this run were good and their headline numbers held, but this pipeline measured
   Sonnet approving a phase carrying a silent `DROP DATABASE` and affirming coverage that did not
   exist. **Trust its claims exactly as far as you can re-measure them.**
2. **Both plans were amended before implementation** — 21 fixture and mutation cells folded because
   they specified guards that could not fail or predicted consequences the row cannot observe. Plan
   6 carries a Fold note. Judge the fold, as §"The fold" says.
3. **Seven mutations were declined**, with reasoning, and closing them is explicitly yours. See §2.

Paths relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. Run tests from `app/`.

## What you are reviewing

- **Tree:** `ff39a96`; HEAD is `dee6257` (docs only).
- **Perimeter:** `git diff a2f4fc2..ff39a96 -- app/` — 17 files, **+2687/−0**. Purely additive,
  which is itself evidence: `record_statements` and `count_writes` are provably byte-identical.
- **Handoff:** `SR/handoffs/implementer/2026-09-21_batch_B2_implement_1_handoff.md`.
- **Projection:** `SR/handoffs/projectionist/2026-09-21_batch_B_projection_handoff.md` — §2's
  hazards H14–H25 and the measured dependency facts are the ground truth the implementer worked
  from.
- **Specification:** `SR/plans/plan_6.md` (36 rows, 8 criteria), `SR/plans/plan_7.md` (52 rows, 7
  criteria). Plans win over the handoff; the intention wins over the plans.

## Read first

The charter and your `plan-reviewer` doctrine; master plan §5, §6.1 (**corrected today**), §6.5
(**amended four times since these plans were written**), §6.8, §9, §10; intention §4A MC-3, §8B
MC-8/MC-9, §9D, §12A, §14C; both plans in full including Fold notes and Review logs; then the
implementation and the tests.

## What I verified (consume by citation, do not re-run)

- **L4 on `ff39a96`, my own run at 02:13 UTC: 21 failed / 3436 passed / 2 skipped**, failure IDs
  identical to the 21-ID baseline **in both directions**. **Do not run L4.**
- **The handoff's one unexplained extra pass is resolved, and it is not a defect.** 3436 = 3349
  (the batch B1 stamp, taken at 00:31 UTC while an analytics test was red) + 86 new + 1 recovered.
  That analytics test is time-dependent and independent of this project: I measured it failing in
  isolation at 00:31 and passing in isolation at 02:11, with no stock-report test present either
  time. Do not investigate it.
- **The perimeter** is the 17 files above, purely additive, with the two authorized extensions
  (`statement_listener.py`'s new sibling helper, `enums.py`'s one enum) exactly as scoped.

## Per-row verdict

Every row of both plans gets `PASS | FAIL | NOT_VERIFIED`, with its test id and whether the
assertion has the shape the row specifies. A row whose test cannot fail is not a PASS.

## 1. The five things most likely to be wrong

**1. The statement budget (plan 6 C6).** The bound is exact, not slack: all-new = 8, all-changed =
7, all-unchanged = 5. Any stray `SELECT` — a `session.get`, an autoflush, a lazy-load — breaks it.
Verify the count is real and that the demand path uses Core statements with no ORM loads.

**2. Identity re-discovery (H17).** Step 6 must re-discover client_ids **by identity**, never reuse
the ULIDs generated for step 5's VALUES, because `ON CONFLICT DO NOTHING` returns nothing for a
conflicting row. This is also what keeps two concurrent requests on one lock order. If this is
wrong, the concurrency rows are wrong with it.

**3. The two-session rows (plan 6 C5(a), C5(b), C5(c)).** These are the hardest rows in batch B.
Check the `record_statements` window actually opens after the holder's writes (the listener is
engine-wide, so a badly placed window silently counts the other session's statements against a
`count_writes == 0` assertion), that the second session is opened and closed correctly, and that
each row's interleaving is really forced rather than hoped for.

**4. The committing-test shape (B5).** Every row in both plans commits and must purge in `finally`.
There is no rollback safety net. Check the purge is present everywhere, that assertions are
workspace-scoped, and that no row asserts a global total. Measured 2026-09-19: ~819 rows already
leak per run.

**5. The self-caught false green.** The implementer reports that its first-draft C1 auth fixture
used a nonexistent workspace id, which made two mutations show green because verification failure
and the command's own workspace check raise the same exception type for different reasons. It says
it found this with a probe-landed check, fixed the fixture and re-confirmed both red. **Verify
that** — both that the fix is real, and that the same masking shape does not exist anywhere else in
the C1 group. An exception type that two distinct causes share is a defect family, not a one-off.

## 2. The seven declined mutations — closing them is yours

Plan 7 **C4(b)–(h)** name properties of `criteria_normalization.py`, which is phase 1's APPROVED
and out-of-perimeter code. Rather than mutate an approved phase's file, the implementer cited that
file's own golden-vector coverage and declined the seven, with reasoning, in its handoff. Only
C4(a), whose site is genuinely phase 7's, was run.

Batch B1 established the rule that applies here: **when an implementer declines a probe on caution
grounds, the reviewer closes it in the same round** — you are the cheapest party to do it, and a
declared gap still has to be closed by somebody.

So: decide whether the cited golden-vector coverage genuinely discharges each of the seven, or
whether the rows need their own probes. Where it does not, run the mutation yourself. Reverting
cleanly matters more than usual here, because you would be touching approved code.

## 3. The O1 decision

Plan 6 C7(a)'s outcome cell says the statement has "two parameters", but the statement its own task
prescribes uses one bind name twice, which compiles to a single `$1`. An outcome cell is an
acceptance criterion and I may not amend one, so I instructed the implementer to bind **two
distinct parameters**, which satisfies the cell verbatim and makes the row stronger — it now pins
that both limits are set. Judge whether that was the right call or whether I should have escalated
the outcome cell to the owner instead.

## 4. The fold — judge it

I amended 21 cells across plans 6 and 7 (`git show a2f4fc2`), under authority limited to **mutation
and fixture cells only**. No outcome cell was touched.

Batch B1's review found my fold sound in 20 of 22 cells but caught two analytical errors: I
declared a mutant equivalent when it was not, and I narrowed a vague mutation cell into a precise
site that does not execute under the row's own fixture. **The lesson carried into this fold was: a
fold that replaces a vague mutation with a precise site must verify that the site executes under
that row's fixture.** Check whether I actually applied it. Several cells in this fold do exactly
that substitution — C1(f), C2(f), C6(a) in plan 7, C1(b) and C1(f) in plan 6.

If I over-reached anywhere, say so plainly. A fold that weakened a row is a finding against me.

## 5. Batch level

- **Contract compliance** against §5 and intention §8B MC-8/MC-9, §4A MC-3, §9D.
- **Cross-phase:** phase 7's webhook is the only caller of phase 6's command; confirm the command
  owns the transaction, the webhook opens nothing, and the deadline is computed on the command's
  first line so the budget covers verify and parse.
- **The perimeter extensions:** `record_statement_calls` must not have perturbed
  `record_statements`/`count_writes` (the +2687/−0 diff is strong evidence, but confirm batch A's
  caller still passes); `enums.py` gained one enum and must not have gained the other five.
- **Settings-coverage restoration:** batch A's fix round deleted the only coverage of the three new
  settings. Plan 6 C7(a) and plan 7 C1(a)–(c) restore it. Confirm.
- **Workspace isolation, orphan tests (charter rule 16), perimeter escape**, and whether any test
  is implementation-coupled rather than outcome-asserting.
- **The mutation ledger:** derived or typed? Batch B1 lost a round to a typed count, and its fix
  round then found two mutations that had been counted but never run. Spot-check the derivation.

## 6. Rules

- **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19). A finding that only asks for
  an implementation-coupled assertion is a **backlog note**, never CHANGES_REQUESTED.
- Do not redesign, do not weaken a row, do not invent rows.
- The 21 baseline failures are not yours; neither is the analytics drifter.
- Findings route into **one** grouped fix prompt — group by cause, rank blocking first.
- **Owner asleep, authorized unattended run.** On any card: give a recommendation and say whether
  the RATIFIED intention settles it. I rule what the intention determines and proceed provisionally
  on your recommendation where it does not. **I will not author a criterion row** — that is
  reserved to the owner — so if a finding needs one, say so and I will route it as a candidate.
- **This is the last batch of batch B.** If you approve, say so without hedging. If you request
  changes, be explicit about what genuinely blocks: a fix round is cheap, a third round is not.

## 7. Do not touch

The intention; the Scanner repository; the plans except one appended **Review log** entry each; the
master plan (§6.1 and §6.5 already carry today's corrections — report anything further); other
roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`. Do not modify source or tests.
Revert every probe and prove it byte-identical — especially any probe in approved code under §2. No
commits, no graph write, no L4.

## 8. Handoff

`SR/handoffs/reviewer/2026-09-21_batch_B2_review_1_handoff.md`. Frontmatter: `plan: batch B2 (6,
7)`, `role: review`, `round: batch_B2-review-1`, `state: APPROVED | CHANGES_REQUESTED`, `date`,
`actor`, `tree: ff39a96`. Sections:

1. **Verdict** and counts per phase and in total (of 88).
2. **Per-phase verdict tables**, one line per criterion row.
3. **The seven declined mutations** — your ruling on each, and what you ran.
4. **The five risk areas** (§1), each with a finding or a confirmation.
5. **Your judgment on the fold** (§4) and on the O1 decision (§3).
6. **Mutation audit**: declared vs executed, derived or typed, what you re-ran.
7. **Batch-level findings**, grouped by cause, blocking first; **backlog notes** separate.
8. **Any master-plan amendments** as final text, for me to write in.
9. **What you ran**, and the mutation-probe declaration.
10. `⚠ OWNER DECISIONS REQUIRED (n)` with recommendations, or `(0)`.

First line of your final message: `HANDOFF: … | STATE: … | OWNER_CARDS: n`, then a short summary
and the most important thing I should know.
