# HANDOFF_TO_FRONTEND_upholstery_ordering_routers_contract_20260616

## Metadata

- Handoff ID: HANDOFF_TO_FRONTEND_upholstery_ordering_routers_contract_20260616
- Created at (UTC): 2026-06-16T16:00:00Z
- Owner agent: GitHub Copilot (GPT-5.3-Codex)
- Source plan: backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_order_20260616.md
- Source summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_20260616.md

## Backend delivery context

- What backend implemented:
  - Dedicated upholstery order read/write routers under /api/v1/upholstery-orders.
  - Dedicated upholstery order needs routers under /api/v1/upholstery-order-needs.
  - Query surfaces for order counts, order list, order-item task list, needs counts, needs list, and needs-by-upholstery item list.
  - Create order command integrated with inventory ordered-pool update and requirement allocation when created in ordered state.
  - Receive order command for recording full or partial stock receipt, auto-transitioning order state, and re-allocating requirements from the received stock.
- API or contract changes:
  - New route family for upholstery order lifecycle and planning lists.
  - New query filters: states, upholstery_ids, requirement_states, q.
  - `POST /api/v1/upholstery-orders/receive` success payload includes the order end-state after receipt processing.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use the new order-needs routes to build the planning and pre-order selection screens.
2. Use the new order routes to create orders and list orders/order-items with server-side pagination.
3. Send CSV query values for multi-filter query params (states, upholstery_ids, requirement_states).
4. Treat all successful responses as wrapped payloads under data, with ok and warnings at envelope level.

## Enum reference

### UpholsteryOrderStateEnum

Valid order states (use as string values in queries and responses):
- `draft` — initial creation state, no side effects on inventory or requirements.
- `pending` — order awaiting approval workflow.
- `approved` — order approved, ready for ordering.
- `ordered` — order placed with supplier; requirement allocation is active. **Only this state triggers inventory pool update and requirement allocation.**
- `failed` — procurement failed; order lifecycle ended.
- `cancelled` — order cancelled; procurement suspended.
- `partially_received` — partial stock received; order awaiting remainder.
- `received` — full stock received; procurement complete.

### ItemUpholsteryRequirementStateEnum

Valid requirement states (used in requirement_states filter and requirement responses):
- `missing_quantity` — upholstery selected but quantity not yet specified.
- `available` — sufficient stock exists in inventory to fulfill this requirement.
- `needs_ordering` — insufficient stock; material must be ordered.
- `ordered` — material has been ordered and is in transit/pending receipt.
- `in_use` — material allocated and currently being used in production.
- `completed` — requirement fully satisfied; material consumption complete.
- `failed` — requirement procurement or fulfillment failed.

### UpholsteryCurrencyEnum

Valid currency values (optional, used in order creation):
- `swedish_krona`
- `danish_krona`
- `euro`

## Interface details

- Common response envelope:
  - Success: { ok: true, data: <payload>, warnings: [] }
  - Error: { ok: false, error: <message> }

### 1) GET /api/v1/upholstery-orders/count

- Handler: route_get_upholstery_orders_count
- Auth roles: admin, manager
- Query params:
  - states: optional string (CSV). Valid values from UpholsteryOrderStateEnum. Example: `ordered,partially_received,received`
- Defaults and behavior:
  - If states is omitted, count includes all non-deleted orders in workspace.
- Response payload (data):
  - total: integer
  - by_state: object map where keys are order state values (from UpholsteryOrderStateEnum) and values are counts
- Example payload:
  - { total: 8, by_state: { ordered: 5, partially_received: 2, received: 1 } }

### 2) GET /api/v1/upholstery-orders

- Handler: route_list_upholstery_orders
- Auth roles: admin, manager
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
  - states: optional string (CSV). Valid values from UpholsteryOrderStateEnum. Example: `ordered,partially_received`
- Defaults and behavior:
  - limit defaults to 50 if not passed.
  - Hard max limit is 200.
  - Sorted by created_at descending.
  - If states omitted, no state filtering.
  - q searches across upholstery fields and linked task/item text fields.
