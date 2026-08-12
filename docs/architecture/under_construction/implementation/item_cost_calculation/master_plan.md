# Master plan — item_cost_calculation

```
plan: master
role: planner artifact (coordination hub)
round: 1
date: 2026-08-11
status: ACTIVE
authority: planning/intention.md (round 4) is the semantic authority; this file owns
           the shared skeleton (naming registry, contract resolution, environment
           topology, sequencing, tracker). Semantic changes amend the intention;
           skeleton changes amend this file; a phase plan is NEVER patched into
           divergence with either.
```

## 1. Goal

Build the **item-economics domain**: expected sale price minus configured allocation
terms → production budget → aggregate worker-minute allowance, frozen as immutable
committed evaluations per task episode, with what-if projections, live consumption
from the existing step-time rollups, and a replay-safe result refreshed at every
episode boundary (READY entries, reopens, terminal transitions — intention §8B,
round 6; "final" = terminal-computed).
Full semantics: `planning/intention.md` — this plan never restates them. The
mechanism contracts live in intention §4A, §6A, §7A, §7B, §8A, **§8B**, §10A, §11A
(lettered sections govern the numbered ones they amend). Round-4 owner decisions are
settled:
**§8A.5 branch A (re-emit) only — branch B is rejected and no phase builds it**
(guard widened to READY ∪ terminal, round 6);
**§6A.4 gross-base planning-allocation semantics with the binding presentation rule**
(a percentage term is never presented as computing legally payable tax).

## 2. Sources of truth

| Content | Artifact |
|---|---|
| Product semantics, invariants, mechanism contracts | `planning/intention.md` (round 4) |
| Evidence census, verified code facts | `planning/research_context.md` (record — never edited) |
| Owner decisions | `planning/owner_decisions.md` (CLOSED) |
| Gate report, inventory table (34 rows), D-1…D-4 | `handoffs/mechanism_inventory/2026-08-11_mechanism-inventory_r1_handoff.md` |
| Shared skeleton: naming registry, contract resolution, environment topology, tracker | this file |
| Phase-local goal/tasks/criteria + Review log | `plans/phase_<n>_<slug>.md` |
| Session framing | `prompts/<role>/`, generated just-in-time by the coordinator |
| External-source evidence | none — §12 of the intention is satisfied vacuously |

**Fold-back rule:** a semantic gap found mid-phase routes to the coordinator as a
decision card or intention amendment (lettered section, never a renumber); a skeleton
gap amends this file. Nothing is silently patched into a phase plan.

## 3. Roles & session workflow

Per the pipeline charter (`/Users/davidloorenz/agent-skills/pipeline-charter.md`) and skills. State machine:
`NOT_STARTED → PROJECTED → PROMPT_READY → IMPLEMENTING → IMPLEMENTED → REVIEWING →
CHANGES_REQUESTED (→ IMPLEMENTING) → APPROVED`. A phase starts implementation only
when the previous phase is APPROVED. Every implementation and every fix cycle is
committed at `IMPLEMENTED` (`CHECKPOINT (not approved):` prefix, standing owner
authorization). First review = full checklist; re-review = delta-scoped with verified
perimeter. Agents update only their own tracker row; findings go to the phase plan's
Review log (append-only).

