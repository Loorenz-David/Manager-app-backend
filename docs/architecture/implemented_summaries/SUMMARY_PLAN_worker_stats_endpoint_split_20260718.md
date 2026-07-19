# SUMMARY_PLAN_worker_stats_endpoint_split_20260718

## Metadata

- Summary ID: `SUMMARY_PLAN_worker_stats_endpoint_split_20260718`
- Status: `summarized`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_stats_endpoint_split_20260718.md`
- Completed at (UTC): `2026-07-18T17:08:25Z`

## What was implemented

The combined worker roster endpoint was split into three focused query services and routes:

- `GET /api/v1/worker-stats/last-interacted-steps` — `user`, `last_interacted_step`, and `batch`.
- `GET /api/v1/worker-stats/totals` — `user`, `daily_stats`, and `running`.
- `GET /api/v1/worker-stats/insights` — `user` and `insights`.

All three use the same active-worker roster, username ordering, offset pagination, role filter, and pagination envelope. The existing `GET /api/v1/worker-stats/{user_id}/daily-steps` route was not changed.

The totals and insights computations were extracted without changing their existing date, live-running, concurrency-averaging, or baseline behavior. The last-step service retains its point-in-time cohort and representative-step logic. Its established `work_date` validation remains accepted for compatibility, although the slim snapshot does not return date-scoped analytics.

## Files changed

- `backend/app/beyo_manager/services/queries/worker_stats/_roster.py` — shared worker page, role filter, constants, and date resolver.
- `backend/app/beyo_manager/services/queries/worker_stats/list_workers_last_interacted_step.py` — slimmed snapshot service.
- `backend/app/beyo_manager/services/queries/worker_stats/list_workers_totals.py` — extracted daily totals and live-running service.
- `backend/app/beyo_manager/services/queries/worker_stats/list_workers_insights.py` — extracted insights service.
- `backend/app/beyo_manager/routers/api_v1/worker_stats.py` — registered `/totals` and `/insights`.
- `backend/app/tests/unit/services/queries/worker_stats/test_daily_metrics.py` — moved date-resolver test import.
- `backend/app/tests/unit/services/queries/worker_stats/test_endpoint_split.py` — split response-shape and route-registration checks.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_endpoint_split_20260718.md` — implemented frontend contract.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md` — updated split contract reference.
- `backend/docs/architecture/under_construction/intention/worker_stats_modification.md` — added implementation progress links.

## Validation evidence

- Focused worker-stats unit tests: **5 passed**.
- Ruff on all new/touched split files: **passed**.
- Python compilation of new/touched Python modules: **passed**.
- Worker-stats route registration check: **passed** for all four routes.
- `git diff --check`: **passed**.
- Existing daily-step integration suite: attempted with PostgreSQL access, but both tests stopped during fixture setup because the test database schema is stale and lacks `workspace_roles.specialization`. No split assertion was reached.

## Follow-ups

- Apply the current database migrations to the test database, then rerun `app/tests/integration/services/queries/worker_stats/test_get_worker_daily_step_breakdown.py`.
- Frontend must migrate to three parallel calls and join worker sections by `user.client_id`.
- Date ranges remain deferred to `/totals` and `/{user_id}/daily-steps` as a coordinated follow-up.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_stats_endpoint_split_20260718.md`
