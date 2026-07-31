# HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Owner agent: `claude-opus-5`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_reassigned_steps_endpoints_20260731.md`
- Source summary: pending (backend under construction)

> **STATUS: BUILD-AHEAD CONTRACT.** The backend for this surface has **not been implemented yet** —
> it is being built from the source plan in parallel with this frontend work. This document is the
> **authoritative API contract**: the backend implements to match it field-for-field; the frontend
> builds against it now.
>
> | Endpoint | Live? |
> |---|---|
> | `GET /api/v1/task-step-acknowledgments/reassigned-steps` (§3) | ⏳ **not live — mock this shape** |
> | `GET /api/v1/task-step-acknowledgments/reassigned-steps/count` (§4) | ⏳ **not live — mock this shape** |
> | `POST /api/v1/task-step-acknowledgments/acknowledge` (§9) | ✅ live today (pre-existing, unchanged) |
> | `POST /api/v1/task-step-acknowledgments/seen` (§9) | ✅ live today (pre-existing, unchanged) |
> | `GET /api/v1/worker-shifts/current` (§12, appendix — not part of this delivery) | ✅ live today, but see the §12.3 in-flight warning |
> | `POST /worker-shifts/declared-states` + `/close`, `GET /pause-reasons` (§12.5–12.7, appendix) | ✅ live today (pre-existing, unchanged) |
> | Removal of the `ended_shift` **task-step state** (§6.1) | ⏳ **not live — lands after these endpoints.** Build per §6.1's guidance, which covers both sides of the transition |
>
> Any contract change will be edited **here first**, then implemented. If the backend cannot match
> something in this document, that is an operator decision — not a silent implementer deviation.

## 1. What this is

A dedicated **"Reassigned to me"** page in the **worker app** (`app_scope="worker"`).

When a manager adds steps to a task a worker had already finished — a *reassignment* — the backend
writes one `TaskStepAcknowledgment` obligation row per newly added step, for **every active member
of that step's working section**. Today those rows are only surfaced through the acknowledgment
modal (`GET /pending`). This page gives them a permanent home: a list of every step reassigned into
one of the worker's sections that is still unfinished, grouped into per-working-section containers.

Model facts the UI should reflect:

- The obligation is created for **all section members**, not just the step's assigned worker. Several
  workers can see the same reassigned step.
- A step **leaves this list on its own** when it reaches a terminal state — no acknowledgment action
  required. Completing the work is what clears it.
- A step also leaves the list if the worker is **removed from the working section**. Visibility is
  re-checked against *current* membership on every request, not frozen at reassignment time.
- **Acknowledging does not remove the row** from this page (see §3.3). It only flips
  `acknowledged_at` and decrements the `unacknowledged` counter.
- `reason` is a free-text note the manager attached to the reassignment, snapshotted per row so it
  stays stable even if the source note is later edited. Truncate it through the existing notes system.

## 2. Auth

Both endpoints take a standard worker-app bearer token:

```
Authorization: Bearer <access_token>
```

- Allowed roles: **admin, manager, worker**.
- Both endpoints are scoped to **the calling user**, always. There is no `user_id` parameter and no
  way to read another worker's reassignments — an admin calling this sees their *own* obligations.
  This is a personal inbox, not an admin view.
- Workspace scoping is taken from the token claims.

## 3. `GET /api/v1/task-step-acknowledgments/reassigned-steps`

The paginated page content.

### 3.1 Query parameters

| Param | Type | Default | Constraints | Meaning |
|---|---|---|---|---|
| `limit` | int | `50` | `≤ 200` (else `422`) | page size |
| `offset` | int | `0` | `≥ 0` (else `422`) | page offset |
| `unacknowledged_only` | bool | `false` | — | when `true`, drops rows the worker already acknowledged |
| `q` | string | — | `max_length=200` (else `422`) | free-text search — see §3.5 |

### 3.2 What is returned

A step appears **only if all of these hold**:

1. a live acknowledgment row exists for (this workspace, this step, **the calling user**);
2. the caller has an **active** working-section membership for the step's working section;
3. the step's state is **not** terminal — i.e. not `completed`, `skipped`, `failed`, or `cancelled`;
4. the step, its task, and its working section are all live (not soft-deleted).

### 3.3 Acknowledged rows are included

Unlike `GET /pending` (which is unacknowledged-only, for the modal), this page returns **both
acknowledged and unacknowledged** rows, and exposes `first_seen_at` / `acknowledged_at` per item so
you can badge the unread ones. Pass `unacknowledged_only=true` if you want the narrower set.

### 3.4 Ordering

Newest reassignment first: `acknowledgment.created_at` descending, tie-broken by step id descending.

**A working section's steps can therefore span pages.** The order is chronological, not grouped by
section — see §7 for how to build the containers anyway.

### 3.5 `q` — free-text search

Case-insensitive **partial** match (SQL `ILIKE '%q%'`) against the primary item's
**`article_number`** or **`sku`**. A step matches if either column contains `q`.

```
GET /api/v1/task-step-acknowledgments/reassigned-steps?q=302.4
GET /api/v1/task-step-acknowledgments/reassigned-steps?q=sofa      → matches SKU "SOFA-3S-GREY"
```

Identical search behaviour to `GET /api/v1/working-sections/{id}/steps?q=…`, so a shared search
input component works on both surfaces.

Things to know:

- **Not searched:** working-section name, task type, worker name, upholstery name/code, the
  reassignment `reason`. On the section list, upholstery search is a separate opt-in flag; this
  endpoint has no such flag, so upholstery is never searched here.
- **`q` narrows within what you can already see.** It never widens the set — a step outside your
  sections, or already finished, stays invisible no matter what you type.