**Projection gate (round 0):** mandatory for every phase flagged ⚑ in the tracker
(the phase touches mechanisms ranked S1/S2 in the gate handoff's inventory table);
waivable only for unflagged phases with a recorded one-line justification.
Self-retiring per charter (two consecutive empty ledgers).

**Per-session obligations (every implementer/reviewer session):**
1. Re-emit the §5 contract resolution before coding (implementers).
2. Archgraph: `archgraph_status` + orient on the phase's named nodes at start; record
   the phase's architectural delta at close in ONE batched `archgraph_apply_changes`
   (accurate evidence spans; a delta of zero items is stated, not skipped). Never
   adjudicate the 244 pending reviews. Planner-verified graph state 2026-08-12:
   116 nodes / 157 edges, revision `b0702c3c…`, 0 stale, permissionMode `review`.
3. Tests, tracker row, Review log, checkpoint commit per charter.

## 4. Progress tracker

⚑ = projection gate MANDATORY (silent-failure mechanisms touched; inventory rows cited).

| # | Phase | Plan file | Gate | State | Date | Actor | Note |
|---|---|---|---|---|---|---|---|
| 1 | Worker money redaction | `plans/phase_1_worker_money_redaction.md` | ⚑ (row 33) | **APPROVED** | 2026-08-12 | reviewer (Claude); Codex (fix r2); reviewer r2 (Claude) | review r1: leak closed correctly on all 8 endpoints, 8/8 mutations bite, zero regressions (P-R1 settled: 23 pre-existing failures, identical sets at `545e504` and `4416570`); 2 should-fix — 5 ADMIN criteria rows untested (S1), recorded baseline wrong (S2) — + 6 notes. Coordinator: findings routed (N1/N2→phase 9, baseline→§10, lessons→§9 P-G/P-H), fix-r2 prompt authored; reviewer handoff was deposited late (after the coordinator's sweep) — consumed, authoritative. Fix r2: S1 ADMIN rows added and asserted `== 4321`; S2 baseline correction and full 23-item list recorded; focused 39 passed, full run 1605 passed / 23 failed / 1 deselected. Coordinator: fix handoff consumed, perimeter exact vs `ed99e7e`, arithmetic reconciled (1624→1629 = the 5 rows); re-review r2 prompt authored (probes: reshaped worker assertions, baseline list match, new-row liveness). **Review r2: APPROVED** — perimeter exact (six files, zero production-code change), S1+S2 resolved, criteria now 26/26 (24/24 cells), rows 19/22 survived the reshaping and run twice, all four probes bite per-parameter plus an ADMIN-drop probe reddening exactly 9 ADMIN ids with zero collateral, baseline list set-identical to r1's, suite 1605/23/1 with the failure set byte-identical to baseline, archgraph zero delta. Open notes carried forward: N1/N2→phase 9, N7 (test naming)→next touch |
| 2 | Schema, models & migration | `plans/phase_2_schema_models.md` | ⚑ (rows 1,3,8,11,12,15 — DDL side) | IMPLEMENTED | 2026-08-12 | coordinator; Codex | projection r0 AMENDMENTS_REQUIRED (16-row ledger, 4 blocking: name truncation, open name list, unfalsifiable C5, no disposable-DB harness) — fully routed: §6.2 closed CHECK list + named FKs, §6.1 citation fix, §10 disposable recipe, intention round 7 (icet columns), plan tasks/criteria rewritten (C1a/b, C2 per-clause, C3 12-row table, C5 migration-site, C6); implementer r1: nine models/migration and focused suite 23 passed; full suite 1628 passed / 23 known failures / 1 deselected; enum ownership mutations pass; C2 predicate mutations outstanding for review |
| 3 | Canonical calculator | `plans/phase_3_canonical_calculator.md` | ⚑ (rows 1–14) | NOT_STARTED | 2026-08-11 | planner | pure module, §6A entire |
| 4 | Configuration services | `plans/phase_4_configuration_services.md` | ⚑ (rows 15–20) | NOT_STARTED | 2026-08-11 | planner | groups, chains, guarded deletes, config status |
| 5 | Valuation surface | `plans/phase_5_valuation_surface.md` | ⚑ (rows 15,16 — valuation chain; 34) | NOT_STARTED | 2026-08-11 | planner | ItemValuation chain command + preview |
| 6 | Legacy money migration & API bridge | `plans/phase_6_legacy_migration_api_bridge.md` | ⚑ (rows 31,32) | NOT_STARTED | 2026-08-11 | planner | journaled migrate-and-drop + reject-iff-non-null bridge |
| 7 | Evaluations | `plans/phase_7_evaluations.md` | ⚑ (rows 2,5,7,10,14,16,17,19,21–25) | NOT_STARTED | 2026-08-11 | planner | commit tx, projections, promotion, auto path, mirror |
| 8 | Status & results | `plans/phase_8_status_results.md` | ⚑ (rows 9,26–30,34) | NOT_STARTED | 2026-08-12 | coordinator | status query, result handler, §8B boundary emissions (round-6 fold: READY/reopen hooks, widened guard, C6b) |
| 9 | Living docs & drift routing | `plans/phase_9_docs_and_drift.md` | waivable (no S1/S2 mechanism; docs only) | NOT_STARTED | 2026-08-11 | planner | living-docs page, §2.6 + D-1…D-4 landing spots |

## 5. Contract resolution (goal-mapping guide protocol)

Run per `task_system/backend_contract_goal_mapping_guide.md` from intention §15's
bundle. Implementing sessions re-emit this list before coding. Pattern-authority
rule binds: contracts say how to write; implementation files say only what exists.

**Selected (core):** `01_architecture`, `04_context`, `05_errors`,
`06_commands` + `06_commands_local` (maybe_begin, session-call safety,
subordinate-command event rule), `07_queries` + `07_queries_local` (offset
pagination override), `09_routers`, `21_naming_conventions`, `40_identity` +
`40_identity_local`, `41_user` + `41_user_local`, `42_event` + `42_event_local`,
`48_presence` + `48_presence_local`.

**Selected (intention §15 bundle):** `03_models`, `08_domain`, `11_infra_events`,
`15_testing`, `16_background_jobs`, `24_multi_tenancy`, `25_soft_delete`,
`28_roles_permissions`, `29_feature_workflow`, `30_migrations`, `36_audit_log`,
`46_serialization` + `46_serialization_local`, `50_testing_strategy`,
`51_worker_runtime`, `52_replayability`.

**Added from guide:**
- `12_infra_redis`: trigger "worker" — the result handler rides the outbox →
  `queue:analytics` pipeline.
- `32_concurrency`: the goal explicitly requires row-locking discipline (§7A.2 race
  arbitration, §7A.6 `FOR UPDATE`/`FOR SHARE`, §7B.1 task lock).

**Excluded (with reasons):**
- `13_sockets`: no new socket surface; workspace events follow 42/11.
- `53_operational_cli`: the CLI re-emit is "only if cheap" (§13, R4-1) — load at
  prompt time iff the coordinator picks it up.
- `55_query_filters_local`: v1 list endpoints take no search/filter params; add at
  prompt time if that changes.
- `37_scheduled_jobs`: future-dated config versions are deferred — no scheduler.
- `49_observability_runtime`, `54_ci_cd_runtime`, `33_deployment`,
  `31_health_observability`: no new worker process, no CI/deploy change — the handler
  registers in the existing analytics worker.
- `57_shopify_integration`, `34_file_storage`, `35_gdpr_erasure`, `18_security`,
  `19_integrations`, `22_performance`, `20_api_versioning`, `26/27/38/39/43/44/45/47/56`:
  no touchpoint in this domain's v1 surface.

**Contract gap found by the planner (coordinator to route):** canonical `05_errors.md`
defines a `code: str` attribute on `DomainError` subclasses; the implementation
(`app/beyo_manager/errors/base.py`, `validation.py`, `not_found.py`) carries only
`message` + `http_status` — no code field, and no `05_errors_local.md` records the
divergence. This plan does not repair the drift; §6's error-identity carrier decision
below is valid under either resolution.

**Contract gap 2 (phase-1 projection D7, recorded 2026-08-12):** `46_serialization.md`
mandates router-owned serialization ("services never call serializer functions";
dataclasses, never dicts); the repo's entire task / working-section query layer does
the opposite, and `46_serialization_local.md` is an unmodified template recording no
override. **Standing divergence record:** phases of this project keep serialization
where the code they modify has it (the query layer); re-emitting the contract bundle
is never license to relocate serialization mid-phase. The local contract file's
actual amendment lands with the phase-9 drift batch, alongside the `05_errors` gap.
Verified not in conflict: `28_roles_permissions` blesses `require_roles` route
dependencies and the `role_name` claim — identity-derived flags at the query boundary
are contract-faithful.

## 6. Shared skeleton & naming registry (FINAL — authority over intention's proposals)

Registry authority per intention §4 preamble. Conventions per §2.5 and
`21_naming_conventions`. Every name below is fixed; a session needing an unlisted
name routes it back to the coordinator rather than inventing one.

### 6.1 Tables, model classes, client_id prefixes

| Table | Class | Prefix | Model file (`app/beyo_manager/models/tables/item_economics/`) |
|---|---|---|---|
| `production_cost_groups` | `ProductionCostGroup` | `pcg` | `production_cost_group.py` |
| `production_cost_group_sections` | `ProductionCostGroupSection` | `pcgs` | `production_cost_group_section.py` |
| `production_cost_basis_versions` | `ProductionCostBasisVersion` | `pcbv` | `production_cost_basis_version.py` |
| `cost_model_versions` | `CostModelVersion` | `cmv` | `cost_model_version.py` |
| `cost_model_terms` | `CostModelTerm` | **`cmvt`** | `cost_model_term.py` |
| `item_cost_evaluations` | `ItemCostEvaluation` | `ice` | `item_cost_evaluation.py` |
| `item_cost_evaluation_terms` | `ItemCostEvaluationTerm` | `icet` | `item_cost_evaluation_term.py` |
| `item_cost_results` | `ItemCostResult` | `icr` | `item_cost_result.py` |
| `item_valuations` | `ItemValuation` | `ival` | `item_valuation.py` |

- **`cmvt` replaces the intention's proposed `cmt`, which collides with
  `ContentMention | cmt`** in `client_id_prefix_map.md` (verified 2026-08-12).
  Mnemonic: cost-model-version term. All other proposed prefixes verified free.
- All nine registered in `models/__init__.py` and appended to
  `client_id_prefix_map.md`; one table guide `models/tables/item_economics/README.md`.
- Migration journal table `item_valuation_migration_journal` (§10A.1) is
  migration-internal: no ORM model, no prefix, PK `item_client_id`; created and
  dropped by the phase-6 migrations only.
- Column names exactly as intention §4/§4A (as amended: `cost_per_worker_minute_minor`,
  `cost_per_worker_minute_minor_snapshot`, `percent_value`, `fixed_amount_minor`).
  Temporal columns `effective_from`/`effective_to` (Date) — a deliberate, recorded
  deviation from `21`'s `<context>_date` suffix guidance, justified by §7A.3's
  calendar-date resolution semantics and vocabulary continuity with the sibling
  compensation intention. *(Correction, projection D14: the previously cited
  `issue_category_configs` precedent was dropped from the schema by `99accdeba8b9`
  and used `DateTime`, not `Date` — no live effective-dated table exists; the
  decision stands on the semantics, not on precedent.)*

### 6.2 Constraint & index names (repo idiom: `uix_` partial uniques, `ck_` CHECKs)

| Invariant | Name |
|---|---|
| group name unique per workspace (non-deleted) | `uix_production_cost_groups_name_active` |
| INV-G1 one active group per section | `uix_production_cost_group_sections_active` |
| INV-B1 one open basis version per group | `uix_production_cost_basis_versions_open` |
| INV-M1 one open model version per workspace | `uix_cost_model_versions_open` |
| A5 one `item_purchase_cost` term per version | `uix_cost_model_terms_purchase_cost` |
| term name unique per version (non-deleted) | `uix_cost_model_terms_name_active` |
| INV-E1 one current committed evaluation per task | `uix_item_cost_evaluations_current` |
| INV-V1 one current valuation per item | `uix_item_valuations_current` |
| one result per episode | `uq_item_cost_results_task_id` (plain unique) |

**CHECK constraints (CLOSED enumerated list — phase-2 projection D1/D2, 2026-08-12;
this replaces the earlier pattern rows).** Registry rule: names use the full table
name unless the result exceeds **60 bytes** (PostgreSQL truncates at 63 silently —
verified empirically), in which case the table token is the registered client
prefix. C1 asserts exactly this list, nothing else.

| Constraint | Name (bytes) |
|---|---|
| `production_cost_basis_versions.fixed_monthly_cost_minor > 0` (A1) | `ck_pcbv_fixed_monthly_cost_minor_positive` |
| `production_cost_basis_versions.cost_per_worker_minute_minor > 0` (A2) | `ck_pcbv_cost_per_worker_minute_minor_positive` |
| `production_cost_basis_versions.monthly_paid_hours > 0` | `ck_pcbv_monthly_paid_hours_positive` |
| `production_cost_basis_versions.planning_utilization_percent > 0` | `ck_pcbv_planning_utilization_percent_positive` |
| `production_cost_basis_versions.planning_utilization_percent <= 100` | `ck_pcbv_planning_utilization_percent_max` |
| basis-version window | `ck_production_cost_basis_versions_effective_window` |
| model-version window | `ck_cost_model_versions_effective_window` |
| term per-type nullability (6A.4) | `ck_cost_model_terms_value_by_type` |
| `cost_model_terms.percent_value >= 0` | `ck_cost_model_terms_percent_value_non_negative` |
| `cost_model_terms.fixed_amount_minor >= 0` | `ck_cost_model_terms_fixed_amount_minor_non_negative` |
| `item_cost_evaluations.expected_sale_price_minor >= 0` | `ck_ice_expected_sale_price_minor_non_negative` (full name is 63 bytes — prefix token per the rule) |
| `item_cost_evaluations.purchase_cost_minor >= 0` | `ck_ice_purchase_cost_minor_non_negative` |
| `item_valuations.expected_sale_price_minor >= 0` | `ck_item_valuations_expected_sale_price_minor_non_negative` |
| `item_valuations.purchase_cost_minor >= 0` | `ck_item_valuations_purchase_cost_minor_non_negative` |
| valuation ≥1 amount | `ck_item_valuations_amount_present` |
| `item_cost_results.actual_worker_seconds >= 0` | `ck_item_cost_results_actual_worker_seconds_non_negative` |

**Deliberate CHECK absences (registry decisions — stated so nobody "fixes" them):**
`production_budget_minor` / `allowed_worker_minutes` carry NO CHECK (A8);
`task_state_snapshot` carries NO narrowing CHECK (admission is the §8B.2 handler's
job); `percent_value` has NO upper-bound CHECK — `Numeric(6,3)` is the bound (1000
raises `NumericValueOutOfRangeError`, a DataError, before any CHECK — verified;
projection D12).

**Named foreign keys (projection D7):** the three self-FKs are `use_alter=True`
per §2.5's pointer convention, explicitly named, and **hand-added to the migration**
— autogenerate omits `use_alter` FKs in this repo (precedent `243e62bcd858`):
`fk_item_cost_evaluations_superseded_by_id`,
`fk_item_cost_evaluations_promoted_from_id`,
`fk_item_valuations_superseded_by_id`.

### 6.3 Enums

| Where | Python class | PG type | Notes |
|---|---|---|---|
| term calculation type | `CostModelTermCalculationTypeEnum` | `cost_model_term_calculation_type_enum` | members `PERCENTAGE_OF_EXPECTED_SALE_PRICE`, `FIXED_AMOUNT`, `ITEM_PURCHASE_COST`; lowercase values |
| evaluation kind | `ItemCostEvaluationKindEnum` | `item_cost_evaluation_kind_enum` | `PROJECTION`, `COMMITTED` |
| currencies (3 columns) | **reuse `ItemCurrencyEnum`** (`domain/items/enums.py`) | `item_valuation_currency_enum`, `production_cost_basis_version_currency_enum`, `cost_model_version_currency_enum` | one Python class, three per-table PG types (each `create_type=True` on its own column); values stay lockstep by construction |
| evaluation episode snapshots | reuse `TaskTypeEnum` / `TaskReturnSourceEnum` | **reuse** `business_task_type_enum` / `task_return_source_enum` with `create_type=False` | type-creation ownership stays on `tasks` columns (R2-1 lesson: pin ownership explicitly; PG enums are append-only, so snapshots can never hold a value the type lost) |
| result lifecycle snapshot (round 6) | reuse `TaskStateEnum` | **reuse** `task_state_enum` with `create_type=False` (ownership stays on `tasks.state`, `task.py:52`) | `item_cost_results.task_state_snapshot` — §4.6 as amended, §8B.2 |
| economics status | `EconomicsStatusEnum` | **none — never persisted** | code-owned (§11A.4, catalog lesson); members = the 11 ordered values of §11A.4, lowercase values |

All new enums via `configure_sa_enum_values` (`models/base/sa_enum.py`), lowercase
values, in `app/beyo_manager/domain/item_economics/enums.py`.

### 6.4 Error identities

The implementation's `DomainError` classes carry no `code` field (§5 gap). **Carrier
decision:** an error identity is the leading token of `message`, format
`<IDENTITY>: <human sentence>`. Tests assert the exact leading token (and class /
http_status). Raised as `ValidationError` unless noted `ConflictError`.

Identity list (FINAL — includes registry-authored names for errors the intention
required but did not name):

- Selection (§7A.5, in order): `ITEM_COST_NO_COST_GROUP`,
  `ITEM_COST_AMBIGUOUS_COST_GROUP` (message names count + group ids),
  `ITEM_COST_NO_BASIS_VERSION` (rows 3 AND 4 — same identity, pinned),
  `ITEM_COST_NO_COST_MODEL_VERSION`.
- Inputs (§6A.9, §6A.4, §7B): `ITEM_COST_ITEM_UNVALUED`,
  `ITEM_COST_EXPECTED_PRICE_REQUIRED` (registry-authored),
  `ITEM_COST_PURCHASE_COST_REQUIRED`, `ITEM_COST_CURRENCY_MISMATCH` (message names
  both sides and which pair failed), `ITEM_COST_TASK_TERMINAL`,
  `ITEM_COST_NO_PRIMARY_ITEM`.
- Rate: `ITEM_COST_RATE_UNDERFLOW` (§6A.6).
- Chain races (`ConflictError`, §7A.2): `ITEM_COST_CONCURRENT_COMMIT`,
  `ITEM_COST_CONCURRENT_VALUATION`, `ITEM_COST_CONCURRENT_BASIS_VERSION`,
  `ITEM_COST_CONCURRENT_MODEL_VERSION`.
- Version admission (§7A.4; chain named in the identity, registry-authored):
  `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN`,
  `ITEM_COST_MODEL_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN`.
- Guarded deletes (§7A.6, §7.5; registry-authored):
  `ITEM_COST_BASIS_VERSION_IN_USE`, `ITEM_COST_MODEL_VERSION_IN_USE`,
  `ITEM_COST_GROUP_IN_USE`.
- Valuation validation (§4.7A, test 11; registry-authored):
  `ITEM_COST_VALUATION_AMOUNT_REQUIRED` (both amounts NULL),
  `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` (delete attempted on a superseded
  valuation row, §7.5). Negative amounts and missing currency are request-schema
  rejections (pydantic 422) + DB CHECK — no domain identity.
- Group membership (INV-G1; registry-authored): `ITEM_COST_SECTION_ALREADY_GROUPED` —
  same identity on the application pre-check (`ValidationError`) and on the DB
  conflict path (`ConflictError`), mirroring the §7A.5 rows-3/4 same-identity rule.
- API bridge (§10A.3): pydantic `ValidationError` with message
  `ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint`.
- Migration pre-flight P1/P2 (§10A.2): `RuntimeError` aborting `upgrade` with a row
  report — never a DomainError (no request context).

### 6.5 Files — domain, services, workers, routers

- **Domain (pure, no I/O):** `app/beyo_manager/domain/item_economics/`
  `calculator.py` (§6A entire: boundary guards, Q1–Q5, budget, rate, allowance,
  consumption/variance, `CALCULATION_VERSION: int = 1`, `rederive()`),
  `enums.py`, `configuration.py` (pure §7A.5 ordered classifier over loaded rows →
  `EconomicsStatusEnum` / selection outcome), `serializers.py` (manager evaluation /
  status serializers AND the worker status serializer — the worker one has **no
  monetary keys at all**, a separate function, per §11A.3).
- **Commands:** `app/beyo_manager/services/commands/item_economics/` with
  `requests/__init__.py`:
  `create_production_cost_group.py`, `update_production_cost_group.py`,
  `delete_production_cost_group.py`, `add_section_to_cost_group.py`,
  `remove_section_from_cost_group.py`, `create_production_cost_basis_version.py`,
  `delete_production_cost_basis_version.py`, `create_cost_model_version.py`,
  `delete_cost_model_version.py`, `set_item_valuation.py`, `delete_item_valuation.py`,
  `commit_item_cost_evaluation.py`, `create_item_cost_projection.py`,
  `delete_item_cost_projection.py`, `promote_item_cost_projection.py`.
- **Queries:** `app/beyo_manager/services/queries/item_economics/`:
  `get_economics_configuration_status.py`, `list_production_cost_groups.py`,
  `list_production_cost_basis_versions.py`, `list_cost_model_versions.py`,
  `get_item_valuation_history.py`, `get_task_budget_status.py` (ADMIN/MANAGER),
  `get_task_budget_status_worker.py` (WORKER/SELLER — separate service, §11A.3),
  `list_task_evaluations.py`, `get_item_lifetime_economics.py`.
- **Worker handler:** `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py`
  (`handle_process_item_cost_result`), registered in
  `beyo_manager/workers/analytics_worker.py` handler map.
- **Task type & routing:** `TaskType.PROCESS_ITEM_COST_RESULT = "process_item_cost_result"`
  (`domain/execution/enums.py`), routed `"queue:analytics"` in
  `services/infra/execution/task_router.py`.
- **Payload:** `domain/execution/payloads/item_cost_result.py` —
  frozen dataclass `ItemCostResultPayload(workspace_id, task_id)` and nothing else
  (§8A.3).
- **Router:** `routers/api_v1/item_economics.py`, blueprint `api_v1_item_economics`,
  path root `/api/v1/item-economics/`. Routes (kebab-case):
  `POST|GET /cost-groups`, `PATCH|DELETE /cost-groups/<client_id>`,
  `POST /cost-groups/<client_id>/sections`,
  `DELETE /cost-groups/<client_id>/sections/<working_section_client_id>`,
  `POST|GET /cost-groups/<client_id>/basis-versions`,
  `DELETE /basis-versions/<client_id>`, `POST|GET /cost-model-versions`,
  `DELETE /cost-model-versions/<client_id>`, `GET /configuration-status`,
  `PUT /items/<item_client_id>/valuation` (set + returns §11A.5 preview),
  `GET /items/<item_client_id>/valuations`, `DELETE /items/<item_client_id>/valuation`,
  `POST /tasks/<task_client_id>/evaluations/commit`,
  `GET /tasks/<task_client_id>/evaluations`,
  `POST /tasks/<task_client_id>/projections`, `DELETE /projections/<client_id>`,
  `POST /projections/<client_id>/promote`,
  `GET /tasks/<task_client_id>/budget-status` (all roles; handler selects the worker
  service for WORKER and SELLER identities, the manager service for ADMIN/MANAGER),
  `GET /items/<item_client_id>/economics` (lifetime read model).
  Role gates: everything ADMIN/MANAGER except budget-status (all roles, role-split
  serialization) per cards 2/4 and §11A.1.
- **Workspace event:** `item_economics:evaluation-committed` (matches
  `task:state-changed` shape; dispatched after the transaction per §7B.1 step 9).
- **Living docs:** `docs/domains/item_economics.md` (phase 9).
- **Config keys / env vars:** none — this domain adds no configuration.
- **Tests:** under `tests/` mirroring existing layout; factories/fixtures added by a
  phase must have a caller in that same phase (charter rule 4).

## 7. Sequencing & gates

Linear chain; phase N starts only when phase N−1 is APPROVED.

1 (redaction — no schema dependency, closes a live exposure first)
→ 2 (schema) → 3 (calculator; imports phase-2 enums)
→ 4 (config services; rate derivation calls the calculator)
→ 5 (valuation; preview needs calculator + §7A.5 classifier)
→ 6 (legacy migration; the valuation surface of 5 must exist before item CRUD loses
     money — replacement before removal)
→ 7 (evaluations; needs 3+4+5, runs on final schema after 6)
→ 8 (status & results; needs 7)
→ 9 (docs & drift; documents what shipped).

**§10A.3 sequencing note (planner-owned):** the API-bridge validator ships in
phase 6 and is **kept for at least one release**; its removal (together with the
request-schema keys) is explicitly OUT of this project's scope and is recorded as a
follow-up item for the release after the frontend stops sending the keys. No phase
in this plan deletes it.

## 8. Tool protocols

Archgraph per §3 obligations. Named orientation nodes per phase are listed in each
phase plan.

**D-3: RESOLVED 2026-08-12** — owner-authorized; the node was promoted to
`human_confirmed` with corrected anchors (161–234); audit record
`.archgraph/reviews/2026-08-12T10-23-51-250Z--45ed55.yml`; graph revision now
`810325a0…`, pending 243. Ledger record:
`../archGraph_mapping_mantainance/resolved/node-analytics-recompute-step-time-totals.md`.
Its three outgoing edges still carry the stale 138–211 span and remain pending —
queued for the phase-8/9 delta adjudication.

**Graph-delta adjudication flow (standing owner authorization, 2026-08-12):** for
review items **created or changed by this implementation's phases** (and the three
stale-anchor edges above), the phase reviewer verifies the delta as part of the
phase review, and the **coordinator confirms** (promote/reject via
preview→apply) after the phase is APPROVED — batched per phase, each with its
audit record and a commit. The pre-existing pending backlog (unrelated to this
project) remains owner-adjudicated; sessions still never adjudicate it.
Reporter discipline (learned on D-3): a discrepancy is "filed" only when its file
exists in the maintenance ledger's `open/` — a handoff row alone is not a filing.

## 9. Standing rules

Charter rules 1–11½ imported wholesale. Project-specific additions:

- **P-A (two cost numbers):** `task_steps.total_cost_minor` and any item-economics
  money figure never co-occur in one payload, query projection, or doc sentence
  without the §8A.2 divergence statement. The disjointness test (phase 8) is the
  structural guard.
- **P-B (R-9, no inferred zeros):** absent input ⇒ named error or `null` + status —
  never 0. Every status payload row for a non-`ok`/`infeasible` status carries
  `null` numerics (§11A.4).
- **P-C (vocabulary):** "worker-minutes" everywhere; "minutes per worker" is banned
  from schema, API names, payload keys, docs, and test names (R-14).
- **P-D (presentation rule, R4-2):** wherever a percentage term is documented or
  serialized, it is presented as a planning allocation; never as computing legally
  payable tax. Phase 4 (API field docs) and phase 9 (living docs) carry it as
  tasks + criteria.
- **P-E (HC-3):** no phase modifies `step_state_records` writers, the concurrency
  sweep, or `_recompute_step_time_totals` — except the four §8B emission touch
  points, all phase 8: the §8A.5 guarded re-emit line in
  `handle_process_step_transition` (guard: READY ∪ terminal, round 6), one emit hook
  in `maybe_evaluate_task_ready`, one in `maybe_reopen_task_to_working`
  (`services/commands/tasks/_task_state_transitions.py`), and the three terminal
  commands' side-effect lines. Nothing else in the execution path.
- **P-F (calculator monopoly):** every derived economic value is produced by
  `domain/item_economics/calculator.py`; no service computes money/rate/minutes
  arithmetic inline. Snapshots are written only from calculator outputs.
- **P-G (review-r1 lesson 1; extended by re-review r2):** when a criteria table
  carries rows whose expected outcome is identical to a neighbour's (e.g. ADMIN
  mirroring MANAGER), the plan names them **separately required** or collapses
  them explicitly — a row that looks redundant is the row that gets sampled.
  Additionally: (a) such **retention rows get their own named mutation** ("removing
  ADMIN from the allow-list must redden every ADMIN row") so they cannot be
  dismissed as redundant — charter rule 11 applied to retention, not only guards;
  (b) role/audience-parametrized tests **name the audience in the test name**, not
  one example member (opacity about covered roles is what produced S1/N7).
  Implementer prompts restate this where such rows exist.
- **P-I (re-review-r2 lesson 3):** a fix cycle that adds test rows to satisfy a
  coverage finding **mutation-tests those rows itself** — "do the new rows bite?"
  never reaches the re-reviewer unanswered. Fix prompts carry this line whenever
  the findings include missing coverage.
- **P-H (review-r1 lesson 4):** a phase that redacts or reshapes an existing
  payload carries a one-line **structural criterion** for the HTTP boundary — "no
  `response_model` (or equivalent coercion) on the affected routes re-adds the
  field" — because the query-level harness cannot observe it. Applies to phase 8's
  worker status payload.
- **Projection practice (review-r1 lesson 2):** projections enumerating breaking
  tests grep the affected **payload keys** across the test tree, not only callers
  of the changed symbol (D8 missed one of three this way).

## 10. Environment topology (VERIFIED 2026-08-12 in this workspace — update here if reality disagrees)

- **Working directory for all commands:** `backend/app/` (repo-root-relative:
  `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app`).
- **Infra:** `make dev-up` starts postgres + redis in Docker (hybrid mode: app local,
  infra containerized). `make dev-up-full` runs backend + worker containerized.
  Service addresses: PostgreSQL `127.0.0.1:5433`, Redis `127.0.0.1:6380`.
- **Codex sandbox access — RESOLVED by permanent configuration (owner,
  2026-08-12):** the default Codex sandbox originally could not reach
  `127.0.0.1:5433` / `127.0.0.1:6380` (this burned the phase-1 baseline —
  connection-noise failures recorded as a baseline). The owner has since granted
  the access in Codex's own configuration, so **prompts no longer carry an
  elevated-permissions clause**. The environment-agnostic rule stands for every
  agent and session: **a run whose environment cannot reach the database/Redis is
  never recorded as a baseline or as evidence** — the session verifies
  connectivity is real (no connection-refused / `OperationalError` noise in the
  output) and otherwise stops and reports "baseline unobtainable".
- **Tests:** `PYTHONPATH=. pytest -m 'not e2e'` — **`PYTHONPATH=.` is required**;
  bare `make test` (which omits it) fails at conftest import
  (`ModuleNotFoundError: beyo_manager`), verified 2026-08-12. Collection verified:
  `PYTHONPATH=. pytest --collect-only -q` → **1602 tests, 1.72s**. Markers:
  `unit` / `integration` / `e2e` (`pytest.ini`, strict markers, asyncio_mode auto).
  **Verified branch baseline (reviewer r1, healthy containers, elevated
  permissions, 2026-08-12):** pre-phase-1 `545e504` → 1578 passed / **23 failed** /
  1 deselected; phase-1 checkpoint `4416570` → 1600 passed / **23 failed** /
  1 deselected — failure sets byte-identical (zero phase-1 regressions). The 23
  pre-existing failures are enumerated in the phase-1 Review log (S2 correction);
  later phases compare against that list, not the implementer's original
  sandbox-invalidated numbers.
- **Migrations:** `APP_ENV=development alembic upgrade head` (= `make db-migrate`);
  autogenerate via `APP_ENV=development alembic revision --autogenerate -m "<msg>"`
  then hand-fix per `30_migrations` (partial uniques via `postgresql_where`, idiom
  `595e7b840926:44,50`; journaled data-migration exemplar `97b60e06d42a`; both files
  verified present in `migrations/versions/`).
- **Analytics worker launch caveat (VERIFIED):** the analytics worker starts ONLY via
  `make analytics-worker` (`PYTHONPATH=. APP_ENV=development python -m
  beyo_manager.workers.analytics_worker`). It is **absent from the Procfile** (which
  carries web / worker / task-router / delayed- & recurring-scheduler / tasks-worker /
  email-idle-watcher) **and from docker-compose** (services: postgres, redis, backend,
  generic `worker: python worker.py`). Outbox dispatch additionally needs
  `make task-router`. Gotcha: `make worker-logs` tails the *Docker* `worker` service,
  not any Makefile-launched local worker.
- **DB safety:** destructive verification (migration round-trips, downgrade tests)
  on disposable databases only; the configured DB is always left at `head`
  (charter rule 7). `make reset-db` is dry-run by default. Tests that commit rows
  own their teardown (charter rule 11½).
- **Disposable-database recipe (projection D4, verified mechanics 2026-08-12):**
  the suite and alembic both resolve `settings.database_url`, and a real
  `DATABASE_URL` env var **overrides `.env`** (pydantic-settings precedence;
  `config.py` alias `DATABASE_URL`). So, from `backend/app/`:
  1. `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager_disposable PYTHONPATH=. APP_ENV=development python3 -m scripts.create_db`
  2. same `DATABASE_URL=…` prefix on `alembic upgrade head` / `alembic downgrade <rev>` for the round-trip;
  3. drop afterwards: `docker compose exec postgres psql -U postgres -c 'DROP DATABASE beyo_manager_disposable;'`.
  **Without the `DATABASE_URL` override, every pytest/alembic command targets the
  configured development database** (`.env` → `beyo_manager` @ 5433) — there is no
  built-in test-schema creation anywhere in `tests/` (no `create_all`, no alembic
  hook). Plans must say per criterion which database it runs against.
- **Error surface:** `run_service` (`services/run_service.py`) is the single error
  boundary; DomainError → `StatusOutcome(success=False, error=exc)`; identities per
  §6.4 travel in `error.message`.

## 11. Only-if-cheap ledger (coordinator picks up at prompt time; never blocks a gate)

Per intention §13: embedded budget block in step/task payloads (minutes/percent only,
every role); operational CLI re-emit of `PROCESS_ITEM_COST_RESULT`
(`53_operational_cli` pattern — a convenience, NOT the repair path, R4-1);
evaluation `note` field; projection comparison endpoint.
