---
batch: D2
phases: [13A, 14]
role: review
round: 1
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
---

# Batch D2 review — phases 13A and 14. The last review in this project.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-reviewer.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_13A.md` (**37** rows / 7 criteria), `SR/plans/plan_14.md` (**5** rows / 2).
Intention: `SR/planning/intention.md` — **RATIFIED**, check its header; it wins over any plan.
Implementer handoff: `SR/handoffs/implementer/2026-09-22_batch_D2_implement_1_handoff.md`.

**42 rows in scope. Nothing is carried from a previous round — this is round 1.**

## What the tree is

Implemented at `f0b6e98` / `3ff4ea5` / `fcf2fb8`; docs-only after. 56 new tests.

**Verified by the orchestrator by hand — consume these, do not re-buy them:**

- **Gate L4: 23 failed / 3798 passed / 1 skipped**, both failure-ID diffs **empty** against the
  checked-in 23-ID baseline (`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`). Pass
  delta +56, reconciling exactly.
- **Perimeter exact.** `_events.py` and `stock_demand_request.py` both clean;
  `enums.py` carries `StockDemandDeletedOutcomeEnum` only and **no** `INLINE_REPAIR_TRIGGERS`.
- **The handoff re-issue is correct.** Pure rename at 100% similarity, old file unedited in
  `archived/`, new file carries `supersedes:`, `…match_preview_v2…` untouched.
- **Plan 14 C2(a) bites.** Three independent mutants — flip a nullable field to non-nullable, flip
  a non-nullable to nullable, delete a table row — each reddens that test alone.

**Spend your round on what I did not check.**

## The five things most likely to be wrong, and why

The implementer self-reported three rows that could not fail and fixed two. **That is the level to
match — assume there are more.**

1. **Rows that cannot fail.** This project's dominant defect class, by a distance: 26 of 30
   first-review FAILs across the pipeline were tests weaker than their row. For every row, ask what
   input would make it red and whether the fixture can produce it.
2. **L-41 — additive mutants are absorbed here.** A spurious write is overwritten by a later
   `UPDATE … RETURNING`; a spurious event is dropped by `coalesce_stock_report_events`. If a cell's
   mutant *adds* something, suspect it. But **do not apply this blanket** — five additive cells in
   these plans were measured and are **not** absorbed.
3. **L-42 — fixture discrimination is per row.** Audit every ordered assertion **individually**.
   The same defect was fixed in one plan and found untouched in its twin hours later.
4. **L-46 — a subset assertion is not a shape assertion.** Where a criterion says "exactly", the
   test must say `==`. A reviewer once replaced a whole event payload with junk and six tests passed.
5. **L-47 — plant the mutant at every surface the outcome passes through.** Three D1 mutants were
   absorbed because a second guard re-raised.

## Four things already settled — do not re-open them

Re-raising a settled item costs the round. Each of these is recorded with its measurement.

- **13A C5(b) mutant (i) is retired.** The ORM-staleness premise is **false** — measured on the
  production shape: `synchronize_session="auto"` → `"evaluate"`, the WHERE clause evaluates the same
  in Python as in SQL when the caller passes an enum member, so the identity map is synchronised.
  Replacement **(i-r)** arms the multi-row claim instead. The cascade's fresh `SELECT` **stays**,
  recorded "unobservable, not unnecessary" — **do not recommend deleting it.**
- **13A C5(g) does not arm the two sorts**, measured four times at two sizes. The positive half is
  armed; the sorts are met by §9 rule 9's structural check. **Do not try to force a deadlock red.**
- **Card D-3 is closed as "no change"** — phase 7 is not touched, deliberately.
- **`_events.py` mutation probes** are declared in 13A §4 as reverted probes, not edits. Check they
  were in fact reverted; do not read them as perimeter violations.

## The one question I most want answered

**13A's webhook deletes rows in a loop, with `actor_user_id=None`.** That path deletes *every*
assignment in *any* state, including ones a worker is actively holding, and it can delete several
rows in one request. **Is there a state this leaves inconsistent that no row asserts?** Check the
counters, the history records, the events, and `assert_stock_report_clean` across a multi-row
delete — not one row at a time.

## Standing rules

- **Never approve a batch a review failed**, and **never weaken a criterion to make a round pass.**
  Say a FAIL plainly.
- **You author no criterion row and edit no plan cell.** Recommendations and candidates go in your
  handoff.
- **Review by execution, not by judgement.** Every claim backed by a command whose output you paste.
  You may not discharge a mutation cell by reading a ledger.
- Route every finding: `production | verification | plan`.

## Environment

**Slot `BEYO_TEST_SLOT=d2r` on every pytest command** — every one. `pytest.ini` carries
`-n 6 --dist loadfile`, so even a one-file run claims six worker databases. **Never run two suites
at once, even on your own slot** (L-50: three concurrent runs on one slot reported 959 failures on a
clean tree earlier today).

## Deliverable

`SR/handoffs/reviewer/2026-09-22_batch_D2_review_1_handoff.md`: the verdict; PASS / FAIL /
NOT_VERIFIED per row; each finding with route and pasted evidence; your answer to the multi-row
question above; the perimeter check; one L4 with both ID diffs; owner questions under
`⚠ OWNER DECISIONS REQUIRED (n)`.

**Report what you could hide.** Every session in this batch has — a fabricated placeholder SHA, an
arithmetic error in one of my prompts, a measurably false claim I folded into a plan cell, a probe
of mine that overruled a correct agent finding because it passed a string where production passes
an enum, and three concurrent test runs of mine that faked a catastrophe. That norm is the point.

**Never push. Commit with explicit paths, never `git add -A`.**
