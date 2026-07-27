# HANDOFF_TO_FRONTEND_upholstery_grouping_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_upholstery_grouping_20260718`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Owner agent: `claude`
- Source plan: n/a (direct implementation request)
- Source summary: n/a

## Backend delivery context

- What backend implemented: an opt-in `group_by_upholstery` query param on the two list endpoints below. When enabled, the server re-orders the flat paginated list so rows sharing the same upholstery sit contiguously, and each row carries the group's display label, fabric image, master upholstery id, and current inventory amounts. The existing priority ordering is preserved **within** each group.
- API or contract changes: new optional query param + four new response fields per item (additive, backward compatible — omitting the param keeps today's ordering exactly).
- Feature flags/toggles: none. Behavior is controlled entirely by the query param.

## Frontend action required

1. Where the upholstery-grouped view is wanted, send `group_by_upholstery=true` and render section headers from `upholstery_group_key` / `upholstery_group_image_url` (see rendering recipe below).
2. Keep pagination logic unchanged (`limit` / `offset` / `has_more`); verify that loading page N+1 continues an in-progress group under the same header instead of starting a new one.

## Interface details

### Endpoints

Both endpoints accept the same new param:

| Endpoint | New param |
|---|---|
| `GET /api/v1/working-sections/{working_section_id}/steps` | `group_by_upholstery` (bool, default `false`) |
| `GET /api/v1/tasks` | `group_by_upholstery` (bool, default `false`) |

It composes with every existing filter and param. On `GET /tasks` it also composes with `order_by`: grouping is applied first, then the requested `order_by` sorts rows **inside** each group.

### Request examples

```
GET /api/v1/working-sections/wse_123/steps?group_by_upholstery=true&limit=50&offset=0
GET /api/v1/tasks?group_by_upholstery=true&task_states=in_progress&order_by=priority:desc
```

### Response shape

The envelope is unchanged (`steps_pagination` / `tasks_pagination` with `items`, `limit`, `offset`, `has_more`). Every element of `items` gains four fields:

```jsonc
// GET /working-sections/{id}/steps — each entry in steps_pagination.items
{
  // ...all existing step fields (task, item, item_images, last_state_record, ...)
  "is_reassigned": false,
  "upholstery_group_key": "Leather Cognac",          // string | null
  "upholstery_group_image_url": "https://…/x.jpg",   // string | null
  "upholstery_group_upholstery_id": "uph_abc123",    // string | null
  "upholstery_group_inventory": {                    // object | null
    "client_id": "uin_def456",
    "upholstery_id": "uph_abc123",
    "inventory_condition": "available",              // available | low_stock | out_of_stock
    "current_stored_amount_meters": "42.500",        // string | null (decimal as string)
    "current_amount_in_use_meters": "6.000",         // string | null
    "current_amount_in_need_meters": "0.000",        // string | null
    "current_amount_ordered_meters": "15.000"        // string | null
  }
}
```

```jsonc
// GET /tasks — each entry in tasks_pagination.items
{
  "task": { /* unchanged */ },
  "primary_item": { /* unchanged */ },
  "item_images": [ /* unchanged */ ],
  "upholstery_group_key": "Leather Cognac",          // string | null
  "upholstery_group_image_url": "https://…/x.jpg",   // string | null
  "upholstery_group_upholstery_id": "uph_abc123",    // string | null
  "upholstery_group_inventory": { /* same shape as above */ }  // object | null
}
```

Field semantics:

- `upholstery_group_key` — the group's display label: the representative upholstery's name, falling back to its code (item-level value first, then the master upholstery record's). This is the exact value the server sorted on, so it is safe to group on it verbatim.
- `upholstery_group_image_url` — the same representative upholstery's fabric image from the master upholstery record. May be `null` even when the key is set (master record missing or has no image).
- `upholstery_group_upholstery_id` — the representative's **master** upholstery `client_id`. This is the stable identity of the group: use it for navigation/links and as the grouping equality check if you prefer id over label. `null` when the item-level upholstery is not linked to a master record (the key may still be set from item-level name/code).
- `upholstery_group_inventory` — the current inventory amounts for that master upholstery (one inventory record per upholstery). `null` when there is no master id or no inventory record. All `*_meters` values are **decimals serialized as strings** (same convention as the upholstery inventory endpoints) — parse before doing math. `inventory_condition` is `available` / `low_stock` / `out_of_stock`.
- Note: since all rows in a group share the same representative upholstery, the id/image/inventory values repeat on every row of the group — read them off the first row when rendering a group header.
- If the row's primary item has several upholsteries, the representative is the alphabetically-first one; the row appears in that group only (rows are never duplicated across groups — pagination counts stay exact).
- `upholstery_group_key: null` means the primary item has **no upholstery**. These rows always sort **last**, as a trailing "No upholstery" bucket.
- When `group_by_upholstery` is omitted or `false`, all four fields are present but always `null`. Do not interpret that as "no upholstery" — only trust the fields when you sent the param.

### Ordering guarantees

- Groups are ordered alphabetically by key (server collation), `null` last.
- Within a group, the existing order is untouched:
  - steps endpoint: reassigned-to-viewer steps first, then `ready_by_at` asc (nulls last), then `client_id` desc. Note: a reassigned step floats to the top of **its own group**, not above all groups.
  - tasks endpoint: the default sort (`ready_by_at` asc nulls last, priority desc, `created_at` asc) or whatever `order_by` you passed.

### Rendering recipe

The response is a flat list, not a nested structure — pagination is unchanged on purpose. To render sections, iterate the page in order and emit a header whenever the key changes:

```ts
let currentKey: string | null | undefined = lastKeyFromPreviousPage; // undefined on first page
for (const row of items) {
  if (row.upholstery_group_key !== currentKey) {
    currentKey = row.upholstery_group_key;
    renderHeader(currentKey ?? "No upholstery", row.upholstery_group_image_url);
  }
  renderRow(row);
}
```

Carry `currentKey` across pages: if page N+1 starts with the same key page N ended with, do not emit a new header. Compare keys by exact string equality.

### Error cases

No new error cases. An invalid value for the param (anything not parseable as bool) is rejected by FastAPI with the standard `422`.

## Validation notes

- Backend validation run: modules compile; both statements rendered to PostgreSQL SQL offline with assertions that the three grouping subqueries correlate on the correct column (`task_steps.task_id` / `tasks.client_id`), select `upholsteries.image_url`, and use the deterministic order-by-limit-1 representative; the inventory batch query compiles. Not yet exercised against a live database.
- Suggested frontend validation: with a workspace containing items on ≥2 upholsteries plus one item with none — (1) request page size smaller than a group and confirm the group continues across pages without a duplicate header; (2) confirm the "No upholstery" bucket renders last; (3) toggle the param off and confirm both fields come back `null` while ordering returns to the previous behavior.

## Trace links

- Parent plan: n/a
- Parent summary: n/a
- Backend files: `backend/app/beyo_manager/routers/api_v1/working_sections.py`, `backend/app/beyo_manager/routers/api_v1/tasks.py`, `backend/app/beyo_manager/services/queries/working_sections/list_working_section_steps.py`, `backend/app/beyo_manager/services/queries/tasks/tasks.py`, `backend/app/beyo_manager/services/queries/utils/upholstery_grouping.py`
