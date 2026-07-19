# SUMMARY_PLAN_batch_concurrency_averaged_time_20260718

## Metadata

- Summary ID: `SUMMARY_PLAN_batch_concurrency_averaged_time_20260718`
- Status: `summarized`
- Owner agent: `claude-opus-4-8` (direct implementation)
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_concurrency_averaged_time_20260718.md`

## What was implemented

Batch-worked time is now **concurrency-averaged**: each moment of real time is divided by the number of the worker's concurrently-open **batchable** steps in that state, so a batch of N steps splits the real time and the steps sum back to the real wall-clock. Non-batch steps always keep full time. All aggregates are a **deterministic, idempotent projection** of `step_state_records` (no stored batch id — concurrency is derived from record overlap).

- **Pure sweep** — `domain/analytics/concurrency.py` (`TimeInterval`, `averaged_seconds_by_record`): per-state sweep-line, only batchable intervals divide, open records count toward `k`, `marked_wrong` excluded, deterministic. The single source of truth.
- **Reconstruct primitive** — `services/queries/analytics/averaged_time.py` (`compute_record_contributions`): fetch a worker's records (joined to `TaskStep` for `allows_batch_working`) over a window, run the sweep, return per-record averaged seconds + metadata.
- **Reconcile primitive** — `services/queries/analytics/reconcile_user_time.py`: recompute-and-**SET** `user_daily` + `user_section_daily` time fields (seconds/counts/cost) from records; return deltas applied to the Σ tables (`user_lifetime`, `working_section_daily`).
- **Analytics worker** — `process_step_transition.py`: on a time-bearing close, reconcile-and-SET the credited worker's day (+ delta to Σ tables) and recompute the step's `TaskStep.total_*` (averaged, async). Old full-interval booking (`_apply_working/paused/ended_shift_close`, `_compute_interval_seconds`, `_compute_cost_minor`) removed.
- **Synchronous step increments retired** — `increment_step_time_metrics` calls removed from `transition_step_state.py` and `_step_transition_core.py` (main + auto-pause paths); `TaskStep.total_*` is now worker-maintained (eventually-consistent).
- **Breakdown endpoint** — per-step `contribution` and `totals` now averaged (via the sweep); sorts by averaged seconds.
- **`running` sidecar** — open intervals averaged (`build_running_totals_averaged`); worker-level advances at real time, per-step at `1/k`.
- **Index** — migration `a7f3c1e9d240`: functional index `(workspace_id, COALESCE(credited_user_id, created_by_id), entered_at)` on `step_state_records`.
- **Backfill** — `app/scripts/backfill/backfill_averaged_time.py` (typer, dry-run-first): rebuild all four analytics tables + `TaskStep.total_*` from records; idempotent absolute SET.

## Resolved decisions

- Working, paused, and ended-shift all averaged; completion counts untouched.
- **Only batchable steps divide**; non-batch steps always full time (excluded from `k`).
- `TaskStep.total_*` computed **async** in the worker.
- Live maintenance = **recompute-and-SET** the worker's day (idempotent); lifetime/section-wide by delta.
- **Rebuild all** historical aggregates via the backfill.

## Files changed

- `backend/app/beyo_manager/domain/analytics/concurrency.py` (new)
- `backend/app/beyo_manager/domain/analytics/serializers.py` (`build_running_totals_averaged`)
- `backend/app/beyo_manager/services/queries/analytics/averaged_time.py` (new)
- `backend/app/beyo_manager/services/queries/analytics/reconcile_user_time.py` (new)
- `backend/app/beyo_manager/services/tasks/analytics/process_step_transition.py` (reworked)
- `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`, `_step_transition_core.py` (retired sync increments)
- `backend/app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`, `list_workers_last_interacted_step.py` (averaged)
- `backend/app/migrations/versions/a7f3c1e9d240_index_step_records_credited_user_entered.py` (new)
- `backend/app/scripts/backfill/backfill_averaged_time.py` (new)
- Tests: `tests/unit/domain/analytics/test_concurrency.py`, `tests/integration/services/queries/analytics/test_reconcile_user_time.py`

## Validation evidence

- **35 tests pass** (sweep unit: 11; reconcile/step-averaging integration incl. batch-of-5 → real time, idempotency, non-batch full, step totals; breakdown/running/insights suites; analytics worker unit).
- Ruff clean on all new/touched files; single alembic head (`a7f3c1e9d240`); app + worker + backfill import cleanly; both worker-stats routes register.
- Pre-existing unrelated lint (F401/F821) in the two transition-command files was left untouched (present at HEAD).

## Known gaps or deferred items

- **`running` FE contract shifted** — tick math changes from `open_count × elapsed` to real-time (worker-level) / `1/k` (per step). Handoffs updated; frontend must adjust.
- **Backfill not executed** here — run `python scripts/backfill/backfill_averaged_time.py backfill-averaged-time --execute` (queue drained) to correct historical data.
- **Migration not applied** here (DB not reachable from the sandbox) — run `alembic upgrade head`.
- **Cost precision**: step/day cost recomputed from averaged seconds; ±rounding.
- Full analytics-worker end-to-end (task-queue) not exercised in the sandbox; the reconcile/step primitives it calls are integration-tested directly.

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md` and `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md` updated with the averaging change.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_batch_concurrency_averaged_time_20260718.md`
