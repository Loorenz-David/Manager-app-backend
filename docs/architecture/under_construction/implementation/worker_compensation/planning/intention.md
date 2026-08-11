# Intention: Temporal Worker Compensation & Cost Model

```
status: resolved — awaiting owner decisions (4 cards, §16)
role: intention (pipeline root artifact)
shaped_from: raw_intention.md (this folder)
date: 2026-08-11
round: 0 (initial shaping)
```

---

## 1. Objective & hard constraints

Introduce a **compensation domain** that separates a worker's employment compensation from
their operational profile, preserves compensation history as effective-dated versions,
normalizes every contract payment model into a gross hourly basis, and exposes one stable
derived rate — `estimated_cost_per_hour` — as the single labor-cost input to analytics.

The analytics contract this must realize:

```
worker + point in time
        ↓  temporal resolution (§7)
applicable UserCompensation version
        ↓  persisted derived rate (§6)
estimated_cost_per_hour
        ↓  worked duration (existing concurrency-averaged seconds)
labor cost in total_cost_minor  (AggregateMetricsCostMixin tables + task_steps)
```

**Hard constraints:**

- **HC-1 — History never silently reprices.** Once a day's work is priced, its cost changes
  only through (a) a *contract change* affecting later work, or (b) an explicit *correction*
  with a mandated scoped reprice. Today's behavior — editing
  `salary_per_hour_before_tax` silently reprices any old day on its next reconcile — is the
  defect this domain exists to remove.
- **HC-2 — One canonical calculation path.** All derived compensation values
  (`gross_hourly_equivalent`, component hourly costs, `estimated_cost_per_hour`) are produced
  by one pure domain module. No API consumer may write them. The two existing duplicated
  `_rate`/`_cost_minor` implementations collapse onto it.
- **HC-3 — Replay-safety is preserved.** The analytics pipeline's idempotency scheme
  (recompute-and-SET on per-user tables, delta application on Σ tables —
  `app/beyo_manager/services/queries/analytics/reconcile_user_time.py:1-14`) must survive
  unchanged. Cost recomputation becomes a deterministic function of
  (step_state_records, compensation history), both append-only under normal operation.
- **HC-4 — Repo conventions are binding.** Contracts under `architecture/` govern how code is
  written (pattern-authority rule,
  `task_system/backend_contract_goal_mapping_guide.md:16-52`). This document uses the repo's
  real vocabulary and cites real paths; where it proposes names, the implementation
  planner's naming registry has final authority.
- **HC-5 — Gross, employer-side money only.** Stored contractual values are gross (bruttolön).
  Employee income-tax withholding is out of scope; `estimated_cost_per_hour` is an employer
  cost, not a net-pay figure.

---

## 2. Grounding — what exists today (verified 2026-08-11)

### 2.1 Current compensation storage

`UserWorkProfile` (`app/beyo_manager/models/tables/users/user_work_profile.py`, table
`user_work_profiles`, prefix `uwp`) carries:

- `salary_per_hour_before_tax`, `salary_per_hour_after_tax` — both `Numeric(12,4)`,
  nullable, CHECK `>= 0` (`:33-34`, `:59-66`). Schema unchanged since the founding migration
  `7d92a90e6282` (`:192-200`).
- `salary_per_hour_before_tax` is the **sole cost driver**. `salary_per_hour_after_tax` is
  **write-and-display only** — it is set by register/PATCH, echoed by serializers, and
  participates in zero computation anywhere.

**Correction to the raw draft:** the claim "none of them are surfaced to the frontend" is
**false**. Both columns are emitted as 4-decimal strings under `user.work_profile` by
`app/beyo_manager/domain/users/serializers.py:18-27,43-44`, reached by three endpoints:
`POST /api/v1/auth/register`, `PATCH /api/v1/users/{user_client_id}`,
`GET /api/v1/users/{user_client_id}`. An end-to-end shell test reads them from the response
(`tests/users/test_user_management.sh:236,250`). Write paths:
`register_user.py:113-114` (Decimal body fields, non-negative validator) and
`update_user_admin.py:83-86` (string body fields, key-presence gated, **no request-level
non-negative validator** — only the DB CHECK catches it). `PATCH` is open to
`ADMIN, MANAGER`; register to `ADMIN` only.

### 2.2 Current cost computation

Two near-duplicate implementations, both reading the **live** rate at recompute time:

- **Day/section grain** — `services/queries/analytics/reconcile_user_time.py`:
  `_rate` (`:164-173`) reads `salary_per_hour_before_tax` by `(user_id, workspace_id)`;
  `_cost_minor` (`:84-89`) computes
  `int(((Decimal(working_s + pause_s) / 3600) * rate * 100).to_integral_value())`
  → integer minor units (öre), ROUND_HALF_EVEN. Applied per day (`:304`) and per section
  slice (`:305-306`). SET on `user_daily_work_stats` / `user_section_daily_work_stats`;
  delta-applied to `user_lifetime_stats` / `working_section_daily_work_stats`.
