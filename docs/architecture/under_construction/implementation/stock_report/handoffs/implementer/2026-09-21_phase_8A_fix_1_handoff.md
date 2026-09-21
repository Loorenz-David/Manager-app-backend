---
plan: 8A
role: fix
round: 1
state: CHECKPOINT_NOT_APPROVED
date: 2026-09-21
actor: Codex (terra)
---

# Phase 8A fix 1 — C1(b) production-instance fixture

Closed finding: **P8A-R1-04** only.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Summary

Replaced the three `SimpleNamespace` evaluator inputs in
`app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py` with transient,
un-persisted production model instances:

- `StockReportItem(is_deleted=False, item_category_id="category-1")`
- `Task(is_deleted=False, state=TaskStateEnum.FAILED)`
- `Item(is_deleted=False, item_category_id="category-2")`

The models construct without a session or database. The row's nine check names, expected results,
advisory assertions, and `first_failed_check` assertion were left unchanged. No production code was
changed.

## Verification

### Targeted file

Command:

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/unit/domain/stock_report/test_stock_report_assignment_checks.py
```

Result: `1 passed`.

### C1(b) named mutation re-run

Mutation site: `app/beyo_manager/domain/stock_report/assignment_checks.py`, definition site
`evaluate_assignment_checks`; inserted an early `return results` immediately after appending the
first failed check result.

Command:

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/unit/domain/stock_report/test_stock_report_assignment_checks.py
```

Observed red:

```text
FAILED tests/unit/domain/stock_report/test_stock_report_assignment_checks.py::test_assignment_checks_returns_all_results_in_precedence_order
AssertionError at test_stock_report_assignment_checks.py:24
asserted nine check names; returned list stopped at item_not_task_primary
1 failed
```

The mutation was reverted. Proof:

```text
git diff --quiet -- app/beyo_manager/domain/stock_report/assignment_checks.py
revert_exit=0
```

Mutation-probe file, applied and reverted: `app/beyo_manager/domain/stock_report/assignment_checks.py`.

### Lint

```text
cd app && ruff check tests/unit/domain/stock_report/test_stock_report_assignment_checks.py
```

Result: `All checks passed!`

### One authoritative L4

Command:

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'
```

Result: `23 failed, 3661 passed, 1 skipped` in 76.12s. Observed arithmetic is
`23 + 3661 + 1 = 3685` collected; this run's pass count is reported from the observed result, not
from an earlier checkpoint.

Failure-ID comparison against the published 21-ID set in the archive handoff:

- Current minus published: exactly these two expected slot-sensitive isolation tests:

  ```text
  tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]
  tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker
  ```

- Published minus current: empty.

The remaining 21 failure IDs are identical to the published set. The two additional failures are
the known ambient-slot assertions and are not part of this finding.

## Perimeter and graph

Fix changes:

- `app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py`
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_8A.md` (Review log only)
- this handoff

Mutation probe, applied and reverted separately:

- `app/beyo_manager/domain/stock_report/assignment_checks.py`

Unrelated concurrent Batch C2 edits and other pre-existing worktree changes were preserved. No
Architecture Graph mutation was needed; the existing evaluator architecture is unchanged. No owner
decision cards are open.

Checkpoint subject: `CHECKPOINT (not approved): phase 8A fix 1`.
