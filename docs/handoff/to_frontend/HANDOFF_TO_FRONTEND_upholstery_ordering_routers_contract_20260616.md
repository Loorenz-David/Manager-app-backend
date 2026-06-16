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
- API or contract changes:
  - New route family for upholstery order lifecycle and planning lists.
  - New query filters: states, upholstery_ids, requirement_states, q.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use the new order-needs routes to build the planning and pre-order selection screens.
2. Use the new order routes to create orders and list orders/order-items with server-side pagination.
3. Send CSV query values for multi-filter query params (states, upholstery_ids, requirement_states).
4. Treat all successful responses as wrapped payloads under data, with ok and warnings at envelope level.

## Interface details

- Common response envelope:
  - Success: { ok: true, data: <payload>, warnings: [] }
  - Error: { ok: false, error: <message> }

### 1) GET /api/v1/upholstery-orders/count

- Handler: route_get_upholstery_orders_count
- Auth roles: admin, manager
- Query params:
  - states: optional string (CSV). Example: ordered,partially_received
- Defaults and behavior:
  - If states is omitted, count includes all non-deleted orders in workspace.
- Response payload (data):
  - total: integer
  - by_state: object map where keys are order state values and values are counts
- Example payload:
  - { total: 8, by_state: { ordered: 5, partially_received: 2, received: 1 } }

### 2) GET /api/v1/upholstery-orders

- Handler: route_list_upholstery_orders
- Auth roles: admin, manager
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
  - states: optional string (CSV)
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
      - expected_receive_at: ISO datetime string or null
      - received_at: ISO datetime string or null
      - state: string
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
  - requirement_states: optional string (CSV)
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
      - task: serialized task object
      - primary_item: serialized item object
      - item_images: array of image objects
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
    - client_id: string or null
    - priority_item_upholstery_ids: array of string, default []
    - state: string enum, default ordered
    - supplier_id: string or null
    - upholstery_supplier_link_id: string or null
    - price_minor: integer or null, must be >= 0 when provided
    - currency: string enum (swedish_krona, danish_krona, euro) or null
    - order_at: datetime or null
    - expected_receive_at: datetime or null
- Service-side defaults and validation:
  - state default is ordered.
  - Allowed create states: draft, pending, approved, ordered.
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

### 5) GET /api/v1/upholstery-order-needs/count

- Handler: route_get_upholstery_order_needs_count
- Auth roles: admin, manager
- Query params:
  - none
- Defaults and behavior:
  - Counts only requirements in state needs_ordering.
- Response payload (data):
  - needs_ordering_count: integer
  - upholstery_count: integer (distinct upholstery inventories represented)

### 6) GET /api/v1/upholstery-order-needs

- Handler: route_list_upholstery_order_needs
- Auth roles: admin, manager
- Query params:
  - limit: optional integer, default 50, range 1..200
  - offset: optional integer, default 0, min 0
  - q: optional string, max length 200
- Defaults and behavior:
  - limit defaults to 50, capped at 200.
  - Includes upholsteries that currently have at least one needs_ordering requirement.
  - Sorted by earliest linked task ready_by_at asc nulls-last, then upholstery name asc.
- Response payload (data):
  - upholstery_needs_pagination:
    - items: array
      - upholstery_id: string
      - upholstery_name: string
      - upholstery_code: string or null
      - upholstery_image_url: string or null
      - item_count: integer
      - total_amount_meters: number
      - earliest_due_date: ISO date string or null
    - limit: integer
    - offset: integer
    - has_more: boolean

### 7) GET /api/v1/upholstery-order-needs/{upholstery_id}/items

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
      - task: serialized task object
      - primary_item: serialized item object
      - item_images: array of image objects
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
- Suggested frontend validation:
  1. Verify create-order form blocks invalid states outside draft/pending/approved/ordered.
  2. Verify positive decimal validation for order_amount_meters.
  3. Verify CSV query builder for states, upholstery_ids, requirement_states.
  4. Verify empty-result behavior for order-items route when upholstery_ids is omitted.
  5. Verify pagination behavior using limit/offset and has_more.

## Trace links

- Parent plan: backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_order_20260616.md
- Parent summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_20260616.md
- Related debug plan (optional): backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_receive_upholstery_order_20260616.md
