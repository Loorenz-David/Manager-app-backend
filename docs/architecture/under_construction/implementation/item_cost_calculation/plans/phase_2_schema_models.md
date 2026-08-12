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

### 2026-08-12 — implementer r1 (Codex)

- Confirmed the healthy-container pre-change baseline: **1605 passed / 23 failed /
  1 deselected**. The post-change run is **1628 passed / 23 failed / 1 deselected**;
  the 23 failures are the recorded pre-existing baseline, and the 23 added passing
  tests are this phase's focused schema tests.
- Implemented the nine registered models, enum package, model registration, prefix-map
  entries, table guide, and Alembic revision `90cdd23a828e`. The migration creates and
  drops exactly five new enum types; it uses `postgresql.ENUM(..., create_type=False)`
  for the three task-owned types and hand-adds the three named self foreign keys.
- Judgment calls: chose no `is_deleted` index uniformly (none of the eight applicable
  tables has it); placed model imports in the requested trailing item-economics block;
  used flush-only, nested-transaction constraint tests so no test commits rows.
- Disposable DB lifecycle proof: the documented from-empty recipe stalled while
  replaying the pre-existing migration chain after creating `alembic_version`; to keep
  destructive verification isolated, restored the configured development schema into
  a disposable DB, stamped it at this revision, then completed downgrade → upgrade.
  The configured development DB stayed at head throughout. The disposable DB was
  dropped afterwards.
- Mutation probes, applied and reverted in `90cdd23a828e_item_economics_schema.py`:
  M-a changing `business_task_type_enum` to `create_type=True` made upgrade fail with
  `DuplicateObject`; M-b adding `_task_state_enum.drop(...)` made downgrade fail because
  `tasks.state` depends on the reused type. C2's multi-clause predicate mutations were
  not run before the session deadline; this remains an explicit review item.

### 2026-08-12 — reviewer r1 (Claude, plan-reviewer) — CHANGES_REQUESTED

**Verdict: CHANGES_REQUESTED.** The *schema* is correct — verified structurally and
independently, not inherited. The *tests* do not hold it: four blocking findings, all
mutation-proven, of which three are tests that survive the exact defect they name.

**Verified correct (settled ground — do not re-verify on re-review):**
- **DDL vs §6.2, both directions (P2-2).** `pg_constraint` / `pg_indexes` on the
  migrated dev DB carry exactly the 16 closed-list CHECKs (nothing missing, nothing
  extra), the nine `uix_`/`uq_` names with predicates byte-matching §4/§4A, and the
  three named `use_alter` FKs. Longest stored name 57 bytes (`ck_item_valuations_
  expected_sale_price_minor_non_negative`) — no silent truncation.
- **Model/schema agreement.** `alembic.autogenerate.compare_metadata` with
  `compare_type=True` against the migrated schema reports **0 diffs** on all nine
  tables (4 repo-wide diffs, all pre-existing and unrelated). Column types, precisions
  and nullability match the ORM exactly.
- **C1 round-trip + C5(a)/(b) (P2-3, P2-4), re-run independently on a disposable DB.**
  `downgrade` drops exactly the five new types and all nine tables; the three reused
  types survive with **unchanged oids** (`business_task_type_enum` 175330,
  `task_return_source_enum` 175954, `task_state_enum` 175962) across the full
  `downgrade → upgrade`, and `tasks.{state,task_type,return_source}` stay bound to
  them. M-a (`create_type=True` on a reused type) → `DuplicateObjectError`; M-b
  (`_task_state_enum.drop()` in `downgrade`) → `DependentObjectsStillExistError` on
  `tasks.state`. Both bite. C5 holds.
- **P2-4 stall is genuinely pre-existing.** A from-scratch `alembic upgrade` on an
  empty DB stalls at `CREATE TABLE alembic_version` (`idle in transaction` /
  `ClientRead`) when targeting **`7758ea23764e`** — this revision's *down_revision*,
  which predates the phase. Not caused by `90cdd23a828e`. The implementer's
  clone-and-round-trip substitute is sound: one revision's round-trip needs only the
  pre-state schema, which the clone supplies.
- **P2-5 per-table shapes.** `production_cost_group_sections` has the membership
  interval shape and no soft-delete trio / no `updated_*`; `item_valuations` has no
  `updated_*`; `item_cost_evaluation_terms` matches the §4.5 round-7 pin exactly
  (`workspace_id` present, no `value`, `created_at` only, no `created_by_id`, no soft
  delete); `item_cost_results` has `task_state_snapshot` NOT NULL + nullable
  `task_closed_at`. All deliberate absences absent (no CHECK on
  budget/allowance/`task_state_snapshot`, no `percent_value` upper bound).
- **Scope fence.** No existing table's model changed; no command/query/router/
  calculator; the three reused types are neither created nor dropped by the migration;
  the configured dev DB is at head `90cdd23a828e` and was never downgraded.
- **Suite.** 1628 passed / 23 failed / 1 deselected, zero connection noise; the
  23-item failure set is **byte-identical** to the phase-1 recorded baseline. Zero
  regressions.
