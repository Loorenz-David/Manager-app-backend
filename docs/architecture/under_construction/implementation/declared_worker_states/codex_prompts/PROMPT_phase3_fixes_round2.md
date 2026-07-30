# Codex prompt — Phase 3 FIX CYCLE, ROUND 2 (review verdict: NEEDS_CHANGES — one code finding)

You are fixing the round-2 review finding on the Phase 3 implementation (`backend/`). Round 1
(K1–K4) is fixed and mutation-test-verified at commit `820e175` — keep those tests green. The
findings are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md`.

## L1 (MINOR — the only code change): K1's root cause survives at the reconcile's own call site

`reconcile_worker_shift_state.py` (~lines 79–89) re-implements the open-shift locked select inline
instead of calling `load_open_worker_shift_for_update`, so the analytics-worker path
(`process_step_transition.py` → reconcile) still carries the EvalPlanQual false-`None` race that
K1 fixed for the HTTP commands. Reviewer-proved consequence: a concurrent reconcile can return
`changed=False, state=None` for a clocked-in worker — with open WORKING steps it self-heals via
the existing `IntegrityError` retry; with none, a live projection update is silently dropped
until the next trigger.

**Fix:** delegate the inline select to `load_open_worker_shift_for_update` (the K1-hardened
helper). Preserve exact semantics otherwise (same lock, same transaction position, lock order
shift row → declared row unchanged). While there, extend the helper's mechanism comment with the
known limitation the reviewer noted: the retry is bounded (one re-select), so pathological
sustained contention can still yield a false `None` — accepted; every caller either surfaces a
retryable conflict or self-heals on the next trigger, and the clock-out rebuild is always
correct.

**Required test:** two-session probe on the RECONCILE path mirroring the reviewer's: concurrent
declare + reconcile for one clocked-in worker → the reconcile must never return
`state=None`/no-op due to the race (assert repeat-run stability like the K1 tests). Mutation
check: with the helper's retry removed, this test must fail.

## L2 — already fixed by the operator (do not touch)

The master plan's stale "Phase 3 completed and archived" progress note is superseded. Reminder
stands: **do NOT archive, do NOT write a summary, do NOT flip the master table, do NOT touch the
handoff** — the phase archives ONLY after the reviewer returns APPROVED.

## Protocol

1. Fix on top of `820e175`. Test first (must fail against the inline select via the same
   mutation-style check the reviewer used), then delegate.
2. Re-run the phase Validation plan + baseline rule (no NEW failures vs. baseline; K1–K4 tests
   green; touched files ruff-clean).
3. Append a round-2 fix entry to the plan's Review log.
4. One fix commit referencing L1.
