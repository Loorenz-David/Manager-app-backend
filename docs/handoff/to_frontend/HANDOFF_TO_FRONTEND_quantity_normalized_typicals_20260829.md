# HANDOFF_TO_FRONTEND_quantity_normalized_typicals_20260829

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_quantity_normalized_typicals_20260829`
- Created at (UTC): `2026-08-29T07:30:00Z`
- Owner agent: `Claude`
- Source plan: none — direct owner-approved implementation (quantity normalization for absolute typical projections), recorded in the architecture graph change `\.archgraph/changes/2026-08-29T07-12-07-341Z--fbef75.yml`
- This is an **addendum** to the published typical/production-time contracts. It does not replace `HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`, `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`, or `HANDOFF_TO_FRONTEND_price_scenario_20260819.md`; everything in those documents stays true except the one price-scenario semantic change called out below.

## Backend delivery context

- Historical typical-time samples are now **additionally** normalized per unit: each historical task's section total is divided by that task's PRIMARY-item `quantity` (clamped to at least 1; missing or deleted items count as 1) before a second median is taken. The existing raw medians are computed exactly as before.
- Narrowing is unchanged. Quantity is **not** a narrowing criterion — the comparable-task population (category, etc.) is selected first, then quantity scales the result.
- Two values therefore now travel together everywhere a typical appears:
  - `typical_worker_seconds` — unchanged meaning: median duration of a typical historical order of whatever size, on the selected basis (`item_narrowed` / `section_wide`).
  - `typical_unit_worker_seconds` × current task quantity = `projected_typical_worker_seconds` — the quantity-aware expectation for **this** task. The multiplication, clamping, and half-even rounding happen server-side.
- **The production-budget division did not change.** Section/step `allowance_seconds`, `left_seconds`, `share_state`, pressure fields, and `allocation_method` (`static_proportional_section_v2`) are still derived from the raw typicals. Quantity never moves an allowance.
- `budget-signals` and `GET /api/v1/working-sections/typical-times` are unchanged. No new endpoint, persistence, flag, event, or socket.

## Frontend action required

1. Extend the response schemas with the additive fields listed below (strict parsers will reject the payloads until this is done; lenient parsers keep working but should still add them).
2. Wherever a screen answers *"how long should this task's section/step take"*, display `projected_typical_worker_seconds`. **Do not compute unit × quantity client-side** — reuse the server value so every surface agrees and rounding cannot drift.
3. Keep using `typical_worker_seconds` where the raw historical median is the honest reference — in particular anything that explains the budget split, since allowances are still derived from it.
4. Optionally show the derivation using `projection_quantity` / `quantity_applied` (e.g. "140 s/unit × 3").
5. Price screen: re-read the semantic change to `typical.total_seconds` below — break-even and suggested price now price the **whole order**.

## Interface details

- Endpoint(s):
  - `GET /api/v1/item-economics/tasks/<task_id>/production-time`
  - `GET /api/v1/item-economics/tasks/budget-allocations?task_ids=<id>&task_ids=<id>`
  - `GET /api/v1/item-economics/tasks/<task_id>/price-scenario`
- Request shapes, roles, envelopes, role-gated money fields, omissions, and errors: unchanged.

### `production-time` additions

Top level of the response:

| Field | Type | Meaning |
| --- | --- | --- |
| `projection_quantity` | integer | The quantity applied to every projection in this response: the current PRIMARY item's `quantity`, clamped to at least 1. Detached tasks and legacy `quantity <= 0` yield `1`. |

Every `sections[].typical{}` block:

| Field | Type | Meaning |
| --- | --- | --- |
| `typical_unit_worker_seconds` | decimal string \| null | Per-unit median of the same population the raw typical was selected from. May be fractional (e.g. `"433.5"`). |
| `projected_typical_worker_seconds` | integer \| null | `typical_unit_worker_seconds × projection_quantity`, half-even rounded server-side. |

### `budget-allocations` additions

Every task row:

| Field | Type | Meaning |
| --- | --- | --- |
| `projection_quantity` | integer | Same clamping rule as production-time, per task. |

Every `steps[]` row:

| Field | Type | Meaning |
| --- | --- | --- |
| `typical_unit_worker_seconds` | decimal string \| null | Per-unit median for the step's section, on the task's selected basis. |
| `projected_typical_worker_seconds` | integer \| null | The server-computed projection for that section under this task's quantity. |

### `price-scenario` — one semantic change plus additions

In the `typical{}` block:

| Field | Type | Meaning |
| --- | --- | --- |
| `total_seconds` | integer | **CHANGED MEANING**: now the quantity-projected task typical — each participating section's per-unit typical (business fallback applied in per-unit space) scaled by the current item's quantity, per-section half-even rounded, then summed. Previously this was the sum of raw typicals. |
| `total_unit_seconds` | integer | NEW — the same total at quantity 1. |
| `quantity_applied` | integer | NEW — the clamped quantity used. |

Consequence: `anchors.break_even_price_minor`, `anchors.suggested_price_minor`, and the slider `domain` are now derived from the whole-order time. The slider step granularity already used quantity and is unchanged. `is_estimated`, `sections_without_sample`, `sections_total`, `method`, `window_days`, `min_sample_size`: unchanged.

### Nullability

- `projected_typical_worker_seconds` is `null` **exactly when** `typical_worker_seconds` is `null` (same basis, same sample gates) — the existing insufficient-sample fallback path covers both; no new empty states.
- Excluded (SKIPPED/CANCELLED/FAILED) step rows carry `null` in both new fields, matching their existing typical fields.
- `projection_quantity` / `quantity_applied` are always present and always `>= 1`.
- When every historical and current quantity is 1, `projected_typical_worker_seconds == typical_worker_seconds` and price-scenario `total_seconds` equals its old value — existing screens render identically for quantity-1 data.

## Validation notes

- Backend validation run: full suite green outside the pre-existing baseline (2833 passed). New discriminating coverage includes a SQL-level test (mixed quantities 1/2/1/4/0 → raw median 3000 vs unit median 1000, legacy zero clamps) and a cross-surface test (raw 600 / unit 140 / quantity 3 → 420 on production-time, budget-allocations, and price-scenario; re-read at quantity 1 moves only the projection while `allowance_seconds` is byte-identical). Live-clock goldens were regenerated; their diff is exactly the additive fields.
- Suggested frontend validation: parse all three responses with the extended schemas; verify a step card shows the projected value, not raw × anything; verify changing the item quantity moves projections and the price screen but never `allowance_seconds`; verify `null` typicals still render the existing insufficient-sample state.

## Trace links

- Superseded-in-part contract (price `total_seconds` semantics): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_20260819.md`
- Parent typical contract (unchanged): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824.md`
- Parent allocation contract (unchanged): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md`
- Architecture graph change record: `.archgraph/changes/2026-08-29T07-12-07-341Z--fbef75.yml`
