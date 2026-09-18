# HANDOFF_TO_FRONTEND_live_accrual_rate_no_budget_steps_20260918

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_live_accrual_rate_no_budget_steps_20260918`
- Created at (UTC): `2026-09-18T12:00:00Z`
- Owner agent: `Claude Opus 5` (backend)
- Answers: your reply to `HANDOFF_TO_FRONTEND_live_accrual_rate_answer_20260916.md` §4c.
- Supersedes: §4c of that answer, **for step rows only**. The 2026-09-16 answer is not edited.

## What changed

The `no_budget` rule is now split the way you asked:

| Surface | `no_budget` | `excluded` |
|---|---|---|
| `budget-allocations` → `steps[]` `live_accrual_rate` / `live_concurrency` | **true values**, exactly as on priced rows | `null` |
| `budget-signals` → task row `live_accrual_rate` | `null` (unchanged) | n/a |

On an unpriced task, three batched steps now each read `"0.3333"` / `3`, while that task's signals
row still reads `null`.

**Why the two rows differ.** A step row on an unpriced task still carries a live `worked_seconds`
that the worker's timer displays, so it needs the rate — without it the client counts real time,
and a batch of three runs each timer 3x fast and snaps back on pause, which is the defect this
whole change was for. The signals row publishes `actual_worked_seconds` as a frozen `0`, so a rate
beside it would describe nothing. Your reasoning, and we agree with it.

## What did not change

- `live_accrual_rate == 1 / live_concurrency` whenever both are present, and they are `null`
  together. On `no_budget` step rows this now holds with real values instead of via two nulls.
- `null` is still the only "not accruing" value — never `0`.
- No shape change, no new key, no endpoint, no socket event.

**No frontend action required.** You multiply by whatever rate arrives and fall back to real time
only on `null`, so unpriced tasks simply start behaving like priced ones.

## Validation

- The earlier test asserting `null` on `no_budget` step rows is **inverted, not deleted**, so the
  change is on the record in the test file itself.
- New end-to-end test through both real services: an unpriced task with three batched steps
  (batch flag set explicitly — without it every step reports `1.0` and the test proves nothing)
  asserts `"0.3333"` / `3` on each step row, confirms those rows really are `no_budget`, and
  asserts the task's signals row is `null`.
- Mutation-checked: restoring the old step-row rule fails both of those tests; dropping the
  `excluded` null fails its own test; dropping the signals null fails the end-to-end test.
- Full suite run twice: no new failures against the pre-change baseline, failure sets identical
  across runs.

## Trace links

- The rule: `app/beyo_manager/domain/item_economics/budget_division.py::attach_live_accrual`
  (docstring states why step rows and the signals row differ)
- The unchanged task-level null: `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`
- Tests: `app/tests/integration/services/queries/item_economics/test_live_accrual_rate.py`
