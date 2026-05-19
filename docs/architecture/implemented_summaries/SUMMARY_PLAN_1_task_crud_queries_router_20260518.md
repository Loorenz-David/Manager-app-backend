# SUMMARY: Plan 1 — Task CRUD, Queries & Router

## Plan ID
`PLAN_task_crud_queries_router_20260518`

## Status
✅ **COMPLETE** — All acceptance criteria met, all tests passing (10/10)

## Lifecycle State
`ARCHIVED` — Moved to `backend/docs/architecture/archives/implementation/`

---

## Implementation Overview

Plan 1 implemented the core task lifecycle: create, read, update, delete (soft), and state transitions (resolve/cancel/fail). This plan established the foundational task API surface used by all subsequent plans.

### Files Created/Modified

| File | Purpose |
|---|---|
| `beyo_manager/services/commands/tasks/requests/__init__.py` | **NEW** — Request models for all 8 commands |
| `beyo_manager/services/commands/tasks/create_task.py` | **NEW** — CMD-1: Create task with customer & item |
| `beyo_manager/services/commands/tasks/update_task.py` | **NEW** — CMD-2: Patch task fields |
| `beyo_manager/services/commands/tasks/delete_task.py` | **NEW** — CMD-3: Soft-delete task |
| `beyo_manager/services/commands/tasks/resolve_task.py` | **NEW** — CMD-4: Transition task to RESOLVED |
| `beyo_manager/services/commands/tasks/cancel_task.py` | **NEW** — CMD-5: Transition task to CANCELLED |
| `beyo_manager/services/commands/tasks/fail_task.py` | **NEW** — CMD-6: Transition task to FAILED |
| `beyo_manager/services/commands/tasks/add_item_to_task.py` | **NEW** — CMD-7: Link item to task |
| `beyo_manager/services/commands/tasks/remove_item_from_task.py` | **NEW** — CMD-8: Unlink item from task |
| `beyo_manager/services/queries/tasks/tasks.py` | **NEW** — QUERY-1 & QUERY-2: List & detail queries |
| `beyo_manager/routers/api_v1/tasks.py` | **NEW** — Task router with all endpoints |
| `beyo_manager/routers/api_v1/__init__.py` | Modified: Register task router |

### Key Features Implemented

1. **CMD-1: Create Task**
   - Calls `find_or_create_customer` (subordinate) for customer data
   - Calls `find_or_create_item` (subordinate) for primary item
   - Creates `TaskItem` entries for each item in payload
   - Handles item issues via `_create_item_issue_in_session` (subordinate)
   - Handles item upholstery via `_create_item_upholstery_in_session` (subordinate)
   - Seller role → always `state=pending`; Manager/Admin can specify working_section_ids
   - Returns: `{client_id, task_scalar_id}` — unique sequential integer per workspace

2. **CMD-2: Update Task (PATCH)**
   - Only fields in request body are updated (`model_fields_set` semantics)
   - Omitted fields not overwritten
   - All snapshot fields (customer contact, working section name) updated on change

3. **CMD-3, CMD-4, CMD-5, CMD-6: Delete & State Transitions**
   - `DELETE /tasks/{id}`: soft-delete with `is_deleted=true, deleted_at=now()`
   - `POST /tasks/{id}/resolve`: `state=resolved, closed_at=now()`
   - `POST /tasks/{id}/cancel`: `state=cancelled, closed_at=now()`, guards against already-terminal
   - `POST /tasks/{id}/fail`: `state=failed, closed_at=now()`, guards against already-terminal

4. **CMD-7 & CMD-8: Item Link Management**
   - `POST /tasks/{id}/items`: Add item to task, enforces single active PRIMARY
   - `DELETE /tasks/{id}/items/{item_id}`: Soft-remove with `removed_at, removed_by_id`

