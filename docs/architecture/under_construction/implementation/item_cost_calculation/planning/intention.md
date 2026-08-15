# Intention: Item Cost Calculation & Production Budgeting

```
status: resolved — mechanism gate PASSED (round 4: gate cards 1–2 answered and
        folded); mechanism contracts complete (§4A/§6A/§7A/§7B/§8A/§10A/§11A);
        open-decisions ledger EMPTY; next gate implementation-planner
role: intention (pipeline root artifact)
shaped_from: raw_intention.md (this folder)
date: 2026-08-11
round: 4 (round 0 initial shaping; round 1 owner answers folded; round 2 R1-1 veto
         point confirmed; round 3 mechanism-inventory contracts; round 4 gate cards
         answered and folded — all same day)
```

---

## 1. Objective & hard constraints

Introduce an **item-economics domain** that converts an item's expected sale price, minus
configured economic allocations, into a **production budget** expressed as an aggregate
**worker-minute allowance**, freezes that decision as an immutable committed evaluation
per economic episode (task), lets managers explore what-if projections without touching
committed history, and measures actual consumption against the allowance from the
existing step-time records.

The economic contract this must realize:

```
expected sale price  (snapshot at commit)
        ↓  subtract configured allocations (cost model terms, §6.1–6.2)
production budget (minor units)
        ↓  ÷ cost per productive worker-minute (production cost basis, §6.3)
allowed worker-minutes  (the aggregate economic constraint)
        ↓  compare against trusted WORKING seconds from step_state_records (§8)
consumed / remaining / variance  (live while working, final result at episode close)
```

**Hard constraints:**

- **HC-1 — Committed economics never silently change.** A committed evaluation is an
  immutable snapshot of every input and derived value it used. Changing a cost model,
  a cost basis, or the item's live monetary fields never alters any committed
  evaluation. New decisions are new versions that supersede, never edits.
- **HC-2 — Projections never operate.** A projection answers "what if". It is never read
  by worker-facing surfaces, analytics, or the final result. Only committed evaluations
  carry operational meaning. Promotion creates a committed evaluation; it does not
  mutate the projection.
- **HC-3 — One time-truth.** Actual consumption derives exclusively from the existing
  operational records (`step_state_records` → concurrency-averaged rollups on
  `task_steps`). No second time-tracking mechanism is built, and the existing execution
  path is not modified.
- **HC-4 — No compensation dependency.** `UserWorkProfile.salary_per_hour_before_tax`
  / `salary_per_hour_after_tax` (scheduled for removal by the separate compensation
  implementation, which ships AFTER this one) are not read, and the future compensation
  tables are not referenced. The production cost basis is independently configured;
  §10.3 defines the seam through which compensation can later feed it without redesign.
- **HC-5 — Worker-count-free economics.** The allowance is an aggregate worker-minute
  quantity. Worker count and section count appear nowhere in the calculation contracts
  (§6); they are presentation/allocation concerns only (§9.3). The vocabulary is
  "worker-minutes", never "minutes per worker".
- **HC-6 — Repo conventions are binding.** Money is integer minor units + per-table
  currency enum; rates/percentages are `Numeric` Decimal; no floats
  (`models/tables/static_costs/README.md`, `models/tables/items/README.md:30`).
  Contracts under `architecture/` govern how code is written (pattern-authority rule,
  `task_system/backend_contract_goal_mapping_guide.md:16-52`). Proposed names below are
  subject to the implementation planner's naming registry.
- **HC-7 — Reconstructible by design.** Committed snapshots carry everything needed to
  reproduce their derivation; live actuals and the final result are recomputable from
  source records at any time (recompute-and-SET, replay-safe like the existing
  analytics scheme).

---

## 2. Grounding — what exists today (verified 2026-08-11)

Full evidence census with all write/read sites: `research_context.md` (this folder).
The load-bearing facts:

### 2.1 Item monetary fields — plumbed, undefined, unprotected

`Item` (`app/beyo_manager/models/tables/items/item.py`, prefix `itm`) carries
`item_value_minor` (Integer, nullable, `:38`), `item_cost_minor` (Integer, nullable,
`:39`), `item_currency` (enum `swedish_krona | danish_krona | euro`, **nullable, no
default, no workspace fallback**, `:40-42`).

- **Semantics are undefined.** No code consumes either field for any business rule —
  they are written by item/task CRUD and echoed by serializers, nothing else. The only
  descriptors disagree: the planning doc calls value "estimated business value" and cost
  "internal operational cost" (`docs/architecture/under_construction/intention/planning_tables/item/item_models.md:105-107`),
  while the frontend handoff example (value 120000 / cost 80000) reads as
  sale-side vs acquisition-side. **Owner card 1 ratifies the semantics this domain
  assigns** (§17).
- **No validation anywhere**: no non-negativity CHECK (unlike every sibling money column,
  e.g. `item_upholstery_requirement.py:104-107`), no request validator, and an amount
  can exist with NULL currency.
- **Silently overwritable**: `find_or_create_item` overwrites both fields on a
  pre-existing item matched by article_number/sku (`find_or_create_item.py:98-100`) and
  is reachable from `create_task` (`create_task.py:226-232`), whose route admits
  **WORKER** (`routers/api_v1/tasks.py:331`); `PATCH /items/{id}` admits **SELLER**
  (`routers/api_v1/items.py:342`). History records discard old/new values
  (`update_item.py:106-117`) — a prior amount is unrecoverable. This is why every
  evaluation snapshots the values it used (HC-1).
- `Item.state` is dead (always `PENDING`; no writer besides creation) — item lifecycle
  lives in Task/TaskStep state. **No sale/sold-price record exists anywhere**; Shopify
  order webhooks are subscribed but explicitly unprocessed
  (`architecture/57_shopify_integration.md:201`). Actual realized sale price is not
  obtainable today (deferred, §13).
- Category grouping for analytics exists: `item_category_snapshot` /
  `item_major_category_snapshot` (wood|seat) denormalized on the item with a partial
  index (`item.py:72-77`).
- *(Round 1 note: the three monetary columns described here are scheduled for removal
  — §4.7, §10.2. This subsection remains as grounding of the legacy state the
  migration must handle.)*

### 2.2 Tasks are the episode vehicle — with corrections to the raw draft

- `task_type` enum: `internal | return | pre_order` (`domain/tasks/enums.py:4-7`).
  **The raw draft's "return_type" does not exist.** The real fields are
  `return_source` (`after_purchase | before_purchase | store_return`, `enums.py:28-31`)
  and `return_method` (`drop_off_by_customer | pickup`, `:39-41`) — both optional,
  **not gated to `task_type = return`**, and freely editable via `update_task`
  (`update_task.py:32,34`). Because they are mutable, the evaluation snapshots the
  episode typing (§4.5).
- **One active PRIMARY item per task is DB-enforced** (`uix_task_items_primary_active`,
  `task_item.py:52-58`). `RELATED` exists in the enum but has **no production writer**
  (single test exercises it, asserting analytics ignores it); `create_task` attaches at
  most one item, always PRIMARY (`create_task.py:295-303`); the only multi-item entry
  is ADMIN/MANAGER-only `POST /{task_id}/items` with zero test coverage. An item CAN be
  on multiple tasks over time (uniqueness includes task_id) — which is exactly the
  episode model this domain needs.
- **No return↔original linkage exists** (no source/parent task FK anywhere). The only
  cross-episode thread is the shared `item_id`.
- Task lifecycle: work-finished boundary is `READY` (only via
  `maybe_evaluate_task_ready`, `_task_state_transitions.py:51-102`, **no timestamp**);
  terminal states `RESOLVED | FAILED | CANCELLED` set `closed_at` and share an
  identical side-effect block (history record, notifications, event dispatch —
  `resolve_task.py:53-104` et al.). `READY` tasks can reopen
  (`maybe_reopen_task_to_working`, called from `add_task_steps.py:181-186`).
  **Nothing totals a task at any lifecycle point** — task carries no aggregate columns.
- `tasks.additional_details` JSON exists; customer snapshot columns on task are the
  established snapshot-at-creation precedent (`models/tables/tasks/README.md:60`).

### 2.3 Time & batch pipeline — worker-seconds already exist per step

- `step_state_records` is the labor-time source of truth; at most one open record per
  step (partial unique `step_state_record.py:100-106`), so simultaneous multi-worker
  work on one step is structurally impossible — a step's history is a sequential chain
  of records with per-record `credited_user_id`/`created_by_id` attribution.
- The concurrency sweep (`domain/analytics/concurrency.py:35-76`) divides a **single
  user's** overlapping batchable intervals by `k` (blind to task/step/item; state
  buckets never share a divisor; non-batchable intervals always earn full duration).
  Consequence: when a worker batch-works N steps of N different tasks, each step —
  and therefore each task and each item — receives `1/N` of the wall clock. **Per-item
  time is already correctly diluted by construction; this domain adds no allocation
  arithmetic on top** (§9.2).
- `TaskStep.total_working_seconds` (and siblings) are recomputed-and-SET from settled,
  trusted (non-`marked_wrong`) contributions by `_recompute_step_time_totals`
  (`process_step_transition.py:161-234`), via the transactional-outbox →
  `queue:analytics` worker pipeline (at-least-once, replay-safe). `inaccurate_*`
  columns hold the marked-wrong time separately.
- Per-item time attribution below task level does not exist (`StepStateRecord` and
  `TaskStep` have no item_id; `ItemIssue` is the only per-(item, step) fact). The
  existing per-item aggregate precedent is
  `TaskItem(PRIMARY) → Σ TaskStep.total_working_seconds`
  (`get_worker_clock_out_analytics.py:149-168`).
- `TaskStep.total_cost_minor` is salary-priced (working+paused seconds ×
  `salary_per_hour_before_tax`) — the machinery the compensation project will replace.
  This domain **consumes the time columns and stays separate from the salary-cost
  columns** (§8.2).

### 2.4 Sections, configuration, utilization — the gaps

- **No grouping entity over working sections exists** (exhaustive: 90 tables, no
  group/pipeline/department; only seed-time dict constants). Net-new modelling required.
  Memberships are many-to-many and time-varying (`uix_working_section_memberships_active`),
  so "a worker belongs to one cost group" is not derivable — another reason the cost
  basis is configured as an aggregate, not derived from headcount.
- **No workspace settings store of any kind** (workspaces table: name, time_zone, audit
  only). The established config pattern is a first-class workspace-scoped table with
  audit + soft delete + workspace-scoped uniqueness, exposed via a 5-verb router
  (`pause_reasons`, `issue_types`, `item_categories`). The catalog lesson
  (`pause_reason.py:25-34`): manager-owned rows with a **code-owned enum
  discriminator** — never slug-resolved rows.
- **No live effective-dated table.** The dropped `issue_category_configs`
  (`7d92a90e6282:260-289`) is the only precedent: nullable `effective_from`/`effective_to`,
  window CHECK, unique on the start. The live "one open row" idiom is a partial unique
  index on the open predicate (four tables). Identical to the conventions the sibling
  compensation intention adopted.
- `static_costs` (`static_cost.py`) is fully modelled, migrated, documented — and
  completely unwired (no commands/queries/routers/seeds). Its README carries the repo's
  snapshot-on-use doctrine ("historical records must not depend on the mutable live
  row"). This domain follows the doctrine; whether to absorb the dormant table is
  resolved in R-9 (no — it stays the seed for future non-worker static costs, §13).
- **"Month" is undefined in this codebase** — every rollup is UTC-day;
  `workspaces.time_zone` is never read by analytics. §6.3 therefore keeps calendar
  months out of the calculation: monthly figures are configuration inputs; only the
  derived per-minute rate feeds any computation.
- **Observed utilization** is reconstructible per worker (shift records split
  working/in_pause/idle — `build_recorded_shift_timeline`,
  `list_workers_linear_timeline.py:34-71`) but **not per section** (shift time carries
  no section; only step time is section-attributed). No utilization ratio is computed
  anywhere today; `focus_ratio` (`insights/metrics.py:26-28`) is working÷active-step
  time, not utilization. Observed utilization is therefore an analytics surface built
  on existing data, deferred (§13), and never conflated with planning utilization (HC
  of raw §6, kept).
- `working_section_daily_work_stats` (per-section-day productive seconds + counts) is
  maintained but has **zero readers** — the natural numerator for future per-section
  observed utilization.

### 2.5 Conventions this domain must follow

Identical baseline to the sibling compensation intention (verified same day, same
branch): `IdentityMixin` client_id prefixes; inline tz-aware audit columns +
`created_by_id`/`updated_by_id` (users FK RESTRICT); soft-delete trio
(`architecture/25_soft_delete.md`); workspace scoping from JWT
(`architecture/24_multi_tenancy.md`); enums via `configure_sa_enum_values`, lowercase
values, `<singular>_<column>_enum`; partial unique open-row idiom + window CHECK;
`use_alter=True` current-child pointers; commands with `requests/` parsing,
`maybe_begin`, `run_service` boundary; pure calculation in
`app/beyo_manager/domain/<domain>/`; worker handlers `handle_<event>(raw, task_id)`;
journaled data-migration exemplar `97b60e06d42a`; new tables registered in
`models/__init__.py` and `client_id_prefix_map.md`; a `models/tables/<domain>/README.md`
table guide per house style.

### 2.6 Documentation drift observed while grounding (coordinator to route)

1. `models/tables/items/README.md:34` — says item state `STALL`; code says `STALLED`.
2. `models/tables/items/README.md:53-61` — documents `base_time_seconds` /
   `time_multiplier` / name-snapshot columns on `item_issues` that no longer exist
   (`item_issue.py:22-57`).
3. `models/tables/tasks/README.md:8,42` — references `task_history_record.py` /
   `latest_history_record_id`, neither of which exists.
4. `Application_contracts` planning docs never mention the step time/cost aggregates
   (`planning/task/task_step_models.md` has no `total_working_seconds` or
   `total_cost_minor`) — an existing contract gap this project will widen if not routed.
5. Dead code/columns noticed in passing: `Task.recorded_time_marked_wrong` /
   `Task.taken_from_average` have no writers; `TaskStateEnum.STALLED` is never written;
   `domain/task_steps/aggregate_metrics.py` has no callers.

---

## 3. Core workflow

1. **Manager configures the economics** (once, then rarely): a production cost group
   naming the pipeline's sections; a cost basis version (fixed monthly cost, monthly
   paid worker-hours, planning utilization) — the system derives and persists the cost
   per productive worker-minute; a cost model version with allocation terms (VAT %,
   desired profit %, materials fixed amount, purchase-cost passthrough…).
2. **An episode begins.** A task is created for an item (task_type internal / return /
   pre_order — the episode typing). An initial committed evaluation is created
   automatically when the workspace is evaluable and the item has a current valuation
   with an expected price (card 3: yes), and explicitly by a manager otherwise or at
   any later point. The evaluation snapshots every input and derives budget and
   allowed worker-minutes (§6).
3. **Work happens.** Step transitions close interval records and the analytics worker
   maintains `task_steps.total_working_seconds` exactly as today. Nothing in the
   execution path changes (HC-3).
4. **Anyone entitled reads budget status live**: consumed worker-minutes
   (Σ trusted working seconds of the task's steps), remaining minutes, percent
   consumed, projected overrun — derived on read from the committed evaluation +
   step rollups; never stored (§8.1).
5. **Manager experiments.** Projections copy the current committed evaluation's inputs,
   let the manager vary price/assumptions, compute the same derivation, and are saved
   for comparison. Promoting one commits a new evaluation version that supersedes the
   previous (HC-1, HC-2) and supersedes the item's current valuation to match (§7.2).
6. **The episode closes.** On the task's terminal transition (RESOLVED / FAILED /
   CANCELLED) an outbox event triggers the final result: actual worker-minutes,
   consumed cost at the evaluation's snapshot rate, variance — recompute-and-SET,
   replay-safe (§8.3).
7. **Analytics read across episodes**: restoration vs return vs pre-order economics per
   item (lifetime = Σ episodes), by category, by section — enabled by the model, UI
   deferred (§13).

---

## 4. Domain model

