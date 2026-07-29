# Codex prompt — Phase 2 FIX CYCLE (review verdict: NEEDS_CHANGES)

You are fixing review findings on the Phase 2 implementation in the ManagerBeyo backend (`backend/`).
The independent review (Opus, commit `fb52e96`) returned **NEEDS_CHANGES**. The full findings, with
file:line references and reproduction probes, are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`.
Read that Review log FIRST, then the master plan's decisions (D3–D6), then this brief.

## Scope of this fix cycle — findings F1, F2, F3, F5 only

- **F1 (BLOCKING — rebuild contradicts D4).** `_reconstruct_shift_middle` feeds declared rows into
  the sweep as plain `paused` intervals, and `compute_linear_segments` awards overlapping-pause
  ownership to the EARLIEST interval. A declaration overlapping an earlier open step pause is
  erased from the rebuilt timeline — while the live reconcile (correctly) shows the declared
  reason. Fix so the rebuild honors D4 (declared outranks step pause) and the rebuilt timeline
  matches the live derivation for the reviewer's probe (step pause open 09:05, declaration 09:20,
  clock-out 09:50 → declared reason owns 09:20–09:50). Suggested direction: an explicit,
  **additive** priority in the sweep's ownership rule (e.g. optional priority field on
  `LinearInterval`, default preserving current behavior) — but the design is yours within the
  plan's constraints. `domain/analytics/linear_timeline.py` is shared domain code: check every
  caller (reconstruction, backfill scripts) and keep default behavior identical for non-declared
  input.
- **F2 (BLOCKING — `manually_recorded` leak).** Segment ownership of `manually_recorded` uses
  membership in `segment.record_ids`, which contains ALL active pauses, not just the owner. A
  step-sourced pause segment overlapping a declaration gets `manually_recorded = True`. Fix so
  only declared-OWNED segments carry `manually_recorded = True` and the declared reason —
  step-sourced segments stay `False` with the step reason. (F1's ownership fix should make this
  precise — solve them together.)
- **F3 (MAJOR — asymmetric idempotency guard).** The reconcile's no-op check re-verifies
  `reason`/`manually_recorded` only when the declared row is the source. Make the guard
  symmetric: an `IN_PAUSE` whose reason or `manually_recorded` no longer matches the current
  derivation (e.g. declaration closed, step pause with a different reason now open) must
  transition, not no-op.
- **F5 (MINOR — restore test coverage).** The midnight-safeguard test's open legacy
  `manually_recorded` "Late lunch" row was REPLACED by a declared row. Restore the legacy case
  ADDITIVELY (both variants covered): an open legacy manual pause surviving a shift close is
  exactly D7's "shifts open across the deploy" scenario.

## Explicitly OUT of this fix cycle

- **F4** (carve-out trap) and **F6** (unscoped declared lookup): latent until Phase 3 and now
  PINNED in Phase 3's plan (Clarifications section) with mandatory tests. Do not fix them here;
  do not remove the carve-out here.

## Protocol

1. Fix on top of `fb52e96`. Add regression tests for each finding — F1's probe and F2's assertion
   are the flagship tests; write them first, watch them fail, then fix.
2. Re-run the phase's full Validation plan + the master plan's baseline rule (no NEW failures vs.
   the recorded baseline; touched files ruff-clean).
3. Append a fix-cycle entry to the plan's Review log: per finding, what changed (file:line) and
   the test that pins it.
4. **Do NOT archive, do NOT write a summary, do NOT flip the master table.** The phase goes back
   to the reviewer first (`review_prompts/REVIEW_phase2_derivation.md` re-run) and is archived
   only on APPROVED — the previous premature archive has been unwound; do not repeat it.
5. Commit as one fix commit with a message referencing F1/F2/F3/F5.
