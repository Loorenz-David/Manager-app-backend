---
batch: D1
phases: [12, 13, + an owner-authorized amendment to APPROVED phase 3]
role: re-review
round: 2
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
---

# Batch D1 re-review — delta-scoped

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-reviewer.md` ← **this is the correct filename.** Round 1's
  prompt cited `independent-reviewer.md`, which does not exist. My error, flagged by that
  reviewer, fixed here.
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_12.md`, `SR/plans/plan_13.md`. Intention: `SR/planning/intention.md` —
**RATIFIED**, check its header, and it wins over any plan.

## This is a delta re-review. Round 1 settled 58 of 64 rows and they are not re-opened.

Round 1 (`SR/handoffs/reviewer/2026-09-21_batch_D1_review_1_handoff.md`) returned
**CHANGES_REQUESTED, 58 PASS / 2 FAIL / 4 NOT_VERIFIED**. Two fix rounds have since landed. **Your
scope is the delta and its blast radius, not the batch.**

### In scope

| # | What | Where |
|---|---|---|
| 1 | **The production fix** (finding B-1 / owner card D-5) | `consistency.py`, one predicate |
| 2 | **Plan 12 C3(d)** — was `BLOCKED-PRODUCTION`, should now PASS | the witness test |
| 3 | **Plan 13 C4(a)** — was FAIL (S-1), fixture rebuilt | `test_list_stock_task_assignments.py` |
| 4 | **Plan 13 C2(a)** — gained a `target_kind` assertion (N-4) | `test_delete_stock_report_item.py` |
| 5 | **L-45 re-confirmation** | see below |

### Explicitly out of scope

The other 58 rows, the perimeter of the original implementation, and every owner card already
ruled (D-1 … D-11 in `SR/OWNER_CARDS_batch_D.md`). **Do not re-litigate them.** New findings are
welcome; re-raising settled ones costs the round.

## Item 1 — the production fix, and the thing to actually check

**The owner's ruling, verbatim:** *"yes i approve the fix ( only assignment reconciliation against
goal records )."*

The change is one predicate on the `histories` selection in
`app/beyo_manager/services/queries/stock_report/consistency.py`, so the `goal_total` rule is
computed over `StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE` records only.

**What I already verified by hand — consume, do not re-buy.** Gate L4 at **23 failed / 3740
passed / 1 skipped**, failure-ID diff **empty in both directions** against
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`. Reverting the predicate reddens
**exactly** `test_the_priority_record_snapshots_the_live_awaiting_counter` and nothing else in its
file (1 failed / 15 passed); restored with `git diff --quiet` exit 0. So the fix is load-bearing
and the witness is a real guard.

**The repair was deliberately NOT changed, and you should test that judgement.** My reasoning:
`repair_stock_report` obtains its divergence list *only* from `compute_stock_report_divergences`
(`:170`, `:217`, `:294`) and never builds one, so a second type guard on its `UPDATE` would be an
**unreachable mirror no test could arm** — the shape this project recorded as **L-37**. **Prove me
wrong or confirm me**, by execution.

**Three consequences to check that the "one predicate" framing hides.** The implementer flagged
the first itself rather than letting you find it:

1. **The repair no longer locks records it can no longer touch.** `repair_stock_report` derives
   which history records to lock from the divergence list. Narrowing the list narrows the lock
   set. Correct, probably — but is there a path where a *goal* record's repair needed a lock on a
   sibling record that is now unlocked?
2. **`get_stock_report_consistency`** is the third consumer — a **read endpoint**. Does any
   ratified text or published contract say it reports on all record types? If a client reads that
   endpoint, its payload just got narrower.
3. **Neither the `histories` selection nor `_recompute_goal_totals_for_workspace` filters
   `is_deleted`.** MC-5 says the goal total counts *"all assignments credited to it, **deleted
   included**"*, so including deleted assignments is correct — but a **soft-deleted goal record**
   is still reconciled, and phase 13's cascade soft-deletes history records. Is that right? The
   implementer recorded it as a candidate rather than acting. **Route it; do not author a row.**

## Item 5 — L-45, and why this re-review is not a formality

**Every mutation observed in round 1 and in the verification fix round ran against a suite that
was already red by one test.** A mutation run against an already-red suite proves less: a second
red can hide inside the first, and a test that was going to fail anyway cannot demonstrate it
failed *for the mutation's reason*.

The suite is green now (bar the known 23). **Re-confirm the mutations that the fix's blast radius
touches** — at minimum C3(d)'s, C4(a)'s three ordering runs, and C2(a)'s `target_kind` run. You
need not re-run the whole campaign.

**C4(a) specifically:** its `created_at` term was green under a `client_id`-only ordering five
times before the fixture was rebuilt. Confirm it is red now. Its `client_id` **tiebreaker** is a
ruled **EQUIVALENT** (owner card D-11) — *unobservable, not unnecessary*, because today's query
plan feeds a stable sort in insertion order. **Do not try to force it and do not recommend
deleting the clause.**

## Standing rules

- **Never approve a batch a review failed**, and **never weaken a criterion to make a round
  pass.** If this round fails, it is a **second** `CHANGES_REQUESTED` on one batch — §3A says that
  is not automatic: the coordinator stops and relays each finding to the owner. Say so plainly
  rather than softening a verdict to avoid it.
- **You author no criterion row and edit no plan cell.** Recommendations and candidates go in your
  handoff. Three rows are already queued to be authored *after* this gate (owner cards D-8, D-1,
  D-7) — that sequencing is deliberate, so **do not treat their absence as a gap.**
- **Review by execution, not by judgment.** Every claim backed by a command whose output you
  paste. You may not discharge a mutation cell by reading a ledger.
- Route every finding: `production | verification | plan`.

## Environment

**Slot `BEYO_TEST_SLOT=dr2` on every pytest command** (`pytest.ini` carries `-n 6 --dist loadfile`).
Baseline: the checked-in 23-ID file. **Expected L4: 23 / 3740 / 1** — note **3740**, not 3739: the
witness moved from the failed column to the passed column, it was not removed. That correction is
the implementer's; my own prompt had it wrong.

## Deliverable

`SR/handoffs/reviewer/2026-09-22_batch_D1_rereview_1_handoff.md`: the verdict; PASS / FAIL /
NOT_VERIFIED for the rows in scope and a one-line statement that the other 58 are carried from
round 1; each finding with route and pasted evidence; your answers to the three consequence checks
and to the repair-mirror question; the perimeter check; one L4 with both ID diffs; owner questions
under `⚠ OWNER DECISIONS REQUIRED (n)`.

**Report what you could hide.** Every session in this batch has, including a fabricated
placeholder SHA and an arithmetic error in my own prompt.

**Never push. Commit with explicit paths, never `git add -A`.**
