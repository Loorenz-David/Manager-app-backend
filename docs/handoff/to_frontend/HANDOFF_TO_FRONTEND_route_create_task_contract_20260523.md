# HANDOFF_TO_FRONTEND_route_create_task_contract_20260523

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_route_create_task_contract_20260523`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Owner agent: `copilot`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - Create task endpoint with optional nested creation for item, item issues, item upholstery, notes, and task steps.
- API or contract changes:
  - None in this handoff file; this documents current behavior of `route_create_task`.
- Feature flags/toggles (if any):
  - Item issue severity is currently disabled at write-time in backend command logic. Severity fields can be sent but are ignored for persistence.

## Frontend action required


3. If sending nested `item_issues` or `item_upholstery`, include `item` in the same payload.

## Interface details

### Endpoint

- Method: `PUT`
- URL: `/api/v1/tasks`
- Auth roles accepted: `ADMIN`, `MANAGER`, `SELLER`
- Query params: none

### Request body shape

All fields are optional except `task_type`.

```json
{
  "client_id": "tsk_custom_optional",
  "task_type": "return",
  "state": "pending",
  "title": "Repair chair",
  "summary": "Front leg scratch",
  "priority": "normal",
  "ready_by_at": "2026-05-25T16:00:00+00:00",
  "scheduled_start_at": "2026-05-24T09:00:00+00:00",
  "scheduled_end_at": "2026-05-24T12:00:00+00:00",
  "return_source": "after_purchase",
  "item_location": "store",
  "return_method": "drop_off_by_customer",
  "fulfillment_method": "pickup_at_store",
  "additional_details": {"channel": "store"},

  "customer_id": "cus_xxx",
  "customer_display_name": "John Doe",
  "primary_phone_number": "+1...",
  "secondary_phone_number": "+1...",
  "primary_email": "customer@example.com",
  "secondary_email": "alt@example.com",
  "customer_address": {"line1": "..."},

  "item": {
    "client_id": "itm_custom_optional",
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
  },

  "item_issues": [
    {
      "issue_type_id": "ist_xxx",
      "issue_severity_id": "iss_xxx",
      "base_time_seconds": 600,
      "time_multiplier": 1.5,
      "issue_name_snapshot": "Broken parts",
      "severity_name_snapshot": "Medium"
    }
  ],

  "item_upholstery": {
    "client_id": "iup_custom_optional",
    "upholstery_id": "uph_xxx",
    "source": "internal",
    "name": "Linen A",
    "code": "LIN-A",
    "amount_meters": 2.5,
    "time_to_fix_in_seconds": 900
  },

  "notes": [
    {
      "client_id": "tno_custom_optional",
      "note_type": "user_note",
      "content": {"text": "Customer called"}
    }
  ],

  "steps": [
    {
      "client_id": "tsp_custom_optional",
      "working_section_id": "wse_xxx",
      "worker_id": "usr_xxx",
      "sequence_order": 1
    }
  ]
}
```

### Enum values

- `task_type`: `return` | `pre_order` | `internal`
- `priority`: `low` | `normal` | `high` | `urgent`
- `state`: `pending` | `assigned` | `working` | `stalled` | `ready` | `resolved` | `failed` | `cancelled`
- `return_source`: `after_purchase` | `before_purchase` | `store_return`
- `item_location`: `store` | `customer`
- `return_method`: `drop_off_by_customer` | `pickup`
- `fulfillment_method`: `pickup_at_store` | `delivery`
- `item.item_currency`: `swedish_krona` | `danish_krona` | `euro`
- `item_upholstery.source`: `internal` | `customer`
- `notes[].note_type`: `user_note` | `system_note` | `correction_note` | `retraction_note`

### Success response shape

HTTP status: `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "client_id": "tsk_xxx",
    "task_scalar_id": 123
  }
}
```

### Error response shape

```json
{
  "ok": false,
  "error": "..."
}
```

### Common error cases

- Validation / domain errors:
  - `item_issues require item in payload.`
  - `item_upholstery requires item in payload.`
  - `upholstery_id is required when source is INTERNAL.`
  - Pydantic field errors (for missing/invalid body fields).
- Not found:
  - `ItemCategory not found.`
  - `Upholstery not found.`
  - `Customer not found.`
  - `Working section '<id>' not found.`
- Conflict:
  - `Provided client_id is already in use.`
  - `Provided client_id for step is already in use.`

## Behavior notes for frontend

- Seller role behavior:
  - If requester role is `SELLER`, task state is forced to `pending` even if `state` is sent.
- Steps behavior:
  - If `steps` are provided and requester is not seller, backend sets task state to `assigned`.
- Customer behavior:
  - If `customer_id` is absent but customer fields are provided, backend finds or creates a customer.
- Item issue severity temporary behavior:
  - `issue_severity_id` and `severity_name_snapshot` are currently accepted but not persisted by backend write logic.

## Validation notes

- Backend validation run:
  - Shape compiled from router + request parser + command implementation.
- Suggested frontend validation:
  - Enforce `task_type` required.
  - Enforce `item` present when sending `item_issues` or `item_upholstery`.
  - Enforce `item_upholstery.upholstery_id` when `item_upholstery.source = internal`.

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/tasks.py`
- Command: `backend/app/beyo_manager/services/commands/tasks/create_task.py`
- Task request models: `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py`
- HTTP response envelope: `backend/app/beyo_manager/routers/http/response.py`
