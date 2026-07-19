# SUMMARY_PLAN_worker_shift_state_recording_20260720

## Metadata

- Summary ID: `SUMMARY_PLAN_worker_shift_state_recording_20260720`
- Status: `summarized`
- Owner agent: `Codex`
- Completed at (UTC): `2026-07-20T00:00:30Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_worker_shift_state_recording_20260720.md`
- Frontend handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719.md`

## What was implemented

- Extended worker shift persistence with `IDLE`, free-text `reason`, and the `manually_recorded` origin flag. Added the scheduler and execution enum values for midnight auto-clock-out.
- Added an exhaustively tested pure state machine and a transport-agnostic reconcile service. Reconciliation locks the current worker shift, derives from current shift-scoped open step records, auto-clocks-in working users with the required prior-close clamp, preserves manual pause stickiness, and retries the first-open unique-index race once.
- Added worker self-service clock toggle, pause, and resume commands/routes. Managers and admins can clock a selected worker on behalf; direct double clock-in and invalid pause/resume transitions return conflicts.
- Clock-out delegates every open working step to the existing step-transition core targeting `ended_shift`, preserving its outbox behavior, while paused steps remain open. Shift boundary markers are always closed at creation.
- Added the daily safeguard task and registered it through the recurring scheduler and task worker. Because the repository had no established system-owned recurring-scheduler creation path, migration `b4074f2e26c4` seeds one fixed idempotent daily row (`origin_source = worker`, one-day interval); safeguard changes use `changed_by_id = NULL`.
- Hooked the analytics step-transition handler to reconcile the credited worker in the same session and transaction. Per-step batch fan-out converges idempotently to one shift transition.
- Hard-swapped both linear timeline reads to `UserShiftStateRecord`. Roster totals sum only recorded on-shift durations; drill-down segments are the recorded intervals with overlapping step details. Existing response keys and nested shapes remain intact; only zero-duration shift markers and `manually_recorded` were added.
- Added a dry-run-first, UTC historical backfill CLI. It reuses the unchanged `compute_linear_segments` sweep, delete-and-rewrites each selected worker-day, maps sweep states exactly as approved, stops at the first `ended_shift`, and writes reconstructed rows closed with no actor/manual origin.
- Added the frontend handoff addendum describing off-shift exclusion, recorded idle/pause semantics, free-text reason keys, markers, and live `is_open` behavior.

## Key files

- `backend/app/migrations/versions/759ed2d573c2_worker_shift_state_recording.py` and `b4074f2e26c4_seed_auto_clock_out_open_shifts_.py`: schema, enum, and scheduler seed migrations.
- `backend/app/beyo_manager/domain/users/shift_state_machine.py`: pure derivation and transition validity.
- `backend/app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py`: serialized reconcile seam.
- `backend/app/beyo_manager/services/commands/users/*worker_shift.py`: clock, pause, resume, access, and shared clock-out mechanics.
- `backend/app/beyo_manager/routers/api_v1/worker_shifts.py`: `/clock`, `/pause`, and `/resume` routes.
- `backend/app/beyo_manager/services/tasks/users/auto_clock_out_open_shifts.py`: midnight safeguard.
- `backend/app/beyo_manager/services/tasks/analytics/process_step_transition.py`: credited-worker reconcile hook.
- `backend/app/beyo_manager/services/queries/worker_stats/list_workers_linear_timeline.py` and `get_worker_linear_timeline_breakdown.py`: recorded-state roster and drill-down reads.
- `backend/app/scripts/backfill/backfill_worker_shift_state_records.py`: operational reconstruction CLI.

## Contract adherence

- Canonical architecture contracts were loaded before their `_local.md` companions; local rules took precedence for commands, router/service wiring, persistence, scheduler execution, and testing.
- The linear endpoint contract is additive-only. Contract tests pin all existing top-level, user, timeline, segment, and step-detail key sets; the public pause value remains `paused` even though persistence uses `in_pause`.
- `STARTED_SHIFT` and `ENDED_SHIFT` are written closed and returned only as zero-duration marker segments. The partial unique index therefore continues to mean that an open shift-state record exists exactly while a worker is on shift.
- `/totals`, `/{user_id}/daily-steps`, `UserDailyWorkStats`, and the pure analytics sweep were not behaviorally changed.
- The read side no longer derives shift time from step intervals, eliminating cross-day lunch, post-shift idle, and long ended-shift bleed. Step records remain the source only for `completed_count` and drill-down `steps[]` detail.

## Validation evidence

- Final worker-shift + worker-stats + analytics command: **149 passed**.
- Part E contract/backfill/pure-sweep verification: **39 passed** before the final combined run; focused backfill/read integration rerun: **9 passed**.
- Part C clock controls and safeguard: **13 passed**; Part D handler hook: **5 passed**; Part A/B focused state/reconcile verification: **42 passed**.
- Changed Python files across all five plan commits: `ruff check` **passed**.
- `alembic upgrade head`: **passed**; current head is `b4074f2e26c4`.
- Backfill CLI `--help`: **passed** with dry-run as the default.
- `git diff --check`: **passed** before each part commit.

## Known gaps or operational follow-up

- Run `scripts/backfill/backfill_worker_shift_state_records.py --execute` during rollout before historical linear-timeline reads are relied upon. The command intentionally refuses current/future UTC days and supports date/workspace/user scoping.
- Re-run the named 2026-07-16 and 2026-07-19 live roster checks after rollout/backfill; the equivalent three-week pause, post-shift idle, and long ended-shift cases are covered by the database contract suite.
- Night shifts spanning midnight remain the plan's accepted limitation: the safeguard splits them at 00:00 and the next working transition auto-clocks-in again.
- A repository-wide Ruff run still reports pre-existing unrelated lint debt (126 errors in legacy case/image models, old imports, and other untouched modules). Every Python file changed by this plan is clean.

## Commits

- Part A — `feat(shifts): implement part A state foundation (PLAN_worker_shift_state_recording_20260720)`.
- Part B — `feat(shifts): implement part B reconciliation (PLAN_worker_shift_state_recording_20260720)`.
- Part C — `feat(shifts): implement part C clock controls (PLAN_worker_shift_state_recording_20260720)`.
- Part D — `feat(shifts): implement part D worker hook (PLAN_worker_shift_state_recording_20260720)`.
- Part E — `feat(shifts): implement part E recorded timeline (PLAN_worker_shift_state_recording_20260720)`; lifecycle artifacts were folded into this part.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_shift_state_recording_20260720.md`
