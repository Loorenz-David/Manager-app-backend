# HANDOFF_TO_FRONTEND_task_steps_add_assign_remove_contracts_20260525

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_steps_add_assign_remove_contracts_20260525`
- Created at (UTC): `2026-05-25T00:00:00Z`
- Owner agent: `copilot`
- Scope: add task step + assign worker to step + remove task step

## Global response envelope

- Success:

```json
{
  "ok": true,
  "warnings": [],
  "data": {}
}
```

- Error:

```json
{
  "ok": false,
  "error": "..."
}
```

## 1) Add task step (working section + optional worker)

### Endpoint

- `POST /api/v1/tasks/{task_id}/steps`

### Params

- Path:
  - `task_id: string` (required)

### Body

```json
{
  "client_id": "tsp_custom_optional",
  "working_section_id": "wsec_xxx",
  "worker_id": "usr_worker_optional",
  "sequence_order": 3
}
```

### Body field notes

- `working_section_id` is required.
- `worker_id` is optional.
- `client_id` is optional custom step id; when provided it must be unique and valid for `tsp` prefix rules.
- If `worker_id` is omitted:
  - if the working section has exactly one active member, backend auto-assigns that worker,
  - otherwise step remains unassigned.

### Success data shape

```json
{
  "step_id": "tsp_xxx"
}
```

### Common errors

- `Task not found.`
- `Working section not found.`
- `Cannot add a step to a terminal task.`
- `Provided client_id is already in use.`

## 2) Assign worker to an existing step

### Endpoint

- `POST /api/v1/tasks/{task_id}/steps/{step_id}/assign-worker`

### Params

- Path:
  - `task_id: string` (required)
  - `step_id: string` (required)

### Body

```json
{
  "worker_id": "usr_worker_xxx"
}
```

### Behavior notes

- Does not create a new step.
- Replaces current active assignment (if any): old assignment is closed, a new assignment record is created.
- Updates step assignee snapshot fields.
- If assigned worker is not the same user as requester, backend emits a notification task.

### Success data shape

```json
{
  "assignment_id": "sar_xxx",
  "worker_id": "usr_worker_xxx"
}
```

### Common errors

- `Task step not found.`
- `Worker not found.`

## 3) Remove task step

### Endpoint

- `DELETE /api/v1/tasks/{task_id}/steps/{step_id}`

### Params

- Path:
  - `task_id: string` (required)
  - `step_id: string` (required)

### Body

- none

### Behavior notes

- Step is soft-deleted.
- Step state is set to `skipped` and open state record is closed.
- Related active dependencies are removed.
- Task state may be recalculated:
  - no remaining steps => task may revert to `pending`,
  - all remaining steps terminal => task may move to `ready`.

### Success data shape

```json
{
  "step_id": "tsp_xxx"
}
```

### Common errors

- `Task step not found.`
- `Task not found.`
- `Task step is already deleted.`

## Trace links

- Router:
  - `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Commands:
  - `backend/app/beyo_manager/services/commands/task_steps/add_task_step.py`
  - `backend/app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py`
  - `backend/app/beyo_manager/services/commands/task_steps/remove_task_step.py`
- Request parsing:
  - `backend/app/beyo_manager/services/commands/task_steps/requests/__init__.py`
