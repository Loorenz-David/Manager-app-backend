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
2. Nine models exactly per intention §4/§4.7A as amended by §4A **and the round-6/7
   pins**, with registry §6.1 columns/§6.2 constraint names (the §6.2 CHECK list is
   CLOSED — build exactly it, including both `planning_utilization_percent` bounds).
   **Column shape is per-table, NOT blanket (projection D5/D6 — intention wins):**
   - full audit (`created_at/by`, `updated_at/by`) + soft-delete trio:
     `production_cost_groups`, `production_cost_basis_versions`,
     `cost_model_versions`, `cost_model_terms`, `item_cost_evaluations`;
   - `production_cost_group_sections`: **membership-interval shape** per §4.2 /
     `working_section_membership.py` idiom — `added_at/by`, `removed_at/by`, **no
     soft-delete trio, no `updated_*`**; INV-G1's predicate is
     `removed_at IS NULL` alone;
   - `item_valuations`: `created_at/by` + soft-delete trio, **no `updated_*`**
     (INV-V2 immutability);
   - `item_cost_evaluation_terms`: per the §4.5 round-7 pin — `workspace_id`,
     `percent_value`/`fixed_amount_minor` (never `value`), `created_at` only, no
     soft delete;
   - `item_cost_results`: `created_at` only (§4.6 round 6: `task_closed_at`
     nullable + `task_state_snapshot` **NOT NULL** enum copy reusing PG type
     `task_state_enum` with `create_type=False`, registry §6.3).
   Three self-FKs — `ItemCostEvaluation.superseded_by_id`, **`.promoted_from_id`**,
   `ItemValuation.superseded_by_id` — `use_alter=True` with the §6.2 registry names.
   `ItemCostResult.evaluation_id` NOT NULL. Deliberate CHECK absences per §6.2's
   absence list: A8 (budget/allowance), `task_state_snapshot` (no narrowing CHECK —
   §8B.2 owns admission), `percent_value` upper bound (type-guaranteed). Do not let
   autogenerate or review "fix" any of them.
3. Migration: autogenerate, then hand-fix per `30_migrations`. The hand-fix list is
   explicit (projection D3/D7):
   - partial uniques via `postgresql_where` (idiom `595e7b840926:44,50`);
   - **enum ownership** — three populations: (i) the five NEW types
     (`cost_model_term_calculation_type_enum`, `item_cost_evaluation_kind_enum`,
     three currency types) are created by `upgrade` and **explicitly dropped by
     `downgrade`** (`op.drop_table` does not drop types — exemplar
     `677ed7131bb2:271-277`); (ii) the three REUSED types (`business_task_type_enum`,
     `task_return_source_enum`, `task_state_enum`) must be hand-fixed to
     `postgresql.ENUM(..., create_type=False)` in `upgrade` (inline `sa.Enum` raises
     `DuplicateObject` against a DB at head — exemplar `261971b16234:25-28`) and
     must **NOT** be dropped by `downgrade` (`DROP TYPE task_state_enum` fails on
     `tasks.state`); note the model-layer `create_type=False` flag is inert on
     `sa.Enum` — the migration is the ONLY enforcement site;
   - **hand-add the three named `use_alter` FKs** — autogenerate omits them
     (precedent `243e62bcd858`);
   - CHECK constraints exactly per §6.2's closed list.
   Upgrade + downgrade both complete and proven per C1/C5.
4. Table guide README; registration; prefix map rows.
5. Model factories for the constraint tests below (every factory has a caller in
   this phase — charter rule 4).

## Acceptance criteria

**Databases, per criterion (projection D4 — the repo has NO test-schema harness;
without an override everything runs on the configured development DB):**
C2/C3/C4 and C1's in-suite assertions run against the **configured development
database at head** with production ORM instances (charter rule 3) — flush-only on the
rolled-back `db_session`, so rule 11½ holds by construction. C1's round-trip and
C5's ownership proof run against a **disposable database built with the master plan
§10 recipe** (`DATABASE_URL` override; created, migrated, dropped); the configured
DB is never downgraded (rule 7).

