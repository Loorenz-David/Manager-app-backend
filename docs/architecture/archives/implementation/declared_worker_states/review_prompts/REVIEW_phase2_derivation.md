# Review prompt — Declared Worker States, Phase 2: derivation integration

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification: try to find where the implementation deviates from the plan or breaks an invariant. Do not fix anything — report.

## Inputs

- Master plan (decisions D3–D6 govern this phase): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read the master decisions, then the phase plan in full.
2. Read the diff completely; map every acceptance criterion to concrete evidence (code + test). Missing evidence = finding.
3. Re-run the plan's Validation plan commands yourself — especially the **unchanged legacy suites** (deploy-neutrality is this phase's core promise).
4. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] `derive_target_state` precedence is exactly D4 (working > declared > step-paused > idle); still pure (no imports of session/models); exhaustive unit table extended; **every call site** updated to the new signature.
- [ ] Reconcile loads the open declared row `with_for_update()` and in the documented lock order (shift row FIRST, then declared row) — a code comment states the order.
- [ ] Declared-sourced `IN_PAUSE` derived records carry `reason = pause_reason_id` AND `manually_recorded = True`; step-sourced pauses unchanged (`manually_recorded = False`, earliest-open-paused-step reason).
- [ ] Transition to `WORKING` closes the open declared row with `closed_by_id = NULL` (system-closed) — and ONLY on `WORKING` (an `IDLE` target must not close it; that would break the "declared outranks idle" invariant — the target can't even be `IDLE` while declared is open; verify the derivation makes that unreachable).
- [ ] Legacy manual-pause stickiness carve-out is STILL PRESENT (removal is Phase 3 — premature removal is a blocking finding).
- [ ] Reconstruction: declared query uses the same window scoping as the manual query (`entered_at >= shift_start AND < shift_end`); open declared row passes `exited_at=None` (sweep clamps); declared ids unioned into the `manually_recorded` re-emission set; legacy manual-rows query still present; module docstring updated.
- [ ] Clock-out clamps the open declared row to exactly `clock_out_at` with `closed_by_id = NULL`, under `FOR UPDATE`, before/independent of reconstruction; midnight-safeguard path covered by a test (clamp at 00:00).
- [ ] The `_sweep` priority verification finding is recorded in the Review log (mandatory per the codex prompt).
- [ ] Reconcile emits no events and does not commit (subordinate rule).
- [ ] Deploy-neutrality: full existing worker-shift/worker-stats/connecteam/analytics suites pass without modification of their assertions (test edits should be additive; assertion changes to make old tests pass = blocking finding).
- [ ] Ruff clean.

## Adversarial probes (attempt at least these)

- Declared row + open working step simultaneously (race residue): does derivation yield `WORKING` and close the declaration?
- Two reconciles racing on the same worker with a declared row: can the unique open-shift index or a double-close occur? (Check the existing retry path still covers the new code.)
- Reconcile idempotency with declared open: second call writes nothing.

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
