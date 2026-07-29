# Codex prompt — Phase 2 FIX CYCLE, ROUND 3 (review verdict: NEEDS_CHANGES)

You are fixing round-3 review findings on the Phase 2 implementation (`backend/`). Rounds 1–2
(F1/F2/F3/F5, G1/G2/G3) are fixed and independently verified at commit `d8a123a` — keep their
tests green; do not revisit. The remaining findings are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`.
Read that first, then this brief.

## Findings in scope

- **H1 (MEDIUM — fix required).** The G1 provenance rule (`manually_recorded AND changed_by_id IS
  NOT NULL` = legacy manual) is not an invariant: `_reconstruct_shift_middle` re-emits EVERY
  rebuilt record with `changed_by_id = None` — including legacy manual segments — and
  `scripts/backfill/heal_open_shifts_today.py` rebuilds an open shift then reopens the tail row
  (`exited_at = None`). A re-emitted `/pause` row therefore reads as a reconcile-authored
  declared projection, stickiness is lost, and the next reconcile drops the worker to `IDLE` —
  `/resume` then 409s. Operationally reachable: the heal script is documented safe-to-re-run and
  has been used on production data.
  **Fix (small, reviewer-suggested):** when re-emitting a segment whose owner id is in
  `manual_ids` (a legacy manual row), carry the original row's `changed_by_id` through instead of
  `None` — or use a provenance signal the rebuild cannot launder. Either way the G1 rule and the
  rebuild must agree.
  **Required test:** seed an open `/pause` row → run the heal script's rebuild-and-reopen body →
  reconcile → `changed=False`, row still `IN_PAUSE` with its reason and `manually_recorded=True`,
  `/resume` still callable. Assert parity with the pre-Phase-2 baseline behavior.
- **H2 (INFORMATIONAL — docs only).** Plan line ~35 claims legacy stickiness against `IDLE` and
  step-`IN_PAUSE`; the code actually makes a legacy `/pause` row suppress a DECLARED projection
  too (declaration never reaches the live timeline while the manual row is open). Unreachable in
  Phase 2 and both constructs retire together in Phase 3 — do NOT change behavior; make the plan
  sentence state what the code does (legacy manual row is sticky against everything; declared
  projections included; retired with Phase 3).
- **T1 (test-debt from the review — commit the repro).** The reviewer has now manually re-run the
  F1 "both sources still open at clock-out" repro in two consecutive rounds because no committed
  test covers it: step pause OPEN at 09:05 (catalog reason) + declaration OPEN at 09:20
  (different reason), clock-out 09:50 → rebuild must yield `IN_PAUSE 09:05→09:20` (step reason,
  `manually_recorded=False`) then `IN_PAUSE 09:20→09:50` (declared reason,
  `manually_recorded=True`). Commit it as a permanent regression test (the existing F1 test uses
  a CLOSED step pause — keep both).

## Protocol

1. Fix on top of `d8a123a`. Tests first (H1 heal-body test, T1 repro), watch them fail (T1 should
   pass immediately if F1's fix is complete — if it fails, that is a finding to fix), then fix H1.
2. Re-run the full phase Validation plan + baseline rule (no NEW failures vs. baseline; all
   round-1/2 regression tests green; touched files ruff-clean).
3. Append a round-3 fix entry to the plan's Review log (per finding: change + pinning test).
4. **Do NOT archive, do NOT write a summary, do NOT flip the master table** — the phase returns to
   the reviewer (`review_prompts/REVIEW_phase2_derivation.md`) and archives only on APPROVED.
5. One fix commit referencing H1/H2/T1.
