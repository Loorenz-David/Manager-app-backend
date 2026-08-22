---
plan: 1
role: implementer
round: 1c (second fix round — close the mutation ledger)
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Implement round 1c — plan 1: make every criterion's mutation bite

Round 1b's complete mutation ledger (your own, honest, correct to produce) exposed
**9 surviving mutations and 5 uncovered criteria** — fourteen criterion-rows whose
tests are currently decoration. This round closes all fourteen. It is test-only,
with ONE exception: where a new fixture proves the production code violates M1/M2
as contracted, you fix production AND record the defect per-site in the handoff.
That exception matters most for C9c and C9d — their survivals mean the D9
group-window admission and the `percentile_cont` + half-even statistic are
currently UNPROVEN in production; your new fixtures adjudicate.

## Read first

1. `plans/plan_1.md` — criteria C9b–C9e, C10, C11 as amended (the P1 padded-fixture
   matrix with its worked example), and the Review log's r1b-consumption entry.
2. `planning/intention.md` §3 (M1) — the group/window/rounding contracts your
   fixtures must pin.
3. Your r1b handoff's ledger — the 9 SURVIVED rows and 5 NOT COVERED rows are the
   work list.

## Work list (all fourteen rows; each ends with an observed-red record or a
recorded equivalence STOP)

**Uncovered criteria — write the tests as specified in the plan:**
- **W1 / C9b** — group aggregation: one task, same section, 3600s + 600s completed
  steps ⇒ ONE sample of 4200 (padded per the plan's worked example: fillers
  `{1000, 2000, 5000, 6000}` ⇒ median 4200). RED: drop `task_id` from the GROUP BY
  ⇒ median 2800. (r1b's GROUP-BY probe produced a transaction error on an
  unrelated node — this fixture makes the arithmetic bite, not the transaction.)
- **W2 / C9c** — group-window integrity: first pass closed 100 days ago, rework
  closed yesterday, same task+section ⇒ one in-window sample of the FULL sum.
  RED: per-step `closed_at` admission ⇒ rework-only sample, wrong median. **If
  production already admits per-step, that is a production defect against M1 —
  fix it and record.**
- **W3 / C9d** — even-count rows exactly as the plan pins them: middles
  `{1000,1003}` ⇒ 1002 (RED: `percentile_disc` ⇒ 1000) and middles `{1000,1001}`
  ⇒ 1000 (RED: `::numeric`/half-away rounding ⇒ 1001). **If production uses disc,
  an int cast, or a numeric-cast round, that is a production defect — fix and
  record.**
- **W4 / C10** — each contributing-step exclusion bites independently: one
  non-completed step and one marked-wrong step INSIDE an otherwise-qualifying
  group, each moving the group's pinned sum when its predicate is removed. RED per
  row: remove exactly that predicate.
- **W5 / C11** — the boundary as specified: 4 qualifying groups ⇒ `null` +
  `sample_count: 4`; adding a 5th ⇒ non-null pinned value. RED: `<` → `<=`.

**Surviving mutations — strengthen the fixture until it bites (or prove
equivalence):**
- **W6 / C6** — fixture must include allocated steps in states OTHER than
  `pending` (e.g. `working`, `paused`, `completed`) with pinned allowances, so
  freezing the partition to `state == PENDING` changes the output.
- **W7 / C10a-C10b at the pure/M2 level if applicable** — r1b probed these at the
  C9 node; after W4 they bite at their own rows. Re-run both probes.
- **W8 / C13b-door2** — give the pure-function fixture BOTH a deleted+skipped
  step (must be invisible to `C`) and a non-deleted skipped step (must be
  charged), pinned figures, so adding deletion-exclusion to the charged partition
  changes `D`.
- **W9 / C16** — diagnose WHY the at-fifty test tolerated `>=`: read the route's
  cap check and the test's request. Likely causes: the mutation was applied where
  the monkeypatched `run_service` bypasses it, or the test sends ≠50 ids. Fix
  test (or probe site) so `>=` rejects 50 and turns the at-fifty row red.
- **W10 / C20** — analyze whether the empty-allocated-set guard is genuinely
  redundant (iterating an empty allocated set may naturally produce no allowances
  and no division). If behavior WITH and WITHOUT the guard is provably identical
  on every C20 fixture, record the equivalence analysis as a STOP item proposing
  the criterion's mutation be re-negotiated (e.g. named mutation becomes "make
  the empty set take the division path with Σw=0 short-circuited to equal
  weights") — do NOT add a fixture that only exists to justify dead code, and do
  NOT delete the guard yourself.

## Discipline

- Every new/changed test: teardown owned (rule 11½), fixtures padded per P1,
  pinned integers, distinct values.
- Re-run the FULL named-mutation ledger for every row touched this round:
  mutation (byte-reproducible) → test node → exact red line → revert. The handoff
  ledger must end with ZERO surviving rows that lack either a red record or a
  W10-style recorded equivalence STOP.
- Updated criterion→test map with zero "NOT COVERED" rows.
- Full suite from `backend/app/`: `PYTHONPATH=. pytest -q -m 'not e2e'` —
  expected failures: the 23 baseline IDs + the 3 foreign
  `test_seed_item_economics_configuration.py` IDs + zero others. Record totals +
  full failure list.
- Perimeter: your four phase test files + (only under the W2/W3 production-defect
  exception) `get_working_section_typical_times.py`, with each production change
  recorded per-site in the handoff. Nothing else. No graph changes.

## Checkpoint + handoff

`CHECKPOINT (not approved): plan1 implement r1c — mutation ledger closed`.
Handoff: `handoffs/implementer/2026-08-16_phase1_implement_r1c_handoff.md` —
frontmatter (`round: 1c, state: IMPLEMENTED`), checkpoint hash, write perimeter,
W1–W10 outcomes (including the W2/W3 production verdicts stated explicitly:
"production complied" or "production defect found and fixed: <site, diff
summary>"), the closed ledger, the updated map, suite totals + failure list,
STOP items (W10 analysis if applicable).
