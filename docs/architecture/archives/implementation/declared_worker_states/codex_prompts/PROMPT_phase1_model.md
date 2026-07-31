# Codex prompt — Declared Worker States, Phase 1: model + migration

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Its cross-phase decisions D1–D10 are binding — do not contradict them.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase1_model_20260729.md`. Read it fully before touching code.
4. Prerequisite check: this is Phase 1 — no prerequisite. Confirm the master plan's phase table shows no phase already in progress.
5. Clarification-first: if you hit ambiguity the plan does not resolve, STOP and ask the operator. Do not invent requirements. All "Clarifications required" boxes in the plan are already resolved.
6. Respect the plan's "File read intent" section: load the listed architecture contracts for *how to write* code; only perform the listed relational reads for *what exists*.

## Hard constraints for this phase

- The table must be **inert** after this phase: no service, command, query, router, or worker may reference the new model (only `models/__init__.py` registration and tests).
- Do not modify `UserShiftStateRecord`, any command, or any router.
- The partial unique open-row index and the `exited_at >= entered_at` check MUST exist at the DB level and be proven by the integration tests listed in the plan.
- Verify the `uds` client-id prefix is unclaimed before using it.

## Definition of done

- Every acceptance criterion in the plan is verified with evidence (test run output, alembic output).
- Full validation plan executed and green; `ruff check` clean.
- Plan's Review log updated with an implementer entry; plan archived per the master plan's archiving note (preserve the `declared_worker_states/` subfolder under `archives/implementation/`); implemented summary written; master plan phase table updated (Phase 1 → archived/implemented).
