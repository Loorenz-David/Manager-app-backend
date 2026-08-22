---
plan: test_isolation_and_xdist/plans/plan_1.md
role: implementer (fix)
state: IMPLEMENTED
date: 2026-08-21
actor: codex
---

# Phase 1 fix r4 handoff

Closed the four r3 items assigned to this round: B2, S1, S2, and N7. **OWNER DECISIONS REQUIRED
(0).** The approximately 118-test order-dependent class remains phase 2 work under OD-3;
`pytest-xdist`, `-n`, and parallel execution were not installed or run.

## Outcome

- B2: `DatabaseIsolation._marker_present_on_connection` now recognizes the exact isolation
  marker key without requiring the copied row's `database_name` to already equal the worker name.
  A template-created worker therefore remains droppable during the create-before-`_set_marker`
  interruption window. The existing exact database-name pattern, configured-database rejection,
  PostgreSQL URL parsing, and marker-presence checks remain in force. `start()` cleanup now catches
  `KeyboardInterrupt`.
- C8: `test_fixed_name_reabsorbs_an_interrupted_worker` has separate explicitly-marked and
  inherited-marker rows. `test_start_cleans_worker_when_interrupted_during_creation` injects a
  `KeyboardInterrupt` after the exact worker is created and verifies cleanup.
- S1/S2: both retirement tests now call production `list_pause_reasons`. Each soft-deletes one
  fixture reason, asserts it is absent from the picker, and asserts a live reason remains. No raw
  count asserts the rows inserted by the fixture.
- N7/B1 documentation: the published baseline is corrected to **22 failed / 2539 passed / 1
  deselected**. Deliverable 12 now identifies approximately **118 tests across 11 files**, the
  reversed-order result `139 failed / 2422 passed / 1 deselected` with `added=118 / removed=1`,
  and the coupling source `tests/connecteam/test_clock_actions_integration.py`, which commits
  `Role(WORKER)` as the second collected file. The template carries no migration-owned seed rows.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Verification ledger

Test tree identity for all rows below: `HEAD 584d0f2` plus the intended code diff; no production
application diff. Code-only diff digest: `2687cbc6a84a3ddf5e2556cba797e839a284d703317315e1df951e3dc4b14fd2`.

| Hypothesis | Scope and command | Result and ID delta |
|---|---|---|
| Isolation criteria and cleanup pass | L1: `PYTHONPATH=. pytest -q --tb=short tests/integration/infrastructure/test_database_isolation.py` | **17 passed**; `added=∅ / removed=∅` |
| Retirement tests observe production behavior | L1: `PYTHONPATH=. pytest -q --tb=short tests/integration/services/commands/test_system_transition_reasons_retirement.py` | **5 passed**; `added=∅ / removed=∅` |
| Combined phase-specific test surface | L1/L2: both files in one invocation | **22 passed**; `added=∅ / removed=∅` |
| Authoritative serial baseline | Reused matching prior L4 evidence: `22 failed / 2539 passed / 1 deselected` | No application-wide run in this session; the user-requested scope was phase tests only |
| Static checks | Targeted `ruff check`, `python3 -m compileall -q`, and `git diff --check` on changed Python files | Passed |

The prior matching L4 stamp remains valid for the unchanged application-wide tree: **22 failed /
2539 passed / 1 deselected**. A new application-wide suite run was intentionally not performed in
this session because the request explicitly limited execution to this phase's tests.

## Named mutation evidence

Every mutation was applied at the named site, run at targeted scope, reverted, and checksum-
verified. Mutation files are listed separately from the intended fix perimeter.

| Hypothesis and site | Command and mutant result | Revert evidence |
|---|---|---|
| C8 inherited-marker row must catch the old `marker_key AND database_name` predicate in `app/tests/database_isolation.py` | `PYTHONPATH=. pytest -q --tb=short 'tests/integration/infrastructure/test_database_isolation.py::test_fixed_name_reabsorbs_an_interrupted_worker[inherited-marker]'` → **1 failed**, `UnsafeDatabaseError: Database lacks the disposable marker` | `tests/database_isolation.py` restored to SHA-256 `30017508b99773e2d3182794442173fd83eb6a3055acdfc72beba0ca5356f50c` |
| Keyboard interruption must enter `start()` cleanup at `app/tests/database_isolation.py:139` | `PYTHONPATH=. pytest -q --tb=short tests/integration/infrastructure/test_database_isolation.py::test_start_cleans_worker_when_interrupted_during_creation` with `except Exception` → **1 failed**, exact worker still existed | Same `tests/database_isolation.py` checksum; `beyo_test_gw998` removed |
| S2 must bite when `PauseReason.is_deleted.is_(False)` is removed from `app/beyo_manager/services/queries/pause_reasons/list_pause_reasons.py` | `PYTHONPATH=. pytest -q --tb=short tests/integration/services/commands/test_system_transition_reasons_retirement.py::test_soft_deleted_pause_reason_is_not_selectable_through_the_endpoint` → **1 failed**, soft-deleted slug appeared | `list_pause_reasons.py` restored to SHA-256 `45ddd137416aa3f25a9c17216e78f1e633bad74b5f0ac235ad2485956991286b` |

The C8 and keyboard-probe test teardowns were themselves verified to remove failed-mutant
workers. No probe rows were committed to the configured database. Disposable probe databases
`beyo_test_gw999` and `beyo_test_gw998` were removed; the only persistent test database remains
the template.

## Judgment calls and deviations

- Chose the reviewer-approved marker-key shape rather than redesigning database creation. The
  marker table is created by this isolation module, and the independent exact-name, configured
  URL, parsed-PostgreSQL, and marker-key checks remain fail-closed.
- Rewrote the historical-population test to protect the observable picker contract. A clean-schema
  test cannot replay rows that predated a migration; it now verifies that a retired row is not
  resurrected as a selectable catalog entry rather than asserting its own fixture count.
- No application-wide L4 run was added because the request explicitly said not to run all app
  tests. The prior matching 22/2539/1 L4 evidence is cited rather than reproduced.

## Full write perimeter

Intended code/test changes this cycle:

- `app/tests/database_isolation.py`
- `app/tests/integration/infrastructure/test_database_isolation.py`
- `app/tests/integration/services/commands/test_system_transition_reasons_retirement.py`

Documents changed:

- `plans/plan_1.md` (tracker and append-only r4 review-log entry)
- `handoffs/implementer/2026-08-21_phase1_fix_r2_handoff.md` (corrected published baseline and
  deliverable 12)
- this handoff

Mutation-probe files, listed separately from the fix: `app/tests/database_isolation.py` and
`app/beyo_manager/services/queries/pause_reasons/list_pause_reasons.py`. The latter was restored
byte-for-byte and is not an intended change. Probe artifacts `beyo_test_gw998` and
`beyo_test_gw999` were removed. No Architecture Graph delta was made; the existing three
isolation items remain pending human review.

Checkpoint commit is required by the closing protocol: `CHECKPOINT (not approved): phase 1 fix r4`.
