# Phase 2 — Schema, models & migration

```
plan: phase 2
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Create the nine item-economics tables, their enums, constraints and the schema
migration — the structural layer every later phase builds on. **NOT in this phase:**
any command, query, router, calculator, or data migration (the §10.2 legacy
migration is phase 6); no writes to any existing table's model.

## Read first

1. `master_plan.md` §§5, 6 (FULL naming registry — every name is fixed there), 10.
2. Intention §4 with §4A (all amendments A1–A8), §4.7A, §4.8, §7A intro table
   (the four chains' open predicates and close columns — the indexes built here are
   their arbiters), §2.5 (conventions).
3. Contracts: `03_models`, `30_migrations`, `25_soft_delete`, `24_multi_tenancy`,
   `21_naming_conventions`, `15_testing` (+ core set per master plan §5).

## Dependencies

Phase 1 APPROVED.

## Files expected to change

- `app/beyo_manager/domain/item_economics/__init__.py`, `enums.py` (registry §6.3)
- `app/beyo_manager/models/tables/item_economics/` — nine model files + `README.md`
  (registry §6.1)
- `app/beyo_manager/models/__init__.py` (registration)
- `app/beyo_manager/models/tables/client_id_prefix_map.md` (nine prefixes; note
  `cmvt`, not the intention's proposed `cmt` — collision, registry §6.1)
- `migrations/versions/<new>_item_economics_schema.py` (autogenerate + hand-fix)
- tests (constraint/round-trip tests + model factories used by them)

## Implementation tasks (ordered)

1. Enums per registry §6.3 (incl. the two reuse decisions: `ItemCurrencyEnum` Python
   class with three new per-table PG types; `business_task_type_enum` /
   `task_return_source_enum` reused with `create_type=False` — type-creation
   ownership stays on `tasks`).
2. Nine models exactly per intention §4/§4.7A as amended by §4A, with registry §6.1
   columns/§6.2 constraint names. Load-bearing details: `IdentityMixin` prefixes;
   inline tz-aware audit + `created_by_id`/`updated_by_id` (users FK RESTRICT);
   soft-delete trio everywhere except `ItemCostResult` (`created_at` only, §4.6 —
   **as amended round 6**: `task_closed_at` nullable + `task_state_snapshot` enum
   copy reusing PG type `task_state_enum` with `create_type=False`, registry §6.3);
   self-FKs (`superseded_by_id`, both chains) with `use_alter=True`;
   `ItemCostResult.evaluation_id` NOT NULL; A8 — **no** non-negativity CHECK on
   `production_budget_minor` / `allowed_worker_minutes` (deliberate; do not let
   autogenerate or review "fix" it).
3. Migration: autogenerate, then hand-fix per `30_migrations` (partial uniques via
   `postgresql_where`, idiom `595e7b840926:44,50`; enum create/reuse flags; CHECK
   constraints). Upgrade + downgrade both complete.
4. Table guide README; registration; prefix map rows.
5. Model factories for the constraint tests below (every factory has a caller in
   this phase — charter rule 4).

## Acceptance criteria

DB-level tests run against a migrated disposable database with production ORM
instances (charter rule 3); the configured DB is left at head (rule 7).

**C1 — migration lifecycle.** Manual `upgrade → downgrade → upgrade` round-trip on a
disposable DB (rule-1 exemption, recorded in the Review log when exercised) **plus**
the automated in-suite proxy: a test importing all nine models and asserting their
tables + PG enum types exist in the test schema and every §6.2-named constraint is
present (query `pg_constraint`/`pg_indexes` by exact name).

**C2 — partial uniques (one pair of rows per index; second row's predicate is the
only differing fact — rule 2 companion):**

| Index | (a) both rows match predicate → `IntegrityError` | (b) second row outside predicate → accepted |
|---|---|---|
| `uix_production_cost_groups_name_active` | two non-deleted same-name groups | second is soft-deleted |
| `uix_production_cost_group_sections_active` (INV-G1) | section active in two groups | second membership has `removed_at` |
| `uix_production_cost_basis_versions_open` (INV-B1) | two open versions, one group | second has `effective_to` |
| `uix_cost_model_versions_open` (INV-M1) | two open versions, one workspace | second has `effective_to` |
| `uix_cost_model_terms_purchase_cost` (A5) | two `item_purchase_cost` terms, one version | second is a `fixed_amount` term |
| `uix_cost_model_terms_name_active` | two same-name terms, one version | second on another version |
| `uix_item_cost_evaluations_current` (INV-E1) | two current committed evaluations, one task | second has `superseded_at` (and a `projection` third row is also accepted) |
| `uix_item_valuations_current` (INV-V1) | two current valuations, one item | second has `superseded_at` |
| `uq_item_cost_results_task_id` | two results, one task | second for another task |

**C3 — CHECKs (one row per boundary, exact outcome each; adjacent-pair enumeration):**
- `fixed_monthly_cost_minor`: −1 reject, 0 reject (A1), 1 accept.
- `cost_per_worker_minute_minor`: 0 reject (A2), 0.0001 accept.
- `monthly_paid_hours`: 0 reject, 0.01 accept.
- `planning_utilization_percent`: 0 reject, 0.01 accept, 100 accept, 100.01 reject.
- `percent_value`: −0.001 reject, 0 accept, 999.999 accept, 1000 reject (6A.4).
- term type×columns CHECK (`ck_cost_model_terms_value_by_type`, 6A.4 table): the 3
  valid combinations accept; each of the 5 invalid combinations rejects
  (percentage+fixed set, percentage+NULL percent, fixed+percent set, fixed+NULL
  fixed, purchase+either set).
- valuation: negative `expected_sale_price_minor` reject; negative
  `purchase_cost_minor` reject; both amounts NULL reject
  (`ck_item_valuations_amount_present`); one amount + currency accept; NULL currency
  reject (NOT NULL).
- window CHECK both config chains: `effective_to = effective_from` reject,
  `effective_to = effective_from + 1 day` accept, either side NULL accept.

**C4 — A8 proof.** An `ItemCostEvaluation` row with `production_budget_minor = -500`
and `allowed_worker_minutes = -12.50` INSERTs successfully. (Adding any CHECK there
turns this row red — that is the row's purpose.)

**C5 — enum reuse.** Metadata create on a fresh disposable schema succeeds with the
snapshot columns reusing `business_task_type_enum` / `task_return_source_enum`
(`create_type=False`) — proves type-creation ownership stayed put.

## Notes

- Names come from the registry, not the intention's proposals — `cmvt` is the settled
  prefix for `CostModelTerm`.
- The soft-delete trio on `cost_model_terms` exists for house-style shape only; no
  command will ever write it (A6) — nothing to build here, but the README states it.
- Teardown discipline (rule 11½) applies to every constraint test that commits.
- Archgraph: orient on `table-task-step`, `table-task-item`; delta at close = the new
  `table-*` nodes for this domain (one batched apply_changes, evidence = the model
  files; agents never adjudicate pending reviews).

## Review log

(append-only)