- **A step whose task has no primary item is dropped by any non-empty `q`** (there is nothing to
  match against). The same step *is* returned when `q` is absent. So an empty search result does
  not always mean "nothing matches" — it can mean the matching rows have no item.
- **`q` composes with `unacknowledged_only` and with pagination.** `has_more` reflects the
  *filtered* set, so pagination stays correct while searching.
- **Trim client-side and debounce.** Every keystroke is a full query; a `q` over 200 characters
  is a `422`.
- **`q` is not a parameter on the count endpoint** — see §4.

### 3.6 Response `200`

Every response is wrapped in the standard envelope `{ "data": …, "ok": true, "warnings": [] }`.
The example below shows one item with every key populated; `data` is the object you care about.

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "steps_pagination": {
      "items": [
        {
          "client_id": "tsp_9f3a1c",
          "task_id": "tsk_44b1de",
          "state": "pending",
          "readiness_status": "ready",
          "sequence_order": 3,
          "working_section_id": "wsec_upholstery",
          "assigned_worker_id": "usr_mykola",
          "total_dependencies": 2,
          "completed_dependencies": 2,
          "working_section_name_snapshot": "Upholstery",
          "assigned_worker_display_name_snapshot": "Mykola",
          "created_at": "2026-07-30T14:05:11.482913+00:00",
          "closed_at": null,
          "ready_by_at": "2026-08-02T12:00:00+00:00",
          "total_working_seconds": 0,
          "total_pause_seconds": 0,
          "total_ended_shift_seconds": 0,
          "total_working_count": 0,
          "total_pause_count": 0,
          "total_ended_shift_count": 0,
          "total_issues_count": 0,
          "total_issues_resolved_count": 0,
          "total_cost_minor": null,
          "recorded_time_marked_wrong": false,

          "updated_at": null,
          "created_by": {
            "client_id": "usr_manager",
            "username": "Sara",
            "profile_picture": "https://cdn.example.com/u/sara.jpg"
          },
          "updated_by": null,
          "last_state_record": {
            "state": "pending",
            "pause_reason": null,
            "description": null,
            "entered_at": "2026-07-30T14:05:11.482913+00:00",
            "exited_at": null,
            "last_action_by": {
              "client_id": "usr_manager",
              "username": "Sara",
              "profile_picture": "https://cdn.example.com/u/sara.jpg"
            },
            "first_started_at": "2026-07-30T14:05:11.482913+00:00"
          },
          "task": {
            "client_id": "tsk_44b1de",
            "task_type": "return",
            "priority": "high",
            "state": "working",
            "return_source": "after_purchase",
            "item_location": "store",
            "ready_by_at": "2026-08-02T12:00:00+00:00",
            "scheduled_start_at": null,
            "scheduled_end_at": null,
            "return_method": "pickup",
            "assortment": "SOFA-3S"
          },
          "item": {
            "client_id": "itm_77c2",
            "article_number": "302.445.11",
            "sku": "SOFA-3S-GREY",
            "state": "fixing",
            "item_category_id": "itc_sofa",
            "quantity": 1,
            "item_position": "A-12",
            "item_zone": "Warehouse North",
            "upholstery_requirement": [
              {
                "client_id": "iur_1a",
                "item_upholstery_id": "iup_5b",
                "upholstery_id": "uph_grey_linen",
                "state": "available",
                "source": "inventory",
                "amount_meters": 3.5
              }
            ]
          },
          "item_images": [
            {
              "client_id": "img_aa11",
              "image_url": "https://cdn.example.com/i/aa11.jpg",
              "storage_provider": "s3",
              "source_type": "upload",
              "source_reference": null,
              "width_px": 1600,
              "height_px": 1200,
              "file_size_bytes": 384210,
              "created_at": "2026-07-12T09:14:00+00:00",
              "last_event": {
                "client_id": "iev_9x",
                "event_type": "processed",
                "state": "succeeded",
                "created_at": "2026-07-12T09:14:30+00:00",
                "last_error": null
              },
              "events": [],
              "image_annotation": null
            },
            {
              "client_id": "img_bb22",
              "image_url": "https://cdn.example.com/i/bb22.jpg",
              "width_px": 1600,
              "height_px": 1200,
              "file_size_bytes": 291044
            }
          ],
          "cases_summary": { "total_unread": 2 },
          "dependency_working_sections": [
            {
              "working_section": {
                "client_id": "wsec_carpentry",
                "name": "Carpentry",
                "image": "https://cdn.example.com/ws/carpentry.png",
                "order_list": 1,
                "allows_batch_working": false,
                "allows_shopify_product_modifications": false
              },
              "prerequisite_step_state": "completed"
            }
          ],
          "is_reassigned": true,
          "upholstery_group_key": null,
          "upholstery_group_image_url": null,
          "upholstery_group_upholstery_id": null,
          "upholstery_group_inventory": null,

          "acknowledgment": {
            "client_id": "tsa_31f7",
            "step_id": "tsp_9f3a1c",
            "task_id": "tsk_44b1de",
            "reason": "Customer called — the left armrest seam needs redoing.",
            "worker": {
              "client_id": "usr_mykola",
              "username": "Mykola",
              "profile_picture": "https://cdn.example.com/u/mykola.jpg"
            },
            "created_by": {
              "client_id": "usr_manager",
              "username": "Sara",
              "profile_picture": "https://cdn.example.com/u/sara.jpg"
            },
            "first_seen_at": "2026-07-30T15:02:00+00:00",
            "acknowledged_at": null,
            "created_at": "2026-07-30T14:05:11.482913+00:00"
          }
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": false
    },
    "working_sections": {
      "wsec_upholstery": {
        "client_id": "wsec_upholstery",
        "name": "Upholstery",
        "image": "https://cdn.example.com/ws/upholstery.png",
        "order_list": 2,
        "allows_batch_working": true,
        "allows_shopify_product_modifications": false
      }
    }
  }
}
```

Empty result:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "steps_pagination": { "items": [], "limit": 50, "offset": 0, "has_more": false },
    "working_sections": {}
  }
}
```

