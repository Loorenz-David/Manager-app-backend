# Research context — worker_compensation (grounding evidence & reasoning)

```
role: grounding evidence appendix (companion to intention.md)
date: 2026-08-11 (all citations verified against the tree on this date)
purpose: let a future session resume this pipeline WITHOUT re-running the research
read order for a resuming session:
  1. intention.md            (the authority — product semantics, resolved decisions)
  2. owner_decisions.md      (4 open cards; check for ANSWER lines)
  3. this file               (evidence behind intention §2, plus reasoning not in the doc)
  next gate: mechanism-inventory (see intention §14 for the flagged mechanisms)
```

Line numbers are as of 2026-08-11 (branch `fix/idempotent-completion-analytics`); they
may drift, but symbol names and file paths are the stable handles.

---

## 1. The two legacy salary columns — complete usage census

### Definition
- `app/beyo_manager/models/tables/users/user_work_profile.py:33-34` —
  `salary_per_hour_before_tax` / `salary_per_hour_after_tax`, both
  `Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)`.
- CHECKs `:59-66`: `X IS NULL OR X >= 0`
  (`ck_user_work_profiles_salary_before_tax` / `..._after_tax`). No index on either.
- Migration `app/migrations/versions/7d92a90e6282_model_creation_for_beyo_manager.py:192-200`;
  no later migration touches them → schema == model.
- `user_work_profiles` has **no soft-delete columns**.

### Writes
1. `services/commands/users/register_user.py:113-114` — profile creation, values straight
   from request (`Decimal | None`). Request `requests/register_user_request.py:16-17`
   with non-negative validator `:68-73`. Route `POST /auth/register`
   (`routers/api_v1/auth.py:45-46,133-147`), `require_roles([ADMIN])`, body
   `model_dump()` **without** `exclude_unset` (keys always present).
2. `services/commands/users/update_user_admin.py:83-86` — per-field, gated on key
   presence in `ctx.incoming_data` (omitted = untouched, explicit null = cleared).
   `_WORK_PROFILE_FIELDS` `:19-23`; lazily creates the profile `:74-81`. Route
   `PATCH /users/{user_client_id}` (`routers/api_v1/users.py:42-43,220-236`),
   `require_roles([ADMIN, MANAGER])`, body fields are **`str | None`** (vs register's
   `Decimal`), `model_dump(exclude_unset=True)`.
   **Asymmetry:** `requests/update_user_admin_request.py:17-18` has **no non-negative
   validator** — a negative salary on PATCH is caught only by the DB CHECK
   (`IntegrityError`, not `ValidationError`).
3. Seeds do NOT write salary (`bootstrap/phases/seed_admin_user.py:75-80`,
   `seed_workers.py:285-290` leave it NULL). Workspace reset deletes whole profiles
   (`reset/phases/delete_user_work_profiles.py`).
4. Test write: `tests/integration/services/commands/users/test_update_user_admin_clock_in_code.py:311`
   writes `"42.5"`, `:317` asserts `Decimal("42.5000")` (quantization round-trip).

### Reads — API surface (FRONTEND-SURFACED — the raw draft claimed otherwise, falsely)
- `domain/users/serializers.py:26-27` — both emitted as 4-decimal strings via
  `_serialize_decimal_4` (`:18-21`, `f"{value:.4f}"`), nested under `work_profile`
  (`:43-44`).
- Reached by exactly three endpoints: `POST /auth/register` (`register_user.py:159`),
  `PATCH /users/{id}` (`update_user_admin.py:94`), `GET /users/{id}`
  (`queries/users/get_user_admin.py:30-37`).
- NOT surfaced by `GET/PATCH /users/me` or the `GET /users` list.
- E2E proof: `tests/users/test_user_management.sh:236` (sends), `:250` (reads
  `.data.user.work_profile.salary_per_hour_before_tax` from the response).
- OpenAPI doc mirrors: `routers/README.md:230-231` (register), `:3784-3785` (patch).

### Reads — computation (ONLY `before_tax`; `after_tax` computes NOTHING anywhere)
- `services/queries/analytics/reconcile_user_time.py:164-173` `_rate()` and its
  byte-for-byte duplicate `services/tasks/analytics/process_step_transition.py:149-158`.
  Both return None for missing profile OR NULL column.
- Backfill: `app/scripts/backfill/backfill_averaged_time.py:114,122` runs both over all
  history.
