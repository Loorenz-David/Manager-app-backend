---
plan: phase 2 (schema, models & migration)
role: reviewer
session_doctrine: plan-projection (charter: reviewer role tables, round 0)
round: 0
date: 2026-08-12
state: COMPLETE
verdict: AMENDMENTS_REQUIRED
actor: Claude (plan-projection agent)
---

# Projection handoff — phase 2, round 0

## Opening (owner-readable)

Phase 2 builds the nine database tables the whole cost feature sits on. The design is
sound — the tables, the rules they enforce, and the names they were given all hold up.
What does not hold up is the plan's confidence that the work can be checked. Four of
the plan's names for database rules are too long for PostgreSQL, which silently cuts
them short; a test the plan relies on to prove the tables were built correctly would
then look for a name that does not exist. Separately, one of the five checks the plan
lists cannot fail no matter what the implementer does, and the plan describes running
its tests against a throwaway database that this project does not actually have — the
tests run against the real development database.

Nothing here needs a decision from you. Sixteen issues are recorded for the
coordinator: four are blocking (they would let an implementer finish, pass every
listed check, and still ship a schema nobody has verified), and the rest are wording
that two implementers would read two different ways. No code, plan, or intention text
was touched.

---

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this projection needs the owner. Every finding is a plan, registry, or
criteria defect routed through the coordinator; none changes a product semantic.

---

## Decision ledger

| # | Decision the artifacts do not determine | Class | Severity | Proposed routing |
|---|---|---|---|---|
| D1 | What the money/rate CHECK constraints on `production_cost_basis_versions` are actually called — three §6.2-pattern names exceed PostgreSQL's 63-byte identifier limit and one pair collides after truncation | registry gap (master plan §6.2) | **BLOCKING** | amend master plan §6.2 with explicit shortened names |
| D2 | The closed list of §6.2 constraint names — §6.2 gives money/rate CHECKs as a *pattern*, and names no constraint for the two upper bounds (`planning_utilization_percent ≤ 100`, `percent_value ≤ 999.999`) | registry gap | **BLOCKING** | amend master plan §6.2 to a closed, enumerated name table |
| D3 | How PG-enum-type ownership is actually enforced and tested — C5's metadata-create cannot fail; the decidable site is the migration, and the plan does not say what `upgrade` must not create nor what `downgrade` must not drop | plan gap | **BLOCKING** | amend plan task 3 + replace C5 |
| D4 | Which database C1–C5 run against — the plan says "a migrated disposable database"; no such harness exists in `tests/`, and there is no documented way to make one | plan gap + environment gap (master plan §10) | **BLOCKING** | amend criteria preamble; add the disposable-DB recipe to master plan §10 |
| D5 | Whether `production_cost_group_sections` and `item_valuations` carry the soft-delete trio and `updated_at`/`updated_by_id` — task 2's blanket rule contradicts intention §4.2 and INV-V2, and changes one index predicate | plan gap (plan vs intention) | HIGH | plan amendment (task 2), intention wins |
| D6 | The column set of `item_cost_evaluation_terms` — `value` is dead (A3), `workspace_id` is required by `24_multi_tenancy` and absent from §4.5, audit/soft-delete shape unstated | intention gap + contract conflict | HIGH | amend intention §4.5 (lettered) or pin in master plan §6.1 |
| D7 | The names of the three `use_alter=True` self-FKs, and whether the migration carries them at all — autogenerate omits them (repo precedent `243e62bcd858`), no criterion checks FKs, and `promoted_from_id` is unmentioned | plan gap + registry gap | HIGH | amend plan task 2/3 + master plan §6.2 (FK names) |
| D8 | Whether C2's (b) column proves each index predicate — the predicates carry 1–3 clauses each and the plan gives one (b) row per index; `uix_cost_model_terms_name_active` has no row that bites on its predicate at all | plan gap (charter rule 2 companion) | HIGH | plan amendment (C2 table: one (b) row per predicate clause) |
| D9 | The full case table for `ck_cost_model_terms_value_by_type` — 3 types × 4 column-presence combinations is 12 rows (3 accept, 9 reject); the plan names 5 reject labels, two of which overlap | plan gap (charter rule 2) | MEDIUM-HIGH | plan amendment (C3 term bullet → 12-row table) |
| D10 | Criteria for the money CHECKs §6.2 requires but C3 omits: `item_cost_evaluations.expected_sale_price_minor` / `purchase_cost_minor`, `cost_model_terms.fixed_amount_minor`, `item_cost_results.actual_worker_seconds` | plan gap (coverage) | MEDIUM | plan amendment (C3 rows) |
| D11 | How `downgrade` is proven — C1's in-suite proxy asserts existence at head only and cannot fail on a broken `downgrade`; charter rule 1's exemption requires an automated proxy | plan gap | MEDIUM | plan amendment (C1) |
| D12 | The exact expected outcome of C3's `percent_value = 1000` row — Numeric(6,3) raises `NumericValueOutOfRangeError` (a DataError), not a CHECK violation | plan gap (decidability) | MEDIUM | plan amendment (C3 row: name the exception class) |
| D13 | Whether `task_state_snapshot` gets a CHECK narrowing it to the five boundary states named in §4.6's parenthetical | plan gap | LOW-MED | plan amendment (task 2, stated the way A8 is stated) |
| D14 | On what authority `effective_from` / `effective_to` deviate from `21_naming_conventions` — §6.1's cited precedent (`issue_category_configs`) was dropped from the schema and used `DateTime`, not `Date` | reality-check defect (master plan §6.1) | LOW | correct §6.1's justification; the decision itself stands |
| D15 | Flush vs commit for constraint tests, and how ~30 reject-cases survive session poisoning | free choice | LOW | explicit delegation (below) |
| D16 | Import placement in `models/__init__.py`, `is_deleted` indexing, and whether `models/tables/README.md` gains the nine tables now or in phase 9 | free choice | LOW | explicit delegation (below) |