- **Step grain** — `services/tasks/analytics/process_step_transition.py`:
  duplicate `_rate` (`:149-158`); per contributing user, seconds summed as float across the
  step's records, rounded once, priced at that user's rate, summed into
  `task_steps.total_cost_minor` (`:205,218-233`). Absolute SET.

Shared cost rules (inherited, preserved): only `working` + `paused` buckets are costed;
the derived `ended_shift` bucket never is; `marked_wrong` seconds are excluded (they feed
`inaccurate_*`); missing rate → cost `0` (not NULL). Duration comes from the
concurrency-averaged sweep over `step_state_records`
(`domain/analytics/concurrency.py:35-105`), attribution via
`COALESCE(credited_user_id, created_by_id)` (`averaged_time.py:102`).

Cost lands in `AggregateMetricsCostMixin.total_cost_minor`
(`models/base/aggregate_metrics.py:40-41`, `Integer`, nullable, **no currency column**) on
exactly five tables: the four analytics tables and `task_steps`. Today it is **read back by
exactly one surface**: `domain/tasks/serializers.py:176` (step grain). The four analytics
tables' cost is written but never read by any API.

### 2.3 Pipeline & recalculation infrastructure (reused, not rebuilt)

Transactional outbox (`ExecutionTask`+`ExecutionPayload`, `create_instant_task`) → Postgres
NOTIFY → `task_router` → Redis `queue:analytics` → `workers/analytics_worker.py` →
`handle_process_step_transition`. At-least-once delivery; idempotency is arithmetic
(recompute-and-SET / recompute-minus-stored deltas), no dedupe key. Offline rebuild
precedent: `app/scripts/backfill/backfill_averaged_time.py` (dry-run default, reuses the
production reconcile functions, requires a drained queue). Data-migration exemplar with
journal table, pre-flight refusal and post-condition counts:
`app/migrations/versions/97b60e06d42a_backfill_other_task_priority_transition_.py`;
`env.py:20-48` protects `*_journal` tables from autogenerate sweeps.

### 2.4 Conventions this domain must follow

- **Temporal:** no live effective-dated table exists. Dropped-table precedent
  (`7d92a90e6282:265-284`, `:439-460`) used `effective_from`/`effective_to` (nullable), a
  window CHECK, and unique on the `effective_from` start. The live "one open row" idiom is a
  **partial unique index** on the open predicate (four tables, e.g.
  `step_state_record.py:100-106`). No `ExcludeConstraint`/`btree_gist` anywhere.
- **Current-child pointer:** `use_alter=True` FK shortcut updated atomically with the new
  child (`user.py:41-60`, `task.py:96-106`, `task_step.py:110`).
- **Enums:** Python enum, lowercase values, `SAEnum` via `configure_sa_enum_values`
  (`models/base/sa_enum.py:5-11`), type name `<singular>_<column>_enum`, `create_type=True`
  on the introducing table. Constrained-String is the sanctioned alternative for code-owned
  vocabularies expected to grow (`step_state_record.py:52-64` rationale).
- **Money:** stored amounts = `Integer` minor units + per-table currency enum
  (`static_cost.py:24-27`); **rates** = `Numeric(12,4)` Decimal, no floats. Governing doc:
  `docs/architecture/under_construction/intention/planning_tables/isolated_tables/currency_governance_models.md`.
- **Models:** `IdentityMixin` `client_id` (`<prefix>_<ULID>`), inline
  `created_at/updated_at` (tz-aware), `created_by_id/updated_by_id` → `users.client_id`
  RESTRICT, soft-delete trio (`architecture/25_soft_delete.md`), `workspace_id` scoping from
  JWT (`architecture/24_multi_tenancy.md`), registration in `models/__init__.py`.
- **Services:** commands with `requests/` parse functions, `maybe_begin`, `run_service`
  boundary; pure calculation in `app/beyo_manager/domain/<domain>/`
  (`architecture/08_domain.md`); worker handlers `handle_<event>(raw, task_id)`.
- **Snapshot-on-use policy precedent:** `models/tables/static_costs/README.md:37-49` and
  `static_cost_models.md` §4 already mandate that historical consumers must not depend on
  mutable live rows — the exact reasoning this domain applies to compensation.

### 2.5 Documentation drift observed while grounding (for the coordinator to route)

- `architecture/01_architecture.md:140` describes a single stale `salary: Decimal` field.
- `models/tables/client_id_prefix_map.md:47` says `StaticCost | stc`; code says `scst`
  (`static_cost.py:16`).
