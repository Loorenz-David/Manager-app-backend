# HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823`
- Created at (UTC): `2026-08-23T00:00:00Z`
- Owner agent: `Claude Opus 5` (frontend), on the owner's decision
- Related:
  - `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md` — the endpoint we read
    today. **We are not asking you to change it.** The workers-app step cards depend on it as-is.
  - `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md` — the single-task surface
    whose `sections[]` feed the projection rule this handoff asks you to take over.
  - `HANDOFF_TO_FRONTEND_price_scenario_20260819.md` §4, extended by
    `HANDOFF_TO_FRONTEND_production_budget_cap_20260820.md` — the money arithmetic the cost figures
    must agree with, exactly.
  - `HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819.md` — the same principle applied
    once before: one correct rule in your layer beats a second rule in ours that drifts.

## Summary

The managers task list now renders a red strip under any task that has run past its production
budget ("Over budget by 1h 25m"). It is shipped, and it reads exactly one field —
`remaining_worker_minutes` — out of the batched `budget-allocations` payload.

Three things make that arrangement the wrong long-term shape:

1. we fetch a full per-step payload to render two numbers per task;
2. the amber **"projected to go over"** half of the design cannot be built from that payload at all;
3. the owner intends to push **notifications/events** on these same warnings — which turns "is this
   task over budget, by how much, and what does that cost" into a backend domain concept with an
   identity, not a client-side rendering.

We are asking for a **new, narrow, batched read** that answers only the budget-signal question, and
— with it — for you to take ownership of the projection rule that currently lives in our layer.

We are not asking you to remove or alter anything that exists today.

## What we render today, and what it costs

The strip is `TaskBudgetOverrunBand`, mounted through `TaskListCard`'s `bottomAction` slot from
`packages/tasks/src/components/TasksView.tsx`. Its entire input is:

```ts
// packages/item-economics/src/lib/task-budget-overrun.ts
buildTaskBudgetOverrun(
  allocation: Pick<TaskBudgetAllocation, "remaining_worker_minutes">,
)
```

One field. To get it we call
`GET /api/v1/item-economics/tasks/budget-allocations?task_ids=…` and receive, per task:

- **6 task-level keys** — `task_id`, `status`, `allowed_worker_minutes`, `actual_worker_seconds`,
  `remaining_worker_minutes`, `allocation_method`
- **`steps[]`, 8 keys per non-deleted step** — `step_id`, `working_section_id`,
  `section_name_snapshot`, `typical_worker_seconds`, `allowance_seconds`, `worked_seconds`,
  `left_seconds`, `share_state` (`division_serializers.py:serialize_budget_step`)

A 25-task page of 6-step tasks is ~1,350 serialized values to render 25 badges. It works; it is
simply the wrong read for the surface, and it will be the wrong read again for every future
list-level budget signal.

## Why the projection cannot be built from that payload

The projection rule exists and ships — but **in our layer**, as `buildOutlook`
(`packages/item-economics/src/lib/production-time-view-model.ts:281-317`), fed by the *single-task*
`production-time` response. It is not `expected_total − actual_total`. It is:

```
remaining_commitment = Σ over sections where
                         left_seconds is not null
                         AND state ∉ {completed, skipped, failed, cancelled}
                       of max(0, left_seconds)

if remaining_commitment <= 0                    → no signal
projected_overrun = remaining_commitment − remaining_pot_seconds
if projected_overrun < 60                       → no signal (noise floor)
```

Two properties are load-bearing and cannot survive a task-level subtraction:

- **the per-section `max(0, …)` clamp.** Our own comment on it: *"A section already past its own
  slice contributes nothing rather than a negative: how far it will keep overrunning is not
  knowable, and letting it subtract would quietly cancel out another stage's real remaining work."*
- **the 60-second noise floor**, because `formatWorkSeconds` floors to minutes and a smaller gap
  announces itself as "0m over".

`budget-allocations` serializes `steps[]` but not `sections[]`, and carries no step lifecycle state
— `share_state` is a section-share verdict, not a step's position in its lifecycle. So the list
surface cannot tell finished work from work still to come, which is precisely the distinction the
rule turns on. Note that `divide_production_budget` **already computes** the section rows this needs
(`sections[]`, with `state` from `_governing_step` and `left_seconds`); `serialize_budget_allocation`
simply does not emit them.

We would rather hand you the rule than replicate it. This is the same trade you accepted on the live
clock: one definition in your layer, none in ours.