- Response payload (data):
  - orders_pagination:
    - items: array
      - client_id: string
      - upholstery_id: string or null
      - upholstery_name: string or null
      - upholstery_code: string or null
      - upholstery_image_url: string or null
      - order_amount_meters: number
      - received_amount_meters: number or null
      - expected_receive_at: ISO datetime string or null
      - received_at: ISO datetime string or null
      - state: string (from UpholsteryOrderStateEnum)
      - supplier_id: string or null
    - limit: integer
    - offset: integer
    - has_more: boolean

### 3) GET /api/v1/upholstery-orders/items

- Handler: route_list_upholstery_order_items
- Auth roles: admin, manager
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
  - upholstery_ids: optional string (CSV)
  - requirement_states: optional string (CSV). Valid values from ItemUpholsteryRequirementStateEnum. Example: `available,needs_ordering,ordered`
- Mandatory/optional usage notes:
  - upholstery_ids is functionally required for meaningful results.
  - If upholstery_ids is omitted or empty, service returns an empty tasks_pagination result (no error).
  - requirement_states is optional; if omitted, no requirement-state filter is applied.
- Defaults and behavior:
  - limit defaults to 50, capped at 200.
  - Ordering follows task ordering helper default: ready_by_at asc nulls-last, then priority desc, then created_at asc.
- Response payload (data):
  - tasks_pagination:
    - items: array
      - task:
        - client_id: string
        - task_scalar_id: integer or null
        - task_type: string
        - priority: string
        - state: string
        - title: string or null
        - summary: string or null
        - return_source: string or null
        - item_location: string or null
        - return_method: string or null
        - fulfillment_method: string or null
        - additional_details: any or null
        - ready_by_at: ISO datetime string or null
        - scheduled_start_at: ISO datetime string or null
        - scheduled_end_at: ISO datetime string or null
        - customer_id: string or null
        - primary_phone_number: string or null
        - secondary_phone_number: string or null
        - primary_email: string or null
        - secondary_email: string or null
        - address: string or null
        - created_at: ISO datetime string or null
        - updated_at: ISO datetime string or null
        - closed_at: ISO datetime string or null
        - is_deleted: boolean
        - deleted_at: ISO datetime string or null
      - primary_item: object or null
        - client_id: string
        - article_number: string or null
        - sku: string or null
        - state: string
        - item_category_id: string or null
        - quantity: integer
        - designer: string or null
        - height_in_cm: integer or null
        - width_in_cm: integer or null
        - depth_in_cm: integer or null
        - item_value_minor: integer or null
        - item_cost_minor: integer or null
        - item_currency: string or null
        - item_position: string or null
        - external_id: string or null
        - external_url: string or null
        - external_source: string or null
        - external_order_id: string or null
        - item_category_snapshot: string or null
        - item_major_category_snapshot: string or null
      - item_images: array. First element is full image, subsequent elements are light.
        - First element (full):
          - client_id: string
          - image_url: string or null
          - storage_provider: string or null
          - source_type: string or null
          - source_reference: string or null
          - width_px: integer or null
          - height_px: integer or null
          - file_size_bytes: integer or null
          - created_at: ISO datetime string
          - last_event: object or null (client_id, event_type, state, created_at, last_error)
          - events: array (empty unless requested)
          - image_annotation: object or null
        - Subsequent elements (light):
          - client_id: string
          - image_url: string or null
          - width_px: integer or null
          - height_px: integer or null
          - file_size_bytes: integer or null
      - item_upholstery: object or null
        - client_id: string
        - amount_meters: number or null
    - limit: integer
    - offset: integer
    - has_more: boolean

### 4) PUT /api/v1/upholstery-orders

- Handler: route_create_upholstery_order
- Auth roles: admin, manager
- Request body fields:
  - Required:
    - upholstery_id: string
    - order_amount_meters: decimal number, must be > 0
  - Optional:
    - client_id: string or null. **If provided by frontend, must start with prefix `uor` (e.g., `uor_abc123def456`).** Backend validates uniqueness and prefix format; omit if server should auto-generate.
    - priority_item_upholstery_ids: array of string, default []
    - state: string enum (UpholsteryOrderStateEnum), default `ordered`. Allowed create states: `draft`, `pending`, `approved`, `ordered`.
    - supplier_id: string or null
    - upholstery_supplier_link_id: string or null
    - price_minor: integer or null, must be >= 0 when provided
    - currency: string enum (UpholsteryCurrencyEnum), or null. Valid: `swedish_krona`, `danish_krona`, `euro`.
    - order_at: datetime or null
    - expected_receive_at: datetime or null
