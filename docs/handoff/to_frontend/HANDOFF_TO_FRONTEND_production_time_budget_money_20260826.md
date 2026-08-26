# HANDOFF_TO_FRONTEND_production_time_budget_money_20260826

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_production_time_budget_money_20260826`
- Created at (UTC): `2026-08-26T20:00:00Z`
- Owner agent: `Claude`
- Source plan: none — direct owner-requested change in an interactive session, not a pipeline phase
- Related stable handoff: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
- Related stable handoff: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_remaining_production_pressure_20260825.md`

## Backend delivery context

- The production-time read `GET /api/v1/item-economics/tasks/{task_client_id}/production-time` now serves money on its `budget` block — for ADMIN and MANAGER only.
- The change is purely additive and role-gated. WORKER and SELLER responses are byte-identical to the previous contract: no money key appears anywhere in their bodies, and this is asserted by test.
- The three new fields are the same values, under the same names, that `budget-status` already serves in its monetary view. No new calculation was introduced; the values were already computed server-side and are now forwarded.
- Everything else in the response is unchanged: the `final` block still carries no money, the per-section rows still carry no money (time only), and no field was renamed or removed.

## Frontend action required

1. Extend the production-time response schema: for ADMIN/MANAGER sessions, `data.budget` gains three nullable fields — `production_budget_minor`, `consumed_cost_minor`, `variance_cost_minor`. For WORKER/SELLER sessions the schema is unchanged; do not require the keys there.
2. Render the labor-money view wherever the production-time budget block is shown to managers: the pot, the cost of worked time so far, and the over/under amount.
3. Do not derive an overflow boolean client-side — `variance_cost_minor < 0` **is** the overflow signal and its magnitude is the overflow amount. Do not recompute any of the three from seconds and a rate; all three are served.

## Interface details

### Endpoint

`GET /api/v1/item-economics/tasks/{task_client_id}/production-time` — path, method, request shape, and access roles (ADMIN, MANAGER, WORKER, SELLER) are all unchanged.

### Response shape — the `budget` block for ADMIN/MANAGER

| Field | Type | Meaning |
| --- | --- | --- |
| `production_budget_minor` | integer or null | The labor money pot: expected sale price minus the item's cost-model terms, capped at 25% of the sale price. **Can be negative** — that is the `infeasible` case: costs exceed the sale price before any labor. |
| `consumed_cost_minor` | integer or null | What the worked time has cost so far: live worked seconds / 60 × the evaluation's snapshotted rate, rounded half-even to minor units. |
| `variance_cost_minor` | integer or null | `production_budget_minor − consumed_cost_minor`. Positive = money left; negative = over budget by that amount. |

- Units are integer minor units (öre for SEK): divide by 100 for display. The response does not carry a currency field; currency lives on the item's evaluation and is served by `budget-status`.
- The three fields mirror the existing time fields one-to-one: `production_budget_minor` ↔ `allowed_worker_minutes`, `consumed_cost_minor` ↔ `actual_worker_minutes`, `variance_cost_minor` ↔ `remaining_worker_minutes`. The time and money sides of the block always describe the same live worked basis.
- On a degraded task (status is not `ok`/`infeasible` — e.g. `not_evaluated`), the three keys are present with `null`, matching the rest of the budget block.
- The `final` (frozen result) block deliberately remains money-free; frozen money is served by `budget-status`, not this endpoint.
- Sections remain time-only. There is no per-section cost in this delivery.

### Worked example (real task)

An infeasible task — item priced 7 000,00 kr, purchase cost 4 000,00 kr, percentage cost-model terms bringing total non-labor costs to 7 500,00 kr, rate ≈ 13.02 kr/min, 4 076 s worked:

```json
"budget": {
    "allowed_worker_minutes": "-38.40",
    "actual_worker_seconds": 4076,
    "actual_worker_minutes": "67.93",
    "remaining_worker_minutes": "-106.33",
    "percent_consumed": null,
    "production_budget_minor": -50000,
    "consumed_cost_minor": 88456,
    "variance_cost_minor": -138456
}
```

Reading: the pot is −500,00 kr (infeasible — the price does not cover non-labor costs), the worked time has cost 884,56 kr, and the task is 1 384,56 kr over. Note `status: "infeasible"` continues to mean exactly `allowed_worker_minutes ≤ 0`; the money fields explain it but do not redefine it.

### Error cases

Unchanged — same envelopes, same not-found and role behavior as the existing production-time contract.

## Validation notes

- Backend validation run: full item-economics unit + integration + router suites, 601 passed. The role matrix test asserts WORKER and SELLER bodies are byte-identical money-free, ADMIN and MANAGER bodies are byte-identical with exactly the three money keys, confined to `budget`.
- The pre-change byte-golden for the manager production-time payload was regenerated; the diff is exactly the three added keys.
- Suggested frontend validation: assert the three keys are absent for a worker session and present (possibly null) for a manager session; assert `variance_cost_minor === production_budget_minor - consumed_cost_minor` on a live task; render a negative `production_budget_minor` without clamping.

## Trace links

- Prior production-time contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
- Pressure field on the same response: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_remaining_production_pressure_20260825.md`
- Monetary view precedent (same keys on budget-status): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
