# HANDOFF_TO_FRONTEND_remaining_production_pressure_20260825

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_remaining_production_pressure_20260825`
- Created at (UTC): `2026-08-25T12:00:00Z`
- Owner agent: `Codex`
- Source plan: `docs/architecture/under_construction/implementation/remaining_production_pressure/planning/intention.md`
- Related request: worker time-pressure request recorded in the parent intention (the original handoff is not present in this checkout).

## Backend delivery context

- The existing `budget-allocations` and `production-time` reads now derive one remaining-production-pressure calculation from the unchanged budget division. There is no new endpoint, persistence, event, socket, worker, or feature flag.
- Static `allowance_seconds`, `worked_seconds`, `left_seconds`, `share_state`, and `allocation_method` keep their existing meanings. The new pressure figure is a target allocation of the distributable budget still left, not a countdown.
- The calculation is live on the existing polling cadence. A step's own time does not change its target while it remains within its allowance; another step settling, or an open step going beyond its allowance, can change it.

## Frontend action required

1. On worker step cards, render `min(allowance_seconds, pressure_share_seconds)` when both values are non-null. This prevents an under-running upstream step from raising the worker-facing target above the static allowance.
2. Continue showing the static allowance and the live `worked_seconds`; do not derive, tick, smooth, or subtract the pressure value client-side.
3. Treat `0` as an immediate no-time-left/escalate signal for an open step and `null` as not applicable. Preserve the existing live-overrun display from `left_seconds < 0` / `share_state` before a step becomes consuming.
4. Manager surfaces may show the honest served pressure share and `pressure_ratio`, including a ratio above `1` or below `0`.

## Interface details

- Endpoint(s):
  - `GET /api/v1/item-economics/tasks/budget-allocations?task_ids=<id>&task_ids=<id>`
  - `GET /api/v1/item-economics/tasks/<task_id>/production-time`
- Request shape, roles, caps, envelopes, omissions, and errors: unchanged.

### `budget-allocations` additions

Every task row now has:

| Field | Type | Meaning |
| --- | --- | --- |
| `pressure_ratio` | decimal string \| null | Exact pressure ratio rendered as a decimal; it is not clamped. `null` means no allocatable open step or a zero total allowance. |
| `pressure_method` | string | Always `open_share_proportional_v1`. |

Every `steps[]` row now has:

| Field | Type | Meaning |
| --- | --- | --- |
| `state` | string | The step's own task-step state. This is not the section governing state. |
| `pressure_share_seconds` | integer \| null | The step's current share of the remaining distributable production budget. |

### `production-time` additions

Every task response now has the same `pressure_ratio` and `pressure_method`. Each `sections[]` row has `pressure_share_seconds`, the exact sum of its open steps' pressure shares. It is `null` when that section has no open step. The frozen `final{}` block is unchanged.

### Nullability and live-overrun behavior

- No usable task pot: ratio and every step/section pressure share are `null`.
- Settled or excluded step: step share is `null`.
- Open step that has exceeded `allowance_seconds`: its share is `0`; its live `worked_seconds` reduces the remaining shares for other open steps on every poll.
- Open allocatable step with exhausted or negative remaining budget: share is `0`, not `null`.
- An open step with a zero allowance can have share `0` with a `null` ratio when no positive allowance remains to form a denominator.

## Validation notes

- Backend validation run: pure-rule unit tests, route serializer contract tests, and the affected allocation/production-time integration and golden suites passed (81 tests total across the targeted runs).
- Suggested frontend validation: verify that changing a worker's own `worked_seconds` below its allowance does not move the displayed target; verify the target falls when another open step becomes over allowance; verify `0` versus `null` rendering; and verify manager rendering of ratios above one.

## Trace links

- Parent intention: `docs/architecture/under_construction/implementation/remaining_production_pressure/planning/intention.md`
- Sibling gate: `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md`
- Existing worker allocation contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`