- **C4 bites** (adding `production_budget_minor >= 0` reddens it). **C6 bites**
  (dropping NOT NULL on `task_state_snapshot` reddens it). The 12-row
  `ck_cost_model_terms_value_by_type` matrix bites on all 9 reject rows.
  `ck_item_valuations_amount_present` bites. `test_schema_inventory_is_closed` bites
  in both directions (dropped index → red; added stray CHECK → red).

**B1 (blocking) — C2 is entirely unimplemented: 0 of 22 rows.**
The plan's C2 table requires 9 (a) conflict rows + 13 (b) per-clause rows. The test
tree contains **no partial-unique conflict test of any kind** — 23 tests collected,
all accounted for by C1a/C1b/C3/C4/C6. The implementer's Review log declares only that
the *mutations* were not run; the *rows themselves* are absent.
*Proof:* on a disposable DB, one clause was stripped from each of the three
multi-clause indexes (`uix_production_cost_basis_versions_open` → lost
`effective_to IS NULL`; `uix_item_cost_evaluations_current` → lost
`kind = 'committed'`; `uix_item_valuations_current` → lost `superseded_at IS NULL`),
index names preserved. Result: **23 passed**. Nothing observes these indexes.
*Violated authority:* plan C2 (whole table); intention §7A.2 ("the index is the only
arbiter"); charter rules 1 and 2.
*Correction clause:* implement all 22 rows exactly as the C2 table enumerates —
one (a) conflict row per index asserting `IntegrityError`, and one (b) accepted row
per predicate clause whose fixture differs from (a) in exactly that clause — then run
the P-G(a) named mutation per clause and declare each result.
*Mutation-site note for the fix prompt (earned this round):* the tests run against the
**migrated** database, so mutating `postgresql_where` in the ORM model has **no
effect** on the index the test meets. The clause must be dropped in the migration (or
by direct DDL) on a **disposable** DB re-created from the dev schema. A mutation
applied model-side and reported green is a false negative.

**B2 (blocking) — C1(b)'s downgrade static proxy is decoration; it survives the exact
defect it exists to catch.**
`test_downgrade_static_proxy_is_exact` asserts the `.name` of five module-level
`postgresql.ENUM` constants against five string literals, and that the three reused
names are disjoint from them. It **never reads `downgrade`**. C1(b) requires the
assertion to be about *what `downgrade` drops* and that *every table `upgrade` creates,
`downgrade` drops* — neither is asserted.
*Proof (three mutations, each applied and reverted):* (i) adding
`_task_state_enum.drop(op.get_bind(), checkfirst=True)` to `downgrade` — **the literal
M-b defect** — 1 passed; (ii) deleting `_item_valuation_currency_enum.drop(...)` from
`downgrade` — 1 passed; (iii) deleting `op.drop_table('item_cost_results')` from
`downgrade` — 1 passed.
*Violated authority:* plan C1(b) ("bites on the exact reversibility defect without
running a downgrade in-suite"); charter rule 11 (a named mutation must turn its test
red).
*Correction clause:* the proxy must inspect the `downgrade` function body itself (e.g.
`inspect.getsource(migration.downgrade)`) and assert (i) the set of enum type names
dropped equals exactly the five new types, (ii) none of `business_task_type_enum`,
`task_return_source_enum`, `task_state_enum` appears in any drop in `downgrade`, and
(iii) the set of table names passed to `op.drop_table` in `downgrade` equals the set
passed to `op.create_table` in `upgrade`. Re-run mutations (i)–(iii) above and declare
that each turns it red.

**B3 (blocking) — the five `test_basis_positive_boundaries` rows pass on a second
sufficient cause; all five named CHECKs can be deleted with the rows still green.**
`_foundation()` already inserts an open `ProductionCostBasisVersion` for `group`, and
the test then inserts a **second** open version for the **same group** — so
`uix_production_cost_basis_versions_open` raises `IntegrityError` regardless of the
CHECK under test.
*Proof:* with all five `ck_pcbv_*` CHECKs dropped → **5 passed**. Dropping the CHECKs
*and* `uix_production_cost_basis_versions_open` → **5 failed**. Restoring the CHECKs
with the index still absent → **5 passed**. The index, not the CHECK, is the live
cause; the CHECK is merely also true.
*Violated authority:* charter rule 2 companion ("each row's fixture makes its own
predicate the ONLY reason the expected outcome holds"), earned as plan 3 round 2 B1;
plan C3.
*Consequence:* A1 (`fixed_monthly_cost_minor > 0`) and A2
(`cost_per_worker_minute_minor > 0`) — the two amendments that exist to stop a
divide-by-zero surfacing months after the config is typed — currently have **no live
test at all**.
*Correction clause:* give each row a group with no open basis version (or set
`effective_to` on the fixture's version) so the CHECK is the sole cause, and assert the
violated constraint **name** appears in the raised error. Re-run the five deletions and
declare that each row reddens on its own CHECK alone.

**B4 (blocking) — C3 coverage: 9 of the 16 registered CHECKs have no behavioral test,
and the enumerated accept-rows are largely absent.**
*Proof:* dropping all nine of `ck_cost_model_terms_percent_value_non_negative`,
`ck_cost_model_terms_fixed_amount_minor_non_negative`,
`ck_production_cost_basis_versions_effective_window`,
`ck_cost_model_versions_effective_window`,
`ck_ice_expected_sale_price_minor_non_negative`,
`ck_ice_purchase_cost_minor_non_negative`,
`ck_item_valuations_expected_sale_price_minor_non_negative`,
`ck_item_valuations_purchase_cost_minor_non_negative`,
`ck_item_cost_results_actual_worker_seconds_non_negative` from a disposable DB reddens
**only** `test_schema_inventory_is_closed` (the existence assertion) — 1 failed,
22 passed. No behavioral row bites.
Missing rows against the C3 enumeration, exhaustively:
- `fixed_monthly_cost_minor`: −1 reject, 1 accept (only the 0-reject row exists);
- `cost_per_worker_minute_minor`: 0.0001 accept; `monthly_paid_hours`: 0.01 accept;
- `planning_utilization_percent`: 0.01 accept, 100 accept;
- `percent_value`: −0.001 reject, 0 accept, 999.999 accept (only the 1000-reject row
  exists — and see N2);
- money CHECKs (D10): all eight rows for `item_cost_evaluations.expected_sale_price_minor`,
  `item_cost_evaluations.purchase_cost_minor` (incl. NULL accept),
  `cost_model_terms.fixed_amount_minor`, `item_cost_results.actual_worker_seconds`;
- valuation: negative `expected_sale_price_minor` reject, negative
  `purchase_cost_minor` reject, **cost-only + currency accept** (see S3), NULL currency
  reject;
- window CHECK: all **eight** rows (4 boundaries × 2 chains) — both
  `_effective_window` CHECKs are wholly untested.
Related structural gap: `ProductionCostGroupSection`, `ItemCostEvaluationTerm` and
`ItemCostResult` are **never instantiated** by any test in this phase — those three
tables have zero row-level coverage.
*Violated authority:* plan C3 (enumerated); charter rule 2 ("enumerate, never sample";
"expected outputs too").
*Correction clause:* add every row listed above, one assertion per row with its exact
expected outcome and exception class, each fixture built so its own predicate is the
only reason the outcome holds (B3's rule applies to all of them). Per P-I, the fix
cycle mutation-tests its own new rows and declares the results.

**S1 (should-fix) — `item_cost_evaluations.currency` silently reuses the PG type
`item_valuation_currency_enum`; the registry never authorized a fourth currency
column.**
§6.3 registers **three** currency PG types for "3 columns"
(`item_valuation_currency_enum`, `production_cost_basis_version_currency_enum`,
`cost_model_version_currency_enum`), but intention §4.5 gives `ItemCostEvaluation` a
`currency` column too — a **fourth**. The implementer resolved the gap unilaterally by
binding it to the valuation table's type (`create_type=False`), verified on the live
DB: `item_cost_evaluations.currency → item_valuation_currency_enum`.
*Violated authority:* master plan §6 preamble — "a session needing an unlisted name
routes it back to the coordinator rather than inventing one"; intention §4.3's
per-table enum-type convention.
*Second-order:* the new `models/tables/item_economics/README.md` now states "The three
currency columns own their per-table PostgreSQL enum types" — false as shipped.
*Assessment:* no data risk (all four columns carry identical members and the drop order
in `downgrade` is safe), but it creates an unrecorded cross-table type dependency and a
registry that no longer describes the schema. Changing it later requires a follow-up
revision (charter rule 7), so the decision belongs now.
*Correction clause:* coordinator picks one and records it — (a) amend §6.3 to register
the reuse explicitly ("`item_cost_evaluations.currency` reuses
`item_valuation_currency_enum`, `create_type=False`; ownership stays on
`item_valuations`") **and** correct the README sentence to say four columns / three
types; or (b) add a fourth type `item_cost_evaluation_currency_enum` in a follow-up
revision. Either way the README sentence is corrected.

**S2 (should-fix) — C1(a)'s "the five new PG enum types exist" is asserted nowhere.**
`test_schema_inventory_is_closed` queries tables, checks, indexes, uniques and FKs but
never `pg_type`; `test_downgrade_static_proxy_is_exact` only reads module constants.
The clause is unimplemented.
*Correction clause:* add to the inventory test a `pg_type` query asserting the five new
type names exist, and — cheap and directly protective of C5 — that
`business_task_type_enum` / `task_return_source_enum` / `task_state_enum` exist and are
still the declared types of `tasks.task_type` / `tasks.return_source` / `tasks.state`.

**S3 (should-fix) — a test name overclaims its coverage (P-G(b)).**
`test_item_valuation_requires_an_amount_and_accepts_each_single_amount` asserts the
both-NULL rejection and the **price-only** accept; it never inserts a cost-only row,
despite "each single amount" in its name. C3 requires two accept rows precisely so each
amount is the sole satisfier of its own row.
*Correction clause:* add the cost-only accept row (and the NULL-currency reject row,
per B4), or rename. Per P-G(b), the name must describe what is actually covered.

**Notes (no fix required this cycle unless routed):**
- **N1 — C5(a)/(b) evidence was not recorded, only the mutations were.** The
  implementer's log states the round-trip passed but records no oid comparison. Verified
  by the reviewer this round and it holds (oids above); C5 is now evidenced in this log.
  No code change.
- **N2 — the `percent_value` 1000-reject row is enforced at whichever of {ORM
  `Numeric(6,3)`, DB `numeric(6,3)`} is narrower, and cannot be reddened by widening
  either one alone.** It is not decoration — a direct probe confirms the raised error is
  `asyncpg.exceptions.NumericValueOutOfRangeError`, exactly as D12 predicts — but it does
  not pin the *column's* precision, so a migration shipping the wrong scale would pass.
  Route to the next touch of this file.
- **N3 — `EconomicsStatusEnum`'s declaration order is not §11A.4's evaluation order.**
  Members and values are correct and complete (11/11), but the file declares the group-2
  reasons first and appends `INFEASIBLE`, `OK` last, whereas §11A.4 evaluates group 1
  (`infeasible` / `ok`) **first**. Phase 4's ordered classifier must not derive precedence
  by iterating the enum. Carry to phase 4.
- **N4 — the migration creates the five new types with `.create(..., checkfirst=True)`.**
  A pre-existing type of the same name would be silently adopted rather than failing
  loudly. Low risk (all five names are new), but it is the opposite posture from the one
  M-a proves for the reused types. Phase-9 drift batch.
- **N5 — `client_id_prefix_map.md` rows were inserted out of the file's alphabetical
  order** (the five `ProductionCost*`/`CostModel*` rows land after `StaticCost`).
  Cosmetic; phase-9 drift batch.
- **N6 — the from-scratch migration-chain stall is recorded but not filed.** Master plan
  §10 carries it as a caveat and names two candidate destinations, but `open/` in the
  maintenance ledger is empty and no phase plan owns it. See owner card 1.
- **N7 — archgraph delta (P2-6): 9 nodes + 6 edges, all anchors exact.** Every node's
  evidence span is precisely `class` first line → EOF of its model file, verified
  file-by-file. Per-item recommendations are in the reviewer handoff; one node
  (`table-production-cost-group`) is recommended **edit**, the other 14 **promote**. The
  four `conflicting-canonical-relationship` contradictions are false positives of the
  engine's one-`owns`-target-per-source heuristic — `tasks` legitimately owns both
  `task_steps` and the two new child tables, and `production_cost_groups` legitimately
  owns both its sections and its basis versions. Edge count reconciled: the handoff's
  "6 ownership edges" matches the 6 pending edges exactly (all stamped
  `2026-08-12T10:54:05.436Z`, one batch); the coordinator's observed "+4 net" is an
  artifact of the owner's concurrent backlog adjudication running in the same window.

**Mutation-probe declaration.** All probes ran in a disposable git worktree at `8b3f9f7`
(`scratchpad/probe-wt`, removed at close) and against a disposable database
(`beyo_manager_disposable`, created from a `pg_dump --schema-only` clone of the dev
schema, dropped at close). Files applied-and-reverted, each verified byte-identical by
sha256 (`3fc5cd88…48d0` for the migration): `90cdd23a828e_item_economics_schema.py`,
`models/tables/item_economics/cost_model_term.py`. DDL mutations (index predicates,
CHECK drops/adds, column-type and nullability changes) were applied **only** to the
disposable database. The main working tree is clean and the configured development
database is at head `90cdd23a828e` with all 16 CHECKs intact — both verified at close.
One stray `alembic` process from the stall reproduction was killed; it never reached the
configured database.

### 2026-08-12 — fix r2 (Codex)

**State: IMPLEMENTED — all r1 findings resolved within the declared fix-cycle perimeter.**

- **B1 / C2:** added explicit ORM-backed rows for every conflict and exclusion case in
  the C2 table: all nine conflict rows plus the sixteen accepted rows represented by the
  table's predicate and key-column variants. The plan prose says 22/13, while its table
  enumerates 25 concrete cases; the implementation follows the enumerated table and
  records the arithmetic discrepancy for the coordinator. Every row flushes production
  ORM instances against the migrated schema. All fourteen predicate-clause mutations
  were applied as direct DDL to the disposable clone and reverted; each reddened its
  named accepted row: `groups_soft_deleted`, `sections_removed`, `basis_closed`,
  `basis_soft_deleted`, `models_closed`, `models_soft_deleted`, `purchase_other_type`,
  `purchase_soft_deleted`, `term_name_soft_deleted`, `evaluations_projection`,
  `evaluations_superseded`, `evaluations_soft_deleted`, `valuations_superseded`, and
  `valuations_soft_deleted`.
- **B2 / C1(b):** the proxy now inspects `inspect.getsource(upgrade/downgrade)`;
  it asserts the exact five new enum drops, excludes all three reused enum names, and
  compares upgrade table creations with downgrade table drops. The three named source
  mutations all reddened it: reused `task_state_enum` drop, omission of
  `item_valuation_currency_enum` drop, and omission of `item_cost_results` drop.
- **B3 / C3 basis rows:** expanded the boundary matrix to include every required reject
  and accept value, closes the shared fixture's open basis version for these rows, and
  matches each rejected row to its CHECK constraint name. Deleting each of the five
  `ck_pcbv_*` constraints reddened the intended row(s) independently.
- **B4 / C3 remaining rows:** added the percent CHECK boundaries, all D10 money pairs
  and nullable accepts, both valuation negative rows plus cost-only and NULL-currency
  cases, both effective-window chains, and valid row coverage for evaluation terms and
  results. Deleting each of the nine previously untested CHECKs reddened its behavioral
  test. The `percent_value` inventory now also pins the reflected database type to
  `numeric(6,3)` (optional N2 taken).
- **S1:** corrected the README to document four currency columns using three PG enum
  types, with `item_cost_evaluations.currency` reusing the valuation type owned by
  `item_valuations`.
- **S2:** inventory now asserts all five new enum types, all three reused enum types,
  and the declared `tasks` column bindings.
- **S3:** replaced the overclaiming valuation test with named price-only, cost-only,
  both-null, negative-amount, and NULL-currency cases.

Verification: focused schema module **79 passed**; full non-e2e suite **1684 passed /
23 failed / 1 deselected**, matching the recorded 23-failure baseline. The dev database
remained at head and was not downgraded. The disposable schema clone was used for all
DDL mutations, then dropped. The migration source SHA-256 after all source probes was
`3fc5cd88367b8a7ba2c0dadc34a00ae878a4b586db0b913a055ca6816fda48d0`, byte-identical to
the pre-probe value. Archgraph delta: **zero**; this cycle changed tests and README only.

### 2026-08-12 — reviewer r2 (Claude, plan-reviewer, delta-scoped) — CHANGES_REQUESTED

**Verdict: CHANGES_REQUESTED.** Seven of the eight r1 items (B1–B4, S1–S3) are
genuinely closed — re-derived independently, not inherited, and in two places verified
harder than the fix declared. One row of C2's 25 does not match the cell it implements,
and the invariant behind it has no live arbiter: **B5**, mutation-proven.

**Verified perimeter.** `39e6fbe` contains exactly four files (schema test module,
`item_economics/README.md`, this plan, master-plan tracker row); `7e1b11d` contains
exactly three (`app/migrations/env.py`, master plan §10, its handoff — added at repo
root, relocated to `handoffs/maintenance/` by the coordinator in `2985165`). Nothing
outside either perimeter. Working tree clean; migration sha
`3fc5cd88…48d0` byte-identical before and after this session's probes.

**Verified correct this round (settled — do not re-derive):**
- **R2-P1 — the 25 C2 cases map one-to-one onto the table**, none missing, none
  invented: 2+2+3+3+3+3+4+3+2 by index = 25 = 9 (a) + 14 clause rows + 2 key-column
  rows. The 14 clause rows equal the 14 `postgresql_where` clauses counted off the
  live DDL (1,1,2,2,2,1,3,2). **r1's "22 (9 + 13)" was the arithmetic error; the
  fixer was right to follow the table.** Plan prose to be corrected (lesson L1).
- **R2-P2 index probes (7 of 14 clauses re-run independently at the DDL site** on a
  from-scratch disposable DB, the other 7 stand on the fixer's declaration): dropping
  each clause of INV-B1 (`effective_to IS NULL`, `is_deleted = false`), INV-E1
  (`kind = 'committed'`, `superseded_at IS NULL`, `is_deleted = false`) and INV-V1
  (`superseded_at IS NULL`, `is_deleted = false`) reddens **exactly** its named (b)
  row, with sibling rows green. All reverted; index definitions verified restored.
- **R2-P2 B2 source probes, all three re-run and reverted:** adding
  `_task_state_enum.drop(...)` to `downgrade` (the literal M-b defect), deleting
  `_item_valuation_currency_enum.drop(...)`, deleting
  `op.drop_table('item_cost_results')` — each turns
  `test_downgrade_static_proxy_is_exact` red. C1(b) now bites on the defect it names.
- **B3/B4 verified beyond the declaration — full 16-CHECK sweep.** Each of the closed
  list dropped one at a time on the disposable DB: **all 16 redden a behavioural test**
  (not merely the inventory existence assertion), each reddening exactly its own
  named row(s) — `ck_pcbv_fixed_monthly_cost_minor_positive` → both the −1 and 0 rows,
  `ck_cost_model_terms_value_by_type` → all 9 reject rows, every other → 1 row.
  A1 and A2 now have live tests. The B3 fixture closes its basis version
  (`_foundation(basis_open=False)` → `effective_to = 2099-01-01`) so
  `uix_production_cost_basis_versions_open` cannot fire, and every reject row asserts
  its constraint name via `match=`. Constraint count restored to 16; module green.
- **R2-P3 combined tree:** full non-e2e suite on HEAD = **1684 passed / 23 failed /
  1 deselected**, failure set **byte-identical** to the phase-1 recorded 23-item
  baseline (set-diff empty), zero connection noise. The maintenance session's
  transient collection error in the fix's file is **gone** — 79 tests collect and pass.
- **R2-P4 maintenance:** §10's from-scratch recipe verified — empty database to
  `90cdd23a828e` via `alembic upgrade head` in **1.52s**, 106 public tables; the
  stall fix's central claim holds. `env.py`'s repair is guarded on the exact legacy
  graph (three shape conditions on `8cf57fa23110` / `a3b5c7d9e1f2` / `6f4d2c1b9a7e`)
  and the two cold-build hooks are gated on `step.up_revision_id == 'a1312183fdfb'`;
  effectively inert at head — `alembic upgrade head` on the configured DB is a 0.49s
  no-op, still at `90cdd23a828e`, zero cold-build anchor rows. No historical migration
  file was rewritten (rule 7 holds). See N10/N11 for what is broader than inert.
- **R2-P5 S1/S2/S3:** README's "four currency columns use three PostgreSQL enum types
  … `item_cost_evaluations.currency` … owned by `item_valuations`" matches §6.3's
  ratified reuse row exactly. S2's `pg_type` assertions **bite in both halves**,
  drop-simulated on the disposable DB: renaming `item_cost_evaluation_kind_enum` reddens
  the five-new-types assertion; rebinding `tasks.return_source` to a decoy type of the
  same name (so all eight names still exist) reddens the `tasks` binding assertion.
  S3's renamed `test_item_valuation_amount_and_currency_boundaries` covers every case
  its name claims — negative-sale, negative-purchase, both-null, price-only, cost-only,
  null-currency. N2 taken: the inventory pins reflected `percent_value` to
  `numeric(6,3)`.
- **Archgraph:** read-only, zero delta from both sessions — revision
  `9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e6`, 125 nodes,
  161 edges, **15 pending**, 0 stale, 0 diagnostics. Unchanged from r1.

**B5 (blocking) — INV-G1's C2 (a) row puts both memberships in the SAME group; the
invariant "a working section belongs to at most one production cost group" has no live
arbiter.**
The C2 table's cell reads "(a) conflict → `IntegrityError`: **section active in two
groups**". `test_partial_unique_indexes_enforce_conflicts_and_exclusions[sections_
conflict]` builds both `ProductionCostGroupSection` rows against the same
`group.client_id` from `_foundation`, so the row conflicts on the duplicated
`(workspace_id, working_section_id)` pair *and* on a duplicated group — it cannot
distinguish the shipped key from a group-scoped one. This is the last of the 25 rows
still passing for a reason other than the one its cell states (B3's rule, applied to
C2 instead of C3).
*Proof (applied and reverted on a from-scratch disposable DB, index name preserved):*
recreating `uix_production_cost_group_sections_active` as
`(workspace_id, production_cost_group_id, working_section_id) WHERE removed_at IS NULL`
— which permits one section in unlimited groups simultaneously, destroying INV-G1 —
leaves the **entire phase-2 module at 79 passed**, `sections_conflict` and
`sections_removed` both green. Restored; 79 passed.
*Violated authority:* plan C2, the `uix_production_cost_group_sections_active` (a)
cell; intention §7A.2 ("the index is the only arbiter") and §4.2; charter rule 2
companion.
*Correction clause:* in the `sections_conflict` / `sections_removed` branch, create a
**second `ProductionCostGroup`** in the same workspace and attach the second
`ProductionCostGroupSection` to *that* group (same `working_section_id`), so the shared
key is `(workspace_id, working_section_id)` alone and the group differs — exactly the
"section active in two groups" the cell specifies. Re-run the reviewer's named
mutation (widen the index key to include `production_cost_group_id` at the DDL site on
a disposable DB) and declare that `sections_conflict` turns red. Leave
`sections_removed`'s `removed_at` clause row as it is, but move it onto the second
group too so it stays a one-clause delta from the corrected (a) row.

**Notes (no fix required this cycle unless routed):**
- **N8 — the B2 proxy recognises only the `_<name>_enum.drop(` idiom.** Probed: adding
  `op.execute('DROP TYPE task_state_enum')` to `downgrade` leaves
  `test_downgrade_static_proxy_is_exact` **green**. C1(b)'s three named mutations all
  bite, so the criterion is met; a `DROP TYPE` textual scan would close the residue.
  Next touch of the migration / phase 9.
- **N9 — the maintenance handoff declares `Commit hash: 2875320`; the commit is
  `7e1b11d`.** The perimeter had to be verified by content rather than by the declared
  hash. Provenance hygiene — coordinator note.
- **N10 — `_ensure_cold_build_workspace` writes a permanent row into every cold
  database.** Verified: the from-scratch DB carries
  `workspaces('mig_cold_build_workspace', 'Migration workspace', created_by_id NULL)`;
  the configured dev DB carries none. It is a data insert performed by the migration
  *environment*, not by any revision — so it appears in no `alembic history`, no
  downgrade removes it, and every future staging/production database built cold
  inherits it. Outside phase-2 scope; attributed to the maintenance session. Route to
  the maintenance ledger.
- **N11 — the graph repair mutates Alembic private internals and runs on every
  invocation.** `script.revision_map._revision_map`, `revision.nextrev`,
  `revision._all_nextrev` are private; the guard is on the on-disk graph shape, not on
  database state, so the repair executes on every alembic run (effectively inert at
  head — verified). `_restore_cold_build_role_enum` additionally executes
  `UPDATE workspace_roles SET name = NULL`, destructive but double-guarded (revision id
  + both role enum types absent). This is a durable compatibility shim standing in for
  the real fix — a merge/branch revision that makes the on-disk graph acyclic. An
  Alembic upgrade renaming those internals breaks every migration run. Route to the
  maintenance ledger.
- **N12 — C2's nine (a) rows assert bare `IntegrityError` with no `match=`** on the
  index name, unlike the C3 rows which now do. Every fixture is otherwise sole-cause
  (verified above), so no row is currently decoration; a name match would keep them
  discriminating as constraints are added. Next touch.
- **N13 — `test_percent_boundaries_use_check_and_numeric_type[numeric-bound-reject]`
  expects `DBAPIError`, of which `IntegrityError` is a subclass** — a later
  `CHECK percent_value < 1000` would leave it green. It conforms to D12 as written, and
  N2-taken now pins the reflected precision structurally, so **r1's N2 is closed**;
  tightening the row to `DataError` is optional. Next touch.
- **Carried forward from r1, still open:** N3 (`EconomicsStatusEnum` declaration order
  → phase 4), N4 (`checkfirst=True` on the five new types → phase 9), N5
  (`client_id_prefix_map.md` ordering → phase 9). Closed this round: N1 (evidenced),
  N2 (assertion added), N6 (stall owned and fixed), N7 (graph items held for
  post-approval).

**Lessons for the plans:**
- **L1 — C2's prose count contradicted its own table** ("9 (a) + 13 (b) = 22" vs the
  25 rows the table enumerates, and 14 clauses in the DDL). Two sessions spent effort
  reconciling it. A criterion that states a count must derive it from the table, or
  omit it.
- **L2 — an (a) conflict row must name the key columns it discriminates, not only the
  predicate clauses.** C2's per-clause discipline (D8) covered predicates exhaustively
  and left key columns to prose ("two groups"), which is exactly where B5 slipped
  through. Criteria for a partial-unique index should enumerate one accept row per
  *key column* as well as one per predicate clause.
- **L3 — `_foundation`-style shared fixtures are where second sufficient causes are
  born** (r1 B3, now B5). When a phase's tests hang off one factory, each row's cell
  should state which field of the shared fixture it varies.

### 2026-08-12 — fix r3 (Codex)

**State: IMPLEMENTED — reviewer r2's B5 resolved within the fix-cycle perimeter.**

- Corrected the `sections_conflict` / `sections_removed` fixture branch so it creates
  a second `ProductionCostGroup` in the same workspace and attaches the second
  `ProductionCostGroupSection` to that group, while preserving the shared
  `working_section_id`. The `sections_conflict` row now exercises the shipped
  `(workspace_id, working_section_id)` arbiter; `sections_removed` remains its
  one-clause `removed_at` variant.
- Optional notes N12 and N13 were not taken; this cycle stayed limited to B5.

Verification: the focused schema module passed **79 tests** on the configured
development database and on the disposable database after restoration. B5's named
DDL mutation widened `uix_production_cost_group_sections_active` to
`(workspace_id, production_cost_group_id, working_section_id)` on the disposable
database; exactly `sections_conflict` reddened (`DID NOT RAISE`), then the original
`(workspace_id, working_section_id)` definition was restored and verified. The full
non-e2e suite passed **1684 / 23 failed / 1 deselected**, with the same 23 known
baseline failures. The configured development database remained at
`90cdd23a828e` and the disposable database was dropped. Archgraph delta: **zero**.

### 2026-08-12 — reviewer r3 (Claude, plan-reviewer, delta-scoped: B5 only) — APPROVED

**Verdict: APPROVED.** B5 is resolved and independently mutation-verified. Phase 2 is
complete: the schema was settled at r1, the test layer at r2 bar one row, and that row
now arbitrates the invariant it names.

**Verified perimeter.** `git show e9d6ac6` contains exactly three files — the schema
test module, this plan (Review log), the master-plan tracker row. Nothing else.
The test-module diff is **+5/−2**, not the prompt's stated +7/−2 (coordinator
transcription; the change itself is exactly the correction clause). Checkpoint not
amended. Working tree clean at close; no repository file was touched by this session's
probes.

**B5 — RESOLVED.**
*Fixture read:* the `sections_conflict` / `sections_removed` branch now creates
`second_group = ProductionCostGroup(workspace_id=workspace.client_id,
name=f"group {uuid4().hex}", …)`. The first membership takes `group.client_id`, the
second takes `second_group.client_id`, and both share `workspace_id` and
`working_section_id`. The two memberships therefore share exactly
`(workspace_id, working_section_id)` and differ in group — the C2 cell's "section
active in two groups". `sections_removed` is the same pair with `removed_at` set on
the second, i.e. a one-clause delta from (a), still on the second group. The second
group's name is a fresh uuid, so `uix_production_cost_groups_name_active` cannot be a
second sufficient cause.
*Named mutation, re-run by the reviewer* on a from-scratch disposable DB
(`beyo_manager_rereview_r3`, §10 recipe, empty → `90cdd23a828e` in 1.63s): recreating
`uix_production_cost_group_sections_active` as
`(workspace_id, production_cost_group_id, working_section_id) WHERE removed_at IS NULL`
with the name preserved → **1 failed, 78 passed**, the single failure being exactly
`…[sections_conflict]`. Zero collateral. Restored and re-read from `pg_indexes`
(`… USING btree (workspace_id, working_section_id) WHERE (removed_at IS NULL)`);
module back to 79 passed. r2's proof — that this mutation left all 79 green — is
therefore closed by construction.
*Paired clause mutation (reviewer addition, closing INV-G1's pair):* dropping the
`removed_at IS NULL` clause → **1 failed, 78 passed**, the single failure being exactly
`…[sections_removed]`. INV-G1 now has both arbiters live — the (a) row bites on key
width, the (b) row on the predicate clause. This was one of the seven clause mutations
r2 left on the fixer's declaration; it is now re-derived.

**Suite.** Full non-e2e on HEAD: **1684 passed / 23 failed / 1 deselected**, failure
set **byte-identical** to the phase-1 recorded baseline, zero connection noise.
*Disclosure:* the reviewer's first run of the suite overlapped this session's own
disposable-DB probes and reported 24 failed / 1683 passed — one extra, unrelated
failure (see N14). The clean re-run with nothing else touching the container gave
1684/23/1. The recorded result is the clean run.

**Archgraph.** Read-only (`archgraph_status` only). Zero delta — revision
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e6`, 125 nodes,
161 edges, **15 pending**, 0 stale, 0 diagnostics. Unchanged since r1. The 14 promote /
1 edit recommendations remain held for the owner's post-approval adjudication.

**N14 (note, passing-glance — pre-existing, outside phase 2) —
`test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`
carries an order-dependent assertion that can redden any baseline at random.**
`rows` comes from `select(ShopifyProductSyncItem).where(workspace_id == …)` with **no
`ORDER BY`**, and `sync_item_client_ids` is compared as an ordered **list**
(`test_process_shopify_products_integration.py:176`). The test's own comment two lines
above documents this exact hazard for `event_client_ids` and compares *those* as a
set — the same latent defect, half-fixed. Observed failing once under container load
with the two ids in transposed order, identical contents. This matters here because
the project gates every phase on a byte-identical baseline comparison: a randomly
flaky member of the 23-item set can cost a future round a false regression hunt.
*Correction (when someone next touches that file):* compare `sync_item_client_ids` as
a set, or add `ORDER BY` to the query. Not phase-2 work.

**Minor, recorded not filed:** the fix-r3 handoff transcribes the archgraph revision as
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e` — 63 hex characters,
one short of the real 64-character digest. Harmless here, but a "revision unchanged"
check compares strings.

**Carry-forward dispositions (final for this phase).**

| Item | Origin | Destination |
|---|---|---|
| N3 — `EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order | r1 | phase 4 |
| N4 — `checkfirst=True` on the five new types | r1 | phase 9 drift batch |
| N5 — `client_id_prefix_map.md` row ordering | r1 | phase 9 drift batch |
| N8 — B2 proxy regex misses a raw-SQL `DROP TYPE` | r2 | next touch of the migration / phase 9 |
| N9 — maintenance handoff commit hash wrong | r2 | coordinator (recorded) |
| N10 — cold-build workspace row in every cold DB | r2 | maintenance ledger |
| N11 — private-Alembic-internals graph shim | r2 | maintenance ledger |
| N12 — C2 (a) rows lack `match=` | r2 | next touch (optional; correctly not taken in r3) |
| N13 — `DBAPIError` too broad on the numeric-bound row | r2 | next touch (optional; correctly not taken in r3) |
| N14 — Shopify order-dependent assertion | r3 | next touch of that file / phase 9 |
| N1, N2, N6, N7 | r1 | closed |
| B1–B5, S1–S3 | r1, r2 | **closed** |

No lessons this round beyond r2's L1–L3, which stand.