**C1 — migration lifecycle.** Manual `upgrade → downgrade → upgrade` round-trip on
the §10-recipe disposable DB (rule-1 exemption, recorded in the Review log when
exercised) **plus** two automated in-suite proxies:
(a) all nine models import; their tables, the five new PG enum types, **every
constraint on §6.2's closed CHECK list, all nine `uix_`/`uq_` names, and the three
§6.2-named FKs** exist (query `pg_constraint`/`pg_indexes` by exact name — the list
is closed, so the assertion is enumerable);
(b) **downgrade static proxy (projection D11):** a test importing the migration
module and asserting the set of enum types `downgrade` drops equals exactly the five
new types (and excludes the three reused ones) and that every table `upgrade`
creates, `downgrade` drops. This bites on the exact reversibility defect without
running a downgrade in-suite.

**C2 — partial uniques (projection D8: one (a) row per index, and one (b) row PER
PREDICATE CLAUSE — each (b) row's fixture differs from (a) in exactly that clause,
so it is the only reason acceptance holds; rule 2 companion + P-G(a)):**

| Index | (a) conflict → `IntegrityError` | (b) rows — one per clause, each accepted |
|---|---|---|
| `uix_production_cost_groups_name_active` | two non-deleted same-name groups | b1: second soft-deleted |
| `uix_production_cost_group_sections_active` (INV-G1) | section active in two groups | b1: second has `removed_at` (sole clause — §4.2/D5 shape) |
| `uix_production_cost_basis_versions_open` (INV-B1) | two open versions, one group | b1: second has `effective_to`; b2: second soft-deleted (open `effective_to`) |
| `uix_cost_model_versions_open` (INV-M1) | two open versions, one workspace | b1: second has `effective_to`; b2: second soft-deleted |
| `uix_cost_model_terms_purchase_cost` (A5) | two `item_purchase_cost` terms, one version | b1: second is `fixed_amount` type; b2: second `item_purchase_cost` but soft-deleted |
| `uix_cost_model_terms_name_active` | two same-name terms, one version | b1: **second same-name soft-deleted** (the predicate row); b2: second on another version (key-column row) |
| `uix_item_cost_evaluations_current` (INV-E1) | two current committed evaluations, one task | b1: second has `superseded_at`; b2: second is `kind='projection'`; b3: second soft-deleted |
| `uix_item_valuations_current` (INV-V1) | two current valuations, one item | b1: second has `superseded_at`; b2: second soft-deleted |
| `uq_item_cost_results_task_id` | two results, one task | b1: second for another task (no predicate — key row only) |

**Named mutation per predicate clause (P-G(a)):** dropping any single clause from an
index's `postgresql_where` must redden exactly that index's corresponding (b) row
(the row is accepted only because the clause excludes it from the index; with the
clause gone, the insert conflicts). The implementer runs these on the three
multi-clause indexes at minimum (INV-B1, INV-E1, INV-V1) and declares them.

**C3 — CHECKs (one row per boundary, exact outcome each — outcome names the
exception class: CHECK violations raise `IntegrityError` (CheckViolation); type
overflows raise `DBAPIError` (`NumericValueOutOfRangeError`, a DataError) —
projection D12):**
- `fixed_monthly_cost_minor`: −1 reject (IntegrityError), 0 reject (A1), 1 accept.
- `cost_per_worker_minute_minor`: 0 reject (A2), 0.0001 accept.
- `monthly_paid_hours`: 0 reject, 0.01 accept.
- `planning_utilization_percent`: 0 reject, 0.01 accept, 100 accept,
  100.01 reject (IntegrityError — `ck_pcbv_planning_utilization_percent_max`).
- `percent_value`: −0.001 reject (IntegrityError), 0 accept, 999.999 accept,
  **1000 reject with `DBAPIError`/DataError — the `Numeric(6,3)` type bound, NOT a
  CHECK** (§6.2 absence list; a test expecting IntegrityError here is wrong).
- **term type×columns CHECK (`ck_cost_model_terms_value_by_type`) — TOTAL 12-row
  table (projection D9): 3 types × percent_value {NULL, NOT NULL} ×
  fixed_amount_minor {NULL, NOT NULL}:**

  | # | type | percent | fixed | outcome |
  |---|---|---|---|---|
  | 1 | percentage | NOT NULL | NULL | **accept** |
  | 2 | percentage | NOT NULL | NOT NULL | reject |
  | 3 | percentage | NULL | NULL | reject |
  | 4 | percentage | NULL | NOT NULL | reject |
  | 5 | fixed_amount | NULL | NOT NULL | **accept** |
  | 6 | fixed_amount | NOT NULL | NOT NULL | reject |
  | 7 | fixed_amount | NULL | NULL | reject |
  | 8 | fixed_amount | NOT NULL | NULL | reject |
  | 9 | item_purchase_cost | NULL | NULL | **accept** |
  | 10 | item_purchase_cost | NOT NULL | NULL | reject |
  | 11 | item_purchase_cost | NULL | NOT NULL | reject |
  | 12 | item_purchase_cost | NOT NULL | NOT NULL | reject |