New domain package: `item_economics` — models under
`app/beyo_manager/models/tables/item_economics/`, pure logic under
`app/beyo_manager/domain/item_economics/`, services under
`services/commands/item_economics/` and `services/queries/item_economics/`.
(All table/prefix names proposed; the planner's naming registry has final authority.)

### 4.1 `ProductionCostGroup` — a named pipeline of working sections
(table `production_cost_groups`, prefix `pcg`)

| Field | Type | Owner (who writes) | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system (IdentityMixin) | |
| `workspace_id` | FK workspaces RESTRICT, index | command | 24_multi_tenancy |
| `name` | String(255) | command | partial unique `(workspace_id, name) WHERE is_deleted = false` (repo idiom, `working_section.py:50-57`) |
| audit + soft-delete trio | | system / commands | `created_by_id` NOT NULL (admin-written) |

### 4.2 `ProductionCostGroupSection` — group membership of a working section
(table `production_cost_group_sections`, prefix `pcgs`)

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK workspaces RESTRICT | command | matches parent |
| `production_cost_group_id` | FK RESTRICT, index | command | |
| `working_section_id` | FK working_sections RESTRICT, index | command | |
| `added_at` / `added_by_id`, `removed_at` / `removed_by_id` | | command | membership interval, `working_section_membership.py` idiom |

**INV-G1:** one active group per section — partial unique
`(workspace_id, working_section_id) WHERE removed_at IS NULL`. A section in two groups
would double-count its cost. Membership is **analytic attribution only** in v1 — rate
selection does not read it (§7.4, R-8).

### 4.3 `ProductionCostBasisVersion` — one effective-dated version of a group's cost basis
(table `production_cost_basis_versions`, prefix `pcbv`)

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK RESTRICT | command | |
| `production_cost_group_id` | FK RESTRICT, index | command at creation | never reassigned |
| `effective_from` | Date, nullable | command at creation | NULL = unbounded past (first version only); command-created versions require date ≤ today (mirrors compensation R-5 rationale) |
| `effective_to` | Date, nullable | **system only** (chain construction) | NULL = open; half-open `[from, to)` |
| `fixed_monthly_cost_minor` | Integer, ≥ 0 CHECK | command | the group's total fixed production cost per month |
| `currency` | enum `swedish_krona \| danish_krona \| euro` | command | own enum type per per-table convention |
| `monthly_paid_hours` | Numeric(8,2), > 0 CHECK | command | **aggregate** paid worker-hours/month for the whole group — not per worker (HC-5); UI may compute it as headcount × 160 but stores the total |
| `planning_utilization_percent` | Numeric(5,2), CHECK > 0 AND ≤ 100 | command | e.g. 80.00 |
| `cost_per_worker_minute` | Numeric(12,4) | **system only** (canonical calculator §6.3) | derived-persisted; never accepted from API |
| audit + soft-delete trio | | | delete guarded §7.5 |

> **Amended by §4A (round 3):** A1 raises `fixed_monthly_cost_minor` to CHECK **> 0**;
> A2 renames `cost_per_worker_minute` to `cost_per_worker_minute_minor` (minor units per
> worker-minute, CHECK > 0).

**INV-B1:** one open version per group — partial unique
`(production_cost_group_id) WHERE effective_to IS NULL AND is_deleted = false` + window
CHECK (`effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from`).
**INV-B2:** after creation, facts change only via a new version; `effective_to` only via
chain construction; the derived rate only via the canonical calculator.

### 4.4 `CostModelVersion` + `CostModelTerm` — the workspace's allocation assumptions
(tables `cost_model_versions` prefix `cmv`, `cost_model_terms` prefix `cmt`)

`CostModelVersion`: `workspace_id`, `effective_from` / `effective_to` (same temporal
contract as §4.3, **INV-M1** one open version per workspace), audit + soft delete.

`CostModelTerm` — one allocation rule on a version:

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK RESTRICT | command | |
| `cost_model_version_id` | FK RESTRICT, index | command at creation | terms belong to exactly one version; never re-parented; unique `(cost_model_version_id, name)` among non-deleted |
| `name` | String(100), non-empty | command | e.g. "VAT", "materials", "desired profit", "purchase cost" |
| `calculation_type` | enum `percentage_of_expected_sale_price \| fixed_amount \| item_purchase_cost` | command | code-owned discriminator (catalog lesson §2.4); the extension point for future bases (per-worker-minute cost etc.) |
| `value` | Numeric(12,4), ≥ 0, nullable | command | percent units for percentage (25.00 = 25%); major currency units for fixed_amount; **NULL required** for `item_purchase_cost` (value comes from the item) |
| audit + soft-delete trio | | | term removal on the open version = new version, not edit (INV-M2 mirrors INV-B2) |

> **Amended by §4A (round 3):** A3 replaces `value` with `percent_value` Numeric(6,3)
> and `fixed_amount_minor` Integer (per-type nullability: §6A.4); A4 adds
> `CostModelVersion.currency` NOT NULL; A5 adds a partial unique allowing at most one
> `item_purchase_cost` term per version; A6 pins terms as immutable with their version.

Terms are unordered; the budget subtracts their sum (§6.2). There is no
"production/restoration allocation" term — production is the **residual** by
construction, which is what makes expected-price changes flow straight into the budget
(raw §13).

### 4.5 `ItemCostEvaluation` — one economic decision (or scenario) for one episode
(table `item_cost_evaluations`, prefix `ice`)

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK RESTRICT | command | |
| `task_id` | FK tasks RESTRICT, index | command at creation | the episode anchor (R-3) |
| `item_id` | FK items RESTRICT, index | command at creation | the task's PRIMARY item at creation (R-11); keying by (task, item) is the multi-item extension seam |
| `kind` | enum `projection \| committed` | command at creation, **immutable** | HC-2 |
| `label` | String(255), nullable | command | scenario name for projections ("price 3800") |
| `task_type_snapshot` | enum copy of task_type | system at creation | episode typing frozen (task fields are mutable, §2.2) |
| `return_source_snapshot` | enum copy, nullable | system at creation | return granularity frozen |
| `expected_sale_price_minor` | Integer, ≥ 0 | command (defaults from the item's current valuation §4.7A, overridable on projections) | snapshot input |
| `purchase_cost_minor` | Integer, ≥ 0, nullable | command (defaults from the current valuation) | snapshot input; required iff the model has an `item_purchase_cost` term |
| `currency` | enum, NOT NULL | system at creation | resolved per §6.6; must match the basis version's currency |
| `cost_model_version_id` | FK RESTRICT | system at creation | provenance ref |
| `production_cost_group_id` / `production_cost_basis_version_id` | FK RESTRICT | system at creation | provenance refs |
| `monthly_paid_hours_snapshot` / `planning_utilization_percent_snapshot` / `fixed_monthly_cost_minor_snapshot` | as §4.3 | **system only** | copied values — the evaluation is reproducible without the live rows (HC-7) |
| `cost_per_worker_minute_snapshot` | Numeric(12,4) | **system only** | |
| `production_budget_minor` | Integer (may be negative, §6.2) | **system only** (calculator) | derived-persisted |
| `allowed_worker_minutes` | Numeric(12,2) | **system only** (calculator) | derived-persisted; the aggregate allowance |
| `calculation_version` | Integer | system | formula/model version stamp (raw §9) |
| `committed_at` | tz datetime, nullable | system | set iff kind = committed |
| `superseded_at` / `superseded_by_id` | tz datetime / FK self, nullable | **system only** (commit chain §7.2) | committed chain |
| `promoted_from_id` | FK self, nullable | system | committed row's source projection, if promoted |
| audit + soft-delete trio | | | projections deletable; committed rows **never** (guard §7.5) |

> **Amended by §4A (round 3):** A2 renames the rate snapshot to
> `cost_per_worker_minute_minor_snapshot`; A8 states that `production_budget_minor` and
> `allowed_worker_minutes` deliberately carry no non-negativity CHECK. The closed set of
> fields this row must carry for HC-7 is proved in §6A.11.

**INV-E1 (one current decision per episode):** partial unique
`(task_id) WHERE kind = 'committed' AND superseded_at IS NULL AND is_deleted = false`.
**INV-E2 (immutability):** a committed evaluation's columns never change except
`superseded_at`/`superseded_by_id` via the commit chain. Projections are create-and-
delete only — editing assumptions = new projection (cheap rows beat mutable history).

#### `ItemCostEvaluationTerm` — snapshot of one term line as applied
(table `item_cost_evaluation_terms`, prefix `icet`)

`evaluation_id` FK RESTRICT + index; `name`, `calculation_type`, `value` copied from the
term; `amount_minor` Integer — the computed subtraction (§6.1). Written only by the
calculator at evaluation creation; immutable. These rows are the "where did the cost
come from" drill-down (raw §8) and make the budget re-derivable line by line.

**Round-7 column-set pin (projection D6 — this paragraph governs the table shape):**
the exact columns are `client_id` (prefix `icet`), `workspace_id` (FK RESTRICT —
`24_multi_tenancy` binds every domain table), `evaluation_id` (FK RESTRICT + index),
`name`, `calculation_type`, **`percent_value` and `fixed_amount_minor`** (A3's
replacement of the round-0 `value` column applies to this snapshot table too — the
§6A.11 closed set is the authority), `amount_minor`, and `created_at` only. **No**
`created_by_id`/`updated_*` (system-authored; the acting user is stamped on the
evaluation) and **no** soft-delete trio (rows are immutable and reachable only
through their evaluation; a projection's soft delete orphans its term rows
harmlessly — every read path goes through the evaluation).

### 4.6 `ItemCostResult` — the final actuals of a closed episode
(table `item_cost_results`, prefix `icr`)

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` / `task_id` / `item_id` | FKs RESTRICT | worker handler | **unique (task_id)** — one result per episode |
| `evaluation_id` | FK item_cost_evaluations RESTRICT | worker handler | the current committed evaluation at close; NULL forbidden — no evaluation ⇒ no result row (§8.3) |
| `actual_worker_seconds` | Integer ≥ 0 | worker handler | Σ trusted working seconds (§8.1) |
| `actual_worker_minutes` | Numeric(12,2) | worker handler | seconds/60, quantized §6.6 |
| `consumed_cost_minor` | Integer | worker handler | minutes × snapshot rate (§6.5) |
| `variance_worker_minutes` / `variance_cost_minor` | Numeric(12,2) / Integer | worker handler | allowed − actual (negative = overrun) |
| `task_closed_at` | tz datetime, **nullable (round 6)** | worker handler | copied from `task.closed_at`; NULL while the episode is not terminal |
| `task_state_snapshot` | enum copy of task state, **NOT NULL** (**round 6**; reuses PG type `task_state_enum`, `create_type=False`, ownership stays on `tasks.state` — R2-1 rule) | worker handler | the lifecycle boundary the row was last computed at (working \| ready \| resolved \| failed \| cancelled); every §8B.2 recompute stamps it, so NULL is unrepresentable |
| `computed_at` | tz datetime | worker handler | |
| `created_at` (no soft delete) | | system | corrections happen by replay (recompute-and-SET), not edits |

*(Round 6: the result is computed at every episode boundary, not only at terminal
close — contract in §8B. `task_closed_at` therefore became nullable and
`task_state_snapshot` was added; both are refreshed by every recompute.)*

### 4.7 `Item` changes — the legacy monetary columns are REMOVED (round 1, card 1)

Owner decision: `item_value_minor`, `item_cost_minor` and `item_currency` leave the
`items` table — valuation and cost are taken over by the independent `ItemValuation`
table (§4.7A) linked to the item. Nothing in this domain writes Item at all.
Consequences:

- every item write path stops accepting monetary fields — which also implements card
  2's tightening structurally: the **only** money write path left in the system is the
  specialized valuation command (§11, ADMIN/MANAGER); the WORKER task-creation and
  SELLER item-PATCH exposures cease to exist rather than being gated;
- item serializers stop emitting them (`domain/items/serializers.py:103-105`,
  `domain/tasks/serializers.py:104-105`); full migration & breakage list in §10.2;
- `item_currency` is dropped together with the amounts it qualifies (**owner-confirmed
  round 2, R2-1**); the PG enum TYPE `item_currency_enum` is retained (reused by
  `item_upholstery_requirements.currency` — a column verified dormant: never written,
  only NULL-echoed by two serializers), with type-creation ownership moved — planner
  detail (§10.2 step 3).

### 4.7A `ItemValuation` — the item's current price/cost record (round 1)
(table `item_valuations`, prefix `ival`)

| Field | Type | Owner | Notes |
|---|---|---|---|
| `client_id` | String(64) PK | system | |
| `workspace_id` | FK workspaces RESTRICT | command | |
| `item_id` | FK items RESTRICT, index | command at creation | |
| `expected_sale_price_minor` | Integer, ≥ 0 CHECK, nullable | command | |
| `purchase_cost_minor` | Integer, ≥ 0 CHECK, nullable | command | |
| `currency` | enum `swedish_krona \| danish_krona \| euro` (own type) | command | NOT NULL — amounts are never currency-less (closes the legacy gap §2.1) |
| `superseded_at` / `superseded_by_id` | tz datetime / FK self, nullable | **system only** (supersession chain) | |
| `created_at` / `created_by_id` | | system / command | rows immutable after creation (INV-V2) |
| soft-delete trio | | guarded delete | deleting the current row returns the item to "unvalued" |

Table CHECK: at least one of the two amounts is non-NULL.

**INV-V1 (one current valuation per item):** partial unique
`(item_id) WHERE superseded_at IS NULL AND is_deleted = false`.
**INV-V2 (immutability):** rows never change after creation; every edit is a
superseding row — an append-only price history, answering raw §21's auditability
questions structurally where the legacy columns' history was lossy (§2.1).
Writers: the specialized valuation command (§11), the §7.2 mirror step, the §10.2
data migration, **and (round 18, R18-1/§7B.6) `create_task`'s inline birth write —
the fourth writer, through the same registered chain**. An item with no current
valuation is simply **unvalued** — the common
creation state (card 2's answer) — and is never inferred as zero (R-9).

### 4.8 State dimensions

Every entity's state is fully determined by its columns — no separate status enums
beyond `kind`: config versions are **open/closed/deleted** (as compensation §4.4);
evaluations are **projection**, **committed-current** (`superseded_at IS NULL`),
**committed-superseded**; episodes take their lifecycle from the Task itself. Committed
evaluations of one task are totally ordered by `committed_at` (chain-constructed,
strictly increasing). No other precedence rule exists.

### 4A. Schema amendments required by the mechanism contracts (round 3)

The §4 tables above are amended as follows. Each amendment closes a mechanism that
would otherwise fail silently; none changes a product semantic. Names remain subject
to the planner's naming registry (§4 preamble).

| # | Amends | Amendment | Silent failure it closes |
|---|---|---|---|
| **A1** | §4.3 `fixed_monthly_cost_minor` | CHECK **> 0** (was ≥ 0) | 0 ⇒ rate 0 ⇒ §6.4 divides by zero (a crash on the *second* command, months after the config was typed) |
| **A2** | §4.3 `cost_per_worker_minute` | renamed **`cost_per_worker_minute_minor`**, Numeric(12,4), denominated in **minor units per worker-minute**; CHECK > 0; §4.5's snapshot renamed to match | HC-6 (money is minor units). Removes all three ÷100/×100 conversions from §6.3–6.5 — three unit-inversion sites, each silent |
| **A3** | §4.4 `CostModelTerm.value` | replaced by two typed columns: **`percent_value` Numeric(6,3)** and **`fixed_amount_minor` Integer** (per-type nullability in §6A.4) | one column carrying percent units *and* major currency units: a 500 typed as "500 kr" and read as 5.00 kr is invisible in every payload |
| **A4** | §4.4 `CostModelVersion` | + **`currency`** enum (own type), NOT NULL | `fixed_amount` terms are money with no currency of their own; §6A.9 makes the equality three-way |
| **A5** | §4.4 `CostModelTerm` | partial unique **one `item_purchase_cost` term per version** (`WHERE calculation_type = 'item_purchase_cost' AND is_deleted = false`) | two such terms (legal today — uniqueness is on `name`) subtract the purchase cost twice |
| **A6** | §4.4 `CostModelTerm` | terms are immutable with their version (INV-M2): the soft-delete trio exists for house-style shape but **no v1 command writes it**; §6.2's "non-deleted" filter is retained as a defensive predicate, not an editing affordance | §4.4/§6.2 as written imply terms can be deleted from a live version, which would silently reprice every later evaluation on that version |
| **A7** | §4.6 `ItemCostResult` | + **`calculation_version`** Integer, copied from the evaluation | a formula change must be detectable on a result row, not only on the evaluation |
| **A8** | §4.5 | `production_budget_minor` and `allowed_worker_minutes` carry **no** non-negativity CHECK — stated explicitly so a later autogenerate or reviewer does not "fix" §6.2's deliberate negative | a clamped budget turns "this item cannot support production" into "this item has no allowance", which reads as a configuration bug |

---

## 5. Facts vs derived values (provenance boundaries)

| Layer | Values | Written by | May be overwritten by |
|---|---|---|---|
| **Live economic inputs** | the item's current `ItemValuation` row (§4.7A) | specialized valuation command (ADMIN/MANAGER) + §7.2 mirror + §10.2 migration | superseding rows only (INV-V2) |
| **Configuration facts** | group name/membership; basis version facts; model version terms | admin commands | new versions only (INV-B2/M2) |
| **System-managed temporal state** | `effective_to`, `superseded_at`/`superseded_by_id`, `committed_at` | chain construction | chain construction |
| **Derived-persisted snapshots** | `cost_per_worker_minute` (basis); every `*_snapshot`, term `amount_minor`, `production_budget_minor`, `allowed_worker_minutes` (evaluation) | canonical calculator at write time | never (committed) / never (basis rate changes only via new version) |
| **Operational facts** | `step_state_records`, `task_steps.total_working_seconds` | existing pipeline | existing pipeline (untouched, HC-3) |
| **Derived-recomputable** | live budget status (§8.1), `ItemCostResult` rows | read-time queries / replay-safe worker handler | any replay |

Rules: derived values are never accepted from any API request (schemas simply lack the
fields); missing inputs are never inferred (no expected price ⇒ no evaluation — never a
zero-budget evaluation, R-9); facts and their interpretations never share a column.

---

## 6. Calculation contracts (canonical path)

One pure module, `app/beyo_manager/domain/item_economics/` (no I/O,
`architecture/08_domain.md`), owns every formula. Commands call it and persist its
outputs; queries and the result handler reuse its consumption/variance functions.
All arithmetic in `Decimal`; §6.6 pins precision.

### 6.1 Term amounts (per term, in minor units)

> **Superseded in detail by §6A.4 (round 3, M-4).** The `value × 100` row below assumed
> a single `value` column in major currency units; A3 replaced it with
> `fixed_amount_minor`, so no major→minor conversion and no quantization remain for
> `fixed_amount`. §6A.4 is the authority; the table is kept as the round-0 statement.

| `calculation_type` | `amount_minor` | Requires |
|---|---|---|
| `percentage_of_expected_sale_price` | `expected_sale_price_minor × value / 100`, quantized to integer minor units | — |
| `fixed_amount` | `value × 100` (major → minor), quantized | value in the evaluation's currency |
| `item_purchase_cost` | `purchase_cost_minor` | item purchase cost present, else validation error |

### 6.2 Production budget

`production_budget_minor = expected_sale_price_minor − Σ amount_minor`
(non-deleted terms of the model version). **May be negative** — a negative budget is a
true statement ("this item cannot economically support production work"), stored as-is,
surfaced as infeasible; never clamped silently (mechanism gate pins presentation).

### 6.3 Cost per productive worker-minute (per basis version, derived-persisted)

`cost_per_worker_minute = (fixed_monthly_cost_minor / 100) / (monthly_paid_hours × planning_utilization_percent / 100 × 60)`

> **Superseded by §6A.3 Q2 (round 3, M-5).** The rate is denominated in **minor units**
> per worker-minute (A2), so the leading `/ 100` is gone. Underflow and zero-rate guards:
> §6A.6.

Monthly figures appear only here, as configured inputs — no calendar-month arithmetic
exists anywhere in the domain (§2.4 "month is undefined"). Worker count appears nowhere
(HC-5): the spreadsheet's per-worker intermediate multiplied worker count back out, so
the model stores the economically meaningful aggregate directly (raw §2).

### 6.4 Allowed worker-minutes

`allowed_worker_minutes = (production_budget_minor / 100) / cost_per_worker_minute`
(negative when the budget is negative).

> **Superseded by §6A.3 Q3 (round 3, M-5).** With the rate in minor units the `/ 100`
> is gone: `allowed_worker_minutes = production_budget_minor / cost_per_worker_minute_minor`,
> quantized 2 dp against the **persisted** rate.

### 6.5 Consumption, remaining, variance (derived, never stored except in the result)

> **Superseded by §6A.8 (round 3, M-5, M-14).** `consumed_cost_minor` loses its `× 100`
> and derives from **seconds**, not from the quantized minutes; `percent_consumed` is
> `null` (never 0 or 100) when `allowed ≤ 0`; the two variances are independent and may
> differ by one minor unit from each other's implied value.

- `actual_worker_seconds = Σ task_steps.total_working_seconds` over the task's
  non-deleted steps (§8.1 defines the bucket policy).
- `actual_worker_minutes = actual_worker_seconds / 60`.
- `consumed_cost_minor = actual_worker_minutes × cost_per_worker_minute_snapshot × 100`,
  quantized to integer.
- `remaining_worker_minutes = allowed − actual`; `percent_consumed = actual / allowed ×
  100` (undefined when `allowed ≤ 0` → surfaced as infeasible/overrun, never
  divide-by-zero).
- Variances in the result: `allowed − actual` (minutes) and
  `production_budget_minor − consumed_cost_minor` (money).

### 6.6 Precision, rounding, currency

Intermediates unquantized `Decimal`; persisted derived values quantized
`ROUND_HALF_EVEN` — money to integer minor units, rates to 4 dp, minutes to 2 dp
(matches storage types and the repo's banker's-rounding precedent in `_cost_minor`).
**Currency consistency rule:** the evaluation's currency = the item's current
valuation currency (§4.7A), which must equal the basis version's currency; a missing
valuation or a mismatch is a validation error at evaluation time (no workspace default
currency exists to fall back on, §2.1). All three enum currencies have 2-decimal minor units, so ×100 stays
correct. Analytics remain currency-naive as today — documented inherited limitation
(compensation intention R-9 reasoning, shared).

> **Extended by §6A.2 and §6A.9 (round 3, M-6, M-13).** The equality is **three-way**
> (valuation = basis = cost model, A4). ROUND_HALF_EVEN is this domain's own decision,
> passed explicitly at each of the five quantization sites — `_cost_minor` is not a
> precedent for it (it inherits the ambient context), and the repo's only explicit
> quantize rounds HALF_UP.

### 6A. Canonical calculator contract (round 3 — governs where §6.1–6.6 are prose)

One pure module owns every expression below. Where this section and §6.1–6.6 differ,
**this section governs**; §6.1–6.6 remain as the readable statement of intent.

#### 6A.1 Input types and canonicalization at the module boundary

| Input class | Type crossing the boundary | Canonicalization | On violation |
|---|---|---|---|
| money (prices, costs, fixed amounts, budgets) | `int`, minor units — what SQLAlchemy `Integer` returns | none; never converted to Decimal until it enters an expression, never to `float` | `TypeError` at the guard |
| rates / percentages | `decimal.Decimal` — what SQLAlchemy `Numeric` returns under asyncpg | none | `TypeError` at the guard |
| JSON-borne numerics (request layer, before the module) | parsed `Decimal(str(v))` | never `Decimal(v)` on a float | `ValidationError` |
| seconds | `int` (`task_steps.total_working_seconds` is `Integer NOT NULL default 0`, `models/base/aggregate_metrics.py:6`) | none | `TypeError` |
| enums | Python enum **members** | compared as members, never by `.value` string | `TypeError` |
| absent input | — | **never coerced to 0** (R-9) | the named `ValidationError` of §6A/§7A |

The module contains a `float` guard on entry: a `float` reaching money or rate
arithmetic is the one way HC-6 can be violated invisibly, and the only routes in are a
hand-built test fixture or an unparsed JSON body (charter rule 3 — the invariant is
proven with the object types production holds).

**Persisted configuration numerics (round 11, R11-1 — owner card, phase-4
projection B1):** a request-borne numeric destined for a `Numeric` column is
**canonicalized to the column's exact scale in the request model — quantized
`ROUND_HALF_EVEN` (§6A.2's domain rule; the upholstery precedent quantizes but
rounds HALF_UP and is NOT followed for rounding mode) — before ANY derivation reads
it.** PostgreSQL rounds silently on scale overflow, so deriving from the unrounded
request value stores a rate that disagrees with its own persisted inputs and
falsifies §6A.11's theorem for that row (verified: `173.456` hours → stored
`173.46`, but Q2 from the raw value gives `12.0107` vs `12.0105` from the stored).
Owner decision: **round-then-derive** (never refuse over-precise entries); every
derived value comes from the canonicalized inputs, so a stored basis and its stored
rate agree by construction.

#### 6A.2 Decimal context and rounding — explicit, never ambient

Every quantization passes `rounding=ROUND_HALF_EVEN` **explicitly**. The module never
mutates the global decimal context, and **runs its arithmetic inside a
`decimal.localcontext()`** (round 8, R8-2): an explicit `rounding=` argument
neutralizes an ambient rounding change, but `Decimal.__truediv__` and `.quantize()`
read `getcontext().prec` — a lowered ambient precision turns the division sites into
`InvalidOperation` unless a local context pins precision. "Never relies on the global
context" is therefore realized by construction, not by hope.

*Correction to §6.6's citation (address corrected round 8):* the repo has no explicit
banker's-rounding precedent. The step-cost computation (local `cost_minor` inside
`_recompute_step_time_totals`, `services/tasks/analytics/process_step_transition.py:231-233`)
calls `.to_integral_value()` with no argument — it inherits ROUND_HALF_EVEN from
Python's default context by accident, not by decision. The only *explicit* quantize in the repo
rounds the other way (`ROUND_HALF_UP`,
`services/commands/upholstery/requests/__init__.py:17`). ROUND_HALF_EVEN therefore
stands as this domain's own decision (money quantized at scale, no systematic upward
drift), not as an inherited convention.

#### 6A.3 The five quantization sites — a closed list

Every other value is exact integer arithmetic. No intermediate is quantized.

| # | Site | Expression | Target | Persisted in |
|---|---|---|---|---|
| **Q1** | term amount (percentage type only) | `(Decimal(expected_sale_price_minor) * percent_value / Decimal(100))` | integer minor units | `item_cost_evaluation_terms.amount_minor` |
| **Q2** | cost per worker-minute | `Decimal(fixed_monthly_cost_minor) / (monthly_paid_hours * planning_utilization_percent / Decimal(100) * Decimal(60))` | 4 dp | `production_cost_basis_versions.cost_per_worker_minute_minor` |
| **Q3** | allowance | `Decimal(production_budget_minor) / cost_per_worker_minute_minor` | 2 dp | `item_cost_evaluations.allowed_worker_minutes` |
| **Q4** | actual minutes | `Decimal(actual_worker_seconds) / Decimal(60)` | 2 dp | `item_cost_results.actual_worker_minutes` |
| **Q5** | consumed cost | `Decimal(actual_worker_seconds) / Decimal(60) * cost_per_worker_minute_minor_snapshot` | integer minor units | `item_cost_results.consumed_cost_minor` |

**Q3 consumes the quantized, persisted Q2 value** (not the unrounded intermediate) and
**Q5 consumes the evaluation's snapshot of it** — that is what makes HC-7's
re-derivation reproduce stored values bit for bit (6A.11).
**Q5 derives from seconds, not from Q4's output:** `actual_worker_minutes` is a display
projection and is an input to nothing except `variance_worker_minutes`. Rounding the
same quantity twice is the classic drift the result table would show as a wandering
øre.

#### 6A.4 Term types — total over (type × column presence)

| `calculation_type` | `percent_value` | `fixed_amount_minor` | `amount_minor` | Requires |
|---|---|---|---|---|
| `percentage_of_expected_sale_price` | NOT NULL, ≥ 0, ≤ 999.999 | NULL | **Q1** | — |
| `fixed_amount` | NULL | NOT NULL, ≥ 0 | `= fixed_amount_minor` (copied; no arithmetic, no rounding) | currency equality (6A.9) |
| `item_purchase_cost` | NULL | NULL | `= purchase_cost_minor` of the evaluation | `purchase_cost_minor` non-NULL, else `ITEM_COST_PURCHASE_COST_REQUIRED` |

Any other combination of NULL/NOT NULL is rejected **twice**: at term creation
(request + DB CHECK) and again by the calculator before use, so a row written by a
future path cannot silently produce a wrong `amount_minor`. Terms have no order; the
budget's sum is over `int`s and is therefore order-insensitive by construction — that
is proved, not asserted (charter rule 5).

**Percentage base — the gross price (gate card 2 answered, R4-2).** `percent_value` is
applied to `expected_sale_price_minor` **exactly as entered**: the *gross* expected
sale price, no conversion of any kind. The owner confirmed this and repositioned the
semantics: percentage terms are **manager-controlled planning allocations**, not
statutory tax calculations — the domain answers "how much of the expected selling
price does management want to reserve for this economic category?", never "what tax
amount must be declared for this sale?". A term's **name carries no calculation
semantics**: a term named "VAT reserve" with `percent_value = 15.00` on a 4,000 kr
expected price reserves exactly 600 kr; it is not a statutory VAT engine.
**Presentation rule (binding on API field docs, the living-docs page, and every
frontend surface):** a percentage term must never be presented as computing the legally
payable tax amount. Actual VAT treatment — including Swedish margin taxation (VMB) for
qualifying second-hand goods — is an accounting concern outside this implementation;
a future accounting integration may introduce legally derived tax amounts or new
`calculation_type`s without changing this allocation's semantics (§13 deferral stands).
Documentation guidance retained: a manager encoding a statutory 25 % VAT-on-net as a
reserve on the gross price enters **20.00**, and the docs name the base explicitly so
that translation is done once, by the manager, at term setup.

#### 6A.5 Budget

`production_budget_minor = expected_sale_price_minor − Σ amount_minor` over the
evaluation's **snapshot term rows** (never the live term rows). Exact integer
arithmetic; no quantization. Empty term set ⇒ budget = expected price. Negative
permitted and stored as-is (§6.2, A8).

#### 6A.6 Rate (Q2) and its underflow guard

Denominator > 0 by the §4.3 CHECKs; numerator > 0 by A1. **But the quantized result can
still be 0.0000** (a small fixed cost over a large capacity), which would make §6A.7
divide by zero at every later evaluation. Contract: after Q2, `rate == 0` ⇒
`ValidationError ITEM_COST_RATE_UNDERFLOW` at basis-version creation, *and* CHECK
`cost_per_worker_minute_minor > 0` on the column (A2). The derived value is never
accepted from an API request (§5).

#### 6A.7 Allowance (Q3)

`allowed_worker_minutes = Q3(production_budget_minor, cost_per_worker_minute_minor)`.
Negative when the budget is negative. Never clamped.

#### 6A.8 Consumption, remaining, variance

- `actual_worker_seconds`: §8A.1.
- `actual_worker_minutes`: Q4. `consumed_cost_minor`: Q5.
- `remaining_worker_minutes = allowed_worker_minutes − actual_worker_minutes` — exact
  2 dp subtraction.
- `percent_consumed`: `allowed_worker_minutes > 0` ⇒
  `(actual_worker_minutes / allowed_worker_minutes * 100)` quantized 2 dp;
  `allowed_worker_minutes ≤ 0` ⇒ **`null`** plus status `infeasible` (§11A.4). Never 0,
  never 100, never a division guarded by `try/except` — the branch is on the value.
- Variances: `variance_worker_minutes = allowed − actual` (2 dp, exact);
  `variance_cost_minor = production_budget_minor − consumed_cost_minor` (integer,
  exact). These are two independent quantities: `variance_cost_minor` may differ from
  `variance_worker_minutes × rate` — **bound corrected round 8 (R8-1):** the
  discrepancy scales with the rate, ≈ `0.01 × rate + 0.5` minor units (both `allowed`
  (Q3) and `actual_worker_minutes` (Q4) carry 2-dp rounding error the multiplication
  amplifies — ~3 minor units at rate `400.0000`, ~8 at `1000.0000`; the earlier
  "up to one minor unit" was measured only at rates below 6). Pinned as correct and
  deliberately unreconciled, so no future reviewer "reconciles" them; any test
  asserts an exact difference for its seeded fixture, never the general bound.

#### 6A.9 Currency — resolution order and the three-way equality

1. Load the item's current `ItemValuation` (INV-V1). None ⇒ `ITEM_COST_ITEM_UNVALUED`.
2. The evaluation's currency **is** `valuation.currency` (NOT NULL by schema). There is
   no other source: the request never carries a currency, no workspace default exists
   (§2.1), and no fallback is permitted.
3. Assert `valuation.currency == basis_version.currency == cost_model_version.currency`
   (A4). Any inequality ⇒ `ITEM_COST_CURRENCY_MISMATCH`, naming both sides and which
   pair failed. Enumerated as three criterion rows (valuation≠basis, valuation≠model,
   basis≠model), not one sampled row.
4. All three enum values are 2-decimal ISO currencies. Adding a 0- or 3-decimal currency
   to the enum changes minor-unit arithmetic and is a `calculation_version` bump
   (6A.10), not an enum edit.

Consequence, stated so nobody rediscovers it as a bug: with one active group (§7.4),
a workspace can only evaluate items priced in that group's basis currency; items in
another currency get status `currency_mismatch` and no evaluation — never a converted
number (no rate source exists anywhere in the repo).

#### 6A.10 `calculation_version` — the contract's identity

A module constant `CALCULATION_VERSION: int` (v1 = 1), stamped on every evaluation
(§4.5) and every result (A7). **Bump when** any of: a Q1–Q5 target or rounding mode
changes; the term type set or any per-type formula changes; the budget / allowance /
consumption / variance formulas change; the currency rule changes; the §8A.1 bucket
policy changes. **Never bump for**: renames, storage widening that cannot change a
value, API shape, or documentation. Stored rows are never recomputed. Re-derivation
(6A.11) asserts `row.calculation_version == CALCULATION_VERSION` before comparing —
a mismatch skips the comparison, it does not fail it.

#### 6A.11 Snapshot completeness — the closed set (HC-7)

**Theorem.** Given *only* an evaluation row and its term rows — dereferencing no FK,
reading no live configuration — these are exactly reproducible:
`cost_per_worker_minute_minor_snapshot` (from `fixed_monthly_cost_minor_snapshot`,
`monthly_paid_hours_snapshot`, `planning_utilization_percent_snapshot` via Q2),
`production_budget_minor` (from `expected_sale_price_minor` and the term rows'
`amount_minor` via 6A.5), `allowed_worker_minutes` (via Q3), and every term's
`amount_minor` (from `calculation_type`, `percent_value`, `fixed_amount_minor`,
`expected_sale_price_minor`, `purchase_cost_minor` via 6A.4).

**The closed set** an evaluation must therefore carry: `expected_sale_price_minor`,
`purchase_cost_minor`, `currency`, `fixed_monthly_cost_minor_snapshot`,
`monthly_paid_hours_snapshot`, `planning_utilization_percent_snapshot`,
`cost_per_worker_minute_minor_snapshot`, `calculation_version`, plus one term row per
applied term carrying `name`, `calculation_type`, `percent_value`,
`fixed_amount_minor`, `amount_minor`. The FK columns (`cost_model_version_id`,
`production_cost_group_id`, `production_cost_basis_version_id`) and the episode
snapshots (`task_type_snapshot`, `return_source_snapshot`) are **provenance and
typing** — they are not inputs to any derivation, and no re-derivation may read them.

The re-derivation is a pure function `rederive(evaluation_row, term_rows) -> (rate,
budget, allowed)` used by the HC-1/HC-7 test (§14 test 2) on ORM instances, not dicts.

**Mismatch outcome (round 9, R9-1 — owner card, phase-3 review):** when a stored
value disagrees with its own re-derivation, `rederive` returns the named
**`REDERIVE_MISMATCH`** structured result (naming the disagreeing fields and both
values) — it **never raises a `ValidationError`** and no user-facing error identity
exists for it. A snapshot disagreeing with itself is a data-integrity event, not a
reader's mistake: calling services (phases 7–8) log/escalate the marker at error
level and the read still renders. Same carrier family as `REDERIVE_SKIPPED`.

**Input-class totality (round 10, R10-1 — owner card, phase-3 re-review; L5):**
"never fails the read" is total over `rederive`'s input, enumerated:
(i) **value disagreement** — stored derived value ≠ re-derived value;
(ii) **malformed term snapshot** — an invalid type×column shape (incl. NULL typed
values and duplicate `item_purchase_cost` rows);
(iii) **malformed evaluation snapshot** — a zeroed/invalid stored rate or missing
snapshot field.
All three classes return the integrity marker result; **no `ValidationError`
escapes `rederive` on any path** — the calculation-path guards (§6A.4, §6A.6)
still raise for live calculation, but `rederive` catches/converts them into the
marker payload. **Cascade pinned:** a mismatched stored rate also yields a derived
`allowed_worker_minutes` entry (the allowance re-derives from the rate) — both
entries are reported, by design. **Payload shape pinned (R10-2):** every mismatch
entry carries the same four keys — `field`, `rederived_value`, `stored_value`,
`error` — with `error = None` for plain value disagreements and the converted
exception text for malformed-input conversions; callers never key defensively.

---

## 7. Temporal semantics & mutation operations

### 7.1 Configuration chains (basis versions, model versions)

Same contract as the sibling compensation intention §7 (same idioms, one authority for
the pattern): granularity **calendar date**, half-open `[from, to)`; creating a new
version atomically closes the open one at the new `effective_from` (must be > the open
version's `effective_from`, ≤ today), inserts the new open version with
calculator-derived values, all in one command transaction. Future-dated versions
deferred (no scheduler; same R-5 rationale). **Resolution rule for this domain:** an
evaluation resolves each chain to the version applicable **on its creation date** and
snapshots the values. There is no resolution-by-work-date anywhere (unlike
compensation): the committed evaluation freezes the economics for the whole episode —
that is the product semantics of "committed" (R-6).

### 7.2 Committing an evaluation (create / supersede)

> **Step order corrected by §7A.1 / §7B.1 (round 3, M-1).** Steps 2 and 3 below are in
> the wrong order: inserting the new committed row before closing the previous one
> violates INV-E1's non-deferrable partial unique on every second commit. §7B.1 is the
> procedure to build; the narrative below is kept for readability.

Atomically, in one command transaction:
1. Resolve inputs: task (must be non-deleted, non-terminal), its active PRIMARY
   `TaskItem` (its item is the evaluation's `item_id`), expected sale price (request
   override or the item's current valuation — required), purchase cost (request
   override or the current valuation — required iff the model has an
   `item_purchase_cost` term), currency (§6.6), open cost-model version and basis
   version (§7.4).
2. Run the canonical calculator; insert the evaluation (kind = committed,
   `committed_at = now`) + its term snapshot rows.
3. Close the previous current committed evaluation for the task, if any:
   `superseded_at = now`, `superseded_by_id = new` (INV-E1's partial unique arbitrates
   the concurrent-commit race — exactly one wins).
4. **Mirror rule (round 1 form):** if the committed price/cost differ from the item's
   current valuation, create a superseding `ItemValuation` row to match
   (system-authored, stamped with the committing user) — the current valuation always
   shows the currently-operative figures (R-15 as amended by R1-2).
5. History record + `item_economics:evaluation-committed` workspace event (repo event
   conventions).

Per card 3 (answered yes): steps 1–5 also run automatically inside `create_task` when
the workspace is evaluable and the item has a current valuation with an expected
price. A failure of the auto path never fails task creation — the task is simply
created without an evaluation ("not configured" status); the explicit commit surface
exists regardless.

### 7.3 Projections

`kind = projection` rows: created from (a) the current committed evaluation's inputs,
(b) another projection, or (c) scratch — with any inputs overridden; computed by the
same calculator; listed/compared per task; soft-deletable freely. Promotion = §7.2
with the projection's inputs and `promoted_from_id` set. Projections never appear in
worker payloads, analytics, or results (HC-2) — enforced structurally: every
operational read filters `kind = 'committed' AND superseded_at IS NULL`.

### 7.4 Basis selection (v1 rule)

*(Round 12: SUPERSEDED for group resolution by §7C — selection is by the item's
major category, one active group per category. This section's zero/many refusal
discipline survives inside §7C.2.)*

The evaluation uses the workspace's **single active production cost group**. Zero
active groups, or more than one → `ValidationError` naming the condition — never a
guess (R-8). The schema supports many groups; selection among them (per item category,
per task's sections…) is a deferred product decision listed in §13. Group section
membership does not affect selection in v1 — it exists for future observed-utilization
and per-section analytics attribution.

### 7.5 Deletion guards

- Config versions: soft-deletable only while **no evaluation references them**
  (mistaken-entry escape hatch); referenced versions are corrected by superseding.
- Committed evaluations: never deletable (INV-E2). A wrong commitment is superseded by
  a corrected commitment — the wrong decision remains part of history (raw §21's
  auditability questions all answer from the chain).
- Projections: freely soft-deletable.
- Groups: soft-deletable only with no non-deleted basis versions and no active section
  memberships.
- Valuations (round 1): superseded rows are never deletable (they are the price
  history); the current row is soft-deletable, returning the item to "unvalued".

### 7A. Chain construction, resolution and races (round 3)

Four chains share one shape — the three of §15 plus the valuation chain of §4.7A. They
are specified once here and referenced everywhere.

| Chain | Scope | "Open" predicate | Partial unique on the open predicate | Close columns |
|---|---|---|---|---|
| basis versions | per group | `effective_to IS NULL AND is_deleted = false` | `(production_cost_group_id)` — INV-B1 | `effective_to` |
| model versions | per workspace | `effective_to IS NULL AND is_deleted = false` | `(workspace_id)` — INV-M1 | `effective_to` |
| committed evaluations | per task | `kind = 'committed' AND superseded_at IS NULL AND is_deleted = false` | `(task_id)` — INV-E1 | `superseded_at`, `superseded_by_id` |
| valuations | per item | `superseded_at IS NULL AND is_deleted = false` | `(item_id)` — INV-V1 | `superseded_at`, `superseded_by_id` |

#### 7A.1 Statement order is load-bearing — **this corrects §7.2's step order**

A partial unique index is not deferrable and is enforced per statement. §7.2 as written
inserts the new committed evaluation (step 2) *before* closing the previous one
(step 3) — at that instant two rows satisfy INV-E1's predicate, so the INSERT raises
`UniqueViolation` on **every** second commit of a task, not only under concurrency.
The mandatory order for all four chains is:

- **S1** `UPDATE <table> SET <close columns> = :now WHERE <scope> AND <open predicate>`
  → `rowcount ∈ {0, 1}`. **rowcount 0 is legal** (first row of a chain) and is never an
  error. rowcount > 1 is impossible (the partial unique).
- **S2** `INSERT` the new open row; `flush()` (client_id needed for S3).
- **S3** *(evaluation and valuation chains)* `UPDATE <old> SET superseded_by_id =
  :new_id WHERE client_id = :old_id` — executed iff S1 reported 1.

Never insert before S1. Never use `ON CONFLICT DO NOTHING` / `DO UPDATE` on these
indexes: the conflict is the arbiter, and swallowing it is how a second "current" row
appears.

#### 7A.2 Race arbitration — the index is the only arbiter

No command in this repo sets an isolation level, so all of this runs at PostgreSQL's
default **READ COMMITTED**. Two concurrent advances of the same chain: both run S1; the
second blocks on the first's row lock, re-evaluates its predicate after the first
commits, and reports **rowcount 0**. It must **not** read that as "nothing to
supersede, so I may insert freely" — that inference is exactly what the index exists to
refute. Its S2 then blocks on the winner's uncommitted index entry and raises
`IntegrityError` at the winner's commit.

Contract: commands let that `IntegrityError` surface as `ConflictError` with the
chain's identity (`ITEM_COST_CONCURRENT_COMMIT`, `..._CONCURRENT_VALUATION`,
`..._CONCURRENT_BASIS_VERSION`, `..._CONCURRENT_MODEL_VERSION`). Never caught, never
retried, never logged-and-continued.

Criterion (charter rule 2's error-contract clause): one test per chain on the **DB
conflict path** — two sessions, both past S1, both attempting S2 — asserting (a) exactly
one row satisfies the open predicate afterwards and (b) the loser's exact error
identity. A test that only exercises the application pre-check does not satisfy this.

#### 7A.3 Resolution predicate, its date frame, and its totality

`applicable(v, D) := v.is_deleted = false AND (v.effective_from IS NULL OR
v.effective_from ≤ D) AND (v.effective_to IS NULL OR v.effective_to > D)`.

- **D is the UTC calendar date** of the evaluation's creation instant
  (`datetime.now(timezone.utc).date()`). Every date bucket in this repo is UTC and
  `workspaces.time_zone` is read by no analytics code (§2.4). A workspace at UTC+2
  committing at 01:00 local resolves against the previous UTC date — accepted and
  pinned, because `effective_from ≤ today` is checked in the same frame, so the two can
  never disagree with each other.
- **Theorem (v1):** `applicable(v, today)` selects exactly the chain's open row. Every
  version is created with `effective_from ≤ today` (7A.4) and construction is
  contiguous half-open with exactly one open row, so no other row can cover today.
  v1 resolution is therefore "the open row", and no gap in a chain's past can be hit.
- Resolution runs **once**, at evaluation creation, and is snapshotted. The date rule is
  never re-run against an existing evaluation: a version created later the same day
  would resolve differently, and the snapshot — not the chain — is the authority
  (HC-1).

#### 7A.4 Version-creation admission — total over the open row's state

| Open version | Requested `effective_from` | Outcome |
|---|---|---|
| none | NULL | accept (unbounded-past first version) |
| none | ≤ today | accept |
| none | > today | reject `..._EFFECTIVE_FROM_FUTURE` |
| `effective_from IS NULL` | NULL | reject `..._EFFECTIVE_FROM_REQUIRED` |
| `effective_from IS NULL` | ≤ today | accept; closes the open row at that date |
| `effective_from IS NULL` | > today | reject `..._EFFECTIVE_FROM_FUTURE` |
| `effective_from = d0` | NULL | reject `..._EFFECTIVE_FROM_REQUIRED` |
| `effective_from = d0` | ≤ d0 | reject `..._EFFECTIVE_FROM_NOT_AFTER_OPEN` |
| `effective_from = d0` | d0 < d ≤ today | accept |
| `effective_from = d0` | > today | reject `..._EFFECTIVE_FROM_FUTURE` |

Complete over {no open row, open with NULL from, open with dated from} × {NULL, ≤ d0,
(d0, today], > today}. Same table for both configuration chains.

#### 7A.5 §7.4 selection — total enumeration of the failure modes

*(Round 12: the group-resolution rows are SUPERSEDED by §7C.2 — resolution is by
the item's major category; the zero/many refusal discipline and rows 3-6 survive
per the selected group. Pointer only; no renumbering.)*

Evaluated in this order; first match wins.

| # | Workspace / group state | Outcome |
|---|---|---|
| 1 | 0 non-deleted production cost groups | `ITEM_COST_NO_COST_GROUP` |
| 2 | ≥ 2 non-deleted groups | `ITEM_COST_AMBIGUOUS_COST_GROUP`, naming the count and the group ids (never "first one wins", R-8) |
| 3 | exactly 1 group, no non-deleted basis version at all | `ITEM_COST_NO_BASIS_VERSION` |
| 4 | exactly 1 group, versions exist but none applicable today (the open row was soft-deleted) | `ITEM_COST_NO_BASIS_VERSION` — deliberately the same identity: indistinguishable to the caller, and the repair is the same (create a version) |
| 5 | no version of the workspace's cost model applicable today | `ITEM_COST_NO_COST_MODEL_VERSION` |
| 6 | all present | proceed |

Rows 1–5 are five distinct fixtures in the acceptance criteria, each the sole reason its
outcome holds (charter rule 2's companion clause).

#### 7A.6 Deletion guards (§7.5) — the race, closed

FK RESTRICT restrains a hard delete, not a soft delete, so §7.5's guard is
application-level and racy: a commit that resolved a version before a concurrent soft
delete commits would reference a deleted version. Contract: the delete command takes
`SELECT … FOR UPDATE` on the version row and re-runs the "no evaluation references
this version" existence check **inside** that lock; the commit path (7B.1 step 3)
resolves configuration versions with `SELECT … FOR SHARE`. The consequence of skipping
this is benign in value terms (everything is snapshotted) but would make §7.5's
guarantee false, so it is enforced rather than downgraded to a hope.

### 7B. The commit transaction (round 3 — governs §7.2)

#### 7B.1 Ordered procedure

One transaction. Steps 6–8 are 7A.1's S1/S2/S3.

1. Load the task `FOR UPDATE`; admit per 7B.2.
2. Resolve the active PRIMARY `TaskItem` (7B.3).
3. Resolve the cost model version and the basis version (7A.3, 7A.5) with `FOR SHARE`
   (7A.6).
4. Resolve the item's current valuation **`FOR UPDATE`** (round 16, D4 — the row
   lock is held for the whole transaction: a concurrent `set_item_valuation`
   blocks at its own S1 until this commit ends, then supersedes the mirror row,
   so the manager's figures win under both orderings; see 7B.4's corrected race
   clause), the inputs, and the currency (6A.9).
5. Run the calculator (§6A); nothing is written before this point.
6. **S1** — close the task's current committed evaluation, if any.
7. **S2** — insert the evaluation (`kind = committed`, `committed_at = now`) and its
   term snapshot rows; flush.
8. **S3** — set the previous row's `superseded_by_id`.
9. Mirror rule (7B.4); history record (round 16, R16-1: a **TASK-linked**
   `HistoryRecord` — `entity_type = TASK`, `entity_client_id = task.client_id`,
   `change_type = UPDATED`, precedent `resolve_task.py:61` — so the commit appears
   in the team task flow via `get_task_flow_records`'s always-on TASK condition
   with **no** flow-service change, no enum migration, and no new serializer;
   `from_value`/`to_value` carry the superseded/new figures);
   `item_economics:evaluation-committed` event dispatched **after** the
   transaction (repo convention: `event_bus.dispatch` outside `maybe_begin`,
   e.g. `resolve_task.py:102-104` — span narrowed round 16).

#### 7B.2 Task admission — total over `TaskStateEnum` (all 8 values)

| Task state | Explicit commit | Auto path (§7.2, card 3) |
|---|---|---|
| `PENDING` | accept | accept |
| `ASSIGNED` | accept | accept |
| `WORKING` | accept | n/a (task is new) |
| `STALLED` | accept | n/a |
| `READY` | accept | n/a |
| `RESOLVED` | reject `ITEM_COST_TASK_TERMINAL` | n/a |
| `FAILED` | reject `ITEM_COST_TASK_TERMINAL` | n/a |
| `CANCELLED` | reject `ITEM_COST_TASK_TERMINAL` | n/a |
| any state, `is_deleted = true` | reject `NotFound` | n/a |

`STALLED` is accepted although nothing writes it today (§2.2) — an accept-list keyed to
current writers would silently start rejecting commits the day someone implements it.

#### 7B.3 PRIMARY-item binding — the exact predicate (§9.1's flag)

Let `P` := the task's active PRIMARY task-item (`role = PRIMARY AND removed_at IS
NULL`) — at most one, by `uix_task_items_primary_active`.

- **At commit:** `P` absent ⇒ reject `ITEM_COST_NO_PRIMARY_ITEM` (never commit against
  a task with no item). Otherwise `evaluation.item_id := P.item_id`.
- **At read** (status query) and **at result time**, `item_binding` is one of exactly
  three values:
  - `bound` — `P` exists and `P.item_id == evaluation.item_id`;
  - `mismatched` — `P` exists and `P.item_id != evaluation.item_id` (the item was
    swapped after the commit);
  - `detached` — no active PRIMARY task-item.
- The result row always records `evaluation.item_id`, never the live `P`: the economics
  belong to the item the decision was made for. Consumption is task-scoped either way
  (§8A.1), so a swap re-attributes nothing — which is precisely why the state is
  surfaced as a flag rather than silently repaired. Re-committing binds the new PRIMARY
  (§9.1).

#### 7B.4 Mirror rule — the exact predicate

Because the currency has no source other than the valuation (6A.9 step 2), a commit
against an unvalued item is impossible; a current valuation `V` therefore always exists
at step 4. Let `E` be the evaluation being committed.

- **Fires iff** `(E.expected_sale_price_minor, E.purchase_cost_minor) !=
  (V.expected_sale_price_minor, V.purchase_cost_minor)`, compared as a Python tuple on
  loaded ORM values (`None == None` is True) — **never** as a SQL predicate, where
  `NULL != NULL` would make every unpriced-purchase-cost commit look like a change.
  Currency can never differ (it came from `V`).
- **What the mirror row carries:** *both* figures from `E` — the overridden one and the
  one inherited from `V` — plus `V`'s currency; `created_by_id` = the committing user.
  It is written through the valuation chain's S1→S2→S3 (7A.1), in the same transaction.
- **On the auto path the predicate is false by construction** (the inputs came from
  `V`): no mirror row is written at task creation. Stated so no implementer writes a
  "helpful" duplicate.
- **Race (corrected round 16, D4 — two orderings exist at READ COMMITTED):**
  a valuation writer still **uncommitted** when the mirror's S1 runs is arbitrated
  by INV-V1 (7A.2); the losing transaction is the whole commit, which fails with
  `ITEM_COST_CONCURRENT_VALUATION`. A writer that **commits between step 4's read
  and step 9** is NOT arbitrated by the index: the mirror's S1 predicate would
  re-evaluate against the committed state, silently close the manager's brand-new
  row, and supersede it with figures derived from the *older* valuation — no error
  on either side. That ordering is closed by step 4's `FOR UPDATE` on `V`: the
  concurrent `set_item_valuation` blocks at its own S1 until this transaction
  ends, then supersedes the mirror row afterwards — the manager's price wins under
  both orderings and "the current valuation always shows the currently-operative
  figures" (§7.2 step 4) is true again. A commit never half-applies — there is no
  state in which an evaluation exists without its mirror row, or vice versa.

#### 7B.5 The auto path inside `create_task` — savepoint, not try/except

`create_task` runs a single transaction (`maybe_begin`, `create_task.py:76`), and in
PostgreSQL a failed statement aborts it. "A failure of the auto path never fails task
creation" (§7.2) is therefore **unimplementable with a bare `try/except`** — by the time
the handler runs, the transaction is already poisoned and the task INSERT will not
commit either.

- **Pre-checks first, exceptions never as control flow (restated round 16, D7 —
  total by construction).** The auto path runs **iff** the task has an active
  PRIMARY item **and**
  `resolve_item_economics_status(valuation, selection, model_terms) is
  EconomicsStatusEnum.NOT_EVALUATED` — the same registered resolver the phase-5
  preview and the phase-8 status query consume, whose `ITEM_READINESS_PRECEDENCE`
  ends in `NOT_EVALUATED`, making the pre-check total over every §11A.4 state.
  (The round-3 enumeration omitted `currency_mismatch` and the no-item case; both
  fell through into the exception path this clause forbids.) Any pre-check false
  ⇒ no evaluation, no error, task created; the reason is the `EconomicsStatusEnum`
  value, logged verbatim (round 16, D17 — the §11A.4 auto-path status line) as
  `"item_economics.auto_commit_skipped | task_id=%s item_id=%s status=%s"` at
  INFO, and recomputable later from the status query.
- **Execution** is wrapped in `async with ctx.session.begin_nested():` (SAVEPOINT —
  precedent `services/commands/users/reconcile_worker_shift_state.py:278`). Any
  exception rolls back the savepoint only, is logged (round 16, D17 — verbatim
  shape, repo pipe-delimited idiom) as
  `"item_economics.auto_commit_failed | task_id=%s item_id=%s error=%s"` at
  WARNING with the exception class as `error`, and is not re-raised.
- **Event and history on the auto path (round 16, D9).** A subordinate command
  must NOT dispatch events (`06_commands_local` subordinate-command event rule),
  so the auto path appends `item_economics:evaluation-committed` to
  `create_task`'s `pending_events` **only after the savepoint block exits
  normally** — the parent dispatches after its own transaction, and a rolled-back
  savepoint can never leave a queued event behind. The TASK-linked history record
  (7B.1 step 9's form) is written inside the savepoint. No existing statement in
  `create_task` moves; the file's additions are the savepoint block plus this
  conditional append.
- **Named mutation** (charter rule 11): replacing `session.begin_nested()` with a plain
  `try/except` around the same body in
  `services/commands/tasks/create_task.py` (definition site) must turn red a test in
  which the evaluation INSERT itself raises (the 7A.2 conflict path, or a patched
  calculator) and which asserts the task row is committed and readable afterwards.

#### 7B.6 Inline valuation at item birth (round 18, R18-1 — ships as phase 8B)

The task-creation item block (`FindOrCreateItemInput`) accepts the VALUATION
vocabulary: `expected_sale_price_minor`, `purchase_cost_minor`, `currency`.
**(a) Shape corrected (8B projection L1 — the original "mirroring
`ItemValuationRequest` exactly" was false: on the PUT surface `currency` is
unconditionally required; here the whole block is optional):** all three
fields OPTIONAL; `ge=0` on both amounts; `currency` required **iff** either
amount is present. This deliberately DIVERGES from `ItemValuationRequest` —
the PUT block IS the request, this one is an optional sub-block. A
currency alone (no amounts) is accepted and ignored: 200, NO valuation row
(the DB CHECK `ck_item_valuations_amount_present` makes a currency-only
row impossible, and a 422 would reproduce §10A.3's recorded
currency-input hazard); nothing is inferred, P-B holds. The legacy names
(`item_value_minor`/`item_cost_minor`/`item_currency`) remain REJECTED with
`ITEM_MONEY_MOVED` — the new names are the only accepted carriers, and the
bridge validator stays FIRST in definition order (never shadowed by the
new vocabulary's own validation).

- **On a NEWLY CREATED item** with any of the trio present: valuation
  version 1 is written through the registered chain writer
  (`write_item_valuation_chain_in_session`, `_common.py`) inside
  `create_task`'s transaction, BEFORE the §7B.5 auto-commit savepoint — the
  existing pre-check then sees the valuation and the task is priced in one
  call. R13-1 applies (first save IS version 1, no confirmation);
  `created_by_id` = the creating user; the valuation audit event fires as
  on the PUT path.
- **(b) On a MATCHED EXISTING item (CORRECTED by owner card, R18-3 —
  branch B):** inline prices REFUSE **iff the item carries a CURRENT
  valuation** (`superseded_at IS NULL AND is_deleted = false`, INV-V1) —
  a task creation never changes a standing price; the registered identity
  is `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` and the refusal aborts the
  WHOLE request (nothing persists — task, item mutations, TaskItem all
  roll back). A matched item with NO current valuation ACCEPTS them: a
  never-valued item writes version 1 (R13-1); an item whose prices were
  all deleted or superseded writes the NEXT version through the chain —
  an explicit manager-typed act, deliberately distinct from R15-1's
  migration rule, which stays untouched.
- No new status, no new read surface, no schema change: the mechanism is
  request vocabulary + one guarded write reusing shipped machinery.

### 7C. Category-driven group selection (round 12 — supersedes §7.4's and §7A.5's group-resolution rows)

Owner decision (2026-08-12): the workspace's cost groups are resolved by the
item's **major category** (wood | seat), not by being the workspace's only group.
Ships as phase 4B, before v1.

**7C.1 Schema.** `production_cost_groups.major_category` — **NOT NULL** enum copy
of the items domain's major-category vocabulary (WOOD | SEAT; PG type reused with
`create_type=False`, ownership stays on its owning items-domain column — R2-1
rule; exact type name pinned by the phase-4B registry row). **INV-G3: one active
group per (workspace, major_category)** — partial unique
`uix_production_cost_groups_major_category_active` (`WHERE is_deleted = false`).
The name-uniqueness (INV of §4.1) stands unchanged. Migration note: the table is
unshipped to production; the column lands NOT NULL with a pre-flight refusing if
uncategorizable rows exist in the target DB (dev rows are test residue — the
migration reports, never guesses a category).

**7C.2 Selection rule (total, ordered — replaces "the single active group"):**
1. Resolve the task's PRIMARY item's major category from the item's
   denormalized `item_major_category_snapshot`. **Absent → status/refusal
   `item_missing_major_category`** (new §11A.4 value; owner pin 2: economics
   precondition only — item creation elsewhere is untouched).
2. Resolve the workspace's active group **for that category**. None →
   `not_configured_no_cost_group` (message names the category). More than one →
   `not_configured_ambiguous_cost_group` — structurally unreachable under INV-G3,
   retained as the classifier's total-order defence row.
3. The chosen group's open basis version resolves as before (§7A.3/§7A.5 rows 3–4
   unchanged, now per the selected group).
The evaluation snapshots the chosen group/basis exactly as before (§4.5) — no
history semantics change.

**7C.3 Vocabulary (§11A.4 amended):** `item_missing_major_category` joins the
ordered group-2 reasons and **evaluates FIRST among them** (the category is a
precondition of every later config check); the list is now 12 values, order:
`item_missing_major_category` → `not_configured_no_cost_group` →
`not_configured_ambiguous_cost_group` → `not_configured_no_basis_version` →
`not_configured_no_cost_model_version` → `item_unvalued` → … (rest unchanged).
The workspace-level configuration-status query becomes **per-category**: one
evaluability block per major category (group? open basis?) plus the shared
cost-model fields — the onboarding UI shows wood and seat readiness separately.

**7C.4 Commands.** Group create requires `major_category`; group update may not
change it once any basis version exists (a category flip would silently reprice —
correction is delete-and-recreate under the §7.5 guards); the INV-G3 conflict is
dual-path like its siblings (registry identity, phase-4B row).

---

---

## 8. Actuals integration

### 8.1 What counts as consumption

`actual_worker_seconds` for an episode = Σ `total_working_seconds` over the task's
non-deleted `task_steps`. This inherits, by construction (HC-3): concurrency-averaged
batch dilution (§2.3), exclusion of marked-wrong time (`inaccurate_*` never counts),
exclusion of open intervals until settled, and per-record attribution.

**Bucket policy (R-5): WORKING seconds only.** Paused and ended-shift time do not
consume the allowance. Rationale: planning utilization already prices non-productive
paid time into the rate — a minute of pause is paid for by the utilization discount in
§6.3's denominator; charging it again against the item's allowance would double-count
it. This **deliberately diverges** from the salary-cost convention
(`total_cost_minor` costs working+paused): the two numbers answer different questions
(what did labor cost vs. how much productive allowance was consumed) and must never be
presented as the same metric (named silent-failure hazard for the mechanism gate).

### 8.2 Relationship to existing aggregates (raw §24)

This domain **consumes** `AggregateMetricsTimeMixin.total_working_seconds` and builds
no duplicate aggregate machinery (live per-task sums over one task's steps are cheap
reads). It does **not** read, extend, or replace `total_cost_minor` (salary-based,
compensation's remit) and does not touch the four analytics stat tables. If the
compensation project later changes how `total_cost_minor` is priced, nothing here
moves — the only shared dependency is the time columns, whose semantics neither
project alters.

### 8.3 Final result (episode close)

*(Round 6: terminal transitions are no longer the only producers — §8B governs; the
result is computed at every episode boundary, READY entries and reopens included,
and "final" means terminal-computed. This section's handler description stands.)*

The three terminal-transition commands (`resolve_task`, `fail_task`, `cancel_task`)
gain one line in their existing side-effect block: `create_instant_task` with a new
event type `PROCESS_ITEM_COST_RESULT` (routed to `queue:analytics`, repo outbox
conventions). The handler:
- loads the task's current committed evaluation — **none ⇒ no result row** (an
  unevaluated episode is "not configured", never a zero-budget result, R-9);
- recomputes actual seconds from `task_steps` (same read as §8.1), derives §6.5 values
  at the evaluation's snapshot rate;
- **upserts by `task_id` (recompute-and-SET)** — at-least-once delivery and replays
  converge, matching the existing analytics idempotency scheme; late-arriving
  analytics (a straggling `PROCESS_STEP_TRANSITION`) self-heals on any replay of the
  result event.
The result is a convenience snapshot: authoritative facts remain the step records and
the evaluation (HC-7). Expected values (evaluation) and actual values (result) live in
different tables and are never merged into one row's mutable columns (raw §10).

### 8.4 New invariant (testable)

After an episode's result exists, superseding config versions, editing the item's live
fields, or replaying any analytics reconcile leaves the result byte-identical on
recompute — because every input is snapshotted and the time source is append-only
settled history. (The item-economics twin of compensation's §8.3 replay invariant.)

### 8A. Consumption, result and replay contracts (round 3)

#### 8A.1 The consumption read — one expression

```
actual_worker_seconds(task) :=
    SELECT COALESCE(SUM(task_steps.total_working_seconds), 0)
    FROM task_steps
    WHERE task_steps.task_id = :task_id AND task_steps.is_deleted = false
```

- `total_working_seconds` is `Integer NOT NULL default 0`
  (`models/base/aggregate_metrics.py:6`), so the SUM is NULL only over an empty step
  set. `COALESCE(…, 0)` is mandatory: a task with no steps consumes 0, and here 0 is a
  true statement about consumption, not an inferred input (contrast R-9 — an *absent
  price* is never 0).
- **Step state is not filtered.** PENDING and SKIPPED steps contribute their 0. The only
  filter is `is_deleted` — deleting a step removes its time from the episode, which is
  the intended and only way an episode's consumption can decrease.
- `inaccurate_*` is never read (marked-wrong time is already excluded upstream);
  `total_pause_seconds` and `total_ended_shift_seconds` are never read (R-5).
- The value is always read from the rollup columns and **never** recomputed from
  `step_state_records` by this domain (HC-3: one time-truth with one owner — the
  concurrency sweep).

#### 8A.2 The two-cost-numbers boundary (§8.1's named hazard, made structural)

`task_steps.total_cost_minor` (salary-priced, working **+ paused**, compensation's
remit) and `item_cost_results.consumed_cost_minor` (allowance-priced, working only)
answer different questions and differ for the same episode by construction.

1. They **never appear in the same serialized object**.
2. No item-economics payload carries any money field sourced from `TaskStep`.
3. No step or task payload embeds an economics money field — the §13 "only if cheap"
   embedded budget block carries **minutes and percent only, for every role**.
4. They are never summed, differenced, compared or reconciled anywhere in code, and no
   query projects them into one column.
5. The living-docs page states both definitions side by side, with the divergence and
   its reason (R-5).

Criterion: a test asserting the money-key sets of the two payload families are
disjoint; named mutation — adding `total_cost_minor` to the item-economics status
payload (`services/queries/item_economics/…`, definition site) must turn it red.

#### 8A.3 The result handler — idempotency contract

- Event: `TaskType.PROCESS_ITEM_COST_RESULT`, routed to `queue:analytics`
  (`services/infra/execution/task_router.py`), emitted with `create_instant_task`
  inside the existing side-effect block of `resolve_task` / `fail_task` /
  `cancel_task` (the same transaction, outbox semantics).
- **Payload carries `{workspace_id, task_id}` and nothing else** — a frozen dataclass
  beside `domain/execution/payloads/step_transition.py`. No derived value ever travels
  in a payload; the handler re-resolves everything, which is what makes a replay of an
  old event produce today's correct answer.
- Handler: open `task_db_session()`; load the task (non-deleted and in a §8B-admitted
  state — round 6 supersedes the original "terminal only" admission — else log and
  return); resolve the **current committed evaluation at handler time**
  (`kind = committed AND superseded_at IS NULL AND is_deleted = false`) — none ⇒ log and
  return, **writing and deleting nothing** (R-9); compute 8A.1 and §6A.8; upsert.
- **Upsert:** `INSERT … ON CONFLICT (task_id) DO UPDATE SET <derived columns>`. The
  `unique (task_id)` of §4.6 is the idempotency key; there is no other dedupe key and no
  delivery-count assumption. Because the evaluation is resolved at handler time, a
  commit that lands between the terminal transition and the handler run is picked up by
  that run or by any later replay.
- "Result exists but its evaluation is gone" is unreachable: committed evaluations are
  never deletable (INV-E2). The handler has no delete path.

#### 8A.4 Replay identity — the named column set (resolves §8.4 against `computed_at`)

§8.4's "byte-identical" is **over this set**: `evaluation_id`, `item_id`,
`actual_worker_seconds`, `actual_worker_minutes`, `consumed_cost_minor`,
`variance_worker_minutes`, `variance_cost_minor`, `task_closed_at`,
`calculation_version`. **`computed_at` is refreshed on every recompute and is excluded
from every identity assertion**, as is any `updated_at`-shaped column. Without this
exclusion the invariant is false as written and the test that "proves" it would have to
be weakened silently — which is how replay invariants die.

#### 8A.5 Time that settles after the episode closes (gate card 1 answered: re-emit, R4-1)

Verified in code: `transition_step_state` guards only on the **step** being terminal
(`services/commands/task_steps/transition_step_state.py:150`); nothing forbids
transitioning a step whose **task** is already terminal, and the three terminal commands
do not close open step records. So a worker who closes a straggling step after the task
was resolved changes `task_steps.total_working_seconds` — and nothing re-emits the
result event. §8.3's "self-heals on any replay" is true only if a replay happens, and in
v1 nothing produces one. The stored result then disagrees with a live recompute
**forever**, silently.

**Contract (gate card 1 answered re-emit, R4-1; guard widened round 6, §8B):** in
`handle_process_step_transition`, inside the existing time-bearing branch after
`_recompute_step_time_totals`, enqueue one `PROCESS_ITEM_COST_RESULT` for the step's
task **iff** that task's state is **READY or terminal**. Recompute-and-SET makes
redundant emissions free. This is the only change to an existing analytics handler; it adds no
time mechanism and reads no new source (HC-3 intact). The result is therefore always
the truth about the episode, and §8.4's replay invariant holds as stated.

Branch B ("results freeze at close") was **rejected by the owner's card-1 answer**;
recorded for provenance only, not to be built. Consequences of the choice: the
operational CLI re-emit stays in §13's "only if cheap" (it is a convenience, not the
repair path), and §14 test 18 builds the branch-A row.

#### 8A.6 The live status query

Read-time only; nothing stored (§8.1). Returns: the `EconomicsStatusEnum` (§11A.4), the
committed evaluation's snapshot values, live consumption (§6A.8), `item_binding`
(7B.3), and — **whenever a result row exists** — the result, labelled with the
boundary it was computed at (`task_state_snapshot` + `computed_at`). (Corrected
round 17, R17-1, owner card 1: the earlier "when the episode is closed" clause
predated round 6 — READY is when the item is finished working, so the figures
show from the first READY entry, days before the manual resolution; "final" stays
distinguishable through the boundary label.) Every
operational read carries the literal filter `kind = 'committed' AND superseded_at IS
NULL AND is_deleted = false` (HC-2); §14 test 4's named mutation is the deletion of that
filter at its call site.

### 8B. Result lifecycle — computed at every episode boundary (round 6)

Owner correction (2026-08-12): READY is the machine-detectable completion of the work
(all steps terminal); RESOLVED/FAILED/CANCELLED are manual acts that may lag it by
days. Terminal-only results (R-10's original boundary) would mean the machine never
writes the result at actual completion. The result is therefore a
**continuously-converging snapshot of the episode's economics, refreshed at every
lifecycle boundary**; "final" = computed at a terminal state (`task_state_snapshot`
terminal, `task_closed_at` set). R-10's *reasons* stand — READY still has no
timestamp and still reopens — which is exactly why the row snapshots its boundary
instead of pretending READY is a close.

**8B.1 Emission points (the complete list; all feed the same §8A.3 handler):**

1. **Every sanctioned entry into READY** — one emit hook inside
   `maybe_evaluate_task_ready` (`services/commands/tasks/_task_state_transitions.py`),
   which is the only route into READY (all its callers — step transition core,
   batch transition, remove_task_step, and force_task_ready's sweep — inherit it).
2. **Every reopen** — one emit hook inside `maybe_reopen_task_to_working` (same
   file; sole production caller today is add_task_steps, which is also how section
   reassignment flows): the row refreshes immediately, its snapshot flipping to
   `working`, so a stored result never claims READY while work is ongoing (owner pin
   2, 2026-08-12).
3. **The three terminal commands** (unchanged from §8.3/§8A.3).
4. **Post-boundary time settlement** — §8A.5's guard, widened to
   `state ∈ {READY} ∪ terminal`: time that settles while the episode sits at READY
   or after close refreshes the row.

**8B.2 Handler admission — total over all eight `TaskStateEnum` values:**
`WORKING | READY | RESOLVED | FAILED | CANCELLED` → compute and upsert (WORKING is
admitted solely so the reopen refresh is honest);
`PENDING | ASSIGNED | STALLED` → log and return, writing nothing (no v1 emission
point can fire there; a replayed or operator-re-emitted event must not fabricate a
result for an unstarted episode — R-9 discipline). Every recompute stamps
`task_state_snapshot` with the task's state **at handler time** and copies
`task.closed_at` (NULL when not terminal). The §8A.3 upsert, idempotency key, and
payload are unchanged; the §8A.4 replay-identity column set gains
`task_state_snapshot` and `task_closed_at` (both are functions of re-resolved state,
so replays converge exactly as before).

**8B.3 Reopen convergence invariant (extends §8.4):** for any interleaving of
READY entries, reopens, terminal transitions, and straggler settlements, the stored
row always equals the handler's recompute at the last-fired boundary; a task that
re-reaches READY after a reopen converges onto the new totals with no special case
(recompute-and-SET; no delete path).

**8B.4 Cross-episode accumulation (owner-confirmed reading, no change):** an item
returning on a future task (return / pre_order; matched by article_number/SKU through
`find_or_create_item`) is the same item row on a new episode: new evaluation
(auto-path per card 3, or explicit), new result row keyed by the new task. Lifetime
economics remain read-time summation over the item's episodes (§11) — results never
merge across tasks, and item economics stay decoupled from any single task (R-3's
episode chain, reaffirmed).

---

## 9. Multi-item, batch, and section allocation

### 9.1 Multi-item tasks (raw §17)

The de facto and DB-enforced reality is one PRIMARY item per task (§2.2). **v1 binds
each evaluation to the task's PRIMARY item**; RELATED items carry no economics
(matching the only existing per-item analytics precedent, which deliberately ignores
RELATED). The extension seam is structural: evaluations key (task_id, item_id), so a
future multi-item treatment adds evaluations for further items plus an explicit
allocation rule for splitting step time between co-worked items — an explicitly
deferred product decision (§13), not an accident of worker count (raw §16). Guard in
v1: committing an evaluation when the task's PRIMARY item differs from the
evaluation's item (item swapped after commit) is surfaced by the status query as a
mismatch flag, and re-commit binds the new PRIMARY (mechanism gate pins the exact
predicate).

### 9.2 Batch work (raw §17's batch questions — answered by the existing sweep)

One state record belongs to one step of one task; simultaneous work on several items
happens only via one worker holding several batchable steps open across tasks, and the
sweep already splits the wall clock `1/k` across them (§2.3). Therefore batch-work
cost allocation between items is **already solved at the time layer** — each item's
task accrues exactly its diluted share, and Σ across items = wall clock. This domain
adds no further allocation arithmetic (R-11).

### 9.3 Section-level display split (raw §2, §16)

The allowance is the aggregate constraint; any per-section display division is
presentation only. v1 ships **no stored per-section expected allocation**: the UI may
divide `allowed_worker_minutes` by the task's section count for orientation, labelled
as illustrative. Configured/derived section ratios are deferred (§13); the model keeps
the door open because actual per-section consumption is already measurable
(`task_steps.working_section_id` + time columns) for any future ratio source, including
`item_issues` severity signals (the raw's "given the item issues recorded").

---

## 10. Migration & compatibility

### 10.1 Schema migration

New tables + enums (autogenerate + hand-fix per `architecture/30_migrations.md`
checklist; partial uniques via `postgresql_where` idiom `595e7b840926:44,50`).
Evaluation history starts empty; existing tasks need no backfill (an unevaluated
episode is legal forever).

### 10.2 Legacy column migration (round 1 — replaces the round-0 validate-in-place plan)

Card 1's answer removes the legacy columns instead of ratifying them:

1. **Data (journaled, per exemplar `97b60e06d42a`):** every non-deleted item with
   either amount non-NULL gets one current `ItemValuation` row copying
   value/cost/currency verbatim. **Pre-flight refusal:** a row carrying an amount with
   NULL `item_currency` (legal today, §2.1) blocks the migration with a row report —
   currency is never guessed (charter: missing data is never inferred). Journal
   table, post-condition counts, exact `downgrade` — all four per the exemplar.
2. **API bridge:** monetary fields removed from the item create / patch /
   find-or-create request schemas, from `create_task`'s nested item body, and from
   both item serializers (`domain/items/serializers.py:103-105`,
   `domain/tasks/serializers.py:104-105`). The specialized valuation endpoint (§11)
   becomes the only money surface.
3. **Column drop:** a follow-up migration (never a rewrite of an applied one, charter
   rule 7) drops `item_value_minor`, `item_cost_minor`, `item_currency`. The PG enum
   type `item_currency_enum` is retained for `item_upholstery_requirements`;
   type-creation ownership (`create_type` flags) moves accordingly.

Breakage surface: both serializers and their five embedding query payloads (§2.1
read census), request schemas (`items.py:68-70,91-93,113-115`, `tasks.py:105-106`),
OpenAPI mirrors (`routers/README.md`), frontend types (typed but never rendered —
§10.4, low risk), `Application_contracts/planning/item/item_models.md` §"Value and
cost semantics", and the archived frontend handoff examples (historical, not
updated). Coordinator routes these with the §2.6 items.

### 10.3 Compensation seam (raw §25, HC-4)

The interface between the two domains is exactly one surface:
`ProductionCostBasisVersion`'s input facts (`fixed_monthly_cost_minor`,
`monthly_paid_hours`). Today an admin types them. When the compensation domain ships,
a derivation can propose or populate new basis versions from compensation aggregates
(Σ employer cost of the group's workers) **through the same command path** — new
version, same calculator, same snapshots; nothing in item-economics changes. The two
intentions were shaped against the same conventions on the same day to keep this seam
clean; neither reads the other's tables in v1.

### 10.4 Frontend impact (grounded)

No manager screen renders item economics today — the fields are typed end-to-end but
terminate before render (`features/items/types.ts:102-135` computes formatted values
nothing consumes). Landing zones already stubbed: `features/static_costs_configuration`
/ `items_configuration` / `working_sections_configuration` (type-only stubs), the
settings screen pattern (`features/settings/`), and the worker's
`LastActiveStepCard.tsx` live timer (`:390-407`) for a budget indicator. v1 backend
ships the APIs; frontend work is scoped separately, and the removed item money fields
disappear from frontend schemas with the §10.2 bridge. Card 4 (answered): worker-facing
surfaces carry **minutes and percentages only**; money is ADMIN/MANAGER; the existing
leak — `serialize_step` exposing `total_cost_minor` to WORKER via
`GET /tasks/{id}/steps` and `GET /working-sections/{id}/steps` — is **closed in this
project** (redaction per the `serialize_item_worker_light` precedent,
`serializers.py:411-441`).
*(Round 3: the leak is wider than the two endpoints named here — the complete,
verified census is §11A.2.)*

### 10A. Legacy migration and API-bridge contracts (round 3)

#### 10A.1 Journal scope — what reversibility actually requires

The §10.2 step-3 migration drops the three columns for **every** `items` row, including
soft-deleted ones — which step 1 (non-deleted only) never copied anywhere. A journal
covering only the migrated rows therefore makes `downgrade` lossy for exactly the rows
nobody would notice.

Contract: the data migration journals **every `items` row with any of the three columns
non-NULL, regardless of `is_deleted`**.

`item_valuation_migration_journal(item_client_id PK, item_value_minor, item_cost_minor,
item_currency, valuation_client_id NULL)` — `valuation_client_id` is set only for rows
that also produced an `ItemValuation` (i.e. non-deleted items with ≥ 1 amount).
`downgrade` restores all three columns on every journaled row, deletes the valuations it
created (by `valuation_client_id`, never by a predicate over `item_valuations`), then
drops the journal. Per exemplar `97b60e06d42a`.

Post-conditions asserted inside `upgrade` (exemplar discipline):
1. journal row count == count of items with any of the three columns non-NULL;
2. created-valuation count == count of **non-deleted** items with ≥ 1 non-NULL amount;
3. every created valuation has `superseded_at IS NULL`, `is_deleted = false` and a
   NOT NULL currency.

Idempotent by predicate: the copy INSERT excludes items that already have a current
valuation, so re-execution affects zero rows.

**R14 lettered clauses (2026-08-14, phase-6 projection r0; owner answers folded):**

- **(a) Post-condition 2 restated over the journal (D3):** created-valuation
  count == count of journal rows with `valuation_client_id IS NOT NULL` ==
  count of ELIGIBLE non-deleted items with ≥ 1 amount that had **no current
  valuation at entry**. The original pc2 contradicted the idempotency clause
  (a re-run creates 0 where pc2 expected N and aborts). C2 additionally runs
  the copy TWICE and asserts the second pass is a no-op **without aborting**;
  and one C1 row covers the phase-5 collision (item with legacy money AND a
  current valuation → journaled, `valuation_client_id` NULL, existing
  valuation untouched).
- **(b) Attribution — P3 pre-flight (owner, 2026-08-14):** migrated valuations
  carry the **item's own `created_by_id`**; where an item holds an amount with
  a NULL `created_by_id` (legal, `item.py:55`), the migration **refuses before
  any write** with a row report naming the offending `client_id`s (P3, beside
  P1/P2). No system user is invented; nothing is guessed. Owner context: the
  valuation functionality is unshipped and every write-path check measures the
  legacy population empty — P3 is totality armor, unreachable on any known
  database.
- **(c) Deliberately deleted prices stay deleted (owner, 2026-08-14;
  predicate CORRECTED R15-1, 2026-08-14):** an item whose only valuation is
  soft-deleted is **not** re-valued (the deletion is a decision somebody made;
  §11A.5(d)/R13-2's intent). The clause as first folded contradicted itself —
  its predicate (`NOT EXISTS (… AND is_deleted = false)`) made exactly those
  items ELIGIBLE (phase-6 review B2, executed). Corrected eligibility
  predicate, verbatim: **`NOT EXISTS (SELECT 1 FROM item_valuations v WHERE
  v.item_id = i.client_id)`** — an item with ANY valuation row (current,
  superseded, or deleted) has entered the new system and is never re-valued;
  only never-valued items are eligible. INV-V1's full predicate remains what
  the index enforces — state both. The migration only ever writes the FIRST
  row of a chain, so §7A.1's S1 close does not apply and `superseded_by_id`
  is never set.

#### 10A.2 Pre-flight — total over (amounts × currency)

| `item_value_minor` | `item_cost_minor` | `item_currency` | Outcome |
|---|---|---|---|
| NULL | NULL | NULL | skipped; not journaled (nothing is destroyed by the drop) |
| NULL | NULL | set | **journaled, no valuation** — the §4.7A CHECK requires ≥ 1 amount. Not a refusal, and explicitly not a zero-amount valuation |
| ≥ 1 set (any ≥ 0) | | NULL | **REFUSE — P1**, with a row report. Currency is never guessed (§10.2, charter: missing data is never inferred) |
| ≥ 1 set, any < 0 | | set | **REFUSE — P2**, with a row report. `items` carries no CHECK today (§2.1), so a negative legacy amount is reachable and would abort mid-migration against the §4.7A `≥ 0` CHECKs |
| ≥ 1 set, all ≥ 0 | | set | journaled + one current `ItemValuation` (non-deleted items) / journaled only (soft-deleted items) |

P1 and P2 both run **before any write**, each reporting its offending `client_id`s.
**R14: the table gains P3** — ≥ 1 amount set (any) with the item's
`created_by_id` NULL → **REFUSE — P3**, row report, before any write
(attribution is never guessed; §10A.1(b)).

#### 10A.3 API bridge — the removal must be loud, not silent

Verified: no item or task request model sets `extra="forbid"` (the repo's only
`ConfigDict(extra="forbid")` is `routers/api_v1/images.py:36,49`), so pydantic's default
`ignore` applies. Simply deleting the three fields from the four request schemas
(`services/commands/items/requests/__init__.py:195-197, 246-248, 460-462`;
`services/commands/tasks/requests/__init__.py:36-38`) means a client that still sends a
price receives **200 with the money silently discarded** — the precise failure mode this
domain exists to remove. **R14 evidence correction (D15):** the earlier claim that "the
manager app sends `item_value_minor: null` on every task creation
(`use-create-task.ts:84-85`)" was a misread — those lines are the optimistic cache
entry, not the request body. The real body builder
(`normalize-task-form-payload.ts:88-101`, `buildItemFields`) **omits both amounts
entirely** and serialises `item_currency` as an absent key; no component renders a
currency input. Production task creation sends all three keys ABSENT. The
reject-iff-present-and-non-NULL shape stays (it is strictly safer); the real recorded
risk is: if a currency input is ever mounted, task creation 422s the moment a user
picks one.

Contract: for one release the four schemas keep a validator that raises
**`beyo_manager.errors.validation.ValidationError`** (the repo's `DomainError` — R14/D1:
NEVER a pydantic-side `ValueError`, whose message reaches the client mangled by the
parse helpers' field-locator prefix; the DomainError propagates unwrapped through
pydantic, reaches `run_service`, and `build_err` emits
`{"error": "ITEM_MONEY_MOVED: …", "ok": false}` at 422 with the identity as the exact
leading token) **iff a removed key is present with a non-NULL value**; present-with-null
and absent both pass and are ignored. R14/D16: `model_fields_set` is inert for this
purpose (both non-reject outcomes pass, and the create-item route materialises every
key via `model_dump()` without `exclude_unset`) — the predicate is simply
`value is not None`. R14/D6: the four FastAPI ROUTER body models **retain** the three
keys for this release (deleting them there silently drops a client's price at the HTTP
boundary under pydantic's default `ignore` — the exact silent failure again); one
criterion row proves a non-NULL value SURVIVES the router body into the command
validator. The validator is deleted together with the keys in the phase that ships
after the frontend stops sending them — a sequencing note the planner owns, not a
permanent shape.

Criterion — three rows, exact outcomes: key absent ⇒ 200 and no write; key present and
null ⇒ 200 and no write; key present and non-null ⇒ 422 with the named message.

---

## 11. Operations & API surface

All workspace-scoped through the standard `router → run_service → command/query` seam;
role gates settled by cards 2 & 4 (round 1). Proposed surface (names to the planner's
registry):

**Item valuation (ADMIN/MANAGER — card 2):**
- **Set item valuation** — the specialized command/endpoint: creates the superseding
  current `ItemValuation` for an item (§4.7A) and returns the recomputed economic
  preview (budget + allowed worker-minutes under the current config — an ephemeral,
  non-persisted projection), so pricing and time-projection live in this domain's
  services rather than generic item CRUD (the owner's stated separation/scalability
  intent). Read: valuation history per item.

**Configuration (manager/admin):**
- CRUD production cost group + section membership (5-verb router per catalog pattern).
- Create basis version / create model version (chain semantics §7.1); list history per
  group / workspace; guarded delete (§7.5). No PATCH on versions — new version is the
  only change vector.
- Read "economics configuration status" (is the workspace evaluable: group? open basis?
  open model? — drives onboarding UI).

**Evaluations (manager/admin):**
- Commit evaluation for a task (§7.2 explicit path; auto path at task creation per
  card 3's answer).
- Create / list / delete projections for a task; promote projection.
- Read evaluation history for a task (committed chain + projections, term drill-down).

**Status (card 4: workers see minutes/percent only; money ADMIN/MANAGER):**
- Budget status for a task (and by item across tasks): committed evaluation values +
  live consumption (§6.5). The worker-facing variant returns minutes/percentages
  only — no monetary fields in its schema.
- Item lifetime economics (Σ episodes: per-task committed evaluation + result rows,
  typed by task_type/return_source snapshots) — read model only in v1.

**Worker handler:** `handle_process_item_cost_result` (§8.3).
**No standalone backfill script needed** (results self-heal by re-emitting the event;
an operational CLI re-emit is only-if-cheap, §12-adjacent — but see §8A.5 branch B,
which promotes it to must-ship).

### 11A. Money-exposure boundary and the status vocabulary (round 3)

#### 11A.1 The exposure predicate

A payload may carry monetary fields **iff the requesting identity's role is ADMIN or
MANAGER**. WORKER *and* SELLER are both excluded. Card 4's answer names ADMIN/MANAGER as
the money audience and SELLER is neither; its story spoke only of workers, so this is
recorded as a round-3 unilateral resolution for owner ratification, not as a decision
the owner already made. Consequence: a seller loses the step cost number they can see on
task detail today.

#### 11A.2 `total_cost_minor` exposure census — complete and verified (§10.4 named two of five)

`serialize_step` (`domain/tasks/serializers.py:152-177`) emits `total_cost_minor` and
has **five** call sites:

| # | Call site | Endpoint | Roles today | v1 |
|---|---|---|---|---|
| 1 | `services/queries/tasks/tasks.py:702` (`get_task`) | `GET /tasks/{task_id}` (`routers/api_v1/tasks.py:540-543`) | ADMIN, MANAGER, WORKER, SELLER | redact for WORKER + SELLER |
| 2 | `services/queries/tasks/list_task_steps.py:57` | `GET /tasks/{task_id}/steps` (`routers/api_v1/tasks.py:933-936`) | ADMIN, MANAGER, WORKER, SELLER | redact for WORKER + SELLER |
| 3 | `services/queries/working_sections/steps_list_payload.py:320` | `GET /working-sections/{id}/steps` (`routers/api_v1/working_sections.py:145-148`) | ADMIN, MANAGER, WORKER | redact for WORKER |
| 4 | `services/queries/working_sections/step_record_payload.py:208` | `GET /working-sections/steps/user-last-active` (`routers/api_v1/working_sections.py:111-113`) | ADMIN, MANAGER, WORKER | redact for WORKER |
| 5 | `services/queries/worker_stats/get_worker_daily_step_breakdown.py:436` | `GET /worker-stats/{user_id}/daily-steps` (`routers/api_v1/worker_stats.py:129-133`) | ADMIN, MANAGER | unchanged |

Sites **1 and 4 are round-3 findings** — §10.4 and research_context §5 name only 2 and
3. Site 4 is the worker's live step card (`LastActiveStepCard.tsx`), i.e. the most
frequently fetched worker payload in the app.

**Round-5 correction (phase-1 projection finding D1, verified 2026-08-12): the five
call expressions above are correct, but two of them are shared payload builders, and
the exposure surface is *endpoints*, not call expressions.** Site 3's builder
(`build_steps_list_payload`) and site 4's builder (`build_step_record_payload`) are
each called by more than one query service. The complete endpoint census is
**eight**, adding three the round-3 table missed:

| # | Via builder of site | Endpoint | Query service | Roles today | v1 |
|---|---|---|---|---|---|
| 6 | 3 | `GET /task-step-acknowledgments/reassigned-steps` (`routers/api_v1/task_step_acknowledgments.py:35`) | `task_step_acknowledgments/list_reassigned_steps.py:85` | ADMIN, MANAGER, WORKER | redact for WORKER |
| 7 | 4 | `GET /task-step-acknowledgments/pending` (`routers/api_v1/task_step_acknowledgments.py:74`) | `task_step_acknowledgments/list_pending_step_acknowledgments.py:75` | ADMIN, MANAGER, WORKER | redact for WORKER |
| 8 | 4 | `GET /worker-stats/last-interacted-steps` (`routers/api_v1/worker_stats.py:30`) | `worker_stats/list_workers_last_interacted_step.py:111` | ADMIN, MANAGER | unchanged (money stays; anti-blanket-redaction row like site 5) |

Endpoints 6 and 7 are live WORKER money exposures of exactly the kind card 4 ordered
closed. The exposure matrix over (endpoint × admitted role) is therefore **24 cells**.
Consequence for §11A.3's boundary: the flag is derived from the request identity
**once inside each shared builder** (both already receive `ctx`), so every endpoint
riding a builder — present and future — inherits the redaction; if a builder's flag
is ever instead threaded as a parameter, that parameter must itself be keyword-only
with **no default** (the fail-closed guarantee must sit at the level where new
callers actually appear). M4/M5 of the §11A.3 table apply at the builders' flag
derivation and must each also turn red the acknowledgment-endpoint rows riding that
builder (M4 → endpoints 3 and 6; M5 → endpoints 4 and 7).

#### 11A.3 The boundary declaration (charter rule 11)

The safeguard is a **declared field of the interface, failing closed**:

`serialize_step(step, *, include_monetary: bool)` — keyword-only, **no default**.
Omitting it raises `TypeError` at the call, so a sixth call site cannot inherit money by
silence. `total_cost_minor` is **absent from the dict** when `include_monetary` is False
(absent, not `null`: a null key still tells a worker that a cost number exists). Each
call site derives the flag from the request identity at the query boundary, never from
the step row.

Named mutations — file + definition-vs-call-site, one row per redacting site (charter
rules 2 and 11):

| # | Mutation | Site kind | Test that must turn red |
|---|---|---|---|
| M1 | give `include_monetary` a default of `True` in `domain/tasks/serializers.py::serialize_step` | definition | the test calling `serialize_step(step)` with no keyword and expecting `TypeError` |
| M2 | pass `include_monetary=True` at `services/queries/tasks/tasks.py:702` | call site | `GET /tasks/{id}` payload test under a WORKER identity, and under a SELLER identity |
| M3 | pass `include_monetary=True` at `services/queries/tasks/list_task_steps.py:57` | call site | `GET /tasks/{id}/steps` payload test under WORKER, and under SELLER |
| M4 | pass `include_monetary=True` at `services/queries/working_sections/steps_list_payload.py:320` | call site | `GET /working-sections/{id}/steps` payload test under WORKER |
| M5 | pass `include_monetary=True` at `services/queries/working_sections/step_record_payload.py:208` | call site | `GET /working-sections/steps/user-last-active` payload test under WORKER |

Site 5 keeps money and gets the complementary row: a MANAGER-identity test asserting
`total_cost_minor` is **present** (so a blanket redaction cannot pass unnoticed).

The same declared-field discipline governs this domain's own payloads: the worker-facing
budget status is a **separate query service whose serializer has no monetary keys at
all**, not a flag on the manager serializer (§11).

#### 11A.4 `EconomicsStatusEnum` — one code-owned vocabulary, total and ordered

*(Round 12: the vocabulary is amended by §7C.3 — `item_missing_major_category`
joins group 2 and evaluates FIRST among its reasons; the list is now 12 values.
Pointer only; §7C.3 governs.)*

Used identically by the budget status query, the valuation endpoint's preview, and the
auto-path log line. Evaluated in this order; first match wins.

1. **A current committed evaluation exists** (the configuration is irrelevant — the
   snapshot is self-sufficient, HC-1):
   - `infeasible` — `allowed_worker_minutes ≤ 0`;
   - `ok` — otherwise.
2. **No current committed evaluation** — the reason, in order:
   1. `not_configured_no_cost_group`
   2. `not_configured_ambiguous_cost_group`
   3. `not_configured_no_basis_version`
   4. `not_configured_no_cost_model_version`
   5. `item_unvalued`
   6. `item_missing_expected_price`
   7. `item_missing_purchase_cost` (only when the model carries an `item_purchase_cost`
      term)
   8. `currency_mismatch`
   9. `not_evaluated` — everything above is satisfied; nobody has committed yet.

Rules: for every value except `ok` and `infeasible`, the payload's numeric fields are
**`null`**, never `0` and never omitted — R-9's entire point is that "unknown" must not
be renderable as a decision. `percent_consumed` is `null` for `infeasible` and for every
status in group 2. The enum is code-owned (never a catalog row — the §2.4 catalog
lesson) and is the same enum in all three surfaces.

#### 11A.5 The valuation endpoint's preview (§11)

Ephemeral: computed by the same calculator, never persisted, given no `client_id`,
carrying the same status vocabulary. A preview creates nothing and supersedes nothing —
it is a pure function of the posted valuation plus the current configuration.

**R13-1 lettered clauses (2026-08-13, owner cards — phase-5 projection r0):**

- **(a) The preview lives under its own payload key** (`preview`), sibling to the
  persisted valuation in the response envelope, and is never merged with
  committed figures — no consumer may render a preview numeric as a decided one.
- **(b) Numerics carve-out to §11A.4's closing rule:** the null-numerics rule
  binds **non-computable** statuses. Inside the `preview` key, the computable
  preview state (`not_evaluated` — configuration resolved, valuation present,
  inputs sufficient) carries the fully computed `production_budget_minor` and
  `allowed_worker_minutes`. Every other status in a preview carries `null`
  numerics exactly as before — never 0, never a guess. Outside the `preview`
  key, §11A.4's closing rule stands unmodified.
- **(c) First save is version 1 — no confirmation:** the first
  expected-sale-price save on an item auto-creates valuation version 1; no
  confirm step exists anywhere in the flow. That version is the comparison
  baseline. (AMENDED round 18, R18-1: task creation now carries the OPTIONAL
  inline valuation trio per §7B.6 — the birth write flows through the same
  chain and R13-1 applies unchanged; the legacy money keys stay rejected,
  and the valuation ENDPOINT remains the only surface that can CHANGE an
  existing price.)
- **(d) Deleted valuations are hidden from the history read (R13-2):** the
  history query returns only non-deleted rows; deleting the current price is
  the escape hatch for a mistaken entry, and superseded rows (true history)
  are never deletable, so nothing real is lost. The DELETE response carries
  the status-only preview, whose status is **RE-RESOLVED through
  `resolve_item_economics_status` / the §11A.4 ordering — never hand-written**
  (corrected round 17, R17-2, owner card 2: one rule, no drift — a
  never-priced item and a deleted-price item must show the SAME status, so in
  an unconfigured workspace both read the missing-setup reason and in a
  configured workspace both read `item_unvalued`; the shipped
  `delete_item_valuation.py:44` literal is the drift and phase 8 corrects it,
  landing phase-5 review N2).

---

## 12. External-source strategy

None required — no external transport exists in this domain. Expected sale price and
purchase cost are manager-entered; production costs are manager-configured; actual sale
prices (Shopify orders) are explicitly unprocessed today (§2.1) and their future
ingestion is a deferred analytics input, not a v1 dependency. The source-evidence
protocol is satisfied vacuously (recorded so the mechanism-inventory gate does not
search for a missing evidence doc).

---

## 13. Scope ladder

**Must ship (v1):**
- All §4 tables + enums with INV-G1/B1/B2/M1/M2/E1/E2/**V1/V2**, the canonical
  calculator with §6 contracts, config chains + guarded deletes (§7),
  commit/supersede + mirror rule (§7.2) incl. the card-3 auto path, projections +
  promotion (§7.3), v1 basis selection rule (§7.4), live budget status query, final
  result event + idempotent handler (§8.3), **the `ItemValuation` table + specialized
  valuation endpoint with economic preview (§4.7A, §11)**, **the §10.2 legacy
  migration, API bridge and column drop**, **worker-payload money redaction incl.
  closing the `total_cost_minor` leak (card 4, §10.4)**, APIs of §11, tests (§14),
  living-docs page (`docs/domains/`) + archgraph delta in the same change,
  contract-gap routing (§2.6).

**Only if cheap:**
- Budget block embedded in existing step/task payloads (vs. dedicated status endpoint
  only) — respecting card 4.
- Operational CLI to re-emit `PROCESS_ITEM_COST_RESULT` for a task
  (`architecture/53_operational_cli.md` pattern). **Round 4 (R4-1):** stays here —
  gate card 1 answered re-emit (§8A.5 branch A), so results self-heal at the
  analytics seam and the CLI is a convenience, not the repair path.
- `note` field on committed evaluations; projection comparison endpoint (side-by-side).

**Explicitly deferred:**
- Section-level expected allocations / ratios (configured or issue-derived) and any
  per-section budget guidance (raw §2's "later implementation"; §9.3).
- Multi-item allocation beyond PRIMARY; any RELATED-item economics (§9.1).
- Multi-group basis selection rules; per-group rate analytics (§7.4).
  *(Round 12: category-driven selection is CONSUMED into v1 as §7C / phase 4B;
  per-task-section and other finer selection rules remain deferred.)*
- Observed utilization surfaces (per-worker ratio from shift records; per-section
  blocked on the §2.4 attribution gap) and planned-vs-observed comparisons.
- Actual sale price ingestion (Shopify orders) and realized-margin analytics.
- Aggregate manager dashboards (cost by section/category/period, lifetime rollups
  beyond the v1 read model); `working_section_daily_work_stats` reader work.
- Per-worker-minute cost terms and other new `calculation_type`s; static_costs
  absorption (the dormant table stays the seed for non-worker overheads).
- Future-dated config versions (needs the same scheduler compensation deferred).
- Currency-aware analytics.

When elegance and budget conflict downstream: cut from the bottom of must-ship's
periphery (auto-commit path, mirror rule, status embellishments) before touching
invariants, snapshots, or the canonical calculator — architecture is kept, scope is cut.

---

## 14. Testing priorities

Per charter rules (automated criteria; enumerate never sample; production-path
objects; exact expected outcomes; named mutations at named sites; teardown discipline
— the planner formalizes into criteria):

1. **Calculator table** — one row per term `calculation_type` (3) + missing-purchase-
   cost rejection + NULL-value-for-typed-term rejections; budget rows including a
   negative-budget case and a ROUND_HALF_EVEN tie at the minor-unit boundary; rate
   derivation rows (§6.3) with exact 4-dp expectations; allowance rows including
   negative; each row's fixture makes its own predicate the only reason the
   expectation holds.
2. **Snapshot immutability (HC-1)** — commit; then supersede the item's valuation and
   the model & basis versions; assert the committed evaluation and its term rows
   byte-identical; re-derive from snapshots reproduces stored values (HC-7).
3. **Commit chain & race** — supersession sets exactly one current (INV-E1) under
   concurrent commits on the exact DB conflict path (partial unique, not the
   pre-check); mirror rule fires only on price change; task in terminal state rejects
   commit.
4. **Projection isolation (HC-2)** — projections invisible to status query, worker
   payloads, and result handler; promotion copies inputs and leaves the projection
   unchanged; named mutation: "make the status query drop the `kind='committed'`
   filter" (file + call site named) must turn a specific test red.
5. **Consumption policy (R-5)** — fixture with one record per bucket
   (working / paused / ended-shift collapse / marked-wrong), each the sole
   discriminator: only the working row counts; assert against production rollup
   columns on real ORM instances.
6. **Batch dilution flow-through** — one worker, two batchable steps on two tasks,
   full overlap: each episode consumes exactly half the wall clock; Σ = wall clock.
7. **Result idempotency (§8.3/8.4)** — handler replay converges (recompute-and-SET);
   result without committed evaluation writes nothing; late analytics + replay
   self-heals; config supersession after close leaves recompute byte-identical.
8. **Config chains** — adjacent-pair boundary enumeration on `[from, to)` for both
   chains; one-open-row race on the partial unique; guarded deletes (§7.5) on the
   exact referenced-row path.
9. **Currency consistency** — missing-valuation and mismatch rejection rows
   (valuation vs basis).
10. **Basis selection** — zero groups / one group / two groups: exact outcomes per §7.4.
11. **Valuation validation** — negative amounts rejected at request layer AND DB CHECK
    (both paths, exact error contracts); both-amounts-NULL rejected; currency NOT NULL
    enforced.
12. **Valuation chain (round 1)** — supersession sets exactly one current (INV-V1)
    under concurrent writes on the exact DB conflict path; immutability of superseded
    rows (INV-V2); guarded-delete paths (§7.5); mirror rule creates a superseding row
    only when figures differ.
13. **Legacy migration round-trip (round 1)** — disposable DB only (charter rule 7):
    upgrade migrates every legacy amount into a current valuation verbatim; the
    pre-flight amount-with-NULL-currency case refuses with a row report; downgrade
    exact via journal; automated in-suite proxy for the lifecycle check.
14. **Worker redaction (card 4)** — worker-variant payloads contain no monetary
    fields; named mutation: "re-add `total_cost_minor` to the worker step payload"
    (file + serializer call site named by the planner) must turn a specific test red.
    *(Round 3: superseded in detail by §11A.3 — five call sites, five named mutations
    M1–M5 plus the MANAGER-present row; the planner enumerates all six.)*

**Round-3 additions (from the mechanism contracts):**

15. **Calculator boundary guards (§6A.1)** — a `float` for money or rate raises; `None`
    for a required input raises the named error, never yields 0; `Decimal(str(v))`
    parsing proven on a request-layer value with more decimals than the target scale.
16. **Rate underflow (§6A.6)** — a basis version whose quantized rate would be 0.0000 is
    rejected with `ITEM_COST_RATE_UNDERFLOW`; the DB CHECK rejects it too (both paths,
    exact error contracts).
17. **Chain statement order (7A.1)** — committing a second evaluation for a task that
    already has a current one succeeds; this row fails outright under §7.2's original
    insert-then-close order, which is why it is a criterion and not an assumption.
    Same row for the valuation chain.
18. **Post-close straggler (§8A.5)** — branch A (selected by gate card 1, R4-1):
    transitioning a step after its task is terminal converges the result row onto the
    new total. The branch-B row is not built (branch rejected, recorded in §8A.5).
19. **API bridge (10A.3)** — three rows: key absent / present-null / present-non-null,
    each with its one exact outcome.
20. **Migration journal (10A.1–10A.2)** — a soft-deleted item carrying an amount is
    journaled and restored by `downgrade` (the row a non-deleted-only journal loses);
    both refusal predicates P1 and P2 refuse with a row report; the currency-only row
    produces no valuation.
21. **Replay identity (8A.4)** — the named column set is unchanged across a replay while
    `computed_at` advances; asserting over the whole row instead must fail, proving the
    exclusion is real and not a convenience.

**Round-6 addition:**

22. **Boundary lifecycle (§8B)** — enumerated over the emission points: entry into
    READY writes the row (`task_state_snapshot = ready`, `task_closed_at` NULL);
    reopen refreshes it (`snapshot = working`); re-entry into READY after more work
    converges onto the new totals (8B.3); terminal transition finalizes
    (`snapshot` = the exact terminal state, `task_closed_at` set); straggler
    settlement while READY refreshes the row, while WORKING (mid-episode) emits
    nothing; a replayed event for a PENDING task with a committed evaluation writes
    nothing (8B.2 admission row).

---

## 15. Pre-implementation protocol

- **Mechanism-inventory: RUN (round 1, 2026-08-11).** Every mechanism below now has a
  contract in §4A / §6A / §7A / §7B / §8A / §10A / §11A. The gate is **held** only by
  the two owner decisions in §17; on their answers the next gate is
  **implementation-planner**. The original flag list, kept for traceability —
  silent-failure mechanisms flagged (charter rule 6): every §6 formula and its quantization points (percent units, major→minor,
  negative budget, divide-by-zero guard in percent-consumed); the §7.1 chain
  construction + partial-unique races (three chains: basis, model, evaluation); the
  §7.2 commit atomicity incl. mirror rule and PRIMARY-item binding predicate (§9.1);
  the §8.1 bucket policy and its divergence from `total_cost_minor` (two-cost-numbers
  hazard); §8.3 recompute-and-SET idempotency; snapshot completeness (HC-7
  reproducibility); the §7.4 selection rule's failure modes; currency consistency
  (§6.6); **round 1 additions:** the §4.7A valuation supersession chain + INV-V1
  race, the §10.2 journal reversibility + pre-flight refusal predicate, and the
  worker-payload redaction boundary (which serializer variant, which endpoints).
- The implementation planner then produces master plan + phase plans. The master
  plan's environment topology must carry the analytics-worker launch caveat
  (Makefile-only; absent from Procfile/docker-compose — compensation research §5) and
  exact test commands.
- Archgraph: orient on `intention-step-transition-analytics`, `table-task-step`,
  `table-task-item`, `table-item-issue`, `analytics-recompute-step-time-totals`,
  `domain-work-analytics`, `helper-task-state-transitions`; record the phase delta at
  close (one batched apply_changes); never adjudicate the 244 pending reviews.
- Contract bundle for implementers (per goal-mapping guide): core set + `03_models`,
  `06_commands(_local)`, `07_queries(_local)`, `08_domain`, `11_infra_events`,
  `15_testing`, `16_background_jobs`, `21_naming_conventions`, `24_multi_tenancy`,
  `25_soft_delete`, `28_roles_permissions`, `29_feature_workflow`, `30_migrations`,
  `36_audit_log`, `46_serialization`, `50_testing_strategy`, `51_worker_runtime`,
  `52_replayability`.
- Sibling artifact: the worker_compensation intention (committed, deferred) shares the
  temporal/money idioms; where both describe the same repo idiom, this document cites
  the idiom's source, not the sibling — the sibling never becomes a dependency (HC-4).

---

## 16. Shaping changelog

**Round 0 — 2026-08-11 (initial shaping from raw_intention.md):**

- **R-1** Corrected the raw draft: **`return_type` does not exist.** Return granularity
  is `return_source` (3 values) + `return_method` (2 values), neither gated to
  `task_type = return`, both mutable — hence the evaluation snapshots
  `task_type`/`return_source` (§4.5) instead of trusting live task fields.
- **R-2** Established both item monetary fields have zero business consumers,
  contradictory documentation, no validation, and silently-overwritable write paths
  (§2.1) — so this domain may define them, but the definition is a product act →
  owner card 1; write-path tightening → card 2.
- **R-3** Resolved the episode question (raw §7): **the episode IS the task** — no new
  episode entity. Tasks already carry identity, typing, lifecycle, and the one-PRIMARY-
  item invariant; a separate episode table would duplicate them (raw's own
  anti-duplication rule). Evaluations anchor (task_id, item_id); lifetime economics =
  Σ over the item's tasks. Rejected: `item_economic_episodes` table.
- **R-4** Modeled the cost basis worker-count-free (HC-5): inputs = fixed monthly cost
  (group total), **aggregate** monthly paid worker-hours, planning utilization;
  derived-persisted cost per productive worker-minute (§6.3). The spreadsheet's
  worker-count cancellation is thereby structural, not arithmetic. Rejected: per-worker
  capacity × headcount (headcount is not derivable — memberships are many-to-many —
  and economically cancels anyway).
- **R-5** Resolved the consumption bucket policy: **trusted WORKING seconds only.**
  Planning utilization already prices paused/idle paid time into the rate; charging
  pauses against the allowance would double-count them. Divergence from the
  working+paused salary-cost convention is documented as a named hazard (§8.1), not
  hidden. Owner may veto in review round 1.
- **R-6** Resolved config temporality: two effective-dated chains (basis per group,
  model per workspace), date granularity, ≤ today, repo partial-unique idiom — same
  contract as the sibling compensation intention. **Resolution happens once, at
  evaluation creation, and is snapshotted** — no resolution-by-work-date; "committed"
  means frozen for the episode. Rejected: repricing episodes as config changes
  (violates HC-1 and the raw's §5 non-retroactivity).
- **R-7** Resolved projections vs committed (raw §12, §22): one table, immutable `kind`
  discriminator, structural filters, promotion-by-copy. Rejected: separate tables
  (identical shape, double maintenance) and mutable "draft→committed" status flips
  (history would be editable).
- **R-8** Resolved v1 basis selection: exactly one active production cost group per
  workspace is required **at evaluation time** (explicit ValidationError otherwise);
  schema stays multi-group; section membership (unique active group per section,
  INV-G1) is analytic attribution only. Rejected: silent first-group fallback.
- **R-9** No seeded default terms, no zero-budget fallbacks: an unconfigured workspace
  or unpriced item yields **no evaluation** and an explicit "not configured" status —
  never a 0 that looks like a decision. (Existing analytics' missing-rate ⇒ cost-0
  behavior is the counter-example this avoids.) Also rejected: absorbing the dormant
  `static_costs` table (different concept — flat named amounts, no capacity semantics;
  it remains the seed for future non-worker overheads).
- **R-10** Final result at the task's **terminal** transition via a new outbox event +
  recompute-and-SET handler (§8.3). READY rejected as the close boundary: it has no
  timestamp, tasks reopen from it, and the terminal commands already own the
  side-effect seam. Live status covers the READY→terminal window.
- **R-11** Multi-item & batch (raw §17): v1 evaluates the PRIMARY item only (DB-enforced
  singleton; RELATED has no production semantics); batch allocation needs no new
  arithmetic — the concurrency sweep's per-user `1/k` division already dilutes each
  task's accrual correctly (verified in `domain/analytics/concurrency.py` +
  `test_concurrency.py`). Multi-item split within one task: explicitly deferred, seam
  = (task_id, item_id) keying.
- **R-12** Currency: evaluation requires item currency present and equal to basis
  currency; hard validation, no default (no workspace currency exists). Analytics stay
  currency-naive — inherited limitation, documented not fixed.
- **R-13** Recorded documentation drift + the Application_contracts aggregate-fields
  gap (§2.6) for coordinator routing rather than silently patching downstream.
- **R-14** Vocabulary pinned: "worker-minutes" for the aggregate quantity everywhere;
  "minutes per worker" banned from schema, API names, and docs (raw §3).
- **R-15** Mirror rule: committing with a new expected price updates
  `item.item_value_minor` (evaluation → item, single direction, stamped author). The
  live field is thereby always the currently-operative price without becoming an
  authority — history lives only in the committed chain.

**Round 1 — 2026-08-11 (owner answers folded; the four cards in owner_decisions.md):**

- **R1-1 (card 1)** The legacy item columns are **removed, not ratified**: valuation
  and cost move to the independent `ItemValuation` table (§4.7A), item-linked,
  supersession-chained, immutable rows. §4.7 rewritten; §10.2 rewritten from
  validate-in-place to journaled migrate-and-drop. Shaping extension recorded:
  `item_currency` is dropped together with the amounts it qualifies — the owner's
  wording names only value/cost, so this is an explicit **veto point** (flagged in
  the round-1 report).
- **R1-2 (cards 1+2)** R-15's mirror rule retargeted: a commit that changes the
  figures creates a **superseding valuation row** instead of writing an item column
  (round-0 form superseded, entry kept per changelog discipline). R-2's card-1 gate
  closed.
- **R1-3 (card 2)** Item money writes: ADMIN/MANAGER only, through the specialized
  valuation endpoint that also returns the economic preview (owner's
  separation/scalability intent). Generic item CRUD stops carrying money entirely —
  stronger than the recommended gating: the WORKER/SELLER write paths cease to exist
  (§4.7). "Created unvalued, priced later" is the expected common flow; unvalued is an
  explicit state, never zero (consistent with R-9).
- **R1-4 (card 3)** Auto-commit at task creation confirmed (recommendation accepted);
  pinned: auto-path failure never fails task creation (§7.2).
- **R1-5 (card 4)** Worker surfaces: minutes/percentages only (recommendation
  accepted); closing the existing `total_cost_minor` worker exposure moves into
  must-ship (§10.4, §13, test 14).

**Round 2 — 2026-08-11 (R1-1 veto point confirmed):**

- **R2-1** Owner confirmed dropping `item_currency` with the amounts. Supporting
  evidence verified in-session: `ItemUpholsteryRequirement.currency` /
  `.value_minor` are **dormant** — no constructor or update path writes them
  (`create_item_upholstery.py:70,80,90`, `apply_surplus_to_requirement.py:80-88`
  pass neither), only two serializers echo their NULLs
  (`domain/items/serializers.py:47`, `domain/tasks/serializers.py:145`) — so the
  only real coupling is PG type creation (`create_type=True` lives on the Item
  column, `item.py:41`; the requirement reuses with `create_type=False`).
  Type-creation ownership moves in §10.2 step 3; no behavioral migration exists.

**Round 3 — 2026-08-11 (mechanism-inventory gate, round 1; new §4A, §6A, §7A, §7B,
§8A, §10A, §11A; §14 items 15–21):**

- **M-1 (defect, §7.2)** Commit step order was wrong: inserting the new committed
  evaluation before closing the previous one violates INV-E1's non-deferrable partial
  unique on *every* second commit, not only under concurrency. 7A.1 pins close → insert
  → back-link (S1/S2/S3) for all four chains, with rowcount 0 declared legal and the
  index declared the sole race arbiter (7A.2). §14 test 17 is the row that fails under
  the original order.
- **M-2 (defect, §7.2 card-3 path)** "Auto-path failure never fails task creation" is
  unimplementable with `try/except` inside `create_task`'s single transaction — a failed
  statement poisons it. 7B.5 pins pre-checks plus `session.begin_nested()`, with the
  named mutation.
- **M-3 (defect, §6.3/§6.4)** `fixed_monthly_cost_minor ≥ 0` permits a zero rate and
  §6.4 then divides by zero; the quantized rate can also underflow to 0.0000 from
  legal inputs. A1 raises the CHECK to > 0, 6A.6 adds `ITEM_COST_RATE_UNDERFLOW` and a
  CHECK on the derived column.
- **M-4 (HC-6 conflict, §4.4/§6.1)** A single `value` column carrying percent units for
  one term type and **major** currency units for another violates HC-6 and is the
  unit-confusion hazard in its purest form. A3 splits it into `percent_value` /
  `fixed_amount_minor`; the major→minor ×100 disappears from §6.1.
- **M-5 (HC-6 conflict, §6.3–6.5)** `cost_per_worker_minute` was denominated in **major**
  units, forcing three ÷100/×100 conversions through the formulas. A2 redenominates it
  in minor units per worker-minute; §6A.3's five quantization sites are what remains.
- **M-6 (gap, §4.4)** `fixed_amount` terms are money with no currency. A4 adds
  `CostModelVersion.currency` NOT NULL and 6A.9 makes the equality three-way.
- **M-7 (gap, §4.4)** Term uniqueness is on `name`, so two `item_purchase_cost` terms
  are legal and would subtract the purchase cost twice. A5 adds the partial unique.
- **M-8 (defect, §8.3/§8.4)** Time can settle **after** an episode closes — nothing stops
  a step transition on a terminal task and nothing re-emits the result event — so a
  stored result can disagree with a live recompute forever. §8A.5 writes both branches;
  **owner card 1** picks one.
- **M-9 (ambiguity, §8.4)** "Byte-identical on recompute" is false as written because
  `computed_at` changes. 8A.4 names the identity column set and the exclusions.
- **M-10 (defect, §10.2)** The journal as described covers non-deleted items only, while
  the column drop destroys soft-deleted items' amounts too — `downgrade` would be
  lossy. 10A.1 widens the journal to every row with any non-NULL column; 10A.2 adds the
  negative-amount refusal P2 alongside the NULL-currency refusal P1 and totalises the
  case table.
- **M-11 (defect, §10.2 step 2)** Request models default to pydantic `ignore`, so
  removing the money keys makes a client's price vanish with a 200; but rejecting the
  key outright breaks the manager app, which sends `item_value_minor: null` on every
  task creation. 10A.3 pins reject-iff-present-and-non-NULL for one release.
- **M-12 (census error, §10.4)** `serialize_step` has **five** call sites, not two:
  `GET /tasks/{task_id}` (WORKER + SELLER) and `GET /working-sections/steps/user-last-
  active` (WORKER — the worker's live step card) also leak `total_cost_minor`. 11A.2
  carries the verified census; 11A.3 turns card 4's rule into a declared, fail-closed
  interface field with five named mutations. SELLER is excluded from money along with
  WORKER — a unilateral resolution of card 4's wording, listed for ratification.
- **M-13 (adjective, §6.6)** "The repo's banker's-rounding precedent in `_cost_minor`"
  is not a precedent: `_cost_minor` inherits ROUND_HALF_EVEN from the ambient decimal
  context (`to_integral_value()` with no argument), and the repo's only *explicit*
  quantize rounds HALF_UP. 6A.2 makes ROUND_HALF_EVEN this domain's own decision, passed
  explicitly at all five sites.
- **M-14 (ambiguity, §6.5)** Double rounding: consumption derived from the already-
  quantized `actual_worker_minutes` would drift against the same figure derived from
  seconds. 6A.3 pins Q5 on seconds and demotes `actual_worker_minutes` to a display
  projection; it also pins Q3 and Q5 onto the *quantized, persisted* rate so HC-7's
  re-derivation reproduces stored values exactly.
- **M-15 (ambiguity, §6.1)** The percentage base is the **gross** expected sale price, so
  a 25 % VAT term must be entered as 20.00. Nothing crashes if it is entered as 25.00 —
  the budget is simply 5 % of the sale price too small, on every item. 6A.4 pins the base
  and the documentation duty; **owner card 2** confirms the reading.
- **M-16 (totality)** Ranked/precedence rules made complete and decidable: version-
  creation admission (7A.4), basis/model selection failure modes (7A.5), task-state
  admission over all 8 `TaskStateEnum` values (7B.2), PRIMARY binding as three values
  (7B.3), term types × column presence (6A.4), migration cases (10A.2), and the status
  vocabulary as a single ordered enum (11A.4).
- **M-17 (contract identity)** `calculation_version` was "a formula/model version stamp";
  6A.10 defines what bumps it, what never does, and that stored rows are never
  recomputed. 6A.11 states the snapshot-completeness theorem and its closed field set —
  the HC-7 claim is now provable rather than asserted.
- **M-18 (guard race, §7.5)** The deletion guard is application-level (FK RESTRICT does
  not restrain a soft delete); 7A.6 pins `FOR UPDATE` on the delete path and `FOR SHARE`
  on the commit path so §7.5's guarantee is enforced, and records that the failure
  would have been benign in value terms — every input is snapshotted.
- **M-19 (mirror rule, §7.2 step 4)** The predicate is now exact: a Python tuple
  comparison on loaded ORM values (so `None == None` holds), never a SQL predicate where
  `NULL != NULL` would fire the mirror on every unpriced purchase cost; the mirror row
  carries both figures; and the auto path never fires it (7B.4).
- **M-20 (consumption read, §8.1)** Pinned as one expression with `COALESCE(…, 0)`,
  `is_deleted` as the only filter, step state deliberately unfiltered, and the
  two-cost-numbers hazard turned into four structural rules plus a disjointness test
  (8A.1–8A.2).

**Round 4 — 2026-08-11 (mechanism-gate cards answered; coordinator fold):**

- **R4-1 (gate card 1)** Post-close time settlement: **re-emit** (branch A) adopted —
  the owner accepted the recommendation. §8A.5 is now the binding contract; branch B
  recorded as rejected. Consequences: the CLI re-emit stays "only if cheap" (§13),
  §8.4's replay invariant holds as stated, §14 test 18 builds the branch-A row only.
- **R4-2 (gate card 2)** Percentage base **confirmed gross — and repositioned**: the
  owner's answer goes beyond confirming the arithmetic. Percentage terms are
  manager-controlled **planning allocations**, not statutory tax calculations; a
  term's name carries no calculation semantics; a percentage term must never be
  presented as computing legally payable tax (binding presentation rule on API docs,
  living docs, frontend); Swedish margin taxation (VMB) and all statutory VAT
  treatment are explicitly outside this implementation; future accounting integration
  may add legally derived amounts or new `calculation_type`s without changing this
  allocation's semantics. §6A.4 rewritten accordingly.
- **R4-3** The seven round-3 unilateral resolutions (handoff ratification section)
  were relayed to the owner with this fold; per the handoff's protocol they need
  visibility, not answers — they stand as written, and any later veto folds as a
  lettered amendment, never a rewrite.

**Round 5 — 2026-08-12 (phase-1 projection findings folded; coordinator):**

- **R5-1 (projection D1)** §11A.2's census corrected: the five call expressions are
  right, but two are shared payload builders and the exposure surface is endpoints —
  **eight**, not five. Endpoints 6–7 (`task-step-acknowledgments`
  reassigned-steps/pending) are live WORKER exposures the round-3 census missed;
  endpoint 8 (`worker-stats/last-interacted-steps`, ADMIN/MANAGER) keeps money.
  Boundary consequence pinned: the flag derives once inside each shared builder; a
  threaded parameter, if ever chosen instead, is keyword-only with no default.
  (Same error class as the §10.4 two-of-five drift the round-3 census itself
  corrected: counting call expressions where the claim is about surfaces.)
- **R5-2 (projection card 1)** Owner answered 2026-08-12: the item-money exposure on
  worker-reachable task payloads (`item_value_minor`/`item_cost_minor`/`item_currency`
  via `serialize_item`) **remains until phase 6 removes the columns** — no phase-1
  interim redaction (recommendation accepted; the fields are not rendered by any
  worker screen). Phase 1's "money absent" criterion stays scoped to
  `total_cost_minor` exactly as written.

**Round 6 — 2026-08-12 (owner correction: results at every episode boundary):**

- **R6-1 (owner-initiated)** The result is computed at **every episode boundary**,
  not only at terminal close — new §8B: emit hooks at every sanctioned READY entry
  (`maybe_evaluate_task_ready`) and every reopen (`maybe_reopen_task_to_working`),
  the three terminal emissions kept, and §8A.5's straggler guard widened to
  `{READY} ∪ terminal`. Handler admission made total over all 8 task states (8B.2).
  Rationale: READY is the machine-detectable completion; terminal states are manual
  and may lag. **Supersedes R-10's terminal-only boundary** (R-10's reasons stand —
  no READY timestamp, reopens happen — which is why the row snapshots its boundary
  rather than treating READY as a close). Gate card 1's re-emit answer (R4-1) is
  extended, not contradicted.
- **R6-2 (owner pins, same day)** Finality marking: `task_state_snapshot` (enum copy,
  PG type reuse `task_state_enum` with `create_type=False`) + `task_closed_at` made
  nullable (§4.6 as amended); **reopen refreshes the row immediately** so it never
  claims READY during ongoing work. Both columns join the §8A.4 replay-identity set.
- **R6-3 (owner-confirmed reading, no change)** Cross-episode accumulation for an
  item returning on future tasks (return / pre_order via article/SKU matching) is
  already structural — (task_id, item_id) evaluation keying, per-episode results,
  read-time lifetime summation (8B.4). Recorded so no session "fixes" what is
  deliberate.

**Round 7 — 2026-08-12 (phase-2 projection D6 folded; coordinator):**

- **R7-1** `ItemCostEvaluationTerm`'s column set pinned in §4.5 (round-7 paragraph):
  `workspace_id` added (`24_multi_tenancy` — three artifacts disagreed and none
  carried it), A3's `percent_value`/`fixed_amount_minor` replace the round-0 `value`
  in the snapshot table too (§6A.11 is the authority), audit shape is `created_at`
  only, no soft-delete trio. Resolves the §4.5-vs-§4A-vs-contract conflict the
  phase-2 projection found (D6); no product semantic changed.

**Round 8 — 2026-08-12 (phase-3 projection findings folded; coordinator):**

- **R8-1 (projection S6)** §6A.8's variance-independence bound was **factually
  wrong**: "up to one minor unit" holds only at rates below ~6; the real discrepancy
  scales ≈ `0.01 × rate + 0.5` minor units (verified: ~3 at rate 400, ~8 at 1000).
  Sentence replaced with the derived bound; tests assert exact per-fixture
  differences, never the general bound. Formulas unchanged.
- **R8-2 (projection S5)** §6A.2's "never relies on the global context" tightened
  into a **`decimal.localcontext()` requirement**: explicit `rounding=` neutralizes
  ambient rounding changes but not ambient precision (`__truediv__`/`quantize` read
  `getcontext().prec` — a lowered precision turns Q3 into `InvalidOperation`,
  verified). Also corrected §6A.2's citation: the accidental-HALF_EVEN precedent is
  the local `cost_minor` at `process_step_transition.py:231-233`, not a
  `_cost_minor` function.

**Round 9 — 2026-08-12 (phase-3 review cards answered; coordinator fold):**

- **R9-1 (review card 1)** Re-derivation mismatch is an **internal integrity
  alarm**, never a user-facing validation error: §6A.11 gains the
  `REDERIVE_MISMATCH` structured-result contract (marker carrier, sibling of
  `REDERIVE_SKIPPED`); the fix cycle replaces the implementer's unregistered
  `ITEM_COST_SNAPSHOT_MISMATCH` ValidationError with it. Callers log/escalate;
  the read renders.
- **R9-2 (review card 2)** The implementer's two defensive guards are **absorbed
  as intended semantics**: (a) negative `percent_value`/`fixed_amount_minor`
  reject with `ITEM_COST_TERM_SHAPE_INVALID` — the calculator re-validates §6A.4's
  `≥ 0` range, not only presence/type; (b) a zero rate reaching the allowance
  (Q3) raises `ITEM_COST_RATE_UNDERFLOW` — defence-in-depth at a second site of
  §6A.6's identity. Both gain required test rows (fix r2).

**Round 10 — 2026-08-12 (phase-3 re-review card answered; coordinator fold):**

- **R10-1 (re-review card 1)** R9-1's "never fails the read" made **total over
  input classes** (§6A.11 round-10 paragraph): value disagreement, malformed term
  snapshot, malformed evaluation snapshot — all return the integrity marker; no
  `ValidationError` escapes `rederive` on any path (the re-review proved three
  escape routes, one opened by the fix's own refactor). Cascade pinned: a rate
  mismatch also reports its derived allowance entry. Lesson L5 applied: a
  "never raises" contract enumerates the input classes it covers.
- **R10-2 (re-review r3 N14; coordinator)** Mismatch-payload shape pinned
  homogeneous: every entry carries `field`/`rederived_value`/`stored_value`/`error`
  (`error = None` on plain disagreements) — half the entries carrying an extra key
  would make callers key defensively or crash on `entry["error"]`.

**Round 11 — 2026-08-12 (phase-4 projection B1 + owner card; coordinator fold):**

- **R11-1 (projection B1; owner card: round-then-derive)** §6A.1 gains the
  persisted-configuration-numerics rule: request numerics are quantized to the
  destination column's scale (ROUND_HALF_EVEN) in the request model before any
  derivation — PostgreSQL's silent scale-rounding otherwise stores a rate that
  disagrees with its own inputs (verified 173.456h → 12.0107 vs 12.0105),
  silently falsifying HC-7's re-derivation theorem. Over-precise entries are
  rounded, never refused (owner: the manager mid-setup is not blocked over a
  payroll export's spare digit).

**Round 12 — 2026-08-12 (owner scope decision: category-driven group selection):**

- **R12-1 (owner-initiated, pre-v1)** Cost groups are selected by the PRIMARY
  item's **major category** (wood | seat) — new §7C: `major_category` NOT NULL on
  groups (enum reuse, R2-1 ownership), **INV-G3** one active group per
  (workspace, category), the total ordered selection rule (missing category →
  new status `item_missing_major_category`, evaluated first among group-2
  reasons; §11A.4 now 12 values), per-category configuration status, and the
  category-immutable-once-versioned command rule. Owner pins: category required
  at group creation (one per category); category-less items are an economics
  precondition failure only — item creation untouched. Ships as **phase 4B**
  between phases 4 and 5 (the consumers — preview, commit, status — build against
  the final rule; the unshipped schema takes NOT NULL cleanly). §7.4's and
  §7A.5's single-group rows are superseded; §13's "multi-group basis selection
  rules" deferral is partially consumed (per-task-section rules stay deferred).

**Round 13 — 2026-08-13 (phase-5 projection r0 owner cards; coordinator fold):**

- **R13-1 (card 1)** The valuation endpoint's preview: dedicated `preview`
  payload key, never merged with committed figures; the computable preview
  state (`not_evaluated`) carries computed numerics INSIDE that key; all other
  statuses stay null-numeric (§11A.5 lettered clauses (a)–(c); §11A.4's closing
  rule refined to non-computable statuses; master §9 P-B refined to match).
  Owner pin: the first expected-sale-price save auto-creates valuation
  version 1 with no confirmation step — the comparison baseline.
- **R13-2 (card 2)** Deleted valuations are hidden from the item's price
  history (§11A.5 (d)); the history's "current" predicate is INV-V1's
  (`superseded_at IS NULL AND is_deleted = false`), and its total order is
  `created_at DESC, client_id DESC`.

**Round 14 — 2026-08-14 (phase-6 projection r0; two owner cards answered in-session):**

- **R14-1 (D1)** The §10A.3 bridge identity is raised as the repo's
  `beyo_manager.errors.validation.ValidationError`, never a pydantic-side
  `ValueError` (the parse helpers mangle the leading token); exact full
  message asserted. §6.4's carrier wording corrected to match.
- **R14-2 (D3)** §10A.1 post-condition 2 restated over the journal; re-run =
  no-op without aborting; the phase-5 collision row added (§10A.1(a)).
- **R14-3 (owner cards 1–2)** Attribution: the item's own `created_by_id`,
  with the new **P3** pre-flight refusal for amount-with-NULL-creator rows
  (§10A.1(b), §10A.2); deliberately deleted prices are NOT re-valued
  (§10A.1(c)). Both unreachable on any known database (the valuation surface
  is unshipped and the legacy population measures empty everywhere) — totality
  armor, not behavior.
- **R14-4 (D15/D16/D6)** §10A.3's frontend evidence corrected (the request
  body omits the money keys; the cited lines were the optimistic cache);
  `model_fields_set` dropped as inert; the router body models retain the keys
  with a survival criterion row.

**Round 15 — 2026-08-14 (phase-6 review r1 card 1; coordinator fold):**

- **R15-1 (owner)** The §10A.1(c) eligibility predicate is corrected to
  `NOT EXISTS (any item_valuations row for the item)` — the round-14 folding
  carried a predicate that contradicted the clause's own heading and would
  have re-valued deliberately deleted prices (review B2, executed on a
  seeded disposable). The owner re-confirmed: leave deleted prices deleted;
  never-valued items only. Review L3 (a clause whose prose and verbatim
  predicate disagree is undischargeable) becomes projection practice.

**Round 16 — 2026-08-14 (phase-7 projection r0; one owner card answered):**

- **R16-1 (owner, card 1)** A committed evaluation appears in the **task's
  activity history the whole team reads** (plus the admin audit trail), and the
  extraction surface is the existing flow read
  (`services/queries/tasks/task_flow_records.py` centralizes it). Coordinator
  mechanism fold: satisfied by a **TASK-linked** `HistoryRecord`
  (`entity_type = TASK`, precedent `resolve_task.py:61`) — the flow query's
  always-on TASK condition picks it up with zero migration, zero flow-service
  change, zero new serializer; the projection card's "small database change"
  branch (a new `history_record_entity_type_enum` member) is dissolved as
  unnecessary. §7B.1 step 9 amended.
- **R16-2 (D4)** The mirror race clause was false for the committed-mid-flight
  ordering at READ COMMITTED (a manager's corrected price could be silently
  superseded by figures from the older valuation). §7B.1 step 4 now takes the
  current valuation `FOR UPDATE`; §7B.4's race clause restated over both
  orderings.
- **R16-3 (D7/D17)** §7B.5's pre-check enumeration replaced by the registered
  resolver (`resolve_item_economics_status … is NOT_EVALUATED` + active PRIMARY
  item) — total by construction; the round-3 list omitted `currency_mismatch`
  and the no-item case. Both auto-path log lines pinned verbatim
  (`item_economics.auto_commit_skipped` INFO /
  `item_economics.auto_commit_failed` WARNING).
- **R16-4 (D9)** The auto path never dispatches its own event: conditional
  `pending_events` append after the savepoint exits normally, per the
  subordinate-command event rule. The plan's "savepoint block only" file fence
  is amended accordingly (spirit kept: no existing statement moves).

**Round 17 — 2026-08-14 (phase-8 projection r0; two owner cards answered):**

- **R17-1 (owner, card 1)** §8A.6's result clause corrected: the result block
  renders **whenever a result row exists**, labelled with its computed-at
  boundary — the "when the episode is closed" wording predated round 6.
  Owner: "READY is when the item is finished working, so it counts as
  resolved from this item-cost perspective."
- **R17-2 (owner, card 2)** §11A.5(d)'s DELETE status is re-resolved through
  the §11A.4 ordering, never hand-written. Owner: one rule, no drift — a
  never-priced item and a deleted-price item give the same warning. The
  shipped hardcoded `item_unvalued` (phase-5 review N2) is corrected in
  phase 8.

**Round 18 — 2026-08-15 (owner scope additions, direct conversation):**

- **R18-1 (owner card)** Task creation accepts the valuation vocabulary
  inline (§7B.6 NEW): on a newly created item, valuation v1 via the
  registered chain writer before the auto-commit savepoint — priced in one
  call; on a matched existing item, REFUSE (conservative default, 8B
  projection may card). Legacy money keys stay rejected. Ships as
  **phase 8B** before phase 9. (The coordinator surfaced that the shipped
  system rejected inline prices by the owner's own earlier design; the
  owner chose to add the mechanism rather than document the two-step flow.)
- **R18-2 (owner)** Phase 9 gains the frontend-handoff deliverable: the ten
  new routes + the CHANGED existing endpoints (the money-key removals
  prominently), so the frontend can build the capability from the handoff
  alone.
- **R18-3 (owner, 8B projection card 1 — branch B)** A matched existing
  item with a CURRENT valuation refuses inline prices
  (`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`, whole request aborts); one
  with NO current valuation accepts them (never-valued → v1 per R13-1;
  deleted/superseded-only → next version — explicit act, distinct from
  R15-1). §7B.6 lettered corrections (a) trio shape (all optional,
  currency-iff-amount, currency-alone accepted-and-ignored — the "exact
  mirror" gloss was false against shipped code) and (b) the branch-B
  clause; §4.7A writers list += create_task; §11A.5(c) corrected.

---

## 17. Open decisions ledger

**Rounds 0–2: closed.** All four round-0 cards were answered by the owner on 2026-08-11
(answers recorded in `owner_decisions.md` `ANSWER:` slots; folded as changelog round 1,
R1-1…R1-5). The one veto point flagged inside R1-1 — extending the column removal to
`item_currency` — was **owner-confirmed the same day (round 2, R2-1)**.

**Round 3: closed in round 4.** The mechanism-inventory gate raised two decisions
(cards carried verbatim in
`handoffs/mechanism_inventory/2026-08-11_mechanism-inventory_r1_handoff.md`); the
owner answered both on 2026-08-11 (answers recorded in `owner_decisions.md`, gate
cards 1–2) and they are folded as changelog round 4 (R4-1, R4-2): card 1 → re-emit
(branch A); card 2 → gross base confirmed, percentage terms are planning allocations,
never statutory tax.

**Ratification items:** the seven round-3 unilateral resolutions were relayed to the
owner with the round-4 fold (R4-3). Per the gate's protocol they required visibility,
not answers; they stand as written. A later veto folds as a lettered amendment.

**EMPTY.** Nothing remains open or flagged.

Exit gate: **PASSED.** Every silent-failure mechanism has a contract-grade definition
in this document and none is provisional. Next gate: **implementation-planner**.

---

## Appendix A — raw-draft deliverable map (raw §27)

| # | Raw deliverable | Answered in |
|---|---|---|
| 1 | Reusable architecture | §2.3, §2.5, §8.2 |
| 2 | Conflicting/constraining architecture | §2.1, §2.2, §2.4 |
| 3 | Domain boundaries | §1, §4 preamble, §10.3 |
| 4 | Entities & relationships | §4 |
| 5 | Item vs cost structures | §4.7, §4.7A, §5 |
| 6 | Config & effective-dating | §4.3–4.4, §7.1, R-6 |
| 7 | Episode strategy | R-3, §4.5 |
| 8 | Projection strategy | §7.3, R-7 |
| 9 | Worker-time reconstruction | §8.1, §2.3 |
| 10 | Multi-item allocation | §9.1, R-11 |
| 11 | Batch implications | §9.2, §2.3 |
| 12 | Section cost basis | §4.1–4.3, §7.4, R-4/R-8 |
| 13 | Money/rate representation | §6.6, HC-6 |
| 14 | Expected vs actual snapshots | §4.5–4.6, §8.3 |
| 15 | Recalculation/correction semantics | §7.5, §8.3–8.4, HC-1 |
| 16 | DB invariants & uniqueness | INV-G1/B1/B2/M1/M2/E1/E2 |
| 17 | Migration implications | §10.1–10.2 |
| 18 | Backend/service/API impact | §11 |
| 19 | Frontend impact | §10.4 |
| 20 | Analytics/recompute impact | §8.2–8.3, §13 |
| 21 | Compensation compatibility | §10.3, HC-4 |
| 22 | Risks & product decisions | §17, R-5, §8.1 hazard |
