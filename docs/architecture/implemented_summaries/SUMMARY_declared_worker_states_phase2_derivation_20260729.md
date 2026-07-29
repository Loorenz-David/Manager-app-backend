# SUMMARY_declared_worker_states_phase2_derivation_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase2_derivation_20260729`
- Status: `summarized`
- Owner agent: `Codex` (implementation) / `Opus` (review, 5 rounds) / `claude-fable-5` (lifecycle)
- Created at (UTC): `2026-07-29T20:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 2 of 7)
- Related debug plan: none (defects handled in-review across 4 fix cycles; full trail in the plan's Review log)

## What was implemented

- `derive_target_state` gained `open_declared_count` — precedence per D4: WORKING > declared
  IN_PAUSE > step IN_PAUSE > IDLE. Pure, exhaustively unit-tested (3³ matrix), one production
  call site.
- Reconcile (`reconcile_worker_shift_state`): loads the open declared row `FOR UPDATE` (documented
  lock order: shift row → declared row), sources `reason`/`manually_recorded` from it, auto-closes
  it on transition to WORKING (`closed_by_id = NULL`), with the idempotency re-check narrowed to
  declared-involved transitions only (legacy step→step and manual-pause stickiness preserved at
  baseline behavior).
- Clock-out (`clock_out_shift_for_user`): clamps any open declared row at `clock_out_at` before
  reconstruction; midnight safeguard inherits (00:00 clamp tested).
- Reconstruction (`_reconstruct_shift_middle`): folds declared intervals into the sweep with
  ownership priority (declared > legacy manual > step pause), re-emits declared/manual segments
  with `manually_recorded = True` and correct reasons, carries legacy owners' `changed_by_id`
  through the rebuild, and keeps the legacy manual-rows query (D7).
- `domain/analytics/linear_timeline.py`: additive ownership-priority field on intervals (default
  preserves prior behavior for all other callers — verified).
- Transitional legacy guard: open `IN_PAUSE` + `manually_recorded` rows are distinguished by
  provenance (`changed_by_id IS NOT NULL` = worker's own `/pause`, fully sticky;
  `NULL` = reconcile-authored declared projection, re-derivable). Deleted wholesale in Phase 3.
- Migration `c2f4a6b8d0e1` (operator-authorized D7 deviation): one-time idempotent repair
  restoring `changed_by_id = user_id` on open legacy manual rows laundered by pre-Phase-2 heal
  runs. Sound only while the declared table has no writers — precondition documented in the
  migration docstring (review finding J1).
- **Deploy-neutral**: with zero declared rows, behavior matches the pre-phase baseline —
  proven test-for-test against a detached worktree at `9d922cb` every review round.

## Files changed

- `app/beyo_manager/domain/users/shift_state_machine.py`: declared count + precedence.
- `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py`: declared lookup,
  sourcing, auto-close, narrowed idempotency guard, transitional provenance rule.
- `app/beyo_manager/services/commands/users/_clock_worker_shift.py`: clock-out declared clamp.
- `app/beyo_manager/services/commands/users/_reconstruct_shift_middle.py`: declared folding,
  ownership-derived flags, `changed_by_id` carry-through, backfill-divergence docstring note.
- `app/beyo_manager/domain/analytics/linear_timeline.py`: additive ownership priority.
- `app/migrations/versions/c2f4a6b8d0e1_repair_open_legacy_manual_pause_provenance.py`: I1 repair.
- Tests: state-machine matrix, reconcile precedence/auto-close/idempotency/stickiness suites,
  reconstruction + clamp + midnight cases, four-round regression ladder incl. the
  both-sources-open clock-out repro and the heal-body laundering case.

## Contract adherence

- `08_domain.md`: state machine pure; sweep change additive in pure domain code.
- `06_commands.md` (+ local): reconcile subordinate — no events, no commits; lock order commented.
- `32_concurrency.md`: shift→declared `FOR UPDATE` order; racing-reconcile probes clean.
- `30_migrations.md`: linear chain (single head), idempotent data repair, documented no-op
  downgrade.

## Validation evidence

- Five independent review rounds (Opus), each re-running all gates + adversarial probes; final
  verdict **APPROVED** with zero blocking/medium findings (J1/J2 informational, J1 addressed via
  docstring). Full trail: plan Review log, commits `fb52e96 → aa0260a → d8a123a → fa20b5a →
  d952655`.
- Migration verified in depth: 6-candidate predicate probe (1 target row touched, 5 decoys
  untouched), idempotency (second run = 0 rows), downgrade no-op, chain linearity.
- Baseline rule held every round: failure node sets byte-identical to `9d922cb`; touched-file
  ruff clean; declared table 0 rows post-suite.

## Known gaps or deferred items

- F4/F6 pinned into Phase 3's plan (carve-out trap test; declared-lookup scoping or documented
  clamp invariant).
- The transitional provenance rule + carve-out + `/pause`/`/resume` are deleted in Phase 3.
- `scripts/backfill/backfill_worker_shift_state_records.py` builds its own intervals and does not
  fold declared rows — a second projection, harmless for pre-declaration history (documented in
  the reconstruction docstring); revisit only if rerun over post-declaration dates.
- J2 (informational, carried): sweep owner attribution is per-merged-run, not per-instant.

## Handoff notes

- No frontend-visible change in this phase (derivation only; declared table still has no
  writers). Contract: `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` — unchanged.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 2 → `archived`; next phase: Phase 3 (declare/close commands + retirement).
