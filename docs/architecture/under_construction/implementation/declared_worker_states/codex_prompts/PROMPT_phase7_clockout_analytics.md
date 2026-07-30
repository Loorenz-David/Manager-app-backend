# Implementer prompt — Declared Worker States, Phase 7 (FINAL): clock-out analytics

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process this work as: implement → validate → review-log entry → STOP for independent review.
   Summary/archive happen ONLY after the reviewer approves.
2. Read the master plan: `.../declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
   (decision D14 and the "Repository validation baseline" section).
3. Your implementation plan: `.../declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md`
   — **read rev 2**, which rewrote this phase. The frontend requirement it answers is
   `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md`.
4. Prerequisite: master phase table shows Phases 2, 4 and 6 archived. If not, STOP and report.
5. Clarification-first: ambiguity the plan does not resolve → STOP and ask.
6. Two verify-first items before coding: (a) the image-link entity enum member and whether image links
   carry an ordering column — if not, define "first image" deterministically and record it; (b) which
   `TaskStep.total_*` fields constitute an item's `total_seconds` — record the definition and note it
   is task-level, not this worker's share.

## Hard constraints

- Shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`
  §5.1 field-for-field. The handoff is operator-owned — do NOT edit it, do NOT flip liveness rows.
  Conflicts → STOP and ask.
- **Do NOT extract a seam from `get_worker_linear_timeline_breakdown`, and do NOT ship `segments[]` or
  `insights`.** (Rev 1 planned that; rev 2 dropped it — the kiosk renders totals only, and the
  insights engine cannot express unit-based comparisons.) Reuse only the cheap shared helpers
  `load_recorded_shift_records` / `build_recorded_shift_timeline` / the pause-reason lookup from
  `list_workers_linear_timeline.py`, plus the `item_by_task` mapping from the breakdown module.
- `week` = ONE range query bucketed by day. Never seven queries. Never `UserDailyWorkStats` (no idle
  bucket, async lag).
- Batched loads only for item images, sections, issue counts and the rate baseline — no per-item,
  per-day or per-baseline-day round trips. The query budget is acceptance criterion 7, proven with a
  local query-count listener (the shared `count_queries` fixture is broken) and a mutation check.
- Composition runs AFTER the write transaction, in the route/service wiring;
  `clock_out_shift_for_user` must remain untouched so the midnight safeguard and Connecteam never
  compute analytics.
- Degradation is absolute: any exception → `analytics: null` **in full** (never partial), clock-out
  still `200` with the shift closed, structured error log. Prove it with a monkeypatched failure.
- Floor roster additions use Phase 6's exact conditional and merge point (floor only; **absent**, not
  `null`, for every other scope).
- The two carried Phase 6 items (R1-1 index-name pin + race test; duplicate-code `409` message) are
  deliverables, not optional.

## Definition of done

- Every acceptance criterion verified with evidence, including the query-count mutation proof, the
  actor/target split probe, and the real-ASGI roster probe.
- Quiet-tree full suite with **no new failure nodes** vs the recorded baseline (compare node sets, not
  counts — concurrent sessions have produced phantom 313/321-failure runs twice in this feature set);
  `ruff check` clean on touched files.
- Plan's Review log updated with your implementer entry, including both verify-first definitions and
  the measured composite latency for a realistic seeded day. Then STOP for independent review — no
  summary, no archive, no master-table flip, no handoff edit.
