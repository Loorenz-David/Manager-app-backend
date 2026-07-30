# SUMMARY_declared_worker_states_phase3_commands_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase3_commands_20260729`
- Status: `summarized`
- Owner agent: `Codex` (implementation) / `Opus` (review, 4 rounds) / `claude-fable-5` (lifecycle)
- Created at (UTC): `2026-07-30T10:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 3 of 7)
- Related debug plan: none (defects handled in-review across 2 fix cycles + 1 operator doc fix; trail in the plan's Review log)

## What was implemented

- **`declare_worker_state`**: worker (or admin/manager on-behalf per D10) declares a catalog-backed
  state. Validates open shift (`409`, never auto-clocks-in per D9), workspace + not-deleted +
  `pause_type = PERSONAL` reason, `description` iff `requires_description`. Auto-pauses open
  WORKING steps under the declared `pause_reason_id` via the existing `_apply_step_transition`
  machinery (no parallel path); switch semantics (declare-over-declare closes the old row
  atomically); synchronous same-session reconcile so the live derived state is correct in the
  same transaction. Routes: `POST /worker-shifts/declared-states` (+ `/close`), thin, handoff §6
  conformant field-for-field.
- **`close_declared_worker_state`**: closes the open declaration (`closed_by_id` = actor),
  reconciles; closing does NOT resume auto-paused steps (pinned by test — resumption is an
  explicit worker action on the task).
- **Total retirement**: `/pause` + `/resume` routes and commands deleted; the reconcile's legacy
  manual-pause carve-out and the transitional provenance rule removed; retired tests converted
  (not dropped); retirement greps return zero hits; both retired paths pinned to `404`.
- **F4/F6 obligations** (pinned from Phase 2's review): carve-out-trap test (declare → close with
  no steps → `IDLE`, no phantom pause) and declared-lookup scoping delivered.
- **K1 concurrency hardening**: `load_open_worker_shift_for_update` now does a bounded
  retry-on-None re-select, closing a READ COMMITTED EvalPlanQual race where a concurrently
  replaced open-shift row read as "not clocked in" (false 409 at the kiosk). The reconcile's
  inline select was delegated to the same helper (L1) so the analytics-worker path is equally
  protected. Both fixes mutation-verified load-bearing by the reviewer (retry removed → tests
  fail 5–10/10; delegation reverted → reconcile test fails 5/5).
- **K4 decision (operator)**: switching declarations does not re-label already-paused steps —
  the step's pause record stays historically truthful; `paused_steps` counts only newly-paused
  WORKING steps. Documented in plan + handoff §6, pinned by test.

## Deploy note (carried obligation from the review)

**A worker mid-manual-pause at the moment this phase deploys will reconcile to `IDLE` once** (the
legacy carve-out that kept their `/pause` sticky is removed, and `/resume` no longer exists).
Cosmetic and one-time: the clock-out rebuild still folds their open legacy `manually_recorded`
row correctly per D7, so the closed shift's timeline remains accurate. No action needed; deploy
at a low-activity moment if cosmetic correctness matters.

## Files changed

- `app/beyo_manager/services/commands/users/declare_worker_state.py` (new),
  `close_declared_worker_state.py` (new); `pause_worker_shift.py`, `resume_worker_shift.py`
  (deleted).
- `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py`: carve-out +
  provenance rule removed; L1 delegation to the shared locked-select helper.
- `app/beyo_manager/services/commands/users/_clock_worker_shift.py`: K1 bounded retry-on-None in
  `load_open_worker_shift_for_update` (comments document the EPQ mechanism + bounded-retry
  limitation).
- `app/beyo_manager/routers/api_v1/worker_shifts.py`: declared-state routes; retired routes gone.
- `app/beyo_manager/domain/users/serializers.py`: declared-state payload serializer.
- `app/beyo_manager/models/tables/users/README.md`: state-machine section rewritten (IDLE,
  declared states, `manually_recorded` redefinition, retirement).
- Tests: +22 net incl. full-loop flagship (declare → auto-close via step → re-declare →
  clock-out → both declared segments, zero unexplained idle), two-session concurrency suites for
  declare/close/reconcile, K2–K4 pins, retirement/404 pins.

## Contract adherence

- `06_commands.md` (+ local): `maybe_begin`, subordinate reconcile, no new event paths.
- `09_routers.md`: thin routes; `28_roles_permissions.md`: D10 matrix via
  `resolve_worker_shift_target`, no reimplementation.
- `32_concurrency.md`: lock order shift row → declared row preserved at every site.
- `05_errors.md`: 409/404/422/403 class-level mapping confirmed by the reviewer.

## Validation evidence

- Four review rounds (Opus), final verdict **APPROVED** (round-4 confirmation pass, commit
  `8b0fd78`; production code final at `a39ae40`). Mutation testing proved the K1 retry and the
  L1 delegation independently load-bearing and the concurrency tests non-vacuous.
- Baseline rule held every round: full suite FAILED list byte-identical to the pre-phase
  baseline; +22 passing tests; touched-file ruff clean (repo-wide 141 < 149 baseline).
- Post-commit serialization safe (`expire_on_commit=False`) — verified no implicit async refresh
  outside the transaction.

## Known gaps or deferred items

- Bounded retry limitation (documented in-code): pathological sustained contention can still
  yield a false None from the locked select; every caller self-heals or surfaces a retryable
  conflict, and the clock-out rebuild is always correct.
- Pre-existing shared-DB seed gap (`pause_ended_shift` missing in one workspace fixture) — part
  of the recorded repo baseline, not this phase.
- Frontend contract: declared-states endpoints (§6) now live — liveness table flipped in the
  handoff as part of this finalization.

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §6 shapes verified field-for-field
  across review rounds; Phase 3 row flipped to ✅ live at finalization. K4's semantics sentence
  added to §6; timestamp wire-format note (K5) in §4.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 3 → `archived`; Phase 4 unblocked (Phase 5 independent, may run parallel).