---

## Findings

### D1 — BLOCKING. Three §6.2 constraint names are longer than PostgreSQL allows

**Confirmed empirically against the configured database (PostgreSQL 18.4,
`max_identifier_length = 63`), 2026-08-12.** Master plan §6.2 specifies money/rate
CHECKs as `ck_<table>_<column>_positive` / `_non_negative`. Applied to
`production_cost_basis_versions` (30 characters of table name alone):

| Name §6.2 produces | Bytes | Stored `pg_constraint.conname` |
|---|---|---|
| `ck_production_cost_basis_versions_fixed_monthly_cost_minor_positive` | 67 | `…_fixed_monthly_cost_minor_posi` (truncated) |
| `ck_production_cost_basis_versions_cost_per_worker_minute_minor_positive` | 71 | `…_cost_per_worker_minute_minor_` (truncated) |
| `ck_production_cost_basis_versions_planning_utilization_percent_positive` | 71 | `ck_production_cost_basis_versions_planning_utilization_percent_` |
| `ck_production_cost_basis_versions_monthly_paid_hours_positive` | 61 | exact (fits, with 2 bytes to spare) |

Verified by creating the 71-byte constraint on a scratch schema and reading
`pg_constraint`: PostgreSQL truncates with a NOTICE and returns success, so the
implementer sees nothing wrong.

**Two consequences:**

1. **C1 fails.** C1 asserts "every §6.2-named constraint is present (query
   `pg_constraint`/`pg_indexes` by exact name)". For these three the exact name is not
   what is stored, so the test reddens on a correct schema — and the implementer's
   likeliest repair is to shorten the name on the spot, which master plan §6 forbids
   ("a session needing an unlisted name routes it back to the coordinator rather than
   inventing one"). The gate as designed therefore produces either a false red or a
   registry violation.
2. **A collision, not just a mismatch.** `planning_utilization_percent` needs two
   bounds (§4.3: `> 0 AND ≤ 100`). If they are written as two constraints, both
   truncate to the identical 63 bytes `ck_production_cost_basis_versions_planning_utilization_percent_`
   and the second `CREATE` fails outright. §6.2's pattern has no name for an upper
   bound at all (see D2), so this is undetectable from the artifacts.

All other generated identifiers were checked and fit: the longest FK
(`production_cost_group_sections_production_cost_group_id_fkey`, 60), the longest
implicit index (`ix_production_cost_group_sections_production_cost_group_id`, 58),
all nine `uix_`/`uq_` names (27–41), both window CHECKs (39, 50), and all five new PG
enum type names (28–43).

**Routing:** master plan §6.2 amendment. The registry, not the implementer, must
choose the shortened names, and it should choose them for the whole
`production_cost_basis_versions` family at once (all four columns) so the abbreviation
is consistent rather than applied only where it overflowed.

---

### D2 — BLOCKING. §6.2 is a pattern, not a list, so C1 is unwritable

C1 requires asserting "every §6.2-named constraint is present … by exact name". §6.2's
last four rows are not names:

- `ck_<table>_<column>_positive` / `_non_negative` **per §4/§4A** — the implementer
  must derive the table×column set from the intention, and the answer is not obvious
  (see D10: at least four columns that §6.2 covers have no C3 row, so nothing else in
  the plan pins the set either).
- No name is given for **`planning_utilization_percent ≤ 100`** (§4.3) or for
  **`percent_value ≤ 999.999`** (§6A.4). Both are required bounds with C3 rows
  (`100.01 reject`, `1000 reject`) and neither has a registry name.

An implementer cannot write C1's assertion list, and §6 forbids inventing the missing
names. Note also that `percent_value ≤ 999.999` may not need a CHECK at all —
`Numeric(6,3)` already caps the value at 999.999 (D12) — which is itself a decision the
registry should make rather than leave to the implementer.

**Routing:** replace §6.2's four pattern rows with an enumerated name table covering
every constraint this phase creates. Doing that surfaces D1 mechanically.

---

### D3 — BLOCKING. C5 cannot fail, and the migration's enum ownership is undetermined

This is the phase's flagged silent-failure mechanism (tracker row for phase 2,
depth target 2), and nothing in the plan tests it.

**C5 as written proves nothing.** "Metadata create on a fresh disposable schema
succeeds with the snapshot columns reusing `business_task_type_enum` /
`task_return_source_enum` (`create_type=False`)". Two independent reasons it cannot
redden, both verified in this workspace:

