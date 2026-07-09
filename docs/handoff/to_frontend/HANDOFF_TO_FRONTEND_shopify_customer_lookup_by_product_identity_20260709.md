# HANDOFF_TO_FRONTEND_shopify_customer_lookup_by_product_identity_20260709

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_shopify_customer_lookup_by_product_identity_20260709`
- Created at (UTC): `2026-07-09T11:44:44Z`
- Owner agent: `Codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_by_product_identity_20260709.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`

## Backend delivery context

- What backend implemented: A new read-only Shopify lookup endpoint that lets the frontend resolve customer/order ownership for a physical product identity by `sku` and/or Shopify barcode (`article_number`) across all active Shopify shop integrations in the current workspace.
- API or contract changes: New protected route added under the existing Shopify admin prefix: `POST /api/v1/integrations/shopify/customers/by-product-identity`.
- Feature flags/toggles (if any): None. The route is always registered. Actual per-shop lookup depends on the shop having granted `read_orders`, `read_products`, and `read_customers`.

## Frontend action required

1. Add a client call for `POST /api/v1/integrations/shopify/customers/by-product-identity`.
2. Only expose the UI for users with backend roles `admin`, `manager`, or `seller`. `worker` is rejected with `403`.
3. Send at least one of `sku` or `article_number`. Sending both is allowed and preferred when available.
4. Read the payload from `response.data`, not from the top level.
5. Handle partial success: `customer_matches` can contain valid results while `failed_shops` simultaneously explains shops that were skipped or failed.

## Interface details

### Endpoint

- Method: `POST`
- Path: `/api/v1/integrations/shopify/customers/by-product-identity`
- Auth: JWT required
- Allowed roles: `admin`, `manager`, `seller`

### Request body

```json
{
  "sku": "SKU-123",
  "article_number": "BAR-123"
}
```

Field rules:

- `sku`: optional string
- `article_number`: optional string
- At least one of the two must be present after trimming whitespace.
- Both may be provided in the same request.
- Per shop, backend behavior is:
  - try `sku` first if present
  - if that shop returns no exact SKU match and `article_number` is present, fall back to barcode lookup for that same shop

### Success response envelope

HTTP `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "customer_matches": [
      {
        "shop_integration_id": "shpint_1",
        "shop_domain": "shop-a.myshopify.com",
        "match_type": "sku",
        "matched_value": "SKU-123",
        "order_id": "gid://shopify/Order/1",
        "order_name": "#1001",
        "customer_id": "gid://shopify/Customer/1",
        "display_name": "Customer Name",
        "primary_phone_number": "+46701234567",
        "primary_email": "customer@example.com",
        "address": {
          "street_address": "Ship Street 1",
          "post_code": "12345",
          "coordinates": {
            "latitude": 59.1,
            "longitude": 18.2
          },
          "city": "Stockholm",
          "district": "Stockholm County"
        }
      }
    ],
    "failed_shops": [
      {
        "shop_integration_id": "shpint_2",
        "shop_domain": "shop-b.myshopify.com",
        "error_code": "missing_required_scope"
      }
    ]
  }
}
```

### Response field meanings

- `customer_matches`: flat aggregated list across all active Shopify shops in the workspace.
- `failed_shops`: safe per-shop failures that did not abort the full request.
- `match_type`: `"sku"` or `"barcode"`.
- `matched_value`: the exact value that produced this result for that shop.
- `display_name`: best available customer-facing name, not guaranteed to come from a linked Shopify customer account. It may fall back to shipping or billing recipient names.
- `primary_phone_number`: best available phone using backend fallback priority.
- `primary_email`: best available email using backend fallback priority.
- `address`: best available address using backend fallback priority.
- `address.coordinates.latitude` / `longitude`: nullable floats; they may both be `null`.

### Important frontend behavior notes

- `customer_matches` may be empty with HTTP `200`. That means:
  - no active shop had an exact match, or
  - all active shops were skipped for missing scope
- `failed_shops` does not mean the whole request failed.
- The backend only returns exact matches:
  - `sku` must exactly match a line item SKU
  - `article_number` must exactly match a Shopify variant barcode
- The same request can return matches from multiple shops.
- The same request can return different `match_type` values for different shops depending on whether SKU matched before barcode fallback.

### Error cases

`401` or `403` from auth dependency:

```json
{ "detail": "Insufficient role permissions." }
```

Typical causes:

- missing or invalid JWT
- `worker` role

Domain validation error, HTTP `422`:

```json
{
  "ok": false,
  "error": "At least one of sku or article_number is required."
}
```

Typical cause:

- both `sku` and `article_number` omitted or blank after trimming

Total upstream failure, HTTP `502`:

```json
{
  "ok": false,
  "error": "All Shopify shop lookups failed."
}
```

Typical cause:

- every active, sufficiently scoped shop lookup failed with Shopify/API transport/graphql errors

## Validation notes

- Backend validation run: the new route, query, infra adapter, and normalization logic were covered by focused tests; the command used was `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt PYTHONPATH=. pytest tests/unit/domain/shopify/test_customer_lookup.py tests/unit/services/infra/shopify/test_product_identity_client.py tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py tests/unit/test_shopify_router.py -q` and it passed with `63 passed`.
- Suggested frontend validation:
  - require at least one non-blank field before submit
  - trim both values client-side before sending
  - treat `customer_matches.length === 0` as a valid “no ownership found” state, not a transport failure
  - surface `failed_shops` as a secondary warning or info state, not as the primary result when matches exist

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_by_product_identity_20260709.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`
- Related debug plan (optional): `none`
