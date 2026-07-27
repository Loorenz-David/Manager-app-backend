# HANDOFF_TO_FRONTEND_task_post_handling_20260701

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_post_handling_20260701`
- Created at (UTC): `2026-07-01T12:51:50Z`
- Owner agent: `Codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_system_scalability_20260701.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_system_scalability_20260701.md`

## Backend delivery context

- What backend implemented:
  - Added nullable `assortment` to task payloads.
  - Extended `PATCH /api/v1/tasks/{task_id}` so `assortment` can be updated through the existing general task edit flow.
  - Added `PATCH /api/v1/tasks/{task_id}/post-handling` for post-handling updates without using the broader task edit route.
- API or contract changes:
  - Task objects returned by task APIs now include `assortment`.
  - New post-handling route accepts partial updates to `fulfillment_method`, `scheduled_start_at`, `scheduled_end_at`, `task_type`, and `assortment`.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Read and render `assortment` from task payloads where post-handling or assortment information is shown.
2. Send `assortment` through `PATCH /api/v1/tasks/{task_id}` if the existing general task edit UI owns that field.
3. Use `PATCH /api/v1/tasks/{task_id}/post-handling` for the dedicated post-handling UI so fulfillment, schedule, task type, and assortment can be saved independently.
4. Handle nullable values for all post-handling fields, especially `assortment`, `scheduled_start_at`, and `scheduled_end_at`.

## Interface details

- Endpoint(s):
  - `PATCH /api/v1/tasks/{task_id}`
  - `PATCH /api/v1/tasks/{task_id}/post-handling`
  - `GET /api/v1/tasks/{task_id}`
- Request shape:
  - Task update now also accepts:
    ```json
    {
      "assortment": "Dining collection"
    }
    ```
  - Post-handling route accepts any subset of:
    ```json
    {
      "fulfillment_method": "delivery",
      "scheduled_start_at": "2026-07-10T08:00:00Z",
      "scheduled_end_at": "2026-07-10T12:00:00Z",
      "task_type": "internal",
      "assortment": "Dining collection"
    }
    ```
- Response shape:
  - Both patch routes return:
    ```json
    {
      "client_id": "tsk_..."
    }
    ```
  - Task payloads now include:
    ```json
    {
      "assortment": "Dining collection"
    }
    ```
- Realtime event: both routes emit `task:updated` on success — existing task subscriptions will receive the change without additional wiring.
- Error cases:
  - `404` if the task does not exist in the workspace.
  - `400` if a terminal task is patched.
  - `400` if `scheduled_end_at` is earlier than `scheduled_start_at`.
  - `400` if enum values such as `task_type` or `fulfillment_method` are invalid.

## Validation notes

- Backend validation run:
  - Python syntax compilation passed for the changed backend modules.
  - Alembic migration `1f6a0c9b3d2e` applied successfully and is the current head.
  - Frontend monorepo `npm run typecheck` passed.
- Suggested frontend validation:
  - Edit only `assortment` through the general task edit flow and confirm the next `GET /tasks/{task_id}` returns it.
  - Save a post-handling form that updates schedule plus fulfillment method.
  - Save a post-handling form that changes only `task_type`.
  - Clear `assortment` by sending `null` and verify the UI renders an empty state correctly.

---

## Update: Task post-handling lifecycle (2026-07-01)

### New endpoints

#### `GET /api/v1/tasks/{task_id}/post-handling`

Returns all post-handling instances for a task in oldest-first order.
Access: `ADMIN`, `MANAGER`, `SELLER`.

Response:

```json
{
  "post_handling": [
    {
      "client_id": "tph_...",
      "task_id": "tsk_...",
      "state": "pending",
      "created_at": "2026-07-01T10:00:00Z",
      "updated_at": null
    }
  ]
}
```

States: `pending` -> `filled` -> `completed`.

#### `POST /api/v1/tasks/{task_id}/post-handling/complete`

Marks the active non-completed post-handling instance as completed.
Access: `ADMIN`, `MANAGER`, `SELLER`.

Request body:

```json
{
  "post_handling_id": "tph_...",
  "force": false
}
```

- If `post_handling_id` is omitted, the backend uses the `task_id` path parameter to resolve the active instance.
- Completion requires state `filled` unless `force` is `true`.

Response:

```json
{
  "client_id": "tph_..."
}
```

### Updated task payloads and filtering

- `GET /api/v1/tasks/{task_id}` now always includes `task.post_handling` as an array.
- `GET /api/v1/tasks` accepts `post_handling_states` as a CSV filter such as `"pending,filled"`.
- When the list filter is absent, each task payload includes `"post_handling": null`.
- When the list filter is present, each task payload includes `"post_handling": [...]`.

Example task fragment:

```json
{
  "task": {
    "client_id": "tsk_...",
    "post_handling": [
      {
        "client_id": "tph_...",
        "task_id": "tsk_...",
        "state": "filled",
        "created_at": "2026-07-01T10:00:00Z",
        "updated_at": "2026-07-01T11:15:00Z"
      }
    ]
  }
}
```

#### `GET /api/v1/tasks/post-handling/counts`

Returns the count of post-handling records per state for the workspace.
Access: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`.

