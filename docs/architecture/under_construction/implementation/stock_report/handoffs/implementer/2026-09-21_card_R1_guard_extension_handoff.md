---
plan: 10 (follow-up, owner card R-1)
role: implement
state: CHECKPOINT_NOT_APPROVED
date: 2026-09-21
actor: Codex
---

# Checkpoint handoff — owner card R-1 guard extension

Checkpoint message: **CHECKPOINT (not approved): owner card R-1 — guard extension**

## Built

- Extended `app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py`
  to collect the four ratified construct families, including all six planted spellings.
- Corrected the guard test module docstring for class (f), C4(i)/(j)/(k), and the four
  new forms (N-12).
- Kept production code unchanged and added no registry entries.
- Added one Review log entry to `plans/plan_10.md` only; no master-plan, intention, or
  criterion-cell edits.

## Verification

- Clean guard baseline: `7 passed`.
- Full guard with the EOF plant: all six new plant lines reported as unregistered and
  the other six guard checks passed.
- Mutation ledger: **4 declared / 4 executed / 4 red / 4 reverted**.

| Mutation | Observed red from `test_c4a_every_collected_site_has_a_registry_entry` | Revert proof |
|---|---|---|
| Disable table-object support | Lines 122 and 123 disappeared; remaining plants 117, 119, 121, 124 remained red; `1 failed, 6 passed` | `git diff --quiet -- app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py` exit 0 |
| Disable `for`/`with` attribute targets | Lines 117 and 119 disappeared; remaining plants 121–124 remained red; `1 failed, 6 passed` | same command, exit 0 |
| Restore plain-name-only `setattr` matching | Line 121 disappeared; remaining plants 117, 119, 122–124 remained red; `1 failed, 6 passed` | same command, exit 0 |
| Restore literal `state=`-only Task construction | Line 124 disappeared; remaining plants 117–123 remained red; `1 failed, 6 passed` | same command, exit 0 |

The plant itself was appended at EOF of
`app/beyo_manager/services/commands/tasks/update_task.py`, after all registered lines,
then removed and proved with `git diff --quiet -- app/beyo_manager/services/commands/tasks/update_task.py` exit 0.

- Live-instance grep: zero matches in `app/beyo_manager/` and `app/scripts/` for
  `Task.__table__.update`, `update(Task.__table__)`, `builtins.setattr`, `for ... .state`,
  `with ... as ... .state`, and `Task(**{"state": ...})`. Existing table-object matches
  are in excluded `app/tests/` files.
- Lint: `ruff check` on both touched Python files — passed.
- L4: `BEYO_TEST_SLOT=r1 PYTHONPATH=. pytest -m 'not e2e'` → **23 failed / 3668 passed /
  1 skipped**, 3692 collected. The 23 are exactly the published 21-ID baseline plus:
  `tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]`
  and `tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker`.
  Failure-ID diff is empty in both directions. Arithmetic: `23 = 21 + 2`; `23 + 3668 + 1 = 3692`.

## Write perimeter

Fix changes:

- `app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py`
- `app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py`
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_10.md`
- this handoff file

Applied-and-reverted mutation/probe file:

- `app/beyo_manager/services/commands/tasks/update_task.py` — EOF plant only; no final diff.

No Architecture Graph mutation was recorded: this is a test instrument extension and does
not create or alter an independently named runtime architectural boundary. The graph was
checked for orientation before implementation; no source anchor or architecture concept
needed updating.

## Owner decisions

### ⚠ OWNER DECISIONS REQUIRED (0)

None. The existing migrations exclusion remains the owner question already recorded in
§5B; this follow-up does not widen or resolve it.

Anything found wrong: no live production/script instance of the four forms was found, and
no production behavior or registry classification required change.
