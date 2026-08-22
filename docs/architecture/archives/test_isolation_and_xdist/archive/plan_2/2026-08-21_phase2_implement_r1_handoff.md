---
plan: 2
role: implement
state: IMPLEMENTED
date: 2026-08-21
actor: codex
---

# Phase 2 implementation handoff

Implemented serial order-independence and per-checkout test isolation. The code-side
implementation stamp was `HEAD a2144aee5d6fc53f7086261f73069edd8f1056ed` plus tracked dirty
diff digest `469d842fbc85b4e5a4e357735d48126db3a6aa087f12be90270f3a554f9e4024`; the only
untracked implementation file was the listed shared factory module. Documentation changes
were made after the stamp and do not alter the application/test implementation.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## What changed

- Added `create_test_workspace` and `adopt_or_create_role` in
  `app/tests/fixtures/phase2_row_factories.py`, then applied that single factory strategy to
  the eleven named C1 files. The twelfth task-step file uses the same adopt-or-create rule for
  its collision site.
- Added strict checkout-slot support with `BEYO_TEST_SLOT` (default `main`) and documented it in
  `app/.env.example`. Worker and template names are now slot-qualified; old unqualified names
  are swept permanently for compatibility.
- Hardened PostgreSQL disposal checks and template/worker lifecycle in
  `app/tests/database_isolation.py`. The new signature is:

  `assert_disposable_database(database_name, configured_database_url, *, target_database_url, marker_present, public_table_count=None)`

  It validates the slot/legacy name, configured and target PostgreSQL URLs, normalized endpoint,
  configured-database tuple, marker, and empty-unmarked-shell rule. Template-sourced workers are
  marked before interruption can leave an unmarked populated database.
- Made Redis isolation session-scoped autouse by overriding `settings.redis_key_prefix` and
  deleting only the generated prefix at teardown.
- Added the default-off `BEYO_TEST_COLLECTION_ORDER=reverse` hook.
- Added the production-path pause-reason ownership assertion and a configured-development-
  database row-count assertion during isolation teardown.

## Verification

All runs were serial; pytest-xdist was not installed and no `-n` flag or parallel run was used.

- Infrastructure criterion: `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` — **36 passed**.
- Retirement criterion: **5 passed**.
- Twelve file-scoped C1 runs: all passed; the paired clock-actions/task-steps run passed.
- Ruff and compileall on all changed Python files: passed.
- Authorized diagnostic reversal: **22 failed / 2560 passed / 1 deselected**.
- Mandatory closing default: **21 failed / 2561 passed / 1 deselected**.
- Mandatory closing reversal: **22 failed / 2560 passed / 1 deselected**.

The closing default failure set is the published 22 minus
`tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`.
The remaining failures are the pre-existing foreign failure stream. The reversed run also retains
the known concurrency failure in `test_concurrent_allocations_return_distinct_scalars`.

## Judgment calls and deviations

- Shared factories were selected because the class is uniform and the resulting C1 evidence is
  attributable to one strategy. Workspaces are created per test; globally unique roles are
  adopted or created, never blindly inserted.
- `BEYO_TEST_SLOT` was selected as the explicit lowercase operator-facing slot variable and is
  strictly validated without normalization.
- Legacy-name cleanup is permanent so an older checkout cannot leave an orphaned database after
  a newer slot-aware checkout starts.
- Redis isolation is autouse because production key builders read `settings.redis_key_prefix`
  at call time; teardown is prefix-bounded.
- Collection reversal is shipped but opt-in, preserving normal collection order unless
  `BEYO_TEST_COLLECTION_ORDER=reverse` is set.
- The empty-unmarked database exception is deliberately limited to zero public tables. A
  populated markerless database is refused. Only `UndefinedTableError` is tolerated around
  inspection probes; no broad guard exception was introduced.
- The phase stayed within its production scope fence. The only production path touched was a
  mutation probe, which was reverted.
- The phase-2 L4 budget was exactly three and was consumed by the diagnostic reversal and the
  closing default/reversal pair. No further full-suite run was taken.

## Mutation probes (separate from implementation changes)

Every named probe was applied, observed red, and reverted. Files touched by probes were:

- `app/tests/database_isolation.py` — slot derivation, slot normalization, disposable-name
  pattern, configured tuple, endpoint confinement, marker predicate, and URL parsing probes.
- `app/tests/conftest.py` — removal of the Redis settings override and unconditional reversal-hook
  probes.
- `app/tests/integration/infrastructure/test_database_isolation.py` — all C3–C8 hypothesis
  probes, including the residue and empty-shell checks.
- `app/tests/integration/services/commands/users/test_worker_shift_commands.py` — restored
  unfiltered workspace lookup probe: **41 failed / 1 passed**.
- `app/tests/integration/services/commands/task_steps/test_add_task_steps_integration.py` —
  restored unconditional `Role(...)` probe: **1 failed / 1 passed**.
- `app/beyo_manager/services/commands/pause_reasons/create_pause_reason.py` — C7(a) production
  ownership mutation at line 36; the targeted retirement test failed and the line was restored.

No production file is part of the implementation diff.

## Probe databases and residue

The phase tests created disposable worker probes including `beyo_test_main_gw993` through
`beyo_test_main_gw999` as applicable to the named scenarios, plus randomized slot-qualified
template/worker names for the interrupted-template test. Each was dropped by the test cleanup;
the criterion also exercises the populated markerless refusal without dropping it through the
guard. The configured development database was never a disposal target, and its before/after
row-count assertion passed. No probe database remained at close.

## Full write perimeter

Implementation files:

- `app/.env.example`
- `app/tests/conftest.py`
- `app/tests/database_isolation.py`
- `app/tests/fixtures/phase2_row_factories.py`
- `app/tests/integration/infrastructure/test_database_isolation.py`
- `app/tests/integration/scripts/backfill/test_backfill_worker_shift_state_records.py`
- `app/tests/integration/scripts/backfill/test_curate_shifts_from_connecteam.py`
- `app/tests/integration/services/commands/cases/test_case_created_step_pause.py`
- `app/tests/integration/services/commands/task_steps/test_add_task_steps_integration.py`
- `app/tests/integration/services/commands/test_system_transition_reasons_retirement.py`
- `app/tests/integration/services/commands/users/test_update_user_admin_clock_in_code.py`
- `app/tests/integration/services/commands/users/test_worker_shift_commands.py`
- `app/tests/integration/services/commands/users/test_worker_shift_realtime_events.py`
- `app/tests/integration/services/queries/users/test_get_current_worker_shift_state.py`
- `app/tests/integration/services/queries/users/test_list_users_floor_identification.py`
- `app/tests/integration/services/queries/worker_stats/test_get_worker_linear_timeline_breakdown.py`
- `app/tests/integration/services/queries/worker_stats/test_list_workers_linear_timeline.py`
- `app/tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py`

Documents:

- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/handoffs/implementer/2026-08-21_phase2_implement_r1_handoff.md`

Tool-recorded state: Architecture Graph was checked at revision
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`. It is valid, has no
diagnostics, and remains in review mode with three pending owner-review items. Relevant existing
pending isolation nodes were read but not promoted or edited. No graph mutation was recorded;
the new behavior remains within that existing architecture boundary.
