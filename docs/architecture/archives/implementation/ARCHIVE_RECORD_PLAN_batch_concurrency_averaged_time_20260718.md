# ARCHIVE_RECORD_PLAN_batch_concurrency_averaged_time_20260718

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_batch_concurrency_averaged_time_20260718`
- Archived at (UTC): `2026-07-18T11:39:42Z`
- Archive owner agent: `claude-opus-4-8`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_batch_concurrency_averaged_time_20260718.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_batch_concurrency_averaged_time_20260718.md`
- Debug chain: `—`

## Outcome classification

- Result: `completed_with_followups`
- Acceptance criteria met: `yes` (operational backfill + migration to be run in the target environment)

## Final notes

- Batch time is concurrency-averaged from record overlap; aggregates are a deterministic idempotent projection of `step_state_records` (no stored batch id). The pure sweep (`domain/analytics/concurrency.py`) is the single definition, shared by the worker, both worker-stats endpoints, and the backfill.
- Only batchable steps divide; non-batch always full time. Working/paused/ended-shift averaged; completion counts unchanged.
- Live path is recompute-and-SET the worker's day (idempotent), lifetime/section-wide by delta; the backfill re-derives the Σ tables by summation for a clean rebuild.
- **Followups to run in the target env**: `alembic upgrade head` (index `a7f3c1e9d240`); `scripts/backfill/backfill_averaged_time.py --execute` with the analytics queue drained.
- **Frontend**: `running` tick math changed (real-time worker-level, `1/k` per step) — both handoffs updated.
- 35 tests pass; ruff clean; single alembic head; app/worker/backfill import cleanly.

## Follow-up links

- Related handoffs:
  - `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`
  - `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md`