## 4. `GET /api/v1/task-step-acknowledgments/reassigned-steps/count`

The badge endpoint. Deliberately light — one SQL statement, no entities loaded. Safe to poll.

**No query parameters at all** — no `limit`, no `offset`, and **no `q`**. It counts the whole
visible set.

`q` is deliberately absent: this drives a badge, and a badge that shrank because of whatever the
user last typed into a search box would be wrong. If you need "how many match my search", that is
the list endpoint's job — read it from the page you already fetched.

Response `200`:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "reassigned_steps_count": {
      "total": 7,
      "unacknowledged": 3
    }
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `total` | int | every visible reassigned step (§3.2 filters), acknowledged or not |
| `unacknowledged` | int | the subset with `acknowledgment.acknowledged_at === null` |

Guarantees:

- `total` **equals** the number of items you get by paging §3 to exhaustion with
  `unacknowledged_only=false` **and no `q`**, for the same user at the same moment. The two
  endpoints share one filter definition in the backend, so the badge can never disagree with the
  page. With `q` set the list is a subset and the count is not — that is intended, not a bug.
- `unacknowledged` equals the item count with `unacknowledged_only=true`.
- Both are `0`, never `null`, when nothing is visible.

## 5. Field reference

### 5.1 Step object (the item)

The step level is `serialize_step` — 22 keys — plus the enrichment keys below.

| Field | Type | Null? | Notes |
|---|---|---|---|
| `client_id` | string | no | step id, prefix `tsp_` |
| `task_id` | string | no | prefix `task_` |
| `state` | enum string | no | §6.1 — never a terminal value on this endpoint; **`ended_shift` is being removed, read §6.1** |
| `readiness_status` | enum string | no | §6.2 |
| `sequence_order` | int | **yes** | |
| `working_section_id` | string | no | key into `working_sections` |
| `assigned_worker_id` | string | **yes** | may differ from `acknowledgment.worker` |
| `total_dependencies` | int | no | ≥ 0 |
| `completed_dependencies` | int | no | ≤ `total_dependencies` |
| `working_section_name_snapshot` | string | **yes** | snapshot; prefer the live name from `working_sections` |
| `assigned_worker_display_name_snapshot` | string | **yes** | snapshot |
| `created_at` | ISO datetime | **yes** | |
| `closed_at` | ISO datetime | **yes** | `null` on this endpoint (non-terminal steps only) |
| `ready_by_at` | ISO datetime | **yes** | step-level deadline |
| `total_working_seconds` | int | no | |
| `total_pause_seconds` | int | no | |
| `total_ended_shift_seconds` | int | no | time the step sat idle because the shift ended. **Kept** — unaffected by the §6.1 state removal |
| `total_working_count` | int | no | |
| `total_pause_count` | int | no | |
| `total_ended_shift_count` | int | no | |
| `total_issues_count` | int | no | |
| `total_issues_resolved_count` | int | no | |
| `total_cost_minor` | int | **yes** | **minor currency units** (öre/cents), not major |
| `recorded_time_marked_wrong` | bool | no | |
| `updated_at` | ISO datetime | **yes** | |
| `created_by` | user object (§5.5) | **yes** | |
| `updated_by` | user object (§5.5) | **yes** | |
| `last_state_record` | object (§5.3) | **yes** | `null` if the step has no state record |
| `task` | object (§5.4) | **yes** | |
| `item` | object (§5.6) | **yes** | `null` when the task has no primary item |
| `item_images` | array (§5.7) | no | `[]` when none — **heterogeneous, read §5.7** |
| `cases_summary` | `{ total_unread: int }` | no | viewer-relative unread count for the task's cases |
| `dependency_working_sections` | array (§5.8) | no | `[]` when none |
| `is_reassigned` | bool | no | **always `true`** on this endpoint |
| `upholstery_group_key` | string | **yes** | **always `null`** here — see §5.9 |
| `upholstery_group_image_url` | string | **yes** | **always `null`** here |
| `upholstery_group_upholstery_id` | string | **yes** | **always `null`** here |
| `upholstery_group_inventory` | object | **yes** | **always `null`** here |
| `acknowledgment` | object (§5.2) | no | **the key this endpoint adds** |

### 5.2 `acknowledgment`

| Field | Type | Null? | Notes |
|---|---|---|---|
| `client_id` | string | no | ack row id, prefix `tsa_` |
| `step_id` | string | no | equals the item's `client_id` |
| `task_id` | string | no | equals the item's `task_id` |
| `reason` | string | **yes** | manager's free-text note, ≤ 1024 chars, snapshotted |
| `worker` | user object (§5.5) | **yes** | the worker who owes the ack — **this is always the calling user** on this endpoint |
| `created_by` | user object (§5.5) | **yes** | the manager who made the reassignment |
| `first_seen_at` | ISO datetime | **yes** | `null` = never rendered to the worker yet |
| `acknowledged_at` | ISO datetime | **yes** | `null` = not acknowledged |
| `created_at` | ISO datetime | no | when the reassignment happened — **the sort key** (§3.4) |

### 5.3 `last_state_record`

