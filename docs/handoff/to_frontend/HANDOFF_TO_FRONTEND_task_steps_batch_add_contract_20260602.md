# HANDOFF_TO_FRONTEND_task_steps_batch_add_contract_20260602

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_steps_batch_add_contract_20260602`
- Created at (UTC): `2026-06-02T15:59:16Z`
- Owner agent: `copilot`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_step_creation_with_dependencies_20260602.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_batch_step_creation_with_dependencies_20260602.md`

## Backend delivery context

- What backend implemented:
  - `POST /api/v1/tasks/{task_id}/steps` now creates one or more task steps in a single request.
  - `DELETE /api/v1/tasks/{task_id}/steps` now deletes one or more task steps in a single request.
  - New steps are wired into the working-section dependency graph immediately at creation time.
  - New steps now start with correct `total_dependencies`, `completed_dependencies`, and `readiness_status` instead of always starting effectively ready.
  - When a new prerequisite step is added, existing non-terminal dependent steps in the same task may have readiness recalculated.
  - When prerequisite steps are deleted, surviving dependent steps now have dependency counters and readiness recalculated in bulk.
- API or contract changes:
  - Breaking request change: body changed from a single object to an array of step objects.
  - Breaking response change: success data changed from `{ "step_id": "..." }` to `{ "step_ids": ["...", ...] }`.
  - New batch delete endpoint: `DELETE /api/v1/tasks/{task_id}/steps` with raw JSON array body.
  - Behavioral change: step readiness and dependency counters may now reflect blocking state immediately after creation.
  - Behavioral change: deleting multiple prerequisite steps in one request updates surviving dependents once per affected step instead of per-edge looping.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Update every caller of `POST /api/v1/tasks/{task_id}/steps` to send a JSON array, including the single-step case.
2. Update success handling to read `data.step_ids` instead of `data.step_id`.
3. If the UI adds one step at a time, wrap the existing payload in an array of length 1.
4. Do not assume newly created steps are immediately ready; use the returned/refetched step data to render `readiness_status`, `total_dependencies`, and `completed_dependencies`.
5. Keep realtime listeners or refresh flows active for existing steps in the task, because adding a prerequisite step can trigger `task:step-readiness-changed` for already-existing dependent steps.
6. Add a batch delete API method for `DELETE /api/v1/tasks/{task_id}/steps` that sends a raw JSON array of step ids.
7. For bulk delete UX, use the new batch delete endpoint instead of looping `DELETE /{task_id}/steps/{step_id}`.
8. Keep the single-delete path only for one-off removal if desired; it remains supported as a compatibility route.
9. After batch delete, refresh or react to realtime updates for surviving steps because dependency counters and readiness may change.

## Interface details

- Endpoint: `POST /api/v1/tasks/{task_id}/steps`
- Roles allowed: `ADMIN`, `MANAGER`

### Previous request shape

```json
{
  "client_id": "tsp_custom_optional",
  "working_section_id": "wsec_xxx",
  "worker_id": "usr_worker_optional",
  "sequence_order": 3
}
```

### New request shape

```json
[
  {
    "client_id": "tsp_custom_optional_a",
    "working_section_id": "wsec_cutting",
    "worker_id": "usr_worker_optional",
    "sequence_order": 1
  },
  {
    "working_section_id": "wsec_upholstery",
    "sequence_order": 2
  }
]
```

Request notes:

- The request body is now an array.
- Each item keeps the same field shape as before:
  - `working_section_id`: required
  - `worker_id`: optional
  - `client_id`: optional custom step id
  - `sequence_order`: optional
- Single-step creation is still supported, but the body must be:

```json
[
  {
    "working_section_id": "wsec_xxx"
  }
]
```

### Previous success data

```json
{
  "step_id": "tsp_xxx"
}
```

### New success data

```json
{
  "step_ids": [
    "tsp_xxx",
    "tsp_yyy"
  ]
}
```

### Behavioral notes

- If `worker_id` is omitted for an item:
  - if the working section has exactly one active member, backend auto-assigns that worker,
  - otherwise the step remains unassigned.
- Newly created steps may now start as:
  - `ready`
  - `partial`
  - `blocked`
  depending on configured working-section prerequisites and prerequisite step state in the same task.
