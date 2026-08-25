---
plan: plan_2
role: maintenance
round: 1
date: 2026-08-25
---

# Maintenance — stabilize the order-dependent full-suite baseline

The owner authorized a separate maintenance cycle to stabilize the unrelated fixture coupling
that blocks the Plan 2 checkpoint. Work in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Read `/Users/davidloorenz/agent-skills/implementation-executor.md` and
`/Users/davidloorenz/agent-skills/pipeline-charter.md` first. This is maintenance work, not
Plan 2 implementation: do not modify any Task Budget Signal production, integration, plan,
or architecture-graph artifact.

## Evidence to start from

Read:

- `handoffs/implementer/20260825_plan_2_implementation_round_2.md` — the captured two-run
  anomaly and exact failing IDs;
- `tests/integration/models/users/test_user_work_profile_clock_in_code.py`;
- `tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`, especially C10;
- `tests/integration/services/queries/item_economics/_narrowing_fixture.py`;
- master-plan §10 for disposable-DB safety and the full-suite baseline protocol.

## Allowed perimeter

Only these pre-existing test/fixture files may change, and only to remove their inter-test
database assumptions:

1. `app/tests/integration/models/users/test_user_work_profile_clock_in_code.py`;
2. `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`;
3. `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`, only if the
   C10 repair belongs in that shared fixture helper.

You may also write your report under `handoffs/maintenance/`. No application code, migrations,
Task Budget Signal files, plans, master plan, intention, prompts, or architecture graph writes.
If the repair needs any other file, stop and report it rather than expanding scope.

## Required outcome

Each affected test must seed and clean up every prerequisite it owns; it must not depend on
another test file having run first. Preserve the existing behavior each test is meant to prove.
Add no convenience or unrelated coverage.

Prove the repair at the smallest useful scopes:

1. each affected test file alone;
2. both affected files serially in each order (`-n 0`), demonstrating order independence;
3. this cycle's exactly **one** L4 run: `PYTHONPATH=. pytest -m 'not e2e'`, with the full
   failing-ID delta against the durable 21-ID baseline captured before any anomaly recovery.

If the L4 run is anomalous, follow the charter flaky-capture procedure; do not take an
unbounded sequence of full-suite retries. Do not make a Plan 2 checkpoint.

Write `handoffs/maintenance/20260825_full_suite_fixture_order_stabilization_round_1.md` with
frontmatter, exact perimeter, root cause, tests/evidence/tree identity, remaining blocker if
any, and owner-layer final response. The coordinator will decide whether its evidence unblocks
Plan 2.