- `architecture/30_migrations.md:66` claims date-prefixed migration filenames; the tree uses
  Alembic hex revisions.
- `models/tables/users/README.md:31,36` states an unimplemented rule "snapshot previous
  values before overwriting salary" — this intention supersedes it with real versioning.
- Ops caveat for the master plan's environment topology: the analytics worker is launched
  via `app/Makefile:57-58,82-85` but is absent from `app/Procfile` and
  `app/docker-compose.yml` — verify the production launch path before relying on it.

---

## 3. Core workflow

1. **Admin sets compensation.** At registration (initial hourly compensation, bridge — §9)
   or via the compensation API (§10): a `UserCompensation` version with contractual facts
   and zero-or-more components. The canonical calculator derives and persists
   `gross_hourly_equivalent`, per-component hourly costs, and `estimated_cost_per_hour` on
   the version at write time.
2. **Work happens.** Step transitions close `step_state_records` intervals and enqueue
   `PROCESS_STEP_TRANSITION` exactly as today. Nothing in the execution path changes.
3. **Analytics prices work.** The reconcile paths replace their live `_rate` lookup with
   temporal resolution: for each priced unit, the applicable version for
   `(user, work date)` supplies its persisted `estimated_cost_per_hour`. Same minor-unit
   conversion and rounding as today (§8).
4. **Compensation changes** create a new version effective from a date; the previous version
   closes at that date. Work before the boundary keeps its price (HC-1).
5. **Corrections** amend a version's facts in place, re-derive its persisted values through
   the canonical path, and trigger a scoped reprice of affected days (§7.3).

---

## 4. Domain model

New domain package: `compensation` — models under
`app/beyo_manager/models/tables/compensation/`, pure logic under
`app/beyo_manager/domain/compensation/`, services under
`services/commands/compensation/` and `services/queries/compensation/`.
(Proposed table names `user_compensations`, `user_compensation_components`; proposed
client-id prefixes `ucmp`, `ucc` — final names belong to the planner's naming registry.)

### 4.1 `UserCompensation` — one effective-dated version of a worker's terms

| Field | Type | Owner (who writes) | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system (IdentityMixin) | |
| `workspace_id` | FK workspaces, RESTRICT | command, from profile | scoping per 24_multi_tenancy |
| `user_work_profile_id` | FK user_work_profiles, RESTRICT, index | command at creation | never reassigned |
| `effective_from` | Date, nullable | command at creation | NULL **only** on migration-seeded initial versions = "unbounded past"; command-created versions require a date ≤ today (§7.4) |
| `effective_to` | Date, nullable | **system only** (chain construction §7.2) | NULL = open version; half-open `[from, to)` |
| `compensation_type` | enum `hourly \| monthly \| annual` | command at creation | native PG enum `user_compensation_type_enum` |
| `base_compensation_amount` | Numeric(12,4), ≥ 0 | command at creation | gross amount in `currency`, per the type's period |
| `currency` | enum `swedish_krona \| danish_krona \| euro` | command at creation | own enum type, same value set as `StaticCostCurrencyEnum` (per-table enum convention) |
| `contracted_hours_per_week` | Numeric(5,2), nullable, > 0 when set | command at creation | required when `compensation_type ∈ {monthly, annual}` or any component needs a period divisor (§6.3) |
| `gross_hourly_equivalent` | Numeric(12,4) | **system only** (canonical calculator) | derived-persisted; never accepted from API |
| `estimated_cost_per_hour` | Numeric(12,4) | **system only** (canonical calculator) | derived-persisted; never accepted from API |
| `created_at` / `created_by_id` | tz datetime / FK users | system / command | `created_by_id` NOT NULL (admin-written table) |
| `updated_at` / `updated_by_id` | tz datetime / FK users, nullable | system / correction command only | populated only by corrections |
| `is_deleted` / `deleted_at` / `deleted_by_id` | soft-delete trio | guarded delete command only | per 25_soft_delete; deletable only under §7.5 guard |

**Invariants:**

- **INV-1 (non-overlap):** for one `user_work_profile_id`, applicable intervals never
  overlap: at most one non-deleted version satisfies
  `(effective_from IS NULL OR effective_from <= D) AND (effective_to IS NULL OR D < effective_to)`
  for any date `D`. Enforced by construction (§7.2), a partial unique index
  `(user_work_profile_id) WHERE effective_to IS NULL AND is_deleted = false` (repo idiom),
  and a window CHECK `effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from`
  (mirrors the dropped-table precedent).
- **INV-2 (immutability):** after creation, a version's contractual facts change only via
  the correction operation; `effective_to` changes only via chain construction; derived
  fields change only via the canonical calculator invoked by those two operations.
- **INV-3 (one open version):** exactly zero or one open (`effective_to IS NULL`,
  non-deleted) version per profile; a profile with any version has exactly one.

### 4.2 `UserCompensationComponent` — one additional employer cost rule on a version

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK workspaces, RESTRICT | command | denormalized for tenancy filters, matches parent |
| `user_compensation_id` | FK user_compensations, RESTRICT, index | command at creation | components belong to exactly one version; never re-parented |
| `name` | String(100), non-empty | command | e.g. "arbetsgivaravgift", "semesterersättning" |
| `calculation_type` | enum `percentage_of_gross \| fixed_per_hour \| fixed_per_month \| fixed_per_year` | command | native PG enum |
| `source` | enum `statutory \| contract \| company_policy \| manual` | command | provenance label only in v1 — no behavior branches on it |
| `value` | Numeric(12,4), ≥ 0 | command | semantics per `calculation_type` (§6.3): percent units for `percentage_of_gross` (31.42 means 31.42%), money in the version's `currency` otherwise |
| `hourly_cost` | Numeric(12,4) | **system only** (canonical calculator) | derived-persisted |
| `created_at` / `created_by_id` | | system / command | |
| `is_deleted` / `deleted_at` / `deleted_by_id` | soft-delete trio | correction command only | removing a component from a version is a correction (§7.3) |

Components inherit the parent version's lifecycle: they are created with the version (or
added/removed by a correction to it), never edited independently of it.

