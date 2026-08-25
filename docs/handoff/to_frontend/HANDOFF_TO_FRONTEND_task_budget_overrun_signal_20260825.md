# HANDOFF_TO_FRONTEND_task_budget_overrun_signal_20260825

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_budget_overrun_signal_20260825`
- Created at (UTC): `2026-08-25T06:30:00Z`
- Owner agent: `Codex`
- Source plan: `backend/docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_3.md`
- Intention: `backend/docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`
- Related request: `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md`
- Related stable handoff: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`

## Backend delivery context

- Backend delivery is additive: `GET /api/v1/item-economics/tasks/budget-signals` is now mounted beside the unchanged `budget-allocations` read.
- The endpoint is batched, accepts repeatable `task_ids`, caps the raw request at 50 ids, silently omits invisible tasks, and returns the standard success/error envelopes.
- Access is ADMIN and MANAGER only; WORKER and SELLER receive 403.
- Rows are flat, ordered by `task_id` ascending, and contain served integer money figures rather than frontend-derived costs.

## Frontend action required

1. Replace the manager task-list consumer of `budget-allocations` with this endpoint and render the served `budget_state` plus its corresponding figures.
2. Preserve the existing polling interval and extrapolate only forward from the received baseline; do not recompute the verdict client-side.
3. Add the projected-over tone and cost label, and validate the four state values and the two 422 envelope shapes.

## What changed since your request

The route serves both the incurred and forecast pairs. `budget_state` names the headline and `over` wins when both facts are present; on every `over` row, `projected_over_seconds ≥ over_seconds`.

The currency vocabulary adds the explicit `no_currency` sentinel for `no_budget`. No worker or seller variant is shipped: ADMIN and MANAGER only; WORKER and SELLER receive 403.

The D9/D10 rule is simple: a negative budget before any work is a forecast: the unclamped task pot is preserved for projection, while the served `allowed_seconds` is clamped to zero. In the same rule, no work left to come means no forecast, even when the task is otherwise within budget. Under the production-time contract, production-time shows no amber on an infeasible task until it converges; this endpoint represents that case as `no_budget`.

## Corrections to the request

1. `over_cost_minor` may be `0` while `over_seconds > 0` — acceptance criterion 2 is not satisfiable as written. At the measured `3.7500` rate, the first eight seconds cost zero minor units under the shared half-even money rule.
2. N rows means one row per **distinct** visible requested id. Duplicate ids collapse in the database `IN` selection and do not produce duplicate output rows.
3. the route has two different 422 envelopes. Missing `task_ids` is FastAPI validation and returns `{"detail": [...]}`; an over-cap request reaches the service and returns `{"error": "BUDGET_SIGNALS_TOO_MANY_TASK_IDS:…", "ok": false}`.

## Open questions answered

### Open question 1

Both incurred and forecast pairs are populated when their calculations are available. `budget_state` remains the single headline, with `over` taking precedence over `projected_over`.

### Open question 2

Event hysteresis belongs to the future event/notification mechanism, not this read endpoint. Polling this endpoint does not create or deduplicate notifications.

### Open question 3

The 60-second floor gates the `projected_over` state only; raw projected seconds are always served. A client can therefore display the served pair without rebuilding the threshold decision.

### Open question 4

The production-time outlook may converge later, but that is not scheduled in this delivery. It is no longer a zero-behaviour-change swap for infeasible tasks: the backend contract explicitly represents their state as `no_budget`.

### Open question 5

The rate is per task and is resolved at commit from the evaluation snapshot. Two tasks in one list can therefore carry different `cost_per_worker_minute_ten_thousandths` values.

## Interface details

### Endpoint and request

`GET /api/v1/item-economics/tasks/budget-signals?task_ids=<id>&task_ids=<id>&...`

The request accepts repeatable `task_ids`, with a hard cap of 50 raw values. Unknown, deleted, and other-workspace ids are silently omitted. The contract guarantees rows are ordered by `task_id` ascending. The contract also guarantees that no server timestamp is served; the client re-anchors any between-poll extrapolation on each fresh response and never recomputes the verdict.

### Response shape

The standard success envelope contains `data.budget_signals`, a flat list with no nested arrays:

| Field | Type | Meaning |
| --- | --- | --- |
| `task_id` | string | Visible task identity. |
| `budget_state` | string | Exactly `no_budget`, `over`, `projected_over`, or `within_budget`. |
| `over_seconds` | integer | Already-incurred overrun seconds. |
| `over_cost_minor` | integer | Cost of `over_seconds` in minor units. |
| `projected_over_seconds` | integer | Forecast overrun seconds. |
| `projected_over_cost_minor` | integer | Cost of `projected_over_seconds` in minor units. |
| `currency` | string | Exactly `swedish_krona`, `danish_krona`, `euro`, or `no_currency`. |
| `allowed_seconds` | integer | Served task pot, clamped to zero when the raw budget is negative. |
| `actual_worked_seconds` | integer | Live worked basis at request time. |
| `cost_per_worker_minute_ten_thousandths` | integer | Resolved task rate for forward extrapolation only. |

All ten fields are non-null integer/string values. `over_cost_minor` and `projected_over_cost_minor` are already costed by the backend; do not multiply seconds by the rate in the frontend. ADMIN and MANAGER only; WORKER and SELLER receive 403. The route has no socket event and keeps the existing polling model. There is no server timestamp to compare against.

### Error cases

- More than 50 requested ids: HTTP 422 with `error` beginning `BUDGET_SIGNALS_TOO_MANY_TASK_IDS:` and `ok: false`.
- Missing `task_ids`: HTTP 422 with FastAPI's `detail[]` validation shape and no `error` key.

## Validation notes

- The shared money rule measured `136 s → 9` and `8 s → 0` at rate `3.7500`; this is why a positive overrun does not guarantee a positive `over_cost_minor`.
- The projection floor is checked at the `59/60` boundary.
- The untouched infeasible fixture measured `-12.50` allowed minutes as `projected_over 750`, then `over` after one worked second.
- Between polls, use `actual_worked_seconds` and the served rate only to tick the displayed figure forward; the received `budget_state`, ordering, membership, and allowed budget remain authoritative until the next response.

## Trace links

- Parent plan: `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_3.md`
- Master plan: `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md`
- Ratified intention: `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`
- Backend request: `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md`
- Existing allocation contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`