| Field | Type | Null? |
|---|---|---|
| `state` | enum string (§6.1) | no |
| `pause_reason` | object (§5.10) | **yes** |
| `description` | string | **yes** |
| `entered_at` | ISO datetime | **yes** |
| `exited_at` | ISO datetime | **yes** |
| `last_action_by` | user object (§5.5) | **yes** |
| `first_started_at` | ISO datetime | **yes** | earliest `entered_at` across *all* the step's records |

### 5.4 `task`

| Field | Type | Null? | Notes |
|---|---|---|---|
| `client_id` | string | no | |
| `task_type` | enum string | no | §6.3 |
| `priority` | enum string | no | §6.4 |
| `state` | enum string | no | §6.5 |
| `return_source` | enum string | **yes** | §6.6 |
| `item_location` | enum string | **yes** | §6.7 |
| `ready_by_at` | ISO datetime | **yes** | task-level deadline |
| `scheduled_start_at` | ISO datetime | **yes** | |
| `scheduled_end_at` | ISO datetime | **yes** | |
| `return_method` | enum string | **yes** | §6.8 |
| `assortment` | string | **yes** | free text, ≤ 255 |

### 5.5 User object (`serialize_user_working_section_member`)

Used for `created_by`, `updated_by`, `last_action_by`, `acknowledgment.worker`,
`acknowledgment.created_by`.

| Field | Type | Null? |
|---|---|---|
| `client_id` | string | no |
| `username` | string | no |
| `profile_picture` | string | **yes** |

### 5.6 `item`

| Field | Type | Null? | Notes |
|---|---|---|---|
| `client_id` | string | no | |
| `article_number` | string | **yes** | |
| `sku` | string | **yes** | |
| `state` | enum string | no | §6.9 |
| `item_category_id` | string | **yes** | |
| `quantity` | int | **yes** | |
| `item_position` | string | **yes** | |
| `item_zone` | string | **yes** | |
| `upholstery_requirement` | array | no | `[]` when none |

Each `upholstery_requirement[]` entry:

| Field | Type | Null? | Notes |
|---|---|---|---|
| `client_id` | string | no | |
| `item_upholstery_id` | string | no | |
| `upholstery_id` | string | **yes** | master upholstery id |
| `state` | enum string | no | §6.10 |
| `source` | enum string | no | §6.11 |
| `amount_meters` | number | **yes** | float, meters |

### 5.7 `item_images` — heterogeneous array, read this

**The first element has a different shape from the rest.** A naive shared type will break.

Element `[0]` (rich):

| Field | Type | Null? |
|---|---|---|
| `client_id` | string | no |
| `image_url` | string | no |
| `storage_provider` | string | **yes** |
| `source_type` | string | **yes** |
| `source_reference` | string | **yes** |
| `width_px` | int | **yes** |
| `height_px` | int | **yes** |
| `file_size_bytes` | int | **yes** |
| `created_at` | ISO datetime | no |
| `last_event` | `{client_id, event_type, state, created_at, last_error}` | **yes** |
| `events` | array | no | always `[]` on this endpoint |
| `image_annotation` | `{client_id, annotation_type, data, accuracy, created_at}` | **yes** | the *first* annotation only |

Elements `[1..]` (light) — **only** these five keys:
`client_id`, `image_url`, `width_px`, `height_px`, `file_size_bytes`.

Model it as a union, or type the array as the light shape and narrow index `0`.

`image_url` is directly usable: already-absolute URLs pass through; public item photos resolve to a
**stable unsigned URL** you may cache indefinitely; anything else is presigned with a **24 h TTL** —
don't persist those beyond a session.

### 5.8 `dependency_working_sections[]`

Ordered by the prerequisite section's `order_list` ascending (nulls last), then `client_id`.

| Field | Type | Notes |
|---|---|---|
| `working_section` | compact section object (§5.9) | the *prerequisite* section |
| `prerequisite_step_state` | enum string (§6.1) | that prerequisite step's current state |

### 5.9 Working section (compact) — and the `working_sections` map

`working_sections` is an **object keyed by working-section `client_id`**, not an array:

```ts
working_sections: Record<string, WorkingSectionCompact>
```

It contains **exactly the sections referenced by the current page's items** — a section with no step
on this page has no entry, because it has no container to render.

| Field | Type | Null? |
|---|---|---|
| `client_id` | string | no |
| `name` | string | no |
| `image` | string | **yes** |
| `order_list` | int | **yes** |
| `allows_batch_working` | bool | no |
| `allows_shopify_product_modifications` | bool | no |

The same shape appears nested inside `dependency_working_sections[].working_section`.

### 5.10 `pause_reason`

Appears inside `last_state_record` (§5.3). Non-null only when the step is paused.

> **⚠️ `client_id` here is not always a `par_…` catalog id.** A pause the *worker* chose
> references a catalog row. A pause the *system* caused (shift ended, another task took
> priority) references no catalog row — the backend fills this object from a code-owned
> vocabulary instead, so the field is never `null` and `name` always renders.
>
> | `client_id` | Origin | `image_url` | `slug` |
> |---|---|---|---|
> | `par_…` | workspace catalog row | usually set | the row's slug (may be `null` for workspace-created reasons) |
> | `shift_ended` | code-owned vocabulary | **set** — same icon the catalog row carried | `"pause_ended_shift"` |
> | `other_task_priority` | code-owned vocabulary | **set** | `"pause_other_task_priority"` |
> | `worker_declared_state` | code-owned vocabulary | `null` | `"worker_declared_state"` |
>
> **Never prefix-match `client_id`, and never use it to look up a row in a cached
> pause-reasons list** — the code-owned values have no catalog row to find. Render the embedded
> object's own `name` / `image_url` directly.
>
> Icons and labels are **not** degraded: the two system transitions reproduce the exact `name`
> and `image_url` their catalog rows carried, so a system pause renders exactly as it did
> before. Only `worker_declared_state` has no icon, and it never appears in a step payload.
>
> The object shape is **identical** in both cases — all 12 fields below, same types. Only the
> id's meaning widens. This is the same caveat as §12.3, which describes it for
> `GET /worker-shifts/current`; it applies here too.

