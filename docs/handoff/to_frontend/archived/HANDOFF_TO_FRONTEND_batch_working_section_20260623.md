# HANDOFF_TO_FRONTEND_batch_working_section_20260623

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_batch_working_section_20260623`
- Created at (UTC): `2026-06-23T08:43:57Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_working_step_20260623.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_working_step_20260623.md`

## Backend delivery context

- What backend implemented:
  - Added manager-configurable `allows_batch_working` on working sections.
  - Exposed that field on both the compact worker section list payload and the full working-section payload.
  - Added request-body support so create/edit flows can set the flag.
  - Extended the resume-card endpoint (`GET /api/v1/working-sections/steps/user-last-active`) to return the user's whole **active batch group** when their current step belongs to a batch-capable section.
- API or contract changes:
  - `GET /api/v1/working-sections/me`: each `working_sections[]` item now includes `allows_batch_working`.
  - `GET /api/v1/working-sections/{working_section_id}`: `working_section` now includes `allows_batch_working`.
  - `PUT /api/v1/working-sections`: accepts `allows_batch_working`, default `false`.
  - `PATCH /api/v1/working-sections/{working_section_id}`: accepts optional `allows_batch_working`; omitted means unchanged.
  - `GET /api/v1/working-sections/steps/user-last-active`: response now also includes a top-level `active_batch_steps` field (`array | null`). The existing `user_last_active_step_record` field is unchanged and still returned.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Add a boolean control for `allows_batch_working` in working-section create and edit UI.
2. Read and persist `allows_batch_working` from both the worker section list and the full working-section detail payloads.
3. Do not expect this field on task-step payloads; it remains backend-internal on `task_steps` by design.
4. Update the resume card to handle the new `active_batch_steps` on `/steps/user-last-active`: when it is a non-empty array, render a batch resume card listing all of those steps; when it is `null`, render the single `user_last_active_step_record` exactly as today.

## Interface details

- Common success envelope: `{ ok: true, data: <payload>, warnings: [] }`
- Common error envelope: `{ ok: false, error: <message> }`

### 1) GET `/api/v1/working-sections/me`

- Auth roles: `admin`, `manager`, `worker`
- Response payload change:

Before:
```json
{
  "working_sections": [
    {
      "client_id": "wsec_01",
      "name": "Ground oil",
      "image": "https://example.com/ground-oil.webp",
      "order_list": 2,
      "task_steps_counts": {
        "pending": 0,
        "working": 1,
        "paused": 0,
        "ended_shift": 0,
        "blocked": 0,
        "completed": 0,
        "skipped": 0,
        "failed": 0
      }
    }
  ]
}
```

After:
```json
{
  "working_sections": [
    {
      "client_id": "wsec_01",
      "name": "Ground oil",
      "image": "https://example.com/ground-oil.webp",
      "order_list": 2,
      "allows_batch_working": true,
      "task_steps_counts": {
        "pending": 0,
        "working": 1,
        "paused": 0,
        "ended_shift": 0,
        "blocked": 0,
        "completed": 0,
        "skipped": 0,
        "failed": 0
      }
    }
  ]
}
```

### 2) GET `/api/v1/working-sections/{working_section_id}`

- Auth roles: `admin`, `manager`, `worker`, `seller`
- Response payload change:

Before:
```json
{
  "working_section": {
    "client_id": "wsec_01",
    "name": "Ground oil",
    "image": "https://example.com/ground-oil.webp",
    "order_list": 2,
    "dependencies": [],
    "item_categories": [],
    "supported_issue_types": [],
    "members": []
  }
}
```

After:
```json
{
  "working_section": {
    "client_id": "wsec_01",
    "name": "Ground oil",
    "image": "https://example.com/ground-oil.webp",
    "order_list": 2,
    "allows_batch_working": true,
    "dependencies": [],
    "item_categories": [],
    "supported_issue_types": [],
    "members": []
  }
}
```

### 3) PUT `/api/v1/working-sections`

- Auth roles: `admin`, `manager`
- New request field:
  - `allows_batch_working`: optional boolean, defaults to `false`

Example request:
```json
{
  "name": "Ground oil",
  "allows_batch_working": true,
  "working_section_dependencies": [],
  "working_section_item_categories": [],
  "working_section_supported_issue_types": []
}
```

### 4) PATCH `/api/v1/working-sections/{working_section_id}`

- Auth roles: `admin`, `manager`
- New request field:
  - `allows_batch_working`: optional boolean
- Behavior:
  - Omitted field: no change
  - `true` or `false`: updates the section for future step creation only

Example request:
```json
{
  "allows_batch_working": false
}
```

### 5) GET `/api/v1/working-sections/steps/user-last-active` (resume card)

- Auth roles: `admin`, `manager`, `worker`
- Purpose: the "resume where I left off" card for the signed-in user.
- Response now has two top-level fields:
  - `user_last_active_step_record`: the single most-relevant active step — **unchanged shape and meaning** (object or `null`).
  - `active_batch_steps`: **new** — `array | null`.
- Semantics:
  - The backend still computes one primary step (the most-relevant active record).
  - If that primary step belongs to a **batch-capable** section AND the user currently has one or more batch steps with an open active record (`working` / `paused` / `ended_shift`), `active_batch_steps` is the full list of those open batch steps. The primary step is **included** in that list.
  - Otherwise (primary is a non-batch step, or no open batch steps exist), `active_batch_steps` is `null` and behavior is identical to before.
  - Each item in `active_batch_steps` has the **same shape** as `user_last_active_step_record` (step + `last_state_record` + `task` + `item` + `item_images` + `cases_summary`), so the same card component can render either.
  - Ordering: most recently entered open active record first.
- Frontend rule of thumb: `if (active_batch_steps?.length) renderBatchCard(active_batch_steps); else renderSingleCard(user_last_active_step_record);`
- Edge note (mixed state): if the user has both an individual (non-batch) step and batch steps open at once, the primary is whichever the priority ranking selects; `active_batch_steps` is only populated when that primary is itself a batch step. The individual-vs-batch resume stays a single-or-list choice, never both at once.

Single (non-batch) example — unchanged:
```json
{
  "user_last_active_step_record": { "client_id": "tsp_01", "state": "working", "...": "..." },
  "active_batch_steps": null
}
```

Batch example:
```json
{
  "user_last_active_step_record": { "client_id": "tsp_07", "state": "working", "...": "..." },
  "active_batch_steps": [
    { "client_id": "tsp_07", "state": "working", "...": "..." },
    { "client_id": "tsp_05", "state": "paused", "...": "..." },
    { "client_id": "tsp_03", "state": "working", "...": "..." }
  ]
}
```

### 6) Task-step payload note

- `allows_batch_working` is intentionally absent from task-step serializers and task-step API payloads (including the steps returned by the resume-card endpoint above).
- Frontend should treat the working-section responses as the only public source for this flag.

## Validation notes

- Backend validation run:
  - Single-head Alembic chain confirmed after the new migration was added.
  - Targeted unit tests passed for serializer and transition helpers.
  - DB-backed migration and integration execution were blocked in this session by sandbox restrictions on local Postgres access.
- Suggested frontend validation:
  - Verify the create/edit form can toggle the boolean and persist it correctly.
  - Verify `/me` and `/{working_section_id}` consumers tolerate both `true` and `false`.
  - Verify task-step UI does not expect the field to appear in step payloads.
  - Verify the resume card: a non-batch active step returns `active_batch_steps: null` (single card unchanged); a batch active step returns the populated list (batch card), with the primary present in the list.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_batch_working_step_20260623.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_working_step_20260623.md`
- Related debug plan (optional): `—`
