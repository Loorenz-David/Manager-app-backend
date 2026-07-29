# PLAN_declared_worker_states_phase2_derivation_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase2_derivation_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decisions D3–D6 govern this phase)
- Prerequisite: Phase 1 archived (`user_declared_state_records` exists).

## Goal and intent

- Goal: Teach the **entire derived-state pipeline** to read `user_declared_state_records`: the pure state machine, the live reconcile, the clock-out reconstruction, and the clock-out clamp. Behavior-neutral at deploy time (the table is still empty — Phase 3 introduces writers), but fully correct the moment rows appear.
- Business/user intent: Guarantee no deploy window in which a declaration can be recorded but then lost or ignored by the live timeline or the clock-out rebuild.
- Non-goals: Declare/close commands, routes, auto-pause of working steps (Phase 3). Removing the legacy manual-pause carve-out or `/pause`/`/resume` (Phase 3 — they are still the only manual writers until then). Read-endpoint changes (none needed: declared time surfaces as `IN_PAUSE` segments, per D3, which the existing endpoints already serialize).

## Scope

- In scope:
  1. `domain/users/shift_state_machine.py` — `derive_target_state` gains declared-count input; precedence per D4.
  2. `services/commands/users/reconcile_worker_shift_state.py` — load the open declared row; feed derivation; source `reason`/`manually_recorded` from it; auto-close it on transition to `WORKING` (D5).
  3. `services/commands/users/_reconstruct_shift_middle.py` — fold declared intervals into the sweep alongside (not replacing) legacy manual rows.
  4. `services/commands/users/_clock_worker_shift.py::clock_out_shift_for_user` — clamp-close the open declared record at `clock_out_at` (D6).
