# HANDOFF_TO_FRONTEND_tasks_list_query_and_response_shape_20260523

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_tasks_list_query_and_response_shape_20260523`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Owner agent: `copilot`
- Source: `route_list_tasks` in `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Additional source: `route_get_task` in `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Query implementation: `backend/app/beyo_manager/services/queries/tasks/tasks.py`
- Response serializers: `backend/app/beyo_manager/domain/tasks/serializers.py`
- Additional source: `get_image_route` in `backend/app/beyo_manager/routers/api_v1/images.py`
- Additional query implementation: `backend/app/beyo_manager/services/queries/images/get_image.py`
- Additional response serializers: `backend/app/beyo_manager/domain/images/serializers.py`

## Backend delivery context

- What backend exposes:
  - Task list endpoint with pagination, text search, multiple CSV filters, date window filters, optional deleted scope, and custom ordering.
  - Image get endpoint for full single-image payload by `image_client_id`.
- API contract shape:
  - Success envelope: `{"ok": true, "warnings": [], "data": ...}`
  - Error envelope: `{"ok": false, "error": "..."}`

## Frontend action required

1. Send list query params exactly as documented below.
2. Parse list payload from `data.tasks_pagination.items`.
3. Treat filter params marked as CSV as comma-separated strings.
4. Respect pagination with `limit`, `offset`, and `has_more`.
5. Handle empty result pages where `items` is an empty array.
6. For task list `item_images`, treat the first image as full shape and subsequent images as light shape.
7. For full image details, call `GET /api/v1/images/{image_client_id}`.
8. For task detail view, map arrays safely (`item_issues`, `item_upholstery`, `requirements`, `task_steps`, `task_notes`) and handle `item` being null.

## Interface details

### Endpoint

- `GET /api/v1/tasks`

### Query params accepted by route_list_tasks

- `limit: int` (default `50`, min `1`, max `200`)
- `offset: int` (default `0`, min `0`)
- `q: string | null` (max length `200`)
- `working_section_ids: string | null` (CSV)
- `task_states: string | null` (CSV)
- `task_step_states: string | null` (CSV)
- `step_readiness_statuses: string | null` (CSV)
- `priorities: string | null` (CSV)
- `task_types: string | null` (CSV)
- `return_sources: string | null` (CSV)
- `ready_from_date: string | null`
- `ready_to_date: string | null`
- `scheduled_from_date: string | null`
- `scheduled_to_date: string | null`
- `upholstery_requirement_states: string | null` (CSV)
- `deleted: boolean` (default `false`)
- `order_by: string | null`

### CSV behavior

- CSV params are split by comma and trimmed.
- Empty values are ignored.
- Example: `priorities=high,urgent`.

### Known enum values for common filters

- `task_states`: `pending, assigned, working, stalled, ready, resolved, failed, cancelled`
- `task_step_states`: `pending, working, paused, ended_shift, blocked, completed, skipped, failed, cancelled`
- `step_readiness_statuses`: `blocked, partial, ready`
- `priorities`: `low, normal, high, urgent`
- `task_types`: `return, pre_order, internal`
- `return_sources`: `after_purchase, before_purchase, store_return`

### order_by format

- Format: comma-separated list of `<field>:<direction>`.
- Direction: `asc` or `desc`.
- Supported fields:
  - `ready_by_at`
  - `created_at`
  - `scheduled_start_at`
  - `scheduled_end_at`
  - `priority`
- Example: `order_by=ready_by_at:asc,priority:desc,created_at:asc`
- Default order when omitted/invalid:
  - `ready_by_at ASC NULLS LAST`, then `priority DESC`, then `created_at ASC`.

### Query example

```http
GET /api/v1/tasks?limit=50&offset=0&q=linen&priorities=high,urgent&task_states=working,assigned&working_section_ids=wse_a,wse_b&order_by=ready_by_at:asc,priority:desc
```

### Response shape (success)

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "tasks_pagination": {
      "items": [
        {
          "task": {
            "client_id": "tsk_xxx",
            "task_scalar_id": 123,
            "task_type": "return",
            "priority": "high",
            "state": "working",
            "title": "Repair chair",
            "summary": "Front leg scratch",
            "return_source": "after_purchase",
            "item_location": "store",
            "return_method": "drop_off_by_customer",
            "fulfillment_method": "pickup_at_store",
            "additional_details": {"channel": "store"},
            "ready_by_at": "2026-05-25T16:00:00+00:00",
            "scheduled_start_at": "2026-05-24T09:00:00+00:00",
            "scheduled_end_at": "2026-05-24T12:00:00+00:00",
            "customer_id": "cus_xxx",
            "primary_phone_number": "+1...",
            "secondary_phone_number": null,
            "primary_email": "customer@example.com",
            "secondary_email": null,
            "address": {"line1": "..."},
            "created_at": "2026-05-23T10:00:00+00:00",
            "updated_at": "2026-05-23T12:00:00+00:00",
            "closed_at": null,
            "is_deleted": false,
            "deleted_at": null
          },
          "primary_item": {
            "client_id": "itm_xxx",
            "article_number": "ART-01",
            "sku": "SKU-01",
            "state": "pending",
            "item_category_id": "itc_xxx",
            "quantity": 1,
            "designer": "Alex",
            "height_in_cm": 100,
            "width_in_cm": 55,
            "depth_in_cm": 60,
            "item_value_minor": 120000,
            "item_cost_minor": 80000,
            "item_currency": "euro",
            "item_position": "warehouse-a3",
            "external_id": null,
            "external_url": null,
            "external_source": null,
            "external_order_id": null,
            "item_category_snapshot": "Wood",
            "item_major_category_snapshot": "wood"
          },
          "item_images": [
            {
              "client_id": "img_xxx",
              "image_url": "https://...",
              "storage_provider": "s3",
              "source_type": "uploaded",
              "source_reference": "s3_image_url",
              "width_px": 1080,
              "height_px": 720,
              "file_size_bytes": 123456,
              "created_at": "2026-05-23T10:00:00+00:00",
              "last_event": null,
              "events": [],
              "image_annotation": null
            },
            {
              "client_id": "img_yyy",
              "image_url": "https://...",
              "width_px": 640,
              "height_px": 480,
              "file_size_bytes": 54321
            }
          ]
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### Empty page response shape

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "tasks_pagination": {
      "items": [],
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### item_images behavior in list response

- Images are ordered by `display_order` ascending.
- First image is serialized with full `serialize_image` shape.
- Remaining images are serialized with `serialize_image_light` shape.

### Error cases

- Unauthorized/expired JWT:

```json
{
  "ok": false,
  "error": "..."
}
```

## Interface details (Task Get)

### Endpoint

- `GET /api/v1/tasks/{task_id}`

### Params accepted by route_get_task

- Path params:
  - `task_id: string` (required)
- Query params:
  - None exposed by this route.

### Request example

```http
GET /api/v1/tasks/tsk_xxx
```

### Response shape (success)

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "task": {
      "client_id": "tsk_xxx",
      "task_scalar_id": 123,
      "task_type": "return",
      "priority": "high",
      "state": "working",
      "title": "Repair chair",
      "summary": "Front leg scratch",
      "return_source": "after_purchase",
      "item_location": "store",
      "return_method": "drop_off_by_customer",
      "fulfillment_method": "pickup_at_store",
      "additional_details": {"channel": "store"},
      "ready_by_at": "2026-05-25T16:00:00+00:00",
      "scheduled_start_at": "2026-05-24T09:00:00+00:00",
      "scheduled_end_at": "2026-05-24T12:00:00+00:00",
      "customer_id": "cus_xxx",
      "primary_phone_number": "+1...",
      "secondary_phone_number": null,
      "primary_email": "customer@example.com",
      "secondary_email": null,
      "address": {"line1": "..."},
      "created_at": "2026-05-23T10:00:00+00:00",
      "updated_at": "2026-05-23T12:00:00+00:00",
      "closed_at": null,
      "is_deleted": false,
      "deleted_at": null
    },
    "item": {
      "client_id": "itm_xxx",
      "article_number": "ART-01",
      "sku": "SKU-01",
      "state": "pending",
      "item_category_id": "itc_xxx",
      "quantity": 1,
      "designer": "Alex",
      "height_in_cm": 100,
      "width_in_cm": 55,
      "depth_in_cm": 60,
      "item_value_minor": 120000,
      "item_cost_minor": 80000,
      "item_currency": "euro",
      "item_position": "warehouse-a3",
      "external_id": null,
      "external_url": null,
      "external_source": null,
      "external_order_id": null,
      "item_category_snapshot": "Wood",
      "item_major_category_snapshot": "wood"
    },
    "item_images": [
      {
        "client_id": "img_xxx",
        "image_url": "https://...",
        "width_px": 1080,
        "height_px": 720,
        "file_size_bytes": 123456
      }
    ],
    "item_issues": [
      {
        "client_id": "iis_xxx",
        "item_id": "itm_xxx",
        "issue_type_id": "ist_xxx",
        "issue_severity_id": "isv_xxx",
        "state": "pending",
        "base_time_seconds": 600,
        "time_multiplier": 1.25,
        "issue_name_snapshot": "Scratch",
        "severity_name_snapshot": "Medium",
        "created_by_id": "usr_xxx",
        "created_at": "2026-05-23T10:05:00+00:00",
        "started_at": null,
        "resolved_at": null,
        "updated_at": "2026-05-23T10:06:00+00:00"
      }
    ],
    "item_upholstery": [
      {
        "client_id": "iup_xxx",
        "item_id": "itm_xxx",
        "upholstery_id": "uph_xxx",
        "name": "Linen A",
        "code": "LIN-A",
        "amount_meters": 2.5,
        "source": "internal",
        "time_to_fix_in_seconds": 900,
        "active_requirement_id": "iur_xxx"
      }
    ],
    "requirements": [
      {
        "client_id": "iur_xxx",
        "item_upholstery_id": "iup_xxx",
        "upholstery_inventory_id": "uin_xxx",
        "amount_meters": 2.5,
        "value_minor": 4500,
        "currency": "euro",
        "source": "inventory",
        "state": "available"
      }
    ],
    "task_steps": [
      {
        "client_id": "tst_xxx",
        "task_id": "tsk_xxx",
        "state": "working",
        "readiness_status": "ready",
        "sequence_order": 1,
        "working_section_id": "wse_xxx",
        "assigned_worker_id": "usr_worker",
        "total_dependencies": 1,
        "completed_dependencies": 1,
        "working_section_name_snapshot": "Assembly",
        "assigned_worker_display_name_snapshot": "Alex Worker",
        "created_at": "2026-05-23T10:10:00+00:00",
        "closed_at": null,
        "latest_state_records": {
          "id": "ssr_xxx",
          "step_id": "tst_xxx",
          "state": "working",
          "reason": null,
          "entered_at": "2026-05-23T10:12:00+00:00",
          "exited_at": null,
          "created_at": "2026-05-23T10:12:00+00:00",
          "created_by_id": "usr_worker",
          "description": null,
          "accuracy": null,
          "accuracy_measured_by": null,
          "taken_from_average": false
        }
      }
    ],
    "task_notes": [
      {
        "client_id": "tno_xxx",
        "task_id": "tsk_xxx",
        "note_type": "user_note",
        "content": {"text": "Call customer before delivery"},
        "created_at": "2026-05-23T10:15:00+00:00",
        "updated_at": null,
        "is_deleted": false,
        "deleted_at": null
      }
    ],
    "unread_message_count": 2
  }
}
```

