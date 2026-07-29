# Codex prompt — Declared Worker States, Phase 6: kiosk worker flow (clock code + roster exposure)

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decisions D12–D14 are the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase6_kiosk_flow_20260729.md`. Read it fully before touching code.
4. Prerequisite check: the master plan's phase table must show **Phases 3, 4 AND 5 archived**. If not, STOP and report.
5. Clarification-first: ambiguity the plan does not resolve → STOP and ask. Do not invent requirements.
6. Respect the plan's "File read intent". Two verify-first items: (a) locate the established work-profile write path before extending it with `clock_in_code`; (b) check whether `email` is already present in the list_users serialized shapes.

## Hard constraints for this phase

- NO identify endpoint — matching is client-side (D13 rev 3). The backend change is: `GET /users` items gain `clock_in_code` (+ `email` if not already present) **only when the session's `app_scope == "floor"`**. For every other scope the response must be BYTE-IDENTICAL to today (fields absent, not null) — existing list_users tests must pass unmodified.
- Code fetch for the page is ONE batched query (no N+1).
- `clock_in_code` uniqueness is per-workspace via partial unique index; friendly `409` at the command layer.
- Clock-out `analytics: null` must appear on BOTH `/clock-out` and the `/clock` toggle's clock-out branch; all other response keys unchanged.
- All shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` field-for-field. Conflicts → STOP and ask.
- Write the full-loop kiosk test FIRST (plan acceptance 6): floor sign-in → roster with codes → GET /current → clock-in → declare → clock-out.

## Definition of done

- Every acceptance criterion verified with evidence.
- Full validation plan green; `ruff check` clean.
- Handoff status line marks Phase 6's rows live.
- Plan's Review log updated; plan archived (preserve subfolder); implemented summary written; master plan phase table updated. (Phase 7 remains — do NOT archive the master plan or the folder.)
