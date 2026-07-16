# ARCHIVE_RECORD_PLAN_worker_daily_step_breakdown_20260716

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_worker_daily_step_breakdown_20260716`
- Archived at (UTC): `2026-07-16T04:29:26Z`
- Archive owner agent: `claude-opus-4-8`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_worker_daily_step_breakdown_20260716.md`
- Summary: `—` (implemented directly, not via Codex; no separate SUMMARY produced)
- Debug chain (optional):
  - `—`

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `yes`

## What was implemented

- New manager-only drill-down `GET /api/v1/worker-stats/{user_id}/daily-steps`: the per-task-step breakdown behind a worker's daily totals, for one UTC day.
- `services/queries/tasks/step_light_bundle.py` — shared batched entity loaders (steps/tasks/primary-items/upholstery/requirements/images), extracted from `list_working_section_steps` (which was left untouched) so both can compose their own item shapes.
- `services/queries/worker_stats/get_worker_daily_step_breakdown.py` — one settled aggregation over `StepStateRecord` + one open-record query, mirroring the analytics worker's rules; in-memory sort/paginate; batched light-bundle load for the page.
- `domain/analytics/serializers.py` — `serialize_step_contribution` and `serialize_user_daily_work_stats_full` (existing 3-field serializer left unchanged).
- Route added to `routers/api_v1/worker_stats.py` with `work_date`/`limit`/`offset`/`sort_by`/`order`.
- Integration tests in `tests/integration/services/queries/worker_stats/test_get_worker_daily_step_breakdown.py`.
- Frontend handoff (see below).

## Final notes

- **Reconciliation by construction**: settled `contribution`/`totals` use the same rules as the analytics worker (closed-record time, `recorded_time_marked_wrong` excluded from time, completions on the completion moment, `COALESCE(credited_user_id, created_by_id)` attribution, UTC `entered_at` range), so `totals` reconciles with the maintained `user_daily_work_stats`. `totals` can be < `daily_stats` when a contributing step was later deleted — surfaced as both fields, documented.
- **Running interval is display-only**: the currently-open time-bearing record is returned as per-step `active_record` (`state` + `entered_at`), kept out of settled `contribution`/`totals`; the frontend adds `now − entered_at` to the metric matching `active_record.state`.
- **Bug caught during implementation**: a terminal `COMPLETED` record is also `exited_at IS NULL`, so the `active_record` query is restricted to time-bearing states (`WORKING`/`PAUSED`/`ENDED_SHIFT`) — a finished step correctly returns `active_record: null`. Pinned by an integration test.
- **Sorting**: `sort_by ∈ {contribution (default, active-first composite), working, paused, completed, last_activity}` × `order ∈ {asc, desc}`. `completed` is a filter intention (only completed steps, ordered by completion time) while `totals` stay full-day. All sort keys are stable values (flags/settled numbers/fixed timestamps) — pagination is deterministic.
- **Efficiency**: constant query count regardless of step count (aggregation + open-records + membership + daily-stats + the batched bundle); no N+1 by construction.
- **Deferred**: no `count_queries` no-N+1 assertion test was added (guaranteed by the batched loader); adopting the shared loaders in `list_working_section_steps` remains an optional follow-up.
- Verified against real PostgreSQL: 16 related tests pass, ruff clean, both routes register; smoke-tested empty case (zeros/`[]`) and `404` for a non-member.

## Follow-up links

- Next plan (optional): `—`
- Related handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`
