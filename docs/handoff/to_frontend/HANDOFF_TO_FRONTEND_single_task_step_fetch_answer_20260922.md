# HANDOFF_TO_FRONTEND_single_task_step_fetch_answer_20260922

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_single_task_step_fetch_answer_20260922`
- Created at (UTC): `2026-09-22T20:30:00Z`
- Owner agent: `Claude Opus 5` (backend)
- Answers: `HANDOFF_TO_BACKEND_single_task_step_fetch_20260922`
- Source plan: none — single endpoint, delivered directly against the request handoff
- Source summary: none

## Backend delivery context

- What backend implemented: `GET /api/v1/working-sections/steps/{step_id}`, returning one step
  in the worker step-card shape. Shipped, tested, lint-clean.
- API or contract changes: one new read route. No existing route, payload or socket event
  changed.
- Feature flags/toggles: none.

## Frontend action required

1. Point `taskStepKeys.step(stepId)` at `GET /api/v1/working-sections/steps/{step_id}` and read
   `data.step`. It validates against `WorkingSectionStepItemSchema` unchanged — see the parity
   result below.
2. Read the one deliberate divergence in **Interface details → `upholstery_group_*`** before
   wiring the openers. It is in your favour, but it is a difference from an *ungrouped* list page
   and you should know which way it goes.

## Interface details

- Endpoint: `GET /api/v1/working-sections/steps/{step_id}`
- Roles: `ADMIN`, `MANAGER`, `WORKER` — identical to `GET /working-sections/{id}/steps`.
- Request shape: path parameter only. No query parameters, as requested.
- Response shape:

```json
{
  "data": { "step": { /* WorkingSectionStepItem */ } },
  "ok": true,
  "warnings": []
}
```

- Error cases:
  - `404` — unknown step id, deleted step, step on a deleted task, step in another workspace,
    or a blank id. All five render the same body, deliberately, and carry no error identity:
    `{"error": "Step not found.", "ok": false}`.
  - `401` / `403` — as the section list route (`require_roles([ADMIN, MANAGER, WORKER])`).
- Socket events: none added, as requested.

### Parity check result — the answer to your "please verify"

**Your reading of the mechanism was right about the two functions, and right to ask.** We did
*not* build the route from `build_step_record_payload`, because it does not reach parity. Measured
against a section-list item for the same seeded step, that payload is missing exactly six keys and
carries no extras:

```
dependency_working_sections
is_reassigned
upholstery_group_key
upholstery_group_image_url
upholstery_group_upholstery_id
upholstery_group_inventory
```

All six are required by `WorkingSectionStepItemSchema`, so the two-call route you sketched would
have failed your Zod parse and shown the error state — the exact failure you flagged as the risk.
(`load_step_with_latest_record` *is* used, for the visibility check and to reach `task_id`.)

The route instead calls **`build_steps_list_payload` with a one-element page**, which is the same
builder `GET /working-sections/{id}/steps` and `GET /task-step-acknowledgments/reassigned` already
use. There is one payload builder for the step card, not two, so the shapes cannot drift apart
later. An integration test asserts the *whole dict* — not its key set — equal to the list item for
the same step, parametrized over `worker` / `manager` / `admin` so the monetary-field role gate
travels with it.

### `is_reassigned` — computed, no fallback needed

Your clarification item can be closed: it is computed cheaply for a single step, and on the same
shared predicate the section list and the reassigned list use
(`reassigned_steps_where_clauses`) — a live, non-deleted acknowledgment obligation for the
*calling* worker, on a step in a non-terminal state. It is viewer-relative, exactly as in the
list: two workers fetching the same step can legitimately see different values. Drop your local
reassigned-flag fallback if you want to; nothing needs it.

### `upholstery_group_*` — resolved unconditionally (the one divergence)

The four group fields are resolved on **every** call to this route, even though the route takes no
`group_by_upholstery` parameter.

- vs a **grouped** list page (`group_by_upholstery=true`): identical, same values.
- vs an **ungrouped** list page: that page sends all four as `null`; this route sends the real
  values.

The reason is your own plan: every fetch writes into one per-step cache entry and the last write
wins. A `null` from this route would *blank* a group image or inventory chip that a grouped list
page had legitimately seeded — a second freeze-class bug of the same family as the one you
reported. These three values are functions of the step's own primary item (the alphabetically
first upholstery on it), not of the page it was listed in, so resolving them is never wrong; a
step whose primary item has no upholstery still reports all four as `null`.

Practical consequence for you: **treat this route's group fields as authoritative and let them
overwrite**, and do not treat a `null` from an ungrouped list page as "this step has no group".

### Cases summary

`cases_summary.total_unread` is viewer-relative here too, counted against the caller — same as the
list. A manager fetching a worker's step sees their own unread count, not the worker's. This
matches the list route's existing behaviour exactly; it is not new.

### Visibility

The same rule as the list route, not a stricter one, as you asked: workspace scope, a live step on
a live task. **No working-section membership gate** — the section list route does not apply one, so
neither does this. A step you can see through the list today is a step you can fetch here.

## Validation notes

- Backend validation run: 12 new integration tests, all passing, plus the 94 existing tests in
  `tests/integration/services/queries/working_sections` and
  `tests/integration/services/queries/task_step_acknowledgments` (94 passed, 1 skipped — the skip
  is pre-existing). `ruff check` clean on all three touched files.
- Each load-bearing assertion was armed by mutating the implementation and confirming the test
  fails: dropping the group columns fails the parity test (4 tests), dropping the reassigned set
  fails the flag test, and loosening the reassigned predicate to ignore terminal states fails the
  terminal-step test.
- Suggested frontend validation: reproduce the original evidence — open the detail from the
  last-active card, tap Pause, confirm the button and clock update without a reopen; then repeat
  from page 2 of a section list, and once via a push deep link.

## Trace links

- Request handoff: `backend/docs/handoff/from_frontend/HANDOFF_TO_BACKEND_single_task_step_fetch_20260922.md`
- Route: `backend/app/beyo_manager/routers/api_v1/working_sections.py` (`get_task_step_route`)
- Query: `backend/app/beyo_manager/services/queries/working_sections/get_task_step.py`
- Tests: `backend/app/tests/integration/services/queries/working_sections/test_get_task_step_integration.py`
