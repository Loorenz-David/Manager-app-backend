# HANDOFF_TO_BACKEND_task_step_cases_summary_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_task_step_cases_summary_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source frontend plan: `docs/architecture/under_construction/implementation/PLAN_35_task_step_cases_summary_20260529.md`

## Request to backend

- Required backend behavior: Embed a `cases_summary` aggregate object on each task step record returned by the task steps list endpoint. The aggregate must reflect the current state of cases linked to the task (via `entity_type = "task"` and `entity_client_id = task.client_id`).
- User-facing impact: Workers see a notification badge on task cards and inside task detail showing how many unread case messages they have. Tapping the badge/button routes them directly to the right place (creation, list, or conversation) without extra requests.
- Desired timeline: As soon as possible — frontend development is proceeding in parallel and the plan is already written. Frontend Zod schema uses `.nullable().optional()` so it tolerates the field being absent, but routing logic and badges only activate once `cases_summary` is present.

## Frontend context

- Why the frontend needs this: The task detail page needs to decide at tap time which surface to open (creation vs. list vs. conversation), without issuing a separate cases query before the user taps. Embedding the aggregate in the task step fetch eliminates a waterfall and keeps the task card badges cheap (already fetched with the list).
- Blocked frontend plan: `docs/architecture/under_construction/implementation/PLAN_35_task_step_cases_summary_20260529.md`
- Clarifications required:
  - [ ] Should `total_unread` count unread from all participants or only the authenticated worker? — frontend assumes it is scoped to the current user (the worker's own unread count). If it is global, the badge semantics change.
  - [ ] Is `open_resolving_count` inclusive of both `open` and `resolving` states? — frontend assumes yes; please confirm.
  - [ ] When a task has no linked cases at all, should `cases_summary` be `null` or an object with all zeros? — frontend handles both correctly (`.nullable().optional()`), but using a zero object avoids a null check on the front end and is preferred.

## Expected backend deliverables

1. Each task step object in the list response includes a `cases_summary` field with the shape described below.
2. `cases_summary` is always present (not absent) in the response — a task with no cases returns the zero object `{ open_resolving_count: 0, total_unread: 0, unread_case_count: 0, single_unread_case_id: null }`.
3. `single_unread_case_id` is non-null **only** when `unread_case_count === 1`. It must be null when `unread_case_count` is 0 or > 1.
4. `total_unread` and `unread_case_count` are scoped to the authenticated user (the worker), not global totals.
5. `open_resolving_count` counts cases in state `open` or `resolving` linked to the task.

## Interface expectations

- Endpoint(s): `GET /working-sections/:working_section_id/steps` (the existing task steps list endpoint used by `useWorkingSectionStepsQuery`)
  - No new endpoint is needed; this is an additive field on the existing response items.

- Request shape: unchanged (no new params required)

- Response shape change — each item in the `items` array gains:

```json
{
  "client_id": "stp_01...",
  "task_id": "tsk_01...",
  "state": "working",
  "...(existing fields)": "...",
  "cases_summary": {
    "open_resolving_count": 2,
    "total_unread": 5,
    "unread_case_count": 1,
    "single_unread_case_id": "cas_01..."
  }
}
```

**Field semantics:**

| Field | Type | Meaning |
|---|---|---|
| `open_resolving_count` | `int ≥ 0` | Number of cases linked to this task that are in state `open` or `resolving`. |
| `total_unread` | `int ≥ 0` | Total unread message count across all open/resolving cases linked to this task, for the authenticated user. |
| `unread_case_count` | `int ≥ 0` | Number of distinct cases (among open/resolving) that have at least one unread message for the authenticated user. |
| `single_unread_case_id` | `string \| null` | The `client_id` of the one case with unread messages, **only when `unread_case_count === 1`**. Must be `null` in all other situations. |

**Zero state (task has no linked cases or all cases are resolved):**

```json
"cases_summary": {
  "open_resolving_count": 0,
  "total_unread": 0,
  "unread_case_count": 0,
  "single_unread_case_id": null
}
```

- Error cases: No new error cases. If the cases aggregate sub-query fails, the backend should return the zero object rather than failing the entire step list response (treat as non-blocking).

- Socket events: None required for this handoff. Real-time updates to `cases_summary` are deferred to a future plan.

## Frontend contract implications

- Architecture contracts affected:
  - `TaskStepSchema` in `apps/workers-app/.../features/task_steps/types.ts`: new `cases_summary` optional field added with `CasesSummarySchema`
  - `TaskStepCardViewModel`: new `casesSummary` field derived in `toTaskStepCardViewModel`
  - `TaskStepDetailController`: exposes `casesSummary` and `handleOpenCasesForTask`

- Local extension updates needed:
  - Frontend Zod schema `CasesSummarySchema` mirrors the shape above exactly
  - `useListCasesQuery` is called with `entity_client_id` + `entity_type` params when viewing task-scoped cases (from `TaskCasesSlidePage`) — ensure the cases list endpoint already supports these filters (it should per existing contract)

## Linking cases to a task

Cases are linked to tasks via the `case_links` table with:
- `entity_type = "task"`
- `entity_client_id = task.client_id`

The `cases_summary` aggregate should be computed using this link. Unread counts are read from the `case_participants` table for the authenticated user's `last_read_message_seq` vs. the case's `last_message_seq`.

## Trace links

- Related frontend plan: `docs/architecture/under_construction/implementation/PLAN_35_task_step_cases_summary_20260529.md`