### 4.3 `UserWorkProfile` changes

- **Remove** `salary_per_hour_before_tax` and `salary_per_hour_after_tax` (timing per
  migration plan §9 and owner card 1).
- **Add** `current_compensation_id` — nullable `use_alter=True` FK shortcut to the open
  version, updated atomically with version creation/closure (repo precedent
  `user.py:41-60`). **Convenience for API reads and live acquisition only:** analytics
  reconciliation always resolves by work date, never through this pointer (a replayed old
  day must not read a newer version).

### 4.4 State dimensions

A version's state is fully determined by its columns — no separate status enum:
**open** (`effective_to IS NULL`), **closed** (`effective_to` set), **deleted**
(`is_deleted`). Ordering of versions per profile is by `effective_from` (NULL first),
which the chain construction keeps strictly increasing. There is no other precedence rule.

---

## 5. Facts vs derived values (provenance boundaries)

| Layer | Values | Written by | May be overwritten by |
|---|---|---|---|
| **Contractual facts** | `compensation_type`, `base_compensation_amount`, `currency`, `contracted_hours_per_week`, `effective_from`, component `name/calculation_type/source/value` | create/change/correction commands (admin) | correction command only |
| **System-managed temporal state** | `effective_to`, `current_compensation_id` | chain construction | chain construction |
| **Derived-persisted (the §9 snapshot)** | `gross_hourly_equivalent`, component `hourly_cost`, `estimated_cost_per_hour` | canonical calculator, at version create/correct time only | the same calculator, on correction |
| **Derived-recomputable projections** | `total_cost_minor` on the four analytics tables and `task_steps` | reconcile paths | any reconcile/backfill replay (unchanged) |

Rules:

- Derived values are never accepted from any API request; request schemas simply have no
  such fields. Missing facts are never inferred (a version without
  `contracted_hours_per_week` where a divisor is required is a validation error, not a
  default).
- **The persisted per-version derived values are the historical snapshot** demanded by raw
  §9. Because reconciles read them (not raw facts, not live formulas), a future change to
  normalization formulas or rounding rules alters history only when a version is
  deliberately re-derived (correction) — never as a side effect of an analytics replay.
  A separate `WorkerCostSnapshot` table is therefore **not built** (changelog R-7).
- Provenance of a priced day is recoverable by re-running temporal resolution — the
  applicable version for `(user, work_date)` is deterministic and stable (INV-1 +
  append-only history). An explicit `applied_user_compensation_id` column on the two
  single-user-day tables is scope-laddered (§12, only-if-cheap).

---

## 6. Calculation contracts (canonical path)

One pure module, `app/beyo_manager/domain/compensation/` (no I/O, per
`architecture/08_domain.md`), owns every formula below. Commands call it and persist its
outputs; reconciles never re-derive it.

### 6.1 Period divisors

- `hours_per_week` = `contracted_hours_per_week` (Decimal, > 0)
- `hours_per_year` = `hours_per_week × 52`  — **52 exactly**, by convention (R-4)
- `hours_per_month` = `hours_per_week × 52 / 12`  (e.g. 40 h/wk → 173.33… h/month)

### 6.2 `gross_hourly_equivalent`

