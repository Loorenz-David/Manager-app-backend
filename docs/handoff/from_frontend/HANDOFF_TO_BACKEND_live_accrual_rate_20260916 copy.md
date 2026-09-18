# HANDOFF_TO_BACKEND_live_accrual_rate_20260916

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_live_accrual_rate_20260916`
- Created at (UTC): `2026-09-16T06:30:00Z`
- Owner agent: `Claude Opus 5` (frontend), on the owner's decision
- Related:
  - `HANDOFF_TO_FRONTEND_step_time_settlement_window_answer_20260916.md` — shipped earlier today.
    It made `worked_seconds` correct **at rest**. This handoff is about what the client may add
    **between** payloads, which that change did not address and did not break.
  - `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §3 — the sentence this request
    follows from: the server serves "settled work plus the **concurrency-averaged** share of an
    open working interval", and client smoothing "may add elapsed time on top of the last served
    value". Those two rules disagree whenever concurrency is not 1, and nothing on the wire says
    what the concurrency is.
  - `HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md` — the precedent for additive fields on
    `steps[]`; `state` arrived that way and is what made today's client-side clock fix possible.
- **Asking for:** two additive read-only fields. No shape change to anything that exists.

## Summary

A worker running three steps at once sees all three timers advance a full second per second. The
server credits each of them a third of a second per second. The moment they pause, the true totals
arrive and every timer jumps backwards by two thirds of the run.

Separately, on the managers' task list, an overrun figure creeps upward on a task where nobody is
working at all, because that payload has no way to say that nothing is accruing.

Both are the same missing fact: **the client is told what has been worked, but not how fast it is
currently being worked.** We are asking for that rate.

## Evidence

Captured 2026-09-16 from the workers app. One worker, three steps in a batch, started and paused
twice. `credited` is the change in the served `worked_seconds` for that step; `elapsed` is
wall-clock seconds between the two payloads:

```
05:48:19.79  batch start (3 steps)   each step settled = 9
05:48:26.31  batch pause             each step settled = 11
05:48:26.51  served-rate  [{"id":"YD2P80","credited":2,"elapsed":6,"rate":"0.31"},
                           {"id":"657C6N","credited":2,"elapsed":6,"rate":"0.31"},
                           {"id":"RM9J0Z","credited":2,"elapsed":6,"rate":"0.31"}]
```

The earlier cycle agrees: 8 seconds of wall clock, 3 seconds credited per step, `rate 0.36`. Both
sit on 1/3, as expected for three concurrent steps.

The client had been displaying `9 + 6 = 15` for each step at the moment of the pause. The correct
value was 11. Every card fell about four seconds. A two-minute batch would fall by about eighty.

We want to be clear that **the backend is right and the client is wrong here.** Splitting a
worker's attention across three steps and charging each a third is what makes the totals honest.
The client simply has no way to know the divisor.

## Why we cannot derive it client-side

1. **The divisor is not a property of what the client can see.** The averaging sweep is scoped to
   the credited user across their open records, wherever those steps live. A client holds the steps
   of the sections and tasks it has loaded. A worker with a step running in a section this screen
   never fetched would give us a divisor of 3 where the truth is 4 — a wrong number rendered with
   full confidence, which is worse than the honest snap we have now.
2. **Re-implementing the rule would fork it.** The share comes out of
   `averaged_seconds_by_record` over real interval overlaps, not a flat division. A client
   approximation would drift from the server's own figure, and the two are shown side by side.
3. **The managers' payload has nothing at all.** `TaskBudgetSignalSchema` carries no step state and
   no step list, so on that surface there is not even a wrong guess available — only the choice
   between ticking when idle (today) and never ticking at all.

## What we are asking for

### 1. Per step, on `budget-allocations` → `steps[]`

```jsonc
{
  "...": "existing keys, unchanged",
  "live_accrual_rate": "0.3333",   // decimal string | null — seconds credited to this step
                                   // per wall-clock second, right now
  "live_concurrency": 3            // int | null — how many of the worker's records that
                                   // share is being divided across
}
```

The **rate** is what we multiply our locally added seconds by. We ask for it as the rate rather
than as a count so the client never has to know the averaging rule, and so an uneven split would
keep working without a client change.

The **count** is not for arithmetic. It is for the label. A timer advancing one second every three
reads as broken unless the card can say "shared across 3 items", so this field is what makes the
correct number legible. If you ship only one, ship the rate — but the count is cheap and it is what
keeps us from having to explain the slowness with a guess.

### 2. Per task, on `budget-signals`

```jsonc
{
  "...": "existing keys, unchanged",
  "live_accrual_rate": "1.0000"   // decimal string | null — seconds credited to this TASK per
                                  // wall-clock second, summed over its open records
}
```

