# Codex prompt — Phase 3 FIX CYCLE (review verdict: NEEDS_CHANGES)

You are fixing review findings on the Phase 3 implementation (`backend/`). The findings, with
mechanism analysis and probes, are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md`.
Read that first, then this brief. The implementation is committed (see `git log` — the phase
commit lands just before this brief's commit).

## K1 (MAJOR — the real fix): concurrent declare returns a false 409

Mechanism (proven by the reviewer under READ COMMITTED): session B's
`SELECT … WHERE exited_at IS NULL FOR UPDATE` blocks on the open shift row locked by session A;
A's reconcile closes that row (`exited_at = now`) and inserts a replacement open row; on A's
commit, B's EvalPlanQual re-check filters the now-closed row and **never rescans** — B sees
`None` although the worker is clocked in. `declare` maps `None` → `409 "Worker must be clocked
in"` (and the handoff tells the frontend to offer clock-in — a double-tap becomes a wrong
clock-in prompt). `close_declared_worker_state` hits the same artifact and silently proceeds
without the shift-row lock, defeating the documented lock order.

**Fix — bounded retry-on-None re-select.** The reviewer's probe showed an immediate identical
re-select in the same transaction finds the replacement row (fresh statement snapshot under READ
COMMITTED). Implement in `load_open_worker_shift_for_update` (shared helper): if the first locked
select returns `None`, re-run it exactly once and return that result. Genuinely-not-clocked-in
workers cost one cheap extra SELECT; the race window collapses. Comment the mechanism (EPQ +
partial-index replacement row) at the retry site. This also hardens the pre-existing callers
(`/clock`, clock-in/out) that carry the same latent race — in scope, since this phase put two new
HTTP write paths on the helper.

**Required tests (the plan's Risks §1 promised these):** two-session concurrency tests for BOTH
commands mirroring the reviewer's probe — concurrent declares for one clocked-in worker → one
declares, the other either succeeds-as-switch or conflicts on the DECLARED row, but NEVER
"must be clocked in"; concurrent close+declare → lock order holds, no silent lock loss. Assert
5-run stability if the harness allows repetition.

## K2 + K3 (MINOR): commit the two plan-mandated tests

Behavior is already correct (reviewer probed both) — the tests are simply absent:
- Closing a declaration does NOT resume auto-paused steps: worker with auto-paused steps closes
  the declaration → steps stay `PAUSED`, shift lands `IN_PAUSE` step-sourced with the step reason
  and `manually_recorded=False` (Clarifications item 2).
- Declare while a step-sourced pause is open, no working steps: `paused_steps: 0`, step record
  untouched, declared reason wins the live state per D4 (Clarifications item 1).

## K4 (MINOR — OPERATOR DECISION: accept current behavior, document, pin)

Switch (declare A → declare B) does not re-label the step that A auto-paused; its open `PAUSED`
record keeps reason A, and the switch response reports `paused_steps: 0`. **Decision: this is
correct and stays.** Rationale: the step's pause record is historically truthful — the step WAS
paused at that moment because of A; re-labeling would rewrite why an action happened, and a
PAUSED→PAUSED transition path exists nowhere in the step machine. D5's "same story" holds
temporally: the shift timeline shows A then B; the step shows it was paused during A. Do:
(a) add this as an explicit assumption in the plan (D5 clarification), (b) pin with a test
(switch → step record untouched, reason A, `paused_steps: 0`), (c) add one sentence to handoff §6
UNDER OPERATOR-DELEGATED AUTHORITY for this line only: "Switching declarations does not re-label
already-paused task steps; `paused_steps` counts only newly-paused WORKING steps."

## K5 / K6 — already handled by the operator (do not touch)

The handoff timestamp wire-format note and the §-liveness rollback are done. Reminder made
explicit: **the handoff doc is operator-owned** — outside K4's delegated sentence, do not edit it.
And **do NOT archive, do NOT write a summary, do NOT flip the master table** — this is the third
premature-archive slip across phases; the phase archives ONLY after the reviewer returns APPROVED.

## Protocol

1. Fix on top of HEAD. K1 concurrency tests first — they must fail against the current helper
   (reproduce the race), then pass with the retry.
2. Re-run the full phase Validation plan + baseline rule (no NEW failures vs. baseline; all
   existing suites incl. clock/toggle paths green — the shared-helper change must not alter any
   single-session behavior).
3. Append a fix-cycle entry to the plan's Review log (per finding: change + pinning test).
4. One fix commit referencing K1–K4.