- **`salary_per_hour_after_tax` is write-and-display only.** Exhaustive grep found no
  other consumer, no aliases (`salary|hourly_rate|cost_per_hour|wage` sweep — only
  near-misses are `units_per_hour` throughput and `*_cost_minor`/`item_cost_minor`).
- No raw SQL / GraphQL / committed OpenAPI JSON references. In
  `/Users/davidloorenz/Desktop/Developer/Application_contracts`, only stale prose:
  `backend/architecture/01_architecture.md:140` (single `salary: Decimal` — outdated).

---

## 2. Analytics cost pipeline — how cost is computed today

### The cost mixin and its five tables
`AggregateMetricsCostMixin` — `app/beyo_manager/models/base/aggregate_metrics.py:40-41`:
single column `total_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)`.
Integer **minor units** (öre); **no currency, no rate snapshot, no server_default**.
Sibling mixins in the same file: Time `:5-8`, InaccurateTime `:11-23`, Counts `:26-32`,
Totals(issues) `:35-37`.

Used by exactly 5 tables:
| table | mixin at | grain / unique |
|---|---|---|
| `user_daily_work_stats` (`udwr`) | `analytics/user_daily_work_stats.py:23` | unique (workspace_id, user_id, work_date) `:45-48` |
| `user_lifetime_stats` (`usr_stat`) | `analytics/user_lifetime_stats.py:23` | unique (workspace_id, user_id) `:44` — Σ table |
| `user_section_daily_work_stats` (`usdwr`) | `analytics/user_section_daily_work_stats.py:23` | unique (ws, user, working_section_id, work_date) `:49-52` |
| `working_section_daily_work_stats` (`wsdws`) | `analytics/working_section_daily_work_stats.py:23` | unique (ws, working_section_id, work_date) `:45-48` — Σ over users |
| `task_steps` (`tsp`) | `tasks/task_step.py:40` | per-step rollup; redeclares inaccurate cols inline `:74-82`, **no inaccurate_step_count** |

Cost columns migration: `befad87b3463_add_analytics_aggregate_tables.py:37,61,88,115`;
task_steps at `7d92a90e6282:739`.

### Trigger chain (event-driven only; no cron for analytics)
1. Producers write `ExecutionTask`+`ExecutionPayload` in the caller's transaction
   (transactional outbox) via `create_instant_task`
   (`services/infra/execution/task_factory.py:46-61`, state OPEN, `max_try=3`).
   Producer sites for `PROCESS_STEP_TRANSITION`:
   `commands/task_steps/transition_step_state.py:299,422`,
   `commands/task_steps/_step_transition_core.py:160,248`,
   `tasks/task_steps/finalize_pending_step_completion.py:188`; clock-out reaches the core
   via `commands/users/_clock_worker_shift.py:203-221` (one per force-paused open step).
2. Router `services/infra/execution/task_router.py`: `PROCESS_STEP_TRANSITION →
   "queue:analytics"` (`:34`); Postgres LISTEN/NOTIFY channel `task_open` (`:56-74`),
   30s fallback poll; RPUSH ids, OPEN→PENDING (`:113-138`). Recovery: RETRY_SCHEDULED→OPEN
   (`:141-157`), stale IN_PROGRESS >90min→OPEN (`:160-179`), stuck PENDING >5min→OPEN
   (`:182-200`).
3. Worker `workers/analytics_worker.py:10-17`: `HANDLER_MAP = {PROCESS_STEP_TRANSITION:
   handle_process_step_transition}`, `run_worker("queue:analytics", ...)`. Generic loop
   `services/infra/execution/worker_base.py:45-68`; claim = `FOR UPDATE SKIP LOCKED`
   (`:117-139`); retries backoff [30,120,300]±15% (`:20-21`), SIGTERM rescue (`:196-207`);
   default handler timeout 300s.
   **At-least-once**: crash between handler-commit and finalize re-executes the task.

### Handler flow — `services/tasks/analytics/process_step_transition.py:35-133`
- Parses `StepTransitionPayload` (`domain/execution/payloads/step_transition.py:7-27`).
- TIME path (`:63-77`) gated on `credited_user_id AND closing_state ∈ TIME_BEARING_STATES`
  ({WORKING, PAUSED}, `domain/task_steps/constants.py:11-14`):
  `work_date = payload.entered_at.date()` → `reconcile_user_day_time` (SET day+section) →
  `apply_reconcile_deltas` (Σ tables) → `_recompute_step_time_totals` (SET step).
