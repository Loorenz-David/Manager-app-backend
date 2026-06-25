# HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Owner agent: `Codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_step_ready_by_at_20260625.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_step_ready_by_at_20260625.md`

## Backend delivery context

- What backend implemented:
  - Added nullable `ready_by_at` to `TaskStep`.
  - Extended task creation and step-add flows so each step can set `ready_by_at`, with fallback to the task-level `ready_by_at`.
  - Added a batch route to update step deadlines after creation.
- API or contract changes:
  - Step objects now include `ready_by_at` on task detail, task step list, working-section step list, and last-active-step payloads that already serialize steps.
  - New endpoint: `PATCH /api/v1/tasks/{task_id}/steps/ready-by-at`.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Include `ready_by_at` in step-create payloads where step-specific deadlines are supported.
2. Read and render `ready_by_at` from all returned step objects.
3. Wire bulk deadline editing to the new batch endpoint if step deadlines are editable after creation.
4. Validate null handling: a step may have `ready_by_at: null`.

## Interface details

- Endpoint(s):
  - `PUT /api/v1/tasks`
  - `POST /api/v1/tasks/{task_id}/steps`
  - `PATCH /api/v1/tasks/{task_id}/steps/ready-by-at`
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/steps`
  - `GET /api/v1/working-sections/{working_section_id}/steps`
  - `GET /api/v1/working-sections/steps/user-last-active`
- Request shape:
  - Task create `steps[]` items accept `ready_by_at?: string | null`.
  - Task step add body items accept `ready_by_at?: string | null`.
  - Ready-by-at batch update:
    ```json
    {
      "items": [
        {
          "step_id": "tsp_...",
          "ready_by_at": "2026-07-01T00:00:00Z"
        },
        {
          "step_id": "tsp_...",
          "ready_by_at": null
        }
      ]
    }
    ```
- Response shape:
  - Batch update returns:
    ```json
    {
      "step_ids": ["tsp_...", "tsp_..."]
    }
    ```
  - Step objects now contain:
    ```json
    {
      "ready_by_at": "2026-07-01T00:00:00+00:00"
    }
    ```
- Error cases:
  - `404` if the task does not exist.
  - `404` if any provided `step_id` does not belong to the task or does not exist in the workspace.
  - `400` if the batch body is empty or contains duplicate `step_id` values.

## Validation notes

- Backend validation run:
  - Targeted syntax checks and diff review completed.
  - Alembic autogeneration could not be run in this workspace because no local `alembic` executable/virtualenv was available.
- Suggested frontend validation:
  - Create a task with mixed step-level deadlines and inherited task-level deadline.
  - Add steps to an existing task with and without `ready_by_at`.
  - Update multiple step deadlines in one request, including clearing one to `null`.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_task_step_ready_by_at_20260625.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_step_ready_by_at_20260625.md`
- Related debug plan (optional): `—`
