# Research context — item_cost_calculation (grounding evidence & reasoning)

```
role: grounding evidence appendix (companion to intention.md)
date: 2026-08-11 (all citations verified against the tree on this date)
purpose: let a future session resume this pipeline WITHOUT re-running the research
read order for a resuming session:
  1. intention.md            (the authority — round 1 folded; ledger EMPTY)
  2. owner_decisions.md      (CLOSED — all 4 answered 2026-08-11, ANSWER lines filled)
  3. this file               (evidence behind intention §2, plus reasoning not in the doc)
  next gate: mechanism-inventory (see intention §15 for the flagged mechanisms)
ROUND 1 NOTE: card 1's answer REMOVES item_value_minor / item_cost_minor /
  item_currency from the items table — §1 below documents the legacy state as the
  §10.2 migration's evidence, not as the go-forward model (that is intention §4.7A,
  the ItemValuation table).
sibling evidence: ../../worker_compensation/planning/research_context.md — same-day,
  same-branch census of the analytics/time pipeline, money/temporal/model/migration
  conventions, and archgraph state. Shared ground is NOT re-proven here; §6 below
  summarizes what carries over and what this project verified independently.
```

Line numbers are as of 2026-08-11 (branch `fix/idempotent-completion-analytics`); they
may drift, but symbol names and file paths are the stable handles.

---

## 1. Item monetary fields — complete census

### Definition
- `app/beyo_manager/models/tables/items/item.py:38-42` — `item_value_minor` (Integer,
  nullable), `item_cost_minor` (Integer, nullable), `item_currency`
  (`ItemCurrencyEnum`: `swedish_krona | danish_krona | euro`,
  `domain/items/enums.py:11-14`; **nullable, no default**). **No CHECK constraints on
  `items` at all** (`item.py:70-92` is indexes only; verified against migration
  `7d92a90e6282:290-323` and a repo-wide CheckConstraint grep). No request-level
  validators for either field (`services/commands/items/requests/__init__.py:184-262,
  450-484` validate only quantity/article/sku).
- Contrast: every sibling money column IS guarded — `item_upholstery_requirements.value_minor`
  CHECK ≥ 0 + currency (`item_upholstery_requirement.py:42-45,104-107`),
  `upholstery_orders.price_minor` (`upholstery_order.py:86-87`).
- No workspace default currency: `workspaces` = name, time_zone, audit only
  (`workspace.py:14-17`); the users-README claim "currency is workspace-scoped" is
  aspirational, unimplemented.

### Writes (complete: 6 code sites + migration)
`_create_item_in_session.py:38-39,117-118`; `create_item.py:67-68`;
`find_or_create_item.py:30-31,98-100 (update branch!),166-167`; `update_item.py:35-36,
72-74`; `create_task.py:208-209` (nested item create branch); migration
`7d92a90e6282:301-302`. **Zero** seeds/backfills/scripts/tests write them. Item
lookup handlers carry no money (`queries/items/lookup/base.py:10-17`).

