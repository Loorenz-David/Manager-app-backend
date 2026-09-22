# HANDOFF_TO_BACKEND_single_task_step_fetch_20260922

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_single_task_step_fetch_20260922`
- Created at (UTC): `2026-09-22T18:30:00Z`
- Owner agent: `Claude Fable 5.1` (frontend), on the owner's decision
- Source frontend plan: none yet — the frontend change is small and waits on this endpoint
- Related:
  - `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` — the live clock this bug freezes
  - `HANDOFF_TO_FRONTEND_step_time_settlement_window_answer_20260916.md` — the transition
    response the frontend already seeds its caches from. **No change requested there.**

## Summary

The worker task-step detail page has no way to fetch the one step it is showing. It reads the
step out of a cached *section list page* and, when the step is not in that page, falls back to
a frozen copy handed over at open time. That copy is never updated by anything, so tapping
Start/Pause on the detail page updates the server and every cache, but the page keeps showing
the old state and the old clock until it is closed and reopened.

The frontend fix is to give each step its own cache entry that every list fetch, every opener
and every transition writes into. That entry needs one thing the API does not offer today:
**a request that returns a single step in the worker step-card shape.**

## Request to backend

- Required backend behavior: `GET /api/v1/working-sections/steps/{step_id}` returning the
  step-card payload for one step, byte-for-byte the item shape of
  `GET /working-sections/{working_section_id}/steps` (and of `user_last_active_step_record`).
- User-facing impact: on the worker app, Start/Pause/Resume on the step detail page renders
  immediately regardless of how the page was opened (section list page 2+, last-active card,
  reassigned rows, push deep link). Today those paths show a frozen button and clock.
- Desired timeline: next backend release. The bug is reproducible on every step past the
  first list page and on every last-active open.

## Evidence

Captured 2026-09-22 on the workers app (dev server, same on the production build), step
`tsp_01M2842TJ9RGWDQ98RK3RW5607`, opened from the last-active card, then Pause tapped:

```
[clock] detail step   source=initialStep-snapshot  hasListQueryParams=false  items=20  state=working
[clock] tap           state=working  nextState=paused
[clock] onMutate patched   matchedSectionLists=1   (step not in that list)
[clock] socket task:step-state-changed
[clock] onSuccess     new_state=paused  total_working_seconds=47
[clock] invalidating section lists now
[clock] detail step   source=initialStep-snapshot  state=working  totalWorkingSeconds=14   ← unchanged
```

Server state, the transition response and the section-list caches were all correct. The page
was reading an object that no cache write can reach. Reproduced again by paging the section
list to page 2 and opening a step from there: the detail reuses page 1's parameters, the step
lives in the page 2 entry, same fallback, same freeze.

## Mechanism, as we read it

The backend already builds exactly this payload for one step:

- `services/queries/working_sections/step_record_payload.py`
  - `load_step_with_latest_record(ctx, step_id)` — loads the step scoped to the workspace,
    non-deleted task, with `latest_state_record` and its pause reason.
  - `build_step_record_payload(ctx, step)` — the single-step card payload the
    `steps/user-last-active` route returns.

The new route is those two calls behind a path parameter. Please verify parity with
`build_steps_list_payload` (`steps_list_payload.py`) for the fields the list computes in batch
and the single-step builder may not: `is_reassigned`, `upholstery_group_*`, `cases_summary`,
`dependency_working_sections`. The frontend validates the response against the same Zod schema
it uses for list items (`WorkingSectionStepItemSchema` from `@beyo/task-working-sections`), so a
missing required field fails the parse and the page shows the error state.

## Expected backend deliverables

1. `GET /api/v1/working-sections/steps/{step_id}` — roles `ADMIN`, `MANAGER`, `WORKER`
   (same as the section list route).
2. Response `data.step` has the exact section-list item shape. A step from a section the caller
   is not a member of is still returned if the caller can see it through the list route today;
   apply the same visibility rule the list uses, not a stricter one.
3. `404` for a step that does not exist, is deleted, belongs to a deleted task, or belongs to
   another workspace. No distinction between those cases is needed.
4. Route declared after `/steps/user-last-active` in `routers/api_v1/working_sections.py`, so
   the literal path keeps winning. (No collision with `/{working_section_id}/steps` — different
   segment count — but keep the literal-before-parameter order the file already follows.)
5. A dated answer handoff (`HANDOFF_TO_FRONTEND_single_task_step_fetch_answer_<date>.md`)
   confirming the path, the parity check result, and the error envelope used for 404.

## Interface expectations

- Endpoint: `GET /api/v1/working-sections/steps/{step_id}`
- Request shape: path parameter only. No query parameters.
- Response shape (success envelope, as every other route):

```json
{
  "data": {
    "step": { /* WorkingSectionStepItem — identical to a section list item */ }
  }
}
```

- Error cases: `404` not found (see deliverable 3); `401`/`403` as the list route.
- Socket events: none new. The frontend keeps invalidating on `task:step-state-changed`,
  `task:step-assigned`, `task:step-deleted` and the upholstery events, and will refetch this
  route for the open detail.

## Frontend plan once delivered (for context, no action needed)

- New key `taskStepKeys.step(stepId)` in the workers app; the detail controller reads only it.
- Every opener (section list card, last-active card, reassigned rows, reassignment acks, push
  deep link) seeds the entry with the step it already has, so first paint is unchanged.
- `useTransitionStepState` and the batch transition patch the entry in `onMutate` and
  `onSuccess`, next to the list patches they do today.
- Section list, last-active and reassigned fetches write each received step into its entry, so
  whichever fetch lands last wins, for every step.
- The push deep-link resolver stops paging through every section to find one step and calls
  this route instead.

## Frontend contract implications

- Architecture contracts affected:
  - `architecture/task_steps_worker_detail.md` (or the current worker step detail contract):
    the detail's data source becomes the per-step entry, not a list page.
- Local extension updates needed:
  - workers app `features/task_steps/api/` gains `fetch-task-step.ts` + the key; openers and
    both transition actions change as listed above.

## Clarifications required

- [ ] None blocking. If `is_reassigned` cannot be computed cheaply for one step, say so in the
      answer handoff and the frontend will keep its own reassigned flag from the list caches.
