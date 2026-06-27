# SUMMARY_PLAN_task_steps_list_rich_and_count_20260627

## Metadata

- Summary ID: `SUMMARY_PLAN_task_steps_list_rich_and_count_20260627`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-06-27T09:57:10Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_steps_list_rich_and_count_20260627.md`
- Related debug plan (optional): `—`

## What was implemented

- Reworked `list_task_steps` to return the same rich step payload used by `get_task`, including `latest_state_records`.
- Removed the working-section join from the list query and switched the read path to `selectinload(TaskStep.latest_state_record)`.
- Added `count_task_step_states` to return grouped step-state counts for a task with the same task-not-found guard as the list endpoint.
- Added `GET /api/v1/tasks/{task_id}/steps/counts` with the existing task-step list role set and safe route ordering before wildcard step routes.

## Files changed

- `app/beyo_manager/services/queries/tasks/list_task_steps.py`: replaced compact step serialization with the rich task-detail step serialization and eager-loaded `latest_state_record`.
- `app/beyo_manager/services/queries/tasks/count_task_step_states.py`: added the grouped step-state count query service.
- `app/beyo_manager/routers/api_v1/tasks.py`: added the new `/{task_id}/steps/counts` route and query import.

## Contract adherence

- `architecture/07_queries.md` + `architecture/07_queries_local.md`: kept the query read-only, workspace-scoped, soft-delete filtered, and preserved the existing offset pagination shape.
- `architecture/09_routers.md`: kept the router thin, routed path params through `ServiceContext`, and declared the static `counts` path before step wildcard routes.
- `skills/_shared/quality_gate.md`: changes remained inside query/router layers with typed `NotFound` handling and no workspace-scope regression.

## Validation evidence

- `python3 -m py_compile ...`: passed for `list_task_steps.py`, `count_task_step_states.py`, and `routers/api_v1/tasks.py`.
- Manual code-path review: confirmed the list endpoint now matches the `get_task` task-step shape and the count endpoint returns grouped state counts only for the current workspace/task.

## Known gaps or deferred items

- No automated test suite was run in this turn, so runtime verification remains limited to static compilation and code review.

## Handoff notes (if needed)

- To frontend: `—`
- From frontend dependency: `—`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_task_steps_list_rich_and_count_20260627.md`