- Service-side defaults and validation:
  - state defaults to `ordered`.
  - Only allowed creation states are: `draft`, `pending`, `approved`, `ordered`. Other states (failed, cancelled, partially_received, received) cannot be set at creation time.
  - If client_id is provided, prefix and uniqueness are validated.
  - inventory for upholstery_id must exist, otherwise NotFound.
  - supplier_id and upholstery_supplier_link_id are validated when provided.
  - If both supplier_id and upholstery_supplier_link_id are provided, they must match each other.
- Side effects:
  - Always creates UpholsteryOrder and an initial UpholsteryOrderHistoryRecord.
  - If state is ordered:
    - Adds order amount to inventory ordered pool.
    - Allocates NEEDS_ORDERING requirements to ORDERED by priority and scheduling rules.
- Response payload (data):
  - { client_id: <new_order_id> }
- Common error cases:
  - ValidationError for invalid state/amount/price mismatch conditions.
  - NotFound for missing inventory/supplier/link.
  - ConflictError for duplicate provided client_id.

### 5) POST /api/v1/upholstery-orders/receive

- Handler: route_receive_upholstery_order
- Auth roles: admin, manager
- Request body fields:
  - Required:
    - client_id: string — the `client_id` of the existing upholstery order to receive against (prefix `uor`).
    - received_amount_meters: decimal number, must be > 0
  - Optional:
    - priority_item_upholstery_ids: array of string, default []
    - received_at: datetime or null. If omitted, defaults to server UTC now.
- Service-side validation:
  - Order must be in state `ordered` or `partially_received`; any other state returns ValidationError.
  - Cumulative `received_amount_meters` (existing + this call) must not exceed `order_amount_meters`; otherwise ValidationError with the maximum receivable amount.
  - Order must have a linked inventory record.
- Side effects:
  - Appends an `UpholsteryOrderHistoryRecord` snapshot.
  - Moves received quantity from ordered pool into stored stock on inventory.
  - Allocates newly available stock to pending requirements (priority set first, then ORDERED by oldest, then NEEDS_ORDERING by oldest).
  - Transitions matched requirements from `ordered` or `needs_ordering` to `available`.
  - Order state transitions automatically:
    - If cumulative received equals order amount → `received`.
    - If cumulative received is less than order amount → `partially_received`.
  - Dispatches `upholstery:order-received` workspace event.
  - Dispatches `item:upholstery-requirement-state-changed` event for allocated requirements.
- Response payload (data):
  - client_id: string
  - state: string (from UpholsteryOrderStateEnum) — the final persisted state after this receive call completes
    - `received` when cumulative received amount equals the ordered amount
    - `partially_received` when cumulative received amount remains below the ordered amount
- Common error cases:
  - NotFound if order does not exist or belongs to a different workspace.
  - ValidationError if order is not in a receivable state.
  - ValidationError if received amount exceeds remaining order amount.

### 6) GET /api/v1/upholstery-order-needs/count

- Handler: route_get_upholstery_order_needs_count
- Auth roles: admin, manager
- Query params:
  - none
- Defaults and behavior:
  - Counts only actionable order-needs, meaning upholstery inventories that still have a real remaining amount to order greater than 0 after subtracting stored stock and already ordered stock.
- Response payload (data):
  - needs_ordering_count: integer
    - Number of `needs_ordering` requirement rows attached to upholstery inventories that still have a real remaining amount to order greater than 0.
  - upholstery_count: integer
    - Number of distinct upholstery inventories that still have a real remaining amount to order greater than 0.

### 7) GET /api/v1/upholstery-order-needs