- Adding a new prerequisite step can recalculate readiness of existing non-terminal dependent steps already on the task.
- Backend emits:
  - `task:updated` for the task
  - `task:step-readiness-changed` for existing affected steps whose readiness changed

### Error cases

Existing errors still apply:

- `Task not found.`
- `Working section '<id>' not found.`
- `Cannot add a step to a terminal task.`
- `Provided client_id is already in use.`

New batch-specific error case:

- `Duplicate client_id provided in step batch.`

Validation behavior:

- Duplicate `client_id` values inside the same batch fail before any step is written.
- Missing `working_section_id` items fail request validation.
- Unknown `working_section_id` values fail before any step is written.

## Batch delete details

- Endpoint: `DELETE /api/v1/tasks/{task_id}/steps`
- Roles allowed: `ADMIN`, `MANAGER`

### Request shape

```json
[
  "tsp_xxx",
  "tsp_yyy"
]
```

Request notes:

- The request body is a raw JSON array of step ids.
- Array length must be at least 1.
- Duplicate ids in the same batch are rejected.
- If the UI deletes a single step through this endpoint, send an array of length 1.

### Success data

```json
{
  "step_ids": [
    "tsp_xxx",
    "tsp_yyy"
  ]
}
```

### Compatibility note

- Existing single delete remains supported:
  - `DELETE /api/v1/tasks/{task_id}/steps/{step_id}`
- Single delete success shape remains:

```json
{
  "step_id": "tsp_xxx"
}
```

### Delete behavioral notes

- All requested step ids must belong to the task and exist in the current workspace.
- All requested step ids must still be active; already-deleted steps fail the batch.
- The batch operation is transactional; invalid ids do not partially delete the set.
- Open step state records for removed steps are closed in bulk.
- Active dependency edges touching removed steps are soft-removed in bulk.
- Surviving dependent steps have:
  - `total_dependencies` decremented correctly
  - `completed_dependencies` decremented correctly when removed prerequisites had been completed
  - `readiness_status` recalculated once per affected step
- Task state is still recalculated after deletion:
  - no remaining steps => `pending`
  - all remaining non-deleted steps terminal => `ready`

### Delete events

- Backend emits:
  - `task:updated` for the task
  - `task:step-readiness-changed` for surviving affected steps whose readiness changed
  - `task:state-changed` when the task state changes as a side effect

### Delete error cases

- `Task not found.`
- `Task step(s) not found: ...`
- `Task step(s) already deleted: ...`
- `Duplicate step_id provided in step batch.`
- Request validation failure if the array is empty or malformed.

## Validation notes

- Backend validation run:
  - `PYTHONPATH=. ./.venv/bin/pytest tests/unit/services/commands/task_steps/test_wire_new_step_dependencies.py` in `backend/app`: passed
  - `PYTHONPATH=. ./.venv/bin/pytest tests/unit/services/commands/task_steps/test_remove_task_steps.py` in `backend/app`: passed
  - `PYTHONPATH=. ./.venv/bin/python -m py_compile ...` on changed backend files: passed
  - `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed
- Suggested frontend validation:
  - Submit one step using array-of-one payload and verify success reads `step_ids[0]`.
  - Submit multiple steps in one request and verify all returned ids are handled.
  - Add a step in a section with unmet prerequisites and verify the rendered step shows blocked/partial readiness after refresh or realtime update.
  - Add a prerequisite step to a task that already has dependent steps and verify dependent-step readiness updates in UI.
  - Delete one step through `DELETE /api/v1/tasks/{task_id}/steps` using an array-of-one payload and verify success reads `step_ids[0]`.
  - Delete multiple steps in one request and verify all ids are handled and removed from UI.
  - Delete a prerequisite step in a batch and verify surviving dependent steps update readiness and dependency counters.
  - Try sending duplicate ids in the delete batch and verify the request fails without partial deletion.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_batch_step_creation_with_dependencies_20260602.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_batch_step_creation_with_dependencies_20260602.md`
- Related archive record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_batch_step_creation_with_dependencies_20260602_1555.md`
- Prior related handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_steps_add_assign_remove_contracts_20260525.md`
