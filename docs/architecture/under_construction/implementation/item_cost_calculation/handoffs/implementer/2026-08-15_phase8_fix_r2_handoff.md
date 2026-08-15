---
plan: phase 8 — status & results
role: fix
state: IMPLEMENTED
date: 2026-08-15
actor: Codex
---

# Phase 8 fix r2 — implementer handoff

## Summary

Fix r2 is implemented and checkpointed at `69883648d59d8e9902c7b754b73afa3b9fb768f9`.
The cycle is test-side only: no production application file, migration, or
Architecture Graph record was changed. The tracker is `IMPLEMENTED` and the
phase Review log contains the append-only closeout entry.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The fix stayed inside the governing H1–H7 contract.

## Acceptance rows

- [x] **H1:** two real integration rows update a committed evaluation and call
  `get_task_budget_status`; `allowed_worker_minutes <= 0` is INFEASIBLE with
  `percent_consumed is None`, and the positive row is OK. The three
  SimpleNamespace C7 echo rows were removed.
- [x] **H2:** the consumption row carries nonzero pause, ended-shift, and
  inaccurate seconds and still asserts WORKING seconds alone.
- [x] **H3:** both C1 probe rows assert candidate sets rather than physical row
  order. The pair passed 2/2 on each of 10 consecutive runs (20 passes total);
  M1, M2, and M3 still redden their named rows.
- [x] **H4:** the C5 replay row commits a real superseding production basis
  version with a different rate after close, proves the new rate would produce
  a different consumed cost, and proves the §8A.4 result column set is unchanged.
- [x] **H5:** C3 uses two tasks, each with its own committed evaluation; each
  episode is 1800 seconds and their sum is 3600 seconds.
- [x] **H6:** the C6b re-entry assertion counts result rows; the G7 structural
  assertion quantifies `response_model is None` over all
  `item_economics.router.routes`.
- [x] **H7:** zero production edits, zero migration edits, and zero graph writes.

## Write perimeter

The final checkpoint contains exactly these six files:

- `app/tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py`
- `app/tests/integration/services/commands/item_economics/test_phase8_status_results.py`
- `app/tests/unit/services/queries/item_economics/test_phase8_serializers.py`
- `app/tests/unit/routers/api_v1/test_item_economics_router.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8_status_results.md`

The production files below were temporary mutation-probe targets only. Each was
patched, tested, reverted, and restored before the checkpoint:

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
  — MX2 and M1.
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
  — M2.
- `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py`
  — MX1, M3, and M17.

The final production hashes restored to the r2 pre-image are:

```text
d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172  app/beyo_manager/services/tasks/analytics/process_item_cost_result.py
5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8  app/beyo_manager/services/queries/item_economics/get_task_budget_status.py
011cf2ae76dde81fe837a1f7b5f8a869230621001c64af06feb7718951970f00  app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py
```

Final hashes for the four changed test files:

```text
7df683f793d996a0869f9360b153ff56578c85b7df3d6d6881aae95ad026fbfb  app/tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py
adef4c5b2de9bf40dc95488a233509bcfce7a9ea0694afcaf79eed13202ec53c  app/tests/integration/services/commands/item_economics/test_phase8_status_results.py
683ba963b475ad3bbbc2ab0961af7b490c510dabca65f699c008b861c7fe3dc5  app/tests/unit/services/queries/item_economics/test_phase8_serializers.py
cba1fed45366100bdecd6734f6ad5db7a92ed3acb458f91dad24fce99e4529c3  app/tests/unit/routers/api_v1/test_item_economics_router.py
```

## Mutation ledger

All rows were applied in the main worktree, run against the named focused row,
reverted immediately, and hash-checked. There were zero deferrals.

| row | mutation site | expected red node | before sha256 → mutant sha256 | observed red |
|---|---|---|---|---|
| MX1 | `process_item_cost_result.py`: add `total_pause_seconds` to the consumption sum | `test_c4_consumption_excludes_deleted_steps_but_counts_skipped_steps` | `d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172` → `fdae3c4106686398559c4c50574b9653d4b0a5d26f80e430f42dfa9f87b490b7` | `assert 150 == 120` |
| MX2 | `get_task_budget_status.py`: collapse the status ternary to constant OK | `test_c7_committed_evaluation_branch_drives_evaluated_status[P-V-infeasible]` | `5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8` → `57c4591f8d21fbdb5940cc9262012d0d41f33465e47a05c96ffd98ec23d2c140` | `assert 'ok' == 'infeasible'` |
| M1 | `get_task_budget_status.py`: remove committed/current/not-deleted evaluation filters | `test_probe_c1_projection_isolation_with_a_discriminating_fixture` | `5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8` → `3a659e93e75a134df29540b956f72028686b04bb070325dbf6e856ca9bf95c3a` | committed evaluation id assertion failed |
| M2 | `get_task_budget_status_worker.py`: remove committed/current/not-deleted evaluation filters | `test_probe_c1_worker_service_filter_is_independent_and_projection_blind` | `011cf2ae76dde81fe837a1f7b5f8a869230621001c64af06feb7718951970f00` → `783698f82ff07ae145b31266569ebd3014049ac3eea07c82ca57f3b8b66a29d0` | worker committed evaluation id assertion failed |
| M3 | `process_item_cost_result.py`: remove committed/current/not-deleted evaluation filters | `test_probe_c1_projection_isolation_with_a_discriminating_fixture` | `d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172` → `14bb672db9e6c5b2fb3e0deb87b70e80df71452e5e5b97ced3fb0f3628ded095` | result evaluation id assertion failed |
| M17 | `process_item_cost_result.py`: remove `computed_at` from the upsert SET list | `test_c5_replay_updates_only_computed_at_and_converges` | `d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172` → `1929a4c07c8c7bf9c01167a4a4a8da3dd151cb184619701e9cab3a6215b4f512` | `assert second.computed_at > first_computed_at` failed |

## Verification

- Focused phase suite: **146 passed**.
- H3 repeated subset: **2 passed × 10 runs**, no flakes.
- Full `PYTHONPATH=. pytest -m 'not e2e'`: **2138 passed / 23 established
  failures / 1 deselected / 2 warnings**. The sorted failure IDs are the exact
  23-item phase-1 baseline set.
- Ruff: the three directly edited non-adopted test files pass. The adopted probe
  has one pre-existing `F401` for `ItemMajorCategoryEnum`; H3 touched only its
  two authorized rows, so that unrelated import was not changed.
- Database: Alembic reports `c1d2e3f4a5b6 (head)`. Direct read-only checks found
  `item_cost_evaluations = 0`, `item_cost_results = 0`, and
  `execution_tasks(task_type = process_item_cost_result) = 0`.
- Architecture Graph: read-only status/validation only; 172 nodes / 254 edges,
  revision `c74eb91304146d284be10e7eb88dbb26ddfa709daca9849bab0d489c7a966166`,
  stale 1, pending 21, zero delta and no review mutation.

## Closing state

Checkpoint: `69883648d59d8e9902c7b754b73afa3b9fb768f9`.
The handoff is deposited after that checkpoint, per protocol.
