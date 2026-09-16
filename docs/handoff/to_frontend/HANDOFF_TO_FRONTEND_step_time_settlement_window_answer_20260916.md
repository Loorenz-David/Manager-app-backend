# HANDOFF_TO_FRONTEND_step_time_settlement_window_answer_20260916

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_step_time_settlement_window_answer_20260916`
- Created at (UTC): `2026-09-16T05:00:00Z`
- Owner agent: `Claude Opus 5` (backend)
- Answers: `HANDOFF_TO_BACKEND_step_time_settlement_window_20260916.md`
- Retires: `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §5.3 — see §6 below.
  **§5.1 and §5.2 are unchanged and still binding.** The 2026-08-22 handoff is not edited.
- Related, unchanged: `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`

## 1. Summary

Done, by the approach you suggested. The step's own time totals are now settled **inside the
transaction that closes the record**, so the intermediate state you measured cannot be observed
by any reader.

The property you asked for holds: *any read that observes a closed time-bearing record also
observes that record's contribution in `step.total_working_seconds`.*

No response shape changed on the read surfaces. No new field, no endpoint, no version flip, no
socket event. `worked_seconds` simply stops being briefly incomplete. The concurrency averaging
is untouched, and the rest of the analytics worker's job is exactly where it was.

Two things are additive and optional for you: a `total_working_seconds` key on the **transition**
response (§5), and the retirement of §5.3 (§6).

## 2. What we measured before committing to it

You were right to make the latency the gating question, and right that it had not been measured
inside a write path. We measured it against a real Postgres, at five history sizes, then against
the current production-shaped database.

The sweep is one indexed query over the credited worker's records plus an in-process interval
pass. Its cost tracks **the worker's total record count**, not the step's — the query's
`entered_at < window_end` bound has no lower bound, because a record that started before the
window can still overlap it, so the scan cannot be narrowed without changing the averaging.

| Worker's time-bearing records | Added sweep (median) | Transition end-to-end |
|---|---|---|
| 10 | 3.0 ms | 33 ms |
| 100 | 4.3 ms | 31 ms |
| 500 | 8.2 ms | 32 ms |
| 2 000 | 20.4 ms | 43 ms |
| 5 000 | 49.2 ms | 110 ms |

In the current database the busiest worker holds **1 635** working/paused records over roughly
three months, so today the real added cost is **≈16–20 ms** on a tap that you measured at ~90 ms.
We judged that acceptable and shipped it.

Two honest caveats, because you asked to hear them rather than have them shipped quietly:

- **It grows with worker tenure.** At the observed rate (~550 records/month) a worker crosses
  3 000 records in about six months and 5 000 in under a year, where the added cost reaches
  ~50 ms. If tap latency becomes a complaint, this is the thing to look at first, and the fix is
  bounding that scan — a change to the shared averaging query, which is why we did not make it
  here.
- **Starting work pays nothing.** The settlement is gated on the *closing* state being
  time-bearing, so a PENDING→WORKING tap does no sweep at all. Roughly half of all taps are free.

**Why not the settled-marker alternative.** It would have moved the same unbounded scan onto the
read path — which runs on every 45-second poll, on every client, on every manager surface, at a
far higher rate than taps — and cost a schema change besides. Same property, worse place to pay
for it. We took the one you led with.

## 3. Where it applies

Your list of enqueue sites was accurate. We verified it rather than trusting it, and found the
inventory is slightly larger than four:

| Path | Closes a record | Settles now |
|---|---|---|
| `transition_step_state` — ordinary single transition | yes | yes |
| `transition_step_state` — auto-pause of a conflicting step | yes | yes |
| `_step_transition_core._apply_step_transition` — the step itself | yes | yes |
| `_step_transition_core._apply_step_transition` — auto-pause branch | yes | yes |
| `finalize_pending_step_completion` (dormant) | yes | yes |
| `remove_task_step` | yes | **no — see below** |

Settling in the shared core covers all five of its drivers at once: batch transitions,
**clock-out**, declared worker states, the case-created pause, and force-ready.

