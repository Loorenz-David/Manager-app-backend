# Frontend handoff: Shopify locations and inventory-aware product sync

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_shopify_inventory_product_sync_20260715`
- Created at (UTC): `2026-07-15`
- Backend routes: `app/beyo_manager/routers/api_v1/shopify.py`
- Related implementation summary: `docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_inventory_increments_20260715.md`

## Shared API conventions

Both routes are JWT-protected and workspace-scoped. They require the caller to have one of these roles: `admin`, `manager`, `seller`, or `worker`.

Successful service responses use:

```json
{
  "data": {},
  "ok": true,
  "warnings": []
}
```

Domain-level failures use:

```json
{
  "error": "Human-readable message.",
  "ok": false
}
```

FastAPI authentication failures use its `detail` shape. FastAPI body/query type failures may also use its standard `422` `detail` array.

## 1. Get Shopify locations

### Endpoint

```http
GET /api/v1/integrations/shopify/locations?shop_integration_ids=shpint_1,shpint_2
```

The `shop_integration_ids` query parameter is required and is a comma-separated list. At least one ID must be supplied. Duplicate IDs are removed by the backend.

The backend performs a live Shopify read for each requested shop and includes inactive Shopify locations. A failure for one shop does not prevent other requested shops from being returned.

### Success response

```json
{
  "data": {
    "shops": [
      {
        "shop_integration_id": "shpint_1",
        "shop_domain": "warehouse.myshopify.com",
        "status": "ok",
        "locations": [
          {
            "location_id": "gid://shopify/Location/123",
            "name": "Warehouse A",
            "is_active": true
          },
          {
            "location_id": "gid://shopify/Location/456",
            "name": "Old Warehouse",
            "is_active": false
          }
        ]
      },
      {
        "shop_integration_id": "shpint_2",
        "shop_domain": "store.myshopify.com",
        "status": "needs_reauth",
        "locations": []
      },
      {
        "shop_integration_id": "shpint_3",
        "shop_domain": "failed.myshopify.com",
        "status": "error",
        "locations": []
      }
    ]
  },
  "ok": true,
  "warnings": []
}
```

### Response fields

| Field | Shape | Meaning |
|---|---|---|
| `shops` | array | One result for each requested shop, in requested-ID order. |
| `shop_integration_id` | string | ManagerBeyo shop integration ID. |
| `shop_domain` | string | Normalized Shopify domain. |
| `status` | `ok \| needs_reauth \| error` | Whether locations are available for this shop. |
| `locations` | array | Live Shopify locations, including inactive locations when the status is `ok`. |
| `location_id` | string | Shopify Location GID; send this exact value in `inventory_adjustments`. |
| `name` | string | Shopify location name. |
| `is_active` | boolean | Current Shopify location activity state. |

Frontend behavior:

- `ok`: allow the user to choose locations and enter quantities.
- `needs_reauth`: show the existing shop reauthorization action and disable inventory selection for that shop. This can mean the shop is not active or lacks `read_locations`.
- `error`: show a non-blocking location-load error for that shop; do not use locations from another shop as a substitute.
- Inactive locations may be displayed, but the worker activates an inactive location at quantity `0` before applying the requested additive increment.

### Errors

| HTTP status | Cause |
|---|---|
| `401` / `403` | Missing/invalid JWT or insufficient role. |
| `404` | At least one requested shop ID does not belong to the caller's workspace or does not exist. |
| `422` | `shop_integration_ids` is missing or empty. |
| `200` with a per-shop `error` status | Shopify could not be read for that individual shop. |

## 2. Process products with optional inventory increments

### Endpoint

```http
POST /api/v1/integrations/shopify/products/process
Content-Type: application/json
```

This remains an asynchronous endpoint. The HTTP response only confirms that the product-sync task was queued. Product creation/update, inventory adjustment, and metafield processing happen in the Shopify worker.

### Request shape

The existing product fields are unchanged. Add the optional `inventory_adjustments` array to each item when inventory should be incremented for that product's Shopify variant.

```json
{
  "items": [
    {
      "client_id": "frontend-product-123",
      "target_shop_integration_ids": ["shpint_1"],
      "title": "Dining chair",
      "description": "Oak dining chair",
      "sku": "CHAIR-001",
      "price": "1299",
      "tags": ["oak", "dining"],
      "metafields": {
        "custom.material": "oak"
      },
      "inventory_adjustments": [
        {
          "shop_integration_id": "shpint_1",
          "location_id": "gid://shopify/Location/123",
          "quantity_to_add": 3
        }
      ]
    }
  ]
}
```

### Multi-shop request

Each adjustment must be tagged with the shop it belongs to. The backend creates one sync item per `(product item, target shop)` and routes each adjustment to its matching shop:

```json
{
  "items": [
    {
      "client_id": "frontend-product-123",
      "target_shop_integration_ids": ["shpint_1", "shpint_2"],
      "title": "Dining chair",
      "sku": "CHAIR-001",
      "inventory_adjustments": [
        {
          "shop_integration_id": "shpint_1",
          "location_id": "gid://shopify/Location/123",
          "quantity_to_add": 3
        },
        {
          "shop_integration_id": "shpint_2",
          "location_id": "gid://shopify/Location/987",
          "quantity_to_add": 5
        }
      ]
    }
  ]
}
```

If `target_shop_integration_ids` is omitted, the existing behavior targets all active shops in the workspace. An adjustment's `shop_integration_id` must still match one of those target shops.

### Inventory adjustment rules

- `shop_integration_id`: required string; must be a target shop for the item.
- `location_id`: required Shopify Location GID matching `gid://shopify/Location/<numeric-id>`; use the value returned by the locations endpoint.
- `quantity_to_add`: required integer from `0` through `1,000,000`; booleans and decimal values are rejected.
- `0`: dropped as a no-op before any Shopify call. The frontend may preserve a zero row in local form state, but it should not be relied on as a submitted increment.
- Negative values: rejected.
- Duplicate `(shop_integration_id, location_id)` entries in one item: rejected.
- An adjustment tagged for a shop not in `target_shop_integration_ids`: rejected.
- The operation is additive. It never sets an absolute quantity and never decrements inventory.
- Keep `client_id` stable when retrying the same user action. The durable backend ledger uses `(shop_integration_id, client_id, location_id)` to prevent applying the same increment again. Do not reuse a client ID for a different requested quantity; that produces an inventory adjustment conflict.