| `compensation_type` | Formula |
|---|---|
| `hourly` | `base_compensation_amount` |
| `monthly` | `base_compensation_amount / hours_per_month` |
| `annual` | `base_compensation_amount / hours_per_year` |

### 6.3 Component `hourly_cost`

| `calculation_type` | Formula | Requires |
|---|---|---|
| `percentage_of_gross` | `gross_hourly_equivalent × value / 100` | — |
| `fixed_per_hour` | `value` | — |
| `fixed_per_month` | `value / hours_per_month` | `contracted_hours_per_week` |
| `fixed_per_year` | `value / hours_per_year` | `contracted_hours_per_week` |

Validation: a version whose type or any component requires a divisor but lacks
`contracted_hours_per_week` is rejected at the command boundary.

### 6.4 `estimated_cost_per_hour`

`estimated_cost_per_hour = gross_hourly_equivalent + Σ component hourly_cost`
(non-deleted components of the version).

### 6.5 Precision & rounding

All arithmetic in `Decimal`; intermediates unquantized; each **persisted** derived value is
quantized to 4 decimal places with `ROUND_HALF_EVEN` (matching both `Numeric(12,4)` storage
and the existing banker's-rounding convention in `_cost_minor`). The minor-unit conversion
at the analytics boundary is unchanged (§8.1). All three supported currencies have
2-decimal minor units, so the existing `× 100` convention remains correct.

---

## 7. Temporal semantics & mutation operations

### 7.1 Resolution

Granularity is **calendar date** (R-3): the applicable version for `(user, D)` is the
non-deleted version with `(effective_from IS NULL OR effective_from <= D) AND
(effective_to IS NULL OR D < effective_to)`. Resolution key in analytics is
`(user_id, record.entered_at.date())` — the same date already used as `work_date`
(`process_step_transition.py:64`). At most one version matches (INV-1). No version matches
→ that unit contributes cost 0, exactly like today's missing-rate semantics (inherited
limitation, §12 deferred).

### 7.2 Contract change (`create` when a version already exists)

Atomically, in one command transaction: validate `new.effective_from` is a date, ≤ today
(R-5), and strictly greater than the open version's `effective_from` (NULL compares as
-∞); set open version's `effective_to = new.effective_from`; insert the new open version
with calculator-derived values; repoint `current_compensation_id`. Past analytics stay
priced by the closed version (HC-1). If `effective_from` < today, the command triggers the
scoped reprice (§7.3) for `[effective_from, today]` — a backdated change is retroactive
by declaration, not by accident.

### 7.3 Historical correction

A distinct command: amends contractual facts / components of one existing version **in
place**, re-derives its persisted values, stamps `updated_by_id`, writes an audit history
record (repo audit convention, `architecture/36_audit_log.md`), and **must** trigger the
scoped reprice for the version's applicable interval intersected with recorded work.
The reprice reuses the production reconcile functions exactly as
`backfill_averaged_time.py` does (per affected `(user, day)`: `reconcile_user_day_time` +
delta application; then `_recompute_step_time_totals` for touched steps). A correction
without its reprice is the defect class HC-1 forbids — the two are one operation, not two.

### 7.4 Future-dated changes — deferred

Version creation requires `effective_from ≤ today`. Rationale: a future-dated open version
would make "currently applicable" ≠ "open version", forcing either a scheduled
pointer-flip job or resolution-by-date on the live path; the architecture (resolution by
date) already supports future dating, so this is pure scope deferral, not a design cut
(R-5). The raw draft's "raise from Sep 1" is entered on Sep 1 (or backdated shortly
after, §7.2).

### 7.5 Deletion

Soft-delete of a version is allowed only when no settled `step_state_records` work falls
inside its applicable interval (guarded in the command; the mistaken-creation escape
hatch). Versions that have priced work are never deletable — correct them instead.

---

## 8. Analytics integration

### 8.1 What changes

- Both `_rate` helpers (`reconcile_user_time.py:164-173`,
  `process_step_transition.py:149-158`) are replaced by one resolution helper that returns
  the applicable version's persisted `estimated_cost_per_hour` for `(user_id, date)`.
- **Day/section grain:** one resolution per `(user, work_date)` reconcile — same call
  shape as today's `_rate`, same `_cost_minor` conversion:
  `int(((Decimal(working_s + pause_s) / 3600) × estimated_cost_per_hour × 100).to_integral_value())`.
- **Step grain:** contributions are grouped per `(user, entered_at.date())` instead of per
  user only, each group priced at its date's applicable version, then summed into
  `task_steps.total_cost_minor`. (Today's per-user float rounding collapses into
  per-(user, date) rounding; the day-grain path is untouched. R-8.)
- The backfill script gains the same resolution (it already reuses the production
  functions, so this follows automatically).

### 8.2 What deliberately does not change