**Your clock-out question: no, it does not close records by a different route.**
`clock_out_shift_for_user` never touches `exited_at` itself — it loads each open WORKING record
`FOR UPDATE` and hands it to `_apply_step_transition`, so it inherited the settlement for free.
There is an integration test pinning exactly that. (One unrelated detail we noticed: clock-out
filters to `state == WORKING`, so an open PAUSED record survives a clock-out un-closed. That is
pre-existing and out of scope here; flagging it because you may see it.)

**`remove_task_step` is the one closer we did not settle, deliberately.** It closes every open
record of the steps it removes and enqueues no analytics task at all — it is the only live path
that has never done so. But it also soft-deletes the step in the same breath, so no read can
observe those records: the step is gone from every surface. Your §5.2 "disowning" mode already
covers what the client sees. It is a real asymmetry in the write path and worth fixing on its own
terms; it is not part of this defect, and settling a step that is being deleted would be wasted
work.

## 4. Your two decisions, answered

**Should a failed synchronous settlement fail the transition? — Yes, it fails the transition.**
The settlement runs inside the transition's own transaction and does not swallow exceptions, so a
failure rolls back the record close, the new record, and the step state together. You get an
error and the step stays where it was; you never get a commit that reintroduces the window. This
is what you said you would expect, and we agree: a transition that cannot publish its own time is
not a transition worth keeping. There is a test that pins it.

**Should the transition response carry the settled total? — Yes, added.**
See §5.

## 5. Interface details

**Read surfaces — unchanged.** `GET /api/v1/item-economics/tasks/budget-allocations`,
`…/production-time`, `…/budget-status`, and the price scenario keep their exact shapes. The
values of `worked_seconds` / `actual_worker_seconds` / `actual_worked_seconds` become correct
earlier. Nothing is added, removed or renamed. `allocation_method` is untouched.

**Transition responses — one additive key.** Both the single and the batch transition now return
the step's settled working seconds as of the commit:

```
POST /api/v1/tasks/{task_id}/steps/{step_id}/transition
{
  "step_id": "tsp_…",
  "new_state": "paused",
  "last_state_record": { … },
  "was_final_step": false,
  "total_working_seconds": 1488      // NEW
}
```

```
POST /api/v1/tasks/steps/transition-batch
{ "items": [ { …, "total_working_seconds": 1488 } ] }     // NEW, per item
```

This is the settled column only. It **excludes** the run the transition just opened — on a
`paused → working` transition it is the total *before* the new run starts accruing, which is
exactly the baseline your smoothing needs. Seed the cache with it at `onSuccess` and accrue from
receipt.

Additive, so ignoring it is safe. Adopt it when convenient.

**Error cases:** unchanged, plus the settlement-failure case in §4, which surfaces as an ordinary
500 on the transition route rather than a new error code.

**Socket events:** none added, as you asked.

## 6. Retiring §5.3 of the 2026-08-22 live-clock handoff

**§5.3 "Settlement window" no longer describes anything that can happen. Delete the case.**

A decrease in `worked_seconds` that comes back within seconds does not occur any more. A closed
record's time is in the served total from the first request after the commit, so there is nothing
to dip. If you still see a value drop and return, that is a bug — report it rather than smoothing
over it.

**The client rule is now simpler: a decrease is always authoritative.** There are two modes left,
both unchanged from 2026-08-22:

1. **§5.1 Rounding sense** — a decrease of at most 1 second is the rounding bound. Smoothing may
   absorb it; no visible snap required. **Unchanged.**
2. **§5.2 Disowning** — marking a record inaccurate, or removing the step, can remove the step's
   live contribution. A drop larger than 1 second is authoritative: snap down immediately to the
   served value, reset the smoothing baseline, accrue from the new time of receipt, never clamp to
   the previous maximum, and do not animate the descent. **Unchanged, and now the only reason a
   value can fall by more than a second.**

Everything else in §5 stands: smoothing may add elapsed time after receipt but its baseline snaps
rather than clamps, `share_state` renders as received, and there is still no `as_of` field by
design — you no longer need one to tell these cases apart, because there are only two and they
differ by magnitude.

