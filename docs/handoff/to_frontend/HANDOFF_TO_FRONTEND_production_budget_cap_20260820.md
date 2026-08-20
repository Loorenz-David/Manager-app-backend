# HANDOFF_TO_FRONTEND_production_budget_cap_20260820

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_production_budget_cap_20260820`
- Created at (UTC): `2026-08-20T19:35:00Z`
- Owner agent: `Codex`

## Backend delivery context

The item-economics production budget now applies a V1 hard cap of 25% of the
gross expected sale price, rounded to integer minor units with HALF_EVEN:

```text
cap_minor(P) = round_half_even(P × 25 / 100)
budget_minor(P) = min(residual_affine(P), cap_minor(P))
```

The calculation version is now `2`. Persisted version-1 evaluations are not
migrated or recommitted; re-derivation returns `REDERIVE_SKIPPED` for them.
Committed budgets are capped only for evaluations committed after deploy.

## Frontend action required

Replay the published piecewise budget model from the additive
`price_model.budget_cap_percent_milli` field. The field is non-nullable and is
always present when `model` is present; its current value is `25000`.

```text
residual_affine(P) = round_half_even(
    P × residual_percent_milli / 100000
                     ) - constant_deduction_minor
cap_affine(P) = round_half_even(
    P × budget_cap_percent_milli / 100000
)
budget_minor(P) = min(residual_affine(P), cap_affine(P))
```

Use this same piecewise budget for allowance, break-even, slider-domain, and
suggested-price calculations. Above the crossing price, the AT-PRICE time goes
flat rather than following the residual slope.

## Interface details

The existing task price-scenario response is extended additively:

```json
{
  "model": {
    "residual_percent_milli": 78000,
    "constant_deduction_minor": 150000,
    "cost_per_worker_minute_ten_thousandths": 13000000,
    "budget_cap_percent_milli": 25000
  }
}
```

The field is absent only when the existing `model` object is `null`; it is not
nullable inside a published model.

## Validation notes

Backend tests cover cap binding and idle/negative residuals, HALF_EVEN ties,
version-gated re-derivation, a capped model re-derivation, and a price sweep
straddling the residual/cap crossing. The serialized payload carries
`budget_cap_percent_milli: 25000`.