1. **`create_type` is silently discarded by `sa.Enum`.** The repo's `SAEnum` is
   `sqlalchemy.Enum` (`models/tables/tasks/task.py:6,30`). On SQLAlchemy 2.0.40,
   `sa.Enum(..., create_type=False)` accepts the keyword, stores nothing, and its
   PostgreSQL dialect implementation reports `create_type = True`:
   ```
   >>> e = sa.Enum('a','b', name='foo', create_type=False)
   >>> getattr(e, 'create_type', 'ABSENT')          -> ABSENT
   >>> e.dialect_impl(postgresql.dialect()).create_type -> True
   ```
   Every `create_type=False` in the model layer (21 occurrences, e.g.
   `step_state_record.py:40`, `sku_template.py:23`, `item_upholstery_requirement.py:44`)
   is therefore documentation, not behaviour. The real enforcement lives in the
   migrations, where `postgresql.ENUM(..., create_type=False)` is used (15 files).
2. **Even with `create_type=True`, metadata-create succeeds.** Within one `MetaData`,
   SQLAlchemy emits `CREATE TYPE` once per type *name*. Compiled against the
   PostgreSQL dialect with two tables declaring the same enum name — one
   `create_type=True`, one `False` — the DDL contains exactly one `CREATE TYPE`.

So C5 passes identically whether ownership stayed put or not. It is decoration with a
correct name (charter rule 11).

**Where the mechanism actually bites — and what the plan must determine.** Alembic's
`create_table` dispatches schema-type creation with `checkfirst=False`. The migration
therefore has three distinct enum populations and the plan's task 3 ("enum
create/reuse flags") does not distinguish them:

