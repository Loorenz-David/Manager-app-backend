---
plan: 1
role: reviewer
round: 3 (delta-scoped re-review after fix r3)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Re-review round 3 — plan 1 (delta-scoped, minimal)

This should be the shortest round of the phase. Fix r3 was test/docs only: three
exact status assertions (your S6 correction, your measured values), the README
section move (your N-i), the table separator + restored mirror comment (your
N-j), and the fixture rename (your N-l). Everything else was settled in your
rounds 1–2. Verify the closures, probe once, run the suite, and give the verdict.

## Read first

1. Your r2 handoff — S6, N-i, N-j, N-l are the acceptance list.
2. `handoffs/implementer/2026-08-17_phase1_fix_r3_handoff.md` — F1–F4 + the
   one-probe ledger.

## Scope

1. **Perimeter:** `git diff 7f09637 99ade31` — expected: the E2 test file, the
   README, one comment line in the mirror test, pipeline docs. Anything else is
   a finding. **No-weaker-assertions check (master plan §6):** diff the E2 test
   seam for any assertion weaker than at `7f09637` — the round must only have
   strengthened.
2. **S6 closed?** Read `test_budget_allocations_query.py:192-194` against your
   prescribed values. Re-apply YOUR probe 5 (drop `unevaluated_task_item` /
   `unevaluated_valuation` from `add_all`) — the exact-status assertions must go
   red. Revert.
3. **N-i / N-j hand-checks:** the E2 detail section now sits in the
   `/api/v1/item-…` path region (before item-upholsteries), the working-sections
   block is whole again, the E2 422 table has its header-separator row (renders
   as a table), and the worker-service sentence is restored above the
   budget-status mirror row.
4. **Suite (P-L):** `PYTHONPATH=. pytest -q -m 'not e2e'` — expect 26 failures =
   the 23 baseline IDs byte-identical + the 3 foreign bootstrap IDs.

## Out of scope

Everything settled in rounds 1–2 (M1/M2, the S1 seam, S2–S5, lettered map) —
report only if something wrong crosses your path.

## Verdict + handoff

`handoffs/reviewer/2026-08-17_phase1_rereview_r3_handoff.md` — frontmatter
(`plan: 1, role: reviewer, round: 3, state: REVIEWED, verdict:
APPROVED | CHANGES_REQUESTED, actor: <model>`), write perimeter (that one file),
closure table (S6, N-i, N-j, N-l), your probe result, suite totals + diff,
`⚠ OWNER DECISIONS REQUIRED (0)` expected. If everything closes, say APPROVED
plainly — the closeout ritual is the coordinator's.