Costed states (`working`+`paused`, never `ended_shift`), `marked_wrong` exclusion,
attribution (`COALESCE(credited_user_id, created_by_id)` — the known attribution-split
question stays an independent product decision, archgraph node
`concept-attribution-split`), the SET/delta idempotency scheme, minor-unit integer
storage, and the currency-naivety of `total_cost_minor` (analytics still assumes one
workspace currency; compensation rows now carry the currency **fact**, so a future
multi-currency treatment has its input — §12 deferred).

### 8.3 New replay invariant (testable)

After a contract change effective `D`, replaying any reconcile for a day `< D` yields
byte-identical cost. This is the invariant today's pipeline lacks and the reason
resolution reads persisted per-version values.

---

## 9. Migration & compatibility

Evidence-grounded destination for the two legacy columns (§2.1):

1. **Schema:** create the two tables + enums (autogenerate, reviewed per
   `architecture/30_migrations.md` checklist); add `current_compensation_id` shortcut.
2. **Data (journaled, per exemplar `97b60e06d42a`):** for every `user_work_profiles` row
   with `salary_per_hour_before_tax IS NOT NULL`, create one `UserCompensation`:
   `compensation_type = hourly`, `base_compensation_amount = salary_per_hour_before_tax`,
   `currency = swedish_krona`, `effective_from = NULL` (unbounded past — precedented by the
   dropped tables' nullable `effective_from`), `effective_to = NULL`, no components,
   derived values = the calculator's output (for `hourly`, `gross_hourly_equivalent =
   base`, `estimated_cost_per_hour = base` — so migrated history prices identically to
   today, by construction). Profiles with NULL salary get no version (cost 0, unchanged).
   Journal table, pre-flight contradiction refusal, post-condition counts, exact
   `downgrade` — all four per the exemplar.
3. **`salary_per_hour_after_tax`:** migrated **nowhere**. It has no computational meaning
   (§2.1); its disposal is owner card 1. Until the card is answered the column is not
   dropped (gate holds), but no new writes are accepted once the compensation API ships.
4. **API bridge:** `POST /auth/register`'s salary fields become the input for an initial
   `hourly` compensation (created through the same command path, not by writing profile
   columns). `PATCH /users/{id}` stops accepting both salary fields. `GET`/`PATCH`/register
   responses replace the two fields under `work_profile` per card 1's chosen shape.
5. **Column drop:** a follow-up migration (never a rewrite of an applied one,
   charter rule 7) removes both columns and their CHECKs after the bridge is verified.
6. **Cutover reprice:** owner card 3 decides whether the scoped backfill re-prices all
   history through the new pipeline at cutover (expected delta ≈ 0 by construction of
   step 2 — the point is provenance, not new numbers).

Known breakages to plan for: the serializer contract (`serializers.py:26-27`), the shell
test (`test_user_management.sh:236,250`), the integration test
(`test_update_user_admin_clock_in_code.py:311-317`), OpenAPI docs mirrors
(`routers/README.md:230-231,3784-3785`), and the stale
`Application_contracts/backend/architecture/01_architecture.md:140`.

---

## 10. Operations & API surface

All admin-facing, workspace-scoped, through the standard
`router → run_service → command/query` seam. Role gating per owner card 4.

- **Create/change compensation** — command `create_user_compensation` (§7.2 semantics;
  request object validates facts, incl. non-negative amounts — closing the PATCH validator
  gap of §2.1). Components supplied inline with the version.
- **Correct compensation** — command `correct_user_compensation` (§7.3; includes component
  add/remove/amend on that version; mandates reprice; writes audit record).
- **Delete version** — guarded per §7.5.
- **Read** — query: compensation history for a worker (versions + components + derived
  values, ordered by `effective_from`); current version comes with the profile via the
  shortcut.
- **Scoped reprice** — internal operation (not a public endpoint), invoked by §7.2/§7.3
  and runnable standalone as a script under `app/scripts/backfill/` (dry-run default,
  drained-queue requirement — precedent `backfill_averaged_time.py:1-8`).
- **Register bridge** — §9.4.

Not in v1: any endpoint exposing other workers' aggregated cost analytics (the four
analytics tables' cost columns remain API-invisible, as today).

---

## 11. External-source strategy

None required. No external transport exists in this domain: statutory values
(arbetsgivaravgift %, vacation %) are entered by admins (or seeded as workspace defaults
per card 2) as component facts; no API/website is scraped or called. The source-evidence
protocol is therefore satisfied vacuously — recorded here so the mechanism-inventory gate
does not go looking for a missing evidence doc. When a statutory rule engine is built
(§12 deferred), Skatteverket rates enter as effective-dated seeded reference data with
their own evidence doc.

---

## 12. Scope ladder

**Must ship (v1):**
- Both tables + enums, invariants INV-1..3, shortcut pointer, canonical calculator with
  the §6 contracts, temporal resolution, contract-change + correction + guarded-delete
  commands, scoped reprice, analytics integration (both grains), journaled migration +
  API bridge + column drop, audit records on change/correct, tests (§13), living-docs
  update (`docs/domains/` compensation page) and archgraph delta in the same change.
- Workspace-default statutory component set applied at version creation **if card 2
  answers yes** (copy-on-create — components stay facts on the version, never live-linked).

**Only if cheap:**
- `applied_user_compensation_id` provenance column on `user_daily_work_stats` and
  `user_section_daily_work_stats` (single-user-day grains only; ill-defined elsewhere).
- Optional `note` field on versions.
- Component template CRUD UI beyond a seeded default set.

**Explicitly deferred:**
- Statutory payroll-rule engine (effective-dated government rules resolved by worker
  context) — `source = statutory` is the extension point; nothing branches on it in v1.
- Future-dated contract changes (§7.4) and the pointer-flip scheduler they need.
- Multi-currency analytics; currency on `total_cost_minor`.
- Distinguishing "no compensation configured" from "zero cost" in analytics.
- Non-worker cost sources (static cost per hour — dormant `static_costs` table is the
  seed); net-pay / tax-withholding modeling; Connecteam rate sync.
- Any change to costed-state policy or attribution semantics (§8.2).

When elegance and budget conflict downstream: cut from the bottom of "must ship"'s
periphery (bridge shape, seeded defaults) before touching invariants or the canonical
path — architecture is kept, scope is cut.

---

## 13. Testing priorities

Per charter rules (automated criteria; enumerate, never sample; production-path objects;
exact expected outcomes; named mutations at named sites — the planner will formalize
these into criteria):

1. **Normalization table** — one row per `compensation_type` (3) and per component
   `calculation_type` (4), plus divisor-missing rejection rows; each row's fixture makes
   its own predicate the only reason the expectation holds; exact 4-dp expected values
   including a ROUND_HALF_EVEN tie case.
2. **Temporal resolution** — adjacent-pair enumeration around both boundaries:
   `D = from-1, from, to-1, to` (half-open), NULL-from and NULL-to versions, no-version →
   0, deleted-version exclusion.
3. **Non-overlap under the race** — concurrent create against the same profile: exactly
   one wins the partial unique index on the exact conflict path (the DB race, not just the
   pre-check).
4. **Replay invariant §8.3** — contract change effective D, re-reconcile a day < D:
   byte-identical cost (the test that fails against today's live-rate code by design).
5. **Correction end-to-end** — correct a version → persisted derived values change →
   scoped reprice updates exactly the affected days on all five cost surfaces (SET tables,
   Σ-table deltas, step grain); unaffected days untouched.
6. **Chain construction** — change closes the open version at the new `effective_from`;
   pointer repointed atomically; backdated change triggers reprice of the gap.
7. **Migration round-trip** — disposable DB only (charter rule 7): upgrade → seeded
   versions price history identically to legacy (delta = 0) → downgrade exact via
   journal. Automated proxy in-suite for the lifecycle check.
8. **Derived-field write protection** — API requests carrying derived fields are rejected
   or ignored per schema; mutation "make the request schema accept
   `estimated_cost_per_hour`" must turn a named test red.
9. **Teardown discipline** — tests that commit to the configured DB own try/finally
   deletion (charter rule 11½; the reconcile suite precedent
   `test_reconcile_user_completions.py` shows why the handler path is avoided).

---

## 14. Pre-implementation protocol

- **Next gate: mechanism-inventory.** Silent-failure mechanisms flagged for it (charter
  rule 6): the §6 formulas & constants (52-week convention, percent-vs-fraction, 4-dp
  quantization points), the resolution predicate and its NULL bounds, chain-construction
  atomicity + the partial-unique race, per-(user, date) grouping in the step grain, the
  correction↔reprice coupling (HC-1), minor-unit conversion continuity, migration journal
  reversibility, and the delta-consistency of Σ tables across a reprice.
- The implementation planner then produces master plan + phase plans; the master plan's
  environment topology must verify the analytics-worker launch reality (§2.5) and carry
  the drained-queue rule for reprice runs.
- Archgraph: sessions orient on the existing analytics branch nodes
  (`intention-step-transition-analytics`, `analytics-reconcile-user-day-time`,
  `table-user-work-profile`, `concept-attribution-split`) and record the phase delta at
  close; agents never adjudicate the 244 pending review items.
- Contract bundle for implementers (per goal-mapping guide): core set + `03_models`,
  `06_commands(_local)`, `07_queries(_local)`, `08_domain`, `21_naming_conventions`,
  `24_multi_tenancy`, `25_soft_delete`, `28_roles_permissions`, `29_feature_workflow`,
  `30_migrations`, `36_audit_log`, `46_serialization`, `50_testing_strategy`,
  `51_worker_runtime`, `52_replayability`, `53_operational_cli`.

---

## 15. Shaping changelog

**Round 0 — 2026-08-11 (initial shaping from raw_intention.md):**

- **R-1** Corrected the raw draft's claim that the salary fields are not frontend-surfaced
  — they are (three endpoints, §2.1). Consequence: API transition became owner card 1.
- **R-2** Established from code that `salary_per_hour_after_tax` has zero computational
  meaning (write-and-display only) — its disposal is a data/product decision (card 1),
  not a migration mapping.
- **R-3** Resolved effective-dating granularity to **calendar date** (half-open
  `[from, to)`): matches `work_date` keying of every rollup, makes day reconciles resolve
  to exactly one version, and forecloses mid-day ambiguity. Timestamp granularity
  rejected as unrepresentable in the day-grain tables.
- **R-4** Pinned normalization constants: 52 weeks/year exactly; monthly divisor
  `weekly × 52 / 12`; percent stored in percent units (31.42). Rationale: determinism
  over calendrical precision; owner may veto in review.
- **R-5** Resolved the wavering between snapshot-tables and dynamic reads (raw §9 vs §10):
  the snapshot **is** the persisted derived values on the immutable version row; analytics
  stays recompute-and-SET and becomes deterministic over append-only history. Dedicated
  `WorkerCostSnapshot` table rejected (R-7). Future-dated versions deferred to keep
  "open = currently applicable" true without a scheduler (§7.4).
- **R-6** Resolved overlap prevention to chain-construction + partial unique open-version
  index + window CHECK (repo idioms), rejecting `ExcludeConstraint`/`btree_gist` (no
  precedent in this repo, heavier migration surface).
- **R-7** Rejected a separate snapshot table also because the recomputable tables are
  replayed wholesale by design — any snapshot column there would be overwritten by the
  next reconcile; provenance lives on the version + deterministic resolution instead.
- **R-8** Resolved step-grain pricing to per-`(user, entered_at date)` grouping — the
  minimal change making multi-day steps price each day at its applicable version, while
  preserving the existing rounding conventions elsewhere.
- **R-9** Currency: compensation carries a required currency fact (own enum, three
  existing values, default `swedish_krona` at migration); analytics stays currency-naive
  as today — documented inherited limitation, not silently "fixed".
- **R-10** Corrections and their scoped reprice defined as one atomic operation (HC-1);
  reprice mechanics reuse the production reconcile functions per the
  `backfill_averaged_time.py` precedent rather than inventing an invalidation framework.
- **R-11** Recorded documentation drift found while grounding (§2.5) for coordinator
  routing rather than silently patching downstream artifacts.

---

## 16. Open decisions ledger

All remaining items are **owner-owned**; the gate holds on each until answered. The full
decision cards live in `owner_decisions.md` (this folder) with an `ANSWER:` slot per card;
answers are folded back here as a new changelog round. Summary:

| # | Decision | Blocks |
|---|---|---|
| 1 | Fate of the two salary fields on the user API (and of `salary_per_hour_after_tax` data) | §9.3-9.5 migration steps, serializer/bridge shape, column drop |
| 2 | Seed a workspace-default statutory component set (AGA, semester) applied at version creation? | whether v1 costs are realistic by default; §12 must-ship line |
| 3 | Run the cutover reprice of all history through the new pipeline? | §9.6; provenance of pre-cutover cost rows |
| 4 | Who may write/read compensation (today MANAGER can PATCH salary; register is ADMIN) | §10 role gating on every endpoint |

Everything else raised by the raw draft is resolved in-document (changelog above).

---

## Appendix A — raw-draft question map

| Raw "implementation-maker" question | Answered in |
|---|---|
| 1. What owns compensation today | §2.1 |
| 2. Where the salary fields are read/written | §2.1, §9 (breakage list) |
| 3. What records represent worked duration | §2.2 (`step_state_records`, sweep) |
| 4. Where UserCompensation lives | §4 (preamble) |
| 5. Enum/money/temporal patterns to reuse | §2.4, §4, §6.5 |
| 6. Overlap prevention | §7.2, INV-1, R-6 |
| 7. Computed vs persisted | §5 |
| 8. Where historical snapshots live | §5, R-5/R-7 |
| 9. What must be migrated | §9 |
| 10. What breaks | §9 (breakage list), card 1 |
| 11. Tests for normalization/temporal invariants | §13 |
| 12. This implementation vs statutory engine | §12, §11 |
