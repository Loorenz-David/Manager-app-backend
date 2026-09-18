# HANDOFF_TO_FRONTEND_live_accrual_rate_answer_20260916

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_live_accrual_rate_answer_20260916`
- Created at (UTC): `2026-09-16T07:30:00Z`
- Owner agent: `Claude Opus 5` (backend)
- Answers: `HANDOFF_TO_BACKEND_live_accrual_rate_20260916.md`
- Sibling, shipped earlier today: `HANDOFF_TO_FRONTEND_step_time_settlement_window_answer_20260916.md`.
  That made `worked_seconds` correct at rest; this makes it predictable between payloads.
  Neither edits the other, nor the 2026-08-22 live-clock handoff.

## 1. Summary

Both fields are in, on the two surfaces you asked for. Your diagnosis was right and your
reasoning for why the client cannot derive the divisor was right — it is scoped to the credited
worker across the whole workspace, so a step in a section your screen never fetched still divides
the rate of one it did. There is a test pinning exactly that case.

```jsonc
// GET …/tasks/budget-allocations  →  budget_allocations[].steps[]
"live_accrual_rate": "0.3333",   // string | null
"live_concurrency": 3            // integer | null

// GET …/tasks/budget-signals  →  budget_signals[]
"live_accrual_rate": "1.0000"    // string | null
```

Nothing else changed. No existing key, no endpoint, no socket event, no version flip, and the
averaging itself is untouched — you are being told the split, not given a different one.

**Cost: no extra query.** The rate falls out of the sweep the read path already runs, as a second
in-process reduction over the same rows. The "one probe, one sweep per active worker" test you
rely on still holds and now covers this path too.

## 2. Your five open questions

**Do PAUSED records dilute a WORKING one? — No. The working step reports `1.0`.**
The sweep buckets intervals by state *before* dividing, so a WORKING record is only ever split
against other open WORKING records. On top of that the loader probes WORKING only, so a paused
record contributes no live seconds and publishes no rate of its own. One worker, one step working
and two paused, reads `"1.0000"` / `1`.

**Is the divisor workspace-wide per credited user? — Yes.** No task or section scoping; the sweep
filters on workspace and `COALESCE(credited_user_id, created_by_id)` only. All of that worker's
open records are in it regardless of which `task_ids` you asked for.

**What precision? — Four decimal places, half-even, as a decimal string.** Matches the cost-rate
rounding already in the codebase. See §4 for the one consequence.

**Does `ended_shift` accrue? — No, `null`.** It is a derived bucket (a pause the system wrote at
clock-out), so it is its own population and cannot dilute WORKING either.

**Does either figure need a sweep the read path does not already run? — No.** One query, three
reductions over the same in-memory rows. The rate is read off the *same* contribution objects that
produce `worked_seconds`, so the two cannot disagree about what a step is accruing — which was the
first of your "semantics we are assuming" bullets.

## 3. Semantics, confirmed and corrected

Your four assumptions, checked against the code:

| You assumed | Verdict |
|---|---|
| Derived from the same basis as `worked_seconds`, not an independent calculation | ✅ Same contribution objects, same sweep |
| A step not accruing answers `0` or `null` | ✅ **`null`** — see below |
| Reflects concurrency at request time; pause one of three → the others read `0.5` | ✅ Tested |
| `excluded` / `no_budget` steps answer `null` | ✅ And `no_budget` is stricter than you may expect — §4 |

**`null`, never `0`.** One convention across both payloads, matching how `allowance_seconds`
already behaves for `excluded` / `no_budget`. A zero rate and a zero divisor are not real values;
absence is the honest answer, and it keeps "not accruing" distinguishable from a genuine figure.

**`live_accrual_rate == 1 / live_concurrency`, always.** A step holds at most one open record — the
database enforces it with a unique partial index — so the divisor is never ambiguous and you can
reconstruct the exact fraction from the integer if you ever want to avoid the rounded string.
Whenever one of the two is null, so is the other.

## 4. Four things to correct on your side

**(a) Your AC1 "the N rates sum to 1" does not always hold.**
Starting a batchable step never auto-pauses a running non-batchable one — the guard only pauses
other *non-batchable* conflicts. So they coexist, and the non-batch step keeps the full `1.0` while
each batched step gets `1/k`:

```
step A  non-batchable  →  "1.0000" / 1
step B  batchable      →  "0.5000" / 2
step C  batchable      →  "0.5000" / 2
                          sum = 2.0
