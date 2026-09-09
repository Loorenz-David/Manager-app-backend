# HANDOFF_TO_FRONTEND_task_list_sorting_20260909

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_list_sorting_20260909`
- Created at (UTC): `2026-09-09`
- Status: backend complete; frontend action required
- Scope: two new `order_by` strategies on `GET /api/v1/tasks` (`recently_completed`,
  `last_interacted`), one new task field (`completed_at`), one new list-row field
  (`last_interacted_at`)
- This is a new dated handoff. No published handoff was edited.

## 1. What is new, in one paragraph

`GET /api/v1/tasks` accepts two new `order_by` keys. `recently_completed` orders the tasks that
just finished, newest first. `last_interacted` orders by the most recent activity on a task's
steps, optionally narrowed to the working sections you are already filtering by. **No new query
parameter was added** — both strategies reuse `task_states` and `working_section_ids`, which the
endpoint already accepted. Two read-only fields were added to the response so you can render the
timestamps you are sorting by.

## 2. `order_by=recently_completed`

### Request

```
GET /api/v1/tasks?task_states=ready,resolved&order_by=recently_completed
```

Orders by `task.completed_at` descending, most recently completed first.

### The one rule you must implement

**You must send a `task_states` filter containing `ready` and/or `resolved`.** If you do not, the
backend cannot answer the question and silently falls back to its default ordering
(`ready_by_at asc nulls last`, then priority desc, then `created_at asc`). You will get `200` and a
correctly-formed page — just not the order you asked for.

The guard is case-insensitive and matches if **either** value is present, so all of these are
honored:

| `task_states` | `order_by=recently_completed` |
|---|---|
| `ready` | honored |
| `resolved` | honored |
| `ready,resolved` | honored |
| `READY` | honored |
| `working,ready` | honored (ready is present) |
| `working` | **falls back to default** |
| *(omitted)* | **falls back to default** |

This is deliberate: outside a completed cohort, every row's `completed_at` is `null`, the ordering
degenerates, and a silently meaningless page is worse than a documented fallback. Treat "user
picked Recently completed" in your UI as implying the state filter — do not offer the sort without
it.

### Direction

Defaults to **descending**. The key names an order, not a field, so no direction means newest
first. `?order_by=recently_completed:asc` is honored and gives oldest completion first. `NULLS
LAST` applies in both directions — a task with no completion is never the answer to "most recent".

## 3. `order_by=last_interacted`

### Request

```
GET /api/v1/tasks?working_section_ids=wsec_a,wsec_b&order_by=last_interacted
```

Orders by the newest step-state transition on the task, descending.

### Filter and sort are independent, as you specified

`working_section_ids` remains **exactly the filter it already was** and is unchanged by this work:
a task is included if any of its non-deleted steps belongs to one of the listed sections. What is
new is that `last_interacted` *also* narrows its timestamp to those same sections, so the ordering
answers the same question the visible list does. A task's activity in a section you are not looking
at cannot decide its position.

Sending `last_interacted` **without** `working_section_ids` is valid and needs no guard: the
timestamp is then "last interaction anywhere on this task". There is no state filter requirement
for this key.

### What counts as an interaction

The newest `entered_at` across the task's step state records, excluding:

- the `PENDING` record written when a step is created — otherwise every never-touched step would
  sort by its creation date and the strategy would collapse into `created_at`;
- records belonging to soft-deleted steps;
- records outside `working_section_ids` when you send that filter.

A task with no qualifying activity gets `null` and sorts last.

### One behavior worth knowing before you write the label

A step that is **actively being worked right now** sorts by when that work *started*, not by "now".
A task someone paused two minutes ago outranks a task someone has been working on for three hours.
This was a deliberate choice: the key means "when did something last happen on this task", not
"who is busy right now". Word the UI accordingly — "Last activity" reads true, "Currently active"
does not.

### Direction

Same rule as above: defaults to descending, `:asc` honored, `NULLS LAST` both ways.

## 4. New response fields

### `items[].task.completed_at`

- Type: ISO-8601 string or `null`. The key is **always present**.
- Meaning: the task's **current** completion. Set when the task enters `ready` or `resolved`.
  **Cleared back to `null` when the task is reopened to `working`** (which happens when a step is
  added to a ready task). So a non-null `completed_at` means "this task is completed right now",
  not "this task was completed at some point".
- Repeated completions overwrite: a task that goes ready → reopened → ready carries the **second**
  timestamp.

`completed_at` is **not** `closed_at`. Keep both straight:

| | `closed_at` | `completed_at` |
|---|---|---|
| `ready` | `null` | set |
| `resolved` | set | set (same instant) |
| `failed` / `cancelled` | set | `null`, or a stale earlier ready-stamp |
| reopened to `working` | unchanged | **cleared to `null`** |

Do not use `closed_at` to render "completed", and do not use `updated_at` — it is touched by every
unrelated write to the row.

### `items[].last_interacted_at`

- Type: ISO-8601 string or `null`. The key is **always present**.
- Sits on the **list row**, a sibling of `upholstery_group_key`, not inside the `task` object,
  because it is a computed aggregate rather than a task column.
- Computed under **exactly** the rules in §3, including the `working_section_ids` narrowing. The
  same request that orders by it shows the number it ordered by.

### Both fields are unconditional

They are present under **every** `order_by`, including the default, and whether or not you sent the
matching filter. Do not condition your parsing on the sort key.

### Response shape

```jsonc
{
  "data": {
    "tasks_pagination": {
      "items": [
        {
          "task": {
            "client_id": "tsk_01M1KFH8EFPFV85ZV3JDB2BB8X",
            "state": "ready",
            "closed_at": null,
            "completed_at": "2026-09-09T07:49:39.033224+00:00",  // new
            "...": "all existing task keys unchanged"
          },
          "primary_item": { "...": "unchanged" },
          "item_images": [],
          "upholstery_group_key": null,
          "upholstery_group_image_url": null,
          "upholstery_group_upholstery_id": null,
          "upholstery_group_inventory": null,
          "last_interacted_at": "2026-09-09T07:49:39.033224+00:00"  // new
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": true
    }
  },
  "ok": true,
  "warnings": []
}
```

## 5. `completed_at` also appears on five other surfaces

`completed_at` was added to the shared task serializer, so it now appears wherever a task object is
returned. This is purely additive — no existing key changed:

- `GET /api/v1/tasks` (list rows)
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/tasks/customer-coordination/threads`
- `GET /api/v1/upholstery-order-needs/{upholstery_id}/items`
- `GET /api/v1/upholstery-orders/items`
- `GET /api/v1/item-upholsteries/pending-seat-tasks`

Note the two upholstery entries are the **item** sub-routes. The bare
`GET /api/v1/upholstery-order-needs` and `GET /api/v1/upholstery-orders` list routes do not embed a
task object and are unaffected.

`last_interacted_at` is **only** on `GET /api/v1/tasks` list rows. Do not expect it elsewhere.

## 6. Pagination changed for the better — read this if you page

Every ordering now ends with `client_id asc` as a final tiebreaker, on this endpoint **and** on
`GET /api/v1/item-upholsteries/pending-seat-tasks`.

Previously, tasks that tied on the sort key came back in whatever order Postgres chose, which could
differ between two fetches — so page 2 could repeat a task from page 1 and drop another. Ties are
the norm for both new keys (a batch transition stamps one identical timestamp across many rows, and
`null` blocks are unbounded), so the tiebreaker is what makes offset pagination usable here.

This changes observed output only *within* ties, where the previous order was undefined. If you
have a snapshot test pinning the order of same-priority or same-`ready_by_at` tasks, it may need
re-baselining. Nothing else about `limit` / `offset` / `has_more` changed, and there is still no
total count.

## 7. Interaction with `group_by_upholstery`

`group_by_upholstery=true` still wins. It is a bucketing mode, not a sort: the group key is
prepended and your `order_by` orders rows *inside* each bucket. So
`group_by_upholstery=true&order_by=last_interacted` means "groups A→Z, newest first within each
group". Timestamps will **not** be monotonic down the page, and that is correct. If you need a
globally-ordered list, do not send `group_by_upholstery`.

## 8. Unknown and malformed `order_by` values

Unchanged, pre-existing behavior worth stating since you are now writing new keys: an unrecognized
field name is **silently dropped**, never a `422`. If every field in the list is unrecognized, the
default ordering applies. A typo therefore looks like "the sort did nothing". Comma-separated
composition still works — `?order_by=priority:desc,recently_completed` is valid, with the new key
as a secondary sort.

## 9. Historical data caveat for `recently_completed`

Before this change there was no stored timestamp for when a task became `ready`. The migration
backfilled it:

- `resolved` tasks: from `closed_at`, exact.
- `ready` tasks: reconstructed as the last terminal step's `closed_at` — accurate to the moment the
  work actually finished.
- Tasks force-readied with no steps at all: no source existed, so `completed_at` stays `null` and
  they sort last.

On the development dataset all 482 existing `ready` tasks were stamped and every other state was
left untouched. Expect a small tail of older `null`s in production; render them as "no completion
date", not as an error.

## 10. Frontend validation checklist

- Confirm `recently_completed` **with** `task_states=ready,resolved` returns non-increasing
  `completed_at`.
- Confirm `recently_completed` **without** `task_states` returns the same order as sending no
  `order_by` at all — and that your UI cannot reach that state.
- Confirm `recently_completed:asc` reverses it and still puts `null`s last.
- Confirm `last_interacted` scoped to one section shows different timestamps than the unscoped
  call for the same task.
- Confirm a task with steps but no activity shows `last_interacted_at: null` and sorts last.
- Confirm both new keys are present under the default ordering and on a task that has neither
  value.
- Confirm `completed_at` clears to `null` after a ready task is reopened by adding a step.
- Confirm paging twice through a tied cohort yields no duplicated and no missing task.

## Provenance

Backend implementation: `tasks.completed_at` column plus migration `ce99896e6f49`; the stamp at the
central READY evaluation in `_task_state_transitions.maybe_evaluate_task_ready` and in
`resolve_task`; the clear in `maybe_reopen_task_to_working`; the two sort keys in
`services/queries/tasks/tasks.py::_build_order_by`; the interaction aggregate in
`services/queries/utils/task_interaction.py`.

Owner decisions recorded at plan time: stamped column over a query-time proxy; pure
`max(entered_at)` with no active-work special case; unscoped `last_interacted` when no sections are
sent; both values exposed in the payload; and — decided after the plan review — clearing
`completed_at` on reopen rather than preserving it.