## Why the cost figures must be yours

The obvious-looking alternative — "send `cost_per_worker_minute_ten_thousandths`, let the frontend
multiply" — is specifically ruled out by the discipline already written into our money module,
`packages/item-economics/src/lib/price-scenario-math.ts`:

> *"There is no algebraic shortcut: collapsing budget → seconds disagrees with the server by up to a
> second, which would make this screen and the production-time screen name different numbers for the
> same task."*
>
> *"`Number`, `Math.round` and `parseFloat` are forbidden in this module."*

That module works in `BigInt` with a hand-written `roundHalfEven`, transcribed verbatim from your §4
and validated against the shipped Python over 612 cases with zero mismatches. A float
`minutes × rate` on a list card would be exactly the shortcut that paragraph forbids, and it would
produce öre-level disagreements between this badge, the valuation editor, and — once they exist —
the push notifications quoting the same task. Those read as bugs.

So: **money arrives costed, in minor units, computed by you.**

## What we are asking for

A new batched endpoint, in the shape of `budget-allocations` (repeatable `task_ids`, a hard cap,
silent omission of invisible tasks, standard `build_ok` / `build_err` envelope), returning **one flat
row per task and no nested arrays**.

Suggested name, yours to change:
`GET /api/v1/item-economics/tasks/budget-signals?task_ids=<id>&task_ids=<id>&…`

### Row shape

**Authoritative — rendered as served, and quoted verbatim by any future notification:**

| Field | Type | Meaning |
|---|---|---|
| `task_id` | string | — |
| `budget_state` | enum | `within_budget` \| `projected_over` \| `over` \| `no_budget` |
| `over_seconds` | int | Already-incurred overrun. `0` unless `budget_state == "over"`. |
| `over_cost_minor` | int | Cost of `over_seconds`. `0` unless `budget_state == "over"`. |
| `projected_over_seconds` | int | Forecast overrun. `0` unless `budget_state == "projected_over"`. |
| `projected_over_cost_minor` | int | Cost of `projected_over_seconds`. Same rule. |
| `currency` | enum | `swedish_krona` \| `danish_krona` \| `euro` |

**Supporting — so we can tick the displayed figure between polls without re-deriving the verdict:**

| Field | Type | Meaning |
|---|---|---|
| `allowed_seconds` | int | The task's pot. `0` under `no_budget`. |
| `actual_worked_seconds` | int | Live basis, same as `budget-allocations` (live-clock handoff §5). |
| `cost_per_worker_minute_ten_thousandths` | int | The task's resolved rate, for extrapolation only. |

The split is the contract. **We render the served verdict on receipt and may only extrapolate
forward from it between polls; we never recompute the verdict, and every fresh payload re-anchors
the baseline.** That is the pattern your live-clock handoff §5 already establishes and that
`useTaskBudgetAllocationsQuery` already implements via its `receivedAtMs` stamp.

### On nullability

Please make every field **non-nullable with an explicit default** — `0` for the integers, an
explicit enum member for the states. A `.nullable()` field the backend later stops sending has taken
this frontend down twice, and `budget_state` already carries every distinction the nulls would.
`no_budget` is a state, not an absence.

### On `budget_state` specifically

We are asking for an explicit enum rather than letting nullability imply the state, for three
reasons, the first of which is the point of this handoff:

1. **notifications fire on transitions of it**, not on levels — it is the natural event trigger;
2. it gives us an exhaustive switch that breaks the typecheck when you add a member, which is how
   this package already treats `ValuationCurrency`;
3. it separates "not over" from "no budget at all" without a second field.

## What we explicitly do NOT need

- **No change to `budget-allocations`.** The workers-app step cards read it per-step and are correct
  today. This is an additive sibling, not a replacement.
- **No `steps[]` or `sections[]` in the new endpoint.** Their absence is the entire point.
- **No pre-formatted money strings.** Minor units plus `currency`; we format, as we already do
  everywhere else in this package.
- **No server "now" timestamp.** Same reasoning you accepted on the live clock: we measure elapsed
  time from response receipt, so a server clock would reintroduce the comparison we removed.
- **No `status` enum.** Its twelve values collapse to `no_budget` for our purposes — your
  budget-allocations §5 already established that the card need not branch on individual failure
  statuses.

## Open questions

