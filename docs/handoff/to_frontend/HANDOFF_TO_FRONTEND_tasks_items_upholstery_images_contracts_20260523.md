# HANDOFF_TO_FRONTEND_tasks_items_upholstery_images_contracts_20260523

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_tasks_items_upholstery_images_contracts_20260523`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Owner agent: `copilot`
- Scope: task detail + task mutations + image list + item issue + item updates + item upholstery quantity/update/delete + upholstery requirements list

## Global response envelope

- Success:

```json
{
  "ok": true,
  "warnings": [],
  "data": {}
}
```

- Error:

```json
{
  "ok": false,
  "error": "..."
}
```

## 1) Task detail

### Endpoint

- `GET /api/v1/tasks/{task_id}`

### Params

- Path:
  - `task_id: string` (required)
- Query:
  - none exposed by route

### Success data shape

```json
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
```

## 2) Images list for entity

### Endpoint

- `GET /api/v1/images`

### Params

- Query:
  - `entity_type: string` (required)
  - `entity_client_id: string` (required)

### Supported entity_type values

- `item`
- `case`
- `case_conversation_message`
- `item_category`
- `upholstery`

### Success data shape

```json
{
  "images": [
    {
      "link_client_id": "iml_xxx",
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
        "events": [],
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
      },
      "entity_type": "item",
      "entity_client_id": "itm_xxx",
      "display_order": 0
    }
  ]
}
```

## 3) Create item issue

### Endpoint

- `POST /api/v1/items/{client_id}/issues`

### Params

- Path:
  - `client_id: string` (item id, required)

### Body

```json
{
  "issue_type_id": "ist_xxx",
  "issue_severity_id": "isv_xxx",
  "base_time_seconds": 600,
  "time_multiplier": 1.25,
  "issue_name_snapshot": "Scratch",
  "severity_name_snapshot": "Medium"
}
```

### Success data shape

```json
{
  "client_id": "iis_xxx"
}
```

## 4) Set quantity for active requirement

### Endpoint

- `POST /api/v1/item-upholsteries/{client_id}/set-quantity`

### Params

- Path:
  - `client_id: string` (item upholstery id, required)

### Body

```json
{
  "amount_meters": 2.5
}
```

### Success data shape

```json
{}
```

## 5) Update item upholstery

### Endpoint

- `PATCH /api/v1/item-upholsteries/{client_id}`

### Params

- Path:
  - `client_id: string` (required)

### Body

```json
{
  "name": "Linen A",
  "code": "LIN-A",
  "amount_meters": 2.5,
  "time_to_fix_in_seconds": 900
}
```

### Success data shape

```json
{}
```

## 6) Delete item upholstery

### Endpoint

- `DELETE /api/v1/item-upholsteries/{client_id}`

### Params

- Path:
  - `client_id: string` (required)

### Success data shape

```json
{}
```

## 7) List upholstery requirements for one item upholstery

### Endpoint

- `GET /api/v1/item-upholsteries/{client_id}/requirements`

### Params

- Path:
  - `client_id: string` (item upholstery id, required)
- Query:
  - `limit: int` (default `50`, min `1`, max `200`)
  - `offset: int` (default `0`, min `0`)

### Success data shape

```json
{
  "upholstery_requirements_pagination": {
    "items": [
      {
        "client_id": "iur_xxx",
        "workspace_id": "wrk_xxx",
        "item_upholstery_id": "iup_xxx",
        "upholstery_inventory_id": "uin_xxx",
        "amount_meters": "2.500",
        "source": "inventory",
        "state": "available",
        "value_minor": 4500,
        "currency": "euro",
        "created_at": "2026-05-23T10:00:00+00:00",
        "created_by_id": "usr_xxx",
        "ordered_at": null,
        "in_use_at": null,
        "completed_at": null,
        "failed_at": null,
        "updated_at": "2026-05-23T10:10:00+00:00",
        "updated_by_id": "usr_xxx",
        "is_deleted": false
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

## 8) Create task note

### Endpoint

- `POST /api/v1/tasks/{task_id}/notes`

### Params

- Path:
  - `task_id: string` (required)

### Body

```json
{
  "client_id": "tno_custom_optional",
  "note_type": "user_note",
  "content": {"text": "Customer called"}
}
```

### Success data shape

```json
{
  "client_id": "tno_xxx"
}
```

## 9) Update task note

### Endpoint

- `PATCH /api/v1/tasks/{task_id}/notes/{note_id}`

### Params

- Path:
  - `task_id: string` (required by route path)
  - `note_id: string` (required; this is what service uses)

### Body

```json
{
  "note_type": "correction_note",
  "content": {"text": "Corrected note"}
}
```

### Success data shape

```json
{
  "client_id": "tno_xxx"
}
```

## 10) Delete task note

### Endpoint

- `DELETE /api/v1/tasks/{task_id}/notes/{note_id}`

### Params

- Path:
  - `task_id: string` (required by route path)
  - `note_id: string` (required; this is what service uses)

### Success data shape

```json
{
  "client_id": "tno_xxx"
}
```

## 11) Update task

### Endpoint

- `PATCH /api/v1/tasks/{task_id}`

### Params

- Path:
  - `task_id: string` (required)

### Body

```json
{
  "title": "Updated task title",
  "summary": "Updated summary",
  "priority": "high",
  "ready_by_at": "2026-05-25T16:00:00+00:00",
  "scheduled_start_at": "2026-05-24T09:00:00+00:00",
  "scheduled_end_at": "2026-05-24T12:00:00+00:00",
  "return_source": "after_purchase",
  "item_location": "store",
  "return_method": "pickup",
  "fulfillment_method": "delivery",
  "additional_details": {"channel": "store"}
}
```

### Success data shape

```json
{
  "client_id": "tsk_xxx"
}
```

## 12) Delete task

### Endpoint

- `DELETE /api/v1/tasks/{task_id}`

### Params

- Path:
  - `task_id: string` (required)

### Success data shape

```json
{
  "client_id": "tsk_xxx"
}
```

## 13) Resolve task

### Endpoint

- `POST /api/v1/tasks/{task_id}/resolve`

### Params

- Path:
  - `task_id: string` (required)

### Success data shape

```json
{
  "client_id": "tsk_xxx"
}
```

## 14) Cancel task

### Endpoint

- `POST /api/v1/tasks/{task_id}/cancel`

### Params

- Path:
  - `task_id: string` (required)

### Success data shape

```json
{
  "client_id": "tsk_xxx"
}
```

## 15) Fail task

### Endpoint

- `POST /api/v1/tasks/{task_id}/fail`

### Params

- Path:
  - `task_id: string` (required)

### Success data shape

```json
{
  "client_id": "tsk_xxx"
}
```

## 16) Update item

### Endpoint

- `PATCH /api/v1/items/{client_id}`

### Params

- Path:
  - `client_id: string` (required)

### Body

```json
{
  "article_number": "ART-01",
  "sku": "SKU-01",
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
  "external_id": "shopify-1",
  "external_url": "https://...",
  "external_source": "shopify",
  "external_order_id": "ord_123"
}
```

### Success data shape

```json
{
  "client_id": "itm_xxx"
}
```

## 17) Task flow records timeline

### Endpoint

- `GET /api/v1/tasks/{task_id}/flow-records`

### Params

- Path:
  - `task_id: string` (required)
- Query:
  - `offset: int` (default `0`, min `0`)

### Payload

- none

### Success data shape

```json
{
  "flow_records": [
    {
      "type": "history_record",
      "entity_type": "task",
      "entity_client_id": "tsk_xxx",
      "description": "Task created",
      "created_at": "2026-05-23T10:00:00+00:00",
      "created_by": {
        "client_id": "usr_xxx",
        "username": "alice",
        "profile_picture": "https://..."
      }
    },
    {
      "type": "task_step",
      "entity_type": "task_step",
      "entity_client_id": "tst_xxx",
      "description": "alice marked in_progress on working section Upholstery",
      "created_at": "2026-05-23T10:05:00+00:00",
      "created_by": {
        "client_id": "usr_xxx",
        "username": "alice",
        "profile_picture": "https://..."
      }
    }
  ],
  "flow_records_pagination": {
    "has_more": false,
    "limit": 10,
    "offset": 0
  }
}
```

Notes:
- `created_by` can be `null` when the record has no creator id.
- Records are returned in descending `created_at` order.

## 18) Delete item issue

### Endpoint

- `DELETE /api/v1/items/{client_id}/issues/{issue_id}`

### Params

- Path:
  - `client_id: string` (item id, required)
  - `issue_id: string` (item issue id, required)

### Payload

- none

### Success data shape

```json
{}
```

## Common not-found messages observed in services

- Task: `Task not found.`
- Task note: `Task note not found.`
- Item: `Item not found.`
- Item issue: `Item issue not found.`
- Item category (on item update): `ItemCategory not found.`
- ItemUpholstery: `ItemUpholstery not found.`
- Active requirement (set quantity): `Active requirement not found.`

## Trace links

- Tasks router: `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Tasks query service: `backend/app/beyo_manager/services/queries/tasks/tasks.py`
- Task flow records query service: `backend/app/beyo_manager/services/queries/tasks/task_flow_records.py`
- Task commands:
  - `backend/app/beyo_manager/services/commands/tasks/create_task_note.py`
  - `backend/app/beyo_manager/services/commands/tasks/update_task_note.py`
  - `backend/app/beyo_manager/services/commands/tasks/delete_task_note.py`
  - `backend/app/beyo_manager/services/commands/tasks/update_task.py`
  - `backend/app/beyo_manager/services/commands/tasks/delete_task.py`
  - `backend/app/beyo_manager/services/commands/tasks/resolve_task.py`
  - `backend/app/beyo_manager/services/commands/tasks/cancel_task.py`
  - `backend/app/beyo_manager/services/commands/tasks/fail_task.py`
- Images router/query:
  - `backend/app/beyo_manager/routers/api_v1/images.py`
  - `backend/app/beyo_manager/services/queries/images/list_images_for_entity.py`
- Items router/commands:
  - `backend/app/beyo_manager/routers/api_v1/items.py`
  - `backend/app/beyo_manager/services/commands/items/create_item_issue.py`
  - `backend/app/beyo_manager/services/commands/items/delete_item_issue.py`
  - `backend/app/beyo_manager/services/commands/items/update_item.py`
- Item upholsteries router/query/commands:
  - `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`
  - `backend/app/beyo_manager/services/queries/items/item_upholsteries.py`
  - `backend/app/beyo_manager/services/commands/items/set_requirement_quantity.py`
  - `backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py`