| Field | Type | Null? |
|---|---|---|
| `client_id` | string | no |
| `name` | string | no |
| `image_url` | string | **yes** |
| `pause_type` | enum string | no |
| `description` | string | **yes** |
| `requires_description` | bool | no |
| `is_system_managed` | bool | no |
| `slug` | string | **yes** |
| `created_at` | ISO datetime | no |
| `created_by_id` | string | **yes** |
| `updated_at` | ISO datetime | **yes** |
| `updated_by_id` | string | **yes** |

## 6. Enum values

### 6.1 Step `state`

**Target vocabulary** (after the change described below):

`pending` · `working` · `paused` · `blocked` · `completed` · `skipped` · `failed` · `cancelled`

**On this endpoint the last four never appear** — a step in a terminal state has left the list.
Still model the full union: `prerequisite_step_state` (§5.8) uses the same enum and *can* be
terminal.

#### ⚠️ `ended_shift` is being removed from this enum — and it is still returned today

A backend change (`INTENTION_ended_shift_step_state_collapse_20260731`) removes **`ended_shift`
as a task-step state**. The reasoning: `ended_shift` is a *state that encodes a reason*. "The
worker ended their shift" is a fact about the **worker**, already recorded on their shift record —
it does not belong in the step's state vocabulary.

After it lands, a step stopped because the shift ended is simply **`paused`**, and *why* it
paused travels separately:

| Case | step `state` | how you tell |
|---|---|---|
| clock-out force-closed a working step | `paused` | system-typed reason on the state record |
| worker picked a reason in the pause sheet | `paused` | `pause_reason_id` — the reason they chose |
| auto-paused because another task took priority | `paused` | system-typed reason (unchanged today) |

**This is sequenced *after* the endpoints in this document.** So there is a window where these
endpoints are live and steps can still come back as `ended_shift`.

**How to build for that — do both:**

1. **Include `ended_shift` in the union you parse.** A strict Zod enum without it will fail
   validation on every response during the interim window. Keep it accepted.
2. **Do not branch on it.** No UI state, no icon, no filter, no sort keyed to `ended_shift`.
   Treat it exactly as you treat `paused`. When the change lands the value simply stops
   appearing, and correct code needs no edit.

The same applies to `prerequisite_step_state` (§5.8), which draws on the same enum.

**What does *not* change:** `total_ended_shift_seconds` and `total_ended_shift_count` (§5.1) keep
their names **and their meaning** — time a step sat idle because the shift ended. Only their
derivation changes, from the step's state to the state record's reason. Do not remove them from
your types; they are not affected by this.

### 6.2 Step `readiness_status`
`blocked` · `partial` · `ready`

### 6.3 `task.task_type`
`return` · `pre_order` · `internal`

### 6.4 `task.priority`
`low` · `normal` · `high` · `urgent`

### 6.5 `task.state`
`pending` · `assigned` · `working` · `stalled` · `ready` · `resolved` · `failed` · `cancelled`

### 6.6 `task.return_source`
`after_purchase` · `before_purchase` · `store_return` · `null`

### 6.7 `task.item_location`
`store` · `customer` · `null`

### 6.8 `task.return_method`
`drop_off_by_customer` · `pickup` · `null`

### 6.9 `item.state`
`pending` · `stalled` · `fixing` · `ready`

### 6.10 `upholstery_requirement[].state`
`missing_quantity` · `available` · `needs_ordering` · `ordered` · `in_use` · `completed` · `failed`

### 6.11 `upholstery_requirement[].source`
`inventory` · `surplus`

## 7. Building the containers

```
for each item in data.steps_pagination.items:
    section = data.working_sections[item.working_section_id]   // always present
group items by working_section_id
order the groups by section.order_list ASC (nulls last), then section.name ASC
within a group, keep the server order (newest reassignment first)
```

Two things to get right:

1. **`working_sections[item.working_section_id]` is guaranteed present** for every item on the page.
   You never need a fallback lookup — though `working_section_name_snapshot` exists on the step if
   you want a defensive one.
2. **Groups can span pages.** Ordering is chronological (§3.4), so page 2 may contain more steps for
   a section you already rendered on page 1. Merge into the existing container rather than creating a
   second one. If this proves awkward at scale, say so — switching the backend to section-first
   ordering is a one-line change, and it was a deliberate, reversible decision.

## 8. Realtime — when to refetch

**This feature adds no new socket events.** Drive the page and the badge off events that already
exist. Note the asymmetry: only the count going *up* has a targeted event.

| The list/count changes because… | Existing event | Kind |
|---|---|---|
| a new reassignment lands | `task:step-acknowledgment-created` — payload `{task_id, step_ids}` | **targeted**, per-worker |
| a step is removed, destroying the obligation | `task:step-acknowledgment-removed` | **targeted**, per-worker |
| the worker completes/skips/fails/cancels a reassigned step | `task:step-state-changed` | workspace **broadcast** — filter client-side |
| the worker is removed from a working section | *none acknowledgment-specific* | — |
| the worker acknowledges | *none* — you made the call | — |

Recommended: invalidate both queries on `task:step-acknowledgment-created`,
`task:step-acknowledgment-removed`, and `task:step-state-changed`. Treat the membership-change case
as a cold-start concern (refetch on app foreground / page mount), not a live one.