- COMPLETION path (`:95-117`) gated on `new_state == COMPLETED`, keyed
  `payload.exited_at.date()`.
- Shift reconcile every credited transition (`:81-86`); realtime emit only on change.
- One `session.commit()` at `:121`.

### Duration: concurrency-averaged sweep
- IO primitive `services/queries/analytics/averaged_time.py:69-144`
  (`compute_record_contributions`): filters workspace,
  `COALESCE(credited_user_id, created_by_id) == user_id` (`:102`), not deleted,
  state ∈ {WORKING, PAUSED} (`:104`), window overlap. Bucket mapping `_BUCKET_STATE`
  (`:41-50`): PAUSED + transition_reason SHIFT_ENDED → derived `"ended_shift"` bucket
  (SQL twin of `domain/analytics/time_buckets.bucket_for`).
- Sweep `domain/analytics/concurrency.py:35-76`: non-batchable = full duration, excluded
  from divisor; batchable split `segment / k` among k concurrent intervals. Batchability
  = `TaskStep.allows_batch_working`. `averaged_seconds_by_record` (`:79-93`) excludes
  marked_wrong; `wasted_seconds_by_record` (`:96-105`) is the marked-wrong population.
  `marked_wrong = record.recorded_time_marked_wrong OR step.recorded_time_marked_wrong`.

### Cost formulas (the code the new domain replaces)
Day/section grain — `reconcile_user_time.py:84-89`:
```python
def _cost_minor(rate_per_hour, working_seconds, pause_seconds) -> int:
    if rate_per_hour is None: return 0
    costed = Decimal(working_seconds + pause_seconds)
    return int(((costed / Decimal(3600)) * rate_per_hour * Decimal(100)).to_integral_value())
```
Applied `:304` (day) and `:305-306` (per-section). `to_integral_value()` default context
= ROUND_HALF_EVEN. Inputs already `int(round(c.seconds))` per contribution (`:296`).

Step grain — `process_step_transition.py:205,218-233`: accumulates
`costed_seconds_by_user[uid] += c.seconds` (float) for buckets working/paused, then per
user `int(((Decimal(int(round(seconds)))/3600) * rate * 100).to_integral_value())`
summed → `step.total_cost_minor` (absolute SET). **Rounding divergence vs day path:**
day rounds each contribution then sums; step sums floats then rounds once per user.

Shared semantics (all inherited by the new design): only working+paused costed, never
`ended_shift`; marked_wrong excluded (feeds `inaccurate_*`/wasted); `rate is None → 0`
(unknown indistinguishable from zero); `×100` hardcodes 2-decimal minor units.

### Upsert semantics & idempotency (the scheme the new design must not break)
Contract in module docstring `reconcile_user_time.py:1-14`:
- `user_daily_work_stats`, `user_section_daily_work_stats`, `task_steps`: recompute &
  **SET** (`_apply_set` `:108-121`; sections dropped from a day explicitly zeroed via
  `all_section_ids = set(per_section) | set(existing_by_section)` `:327`).
- `user_lifetime_stats`, `working_section_daily_work_stats`: **delta application**
  (`_snapshot` `:92-105` → SET → `_TimeTotals.as_delta` `:56-73` → `_apply_delta`
  `:122-133`). Replay ⇒ delta 0 ⇒ Σ tables don't drift.
- Get-or-create = SELECT then add+flush, **no ON CONFLICT, no row locks** — two workers
  reconciling the same user+day can interleave; Σ tables can drift under that race
  (known gap, unchanged by this project).
- Window `_WINDOW_BUFFER = timedelta(days=1)` (`:39`); only settled (`not is_open`)
  records entered on the target date counted (`:279`); deleted steps included (`:278`).

### Reads of cost (why the analytics-table cost is currently invisible)
Single reader in the entire app: `domain/tasks/serializers.py:176`
(`"total_cost_minor": step.total_cost_minor` in `serialize_step`), spread into 5 query
payloads; locked by characterization test
`test_list_working_section_steps_payload_characterization.py:48`. The four analytics
tables' cost is written but read by no API (`list_workers_totals.py:55-64`,
`get_worker_daily_step_breakdown.py:263-267`, `compute_worker_insights.py:40-48` all
skip it). **Cost arithmetic has no dedicated test anywhere.**

