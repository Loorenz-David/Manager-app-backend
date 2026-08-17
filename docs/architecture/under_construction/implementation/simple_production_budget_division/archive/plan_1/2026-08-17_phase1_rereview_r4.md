---
plan: 1
role: reviewer
round: 4 (delta-scoped re-review after fix r4)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Re-review round 4 — plan 1 (S7 only; final gate)

One finding to close. Fix r4 was a single test-file change adding the
tenant-boundary row (your S7 → criterion C14d). Everything else in the phase is
settled across your rounds 1–3. Verify this one closure, then give the verdict —
if it closes and nothing new crosses your path, this is the approval.

## Read first

1. Your r3 handoff — S7 and its correction sketch.
2. `handoffs/implementer/2026-08-17_phase1_fix_r4_handoff.md` — F1 outcome, the
   one-probe ledger, the residue-table declaration.
3. `plans/plan_1.md` — C14c/C14d as split by the coordinator (letter-verification
   rule), and the r4-consumption Review log entry (the coordinator re-ran your
   probe independently; its result is recorded there).

## Scope

1. **Perimeter:** `git diff 99ade31 1290cc0` — expected: the E2 test file plus
   pipeline docs, and **no production file**. Note the tree carries the owner's
   unrelated `bootstrap_app.py` edit, so scope any diff check to the phase's own
   paths (the implementer flagged this honestly; the overbroad check was the
   coordinator's wording).
2. **No-weaker-assertions check (§6):** the E2 test seam must have moved only in
   the additive direction versus `99ade31`.
3. **S7 / C14d closed?** Read the fixture's foreign `Workspace` + `Task`, the
   four-id call, the absence assertion, and the retained `len(...) == 2`. Then
   **re-apply your own probe** — delete `Task.workspace_id == ctx.workspace_id`
   from E2's visibility query (now at `get_task_budget_allocations.py:65-69`) —
   observe red, revert, confirm byte-identity. Judge whether the row guards the
   boundary the finding named, not merely something.
4. **Teardown (rule 11½):** the foreign task is deleted before the foreign
   workspace, the fixture's declared residue tables cover what it commits, and no
   foreign-workspace rows survive a run against the configured DB.
5. **Suite (P-L):** `PYTHONPATH=. pytest -q -m 'not e2e'` — expect 26 failures =
   the 23 baseline IDs byte-identical + the 3 foreign bootstrap IDs.

## Out of scope

Everything settled in rounds 1–3 (M1/M2, the S1 seam, S2–S6, the README, the
lettered map); the probe-4 equivalence you already recorded as never-reopen; the
foreign bootstrap work; frontend handoffs (coordinator closeout).

## Verdict + handoff

`handoffs/reviewer/2026-08-17_phase1_rereview_r4_handoff.md` — frontmatter
(`plan: 1, role: reviewer, round: 4, state: REVIEWED, verdict:
APPROVED | CHANGES_REQUESTED, actor: <model>`), write perimeter (that one file),
S7/C14d closure with your probe result, teardown judgement, suite totals + diff,
`⚠ OWNER DECISIONS REQUIRED (0)` expected.

If this closes, say **APPROVED** plainly and add one short section — *"Closeout
inputs"* — listing anything the coordinator should carry into the approval gate
from your four rounds: the K5 graph-delta note, the recorded equivalences
(C13b-door2, C20, probe-4) so a future session does not re-open them, and any
contract text you believe the frontend handoff fold must state (e.g. the N-h
`actual_worker_seconds` null on unevaluated tasks). Keep it to what closeout
needs; the phase's own record already lives in the plan.
