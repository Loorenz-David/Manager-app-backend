# PLAN_declared_worker_states_phase2_derivation_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase2_derivation_20260729`
- Status: `implemented`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T15:19:45Z`
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

- `2026-07-29T14:35:47Z` — Codex (implementer), pre-implementation verification:
  - Phase 1 prerequisite confirmed from the master phase table: archived at commit
    `a84610c`; the `user_declared_state_records` migration is at Alembic head.
  - Read `domain/analytics/linear_timeline.py::_sweep` relationally as required.
    Finding: overlap priority is explicit and interval-order-independent — each raw
    segment checks active `working` entries before active `paused` entries. When no
    working entry is active, overlapping pauses are owned deterministically by the
    earliest `(entered_at, record_id)`. Declared intervals can therefore be appended
    normally; no insertion-order workaround is required for working to win.
- `2026-07-29T14:49:01Z` — Codex (implementer), implementation + self-review:
  - Implemented the D3–D6 read/derivation integration: pure three-count state
    derivation; declaration-aware live reconcile; close-on-WORKING; deterministic
    reconstruction from step + declared + legacy manual sources; and clock-out source
    clamp inherited by the midnight safeguard.
  - Concurrency review: both reconcile and clock-out acquire locks in the documented
    order **shift row → declared row**. Declaration queries are workspace/user scoped
    and use `FOR UPDATE`.
  - Boundary review: reconcile still emits no events and performs no commit; no router,
    `/pause`, `/resume`, legacy stickiness, Connecteam, or analytics endpoint code was
    changed.
  - Call-site review: `rg "derive_target_state\(" app --glob "*.py"` confirms the
    implementation and both unit-test comprehensions use the new three-argument
    signature; no stale two-argument call remains.
  - Acceptance evidence:
    - Alembic prerequisite: `595e7b840926 (head)`.
    - `pytest tests/unit/domain/users/test_shift_state_machine.py -q` → `53 passed`.
    - Six explicit new Phase 2 integration nodes → `6 passed`.
    - `pytest tests/integration/services/commands/users/ -q` →
      `21 passed, 2 failed`; failures are exactly the two Phase 1-recorded clock-out
      baseline cases (`unspecified` reason expectation and missing
      `pause_ended_shift` seed). No new worker-shift failure.
    - Unchanged tasks + Connecteam + worker-stats integration suites → `70 passed`.
    - Broader analytics suites → `70 passed, 1 failed`; the single
      worker-stats mock-signature failure is recorded baseline debt.
    - Full backend suite after removing one exact unreferenced fixture left by an
      interrupted test run → `1184 passed, 25 failed, 2 warnings`; failures are the
      established repository baseline categories and contain no Phase 2 test.
    - Test DB post-cleanup: `declared_row_count 0`, confirming deploy-neutral legacy
      evidence was exercised with an empty declaration table.
    - Touched-file `ruff check` → `All checks passed!`.
    - Repository-root `ruff check .` → `148` pre-existing errors (Phase 1 recorded
      `149`); no touched-file error and no Phase 2 delta.
    - `git diff --check` → clean.
  - Self-review findings: no blocking or minor findings. All acceptance criteria are
    covered; implementation summary and archive record written.
- `2026-07-29` — Opus (independent adversarial review of commit `fb52e96`). Verdict:
  **NEEDS_CHANGES**.

  **Gates re-run independently** (venv `app/.venv`, `APP_ENV=testing`, `app_test` @
  `595e7b840926`, `user_declared_state_records` empty before and after):
  - `pytest tests/unit/domain/users/test_shift_state_machine.py -q` → `53 passed`.
  - `pytest tests/integration/services/commands/users/ -q` → `21 passed, 2 failed`.
    Baseline proven with a detached `git worktree` at `9d922cb` (pre-Phase-2): same suite
    → `16 passed, 2 failed`, the *same* two clock-out cases
    (`test_clock_out_reconstructs_middle_from_step_history`,
    `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, both
    `NotFound: System pause reason 'pause_ended_shift' is not configured`). +5 tests, no
    new failure. Deploy-neutrality claim holds.
  - `pytest tests/integration/services/tasks/ tests/connecteam/ tests/integration/services/queries/worker_stats -q`
    → `70 passed`. `pytest tests/integration/services/queries tests/integration/services/tasks -q`
    → `73 passed`. `pytest tests/unit -q` → `894 passed, 8 failed` (all recorded baseline
    categories; none shift-related).
  - `ruff check` on all seven touched files → `All checks passed!`; repo-root
    `ruff check .` → `141 errors` (below the recorded 149 baseline).
  - Confirmed correct: D4 precedence in `derive_target_state` (pure, 3^3 matrix, single
    production call site updated); shift-row→declared-row `FOR UPDATE` order with a code
    comment in both `_reconcile_once` and `clock_out_shift_for_user`; close-on-`WORKING`
    only with `closed_by_id = NULL` (an `IDLE` target is unreachable while a declaration
    is open, by construction of the derivation); legacy stickiness carve-out still
    present; reconstruction window scoping matches the manual query and the legacy manual
    query is retained; clock-out clamps at exactly `clock_out_at` under `FOR UPDATE`
    before reconstruction, with the midnight path asserted at `00:00`; reconcile emits no
    events and does not commit; the `_sweep` priority finding is recorded above.

  **F1 — BLOCKING. Reconstruction contradicts D4: a declaration overlapping an earlier,
  still-open step pause is erased from the rebuilt timeline.**
  `services/commands/users/_reconstruct_shift_middle.py:137-146` appends declared rows as
  plain `paused` intervals; `domain/analytics/linear_timeline.py:205` then awards
  ownership to `min(active_pauses, key=(entered_at, record_id))` — *earliest pause wins*,
  not *declared wins*. Violates D4 ("open declared state > open PAUSED step"), the
  precedence pinned by acceptance 4 on the live path, and the master goal "zero
  unexplained collapse of declared time into idle".
  Probe (run locally, then removed): clock-in 09:00; step `PAUSED` open at 09:05 with a
  catalog reason; declaration open at 09:20 with a different reason; clock-out 09:50.
  Rebuilt timeline = `IDLE 0→5`, `IN_PAUSE 5→50 reason=<step reason>
  manually_recorded=True`, `ENDED_SHIFT`. The declared reason does not appear anywhere.
  The live reconcile on the same state reports the *declared* reason (the phase's own
  `test_reconcile_declared_state_outranks_open_paused_step`), so live and rebuilt
  timelines disagree and the authoritative one drops the declaration. Post-Phase-3 this is
  an ordinary flow, not race residue: a worker whose task is already paused for a blocker
  and who then declares an activity loses the declaration at clock-out. The plan's
  "verify, don't assume" step (Implementation plan §3) only checked working-vs-paused
  priority; declared-vs-step-pause priority was never verified and does not match D4.

  **F2 — BLOCKING (same probe). `manually_recorded = True` leaks onto step-sourced pause
  segments.** `_reconstruct_shift_middle.py:201-203` sets `is_manual` whenever *any*
  declared/legacy id appears in `segment.record_ids`, but `_sweep` puts every *active*
  pause into `chosen` (`linear_timeline.py:206,214`), not just the owner. A step-owned
  segment that merely overlaps a declaration is therefore stamped
  `manually_recorded = True` while carrying the step's reason — directly against the
  plan's "step-sourced pause … `manually_recorded = False`". The pre-Phase-2 code was safe
  only because of the invariant the diff deletes from the module docstring
  (`_reconstruct_shift_middle.py:11-15`, previously "manual and step pauses never
  overlap"); the invariant is gone but the ownership logic was not replaced.

  **F3 — MAJOR (latent until Phase 3). Asymmetric idempotency guard leaves a stale
  declared reason and marker on the live record.**
  `reconcile_worker_shift_state.py:214-225` re-checks `reason`/`manually_recorded` only
  when `declared_is_source` is true. Moving *out of* a declared pause into a step-sourced
  pause therefore short-circuits as a no-op and the open derived record keeps
  `reason = <declared pause_reason_id>` and `manually_recorded = True`.
  Probe: declare 09:05 → reconcile → `IN_PAUSE(reason=declared, manual=True)`; close the
  declaration at 09:10 and open a step pause with a different reason → reconcile 09:11 →
  record unchanged (declared reason, `manual=True`). Violates the plan's "Otherwise
  (step-sourced pause) keep today's behavior: `reason` from the earliest open paused step,
  `manually_recorded = False`" and the phase goal "fully correct the moment rows appear".

  **F4 — MAJOR (latent until Phase 3, cross-phase landmine). The retained legacy
  stickiness carve-out now traps records the reconcile itself authored: the shift can
  never return to `IDLE` after a declaration closes.**
  `reconcile_worker_shift_state.py:197-204` predicates on `current.manually_recorded`,
  which line 242 now sets for declared-sourced pauses. Once the declaration is closed and
  all steps end, `target = IDLE` and `open_declared is None`, so the carve-out fires and
  the worker stays in a phantom `IN_PAUSE` for the rest of the day.
  Probe (continuation of F3): after closing the step pause too, reconcile at 09:21 returns
  `changed=False` and the open record is still `IN_PAUSE` with the declared reason.
  Keeping the carve-out is mandated by this plan (removal is Phase 3), so this is not a
  deviation from the written scope — but the plan's guard ("if an open declared row exists
  the carve-out is irrelevant") only covers the opposite direction. Phase 3 must remove
  the carve-out **and** pin this with a test, or the carve-out predicate must stop reusing
  `manually_recorded` now that the reconcile writes it.

  **F5 — MINOR. Non-additive test edit: open-legacy-manual-pause coverage was removed.**
  `tests/integration/services/commands/users/test_worker_shift_commands.py:773-782`
  replaces the previously seeded open `IN_PAUSE` / `manually_recorded=True` "Late lunch"
  row in `test_midnight_safeguard_closes_previous_day_shift_and_allows_new_day` with a
  declared row instead of adding one alongside. `test_clock_out_preserves_manual_pause`
  covers only a *closed* manual row, so no test now exercises an open legacy manual pause
  surviving a shift close — precisely the "shift open across the deploy" case D7 promises
  to keep working. Acceptance 6 asked for the existing test to be *extended*.

  **F6 — INFORMATIONAL.** The reconcile's declared lookup
  (`reconcile_worker_shift_state.py:154-164`) is not shift-window scoped, while
  `_load_open_steps` is (`entered_at_or_after=shift_started_at`, line 171). A declared row
  left open from an earlier shift would pin every later shift to `IN_PAUSE`. Not reachable
  today (clock-out and the midnight safeguard both clamp), but D9 enforcement in Phase 3
  is the only thing keeping it that way.

  **Required before this phase can be re-approved:** F1 + F2 (make the sweep — or the
  reconstruction's interval/ownership handling — honour D4 for declared-vs-step pauses and
  attribute `manually_recorded` from the segment *owner*, with a regression test for
  "declared opened after an already-open step pause"), F3 (make the idempotency guard
  compare `reason`/`manually_recorded` unconditionally), F5 (restore the legacy open-manual
  coverage additively). F4 must be carried into the Phase 3 plan as an explicit,
  test-pinned deliverable.

- `2026-07-29T15:19:45Z` — Codex (implementer), F1/F2/F3/F5 fix cycle:
  - Re-read `domain/analytics/linear_timeline.py::_sweep` before modifying it. The
    working-over-paused rule remains explicit and interval-order-independent: active
    working entries are still selected before paused entries. For pause-vs-pause
    ownership, `LinearInterval.priority` now supplies an additive higher-wins key while
    the default `0` retains the prior earliest-`(entered_at, record_id)` rule
    (`linear_timeline.py:54-63,202-222`). A caller audit found reconstruction, the worker
    shift-state backfill, and timeline unit tests; all non-reconstruction callers keep the
    default and therefore retain prior behavior.
  - **F1 fixed:** reconstruction assigns declaration intervals priority `2`, frozen
    legacy manual intervals priority `1`, and step intervals the default `0`
    (`_reconstruct_shift_middle.py:43-47,148,181`). The sweep exposes its selected pause
    owner and preserves source-class boundaries during segment merging
    (`linear_timeline.py:96-107,285-339`). Pinned by
    `test_higher_priority_pause_owns_overlap_and_exposes_owner_record` and
    `test_declared_pause_owns_reconstruction_overlap_with_step_pause`.
  - **F2 fixed:** reconstruction derives `manually_recorded` from
    `segment.owner_record_id`, not the set of every concurrently active record
    (`_reconstruct_shift_middle.py:207-209`). The flagship reconstruction test asserts
    the step-owned `09:05→09:20` segment is non-manual and the declaration-owned
    `09:20→09:50` segment carries its catalog reason and manual marker.
  - **F3 fixed:** every derived `IN_PAUSE` no-op now requires both the reason and
    `manually_recorded` projection to match, regardless of which source currently owns
    the pause (`reconcile_worker_shift_state.py:214-225`). Pinned by
    `test_reconcile_updates_pause_projection_when_source_changes`.
  - **F5 fixed:** the declared midnight test remains intact and the separate
    `test_midnight_safeguard_preserves_open_legacy_manual_pause` restores the open
    `"Late lunch"` legacy row through the midnight clock-out path.
  - Scope review: F4/F6 remain deferred and pinned in Phase 3; the legacy stickiness
    carve-out and `/pause`/`/resume` were not changed. Reconcile remains subordinate:
    no events and no commit. The documented cross-command lock order remains
    **shift row → declared row**.
  - Regression-first evidence: before the production fix, the flagship reconstruction
    collapsed `09:05→09:50` into one step-owned segment and the source-change reconcile
    returned `changed=False`; the restored midnight legacy case already passed. After the
    fix, the three focused integration nodes report `3 passed`, and the timeline suite
    reports `29 passed`.
  - Full validation evidence:
    - Alembic: `595e7b840926 (head)`; post-suite
      `user_declared_state_records` count: `0`.
    - Exhaustive derivation matrix: `53 passed`.
    - Worker command/reconcile suites: `24 passed, 2 failed`; the two failures are the
      exact independently proven pre-Phase-2 baseline clock-out cases
      (`unspecified` vs `None`, and missing `pause_ended_shift`). Three new integration
      regressions pass and no new failure was introduced.
    - Unchanged task + Connecteam + worker-stats suites: `70 passed`; broader query/task
      suites: `73 passed`.
    - Full unit suite: `895 passed, 8 failed, 2 warnings` — the recorded eight baseline
      failures plus one new passing timeline regression.
    - Full backend suite: `1188 passed, 25 failed, 2 warnings` — the same recorded 25
      baseline failure categories plus four new passing regression tests.
    - Touched-file `ruff check`: `All checks passed!`; repository-root `ruff check .`:
      `141` recorded baseline errors, with no touched-file error.
    - `git diff --check`: clean.
  - Lifecycle result: implementation fixes are complete and returned to independent
    re-review. Per the fix-cycle protocol, no implemented summary, archive move, or
    master-table status change is made before an `APPROVED` verdict.
- `2026-07-29` — Opus, independent re-review of the fix cycle (`8fdd5bf` + `aa0260a`).
  Verdict: **NEEDS_CHANGES**.

  **Round-1 findings re-verified against the fixed code (probes re-run, then removed):**
  - **F1 — fixed.** Re-ran the original repro (step pause *and* declaration both still
    open at clock-out, which the new
    `test_declared_pause_owns_reconstruction_overlap_with_step_pause` does not cover — it
    uses a closed step pause). Rebuild now yields `IN_PAUSE 09:05→09:20` step reason
    `manually_recorded=False`, then `IN_PAUSE 09:20→09:50` declared reason
    `manually_recorded=True`. Exactly D4.
  - **F2 — fixed.** `is_manual` is owner-derived (`_reconstruct_shift_middle.py:207-210`),
    no longer a `record_ids` intersection.
  - **F3 — fixed.** After a declaration closes with a step pause open, the live record
    switches to the step reason with `manually_recorded=False`.
  - **F4 — dissolved as a consequence of the F3 fix** (verified: after everything closes
    the shift lands on `IDLE`), and still pinned in the Phase 3 plan. **F6** pinned in the
    Phase 3 plan. **F5 — fixed additively** (`test_midnight_safeguard_preserves_open_legacy_manual_pause`).
  - Deploy-neutrality of the `linear_timeline.py` change independently confirmed:
    `pytest tests/integration -q` → `17 failed, 252 passed`, and the failure node set is
    **byte-identical** to a detached `git worktree` at `9d922cb` (pre-Phase-2) running the
    same suite. Unit `895 passed, 8 failed` (same eight baseline nodes); tasks +
    connecteam + worker-stats `70 passed`; users commands `24 passed, 2 failed` (the two
    baseline clock-out cases); touched-file `ruff check` clean; repo-root `141`.
    `serialize_linear_segment` builds its dict field-by-field, so the new
    `owner_record_id` does not leak into any API contract.

  **G1 — BLOCKING (regression introduced by the F3 fix). Legacy manual-pause stickiness is
  broken for `IN_PAUSE → IN_PAUSE`, with zero declared rows, and it strands `/resume`.**
  `services/commands/users/reconcile_worker_shift_state.py:214-225` now demands
  `reason`/`manually_recorded` equality for *every* `IN_PAUSE` target, while the retained
  carve-out (lines 197-204) still only guards `target is IDLE`. An open `/pause` row is
  therefore closed and replaced by a step-sourced `IN_PAUSE` as soon as any step pause
  opens for that worker inside the shift window (manager/batch step transition, or the
  worker's own transitions if the analytics worker lags).
  Probe, run on `aa0260a` and on the pre-Phase-2 baseline `9d922cb`, declared table empty:
  worker `/pause`d at 08:05 (`reason="Cleaning the bench"`, `manually_recorded=True`),
  step pause opens at 08:10, reconcile at 08:11 —
  - `9d922cb`: `changed=False`; manual row still open, reason and marker intact.
  - `aa0260a`: `changed=True`; manual row closed at 08:11; open record carries the step
    reason with `manually_recorded=False`.
  Consequence beyond record churn: `resume_worker_shift`
  (`services/commands/users/resume_worker_shift.py:22-28`) requires the open record to be
  `IN_PAUSE` **and** `manually_recorded`, so after the clobber the worker's `/resume` 409s
  (`"A shift can only be resumed from a manual pause."`) until the step pause closes — a
  user-facing lockout on an endpoint that is still live until Phase 3 retires it.
  Violated clauses: checklist "Legacy manual-pause stickiness carve-out is STILL PRESENT"
  (the line survives; the protection does not), acceptance 7, and the phase goal
  "Behavior-neutral at deploy time".

  **G2 — MEDIUM (same guard, same commit). Legacy step-sourced pause re-derivation
  changed from sticky to re-emitting, with zero declared rows.**
  Probe (both commits, declared table empty): two paused steps, reasons R1 (earliest) and
  R2; the R1 step's record closes; reconcile —
  - `9d922cb`: `changed=False`, one `IN_PAUSE` record, reason stays R1.
  - `aa0260a`: `changed=True`, the record is closed and a second `IN_PAUSE` opens at the
    reconcile instant with reason R2.
  This is arguably *more* correct (it converges the live record with what the clock-out
  rebuild produces), but the plan explicitly scoped it out — "Otherwise (step-sourced
  pause) keep today's behavior" — and no test pins it in either direction, so the suites
  cannot detect the change. Needs either an explicit recorded decision plus a pinning
  test, or a guard that re-derives only when a *declared* source enters or leaves the
  projection, leaving pure step→step reason changes on today's behavior.

  **G3 — MINOR (scope, not a defect). `domain/analytics/linear_timeline.py` is outside
  this phase's declared In-scope list**, which names four files and permits only a
  *relational read* of this module ("File read intent"). The change is well-guarded
  (`priority: int = 0` default, `-priority` leading the owner sort key, `owner_priority`
  added to the merge key, new `LinearSegment` field defaulted and unserialized) and I
  verified inertness for every other caller as recorded above — so this is a scope-record
  gap, not a behavioral one. A shared pure-domain module changing under a deploy-neutral
  phase should be added to the plan's Scope section, with the neutrality argument written
  down. Related, informational: `scripts/backfill/backfill_worker_shift_state_records.py`
  builds its own `LinearInterval` list and does not fold declared rows, so it remains a
  second, now-divergent projection of the same timeline (harmless for historical data,
  which predates declarations).

  **Required before approval:** G1 (restore manual-pause stickiness across
  `IN_PAUSE → IN_PAUSE` and pin it with a test asserting `/resume` still works after a
  step pause opens under a manual pause). G2 (decide and pin, either way). G3 (record the
  scope expansion + neutrality argument in the plan).

## Lifecycle transition

- Current state: `implemented`
- Next state: `independent re-review`
- Transition owner: `David`
