---
plan: phase 2 (schema, models & migration)
role: fix
round: 2
date: 2026-08-12
state: IMPLEMENTED
actor: Codex
---

# Phase 2 fix-r2 handoff

Resolved reviewer r1 findings B1–B4 and S1–S3 within the declared fix-cycle
perimeter. The schema and migration remain unchanged; the cycle adds migrated-schema
behavioral coverage, corrects the registry README, updates the phase records, and
passes the required checkpoint at `39e6fbe`.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Finding-by-finding resolution

### B1 — C2 partial uniques

Added production-ORM fixtures for the nine conflict rows and all accepted variants
enumerated by the C2 table: 25 concrete parametrized cases (the reviewer prose says
22/13, but the table itself enumerates 25 rows; the table was followed). The fixtures
ensure the index predicate or key-column difference is the only reason an accepted row
is accepted.

All 14 predicate clauses were mutated at the migrated database site on the disposable
clone and reverted. Every mutation reddened its named accepted row:

`groups_soft_deleted`, `sections_removed`, `basis_closed`, `basis_soft_deleted`,
`models_closed`, `models_soft_deleted`, `purchase_other_type`,
`purchase_soft_deleted`, `term_name_soft_deleted`, `evaluations_projection`,
`evaluations_superseded`, `evaluations_soft_deleted`, `valuations_superseded`,
`valuations_soft_deleted`.

### B2 — C1(b) downgrade proxy

The test now reads `upgrade` and `downgrade` function bodies with
`inspect.getsource`, asserting the exact five new enum drops, exclusion of the three
reused enum names, and equality between upgrade table creations and downgrade table
drops.

Named source mutations, each applied and reverted in the migration file, all reddened
the proxy:

- adding `_task_state_enum.drop(...)` to `downgrade`;
- deleting `_item_valuation_currency_enum.drop(...)`;
- deleting `op.drop_table('item_cost_results')`.

### B3 — basis CHECK sole-cause rows

Expanded the basis boundary matrix to include every required reject and accept value.
The shared fixture closes its basis version for these rows, so the open-version index
cannot be the second sufficient cause; rejected rows assert their CHECK constraint
name. Dropping each of the five `ck_pcbv_*` constraints reddened the intended rows.

### B4 — remaining CHECK coverage

Added the missing percent-value boundaries, D10 money rows and nullable accepts, both
valuation negative rows plus cost-only and NULL-currency cases, and all eight window
rows across both chains. Valid evaluation-term and result rows are exercised by these
fixtures. Dropping each previously untested CHECK reddened its behavioral test.

### S1–S3 and N2

- README now documents four currency columns using three PG enum types, with
  `item_cost_evaluations.currency` reusing the valuation type owned by
  `item_valuations`.
- Inventory asserts all five new enum types, the three reused task-owned types, and
  the declared types of `tasks.task_type`, `tasks.return_source`, and `tasks.state`.
- The valuation test name and cases now cover price-only and cost-only acceptance,
  both-null rejection, negative amounts, and NULL currency.
- Optional N2 was taken: inventory asserts reflected `cost_model_terms.percent_value`
  is `numeric(6,3)`.

## Verification

- Focused schema module: **79 passed**.
- Full non-e2e suite: **1684 passed / 23 failed / 1 deselected**; the 23 failures
  match the recorded pre-existing baseline.
- Configured development database: at head, never downgraded or mutated.
- Disposable database: schema-only clone used for all index/CHECK DDL probes, then
  dropped. No disposable database remains.
- Migration source probe SHA-256 after all apply/revert mutations:
  `3fc5cd88367b8a7ba2c0dadc34a00ae878a4b586db0b913a055ca6816fda48d0`.

## Full write perimeter

### Fix changes committed in `39e6fbe`

- `app/tests/integration/models/item_economics/test_item_economics_schema.py`
- `app/beyo_manager/models/tables/item_economics/README.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_2_schema_models.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`

### Mutation-probe state applied and reverted; no fix changes remain

- `app/migrations/versions/90cdd23a828e_item_economics_schema.py` — B2 source
  mutations; restored byte-identically to the SHA above.
- Disposable database indexes: all 14 predicate-clause variants named under B1.
- Disposable database CHECK constraints: five `ck_pcbv_*` constraints for B3 and
  the nine B4 constraints (`ck_cost_model_terms_percent_value_non_negative`,
  `ck_cost_model_terms_fixed_amount_minor_non_negative`, both effective-window
  constraints, the two evaluation money constraints, the two valuation money
  constraints, and the result worker-seconds constraint).

### Tool-recorded state

Architecture Graph was read for status and orientation only. It remained at revision
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e`, with 125 nodes,
161 edges, and 15 pending reviews. Delta: **zero**. No graph write or review
adjudication was performed.

## Coordinator notes

The C2 implementation follows the enumerated plan table despite its contradictory
22/13 prose count; no semantic decision is required because the extra cases are the
table's explicit key-column coverage rows. The checkpoint commit is `39e6fbe` with
subject `CHECKPOINT (not approved): item-cost phase 2 fix r2 — close schema test findings`.
