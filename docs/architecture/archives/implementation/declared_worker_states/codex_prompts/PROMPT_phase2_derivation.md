# Codex prompt — Declared Worker States, Phase 2: derivation integration

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decisions D3–D6 are the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`. Read it fully before touching code.
4. Prerequisite check: the master plan's phase table must show **Phase 1 archived** (the `user_declared_state_records` table exists at Alembic head). If not, STOP and report.
5. Clarification-first: if you hit ambiguity the plan does not resolve, STOP and ask the operator. Do not invent requirements.
6. Respect the plan's "File read intent" section. One verification is mandatory before relying on it: read `domain/analytics/linear_timeline.py::_sweep` to confirm overlapping working/paused priority, and record the finding in the plan's Review log.

## Hard constraints for this phase

- **Deploy-neutral**: with zero declared rows, every existing test suite must pass unchanged. The only new write is the clock-out clamp of an open declared row (which cannot fire while the table is empty).
- Do NOT remove the legacy manual-pause stickiness carve-out or touch `/pause`/`/resume` — that is Phase 3.
- Establish and document (code comment) the lock order: shift row → declared row. Phase 3 depends on it.
- The reconcile stays a subordinate command: no events, no commits of its own.
- `derive_target_state` stays pure (no I/O); update every call site in the same change.

## Definition of done

- Every acceptance criterion in the plan is verified with evidence (test output).
- Full validation plan executed and green, including the unchanged legacy suites; `ruff check` clean.
- Plan's Review log updated (including the `_sweep` priority finding); plan archived per the master plan's archiving note (preserve subfolder); implemented summary written; master plan phase table updated.
