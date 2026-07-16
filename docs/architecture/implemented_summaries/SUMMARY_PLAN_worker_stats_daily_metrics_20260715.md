# SUMMARY_PLAN_worker_stats_daily_metrics_20260715

## Metadata

- Summary ID: `SUMMARY_PLAN_worker_stats_daily_metrics_20260715`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-15T14:56:02Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_daily_metrics_20260715.md`
- Predecessor plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_last_interacted_steps_20260715.md`
- Related debug plan: `—`

## What was implemented

- Added `total_completed_count` to the shared aggregate metrics counts model and migrated all five current consumers, including `TaskStep`.
- Updated the analytics transition worker to increment completion counts on the UTC completion date, regardless of inaccurate-time marking or issues.
- Added structured completion-increment logging.
- Added an idempotent dry-run-first backfill CLI that derives absolute counts from non-deleted `COMPLETED` `StepStateRecord` history and updates user daily, lifetime, user-section daily, section daily, and task-step scopes.
- Extended the worker-stats query with one page-wide daily-stats query, UTC date resolution, validation errors for invalid dates, and zero-fill behavior.
- Added `daily_stats` to every worker entry and exposed optional `work_date` on the existing route.
- Updated the frontend handoff with live daily metrics and UTC-day semantics.

## Files changed

- `backend/app/beyo_manager/models/base/aggregate_metrics.py`: added `total_completed_count`.
- `backend/app/migrations/versions/c9d382a037e5_add_completed_count_to_analytics.py`: added the non-null defaulted column.
- `backend/app/beyo_manager/services/tasks/analytics/process_step_transition.py`: completion metric increments.
- `backend/app/scripts/backfill/backfill_completed_count.py`: dry-run-first absolute backfill.
- `backend/app/beyo_manager/domain/analytics/serializers.py`: daily stats serializer.
- `backend/app/beyo_manager/services/queries/worker_stats/list_workers_last_interacted_step.py`: daily stats read/date handling.
- `backend/app/beyo_manager/routers/api_v1/worker_stats.py`: `work_date` query parameter.
- `backend/app/tests/unit/services/tasks/analytics/test_process_step_transition.py`: completion increment coverage.
- `backend/app/tests/unit/services/queries/worker_stats/test_daily_metrics.py`: serializer/date validation coverage.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`: updated contract.

## Validation evidence

- Focused regression, analytics, and daily-metrics tests: `9 passed`.
- Development and test databases upgraded successfully to `c9d382a037e5`.
- Backfill CLI dry-run with `--limit 10`: passed with no writes.
- Router registration/import check: passed.
- Compileall: passed.
- Focused Ruff checks: passed.
- `alembic check` still reports a pre-existing unrelated `email_sync_states.connection_id` unique-constraint drift; it was intentionally excluded from this migration.

## Post-review fixes (2026-07-15)

Applied after an implementation review of this plan:

1. **Credited attribution** — completions are credited to `credited_user_id` (the same key the live worker uses), not the performer. Added a nullable `credited_user_id` column to `step_state_records` (migration `e4a7c9d2b18f`), populated it in the transition core, and the backfill now attributes by `credited_user_id` falling back to `created_by_id` for pre-column rows.
2. **Backfill scalability** — the backfill streams the source scan and writes set-based (bulk zero + touch only rows with completions) instead of loading five whole tables into memory.
3. **Backfill/live race** — documented in the script: run with the analytics queue drained/paused, since it writes absolute values and a completion processed mid-run would be overwritten.
4. **Backfill tests** — added `test_backfill_completed_count.py` (credited-user attribution + idempotency).
5. **Section-name snapshot** — newly-created section rows in the backfill now use the real `working_section_name_snapshot` instead of `""`.

Additional files: `backend/app/migrations/versions/e4a7c9d2b18f_add_credited_user_id_to_step_state_records.py`, `backend/app/beyo_manager/models/tables/tasks/step_state_record.py`, `backend/app/beyo_manager/services/commands/task_steps/_step_transition_core.py`, `backend/app/tests/integration/scripts/backfill/test_backfill_completed_count.py`.

## Known gaps or deferred items

- A full production-scale backfill should be run operationally with `--execute` (queue drained); dry-run is the safe default.
- `credited_user_id` on `step_state_records` is an approximate-analytics reference with no DB-level FK (keeps the add-column migration lock-free on a high-volume table); integrity is enforced in the write path.
- The repository's unrelated email constraint drift remains outside this plan.

## Trace links

- Frontend handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_stats_daily_metrics_20260715.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