### Error cases

- Not found (`task_id` missing or inaccessible in workspace):

```json
{
  "ok": false,
  "error": "Task not found."
}
```

- Unauthorized/expired JWT:

```json
{
  "ok": false,
  "error": "..."
}
```

## Interface details (Image Get)

### Endpoint

- `GET /api/v1/images/{image_client_id}`

### Params accepted by get_image_route

- Path params:
  - `image_client_id: string` (required)

### Request example

```http
GET /api/v1/images/img_xxx
```

### Response shape (success)

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "image": {
      "client_id": "img_xxx",
      "image_url": "https://...",
      "storage_provider": "s3",
      "source_type": "uploaded",
      "source_reference": "s3_image_url",
      "width_px": 1080,
      "height_px": 720,
      "file_size_bytes": 123456,
      "created_at": "2026-05-23T10:00:00+00:00",
      "last_event": {
        "client_id": "ime_xxx",
        "event_type": "upload_item_image",
        "state": "completed",
        "created_at": "2026-05-23T10:00:01+00:00",
        "last_error": null
      },
      "events": [
        {
          "client_id": "ime_xxx",
          "event_type": "upload_item_image",
          "state": "completed",
          "created_at": "2026-05-23T10:00:01+00:00",
          "last_error": null
        }
      ],
      "image_annotation": {
        "client_id": "ian_xxx",
        "annotation_type": "rectangle",
        "data": {"x": 10, "y": 20, "w": 100, "h": 80},
        "accuracy": 95,
        "created_at": "2026-05-23T10:00:02+00:00"
      },
      "image_annotations": [
        {
          "client_id": "ian_xxx",
          "annotation_type": "rectangle",
          "data": {"x": 10, "y": 20, "w": 100, "h": 80},
          "accuracy": 95,
          "created_at": "2026-05-23T10:00:02+00:00"
        }
      ]
    }
  }
}
```

### Error cases

- Unauthorized/expired JWT:

```json
{
  "ok": false,
  "error": "..."
}
```

- Not found:

```json
{
  "ok": false,
  "error": "Image not found"
}
```

- Invalid path param / validation error:

```json
{
  "ok": false,
  "error": "..."
}
```

## Validation notes

- Backend source of truth used:
  - `route_list_tasks` query params in router.
  - `route_get_task` path params in router.
  - `list_tasks` query behavior in service.
  - `get_task` response assembly in service.
  - `serialize_task` and `serialize_item` payload fields.
  - `get_image_route` path params in router.
  - `get_image` query behavior in service.
  - `serialize_image` and related image serializers.
- Suggested frontend validation:
  - Verify CSV filters send correctly and combine as expected.
  - Verify `order_by` fallback behavior when invalid field names are passed.
  - Verify `deleted=true` list view behavior.

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Query service: `backend/app/beyo_manager/services/queries/tasks/tasks.py`
- Serializers: `backend/app/beyo_manager/domain/tasks/serializers.py`
- Router: `backend/app/beyo_manager/routers/api_v1/images.py`
- Query service: `backend/app/beyo_manager/services/queries/images/get_image.py`
- Serializers: `backend/app/beyo_manager/domain/images/serializers.py`