### Recalculation precedent
- `app/scripts/backfill/backfill_averaged_time.py` — zeroes all time+cost aggregates
  (`:50-56`, field list `:38-47`), re-runs the production functions per user/day
  (`:114`) and per step (`:121-122`), rebuilds Σ tables by summation (`:130-207`).
  Dry-run default; requires drained analytics queue (`:5`). Caveat: passes `""` as
  display-name snapshot (`:114,:195`).
- Other scripts: `backfill_missing_completion_counts.py`, `backfill_completed_count.py`,
  `backfill_worker_shift_state_records.py`, `heal_open_shifts_today.py`,
  `curate_shifts_from_connecteam.py`. Evidence-writeup precedent:
  `docs/architecture/implemented_summaries/completion_counting_gap_20260811.md`.
- CLI `backfill` command is a stub (`cli/main.py:32-34` → `operations/backfill.py:4-5`
  logs only). Real backfills are scripts, despite `30_migrations.md:21`.
- **No invalidation/dirty-marking mechanism exists**; nothing snapshots rate inputs.

---

## 3. Worked-duration source records

- **`step_state_records`** (`ssr`, `models/tables/tasks/step_state_record.py:29-115`) —
  THE labor-time source of truth. `state: TaskStepStateEnum` (`create_type=False`,
  reuses type), `entered_at`/`exited_at` (`:76-77`, NULL exited = open),
  `created_by_id` (performer, FK RESTRICT) vs `credited_user_id` (`:91`, **no FK by
  design** — comment `:84-90`: approximate-analytics reference + lock-free migration;
  attribution is COALESCE(credited, created_by)). `pause_reason_id` (catalog FK) vs
  `transition_reason` (constrained String(32), code-owned vocabulary — rationale comment
  `:52-64`). `recorded_time_marked_wrong` `:75`, soft-delete trio. Partial unique
  `uix_step_state_records_active` on (workspace_id, step_id) WHERE exited_at IS NULL
  (`:100-106`); CHECK exited >= entered (`:111-114`).
- `task_steps` — per-step rollup + live state (see §2 table).
- `user_shift_state_records` (`uss`) — derived shift segments (comment `:34-45`),
  partial unique active (`:61-68`).
- `user_declared_state_records` (`uds`) — declared pauses, partial unique active.
- Clock-out: `commands/users/_clock_worker_shift.py:131-234` — rebuilds shift middle,
  force-pauses open working steps with transition_reason=SHIFT_ENDED (`:203-221`).

**Known product question (NOT decided by this project)** — archgraph node
`concept-attribution-split`: hours follow the record
(COALESCE(credited, created_by) — ordinary records never set credited_user_id), while
completions follow the payload's credited_user_id. They diverge when a manager opens a
step and closes it crediting a worker. Intention §8.2 explicitly inherits attribution
as-is.

---

## 4. StaticCost (dormant seed for future non-worker costs)

`models/tables/static_costs/static_cost.py:15-44` — `scst` prefix (NB:
`client_id_prefix_map.md:47` wrongly says `stc`). Columns: name, description,
`cost_minor Integer NOT NULL`, `currency StaticCostCurrencyEnum NOT NULL`
(swedish_krona | danish_krona | euro — `domain/static_costs/enums.py:4`), audit +
soft-delete. **Zero commands/queries/routers/serializers** — dormant. Its README
(`static_costs/README.md:37-49`) mandates snapshot-on-use for historical consumers and
defers versioned history — the policy pattern the compensation design generalizes. Raw
intention's "static cost per hour" future lands here (intention §12 deferred).

---

## 5. Worker infrastructure ops caveat

Custom Redis-list worker over Postgres outbox (not Celery/arq/cron). Launch:
`app/Makefile:57-58` (`make analytics-worker`), `:82-85` (`shift-workers`). **Absent
from `app/Procfile:1-7` and `app/docker-compose.yml`** (which runs only `web` + one
`python worker.py`). The master plan's environment topology must verify the real
production launch path before relying on the analytics worker.

---

## 6. Repo conventions the new domain must follow

