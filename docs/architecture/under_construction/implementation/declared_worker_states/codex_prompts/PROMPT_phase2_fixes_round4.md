# Codex prompt — Phase 2 FIX CYCLE, ROUND 4 (review verdict: NEEDS_CHANGES)

You are fixing round-4 review findings on the Phase 2 implementation (`backend/`). Rounds 1–3
(F*, G*, H1/H2/T1) are fixed and independently verified — keep their tests green; do not revisit.
The remaining findings are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`.
Read that first, then this brief. Both findings carry an OPERATOR DECISION below — implement the
decision; if you believe a decision is wrong, STOP and ask, do not substitute your own.

## Findings in scope

- **I1 (MEDIUM).** The `changed_by_id IS NOT NULL` legacy predicate applies retroactively: open
  manual rows whose `changed_by_id` was already NULLed by a pre-Phase-2 heal run (established as
  having happened in production) are misread as declared projections → clobbered → `/resume`
  409s. H1 fixed the producer; nothing repairs already-laundered rows.
  **OPERATOR DECISION — one-time repair data migration, shipped in this phase.** Key soundness
  argument: `user_declared_state_records` has NEVER had a writer (Phase 3 is unshipped), therefore
  every `manually_recorded = TRUE` row in `user_shift_state_records` today is legacy by
  construction — the repair cannot misclassify. Alembic data migration: for rows with
  `exited_at IS NULL AND state = 'in_pause' AND manually_recorded AND changed_by_id IS NULL`,
  set `changed_by_id = user_id` (the worker paused themself — `/pause` is worker-only, so
  `user_id` is the correct actor). Open rows only (closed rows never reach the stickiness
  predicate). Idempotent; downgrade documented no-op (provenance restoration is not reversible
  and not harmful). **D7 note:** the plan lists "no data migration of legacy `manually_recorded`
  rows" as a non-goal — this narrow provenance repair is an operator-authorized deviation (D7's
  intent was reason/semantics freezing, not provenance metadata); amend the plan's Non-goals
  line to record the authorized exception.
  **Required test:** seed an open manual row with `changed_by_id = NULL` (the laundered state) →
  run the migration's repair → reconcile → `changed=False`, row intact, `/resume` callable.
- **I2 (MEDIUM).** `_LEGACY_MANUAL_PAUSE_PRIORITY = 1` makes a legacy manual pause outrank an
  EARLIER open step pause at rebuild (baseline: one merged segment with the step reason; now:
  split at the manual pause's start).
  **OPERATOR DECISION — KEEP the new behavior, document it, pin it.** Rationale: the worker's
  explicit `/pause` is declared intent and outranking step state matches D4's spirit; it also
  keeps legacy manual consistent with declared-state priority at rebuild (one rule, not two).
  Add the behavior + rationale to the plan's Scope/Assumptions, and pin with a test asserting the
  reviewer's probe: step pause open 09:05, `/pause` 09:20, clock-out 09:50 → two segments split
  at 09:20, second carries the manual reason + `manually_recorded=True`.
- **I3** — already fixed by the operator (master plan progress note superseded). No action.
- **I4** — informational per the reviewer. No action.

## Protocol

1. Fix on top of the current HEAD. Tests first (I1 laundered-row test, I2 split-pin test), watch
   them fail, then implement (migration + plan doc edits).
2. Re-run the full phase Validation plan + baseline rule (no NEW failures vs. baseline; all prior
   rounds' regression tests green; touched files ruff-clean). `alembic upgrade head` +
   `downgrade -1` + `upgrade head` must stay clean on the dev DB.
3. Append a round-4 fix entry to the plan's Review log (per finding: change + pinning test).
4. **Do NOT archive, do NOT write a summary, do NOT flip the master table** — the phase returns to
   the reviewer (`review_prompts/REVIEW_phase2_derivation.md`) and archives only on APPROVED.
5. One fix commit referencing I1/I2.