- [ ] **Should `over` and `projected_over` be mutually exclusive?** We have specified them as
      exclusive, `over` winning, because the badge renders one line. But a task already 20m over
      *and* heading a further hour over is arguably two facts a manager wants. If you would rather
      populate both and let `budget_state` name only the headline, we can render that — say so and
      we will design for it.
- [ ] **Who owns the event's hysteresis?** A task hovering at the boundary must not emit a
      notification per poll. We believe the dedup/threshold rule belongs with whatever fires the
      event, on your side, but we do not know your notification infrastructure well enough to
      assert it. If any part of that lands on us, we need to know before we build the consumer.
- [ ] **Does the projection want the same 60-second noise floor?** We chose it for a frontend
      formatter that floors to minutes. A notification may want a much higher bar — nobody wants a
      push for a 90-second projected overrun. If the thresholds should differ per channel, that is
      an argument for the endpoint serving the raw projected seconds and the *event* owning its own
      trigger threshold.
- [ ] **Should `production-time`'s outlook line converge onto this?** Once you own the projection,
      our `buildOutlook` on the single-task card becomes a second implementation of your rule — the
      exact situation this handoff exists to avoid. We are not asking for it now, but if you would
      like `production-time` to carry the projection too, we will delete `buildOutlook` outright.
- [ ] **Is the cost rate uniform per task?** We assume it is resolved per item, via
      `resolve_economics_selection(major_category, …, selection_date)`, so two tasks in one list can
      carry different rates and the field must be per-row. Confirm, or tell us it is workspace-wide.

## Acceptance criteria

1. A task within budget, whose unfinished sections still fit the remaining pot, returns
   `within_budget` with all four figures `0`.
2. A task whose live `actual_worked_seconds` exceeds `allowed_seconds` returns `over`, with
   `over_seconds > 0` and `over_cost_minor > 0`.
3. A task not yet over, whose unfinished sections' targets exceed the remaining pot by ≥ the agreed
   floor, returns `projected_over` with `projected_over_seconds > 0`.
4. A task with no usable committed evaluation returns `budget_state: "no_budget"` and is **present
   in the response** — only unknown, deleted, and other-workspace ids are omitted, as in
   `budget-allocations` §1.
5. `over_cost_minor` for a given overrun equals, to the öre, the same duration costed through the
   price-scenario pipeline (`roundHalfEven`, scaled integers) for the same task. The badge, the
   valuation editor, and any future notification must never name different money for one task.
6. A section already past its own slice contributes `0` to the projection, never a negative — the
   `max(0, …)` clamp survives into your implementation.
7. Two calls a few seconds apart with no state change differ only in the time-dependent fields,
   never in `budget_state` ordering, membership, or `allowed_seconds`.
8. Requesting more than the cap returns the standard error envelope with a stable identity, in the
   spirit of `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`.
9. The response for N tasks is N flat rows. No nested arrays at any depth.

## Interface expectations

- **Endpoint:** new — `GET /api/v1/item-economics/tasks/budget-signals` (name yours).
- **Roles:** ADMIN and MANAGER cover the shipped surface. WORKER/SELLER only if free.
- **Request shape:** repeatable `task_ids`, hard-capped as `budget-allocations` is at 50. One
  batched call per feed page.
- **Response shape:** as above, inside the standard `build_ok` envelope, under a single key
  (`budget_signals`).
- **Error cases:** over-cap identity as in criterion 8. Unknown/deleted/other-workspace ids omitted
  silently, not an error.
- **Socket events:** none required for v1 — we poll on the same 45-second interval as
  `budget-allocations`. When the notification/event work lands, we expect to revisit this and
  would prefer an invalidation signal over a shorter poll.

## Frontend contract implications

On delivery we will:

- delete `buildTaskBudgetOverrun` (`packages/item-economics/src/lib/task-budget-overrun.ts`) — our
  local subtraction — and render `budget_state` plus the served figures;
- swap `TasksView`'s `useTaskBudgetAllocationsQuery` for the new query, removing the managers task
  list as a consumer of `budget-allocations` entirely;
- extend `TaskBudgetOverrunBand` with the amber `projected_over` tone (`#8a6d1c`, already the
  package's forecast color) and populate its existing `costLabel` slot, which was built empty
  against this handoff;
- keep `buildOutlook` in place for `production-time` until the fourth open question is answered.

No architecture contract changes: the verdict remains a rendered backend value, which is the
property this handoff strengthens rather than relaxes.

## Document convention

Please issue any answer or correction as a **new dated handoff** rather than editing this file or
the 2026-08-22 budget-allocations handoff in place.