5. **QUERY-1: List Tasks (Compressed)**
   - Offset pagination (limit, offset defaults)
   - Filters: working_section, state, step_state, step_readiness, priority, task_type, return_source, date ranges, upholstery requirement state, is_deleted
   - Full-text search on: title, additional_details, phone numbers, emails, item fields (article_number, sku, designer, etc.), upholstery name/code
   - Default ordering: `ready_by_at ASC NULLS LAST`, then `priority DESC`, then `created_at ASC`
   - Returns compressed payload (no nested items/steps)

6. **QUERY-2: Detail Task (Full)**
   - Returns complete payload: task + all items + item_upholstery + requirements + task_steps with state records
   - All navigation relationships included

### Test Results
- **10/10 tests PASSED** ✓
  - Task creation (with customer, item, issues, upholstery)
  - Task update with `model_fields_set` semantics
  - Soft-delete
  - State transitions (resolve, cancel, fail)
  - Item linking (enforces single active PRIMARY)
  - Item removal
  - List query with filters and search
  - Detail query with nested data
  - Pagination
  - Workspace isolation & multi-tenant correctness

### Dependencies
- **Plan 0**: `find_or_create_item` (prerequisite)
- **Implicit**: `find_or_create_customer`, `_create_item_issue_in_session`, `_create_item_upholstery_in_session` (from existing codebase)

### Blockers Resolved
None — no blockers encountered during implementation.

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|---|---|---|
| Create task → `{client_id, task_scalar_id}` | ✅ | Response includes both; scalar_id unique per workspace |
| Seller role → always `state=pending` | ✅ | Test: seller payload ignored state field |
| Customer subordinate call + snapshot fields | ✅ | Test: customer data populated + contact snapshots filled |
| Item subordinate call + `role=primary` | ✅ | Test: find_or_create_item called, TaskItem.role=primary |
| Item issues via session helper | ✅ | Test: issues created in same transaction |
| Item upholstery via session helper | ✅ | Test: upholstery created in same transaction |
| No concurrent `task_scalar_id` collision | ✅ | `pg_advisory_xact_lock` pattern tested |
| PATCH semantics (omitted fields unchanged) | ✅ | Test: partial update leaves other fields untouched |
| Soft-delete (`is_deleted=true, deleted_at`) | ✅ | Test: DELETE endpoint sets both flags |
| State transitions with guards | ✅ | Test: cannot cancel/fail already-terminal task |
| Single active PRIMARY per task | ✅ | Test: second PRIMARY request → ConflictError |
| Soft-remove item (`removed_at, removed_by_id`) | ✅ | Test: DELETE /items/{id} sets both fields |
| List query filters & search | ✅ | Test: all filters work; search on multiple fields (ILIKE) |
| Detail query with nested data | ✅ | Test: GET /{id} returns full payload |
| Default ordering | ✅ | Test: `ready_by_at ASC NULLS LAST`, then `priority DESC`, then `created_at ASC` |

---

## Domain Architecture Alignment

✅ **Contract Compliance:**
- All commands follow `backend/architecture/06_commands.md` pattern
- Subordinate mode correctly implemented (no nested transactions)
- `ServiceContext` threading correct
- Error types properly imported and raised
- Router structure matches `backend/architecture/09_routers.md`

✅ **Multi-Tenant Isolation:**
- All queries include `workspace_id` filter
- Partial indexes on workspace-scoped columns
- Foreign keys respect workspace boundaries

---

## Quality Gate Results

- ✅ Contract adherence: All business logic in commands, not routers
- ✅ Architecture boundaries: Proper layer separation
- ✅ Validation: 10/10 tests pass
- ✅ Error handling: Typed domain errors throughout
- ✅ Transaction safety: `maybe_begin` pattern enforced

---

## Integration Notes

Plan 1 enables:
- Plan 2: Task notes (amends CMD-1 for notes-in-payload)
- Plans 3-6: All task step & analytics functionality depends on task CRUD

---

## Metadata

- Implemented by: Copilot (GitHub Copilot)
- Implementation date: 2026-05-18
- Test suite: `backend/tests/tasks/test_task_crud.sh` (10/10 ✓)
- Linked intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`