Query parameter:
- `post_handling_states` (optional, CSV) — e.g. `"pending,filled"`. When omitted, all three states are returned.

Response with no filter:

```json
{
  "pending": 12,
  "filled": 5,
  "completed": 38
}
```

Response with `?post_handling_states=pending,filled`:

```json
{
  "pending": 12,
  "filled": 5
}
```

- States with zero records are always included in the response as `0`.
- The count reflects post-handling records, not tasks. In practice one active record per task means the counts are equivalent.

### Lifecycle notes

- A `TaskPostHandling` record is created automatically when a supported task (`return` or `pre_order`) transitions to `READY`.
- For `pre_order`, the record becomes `filled` when `fulfillment_method` is set **and** at least one of `scheduled_start_at` / `scheduled_end_at` is set.
- For `return`, the record becomes `filled` when `assortment` is present.
- Completion is manual through `POST /api/v1/tasks/{task_id}/post-handling/complete`.
- Successful completion emits realtime event `task_post_handling:completed`.

---

## PENDING → FILLED transition rules

The backend evaluates post-handling state automatically whenever a task is updated via `PATCH /api/v1/tasks/{task_id}` or `PATCH /api/v1/tasks/{task_id}/post-handling`. Use these rules to know which fields are missing and surface them in the UI.

Only tasks with `task_type` of `return` or `pre_order` have a post-handling record. Other task types are ignored.

### `task_type: pre_order`

**All of the following must be true:**

| Field | Condition |
|---|---|
| `fulfillment_method` | Not null and not empty string |
| `scheduled_start_at` OR `scheduled_end_at` | At least one is not null |

If either condition is missing the record stays `pending`.

Example — missing schedule, `fulfillment_method` is set but no dates → still `pending`.
Example — both `fulfillment_method` set and `scheduled_start_at` set → `filled`.

### `task_type: return`

**The following must be true:**

| Field | Condition |
|---|---|
| `assortment` | Not null and not empty string |

If `assortment` is null or empty the record stays `pending`.

### When evaluation runs

State is re-evaluated after every successful call to:
- `PATCH /api/v1/tasks/{task_id}` (general update)
- `PATCH /api/v1/tasks/{task_id}/post-handling` (post-handling update)

The frontend does not need to trigger evaluation explicitly — saving any relevant field is enough.

### Practical implication for the UI

Show a checklist or inline prompt on the post-handling section based on `task_type`:

**PRE_ORDER checklist:**
- [ ] Fulfillment method selected (`fulfillment_method`)
- [ ] At least one of: delivery start date (`scheduled_start_at`) or delivery end date (`scheduled_end_at`)

**RETURN checklist:**
- [ ] Assortment filled in (`assortment`)

When all required fields are present and the user saves, the `post_handling[0].state` in the response will be `filled`.

---

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_task_system_scalability_20260701.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_system_scalability_20260701.md`
- Related debug plan (optional): `—`