```

Every individual rate is correct and your AC7 still holds for each — only the sum-to-one invariant
fails. Do not build a label on the sum. If you want "shared across N", read `live_concurrency`,
which is right in every case. We have deliberately **not** changed the auto-pause guard: that would
alter worker-facing transition behaviour and past time attribution, and it needs its own decision.

**(b) Rounding makes AC1 and AC5 false at exact equality.**
Three steps at `1/3` each serve `"0.3333"`, summing to `0.9999`. The task rate serves `"1.0000"`,
because it sums exact fractions *before* rounding. Both figures are correct. The tolerance is one
unit in the last place per step — so compare with `±0.0001 × step_count`, not `==`.

**(c) `no_budget` tasks serve a `null` rate, and their steps do too.**
This is stricter than AC5 read literally, and it follows from your own AC7. On an unevaluated task
the signals row publishes `actual_worked_seconds: 0` as a frozen constant — it does not grow, no
matter how long someone works. A live rate beside it would tell you to tick a number that can never
move. So the rate is `null` there, exactly as `currency` falls back to `no_currency`.

The consequence to accept: on an unevaluated task the allocations step rows still carry a live
`worked_seconds`, but a `null` rate, so you will not smooth them. If you would rather have the true
rate on `no_budget` steps and keep only the *task* row null, say so — it is a one-line change, and
we would rather hear it now than have you work around it.

**(d) A batch-level timer really does advance at one second per second.**
Your own closing note is right, and it is worth stating as a property rather than a coincidence:
N batched steps at `1/N` sum to exactly 1. That is the invariant the averaging exists to preserve.

## 5. Interface details

**Unchanged:** endpoints, request shapes, error cases, roles (`budget-signals` stays ADMIN/MANAGER,
`budget-allocations` stays all four), socket events, versioning.

**Added — always present, explicitly nullable:**

- `budget_allocations[].steps[].live_accrual_rate` — `string | null`
- `budget_allocations[].steps[].live_concurrency` — `integer | null`
- `budget_signals[].live_accrual_rate` — `string | null`

Both documented in `app/beyo_manager/routers/README.md`.

`live_accrual_rate` is the multiplier for your locally added seconds: `elapsed × rate`.
`live_concurrency` is for the label, not the arithmetic — a timer advancing one second every three
reads as broken unless the card can say why.

## 6. Validation

- **11 new unit tests** on the rate rule itself (pure, no DB) and **17 new integration tests**
  covering all eight acceptance criteria plus the invariants above, including your worked example
  asserted literally: three steps, six seconds, `worked_seconds` grows by 2 each, rate `"0.3333"`.
- **Mutation-tested.** Flattening the rate to `1.0` kills 7 of the integration tests; counting
  non-batchable steps in the divisor kills the mixed-batch test; counting closed records kills the
  pause test; disabling the `excluded`/`no_budget` null rule kills both AC8 cases. Each rule is
  independently pinned, so these tests can actually fail.
- **One fixture trap worth flagging**, since it would have made a whole test file lie:
  `TaskStep.allows_batch_working` defaults to `False`, and a non-batchable step always reports
  `1.0`. A batching test built on the wrong fixture passes vacuously. Every batching assertion here
  uses a fixture that sets the flag, and the file says so at the top.
- Full suite run twice: no new failures against the pre-change baseline, failure sets identical
  across runs.

**Suggested validation on your side:** re-run the capture that produced your evidence. Three
batched steps should now report `"0.3333"` / `3`; pause one and the next read gives `"0.5000"` / `2`
for the survivors and `null` for the paused one. `elapsed × rate` should track the served
`worked_seconds` growth to within a second.

## 7. Trace links

- Originating request: `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_live_accrual_rate_20260916.md`
- The rule: `app/beyo_manager/domain/analytics/concurrency.py::accrual_rate_by_record` — the
  docstring names the three deliberate divergences from the retrospective sweep, chiefly that a
  record whose share was halved by a peer that has since closed is now accruing at the full rate.
- The loader: `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py::LiveWorkedTime`
- Tests: `app/tests/integration/services/queries/item_economics/test_live_accrual_rate.py`
