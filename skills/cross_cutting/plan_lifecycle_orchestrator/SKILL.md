# Plan Lifecycle Orchestrator

## Intent

Manage the full backend plan workflow across drafting, review, implementation,
summary, archive, and debugging loops.

## Trigger conditions

- User asks to start or manage a plan through full lifecycle.
- Multi-agent handoff is expected between planning and implementation.
- Work requires documentation traceability and state transitions.
- User asks to archive or clean up implemented plans (move plans from `under_construction/implementation/` to `archives/implementation/`).

## Required inputs

- Goal statement and scope
- Acceptance criteria
- Domain and constraints
- Handoff needs (`to_frontend`, `from_frontend`, or none)

## Contracts to load

- `backend/skills/_shared/plan_lifecycle_contract.md`: lifecycle states and transitions (both plan types)
- `backend/architecture/23_documentation.md`: documentation discipline
- `backend/architecture/29_feature_workflow.md`: feature workflow alignment
- `backend/task_system/backend_contract_goal_mapping_guide.md`: baseline contract routing

## Related skills

- `backend/skills/cross_cutting/intention_planning/SKILL.md`: use when creating or updating intention plans

## Execution protocol

1. Determine plan type before creating:
   - Goal/outcome driven → use intention plan first (`intention_planning` skill).
   - Task/implementation driven → use implementation plan directly.
2. Create or update plan in the correct subfolder:
   - Intention: `backend/docs/architecture/under_construction/intention/`
   - Implementation: `backend/docs/architecture/under_construction/implementation/`
3. Link implementation plan back to its intention plan in the metadata field.
4. Run clarification-first checks to avoid requirement invention.
5. Review and correct plan until approved.
6. Execute implementation (current or delegated agent).
7. Write summary in `backend/docs/architecture/implemented_summaries/`.
8. Create archive record in `backend/docs/architecture/archives/`.
9. Move the implementation plan file from `under_construction/implementation/` to `archives/implementation/`:
   - The plan file is the **single source of truth** — once implementation is complete and the summary is written, the plan must live in `archives/implementation/`, not in `under_construction/implementation/`.
   - Update the plan's `Status` field from `under_construction` or `approved` to `archived` and update `Last updated at` before moving.
   - Execute the move with:
     ```
     mv backend/docs/architecture/under_construction/implementation/PLAN_<slug>_<YYYYMMDD>.md \
        backend/docs/architecture/archives/implementation/PLAN_<slug>_<YYYYMMDD>.md
     ```
   - Verify the file is gone from `under_construction/implementation/` after the move:
     ```
     ls backend/docs/architecture/under_construction/implementation/
     ```
   - `README.md` and `TEMPLATE_PLAN.md` must never be moved — they are permanent residents of `under_construction/implementation/`.
   - Plans with status `under_construction` or `approved` (not yet implemented) must NOT be moved.
10. Update the intention plan's "Linked implementation plans" table and progress notes.
11. If defects appear, create nested debug plan in `backend/docs/debugging/`.
12. Repeat review -> implement -> summary -> archive for debug iteration.

## Cleanup protocol (standalone)

Use this when invoked specifically to clean up stale plan files — plans that have been implemented and summarised but whose file is still sitting in `under_construction/implementation/`:

1. List all files in `backend/docs/architecture/under_construction/implementation/` (excluding `README.md` and `TEMPLATE_PLAN.md`).
2. For each plan file found, read its `Status` field:
   - `archived` → the file is stale; it must be moved to `archives/implementation/` (or deleted if a copy already exists there that is identical or newer).
   - `under_construction` or `approved` → leave it in place; it is not ready to move.
3. For each stale file:
   a. If a copy already exists in `archives/implementation/`: compare `Last updated at` timestamps. Keep the newer version in `archives/implementation/`; delete the stale copy from `under_construction/implementation/`.
   b. If no copy exists in `archives/implementation/`: move the file using `mv`.
4. Confirm `under_construction/implementation/` contains only `README.md`, `TEMPLATE_PLAN.md`, and active (non-archived) plans.

## Handoff protocol

- Backend to frontend handoff artifacts go in `backend/docs/handoff/to_frontend/`.
- Frontend to backend incoming artifacts are tracked in `backend/docs/handoff/from_frontend/`.
- All handoff files must reference the originating plan or debug plan.

## Output format

Follow `backend/skills/_shared/output_format.md` and include:

- Current lifecycle state
- Next required transition
- Document paths updated or to be created

## Done criteria

- Lifecycle state is explicit and valid.
- Plan, summary, and archive are trace-linked.
- Debug loops include nested parent references.

## Quality gate

Apply `backend/skills/_shared/quality_gate.md`.
