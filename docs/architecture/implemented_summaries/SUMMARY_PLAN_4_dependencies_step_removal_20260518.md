# SUMMARY: Plan 4 — Task Step Dependencies & Removal

## Plan ID
`PLAN_dependencies_step_removal_20260518`

## Status
✅ **COMPLETE** — All acceptance criteria met, all tests passing (10/10)

## Lifecycle State
`ARCHIVED` — Moved to `backend/docs/architecture/archives/implementation/`

---

## Implementation Overview

Plan 4 implemented the step dependency system (CMD-14, CMD-15) and step removal (CMD-10). It introduced the foundational `_recalculate_readiness` shared helper that is reused by all subsequent commands, particularly the state machine in Plan 5.

### Files Created/Modified

| File | Purpose |
|---|---|
| `beyo_manager/services/commands/task_steps/_readiness.py` | **NEW** — Shared helper `_recalculate_readiness()` |
| `beyo_manager/services/commands/task_steps/requests/__init__.py` | Appended: Request models for CMD-10, CMD-14, CMD-15 |
| `beyo_manager/services/commands/task_steps/add_step_dependency.py` | **NEW** — CMD-14: Add dependency edge |
| `beyo_manager/services/commands/task_steps/remove_step_dependency.py` | **NEW** — CMD-15: Remove dependency edge |
| `beyo_manager/services/commands/task_steps/remove_task_step.py` | **NEW** — CMD-10: Remove step from task |
| `beyo_manager/routers/api_v1/tasks.py` | Added routes for CMD-10, CMD-14, CMD-15 |

### Key Features Implemented

1. **Shared Helper: `_recalculate_readiness(step)`**
   - Stateless computation based on step counters:
     - `total_dependencies` (count of active prerequisite edges)
     - `completed_dependencies` (count of completed prerequisites)
   - Sets `step.readiness_status` to:
     - `READY`: if all dependencies completed or no dependencies exist
     - `BLOCKED`: if has dependencies but none completed
     - `PARTIAL`: if some but not all dependencies completed
   - Used by CMD-14, CMD-15, CMD-10, and CMD-12 (Plan 5)
   - Critical for dependency-aware step scheduling

2. **CMD-14: Add Step Dependency**
   - `POST /api/v1/tasks/{task_id}/steps/{step_id}/dependencies`
   - Request body: `{prerequisite_step_id}`
   - Creates `TaskStepDependency` edge: `step_id` depends on `prerequisite_step_id`
   - Increments dependent step's `total_dependencies` counter
   - Calls `_recalculate_readiness(step)` to update readiness status
   - Returns: `{dependency_id}`
   - Guards:
     - No self-loops (step cannot depend on itself)
     - No duplicate active edges
     - Both steps must belong to same task
   - Raises: `ValidationError` (self-loop, wrong task), `ConflictError` (duplicate)

3. **CMD-15: Remove Step Dependency**
   - `DELETE /api/v1/tasks/{task_id}/steps/{step_id}/dependencies/{dependency_id}`
   - Sets `removed_at = now()` on the edge (soft-delete)
   - Decrements dependent step's `total_dependencies` counter
   - Defensive decrement guard: if `total_dependencies` would go below `completed_dependencies`, also decrements `completed_dependencies` to match
   - Calls `_recalculate_readiness(step)` to update status
   - Returns: `{dependency_id}`

4. **CMD-10: Remove Task Step**
   - `DELETE /api/v1/tasks/{task_id}/steps/{step_id}`
   - Sets `step.state = SKIPPED` (terminal state)
   - Closes the current open `StepStateRecord` (`exited_at = now()`)
   - Soft-deletes step: `is_deleted = true, closed_at = now()`
   - Soft-removes all dependency edges (both as dependent and prerequisite):
     - Sets `removed_at` on each edge
   - For each step that depended on this step:
     - Decrements `total_dependencies`
     - Calls `_recalculate_readiness(dependent_step)` to update status
   - Task state side effects:
     - If all remaining non-deleted steps are terminal → `task.state = READY`
     - If this was the LAST non-deleted step → `task.state = PENDING` (unassigned)
   - Returns: `{step_id}`

### Test Results
- **10/10 tests PASSED** ✓
  - Add dependency edge (valid pair)
  - Remove dependency edge (soft-delete)
  - Readiness recalculation (READY, BLOCKED, PARTIAL)
  - Remove step (close state record, soft-delete, clean up edges)
  - Task state transitions (to READY when all terminal, to PENDING when last removed)
  - Guards: No self-loops
  - Guards: No duplicate edges
  - Guards: Same-task constraint
  - Edge cases: Removing prerequisite updates dependents
  - Workspace isolation

### Dependencies
- **Plan 3**: Steps must exist before dependencies can be added
- **Plan 5**: CMD-12 (state machine) imports and uses `_recalculate_readiness`

### Blockers Resolved
None — no blockers encountered during implementation.

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|---|---|---|
| `_recalculate_readiness()` stateless computation | ✅ | Takes step, reads counters, sets status without DB query |
| READY when no dependencies | ✅ | Test: 0 total → READY |
| READY when all completed | ✅ | Test: total == completed → READY |
| BLOCKED when has deps but none completed | ✅ | Test: total > 0, completed == 0 → BLOCKED |
| PARTIAL when some completed | ✅ | Test: 0 < completed < total → PARTIAL |
| Add dependency increments counter | ✅ | Test: total_dependencies increases |
| Remove dependency decrements counter | ✅ | Test: total_dependencies decreases |
| Self-loop validation | ✅ | Test: step depends on self → ValidationError |
| Duplicate edge guard | ✅ | Test: adding same edge twice → ConflictError |
| Same-task constraint | ✅ | Test: cross-task edge → ValidationError |
| Remove step sets SKIPPED state | ✅ | Test: step.state == SKIPPED after removal |
| Close state record on removal | ✅ | Test: StepStateRecord.exited_at set |
| Soft-delete step (`is_deleted=true`) | ✅ | Test: step marked as deleted |
| Clean up edges (both directions) | ✅ | Test: all edges pointing to removed step marked removed_at |
| Recalculate dependents after removal | ✅ | Test: dependent steps' readiness recalculated |
| Task → READY when all steps terminal | ✅ | Test: removing last non-terminal step → task READY |
| Task → PENDING when last step removed | ✅ | Test: removing only non-deleted step → task PENDING |
| Defensive decrement guard | ✅ | Test: completed_dependencies capped at total_dependencies |

---

## Domain Architecture Alignment

✅ **Contract Compliance:**
- Shared helper pattern correct (stateless, reusable)
- Command structure matches `backend/architecture/06_commands.md`
- Error handling uses typed domain errors
- Transactional safety enforced

✅ **Multi-Tenant Isolation:**
- All queries include `workspace_id` filter
- Foreign keys respect workspace boundaries
- Cross-workspace access prevented

---

## Quality Gate Results

- ✅ Contract adherence: Business logic in commands
- ✅ Architecture boundaries: Shared helper correctly placed
- ✅ Validation: 10/10 tests pass
- ✅ Reusability: Helper will be imported by Plans 5+ without modification
- ✅ State consistency: Counters maintained accurately

---

## Integration Notes

Plan 4 establishes the shared helper pattern used by:
- Plan 5: CMD-12 imports `_recalculate_readiness` for state transitions
- Plan 6: Analytics indirectly affects step states via Plan 5

---

## Metadata

- Implemented by: Copilot (GitHub Copilot)
- Implementation date: 2026-05-18
- Test suite: `backend/tests/tasks/test_dependencies_removal.sh` (10/10 ✓)
- Linked intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`
