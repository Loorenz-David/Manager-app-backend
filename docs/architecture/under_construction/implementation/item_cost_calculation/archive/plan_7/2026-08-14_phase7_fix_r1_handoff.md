---
plan: phase 7 (evaluations — commit/supersede, projections, promotion, auto path)
role: fix
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
---

Phase 7 fix r1 is implemented and checkpointed at `bb233db` (`CHECKPOINT (not
approved): item-cost phase 7 fix r1 — close review findings`). The projection
mirror no longer mutates the valuation chain, the reviewer’s missing criterion
rows are live, and the committing concurrency/C8/C10 observables are verified.

⚠ OWNER DECISIONS REQUIRED (0)

None. No owner card was opened, and no Architecture Graph review decision was
made.

## Changes delivered

- `_commit_item_cost_evaluation_in_session` gates the valuation mirror on
  `ItemCostEvaluationKindEnum.COMMITTED`; its docstring enumerates the
  kind-gated effects.
- Adopted the preserved reviewer probes into
  `test_phase7_criteria.py` and `test_phase7_concurrency.py`, retaining the
  exact source bytes before adding required parameter IDs and fix assertions.
  Source hashes were `a26f11c178d39f000d08c5080cf8b5dfbc1e451848a3d205182e386f2170f9e4`
  and `e42d59d35a395f09ae1155c2bd628a38da1b76338ca1691d2715a7aa58c9035e`.
- Removed the empirically unbuildable direct-INSERT C2 fixture and added the
  existing unit translation row for
  `uix_item_cost_evaluations_current` → `ITEM_COST_CONCURRENT_COMMIT`.
- Reworked C8 to commit its fixture and compare all projection columns,
  including `updated_at`, via a fresh second session.
- Added C9’s literal `no_primary_item` assertion and C10’s exactly-once,
  after-commit second-session visibility checks.
- Strengthened P-Z to assert each predecessor’s exact successor.
- Removed the dead promotion `task_client_id` branch, the no-op request
  validator, and the stray blank line. No migration was added.

## Verification

- Focused phase-7 surface: **82 passed**.
- Committing concurrency subset: **5 passed twice**.
- Phase-5 valuation/request surface: **55 passed** (the former 54 plus the
  new conflict-translation row).
- Full foreground non-E2E suite: **2076 passed / 23 established baseline
  failures / 1 deselected**. The 23 failure IDs are set-identical to the
  phase-1 baseline; no new failure was introduced.
- Ruff and `git diff --check`: clean.
- Alembic: `be9dfe42a035 (head)`.
- Economics-table residue check: zero rows in
  `item_cost_evaluations`, `item_cost_evaluation_terms`, `item_valuations`,
  `production_cost_groups`, `production_cost_group_sections`,
  `production_cost_basis_versions`, `cost_model_versions`, and
  `cost_model_terms`. The wider suite’s known non-economics residue policy is
  unchanged.

## Mutation ledger

Every mutant below was run in the main worktree, observed red, and restored.
The M3/M4 probes were run on the named row-1 BASIS/MODEL cases only.

| ID | Mutant hash | Observed red |
|---|---|---|
| F1 | `cea28666827471fc7e8e5b1d42c14a0522a4777e0c189e8681772e1cb11b9f24` | C5 row 7 projection override valuation-identity assertion |
| M1 | `50e207f5be14b8fe1568065339973962a0158f18a409d58b0fc19c0a0215850f` | C11 task-lock probe: expected `asyncio.TimeoutError` was absent |
| M2 | `893be91da0d81a0f12b8d1b8ad3a35adb44776f4d25d47a85c7de4231f47d188` | C5r6 valuation-lock probe: expected timeout was absent |
| M3 | `a8e12a29ca62d8903655b17cece82f66c3d4e3b4e0b966d69725cbdc5d7664ba` | C12 row 1 BASIS: expected `ValidationError` was absent |
| M4 | `3b29a3c7c149aa7d90885e4ea2459b86c685661cd31a43be61554c22100d8b26` | C12 row 1 MODEL: expected `ValidationError` was absent |
| M5 | `40f8718250d50a329fc35a458fb1d8b01e3e6f71877be6c4130ea3e7e9fa4007` | Projection snapshot and C1 immutability assertions |
| M6 | `412b3d462de146247cf88ae2f31103b14cd357208ffd7b602e05af30b85c96f5` | Authoritative route-table completeness assertion |
| M7 | `999788369bcfe2aa961a4c376577e70139d6e04460d4c057f4dffe2d0cff7fec` | Overflow savepoint test: `PendingRollbackError` |

Final production hashes:

- `commit_item_cost_evaluation.py` — `4df51dcb2bb0473d880974eb9184832af85780b9b9d0084d788529526a8c596e`
- `promote_item_cost_projection.py` — `c65735e141c0e3a0cdd6c92e593b8c9ae5032fb95d6a1c1d99a67c4cf51b12ab`
- `requests/__init__.py` — `a71379b712adbe22aea0868f78c0f4eefa21953eac0c166846d4fa199bf12aad`
- `create_task.py` — `25cc342060b03c3ca5fc867791bcae9a6f91cb2f2b115ac3756631b1214ca8e7`

## Full write perimeter

Production files:

- `app/beyo_manager/services/commands/item_economics/commit_item_cost_evaluation.py`
- `app/beyo_manager/services/commands/item_economics/promote_item_cost_projection.py`
- `app/beyo_manager/services/commands/item_economics/requests/__init__.py`
- `app/beyo_manager/services/commands/tasks/create_task.py`

Verification files:

- `app/tests/integration/services/commands/item_economics/test_phase7_evaluations.py`
- `app/tests/integration/services/commands/item_economics/test_phase7_criteria.py`
- `app/tests/integration/services/commands/item_economics/test_phase7_concurrency.py`
- `app/tests/unit/services/commands/item_economics/test_item_economics_requests.py`

Planning records updated before the checkpoint:

- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_7_evaluations.md`

Probe-only mutation residue was restored and is not part of the checkpoint;
the router’s final hash is the unchanged baseline
`87fcb318050bb089e3e8a5f101e2c47a7def0f68ed85da17d016d4ae544840ae`.

## Architecture Graph

Read-only orientation/status was completed. The graph remains at 166 nodes,
239 edges, 52 pending items, revision
`0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c`; this fix
cycle records **zero architectural delta**. No item was promoted, rejected,
edited, deprecated, or removed.

## Delegations and scope choices

- Reviewer probes were copied exactly from the preserved source files and then
  extended only where the fix prompt required IDs/assertions; source files were
  retained.
- The direct-INSERT C2 direction was removed rather than inventing a fixture
  that PostgreSQL’s FK lock semantics make unreachable.
- The existing request-translation unit test was extended instead of creating
  a duplicate test file.
- No owner decisions, migrations, router production changes, or graph
  adjudications were required.
