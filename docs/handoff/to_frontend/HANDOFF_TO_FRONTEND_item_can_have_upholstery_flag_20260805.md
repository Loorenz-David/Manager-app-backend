# HANDOFF_TO_FRONTEND_item_can_have_upholstery_flag_20260805

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_can_have_upholstery_flag_20260805`
- Created at (UTC): `2026-08-05T00:00:00Z`
- Owner agent: `claude-sonnet-5`
- Model: `backend/app/beyo_manager/models/tables/items/item.py` → `Item.can_have_upholstery`
- Migration: `backend/app/migrations/versions/7758ea23764e_add_can_have_upholstery_to_items.py`

> **STATUS: additive, backward-compatible, ready to consume.** No existing request or response
> field was removed or renamed. Every affected field is optional with a server-side default, so
> **no frontend change is required to keep working as-is.** Read §6 anyway — one existing query
> your UI already calls has a real (currently invisible) behavior change baked in for the day you
> start setting the flag to `false`.

---

## 1. What this is for

Whether an item should carry upholstery has so far been inferred purely from its category:
`item_major_category_snapshot === "seat"`. That's too coarse — not every seat item actually needs
upholstery tracked (e.g. a seat item that's sold or repaired frame-only, with no fabric work
involved).

`can_have_upholstery` is a new per-item boolean (default `true`) that lets a specific item opt out
of upholstery tracking regardless of its category. It does **not** replace the seat-category check
— it narrows it. An item only counts as "needs upholstery" when it is **both** category `seat`
**and** `can_have_upholstery: true`.

---

## 2. Endpoints touched

**Important:** this codebase has **three independent, hand-written item serializers**, not one
shared item schema (see §4c for the third — the worker-facing step card, which does not carry this
field by design). Every response below is tagged with which one it goes through, because that
determines whether `can_have_upholstery` is actually present on the `item` object you receive.

| Endpoint | Change | Item shape |
|---|---|---|
| `PUT /api/v1/items` (create item) | New optional request field `can_have_upholstery` (default `true`) | — |
| `PATCH /api/v1/items/{client_id}` (update item) | New optional request field `can_have_upholstery` (omit = no change) | — |
| `POST /api/v1/items/find-or-create` | New optional request field `can_have_upholstery` (default `true`) | — |
| `PUT /api/v1/tasks` (create task) | New optional field `item.can_have_upholstery` on the embedded item payload (default `true`) | — |
| `GET /api/v1/items`, `GET /api/v1/items/{client_id}` | New response field `can_have_upholstery: boolean` | **Standalone** (§4a) |
| `GET /api/v1/tasks`, `GET /api/v1/tasks/{task_id}` | New response field on `item`/`primary_item`: `can_have_upholstery: boolean` | **Embedded** (§4b) |
| `GET /api/v1/tasks/customer-coordination/threads` | New response field on `primary_item`: `can_have_upholstery: boolean` | **Embedded** (§4b) |
| `GET /api/v1/item-upholsteries/pending-seat-tasks` (+ `/counts`) | New response field on `primary_item`; **also a query behavior change** — see §6 | **Embedded** (§4b) |
| Upholstery order / order-needs item listings (`/api/v1/upholstery-orders/items`, `/api/v1/upholstery-order-needs/{upholstery_id}/items`) | New response field on `primary_item`: `can_have_upholstery: boolean` | **Embedded** (§4b) |
| `GET /api/v1/working-sections/steps/user-last-active`, `GET /api/v1/working-sections/{id}/steps` | **No change, intentionally** — see §4c | **Worker-light** (§4c) |

§4a and §4b now both carry the field as of this handoff — see §4b for a note on where it was
initially missed. §4c does not carry it by design — see §4c.

No route paths, HTTP methods, roles, or error shapes changed. Nothing was removed.

---

## 3. Request shape

Add `can_have_upholstery` wherever you already send other item fields (`designer`,
`item_position`, `item_zone`, etc.) — same nesting level.

**Create item** (`PUT /api/v1/items`) and **find-or-create** (`POST /api/v1/items/find-or-create`):

```ts
{
  // ...existing fields (article_number, sku, item_category_id, quantity, ...)
  can_have_upholstery?: boolean   // optional, defaults to true server-side if omitted
}
```

**Update item** (`PATCH /api/v1/items/{client_id}`):

```ts
{
  // ...existing fields
  can_have_upholstery?: boolean   // optional; OMIT to leave unchanged, send explicit true/false to change it
}
```

This follows the same "omit vs. explicit" rule as every other field on this endpoint: the field
must be **absent from the JSON body**, not `null`, to be treated as "no change." Sending
`can_have_upholstery: null` will be rejected — the column is non-nullable, same as `quantity`.

**Create task** (`PUT /api/v1/tasks`), inside the nested `item` object:

```ts
{
  task_type: "...",
  item: {
    // ...existing item fields
    can_have_upholstery?: boolean   // optional, defaults to true
  },
  // ...
}
```

### Example — create a seat item that should NOT be tracked for upholstery

```json
{
  "article_number": "SEAT-4471",
  "item_category_id": "icg_seat_frame_only",
  "can_have_upholstery": false
}
```

---

## 4. Response shape

### 4a. Standalone item (`beyo_manager/domain/items/serializers.py::_serialize_item_base`)

Used by `GET /api/v1/items` and `GET /api/v1/items/{client_id}` (list and detail). Now includes:

```ts
{
  // ...existing fields
  can_have_upholstery: boolean   // always present, never null
}
```

### 4b. Embedded item (`beyo_manager/domain/tasks/serializers.py::serialize_item`)

A **separate, independently maintained** dict used wherever an item is embedded inside a task or
order payload — `item`/`primary_item` on task list/detail, coordination threads, the
pending-seat-tasks queue, and upholstery order/order-needs item listings (full list in §2). Field
set is similar but not identical to §4a (e.g. it carries `item_category_id` +
`item_category_snapshot` directly rather than a nested `item_category` object). Now also includes:

```ts
{
  // ...existing fields
  can_have_upholstery: boolean   // always present, never null
}
```

**This was initially missed** — the two serializers don't share code, so adding the column and
updating §4a alone left every embedded `item`/`primary_item` without the field. Caught and fixed
before this handoff went out; flagging it because it's the kind of split that will bite again the
next time either shape gains a field. If you're building shared frontend types for "an item," you
may want to know these two response shapes are not interchangeable today.

Both shapes are additive — existing consumers that don't read the field are unaffected. If your
item schemas are strict (`z.object(...)` without `.passthrough()`), add
`can_have_upholstery: z.boolean()` to **both** the standalone and embedded item schemas, or
responses will fail validation once the field appears.

### 4c. Worker-light item (`beyo_manager/domain/tasks/serializers.py::serialize_item_worker_light`) — deliberately NOT changed

There is a **third** item shape, used for the worker's active-step card:
`GET /api/v1/working-sections/steps/user-last-active` (`get_user_last_active_step_record_route`)
and `GET /api/v1/working-sections/{working_section_id}/steps` (`list_working_section_steps_route`).

Unlike §4a/§4b, this one is deliberately pared down to 8 fields (`client_id`, `article_number`,
`sku`, `state`, `item_category_id`, `quantity`, `item_position`, `item_zone`,
`upholstery_requirement`) — it excludes `designer`, dimensions, external refs, and even
`item_category_snapshot`/`item_major_category_snapshot`, the field the seat/upholstery logic is
keyed on. Since this payload doesn't reason about seat/upholstery eligibility at all today (only
about `upholstery_requirement` rows that already exist), `can_have_upholstery` was **intentionally
left out** here — do not add it without a product reason, and if a worker-facing "does this item
need upholstery" indicator is ever built, this is the file to revisit.

---

## 5. No new error cases

No new `4xx` responses were introduced. The only new failure mode is the existing generic `422`
validation error if you send `can_have_upholstery` as a non-boolean (e.g. a string) — same
handling as any other malformed field on these endpoints.

---

## 6. Behavior change: `pending-seat-tasks` queue now respects the flag

`GET /api/v1/item-upholsteries/pending-seat-tasks` and its
`GET /api/v1/item-upholsteries/pending-seat-tasks/counts` sibling power the "seat tasks pending
upholstery" queue. Both used to select purely on category (`item_major_category_snapshot ===
"seat"`). They now **also** require `can_have_upholstery === true` on the primary item.

**Nothing changes for you today** — every existing item has `can_have_upholstery: true` (the
migration backfilled it), so the query returns exactly what it did before. The moment your UI
(or anyone) creates/updates an item with `can_have_upholstery: false`, that item's task
**disappears from this queue and from both counts**, even though it's still category `seat`.

**What this means in practice:** once you start exposing the flag in the item form, a manager
flipping "does this item need upholstery?" off on a seat item will make its task vanish from the
pending-upholstery list on the next fetch/realtime refresh of that screen. That's the intended
effect — just don't be surprised by it, and make sure any "why did this task disappear from my
queue" support question maps back to this flag.

No new query parameters were added to these two endpoints for this — the filter is unconditional,
the same way the seat-category filter itself is (there's no `include_non_seat` toggle either).

---

## 7. Suggested frontend validation

1. Create an item with `can_have_upholstery` omitted → response shows `can_have_upholstery: true`.
2. Create an item with `can_have_upholstery: false` → response shows `false`; it does **not**
   appear in the "pending upholstery" queue even if its category is `seat` and it has no
   upholstery selected yet.
3. Update an existing seat item to `can_have_upholstery: false` while it's currently showing in
   the pending-upholstery queue → refetch the queue, confirm the row is gone and the counts drop.
4. Omit the field entirely on a `PATCH` → confirm the item's existing `can_have_upholstery` value
   is untouched (not reset to `true`).
5. Create a task with an embedded new item and `item.can_have_upholstery: false` → the created
   item reflects that value.
6. Fetch `GET /api/v1/tasks/{task_id}` and `GET /api/v1/item-upholsteries/pending-seat-tasks` for
   the same item → confirm `can_have_upholstery` is present and matches on **both** (§4a vs §4b
   are different code paths; don't assume passing one test covers the other).

---

## 8. Trace links

- Model: `backend/app/beyo_manager/models/tables/items/item.py`
- Migration: `backend/app/migrations/versions/7758ea23764e_add_can_have_upholstery_to_items.py`
- Item create: `backend/app/beyo_manager/services/commands/items/create_item.py`,
  `_create_item_in_session.py`
- Item update: `backend/app/beyo_manager/services/commands/items/update_item.py`
- Find-or-create: `backend/app/beyo_manager/services/commands/items/find_or_create_item.py`
- Task create: `backend/app/beyo_manager/services/commands/tasks/create_task.py`
- Standalone item serializer (§4a): `backend/app/beyo_manager/domain/items/serializers.py` → `_serialize_item_base`
- Embedded item serializer (§4b): `backend/app/beyo_manager/domain/tasks/serializers.py` → `serialize_item`
- Worker-light item serializer (§4c, unchanged): `backend/app/beyo_manager/domain/tasks/serializers.py`
  → `serialize_item_worker_light`, consumed by
  `backend/app/beyo_manager/services/queries/working_sections/step_record_payload.py` and
  `backend/app/beyo_manager/services/queries/working_sections/steps_list_payload.py`
- Pending-upholstery query: `backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py`
  → `_can_have_upholstery_match`
- Routes: `backend/app/beyo_manager/routers/api_v1/items.py`,
  `backend/app/beyo_manager/routers/api_v1/tasks.py`,
  `backend/app/beyo_manager/routers/api_v1/working_sections.py`,
  `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`