### Immediate success response

```json
{
  "data": {
    "queued": true,
    "task_id": "task_01J...",
    "sync_item_client_ids": ["shpsi_01J..."],
    "target_count": 1
  },
  "ok": true,
  "warnings": []
}
```

`target_count` is the number of `(item, shop)` sync operations, not the number of inventory locations. No inventory outcome is available in this immediate response.

### Asynchronous completion event

Listen for the existing workspace-scoped socket event:

```text
shopify.products.synced
```

The event payload has this shape:

```json
{
  "task_id": "task_01J...",
  "succeeded": [
    {
      "frontend_client_id": "frontend-product-123",
      "shop_integration_id": "shpint_1",
      "sync_item_client_id": "shpsi_01J...",
      "requested_operation": "create",
      "shopify_product_id": "gid://shopify/Product/111",
      "shopify_variant_id": "gid://shopify/ProductVariant/222",
      "inventory": {
        "adjustments": [
          {
            "location_id": "gid://shopify/Location/123",
            "requested_delta": 3,
            "outcome": "applied",
            "shopify_error_code": null
          }
        ]
      }
    }
  ],
  "failed": []
}
```

The `succeeded` and `failed` arrays contain one entry per `(item, shop)` sync operation. The `inventory` field is included when inventory processing was requested, including when inventory failed.

### Inventory result shapes

Each inventory adjustment result contains:

```json
{
  "location_id": "gid://shopify/Location/123",
  "requested_delta": 3,
  "outcome": "applied",
  "shopify_error_code": null
}
```

`outcome` values:

- `applied`: the additive increment was applied by Shopify.
- `already_applied`: the durable ledger or baseline reconciliation determined that this increment had already been applied; no second increment was sent.
- `failed`: this location did not complete successfully.

For a partial failure, the product may already have been created or updated, but the sync operation is reported in `failed` with the existing item-level `error_code` / `error_message`; the `inventory.adjustments` array gives the per-location detail. There is intentionally no new `PARTIALLY_SUCCEEDED` status.

Example failure:

```json
{
  "task_id": "task_01J...",
  "succeeded": [],
  "failed": [
    {
      "frontend_client_id": "frontend-product-123",
      "shop_integration_id": "shpint_1",
      "sync_item_client_id": "shpsi_01J...",
      "requested_operation": "update",
      "error_code": "missing_inventory_scope",
      "error_message": "Shopify inventory access needs reauthorization before inventory can be updated.",
      "inventory": {
        "adjustments": [
          {
            "location_id": "gid://shopify/Location/123",
            "requested_delta": 3,
            "outcome": "failed",
            "shopify_error_code": "missing_inventory_scope"
          }
        ]
      }
    }
  ]
}
```

### Processing order

For an item with inventory adjustments, the worker:

1. Finds or creates the Shopify product and variant.
2. Persists the Shopify product, variant, and inventory-item IDs.
3. Validates live location ownership for the shop.
4. Enables tracking or activates locations when needed without adding the requested quantity during activation.
5. Applies the additive inventory adjustments.
6. Processes metafields.

Product-only submissions remain unchanged. Missing inventory scopes affect only items that request inventory adjustments; they do not prevent product-only syncs.

## Recommended frontend flow

1. Load the selected shop integrations.
2. Call `GET /locations` with the selected integration IDs whenever the selected shops change; cache the result briefly by sorted shop-ID list.
3. Render each shop's locations under that shop only. Preserve inactive rows visibly, but communicate that Shopify may activate them during processing.
4. Keep quantity `0` in local form state if useful for the UI, but submit only positive quantities in `inventory_adjustments`.
5. Keep the product item's `client_id` stable for retries of the same action.
6. Call `POST /products/process`, store the returned `task_id`, and listen for `shopify.products.synced` to update the product-sync UI.
7. For `needs_reauth` or `missing_inventory_scope`, show the existing reauthorization flow for that specific shop.

## No-secret guarantee

Neither route returns Shopify access tokens, OAuth codes, HMAC values, or raw Shopify responses. The frontend should treat `shop_domain`, IDs, names, statuses, and error codes as the complete contract.