One caveat on §5.2 that this change does *not* alter: the standalone
`POST …/state-records/{record_id}/mark-inaccurate` endpoint flips the flags but enqueues no
analytics recompute, so a step's already-written daily rollups are not corrected until some later
transition on that step. The step's own `total_working_seconds` is what your surfaces read, and
that is recomputed correctly on the next settlement. Marking a record inaccurate *as part of* a
transition (`mark_closing_record_inaccurate: true`) has no such gap and now settles immediately.

## 7. Frontend action required

1. **Remove the §5.3 handling**, if you carry any. A decrease is authoritative; there is no
   "wait and see if it comes back" case.
2. **Optional:** seed the budget cache from `total_working_seconds` on the transition response at
   `onSuccess` instead of waiting for the refetch.
3. **Remove your temporary instrumentation** as you planned — `step-clock-debug.ts` and its four
   call sites, plus the `queryFn` log in `use-task-budget-allocations-query.ts`.
4. Keep `projectStepBudget` / `restingStepBudget` and the `onMutate` cancellation. Both stay
   correct and still earn their place; this change removes the case where the *served* value was
   wrong, not the case where a payload can arrive stale.

## 8. Validation notes

**Backend validation run.**

- Full suite twice: **3091 passed, 24 failed, 1 skipped**, both runs. The 24 failures are
  pre-existing and identical to the pre-change baseline (shopify dimensions, auth sign-in,
  upholstery inventory, bootstrap seeding, two routers, pause reasons, audit log, phase-6
  migration) — none in `task_steps`, `item_economics` or `analytics`. Failure sets byte-identical
  across both runs, so this is a stable baseline rather than one lucky run.
- **11 new integration tests** covering your acceptance criteria 1–8, including the worked
  1430 + 58 = 1488 example asserted literally, with the analytics worker never invoked.
- **Mutation-tested.** With the settlement disabled, 10 of the 11 fail. Disabling only the shared
  core kills exactly the batch and clock-out tests; disabling only the single-step command kills
  the other nine. Each call site is independently pinned, so these tests can actually fail.
- The test that previously asserted the dip *was* visible
  (`test_c9_settlement_window_drop_is_visible_until_recompute`) has been inverted rather than
  deleted, and renamed to
  `test_c9_closing_a_record_publishes_its_time_with_no_settlement_dip`. It is the record that the
  behaviour changed on purpose.

**Acceptance criteria.** All eight hold, each with a test:

| # | Criterion | Covered by |
|---|---|---|
| 1 | Pause read includes the just-closed interval, worker stopped | `test_ac1_ac7_…` |
| 2 | Same for production-time and budget-signals | `test_ac2_…` |
| 3 | Worker afterwards leaves totals unchanged | `test_ac3_ac4_…` |
| 4 | Replaying the payload twice is inert | `test_ac3_ac4_…` |
| 5 | Settled value is concurrency-averaged, not wall clock | `test_ac5_…` |
| 6 | Completion, auto-pause, batch, clock-out | four `test_ac6_…` |
| 7 | 1430 + 58 s → 1488 on the first request | `test_ac1_ac7_…` |
| 8 | Two reads seconds apart agree | `test_ac8_…` |

**Suggested frontend validation.** Re-run the capture that produced the evidence: pause a step
with the analytics worker stopped, then fire both the single-task and the 20-task
`budget-allocations` refetches. Both should now return the same figure, and whichever lands last
should no longer be the one that loses the run.

## 9. Trace links

- Originating request: `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_step_time_settlement_window_20260916.md`
- Implementation: `app/beyo_manager/services/commands/task_steps/_settle_step_time.py`
  (module docstring carries the reasoning and the gate's sync obligation with the worker)
- Tests: `app/tests/integration/services/commands/task_steps/test_step_time_settlement_integration.py`
- Architecture graph: nodes `helper-settle-closed-step-time` and
  `decision-settle-step-time-in-transition`, recorded 2026-09-16.