**The silent-overwrite path (intention §2.1):** `find_or_create_item` mutates both
fields on a PRE-EXISTING item matched by article_number/sku via `_DIRECT_FIELDS`
(`find_or_create_item.py:30-31,95-100`), reachable from `create_task`
(`create_task.py:226-238`), whose route admits ADMIN/MANAGER/SELLER/**WORKER**
(`routers/api_v1/tasks.py:328-331`). `PATCH /items/{id}` admits ADMIN/MANAGER/**SELLER**
(`routers/api_v1/items.py:338-342`). History records discard values:
`field_name/from_value/to_value = None` (`update_item.py:106-117`) — prior amounts
unrecoverable. Null-vs-omit honoured via `model_fields_set` (`update_item.py:57,73`).

### Reads (complete)
Serializers only: `domain/items/serializers.py:103-105` (item list/detail);
`domain/tasks/serializers.py:104-105` (`serialize_item`, embedded as `primary_item`/
`item` in task-list, task-detail, coordination threads, upholstery-order queries);
router/request echoes. `serialize_item_worker_light` (`domain/tasks/serializers.py:411-441`)
deliberately omits money — the existing redaction precedent for card 4. **No query,
aggregation, filter, or business rule reads either field anywhere.**

### Semantics evidence (contradictory — why card 1 exists)
- `docs/architecture/under_construction/intention/planning_tables/item/item_models.md:104-107`:
  value = "estimated business value semantics", cost = "internal operational cost
  semantics", with an explicit do-not-bind-to-accounting warning.
- `docs/handoff/to_frontend/archived/HANDOFF...20260523.md:87-88`: value 120000 /
  cost 80000 — reads acquisition-cost-vs-sale-side.
- Raw intention (owner's voice): purchase cost "will actually be stored in the same
  table as the expected sold price" — the reading intention §4.7 adopts, pending card 1.

### Item lifecycle & sale reality
- `ItemStateEnum` (`pending|stalled|fixing|ready`, `domain/items/enums.py:4-8`) is
  **inert**: written only at creation (`_create_item_in_session.py:110`,
  `find_or_create_item.py:159`), read only by serializers. Every item stays `PENDING`.
  (README drift: `items/README.md:34` says `STALL`.)
- **No sale/sold/order record anywhere** (`grep sold|sale_price` over app/: zero).
  Shopify: outbound price is caller-supplied request payload, never read from Item
  (`domain/shopify/product_sync_payloads.py:45`); order webhooks
  (`orders/create|updated|paid|cancelled`) registered (`webhook_registry.py:25-48`) but
  every intake is marked PROCESSED with `"processing_mode": "no_business_processor_yet"`
  (`handle_shopify_process_webhook.py:64-82`; confirmed by
  `architecture/57_shopify_integration.md:201`). Item↔Shopify identity: article_number
  = variant barcode (`57_shopify_integration.md:228`).

### Categories & satellites
- Category chain: `item_category_id` → `item_categories` (workspace-scoped name,
  `major_category` WOOD|SEAT) with snapshots denormalized on the item
  (`item_category_snapshot`, `item_major_category_snapshot`; rewritten on category
  change `update_item.py:76-93`; partial index `item.py:72-77`). Bootstrap seeds 6 SEAT
  + 21 WOOD categories; no CRUD commands for categories (read-only API).
- Satellites with money/time: `item_upholstery_requirements` (value_minor+currency,
  state-bound, CHECKed) — the state-bound-money precedent **in schema only: verified
  round 2 that no constructor or update path ever writes those two columns**
  (`create_item_upholstery.py:70,80,90`, `apply_surplus_to_requirement.py:80-88` pass
  neither; readers `domain/items/serializers.py:47`, `domain/tasks/serializers.py:145`
  echo NULL) — its `currency` merely reuses the `item_currency_enum` PG type with
  `create_type=False` (`item_upholstery_requirement.py:43-45`; type created by
  `item.py:41`), which is why dropping `item_currency` is safe (R2-1);
  `upholstery_order_history_records.snapshot_price_minor` (written at
  `create_upholstery_order.py:123`, `receive_upholstery_order.py:80`) — the
  snapshot-money precedent; `item_upholsteries.time_to_fix_in_seconds` — a time
  estimate. `item_issues`: `intensity ≥ 1` CHECK; **has both item_id and step_id**
  (`item_issue.py:25-30`) — the only per-(item, step) fact in the schema; its
  `base_time_seconds`/`time_multiplier` columns were dropped (README drift,
  `items/README.md:53-61`).
- FKs to items: only `task_items`, `item_upholsteries`, `item_issues` (all RESTRICT).

### Existing per-item analytics (the reference implementation)
`get_worker_clock_out_analytics.py:129-180` `_load_item_metadata`:
`Σ TaskStep.total_working_seconds` joined `TaskStep.task_id == TaskItem.task_id` where
`TaskItem.role == PRIMARY AND removed_at IS NULL`, grouped by item (`:149-168`).
Properties inherited: ignores `inaccurate_*`/`recorded_time_marked_wrong` flags at this
layer (they're already excluded from `total_*` by the rollup); RELATED items get zero;
an item PRIMARY on two tasks sums both. Completed-units-by-day joins
`StepStateRecord → TaskStep → TaskItem(PRIMARY) → Item` (`:70-126`). **No cost-per-item
query exists anywhere**; `services/queries/analytics/` never touches Item.

---

## 2. Task domain — episode reality

### Task model (`models/tables/tasks/task.py`)
`task_type` enum `business_task_type_enum`: **`return | pre_order | internal`** only
(`domain/tasks/enums.py:4-7`). **`return_type` does not exist** (repo-wide grep: zero).
Return shape: `return_source` (`after_purchase | before_purchase | store_return`,
`enums.py:28-31`, column `task.py:59-61`) and `return_method`
(`drop_off_by_customer | pickup`, `enums.py:39-41`, `task.py:69-71`) — plain optional
request fields (`tasks/requests/__init__.py:200-201`), written unconditionally
(`create_task.py:114,116`), **not gated to task_type**, freely editable via
`update_task` `_DIRECT_FIELDS` (`update_task.py:32,34`). `return_source` drives
behavior in exactly one place: customer-coordination requirement
(`_create_customer_coordination_in_session.py:22-27`). `assortment` drives RETURN
post-handling FILLED (`_post_handling_state_evaluator.py:20`).

State enum: `PENDING ASSIGNED WORKING STALLED READY RESOLVED FAILED CANCELLED`
(`enums.py:17-25`); **STALLED never written** (read-only membership
`cancel_upholstery_requirements.py:36`). Terminal set `{RESOLVED, FAILED, CANCELLED}`
(`domain/task_steps/constants.py:17`, mirrored in 4 command files). `closed_at` set
ONLY by the three terminal commands (`resolve_task.py:56`, `fail_task.py:56`,
`cancel_task.py:56`) — **READY (work finished) has no timestamp**; only route into
READY is `maybe_evaluate_task_ready` (`_task_state_transitions.py:51-102`, predicate:
every non-deleted step terminal); READY reopens via `maybe_reopen_task_to_working`
(`add_task_steps.py:181-186`). `force_task_ready` SKIPs open steps
(`force_task_ready.py:154-175`). Terminal side-effect block (identical shape ×3):
state+closed_at → history record → notification outbox task → `task:state-changed`
event (`resolve_task.py:53-104`). **Task has NO aggregate-metrics mixins and nothing
totals a task at any lifecycle point** (only `func.sum(TaskStep...)` in the whole repo
is the per-ITEM query above). Dead columns: `Task.recorded_time_marked_wrong` /
`taken_from_average` (`task.py:112-113`) — no writers.

### TaskItem (`models/tables/tasks/task_item.py`, prefix `tim`)
Columns: workspace/task/item FKs, `role` (`primary | related`, `enums.py:56-58`),
created audit, `removed_at`/`removed_by_id` (soft detach; every reader filters
`removed_at IS NULL`). Uniques (`:42-59`): `uix_task_items_active`
(ws, task, item, WHERE removed_at IS NULL); **`uix_task_items_primary_active`
(ws, task, WHERE role='primary' AND removed_at IS NULL)** → at most ONE active PRIMARY
per task, plus app-level pre-check (`add_item_to_task.py:47-57`). An item CAN sit on
multiple tasks (uniqueness includes task_id) — relied on by
`lock_and_filter_items_without_active_tasks` (`cancel_upholstery_requirements.py:189-260`).
Writers (3): `create_task.py:295-303` (hardcoded PRIMARY, at most one — request has a
single optional `item` object), `add_item_to_task.py:70-78` (ADMIN/MANAGER,
router `tasks.py:806-810`), `remove_item_from_task.py:35-36` (ADMIN/MANAGER).
**No tests exist for add/remove-item**; the ONLY multi-item test in the repo
(`test_get_worker_clock_out_analytics.py:330-355`) adds a RELATED item to assert
analytics ignores it. No seed creates tasks at all. ~15 query modules join
`role == PRIMARY` and treat the item as singular (`tasks.py:339,604` pick primary,
discard rest). **De facto invariant: one task ↔ one PRIMARY item; RELATED has no
production writer or economic meaning.**

### No return↔original linkage
No `original/source/parent/related_task_id` column anywhere (grep: zero). Task has no
self-FK. Only cross-episode thread: same item_id on different tasks — exactly the
episode chain intention R-3 builds on. There is exactly ONE task-creating command
(`create_task`); a "return task" is `create_task` with `task_type=return`; SKU
templates seeded only for PRE_ORDER and RETURN (`seed_sku_templates.py:9-10`);
INTERNAL silently gets no SKU (`create_task.py:240-244`).

### TaskStep creation & `allows_batch_working`
Steps created explicitly per requested working section in exactly two commands
(`create_task.py:349-454`, `add_task_steps.py:42-310`); both open a PENDING
StepStateRecord and set `latest_state_record_id`. `allows_batch_working` (default
false, `task_step.py:85-90`) is a **creation-time snapshot** of the section flag
(`create_task.py:400`, `add_task_steps.py:131`); section edits do NOT rewrite existing
steps (asserted by `test_batch_working_section_integration.py:298,304`). Section
source: `working_section.py:20`; seeds set it true only for "ground oil" /
"hardwax oil" (`seed_working_sections.py:67-70,225,241`). Read sites: transition
auto-pause skip (`_step_transition_core.py:101`, `transition_step_state.py:237`),
batch-endpoint gate (`transition_step_state_batch.py:130`), conflicting-record filter
(`_user_working_record.py:34`), **the sweep divisor gate**
(`averaged_time.py:94` → `TimeInterval.is_batchable`), worker-stats surfaces.

---

## 3. Time pipeline — what "actual worker-minutes" means (verified in full)

### The sweep (`domain/analytics/concurrency.py`, read in full)
Partition by derived state bucket (`working|paused|ended_shift` — buckets NEVER share
a divisor); within a bucket, **non-batchable intervals earn full duration and are
excluded from the divisor** (`:53-57`); batchable intervals sweep-line: each segment
`[l,r)` divided by `k` = count of open batchable intervals (`:63-74`). `step_id` is
carried but **never read** by the sweep; task_id absent. The interval population is
**one user's** records only: `COALESCE(credited_user_id, created_by_id) == user_id`
(`averaged_time.py:102`) + workspace + state ∈ {WORKING, PAUSED} + window. **So /k is
strictly "one worker holding several batchable steps open", across any tasks.**
Trusted vs wasted populations swept independently (`averaged_seconds_by_record`
`:79-93` excludes marked_wrong; `wasted_seconds_by_record` `:96-105` is only
marked_wrong). Tests: even split (`test_concurrency.py:38-43`), partial overlap
(`:59-64`), non-batch exclusion (`:67-73`), state independence (`:95-101`).

### One open record per step — multi-worker concurrency on a step is impossible
`uix_step_state_records_active` (ws, step_id) WHERE exited_at IS NULL
(`step_state_record.py:100-106`); transition commands close-then-open
(`_step_transition_core.py:184-206`). A step's time is a **sequential chain** of
records with possibly different credited users; `_recompute_step_time_totals`
(`process_step_transition.py:161-234`) sums per-user averaged contributions
(settled, `c.step_id == step_id`, `:207-212`) into `total_*_seconds` (SET,
idempotent). **Corollary: "4 workers × 10 min on one step" arises as consecutive
records, and total_working_seconds already equals the 40 worker-minutes aggregate.**
`total_cost_minor` on the step = per-user seconds × `salary_per_hour_before_tax`
(`:226-233`) — the salary-priced column this domain does NOT touch (compensation's
remit). Batch dilution propagates into both time and cost columns (a step batched
5-wide accrues 1/5 wall clock).

### Per-item attribution
No item_id on StepStateRecord or TaskStep; ItemIssue is the sole per-(item, step)
fact. Item time exists only via task→task_items(PRIMARY) — see §1's reference query.

(Full pipeline census — outbox → router → `queue:analytics` worker, reconcile
SET/delta scheme, backfill precedent, `_WINDOW_BUFFER`, at-least-once semantics —
in the sibling research_context §2; unchanged and re-confirmed by this project's
agents where touched.)

---

## 4. Sections, workspace config, utilization

### WorkingSection / membership
`working_section.py:14-57`: name (partial unique per workspace among non-deleted),
`image`, `order_list` (nullable display hint; seeds duplicate values),
`allows_batch_working`, `allows_shopify_product_modifications`, audit + soft delete.
No state enum. Three ordering concepts (don't conflate): section `order_list`,
per-user membership `sort_order`, and the `working_section_dependencies` DAG
("execution ordering, not hierarchy" — README). Membership
(`working_section_membership.py`): **many-to-many, time-varying** — active-partial
unique (ws, section, user) WHERE removed_at IS NULL (`:39-46`); WORKER-role-only
assignment (`assign_user_to_working_sections.py:32-53`). ⇒ "worker in exactly one
cost group" is NOT derivable — a reason intention R-4 configures aggregate capacity.

### No grouping entity
90-table inventory + broad greps: no group/pipeline/department/team table; only
seed-time dict constants (`seed_workers.py:86,127,131-140`). No dropped grouping
table in migration history. Net-new modelling confirmed.

### Workspace config reality
`workspaces` = name + time_zone + audit (`workspace.py:14-17`); **no settings columns,
no *_settings/*_config table, no key-value store**. The live config pattern:
first-class workspace-scoped table (audit + soft delete + workspace-scoped unique) with
5-verb router — `pause_reasons`, `issue_types`, `item_categories`,
`shopify_metafield_preferences` (which adds `sequence_order`/`is_enabled`).
**Catalog lesson** (`pause_reason.py:25-34,57-59`): slug-resolution and
`is_system_managed` were abandoned — system behavior keys on code-owned enums, not
catalog rows; and a catalog unique must include workspace_id (a global slug unique
once broke second-workspace bootstrap). Code-owned-global alternative: `case_types`
(no workspace, no audit). Tunable-analytics alternative: frozen dataclass constants
(`insights/config.py:14-26`) — code-owned, not persisted.

### Effective dating
**No live effective-dated table.** Sole precedent (dead): `issue_category_configs`
(`7d92a90e6282:260-289` — nullable from/to, window CHECK named
`ck_..._effective_window`, unique (…, effective_from); dropped `99accdeba8b9:84`).
Live one-open-row idiom: partial unique on the open predicate (step_state_record,
user_shift_state_record, user_declared_state_record + removed_at variants). No
ExcludeConstraint/btree_gist anywhere. (Same findings as the sibling; independently
re-verified.)

### `static_costs` — dormant
`static_cost.py:15-44`: name/description/`cost_minor` NOT NULL/`currency` enum
(same 3 values as ItemCurrencyEnum), workspace-scoped, audit + soft delete, **no
unique constraint at all**; migrated since founding; **zero commands/queries/routers/
serializers/seeds** (only model registry + reset phase). Its README is the repo's
money doctrine: integer minor units, never float, **snapshot-on-use** ("historical
records must not depend exclusively on the mutable live row"), versioned history
explicitly deferred. Frontend stub `features/static_costs_configuration/types.ts:3-11`
mirrors the row shape.

### "Month", time zone, currency
All analytics bucket on **UTC dates** (`reconcile_user_time.py:271-272`,
`_roster.py:36,50`); `workspaces.time_zone` read by no analytics code. No calendar
"month" concept exists → intention §6.3 keeps months as config inputs only.
Currency: two per-table enums (Item, StaticCost) with identical values; no workspace
currency.

### Shift data & utilization
`user_shift_state_records` (`user_shift_state_record.py`): states
`STARTED_SHIFT|WORKING|IN_PAUSE|IDLE|ENDED_SHIFT` (`domain/users/enums.py:4-9`);
**derived table** ("nothing sets this column directly", `:36-37`) — bounds from
Connecteam webhooks/curation (authoritative), middle rebuilt from step records +
declarations (`_reconstruct_shift_middle.py:73`; precedence documented in users
README). Connecteam provides clock in/out instants only — **no scheduled hours,
contracted FTE, break policy, or pay period** (`time_activities_client.py:29-89`;
`curate_shifts_from_connecteam.py:1-15`, discards `is_auto_clock_out` `:143-149`,
92-day cap `:25,134-135`).
- **Observed utilization per worker: derivable** — `build_recorded_shift_timeline`
  (`list_workers_linear_timeline.py:34-71`) already sums WORKING/IN_PAUSE/IDLE clamped
  to a window; the ratio `working/(working+paused+idle)` is computed **nowhere** today.
  `focus_ratio` (`insights/metrics.py:26-28`) = working/(working+pause) — active-step
  ratio, NOT utilization.
- **Per section: NOT derivable** — shift records carry no section; only step time is
  section-attributed (`user_section_daily_work_stats`). The denominator (paid time in
  a section) does not exist; the numerator (productive step time per section) does.
- `working_section_daily_work_stats` (per-section-day time/counts/cost, delta-applied
  Σ table): **zero readers** — no query service, no endpoint (only model registry,
  reconcile writer, reset phase, two backfills, migrations).

Insight/stat queries that exist: `compute_worker_insights` (reads only
`user_daily_work_stats`; frozen-dataclass config), `list_workers_totals`,
`get_worker_daily_step_breakdown`, linear-timeline pair (only readers of shift
records), `get_worker_clock_out_analytics` (kiosk summary; §1's per-item join).

---

## 5. API & frontend impact zones

### Backend surfaces
Item endpoints (`routers/api_v1/items.py`): PUT create (ADMIN/MANAGER `:147-150`),
GET list (`+WORKER :164-166`), find-or-create (ADMIN/MANAGER `:220-223`), GET one
(`+WORKER :304-307`), **PATCH (ADMIN/MANAGER/SELLER `:338-342`)**, DELETE
(ADMIN/MANAGER `:356-359`), positions (`+WORKER :321-324`), lookup (all roles
`:285-287`). Money fields accepted/returned under their column names
(`domain/items/serializers.py:103-105`).
Step time/cost exposure: `serialize_step` (`domain/tasks/serializers.py:152-177`)
emits `total_*_seconds`, counts, issues, **`total_cost_minor`** — consumed by task
detail, `GET /tasks/{id}/steps` (**+WORKER+SELLER**, `tasks.py:933-936`),
`GET /working-sections/{id}/steps` (**+WORKER**, `working_sections.py:145-148`),
worker-stats breakdown (ADMIN/MANAGER, `worker_stats.py:130-133`). ⇒ step
`total_cost_minor` reaches WORKER today (card 4's "existing leak").
`serialize_item_worker_light` (`serializers.py:411-441`) has no money — redaction
precedent. Cost-config API: none (`static_costs` unwired).

### Frontend
Item money typed end-to-end but **rendered nowhere**: schemas at
`managers-app/.../features/items/types.ts:27-28,56-57,84-85,102-135` (computes
`value_formatted`/`cost_formatted` — zero .tsx consumers), `packages/items/src/types.ts:73-74`,
task payload mirrors; only economics editor mounted is the currency field, and only in
the dev harness (`ItemCurrencyField.tsx:12-44` → `TestingFormsContent.tsx:27,197`);
task-creation forms bind `item_currency` only; `use-create-task.ts:84-85` always sends
null money. Worker app: `LastActiveStepCard.tsx:390-407` (live TickingTimer — natural
budget-indicator slot), step cards/detail under `features/task_steps/`. Manager config
patterns: `features/settings/` (header + labelled rows), surface/slide-page CRUD
pattern (`features/upholstery-category/`), and three **type-only stubs**:
`items_configuration`, `static_costs_configuration`, `working_sections_configuration`.

### Application_contracts (`/Users/davidloorenz/Desktop/Developer/Application_contracts`)
Four sets (backend/architecture 54 contracts, Frontend_architecture 32,
AI_Architecture 30, planning/). References to these fields: `planning/item/item_models.md:30,
104-107` (semantics prose + open question on workspace-default currency `:203`),
`planning/isolated_tables/static_cost_models.md` (minor-unit rules `:38-43`, snapshot
mandate `:62-72`), `planning/isolated_tables/currency_governance_models.md:35,54`.
**Gap:** `planning/task/task_step_models.md` and
`planning/working_sections/analytics/analytics_models.md` contain no mention of the
time/cost aggregates that exist in code (intention §2.6 item 4 routes this).

---

## 6. Shared ground with the compensation research (not re-proven here)

Carried over from `../../worker_compensation/planning/research_context.md` (same day,
same branch), re-confirmed by this project's agents wherever touched: the outbox →
router → `queue:analytics` worker pipeline and its at-least-once/idempotency scheme
(§2 there); reconcile SET/delta contract and `_cost_minor` formula; backfill precedent
(`backfill_averaged_time.py`, drained-queue rule); model/enum/money/temporal/migration
conventions (§6 there) including the journaled data-migration exemplar
(`97b60e06d42a`) and partial-unique-in-migration idiom (`595e7b840926:44,50`);
environment caveat (analytics worker launched via Makefile only — absent from
Procfile/docker-compose); archgraph operating rules. **This project does NOT depend on
the compensation intention** (HC-4) — the shared file is evidence provenance, not a
design dependency.

## 7. Architecture graph state (2026-08-11, re-verified this session)

`archgraph_status`: initialized, valid, **116 nodes / 157 edges**, revision
`b0702c3c…` (unchanged from the morning's compensation session), 0 stale, **244
pending reviews**, permissionMode `review`. Relevant nodes for this project (searches
"item", "task", "working section", "cost"): `table-task-item`, `table-item-issue`,
`table-task`, `table-task-step` (rollup columns enumerated in its description),
`vocab-task-state-enum`, `vocab-task-step-state-enum`, `helper-task-state-transitions`
(maybe_evaluate_task_ready = only sanctioned READY route),
`intention-step-transition-analytics`, `domain-work-analytics`,
`analytics-recompute-step-time-totals`, `analytics-reconcile-user-day-time`,
`table-working-section-daily-work-stats`, `concept-attribution-split` (open product
question — inherited untouched), `src-create-instant-task`, `infra-task-router`,
`event-process-step-transition`. **The `Item` table itself is NOT in the graph** — the
mapped branch is step-transition analytics; item/task-creation flows are unmapped.
Implementation sessions record this domain's delta (new tables/domain/commands +
edges into the analytics branch) at phase close, one batched apply_changes; agents
never adjudicate pending reviews.

---

## 8. Documentation drift found while grounding (route via coordinator)

1. `models/tables/items/README.md:34` — `STALL` vs code `STALLED`.
2. `models/tables/items/README.md:53-61` — documents dropped `item_issues` columns
   (`base_time_seconds`, `time_multiplier`, name snapshots).
3. `models/tables/tasks/README.md:8,42` — references nonexistent
   `task_history_record.py` / `latest_history_record_id`.
4. `Application_contracts` planning gap: step/section time+cost aggregates absent from
   `planning/task/task_step_models.md` and `planning/working_sections/analytics/
   analytics_models.md`.
5. Dead code/columns (candidates for later cleanup, NOT this project):
   `Task.recorded_time_marked_wrong` / `Task.taken_from_average` (no writers),
   `TaskStateEnum.STALLED` (never written), `domain/task_steps/aggregate_metrics.py`
   (no callers), `Item.state` machine (inert), `ItemStateEnum` unused values.
6. `raw_intention.md` (this folder) — "return_type" does not exist (intention R-1);
   kept uncorrected: raw input is historical record.

---

## 9. Design reasoning distilled (the "why" behind intention resolutions)

Load-bearing inferences a resuming session should not re-derive:

- **Why the episode is the Task (R-3):** tasks already carry typing
  (task_type/return_source), lifecycle (READY/terminal), workspace scoping, and the
  one-active-PRIMARY-item invariant; an item's tasks over time ARE its episode chain
  (an item may sit on many tasks; a task has one primary item). A separate episode
  entity would restate all of that and add a second lifecycle to keep honest. The cost
  of the choice: episode typing must be **snapshotted** onto evaluations because task
  fields are mutable (`update_task` edits return_source freely).
- **Why evaluations key (task_id, item_id) anyway:** it is the multi-item seam. If
  RELATED items ever become real, additional evaluations per (task, other-item) plus
  an explicit time-allocation rule slot in without moving the committed-chain
  invariant (INV-E1 stays per task in v1; relaxing it is a migration of one index).
- **Why worker-count-free capacity (R-4):** memberships are many-to-many and
  time-varying, so headcount per group is not well-defined; and the spreadsheet's
  worker count cancels arithmetically. Configured aggregate paid-hours makes the
  cancellation structural. UI may present "workers × 160h" as an input helper;
  storage is the total.
- **Why WORKING-only consumption (R-5):** the rate's denominator already discounts
  capacity to the productive fraction (utilization). Charging pauses against the
  allowance would bill non-productive time twice (once in the rate, once in
  consumption). The existing `total_cost_minor` costs working+paused because it
  answers "what did labor cost", not "how much allowance was consumed" — two
  different questions; presenting them as one number is the named hazard.
- **Why resolution-at-commit, not by work date (R-6):** compensation must price each
  day at that day's terms (labor cost is a per-day fact). An item budget is a
  *decision* — "we operate against these assumptions" — so the whole episode reads one
  frozen snapshot; a mid-episode config change affects only subsequent commits. This
  is the projections/committed/actuals triad the raw's closing lines demand.
- **Why one table for projection+committed (R-7):** identical shape, one calculator,
  one serializer; the discriminator is immutable and every operational read filters on
  it structurally. Two tables would duplicate schema and drift; a mutable status flip
  would make history editable (HC-1 violation class).
- **Why terminal-close for results (R-10):** READY has no timestamp and reopens;
  terminal commands own an existing side-effect seam (history/notify/event) — one
  added outbox line, handler recomputes from source, SET by task_id ⇒ replay-safe and
  late-analytics-safe. Results are convenience, never authority (HC-7).
- **Why no zero-budget fallbacks (R-9):** the analytics precedent (missing salary rate
  ⇒ cost 0) makes "unknown" indistinguishable from "zero" — flagged as an inherited
  defect in the compensation shaping. This domain refuses to reproduce it: missing
  config/price ⇒ no evaluation ⇒ explicit "not configured" status.
- **Why static_costs is NOT absorbed (R-9):** flat named amounts with no capacity or
  temporal semantics; wiring it in would conflate "an overhead amount exists" with
  "a production pipeline has a monthly cost and capacity". It remains the seed for
  future non-worker overheads (its README already mandates the snapshot discipline
  this domain generalizes).
- **Batch math worked example (for §9.2 confidence):** worker holds steps A (task 1)
  and B (task 2), both batchable, fully overlapping for 60 min ⇒ sweep gives each 30
  min ⇒ each task's rollup +30 min ⇒ each item consumes 30. Σ = wall clock. A third
  non-batchable step C open in the same hour would take its full 60 and be excluded
  from A/B's divisor (they still split 60 ⇒ 30/30): totals can exceed wall clock only
  via the non-batchable rule, which is the existing, deliberate semantics.

---

## 10. Resume checklist for the next session

1. DONE (rounds 1–2, 2026-08-11): all four cards answered and folded (R1-1…R1-5; new
   §4.7A; §10.2 rewritten). The R1-1 veto point (`item_currency` removal) was
   owner-confirmed the same day (R2-1) — nothing remains open.
2. If a later answer contradicts a resolution, amend affected sections without
   renumbering cited sections (insert lettered sections — charter rule; §4.7A is the
   precedent).
3. Next gate: run **mechanism-inventory** over intention §15's flagged mechanisms
   before any planning (`/Users/davidloorenz/agent-skills/mechanism-inventory.md`).
4. Line numbers may have drifted — verify by symbol name before relying on any.
5. Re-run `archgraph_status` before citing graph state (this file records revision
   `b0702c3c…` / 244 pending).
6. Working branch at shaping time: `fix/idempotent-completion-analytics`; the
   `item_cost_calculation/planning/` folder held only `raw_intention.md` before this
   session; worker_compensation planning docs are committed at `97d2b7c`.
7. The sibling compensation pipeline is deferred by owner decision (commit `97d2b7c`
   message): item cost ships FIRST. Do not let planning sessions assume compensation
   tables exist.