- Out of scope: any writer of `user_declared_state_records` other than the clock-out clamp; router/API changes; analytics endpoints.
- Assumptions:
  - **State machine.** New signature `derive_target_state(open_working_count: int, open_declared_count: int, open_paused_count: int) -> UserShiftStateEnum`: `≥1 working → WORKING`; else `≥1 declared → IN_PAUSE`; else `≥1 paused → IN_PAUSE`; else `IDLE`. Still pure, exhaustive, no I/O. Transition-validity helper unchanged.
  - **Reconcile.** In `_reconcile_once`, after resolving `shift_started_at`: load the worker's open declared row (`exited_at IS NULL`, workspace + user scoped) **`with_for_update()`** — serializes against Phase 3's declare/close commands and the clock-out clamp. Then:
    - Pass `open_declared_count` (0 or 1) into `derive_target_state`.
    - If `target is WORKING` and an open declared row exists → close it (`exited_at = now`, `closed_by_id = NULL` — system-closed). This implements "returning to a task ends the declaration" at the seam, covering every transport (API step transitions, batch, backfill) with zero changes to step commands.
    - If `target is IN_PAUSE` **sourced from the declared row** (i.e., `open_working_count == 0 and open_declared_count >= 1`) → new derived record gets `reason = declared.pause_reason_id`, `manually_recorded = True`. Otherwise (step-sourced pause) keep today's behavior: `reason` from the earliest open paused step, `manually_recorded = False`.
    - **Keep** the legacy manual-pause stickiness carve-out (current open record `IN_PAUSE` + `manually_recorded` + target `IDLE` → no-op). `/pause` still writes such rows until Phase 3 retires it. Add one guard: if an open *declared* row exists, the carve-out is irrelevant (target is already `IN_PAUSE`).
    - Idempotency must hold: reconcile with an open declared row and current state already declared-`IN_PAUSE` (same reason) → no-op, no duplicate rows.
  - **Reconstruction.** In `reconstruct_shift_middle`, add a query over `UserDeclaredStateRecord` with the same window scoping as the manual-rows query (`entered_at >= shift_start AND entered_at < shift_end`), mapped to `LinearInterval(state="paused", reason=row.pause_reason_id, ...)`. An open declared row (`exited_at IS NULL`) passes `exited_at=None` and is clamped to `shift_end` by the sweep, same as open working steps. Collect declared `client_id`s into the same id-set used for `manually_recorded` re-emission (union with legacy `manual_ids`) so rebuilt declared segments carry `manually_recorded = True` and their catalog `reason`. The legacy manual-rows query **stays** (D7). The module docstring must be updated: declared states are now the primary explanation channel; legacy manual rows remain folded for frozen history.
  - **Clock-out clamp.** In `clock_out_shift_for_user`, after resolving `shift_start` and **before** `reconstruct_shift_middle` runs: load the open declared row `with_for_update()`; if present, set `exited_at = clock_out_at`, `closed_by_id = NULL`. (Reconstruction would clamp the interval anyway; this closes the **source** row so the worker isn't "declared" after clock-out. Midnight safeguard inherits via its delegation to this function.)
  - **Sweep semantics** (verify, don't assume): `compute_linear_segments` merges by `(state, reason)` and existing priority already resolves overlapping `working`/`paused` in favor of `working` — a relational read of `domain/analytics/linear_timeline.py::_sweep` must confirm before relying on it; if priority is interval-order-dependent, declared intervals must be inserted so that working wins (record the finding in the Review log).

## Clarifications required

- [x] Where does "step start closes declaration" live? — resolved: in the reconcile (the seam), not in step-transition commands (D5).
- [x] Does the derived record need a marker of *which* declared row produced it? — resolved: no; `reason = pause_reason_id` + `manually_recorded = true` is sufficient for serialization, and reconstruction re-derives from source anyway.

## Acceptance criteria

1. Unit: `derive_target_state` exhaustively tested over the 3-count matrix; precedence exactly D4; markers never derivable.
2. Integration (reconcile): with an open declared row and no open steps → derived record is `IN_PAUSE`, `reason = pause_reason_id`, `manually_recorded = true`. Idempotent on repeat call.
3. Integration (reconcile): worker in declared `IN_PAUSE` starts a step (open working record appears) → reconcile transitions shift to `WORKING` **and** closes the declared row (`exited_at = now`, `closed_by_id IS NULL`). A subsequent reconcile with the step completed → `IDLE` (declaration does not resurrect).
4. Integration (reconcile): declared open + open paused step simultaneously → `IN_PAUSE` with the **declared** reason (declared outranks step pause).
5. Integration (reconstruction): a shift containing [working steps + a closed declared interval + an open declared interval] rebuilds to segments where declared windows appear as `IN_PAUSE` with catalog reason + `manually_recorded = true`, the open declared interval clamps to `shift_end`, and gaps remain `IDLE`. Legacy `manually_recorded` shift rows in the same window still survive the rebuild (regression guard on existing tests).
6. Integration (clock-out): clocking out with an open declared row closes it at exactly `clock_out_at`; the rebuilt timeline shows the declared segment ending at clock-out; midnight-safeguard path (existing test extended) closes it at `00:00`.
7. Deploy-neutrality: with zero rows in `user_declared_state_records`, all existing worker-shift, worker-stats, connecteam, and analytics suites pass unchanged.
8. `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `backend/architecture/08_domain.md`: state machine stays pure (no I/O).
- `backend/architecture/06_commands.md` + `06_commands_local.md`: reconcile is a subordinate command — no events of its own; session-call safety; `maybe_begin` untouched.
- `backend/architecture/32_concurrency.md`: `FOR UPDATE` ordering — declared-row lock joins the existing shift-row lock; document lock order (shift row → declared row) to avoid deadlock with Phase 3 commands, which must use the same order.
- `backend/architecture/16_background_jobs.md`: the reconcile runs inside the analytics worker's transaction.
- `backend/architecture/15_testing.md`: unit vs. integration placement.
- `backend/architecture/49_observability_runtime.md`: structured log lines for declared-close-on-working and clock-out clamp (mirror `worker_shift.reconcile_transition` style).

### Local extensions loaded

- `06_commands_local.md`: subordinate-command event rule (reconcile emits nothing; clock-out already delegates step closures).

### File read intent — pattern vs. relational

Permitted relational reads:
- `domain/users/shift_state_machine.py`, `services/commands/users/reconcile_worker_shift_state.py`, `_reconstruct_shift_middle.py`, `_clock_worker_shift.py` — the four files being modified.
- `domain/analytics/linear_timeline.py` — sweep priority + `LinearInterval` fields (the "verify, don't assume" item).
- `models/tables/users/user_declared_state_record.py` — exact column names (Phase 1 output).
- Existing tests: `tests/unit/domain/users/test_shift_state_machine.py`, `tests/integration/services/commands/users/test_reconcile_worker_shift_state.py`, `test_worker_shift_commands.py` — extend, don't fork.

Prohibited pattern reads: other commands/services for structure → `06_commands.md`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `worker`, `reconcile`, `state machine`.
- Excluded alternatives: none.

## Implementation plan

1. Extend `derive_target_state` (new middle parameter `open_declared_count`); update every call site in the same commit; extend the exhaustive unit table.
2. Reconcile: add the open-declared `FOR UPDATE` load (after shift-row lock — lock order documented in a comment); wire count, reason/`manually_recorded` sourcing, close-on-WORKING, structured log for the auto-close.
3. Relational read of `_sweep` to confirm working-over-paused priority; note the finding in the Review log.
4. Reconstruction: add the declared-intervals query + id-set union; clamp behavior via `exited_at=None` passthrough; update module docstring.
5. Clock-out: clamp-close open declared row before reconstruction; structured log.
6. Tests per acceptance 1–7 (extend existing suites; new declared-specific cases co-located with the suites they extend).
7. Run validation plan.

## Risks and mitigations

- Risk: deadlock between reconcile (analytics worker) and Phase 3 commands locking the same two rows.
  Mitigation: single documented lock order (shift row → declared row) established *now*; Phase 3 plan requires the same order.
- Risk: sweep priority for overlapping working/declared intervals is not what we assume.
  Mitigation: explicit verification step 3; overlaps are also prevented by construction in Phase 3 (declare auto-pauses working steps), so this only matters for race residue.
- Risk: double-source `IN_PAUSE` (declared + step pause open simultaneously) produces flapping reasons in the live state.
  Mitigation: precedence is deterministic (declared wins, D4); acceptance 4 pins it.
- Risk: silent behavior change with an empty table.
  Mitigation: acceptance 7 runs the full existing suites; the only new writes are gated on rows existing.

## Validation plan

- `pytest app/tests/unit/domain/users/test_shift_state_machine.py -q`: exhaustive matrix green.
- `pytest app/tests/integration/services/commands/users/ -q`: reconcile + clock-out + reconstruction cases green.
- `pytest app/tests/integration/services/tasks/ app/tests/connecteam/ app/tests/integration/services/queries/worker_stats -q`: unchanged behavior (acceptance 7).
- `ruff check`: clean.

## Review log

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