### Temporal
- **No live effective-dated table.** Two existed only in migration history, both dropped
  before any model file: `issue_category_configs`
  (`7d92a90e6282:265-284` — nullable effective_from/effective_to, window CHECK
  `effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from`,
  unique on (…, effective_from); dropped `99accdeba8b9:84`) and
  `upholstery_inventory_threshold_policies` (`7d92a90e6282:439-460`; dropped
  `a61def0ca46f:31`). **Nullable effective_from = unbounded past is thus precedented** —
  the intention reuses it for migrated seed versions.
- Live "one open row per parent" idiom = **partial unique index on the open predicate**:
  `user_shift_state_record.py:62-68`, `user_declared_state_record.py:48-54`,
  `step_state_record.py:100-106`, and the `removed_at IS NULL` variants
  (`task_item.py:44-57`, `task_step_dependency.py:35-41`,
  `task_step_assignment_record.py:41-46`). Always paired with a window CHECK.
- **No ExcludeConstraint / tstzrange / btree_gist anywhere** in the repo.
- "Current child" pointer idiom: `use_alter=True` FK shortcuts updated atomically with
  the new child — `user.py:41-60` (last_app_view/history), `task.py:96-106`
  (latest_event_id), `task_step.py:110`, `image.py:57`, `item_upholstery.py:52`.
- History tables (`models/tables/history/`, `HistoryRecordMixin`
  `models/base/history_record.py:8-27`) are field-change audit, NOT queryable temporal
  versions.

### Enums
- Python Enum, **lowercase** values, in `domain/<domain>/enums.py` (27 files).
- `SAEnum = configure_sa_enum_values(SAEnum)` (`models/base/sa_enum.py:5-11`,
  values_callable → member.value).
- `mapped_column(SAEnum(MyEnum, name="<singular>_<column>_enum", create_type=True))` on
  the introducing table; `create_type=False` on reuse (counts: 128 True / 21 False).
- Sanctioned alternative for growing code-owned vocabularies: constrained String
  (rationale comment `step_state_record.py:52-64`; repo already paid to drop an enum
  type, `b58cdffb5ccc`).
- Enum migrations: ADD VALUE example `a61def0ca46f:36`; full retype dance
  `ec9017a0245c:19-60`; lowercase rename `ddc5bf50153b`;
  `transaction_per_migration=True` in `env.py:69-74` (ADD VALUE committed before use).

### Money
- Stored amounts: `Integer` minor units, `_minor` suffix, paired currency enum per
  consuming table (`static_cost.py:24-27`, `item.py:38-39`).
- Rates: `Numeric(12,4)` → Decimal, no currency column (the salary columns).
- Aggregated cost: `total_cost_minor Integer` nullable (mixin). **No Float money
  anywhere.** Governing doc:
  `docs/architecture/under_construction/intention/planning_tables/isolated_tables/currency_governance_models.md`
  ("cost_minor is not self-describing without currency"; formal currency table
  deliberately deferred). Sibling `static_cost_models.md` §4 mandates snapshot-on-use.

### Models
- Base: bare `DeclarativeBase` (`models/base/base.py:4-5`). IDs: `IdentityMixin`
  (`models/base/identity.py:14-31`) — `client_id String(64) PK = f"{PREFIX}_{ULID()}"`,
  per-model `CLIENT_ID_PREFIX`. Class shape `class X(IdentityMixin, Base)`.
- No timestamp mixin — inline tz-aware `created_at`/`updated_at` with lambda defaults
  (exemplar `static_cost.py:28-36`).
- Provenance: `created_by_id`/`updated_by_id`/`deleted_by_id` → `users.client_id`
  RESTRICT; "updated_by_id required on every update command" (`update_user_admin.py:90-92`).
- Soft delete trio per `architecture/25_soft_delete.md:19-35`.
- FKs: String(64), `<referenced_singular>_id`, `index=True`, target `client_id`.
  Relationships explicit `foreign_keys=`, usually `lazy="noload"`.
- Workspace scoping near-universal (`architecture/24_multi_tenancy.md:38-60`); workspace
  from JWT (`ctx.workspace_id`), never request body; composite indexes lead with
  workspace_id. Registration required in `models/__init__.py`
  (`architecture/03_models.md:35-46`).
- Best single table to copy from: `user_work_profile.py` (uniques, CHECKs, partial
  unique, exported index-name constant consumed for 409 translation at
  `update_user_admin.py:9,115-120`).

### Migrations
- Alembic at `app/migrations/`, 114 revisions, hex-named (NOT date-prefixed — the
  `30_migrations.md:66` claim is stale). Autogenerate + hand-fix
  (`30_migrations.md:29-45`, checklist `:69-80`).