| Population | Types | `upgrade` must | `downgrade` must |
|---|---|---|---|
| new, this phase owns | `cost_model_term_calculation_type_enum`, `item_cost_evaluation_kind_enum`, and the three per-table currency types | create (autogenerate's inline `sa.Enum(...)` does this) | drop them explicitly — `op.drop_table` does **not** drop types (exemplar `677ed7131bb2:271-277`) |
| reused, owned by `tasks` | `business_task_type_enum` (`task.py:41`), `task_return_source_enum` (`task.py:58-60`), `task_state_enum` (`task.py:50-55`) | **not** create — inline `sa.Enum` here raises `DuplicateObject` against a DB at head; must be hand-fixed to `postgresql.ENUM(..., create_type=False)` (exemplar `261971b16234:25-28`) | **not** drop — `DROP TYPE task_state_enum` fails on `tasks.state`'s dependency, breaking the round-trip |
| reused elsewhere | none in this phase | — | — |

The R2-1 ownership rule "cuts both ways" exactly here, and the plan says it only for
`upgrade`.

**Proposed replacement for C5** (decidable, and it bites): after `alembic upgrade
head`, assert `pg_type.oid` for the three reused types is unchanged from before the
migration (or equivalently, that `pg_depend` still ties each to its `tasks` column),
and that the five new types exist. Named mutation: "changing any of the three reused
columns to `postgresql.ENUM(..., create_type=True)` must make `upgrade` fail on a DB
at head" and "adding a `.drop()` for `task_state_enum` to `downgrade` must make the
round-trip fail". Both are real failures, not assertions about them.

---

### D4 — BLOCKING. There is no disposable-database harness

The criteria preamble states: "DB-level tests run against a migrated disposable
database with production ORM instances (charter rule 3); the configured DB is left at
head (rule 7)." The first clause is false about this repo.

Verified in the tree:
- `tests/conftest.py` creates no schema. Its autouse fixture calls `init_db()`
  (`models/database.py:21-48`), which binds an engine to `settings.database_url` and
  nothing else. `db_session` yields from `get_db()` and rolls back.
- `grep -rn "create_all|alembic|CREATE DATABASE" tests/` returns zero schema-creation
  hits across the whole test tree.
- With no `APP_ENV` set (the master plan §10 command `PYTHONPATH=. pytest -m 'not e2e'`
  sets none), `config.py:9-16` resolves `.env`, whose `DATABASE_URL` is
  `…@localhost:5433/beyo_manager` — the **same development database** `make db-migrate`
  leaves at head (currently revision `7758ea23764e`).

Consequences the implementer must resolve and the plan does not:

1. **C2/C3/C4 run against the configured development database.** That is workable — the
   migration has been applied, so the constraints are real — but it makes charter rule
   11½ (teardown) load-bearing, and it contradicts the preamble's own sentence.
2. **C1's manual round-trip and C5 have no environment.** Master plan §10 documents
   `make db-create` / `make db-migrate` / `make reset-db`, all of which target
   `settings.database_url`. Nothing documents creating a throwaway database, and rule 7
   forbids running a destructive `downgrade` against the configured one. An implementer
   under time pressure will either skip the round-trip or run it against the real DB.

**Routing:** amend the criteria preamble to say which DB each of C1–C5 runs against,
and add to master plan §10 the exact recipe for a disposable database (e.g. a second
`DATABASE_URL` pointed at `beyo_manager_migrationtest`, created with `scripts/create_db`
and dropped afterwards) — the environment section exists so sessions do not
rediscover this.

---

### D5 — HIGH. "Soft-delete trio everywhere except `ItemCostResult`" contradicts the intention twice

Plan task 2 states the trio applies to eight of the nine tables. Intention §4 does not
agree for two of them:

- **`production_cost_group_sections` (§4.2)** lists exactly `client_id`,
  `workspace_id`, `production_cost_group_id`, `working_section_id`, `added_at` /
  `added_by_id`, `removed_at` / `removed_by_id` — an interval, explicitly citing the
  `working_section_membership.py` idiom. That model (verified,
  `working_section_membership.py:27-47`) has **no** `is_deleted` / `deleted_at` /
  `deleted_by_id` and **no** `created_at`; its partial unique is
  `postgresql_where=text("removed_at IS NULL")`. The sibling `task_items` table follows
  the same shape. INV-G1's predicate in §4.2 is likewise `WHERE removed_at IS NULL`
  alone. Adding the trio changes `uix_production_cost_group_sections_active`'s predicate
  and adds a second, redundant way to deactivate a membership — which is precisely the
  ambiguity INV-G1 exists to remove.
- **`item_valuations` (§4.7A)** lists `created_at` / `created_by_id` and the soft-delete
  trio, and INV-V2 states "rows never change after creation". Task 2's blanket "inline
  tz-aware audit + `created_by_id`/`updated_by_id`" adds `updated_at`/`updated_by_id`
  to a table the intention declares immutable.

Task 2 also says "inline tz-aware audit + `created_by_id`/`updated_by_id`" for
`item_cost_evaluation_terms`, which §4.5 declares immutable and written only by the
calculator.

**Routing:** plan amendment. The intention is the semantic authority (master plan §2)
and already answers all three; the plan's blanket sentence should become a per-table
column-shape table, or defer explicitly to §4/§4.7A.

---

### D6 — HIGH. `item_cost_evaluation_terms`' column set is not determined by any artifact

Three artifacts describe this table and no two agree:

- **§4.5's sub-section** names `evaluation_id` FK + index, `name`, `calculation_type`,
  `value`, `amount_minor`. `value` was **replaced** by A3 (`percent_value` /
  `fixed_amount_minor`) — §4.5's sub-section was never amended, so a literal reading of
  task 2 ("nine models exactly per intention §4/§4.7A as amended by §4A") produces a
  dead column. §4A's table amends "§4.4 `CostModelTerm.value`", not the snapshot table.
- **§6A.11's closed set** is the authoritative list for the snapshot row: `name`,
  `calculation_type`, `percent_value`, `fixed_amount_minor`, `amount_minor`. This is
  the reading the plan intends, but the plan never cites §6A.11 (its Read-first list
  stops at §4A, §4.7A, §4.8, §7A intro, §2.5).
- **`24_multi_tenancy:399` ("Every domain table has `workspace_id`")** conflicts with
  both: §4.5's sub-section omits `workspace_id`, and master plan §6.1 says "Column
  names exactly as intention §4/§4A". The table has a registered prefix (`icet`) so it
  is an addressable domain table.

Unstated as well: whether it carries `created_at`/`created_by_id`, and whether it
carries the soft-delete trio (§4.5 says the rows are immutable; A6's "house-style
shape only" rationale is stated for `cost_model_terms`, not for this table).

**Routing:** the home artifact is the intention (§4.5's sub-section) — a lettered
amendment pinning the column set against §6A.11 and `24_multi_tenancy`. Add §6A.11 to
the plan's Read-first list either way.

---

### D7 — HIGH. The `use_alter` self-FKs are unnamed, probably absent from the migration, and untested

Plan task 2: "self-FKs (`superseded_by_id`, both chains) with `use_alter=True`".

1. **There are three, not two.** §4.5 gives `ItemCostEvaluation` both
   `superseded_by_id` **and** `promoted_from_id` (FK self, nullable); §4.7A gives
   `ItemValuation.superseded_by_id`. The plan mentions only `superseded_by_id`, leaving
   `promoted_from_id`'s treatment undetermined.
2. **They need names and the registry has none.** Every `use_alter` FK in this repo is
   explicitly named `fk_<table>_<column>` (`image.py:57`,
   `243e62bcd858:21-25`, `7d92a90e6282:42`). §6.2 names no foreign key. Unnamed,
   PostgreSQL assigns `<table>_<column>_fkey`, and `downgrade`'s `op.drop_constraint`
   has nothing stable to target.
3. **Autogenerate is known to drop them in this repo.** Migration
   `243e62bcd858_add_missing_circular_fks.py` exists for exactly this: five
   `use_alter=True` FKs were omitted from the original table creation and had to be
   added by hand afterwards. The same failure here loses the supersession back-links
   silently — and **no phase-2 criterion would notice**, because C1 checks only
   §6.2-named constraints (which contain no FK) and C2 checks indexes.
4. **`use_alter=True` is arguably wrong here anyway.** A self-referential FK creates no
   table-ordering cycle; PostgreSQL accepts it inline in `CREATE TABLE`. §2.5's
   convention cites `use_alter=True` for "current-child pointers" — a *circular*
   two-table pattern. Whether these three follow the convention or the simpler inline
   form is a real decision that changes both the model and the migration.

**Routing:** plan amendment (task 2 and task 3) plus master plan §6.2 FK names, and one
C1 row asserting the three FKs exist in `pg_constraint` by name.

---

### D8 — HIGH. C2's (b) column tests one predicate clause per index, not all of them

C2's header promises "second row's predicate is the only differing fact — rule 2
companion". The predicates carry between one and three clauses, and one (b) row can
only exonerate one clause. Enumerated against §7A's chain table and §4:

| Index | Predicate clauses | (b) rows required | (b) rows the plan gives |
|---|---|---|---|
| `uix_production_cost_groups_name_active` | `is_deleted = false` | 1 | 1 ✓ |
| `uix_production_cost_group_sections_active` | `removed_at IS NULL` (+`is_deleted` iff D5 resolves that way) | 1–2 | 1 |
| `uix_production_cost_basis_versions_open` | `effective_to IS NULL`, `is_deleted = false` | 2 | 1 |
| `uix_cost_model_versions_open` | `effective_to IS NULL`, `is_deleted = false` | 2 | 1 |
| `uix_cost_model_terms_purchase_cost` | `calculation_type = 'item_purchase_cost'`, `is_deleted = false` | 2 | 1 |
| `uix_cost_model_terms_name_active` | `is_deleted = false` | 1 | **0** |
| `uix_item_cost_evaluations_current` | `kind = 'committed'`, `superseded_at IS NULL`, `is_deleted = false` | 3 | 2 (packed into one cell) |
| `uix_item_valuations_current` | `superseded_at IS NULL`, `is_deleted = false` | 2 | 1 |
| `uq_item_cost_results_task_id` | none (plain unique) | 0 | n/a ✓ |
| **Total** | | **14–15** | **9** |

Two specifics worth calling out:

- **`uix_cost_model_terms_name_active` has zero rows that bite on its predicate.** Its
  (b) cell is "second on another version" — that varies a *key column*, not the
  predicate. Delete `postgresql_where` entirely and both (a) and (b) stay green. Same
  structural error as `uq_item_cost_results_task_id`'s "second for another task",
  which is correct there only because that index has no predicate.
- **The INV-E1 (b) cell packs two independent accept-reasons** ("second has
  `superseded_at` (and a `projection` third row is also accepted)"). Rule 2's companion
  clause — each row's fixture makes its own predicate the *only* reason the outcome
  holds — needs these as two rows, since the fixture as described satisfies two
  sufficient causes at once.

Per master plan P-G(a), the expanded (b) rows should carry their named mutation
("dropping the `is_deleted = false` clause from index X must redden row X-b2"), so the
near-identical rows cannot later be dismissed as redundant.

**Routing:** plan amendment (C2 table).

---

### D9 — MEDIUM-HIGH. The term-type CHECK case table is sampled, not enumerated

C3's bullet: "the 3 valid combinations accept; each of the 5 invalid combinations
rejects (percentage+fixed set, percentage+NULL percent, fixed+percent set, fixed+NULL
fixed, purchase+either set)".

The domain is 3 `calculation_type` values × 2 (`percent_value` NULL/NOT NULL) × 2
(`fixed_amount_minor` NULL/NOT NULL) = **12 combinations**: 3 valid per §6A.4's table,
**9 invalid**. The plan's five labels cover those nine unevenly:

| type | percent | fixed | §6A.4 | covered by which label |
|---|---|---|---|---|
| percentage | NOT NULL | NULL | **valid** | — |
| percentage | NOT NULL | NOT NULL | invalid | "percentage+fixed set" |
| percentage | NULL | NULL | invalid | "percentage+NULL percent" |
| percentage | NULL | NOT NULL | invalid | **ambiguous** — matches both labels |
| fixed_amount | NULL | NOT NULL | **valid** | — |
| fixed_amount | NOT NULL | NOT NULL | invalid | "fixed+percent set" |
| fixed_amount | NULL | NULL | invalid | "fixed+NULL fixed" |
| fixed_amount | NOT NULL | NULL | invalid | **ambiguous** — matches both labels |
| item_purchase_cost | NULL | NULL | **valid** | — |
| item_purchase_cost | NOT NULL | NULL | invalid | "purchase+either set" |
| item_purchase_cost | NULL | NOT NULL | invalid | "purchase+either set" |
| item_purchase_cost | NOT NULL | NOT NULL | invalid | "purchase+either set" |

The CHECK expression itself **is** fully determined by §6A.4 (depth target 4's first
half passes). What is not determined is the criterion: two honest implementers write
either 8 rows or 12, and only the 12-row form is total.

**Routing:** plan amendment — replace the bullet with the 12-row table above.

---

### D10 — MEDIUM. Four columns §6.2 requires a CHECK on have no C3 row

C3 enumerates boundaries for `fixed_monthly_cost_minor`, `cost_per_worker_minute_minor`,
`monthly_paid_hours`, `planning_utilization_percent`, `percent_value`, the term-type
CHECK, the valuation amounts, and the window CHECKs. §6.2's money-CHECK family also
covers, per §4/§4A:

- `item_cost_evaluations.expected_sale_price_minor` — §4.5 "Integer, ≥ 0"
- `item_cost_evaluations.purchase_cost_minor` — §4.5 "Integer, ≥ 0, nullable"
- `cost_model_terms.fixed_amount_minor` — §6A.4 "NOT NULL, ≥ 0"
- `item_cost_results.actual_worker_seconds` — §4.6 "Integer ≥ 0"

Nothing in the plan asserts these constraints exist or work; nothing lists them either
(D2). The `item_cost_evaluations` pair is the one that matters most, because C4 exists
to prove that the *other* two columns on that same table deliberately carry **no**
CHECK (A8) — a reviewer reading C4 alongside a table with no money CHECKs at all
cannot tell deliberate absence from omission.

**Routing:** plan amendment (C3 rows: −1 reject / 0 accept per column, and for the
nullable one, NULL accept).

---

### D11 — MEDIUM. `downgrade` has no automated proxy

Charter rule 1's exemption: environment-lifecycle checks may be manual but "need an
automated proxy in the suite". C1 pairs the manual `upgrade → downgrade → upgrade`
round-trip with "a test importing all nine models and asserting their tables + PG enum
types exist in the test schema and every §6.2-named constraint is present".

That proxy asserts the state of a database **at head**. It is green whether `downgrade`
is correct, empty, or absent. The plan's task 3 ("Upgrade + downgrade both complete")
therefore ships on the manual run alone — and the manual run has no environment (D4).

Given D3's finding that `downgrade`'s enum handling is the reversibility hazard here
(dropping `task_state_enum` breaks `tasks`), this is the one criterion whose absence
costs the most.

**Routing:** plan amendment — either an in-suite test that runs `downgrade` +
`upgrade` against the disposable DB from D4, or a static assertion over the migration
module (the set of types `downgrade` drops equals the five new types, and excludes the
three reused ones). The static form is cheap and bites on the exact defect.

---

### D12 — MEDIUM. C3's `percent_value = 1000` row has two possible outcomes

**Confirmed on PostgreSQL 18.4** against `numeric(6,3)` with a `>= 0` CHECK:

| value | outcome |
|---|---|
| −0.001 | `CheckViolationError` (an `IntegrityError`) |
| 0 | accepted |
| 999.999 | accepted |
| **1000** | **`NumericValueOutOfRangeError`: numeric field overflow** — a `DataError`, not an `IntegrityError` |

`Numeric(6,3)` (A3) cannot represent 1000 at all, so the type rejects it before any
CHECK is consulted. One implementer writes `pytest.raises(IntegrityError)` and gets a
red test on correct code; another writes `pytest.raises(DBAPIError)` and gets a green
test that would also pass with no CHECK at all.

This also answers a registry question raised in D2: an upper-bound CHECK on
`percent_value` is redundant with the column type. Whether to declare one anyway (for
explicitness, matching §6A.4's prose) is a registry decision, not an implementer's.

**Routing:** plan amendment — name the exact exception class per row, and state
whether the upper bound is a CHECK or a type guarantee.

---

### D13 — LOW-MEDIUM. `task_state_snapshot`'s value domain is stated two ways

§4.6 as amended (round 6) describes the column as "the lifecycle boundary the row was
last computed at (working | ready | resolved | failed | cancelled)" — five of
`TaskStateEnum`'s eight members (`domain/tasks/enums.py:17-25`: pending, assigned,
working, stalled, ready, resolved, failed, cancelled). §8B.2's handler admission is
total over all eight.

The reused PG type carries all eight values, so the parenthetical is a statement about
which values the handler will ever write, not a schema constraint — but nothing says
so, and §6.2 names no such CHECK. An implementer reading the parenthetical as a
requirement adds a five-value CHECK that phase 8 then has to fight, or a reviewer later
"fixes" its absence.

This is the same failure mode A8 was written to prevent, and the fix is the same shape:
state the absence deliberately.

**Routing:** plan amendment (task 2), one line: no CHECK narrows `task_state_snapshot`;
admission is the handler's job per §8B.2.

---

### D14 — LOW. §6.1's justification for the date-column naming deviation cites a dropped table

Master plan §6.1: "Temporal columns `effective_from`/`effective_to` (Date) follow the
repo's effective-dating precedent (`issue_category_configs`, sibling compensation) — a
deliberate, recorded deviation from `21`'s `<context>_date` suffix guidance."

Verified in the tree:

- `issue_category_configs` was **dropped** by `99accdeba8b9_issue_system_rework.py`
  (in `upgrade()`, line 84). It survives only in that migration's `downgrade()` and in
  three stale READMEs.
- The other effective-dated table, `upholstery_inventory_threshold_policies`, was
  dropped by `a61def0ca46f` (`upgrade()`, line 31).
- No model file in `beyo_manager/models/` contains `effective_from` today.
- Both dropped tables used `DateTime(timezone=True)`, not `Date`
  (`7d92a90e6282:265,439`).

The decision itself is right — §7A.3's resolution predicate is a calendar-date
comparison and `Date` is the correct type — but the recorded justification is false in
both halves, and an implementer who greps for the precedent finds nothing. Worth
correcting because §6.1 is the artifact a later phase will cite when asked why the
naming convention was broken.

Positively verified alongside it: the `ck_<table>_effective_window` name idiom is real
(`7d92a90e6282:276,450`), and both names §6.2 derives from it fit the byte limit.

**Routing:** master plan §6.1 — replace the citation with the honest one (the sibling
compensation intention plus §7A.3's semantics), or drop the appeal to precedent.

---

## Reality checks

### Paths and citations in the plan — verified

| Claim | Result |
|---|---|
| `app/beyo_manager/models/tables/item_economics/` | absent — correctly a new package (plan does not mark it new; `__init__.py` is the house convention, all sibling ones are empty) |
| `app/beyo_manager/domain/item_economics/` | absent — correctly new |
| `models/__init__.py` registration point | exists, 164 lines, explicit ordering comments |
| `models/tables/client_id_prefix_map.md` | exists |
| `migrations/versions/` partial-unique idiom `595e7b840926:44,50` | verified — `postgresql_where=sa.text(...)` on both `create_index` (:44) and `drop_index` (:50) |
| journaled exemplar `97b60e06d42a` | exists (phase 6's, correctly out of scope here) |
| `configure_sa_enum_values` | `models/base/sa_enum.py:8` |
| `IdentityMixin` prefixes | `models/base/identity.py:14-29` |
| `uix_` / `ck_` repo idiom (§6.2 preamble) | verified — `working_section.py:50-57`, `task_step.py:130-139`, `upholstery_inventory.py:92-98` |
| enum PG-type ownership on `tasks` | `business_task_type_enum` `task.py:41`, `task_state_enum` `task.py:50-55` (§6.3 cites `task.py:52` — inside that `mapped_column`), `task_return_source_enum` `task.py:58-60` — all `create_type=True` |
| `ItemCurrencyEnum` members | `domain/items/enums.py:11-14` — exactly `swedish_krona`, `danish_krona`, `euro`; matches §4.3/§4.7A |
| §2.5 enum type-name convention `<singular>_<column>_enum` | all five new type names conform |
| all nine `client_id` prefixes free | verified two ways — 95 `CLIENT_ID_PREFIX` literals in `models/` (no duplicates, no collision with the nine) and `client_id_prefix_map.md`; `cmt` → `ContentMention` collision confirmed, so `cmvt` is required |
| identifier lengths (FKs, PKs, `ix_`, `uix_`, enum types) | all ≤ 60 bytes — see D1 for the three that are not |
| `migrations/env.py` `_journal` filter | `env.py:30-48`, wired into both offline and online paths — phase 6's `item_valuation_migration_journal` is protected; correctly not this phase's concern |
| alembic environment | head `7758ea23764e`, 113 revisions, linear; `transaction_per_migration=True` (`env.py:72`); no `compare_type` (irrelevant for new tables) |
| database reachable | PostgreSQL 18.4 at `127.0.0.1:5433`, containers healthy 44h — connectivity real, no connection noise (master plan §10 rule satisfied) |

### Criteria decidability, criterion by criterion

| Criterion | Could a test be written now, one exact outcome per case? |
|---|---|
| **C1** manual round-trip | **No** — no disposable-DB environment (D4) |
| **C1** in-suite proxy, tables + enum types | Yes |
| **C1** in-suite proxy, "every §6.2-named constraint by exact name" | **No** — the name list is not enumerable (D2) and three of the derivable names do not survive PostgreSQL (D1) |
| **C2** (a) column, 9 rows | Yes |
| **C2** (b) column | **Partly** — 9 rows where 14–15 clauses need exonerating; one index has no biting row (D8) |
| **C3** `fixed_monthly_cost_minor`, `cost_per_worker_minute_minor`, `monthly_paid_hours`, `planning_utilization_percent` | Yes — all boundary values representable in their declared types (`Numeric(5,2)` holds 100.01; `Numeric(8,2)` holds 0.01; `Numeric(12,4)` holds 0.0001) |
| **C3** `percent_value` | −0.001 / 0 / 999.999 yes; **1000 no** (D12) |
| **C3** term type×columns | **No** — 5 labels over 9 invalid combinations, two ambiguous (D9) |
| **C3** valuation rows | Mostly — "one amount + currency accept" does not say which amount, so the row does not isolate its own predicate |
| **C3** window CHECK | **Partly** — "either side NULL accept" is two cases stated as one; "both config chains" doubles every row and the plan does not say so explicitly |
| **C4** A8 proof | Yes, and it carries its named mutation ("adding any CHECK there turns this row red"). Note the fixture cost: `ItemCostEvaluation` has ~8 NOT NULL FKs, so this single row needs workspace + item + task + group + basis version + model version. Task 5's factories should be enumerated against it |
| **C5** enum reuse | **No** — cannot fail as written (D3) |

### Depth-target results

1. **Registry ↔ DDL conformance** — nine prefixes, nine table names, nine `uix_`/`uq_`
   names, two window CHECKs and five enum type names all check out and are
   collision-free. The money/rate CHECK family does not (D1, D2).
2. **PG enum type ownership** — simulated on paper and in SQLAlchemy: the model-layer
   `create_type` flag is inert; the migration is the only site where ownership is real;
   `downgrade` is the untested half (D3).
3. **Round-6 result columns** — the plan carries all four facts (`task_state_snapshot`
   NOT NULL enum copy, `task_closed_at` nullable, `unique(task_id)`, `created_at` only).
   Two gaps: no criterion asserts any of them (C1 checks constraint *names*, and
   `uq_item_cost_results_task_id` is the only one of the four that is a named
   constraint), and the value domain is stated two ways (D13). A7's
   `calculation_version` on this table is also carried only by the blanket "as amended
   by §4A" reference.
4. **CHECK totality** — the term-type CHECK expression is fully determined by §6A.4;
   its criterion is not (D9). Window CHECKs determined; money CHECKs incompletely
   covered (D10) and partly unnameable (D2). The A1 `> 0` vs `≥ 0` distinction is
   correctly carried (C3's "0 reject (A1)").
5. **Migration reversibility** — not decidable from the plan (D11); the journal table is
   explicitly and correctly out of scope (plan Goal + master plan §6.1).
6. **Criteria decidability & first-hour reality** — table above. P-G applied: C2's
   mirrored rows are structurally sound (each (b) row bites on its own predicate
   clause where one exists) but are not *named* as separately required and carry no
   named mutations; D8 expands them.

---

## Explicit delegation list (freedom granted on purpose)

These are free choices with no artifact answer and no downstream consequence. Recording
them so the implementer's freedom is granted rather than taken.

1. **Flush vs commit in the constraint tests.** Both partial uniques and CHECKs fire at
   `flush()`, and `tests/conftest.py`'s `db_session` rolls back at teardown — so a
   flush-only design needs no cleanup at all and satisfies charter rule 11½ by
   construction. *Recommended.* Note that the nearest repo exemplar,
   `tests/integration/models/shopify/test_shopify_foundation_constraints.py`, commits
   and never deletes what it committed — a live rule-11½ violation that should not be
   copied.
2. **How reject-cases survive session poisoning.** After an `IntegrityError` the session
   is unusable; `session.begin_nested()` per case, or one test function per case
   (parametrized), are both acceptable. If parametrized, master plan P-G(b) applies —
   name the constraint in the test id, not one example value.
3. **Placement of the nine imports in `models/__init__.py`.** Must land after
   `tables.tasks.task` (owner of all three reused enum types), after `tables.items.item`
   and `tables.working_sections.working_section` (FK targets), and after
   `tables.users.user` / `tables.workspaces.workspace`. Appending a
   `# --- Item economics ---` block at the end of the file satisfies all of these.
   *Recommended* — and the file's existing comment style should be matched, since import
   order is load-bearing here (`tables/tasks/README.md:106` documents the same
   constraint for `task_step` → `step_state_record`).
4. **Whether `is_deleted` carries `index=True`.** `25_soft_delete.md:25,34` says it
   should; `working_section.py:44` does not, `shopify_shop_integrations` does. Either is
   defensible; the choice must be uniform across the eight tables that have it, and it
   adds eight `ix_<table>_is_deleted` names (all within the byte limit).
5. **Whether `models/tables/README.md` gains the nine tables in this phase.** The plan's
   "Files expected to change" omits it. That file is already stale (it still documents
   the dropped `issue_category_configs`), and phase 9 owns the drift batch — so
   deferring is defensible. If deferred, say so in the plan's Notes so the phase-2
   reviewer does not file it.
6. **Test file placement.** `tests/integration/models/` currently has `shopify/` and
   `users/`; `tests/factories/` is empty (no existing factory to follow). A new
   `tests/integration/models/item_economics/` matches the layout.

---

## Session write perimeter

- **Documents written:** this handoff only —
  `handoffs/reviewer/2026-08-12_phase2_projection_r0_handoff.md`.
- **Code, plans, intention, master plan:** nothing. `git status` was clean at session
  start and no file under `app/` or `docs/` was modified.
- **Architecture graph:** read-only. `archgraph_status` (116 nodes / 157 edges,
  revision `b0702c3c…`, 0 stale, 244 pending, permissionMode `review` — matches master
  plan §3's planner-verified state) and `archgraph_get_node` on `table-task-item`. No
  `apply_changes`, no review adjudication, zero delta.
- **Database side effect (declared).** Two findings were confirmed empirically rather
  than reasoned, which required executing DDL: schema `proj_scratch` was created in the
  configured development database (`beyo_manager` @ 5433), used for the identifier-
  truncation test (D1) and the `numeric(6,3)` overflow test (D12), then dropped.
  Verified afterwards: the schema is absent, `alembic_version` is unchanged at
  `7758ea23764e`, and no object in `public` was touched. No migration was generated or
  applied.
- **Scratch/temp files:** none retained.
- **No skeleton appendix.** The paper derivation was discarded per doctrine; nothing in
  this handoff is guidance for the implementer, and the coordinator should not forward
  any of it as such.

---

## Verdict

**AMENDMENTS_REQUIRED.**

Four blocking rows (D1–D4) share one shape: the plan's verification layer does not
verify. An implementer can build all nine tables correctly, write every criterion the
plan lists, and still have (a) three constraints whose real names nobody knows, (b) no
enumerable list to check them against, (c) an enum-ownership test that passes on both
the right and the wrong implementation, and (d) two criteria with no environment to run
in. Conversely an implementer can get the enum ownership *wrong* and C1–C5 stay green
until `alembic upgrade head` fails in someone else's session.

D5–D8 are contradictions and omissions that two honest implementers would resolve two
ways, each producing a different schema. D9–D16 are criteria and delegation work.

Per the exit gate, every ledger row is routed — amendment applied, upstream change
made, or delegation recorded — before the phase-2 implementer prompt is compiled. Note
that D1, D2, D7 and D14 amend the **master plan** (registry and environment topology)
and D6 amends the **intention** (§4.5, lettered); the rest are phase-plan amendments.
The plan-projection gate is not self-retiring after this round (the ledger is not
empty).
