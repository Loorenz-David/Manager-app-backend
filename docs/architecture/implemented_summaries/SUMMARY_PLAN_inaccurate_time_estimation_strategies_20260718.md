# SUMMARY_PLAN_inaccurate_time_estimation_strategies_20260718

## Metadata

- Summary ID: `SUMMARY_PLAN_inaccurate_time_estimation_strategies_20260718`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Source plan: `docs/architecture/archives/implementation/PLAN_inaccurate_time_estimation_strategies_20260718.md`

## What was implemented

- Added a reusable trusted/flagged-only concurrency sweep. A `TaskStep` inaccuracy flag is OR’d into every time-bearing record, so a flagged step contributes zero trusted time and its whole averaged duration to wasted time.
- Added inaccurate working/paused/ended-shift seconds and distinct inaccurate-step counts to all four analytics aggregate tables, plus inaccurate seconds on `TaskStep`.
- Extended reconciliation, the analytics worker recompute, and the dry-run-first backfill to rebuild trusted and inaccurate facts idempotently; inaccurate time is excluded from costing.
- Added pure `mean`, `median`, Tukey IQR-trimmed mean, strategy resolution, and fill functions, plus a worker × section × state trusted per-step sample loader with 28-day lookback and four-sample fallback.
- Extended `/worker-stats/totals` and `/{user_id}/daily-steps` with additive trusted/wasted/estimated components, `time_strategy`, per-step inaccurate records, strategy comparison, usable totals, and `only_inaccurate` filtering.
- Added the schema migration and partial flagged-record index.

## Files changed

- `app/beyo_manager/domain/analytics/concurrency.py`: extracted the pure sweep and added flagged-only wasted projection.
- `app/beyo_manager/domain/analytics/estimation/`: added pure estimation strategies.
- `app/beyo_manager/services/queries/analytics/averaged_time.py`: propagated step flags and returned trusted/wasted contributions.
- `app/beyo_manager/services/queries/analytics/reconcile_user_time.py`: SET/delta projection for inaccurate facts and step counts.
- `app/beyo_manager/services/tasks/analytics/process_step_transition.py`: recomputed TaskStep trusted/inaccurate totals.
- `app/beyo_manager/models/base/aggregate_metrics.py` and analytics/task-step models: added persisted facts.
- `app/beyo_manager/services/queries/analytics/estimation_sample.py`: added read-time trusted sample loading.
- `app/beyo_manager/services/queries/worker_stats/list_workers_totals.py`: added range quality components and strategies.
- `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`: added inaccurate-step drill-down and usable totals.
- `app/beyo_manager/routers/api_v1/worker_stats.py`: added query parameters.
- `app/scripts/backfill/backfill_averaged_time.py`: rebuilt inaccurate facts alongside trusted aggregates.
- `app/migrations/versions/74f152a8b9d1_add_inaccurate_time_metrics.py`: added columns and partial index; reversible.
- `app/tests/unit/domain/analytics/test_estimation.py`, `test_concurrency.py`, and `test_estimation_sample.py`: pure strategy/sweep/sample coverage.
- `app/tests/integration/services/queries/analytics/test_reconcile_user_time.py`: flagged-step whole-time, trusted-zero, idempotent projection coverage.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_inaccurate_time_estimation_20260718.md`: frontend range-shape and summation contract.

## Contract adherence

- Domain estimation and sweep logic remain pure and have no ORM or I/O dependencies.
- Query services own database reads and return serialized dictionaries consistent with the existing local query convention; routers only validate parameters and dispatch services.
- Reconciliation and backfill use deterministic absolute SETs with Σ-table deltas/rebuilds, preserving replay/idempotency behavior.
- Workspace filters and inclusive UTC range bucketing are retained.
- The plan lifecycle is trace-linked through this summary, the archive record, the frontend handoff, and the archived source plan.

## Validation evidence

- `PYTHONPATH=. ./.venv/bin/pytest -q tests/unit/domain/analytics/test_concurrency.py tests/unit/domain/analytics/test_estimation.py tests/unit/services/queries/analytics/test_estimation_sample.py tests/unit/services/queries/worker_stats/test_endpoint_split.py tests/integration/services/queries/analytics/test_reconcile_user_time.py tests/integration/services/queries/worker_stats/test_worker_stats_endpoint_split_integration.py tests/integration/services/queries/worker_stats/test_get_worker_daily_step_breakdown.py`: **31 passed**.
- `ruff check` on all touched implementation, migration, and focused test files: **passed**.
- `alembic current` / `alembic heads`: **single head `74f152a8b9d1`**.
- `alembic downgrade -1 && alembic upgrade head`: **passed**.
- App, worker analytics, worker-stats query, and backfill imports: **passed**.
- `python scripts/backfill/backfill_averaged_time.py --dry-run`: **passed** (`users=3`, `steps=74`, no writes).

## Known gaps or deferred items

- The backfill is implemented and remains dry-run-first; run `python scripts/backfill/backfill_averaged_time.py --execute` with the analytics queue drained in the target environment.
- Standalone `mark_step_time_inaccurate` reconcile wiring remains intentionally deferred per the plan; the step flag is reflected immediately by read-time reconstruction and corrected by backfill/reconcile paths.

## Handoff notes

- To frontend: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_inaccurate_time_estimation_20260718.md`
- Prior range contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_inaccurate_time_estimation_strategies_20260718.md`
