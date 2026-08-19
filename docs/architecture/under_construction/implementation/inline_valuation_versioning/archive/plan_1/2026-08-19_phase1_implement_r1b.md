---
plan: 1
role: implementer
round: 1b (continuation — r1 blocked on a coordinator scoping error)
date: 2026-08-19
pipeline: inline_valuation_versioning
---

# Implement round 1b — plan 1 (inline valuation versioning)

**You were right to stop.** HC-1 said three files; the identity is published in a fourth.
The perimeter constraint did its job, and exceeding it silently would have been the worse
outcome. The error was the coordinator's: the verification grep behind HC-1 was run from
`backend/app/`, so `backend/docs/` was never searched.

**No owner decision was needed and none was taken.** D-AUTH already authorized retiring
the identity; removing it from the document that publishes it follows from that decision
rather than being a new one. HC-1 is corrected to **four files** under the same rationale,
with provenance recorded in intention §1.

Resume from a clean tree. Nothing from r1 needs undoing.

## What changed since your prompt

1. **HC-1 is now FOUR files.** The fourth is
   `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`.
2. **The document edit is specified — do not design it.** Intention **§3.1** states it
   exactly. In short: **rewrite, do not delete.** §9.1 (`:675-691`) is a titled subsection
   — *"The refusal — an existing item that already has a price"* — whose body and closing
   "rule in one line" all assert the retired behaviour. Deleting the two offending lines
   would leave the document silent about what now happens and strand a false rule.
   Validation step 4 (`:725-726`) is rewritten into two checks.
3. **Plan 1 gains T2b and C10**, and C9 is restated: the identity must be absent from
   `app/` and from `docs/handoff/`. It **stays** in `item_cost_calculation`'s planning and
   archive documents — those are provenance of a decision that was true when written and
   **must not be touched**.
4. **The baseline is corrected to 2314 passed / 26 failed / 1 deselected** (2340 selected).
   Your r1 figure was right; the plan's 2313 was stale. The +1 relative to the previous
   pipeline's closeout is **unexplained** and recorded as such — diff failure IDs, never
   totals.

## Everything else stands

Read the prompt for r1 (`…/2026-08-19_phase1_implement_r1.md`) for the rest: HC-2 (one
valuation writer), HC-3 (no schema change), HC-4 (the no-op writes nothing at all), D17
(inherit an omitted field), D18 (currency is part of the comparison), the named mutations
for C2/C3/C5, and why C4 exists.

Two reminders that now matter more:

- **C4 is the row that catches a fixture confound.** C2 and C3 each hold for a second
  independent reason; C4 (a partial request whose inherited field makes the triple
  identical) is the only row neither can cover.
- **You are removing a test and rewriting a published document.** The handoff must map
  each behaviour the rejection test used to pin onto whatever now covers it, and must state
  what §9.1 says now.

## Suite

From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`. Start point **2314 / 26 / 1**.
State the arithmetic explicitly — selected before, tests removed, tests added, selected
after — since this phase removes a test and the total dips before it rises. The configured
DB also accrues ~24 `task_steps` per full run from tests outside this pipeline; never read
a changed row count as evidence of a code change.

## Checkpoint and handoff

`CHECKPOINT (not approved): inline valuation versioning`, and
`…/handoffs/implementer/2026-08-19_phase1_implement_r1b_handoff.md` with the fields the r1
prompt lists — full perimeter **generated from `git`**, suite arithmetic and failure-ID
diff, observed-red output per named mutation, the C1–C10 table, the deleted-assertion
mapping, and **DECISIONS I HAD TO MAKE**.