- money CHECKs the §6.2 list adds (projection D10) — one −1 reject / 0 accept pair
  each, plus NULL accept where nullable:
  `item_cost_evaluations.expected_sale_price_minor` (−1 reject, 0 accept);
  `item_cost_evaluations.purchase_cost_minor` (−1 reject, 0 accept, NULL accept);
  `cost_model_terms.fixed_amount_minor` (−1 reject, 0 accept — on a `fixed_amount`
  row so the type CHECK is satisfied);
  `item_cost_results.actual_worker_seconds` (−1 reject, 0 accept).
- valuation: negative `expected_sale_price_minor` reject; negative
  `purchase_cost_minor` reject; both amounts NULL reject
  (`ck_item_valuations_amount_present`); **price-only + currency accept; cost-only +
  currency accept** (two rows — each amount is the sole satisfier of its row); NULL
  currency reject (NOT NULL).
- window CHECK, **enumerated per chain** (rows run once for
  `production_cost_basis_versions` and once for `cost_model_versions`):
  `effective_to = effective_from` reject; `effective_to = effective_from + 1 day`
  accept; `effective_from` NULL accept; `effective_to` NULL accept (four rows × two
  chains).

**C4 — A8 proof.** An `ItemCostEvaluation` row with `production_budget_minor = -500`
and `allowed_worker_minutes = -12.50` INSERTs successfully. (Adding any CHECK there
turns this row red — that is the row's purpose.)

**C5 — enum ownership, proven at the migration (projection D3 replaced the
unfalsifiable metadata-create form).** On the §10-recipe disposable DB:
(a) after `alembic upgrade head`, the `pg_type.oid` of each of the three reused
types (`business_task_type_enum`, `task_return_source_enum`, `task_state_enum`) is
**unchanged** from before the migration (equivalently: `pg_depend` still ties each
to its `tasks` column), and the five new types exist;
(b) after the full `downgrade → upgrade` round-trip, the three reused types still
exist with their original oids and `tasks` is untouched.
**Named mutations (both must be run and reverted, results declared):**
(M-a) changing any reused column's migration DDL to
`postgresql.ENUM(..., create_type=True)` must make `upgrade` fail on a DB at head
(`DuplicateObject`); (M-b) adding a `.drop()` for `task_state_enum` to `downgrade`
must make the round-trip fail on `tasks.state`'s dependency. These are real
failures on the decidable site — the model-layer flag is inert and proves nothing.

**C6 — round-6 result columns (closes the projection's depth-target-3 gap).**
Reflected against the migrated schema: `item_cost_results.task_state_snapshot` is
NOT NULL and of PG type `task_state_enum`; `task_closed_at` is nullable;
`calculation_version` exists (A7); the table carries `created_at` and none of
`updated_at`/`is_deleted`.

## Notes

- Names come from the registry, not the intention's proposals — `cmvt` is the settled
  prefix for `CostModelTerm`.
- **Column-shape authority order (projection D5/D6):** intention §4/§4.7A + the
  round-6/7 pins beat any blanket convention sentence; task 2's per-table list is the
  compiled form. `production_cost_group_sections` is an interval table, not a
  soft-delete table.
- `models/tables/README.md` (the tables index) is **deferred to phase 9's drift
  batch** — it is already stale (documents dropped tables); the phase-2 reviewer
  should not file its omission. The new `models/tables/item_economics/README.md`
  table guide IS this phase's deliverable.
- Import placement in `models/__init__.py` must land after `tables.tasks.task`
  (owner of the three reused enum types) and after the FK targets (items,
  working_sections, users, workspaces); a trailing `# --- Item economics ---` block
  satisfies this. `is_deleted` indexing: uniform choice across the eight tables that
  carry it.
- The soft-delete trio on `cost_model_terms` exists for house-style shape only; no
  command will ever write it (A6) — nothing to build here, but the README states it.
- Teardown discipline (rule 11½) applies to every constraint test that commits.
- Archgraph: orient on `table-task-step`, `table-task-item`; delta at close = the new
  `table-*` nodes for this domain (one batched apply_changes, evidence = the model
  files; agents never adjudicate pending reviews).

## Review log

(append-only)