The two `task:step-acknowledgment-*` events were built for the existing `/pending` modal flow. They
fit this page, but it is a second consumer they were not designed for. If the badge proves laggy in
practice, tell backend — adding a targeted event on terminal transition is a known follow-up,
deliberately out of scope for this delivery.

A `task_steps_reopened` **push notification** also fires to the same audience on reassignment
(excluding the acting manager). Deep-link it to this page.

## 9. Acknowledging (existing endpoints, unchanged)

Neither is modified by this work.

```
POST /api/v1/task-step-acknowledgments/seen           { "step_ids": ["tsp_…", …] }   → sets first_seen_at
POST /api/v1/task-step-acknowledgments/acknowledge    { "step_ids": ["tsp_…", …] }   → sets acknowledged_at
```

After acknowledging, the row **stays** in this list (§3.3) with `acknowledged_at` set; only
`count.unacknowledged` drops. If you want it gone from view, use `unacknowledged_only=true`.

`GET /api/v1/task-step-acknowledgments/pending` also still exists and is unchanged — it is the
unacknowledged-only feed for the acknowledgment modal. Its items carry a **similar but not identical**
payload (no `dependency_working_sections`, no `is_reassigned`, no `upholstery_group_*`). Don't share a
type between the two surfaces.

## 10. Errors

**Two different error envelopes exist.** Auth and validation failures come from the framework and do
**not** carry `ok`:

| Status | Body | When |
|---|---|---|
| `401` | `{"detail": "Invalid or expired token."}` | missing / malformed / expired token |
| `401` | `{"detail": "Token has been revoked."}` | token blocklisted (logged out) |
| `403` | `{"detail": "Insufficient role permissions."}` | role outside admin/manager/worker |
| `422` | `{"detail": [ … FastAPI validation array … ]}` | `limit > 200`, `offset < 0`, non-integer values |

Domain errors would use `{"error": "…", "ok": false}` — but **neither endpoint raises one**. In
particular:

- **Neither endpoint ever returns `404`.** No visible reassignments is a `200` with an empty list /
  zero counts, not an error.
- No `403` for "not a member of any section" — that is simply an empty result.

Handle `401` by routing to sign-in; everything else on these two endpoints is a client bug.

## 11. Type reuse — the item is a superset of the section-list item

The step object in §3.5 is **exactly** the item shape already returned by
`GET /api/v1/working-sections/{working_section_id}/steps`, plus one added key `acknowledgment`.

So extend your existing type rather than redefining it:

```ts
type ReassignedStepItem = WorkingSectionStepItem & {
  acknowledgment: TaskStepAcknowledgment
}
```

This parity is a backend acceptance criterion, enforced by a characterization test — it will not
drift. The only caveats, both already noted: `is_reassigned` is always `true` here, and the four
`upholstery_group_*` keys are always `null` (this page has no grouping mode; the keys are kept so one
type serves both surfaces).

## 12. Appendix — worker shift state (pre-existing endpoints)

Included by request because the worker app needs these alongside this page: reading a worker's
current shift state (§12.1–12.3) and changing it with a reason (§12.4–12.7). **None of it is part
of this delivery** — all of it is live today and unchanged by this work.

> **Canonical reference: §4, §6 and §7 of
> `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`.** That document owns these
> endpoints' contracts. What follows is the **worker-app view**, which that handoff covers only
> in passing because it was written for the kiosk. Where the two disagree on a request or
> response body, the floor handoff wins — and tell backend, because they shouldn't disagree.

### 12.1 The access rule — read this before wiring it

```
GET /api/v1/worker-shifts/current            → self (worker-role tokens only)
GET /api/v1/worker-shifts/current?user_id=…  → that worker (admin/manager tokens only)
```

Roles accepted by the route: admin, manager, worker. But the service applies a stricter,
**mutually exclusive** rule:

| Caller's `role_name` | `user_id` omitted | `user_id` = another worker |
|---|---|---|
| `worker` | ✅ returns own state | ❌ `403` `"Workers may only manage their own shift."` |
| `manager` / `admin` | ❌ `403` `"Managers and admins must select a worker."` | ✅ returns that worker's state |

**The trap:** the worker app's sign-in scope (`app_scope="worker"`) admits **both `worker` and
`manager` roles**. So a manager signed into the worker app who calls this with no `user_id`
gets a `403`, not their own state — there is no "self" for a manager here, because shift state
only exists for worker-role users.

Handle it: branch on the `role_name` claim from sign-in. For a manager-role session, either skip
this call entirely or pass an explicit `user_id`. Don't treat the `403` as an auth failure and
bounce to sign-in.

Also: the target must be an **active workspace member with the worker role**, or you get
`404` `"Worker not found in this workspace."`

Both are domain errors, so they use the `{"error": …, "ok": false}` envelope — **not** the
`{"detail": …}` shape from §10.

