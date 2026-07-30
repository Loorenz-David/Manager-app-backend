# Implementer prompt — Declared Worker States, Phase 8: kiosk analytics extras

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process this work as: implement → validate → review-log entry → STOP for independent review.
   Summary/archive happen ONLY after the reviewer approves (see Definition of done).
2. Read the master plan first: `.../declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
   (decisions D12–D14 and the "Repository validation baseline" section).
3. Your implementation plan: `.../declared_worker_states/PLAN_declared_worker_states_phase8_kiosk_analytics_extras_20260730.md`.
   Read it fully. The frontend requirement it answers is
   `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md` (items 3, 4, 6-partial, 7).
4. Prerequisite: the master phase table must show **Phase 7 archived** — the `analytics` composite must
   exist before you add keys to it. If not, STOP and report.
5. Clarification-first: ambiguity the plan does not resolve → STOP and ask.
6. Two verify-first items before coding: (a) the image-link entity enum member and whether image links
   have an ordering column (if not, define "first" deterministically and say so); (b) which
   `TaskStep.total_*` fields constitute an item's "time to complete" — propose the definition, record
   it in the Review log, and note it is task-level rather than this worker's share.

## Hard constraints

- Shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`
  §5.2 field-for-field. The handoff is operator-owned — do NOT edit it, and do NOT flip any liveness
  row. Conflicts → STOP and ask.
- **No new tables, no scheduling, no announcements, no badge numbers.** Scheduling was explicitly
  skipped by the operator; there is no `scheduled_seconds`.
- `week` comes from `UserShiftStateRecord` via the existing `build_recorded_shift_timeline` /
  `load_recorded_shift_records` helpers — **one range query bucketed by day**, never seven queries, and
  never `UserDailyWorkStats` (no idle bucket, async lag).
- `completed_items` reuses the existing task→item mapping from
  `get_worker_linear_timeline_breakdown` (`item_by_task`) — do not fork it. Batched loads only: no
  per-item query for images, sections, or issue counts.
- Both keys compose inside Phase 7's composite, after the write transaction, and inherit its
  degradation rule: any failure → `analytics: null` in full, never partial, never a failed clock-out.
- Floor roster additions use Phase 6's exact conditional and merge point (floor only; absent — not
  `null` — for every other scope).
- Query budget is an acceptance criterion, not a nicety: prove it with a local query-count listener
  (the shared `count_queries` fixture is broken — see the master baseline).

## Definition of done

- Every acceptance criterion verified with evidence, including the query-count proofs and the real-ASGI
  probe for the roster exposure (mirror the Phase 6 review's method).
- Quiet-tree full suite with **no new failure nodes** vs the recorded baseline (compare node sets, not
  counts — concurrent sessions have produced 313/321-failure phantoms twice in this feature set);
  `ruff check` clean on touched files.
- Plan's Review log updated with your implementer entry, including both verify-first definitions. Then
  STOP for independent review. Do NOT write the summary, archive the plan, flip the master table, or
  touch the handoff — those are operator steps after APPROVED.
