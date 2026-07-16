# PLAN_worker_stats_daily_metrics_20260715

## Metadata

- Plan ID: `PLAN_worker_stats_daily_metrics_20260715`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-15T15:10:00Z`
- Last updated at (UTC): `2026-07-15T14:56:02Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`
- Predecessor: `PLAN_worker_stats_last_interacted_steps_20260715` (implemented + reviewed)

## Goal and intent

- Goal: Evolve `GET /api/v1/worker-stats/last-interacted-steps` so each worker entry also carries **daily work stats for the current date**: total worked time, total paused time, and the count of task steps completed.
- Business/user intent: Managers get an at-a-glance daily productivity read (time working, time paused, steps finished today) alongside each worker's last-interacted step.
- Non-goals:
  - No change to the last-interacted-step / batch logic already shipped.
  - No historical/range reporting — a single day only (defaults to today).
  - No cost/salary, issues, or ended-shift metrics in the response (they exist in the table but are out of scope here).

## Scope

- In scope:
  - **Analytics pipeline extension**: add a `total_completed_count` metric to the aggregate stats and increment it in the background analytics worker on each `COMPLETED` transition.
  - **Schema migration** for the new column across the analytics tables that share the counts mixin.
  - **Backfill** of `total_completed_count` from historical `StepStateRecord` completions (idempotent operational script).
  - **Endpoint/query**: read `user_daily_work_stats` for the page's workers on the resolved `work_date`, surface `daily_stats` per worker, add an optional `work_date` query param (defaults to UTC today).
  - Handoff-doc update.
- Out of scope:
  - Section-level or lifetime-level *reads* (the worker/backfill still write those scopes for consistency, but the endpoint only reads `user_daily_work_stats`).
  - Any timezone infrastructure — the system is UTC-only and stats are UTC-`work_date`-bucketed.
- Assumptions:
  - `total_working_seconds` and `total_pause_seconds` on `user_daily_work_stats` are authoritative for worked/paused time (written by the analytics worker). Confirmed in `process_step_transition.py`.
  - A `COMPLETED` transition writes exactly one per-step `PROCESS_STEP_TRANSITION` outbox task with `exited_at = now` (completion moment). Confirmed in `_step_transition_core.py:218`.
  - The analytics increment model is **at-least-once** (retries can double-count) — the new counter inherits the same property as the existing `*_count` metrics; acceptable and consistent.

## Clarifications required

Both blocking decisions resolved with the requester on 2026-07-15:

- [x] **Completed-count source** — the analytics tables have **no** completed-step counter today (the `*_count` fields count state-transition intervals, not completions). Resolution: **extend the analytics pipeline** (new column + worker increment + migration + backfill), consistent with how worked/paused time is sourced.
- [x] **"Current date" boundary** — Resolution: **optional `work_date` query param, defaulting to UTC today**. Resolves to a single UTC-keyed `work_date` row (matching how the table is bucketed).

## Acceptance criteria

1. Each entry in `workers[]` gains a non-null `daily_stats` object:
   ```json
   "daily_stats": {
     "work_date": "2026-07-15",
     "total_working_seconds": 3600,
     "total_pause_seconds": 600,
     "total_completed_count": 5
   }
   ```
2. `daily_stats` values come from the worker's `user_daily_work_stats` row for the resolved `work_date`; a worker with **no row** for that date yields zeros with the `work_date` echoed (never `null`, never a 500).
3. `work_date` resolution: `?work_date=YYYY-MM-DD` when provided and valid; otherwise `datetime.now(timezone.utc).date()`. An unparseable `work_date` yields a validation error via the standard error contract (not a 500).
4. The daily-stats read is **one query for the whole page** (workers filtered by `user_id IN page`, `workspace_id`, `work_date`) — no per-worker N+1.
5. `total_completed_count` in the table is incremented by exactly **1 per completed step**: the analytics worker, on `new_state == COMPLETED`, increments the counter on the user-daily (and lifetime + section scopes) bucketed on the **completion date** (`exited_at.date()`), independent of `recorded_time_marked_wrong` and independent of whether the step had issues.
6. The new column exists on all analytics tables that use the shared counts mixin, is `NOT NULL DEFAULT 0`, and existing rows read as `0` post-migration.
7. Backfill: after running the backfill script, `total_completed_count` on `user_daily_work_stats` equals the true count of that user's `COMPLETED` `StepStateRecord`s per `work_date`; the script is idempotent (re-running does not change values).
8. Cross-workspace isolation holds for the daily-stats read (a worker's stats from another workspace never appear).
9. No regression to the already-shipped last-interacted-step / batch behavior or to existing analytics metrics (worked/paused/issues) — verified by existing tests.

## Contracts and skills

### Read order block (document-only protocol)

Read order (canonical first, local delta second where present):
- `../architecture/06_commands.md` → `../architecture/06_commands_local.md`
- `../architecture/07_queries.md` → `../architecture/07_queries_local.md`

Applied precedence: local overrides baseline for this app only.

### Contracts loaded

- Core: `01_architecture.md`, `04_context.md`, `05_errors.md`, `06_commands.md`(+local), `07_queries.md`(+local), `09_routers.md`, `21_naming_conventions.md`, `40_identity.md`, `41_user.md`, `42_event.md`, `48_presence.md`, `46_serialization.md`.
- `03_models.md`: adding a column to the aggregate-metrics mixin / analytics models.
- `30_migrations.md`: Alembic migration for the new column across 4 tables (trigger: schema change).
- `16_background_jobs.md` + `51_worker_runtime.md`: modifying the `PROCESS_STEP_TRANSITION` analytics worker (trigger: "worker").
- `49_observability_runtime.md`: logging/observability around the new worker increment.
- `52_replayability.md` + `53_operational_cli.md`: the idempotent backfill script (trigger: "backfill/reprocess/recover").
- `15_testing.md`: worker-increment, backfill idempotency, and endpoint tests.

### Excluded contracts

- `13_sockets.md`, `11_infra_events.md`: no new realtime surface (the read endpoint stays read-only; the worker already consumes the existing outbox event — no new event type).
- `08_domain.md`: no new domain aggregate.
- `18/34/55` etc.: no rate-limit/upload/search triggers.

### File read intent — pattern vs. relational

Relational reads already done (what exists): `user_daily_work_stats.py`, `aggregate_metrics.py`, `process_step_transition.py`, `_step_transition_core.py`, `step_transition.py` payload, `list_workers_last_interacted_step.py`. All legitimate (field names, worker write path, enqueue semantics). No pattern reads needed — migration shape from `30`, worker shape from `16/51`, serializer from `46`.

### Skill selection

- Primary: contract-goal-mapping guide (`task_system/backend_contract_goal_mapping_guide.md`).
- Trigger terms: `worker` (background job here — the analytics worker), `migration`, `backfill`, `serialization`, `query`.

## Implementation plan

### Phase 1 — Metric column (model + migration)

1. Add to `AggregateMetricsCountsMixin` (`app/beyo_manager/models/base/aggregate_metrics.py`):
   ```python
   total_completed_count: Mapped[int] = mapped_column(
       Integer, nullable=False, default=0, server_default="0"
   )
   ```
   This uniformly adds the column to all four consumers: `user_daily_work_stats`, `user_lifetime_stats`, `user_section_daily_work_stats`, `working_section_daily_work_stats` (consistent with how every other `*_count` is defined).
2. Alembic migration (per `30_migrations.md`): `add_column` `total_completed_count INTEGER NOT NULL DEFAULT 0` (`server_default="0"`) to the four tables above; downgrade drops it. `server_default` keeps the migration fast and NOT-NULL-safe on existing rows.

### Phase 2 — Worker increment (analytics)

3. In `process_step_transition.py`:
   - Thread a `completed_count: int = 0` kwarg through `_increment_user_daily`, `_increment_user_lifetime`, `_increment_user_section_daily`, `_increment_section_daily` (add `row.total_completed_count += completed_count`).
   - Add `_apply_step_completed(session, payload, worker_display_name, task_step)` that increments `completed_count=1` on user-daily (+ lifetime + user-section + section), bucketed on `work_date = datetime.fromisoformat(payload.exited_at).date()` (completion moment — distinct from the interval-start `work_date` used for time metrics).
   - Call it from the existing `if new_state == TaskStepStateEnum.COMPLETED:` branch, **alongside** `_apply_issues_at_completion`, and **outside** the `if not closing_record.recorded_time_marked_wrong` guard (completion is a fact regardless of time accuracy). User-scoped increments still gate on `payload.credited_user_id`.
   - Add a structured log line per completion increment (per `49_observability_runtime.md`).

### Phase 3 — Backfill (operational, idempotent)

4. One-time backfill script (per `53_operational_cli.md` / `52_replayability.md`), **not** embedded in the schema migration. Follow the repo's established convention: a `typer` CLI under `app/scripts/backfill/` (mirror `app/scripts/backfill/migrate_shopify_dimensions.py` and `cleanup_expired_uploads.py` — `typer.Typer(add_completion=False, no_args_is_help=True)`, `--dry-run` first with a summary, `--limit` for staged runs; reuse `beyo_manager.operations.backfill` / `beyo_manager.cli.main` wiring if applicable). New file e.g. `app/scripts/backfill/backfill_completed_count.py`.
   - Compute from source of truth: for terminal COMPLETED records, the `StepStateRecord` has `state == COMPLETED` and `entered_at` = completion time (its `exited_at` is null). Group by `(workspace_id, created_by_id, entered_at::date)` counting COMPLETED records → the true daily completed count.
   - **Set** (not increment) `user_daily_work_stats.total_completed_count` to the computed absolute value (upsert rows as needed) so the script is safely re-runnable and cannot double-count against the live worker. Do the same for lifetime (sum per user) and section-daily/section (join `StepStateRecord.step_id → TaskStep.working_section_id`) for consistency.
   - Guard: only touches `total_completed_count`; never rewrites time/issue columns. Default `--dry-run` prints per-scope row counts and a sample before any write.
   - Note in the runbook: until the backfill runs, only completions after deploy are counted; same-day-earlier completions read low.

### Phase 4 — Query service

5. In `list_workers_last_interacted_step`:
   - Resolve `work_date`: parse `ctx.query_params.get("work_date")` as an ISO date; on parse failure raise the standard validation error; default `datetime.now(timezone.utc).date()`.
   - After building the worker page, run **one** query:
     ```python
     select(
       UserDailyWorkStats.user_id,
       UserDailyWorkStats.total_working_seconds,
       UserDailyWorkStats.total_pause_seconds,
       UserDailyWorkStats.total_completed_count,
     ).where(
       UserDailyWorkStats.workspace_id == ctx.workspace_id,
       UserDailyWorkStats.user_id.in_(worker_ids),
       UserDailyWorkStats.work_date == work_date,
     )
     ```
     Build `stats_by_user`. Workers absent from the result → zeros.
   - Attach `daily_stats` (via serializer) to each worker entry.

### Phase 5 — Router param

6. In `worker_stats.py`, add `work_date: str | None = Query(None)` and pass it into `query_params` (only when provided).

### Phase 6 — Serializer

7. Add `serialize_user_daily_work_stats(work_date, total_working_seconds, total_pause_seconds, total_completed_count) -> dict` (new `domain/analytics/serializers.py` or existing analytics serializer module) returning the AC #1 shape with `work_date` as ISO string. Use it for both the found-row and zero-fill cases.

### Phase 7 — Handoff doc

8. Update `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`: the new `daily_stats` object, the `?work_date=YYYY-MM-DD` param (UTC-today default), the zero-fill semantics, and that stats are UTC-day-bucketed.

## Risks and mitigations

- Risk: **Shared-mixin migration touches 4 tables.** Adding to `AggregateMetricsCountsMixin` migrates `user_lifetime_stats` and the two section tables too.
  Mitigation: intentional — keeps the metric uniform and lets the worker increment all scopes as it already does for every counter. `server_default="0"` makes the DDL cheap and safe.
- Risk: **At-least-once double counting.** A retried `PROCESS_STEP_TRANSITION` task would increment `total_completed_count` twice.
  Mitigation: identical to existing `*_count` metrics — accepted system-wide behavior, not a new class of bug. The absolute-value backfill can correct drift if ever needed.
- Risk: **Backfill vs. live-increment overlap.** If the backfill runs after deploy, it must not double-count completions the worker already counted post-deploy.
  Mitigation: backfill **sets** the absolute value computed from `StepStateRecord` (source of truth), not increments — running it at any time converges to truth and is idempotent.
- Risk: **Completion-date vs interval-date skew.** Time metrics bucket on the interval-start date; completed_count buckets on completion date (`exited_at`). A step worked across midnight books time on one day and its completion on the next.
  Mitigation: this is correct for "completed today" and documented; the two metrics answer different questions.
- Risk: **`work_date` UTC vs a worker's local day.** No timezone data exists; the `work_date` param and default are UTC.
  Mitigation: documented in the handoff; the param lets the frontend pin a specific UTC day if needed.

## Validation plan

- Unit/integration: worker increments `total_completed_count` by 1 on COMPLETED (incl. when `recorded_time_marked_wrong` and when no issues); batch completion of N steps → +N; non-COMPLETED transitions → +0.
- Backfill idempotency: run twice on seeded COMPLETED history → identical values equal to a direct `StepStateRecord` count.
- Endpoint: worker with a stats row → correct worked/paused/completed; worker with no row → zeros; `?work_date=` past date → that day's row; invalid `work_date` → validation error (not 500); cross-workspace isolation; single daily-stats query for the page (assert no N+1).
- Regression: existing `get_user_last_active_step_record` and analytics worker tests stay green.
- `alembic upgrade head` then `downgrade -1` round-trips cleanly on a scratch DB.
- `ruff` / `mypy` clean.

## Review log

- `2026-07-15` requester: evolve endpoint to add worked time, paused time, completed-step count for the current date, sourced from the analytics stats tables.
- `2026-07-15` owner: discovered the analytics tables track no completed-step counter; surfaced the source fork.
- `2026-07-15` requester: extend the analytics pipeline for completed count; `work_date` optional param with UTC-today fallback.
- `2026-07-15` owner: encoded the schema/mixin change, worker increment on completion date, idempotent backfill, single-query daily read, and endpoint/serializer/handoff changes.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation completion

- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_daily_metrics_20260715.md`
- Frontend handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_stats_daily_metrics_20260715.md`
- Validation: focused suite passed (`9 passed`); migration applied to development and test databases.