### 12.2 Response `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "user_id": "usr_mykola",
    "clocked_in": true,
    "shift_started_at": "2026-07-31T06:58:00+00:00",
    "state": "in_pause",
    "state_entered_at": "2026-07-31T09:12:00+00:00",
    "pause_reason": { "id": "par_lunch", "name": "Lunch break", "image_url": "https://…" },
    "declared_state": {
      "id": "uds_7c1",
      "pause_reason": { "id": "par_lunch", "name": "Lunch break", "image_url": "https://…" },
      "description": null,
      "entered_at": "2026-07-31T09:12:00+00:00"
    }
  }
}
```

Not clocked in — every field flattens to `null`:

```json
{
  "user_id": "usr_mykola",
  "clocked_in": false,
  "shift_started_at": null,
  "state": null,
  "state_entered_at": null,
  "pause_reason": null,
  "declared_state": null
}
```

| Field | Type | Null? | Notes |
|---|---|---|---|
| `user_id` | string | no | the resolved target, echoed back |
| `clocked_in` | bool | no | |
| `shift_started_at` | ISO datetime | **yes** | latest `started_shift` marker |
| `state` | enum string | **yes** | `idle` · `working` · `in_pause` while clocked in; `null` otherwise |
| `state_entered_at` | ISO datetime | **yes** | |
| `pause_reason` | `{id, name, image_url}` | **yes** | non-null only when `state === "in_pause"` — **see §12.3** |
| `declared_state` | object | **yes** | non-null only when the pause is a *worker declaration* |
| `reason_text` | string | **yes** | **conditionally absent** — see below |

`declared_state`: `{ id, pause_reason: {id, name, image_url}, description, entered_at }`.
`pause_reason` non-null with `declared_state` null = a system/task-step pause, not something the
worker chose.

**`reason_text` has three-way variance** — the key may be **absent entirely** (the normal case),
a **string** (legacy free-text pause; `pause_reason` is `null`, render the text), or **`null`**
(the pause points at a catalog reason that can't be resolved; render a neutral "paused, reason
unavailable"). Model it as `reason_text?: string | null` and handle all three.

Timestamps are UTC ISO-8601 serialized with a `+00:00` offset, not `Z`. Parse with a real
ISO-8601 parser; don't string-match the suffix.

### 12.3 ⚠️ `pause_reason.id` is changing — don't assume a `par_` prefix

A backend capability (`system_transition_reasons`) is **in flight in this repo right now** and
changes what `pause_reason.id` can contain. The three-field *shape* is deliberately preserved,
so this is not a breaking change — but the **meaning of `id` widens**:

| `pause_reason.id` | Origin | `image_url` |
|---|---|---|
| `par_…` | a workspace catalog row (today's only case) | usually set |
| `shift_ended` | code-owned transition vocabulary | **set** — reproduces the catalog row's icon |
| `other_task_priority` | code-owned transition vocabulary | **set** |
| `worker_declared_state` | code-owned transition vocabulary | `null` |

One consequence for the frontend:

- **Never parse or prefix-match `pause_reason.id`**, and never use it to look up a row in a
  cached pause-reasons list — the transition values have no catalog row. Render the embedded
  `name` and `image_url` directly; `name` is always populated.

Rendering is **not** degraded: `name` and `image_url` reproduce byte-for-byte what the catalog
rows these transitions replace carried, so a system pause looks exactly as it does today. Only
`worker_declared_state` has no icon — and it only surfaces when a declaration's own catalog
reason cannot be resolved, which is an edge case, not the normal declared-state path (a
declaration carries the worker's chosen reason and that wins).

This is uncommitted work as of 2026-07-31 — confirm current behavior against the backend before
shipping anything that depends on it.

### 12.4 Changing a worker's state — there is no "set state" endpoint

`state` is **not directly settable**. `idle` and `working` are *derived* from task-step activity
by the backend's reconciliation, so the frontend cannot assign them:

| Want the worker in… | How |
|---|---|
| `working` | start/resume a task step (the task-step endpoints) — the shift state follows |
| `idle` | stop/finish their steps, or close an open declaration |
| `in_pause` **with a reason** | **declare a state** — §12.5 |
| clocked out | `POST /worker-shifts/clock-out` (or `/clock` to toggle) |

So "record a state change with a pause reason" = **declare a state**. That is the one worker-facing
write that attaches a reason to shift state.

Canonical reference for these: **§6 and §7 of the floor-app handoff.** The rules below are the same
ones; repeated here only because they're the answer to "how do I change state", with the worker-app
role caveat added.

**The §12.1 role rule applies to every write below too** — the access check is literally the same
function. A worker-role token omits `user_id`; a manager/admin token must pass it.

### 12.5 Declaring a state

**Step 1 — load the picker.** Only `personal` reasons are declarable:

```
GET /api/v1/pause-reasons?pause_type=personal&limit=200
```

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "pause_reasons": [
      {
        "client_id": "par_lunch",
        "name": "Lunch break",
        "image_url": "https://…",
        "pause_type": "personal",
        "description": "…",
        "requires_description": false,
        "is_system_managed": false,
        "slug": "lunch-break",
        "created_at": "…", "created_by_id": "usr_…", "updated_at": null, "updated_by_id": null
      }
    ],
    "pause_reasons_pagination": { "has_more": false, "limit": 200, "offset": 0 }
  }
}
```

Paginated — pass a large `limit` or follow `has_more`; workspace catalogs are small. Note
`requires_description`: it drives step 2.

**Step 2 — declare.**

```
POST /api/v1/worker-shifts/declared-states
```

| Body field | Type | Required | Notes |
|---|---|---|---|
| `pause_reason_id` | string | **yes** | a `personal` reason's `client_id` |
| `description` | string | conditional | **required** when the reason has `requires_description: true`; trimmed, ≤ 512 chars; blank → `null` |
| `user_id` | string | role-dependent | omit for worker tokens; **required** for manager/admin (§12.1) |

```json
{ "pause_reason_id": "par_lunch", "description": null }
```

→ `200` `data`:

```json
{
  "declared_state": {
    "id": "uds_7c1",
    "pause_reason": { "id": "par_lunch", "name": "Lunch break", "image_url": "https://…" },
    "description": null,
    "entered_at": "2026-07-31T09:12:00+00:00"
  },
  "shift_state": "in_pause",
  "paused_steps": 1
}
```