- **Data-migration exemplar to imitate:**
  `97b60e06d42a_backfill_other_task_priority_transition_.py` — 30-line docstring
  (predicate, populations, reversibility, idempotence), pre-flight `RuntimeError` refusal
  on contradictory rows (`:88-108`), `*_journal` bookkeeping table for exact downgrade
  (`:112-150,209-233`), post-condition count assertions (`:179-206`).
  `env.py:20-48` excludes `*_journal` tables from autogenerate.
- Partial unique in migration: `op.create_index(..., unique=True,
  postgresql_where=sa.text('exited_at IS NULL'))` (`595e7b840926:44,50`).

### Services & domain
- `services/commands|queries|tasks/<domain>/<verb>_<noun>.py`; request objects in
  `requests/` with `parse_*_request` converting pydantic errors; presence/absence idiom
  = `"field" in ctx.incoming_data`.
- Command shape: parse → `async with maybe_begin(ctx.session)` → load/guard/mutate/flush
  → serialized dict. No commit/rollback inside; events via `pending_events` dispatched by
  the owning parent (`architecture/06_commands_local.md`).
- `ServiceContext` (`services/context.py:6-55`); `run_service` → `StatusOutcome`
  boundary; routers never try/except.
- Pure calculation in `app/beyo_manager/domain/<domain>/` (no I/O,
  `architecture/08_domain.md`); `domain/analytics/` (concurrency, time_buckets,
  linear_timeline) is the model to follow for `domain/compensation/`.
- Worker handlers: `handle_<event>(raw: dict, task_id: str)`, own `task_db_session()`.
- Known layering wart to not copy: `queries/analytics/reconcile_user_time.py` WRITES
  despite living under queries/.

### Contract system (pattern-authority)
- 58 numbered contracts under `architecture/` (root), `*_local.md` overrides canonical.
- Routing guide: `task_system/backend_contract_goal_mapping_guide.md` (core set `:56-70`,
  bundles `:73-82`, pattern-authority rule `:16-52`: contracts say HOW to write, code
  only says WHAT exists).
- `docs/README.md` = orientation: living docs in `docs/domains/` updated **in the same
  change**; plan lifecycle under_construction → implemented_summaries → archives.
- No CLAUDE.md; root `AGENTS.md` is the archgraph adapter.
- Contract bundle already selected for implementers: intention §14.

---

## 7. Architecture graph state (2026-08-11)

- Initialized, valid, 116 nodes / 157 edges, revision `b0702c3c…`, **244 pending
  reviews**, permissionMode `review`, maintenance + anchor-repair enabled. Agents never
  adjudicate pending items (human-authorized only).
