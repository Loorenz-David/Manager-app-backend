# ARCHIVE_RECORD_PLAN_inaccurate_time_estimation_strategies_20260718

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_inaccurate_time_estimation_strategies_20260718`
- Archived at (UTC): `2026-07-18T00:00:00Z`
- Archive owner agent: `codex`

## Source references

- Plan: `docs/architecture/archives/implementation/PLAN_inaccurate_time_estimation_strategies_20260718.md`
- Summary: `docs/architecture/implemented_summaries/SUMMARY_PLAN_inaccurate_time_estimation_strategies_20260718.md`
- Frontend handoff: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_inaccurate_time_estimation_20260718.md`
- Debug chain: `—`

## Outcome classification

- Result: `completed_with_operational_followup`
- Acceptance criteria met: `yes` for code, tests, and migration; production backfill execution remains an operator step.

## Final notes

- Inaccuracy is step-grained. Trusted totals for unflagged steps remain unchanged; flagged steps move wholly to wasted facts.
- Mean is the default, aggregate-only strategy. Median and IQR are opt-in and use the bounded trusted per-step sample path.
- The frontend owns the final choice/sum: trusted-only, wasted-only, or trusted + selected estimated fill.
- Migration `74f152a8b9d1` is reversible and leaves a single Alembic head.
- Run the dry-run-first backfill with the analytics queue drained before executing historical correction in a target environment.
