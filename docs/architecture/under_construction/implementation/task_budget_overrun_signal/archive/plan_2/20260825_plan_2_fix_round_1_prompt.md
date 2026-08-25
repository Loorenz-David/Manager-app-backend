---
plan: plan_2
role: fix
round: 1
date: 2026-08-25
---

# Fix Plan 2 review r1 — money-field mapping and non-vacuity

Resolve the Plan 2 review-r1 findings in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.
Invoke the `implementation-executor` skill and charter. The current Plan 2 is authoritative.

## Gates and read order

Confirm: ratified intention header (round 12); Plan 1 `APPROVED`; Plan 2
`CHANGES_REQUESTED`; checkpoint `8a63402`; and the review-r1 handoff plus its owner-approved
count correction already folded into the intention, master plan, and plans. Read Plan 2 in full,
then `handoffs/reviewer/20260825_plan_2_review_round_1.md` before editing.

## Allowed executable perimeter

Only these executable files may change:

1. `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`;
2. `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py`.

Tracker/Review-log updates, the fix handoff, and the checkpoint commit are closing artifacts.
No serializer, C19, maintenance, route, graph, or other application/test file changes. The
already folded intention/master-plan/plan changes are coordinator work; do not alter them.

## Required corrections

Implement the review correction exactly:

- Add C8(e), using the Plan 2 fixture and exact expected tuple
  `60, 4, 810, 51, over`; it must assert both money fields independently.
- Add and run MUT-19 at the service row-dict call site: transpose `over_cost_minor` and
  `projected_over_cost_minor`; C8(e) must redden.
- Make C4(b)'s two-row fixture assert `len(rows) == 2` and C4(c)'s flatness test assert a
  non-empty `result["budget_signals"]` list, as the amended plan requires.

Resolve, do not relitigate; add no tests beyond C8(e)'s criterion and those two prescribed
non-vacuity assertions.

## Evidence and closeout

Because this fix edits the phase test file, rerun all **19** named mutations (the retained 18
plus MUT-19) at their declared sites, then revert and record every observed red. Retained rows
from the prior ledger do not survive a test-file edit without re-execution. Run L1/L2 as needed.
This fix cycle's L4 budget is exactly **1** run: `PYTHONPATH=. pytest -m 'not e2e'` on the final
tree, with failing-ID delta against the durable 21-ID baseline.

No architecture-graph mutation is expected; inspect/status only if needed and report the
no-delta assessment. On success update only Plan 2 to `IMPLEMENTED`, append its Review log,
make a checkpoint commit prefixed `CHECKPOINT (not approved):`, and write
`handoffs/implementer/20260825_plan_2_fix_round_1.md` with full perimeter, 19-row mutation
ledger, evidence, and owner layer. The re-review will be delta-scoped to this perimeter.