Defined as the sum of the per-record shares currently accruing on that task, so two workers on the
same task legitimately exceed 1. **Zero or null when nothing is running** is the case that matters
most: it is what stops the manager's overrun figure from creeping while the floor is empty.

## Semantics we are assuming

Please confirm or correct these; each one changes what we render:

- The rate is derived from the **same basis** as `worked_seconds`, not an independent calculation,
  so the two cannot disagree.
- A step that is not accruing answers `0` or `null` — and we would like to know which, since we
  treat them the same but would rather match your convention.
- The rate reflects concurrency **at request time**. If one of three steps pauses, the next read
  shows the other two at `0.5`.
- `excluded` / `no_budget` steps answer `null`, consistently with how `allowance_seconds` already
  behaves there.

## What we explicitly do NOT need

- **Do not change `worked_seconds`.** It is correct, and this morning's settlement change made it
  correct earlier. This request is only about the interval between payloads.
- **Do not change the averaging.** We are not asking for a different split, only to be told what
  the split is.
- **No new endpoint and no socket event.** Both fields ride on payloads we already poll.
- **No push on rate changes.** A stale rate for up to one poll is fine: we re-anchor on every
  payload, and a transition already triggers a refetch.

## Open questions

- [ ] **Do PAUSED records dilute a WORKING one?** The averaging treats both as time-bearing. If a
      worker has one step working and two paused, is the working step's rate `1.0` or `0.33`? We
      would expect the share we display to reflect only what the served `worked_seconds` will
      actually grow by, whatever the internal rule.
- [ ] **Is the divisor workspace-wide per credited user**, including steps in sections and tasks
      outside the requested `task_ids`? We assume yes, and it is the main reason we cannot compute
      this ourselves.
- [ ] **What precision, and is a decimal string right?** We read `pressure_ratio` and
      `typical_unit_worker_seconds` as decimal strings today and would rather stay consistent than
      introduce a float.
- [ ] **Does `ended_shift` accrue?** We assume it does not and would render its rate as zero.
- [ ] **Cost:** does either figure need a sweep the read path does not already run? If the rate
      falls out of the computation `load_live_worked_seconds` already performs, this is nearly
      free; if it needs a second pass, tell us and we will scope it against the benefit.

## Acceptance criteria

1. For one worker with N steps running concurrently, each step's `live_accrual_rate` is `1/N` to
   the served precision, and the N rates sum to `1`.
2. With the worked example: three concurrent steps, six seconds of wall clock, each step's
   `worked_seconds` grows by two and each reports a rate of `0.33`.
3. Pausing one of three steps makes the next read report `0.5` for the remaining two and zero/null
   for the paused one.
4. A step with no open record reports zero/null, and a task with no open records reports zero/null
   at the signals level.
5. A task's `live_accrual_rate` equals the sum of its own steps' rates in the allocations payload
   for the same instant.
6. Two reads seconds apart, with no transition in between, return the same rate.
7. The rate is consistent with observed growth: `worked_seconds` measured across two reads grows by
   `rate × elapsed`, within rounding — this is the property the evidence above measures, and the
   one that makes the client's timer match the server.
8. `excluded` / `no_budget` steps answer `null`.

## Interface expectations

- **Endpoint(s):** existing — `GET /api/v1/item-economics/tasks/budget-allocations` and
  `…/budget-signals`. Additive keys only.
- **Request shape:** unchanged.
- **Response shape:** as above, always-present keys with explicit nullability.
- **Error cases:** unchanged.
- **Socket events:** none required.
- **Versioning:** none expected.

## Frontend contract implications

On delivery:

- the per-step accrual in `projectStepBudget`
  (`apps/workers-app/ManagerBeyo-app-workers/src/features/task_steps/domain/step-budget.ts`)
  becomes `elapsed × live_accrual_rate`, so every worker surface inherits it from one place;
- the step cards gain a "shared across N" label driven by `live_concurrency`, so a correctly slow
  timer does not read as a stuck one;
- `buildTaskBudgetSignalDisplay` (`packages/item-economics/src/lib/task-budget-overrun.ts`) scales
  its elapsed term by the task rate, which is what stops an idle task's overrun from creeping.

One thing we intend to do on our own side, mentioned only so the numbers are not a surprise if you
see them: because each step accrues `1/N` and the batch has `N` of them, a batch-level timer
advances at exactly one second per second. We may add that wall-clock total to the batch card as
the counterpart to the per-item shares. It needs nothing from you.

No architecture contract changes. The served value stays authoritative; this request tells the
client how to keep pace with it between payloads instead of guessing.

## Document convention

Please issue any answer or correction as a **new dated handoff** rather than editing this file or
either 2026-09-16 handoff in place.
