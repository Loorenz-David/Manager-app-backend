# SUMMARY_declared_worker_states_phase2_derivation_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase2_derivation_20260729`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-29T14:49:01Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 2 of 7)
- Related debug plan: none

## What was implemented

- Extended the pure `derive_target_state` function with `open_declared_count` and the
  D4 precedence `WORKING step > declared state > PAUSED step > IDLE`; every call site
  was updated in the same change.
- Integrated open declaration rows into live reconcile under `FOR UPDATE`. A declaration
  produces `IN_PAUSE` with its catalog reason and `manually_recorded=True`; identical
  repeats are idempotent. Starting/resuming work system-closes the source declaration
  (`closed_by_id=None`) before the derived shift transitions to `WORKING`.
- Preserved the legacy manual-pause stickiness carve-out and left `/pause` and `/resume`
  untouched for Phase 3.
- Added declaration intervals to deterministic clock-out reconstruction alongside step
  intervals and frozen legacy manual shift rows. Closed and open declarations rebuild as
  `IN_PAUSE` with catalog reason and `manually_recorded=True`; open intervals clamp to
  `shift_end`, while gaps remain `IDLE`.
- Added the clock-out source clamp: an open declaration is locked and closed at exactly
  `clock_out_at` before reconstruction. The midnight safeguard inherits this behavior
  through its existing delegation.
- Documented the cross-command lock order in both write seams:
  **shift row → declared row**. Phase 3 commands must preserve it.
- Kept reconcile subordinate: no event dispatch and no transaction commit were added.
  Structured logs cover reconcile auto-close and clock-out clamp.

## Files changed

- `app/beyo_manager/domain/users/shift_state_machine.py`
- `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py`
- `app/beyo_manager/services/commands/users/_reconstruct_shift_middle.py`
- `app/beyo_manager/services/commands/users/_clock_worker_shift.py`
- `app/tests/unit/domain/users/test_shift_state_machine.py`
- `app/tests/integration/services/commands/users/test_reconcile_worker_shift_state.py`
- `app/tests/integration/services/commands/users/test_worker_shift_commands.py`

## Acceptance and validation evidence

- Alembic prerequisite: `alembic current` → `595e7b840926 (head)`.
- Required `_sweep` verification: working priority is explicit and independent of input
  order; paused ownership is deterministic by earliest `(entered_at, record_id)`.
- Pure state-machine matrix: `53 passed`.
- Six declaration-specific integration acceptance cases: `6 passed` (live derivation and
  idempotency, work auto-close/no resurrection, declared-over-paused precedence, mixed
  reconstruction with legacy preservation, direct open-interval clamp, midnight clamp).
- Full user-command integration directory: `21 passed, 2 failed`; the two failures are the
  exact pre-existing clock-out baseline cases recorded by Phase 1. No new failure.
- Unchanged tasks + Connecteam + worker-stats integration suites: `70 passed`.
- Broader analytics suites: `70 passed, 1 failed`; the one worker-stats mock-signature
  failure is in the recorded repository baseline and outside touched code.
- Full backend suite after test-data cleanup: `1184 passed, 25 failed, 2 warnings`.
  The 25 failures are the established dirty/shared-DB repository baseline categories;
  every new Phase 2 test passed.
- Deploy-neutrality check: the test database contained `0` declared rows after cleanup,
  and the unchanged legacy suites above remained green/baseline-identical.
- Ruff: all touched source and test files clean. Repository-wide `ruff check .` reports
  `148` pre-existing errors (recorded Phase 1 baseline: `149`); Phase 2 adds none.
- `git diff --check`: clean.

## Contract adherence

- Domain derivation remains pure with no ORM or I/O imports.
- Reconcile remains a subordinate command and joins its caller's transaction.
- Both declaration reads are workspace/user scoped and pessimistically locked.
- Lock acquisition order is documented and consistent.
- No routers, API shapes, events, legacy pause/resume commands, or analytics endpoints
  changed.

## Known gaps or deferred items

- Phase 3 owns declaration writers/routes, working-step auto-pause, and retirement of the
  legacy `/pause` and `/resume` surface.
- Repository-health debt remains outside this feature set: the recorded test failures,
  dirty-DB flakiness, and full-repository Ruff findings.

## Lifecycle transition

- Plan archived to
  `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 2 status → `archived`; next sequential phase is Phase 3 (commands).
