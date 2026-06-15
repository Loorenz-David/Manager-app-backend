# HANDOFF_TO_FRONTEND_seat_tasks_pending_upholstery_20260615

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_seat_tasks_pending_upholstery_20260615`
- Created at (UTC): `2026-06-15T12:15:46Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_seat_tasks_pending_upholstery_20260615.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_seat_tasks_pending_upholstery_20260615.md`

## Backend delivery context

- What backend implemented:
  - Added a paginated list endpoint for seat tasks whose primary item is blocked on missing upholstery data.
  - Added a separate counts endpoint for lightweight badge/counter reads.
  - Both endpoints are read-only and scoped to the authenticated workspace.
- API or contract changes:
  - New endpoint: `GET /api/v1/item-upholsteries/pending-seat-tasks`
  - New endpoint: `GET /api/v1/item-upholsteries/pending-seat-tasks/counts`
  - Both endpoints return the standard backend response envelope: `{ "ok": true, "data": ..., "warnings": [] }`
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use `GET /api/v1/item-upholsteries/pending-seat-tasks` for the main list/table/card UI of seat tasks missing upholstery information.
2. Use `GET /api/v1/item-upholsteries/pending-seat-tasks/counts` independently for badges, tabs, or summary counters. It is not tied to the current list filter state.
3. Treat `missing_selection` and `missing_quantity` as optional boolean filters on the list endpoint:
   - `missing_selection=true`: only tasks whose primary seat item has no `ItemUpholstery` record.
   - `missing_quantity=true`: only tasks whose primary seat item has an upholstery record but `amount_meters` is `null` or `0`.
   - both `false` or both `true`: union of both buckets.
4. Render each list row/card from `tasks_pagination.items[]`, where each item contains:
   - `task`
   - `primary_item`
   - `pending_upholstery_reason`
   - `item_upholstery_id`
   - `item_images`
5. Expect `primary_item` to be nullable in defensive UI code, even though the query is built around primary seat items.
6. Use `pending_upholstery_reason` as the source of truth for badge text, grouping, or row styling:
   - `missing_selection`
   - `missing_quantity`
7. Use `item_upholstery_id` as the direct reference for edit/view flows when the reason is `missing_quantity`. When the reason is `missing_selection`, this field is `null`.

## Interface details

- Endpoint(s):
  - `GET /api/v1/item-upholsteries/pending-seat-tasks`
  - `GET /api/v1/item-upholsteries/pending-seat-tasks/counts`

- Auth and role access:
  - Allowed roles: `ADMIN`, `MANAGER`, `WORKER`
  - Other roles receive `403`

- Request shape for `GET /pending-seat-tasks`:
  - Query params:
    - `limit: number` optional, default `50`, max `200`
    - `offset: number` optional, default `0`
    - `q: string` optional, max length `200`
    - `missing_selection: boolean` optional, default `false`
    - `missing_quantity: boolean` optional, default `false`

- Query behavior notes:
  - `q` searches across task fields and related item/upholstery text fields:
    - task title
    - task additional details
    - task phone/email fields
    - item article number / sku / designer / position / category snapshots
    - upholstery name / code
  - The list only contains tasks whose active primary item is a seat item.
  - Seat matching is case-insensitive on `item_major_category_snapshot`.

- Response envelope for both endpoints:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- `GET /pending-seat-tasks` response shape:

```json
{
  "ok": true,
  "data": {
    "tasks_pagination": {
      "items": [
        {
          "task": {
            "client_id": "tsk_...",
            "task_scalar_id": 123,
            "task_type": "repair",
            "priority": "normal",
            "state": "pending",
            "title": "Dining chair repair",
            "summary": "Seat fabric missing",
            "return_source": null,
            "item_location": null,
            "return_method": null,
            "fulfillment_method": null,
            "additional_details": {},
            "ready_by_at": null,
            "scheduled_start_at": null,
            "scheduled_end_at": null,
            "customer_id": "cus_...",
            "primary_phone_number": null,
            "secondary_phone_number": null,
            "primary_email": null,
            "secondary_email": null,
            "address": null,
            "created_at": "2026-06-15T10:00:00+00:00",
            "updated_at": null,
            "closed_at": null,
            "is_deleted": false,
            "deleted_at": null
          },
          "primary_item": {
            "client_id": "itm_...",
            "article_number": "ART-123",
            "sku": "SKU-123",
            "state": "pending",
            "item_category_id": "icat_...",
            "quantity": 1,
            "designer": "Example Designer",
            "height_in_cm": null,
            "width_in_cm": null,
            "depth_in_cm": null,
            "item_value_minor": null,
            "item_cost_minor": null,
            "item_currency": null,
            "item_position": "seat",
            "external_id": null,
            "external_url": null,
            "external_source": null,
            "external_order_id": null,
            "item_category_snapshot": "chair",
            "item_major_category_snapshot": "seat"
          },
          "pending_upholstery_reason": "missing_selection",
          "item_upholstery_id": null,
          "item_images": [
            {
              "client_id": "img_...",
              "image_url": "https://...",
              "storage_provider": "s3",
              "source_type": "upload",
              "source_reference": null,
              "width_px": 1600,
              "height_px": 1200,
              "file_size_bytes": 245000,
              "created_at": "2026-06-15T09:00:00+00:00",
              "last_event": null,
              "events": [],
              "image_annotation": null
            },
            {
              "client_id": "img_...",
              "image_url": "https://...",
              "width_px": 1600,
              "height_px": 1200,
              "file_size_bytes": 201000
            }
          ]
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  },
  "warnings": []
}
```

- Notes on `pending_upholstery_reason`:
  - `missing_selection` means the primary seat item has no active `ItemUpholstery` record at all.
  - `missing_quantity` means the primary seat item has an active `ItemUpholstery` record, but its `amount_meters` is `null` or `0`.
  - Frontend should use this field directly instead of inferring the reason from `primary_item` or from the currently selected filter.

- Notes on `item_upholstery_id`:
  - This field is always present in the payload.
  - It is `null` when `pending_upholstery_reason = "missing_selection"`.
  - It contains the relevant `ItemUpholstery.client_id` when `pending_upholstery_reason = "missing_quantity"`.
  - Frontend can treat this as `string | null`.

- Notes on `item_images`:
  - First image is the full `serialize_image(...)` shape.
  - Remaining images use the lighter `serialize_image_light(...)` shape.
  - In UI terms, it is safe to read `client_id`, `image_url`, `width_px`, `height_px`, and `file_size_bytes` from every image object.
  - Only the first image is guaranteed to also include `storage_provider`, `source_type`, `source_reference`, `created_at`, `last_event`, `events`, and `image_annotation`.

- `GET /pending-seat-tasks/counts` response shape:

```json
{
  "ok": true,
  "data": {
    "missing_selection_total": 12,
    "missing_quantity_total": 7
  },
  "warnings": []
}
```

- Counts endpoint behavior notes:
  - No query params are used.
  - Counts are workspace-wide totals.
  - Counts are not affected by `q`, pagination, or the currently selected list filter in the UI.

- Suggested frontend usage examples:
  - List all pending seat tasks:
    - `GET /api/v1/item-upholsteries/pending-seat-tasks`
  - Only tasks missing upholstery selection:
    - `GET /api/v1/item-upholsteries/pending-seat-tasks?missing_selection=true`
  - Only tasks missing upholstery quantity:
    - `GET /api/v1/item-upholsteries/pending-seat-tasks?missing_quantity=true`
  - Search within pending seat tasks:
    - `GET /api/v1/item-upholsteries/pending-seat-tasks?q=chair`
  - Paginate:
    - `GET /api/v1/item-upholsteries/pending-seat-tasks?limit=20&offset=20`

- Error cases:
  - `401` if the user is not authenticated.
  - `403` if the authenticated role is not `ADMIN`, `MANAGER`, or `WORKER`.
  - `422` if query params are invalid, for example `limit > 200` or negative `offset`.

## Validation notes

- Backend validation run:
  - `python3 -m py_compile backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: passed.
- Suggested frontend validation:
  - Verify the counters load correctly from `/pending-seat-tasks/counts` before or independently of the list request.
  - Verify `missing_selection` and `missing_quantity` each produce the expected subset.
  - Verify enabling both filters behaves the same as the default combined view.
  - Verify UI handles empty states when `tasks_pagination.items` is an empty array.
  - Verify image rendering handles the mixed full/light image object shapes safely.

## Trace links

- Parent plan:
  - `backend/docs/architecture/archives/implementation/PLAN_seat_tasks_pending_upholstery_20260615.md`
- Parent summary:
  - `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_seat_tasks_pending_upholstery_20260615.md`
- Related debug plan (optional):
  - `N/A`
