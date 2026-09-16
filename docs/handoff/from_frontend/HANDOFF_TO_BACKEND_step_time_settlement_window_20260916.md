# HANDOFF_TO_BACKEND_step_time_settlement_window_20260916

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_step_time_settlement_window_20260916`
- Created at (UTC): `2026-09-16T00:00:00Z`
- Owner agent: `Claude Opus 5` (frontend), on the owner's decision
- Related:
  - `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §5.3 — the "settlement window"
    decrease mode. **This handoff asks you to make that mode stop existing, and to retire it in a
    new dated handoff.** §5.1 (rounding) and §5.2 (disowning) are untouched and must survive.
  - `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md` — the endpoint whose
    `worked_seconds` is affected. **No shape change is requested.**

## Summary

For roughly 100–300 ms after a worker pauses a step, `GET /item-economics/tasks/budget-allocations`
serves a `worked_seconds` that is missing the run that just ended. A client that refetches inside
that window — which is exactly when every client refetches, because the pause is what triggers the
invalidation — receives the step's total *as it was when the run started*.

On a worker's device the timer jumps backwards by the length of the work they just did. The
worker's own screen is the least of it: the same figure feeds the manager surfaces, and a manager
has no way to know a pause just happened.

We have already done what the client can do. The remaining defect is that the endpoint publishes
a state the database is only briefly in, and nothing in the payload says so.

## Evidence

Captured on 2026-09-16 from the workers app, step `tsp_01M2FE9Q373R8A2MVDE2WDRZKP`. Two responses
from the same endpoint, 53 ms apart:

```
04:01:41.663  payload (1 task id)   WDRZKP  paused  worked_seconds=1488   ← settled
04:01:41.716  payload (20 task ids) WDRZKP  paused  worked_seconds=1430   ← not yet settled
```

The arithmetic identifies 1430 exactly:

| time | event | served |
|---|---|---|
| 04:00:43 | worker taps Start | `working, worked=1430` → settled total before this run is **1430** |
| 04:01:28 | 45 s poll | `working, worked=1475` (1430 + 45 ✓) |
| 04:01:41.315 | worker taps Pause | — |
| 04:01:41.408 | transition response | `last_state_record.entered_at = 04:01:41.340` |
| 04:01:41.663 | refetch A | `paused, worked=1488` (1430 + 58 ✓) |
| 04:01:41.716 | refetch B | `paused, worked=1430` — the 58 s run is absent |

Both are freshly computed. The difference is only whether the analytics worker had committed yet.
Response B landed last, so 1430 is what stayed on screen, and nothing corrected it until the next
45-second poll.

## Mechanism, as we read it

`load_live_worked_seconds` sums exactly two sources:

```
worked_seconds = step.total_working_seconds          # settled column
               + share of any OPEN working record    # exited_at IS NULL AND state = WORKING
```

The transition closes the record in its own transaction
(`transition_step_state.py:341`, `closing_record.exited_at = now`) and deliberately leaves the
column to the analytics worker (`transition_step_state.py:377-378`). Between the commit and
`_recompute_step_time_totals` (`process_step_transition.py:185`) the just-closed record is in
neither source: no longer open, not yet summed.

This is a gap between two mechanisms, not bad data. The record itself is correct and complete
throughout.

## Why we cannot resolve this client-side

1. **The payload is unlabelled.** `1430` and `1488` are equally well-formed. There is no `as_of`,
   no version, and no settled marker — and `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822`
   §5 states the absence of `as_of` is by design.
2. **Responses arrive out of order relative to truth.** Above, the *correct* response landed first
   and was overwritten by the stale one. Preferring the newest arrival does not help.
3. **The only client-side rule available is the one you forbade.** Keeping 1488 over a served 1430
   is a clamp to the previous maximum, which §5.2 rules out — correctly, because a record marked
   inaccurate must be able to lower a step's total and show up immediately on the worker's screen.
4. **Most affected readers have no local context.** `load_live_worked_seconds` also feeds
   `get_task_budget_signals`, `get_task_production_time`, and transitively the price scenario. A
   manager's device cannot know that a worker on another device just paused, so no optimistic
   reconstruction is possible there at all. On those surfaces the figure informs money decisions,
   not a timer.

## What we are asking for

**Settle the step's own time totals inside the transaction that closes the record**, so no read can
observe the intermediate state.

`_recompute_step_time_totals` already recomputes from the records and *sets* the columns rather
than incrementing them, so running it in the request and again in the worker is idempotent. Our
reading is that it can be lifted out of `process_step_transition.py` into a shared module and
called before commit, with no change to its logic.

The property we need, stated without prescribing the implementation: **any read that observes a
closed time-bearing record must also observe that record's contribution in
`step.total_working_seconds`.**

Every path that closes a time-bearing record needs it. From our reading, the enqueue sites are:

- `transition_step_state.py:445` — the ordinary transition
- `transition_step_state.py:310` — the auto-pause of a conflicting step
- `_step_transition_core.py:164` and `:266`
- `finalize_pending_step_completion.py:188`

