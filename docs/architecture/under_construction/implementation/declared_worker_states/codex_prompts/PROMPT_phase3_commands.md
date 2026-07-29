# Codex prompt — Declared Worker States, Phase 3: declare/close commands + retirement of pause/resume

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decisions D2, D5, D7, D9, D10 are the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md`. Read it fully before touching code.
4. Prerequisite check: the master plan's phase table must show **Phases 1 and 2 archived** (the derived pipeline already reads declared rows). If not, STOP and report.
5. Clarification-first: if you hit ambiguity the plan does not resolve, STOP and ask the operator. Do not invent requirements.
6. Respect the plan's "File read intent" section — notably read `_step_transition_core.py` (relational) before reusing `_apply_step_transition` for the auto-pause.

## Hard constraints for this phase

- Declaring requires an open shift (`409` otherwise) and NEVER auto-clocks-in (D9). Declare/close accept optional `user_id` with the same on-behalf matrix as clock actions via `resolve_worker_shift_target` (D10 rev 2).
- Request/response shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` — the frontend is being built against it in parallel. Conflicts between plan and handoff → STOP and ask the operator.
- Declarable reasons: same workspace, not deleted, `pause_type = PERSONAL`, description enforced iff `requires_description` (D2).
- Auto-pause of open working steps uses the declared `pause_reason_id` and the existing `_apply_step_transition` machinery — no new transition path (D5).
- Both commands finish with a synchronous same-session `reconcile_worker_shift_state` call — the live state must be correct in the same transaction, not after the analytics worker catches up.
- Honor the Phase 2 lock order: shift row → declared row.
- Retirement is total: `/pause` + `/resume` routes, both commands, the reconcile's manual-pause carve-out, and their dedicated tests (converted, not deleted-without-replacement). NO data migration of legacy `manually_recorded` rows (D7).
- Write the full-loop integration test (plan acceptance 5) FIRST — it is the flagship proof of the feature.

## Definition of done

- Every acceptance criterion in the plan is verified with evidence (test output; `grep` proof for the retirement).
- Full validation plan executed and green; `ruff check` clean.
- Deploy note recorded in the implemented summary: a worker mid-manual-pause at deploy time will reconcile to `IDLE` (accepted, cosmetic; clock-out rebuild stays correct).
- Plan's Review log updated; plan archived per the master plan's archiving note (preserve subfolder); implemented summary written; master plan phase table updated.
