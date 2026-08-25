---
plan: plan_3
role: implement
round: 2
state: IMPLEMENTED
date: 2026-08-25
actor: Codex
---

# Plan 3 fix round 1 — C4(d) exact README cell assertions

## Outcome

SF1 from review round 1 is closed. The sole implementation change is the C4(d) test in
`app/tests/unit/routers/api_v1/test_budget_signals_route.py`. It now checks one exact table cell
for every field: `task_id`, `budget_state`, and `currency` must be `string` and `Yes`; the seven
numeric fields must be `integer` and `Yes`. The production route, README, frontend handoff,
intention, route table, and Architecture Graph were not changed.

## Gate and scope

- Intention: `planning/intention.md`, RATIFIED round 13.
- Phase 2: APPROVED.
- Phase 3 on entry: CHANGES_REQUESTED for SF1 only.
- Review authority: `handoffs/reviewer/20260825_plan_3_review_round_1.md`, SF1 and its two
  named mutations. N2–N6 were carried as non-blocking lessons and did not expand this fix.
- Implementation write perimeter: exactly one file,
  `app/tests/unit/routers/api_v1/test_budget_signals_route.py`.
- Closeout-only writes: this handoff, the Phase 3 tracker row in `master_plan.md`, and this
  append-only entry in `plans/plan_3.md`.
- README was probe-only; no final README change is present.

## Trace map

| Criterion | Test/evidence | Result |
|---|---|---|
| C4(d), all ten field rows | `test_budget_signals_readme_detail_documents_the_ten_field_contract` | Exact type and `Required: Yes` cell asserted per field; green |
| C4(d), numeric type sub-check | Same test, seven-field numeric loop | `integer` asserted for `over_seconds`, `over_cost_minor`, `projected_over_seconds`, `projected_over_cost_minor`, `allowed_seconds`, `actual_worked_seconds`, and `cost_per_worker_minute_ten_thousandths` |
| C4(d), string type sub-check | Same test, three-field string loop | `string` asserted for `task_id`, `budget_state`, and `currency` |
| Fix perimeter | `git diff --name-only` and final status | No production or README change; unrelated pre-existing dirty work preserved |

## Mutation evidence

The README was checksum-verified before and after each probe. Restored checksum:

`e23b93f8b17cb1d9034383a255254e81ec00f1f48b53a7cec6a1697e90db6620  app/beyo_manager/routers/README.md`

1. Changed `data.budget_signals[].over_seconds` from `integer | Yes` to `string | Yes`.
   The C4(d) test reddened at the numeric exact-cell assertion for `over_seconds` (`1 failed`).
   Reverted and checksum matched.
2. Changed a different row, `data.budget_signals[].allowed_seconds`, from `Required: Yes` to
   `Required: No`. The C4(d) test reddened at the numeric exact-cell assertion for
   `allowed_seconds` (`1 failed`). Reverted and checksum matched.

These were separate runs, so each sub-check was independently shown to reject its named defect.

## Test evidence

Pre-fix L1 baseline, before the test edit:

`PYTHONPATH=. pytest tests/unit/routers/api_v1/test_budget_signals_route.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs/test_budget_signals_handoff.py -q`

Result: **13 passed**.

Post-fix L1, after both probes were reverted:

`PYTHONPATH=. pytest tests/unit/routers/api_v1/test_budget_signals_route.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs/test_budget_signals_handoff.py -q`

Result: **13 passed**.

The prior durable L4 baseline is the 21-ID set in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7. The
required single closing L4 for this fix cycle ran on the handed-over tree below.

`PYTHONPATH=. pytest -m 'not e2e'` from `app/`

Result: **21 failed / 2800 passed / 1 skipped / 2 warnings in 52.16s**.

The failing-ID set was compared member-by-member with the durable 21-ID baseline: **additions: 0;
removals: 0**. All six C5(a) sibling files remained absent from the failing set. The test suite's
21 failures are pre-existing baseline failures and are not caused by this test-only fix.

The fix-tree diff digest immediately before the L4 run, excluding unrelated pre-existing dirty
paths and untracked prompt/reviewer material, was
`6fcb43b2772f266fd33eabb592aa42ff5a21d92091cfb95943241424e0ff6411`. The only app diff in that
tree was the corrected test file; the L4 did not mutate source files.

## Graph and disposition

No Architecture Graph tool was called and no graph state changed. The existing Phase 3 endpoint
delta remains the prior session's responsibility. N2 (operation-id guard), N3 (union observation),
N4 (sequential mutation coverage lesson), N5 (frontend table criterion candidate), and N6
(historical prose count) remain non-blocking coordinator/planner lessons; none is a fix-round
scope item.

## Closing record

- Phase 3 tracker is set to `IMPLEMENTED`.
- The plan Review log has one append-only fix-round closeout entry.
- Checkpoint commit subject will use the required prefix:
  `CHECKPOINT (not approved): fix plan 3 C4(d) README cell assertions`.