- Handler: route_list_upholstery_order_needs
- Auth roles: admin, manager
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
- Defaults and behavior:
  - limit defaults to 50, capped at 200.
  - Includes only upholsteries that:
    - currently have at least one `needs_ordering` requirement
    - and still have a real remaining amount to order greater than 0 after subtracting stored stock and already ordered stock
  - The order amount is inventory-driven, not a raw sum of requirement amounts:
    - `amount_to_order_meters = max(current_amount_in_need_meters - current_stored_amount_meters - current_amount_ordered_meters, 0)`
  - Sorted by earliest linked task ready_by_at asc nulls-last, then upholstery name asc.
- Response payload (data):
  - upholstery_needs_pagination:
    - items: array
      - upholstery_id: string
      - upholstery_name: string
      - upholstery_code: string or null
      - upholstery_image_url: string or null
      - item_count: integer
      - amount_to_order_meters: number
      - earliest_due_date: ISO date string or null
    - limit: integer
    - offset: integer
    - has_more: boolean

### 8) GET /api/v1/upholstery-order-needs/{upholstery_id}/items

- Handler: route_get_upholstery_order_need_items
- Auth roles: admin, manager
- Path params:
  - upholstery_id: required string
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
- Defaults and behavior:
  - limit defaults to 50, capped at 200.
  - Returns tasks linked to items whose selected upholstery matches upholstery_id and active requirement state is needs_ordering.
  - If no matches, returns empty tasks_pagination (not an error).
- Response payload (data):
  - tasks_pagination:
    - items: array
      - task: (same full task shape as route 3 — see task fields above)
        - client_id: string
        - task_scalar_id: integer or null
        - task_type: string
        - priority: string
        - state: string
        - title: string or null
        - summary: string or null
        - return_source: string or null
        - item_location: string or null
        - return_method: string or null
        - fulfillment_method: string or null
        - additional_details: any or null
        - ready_by_at: ISO datetime string or null
        - scheduled_start_at: ISO datetime string or null
        - scheduled_end_at: ISO datetime string or null
        - customer_id: string or null
        - primary_phone_number: string or null
        - secondary_phone_number: string or null
        - primary_email: string or null
        - secondary_email: string or null
        - address: string or null
        - created_at: ISO datetime string or null
        - updated_at: ISO datetime string or null
        - closed_at: ISO datetime string or null
        - is_deleted: boolean
        - deleted_at: ISO datetime string or null
      - primary_item: object or null (same shape as route 3)
        - client_id: string
        - article_number: string or null
        - sku: string or null
        - state: string
        - item_category_id: string or null
        - quantity: integer
        - designer: string or null
        - height_in_cm: integer or null
        - width_in_cm: integer or null
        - depth_in_cm: integer or null
        - item_value_minor: integer or null
        - item_cost_minor: integer or null
        - item_currency: string or null
        - item_position: string or null
        - external_id: string or null
        - external_url: string or null
        - external_source: string or null
        - external_order_id: string or null
        - item_category_snapshot: string or null
        - item_major_category_snapshot: string or null
      - item_images: array (same shape as route 3 — first full, subsequent light)
      - item_upholstery: object or null
        - client_id: string
        - amount_meters: number or null
    - limit: integer
    - offset: integer
    - has_more: boolean

## Validation notes

- Backend validation run:
  - Contract documentation compiled from current router, command, request parser, and query implementations.
  - No additional runtime test execution was performed while preparing this handoff document.
- Frontend client_id generation:
  - If frontend generates `client_id` for upholstery orders, **prefix must be `uor`** (e.g., `uor_a1b2c3d4e5f6`).
  - Backend validates prefix format and uniqueness within workspace.
  - If `client_id` is omitted, backend auto-generates a unique ID with correct prefix.
- Suggested frontend validation:
  1. Verify create-order form blocks invalid states outside draft/pending/approved/ordered.
  2. Verify positive decimal validation for order_amount_meters.
  3. Verify CSV query builder for states, upholstery_ids, requirement_states.
  4. Verify empty-result behavior for order-items route when upholstery_ids is omitted.
  5. Verify pagination behavior using limit/offset and has_more.
  6. **If generating client_id, enforce `uor_` prefix** to match backend expectations.

## Trace links

- Parent plan: backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_order_20260616.md
- Parent summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_20260616.md
- Related debug plan (optional): backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_receive_upholstery_order_20260616.md