- Relevant existing nodes (search hits; orient here, don't recreate):
  `intention-step-transition-analytics` (the analytics branch intention),
  `domain-work-analytics`, `analytics-process-step-transition` (WORKER-1),
  `analytics-reconcile-user-day-time`, `analytics-reconcile-user-day-completions`
  (human_confirmed), `analytics-apply-reconcile-deltas`,
  `analytics-apply-completion-reconcile-deltas` (human_confirmed),
  `analytics-recompute-step-time-totals`, `analytics-recompute-step-completion-totals`
  (human_confirmed), `table-user-daily-work-stats`, `table-user-lifetime-stats`,
  `table-user-section-daily-work-stats`, `table-task-step`, `table-user-work-profile`,
  `table-user-shift-state-record`, `infra-analytics-worker`, `infra-queue-analytics`,
  `decision-transactional-outbox`, `decision-credited-user-no-fk`,
  `concept-credited-user-vs-performer`, `concept-attribution-split` (open product
  question), `concept-one-active-step-per-user`, `concept-ended-shift-collapse`,
  `test-completion-replay-idempotency` (human_confirmed),
  `script-backfill-completed-count`, `src-bucket-for`.
- Implementation sessions will record the compensation delta (new tables/domain/commands
  as nodes + edges to the analytics branch) at phase close, per
  `.archgraph/agent-operating-policy.md` (`implement-and-record` workflow, one batched
  apply_changes).

---

## 8. Documentation drift found while grounding (route via coordinator)

1. `architecture/01_architecture.md:140` — stale single `salary: Decimal` field
   description (also mirrored in `Application_contracts/backend/architecture/01_architecture.md:140`).
2. `models/tables/client_id_prefix_map.md:47` — says StaticCost prefix `stc`; code says
   `scst` (`static_cost.py:16`).
3. `architecture/30_migrations.md:66` — claims date-prefixed migration filenames; tree
   uses Alembic hex. Also `:21` points at CLI backfills; reality is
   `app/scripts/backfill/` scripts (CLI stub logs only).
4. `models/tables/users/README.md:31,36` — unimplemented "snapshot previous values
   before overwriting salary" rule; superseded by this intention's versioning.
5. `raw_intention.md` (this folder) — "columns … none of them are surfaced to the
   frontend" is false (see §1). Kept uncorrected: raw input is historical record; the
   correction lives in intention.md R-1.

---

## 9. Design reasoning distilled (the "why" behind intention resolutions)

These are the load-bearing inferences a resuming session should not have to re-derive:

- **Why the snapshot lives on the version row (R-5/R-7):** the four analytics tables +
  task_steps are replayed wholesale (recompute-and-SET) — any snapshot column there is
  overwritten by the next reconcile. The only stable place is the effective-dated version
  itself: persist `gross_hourly_equivalent` / component `hourly_cost` /
  `estimated_cost_per_hour` at version write time, have reconciles READ the persisted
  value (never re-derive). Then formula/code changes can't rewrite history via replay,
  and HC-1 falls out. This also generalizes the already-stated repo policy
  (`static_cost_models.md` §4, `static_costs/README.md:37-49`) and the reasoning on
  `credited_user_id` persistence (`step_state_record.py:84-90` — "so analytics backfills
  reconstruct the same attribution").
- **Why date granularity (R-3):** every rollup is keyed by `work_date =
  entered_at.date()`; a timestamp-granular rate change mid-day is unrepresentable in the
  day-grain tables. One version per (user, date) makes day reconciles resolve exactly one
  rate.
- **Why chain construction, not ExcludeConstraint (R-6):** zero btree_gist precedent in
  the repo; the live idiom (partial unique open-row + single writer command + window
  CHECK) is what implementers and reviewers here already know how to verify.
- **Why future-dated versions are deferred (§7.4):** a future-dated open version breaks
  "open == currently applicable", which the `current_compensation_id` pointer and live
  acquisition rely on; fixing it needs a scheduled pointer-flip job. Resolution-by-date
  already supports future dating architecturally — pure scope deferral.
- **Why per-(user, entered_at date) grouping in the step grain (R-8):** step totals sum
  contributions across records that may span days; each record must be priced by the
  version applicable on ITS date, or a raise mid-step would misprice earlier days'
  records.
- **Why the correction↔reprice coupling is atomic (R-10):** with persisted per-version
  rates, correcting a version changes the rate but NOT the already-written analytics
  rows; those days stay stale until something touches them. If reprice were a separate
  optional step, corrections would silently half-apply — exactly the HC-1 defect class.
- **Migration prices identically by construction:** migrated versions are
  `hourly`/`base = before_tax`/no components, so `estimated_cost_per_hour == before_tax`
  and recomputed history matches legacy output (delta ≈ 0). Card 3 only decides whether
  to prove it at cutover.
- **Inherited limitations deliberately NOT fixed here** (each a deferred-scope line):
  no-rate ⇒ cost 0 (unknown ≡ zero); analytics currency-naivety; Σ-table concurrent
  reconcile race; attribution split.

---

## 10. Resume checklist for the next session

1. Read `intention.md`, then `owner_decisions.md` — if cards have ANSWER lines, fold
   them into intention.md as changelog round 1 and flip the status header accordingly.
2. If any answer contradicts a resolution (e.g. card 1 branch (a) vs the §9.4 bridge),
   amend the affected sections — never renumber cited sections; insert lettered sections
   (charter rule).
3. Next gate: run **mechanism-inventory** (`/Users/davidloorenz/agent-skills/`) over
   intention §14's flagged mechanisms before any planning.
4. Line-number citations in these documents may have drifted — verify by symbol name
   before relying on any exact line.
5. The archgraph may have moved past revision `b0702c3c…` / 244 pending reviews —
   re-run `archgraph_status` and re-search before citing graph state.
6. Working branch at shaping time was `fix/idempotent-completion-analytics`; the
   `worker_compensation/` folder was untracked. Check where it landed.