`transition_step_state.py:125` and `_step_transition_core.py:16` already record the invariant that
a change to one of the three sibling drivers must be evaluated for the other two. Please treat our
list as a starting point rather than as authoritative.

## What we explicitly do NOT need

- **No response shape change.** No new field, no new endpoint, no version flip. The existing
  `worked_seconds` simply stops being briefly incomplete.
- **Do not move the rest of the worker's job.** The per-user daily rollups, the completion and
  issue counters, the cost recompute, and the shift-state derivation should stay exactly where they
  are. Only the step's own totals need to be settled synchronously.
- **Do not change the concurrency averaging.** We are not asking for a different number, only for
  the same number to be available earlier.
- **No socket event.** We already invalidate on `task:step-state-changed` and poll every 45 s. If
  the value is right when we ask, that is sufficient.

## Open questions

- [ ] **What does the added sweep cost on the transition request?** This is the one real objection
      to the approach. The tap→response round trip currently measures ~90 ms in local dev
      (`04:01:41.315` → `04:01:41.408`). `compute_record_contributions` already runs once per
      budget read, so the per-tap rate is far lower than the per-read rate — but we have not
      measured it inside a write path. If it proves material, we would rather hear that than have
      it shipped.
- [ ] **If the latency is unacceptable, is a settled marker preferable?** For example a
      `records_settled_through` timestamp on the step, letting `load_live_worked_seconds` include
      closed-but-unsettled records itself. That keeps the write path fast and fixes every consumer,
      at the cost of a schema change. We have no preference between the two as long as the property
      above holds.
- [ ] **Does the clock-out path close records through one of the drivers above?**
      `_clock_worker_shift.py` pauses steps server-side and `emit_steps_paused` broadcasts them. If
      it closes records by a different route, it needs the same treatment.
- [ ] **Would you also return the settled `total_working_seconds` in the transition response?**
      Optional and strictly an improvement, not a requirement: it would let us seed the cache at
      `onSuccess` instead of waiting for a refetch. The response currently carries `step_id`,
      `new_state`, `last_state_record`, and `was_final_step`.

## Acceptance criteria

1. Immediately after a pause transition commits, a `budget-allocations` read for that step returns
   a `worked_seconds` that includes the just-closed working interval — with the analytics worker
   stopped entirely.
2. The same holds for `get_task_production_time` and `get_task_budget_signals`, which share the
   `load_live_worked_seconds` basis.
3. Running the analytics worker afterwards leaves the step's totals unchanged — the synchronous
   settlement and the worker's recompute agree exactly.
4. Replaying the same transition payload through the worker twice still leaves the totals
   unchanged, preserving today's at-least-once safety.
5. The settled value equals the concurrency-averaged figure, not raw wall-clock: a worker with two
   steps running concurrently who pauses one has the same totals as today's worker produces.
6. The same guarantee holds for completion, for the auto-pause of a conflicting step, and for batch
   transitions — not only for the single-step pause.
7. For the worked example: a step whose settled total is 1430 s, worked for 58 s and then paused,
   reads `1488` on the first request after the commit, with no dependency on worker timing.
8. Two reads seconds apart, with no work recorded in between, return the same `worked_seconds`.

## Interface expectations

- **Endpoint(s):** unchanged — `GET /api/v1/item-economics/tasks/budget-allocations`,
  `…/production-time`, `…/budget-status`, and the step transition route.
- **Request shape:** unchanged.
- **Response shape:** unchanged. The values of `worked_seconds` / `actual_worked_seconds` become
  correct earlier; no key is added, removed, or renamed.
- **Error cases:** unchanged. If the synchronous settlement fails, we would expect the transition
  itself to fail rather than commit a state that reintroduces the window — but that is your call,
  and we would like it stated in the answer.
- **Socket events:** none required.
- **Versioning:** none expected. `allocation_method` is read as data and pinned nowhere.

## Frontend contract implications

Already shipped on our side (2026-09-16), and unaffected by this request:

- `projectStepBudget` / `restingStepBudget`
  (`apps/workers-app/ManagerBeyo-app-workers/src/features/task_steps/domain/step-budget.ts`) choose
  the accrual window by comparing the served row's own `state` against the client's state, so a
  payload older than the transition no longer produces a jump. This is what makes the 1487 in the
  evidence above correct at the moment of the pause. It stays either way.
- The step transition action cancels in-flight `budget-allocations` fetches in `onMutate`.

On delivery we will remove the temporary `[step-clock]` instrumentation added to capture the
evidence above (`features/task_steps/lib/step-clock-debug.ts` and its four call sites, plus the
`queryFn` log in `packages/item-economics/src/api/use-task-budget-allocations-query.ts`).

No architecture contract changes. The served value stays authoritative and the client continues to
render it as received — this request removes the case where doing so was wrong.

## Document convention

Please issue the answer as a **new dated handoff** rather than editing this file or the 2026-08-22
live-clock handoff in place. That answer is also the place to retire §5.3: once the window cannot
be observed, the client should be told that a decrease is always authoritative, and that the
"drops and returns within seconds" case no longer occurs.
