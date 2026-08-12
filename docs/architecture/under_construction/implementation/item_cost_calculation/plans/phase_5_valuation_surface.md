# Phase 5 — Valuation surface

```
plan: phase 5
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Ship the specialized item-valuation surface (card 2 / R1-3): the superseding
valuation command with its chain and race, validation, history read, guarded
deletes, and the ephemeral economic preview (§11A.5). **NOT in this phase:** the
§10.2 legacy migration (phase 6), the §7.2 mirror rule (phase 7 — it is part of the
commit transaction), any evaluation or result row.

## Read first

1. `master_plan.md` §§5, 6 (registry: routes, identities), 9 (P-B), 10.
2. Intention §4.7A (table, INV-V1/V2), §7.5 (valuation deletion rules), §7A.1–7A.2
   (the valuation chain has all three steps S1/S2/S3), §11 ("Set item valuation"),
   §11A.4–§11A.5 (status vocabulary, preview), §6A.9 (currency), R-9.
3. Contracts: `06_commands`+local, `07_queries`+local, `09_routers`,
   `28_roles_permissions`, `46_serialization`+local (+ core).

## Dependencies

Phase 4 APPROVED (preview needs the calculator + the §7A.5 classifier + config
loading).

## Files expected to change

- `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`,
  `delete_item_valuation.py` + additions to `requests/__init__.py`
- `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`
- `app/beyo_manager/domain/item_economics/serializers.py` (valuation + preview
  serialization; started here, extended in later phases)
- `routers/api_v1/item_economics.py` (valuation routes per registry §6.5);
  `routers/README.md` mirror rows
- tests

## Implementation tasks (ordered)

1. `set_item_valuation` (ADMIN/MANAGER): validates per §4.7A (≥1 amount —
   `ITEM_COST_VALUATION_AMOUNT_REQUIRED`; non-negative amounts and required currency
   at the request layer), then writes through the valuation chain **S1→S2→S3**
   (§7A.1) in one transaction; `IntegrityError` from INV-V1 surfaces as
   `ConflictError ITEM_COST_CONCURRENT_VALUATION` (§7A.2 — never caught/retried).
2. Response embeds the **preview** (§11A.5): a pure computation from the posted
   valuation + current configuration via the §7A.5 classifier and the calculator —
   `EconomicsStatusEnum` + budget/allowed when computable, `null` numerics
   otherwise (P-B). The preview has no `client_id`, persists nothing, supersedes
   nothing, and **creates no evaluation row**.
3. `delete_item_valuation`: the **current** row only, soft delete → item returns to
   "unvalued"; a superseded row is never deletable
   (`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`, §7.5).
4. `get_item_valuation_history`: full chain, newest first; rows are immutable
   after creation (INV-V2) — no update surface exists anywhere.
5. Routes + role gates per registry §6.5.

## Acceptance criteria

**C1 — chain order (intention test 17, valuation row):** setting a second valuation
for an already-valued item succeeds; afterwards exactly one row satisfies INV-V1's
predicate and the superseded row carries `superseded_at` + `superseded_by_id` of the
new row. (This row fails outright under insert-before-close — its reason to exist.)

**C2 — INV-V1 race (intention test 12):** two sessions past S1 both attempt S2 →
exactly one current row afterwards + loser's exact
`ITEM_COST_CONCURRENT_VALUATION`; the DB conflict path, not the pre-check.

**C3 — validation (intention test 11), request layer AND DB CHECK (both paths per
row):** expected-only OK; cost-only OK; both OK; neither →
`ITEM_COST_VALUATION_AMOUNT_REQUIRED`; negative expected → 422 and CHECK violation;
negative cost → 422 and CHECK violation; missing currency → 422 and NOT NULL
violation.

**C4 — immutability & deletion (§7.5):** superseded row delete →
`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`; current row delete → item unvalued
(history retained; subsequent status reads `item_unvalued`); re-set after delete
starts a fresh current row.

**C5 — preview rows (§11A.5, each fixture sole-predicate; numeric fields `null`
for every non-computable status — P-B):**
- unconfigured workspace (no group) → `not_configured_no_cost_group`, nulls;
- configured + valuation with expected price → `not_evaluated` with exact
  budget/allowed preview values (calculator-derived);
- configured + cost-only valuation → `item_missing_expected_price`, nulls;
- valuation currency ≠ basis currency → `currency_mismatch`, nulls;
- model carries an `item_purchase_cost` term + valuation without purchase cost →
  `item_missing_purchase_cost`, nulls.
Every preview row also asserts `item_cost_evaluations` count unchanged (creates
nothing) and that the valuation row itself WAS written (the command's own effect).

**C6 — history:** after three supersessions, history returns all rows in order with
exactly one current; byte-identical re-read (no mutation on read).

## Notes

- The valuation is the ONLY source of an evaluation's currency (§6A.9 step 2) —
  the preview must never invent a fallback.
- An item with no current valuation is **unvalued** — an explicit state, never
  zero (R-9); the preview payload for it is status-only.
- Teardown discipline (rule 11½) for committed fixtures.
- Archgraph: delta = the valuation command/endpoint nodes; orient on
  `table-task-item` + phase-2 table nodes.

- **Forward item (phase-4 projection, N7 consumption half):** the valuation
  preview divides a budget by the rate — a criterion must prove it consumes the
  PERSISTED `cost_per_worker_minute_minor` (quantized, 4 dp), never a raw
  re-division from the basis inputs (fixture from the Q2-tie family where the
  two differ).

- **Live-data note (4B projection N-d):** the dev DB holds 37 items with NULL
  `item_major_category_snapshot` (225 wood / 193 seat) — `item_missing_major_category`
  is a LIVE preview outcome, not a defence row; the preview's criteria include it
  with P-B null-numerics.

## Review log

(append-only)
