# Codex prompt — Phase 4 FIX CYCLE (review verdict: NEEDS_CHANGES — small)

You are fixing review findings on the Phase 4 implementation (`backend/`), now committed as
`20b11c7`. Findings are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md`.

**Parallel-run discipline:** Phase 5's fix cycle is active in this same working tree. Touch ONLY
worker-shift/current-state/serializer files and your own plan. Never stage anything under
`services/commands/auth/`, `routers/api_v1/auth.py`, `routers/utils/jwt_dep.py`, `sockets/`, or
`services/infra/auth.py`. Stage files explicitly — **never `git add -A`**.

## R1 — RESOLVED by the operator, no action for you

The reviewer flagged that the handoff liveness row for Phase 4 still reads ❌ while the surface is
implemented and green, citing acceptance criterion 5. **Operator ruling: the implementation is
correct and the acceptance criterion was stale.** The handoff is operator-owned; its liveness row
is flipped by the operator only after the reviewer approves. Phase 4/6/7 plans have been amended
accordingly. Do not edit the handoff.

## R4 (hardening) — remove `clock_out_at` from the command entirely

Today the audit hole is closed only by the route's pydantic model dropping extras;
`ClockOutWorkerShiftRequest` still parses `clock_out_at` from `ctx.incoming_data`, so any future
raw-dict caller could backdate a clock-out. Verified: the HTTP route is the command's ONLY caller —
the midnight safeguard calls the `clock_out_shift_for_user` helper directly and keeps its own
`clock_out_at` parameter. **Fix:** delete `clock_out_at` from `ClockOutWorkerShiftRequest` and use
`datetime.now(timezone.utc)` unconditionally in the command. The helper is unchanged (safeguard
behavior must stay byte-identical — its 00:00 test must remain green).
**Test:** the command ignores/rejects a `clock_out_at` present in `incoming_data` (command-layer,
not just route-layer).

## R5 (hardening) — don't let a catalog id leak into `reason_text`

The legacy `reason_text` fallback fires on ANY unresolved reason join. Unreachable today, but if
the join is ever tightened (e.g. to exclude soft-deleted reasons) a raw `par_…` id would ship in a
field the handoff promises is human-readable free text. **Fix:** emit `reason_text` only when the
unresolved value is NOT catalog-id-shaped (i.e. does not start with the `PauseReason`
`CLIENT_ID_PREFIX`); when it is id-shaped but unresolvable, return `pause_reason: null` and
`reason_text: null`. **Test:** both branches (free-text legacy value → `reason_text` populated;
unresolvable `par_…` id → both null, no leak).

## R6 (test gap) — cover the `GET /current` 404 branch

Only the two 403 branches are tested. Add: manager requests `user_id` of someone who is not an
active workspace worker → `404`.

## R7 — evidence hygiene (no code)

The reviewer's suite counts differed from the Review log's because Phase 5's uncommitted work
shared this tree. Phase 4 is now isolated at commit `20b11c7`. When you re-run validation, record
in the Review log that Phase 5's concurrent changes are present in the working tree and state
which files your run's failures belong to (baseline vs. auth-phase). Do not attempt to fix any
auth-surface failure — it is not yours.

Also note for your Review-log entry: the reviewer could not run `git` (sandboxed environment), so
any "git diff --check clean" claim must be phrased as what you actually ran locally.

## Protocol

1. Fix on top of `20b11c7`. Tests first for R4/R5/R6.
2. Re-run the phase Validation plan + baseline rule (no NEW failures attributable to Phase 4;
   touched files ruff-clean).
3. Append a fix-cycle entry to the plan's Review log (per finding: change + pinning test).
4. **Do NOT archive/summarize/flip anything** — back to the reviewer
   (`review_prompts/REVIEW_phase4_clock_surface.md`) after; archive only on APPROVED.
5. One fix commit referencing R4–R6, staging only your own files.