**Side effect worth surfacing in the UI:** declaring **auto-pauses every task step the worker
currently has in `working`**, under the declared reason. `paused_steps` is how many — show it
("1 task was paused"). `shift_state` is where the worker landed.

**Declaring while a declaration is already open is a *switch*** — the old one closes automatically.
Do **not** call close first; that would `409`. Note that switching does not re-label steps already
paused, so `paused_steps` counts only newly-paused ones (often `0` on a switch).

### 12.6 Closing a declared state

```
POST /api/v1/worker-shifts/declared-states/close
```

Body: `{}` for a worker token, `{ "user_id": "usr_…" }` for manager/admin.

→ `200` `data`: `{ "shift_state": "idle", "closed_declared_state_id": "uds_7c1" }`

- **Closing does not resume the auto-paused task steps.** The worker resumes those from the task
  UI. `shift_state` tells you where they actually landed — `idle`, or still `in_pause` if a
  step-blocker pause remains open.
- A declaration **also closes on its own** when the worker starts/resumes any task step, and at
  clock-out. So your cached view goes stale from actions elsewhere in the app — **re-render from
  `GET /current` after any of them** rather than trusting the last write's response.

**The four ways a declaration closes**, and what each stamps:

| Path | Synchronous? | `closed_by_id` |
|---|---|---|
| `POST /declared-states/close` | yes | the actor |
| declaring another state (a *switch*) | yes | the actor |
| the worker starts/resumes a task step | **no — see below** | `null` |
| clock-out | yes | the actor |

### 12.6.1 ⚠️ The start-a-step auto-close is asynchronous

Starting a task step does **not** close the declaration inside that request. The step-transition
command enqueues a `PROCESS_STEP_TRANSITION` job onto the analytics queue; a background worker
later runs the shift reconciliation, which is what actually closes the declaration and moves the
worker to `working`.

**There is therefore a lag window** in which the worker has started a step but `GET /current`
still returns `state: "in_pause"` with `declared_state` populated. The window is however long the
analytics queue takes — normally short, but not zero, and unbounded if that worker is backed up.

Design for it:

- **Don't** block the task UI on the shift state flipping, and don't read the start-step response
  as proof the declaration ended.
- **Do** render optimistically from the action the worker just took, and reconcile from
  `GET /current` on the next natural refresh.
- **Don't** poll `GET /current` in a tight loop waiting for the flip — treat a stale `in_pause`
  right after a step start as expected, not as an error state.

The precedence the backend applies once it does reconcile:

```
any open working step  → working    (outranks everything; closes an open declaration)
an open declaration    → in_pause
any open paused step   → in_pause
otherwise              → idle
```

### 12.7 Errors for the write path

All domain errors, so all use `{"error": …, "ok": false}` — not the §10 `{"detail": …}` shape.

| Status | Message | Cause |
|---|---|---|
| `409` | `"Worker must be clocked in to declare a state."` | not clocked in — offer clock-in |
| `409` | `"No declared state is open."` | close called with nothing open |
| `404` | `"Pause reason not found."` | unknown, deleted, or another workspace's reason |
| `404` | `"Worker not found in this workspace."` | target isn't an active worker-role member |
| `422` | `"Only personal pause reasons can be declared."` | a `blocker` reason was passed |
| `422` | `"Description is required for this pause reason."` | `requires_description` not honored |
| `422` | pydantic message | blank `pause_reason_id`, description > 512 chars |
| `403` | `"Managers and admins must select a worker."` | manager-role token with no `user_id` (§12.1) |
| `403` | `"Workers may only manage their own shift."` | worker token passing someone else's `user_id` |

Treat the `409`s as **normal flow**, not failures — they mean the screen was stale. Re-fetch
`GET /current` and re-render.

## 13. Suggested frontend validation

- Mock both endpoints from §3.5 / §4 and build against the mocks; flip to live when the table at the
  top of this document says ✅.
- Assert `count.total` matches the length of the fully-paged list — that agreement is a backend
  guarantee and a cheap regression canary.
- Exercise: empty state; a section with several steps; steps across ≥ 2 sections; a page boundary
  where one section spans both pages; an acknowledged row alongside unacknowledged ones; an item with
  `item: null`; an item with exactly one image (rich shape only, no light elements); `reason: null`.
- Search (§3.5): a partial mixed-case match; a match on `sku` but not `article_number`; a query
  matching nothing; `q` combined with pagination (check `has_more` reflects the filtered set); and
  confirm a step with `item: null` disappears under any non-empty `q` but returns when `q` is
  cleared.
- Parse a mocked response carrying `state: "ended_shift"` (§6.1) and confirm it validates and
  renders identically to `"paused"` — that is the interim window, and it is what will break first
  if the enum is modelled strictly.
- Confirm your image type handles the §5.7 first-element asymmetry.

## 14. Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_reassigned_steps_endpoints_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/making_endpoint_for_getting_reasign_tasks.md`
- Parent summary: pending — will be
  `backend/docs/architecture/implemented_summaries/SUMMARY_reassigned_steps_endpoints_20260731.md`
- Related surface: `GET /api/v1/working-sections/{id}/steps` (the item shape this reuses)
- **Canonical owner of the §12 appendix endpoint**:
  `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §4 —
  update that document, not this one, if `GET /worker-shifts/current` changes
- Source of the §12.3 warning: the in-flight `system_transition_reasons` capability —
  `backend/docs/architecture/under_construction/implementation/system_transition_reasons/`
- Source of the §6.1 `ended_shift` removal:
  `backend/docs/architecture/under_construction/intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
  — a successor set, planned after `system_transition_reasons` completes
